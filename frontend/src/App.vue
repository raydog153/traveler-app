<template>
  <div class="app-shell">
    <header class="app-nav">
      <span class="brand"><span class="brand-emoji">🚌</span>Bus Living</span>
      <nav class="tab-bar">
        <RouterLink v-for="t in navTabs" :key="t.to" :to="t.to" class="tab-link">{{ t.label }}</RouterLink>
      </nav>
      <div class="right-cluster">
        <span class="odo-label">Odometer</span>
        <span class="odo-value mono">{{ odometerLabel }}</span>
        <span class="divider" />
        <span class="sync-dot" :class="{ error: syncError }" />
        <span class="sync-label">{{ syncError ? 'Sync failed' : lastSyncLabel }}</span>
      </div>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useDashboardStore } from './stores/dashboardStore'
import { formatMiles } from './utils/format'

const navTabs = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/find-places', label: 'Find places' },
  { to: '/map', label: 'Map' },
  { to: '/log', label: 'Data log' },
]

const store = useDashboardStore()
const lastSync = ref(new Date())

const odometerLabel = computed(() => {
  const odo = store.summary?.service_alert?.current_odometer
  return odo != null ? `${formatMiles(odo)} mi` : '—'
})

// resourceStore's fetchAll() never rejects (it records failures on
// store.error and resolves normally), so this reads the store's reactive
// error state directly rather than try/catch around the call below --
// staying correct even when DashboardView's own onMounted resolves the
// fetch first and this component's own call just rides its in-flight promise.
const syncError = computed(() => !!store.error)

const lastSyncLabel = computed(() =>
  lastSync.value.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }),
)

onMounted(() => {
  store.fetchAll()
})
</script>

<style scoped>
.app-shell {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.app-nav {
  height: 62px;
  flex: 0 0 62px;
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 0 26px;
  border-bottom: 1px solid var(--header-border);
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 30;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 15px;
  letter-spacing: -0.015em;
  white-space: nowrap;
}
.brand-emoji {
  font-size: 19px;
}

.tab-bar {
  display: inline-flex;
  background: oklch(0.965 0.004 255);
  padding: 4px;
  border-radius: 11px;
  gap: 3px;
}

.tab-link {
  text-decoration: none;
  color: var(--text-muted);
  font-size: 12.5px;
  font-weight: 500;
  padding: 8px 15px;
  border-radius: 8px;
}

.tab-link.router-link-active {
  background: #fff;
  color: var(--text-primary);
  box-shadow: var(--shadow-tab);
}

.right-cluster {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 14px;
  white-space: nowrap;
}

.odo-label {
  font-weight: 400;
  font-size: 12px;
  color: oklch(0.56 0.012 255);
}
.odo-value {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
}
.divider {
  width: 1px;
  height: 20px;
  background: oklch(0.92 0.005 255);
}
.sync-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
  animation: pulse 2.6s ease-in-out infinite;
}
.sync-dot.error {
  background: oklch(0.75 0.14 75);
  animation: none;
}
.sync-label {
  font-size: 12px;
  color: oklch(0.5 0.012 255);
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

.app-main {
  flex: 1;
  min-height: 0;
}
</style>
