#!/usr/bin/env python3
"""
train_micros.py — Entrenamiento del Detector de Micros (Modelo 1)

Uso:
    python scripts/train_micros.py
    python scripts/train_micros.py --name exp_m1_yolo26s_960_b8 --imgsz 960 --batch 8
    python scripts/train_micros.py --model yolo26m.pt --name exp_m1_yolo26m_640_b16
    python scripts/train_micros.py --resume runs/micros/exp_m1_yolo26s_640_b16/weights/last.pt

Los hiperparámetros base están en configs/train_micros.yaml.
Los argumentos de línea de comandos sobreescriben los valores del YAML.
Todos los experimentos se guardan en runs/micros/<name>/.
"""

import argparse
import sys
from pathlib import Path

import yaml

# ── Rutas base ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "configs" / "train_micros.yaml"


def load_config(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Entrenamiento del Detector de Micros (YOLO26).",
    )
    parser.add_argument("--model", type=str, default="yolo26s.pt",
                        help="Modelo base preentrenado (defecto: yolo26s.pt)")
    parser.add_argument("--data", type=str, default=str(ROOT / "configs" / "data_micros.yaml"),
                        help="Ruta al dataset data.yaml (defecto: configs/data_micros.yaml)")
    parser.add_argument("--epochs", type=int, default=150,
                        help="Número total de épocas de entrenamiento (defecto: 150)")
    parser.add_argument("--patience", type=int, default=30,
                        help="Paciencia para early stopping (defecto: 30)")
    parser.add_argument("--batch", type=int, default=16,
                        help="Tamaño del lote/batch size (defecto: 16)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Tamaño de imagen de entrada (defecto: 640)")
    parser.add_argument("--device", type=str, default="0",
                        help="Dispositivo para entrenamiento: '0' para GPU, 'cpu' para CPU (defecto: 0)")
    parser.add_argument("--workers", type=int, default=8,
                        help="Número de hilos/workers para DataLoader (defecto: 8)")
    parser.add_argument("--project", type=str, default=str(ROOT / "runs" / "micros"),
                        help="Directorio de destino de los experimentos (defecto: runs/micros)")
    parser.add_argument("--name", type=str, default="exp_m1_yolo26s_640_b16",
                        help="Nombre del experimento/carpeta (defecto: exp_m1_yolo26s_640_b16)")
    parser.add_argument("--resume", type=str, default=None,
                        help="Ruta a checkpoint last.pt para reanudar entrenamiento (defecto: None)")
    parser.add_argument("--config", type=str, default=str(CONFIG_PATH),
                        help="Ruta al YAML de hiperparámetros base (defecto: configs/train_micros.yaml)")
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Cargar config base desde YAML ─────────────────────────────────────────
    config_path = Path(args.config)
    cfg = {}
    if config_path.exists():
        cfg = load_config(config_path)
        print(f"\n{'='*60}")
        print(f"  Entrenamiento — Detector de Micros (Modelo 1)")
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

    # ── Mostrar configuración activa ──────────────────────────────────────────
    print(f"\n  Configuración activa:")
    for k, v in cfg.items():
        if not k.startswith("#"):
            print(f"    {k}: {v}")

    # ── Importar y ejecutar ───────────────────────────────────────────────────
    try:
        from ultralytics import YOLO
        from ultralytics.cfg import DEFAULT_CFG_DICT
    except ImportError:
        print("\n[ERROR] ultralytics no está instalado. Activa el .venv:")
        print("  source /home/luffy/Documentos/IA/tienda-deteccion/.venv/bin/activate")
        sys.exit(1)

    # Extraer el modelo base (puede ser nombre o ruta)
    model_name = cfg.pop("model")

    # Si se pasa --resume, ignorar model_name y usar last.pt
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
        if model_name.endswith(".yaml"):
            print(f"  Arquitectura YAML detectada ({model_name}), transfiriendo pesos preentrenados...")
            model = YOLO(model_name).load("yolo26s.pt")
        else:
            model = YOLO(model_name)

    # Asegurar que el proyecto apunta a runs/micros/
    cfg.setdefault("project", str(ROOT / "runs" / "micros"))
    cfg.setdefault("name", "exp_m1")

    # Convertir data a ruta absoluta si es relativa
    data_path = Path(cfg.get("data", "configs/data_micros.yaml"))
    if not data_path.is_absolute():
        data_path = ROOT / data_path
    cfg["data"] = str(data_path)

    # Filtrar únicamente los parámetros reconocidos por Ultralytics
    filtered_cfg = {}
    for k, v in cfg.items():
        if k in DEFAULT_CFG_DICT:
            filtered_cfg[k] = v
        else:
            print(f"  [AVISO] Parámetro no reconocido por YOLO ignorado: {k}={v}")

    print(f"\n  Iniciando entrenamiento...")
    print(f"  Resultados en: {filtered_cfg.get('project', cfg.get('project'))}/{filtered_cfg.get('name', cfg.get('name'))}/\n")

    # ── Entrenamiento ──────────────────────────────────────────────────────────
    results = model.train(**filtered_cfg)

    print(f"\n{'='*60}")
    print(f"  Entrenamiento completado")
    print(f"  Mejor modelo: {cfg['project']}/{cfg['name']}/weights/best.pt")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
