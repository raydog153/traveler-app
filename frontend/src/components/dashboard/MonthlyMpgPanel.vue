<template>
  <div class="panel monthly-mpg">
    <div class="head-row">
      <div>
        <h2>Monthly avg MPG</h2>
        <p class="desc">
          Miles driven ÷ gallons used per calendar month.
        </p>
      </div>
      <div class="legend">
        <button
          v-for="(y, i) in years"
          :key="y"
          type="button"
          class="legend-item"
          :class="{ off: hiddenYears.has(y) }"
          @click="toggleYear(y)"
        >
          <span class="swatch" :style="{ background: hiddenYears.has(y) ? 'var(--track)' : yearColor(i) }" />{{ y }}
        </button>
      </div>
    </div>

    <div class="plot-wrap">
      <div class="y-axis">
        <span v-for="pct in GRID_LEVELS" :key="pct" class="mono" :style="{ bottom: pct + '%' }">{{
          formatMpg((pct / 100) * maxMpg)
        }}</span>
      </div>
      <div class="scroll-wrap">
        <div class="chart-area">
          <div class="gridlines">
            <div v-for="pct in GRID_LEVELS" :key="pct" class="gridline" :style="{ bottom: pct + '%' }" />
          </div>
          <div class="groups">
            <div v-for="g in monthGroups" :key="g.name" class="month-group">
              <div class="year-bars">
                <div
                  v-for="e in g.entries"
                  :key="e.year"
                  class="bar"
                  :class="{ empty: e.avg_mpg == null }"
                  :style="{ height: barHeightPx(e) + 'px', background: e.avg_mpg != null ? e.color : undefined }"
                  @mouseenter="onEnter($event, e)"
                  @mouseleave="onLeave"
                  @click="onClick($event, e)"
                />
              </div>
              <div class="month-label">{{ g.name }}</div>
            </div>
          </div>
        </div>
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
import { formatMiles, formatMpg, formatGallons } from '../../utils/format'
import { yearColor } from '../../theme'

const props = defineProps({
  monthly: { type: Array, required: true },
})

const BAR_MAX_PX = 150
const BAR_MIN_PX = 3
const GRID_LEVELS = [0, 25, 50, 75, 100]
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const years = computed(() => [...new Set(props.monthly.map((m) => Number(m.month.slice(0, 4))))].sort((a, b) => a - b))

function colorForYear(year) {
  return yearColor(years.value.indexOf(year))
}

const hiddenYears = ref(new Set())

function toggleYear(year) {
  const next = new Set(hiddenYears.value)
  if (next.has(year)) next.delete(year)
  else next.add(year)
  hiddenYears.value = next
}

const visibleMonthly = computed(() => props.monthly.filter((m) => !hiddenYears.value.has(Number(m.month.slice(0, 4)))))

const monthGroups = computed(() => {
  const groups = MONTH_NAMES.map((name) => ({ name, entries: [] }))
  for (const m of visibleMonthly.value) {
    const [year, mo] = m.month.split('-').map(Number)
    groups[mo - 1].entries.push({ ...m, year, color: colorForYear(year) })
  }
  for (const g of groups) g.entries.sort((a, b) => a.year - b.year)
  return groups
})

// Rescale to whatever's currently visible so toggling down to fewer years
// still uses the full chart height instead of leaving it at a scale sized
// for years that are now hidden.
const maxMpg = computed(() => Math.max(1, ...visibleMonthly.value.map((m) => m.avg_mpg ?? 0)))

function barHeightPx(e) {
  if (e.avg_mpg == null) return BAR_MIN_PX
  return Math.max(BAR_MIN_PX, (e.avg_mpg / maxMpg.value) * BAR_MAX_PX)
}

onMounted(() => document.addEventListener('pointerdown', onDocumentPointerDown))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown))

const tooltip = ref(null)

function anchorPosition(el) {
  const rect = el.getBoundingClientRect()
  return { x: rect.left + rect.width / 2, y: rect.top }
}

function monthTooltip(e) {
  const title = `${MONTH_NAMES[Number(e.month.slice(5, 7)) - 1]} ${e.year}`
  const subtitle =
    e.avg_mpg != null
      ? `${formatMpg(e.avg_mpg)} mpg · ${formatMiles(e.miles)} mi · ${formatGallons(e.gallons)} gal · ${e.fillups} fill-up${e.fillups === 1 ? '' : 's'}`
      : `No mpg data · ${e.fillups} fill-up${e.fillups === 1 ? '' : 's'}`
  return { key: e.month, title, subtitle }
}

function onEnter(e, m) {
  if (tooltip.value?.pinned) return
  tooltip.value = { ...anchorPosition(e.currentTarget), ...monthTooltip(m), pinned: false }
}

function onLeave() {
  if (!tooltip.value?.pinned) tooltip.value = null
}

function onClick(e, m) {
  const data = monthTooltip(m)
  if (tooltip.value?.pinned && tooltip.value.key === data.key) {
    tooltip.value = null
    return
  }
  tooltip.value = { ...anchorPosition(e.currentTarget), ...data, pinned: true }
}

function onDocumentPointerDown(e) {
  if (tooltip.value?.pinned && !e.target.closest('.bar, .chart-tooltip')) tooltip.value = null
}
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
  max-width: 46ch;
}
.legend {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  background: none;
  border: none;
  padding: 3px 6px;
  border-radius: 6px;
  font-size: 11.5px;
  font-family: inherit;
  color: var(--text-secondary);
  cursor: pointer;
  transition:
    opacity 0.15s,
    background 0.15s;
}
.legend-item:hover {
  background: var(--fill-subtle);
}
.legend-item.off {
  opacity: 0.4;
}
.swatch {
  width: 9px;
  height: 9px;
  border-radius: 3px;
  flex-shrink: 0;
}
.plot-wrap {
  position: relative;
  padding-left: 30px;
}
.y-axis {
  position: absolute;
  left: 0;
  top: 0;
  height: 150px;
  width: 24px;
}
.y-axis span {
  position: absolute;
  right: 6px;
  /* Anchored at the exact same `bottom: X%` offset as its matching
     .gridline, then shifted down by half its own line height so the text is
     vertically centered on that line instead of sitting above it -- a plain
     flex space-between only flushes the first/last items to the container
     edges and drifts out of alignment with the gridlines for everything
     in between (and even "0.0" sits a line-height above the true baseline). */
  transform: translateY(50%);
  font-size: 10px;
  color: var(--text-faint);
  white-space: nowrap;
}
.scroll-wrap {
  overflow-x: auto;
  padding-bottom: 4px;
}
.chart-area {
  position: relative;
}
.gridlines {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 150px;
}
.gridline {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--gridline);
}
.groups {
  position: relative;
  display: flex;
  /* flex-start, not flex-end: each column's year-bars must start flush with
     the top of this row so its 150px matches the .gridlines/.y-axis region
     exactly -- flex-end would bottom-align the (shorter, label included)
     column instead and push the bars' 0 baseline below the 0.0 gridline. */
  align-items: flex-start;
  gap: 10px;
  width: 100%;
}
.month-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1 1 0;
  min-width: 0;
}
.year-bars {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 3px;
  width: 100%;
  height: 150px;
}
.bar {
  flex: 0 0 auto;
  width: 14px;
  border-radius: 3px 3px 0 0;
  background: var(--ac);
  border: 1px solid oklch(0 0 0 / 0.12);
  border-bottom: none;
  cursor: pointer;
}
.bar.empty {
  background: var(--track);
  border-color: var(--card-border);
  cursor: default;
}
.month-label {
  font-size: 10.5px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-top: 8px;
  white-space: nowrap;
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
