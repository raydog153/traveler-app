const BASE_URL = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
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

  listMaintenance: () => request('/maintenance/records'),
  createMaintenance: (payload) =>
    request('/maintenance/records', { method: 'POST', body: JSON.stringify(payload) }),

  dashboardSummary: () => request('/dashboard/summary'),
  mapRoutes: () => request('/map/routes'),
}
