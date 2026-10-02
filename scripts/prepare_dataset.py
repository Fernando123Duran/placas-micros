#!/usr/bin/env python3
"""
prepare_dataset.py — Split y preparación de datasets YOLO para micros y placas.

Flujo:
  1. Lee las anotaciones exportadas de Label Studio (formato YOLO)
  2. Agrupa imágenes por sesión temporal (YYYY-MM-DD_HH-MM)
  3. Split por sesión (no por imagen individual) → evita data leakage
  4. Copia imágenes y labels a datasets/micros/ y datasets/placas/
  5. Para el dataset de placas: genera crops del ROI del micro y reescala labels

Uso:
    python scripts/prepare_dataset.py
    python scripts/prepare_dataset.py --train 0.70 --val 0.15 --test 0.15 --seed 42

Prerequisitos:
  - Anotaciones en: data/annotations/validated/
  - Imágenes en: dataset/
  - Clases en Label Studio: 0=micro, 1=placa
"""

import argparse
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("[ERROR] Pillow no está instalado.")
    sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
SUPPORTED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
CLASS_MICRO = 0
CLASS_PLACA = 1

# Padding para el crop del micro (% extra del bbox)
MICRO_CROP_PADDING = 0.05


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def parse_session_key(filename: str) -> str:
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return stem


def read_yolo_labels(label_path: Path) -> list[tuple[int, float, float, float, float]]:
    """Lee un archivo YOLO y retorna lista de (class_id, cx, cy, w, h)."""
    if not label_path.exists():
        return []
    labels = []
    for line in label_path.read_text().strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 5:
            labels.append((int(parts[0]), float(parts[1]), float(parts[2]),
                           float(parts[3]), float(parts[4])))
    return labels


def yolo_to_abs(cx, cy, bw, bh, img_w, img_h):
    """Convierte coordenadas YOLO normalizadas a píxeles absolutos."""
    x1 = int((cx - bw / 2) * img_w)
    y1 = int((cy - bh / 2) * img_h)
    x2 = int((cx + bw / 2) * img_w)
    y2 = int((cy + bh / 2) * img_h)
    return x1, y1, x2, y2


def abs_to_yolo(x1, y1, x2, y2, img_w, img_h):
    """Convierte píxeles absolutos a coordenadas YOLO normalizadas."""
    cx = ((x1 + x2) / 2) / img_w
    cy = ((y1 + y2) / 2) / img_h
    bw = (x2 - x1) / img_w
    bh = (y2 - y1) / img_h
    return cx, cy, bw, bh


def clip(val, lo=0.0, hi=1.0):
    return max(lo, min(hi, val))


