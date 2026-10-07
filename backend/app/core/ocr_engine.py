import cv2
import logging
from typing import Dict, Any, Optional, List
import numpy as np

from backend.app.config.settings import settings
from backend.app.core.preprocessor import ImagePreprocessor
from backend.app.core.plate_normalizer import PlateNormalizer

logger = logging.getLogger(__name__)


class OCREngine:
    """Motor de OCR con preprocesamiento avanzado OpenCV y ensamble multi-variante."""

    _instance: Optional["OCREngine"] = None

    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.normalizer = PlateNormalizer()
        self.reader = self._init_reader()

    @classmethod
    def get_instance(cls) -> "OCREngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_reader(self):
        import easyocr
        languages = settings.OCR_LANGUAGES
        if isinstance(languages, str):
            languages = [languages]

        logger.info(f"Cargando EasyOCR en GPU={settings.USE_GPU} desde {settings.EASYOCR_MODEL_DIR}...")
        return easyocr.Reader(
            languages,
            gpu=settings.USE_GPU,
            model_storage_directory=settings.EASYOCR_MODEL_DIR,
            download_enabled=False,
            verbose=False,
        )

    def _extract_from_variant(self, img_variant: np.ndarray, ocr_kwargs: dict) -> Dict[str, Any]:
        """Ejecuta EasyOCR sobre una imagen específica y procesa resultados."""
        results = self.reader.readtext(img_variant, **ocr_kwargs)
        if not results:
            return None

        raw_texts = []
        confidences = []
        raw_details = []

        for bbox, text, conf in results:
            text_stripped = text.strip()
            if text_stripped:
                raw_texts.append(text_stripped)
                confidences.append(float(conf))
                raw_details.append({
                    "bbox": [[int(pt[0]), int(pt[1])] for pt in bbox],
                    "text": text_stripped,
                    "confidence": float(conf),
                })

        if not raw_texts:
            return None

        combined_raw = " ".join(raw_texts)
        avg_conf = float(np.mean(confidences)) if confidences else 0.0

        plate_raw, plate_normalized, is_valid = self.normalizer.normalize(combined_raw)

        final_conf = avg_conf
        if is_valid:
            final_conf = min(avg_conf * 1.15, 1.0)

        return {
            "plate_raw": plate_raw,
            "plate_normalized": plate_normalized,
            "is_valid": is_valid,
            "ocr_confidence": round(final_conf, 4),
            "raw_detections": raw_details,
        }

    def read_plate(self, plate_img: np.ndarray) -> Dict[str, Any]:
        """Ejecuta OCR con ensamble de filtros OpenCV para máxima precisión.
        
        Evalúa múltiples variantes (Deskew + Bilateral + CLAHE, Black-Hat morfológico,
        Sharpening y RGB directo) seleccionando el resultado con mayor validez y confianza.
        """
        if plate_img is None or plate_img.size == 0:
            return {
                "plate_raw": "",
                "plate_normalized": "",
                "is_valid": False,
                "ocr_confidence": 0.0,
                "raw_detections": [],
            }

        ocr_kwargs = {
            "allowlist": "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- ",
            "paragraph": False,
            "detail": 1,
            "text_threshold": 0.25,
            "low_text": 0.15,
            "link_threshold": 0.20,
            "mag_ratio": 1.5,
        }

        # Generar variantes con OpenCV
        # Variante 1: Deskewing + Bilateral + CLAHE + Border Padding (Estándar recomendada)
        v_default = self.preprocessor.preprocess_plate(plate_img, variant="default")

        # Variante 2: Morfología Black-Hat para resaltar trazos oscuros
        v_morph = self.preprocessor.preprocess_plate(plate_img, variant="with_morphology")

        # Variante 3: Sharpening (realce de bordes)
        v_sharpen = self.preprocessor.preprocess_plate(plate_img, variant="with_sharpen")

        # Variante 4: RGB original con padding
        v_rgb = cv2.cvtColor(plate_img, cv2.COLOR_BGR2RGB) if len(plate_img.shape) == 3 else plate_img
        v_rgb = cv2.copyMakeBorder(v_rgb, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=[255, 255, 255])

        # Variante 5: Relieve troquelado y sombras para placas desgastadas/despintadas
        v_embossed = self.preprocessor.preprocess_embossed_plate(plate_img)

        candidates = []

        # 1. Probar variante default
        cand1 = self._extract_from_variant(v_default, ocr_kwargs)
        if cand1:
            candidates.append(cand1)
            # Si cand1 ya es una placa boliviana válida con alta confianza, usar directamente
            if cand1["is_valid"] and cand1["ocr_confidence"] >= 0.60:
                return cand1

        # 2. Probar variante morfológica
        cand2 = self._extract_from_variant(v_morph, ocr_kwargs)
        if cand2:
            candidates.append(cand2)
            if cand2["is_valid"] and cand2["ocr_confidence"] >= 0.60:
                return cand2

        # 3. Probar variante de relieve troquelado (para placas despintadas)
        cand_emboss = self._extract_from_variant(v_embossed, ocr_kwargs)
        if cand_emboss:
            candidates.append(cand_emboss)
            if cand_emboss["is_valid"] and cand_emboss["ocr_confidence"] >= 0.55:
                return cand_emboss

        # 4. Probar variante sharpening
        cand3 = self._extract_from_variant(v_sharpen, ocr_kwargs)
        if cand3:
            candidates.append(cand3)

        # 5. Probar variante RGB
        cand4 = self._extract_from_variant(v_rgb, ocr_kwargs)
        if cand4:
            candidates.append(cand4)

        if not candidates:
            return {
                "plate_raw": "",
                "plate_normalized": "",
                "is_valid": False,
                "ocr_confidence": 0.0,
                "raw_detections": [],
            }

        # Criterio de Selección:
        # Prioridad 1: Placas con formato boliviano válido (is_valid == True) ordenadas por confianza
        valid_candidates = [c for c in candidates if c["is_valid"]]
        if valid_candidates:
            valid_candidates.sort(key=lambda c: c["ocr_confidence"], reverse=True)
            return valid_candidates[0]

        # Prioridad 2: Mayor longitud de texto normalizado y mayor confianza
        candidates.sort(
            key=lambda c: (len(c["plate_normalized"]), c["ocr_confidence"]),
            reverse=True,
        )
        return candidates[0]
