<template>
  <div class="panel centrepiece">
    <div class="head-row">
      <div class="head-text">
        <h2>Fuel economy over time</h2>
        <p class="desc">
          MPG per fill-up with a 7-fill-up rolling average.<template v-if="showMaintenance">
            Vertical markers are maintenance events — red $2k+, yellow under.</template
          >
        </p>
      </div>
    </div>

    <div class="plot-wrap">
      <div class="y-axis">
        <span v-for="t in Y_TICKS" :key="t" class="mono">{{ t }}</span>
      </div>
      <div class="plot">
        <div v-for="g in [0, 25, 50, 75]" :key="g" class="gridline" :style="{ top: g + '%' }" />

        <div
          v-for="ev in markers"
          :key="ev.date + ev.label"
          class="maint-rule"
          :class="{ major: ev.is_major }"
          :style="{ left: ev.xPct + '%' }"
          @mouseenter="onMarkerEnter($event, ev)"
          @mouseleave="onLeave"
          @click="onMarkerClick($event, ev)"
        >
          <span v-if="ev.is_major" class="maint-label mono" :class="{ row2: ev.labelRow2 }">{{ ev.tag }}</span>
        </div>

        <svg class="line-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
          <polyline
            v-if="avgLinePoints"
            :points="avgLinePoints"
            fill="none"
            stroke="var(--ac)"
            stroke-width="1.2"
            vector-effect="non-scaling-stroke"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>

        <div
          v-for="p in dots"
          :key="p.x"
          class="dot"
          :style="{ left: p.xPct + '%', top: p.yPct + '%' }"
          @mouseenter="onDotEnter($event, p)"
          @mouseleave="onLeave"
          @click="onDotClick($event, p)"
        />
      </div>
      <div class="x-axis">
        <span v-for="y in xTickYears" :key="y.year" class="mono" :style="{ left: y.xPct + '%' }">{{ y.year }}</span>
      </div>
    </div>

    <div
      v-if="tooltip"
      class="chart-tooltip"
      :class="{ pinned: tooltip.pinned }"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <div class="tooltip-title">{{ tooltip.title }}</div>
      <div class="tooltip-subtitle">{{ tooltip.subtitle }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { dateToPercent, valueToPercent } from '../../utils/chartScale'
import { formatCurrency, formatDate, formatMpg } from '../../utils/format'

const props = defineProps({
  points: { type: Array, required: true },
  rollingAvg: { type: Array, required: true },
  maintenanceEvents: { type: Array, required: true },
  showMaintenance: { type: Boolean, default: true },
})

const Y_TICKS = [18, 14, 10, 6, 2]
const Y_MIN = 2
const Y_MAX = 18

const allDates = computed(() => {
  const dates = props.points.map((p) => p.x)
  return dates.length ? dates : [new Date().toISOString().slice(0, 10)]
})
const minDate = computed(() => allDates.value.reduce((a, b) => (a < b ? a : b)))
const maxDate = computed(() => allDates.value.reduce((a, b) => (a > b ? a : b)))

function toPlotPoint(p) {
  return {
    x: p.x,
    y: p.y,
    xPct: dateToPercent(p.x, minDate.value, maxDate.value),
    yPct: valueToPercent(p.y, Y_MIN, Y_MAX, true),
  }
}

const dots = computed(() => props.points.map(toPlotPoint))

const avgLinePoints = computed(() => {
  if (!props.rollingAvg.length) return ''
  return props.rollingAvg
    .map((p) => toPlotPoint(p))
    .map((p) => `${p.xPct},${p.yPct}`)
    .join(' ')
})

const markers = computed(() => {
  if (!props.showMaintenance) return []
  let majorCount = 0
  return props.maintenanceEvents.map((ev) => {
    const labelRow2 = ev.is_major && majorCount++ % 2 === 1
    return {
      ...ev,
      xPct: dateToPercent(ev.date, minDate.value, maxDate.value),
      tag: `$${Math.round(ev.cost / 1000)}k`,
      labelRow2,
    }
  })
})

const xTickYears = computed(() => {
  const startYear = new Date(minDate.value).getFullYear()
  const endYear = new Date(maxDate.value).getFullYear()
  const years = []
  for (let y = startYear; y <= endYear; y++) {
    years.push({ year: y, xPct: dateToPercent(`${y}-01-01`, minDate.value, maxDate.value) })
  }
  return years
})

// Custom tooltip: a native `title` attribute has a ~1s OS-level delay before
// it appears and can't be styled, so hover/click are tracked here instead.
// Position is captured from the anchor element's own bounding rect (not the
// mouse cursor) so it stays put over small 6px dots. `pinned` (set by click)
// keeps the tooltip open after the pointer leaves -- otherwise there'd be no
// way to read it on a touch device, and the ask was for a click to do
// *something*.
const tooltip = ref(null)

function anchorPosition(el) {
  const rect = el.getBoundingClientRect()
  return { x: rect.left + rect.width / 2, y: rect.top }
}

function pointTooltip(p) {
  return { key: `pt-${p.x}`, title: formatDate(p.x), subtitle: `${formatMpg(p.y)} mpg` }
}

function markerTooltip(ev) {
  return {
    key: `mk-${ev.date}-${ev.label}`,
    title: ev.label,
    subtitle: `${formatCurrency(ev.cost, { decimals: 0 })} — ${formatDate(ev.date)}`,
  }
}

function onDotEnter(e, p) {
  if (tooltip.value?.pinned) return
  tooltip.value = { ...anchorPosition(e.currentTarget), ...pointTooltip(p), pinned: false }
}

function onMarkerEnter(e, ev) {
  if (tooltip.value?.pinned) return
  tooltip.value = { ...anchorPosition(e.currentTarget), ...markerTooltip(ev), pinned: false }
}

function onLeave() {
  if (!tooltip.value?.pinned) tooltip.value = null
}

function togglePinned(el, data) {
  if (tooltip.value?.pinned && tooltip.value.key === data.key) {
    tooltip.value = null
    return
  }
  tooltip.value = { ...anchorPosition(el), ...data, pinned: true }
}

function onDotClick(e, p) {
  togglePinned(e.currentTarget, pointTooltip(p))
}

function onMarkerClick(e, ev) {
  togglePinned(e.currentTarget, markerTooltip(ev))
}

function closeTooltip() {
  tooltip.value = null
}

function onDocumentPointerDown(e) {
  if (tooltip.value?.pinned && !e.target.closest('.dot, .maint-rule, .chart-tooltip')) closeTooltip()
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
  window.addEventListener('scroll', closeTooltip, true)
  window.addEventListener('resize', closeTooltip)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  window.removeEventListener('scroll', closeTooltip, true)
  window.removeEventListener('resize', closeTooltip)
})
</script>