# ──────────────────────────────────────────────────────────────────────────────
# Split por sesión
# ──────────────────────────────────────────────────────────────────────────────
def split_sessions(
    image_files: list[Path],
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> tuple[list[Path], list[Path], list[Path]]:
    """
    Agrupa imágenes por sesión temporal y asigna grupos completos a splits.
    Las sesiones de la última fecha van a test (datos más recientes = más realistas).
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        "Los ratios deben sumar 1.0"

    # Agrupar por sesión
    session_map: dict[str, list[Path]] = defaultdict(list)
    for f in image_files:
        key = parse_session_key(f.name)
        session_map[key].append(f)

    sessions = sorted(session_map.keys())

    # Determinar la última fecha
    last_date = max(s.split("_")[0] for s in sessions)
    test_sessions  = [s for s in sessions if s.split("_")[0] == last_date]
    other_sessions = [s for s in sessions if s.split("_")[0] != last_date]

    # Mezclar las sesiones no-test
    rng = random.Random(seed)
    rng.shuffle(other_sessions)

    # Calcular split ajustado (test ya está fijo = última fecha)
    n_other = len(other_sessions)
    test_imgs_count  = sum(len(session_map[s]) for s in test_sessions)
    total_imgs       = len(image_files)
    remaining_ratio  = 1.0 - (test_imgs_count / total_imgs)

    adjusted_val = val_ratio / (train_ratio + val_ratio)
    n_val = max(1, int(n_other * adjusted_val))
    val_sessions   = other_sessions[:n_val]
    train_sessions = other_sessions[n_val:]

    train_files = [f for s in train_sessions for f in session_map[s]]
    val_files   = [f for s in val_sessions   for f in session_map[s]]
    test_files  = [f for s in test_sessions  for f in session_map[s]]

    print(f"\n  Split por sesión temporal:")
    print(f"    Train: {len(train_sessions)} sesiones → {len(train_files)} imágenes")
    print(f"    Val  : {len(val_sessions)} sesiones → {len(val_files)} imágenes")
    print(f"    Test : {len(test_sessions)} sesiones (fecha {last_date}) → {len(test_files)} imágenes")

    return train_files, val_files, test_files


# ──────────────────────────────────────────────────────────────────────────────
# Dataset de Micros
# ──────────────────────────────────────────────────────────────────────────────
def build_micros_dataset(
    split_name: str,
    image_files: list[Path],
    labels_dir: Path,
    out_images: Path,
    out_labels: Path,
) -> int:
    """Copia imágenes y genera labels de clase 'micro' (class_id=0)."""
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)
    count = 0

    for img_path in image_files:
        label_path = labels_dir / f"{img_path.stem}.txt"
        labels = read_yolo_labels(label_path)
        micro_labels = [l for l in labels if l[0] == CLASS_MICRO]

        if not micro_labels:
            continue  # imagen sin micro → no incluir en dataset de micros

        # Copiar imagen
        shutil.copy2(img_path, out_images / img_path.name)

        # Escribir label (solo micros, remapeado a class_id=0)
        label_out = out_labels / f"{img_path.stem}.txt"
        with open(label_out, "w") as f:
            for _, cx, cy, bw, bh in micro_labels:
                f.write(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")
        count += 1

    print(f"    [{split_name}] Micros: {count} imágenes con anotaciones")
    return count


# ──────────────────────────────────────────────────────────────────────────────
# Dataset de Placas (crops de micros)
# ──────────────────────────────────────────────────────────────────────────────
def build_placas_dataset(
    split_name: str,
    image_files: list[Path],
    labels_dir: Path,
    out_images: Path,
    out_labels: Path,
) -> int:
    """
    Para cada micro detectado en la imagen:
      1. Extrae el crop del micro (con padding)
      2. Busca bboxes de placa que caigan dentro del micro
      3. Reescala los bboxes de placa al sistema de coordenadas del crop
      4. Guarda el crop como imagen + label de placa
    """
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)
    count = 0

    for img_path in image_files:
        label_path = labels_dir / f"{img_path.stem}.txt"
        labels = read_yolo_labels(label_path)

        micro_labels = [l for l in labels if l[0] == CLASS_MICRO]
        placa_labels = [l for l in labels if l[0] == CLASS_PLACA]

        if not micro_labels:
            continue

        with Image.open(img_path) as img:
            img_w, img_h = img.size

            for micro_idx, (_, mcx, mcy, mbw, mbh) in enumerate(micro_labels):
                # Bounding box del micro en píxeles
                mx1, my1, mx2, my2 = yolo_to_abs(mcx, mcy, mbw, mbh, img_w, img_h)

                # Añadir padding
                pad_x = int((mx2 - mx1) * MICRO_CROP_PADDING)
                pad_y = int((my2 - my1) * MICRO_CROP_PADDING)
                mx1 = max(0, mx1 - pad_x)
                my1 = max(0, my1 - pad_y)
                mx2 = min(img_w, mx2 + pad_x)
                my2 = min(img_h, my2 + pad_y)

                crop_w = mx2 - mx1
                crop_h = my2 - my1
                if crop_w <= 0 or crop_h <= 0:
                    continue

                # Crop del micro
                crop = img.crop((mx1, my1, mx2, my2))

                # Buscar placas dentro del crop del micro
                placa_annotations = []
                for _, pcx, pcy, pbw, pbh in placa_labels:
                    px1, py1, px2, py2 = yolo_to_abs(pcx, pcy, pbw, pbh, img_w, img_h)

                    # Verificar si la placa está dentro del micro (IoU mínimo o contención)
                    inter_x1 = max(px1, mx1)
                    inter_y1 = max(py1, my1)
                    inter_x2 = min(px2, mx2)
                    inter_y2 = min(py2, my2)

                    if inter_x1 >= inter_x2 or inter_y1 >= inter_y2:
                        continue  # placa fuera del micro

                    # Reescalar al sistema de coordenadas del crop
                    rel_x1 = inter_x1 - mx1
                    rel_y1 = inter_y1 - my1
                    rel_x2 = inter_x2 - mx1
                    rel_y2 = inter_y2 - my1

                    new_cx, new_cy, new_bw, new_bh = abs_to_yolo(
                        rel_x1, rel_y1, rel_x2, rel_y2, crop_w, crop_h
                    )
                    # Clipear
                    new_cx = clip(new_cx)
                    new_cy = clip(new_cy)
                    new_bw = clip(new_bw)
                    new_bh = clip(new_bh)

                    if new_bw > 0 and new_bh > 0:
                        placa_annotations.append((new_cx, new_cy, new_bw, new_bh))

                if not placa_annotations:
                    continue  # no hay placas dentro de este micro → no incluir

                # Guardar crop
                crop_name = f"{img_path.stem}_micro{micro_idx}.png"
                crop.save(out_images / crop_name)

                # Guardar label
                label_out = out_labels / f"{img_path.stem}_micro{micro_idx}.txt"
                with open(label_out, "w") as f:
                    for cx, cy, bw, bh in placa_annotations:
                        f.write(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")
                count += 1

    print(f"    [{split_name}] Placas: {count} crops con anotaciones")
    return count


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Prepara datasets YOLO para micros y placas desde anotaciones de Label Studio."
    )
    parser.add_argument("--images", default="dataset",
                        help="Directorio de imágenes originales (default: dataset/)")
    parser.add_argument("--labels", default="data/annotations/validated",
                        help="Directorio de labels YOLO validados")
    parser.add_argument("--train", type=float, default=0.70)
    parser.add_argument("--val",   type=float, default=0.15)
    parser.add_argument("--test",  type=float, default=0.15)
    parser.add_argument("--seed",  type=int,   default=42)
    args = parser.parse_args()

    root       = Path(__file__).parent.parent
    images_dir = (root / args.images).resolve()
    labels_dir = (root / args.labels).resolve()

    if not images_dir.exists():
        print(f"[ERROR] Directorio de imágenes no encontrado: {images_dir}")
        sys.exit(1)
    if not labels_dir.exists():
        print(f"[ERROR] Directorio de labels no encontrado: {labels_dir}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Preparación de Datasets YOLO")
    print(f"{'='*60}")
    print(f"  Imágenes  : {images_dir}")
    print(f"  Labels    : {labels_dir}")
    print(f"  Split     : {args.train:.0%} train / {args.val:.0%} val / {args.test:.0%} test")
    print(f"  Seed      : {args.seed}")

    # Recolectar imágenes
    image_files = sorted([
        f for f in images_dir.iterdir()
        if f.suffix.lower() in SUPPORTED_IMAGE_EXT
    ])
    print(f"  Imágenes  : {len(image_files)}")

    # Split por sesión
    train_files, val_files, test_files = split_sessions(
        image_files, args.train, args.val, args.test, args.seed
    )

    # ── Dataset de Micros ──────────────────────────────────────────────────
    print(f"\n[1/2] Generando dataset de MICROS...")
    base_m = root / "datasets" / "micros"
    for split_name, files in [("train", train_files), ("val", val_files), ("test", test_files)]:
        build_micros_dataset(
            split_name, files, labels_dir,
            base_m / "images" / split_name,
            base_m / "labels" / split_name,
        )

    # ── Dataset de Placas ──────────────────────────────────────────────────
    print(f"\n[2/2] Generando dataset de PLACAS (crops de micros)...")
    base_p = root / "datasets" / "placas"
    for split_name, files in [("train", train_files), ("val", val_files), ("test", test_files)]:
        build_placas_dataset(
            split_name, files, labels_dir,
            base_p / "images" / split_name,
            base_p / "labels" / split_name,
        )

    print(f"\n✅ Datasets generados en:")
    print(f"   {base_m}")
    print(f"   {base_p}")
    print(f"\nPróximo paso: verificar con validate_annotations.py y luego entrenar.\n")


if __name__ == "__main__":
    main()
