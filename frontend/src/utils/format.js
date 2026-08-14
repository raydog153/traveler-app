export function formatMiles(v) {
  return v != null ? Math.round(v).toLocaleString() : ''
}

export function formatMpg(v) {
  return v != null ? v.toFixed(1) : ''
}

export function formatGallons(v) {
  return v != null ? v.toFixed(2) : ''
}

export function formatCurrency(v, { decimals = 2 } = {}) {
  if (v == null) return ''
  return `$${v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`
}

export function formatDate(iso) {
  return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}
