import cv2
import numpy as np
from pathlib import Path
import yaml
from typing import Dict, Any, Tuple

from backend.app.config.settings import ROOT_DIR, settings


class ImagePreprocessor:
    """Preprocesamiento especializado para imágenes de placas y cálculo de calidad."""

    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path or (ROOT_DIR / "configs" / "ocr_preprocess.yaml"))
        self.configs = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    @staticmethod
    def calculate_sharpness(img: np.ndarray) -> float:
        """Calcula la nitidez de la imagen usando la varianza del operador Laplaciano.
        
        Valores típicos:
        - < 50: muy borrosa (desenfoque por movimiento severo)
        - 50 - 150: nitidez moderada
        - > 150: buena nitidez
        """
        if img is None or img.size == 0:
            return 0.0
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def preprocess_plate(self, plate_img: np.ndarray, variant: str = None) -> np.ndarray:
        """Aplica el pipeline de preprocesamiento a un recorte de placa para mejorar el OCR."""
        if plate_img is None or plate_img.size == 0:
            return plate_img

        variant_name = variant or settings.OCR_PREPROCESS_VARIANT
        cfg = self.configs.get(variant_name, self.configs.get("default", {}))

        processed = plate_img.copy()

        # 1. Resize proporcional si la altura es menor al mínimo o para normalizar
        h, w = processed.shape[:2]
        target_h = cfg.get("resize_target_height", 80)
        min_h = cfg.get("resize_min_height", 32)

        if h < min_h or h != target_h:
            scale = target_h / max(h, 1)
            new_w = max(int(w * scale), 10)
            processed = cv2.resize(processed, (new_w, target_h), interpolation=cv2.INTER_CUBIC)

        # 2. Escala de grises
        if cfg.get("grayscale", True) and len(processed.shape) == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

        # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        if cfg.get("clahe", True):
            clip = cfg.get("clahe_clip", 2.0)
            grid = tuple(cfg.get("clahe_grid", [8, 8]))
            clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=grid)
            if len(processed.shape) == 2:
                processed = clahe.apply(processed)
            else:
                # Si sigue en color, aplicar sobre canal L en LAB
                lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                l = clahe.apply(l)
                processed = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

        # 4. Sharpening opcional
        if cfg.get("sharpening", False):
            factor = cfg.get("sharpening_factor", 0.5)
            kernel = np.array([[0, -1, 0], [-1, 4 + factor, -1], [0, -1, 0]], dtype=np.float32)
            processed = cv2.filter2D(processed, -1, kernel)

        # 5. Denoise opcional
        if cfg.get("denoise", False):
            sigma = cfg.get("denoise_sigma", 0.5)
            processed = cv2.GaussianBlur(processed, (3, 3), sigma)

        # 6. Binarización opcional
        if cfg.get("threshold", False):
            method = cfg.get("threshold_method", "otsu")
            if len(processed.shape) == 3:
                processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            if method == "adaptive":
                processed = cv2.adaptiveThreshold(
                    processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                )
            else:
                _, processed = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return processed
