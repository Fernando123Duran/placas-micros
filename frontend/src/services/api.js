/**
 * Servicio de conexión con la API de FastAPI
 */

const API_BASE = '/api/v1';

export async function fetchHealth() {
  try {
    const res = await fetch('/health');
    return await res.json();
  } catch (err) {
    return { status: 'offline', gpu_available: false };
  }
}

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/detections/stats`);
  if (!res.ok) throw new Error('Error al obtener estadísticas');
  return await res.json();
}

export async function fetchEvents({ page = 1, limit = 20, plate = '', onlyValid = null } = {}) {
  const params = new URLSearchParams({ page, limit });
  if (plate) params.append('plate', plate);
  if (onlyValid !== null) params.append('only_valid_bolivian', onlyValid);

  const res = await fetch(`${API_BASE}/detections/events?${params.toString()}`);
  if (!res.ok) throw new Error('Error al cargar eventos');
  return await res.json();
}

export async function fetchEventDetail(eventId) {
  const res = await fetch(`${API_BASE}/detections/events/${eventId}`);
  if (!res.ok) throw new Error('Error al cargar detalle del evento');
  return await res.json();
}

export async function uploadImageForDetection(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/detections/image`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Error al procesar la imagen');
  }

  return await res.json();
}
