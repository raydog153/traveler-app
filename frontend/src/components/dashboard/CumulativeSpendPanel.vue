<template>
  <div class="panel small-chart">
    <h2>{{ showMaintenance ? 'Total cost of ownership — gas vs. maintenance' : 'Cumulative gas spend' }}</h2>
    <p class="desc">
      {{
        showMaintenance
          ? 'Maintenance overtook gas early on and never looked back.'
          : 'Running total spent on gas over time.'
      }}
    </p>

    <div class="plot-wrap">
      <div class="y-axis">
        <span v-for="t in yTicks" :key="t" class="mono">{{ t }}</span>
      </div>
      <div class="plot">
        <div v-for="g in [0, 33, 66, 100]" :key="g" class="gridline" :style="{ top: g + '%' }" />

        <svg class="area-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
          <polygon v-if="showMaintenance && maintArea" :points="maintArea" fill="var(--rust)" opacity="0.14" />
          <polygon v-if="gasArea" :points="gasArea" fill="var(--ac)" opacity="0.12" />
          <polyline
            v-if="showMaintenance && maintLine"
            :points="maintLine"
            fill="none"
            stroke="var(--rust)"
            stroke-width="1.2"
            vector-effect="non-scaling-stroke"
          />
          <polyline
            v-if="gasLine"
            :points="gasLine"
            fill="none"
            stroke="var(--ac)"
            stroke-width="1.2"
            vector-effect="non-scaling-stroke"
          />
        </svg>

        <span v-if="showMaintenance" class="inline-label maint-label">Maintenance</span>
        <span class="inline-label gas-label">Gas</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { dateToPercent, valueToPercent } from '../../utils/chartScale'

const props = defineProps({
  gas: { type: Array, required: true },
  maintenance: { type: Array, required: true },
  showMaintenance: { type: Boolean, default: true },
})

const yTicks = computed(() => {
  const max = yMax.value
  return [max, Math.round(max * 0.67), Math.round(max * 0.33), 0].map((v) => `${Math.round(v / 1000)}k`)
})

const allDates = computed(() => [...props.gas, ...(props.showMaintenance ? props.maintenance : [])].map((p) => p.x))
const minDate = computed(() =>
  allDates.value.length ? allDates.value.reduce((a, b) => (a < b ? a : b)) : new Date().toISOString(),
)
const maxDate = computed(() =>
  allDates.value.length ? allDates.value.reduce((a, b) => (a > b ? a : b)) : new Date().toISOString(),
)
const yMax = computed(() => {
  const m = Math.max(
    0,
    ...props.gas.map((p) => p.y),
    ...(props.showMaintenance ? props.maintenance.map((p) => p.y) : []),
  )
  return m > 0 ? m * 1.08 : 100
})

function toXY(p) {
  return {
    xPct: dateToPercent(p.x, minDate.value, maxDate.value),
    yPct: valueToPercent(p.y, 0, yMax.value, true),
  }
}

function lineOf(series) {
  if (!series.length) return ''
  return series
    .map(toXY)
    .map((p) => `${p.xPct},${p.yPct}`)
    .join(' ')
}

function areaOf(series) {
  if (!series.length) return ''
  const pts = series.map(toXY)
  const top = pts.map((p) => `${p.xPct},${p.yPct}`).join(' ')
  return `0,100 ${top} 100,100`
}

const gasLine = computed(() => lineOf(props.gas))
const maintLine = computed(() => lineOf(props.maintenance))
const gasArea = computed(() => areaOf(props.gas))
const maintArea = computed(() => areaOf(props.maintenance))
</script>

<style scoped>
.small-chart {
  padding: 18px 20px 16px;
  margin-bottom: 0;
}
h2 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 2px;
}
.desc {
  font-size: 11.5px;
  color: var(--text-muted);
  margin: 0 0 10px;
}
.plot-wrap {
  position: relative;
  padding-left: 30px;
}
.y-axis {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 30px;
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
.area-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.inline-label {
  position: absolute;
  left: 60%;
  font-size: 11px;
  font-weight: 500;
}
.maint-label {
  top: 6px;
  color: var(--rust);
}
.gas-label {
  bottom: 24px;
  color: var(--ac);
}
</style>
