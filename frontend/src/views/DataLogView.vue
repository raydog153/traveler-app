<template>
  <div class="wrap">
    <div class="header-row">
      <div>
        <h1>Data reference</h1>
        <p class="sub">{{ subhead }}</p>
      </div>
      <button class="btn add-btn" @click="openAddForm">+ Add {{ tab === 'gas' ? 'fill-up' : 'maintenance' }}</button>
    </div>

    <div class="toolbar">
      <PillTabs :tabs="subTabs" :active-key="tab" @update:active-key="tab = $event" />

      <div class="search-wrap">
        <span class="search-icon">○</span>
        <input v-model="search" type="text" class="search-input" :placeholder="searchPlaceholder" />
      </div>

      <label v-if="tab === 'gas'" class="checkbox-label">
        <span class="checkbox-box" :class="{ checked: hideExcludedFillups }" @click="hideExcludedFillups = !hideExcludedFillups">
          <input type="checkbox" v-model="hideExcludedFillups" />
        </span>
        Hide excluded fill-ups
      </label>

      <span class="row-count">{{ rowCountText }}</span>
    </div>

    <DataTable
      v-if="tab === 'gas'"
      :columns="gasColumns"
      :rows="searchedFillups"
      :excluded-predicate="(r) => !r.is_clean"
      :flag-of="flagOf"
      default-sort-key="date"
      editable
      :footer-text="gasFooterText"
      @edit="editingFillup = $event"
      @delete="pendingDelete = { kind: 'gas', row: $event }"
    />
    <DataTable
      v-else
      :columns="maintColumns"
      :rows="searchedRecords"
      default-sort-key="date"
      editable
      :footer-text="maintFooterText"
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
import PillTabs from '../components/PillTabs.vue'
import NewFillupForm from '../components/NewFillupForm.vue'
import NewMaintenanceForm from '../components/NewMaintenanceForm.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { formatCurrency, formatMiles, formatMpg } from '../utils/format'
import { median } from '../utils/stats'

const gasStore = useGasStore()
const maintenanceStore = useMaintenanceStore()
const dashboardStore = useDashboardStore()
const mapStore = useMapStore()

const subTabs = [
  { key: 'gas', label: 'Gas log' },
  { key: 'maint', label: 'Maintenance log' },
]

const tab = ref('gas')
const search = ref('')
const showForm = ref(false)
const hideExcludedFillups = ref(false)
const editingFillup = ref(null)
const editingRecord = ref(null)
const pendingDelete = ref(null)
const deleting = ref(false)
const deleteError = ref('')

const searchPlaceholder = computed(() => (tab.value === 'gas' ? 'Search city, note or date…' : 'Search expense, place or vendor…'))

const visibleFillups = computed(() =>
  hideExcludedFillups.value ? gasStore.fillups.filter((r) => r.is_clean) : gasStore.fillups,
)

function matchesSearch(row, fields) {
  const q = search.value.trim().toLowerCase()
  if (!q) return true
  return fields.some((f) => row[f] != null && String(row[f]).toLowerCase().includes(q))
}

const searchedFillups = computed(() => visibleFillups.value.filter((r) => matchesSearch(r, ['date', 'city', 'notes'])))
const searchedRecords = computed(() =>
  maintenanceStore.records.filter((r) => matchesSearch(r, ['date', 'expense', 'place', 'vendor'])),
)

const rowCountText = computed(() => {
  if (tab.value === 'gas') return `${searchedFillups.value.length} of ${gasStore.fillups.length} rows`
  return `${searchedRecords.value.length} of ${maintenanceStore.records.length} rows`
})

const gasFooterText = computed(() => {
  const rows = searchedFillups.value
  const medMpg = median(rows.map((r) => r.mpg))
  const medPrice = median(rows.map((r) => r.cost_per_gal))
  return `Showing ${rows.length} of ${gasStore.fillups.length} · median ${medMpg != null ? formatMpg(medMpg) : '—'} mpg · median ${medPrice != null ? formatCurrency(medPrice) : '—'}/gal`
})

const maintFooterText = computed(() => {
  const rows = searchedRecords.value
  const medCost = median(rows.map((r) => r.cost))
  const maxCost = rows.length ? Math.max(...rows.map((r) => r.cost)) : null
  return `Showing ${rows.length} of ${maintenanceStore.records.length} · median ${medCost != null ? formatCurrency(medCost, { decimals: 0 }) : '—'} · largest ${maxCost != null ? formatCurrency(maxCost, { decimals: 0 }) : '—'}`
})

