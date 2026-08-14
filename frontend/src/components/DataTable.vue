<template>
  <div class="panel card--table table-card">
    <div class="table-scroll">
      <div class="grid-table" :style="{ gridTemplateColumns: gridTemplateColumns }">
        <div class="row header-row">
          <div
            v-for="c in columns"
            :key="c.key"
            class="cell head-cell"
            :class="{ sorted: sortKey === c.key, num: c.num }"
            @click="sortBy(c.key)"
          >
            {{ c.label }}<span v-if="sortKey === c.key" class="sort-arrow">{{ sortDir === 1 ? ' ▲' : ' ▼' }}</span>
          </div>
          <div v-if="editable" class="cell head-cell actions-col"></div>
        </div>

        <div v-for="row in sortedRows" :key="row.id" class="row body-row">
          <div v-for="c in columns" :key="c.key" class="cell" :class="{ num: c.num, mono: c.mono }">
            <template v-if="c.kind === 'city'">
              <span class="city-text">{{ row[c.key] }}</span>
              <span v-if="flagOf(row)" class="flag-pill" :class="flagOf(row).cls">{{ flagOf(row).text }}</span>
            </template>
            <template v-else-if="c.kind === 'mpg'">
              <div class="mpg-cell">
                <span class="mpg-value mono">{{ row.mpg != null ? row.mpg.toFixed(1) : '—' }}</span>
                <div class="mini-bar-track">
                  <div class="mini-bar-fill" :style="{ width: mpgBarPct(row.mpg) + '%' }" />
                </div>
              </div>
            </template>
            <template v-else-if="c.kind === 'costBar'">
              <div class="cost-cell">
                <span class="cost-value mono">{{ formatCurrency(row[c.key], { decimals: 0 }) }}</span>
                <div class="cost-bar-track">
                  <div class="cost-bar-fill" :style="{ width: costBarPct(row[c.key]) + '%' }" />
                </div>
              </div>
            </template>
            <template v-else-if="c.badge">
              <span v-if="c.badge(row)" class="badge" :class="c.badge(row).cls">{{ c.badge(row).text }}</span>
            </template>
            <template v-else>
              {{ c.fmt ? c.fmt(row[c.key]) : row[c.key] }}
            </template>
          </div>
          <div v-if="editable" class="cell actions-cell">
            <button type="button" class="icon-btn" title="Edit" @click="$emit('edit', row)">✎</button>
            <button type="button" class="icon-btn danger" title="Delete" @click="$emit('delete', row)">🗑</button>
          </div>
        </div>
      </div>
    </div>

    <div class="footer-bar">
      <span class="footer-left">{{ footerText }}</span>
      <div class="footer-actions">
        <button type="button" class="page-btn" disabled>Previous</button>
        <button type="button" class="page-btn" disabled>Next</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { formatCurrency } from '../utils/format'
import { valueToPercent } from '../utils/chartScale'

const props = defineProps({
  columns: { type: Array, required: true }, // [{ key, label, width, num, mono, fmt, badge, kind }]
  rows: { type: Array, required: true },
  defaultSortKey: { type: String, default: 'date' },
  defaultSortDir: { type: Number, default: 1 },
  // Adds a trailing edit/delete actions column, emitting 'edit'/'delete'
  // with the row -- the caller owns what those actions actually do.
  editable: { type: Boolean, default: false },
  footerText: { type: String, default: '' },
  // Best-effort flag pill for a row (gas rows only) -- e.g. "first entry"
  // for a row with no previous fill-up to derive miles/mpg from.
  flagOf: { type: Function, default: () => null },
})
defineEmits(['edit', 'delete'])

const sortKey = ref(props.defaultSortKey)
const sortDir = ref(props.defaultSortDir)

const gridTemplateColumns = computed(() => {
  const widths = props.columns.map((c) => c.width || '1fr').join(' ')
  return props.editable ? `${widths} 64px` : widths
})

