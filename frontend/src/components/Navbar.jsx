import React from 'react';
import { Bus, Camera, History, BarChart3, Cpu, CheckCircle2, AlertCircle } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, healthStatus }) {
  const isOnline = healthStatus?.status === 'healthy';

  return (
    <header className="navbar-container glass-panel">
      <div className="navbar-brand">
        <div className="brand-logo-icon">
          <Bus className="icon-bus" size={24} />
          <div className="icon-badge-dot"></div>
        </div>
        <div className="brand-texts">
          <div className="brand-title">
            <span>PlateVision</span>
            <span className="brand-ai-tag">AI</span>
          </div>
          <span className="brand-subtitle">Detección de Micros & Placas Bolivianas</span>
        </div>
      </div>

      <nav className="navbar-nav">
        <button
          id="nav-tab-analyzer"
          className={`nav-tab-btn ${activeTab === 'analyzer' ? 'active' : ''}`}
          onClick={() => setActiveTab('analyzer')}
        >
          <Camera size={18} />
          <span>Subir & Analizar</span>
        </button>

        <button
          id="nav-tab-events"
          className={`nav-tab-btn ${activeTab === 'events' ? 'active' : ''}`}
          onClick={() => setActiveTab('events')}
        >
          <History size={18} />
          <span>Historial de Eventos</span>
        </button>

        <button
          id="nav-tab-dashboard"
          className={`nav-tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <BarChart3 size={18} />
          <span>Métricas & Stats</span>
        </button>

        <button
          id="nav-tab-models"
          className={`nav-tab-btn ${activeTab === 'models' ? 'active' : ''}`}
          onClick={() => setActiveTab('models')}
        >
          <Cpu size={18} />
          <span>Modelos & Stack</span>
        </button>
      </nav>

      <div className="navbar-status">
        <div className={`status-pill ${isOnline ? 'online' : 'offline'}`}>
          <div className="status-ping"></div>
          {isOnline ? (
            <>
              <CheckCircle2 size={14} className="status-icon" />
              <span>Backend Online {healthStatus?.gpu_available ? '(GPU)' : ''}</span>
            </>
          ) : (
            <>
              <AlertCircle size={14} className="status-icon" />
              <span>Backend Offline</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
