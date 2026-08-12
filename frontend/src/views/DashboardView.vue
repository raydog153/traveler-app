<template>
  <div class="wrap">
    <h1>🚌 Bus Living — Gas &amp; Maintenance</h1>
    <p class="sub">{{ store.loading ? 'Loading…' : store.summary?.subhead }}</p>

    <p v-if="store.error" class="error">Failed to load dashboard: {{ store.error }}</p>

    <template v-if="summary">
      <ServiceAlert v-if="summary.service_alert" :alert="summary.service_alert" />

      <div class="stats">
        <StatCard
          v-for="s in summary.stats"
          :key="s.label"
          :label="s.label"
          :value="s.value"
          :cls="accentFor(s.label)"
        />
      </div>

      <div class="panel">
        <h2>Cost per gallon over time</h2>
        <p class="desc">Every fill-up, price paid per gallon.</p>
        <CostPerGallonChart :series="summary.price_per_gallon_series" />
      </div>

      <div class="panel">
        <h2>Fuel economy (MPG), cleaned, with maintenance overlay</h2>
        <p class="desc">
          Faded dots are excluded (partial fill-ups or entries marked "Est"/off on mileage). Solid
          dots feed the 7-fill-up rolling average. Dashed/solid vertical lines mark maintenance
          events over $2,000 (red = over $10,000).
        </p>
        <MpgScatterChart
          :clean-points="summary.mpg_clean_points"
          :excluded-points="summary.mpg_excluded_points"
          :rolling-avg="summary.mpg_rolling_avg"
          :major-events="summary.major_events"
        />
        <div class="callout">{{ summary.narrative }}</div>
      </div>

      <div class="panel">
        <h2>Total cost of ownership — gas vs. maintenance</h2>
        <p class="desc">Cumulative spend on each.</p>
        <CumulativeSpendChart :gas="summary.cumulative_gas" :maintenance="summary.cumulative_maintenance" />
      </div>

      <div class="two-col">
        <div class="panel">
          <h2>Annual snapshot</h2>
          <p class="desc">Gas + maintenance spend (stacked) vs. miles driven, per year. Most recent year is partial.</p>
          <YearlyComboChart :yearly="summary.yearly" />
        </div>
        <div class="panel">
          <h2>Biggest maintenance events</h2>
          <p class="desc">Single-day repairs over $2,000.</p>
          <ul class="maint-list">
            <li v-for="e in summary.major_events" :key="e.date + e.label">
              <span class="m-date">{{ e.date }}</span>
              <span class="m-label">{{ e.label }}</span>
              <span class="m-cost">{{ formatCurrency(e.cost, { decimals: 0 }) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useDashboardStore } from '../stores/dashboardStore'
import StatCard from '../components/StatCard.vue'
import ServiceAlert from '../components/ServiceAlert.vue'
import CostPerGallonChart from '../components/charts/CostPerGallonChart.vue'
import MpgScatterChart from '../components/charts/MpgScatterChart.vue'
import CumulativeSpendChart from '../components/charts/CumulativeSpendChart.vue'
import YearlyComboChart from '../components/charts/YearlyComboChart.vue'
import { formatCurrency } from '../utils/format'

const store = useDashboardStore()
const summary = computed(() => store.summary)

const ACCENT_BY_LABEL = {
  'Total spent on gas': 'accent',
  'Avg cost / gallon': 'accent2',
  'Total maintenance': 'accent3',
}
function accentFor(label) {
  return ACCENT_BY_LABEL[label] || ''
}

onMounted(() => store.fetchAll())
</script>

<style scoped>
.wrap {
  max-width: 1100px;
  margin: 0 auto;
}
h1 {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 4px;
}
.sub {
  color: var(--muted);
  font-size: 13.5px;
  margin: 0 0 26px;
}
.error {
  color: var(--accent3);
}
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 26px;
}
.callout {
  background: var(--panel2);
  border-left: 3px solid var(--accent3);
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 12.5px;
  margin-top: 10px;
  line-height: 1.5;
}
.maint-list {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 12.5px;
}
.maint-list li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 0;
  border-bottom: 1px solid var(--grid);
}
.maint-list li:last-child {
  border-bottom: none;
}
.m-date {
  color: var(--muted);
  min-width: 78px;
}
.m-label {
  flex: 1;
}
.m-cost {
  color: var(--accent3);
  font-weight: 600;
  white-space: nowrap;
}
</style>