function sortBy(key) {
  if (sortKey.value === key) {
    sortDir.value *= -1
  } else {
    sortKey.value = key
    sortDir.value = 1
  }
}

const sortedRows = computed(() => {
  const rows = [...props.rows]
  const key = sortKey.value
  const dir = sortDir.value
  rows.sort((a, b) => {
    let av = a[key]
    let bv = b[key]
    if (av == null) av = ''
    if (bv == null) bv = ''
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir
    return String(av).localeCompare(String(bv)) * dir
  })
  return rows
})

const MPG_BAR_MAX = 14
function mpgBarPct(mpg) {
  if (mpg == null) return 0
  return valueToPercent(mpg, 0, MPG_BAR_MAX, false)
}
const costMax = computed(() => Math.max(1, ...props.rows.map((r) => r.cost || 0)))
function costBarPct(cost) {
  return valueToPercent(cost || 0, 0, costMax.value, false)
}
</script>

<style scoped>
.table-card {
  padding: 0;
  overflow: hidden;
}
.table-scroll {
  max-height: 560px;
  overflow: auto;
}
.grid-table {
  display: grid;
  font-size: 12.5px;
}
.row {
  display: contents;
}
.header-row .cell {
  position: sticky;
  top: 0;
  background: var(--fill-subtle);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 500;
  padding: 12px 10px;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  z-index: 1;
}
.header-row .cell.sorted {
  color: var(--ac);
}
.sort-arrow {
  font-size: 9px;
}
.body-row .cell {
  padding: 11px 10px;
  border-bottom: 1px solid var(--row-border);
  background: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
}
.cell.num,
.cell.mono {
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  justify-content: flex-end;
}

.city-text {
  overflow: hidden;
  text-overflow: ellipsis;
}
.flag-pill {
  margin-left: 8px;
  font-size: 10.5px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}
.flag-pill.neutral {
  color: var(--text-muted);
  background: var(--fill-subtle);
}

.mpg-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
  width: 100%;
}
.mpg-value {
  font-weight: 600;
  font-size: 12.5px;
}
.mini-bar-track {
  width: 70px;
  height: 5px;
  border-radius: 3px;
  background: var(--gridline);
  overflow: hidden;
}
.mini-bar-fill {
  height: 100%;
  background: var(--ac);
  opacity: 0.8;
  border-radius: 3px;
}

.cost-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
  width: 100%;
}
.cost-value {
  font-weight: 600;
  font-size: 12.5px;
}
.cost-bar-track {
  width: 70px;
  height: 5px;
  border-radius: 3px;
  background: var(--gridline);
  overflow: hidden;
}
.cost-bar-fill {
  height: 100%;
  background: var(--rust);
  opacity: 0.8;
  border-radius: 3px;
}

.badge {
  display: inline-block;
  font-size: 10.5px;
  padding: 2px 8px;
  border-radius: 20px;
  font-weight: 500;
}
.badge.major {
  color: var(--severe-red);
  background: var(--rust-tint);
}

.actions-cell {
  justify-content: flex-end;
  gap: 4px;
}
.icon-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 13px;
  padding: 2px 5px;
  border-radius: 6px;
  line-height: 1;
}
.icon-btn:hover {
  color: var(--text-primary);
  background: var(--fill-subtle);
}
.icon-btn.danger:hover {
  color: var(--severe-red);
}

.footer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--fill-subtle-2);
  border-top: 1px solid var(--row-border);
  padding: 12px 18px;
  font-size: 12px;
  color: var(--text-muted);
}
.footer-actions {
  display: flex;
  gap: 8px;
}
.page-btn {
  background: #fff;
  border: 1px solid var(--card-border);
  color: oklch(0.7 0.012 255);
  padding: 7px 13px;
  border-radius: 8px;
  font-size: 12px;
  cursor: not-allowed;
}
</style>
