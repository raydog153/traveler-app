<template>
  <div class="wrap">
    <h1>🚌 Bus Living — Data Reference</h1>
    <p class="sub">{{ subhead }}</p>

    <div class="tabs">
      <button class="tab-btn" :class="{ active: tab === 'gas' }" @click="tab = 'gas'">Gas Log</button>
      <button class="tab-btn" :class="{ active: tab === 'maint' }" @click="tab = 'maint'">Maintenance Log</button>
      <label v-if="tab === 'gas'" class="checkbox-label">
        <input type="checkbox" v-model="hideExcludedFillups" /> Hide excluded fill-ups
      </label>
      <button class="btn add-btn" @click="openAddForm">
        + Add {{ tab === 'gas' ? 'Fill-up' : 'Maintenance' }}
      </button>
    </div>

    <DataTable
      v-if="tab === 'gas'"
      :columns="gasColumns"
      :rows="visibleFillups"
      :excluded-predicate="(r) => !r.is_clean"
      default-sort-key="date"
      editable
      @edit="editingFillup = $event"
      @delete="pendingDelete = { kind: 'gas', row: $event }"
    />
    <DataTable
      v-else
      :columns="maintColumns"
      :rows="maintenanceStore.records"
      default-sort-key="date"
      editable
      @edit="editingRecord = $event"
      @delete="pendingDelete = { kind: 'maint', row: $event }"
    />

    <NewFillupForm
      v-if="(showForm && tab === 'gas') || editingFillup"
      :fillup="editingFillup"
      @close="closeFillupForm"
      @saved="onFillupSaved"
    />
    <NewMaintenanceForm
      v-if="(showForm && tab === 'maint') || editingRecord"
      :record="editingRecord"
      @close="closeMaintenanceForm"
      @saved="onMaintenanceSaved"
    />

    <ConfirmDialog
      v-if="pendingDelete"
      :message="deleteMessage"
      :busy="deleting"
      :error="deleteError"
      @cancel="pendingDelete = null"
      @confirm="confirmDelete"
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
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { formatCurrency, formatMiles, formatMpg } from '../utils/format'

const gasStore = useGasStore()
const maintenanceStore = useMaintenanceStore()
const dashboardStore = useDashboardStore()
const mapStore = useMapStore()

const tab = ref('gas')
const showForm = ref(false)
const hideExcludedFillups = ref(false)
const editingFillup = ref(null)
const editingRecord = ref(null)
const pendingDelete = ref(null)
const deleting = ref(false)
const deleteError = ref('')

const visibleFillups = computed(() =>
  hideExcludedFillups.value ? gasStore.fillups.filter((r) => r.is_clean) : gasStore.fillups,
)

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
  return `${total} maintenance line items, ${formatCurrency(totalCost, { decimals: 0 })} total — sortable, searchable.`
})

function openAddForm() {
  editingFillup.value = null
  editingRecord.value = null
  showForm.value = true
}

function closeFillupForm() {
  showForm.value = false
  editingFillup.value = null
}

function closeMaintenanceForm() {
  showForm.value = false
  editingRecord.value = null
}

function onFillupSaved() {
  // Dashboard/map stats are server-computed off the full dataset -- mark
  // them stale so they refetch next time those views are visited, rather
  // than trying to patch their cached summaries client-side.
  dashboardStore.invalidate()
  mapStore.invalidate()
}

function onMaintenanceSaved() {
  dashboardStore.invalidate()
}

const deleteMessage = computed(() => {
  if (!pendingDelete.value) return ''
  const { kind, row } = pendingDelete.value
  return kind === 'gas'
    ? `Delete the ${row.date} fill-up in ${row.city}? This can't be undone.`
    : `Delete the ${row.date} "${row.expense}" record? This can't be undone.`
})

async function confirmDelete() {
  if (!pendingDelete.value) return
  const { kind, row } = pendingDelete.value
  deleting.value = true
  deleteError.value = ''
  try {
    if (kind === 'gas') {
      await gasStore.remove(row.id)
      mapStore.invalidate()
    } else {
      await maintenanceStore.remove(row.id)
    }
    dashboardStore.invalidate()
    pendingDelete.value = null
  } catch (err) {
    deleteError.value = err.message
  } finally {
    deleting.value = false
  }
}

const gasColumns = [
  { key: 'date', label: 'Date' },
  { key: 'city', label: 'City' },
  { key: 'odometer_miles', label: 'Odometer', num: true, fmt: formatMiles },
  { key: 'gallons', label: 'Gallons', num: true, fmt: (v) => v.toFixed(2) },
  { key: 'price', label: 'Price', num: true, fmt: formatCurrency },
  { key: 'cost_per_gal', label: '$/gal', num: true, fmt: formatCurrency },
  { key: 'driven', label: 'Miles since', num: true, fmt: formatMiles },
  { key: 'mpg', label: 'MPG', num: true, fmt: formatMpg },
  { key: 'is_clean', label: 'Status', badge: (row) => (row.is_clean ? { text: 'clean', cls: 'clean' } : { text: 'excluded', cls: 'excluded' }) },
  { key: 'notes', label: 'Notes', notes: true },
]

const maintColumns = [
  { key: 'date', label: 'Date' },
  { key: 'expense', label: 'Expense' },
  { key: 'place', label: 'Place' },
  { key: 'odometer_miles', label: 'Odometer', num: true, fmt: formatMiles },
  { key: 'vendor', label: 'Vendor' },
  { key: 'cost', label: 'Cost', num: true, fmt: formatCurrency },
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
.checkbox-label {
  font-size: 12.5px;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.add-btn {
  margin-left: auto;
}
</style>
