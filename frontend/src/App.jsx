import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import StatsCards from './components/StatsCards';
import ImageAnalyzer from './components/ImageAnalyzer';
import EventsTable from './components/EventsTable';
import ModelsInfo from './components/ModelsInfo';
import { fetchHealth, fetchStats } from './services/api';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('analyzer');
  const [healthStatus, setHealthStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const loadInitialData = async () => {
    try {
      const health = await fetchHealth();
      setHealthStatus(health);

      const statsData = await fetchStats();
      setStats(statsData);
    } catch (err) {
      console.warn('API aún no disponible o fuera de línea:', err);
    }
  };

  useEffect(() => {
    loadInitialData();
    // Refresco periódico cada 15 segundos
    const interval = setInterval(loadInitialData, 15000);
    return () => clearInterval(interval);
  }, [refreshTrigger]);

  const handleDetectionSaved = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="app-layout">
      {/* Barra de navegación superior */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthStatus={healthStatus}
      />

      <main className="main-content">
        {/* Métricas destacadas siempre accesibles en el encabezado */}
        <section className="stats-section mb-6">
          <StatsCards stats={stats} />
        </section>

        {/* Contenido según pestaña activa */}
        <section className="tab-view-section">
          {activeTab === 'analyzer' && (
            <ImageAnalyzer onDetectionSaved={handleDetectionSaved} />
          )}

          {activeTab === 'events' && (
            <EventsTable refreshTrigger={refreshTrigger} />
          )}

          {activeTab === 'dashboard' && (
            <div className="dashboard-composite-view animate-fade-in">
              <EventsTable refreshTrigger={refreshTrigger} />
              <div className="mt-6">
                <ModelsInfo />
              </div>
            </div>
          )}

          {activeTab === 'models' && <ModelsInfo />}
        </section>
      </main>

      <footer className="app-footer text-muted text-sm">
        <div className="footer-content">
          <span>PlateVision AI · Prototipo de Visión Artificial para Seguridad Urbana</span>
          <span className="footer-dot">•</span>
          <span>YOLO26s (Micros) + YOLO26n (Placas) + EasyOCR + FastAPI + SQLite</span>
        </div>
      </footer>
    </div>
  );
}
