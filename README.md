# Sistema de Detección de Placas de Micros

Prototipo de visión artificial para detectar micros de transporte público, leer sus placas con OCR y registrar los eventos en una base de datos.

**Stack:** YOLO26 · ByteTrack · EasyOCR · FastAPI · React + Vite · SQLite  
**GPU:** NVIDIA GeForce RTX 4080 SUPER (16 GB)  
**Python:** 3.10.12 (`.venv` compartido con `tienda-deteccion`)

---

## Activar el entorno virtual

Ejecutar **una vez por sesión de terminal** antes de cualquier comando `python`:

```bash
source /home/luffy/Documentos/IA/tienda-deteccion/.venv/bin/activate
```

Para desactivar:

```bash
deactivate
```

---

## Estructura del proyecto

```
placas-micros/
├── dataset/                   # Imágenes originales (547 PNG) — NO modificar
├── data/
│   ├── annotations/
│   │   ├── export_yolo_raw/   # Exportación bruta de Label Studio
│   │   └── validated/         # Anotaciones validadas (usadas por scripts)
│   └── analysis/              # Reportes de análisis del dataset
├── datasets/
│   ├── micros/                # Dataset YOLO — Modelo 1 (detector de micros)
│   └── placas/                # Dataset YOLO — Modelo 2 (detector de placas)
├── configs/                   # Configuraciones de entrenamiento y sistema
├── runs/
│   ├── micros/                # Resultados de experimentos — Modelo 1
│   └── placas/                # Resultados de experimentos — Modelo 2
├── models/                    # Pesos finales seleccionados (.pt)
├── scripts/                   # Scripts de utilidad
├── backend/                   # API FastAPI
├── frontend/                  # Interfaz React + Vite
├── docs/                      # Documentación
└── docker-compose.yml         # Label Studio
```

---

## Comandos en orden — todas las fases

### ─── FASE 0: Activar entorno ───────────────────────────────────

```bash
cd /home/luffy/Documentos/IA/placas-micros
source /home/luffy/Documentos/IA/tienda-deteccion/.venv/bin/activate
```

---

### ─── FASE 1: Análisis del dataset ──────────────────────────────

```bash
python scripts/analyze_dataset.py
```

Genera `data/analysis/dataset_report.md` y `resolution_hist.png`.

---

### ─── FASE 2: Label Studio ───────────────────────────────────────

```bash
# Levantar Label Studio
docker compose up -d

# Abrir en navegador: http://localhost:8080
# Detener Label Studio
docker compose down
```

---

### ─── FASE 3: Etiquetado ─────────────────────────────────────────

Etiquetar manualmente en Label Studio siguiendo `docs/guia_etiquetado.md`.

Clases:
- `micro` (class 0)
- `placa` (class 1) — solo placas de micros

Exportar en formato **YOLO** y colocar los archivos `.txt` en:
```
data/annotations/export_yolo_raw/
```

---

### ─── FASE 4: Validar anotaciones ───────────────────────────────

```bash
# Validar exportación cruda (nc=2: micro + placa)
python scripts/validate_annotations.py \
  --labels data/annotations/export_yolo_raw \
  --images dataset \
  --nc 2

# Si pasa sin errores, copiar a validated/
cp data/annotations/export_yolo_raw/*.txt data/annotations/validated/
```

---

### ─── FASE 5: Preparar datasets YOLO ────────────────────────────

```bash
python scripts/prepare_dataset.py
```

Genera automáticamente:
- `datasets/micros/` — imágenes + labels de micros (split 70/15/15 por sesión)
- `datasets/placas/` — crops de micros con labels de placas reescaladas

Split resultante:
- **Train:** 88 sesiones → 338 imágenes de micros / 217 crops de placas
- **Val:** 18 sesiones → 75 imágenes / 37 crops
- **Test:** 25 sesiones (fecha 2026-10-01) → 134 imágenes / 91 crops

---

### ─── FASE 6: Entrenar Detector de Micros (Modelo 1) ────────────

> ⚠️ Ejecutar tú manualmente. El entrenamiento puede tardar 30-60 min.

Editar hiperparámetros en [`configs/train_micros.yaml`](configs/train_micros.yaml) antes de ejecutar.

```bash
# Entrenamiento con la configuración base del YAML
python scripts/train_micros.py

# Ejemplos de variantes sin modificar el YAML:
python scripts/train_micros.py --name exp_m1_yolo26m_640_b16 --model yolo26m.pt
python scripts/train_micros.py --name exp_m1_yolo26s_960_b8  --imgsz 960 --batch 8

# Reanudar entrenamiento interrumpido:
python scripts/train_micros.py --resume runs/micros/exp_m1_yolo26s_640_b16/weights/last.pt
```

Resultados en: `runs/micros/<name>/`

