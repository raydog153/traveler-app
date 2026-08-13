<template>
  <div class="panel centrepiece">
    <div class="head-row">
      <div class="head-text">
        <h2>Fuel economy over time</h2>
        <p class="desc">
          MPG per fill-up with a 7-fill-up rolling average.<template v-if="showMaintenance">
            Vertical markers are maintenance events over $10k.</template
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
          :class="{ severe: ev.severe }"
          :style="{ left: ev.xPct + '%' }"
        >
          <span v-if="ev.severe" class="maint-label mono">{{ ev.tag }}</span>
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

        <div v-for="p in dots" :key="p.x" class="dot" :style="{ left: p.xPct + '%', top: p.yPct + '%' }" />
      </div>
      <div class="x-axis">
        <span v-for="y in xTickYears" :key="y.year" class="mono" :style="{ left: y.xPct + '%' }">{{ y.year }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { dateToPercent, valueToPercent } from '../../utils/chartScale'

const props = defineProps({
  points: { type: Array, required: true },
  rollingAvg: { type: Array, required: true },
  majorEvents: { type: Array, required: true },
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

const markers = computed(() =>
  props.showMaintenance
    ? props.majorEvents.map((ev) => ({
        ...ev,
        xPct: dateToPercent(ev.date, minDate.value, maxDate.value),
        severe: ev.cost >= 10000,
        tag: `$${Math.round(ev.cost / 1000)}k`,
      }))
    : [],
)

const xTickYears = computed(() => {
  const startYear = new Date(minDate.value).getFullYear()
  const endYear = new Date(maxDate.value).getFullYear()
  const years = []
  for (let y = startYear; y <= endYear; y++) {
    years.push({ year: y, xPct: dateToPercent(`${y}-01-01`, minDate.value, maxDate.value) })
  }
  return years
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
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: oklch(0.82 0.06 35);
}
.maint-rule.severe {
  width: 2px;
  background: var(--severe-red);
}
.maint-label {
  position: absolute;
  top: 30px;
  left: 6px;
  font-size: 10.5px;
  font-weight: 600;
  color: var(--severe-red);
  white-space: nowrap;
}
.line-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.dot {
  position: absolute;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  width: 6px;
  height: 6px;
  background: var(--ac);
  opacity: 0.42;
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
</style>
