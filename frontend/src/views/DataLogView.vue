<template>
  <div class="wrap">
    <h1>🚌 Bus Living — Data Reference</h1>
    <p class="sub">{{ subhead }}</p>

    <div class="tabs">
      <button class="tab-btn" :class="{ active: tab === 'gas' }" @click="tab = 'gas'">Gas Log</button>
      <button class="tab-btn" :class="{ active: tab === 'maint' }" @click="tab = 'maint'">Maintenance Log</button>
      <button class="btn add-btn" @click="showForm = true">
        + Add {{ tab === 'gas' ? 'Fill-up' : 'Maintenance' }}
      </button>
    </div>

    <DataTable
      v-if="tab === 'gas'"
      :columns="gasColumns"
      :rows="gasStore.fillups"
      show-hide-excluded
      :excluded-predicate="(r) => !r.is_clean"
      default-sort-key="date"
    />
    <DataTable v-else :columns="maintColumns" :rows="maintenanceStore.records" default-sort-key="date" />

    <NewFillupForm v-if="showForm && tab === 'gas'" @close="showForm = false" @created="onFillupCreated" />
    <NewMaintenanceForm
      v-if="showForm && tab === 'maint'"
      @close="showForm = false"
      @created="onMaintenanceCreated"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useGasStore } from '../stores/gasStore'
import { useMaintenanceStore } from '../stores/maintenanceStore'
import { useDashboardStore } from '../stores/dashboardStore'
import { useMapStore } from '../stores/mapStore'
import DataTable from '../components/DataTable.vue'
import NewFillupForm from '../components/NewFillupForm.vue'
import NewMaintenanceForm from '../components/NewMaintenanceForm.vue'

const gasStore = useGasStore()
const maintenanceStore = useMaintenanceStore()
const dashboardStore = useDashboardStore()
const mapStore = useMapStore()

const tab = ref('gas')
const showForm = ref(false)

onMounted(() => {
  gasStore.fetchAll()
  maintenanceStore.fetchAll()
})

const subhead = computed(() => {
  if (tab.value === 'gas') {
    const total = gasStore.fillups.length
    const clean = gasStore.fillups.filter((r) => r.is_clean).length
    return `${total} fill-ups logged (${clean} clean, ${total - clean} excluded from MPG averages) — sortable, searchable.`
  }
  const total = maintenanceStore.records.length
  const totalCost = maintenanceStore.records.reduce((s, r) => s + r.cost, 0)
  return `${total} maintenance line items, $${Math.round(totalCost).toLocaleString()} total — sortable, searchable.`
})

function onFillupCreated() {
  // Dashboard/map stats are server-computed off the full dataset -- force a
  // refetch next time those views are visited rather than trying to patch
  // their cached summaries client-side.
  dashboardStore.loaded = false
  mapStore.loaded = false
}

function onMaintenanceCreated() {
  dashboardStore.loaded = false
}

const gasColumns = [
  { key: 'date', label: 'Date' },
  { key: 'city', label: 'City' },
  { key: 'odometer_miles', label: 'Odometer', num: true, fmt: (v) => Math.round(v).toLocaleString() },
  { key: 'gallons', label: 'Gallons', num: true, fmt: (v) => v.toFixed(2) },
  { key: 'price', label: 'Price', num: true, fmt: (v) => `$${v.toFixed(2)}` },
  { key: 'cost_per_gal', label: '$/gal', num: true, fmt: (v) => `$${v.toFixed(2)}` },
  { key: 'driven', label: 'Miles since', num: true, fmt: (v) => (v != null ? Math.round(v).toLocaleString() : '') },
  { key: 'mpg', label: 'MPG', num: true, fmt: (v) => (v != null ? v.toFixed(1) : '') },
  { key: 'is_clean', label: 'Status', badge: (row) => (row.is_clean ? { text: 'clean', cls: 'clean' } : { text: 'excluded', cls: 'excluded' }) },
  { key: 'notes', label: 'Notes', notes: true },
]

const maintColumns = [
  { key: 'date', label: 'Date' },
  { key: 'expense', label: 'Expense' },
  { key: 'place', label: 'Place' },
  { key: 'odometer_miles', label: 'Odometer', num: true, fmt: (v) => (v != null ? Math.round(v).toLocaleString() : '') },
  { key: 'vendor', label: 'Vendor' },
  {
    key: 'cost',
    label: 'Cost',
    num: true,
    fmt: (v) => `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
  },
  { key: 'is_major', label: '', badge: (row) => (row.is_major ? { text: 'major', cls: 'major' } : null) },
]
</script>

<style scoped>
.wrap {
  max-width: 1180px;
  margin: 0 auto;
}
h1 {
  font-size: 21px;
  margin: 0 0 4px;
}
.sub {
  color: var(--muted);
  font-size: 13px;
  margin: 0 0 18px;
}
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
  align-items: center;
}
.tab-btn {
  background: var(--panel);
  border: 1px solid var(--grid);
  color: var(--muted);
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  font-weight: 600;
}
.tab-btn.active {
  background: var(--accent);
  color: #0f1720;
  border-color: var(--accent);
}
.add-btn {
  margin-left: auto;
}
</style>
