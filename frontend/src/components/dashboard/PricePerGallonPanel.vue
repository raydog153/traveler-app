<template>
  <div class="panel small-chart">
    <div class="head-row">
      <div>
        <h2>Price paid per gallon</h2>
        <p class="desc">Every fill-up, {{ yearRange }}</p>
      </div>
      <div class="head-stat">
        <div class="value">{{ formatCurrency(avgPrice) }}</div>
        <div class="sub">lifetime average</div>
      </div>
    </div>

    <div class="plot-wrap">
      <div class="y-axis">
        <span v-for="t in yTicks" :key="t" class="mono">${{ t }}</span>
      </div>
      <div class="plot">
        <div v-for="g in [0, 50, 100]" :key="g" class="gridline" :style="{ top: g + '%' }" />
        <svg class="line-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
          <polyline
            v-if="smoothedPoints"
            :points="smoothedPoints"
            fill="none"
            stroke="var(--rust)"
            stroke-width="1"
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
import { formatCurrency, formatDate, formatGallons } from '../../utils/format'

const props = defineProps({
  series: { type: Array, required: true },
})

const Y_MIN = 2.8
const Y_MAX = 6.2
const yTicks = [6, 5, 4, 3]

const minDate = computed(() =>
  props.series.length ? props.series.map((p) => p.x).reduce((a, b) => (a < b ? a : b)) : new Date().toISOString(),
)
const maxDate = computed(() =>
  props.series.length ? props.series.map((p) => p.x).reduce((a, b) => (a > b ? a : b)) : new Date().toISOString(),
)

const yearRange = computed(() => {
  if (!props.series.length) return ''
  const a = new Date(minDate.value).getFullYear()
  const b = new Date(maxDate.value).getFullYear()
  return a === b ? `${a}` : `${a}–${b}`
})

const avgPrice = computed(() => {
  if (!props.series.length) return 0
  return props.series.reduce((s, p) => s + p.y, 0) / props.series.length
})

function toPlotPoint(p) {
  return {
    x: p.x,
    y: p.y,
    gallons: p.gallons,
    xPct: dateToPercent(p.x, minDate.value, maxDate.value),
    yPct: valueToPercent(p.y, Y_MIN, Y_MAX, true),
  }
}

const dots = computed(() => props.series.map(toPlotPoint))

// Simple windowed average for the smoothed line -- same shape as
// analytics.rolling_avg, computed client-side so this panel doesn't need a
// dedicated backend series.
const smoothedPoints = computed(() => {
  if (!props.series.length) return ''
  const window = 7
  const ys = props.series.map((p) => p.y)
  return props.series
    .map((p, i) => {
      const start = Math.max(0, i - window + 1)
      const slice = ys.slice(start, i + 1)
      const avg = slice.reduce((s, v) => s + v, 0) / slice.length
      const pt = toPlotPoint({ x: p.x, y: avg })
      return `${pt.xPct},${pt.yPct}`
    })
    .join(' ')
})

// See MpgCentrepiece.vue for why this is a custom hover/click tooltip rather
// than a native `title` attribute.
const tooltip = ref(null)

function anchorPosition(el) {
  const rect = el.getBoundingClientRect()
  return { x: rect.left + rect.width / 2, y: rect.top }
}

function pointTooltip(p) {
  return {
    key: `pt-${p.x}`,
    title: formatDate(p.x),
    subtitle: `${formatCurrency(p.y)}/gal — ${formatGallons(p.gallons)} gal`,
  }
}

function onDotEnter(e, p) {
  if (tooltip.value?.pinned) return
  tooltip.value = { ...anchorPosition(e.currentTarget), ...pointTooltip(p), pinned: false }
}

function onLeave() {
  if (!tooltip.value?.pinned) tooltip.value = null
}

function onDotClick(e, p) {
  const data = pointTooltip(p)
  if (tooltip.value?.pinned && tooltip.value.key === data.key) {
    tooltip.value = null
    return
  }
  tooltip.value = { ...anchorPosition(e.currentTarget), ...data, pinned: true }
}

function closeTooltip() {
  tooltip.value = null
}

function onDocumentPointerDown(e) {
  if (tooltip.value?.pinned && !e.target.closest('.dot, .chart-tooltip')) closeTooltip()
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
.small-chart {
  padding: 18px 20px 16px;
  margin-bottom: 0;
}
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}
h2 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 2px;
}
.desc {
  font-size: 11.5px;
  color: var(--text-muted);
  margin: 0;
}
.head-stat {
  text-align: right;
}
.head-stat .value {
  font-size: 19px;
  font-weight: 600;
}
.head-stat .sub {
  font-size: 10.5px;
  color: var(--text-muted);
}
.plot-wrap {
  position: relative;
  padding-left: 26px;
}
.y-axis {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
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
  height: 172px;
  overflow: hidden;
}
.gridline {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--gridline);
}
.line-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.dot {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: oklch(0.75 0.06 35);
  opacity: 0.7;
  transform: translate(-50%, -50%);
  cursor: pointer;
}
.dot:hover {
  opacity: 1;
  width: 6px;
  height: 6px;
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
