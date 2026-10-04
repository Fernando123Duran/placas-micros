import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import sessionmaker, Session

from backend.app.config.settings import settings
from backend.app.db.models import Base, DetectionEvent

db_url = f"sqlite:///{settings.DB_PATH}"

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Crea las tablas en la base de datos si no existen."""
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    """Generador de sesión para inyección de dependencias en FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_duplicate_plate(
    db: Session,
    plate_normalized: str,
    window_minutes: int = None,
) -> bool:
    """Verifica si una patente normalizada ya fue registrada en los últimos N minutos."""
    if not plate_normalized:
        return False

    mins = window_minutes if window_minutes is not None else settings.DEDUP_WINDOW_MINUTES
    cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=mins)

    stmt = (
        select(DetectionEvent)
        .where(
            DetectionEvent.plate_normalized == plate_normalized,
            DetectionEvent.timestamp >= cutoff_time,
        )
        .limit(1)
    )
    result = db.execute(stmt).scalars().first()
    return result is not None
