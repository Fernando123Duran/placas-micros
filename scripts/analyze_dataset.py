#!/usr/bin/env python3
"""
analyze_dataset.py — Análisis estadístico y visual del dataset de imágenes.

Genera un reporte completo en data/analysis/dataset_report.md con:
  - Conteo total, formatos, resoluciones
  - Distribución temporal (sesiones de captura)
  - Detección de duplicados exactos (MD5)
  - Imágenes potencialmente problemáticas
  - Histogramas de resolución y tamaño

Uso:
    python scripts/analyze_dataset.py
    python scripts/analyze_dataset.py --dataset dataset/ --output data/analysis/
"""

import argparse
import hashlib
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# ── Importar PIL (disponible en el .venv) ──────────────────────────────────
try:
    from PIL import Image
except ImportError:
    print("[ERROR] Pillow no está instalado. Activa el .venv correcto.")
    sys.exit(1)

# ── Importar matplotlib (opcional, para histogramas) ───────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")  # no necesita display
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("[WARN] matplotlib no disponible — se omitirán histogramas PNG.")


# ──────────────────────────────────────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}
MIN_VALID_HEIGHT = 32   # imágenes más pequeñas pueden ser problemáticas
MIN_VALID_WIDTH  = 32


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def md5_of_file(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def parse_session_key(filename: str) -> str:
    """
    Extrae la clave de sesión temporal del nombre de archivo.
    Formato esperado: YYYY-MM-DD_HH-MM_N.ext → clave = YYYY-MM-DD_HH-MM
    Si el nombre no sigue el patrón, retorna el nombre completo.
    """
    stem = Path(filename).stem  # sin extensión
    parts = stem.split("_")
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"  # YYYY-MM-DD_HH-MM
    return stem


def laplacian_variance(img_gray) -> float:
    """Calcula la varianza del Laplaciano como medida de nitidez."""
    import numpy as np
    arr = np.array(img_gray, dtype=np.float32)
    # Kernel Laplaciano simple
    kernel = [
        [0, 1, 0],
        [1, -4, 1],
        [0, 1, 0],
    ]
    # Implementación manual sin scipy para evitar dependencias extra
    h, w = arr.shape
    result = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            val = (
                arr[y-1, x] + arr[y+1, x] + arr[y, x-1] + arr[y, x+1]
                - 4 * arr[y, x]
            )
            result.append(val)
    return float(statistics.variance(result)) if len(result) > 1 else 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Análisis principal
# ──────────────────────────────────────────────────────────────────────────────
def analyze(dataset_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Análisis de Dataset: {dataset_dir}")
    print(f"{'='*60}\n")

    # ── Recolectar archivos ────────────────────────────────────────────────
    all_files = sorted(dataset_dir.iterdir())
    image_files = [f for f in all_files if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    other_files = [f for f in all_files if f.suffix.lower() not in SUPPORTED_EXTENSIONS and f.is_file()]

    print(f"[1/6] Archivos encontrados: {len(all_files)} total | {len(image_files)} imágenes | {len(other_files)} otros")

    # ── Análisis por imagen ───────────────────────────────────────────────
    widths, heights, sizes_kb, aspects = [], [], [], []
    formats_counter: Counter = Counter()
    modes_counter:   Counter = Counter()
    errors = []
    tiny_images = []
    hash_map: dict[str, list[str]] = defaultdict(list)
    session_map: dict[str, list[str]] = defaultdict(list)

    print("[2/6] Analizando imágenes...")
    for img_path in image_files:
        try:
            with Image.open(img_path) as img:
                img.verify()  # detecta corrupción

            with Image.open(img_path) as img:
                w, h = img.size
                mode = img.mode
                fmt  = img.format or img_path.suffix.upper().lstrip(".")

            size_kb = img_path.stat().st_size / 1024
            widths.append(w)
            heights.append(h)
            sizes_kb.append(size_kb)
            aspects.append(w / h)
            formats_counter[fmt] += 1
            modes_counter[mode] += 1

            if w < MIN_VALID_WIDTH or h < MIN_VALID_HEIGHT:
                tiny_images.append((img_path.name, w, h))

            # Hash MD5 para duplicados
            md5 = md5_of_file(img_path)
            hash_map[md5].append(img_path.name)

            # Sesión temporal
            session_key = parse_session_key(img_path.name)
            session_map[session_key].append(img_path.name)

        except Exception as exc:
            errors.append((img_path.name, str(exc)))

    total_ok = len(image_files) - len(errors)
    print(f"    → OK: {total_ok} | Errores: {len(errors)} | Muy pequeñas: {len(tiny_images)}")

    # ── Estadísticas de resolución ────────────────────────────────────────
    print("[3/6] Calculando estadísticas de resolución...")

    def safe_stat(lst, fn):
        return fn(lst) if lst else 0

    w_min    = safe_stat(widths, min)
    w_max    = safe_stat(widths, max)
    w_mean   = safe_stat(widths, statistics.mean)
    w_median = safe_stat(widths, statistics.median)

    h_min    = safe_stat(heights, min)
    h_max    = safe_stat(heights, max)
    h_mean   = safe_stat(heights, statistics.mean)
    h_median = safe_stat(heights, statistics.median)

    ar_min   = safe_stat(aspects, min)
    ar_max   = safe_stat(aspects, max)
    ar_mean  = safe_stat(aspects, statistics.mean)

    size_min  = safe_stat(sizes_kb, min)
    size_max  = safe_stat(sizes_kb, max)
    size_mean = safe_stat(sizes_kb, statistics.mean)

    landscape = sum(1 for a in aspects if a > 1.0)
    portrait  = sum(1 for a in aspects if a <= 1.0)
    unique_res = len(set(zip(widths, heights)))

    # Distribución por ancho
    w_buckets = {"<640": 0, "640–960": 0, "960–1280": 0, "1280–1920": 0, "≥1920": 0}
    for w in widths:
        if   w < 640:  w_buckets["<640"]     += 1
        elif w < 960:  w_buckets["640–960"]  += 1
        elif w < 1280: w_buckets["960–1280"] += 1
        elif w < 1920: w_buckets["1280–1920"] += 1
        else:          w_buckets["≥1920"]    += 1

    # ── Duplicados exactos ────────────────────────────────────────────────
    print("[4/6] Detectando duplicados exactos (MD5)...")
    exact_dupes = {k: v for k, v in hash_map.items() if len(v) > 1}

    # ── Sesiones temporales ───────────────────────────────────────────────
    print("[5/6] Analizando sesiones temporales...")
    sessions_sorted = sorted(session_map.items())
    session_sizes   = [len(v) for v in session_map.values()]
    total_sessions  = len(session_map)

    # Distribución por fecha
    date_map: dict[str, int] = defaultdict(int)
    for key, imgs in session_map.items():
        date = key.split("_")[0]
        date_map[date] += len(imgs)

    # ── Histograma (si matplotlib disponible) ─────────────────────────────
    print("[6/6] Generando histogramas...")
    if HAS_MATPLOTLIB and widths:
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))

        axes[0].hist(widths,  bins=20, color="#4C8EDA", edgecolor="white")
        axes[0].set_title("Distribución de Anchos (px)")
        axes[0].set_xlabel("Ancho (px)")
        axes[0].set_ylabel("Imágenes")
        axes[0].axvline(w_median, color="orange", linestyle="--", label=f"Mediana: {w_median:.0f}")
        axes[0].legend()

        axes[1].hist(heights, bins=20, color="#5CB85C", edgecolor="white")
        axes[1].set_title("Distribución de Altos (px)")
        axes[1].set_xlabel("Alto (px)")
        axes[1].axvline(h_median, color="orange", linestyle="--", label=f"Mediana: {h_median:.0f}")
        axes[1].legend()

        axes[2].hist(sizes_kb, bins=20, color="#D9534F", edgecolor="white")
        axes[2].set_title("Distribución de Tamaño (KB)")
        axes[2].set_xlabel("Tamaño (KB)")
        mean_size = statistics.mean(sizes_kb)
        axes[2].axvline(mean_size, color="orange", linestyle="--", label=f"Media: {mean_size:.0f} KB")
        axes[2].legend()

        plt.tight_layout()
        hist_path = output_dir / "resolution_hist.png"
        plt.savefig(hist_path, dpi=120)
        plt.close()
        print(f"    → Histograma guardado: {hist_path}")

    # ── Guardar session_groups.json ────────────────────────────────────────
    import json
    session_json = {k: v for k, v in sessions_sorted}
    json_path = output_dir / "session_groups.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(session_json, f, ensure_ascii=False, indent=2)
    print(f"    → Grupos de sesión guardados: {json_path}")

    # ── Generar reporte Markdown ───────────────────────────────────────────
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = [
        f"# Reporte de Análisis del Dataset",
        f"",
        f"> Generado: {now_str}  ",
        f"> Dataset: `{dataset_dir.resolve()}`",
        f"",
        f"---",
        f"",
        f"## 1. Resumen General",
        f"",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Total imágenes analizadas | **{total_ok}** |",
        f"| Imágenes con error/corruptas | **{len(errors)}** |",
        f"| Otros archivos (no imágenes) | {len(other_files)} |",
        f"| Formatos encontrados | {dict(formats_counter)} |",
        f"| Modos de color | {dict(modes_counter)} |",
        f"",
        f"---",
        f"",
        f"## 2. Resolución",
        f"",
        f"| Métrica | Ancho (px) | Alto (px) |",
        f"|---------|-----------|---------|",
        f"| Mínimo | {w_min} | {h_min} |",
        f"| Máximo | {w_max} | {h_max} |",
        f"| Media | {w_mean:.0f} | {h_mean:.0f} |",
        f"| Mediana | {w_median:.0f} | {h_median:.0f} |",
        f"",
        f"| Orientación | Cantidad |",
        f"|------------|---------|",
        f"| Landscape (w > h) | {landscape} |",
        f"| Portrait (w ≤ h) | {portrait} |",
        f"| Resoluciones únicas | {unique_res} de {total_ok} |",
        f"",
        f"### Distribución por ancho:",
        f"",
    ]
    for bucket, count in w_buckets.items():
        pct = count / total_ok * 100 if total_ok else 0
        report_lines.append(f"- `{bucket}` px: **{count}** imágenes ({pct:.1f}%)")

    report_lines += [
        f"",
        f"### Aspect Ratio:",
        f"- Mínimo: {ar_min:.2f}",
        f"- Máximo: {ar_max:.2f}",
        f"- Media: {ar_mean:.2f}",
        f"",
        f"---",
        f"",
        f"## 3. Tamaño de Archivo",
        f"",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Mínimo | {size_min:.0f} KB |",
        f"| Máximo | {size_max:.0f} KB |",
        f"| Media | {size_mean:.0f} KB |",
        f"",
        f"---",
        f"",
        f"## 4. Duplicados Exactos (MD5)",
        f"",
    ]

    if exact_dupes:
        report_lines.append(f"⚠️ Se encontraron **{len(exact_dupes)}** grupos de duplicados:\n")
        for md5, files in exact_dupes.items():
            report_lines.append(f"- `{md5[:8]}...`: {', '.join(files)}")
    else:
        report_lines.append("✅ No se detectaron duplicados exactos.")

    report_lines += [
        f"",
        f"---",
        f"",
        f"## 5. Imágenes Potencialmente Problemáticas",
        f"",
        f"### Muy pequeñas (< {MIN_VALID_WIDTH}×{MIN_VALID_HEIGHT} px):",
        f"",
    ]
    if tiny_images:
        for name, w, h in tiny_images:
            report_lines.append(f"- `{name}`: {w}×{h} px")
    else:
        report_lines.append("✅ Ninguna imagen por debajo del umbral mínimo.")

    report_lines += [
        f"",
        f"### Imágenes con error de lectura:",
        f"",
    ]
    if errors:
        for name, err in errors:
            report_lines.append(f"- `{name}`: {err}")
    else:
        report_lines.append("✅ Ninguna imagen corrupta detectada.")

    report_lines += [
        f"",
        f"---",
        f"",
        f"## 6. Sesiones Temporales",
        f"",
        f"Las imágenes están nombradas con patrón `YYYY-MM-DD_HH-MM_N.png`.",
        f"Se agrupan por minuto para identificar ráfagas de captura.",
        f"",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Total de sesiones (minutos únicos) | {total_sessions} |",
        f"| Imágenes por sesión — mínimo | {min(session_sizes) if session_sizes else 0} |",
        f"| Imágenes por sesión — máximo | {max(session_sizes) if session_sizes else 0} |",
        f"| Imágenes por sesión — media | {statistics.mean(session_sizes) if session_sizes else 0:.1f} |",
        f"",
        f"### Distribución por fecha:",
        f"",
    ]
    for date, count in sorted(date_map.items()):
        report_lines.append(f"- `{date}`: {count} imágenes")

    report_lines += [
        f"",
        f"### Sesiones con más imágenes (Top 10):",
        f"",
    ]
    top_sessions = sorted(session_map.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    for key, imgs in top_sessions:
        report_lines.append(f"- `{key}`: {len(imgs)} imágenes")

    report_lines += [
        f"",
        f"> Ver `session_groups.json` para el listado completo de grupos.",
        f"",
        f"---",
        f"",
        f"## 7. Recomendaciones para el Split Train/Val/Test",
        f"",
        f"- **Estrategia:** Split por sesión temporal (por minuto), no por imagen individual.",
        f"- Los grupos de imágenes del mismo minuto deben ir completos al mismo split.",
        f"- Distribución propuesta: **70% train / 15% val / 15% test**.",
        f"- El test set debería contener sesiones de la última fecha ({max(date_map.keys()) if date_map else 'N/A'}).",
        f"",
        f"---",
        f"",
        f"*Reporte generado por `scripts/analyze_dataset.py`*",
    ]

    report_path = output_dir / "dataset_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\n✅ Reporte generado: {report_path}")

    # ── Resumen en consola ────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"  RESUMEN")
    print(f"{'─'*60}")
    print(f"  Imágenes válidas : {total_ok}")
    print(f"  Corruptas        : {len(errors)}")
    print(f"  Duplicados exactos: {sum(len(v) - 1 for v in exact_dupes.values())} extra(s)")
    print(f"  Resolución media : {w_mean:.0f} × {h_mean:.0f} px")
    print(f"  Sesiones únicas  : {total_sessions}")
    print(f"{'─'*60}\n")


# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Análisis estadístico del dataset de imágenes."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="dataset",
        help="Directorio del dataset (default: dataset/)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/analysis",
        help="Directorio de salida para el reporte (default: data/analysis/)"
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    dataset_dir  = (project_root / args.dataset).resolve()
    output_dir   = (project_root / args.output).resolve()

    if not dataset_dir.exists():
        print(f"[ERROR] El directorio del dataset no existe: {dataset_dir}")
        sys.exit(1)

    analyze(dataset_dir, output_dir)


if __name__ == "__main__":
    main()
