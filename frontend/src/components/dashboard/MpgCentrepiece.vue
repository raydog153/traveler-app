<template>
  <div class="panel centrepiece">
    <div class="head-row">
      <div class="head-text">
        <h2>Fuel economy never recovered from the engine swap</h2>
        <p class="desc">
          Cleaned MPG per fill-up with a 7-fill-up rolling average. Faded dots are excluded — partial fills or
          estimated mileage.
        </p>
      </div>
      <div class="era-chips">
        <div class="era-chip" style="border-color: oklch(0.7 0.012 255)">
          <div class="chip-label">Before engine swap</div>
          <div class="chip-value">{{ fmtMpg(eraMpg.before_engine) }}</div>
        </div>
        <div class="era-chip" style="border-color: var(--rust)">
          <div class="chip-label">Engine → transmission</div>
          <div class="chip-value">{{ fmtMpg(eraMpg.engine_to_transmission) }}</div>
        </div>
        <div class="era-chip" style="border-color: var(--green)">
          <div class="chip-label">Since transmission</div>
          <div class="chip-value">{{ fmtMpg(eraMpg.since_transmission) }}</div>
        </div>
      </div>
    </div>

    <div class="plot-wrap">
      <div class="y-axis">
        <span v-for="t in Y_TICKS" :key="t" class="mono">{{ t }}</span>
      </div>
      <div class="plot">
        <div v-for="g in [0, 25, 50, 75]" :key="g" class="gridline" :style="{ top: g + '%' }" />

        <div
          v-if="engineXPct != null && transXPct != null"
          class="era-band rust"
          :style="{ left: engineXPct + '%', width: transXPct - engineXPct + '%' }"
        />
        <div
          v-if="transXPct != null"
          class="era-band green"
          :style="{ left: transXPct + '%', right: 0 }"
        />

        <div
          v-for="ev in markers"
          :key="ev.date + ev.label"
          class="maint-rule"
          :class="{ severe: ev.severe }"
          :style="{ left: ev.xPct + '%' }"
        >
          <span v-if="ev.severe" class="maint-label mono">{{ ev.tag }}</span>
        </div>

        <span v-if="engineXPct != null" class="era-label engine-label" :style="{ left: engineXPct + '%' }"
          >New engine</span
        >
        <span v-if="transXPct != null" class="era-label trans-label" :style="{ left: transXPct + '%' }"
          >New transmission</span
        >
        <span class="era-label original-label">Original engine</span>

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
          v-for="p in excludedDots"
          :key="'ex-' + p.x"
          class="dot excluded"
          :style="{ left: p.xPct + '%', top: p.yPct + '%' }"
        />
        <div
          v-for="p in cleanDots"
          :key="'cl-' + p.x"
          class="dot clean"
          :style="{ left: p.xPct + '%', top: p.yPct + '%' }"
        />
      </div>
      <div class="x-axis">
        <span v-for="y in xTickYears" :key="y.year" class="mono" :style="{ left: y.xPct + '%' }">{{ y.year }}</span>
      </div>
    </div>

    <div class="callout">
      <template v-if="eraMpg.before_engine != null">
        Averaging <strong>{{ fmtMpg(eraMpg.before_engine) }} mpg</strong> before the
        {{ formatMonthYear(eraMpg.engine_replacement_date) }} engine replacement
        <template v-if="eraMpg.engine_to_transmission != null">
          and <strong>{{ fmtMpg(eraMpg.engine_to_transmission) }}</strong> between the new engine and the
          {{ formatMonthYear(eraMpg.transmission_replacement_date) }} transmission.
        </template>
        <template v-if="eraMpg.since_transmission != null">
          Since the transmission it has come back to <strong>{{ fmtMpg(eraMpg.since_transmission) }}</strong
          >.
        </template>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { dateToPercent, valueToPercent } from '../../utils/chartScale'

const props = defineProps({
  cleanPoints: { type: Array, required: true },
  excludedPoints: { type: Array, required: true },
  rollingAvg: { type: Array, required: true },
  majorEvents: { type: Array, required: true },
  eraMpg: { type: Object, required: true },
})

const Y_TICKS = [18, 14, 10, 6, 2]
const Y_MIN = 2
const Y_MAX = 18

const allDates = computed(() => {
  const dates = [...props.cleanPoints, ...props.excludedPoints].map((p) => p.x)
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

const cleanDots = computed(() => props.cleanPoints.map(toPlotPoint))
const excludedDots = computed(() => props.excludedPoints.map(toPlotPoint))

const avgLinePoints = computed(() => {
  if (!props.rollingAvg.length) return ''
  return props.rollingAvg
    .map((p) => toPlotPoint(p))
    .map((p) => `${p.xPct},${p.yPct}`)
    .join(' ')
})

const engineXPct = computed(() =>
  props.eraMpg.engine_replacement_date ? dateToPercent(props.eraMpg.engine_replacement_date, minDate.value, maxDate.value) : null,
)
const transXPct = computed(() =>
  props.eraMpg.transmission_replacement_date
    ? dateToPercent(props.eraMpg.transmission_replacement_date, minDate.value, maxDate.value)
    : null,
)

const markers = computed(() =>
  props.majorEvents.map((ev) => ({
    ...ev,
    xPct: dateToPercent(ev.date, minDate.value, maxDate.value),
    severe: ev.cost >= 10000,
    tag: `$${Math.round(ev.cost / 1000)}k`,
  })),
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

function fmtMpg(v) {
  return v != null ? v.toFixed(1) : '—'
}

function formatMonthYear(iso) {
  if (!iso) return ''
  return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
}
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
.era-chips {
  display: flex;
  gap: 14px;
}
.era-chip {
  border-left: 3px solid;
  padding-left: 11px;
}
.chip-label {
  font-size: 10.5px;
  color: var(--text-muted);
}
.chip-value {
  font-size: 17px;
  font-weight: 600;
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
.era-band {
  position: absolute;
  top: 0;
  bottom: 0;
}
.era-band.rust {
  background: oklch(0.63 0.17 35 / 0.07);
}
.era-band.green {
  background: oklch(0.62 0.13 155 / 0.06);
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
.era-label {
  position: absolute;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  transform: translateX(4px);
}
.engine-label {
  top: 4px;
  color: oklch(0.55 0.15 35);
}
.trans-label {
  bottom: 4px;
  color: var(--green-text);
}
.original-label {
  bottom: 4px;
  left: 4px;
  color: var(--text-muted);
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
}
.dot.clean {
  width: 6px;
  height: 6px;
  background: var(--ac);
  opacity: 0.42;
}
.dot.excluded {
  width: 5px;
  height: 5px;
  background: oklch(0.78 0.03 258);
  opacity: 0.55;
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
.callout {
  margin: 16px 24px 4px;
  padding: 14px 16px;
  background: oklch(0.975 0.012 35);
  border: 1px solid oklch(0.93 0.03 35);
  border-radius: 11px;
  color: oklch(0.4 0.05 35);
  font-size: 12.5px;
  line-height: 1.6;
}
</style>
