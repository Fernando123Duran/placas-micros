import logging
from typing import Dict, List, Any, Optional
import numpy as np
from collections import defaultdict
from dataclasses import dataclass

from backend.app.config.settings import settings
from backend.app.core.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


@dataclass
class PlateCandidate:
    frame_idx: int
    timestamp_sec: float
    plate_crop: np.ndarray
    plate_bbox_full: List[int]
    micro_crop: np.ndarray
    micro_bbox: List[int]
    micro_confidence: float
    plate_confidence: float
    sharpness: float
    area: int
    quality_score: float


class TrackCandidateSelector:
    """Acumula y selecciona los mejores candidatos de placa por cada micro trackeado (track_id)."""

    def __init__(self, max_candidates: int = None):
        self.max_candidates = max_candidates or settings.OCR_CANDIDATES_PER_TRACK
        # track_id -> List[PlateCandidate]
        self.tracks: Dict[int, List[PlateCandidate]] = defaultdict(list)
        # track_id -> total frames seen
        self.track_frames_seen: Dict[int, int] = defaultdict(int)
        # track_ids ya procesados/guardados
        self.finalized_tracks: set = set()

    def add_candidate(
        self,
        track_id: int,
        frame_idx: int,
        timestamp_sec: float,
        micro_bbox: List[int],
        micro_crop: np.ndarray,
        micro_confidence: float,
        plate_bbox_full: List[int],
        plate_crop: np.ndarray,
        plate_confidence: float,
        sharpness: float,
    ):
        """Agrega un candidato de placa para un determinado track_id."""
        self.track_frames_seen[track_id] += 1

        h, w = plate_crop.shape[:2]
        area = w * h

        # Score heurístico ponderado:
        # - Confianza del detector de placas (peso principal)
        # - Nitidez (evita desenfoque de movimiento)
        # - Tamaño (favorece tomas cercanas vs lejanas)
        sharpness_norm = min(max(sharpness, 0.0) / 250.0, 1.0)
        area_norm = min(area / 8000.0, 1.0)
        quality_score = float(plate_confidence * 0.5 + sharpness_norm * 0.3 + area_norm * 0.2)

        cand = PlateCandidate(
            frame_idx=frame_idx,
            timestamp_sec=timestamp_sec,
            plate_crop=plate_crop,
            plate_bbox_full=plate_bbox_full,
            micro_crop=micro_crop,
            micro_bbox=micro_bbox,
            micro_confidence=micro_confidence,
            plate_confidence=plate_confidence,
            sharpness=sharpness,
            area=area,
            quality_score=quality_score,
        )

        self.tracks[track_id].append(cand)

        # Mantener solo los N mejores candidatos ordenados por quality_score
        self.tracks[track_id].sort(key=lambda c: c.quality_score, reverse=True)
        if len(self.tracks[track_id]) > self.max_candidates * 2:
            self.tracks[track_id] = self.tracks[track_id][: self.max_candidates * 2]

    def get_best_candidates(self, track_id: int) -> List[PlateCandidate]:
        """Retorna los top N candidatos para un track."""
        cands = self.tracks.get(track_id, [])
        return cands[: self.max_candidates]

    def is_finalized(self, track_id: int) -> bool:
        return track_id in self.finalized_tracks

    def mark_finalized(self, track_id: int):
        self.finalized_tracks.add(track_id)
