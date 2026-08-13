<template>
  <div class="card panel">
    <div class="header-row">
      <div class="label">Next service</div>
      <span class="pill" :class="alert.level">{{ pillText }}</span>
    </div>

    <div class="hero-row">
      <span class="miles">{{ formatMiles(Math.abs(alert.miles_until_next)) }}</span>
      <span class="sub">{{ alert.miles_until_next >= 0 ? 'miles to go' : 'miles overdue' }}</span>
    </div>

    <div class="progress">
      <div class="track">
        <div class="fill" :class="alert.level" :style="{ width: alert.progress_pct + '%' }" />
      </div>
      <div class="endpoints mono">
        <span>{{ formatMiles(alert.last_service_odometer) }}</span>
        <span>{{ formatMiles(alert.last_service_odometer + alert.interval_miles) }}</span>
      </div>
    </div>

    <p class="note">
      Last service {{ formatDate(alert.last_service_date) }} at {{ formatMiles(alert.last_service_odometer) }} mi.
      Interval assumed at {{ formatMiles(alert.interval_miles) }} miles.
    </p>

    <button type="button" class="btn tertiary log-btn" @click="$emit('log-service')">Log a service visit</button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatMiles } from '../../utils/format'

const props = defineProps({
  alert: { type: Object, required: true },
})
defineEmits(['log-service'])

const PILL_TEXT = { ok: 'On track', due_soon: 'Due soon', overdue: 'Overdue' }
const pillText = computed(() => PILL_TEXT[props.alert.level] || props.alert.level)

function formatDate(iso) {
  return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.card {
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 0;
}
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
}
.pill {
  font-size: 11px;
  font-weight: 500;
  border-radius: 20px;
  padding: 5px 10px;
}
.pill.ok {
  color: var(--green-text);
  background: var(--green-tint);
}
.pill.due_soon {
  color: var(--amber-text);
  background: var(--amber-tint);
}
.pill.overdue {
  color: var(--severe-red);
  background: var(--rust-tint);
}
.hero-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.miles {
  font-size: 34px;
  font-weight: 600;
}
.sub {
  font-size: 13px;
  color: var(--text-muted);
}
.progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.track {
  height: 9px;
  border-radius: 6px;
  background: var(--track);
  overflow: hidden;
}
.fill {
  height: 100%;
  background: var(--green);
  border-radius: 6px;
}
.fill.due_soon {
  background: var(--amber-text);
}
.fill.overdue {
  background: var(--severe-red);
}
.endpoints {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-muted);
}
.note {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.55;
  margin: 0;
}
.log-btn {
  margin-top: auto;
  width: 100%;
}
</style>
