#!/usr/bin/env python3
"""
validate_annotations.py — Valida la calidad de las anotaciones YOLO exportadas.

Verifica:
  - Cada archivo .txt tiene su imagen correspondiente y viceversa
  - Todos los bounding boxes están dentro del rango [0, 1]
  - No hay archivos label vacíos sin justificación
  - Los class_ids son válidos según el número de clases declaradas
  - Informa de imágenes sin anotación (posibles backgrounds)

Uso:
    python scripts/validate_annotations.py --labels data/annotations/export_yolo_raw/ --nc 2
    python scripts/validate_annotations.py --labels data/annotations/validated/ --nc 1
"""

import argparse
import sys
from pathlib import Path


SUPPORTED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def find_image_for_label(label_path: Path, images_dir: Path) -> Path | None:
    """Busca la imagen correspondiente a un archivo .txt de label."""
    stem = label_path.stem
    for ext in SUPPORTED_IMAGE_EXT:
        candidate = images_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def validate(labels_dir: Path, images_dir: Path, nc: int) -> bool:
    """
    Valida el conjunto de anotaciones.
    Retorna True si no hay errores críticos.
    """
    errors   = []
    warnings = []

    label_files = list(labels_dir.glob("*.txt"))
    image_files = [
        f for f in images_dir.iterdir()
        if f.suffix.lower() in SUPPORTED_IMAGE_EXT
    ] if images_dir.exists() else []

    print(f"\n{'='*60}")
    print(f"  Validación de Anotaciones YOLO")
    print(f"{'='*60}")
    print(f"  Labels dir : {labels_dir}")
    print(f"  Images dir : {images_dir if images_dir.exists() else '(mismo directorio)'}")
    print(f"  Clases (nc): {nc}")
    print(f"  Labels encontrados: {len(label_files)}")
    print(f"  Imágenes encontradas: {len(image_files)}\n")

    image_stems = {f.stem for f in image_files}
    label_stems = set()

    for label_path in sorted(label_files):
        stem = label_path.stem
        label_stems.add(stem)

        # 1. ¿Existe la imagen correspondiente?
        if image_files and stem not in image_stems:
            errors.append(f"[SIN IMAGEN] {label_path.name} → no se encontró imagen correspondiente")

        # 2. ¿Está vacío el archivo?
        content = label_path.read_text(encoding="utf-8").strip()
        if not content:
            warnings.append(f"[VACÍO] {label_path.name} → sin anotaciones (¿background?)")
            continue

        # 3. Validar cada línea
        for line_num, line in enumerate(content.splitlines(), 1):
            parts = line.strip().split()
            if len(parts) < 5:
                errors.append(
                    f"[FORMATO] {label_path.name}:{line_num} → "
                    f"línea con {len(parts)} campos (se esperan 5: class cx cy w h)"
                )
                continue

            try:
                class_id = int(parts[0])
                cx, cy, bw, bh = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            except ValueError:
                errors.append(
                    f"[TIPO] {label_path.name}:{line_num} → "
                    f"valores no numéricos: '{line.strip()}'"
                )
                continue

            # 4. class_id válido
            if class_id < 0 or class_id >= nc:
                errors.append(
                    f"[CLASE] {label_path.name}:{line_num} → "
                    f"class_id={class_id} fuera de rango [0, {nc-1}]"
                )

            # 5. Coordenadas dentro de [0, 1]
            for name, val in [("cx", cx), ("cy", cy), ("w", bw), ("h", bh)]:
                if not (0.0 <= val <= 1.0):
                    errors.append(
                        f"[RANGO] {label_path.name}:{line_num} → "
                        f"{name}={val:.4f} fuera de [0, 1]"
                    )

            # 6. Bounding box degenerado
            if bw <= 0 or bh <= 0:
                errors.append(
                    f"[BBOX] {label_path.name}:{line_num} → "
                    f"bbox degenerado: w={bw}, h={bh}"
                )

            # 7. Bbox extremadamente pequeño (advertencia)
            if bw < 0.005 or bh < 0.005:
                warnings.append(
                    f"[PEQUEÑO] {label_path.name}:{line_num} → "
                    f"bbox muy pequeño: w={bw:.4f}, h={bh:.4f} — verificar"
                )

    # 8. Imágenes sin label correspondiente
    for stem in image_stems:
        if stem not in label_stems:
            warnings.append(f"[SIN LABEL] imagen `{stem}.*` no tiene archivo .txt correspondiente")

    # ── Reporte ─────────────────────────────────────────────────────────────
    print(f"{'─'*60}")
    if errors:
        print(f"  ❌ ERRORES CRÍTICOS: {len(errors)}")
        for e in errors:
            print(f"     {e}")
    else:
        print(f"  ✅ Sin errores críticos")

    print()
    if warnings:
        print(f"  ⚠️  ADVERTENCIAS: {len(warnings)}")
        for w in warnings:
            print(f"     {w}")
    else:
        print(f"  ✅ Sin advertencias")

    print(f"{'─'*60}\n")

    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Validación de anotaciones YOLO exportadas de Label Studio."
    )
    parser.add_argument(
        "--labels",
        type=str,
        required=True,
        help="Directorio con archivos .txt de labels YOLO"
    )
    parser.add_argument(
        "--images",
        type=str,
        default=None,
        help="Directorio con imágenes (si difiere del de labels). Default: mismo directorio."
    )
    parser.add_argument(
        "--nc",
        type=int,
        default=2,
        help="Número de clases (default: 2 → micro + placa)"
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    labels_dir   = (project_root / args.labels).resolve()
    images_dir   = (project_root / args.images).resolve() if args.images else labels_dir

    if not labels_dir.exists():
        print(f"[ERROR] El directorio de labels no existe: {labels_dir}")
        sys.exit(1)

    ok = validate(labels_dir, images_dir, args.nc)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