// Best-effort flag pill for a gas row, mirroring the substrings
// analytics.is_clean checks on the backend -- purely a display label, the
// authoritative exclusion decision is still the server's `is_clean` field.
// `driven == null` covers both a literal first entry AND any row the
// backend excluded for an unrelated reason (an odometer reset/backdated
// entry with no usable prior reading) -- check is_clean/notes first so
// those don't get mislabeled "first entry".
function flagOf(row) {
  if (!row.is_clean) {
    const notes = (row.notes || '').toLowerCase()
    if (notes.includes('not a full fillup')) return { text: 'partial fill', cls: 'amber' }
    if (/\best\b/.test(notes)) return { text: 'est. mileage', cls: 'amber' }
    return { text: 'excluded', cls: 'amber' }
  }
  if (row.driven == null) return { text: 'first entry', cls: 'neutral' }
  return null
}

onMounted(() => {
  gasStore.fetchAll()
  maintenanceStore.fetchAll()
})

const subhead = computed(() => {
  if (tab.value === 'gas') {
    const total = gasStore.fillups.length
    const clean = gasStore.fillups.filter((r) => r.is_clean).length
    return `${total} fill-ups logged — ${clean} clean, ${total - clean} excluded from MPG averages.`
  }
  const total = maintenanceStore.records.length
  const totalCost = maintenanceStore.records.reduce((s, r) => s + r.cost, 0)
  return `${total} maintenance line items, ${formatCurrency(totalCost, { decimals: 0 })} total — sortable and searchable.`
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
  // Maintenance stops are plotted on the map with their own detail (amount,
  // since-service miles) same as gas fill-ups -- see onFillupSaved above --
  // so an edit/add here needs to invalidate mapStore too, not just dashboard.
  dashboardStore.invalidate()
  mapStore.invalidate()
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
    } else {
      await maintenanceStore.remove(row.id)
    }
    dashboardStore.invalidate()
    mapStore.invalidate()
    pendingDelete.value = null
  } catch (err) {
    deleteError.value = err.message
  } finally {
    deleting.value = false
  }
}

const gasColumns = [
  { key: 'date', label: 'Date', width: '104px', mono: true },
  { key: 'city', label: 'City', width: '1fr', kind: 'city' },
  { key: 'odometer_miles', label: 'Odometer', width: '96px', num: true, fmt: formatMiles },
  { key: 'gallons', label: 'Gallons', width: '84px', num: true, fmt: (v) => v.toFixed(2) },
  { key: 'price', label: 'Price', width: '90px', num: true, fmt: (v) => formatCurrency(v) },
  { key: 'cost_per_gal', label: '$/gal', width: '78px', num: true, fmt: (v) => formatCurrency(v) },
  { key: 'driven', label: 'Miles since', width: '92px', num: true, fmt: (v) => (v != null ? formatMiles(v) : '—') },
  { key: 'mpg', label: 'MPG', width: '108px', kind: 'mpg' },
]

const maintColumns = [
  { key: 'date', label: 'Date', width: '104px', mono: true },
  { key: 'expense', label: 'Expense', width: '1fr' },
  { key: 'is_major', label: '', width: '64px', badge: (row) => (row.is_major ? { text: 'major', cls: 'major' } : null) },
  { key: 'place', label: 'Place', width: '168px' },
  { key: 'odometer_miles', label: 'Odometer', width: '96px', num: true, fmt: (v) => (v != null ? formatMiles(v) : '—') },
  { key: 'vendor', label: 'Vendor', width: '148px' },
  { key: 'cost', label: 'Cost', width: '104px', kind: 'costBar' },
]
</script>

<style scoped>
.wrap {
  max-width: 1440px;
  margin: 0 auto;
  padding: 26px 26px 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}
h1 {
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 4px;
}
.sub {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0;
}
.toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.search-wrap {
  position: relative;
  flex: 1;
  min-width: 240px;
  max-width: 380px;
}
.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  color: var(--text-muted);
  pointer-events: none;
}
.search-input {
  width: 100%;
  padding: 10px 12px 10px 34px;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  font-size: 13px;
  background: #fff;
}
.search-input:focus {
  outline: none;
  border-color: var(--ac);
}
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;
}
.checkbox-label input {
  display: none;
}
.checkbox-box {
  width: 15px;
  height: 15px;
  border-radius: 5px;
  border: 1px solid var(--card-border);
  display: inline-block;
  position: relative;
}
.checkbox-box.checked {
  background: var(--ac);
  border-color: var(--ac);
}
.checkbox-box.checked::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 1px;
  width: 4px;
  height: 8px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
.row-count {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}
.add-btn {
  white-space: nowrap;
}
</style>
