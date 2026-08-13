// Shared date/value -> percent mappers for the hand-built dashboard charts
// (SVG/div based, not a charting library -- see components/dashboard/).
//
// Both mappers clamp to [0, 100]: callers (era bands, major-event markers,
// plot points) sometimes ask for a date/value that falls outside the
// min/max the chart's own axis was built from -- e.g. an era boundary date
// with no MPG points loaded on one side of it yet. Left unclamped, that
// produces negative `left`/`width` or values past 100% and renders off the
// edge of the chart instead of pinned to it.
const clampPct = (pct) => Math.max(0, Math.min(100, pct))

export function dateToPercent(date, minDate, maxDate) {
  const t = new Date(date).getTime()
  const min = new Date(minDate).getTime()
  const max = new Date(maxDate).getTime()
  if (max === min) return 0
  return clampPct(((t - min) / (max - min)) * 100)
}

// invert=true means the larger value maps to 0% (top of the plot), matching
// the design's "value increases upward" y-axis convention for CSS `top`.
export function valueToPercent(value, min, max, invert = true) {
  if (max === min) return 0
  const pct = ((value - min) / (max - min)) * 100
  return clampPct(invert ? 100 - pct : pct)
}
