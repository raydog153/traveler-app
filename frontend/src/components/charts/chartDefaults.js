export const GRID_COLOR = '#1c2733'

export const baseChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
}

export const legendBoxWidth12 = { labels: { boxWidth: 12 } }

export function timeScale(extra = {}) {
  return { type: 'time', time: { unit: 'quarter' }, grid: { color: GRID_COLOR }, ...extra }
}

export function linearScale(extra = {}) {
  return { grid: { color: GRID_COLOR }, ...extra }
}
