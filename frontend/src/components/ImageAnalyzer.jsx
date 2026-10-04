import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, CheckCircle2, AlertTriangle, Image as ImageIcon, Sparkles, RefreshCw, ZoomIn, ShieldCheck } from 'lucide-react';
import { uploadImageForDetection } from '../services/api';

export default function ImageAnalyzer({ onDetectionSaved }) {
  const [file, setFile] = useState(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [selectedPlate, setSelectedPlate] = useState(null);

  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const fileInputRef = useRef(null);

  // Muestra de imágenes de prueba rápidas
  const sampleTestImages = [
    { name: 'Micro con Placa 1', path: '/storage/full/sample1.jpg', desc: 'Micro en tránsito' },
  ];

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      processSelectedFile(selected);
    }
  };

  const processSelectedFile = (selectedFile) => {
    setFile(selectedFile);
    setError(null);
    setResult(null);
    setSelectedPlate(null);

    const objectUrl = URL.createObjectURL(selectedFile);
    setImagePreviewUrl(objectUrl);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);

    try {
      const data = await uploadImageForDetection(file);
      setResult(data);
      if (onDetectionSaved) onDetectionSaved();
    } catch (err) {
      setError(err.message || 'Error al procesar la imagen');
    } finally {
      setLoading(false);
    }
  };

  // Dibujar bounding boxes en el canvas cuando se reciben resultados
  useEffect(() => {
    if (!result || !canvasRef.current || !imageRef.current) return;

    const img = imageRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    const drawBoxes = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      result.detections.forEach((m, mIdx) => {
        // 1. Dibujar BBox del Micro (Azul Neón)
        const [mx1, my1, mx2, my2] = m.micro_bbox;
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = Math.max(3, Math.round(canvas.width / 400));
        ctx.strokeRect(mx1, my1, mx2 - mx1, my2 - my1);

        // Fondo y etiqueta del Micro
        const mLabel = `Micro #${mIdx + 1} (${(m.micro_confidence * 100).toFixed(0)}%)`;
        ctx.font = `bold ${Math.max(16, Math.round(canvas.width / 60))}px 'Outfit', sans-serif`;
        const textWidth = ctx.measureText(mLabel).width;
        ctx.fillStyle = '#0284c7';
        ctx.fillRect(mx1, Math.max(0, my1 - 28), textWidth + 14, 28);
        ctx.fillStyle = '#ffffff';
        ctx.fillText(mLabel, mx1 + 7, Math.max(20, my1 - 8));

        // 2. Dibujar BBox de las Placas (Verde Neón)
        m.plates.forEach((p, pIdx) => {
          const [px1, py1, px2, py2] = p.plate_bbox_full;
          ctx.strokeStyle = '#10b981';
          ctx.lineWidth = Math.max(4, Math.round(canvas.width / 350));
          ctx.strokeRect(px1, py1, px2 - px1, py2 - py1);

          // Etiqueta de la placa
          const pLabel = p.plate_normalized ? `PLACA: ${p.plate_normalized}` : 'PLACA DETECTADA';
          ctx.font = `bold ${Math.max(14, Math.round(canvas.width / 70))}px 'JetBrains Mono', monospace`;
          const pWidth = ctx.measureText(pLabel).width;
          ctx.fillStyle = '#059669';
          ctx.fillRect(px1, Math.max(0, py1 - 24), pWidth + 12, 24);
          ctx.fillStyle = '#ffffff';
          ctx.fillText(pLabel, px1 + 6, Math.max(18, py1 - 7));
        });
      });
    };

    if (img.complete) {
      drawBoxes();
    } else {
      img.onload = drawBoxes;
    }
  }, [result]);

  return (
    <div className="analyzer-container animate-fade-in">
      <div className="analyzer-grid">
        {/* Panel izquierdo: Visualizador / Upload */}
        <div className="viewport-panel glass-panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <ImageIcon size={20} className="text-primary" />
              <h3>Área de Inferencia Visual</h3>
            </div>
            {result && (
              <div className="inference-summary-badges">
                <span className="badge badge-micro">
                  {result.total_micros_detected} Micro(s)
                </span>
                <span className="badge badge-plate">
                  {result.total_plates_detected} Placa(s)
                </span>
              </div>
            )}
          </div>

          <div
            className={`dropzone ${!imagePreviewUrl ? 'empty' : 'loaded'}`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => !imagePreviewUrl && fileInputRef.current.click()}
          >
            <input
              ref={fileInputRef}
              id="file-input-upload"
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />

            {!imagePreviewUrl ? (
              <div className="dropzone-prompt">
                <div className="upload-icon-pulse">
                  <UploadCloud size={48} />
                </div>
                <h4>Arrastra y suelta una imagen aquí</h4>
                <p>O haz clic para seleccionar una foto de tu cámara de seguridad</p>
                <button
                  type="button"
                  className="btn-secondary mt-3"
                  onClick={() => fileInputRef.current.click()}
                >
                  Examinar Archivos
                </button>
              </div>
            ) : (
              <div className="image-stage-wrapper">
                <img
                  ref={imageRef}
                  src={imagePreviewUrl}
                  alt="Vista previa"
                  className="preview-image"
                />
                <canvas ref={canvasRef} className="detection-canvas-overlay" />
              </div>
            )}
          </div>

          {imagePreviewUrl && (
            <div className="viewport-actions">
              <button
                id="btn-trigger-analyze"
                className="btn-primary"
                onClick={handleAnalyze}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <RefreshCw size={18} className="spin" />
                    <span>Procesando (YOLO26 + EasyOCR)...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={18} />
                    <span>Ejecutar Pipeline de Detección</span>
                  </>
                )}
              </button>

              <button
                className="btn-secondary"
                onClick={() => {
                  setFile(null);
                  setImagePreviewUrl(null);
                  setResult(null);
                }}
              >
                Cambiar Imagen
              </button>
            </div>
          )}

          {error && (
            <div className="alert-box alert-error mt-4">
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Panel derecho: Resultados Detallados de Reconocimiento */}
        <div className="results-panel glass-panel">
          <div className="panel-header">
            <h3>Lecturas de Placas & Recortes</h3>
            <span className="text-muted text-sm">
              {result ? `${result.new_records_saved} nuevo(s) registrado(s)` : 'Esperando análisis'}
            </span>
          </div>

          {!result ? (
            <div className="results-placeholder">
              <div className="placeholder-icon">🔍</div>
              <h4>Sin análisis activo</h4>
              <p>
                Carga una imagen y pulsa <strong>"Ejecutar Pipeline"</strong> para visualizar los recortes de micros y la extracción OCR de las patentes.
              </p>
            </div>
          ) : result.detections.length === 0 ? (
            <div className="results-placeholder">
              <h4>No se detectaron micros</h4>
              <p>No se encontraron micros de transporte público en esta toma con la confianza mínima requerida.</p>
            </div>
          ) : (
            <div className="detection-cards-list">
              {result.detections.map((m, mIdx) => (
                <div key={mIdx} className="micro-result-card">
                  <div className="micro-card-top">
                    <div className="micro-header-info">
                      <span className="badge badge-micro">Micro #{mIdx + 1}</span>
                      <span className="conf-text">
                        Confianza: <strong>{(m.micro_confidence * 100).toFixed(1)}%</strong>
                      </span>
                    </div>
                  </div>

                  {m.plates.length === 0 ? (
                    <div className="no-plate-note">
                      <span>⚠️ No se detectó placa legible dentro de este micro.</span>
                    </div>
                  ) : (
                    <div className="plates-inside-list">
                      {m.plates.map((p, pIdx) => (
                        <div key={pIdx} className="plate-card-item">
                          <div className="plate-card-left">
                            <div className="plate-badge-display">
                              {p.plate_normalized || p.plate_raw || '------'}
                            </div>

                            <div className="plate-meta-row mt-2">
                              {p.is_valid_bolivian ? (
                                <span className="badge badge-valid">
                                  <ShieldCheck size={12} />
                                  Bolivia Válida
                                </span>
                              ) : (
                                <span className="badge badge-invalid">
                                  No Estándar
                                </span>
                              )}

                              {p.saved_to_db ? (
                                <span className="badge badge-valid">
                                  Registrado en BD
                                </span>
                              ) : p.is_duplicate ? (
                                <span className="badge badge-invalid">
                                  Duplicado (Ventana 5m)
                                </span>
                              ) : (
                                <span className="badge badge-invalid">
                                  No Registrado
                                </span>
                              )}
                            </div>

                            <div className="confidence-bars mt-2">
                              <div className="conf-bar-item">
                                <div className="conf-bar-label">
                                  <span>Detector Placa:</span>
                                  <span>{(p.plate_confidence * 100).toFixed(1)}%</span>
                                </div>
                                <div className="bar-track">
                                  <div
                                    className="bar-fill plate"
                                    style={{ width: `${p.plate_confidence * 100}%` }}
                                  ></div>
                                </div>
                              </div>

                              <div className="conf-bar-item mt-1">
                                <div className="conf-bar-label">
                                  <span>EasyOCR:</span>
                                  <span>{(p.ocr_confidence * 100).toFixed(1)}%</span>
                                </div>
                                <div className="bar-track">
                                  <div
                                    className="bar-fill ocr"
                                    style={{ width: `${p.ocr_confidence * 100}%` }}
                                  ></div>
                                </div>
                              </div>
                            </div>

                            <div className="text-muted text-xs mt-2">
                              Texto OCR bruto: <code className="code-inline">{p.plate_raw || 'vacío'}</code>
                            </div>
                          </div>

                          {p.evidence_plate_url && (
                            <div className="plate-thumbnail-box">
                              <img
                                src={p.evidence_plate_url}
                                alt="Recorte de placa"
                                className="plate-thumb-img"
                              />
                              <span className="thumb-caption">Recorte Placa</span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
