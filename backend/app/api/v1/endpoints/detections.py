from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func
import datetime

from backend.app.db.session import get_db
from backend.app.db.models import DetectionEvent
from backend.app.schemas.detection import (
    ImageProcessResponse,
    DetectionListResponse,
    DetectionEventItem,
    VideoProcessResponse,
)
from backend.app.services.pipeline_service import PipelineService
from backend.app.config.settings import settings

router = APIRouter(prefix="/detections", tags=["Detecciones y Placas"])

pipeline_service = PipelineService()


@router.post("/image", response_model=ImageProcessResponse)
async def detect_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Sube una imagen completa, detecta micros, localiza placas, lee con EasyOCR y persiste en BD."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser una imagen válida (JPEG, PNG, etc.)",
        )

    content = await file.read()
    result = pipeline_service.process_image(
        image_bytes=content,
        filename=file.filename or "upload.jpg",
        db=db,
    )
    return result


@router.get("/events", response_model=DetectionListResponse)
def list_events(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(20, ge=1, le=100, description="Registros por página"),
    plate: Optional[str] = Query(None, description="Filtrar por coincidencia en patente"),
    only_valid_bolivian: Optional[bool] = Query(None, description="Filtrar solo placas bolivianas válidas"),
    db: Session = Depends(get_db),
):
    """Lista el historial de eventos de detección con paginación y filtros."""
    query = select(DetectionEvent)

    if plate:
        query = query.where(DetectionEvent.plate_normalized.ilike(f"%{plate.strip().upper()}%"))

    if only_valid_bolivian is not None:
        query = query.where(DetectionEvent.is_valid_bolivian == only_valid_bolivian)

    # Conteo total
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    # Paginación y orden cronológico descendente
    offset = (page - 1) * limit
    items = db.execute(
        query.order_by(desc(DetectionEvent.timestamp)).offset(offset).limit(limit)
    ).scalars().all()

    # Formatear URLs de imágenes
    event_items = []
    for item in items:
        event_dict = {
            "id": item.id,
            "timestamp": item.timestamp,
            "source": item.source,
            "track_id": item.track_id,
            "plate_raw": item.plate_raw,
            "plate_normalized": item.plate_normalized,
            "is_valid_bolivian": item.is_valid_bolivian,
            "micro_confidence": item.micro_confidence,
            "plate_confidence": item.plate_confidence,
            "ocr_confidence": item.ocr_confidence,
            "micro_bbox": item.micro_bbox,
            "plate_bbox": item.plate_bbox,
            "full_image_url": f"/storage/{item.full_image_path}" if item.full_image_path else None,
            "micro_image_url": f"/storage/{item.micro_image_path}" if item.micro_image_path else None,
            "plate_image_url": f"/storage/{item.plate_image_path}" if item.plate_image_path else None,
            "created_at": item.created_at,
        }
        event_items.append(DetectionEventItem(**event_dict))

    return DetectionListResponse(
        total=total,
        page=page,
        limit=limit,
        items=event_items,
    )


@router.get("/events/{event_id}", response_model=DetectionEventItem)
def get_event(event_id: int, db: Session = Depends(get_db)):
    """Obtiene los detalles completos de un evento específico por ID."""
    event = db.get(DetectionEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento de detección no encontrado")

    return DetectionEventItem(
        id=event.id,
        timestamp=event.timestamp,
        source=event.source,
        track_id=event.track_id,
        plate_raw=event.plate_raw,
        plate_normalized=event.plate_normalized,
        is_valid_bolivian=event.is_valid_bolivian,
        micro_confidence=event.micro_confidence,
        plate_confidence=event.plate_confidence,
        ocr_confidence=event.ocr_confidence,
        micro_bbox=event.micro_bbox,
        plate_bbox=event.plate_bbox,
        full_image_url=f"/storage/{event.full_image_path}" if event.full_image_path else None,
        micro_image_url=f"/storage/{event.micro_image_path}" if event.micro_image_path else None,
        plate_image_url=f"/storage/{event.plate_image_path}" if event.plate_image_path else None,
        created_at=event.created_at,
    )


@router.get("/stats")
def get_statistics(db: Session = Depends(get_db)):
    """Obtiene métricas y estadísticas consolidadas del sistema."""
    total_detections = db.scalar(select(func.count(DetectionEvent.id))) or 0
    valid_bolivian = db.scalar(
        select(func.count(DetectionEvent.id)).where(DetectionEvent.is_valid_bolivian == True)
    ) or 0
    unique_plates = db.scalar(
        select(func.count(func.distinct(DetectionEvent.plate_normalized)))
    ) or 0

    avg_micro_conf = db.scalar(select(func.avg(DetectionEvent.micro_confidence))) or 0.0
    avg_plate_conf = db.scalar(select(func.avg(DetectionEvent.plate_confidence))) or 0.0
    avg_ocr_conf = db.scalar(select(func.avg(DetectionEvent.ocr_confidence))) or 0.0

    today = datetime.datetime.utcnow().date()
    today_start = datetime.datetime.combine(today, datetime.time.min)
    detections_today = db.scalar(
        select(func.count(DetectionEvent.id)).where(DetectionEvent.timestamp >= today_start)
    ) or 0

    return {
        "total_detections": total_detections,
        "detections_today": detections_today,
        "unique_plates_count": unique_plates,
        "valid_bolivian_plates_count": valid_bolivian,
        "average_confidence": {
            "micro": round(float(avg_micro_conf), 3),
            "plate": round(float(avg_plate_conf), 3),
            "ocr": round(float(avg_ocr_conf), 3),
        }
    }
