# Guía de Modelos y Dataset — Sistema de Detección de Placas de Micros

Este documento describe la procedencia, estructura, formato y procedimiento de descarga tanto de los **conjuntos de datos (datasets)** como de los **pesos de los modelos entrenados** utilizados en el sistema de visión artificial.

---

## 1. Pesos de los Modelos Entrenados

El sistema implementa una arquitectura en cascada de dos etapas de detección basada en YOLO26 más un motor de reconocimiento óptico de caracteres (PaddleOCR + OpenCV):

| Modelo | Arquitectura Base | Tamaño / Pesos | Tarea | Métricas (Test/Val) |
| :--- | :--- | :--- | :--- | :--- |
| **Detector de Micros** | YOLO26s (Small) | `models/micro_detector_v1.pt` (~19 MB) | Detección de buses de transporte público en cuadro completo | **mAP50: 98.9%**, mAP50-95: 91.6% |
| **Detector de Placas** | YOLO26n (Nano) | `models/plate_detector_v1.pt` (~5.5 MB) | Localización de placas bolivianas sobre el recorte del micro | **mAP50: 98.6%**, mAP50-95: 86.8% |
| **Motor OCR (Línea)** | PaddleOCR PP-OCRv4/v6 | Descarga automática en runtime | Transcripción de caracteres alfanuméricos | Precisión en placas estándar > 95% |

### Procedimiento de Descarga e Instalación de Modelos

Dado que los archivos de pesos `.pt` no deben versionarse en repositorios Git por políticas de tamaño, se proporcionan enlaces externos:

> 📌 **Enlaces de Descarga Oficiales:**
> * **Google Drive (Paquete completo de modelos):** `[INSERTAR_ENLACE_GOOGLE_DRIVE_MODELOS]`
> * **Hugging Face Hub / GitHub Releases:** `[INSERTAR_ENLACE_HUGGINGFACE_O_RELEASES]`

#### Pasos para colocar los modelos en el proyecto:
1. Cree la carpeta `models/` en la raíz del proyecto (si no existe):
   ```bash
   mkdir -p models
   ```
2. Descargue los archivos y colóquelos con los siguientes nombres exactos:
   * `models/micro_detector_v1.pt`
   * `models/plate_detector_v1.pt`
3. Verifique la existencia de los archivos ejecutando:
   ```bash
   ls -lh models/*.pt
   ```

---

## 2. Dataset y Procedimiento de Preparación

### 2.1. Recolección de Datos
* **Ámbito geográfico:** Santa Cruz de la Sierra, Bolivia.
* **Sujeto de estudio:** Buses de transporte público urbano ("micros tradicionales" de diversas líneas: Línea 1, 2, 8, 10, etc.).
* **Condiciones de captura:** Variabilidad de iluminación diurna, ángulos frontales y semi-perpendiculares, diferentes distancias focales y niveles de congestión vehicular.

### 2.2. Etiquetado y Formato
* **Formato de anotación:** Formato estándar YOLO (`<class_id> <x_center> <y_center> <width> <height>` normalizado en el rango $[0, 1]$).
* **Herramientas empleadas:** Roboflow / Label Studio.
* **Clases definidas:**
  * Clase `0`: `micro` (delimitación del bus completo).
  * Clase `0` (en detector de placas): `placa` (delimitación estricta del marco de la matrícula vehicular).

### 2.3. Particionamiento del Dataset (Split)
El conjunto total se distribuyó con estratificación representativa:
* **Entrenamiento (Train):** 70% de las imágenes con aumentos fotométricos y espaciales.
* **Validación (Val):** 20% para ajuste de hiperparámetros y early stopping (paciencia 25 épocas).
* **Prueba (Test):** 10% reservado exclusivamente para evaluación ciega final.

### 2.4. Aumentos de Datos (Data Augmentation)
Para garantizar robustez frente al mundo real, se aplicaron las siguientes transformaciones controladas:
* Variación de brillo ($\pm 15\%$) y contraste ($\pm 10\%$).
* Desenfoque por movimiento suave (Motion Blur leve para simular vehículos en marcha).
* Rotación leve ($\pm 5^\circ$) y recorte escalado ($0.9$ a $1.1$).
* Mosaic y MixUp durante las primeras épocas de entrenamiento.

---

## 3. Procedimiento para Obtener o Regenerar el Dataset

> 📌 **Enlace de Descarga del Dataset (Imágenes y Etiquetas YOLO):**
> * **Dataset comprimido (ZIP):** `[INSERTAR_ENLACE_GOOGLE_DRIVE_DATASET]`

### Estructura de Directorios requerida:
```text
dataset/
├── micros/
│   ├── images/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   └── labels/
│       ├── train/
│       ├── val/
│       └── test/
├── placas/
│   ├── images/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   └── labels/
│       ├── train/
│       ├── val/
│       └── test/
├── micros.yaml
└── placas.yaml
```

### Scripts de Entrenamiento Autónomo:
Una vez colocado el dataset, el reentrenamiento se ejecuta con los scripts provistos:
```bash
# Entrenar detector de micros (Fase 6)
python scripts/train_micros.py

# Entrenar detector de placas (Fase 7)
python scripts/train_placas.py
```
Los mejores pesos resultantes se guardarán automáticamente en `models/micro_detector_v1.pt` y `models/plate_detector_v1.pt`.