**Criterios de aceptación:**
- mAP50 > 0.85
- mAP50-95 > 0.60
- Sin signos de overfitting

Si mAP50 < 0.85 → editar `configs/train_micros.yaml` (cambiar `model: yolo26m.pt` o `imgsz: 960`) y re-ejecutar con un nuevo `name`.

---

### ─── FASE 7: Entrenar Detector de Placas (Modelo 2) ────────────

> ⚠️ Solo después de aceptar los resultados de Fase 6.

Editar hiperparámetros en [`configs/train_placas.yaml`](configs/train_placas.yaml) antes de ejecutar.

```bash
# Entrenamiento con la configuración base del YAML
python scripts/train_placas.py

# Variante con modelo mayor si el baseline no alcanza el criterio:
python scripts/train_placas.py --name exp_m2_yolo26s-p2_640_b16 --model yolo26s-p2.pt --batch 16

# Reanudar entrenamiento interrumpido:
python scripts/train_placas.py --resume runs/placas/exp_m2_yolo26n-p2_640_b32/weights/last.pt
```

Resultados en: `runs/placas/<name>/`

**Criterios de aceptación:**
- mAP50 > 0.80 (✅ Obtenido: **0.986**)
- Sin falsos positivos evidentes

> 📄 **Informe detallado de conclusiones:** Consulta [README_EXP_1.md](file:///home/luffy/Documentos/IA/placas-micros/README_EXP_1.md) para el análisis completo de métricas, curvas y tiempos de ambos entrenamientos.

---

### ─── FASE 8-10: Pipeline completo ──────────────────────────────

> ✅ Los modelos del Experimento 1 ya fueron validados y copiados a `models/`:
> - `models/micro_detector_v1.pt`
> - `models/plate_detector_v1.pt`

```bash
# Si se desea re-copiar manualmente:
cp runs/micros/exp_m1_yolo26s_640_b16/weights/best.pt models/micro_detector_v1.pt
cp runs/placas/exp_m2_yolo26n_640_b32/weights/best.pt models/plate_detector_v1.pt
```

---

### ─── FASE 11-12: Backend FastAPI ───────────────────────────────

```bash
# Configurar variables de entorno
cp backend/.env.example backend/.env
# Editar backend/.env con las rutas correctas a los modelos

# Iniciar el servidor de desarrollo
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API disponible en: `http://localhost:8000`  
Documentación Swagger: `http://localhost:8000/docs`

---

### ─── FASE 13: Frontend React + Vite ────────────────────────────

```bash
cd frontend

# Instalar dependencias (primera vez)
npm install

# Servidor de desarrollo
npm run dev
```

Interfaz disponible en: `http://localhost:5173`

---

### ─── FASE 15: Tests ─────────────────────────────────────────────

```bash
# Tests del backend
python -m pytest tests/backend/ -v

# Validar dataset de micros
python scripts/validate_annotations.py \
  --labels datasets/micros/labels/train \
  --images datasets/micros/images/train \
  --nc 1

# Validar dataset de placas
python scripts/validate_annotations.py \
  --labels datasets/placas/labels/train \
  --images datasets/placas/images/train \
  --nc 1
```

---

## Evaluación de experimentos

```bash
# Ver métricas del último experimento de micros
cat runs/micros/exp_m1_yolo26s_640_b16/results.csv

# Evaluar modelo en conjunto test
python -c "
from ultralytics import YOLO
model = YOLO('runs/micros/exp_m1_yolo26s_640_b16/weights/best.pt')
metrics = model.val(data='configs/data_micros.yaml', split='test')
print(metrics)
"
```

---

## Paquetes instalados en el `.venv`

| Paquete | Versión | Para qué |
|---------|---------|---------|
| torch | 2.13.0+cu130 | Entrenamiento e inferencia GPU |
| ultralytics | 8.4.120 | YOLO26, ByteTrack |
| opencv-python | 5.0.0.93 | Procesamiento de imagen |
| easyocr | 1.7.2 | OCR de placas |
| fastapi | 0.142.2 | API backend |
| uvicorn | 0.54.0 | Servidor ASGI |
| sqlalchemy | 2.0.54 | ORM base de datos |
| aiosqlite | 0.22.1 | SQLite async |
| alembic | 1.20.0 | Migraciones DB |
| websockets | 16.1.1 | Stream webcam |
| python-dotenv | 1.2.4 | Variables de entorno |

---

## Notas importantes

- **NO modificar** las imágenes en `dataset/` — son los datos originales
- **NO commitear** pesos `.pt`, datasets o evidencias (están en `.gitignore`)
- **NO iniciar** un entrenamiento sin revisar primero los resultados del anterior
- Los **entrenamientos** siempre los ejecuta el usuario manualmente
- La carpeta `project-1-at-*/` de Label Studio puede eliminarse una vez copiadas las anotaciones a `data/annotations/`
