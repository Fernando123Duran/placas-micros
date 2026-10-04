import React, { useState, useEffect } from 'react';
import { Search, Filter, RefreshCw, ExternalLink, Calendar, CheckCircle, AlertTriangle, Eye, X } from 'lucide-react';
import { fetchEvents } from '../services/api';

export default function EventsTable({ refreshTrigger }) {
  const [events, setEvents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchPlate, setSearchPlate] = useState('');
  const [onlyValid, setOnlyValid] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchEvents({
        page,
        limit: 15,
        plate: searchPlate,
        onlyValid: onlyValid ? true : null,
      });
      setEvents(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Error cargando eventos:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page, onlyValid, refreshTrigger]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const formatDate = (isoString) => {
    if (!isoString) return '--';
    const d = new Date(isoString);
    return d.toLocaleString('es-BO', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="events-view-container glass-panel animate-fade-in">
      <div className="events-toolbar">
        <div className="toolbar-left">
          <h3>Registro Histórico de Detecciones</h3>
          <span className="text-muted text-sm">{total} eventos encontrados en base de datos</span>
        </div>

        <div className="toolbar-right">
          <form onSubmit={handleSearchSubmit} className="search-box-form">
            <Search size={16} className="search-icon" />
            <input
              id="input-search-plate"
              type="text"
              placeholder="Buscar patente (ej. 1234ABC)..."
              value={searchPlate}
              onChange={(e) => setSearchPlate(e.target.value)}
              className="search-input"
            />
          </form>

          <button
            type="button"
            className={`btn-filter ${onlyValid ? 'active' : ''}`}
            onClick={() => {
              setOnlyValid(!onlyValid);
              setPage(1);
            }}
          >
            <Filter size={16} />
            <span>Solo Bolivianas Válidas</span>
          </button>

          <button
            id="btn-refresh-events"
            type="button"
            className="btn-secondary"
            onClick={loadData}
            title="Refrescar datos"
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      {/* Tabla de eventos */}
      <div className="table-responsive">
        <table className="events-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Fecha y Hora</th>
              <th>Patente Normalizada</th>
              <th>Sintaxis</th>
              <th>Conf. Micro</th>
              <th>Conf. Placa</th>
              <th>Conf. OCR</th>
              <th>Evidencias</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan="9" className="text-center py-6 text-muted">
                  {loading ? 'Cargando eventos...' : 'No se encontraron registros que coincidan con la búsqueda.'}
                </td>
              </tr>
            ) : (
              events.map((ev) => (
                <tr key={ev.id} className="event-row">
                  <td className="font-mono text-muted">#{ev.id}</td>
                  <td className="text-sm">
                    <div className="date-cell">
                      <Calendar size={14} className="text-muted" />
                      <span>{formatDate(ev.timestamp)}</span>
                    </div>
                  </td>
                  <td>
                    <div className="plate-badge-display sm">
                      {ev.plate_normalized}
                    </div>
                  </td>
                  <td>
                    {ev.is_valid_bolivian ? (
                      <span className="badge badge-valid">Válida</span>
                    ) : (
                      <span className="badge badge-invalid">No estándar</span>
                    )}
                  </td>
                  <td className="font-mono text-sm">{(ev.micro_confidence * 100).toFixed(1)}%</td>
                  <td className="font-mono text-sm">{(ev.plate_confidence * 100).toFixed(1)}%</td>
                  <td className="font-mono text-sm">{(ev.ocr_confidence * 100).toFixed(1)}%</td>
                  <td>
                    <div className="evidence-thumbs-row">
                      {ev.plate_image_url && (
                        <img
                          src={ev.plate_image_url}
                          alt="Placa"
                          className="table-thumb"
                          title="Recorte de Placa"
                        />
                      )}
                      {ev.micro_image_url && (
                        <img
                          src={ev.micro_image_url}
                          alt="Micro"
                          className="table-thumb"
                          title="Recorte de Micro"
                        />
                      )}
                    </div>
                  </td>
                  <td>
                    <button
                      className="btn-action-view"
                      onClick={() => setSelectedEvent(ev)}
                      title="Ver inspección completa"
                    >
                      <Eye size={16} />
                      <span>Inspeccionar</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      <div className="pagination-bar">
        <span className="text-muted text-sm">
          Página {page} de {Math.max(1, Math.ceil(total / 15))}
        </span>
        <div className="pagination-buttons">
          <button
            className="btn-secondary text-sm"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            Anterior
          </button>
          <button
            className="btn-secondary text-sm"
            disabled={page >= Math.ceil(total / 15)}
            onClick={() => setPage(page + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>

      {/* Modal de Inspección de Evidencias */}
      {selectedEvent && (
        <div className="modal-backdrop animate-fade-in" onClick={() => setSelectedEvent(null)}>
          <div className="modal-dialog glass-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <h3>Inspección de Detección #{selectedEvent.id}</h3>
                <span className="text-muted text-sm">{formatDate(selectedEvent.timestamp)}</span>
              </div>
              <button className="modal-close-btn" onClick={() => setSelectedEvent(null)}>
                <X size={20} />
              </button>
            </div>

            <div className="modal-body">
              <div className="modal-plate-banner">
                <div className="plate-badge-display lg">
                  {selectedEvent.plate_normalized}
                </div>
                <div className="modal-badges-row">
                  {selectedEvent.is_valid_bolivian ? (
                    <span className="badge badge-valid">Patente Boliviana Válida</span>
                  ) : (
                    <span className="badge badge-invalid">No Cumple Patrón Estándar</span>
                  )}
                  <span className="badge badge-micro">
                    Micro Conf: {(selectedEvent.micro_confidence * 100).toFixed(1)}%
                  </span>
                  <span className="badge badge-plate">
                    Placa Conf: {(selectedEvent.plate_confidence * 100).toFixed(1)}%
                  </span>
                  <span className="badge badge-plate">
                    OCR Conf: {(selectedEvent.ocr_confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              <div className="evidence-gallery-grid">
                {selectedEvent.plate_image_url && (
                  <div className="evidence-gallery-card">
                    <h4>1. Recorte de Placa</h4>
                    <div className="gallery-img-wrapper">
                      <img src={selectedEvent.plate_image_url} alt="Placa" />
                    </div>
                  </div>
                )}

                {selectedEvent.micro_image_url && (
                  <div className="evidence-gallery-card">
                    <h4>2. Recorte del Micro</h4>
                    <div className="gallery-img-wrapper">
                      <img src={selectedEvent.micro_image_url} alt="Micro" />
                    </div>
                  </div>
                )}

                {selectedEvent.full_image_url && (
                  <div className="evidence-gallery-card full-span">
                    <h4>3. Fotograma Panorámico Completo (1080p)</h4>
                    <div className="gallery-img-wrapper">
                      <img src={selectedEvent.full_image_url} alt="Full Frame" />
                    </div>
                  </div>
                )}
              </div>

              <div className="modal-details-grid">
                <div className="detail-item">
                  <span className="detail-label">Texto Bruto OCR:</span>
                  <span className="detail-val font-mono">{selectedEvent.plate_raw || '(vacío)'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Origen / Fuente:</span>
                  <span className="detail-val">{selectedEvent.source}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Bounding Box Micro:</span>
                  <span className="detail-val font-mono">{selectedEvent.micro_bbox}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Bounding Box Placa:</span>
                  <span className="detail-val font-mono">{selectedEvent.plate_bbox}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
