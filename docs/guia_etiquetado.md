# Guía de Etiquetado con Label Studio

> **Proyecto:** Sistema de Detección de Placas de Micros  
> **Herramienta:** Label Studio (http://localhost:8080)  
> **Fecha:** 2026-10-02

---

## 1. Clases

| ID | Nombre | Descripción |
|----|--------|-------------|
| 0  | `micro` | Bus, minibús o colectivo de transporte público |
| 1  | `placa` | Placa de matrícula vehicular **perteneciente a un micro** |

**Atajos de teclado recomendados:**
- `M` → seleccionar clase `micro`
- `P` → seleccionar clase `placa`

---

## 2. ¿Qué es un `micro`?

**SÍ etiquetar como `micro`:**
- Buses urbanos de cualquier tamaño
- Minibuses y colectivos de transporte público
- Microbuses tipo van/combi destinados a transporte público
- Micros de cualquier color o empresa

**NO etiquetar:**
- Autos particulares
- Camionetas
- Motos o bicicletas
- Camiones de carga
- Ambulancias
- Taxis (salvo que también sean usados como micro/colectivo en la zona)
- Vehículos de servicio

**Regla general:** Si dudas de si es un micro, **NO etiquetar**.

---

## 3. Reglas de Bounding Box para `micro`

| Situación | Regla |
|-----------|-------|
| Micro completamente visible | Bbox ajustado al contorno exterior del vehículo |
| Micro cortado por el borde de la imagen | ✅ **SÍ etiquetar** — el bbox llega hasta el borde. Mínimo visible: 30% del vehículo |
| Micro con personas u objetos adelante | Bbox incluye al micro completo. Las personas no se anotan |
| Micro muy pequeño y lejano (>80px alto) | ✅ **SÍ etiquetar** |
| Micro muy pequeño (<80px alto) | Etiquetar si es claro. Añadir nota si es dudoso |
| Micro de espaldas sin placa visible | ✅ **SÍ etiquetar el micro** (la placa es clase separada) |
| Micro visto desde arriba | ✅ **SÍ etiquetar** si claramente identificable |
| Micros superpuestos | Un bbox por micro visible. Si solapamiento >70%, etiquetar solo el más visible |
| Vehículo ambiguo | ❌ **NO etiquetar**. En duda, omitir |

### Cómo dibujar el bbox del micro:
1. Ajustar al contorno físico del vehículo (no incluir sombra o reflejo en el suelo)
2. En micros cortados por el borde: el bbox llega exactamente al borde de la imagen
3. No incluir espacio de aire extra alrededor del vehículo (bbox ajustado)

---

## 4. Reglas de Bounding Box para `placa`

| Situación | Regla |
|-----------|-------|
| Placa completamente visible | ✅ Bbox ajustado al borde exterior de la placa |
| Placa visible >50% | ✅ **SÍ etiquetar** — bbox al contorno visible |
| Placa visible <50% | ❌ **NO etiquetar** |
| Placa ilegible (blur/oclusión) | ✅ **SÍ etiquetar** el bbox (el modelo detecta la región; OCR intentará leerla) |
| **Placa de auto, camioneta, moto** | ❌ **NO etiquetar nunca** |
| Múltiples micros en imagen | Anotar **solo** las placas de micros identificados |
| Micro sin placa visible | Solo anotar el `micro`, sin `placa` |
| Placa demasiado pequeña (<15px alto) | Etiquetar si es posible identificarla |
| Placa en un ángulo extremo | Etiquetar si >50% es visible y reconocible como placa |

### Cómo dibujar el bbox de la placa:
1. Ajustar al marco de la placa (incluyendo el borde de la placa misma)
2. No incluir área del vehículo alrededor de la placa
3. Para placas parciales: bbox solo sobre la parte visible

---

## 5. Casos Especiales

### 5.1 Personas delante del micro
- Etiquetar el micro completo (el bbox del micro "incluye" a las personas)
- NO etiquetar a las personas como clase separada
- Si la persona tapa más del 60% del micro → etiquetar igual pero con precaución

### 5.2 Varios micros en la misma imagen
- Etiquetar cada micro individualmente
- Etiquetar las placas de cada micro si son visibles

### 5.3 Auto junto al micro
- Etiquetar el micro
- **NO etiquetar la placa del auto** aunque sea visible y clara
- Si el auto tiene su propia placa visible: ignorarla completamente

### 5.4 Micro muy lejano
- Si el micro es identificable pero muy pequeño, sí etiquetar
- Si la placa del micro lejano no es distinguible (~<15px), no etiquetar la placa

### 5.5 Imagen sin micros
- Si no hay micros en la imagen → dejar sin anotaciones (imagen de fondo)
- NO marcar la imagen como "skip" — dejarla sin bbox

### 5.6 Imagen ambigua o de muy mala calidad
- Si la imagen es demasiado borrosa para identificar si es un micro → **skip**
- Usar el botón "Skip" de Label Studio con una nota explicativa

---

## 6. Flujo de Etiquetado Recomendado

Para cada imagen:

1. **Ver la imagen completa** — ¿hay micros?
2. **Etiquetar todos los micros** primero (clase `micro`)
3. **Para cada micro etiquetado**, buscar su placa visible
4. **Etiquetar placas** (clase `placa`) solo si pertenecen a un micro etiquetado
5. **Verificar** que no hay placas de otros vehículos etiquetadas
6. **Guardar** y pasar a la siguiente imagen

---

## 7. Configuración del Proyecto en Label Studio

### Tipo de proyecto:
`Object Detection with Bounding Boxes`

### Clases:
```xml
<RectangleLabels name="label" toName="image">
  <Label value="micro" background="#00BFFF"/>
  <Label value="placa" background="#FF6B35"/>
</RectangleLabels>
```

### Settings recomendados:
- Mostrar labels sobre los bboxes: ✅ activado
- Hotkeys: M=micro, P=placa
- Guidelines URL: apuntar a este documento

---

## 8. Control de Calidad

Durante el etiquetado, cada 50 imágenes revisar:
- ¿Se están etiquetando placas de autos por error?
- ¿Los bboxes de micros están ajustados correctamente?
- ¿Las placas pequeñas están siendo detectadas?

Se realizará una revisión de muestra aleatoria (~50 imágenes) al finalizar el etiquetado completo.

---

*Guía generada por: plan_tecnico_placas_micros.md*
