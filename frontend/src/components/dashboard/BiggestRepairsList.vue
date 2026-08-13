<template>
  <div class="panel repairs-card">
    <h2>Biggest repairs</h2>
    <p class="desc">Single-day, over $2,000</p>

    <ul class="repairs-list">
      <li v-for="e in events" :key="e.date + e.label" class="row">
        <div class="top-line">
          <span class="label">{{ e.label }}</span>
          <span class="cost mono">{{ formatCurrency(e.cost, { decimals: 0 }) }}</span>
        </div>
        <div class="bottom-line">
          <span class="date mono">{{ e.date }}</span>
          <div class="bar-track">
            <div class="bar-fill" :class="{ severe: e.cost >= 10000 }" :style="{ width: barPct(e.cost) + '%' }" />
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatCurrency } from '../../utils/format'

const props = defineProps({
  events: { type: Array, required: true },
})

const maxCost = computed(() => Math.max(1, ...props.events.map((e) => e.cost)))

function barPct(cost) {
  return (cost / maxCost.value) * 100
}
</script>

<style scoped>
.repairs-card {
  padding: 20px 20px 12px;
  margin-bottom: 0;
}
h2 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 2px;
}
.desc {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0 0 8px;
}
.repairs-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.row {
  padding: 8px 9px;
  border-radius: 9px;
  cursor: default;
}
.row:hover {
  background: var(--fill-subtle);
}
.top-line {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.label {
  font-size: 12.5px;
  color: oklch(0.28 0.012 255);
}
.cost {
  font-size: 12.5px;
  font-weight: 600;
  white-space: nowrap;
}
.bottom-line {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}
.date {
  font-size: 10.5px;
  color: var(--text-muted);
  width: 66px;
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  height: 5px;
  background: var(--gridline);
  border-radius: 3px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: var(--rust);
  opacity: 0.75;
  border-radius: 3px;
}
.bar-fill.severe {
  background: var(--severe-red);
  opacity: 1;
}
</style>
