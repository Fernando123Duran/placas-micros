import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.app.config.settings import settings
from backend.app.db.session import init_db
from backend.app.api.v1.endpoints import detections

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("placas_micros")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando servicio de Detección de Placas de Micros...")
    # 1. Inicializar base de datos
    init_db()
    logger.info(f"Base de datos lista en: {settings.DB_PATH}")
    # 2. Asegurar directorios de almacenamiento
    Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Cerrando servicio...")


app = FastAPI(
    title="Sistema de Detección de Placas de Micros",
    description="API de visión artificial para detección en cascada de micros, placas vehiculares y OCR con EasyOCR.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir evidencias fotográficas guardadas
app.mount("/storage", StaticFiles(directory=settings.STORAGE_PATH), name="storage")

# Router API v1
app.include_router(detections.router, prefix="/api/v1")


@app.get("/health", tags=["Salud"])
def health_check():
    return {
        "status": "healthy",
        "gpu_available": settings.USE_GPU,
        "models": {
            "micro_detector": Path(settings.MODEL_MICRO_PATH).exists(),
            "plate_detector": Path(settings.MODEL_PLATE_PATH).exists(),
            "easyocr": Path(settings.EASYOCR_MODEL_DIR).exists(),
        },
        "database": Path(settings.DB_PATH).exists(),
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "title": "API de Detección de Placas de Micros (YOLO26 + OCR)",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "detect_image": "POST /api/v1/detections/image",
            "list_events": "GET /api/v1/detections/events",
            "get_stats": "GET /api/v1/detections/stats",
            "health": "GET /health",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
