import React from 'react';
import { Cpu, Award, Zap, Layers, FileText, CheckCircle2, ShieldAlert } from 'lucide-react';

export default function ModelsInfo() {
  return (
    <div className="models-info-container animate-fade-in">
      <div className="models-banner glass-panel">
        <div className="banner-left">
          <Award size={36} className="text-warning" />
          <div>
            <h3>Arquitectura en Cascada & Modelos Entrenados</h3>
            <p>
              Ambos detectores fueron entrenados con la GPU RTX 4080 SUPER y alcanzaron más del <strong>98.5% mAP@50</strong> en el conjunto de prueba independiente.
            </p>
          </div>
        </div>
        <div className="banner-badge">
          <span className="badge badge-valid">Experimento 1 Concluido</span>
        </div>
      </div>

      <div className="models-grid">
        {/* Card Modelo 1 */}
        <div className="model-spec-card glass-panel">
          <div className="model-card-header">
            <div className="model-title-row">
              <span className="model-tag blue">Modelo 1</span>
              <h4>Detector de Micros</h4>
            </div>
            <span className="badge badge-micro">YOLO26s</span>
          </div>

          <div className="metrics-highlights">
            <div className="highlight-item">
              <span className="highlight-num text-cyan">98.9%</span>
              <span className="highlight-label">mAP@50 (Test)</span>
            </div>
            <div className="highlight-item">
              <span className="highlight-num text-emerald">98.6%</span>
              <span className="highlight-label">Precisión</span>
            </div>
            <div className="highlight-item">
              <span className="highlight-num text-amber">~3.6 ms</span>
              <span className="highlight-label">Inferencia</span>
            </div>
          </div>

          <div className="model-specs-list">
            <div className="spec-row">
              <span>Pesos:</span>
              <code className="code-inline">models/micro_detector_v1.pt</code>
            </div>
            <div className="spec-row">
              <span>Resolución Entrada:</span>
              <strong>640 × 640 px</strong>
            </div>
            <div className="spec-row">
              <span>Parámetros:</span>
              <strong>9.47M (20.8 GFLOPs)</strong>
            </div>
            <div className="spec-row">
              <span>Dataset de Validación:</span>
              <strong>75 val / 134 test</strong>
            </div>
            <div className="spec-row">
              <span>Función:</span>
              <span>Localiza vehículos de transporte público en el frame panorámico.</span>
            </div>
          </div>
        </div>

        {/* Card Modelo 2 */}
        <div className="model-spec-card glass-panel">
          <div className="model-card-header">
            <div className="model-title-row">
              <span className="model-tag green">Modelo 2</span>
              <h4>Detector de Placas</h4>
            </div>
            <span className="badge badge-plate">YOLO26n</span>
          </div>

          <div className="metrics-highlights">
            <div className="highlight-item">
              <span className="highlight-num text-emerald">98.6%</span>
              <span className="highlight-label">mAP@50 (Test)</span>
            </div>
            <div className="highlight-item">
              <span className="highlight-num text-cyan">94.3%</span>
              <span className="highlight-label">Recall</span>
            </div>
            <div className="highlight-item">
              <span className="highlight-num text-amber">~2.1 ms</span>
              <span className="highlight-label">Inferencia</span>
            </div>
          </div>

          <div className="model-specs-list">
            <div className="spec-row">
              <span>Pesos:</span>
              <code className="code-inline">models/plate_detector_v1.pt</code>
            </div>
            <div className="spec-row">
              <span>Resolución Entrada:</span>
              <strong>640 × 640 px (sobre crop)</strong>
            </div>
            <div className="spec-row">
              <span>Parámetros:</span>
              <strong>2.38M (5.3 GFLOPs)</strong>
            </div>
            <div className="spec-row">
              <span>Dataset de Validación:</span>
              <strong>37 val / 91 test</strong>
            </div>
            <div className="spec-row">
              <span>Función:</span>
              <span>Detecta la patente exclusivamente dentro del micro (cero falsos positivos de otros autos).</span>
            </div>
          </div>
        </div>

        {/* Card OCR & Pipeline */}
        <div className="model-spec-card glass-panel full-col">
          <div className="model-card-header">
            <div className="model-title-row">
              <span className="model-tag purple">Módulos Auxiliares</span>
              <h4>OCR, Tracking & Anti-ráfagas</h4>
            </div>
            <span className="badge badge-valid">Producción Activa</span>
          </div>

          <div className="pipeline-steps-visual">
            <div className="pipe-node">
              <div className="node-icon blue">1</div>
              <div className="node-content">
                <strong>Frame 1080p</strong>
                <span>Cámara de seguridad</span>
              </div>
            </div>

            <div className="pipe-arrow">→</div>

            <div className="pipe-node">
              <div className="node-icon cyan">2</div>
              <div className="node-content">
                <strong>YOLO26s Micro</strong>
                <span>Filtra solo transporte público</span>
              </div>
            </div>

            <div className="pipe-arrow">→</div>

            <div className="pipe-node">
              <div className="node-icon green">3</div>
              <div className="node-content">
                <strong>YOLO26n Placa</strong>
                <span>Recorte ROI + padding 5%</span>
              </div>
            </div>

            <div className="pipe-arrow">→</div>

            <div className="pipe-node">
              <div className="node-icon amber">4</div>
              <div className="node-content">
                <strong>CLAHE + EasyOCR</strong>
                <span>Extracción de caracteres</span>
              </div>
            </div>

            <div className="pipe-arrow">→</div>

            <div className="pipe-node">
              <div className="node-icon emerald">5</div>
              <div className="node-content">
                <strong>Anti-Duplicados</strong>
                <span>Ventana 5 min en SQLite</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
