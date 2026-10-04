import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from ultralytics import YOLO

from backend.app.config.settings import settings
from backend.app.core.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class CascadeDetector:
    """Detector en cascada de dos etapas:
    Etapa 1: Detector de Micros (Full Frame)
    Etapa 2: Detector de Placas (Crop/ROI del Micro)
    """

    _instance: Optional["CascadeDetector"] = None

    def __init__(
        self,
        micro_model_path: str = None,
        plate_model_path: str = None,
        device: str = None,
    ):
        self.device = device or (settings.DEVICE if settings.USE_GPU else "cpu")
        self.micro_model_path = micro_model_path or settings.MODEL_MICRO_PATH
        self.plate_model_path = plate_model_path or settings.MODEL_PLATE_PATH

        logger.info(f"Cargando Modelo de Micros desde {self.micro_model_path} en {self.device}...")
        self.micro_model = YOLO(self.micro_model_path)

        logger.info(f"Cargando Modelo de Placas desde {self.plate_model_path} en {self.device}...")
        self.plate_model = YOLO(self.plate_model_path)

        self.preprocessor = ImagePreprocessor()

    @classmethod
    def get_instance(cls) -> "CascadeDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def extract_crop_with_padding(
        self, image: np.ndarray, bbox: List[int], padding_ratio: float = 0.05
    ) -> Tuple[np.ndarray, List[int]]:
        """Recorta un bounding box con margen (padding) asegurando no salirse de los bordes."""
        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox

        bw = x2 - x1
        bh = y2 - y1

        pad_w = int(bw * padding_ratio)
        pad_h = int(bh * padding_ratio)

        cx1 = max(0, x1 - pad_w)
        cy1 = max(0, y1 - pad_h)
        cx2 = min(w, x2 + pad_w)
        cy2 = min(h, y2 + pad_h)

        crop = image[cy1:cy2, cx1:cx2].copy()
        return crop, [cx1, cy1, cx2, cy2]

    def detect_in_image(
        self,
        image: np.ndarray,
        min_micro_conf: float = None,
        min_plate_conf: float = None,
    ) -> List[Dict[str, Any]]:
        """Ejecuta la cascada completa sobre una sola imagen (BGR numpy array).
        
        Returns:
            Lista de detecciones de micros con sus respectivas placas detectadas.
        """
        if image is None or image.size == 0:
            return []

        micro_conf_thresh = min_micro_conf or settings.MIN_MICRO_CONFIDENCE
        plate_conf_thresh = min_plate_conf or settings.MIN_PLATE_CONFIDENCE

        # 1. Inferencia del detector de micros (Etapa 1)
        micro_results = self.micro_model(
            image,
            conf=micro_conf_thresh,
            device=self.device,
            verbose=False,
        )[0]

        detections = []

        if micro_results.boxes is None or len(micro_results.boxes) == 0:
            return detections

        # 2. Iterar sobre cada micro detectado
        for box in micro_results.boxes:
            m_conf = float(box.conf[0])
            mx1, my1, mx2, my2 = [int(v) for v in box.xyxy[0]]

            # Recortar ROI del micro con padding
            micro_crop, crop_bbox = self.extract_crop_with_padding(
                image, [mx1, my1, mx2, my2], padding_ratio=settings.MICRO_CROP_PADDING
            )

            if micro_crop.size == 0:
                continue

            cx1, cy1, _, _ = crop_bbox

            # 3. Inferencia del detector de placas sobre el crop (Etapa 2)
            plate_results = self.plate_model(
                micro_crop,
                conf=plate_conf_thresh,
                device=self.device,
                verbose=False,
            )[0]

            detected_plates = []

            if plate_results.boxes is not None and len(plate_results.boxes) > 0:
                for p_box in plate_results.boxes:
                    p_conf = float(p_box.conf[0])
                    px1, py1, px2, py2 = [int(v) for v in p_box.xyxy[0]]

                    # Coordenadas globales en la imagen completa
                    gx1 = cx1 + px1
                    gy1 = cy1 + py1
                    gx2 = cx1 + px2
                    gy2 = cy1 + py2

                    # Recorte de la placa
                    plate_crop = micro_crop[py1:py2, px1:px2].copy()
                    if plate_crop.size == 0:
                        continue

                    sharpness = self.preprocessor.calculate_sharpness(plate_crop)
                    area = (px2 - px1) * (py2 - py1)

                    detected_plates.append({
                        "plate_bbox_crop": [px1, py1, px2, py2],
                        "plate_bbox_full": [gx1, gy1, gx2, gy2],
                        "plate_confidence": round(p_conf, 4),
                        "plate_crop": plate_crop,
                        "sharpness": round(sharpness, 2),
                        "area": area,
                    })

            # Ordenar placas detectadas por mayor confianza
            detected_plates.sort(key=lambda x: x["plate_confidence"], reverse=True)

            detections.append({
                "micro_bbox": [mx1, my1, mx2, my2],
                "micro_crop_bbox": crop_bbox,
                "micro_confidence": round(m_conf, 4),
                "micro_crop": micro_crop,
                "plates": detected_plates,
            })

        return detections
