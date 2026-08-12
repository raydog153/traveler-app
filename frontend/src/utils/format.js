export function formatMiles(v) {
  return v != null ? Math.round(v).toLocaleString() : ''
}

export function formatMpg(v) {
  return v != null ? v.toFixed(1) : ''
}

export function formatCurrency(v, { decimals = 2 } = {}) {
  if (v == null) return ''
  return `$${v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`
}
