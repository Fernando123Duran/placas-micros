from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PlateInfo(BaseModel):
    plate_raw: str
    plate_normalized: str
    is_valid_bolivian: bool
    plate_confidence: float
    ocr_confidence: float
    plate_bbox_full: List[int]
    is_duplicate: bool = False
    saved_to_db: bool = False
    evidence_plate_url: Optional[str] = None


class MicroDetectionResult(BaseModel):
    micro_confidence: float
    micro_bbox: List[int]
    evidence_micro_url: Optional[str] = None
    plates: List[PlateInfo] = []


class ImageProcessResponse(BaseModel):
    success: bool
    source_filename: str
    total_micros_detected: int
    total_plates_detected: int
    new_records_saved: int
    detections: List[MicroDetectionResult]
    evidence_full_url: Optional[str] = None


class DetectionEventItem(BaseModel):
    id: int
    timestamp: datetime
    source: str
    track_id: Optional[int] = None
    plate_raw: Optional[str] = None
    plate_normalized: str
    is_valid_bolivian: bool
    micro_confidence: float
    plate_confidence: float
    ocr_confidence: float
    micro_bbox: str
    plate_bbox: str
    full_image_url: Optional[str] = None
    micro_image_url: Optional[str] = None
    plate_image_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DetectionListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[DetectionEventItem]


class VideoProcessResponse(BaseModel):
    success: bool
    video_filename: str
    total_frames_processed: int
    duration_seconds: float
    unique_tracks_detected: int
    plates_registered: int
    items: List[DetectionEventItem]
