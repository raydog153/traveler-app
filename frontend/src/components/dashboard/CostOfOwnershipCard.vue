<template>
  <div class="card panel">
    <div class="label">Total cost of ownership</div>
    <div class="hero-row">
      <span class="total">{{ formatCurrency(data.total_cost, { decimals: 0 }) }}</span>
      <span class="over-miles">over {{ formatMiles(data.total_miles) }} miles</span>
    </div>

    <div class="stats-row">
      <div class="stat">
        <div class="stat-label">Cost per mile</div>
        <div class="stat-value">{{ formatCurrency(data.cost_per_mile) }}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Gas share</div>
        <div class="stat-value accent">{{ Math.round(data.gas_share_pct) }}%</div>
      </div>
    </div>

    <div class="split-bar">
      <div class="seg gas" :style="{ width: data.gas_share_pct + '%' }">
        {{ formatCurrency(data.gas_total, { decimals: 0 }) }}
      </div>
      <div class="seg maint" :style="{ width: 100 - data.gas_share_pct + '%' }">
        {{ formatCurrency(data.maintenance_total, { decimals: 0 }) }}
      </div>
    </div>

    <div class="legend">
      <span class="legend-item">
        <span class="swatch gas" />
        Gas — {{ Math.round(data.gas_gallons).toLocaleString() }} gal at {{ formatCurrency(data.gas_avg_cost_per_gal) }} avg
      </span>
      <span class="legend-item">
        <span class="swatch maint" />
        Maintenance — {{ data.maintenance_visits }} visits, {{ formatCurrency(data.maintenance_cost_per_mile) }} per mile
      </span>
    </div>
  </div>
</template>

<script setup>
import { formatCurrency, formatMiles } from '../../utils/format'

defineProps({
  data: { type: Object, required: true },
})
</script>

<style scoped>
.card {
  padding: 22px 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-bottom: 0;
}
.label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
}
.hero-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}
.total {
  font-size: 42px;
  font-weight: 600;
  line-height: 0.9;
  letter-spacing: -0.035em;
}
.over-miles {
  font-size: 13px;
  color: var(--text-muted);
}
.stats-row {
  display: flex;
  gap: 26px;
}
.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.stat-value {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.025em;
}
.stat-value.accent {
  color: var(--ac);
}
.split-bar {
  display: flex;
  height: 34px;
  border-radius: 9px;
  overflow: hidden;
  gap: 2px;
}
.seg {
  display: flex;
  align-items: center;
  padding-left: 11px;
  font-size: 11.5px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
}
.seg.gas {
  background: var(--ac);
}
.seg.maint {
  background: var(--rust);
}
.legend {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  font-size: 12px;
  color: oklch(0.45 0.012 255);
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.swatch {
  width: 9px;
  height: 9px;
  border-radius: 3px;
  flex-shrink: 0;
}
.swatch.gas {
  background: var(--ac);
}
.swatch.maint {
  background: var(--rust);
}
</style>
