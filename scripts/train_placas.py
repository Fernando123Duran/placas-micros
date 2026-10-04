#!/usr/bin/env python3
"""
train_placas.py — Entrenamiento del Detector de Placas (Modelo 2)

Opera sobre crops del ROI del micro (no sobre imagen completa).
Usa arquitectura YOLO26-P2 para mejor detección de objetos pequeños.

Uso:
    python scripts/train_placas.py
    python scripts/train_placas.py --name exp_m2_yolo26s-p2_640_b16 --model yolo26s-p2.pt
    python scripts/train_placas.py --batch 16 --name exp_m2_yolo26n-p2_640_b16
    python scripts/train_placas.py --resume runs/placas/exp_m2_yolo26n-p2_640_b32/weights/last.pt

Los hiperparámetros base están en configs/train_placas.yaml.
Los argumentos de línea de comandos sobreescriben los valores del YAML.
Todos los experimentos se guardan en runs/placas/<name>/.
"""

import argparse
import sys
from pathlib import Path

import yaml

# ── Rutas base ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "configs" / "train_placas.yaml"


def load_config(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Entrenamiento del Detector de Placas (YOLO26-P2).",
    )
    parser.add_argument("--model", type=str, default="yolo26n-p2.pt",
                        help="Modelo base preentrenado con P2 (defecto: yolo26n-p2.pt)")
    parser.add_argument("--data", type=str, default=str(ROOT / "configs" / "data_placas.yaml"),
                        help="Ruta al dataset data.yaml (defecto: configs/data_placas.yaml)")
    parser.add_argument("--epochs", type=int, default=150,
                        help="Número total de épocas de entrenamiento (defecto: 150)")
    parser.add_argument("--patience", type=int, default=30,
                        help="Paciencia para early stopping (defecto: 30)")
    parser.add_argument("--batch", type=int, default=32,
                        help="Tamaño del lote/batch size (defecto: 32)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Tamaño de imagen de entrada (defecto: 640)")
    parser.add_argument("--device", type=str, default="0",
                        help="Dispositivo para entrenamiento: '0' para GPU, 'cpu' para CPU (defecto: 0)")
    parser.add_argument("--workers", type=int, default=8,
                        help="Número de hilos/workers para DataLoader (defecto: 8)")
    parser.add_argument("--project", type=str, default=str(ROOT / "runs" / "placas"),
                        help="Directorio de destino de los experimentos (defecto: runs/placas)")
    parser.add_argument("--name", type=str, default="exp_m2_yolo26n-p2_640_b32",
                        help="Nombre del experimento/carpeta (defecto: exp_m2_yolo26n-p2_640_b32)")
    parser.add_argument("--resume", type=str, default=None,
                        help="Ruta a checkpoint last.pt para reanudar entrenamiento (defecto: None)")
    parser.add_argument("--config", type=str, default=str(CONFIG_PATH),
                        help="Ruta al YAML de hiperparámetros base (defecto: configs/train_placas.yaml)")
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Cargar config base desde YAML ─────────────────────────────────────────
    config_path = Path(args.config)
    cfg = {}
    if config_path.exists():
        cfg = load_config(config_path)
        print(f"\n{'='*60}")
        print(f"  Entrenamiento — Detector de Placas (Modelo 2)")
        print(f"{'='*60}")
        print(f"  Config base: {config_path}")
    else:
        print(f"\n[AVISO] No se encontró YAML base ({config_path}), usando defaults del script.")

    # ── Sobrescribir con los valores definidos en los argumentos / defaults ────
    cfg["model"] = args.model
    cfg["data"] = args.data
    cfg["epochs"] = args.epochs
    cfg["patience"] = args.patience
    cfg["batch"] = args.batch
    cfg["imgsz"] = args.imgsz
    cfg["device"] = args.device
    cfg["workers"] = args.workers
    cfg["project"] = str(Path(args.project).resolve())
    cfg["name"] = args.name

    print(f"\n  Configuración activa:")
    for k, v in cfg.items():
        if not k.startswith("#"):
            print(f"    {k}: {v}")

    try:
        from ultralytics import YOLO
    except ImportError:
        print("\n[ERROR] ultralytics no está instalado. Activa el .venv:")
        print("  source /home/luffy/Documentos/IA/tienda-deteccion/.venv/bin/activate")
        sys.exit(1)

    model_name = cfg.pop("model")

    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.exists():
            print(f"[ERROR] No se encontró el checkpoint: {resume_path}")
            sys.exit(1)
        print(f"\n  Reanudando desde: {resume_path}")
        model = YOLO(str(resume_path))
        cfg["resume"] = True
    else:
        print(f"\n  Modelo base: {model_name}")
        model = YOLO(model_name)

    cfg.setdefault("project", str(ROOT / "runs" / "placas"))
    cfg.setdefault("name", "exp_m2")

    data_path = Path(cfg.get("data", "configs/data_placas.yaml"))
    if not data_path.is_absolute():
        data_path = ROOT / data_path
    cfg["data"] = str(data_path)

    print(f"\n  Iniciando entrenamiento...")
    print(f"  Resultados en: {cfg['project']}/{cfg['name']}/\n")

    results = model.train(**cfg)

    print(f"\n{'='*60}")
    print(f"  Entrenamiento completado")
    print(f"  Mejor modelo: {cfg['project']}/{cfg['name']}/weights/best.pt")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
