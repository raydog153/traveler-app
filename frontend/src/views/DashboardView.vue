<template>
  <div class="wrap">
    <div class="header-row">
      <div>
        <h1>Gas &amp; maintenance</h1>
        <p class="sub">{{ store.loading ? 'Loading…' : summary?.subhead }}</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn secondary">Export CSV</button>
        <RouterLink to="/log" class="btn add-btn">+ Add fill-up</RouterLink>
      </div>
    </div>

    <p v-if="store.error" class="error">Failed to load dashboard: {{ store.error }}</p>

    <template v-if="summary">
      <div class="hero-row">
        <CostOfOwnershipCard :data="summary.cost_of_ownership" />
        <NextServiceCard v-if="summary.service_alert" :alert="summary.service_alert" @log-service="goLog" />
      </div>

      <MpgCentrepiece
        :clean-points="summary.mpg_clean_points"
        :excluded-points="summary.mpg_excluded_points"
        :rolling-avg="summary.mpg_rolling_avg"
        :major-events="summary.major_events"
      />

      <div class="chart-pair">
        <PricePerGallonPanel :series="summary.price_per_gallon_series" />
        <CumulativeSpendPanel :gas="summary.cumulative_gas" :maintenance="summary.cumulative_maintenance" />
      </div>

      <div class="bottom-row">
        <AnnualSnapshotPanel :yearly="summary.yearly" />
        <BiggestRepairsList :events="summary.major_events_by_cost" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboardStore'
import CostOfOwnershipCard from '../components/dashboard/CostOfOwnershipCard.vue'
import NextServiceCard from '../components/dashboard/NextServiceCard.vue'
import MpgCentrepiece from '../components/dashboard/MpgCentrepiece.vue'
import PricePerGallonPanel from '../components/dashboard/PricePerGallonPanel.vue'
import CumulativeSpendPanel from '../components/dashboard/CumulativeSpendPanel.vue'
import AnnualSnapshotPanel from '../components/dashboard/AnnualSnapshotPanel.vue'
import BiggestRepairsList from '../components/dashboard/BiggestRepairsList.vue'

const store = useDashboardStore()
const summary = computed(() => store.summary)
const router = useRouter()

function goLog() {
  router.push('/log')
}

onMounted(() => store.fetchAll())
</script>

<style scoped>
.wrap {
  max-width: 1440px;
  margin: 0 auto;
  padding: 28px 26px 56px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}
h1 {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.025em;
  margin: 0 0 4px;
}
.sub {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.add-btn {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.error {
  color: var(--severe-red);
}
.hero-row {
  display: grid;
  grid-template-columns: 1fr 330px;
  gap: 16px;
}
.chart-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 460px;
  gap: 16px;
}
@media (max-width: 1100px) {
  .hero-row,
  .chart-pair,
  .bottom-row {
    grid-template-columns: 1fr;
  }
}
</style>
