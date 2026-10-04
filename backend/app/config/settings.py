from pathlib import Path
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# Directorio raíz del proyecto (padre de backend)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"


class Settings(BaseSettings):
    # Modelos YOLO
    MODEL_MICRO_PATH: str = str(ROOT_DIR / "models" / "micro_detector_v1.pt")
    MODEL_PLATE_PATH: str = str(ROOT_DIR / "models" / "plate_detector_v1.pt")

    # Hardware
    USE_GPU: bool = True
    DEVICE: str = "0"

    # Confianzas mínimas
    MIN_MICRO_CONFIDENCE: float = 0.40
    MIN_PLATE_CONFIDENCE: float = 0.35
    MIN_OCR_CONFIDENCE: float = 0.45

    # Padding para recortar el micro (porcentaje del bbox)
    MICRO_CROP_PADDING: float = 0.05

    # Deduplicación y anti-ráfagas
    DEDUP_WINDOW_MINUTES: int = 5

    # Base de datos
    DB_PATH: str = str(BACKEND_DIR / "db" / "placas_micros.db")

    # Evidencias / Storage
    STORAGE_PATH: str = str(BACKEND_DIR / "storage")

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False

    # OCR
    OCR_LANGUAGES: Union[str, List[str]] = ["es"]
    OCR_PREPROCESS_VARIANT: str = "default"
    EASYOCR_MODEL_DIR: str = str(ROOT_DIR / "models" / "easyocr")

    # Tracking
    TRACKER_CONFIG: str = str(ROOT_DIR / "configs" / "bytetrack_micros.yaml")
    TRACK_BUFFER_FRAMES: int = 45

    # Video
    VIDEO_SAMPLE_FPS: float = 5.0
    OCR_CANDIDATES_PER_TRACK: int = 3

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("OCR_LANGUAGES", mode="before")
    @classmethod
    def parse_ocr_languages(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Asegurar directorios requeridos
Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
(Path(settings.STORAGE_PATH) / "full").mkdir(parents=True, exist_ok=True)
(Path(settings.STORAGE_PATH) / "micros").mkdir(parents=True, exist_ok=True)
(Path(settings.STORAGE_PATH) / "plates").mkdir(parents=True, exist_ok=True)
Path(settings.EASYOCR_MODEL_DIR).mkdir(parents=True, exist_ok=True)
