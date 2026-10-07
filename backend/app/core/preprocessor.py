import cv2
import numpy as np
from pathlib import Path
import yaml
from typing import Dict, Any, Tuple

from backend.app.config.settings import ROOT_DIR, settings


class ImagePreprocessor:
    """Preprocesamiento avanzado con OpenCV para mejorar la legibilidad en OCR de placas vehiculares."""

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

    @staticmethod
    def correct_skew(img: np.ndarray, max_angle: float = 25.0) -> np.ndarray:
        """Corrige la inclinación/ángulo (deskewing) de la placa rotándola para que quede horizontal."""
        if img is None or img.size == 0:
            return img

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Binarizar para detectar la orientación de los caracteres o el contorno de la placa
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))

        if len(coords) < 15:
            return img

        # Obtener el rectángulo de área mínima
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]

        # Normalizar el ángulo
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle

        # Si el ángulo es despreciable (<0.5°) o excesivo (>max_angle), no rotar
        if abs(angle) < 0.5 or abs(angle) > max_angle:
            return img

        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return rotated

    @staticmethod
    def apply_blackhat(gray_img: np.ndarray, kernel_size: Tuple[int, int] = (15, 5)) -> np.ndarray:
        """Aplica operador morfológico Black-Hat para resaltar caracteres oscuros sobre fondos claros."""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)
        blackhat = cv2.morphologyEx(gray_img, cv2.MORPH_BLACKHAT, kernel)
        # Combinar para aumentar contraste local de los trazos de letras
        enhanced = cv2.subtract(gray_img, blackhat)
        return enhanced

    def preprocess_plate(self, plate_img: np.ndarray, variant: str = None) -> np.ndarray:
        """Aplica el pipeline de preprocesamiento de OpenCV según la variante configurada."""
        if plate_img is None or plate_img.size == 0:
            return plate_img

        variant_name = variant or settings.OCR_PREPROCESS_VARIANT
        cfg = self.configs.get(variant_name, self.configs.get("default", {}))

        processed = plate_img.copy()

        # 1. Corrección de Inclinación (Deskewing) si está activado
        if cfg.get("deskew", True):
            processed = self.correct_skew(processed, max_angle=25.0)

        # 2. Resize proporcional cúbico para alcanzar la altura ideal para OCR (80-100px)
        h, w = processed.shape[:2]
        target_h = cfg.get("resize_target_height", 85)
        min_h = cfg.get("resize_min_height", 32)

        if h < min_h or h != target_h:
            scale = target_h / max(h, 1)
            new_w = max(int(w * scale), 20)
            processed = cv2.resize(processed, (new_w, target_h), interpolation=cv2.INTER_CUBIC)

        # 3. Escala de grises
        if cfg.get("grayscale", True) and len(processed.shape) == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

        # 4. Filtro Bilateral para reducir ruido del sensor sin desenfocar las letras
        if cfg.get("bilateral", True):
            d = cfg.get("bilateral_d", 7)
            sigma_color = cfg.get("bilateral_sigma_color", 50)
            sigma_space = cfg.get("bilateral_sigma_space", 50)
            processed = cv2.bilateralFilter(processed, d=d, sigmaColor=sigma_color, sigmaSpace=sigma_space)

        # 5. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        if cfg.get("clahe", True):
            clip = cfg.get("clahe_clip", 2.2)
            grid = tuple(cfg.get("clahe_grid", [8, 8]))
            clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=grid)
            if len(processed.shape) == 2:
                processed = clahe.apply(processed)
            else:
                lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                l = clahe.apply(l)
                processed = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

        # 6. Morfología Black-Hat opcional
        if cfg.get("blackhat", False):
            if len(processed.shape) == 2:
                k_size = tuple(cfg.get("blackhat_kernel", [15, 5]))
                processed = self.apply_blackhat(processed, kernel_size=k_size)

        # 7. Sharpening opcional
        if cfg.get("sharpening", False):
            factor = cfg.get("sharpening_factor", 0.6)
            kernel = np.array([[0, -1, 0], [-1, 4 + factor, -1], [0, -1, 0]], dtype=np.float32)
            processed = cv2.filter2D(processed, -1, kernel)

        # 8. Binarización opcional
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

        # 9. Padding blanco en los bordes para evitar corte de caracteres
        pad = cfg.get("border_padding", 8)
        if pad > 0:
            border_val = 255 if len(processed.shape) == 2 else [255, 255, 255]
            processed = cv2.copyMakeBorder(
                processed, pad, pad, pad + 4, pad + 4, cv2.BORDER_CONSTANT, value=border_val
            )

        return processed

    def preprocess_embossed_plate(self, plate_img: np.ndarray) -> np.ndarray:
        """Pipeline tonal suave para placas de bajo contraste o troqueladas.
        
        Preserva los tonos continuos en escala de grises (sin binarización ni Sobel)
        para no destruir la masa de caracteres requerida por EasyOCR/CRAFT:
        1. Deskewing
        2. Escalado cúbico a altura 95px
        3. Filtro bilateral suave para suprimir ruido sin borrar bordes
        4. CLAHE moderado (clipLimit=2.5) para realzar micro-sombras y volumen
        5. Unsharp Masking continuo (suave) para mejorar nitidez de transiciones
        6. Padding perimetral blanco neutral
        """
        if plate_img is None or plate_img.size == 0:
            return plate_img

        # 1. Corrección de inclinación previa
        processed = self.correct_skew(plate_img, max_angle=25.0)

        # 2. Escala de grises
        if len(processed.shape) == 3:
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        else:
            gray = processed.copy()

        # 3. Resize a 95px de altura
        h, w = gray.shape[:2]
        scale = 95.0 / max(h, 1)
        resized = cv2.resize(gray, (max(int(w * scale), 20), 95), interpolation=cv2.INTER_CUBIC)

        # 4. Bilateral suave para suprimir grano metálico sin difuminar transiciones
        bilat = cv2.bilateralFilter(resized, d=5, sigmaColor=35, sigmaSpace=35)

        # 5. CLAHE moderado para realzar sombras y contraste local sin saturación
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(bilat)

        # 6. Unsharp Masking continuo (suave)
        blurred = cv2.GaussianBlur(clahe, (0, 0), 1.5)
        sharpened = cv2.addWeighted(clahe, 1.35, blurred, -0.35, 0)

        # 7. Margen de seguridad blanco
        return cv2.copyMakeBorder(sharpened, 8, 8, 10, 10, cv2.BORDER_CONSTANT, value=255)

