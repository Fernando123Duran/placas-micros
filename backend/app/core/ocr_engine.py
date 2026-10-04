import logging
from typing import Dict, Any, Optional, List
import numpy as np

from backend.app.config.settings import settings
from backend.app.core.preprocessor import ImagePreprocessor
from backend.app.core.plate_normalizer import PlateNormalizer

logger = logging.getLogger(__name__)


class OCREngine:
    """Motor de OCR basado en EasyOCR con preprocesamiento y normalización de placas."""

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

    def read_plate(self, plate_img: np.ndarray) -> Dict[str, Any]:
        """Ejecuta OCR sobre una imagen recortada de placa.
        
        Aplica preprocesamiento, extrae texto, normaliza y valida sintaxis boliviana.
        """
        if plate_img is None or plate_img.size == 0:
            return {
                "plate_raw": "",
                "plate_normalized": "",
                "is_valid": False,
                "ocr_confidence": 0.0,
                "raw_detections": [],
            }

        # 1. Preprocesar variante por defecto
        processed = self.preprocessor.preprocess_plate(plate_img, variant="default")

        # 2. Ejecución de EasyOCR con umbrales calibrados para placas vehiculares en movimiento
        ocr_kwargs = {
            "allowlist": "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- ",
            "paragraph": False,
            "detail": 1,
            "text_threshold": 0.25,
            "low_text": 0.15,
            "link_threshold": 0.20,
            "mag_ratio": 1.5,
        }

        # Pase 1: con preprocesamiento CLAHE / normalización
        results = self.reader.readtext(processed, **ocr_kwargs)

        # Pase 2: si no detectó texto suficiente, intentar con imagen original a color (RGB)
        if not results:
            rgb_img = cv2.cvtColor(plate_img, cv2.COLOR_BGR2RGB) if len(plate_img.shape) == 3 else plate_img
            results = self.reader.readtext(rgb_img, **ocr_kwargs)

        # Pase 3: si sigue sin detectar, intentar con sharpen
        if not results:
            processed_sharpen = self.preprocessor.preprocess_plate(plate_img, variant="with_sharpen")
            results = self.reader.readtext(processed_sharpen, **ocr_kwargs)

        if not results:
            return {
                "plate_raw": "",
                "plate_normalized": "",
                "is_valid": False,
                "ocr_confidence": 0.0,
                "raw_detections": [],
            }

        # 3. Concatenar textos y calcular confianza promedio ponderada
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

        combined_raw = " ".join(raw_texts)
        avg_conf = float(np.mean(confidences)) if confidences else 0.0

        # 4. Normalizar y validar sintaxis boliviana
        plate_raw, plate_normalized, is_valid = self.normalizer.normalize(combined_raw)

        # Si es válida sintácticamente, se premia la confianza
        final_conf = avg_conf
        if is_valid:
            final_conf = min(avg_conf * 1.1, 1.0)

        return {
            "plate_raw": plate_raw,
            "plate_normalized": plate_normalized,
            "is_valid": is_valid,
            "ocr_confidence": round(final_conf, 4),
            "raw_detections": raw_details,
        }