<style scoped>
.centrepiece {
  padding: 20px 24px 20px;
  margin-bottom: 0;
}
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
h2 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 4px;
}
.desc {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
  max-width: 46ch;
}
.plot-wrap {
  position: relative;
  padding-left: 26px;
}
.y-axis {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 22px;
  width: 26px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: 10px;
  color: oklch(0.65 0.012 255);
  text-align: right;
  padding-right: 6px;
}
.plot {
  position: relative;
  height: 286px;
  border-bottom: 1px solid oklch(0.9 0.005 255);
  overflow: hidden;
}
.gridline {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--gridline);
}
.maint-rule {
  /* Wider than the visible line it draws (via ::before) -- a hit target
     just 1-2px wide is nearly impossible to hover/click precisely. */
  position: absolute;
  top: 0;
  bottom: 0;
  width: 10px;
  transform: translateX(-50%);
  cursor: pointer;
}
.maint-rule::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 1px;
  transform: translateX(-50%);
  background: oklch(0.8 0.16 95);
}
.maint-rule.major::before {
  width: 2px;
  background: var(--severe-red);
}
.maint-label {
  position: absolute;
  top: 30px;
  left: 50%;
  transform: translateX(2px);
  font-size: 10.5px;
  font-weight: 600;
  color: var(--severe-red);
  white-space: nowrap;
}
.maint-label.row2 {
  top: 46px;
}
.line-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  /* Purely decorative -- without this its full transparent bounding box
     (not just the stroke) sits on top of the maint-rule markers in DOM
     order and silently swallows their hover/click events. */
  pointer-events: none;
}
.dot {
  position: absolute;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  width: 6px;
  height: 6px;
  background: var(--ac);
  opacity: 0.42;
  cursor: pointer;
}
.dot:hover {
  opacity: 1;
  width: 8px;
  height: 8px;
}
.x-axis {
  position: relative;
  height: 22px;
  margin-left: 36px;
}
.x-axis span {
  position: absolute;
  font-size: 10.5px;
  color: oklch(0.65 0.012 255);
  transform: translateX(-50%);
  top: 4px;
}
.chart-tooltip {
  position: fixed;
  z-index: 50;
  transform: translate(-50%, calc(-100% - 10px));
  pointer-events: none;
  background: var(--surface);
  border: 1px solid var(--card-border);
  border-radius: 8px;
  box-shadow: var(--shadow-overlay);
  padding: 7px 10px;
  max-width: 220px;
}
.chart-tooltip.pinned {
  pointer-events: auto;
}
.chart-tooltip::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 100%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: var(--surface);
  filter: drop-shadow(0 1px 0 var(--card-border));
}
.tooltip-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}
.tooltip-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
  white-space: nowrap;
}
</style>
