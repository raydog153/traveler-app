<template>
  <div class="panel">
    <div class="head-row">
      <div>
        <h2>Annual snapshot</h2>
        <p class="desc">Spend per year against miles driven. Most recent year is partial.</p>
      </div>
      <div class="legend">
        <span class="legend-item"><span class="swatch gas" />Gas</span>
        <span v-if="showMaintenance" class="legend-item"><span class="swatch maint" />Maintenance</span>
        <span class="legend-item"><span class="dash-swatch" />Miles driven</span>
      </div>
    </div>

    <div class="chart-area">
      <svg class="miles-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
        <polyline
          v-if="milesLine"
          :points="milesLine"
          fill="none"
          stroke="oklch(0.45 0.02 255)"
          stroke-width="0.6"
          stroke-dasharray="1.8 1.4"
          vector-effect="non-scaling-stroke"
        />
      </svg>
      <div
        v-for="(m, i) in milesDots"
        :key="'md-' + i"
        class="miles-dot"
        :style="{ left: m.xPct + '%', top: m.yPct + '%' }"
      >
        <span class="miles-chip mono">{{ formatMilesShort(m.value) }}</span>
      </div>

      <div class="bars" ref="barsEl">
        <div
          v-for="(y, i) in yearly"
          :key="y.year"
          class="bar-col"
          :ref="(el) => setBarColEl(el, i)"
        >
          <div class="total-label">{{ formatShort(totalFor(y)) }}</div>
          <div class="bar-stack" :style="{ height: barHeightPx(y) + 'px' }">
            <div v-if="showMaintenance" class="seg maint" :style="{ flexGrow: y.maintenance_cost || 0.0001 }" />
            <div class="seg gas" :style="{ flexGrow: y.cost || 0.0001 }" />
          </div>
          <div class="year-label">{{ y.year }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  yearly: { type: Array, required: true },
  showMaintenance: { type: Boolean, default: true },
})

const BAR_MAX_PX = 150

function totalFor(y) {
  return props.showMaintenance ? y.cost + y.maintenance_cost : y.cost
}

const maxTotal = computed(() => Math.max(1, ...props.yearly.map(totalFor)))
const maxMiles = computed(() => Math.max(1, ...props.yearly.map((y) => y.miles)))

function barHeightPx(y) {
  return (totalFor(y) / maxTotal.value) * BAR_MAX_PX
}

function formatShort(v) {
  return v >= 1000 ? `$${Math.round(v / 1000)}k` : `$${Math.round(v)}`
}

function formatMilesShort(v) {
  return v >= 1000 ? `${(v / 1000).toFixed(1)}k mi` : `${Math.round(v)} mi`
}

const n = computed(() => props.yearly.length)

// The bar columns are laid out by flexbox (equal flex:1 columns, a fixed px
// gap, and a max-width cap on the bar itself), so their on-screen centers
// aren't evenly spaced from 2% to 98% -- they have to be measured from the
// actual DOM rather than derived from index/count alone, or the miles line
// drifts out of alignment with the bars it's meant to track.
const barsEl = ref(null)
let barColEls = []
function setBarColEl(el, i) {
  barColEls[i] = el
}

const colCentersPct = ref([])

function measureColCenters() {
  if (!barsEl.value) return
  const containerRect = barsEl.value.getBoundingClientRect()
  if (containerRect.width === 0) return
  colCentersPct.value = barColEls.filter(Boolean).map((el) => {
    const r = el.getBoundingClientRect()
    return ((r.left + r.width / 2 - containerRect.left) / containerRect.width) * 100
  })
}

let resizeObserver
onMounted(() => {
  resizeObserver = new ResizeObserver(() => measureColCenters())
  if (barsEl.value) resizeObserver.observe(barsEl.value)
  nextTick(measureColCenters)
})
onBeforeUnmount(() => resizeObserver?.disconnect())
watch(
  () => props.yearly,
  () => nextTick(measureColCenters),
)

const milesDots = computed(() =>
  props.yearly.map((y, i) => ({
    value: y.miles,
    xPct: colCentersPct.value[i] ?? (n.value > 1 ? (i / (n.value - 1)) * 96 + 2 : 50),
    yPct: 8 + (100 - (y.miles / maxMiles.value) * 100) * 0.82,
  })),
)

const milesLine = computed(() => milesDots.value.map((m) => `${m.xPct},${m.yPct}`).join(' '))
</script>

<style scoped>
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}
h2 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 2px;
}
.desc {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}
.legend {
  display: flex;
  gap: 16px;
  font-size: 11.5px;
  color: var(--text-muted);
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.swatch {
  width: 9px;
  height: 9px;
  border-radius: 3px;
}
.swatch.gas {
  background: var(--ac);
}
.swatch.maint {
  background: var(--rust);
}
.dash-swatch {
  width: 14px;
  height: 0;
  border-top: 1.75px dashed oklch(0.45 0.02 255);
}
.chart-area {
  position: relative;
  height: 260px;
}
.miles-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 2;
}
.miles-dot {
  position: absolute;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid oklch(0.45 0.02 255);
  transform: translate(-50%, -50%);
  z-index: 2;
}
.miles-chip {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  font-weight: 500;
  background: oklch(1 0 0 / 0.88);
  padding: 2px 5px;
  border-radius: 4px;
  white-space: nowrap;
}
.bars {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: flex-end;
  gap: 16px;
}
.bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  min-width: 0;
}
.total-label {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
  white-space: nowrap;
}
.bar-stack {
  width: 100%;
  max-width: 62px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-radius: 0;
  overflow: hidden;
}
.seg {
  width: 100%;
}
.seg.maint {
  background: var(--rust);
}
.seg.gas {
  background: var(--ac);
}
.year-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-top: 6px;
}
</style>
