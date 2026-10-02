# Reporte de Análisis del Dataset

> Generado: 2026-10-02 11:06:36  
> Dataset: `/home/luffy/Documentos/IA/placas-micros/dataset`

---

## 1. Resumen General

| Métrica | Valor |
|---------|-------|
| Total imágenes analizadas | **547** |
| Imágenes con error/corruptas | **0** |
| Otros archivos (no imágenes) | 0 |
| Formatos encontrados | {'PNG': 547} |
| Modos de color | {'RGB': 547} |

---

## 2. Resolución

| Métrica | Ancho (px) | Alto (px) |
|---------|-----------|---------|
| Mínimo | 627 | 458 |
| Máximo | 1873 | 971 |
| Media | 1336 | 761 |
| Mediana | 1341 | 764 |

| Orientación | Cantidad |
|------------|---------|
| Landscape (w > h) | 543 |
| Portrait (w ≤ h) | 4 |
| Resoluciones únicas | 546 de 547 |

### Distribución por ancho:

- `<640` px: **1** imágenes (0.2%)
- `640–960` px: **18** imágenes (3.3%)
- `960–1280` px: **187** imágenes (34.2%)
- `1280–1920` px: **341** imágenes (62.3%)
- `≥1920` px: **0** imágenes (0.0%)

### Aspect Ratio:
- Mínimo: 0.93
- Máximo: 2.94
- Media: 1.77

---

## 3. Tamaño de Archivo

| Métrica | Valor |
|---------|-------|
| Mínimo | 359 KB |
| Máximo | 2092 KB |
| Media | 1096 KB |

---

## 4. Duplicados Exactos (MD5)

✅ No se detectaron duplicados exactos.

---

## 5. Imágenes Potencialmente Problemáticas

### Muy pequeñas (< 32×32 px):

✅ Ninguna imagen por debajo del umbral mínimo.

### Imágenes con error de lectura:

✅ Ninguna imagen corrupta detectada.

---

## 6. Sesiones Temporales

Las imágenes están nombradas con patrón `YYYY-MM-DD_HH-MM_N.png`.
Se agrupan por minuto para identificar ráfagas de captura.

| Métrica | Valor |
|---------|-------|
| Total de sesiones (minutos únicos) | 131 |
| Imágenes por sesión — mínimo | 1 |
| Imágenes por sesión — máximo | 11 |
| Imágenes por sesión — media | 4.2 |

### Distribución por fecha:

- `2026-09-29`: 306 imágenes
- `2026-09-30`: 107 imágenes
- `2026-10-01`: 134 imágenes

### Sesiones con más imágenes (Top 10):

- `2026-10-01_23-31`: 11 imágenes
- `2026-09-29_23-38`: 10 imágenes
- `2026-10-01_23-29`: 10 imágenes
- `2026-10-01_23-32`: 10 imágenes
- `2026-09-29_23-40`: 9 imágenes
- `2026-09-30_00-18`: 9 imágenes
- `2026-10-01_23-30`: 9 imágenes
- `2026-09-29_23-45`: 8 imágenes
- `2026-09-29_23-56`: 8 imágenes
- `2026-10-01_23-13`: 8 imágenes

> Ver `session_groups.json` para el listado completo de grupos.

---

## 7. Recomendaciones para el Split Train/Val/Test

- **Estrategia:** Split por sesión temporal (por minuto), no por imagen individual.
- Los grupos de imágenes del mismo minuto deben ir completos al mismo split.
- Distribución propuesta: **70% train / 15% val / 15% test**.
- El test set debería contener sesiones de la última fecha (2026-10-01).

---

*Reporte generado por `scripts/analyze_dataset.py`*