import os
import cv2
import json
import uuid
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.core.detector import CascadeDetector
from backend.app.core.ocr_engine import OCREngine
from backend.app.core.tracker import TrackCandidateSelector
from backend.app.db.models import DetectionEvent
from backend.app.db.session import SessionLocal, is_duplicate_plate

logger = logging.getLogger(__name__)


class PipelineService:
    """Servicio orquestador del pipeline completo de detección, OCR y persistencia."""

    def __init__(self):
        self.detector = CascadeDetector.get_instance()
        self.ocr_engine = OCREngine.get_instance()
        self.storage_path = Path(settings.STORAGE_PATH)

    def _save_evidence(
        self,
        prefix: str,
        full_img: np.ndarray,
        micro_crop: np.ndarray,
        plate_crop: np.ndarray,
    ) -> Tuple[str, str, str]:
        """Guarda los 3 niveles de evidencia fotográfica en el disco."""
        unique_id = f"{prefix}_{uuid.uuid4().hex[:10]}"

        full_rel = f"full/{unique_id}.jpg"
        micro_rel = f"micros/{unique_id}.jpg"
        plate_rel = f"plates/{unique_id}.jpg"

        full_abs = self.storage_path / full_rel
        micro_abs = self.storage_path / micro_rel
        plate_abs = self.storage_path / plate_rel

        cv2.imwrite(str(full_abs), full_img)
        cv2.imwrite(str(micro_abs), micro_crop)
        cv2.imwrite(str(plate_abs), plate_crop)

        return full_rel, micro_rel, plate_rel

    def process_image(
        self,
        image_bytes: bytes,
        filename: str = "upload.jpg",
        db: Session = None,
    ) -> Dict[str, Any]:
        """Procesa una imagen fija completa enviada por la API o script."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            # 1. Decodificar imagen
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("No se pudo decodificar la imagen enviada")

            # 2. Detección en cascada (Micros -> Placas)
            detections = self.detector.detect_in_image(img)

            total_micros = len(detections)
            total_plates = 0
            new_records = 0
            results_list = []

            for det in detections:
                micro_bbox = det["micro_bbox"]
                micro_conf = det["micro_confidence"]
                micro_crop = det["micro_crop"]
                micro_evidence_url = None

                plates_info = []

                for p in det["plates"]:
                    total_plates += 1
                    plate_crop = p["plate_crop"]
                    plate_bbox = p["plate_bbox_full"]
                    plate_conf = p["plate_confidence"]

                    # 3. OCR sobre el recorte de placa
                    ocr_res = self.ocr_engine.read_plate(plate_crop)
                    plate_norm = ocr_res["plate_normalized"]
                    plate_raw = ocr_res["plate_raw"]
                    is_valid = ocr_res["is_valid"]
                    ocr_conf = ocr_res["ocr_confidence"]

                    # Solo procesar si el OCR extrajo algún texto con confianza aceptable
                    is_dup = False
                    plate_evidence_url = None
                    micro_evidence_url = None

                    if plate_norm and ocr_conf >= settings.MIN_OCR_CONFIDENCE:
                        # 4. Regla anti-ráfagas / deduplicación
                        is_dup = is_duplicate_plate(
                            db, plate_norm, window_minutes=settings.DEDUP_WINDOW_MINUTES
                        )

                        if not is_dup:
                            # 5. Guardar evidencias fotográficas
                            full_rel, micro_rel, plate_rel = self._save_evidence(
                                prefix="img",
                                full_img=img,
                                micro_crop=micro_crop,
                                plate_crop=plate_crop,
                            )
                            plate_evidence_url = f"/storage/{plate_rel}"
                            micro_evidence_url = f"/storage/{micro_rel}"

                            # 6. Registrar en Base de Datos
                            event = DetectionEvent(
                                timestamp=datetime.datetime.utcnow(),
                                source="image",
                                track_id=None,
                                plate_raw=plate_raw,
                                plate_normalized=plate_norm,
                                is_valid_bolivian=is_valid,
                                micro_confidence=micro_conf,
                                plate_confidence=plate_conf,
                                ocr_confidence=ocr_conf,
                                micro_bbox=json.dumps(micro_bbox),
                                plate_bbox=json.dumps(plate_bbox),
                                full_image_path=full_rel,
                                micro_image_path=micro_rel,
                                plate_image_path=plate_rel,
                            )
                            db.add(event)
                            db.commit()
                            new_records += 1

                    plates_info.append({
                        "plate_raw": plate_raw,
                        "plate_normalized": plate_norm,
                        "is_valid_bolivian": is_valid,
                        "plate_confidence": plate_conf,
                        "ocr_confidence": ocr_conf,
                        "plate_bbox_full": plate_bbox,
                        "is_duplicate": is_dup,
                        "evidence_plate_url": plate_evidence_url,
                    })

                results_list.append({
                    "micro_confidence": micro_conf,
                    "micro_bbox": micro_bbox,
                    "evidence_micro_url": micro_evidence_url,
                    "plates": plates_info,
                })

            return {
                "success": True,
                "source_filename": filename,
                "total_micros_detected": total_micros,
                "total_plates_detected": total_plates,
                "new_records_saved": new_records,
                "detections": results_list,
            }

        finally:
            if close_db:
                db.close()

    def process_video_file(
        self,
        video_path: str,
        sample_fps: float = None,
        max_duration_sec: float = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """Procesa un archivo de video completo con ByteTrack y selección del mejor frame de placa."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise ValueError(f"No se pudo abrir el archivo de video: {video_path}")

            native_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            step = max(int(native_fps / (sample_fps or settings.VIDEO_SAMPLE_FPS)), 1)

            logger.info(
                f"Procesando video: {video_path} ({total_frames} frames a {native_fps:.1f} fps). "
                f"Muestreando cada {step} frames (~{sample_fps or settings.VIDEO_SAMPLE_FPS} fps)..."
            )

            candidate_selector = TrackCandidateSelector()

            frame_idx = 0
            processed_count = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % step == 0:
                    processed_count += 1
                    timestamp_sec = frame_idx / native_fps

                    if max_duration_sec and timestamp_sec > max_duration_sec:
                        break

                    # Tracking de micros con ByteTrack
                    track_results = self.detector.micro_model.track(
                        frame,
                        persist=True,
                        conf=settings.MIN_MICRO_CONFIDENCE,
                        device=self.detector.device,
                        verbose=False,
                    )[0]

                    if track_results.boxes is not None and track_results.boxes.id is not None:
                        for box, track_id_tensor in zip(track_results.boxes, track_results.boxes.id):
                            track_id = int(track_id_tensor)
                            m_conf = float(box.conf[0])
                            mx1, my1, mx2, my2 = [int(v) for v in box.xyxy[0]]

                            # Recorte de micro con padding
                            micro_crop, crop_bbox = self.detector.extract_crop_with_padding(
                                frame, [mx1, my1, mx2, my2], padding_ratio=settings.MICRO_CROP_PADDING
                            )
                            if micro_crop.size == 0:
                                continue

                            cx1, cy1, _, _ = crop_bbox

                            # Detectar placas dentro del micro
                            plate_res = self.detector.plate_model(
                                micro_crop,
                                conf=settings.MIN_PLATE_CONFIDENCE,
                                device=self.detector.device,
                                verbose=False,
                            )[0]

                            if plate_res.boxes is not None and len(plate_res.boxes) > 0:
                                for p_box in plate_res.boxes:
                                    p_conf = float(p_box.conf[0])
                                    px1, py1, px2, py2 = [int(v) for v in p_box.xyxy[0]]

                                    gx1 = cx1 + px1
                                    gy1 = cy1 + py1
                                    gx2 = cx1 + px2
                                    gy2 = cy1 + py2

                                    plate_crop = micro_crop[py1:py2, px1:px2].copy()
                                    if plate_crop.size == 0:
                                        continue

                                    sharpness = self.detector.preprocessor.calculate_sharpness(plate_crop)

                                    candidate_selector.add_candidate(
                                        track_id=track_id,
                                        frame_idx=frame_idx,
                                        timestamp_sec=timestamp_sec,
                                        micro_bbox=[mx1, my1, mx2, my2],
                                        micro_crop=micro_crop,
                                        micro_confidence=m_conf,
                                        plate_bbox_full=[gx1, gy1, gx2, gy2],
                                        plate_crop=plate_crop,
                                        plate_confidence=p_conf,
                                        sharpness=sharpness,
                                    )

                frame_idx += 1

            cap.release()

            # ── Fase de Consolidación y OCR por cada Track ──────────────────────
            unique_tracks = list(candidate_selector.tracks.keys())
            records_saved = []

            for track_id in unique_tracks:
                best_cands = candidate_selector.get_best_candidates(track_id)
                if not best_cands:
                    continue

                best_ocr = None
                best_cand = None

                # Probar OCR en los mejores candidatos del track
                for cand in best_cands:
                    ocr_res = self.ocr_engine.read_plate(cand.plate_crop)
                    if ocr_res["plate_normalized"] and ocr_res["ocr_confidence"] >= settings.MIN_OCR_CONFIDENCE:
                        if best_ocr is None or ocr_res["ocr_confidence"] > best_ocr["ocr_confidence"]:
                            best_ocr = ocr_res
                            best_cand = cand
                        # Si encontramos una válida boliviana con alta confianza, detener búsqueda para este track
                        if ocr_res["is_valid"] and ocr_res["ocr_confidence"] >= 0.75:
                            break

                if best_ocr and best_cand:
                    plate_norm = best_ocr["plate_normalized"]
                    is_dup = is_duplicate_plate(
                        db, plate_norm, window_minutes=settings.DEDUP_WINDOW_MINUTES
                    )

                    if not is_dup:
                        full_rel, micro_rel, plate_rel = self._save_evidence(
                            prefix=f"vid_t{track_id}",
                            full_img=best_cand.micro_crop,  # Usar frame del micro
                            micro_crop=best_cand.micro_crop,
                            plate_crop=best_cand.plate_crop,
                        )

                        event = DetectionEvent(
                            timestamp=datetime.datetime.utcnow(),
                            source="video",
                            track_id=track_id,
                            plate_raw=best_ocr["plate_raw"],
                            plate_normalized=plate_norm,
                            is_valid_bolivian=best_ocr["is_valid"],
                            micro_confidence=best_cand.micro_confidence,
                            plate_confidence=best_cand.plate_confidence,
                            ocr_confidence=best_ocr["ocr_confidence"],
                            micro_bbox=json.dumps(best_cand.micro_bbox),
                            plate_bbox=json.dumps(best_cand.plate_bbox_full),
                            full_image_path=full_rel,
                            micro_image_path=micro_rel,
                            plate_image_path=plate_rel,
                        )
                        db.add(event)
                        db.commit()
                        db.refresh(event)
                        records_saved.append(event)

            return {
                "success": True,
                "video_filename": Path(video_path).name,
                "total_frames_processed": processed_count,
                "duration_seconds": round(frame_idx / max(native_fps, 1.0), 2),
                "unique_tracks_detected": len(unique_tracks),
                "plates_registered": len(records_saved),
                "items": records_saved,
            }

        finally:
            if close_db:
                db.close()
