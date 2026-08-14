const BASE_URL = '/api'

async function request(path, options = {}) {
  // FormData bodies (photo upload) need the browser to set its own
  // multipart boundary in Content-Type -- must not force JSON on those.
  const isFormData = options.body instanceof FormData
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { ...(isFormData ? {} : { 'Content-Type': 'application/json' }), ...(options.headers || {}) },
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${options.method || 'GET'} ${path} failed (${res.status}): ${body}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  listFillups: () => request('/gas/fillups'),
  createFillup: (payload) => request('/gas/fillups', { method: 'POST', body: JSON.stringify(payload) }),
  updateFillup: (id, payload) => request(`/gas/fillups/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteFillup: (id) => request(`/gas/fillups/${id}`, { method: 'DELETE' }),
  scanOdometerPhoto: (file) => {
    const body = new FormData()
    body.append('photo', file)
    return request('/gas/fillups/scan-odometer', { method: 'POST', body })
  },

  listMaintenance: () => request('/maintenance/records'),
  createMaintenance: (payload) => request('/maintenance/records', { method: 'POST', body: JSON.stringify(payload) }),
  updateMaintenance: (id, payload) =>
    request(`/maintenance/records/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteMaintenance: (id) => request(`/maintenance/records/${id}`, { method: 'DELETE' }),

  dashboardSummary: () => request('/dashboard/summary'),
  mapRoutes: () => request('/map/routes'),
}
