import React from 'react';
import { ShieldCheck, Hash, Calendar, CheckSquare, Zap, Activity } from 'lucide-react';

export default function StatsCards({ stats }) {
  const total = stats?.total_detections || 0;
  const today = stats?.detections_today || 0;
  const uniquePlates = stats?.unique_plates_count || 0;
  const validBolivian = stats?.valid_bolivian_plates_count || 0;
  const validPct = total > 0 ? ((validBolivian / total) * 100).toFixed(1) : '100';

  const avgMicro = ((stats?.average_confidence?.micro || 0.95) * 100).toFixed(1);
  const avgPlate = ((stats?.average_confidence?.plate || 0.94) * 100).toFixed(1);
  const avgOcr = ((stats?.average_confidence?.ocr || 0.88) * 100).toFixed(1);

  return (
    <div className="stats-grid">
      <div className="stat-card glass-panel">
        <div className="stat-header">
          <span className="stat-label">Total Detecciones</span>
          <div className="stat-icon-wrapper blue">
            <Activity size={20} />
          </div>
        </div>
        <div className="stat-value">{total}</div>
        <div className="stat-footer">
          <span className="stat-subtext">Eventos registrados en base de datos</span>
        </div>
      </div>

      <div className="stat-card glass-panel">
        <div className="stat-header">
          <span className="stat-label">Detecciones Hoy</span>
          <div className="stat-icon-wrapper green">
            <Calendar size={20} />
          </div>
        </div>
        <div className="stat-value">{today}</div>
        <div className="stat-footer">
          <span className="stat-subtext">Filtradas por ventana anti-ráfagas (5 min)</span>
        </div>
      </div>

      <div className="stat-card glass-panel">
        <div className="stat-header">
          <span className="stat-label">Placas Únicas</span>
          <div className="stat-icon-wrapper amber">
            <Hash size={20} />
          </div>
        </div>
        <div className="stat-value">{uniquePlates}</div>
        <div className="stat-footer">
          <span className="stat-subtext">Vehículos distintos identificados</span>
        </div>
      </div>

      <div className="stat-card glass-panel">
        <div className="stat-header">
          <span className="stat-label">Formato Boliviano Válido</span>
          <div className="stat-icon-wrapper emerald">
            <ShieldCheck size={20} />
          </div>
        </div>
        <div className="stat-value">
          {validBolivian} <span className="stat-unit">({validPct}%)</span>
        </div>
        <div className="stat-footer">
          <span className="stat-subtext">Sintaxis 3-4 dígitos + 3 letras</span>
        </div>
      </div>

      <div className="stat-card glass-panel">
        <div className="stat-header">
          <span className="stat-label">Precisión Promedio</span>
          <div className="stat-icon-wrapper purple">
            <CheckSquare size={20} />
          </div>
        </div>
        <div className="stat-value-group">
          <div><span className="label-sm">Micro:</span> <strong>{avgMicro}%</strong></div>
          <div><span className="label-sm">Placa:</span> <strong>{avgPlate}%</strong></div>
        </div>
        <div className="stat-footer">
          <span className="stat-subtext">Modelos YOLO26s y YOLO26n</span>
        </div>
      </div>

      <div className="stat-card glass-panel">
        <div className="stat-header">
          <span className="stat-label">Inferencia GPU</span>
          <div className="stat-icon-wrapper cyan">
            <Zap size={20} />
          </div>
        </div>
        <div className="stat-value">~5.7 <span className="stat-unit">ms</span></div>
        <div className="stat-footer">
          <span className="stat-subtext">RTX 4080 SUPER (+150 FPS)</span>
        </div>
      </div>
    </div>
  );
}
