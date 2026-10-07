import cv2
import logging
from typing import Dict, Any, Optional, List
import numpy as np

from backend.app.config.settings import settings
from backend.app.core.preprocessor import ImagePreprocessor
from backend.app.core.plate_normalizer import PlateNormalizer

logger = logging.getLogger(__name__)


def _patch_paddle_inference():
    """Aplica parche de compatibilidad para paddle.inference evitando errores de oneDNN y new_ir."""
    try:
        import paddle.inference as paddle_inference
        if not getattr(paddle_inference, "_antigravity_patched", False):
            orig_create = paddle_inference.create_predictor

            def patched_create(config):
                if hasattr(config, "enable_new_ir"):
                    config.enable_new_ir(False)
                if hasattr(config, "disable_mkldnn"):
                    config.disable_mkldnn()
                return orig_create(config)

            paddle_inference.create_predictor = patched_create
            paddle_inference._antigravity_patched = True
    except Exception as e:
        logger.debug(f"Nota en parche de paddle inference: {e}")


class OCREngine:
    """Motor de OCR con PaddleOCR como motor principal, ensamble de filtros OpenCV y normalización boliviana."""

    _instance: Optional["OCREngine"] = None

    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.normalizer = PlateNormalizer()
        self.engine_type = getattr(settings, "OCR_ENGINE", "paddleocr").lower()

        self.paddle_reader = None
        self.easyocr_reader = None

        if self.engine_type == "paddleocr":
            self.paddle_reader = self._init_paddle_reader()
        else:
            self.easyocr_reader = self._init_easyocr_reader()

    @classmethod
    def get_instance(cls) -> "OCREngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_paddle_reader(self):
        _patch_paddle_inference()
        try:
            from paddleocr import PaddleOCR
            lang = getattr(settings, "PADDLEOCR_LANG", "en")
            logger.info(f"Inicializando PaddleOCR (PP-OCR) con lang={lang}...")
            return PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                lang=lang,
            )
        except Exception as e:
            logger.error(f"Error al inicializar PaddleOCR: {e}. Activando EasyOCR de respaldo.")
            self.engine_type = "easyocr"
            return None

    def _init_easyocr_reader(self):
        try:
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
        except Exception as e:
            logger.error(f"Error al inicializar EasyOCR: {e}")
            return None

    def _extract_from_paddle(self, img_variant: np.ndarray) -> Optional[Dict[str, Any]]:
        """Ejecuta inferencia de PaddleOCR sobre una variante de imagen."""
        if self.paddle_reader is None:
            return None

        inp = cv2.cvtColor(img_variant, cv2.COLOR_GRAY2BGR) if len(img_variant.shape) == 2 else img_variant

        try:
            results = list(self.paddle_reader.predict(inp))
        except Exception as e:
            logger.warning(f"Error en predicción PaddleOCR: {e}")
            return None

        if not results:
            return None

        raw_texts = []
        confidences = []
        raw_details = []

        for r in results:
            rec_texts = r.get("rec_texts", [])
            rec_scores = r.get("rec_scores", [])
            rec_boxes = r.get("rec_boxes", [])

            for i, text in enumerate(rec_texts):
                t_clean = text.strip()
                if t_clean:
                    conf = float(rec_scores[i]) if i < len(rec_scores) else 0.5
                    raw_texts.append(t_clean)
                    confidences.append(conf)

                    bbox_coords = []
                    if i < len(rec_boxes):
                        box = rec_boxes[i]
                        if len(box) == 4:
                            x1, y1, x2, y2 = [int(v) for v in box]
                            bbox_coords = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

                    raw_details.append({
                        "bbox": bbox_coords,
                        "text": t_clean,
                        "confidence": round(conf, 4),
                    })

        if not raw_texts:
            return None

        combined_raw = " ".join(raw_texts)
        avg_conf = float(np.mean(confidences)) if confidences else 0.0

        plate_raw, plate_normalized, is_valid = self.normalizer.normalize(combined_raw)
        final_conf = min(avg_conf * 1.15, 1.0) if is_valid else avg_conf

        return {
            "plate_raw": plate_raw,
            "plate_normalized": plate_normalized,
            "is_valid": is_valid,
            "ocr_confidence": round(final_conf, 4),
            "raw_detections": raw_details,
        }

    def _extract_from_easyocr(self, img_variant: np.ndarray) -> Optional[Dict[str, Any]]:
        """Ejecuta inferencia de EasyOCR sobre una variante de imagen."""
        if self.easyocr_reader is None:
            return None

        ocr_kwargs = {
            "allowlist": "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- ",
            "paragraph": False,
            "detail": 1,
            "text_threshold": 0.25,
            "low_text": 0.15,
            "link_threshold": 0.20,
            "mag_ratio": 1.5,
        }

        try:
            results = self.easyocr_reader.readtext(img_variant, **ocr_kwargs)
        except Exception as e:
            logger.warning(f"Error en predicción EasyOCR: {e}")
            return None

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
        final_conf = min(avg_conf * 1.15, 1.0) if is_valid else avg_conf

        return {
            "plate_raw": plate_raw,
            "plate_normalized": plate_normalized,
            "is_valid": is_valid,
            "ocr_confidence": round(final_conf, 4),
            "raw_detections": raw_details,
        }

    def read_plate(self, plate_img: np.ndarray) -> Dict[str, Any]:
        """Ejecuta OCR evaluando un ensamble de filtros OpenCV:
        1. Escala de grises pura
        2. Ajuste de contraste Gamma (ideal para placas en relieve / despintadas)
        3. Ajuste de contraste CLAHE (ecualización adaptativa local)
        4. Ajuste de contraste estiramiento lineal
        5. Binarización Otsu
        6. Binarización Adaptativa Gaussiana
        7. Imagen RGB original
        
        Selecciona el resultado con mayor validez normativa boliviana y confianza.
        """
        if plate_img is None or plate_img.size == 0:
            return {
                "plate_raw": "",
                "plate_normalized": "",
                "is_valid": False,
                "ocr_confidence": 0.0,
                "raw_detections": [],
            }

        # Generar ensamble de variantes filtradas
        variants = self.preprocessor.generate_ocr_variants(plate_img)
        if not variants:
            variants = {"raw": plate_img}

        candidates = []

        for name, img_var in variants.items():
            if self.engine_type == "paddleocr" and self.paddle_reader is not None:
                cand = self._extract_from_paddle(img_var)
            else:
                cand = self._extract_from_easyocr(img_var)

            if cand:
                cand["variant_name"] = name
                candidates.append(cand)

                # Si es una placa boliviana válida con alta confianza, retornar anticipadamente
                if cand["is_valid"] and cand["ocr_confidence"] >= 0.70:
                    return cand

        # Si PaddleOCR no detectó nada y EasyOCR está disponible, probar fallback
        if not candidates and self.engine_type == "paddleocr":
            if self.easyocr_reader is None:
                self.easyocr_reader = self._init_easyocr_reader()
            if self.easyocr_reader:
                for name, img_var in variants.items():
                    cand = self._extract_from_easyocr(img_var)
                    if cand:
                        cand["variant_name"] = f"easyocr_{name}"
                        candidates.append(cand)
                        if cand["is_valid"] and cand["ocr_confidence"] >= 0.65:
                            return cand

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
