#!/usr/bin/env python3
"""
test_pipeline.py — Script de prueba para validar el pipeline de inferencia completo:
Detección de micros -> Recorte -> Detección de placas -> Preprocesamiento -> EasyOCR -> Normalización -> SQLite

Uso:
    python scripts/test_pipeline.py
    python scripts/test_pipeline.py --image datasets/micros/images/test/2026-10-01_23-13.png
"""

import sys
import argparse
from pathlib import Path

# Agregar raíz al PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.services.pipeline_service import PipelineService
from backend.app.db.session import init_db, SessionLocal
from backend.app.db.models import DetectionEvent


def main():
    parser = argparse.ArgumentParser(description="Prueba del Pipeline Completo de Detección y OCR.")
    parser.add_argument(
        "--image",
        type=str,
        default=str(ROOT / "datasets" / "micros" / "images" / "test" / "2026-10-01_23-13.png"),
        help="Ruta a una imagen de prueba",
    )
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        # Fallback a la primera imagen encontrada en test
        test_images = list((ROOT / "datasets" / "micros" / "images" / "test").glob("*.png"))
        if test_images:
            img_path = test_images[0]
        else:
            print(f"[ERROR] No se encontró la imagen: {img_path}")
            sys.exit(1)

    print(f"\n{'='*65}")
    print(f"  PRUEBA DEL PIPELINE COMPLETO (YOLO26 + EasyOCR + SQLite)")
    print(f"{'='*65}")
    print(f"  Imagen de prueba: {img_path.name}")

    # 1. Asegurar base de datos
    init_db()

    # 2. Inicializar servicio de pipeline
    pipeline = PipelineService()

    # 3. Leer bytes de la imagen
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    # 4. Procesar
    print("\n  Ejecutando inferencia en cascada...")
    result = pipeline.process_image(img_bytes, filename=img_path.name)

    print(f"\n  Resultados:")
    print(f"    - Micros detectados: {result['total_micros_detected']}")
    print(f"    - Placas detectadas: {result['total_plates_detected']}")
    print(f"    - Nuevos registros en BD: {result['new_records_saved']}")

    for i, m in enumerate(result["detections"], 1):
        print(f"\n    [Micro #{i}] Confianza: {m['micro_confidence']*100:.1f}% | BBox: {m['micro_bbox']}")
        if not m["plates"]:
            print("      (Sin placa detectada dentro de este micro)")
        for j, p in enumerate(m["plates"], 1):
            print(f"      └── [Placa #{j}]")
            print(f"            - Conf. Detector:  {p['plate_confidence']*100:.1f}%")
            print(f"            - Texto OCR Bruto: '{p['plate_raw']}'")
            print(f"            - Patente Normalizada: '{p['plate_normalized']}'")
            print(f"            - Válida Boliviana: {'SÍ' if p['is_valid_bolivian'] else 'NO'}")
            print(f"            - Conf. OCR:       {p['ocr_confidence']*100:.1f}%")
            print(f"            - ¿Es Duplicado?:  {'SÍ' if p['is_duplicate'] else 'NO'}")
            if p.get("evidence_plate_url"):
                print(f"            - Evidencia:       {p['evidence_plate_url']}")

    # 5. Consultar último registro en BD
    db = SessionLocal()
    last_event = db.query(DetectionEvent).order_by(DetectionEvent.id.desc()).first()
    if last_event:
        print(f"\n  Último registro en SQLite:")
        print(f"    ID: {last_event.id} | Placa: {last_event.plate_normalized} | Fecha: {last_event.timestamp}")
    db.close()

    print(f"\n{'='*65}")
    print(f"  PRUEBA FINALIZADA CON ÉXITO")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
