// Shared color tokens for contexts that can't read CSS custom properties
// (Chart/canvas drawing, Leaflet paint options, Google Maps style arrays).
// Keep in sync with the `:root` block in style.css.

export const ACCENT = '#1f6feb'
export const ACCENT_HOVER = 'oklch(0.5 0.16 258)'
export const ACCENT_TINT = 'oklch(0.96 0.025 258)'

export const RUST = 'oklch(0.63 0.17 35)'
export const RUST_TINT = 'oklch(0.96 0.03 35)'
export const SEVERE_RED = 'oklch(0.58 0.19 27)'

export const GREEN = 'oklch(0.62 0.13 155)'
export const GREEN_TINT = 'oklch(0.96 0.03 155)'

export const AMBER_TEXT = 'oklch(0.55 0.12 65)'
export const AMBER_TINT = 'oklch(0.96 0.03 75)'

export const TEXT_PRIMARY = 'oklch(0.24 0.012 255)'
export const TEXT_MUTED = 'oklch(0.55 0.012 255)'
export const GRIDLINE = 'oklch(0.955 0.004 255)'

// Map/route year coloring: oklch(0.6 0.14 H) cycling through these hues.
export const YEAR_HUES = [258, 232, 196, 160, 88, 48]

export function yearColor(index) {
  return `oklch(0.6 0.14 ${YEAR_HUES[index % YEAR_HUES.length]})`
}

// Hex equivalents for contexts that reject oklch() (Google Maps style
// arrays require hex/rgb strings, not CSS color functions).
export const HEX = {
  pageBg: '#f7f8fb',
  surface: '#ffffff',
  text: '#33363e',
  textMuted: '#8a8f9c',
  road: '#e7e9ee',
  roadArterial: '#eef0f4',
  roadHighway: '#f3d9c8',
  water: '#dce6f0',
  parkFill: '#e3ecdf',
  adminStroke: '#d7dae1',
  accent: '#1f6feb',
}
