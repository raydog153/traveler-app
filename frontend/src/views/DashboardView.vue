<template>
  <div class="wrap">
    <div class="header-row">
      <div>
        <h1>Gas &amp; maintenance</h1>
        <p class="sub">{{ store.loading ? 'Loading…' : summary?.subhead }}</p>
      </div>
      <div class="header-actions">
        <label class="maint-toggle">
          <input v-model="showMaintenance" type="checkbox" />
          <span class="switch-track"><span class="switch-thumb" /></span>
          Show maintenance
        </label>
        <RouterLink to="/log" class="btn add-btn">+ Add fill-up</RouterLink>
      </div>
    </div>

    <p v-if="store.error" class="error">Failed to load dashboard: {{ store.error }}</p>

    <template v-if="summary">
      <div class="hero-row">
        <CostOfOwnershipCard :data="summary.cost_of_ownership" :show-maintenance="showMaintenance" />
        <NextServiceCard v-if="summary.service_alert" :alert="summary.service_alert" @log-service="goLog" />
      </div>

      <MpgCentrepiece
        :points="summary.mpg_points"
        :rolling-avg="summary.mpg_rolling_avg"
        :maintenance-events="summary.maintenance_events"
        :show-maintenance="showMaintenance"
      />

      <div class="chart-pair">
        <PricePerGallonPanel :series="summary.price_per_gallon_series" />
        <CumulativeSpendPanel
          :gas="summary.cumulative_gas"
          :maintenance="summary.cumulative_maintenance"
          :show-maintenance="showMaintenance"
        />
      </div>

      <div class="bottom-row" :class="{ 'maint-hidden': !showMaintenance }">
        <AnnualSnapshotPanel :yearly="summary.yearly" :show-maintenance="showMaintenance" />
        <BiggestRepairsList v-if="showMaintenance" :events="summary.major_events_by_cost" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboardStore'
import CostOfOwnershipCard from '../components/dashboard/CostOfOwnershipCard.vue'
import NextServiceCard from '../components/dashboard/NextServiceCard.vue'
import MpgCentrepiece from '../components/dashboard/MpgCentrepiece.vue'
import PricePerGallonPanel from '../components/dashboard/PricePerGallonPanel.vue'
import CumulativeSpendPanel from '../components/dashboard/CumulativeSpendPanel.vue'
import AnnualSnapshotPanel from '../components/dashboard/AnnualSnapshotPanel.vue'
import BiggestRepairsList from '../components/dashboard/BiggestRepairsList.vue'

const SHOW_MAINTENANCE_KEY = 'dashboard.showMaintenance'

const store = useDashboardStore()
const summary = computed(() => store.summary)
const router = useRouter()

const showMaintenance = ref(localStorage.getItem(SHOW_MAINTENANCE_KEY) === 'true')
watch(showMaintenance, (v) => localStorage.setItem(SHOW_MAINTENANCE_KEY, String(v)))

function goLog() {
  router.push({ path: '/log', query: { tab: 'maint', add: '1' } })
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
  align-items: center;
  gap: 14px;
}
.maint-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}
.maint-toggle input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.switch-track {
  position: relative;
  width: 34px;
  height: 20px;
  border-radius: 10px;
  background: var(--track);
  transition: background 0.15s;
  flex-shrink: 0;
}
.switch-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: var(--shadow-card);
  transition: transform 0.15s;
}
.maint-toggle input:checked + .switch-track {
  background: var(--ac);
}
.maint-toggle input:checked + .switch-track .switch-thumb {
  transform: translateX(14px);
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
.bottom-row.maint-hidden {
  grid-template-columns: 1fr;
}
@media (max-width: 1100px) {
  .hero-row,
  .chart-pair,
  .bottom-row {
    grid-template-columns: 1fr;
  }
}
</style>
