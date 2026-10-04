import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DetectionEvent(Base):
    __tablename__ = "detection_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    source = Column(String(50), default="image", nullable=False)
    track_id = Column(Integer, nullable=True, index=True)

    # Placa y OCR
    plate_raw = Column(String(50), nullable=True)
    plate_normalized = Column(String(20), nullable=False, index=True)
    is_valid_bolivian = Column(Boolean, default=False, nullable=False)

    # Confianzas
    micro_confidence = Column(Float, nullable=False)
    plate_confidence = Column(Float, nullable=False)
    ocr_confidence = Column(Float, nullable=False)

    # Coordenadas (JSON string [x1, y1, x2, y2])
    micro_bbox = Column(String(100), nullable=False)
    plate_bbox = Column(String(100), nullable=False)

    # Rutas a archivos de evidencias guardadas
    full_image_path = Column(String(255), nullable=True)
    micro_image_path = Column(String(255), nullable=True)
    plate_image_path = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_plate_timestamp", "plate_normalized", "timestamp"),
    )
