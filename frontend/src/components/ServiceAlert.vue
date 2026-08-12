<template>
  <div class="service-alert" :class="alert.level">
    <div class="icon">{{ ICONS[alert.level] }}</div>
    <div class="body">
      <div class="headline">{{ headline }}</div>
      <div class="detail">
        Last service {{ alert.last_service_date }} at {{ formatMiles(alert.last_service_odometer) }} mi — assumes a
        service every {{ formatMiles(SERVICE_INTERVAL_MILES) }} miles.
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatMiles } from '../utils/format'

const props = defineProps({
  alert: { type: Object, required: true },
})

const SERVICE_INTERVAL_MILES = 5000
const ICONS = { ok: '✓', due_soon: '⚠', overdue: '⚠' }

const headline = computed(() => {
  const a = props.alert
  if (a.level === 'overdue') {
    return `Service overdue by ${formatMiles(-a.miles_until_next)} miles`
  }
  return `${formatMiles(a.miles_until_next)} miles until next service`
})
</script>

<style scoped>
.service-alert {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px;
  border-radius: 12px;
  border: 1px solid var(--grid);
  margin-bottom: 26px;
}
.icon {
  font-size: 19px;
  line-height: 1.3;
}
.headline {
  font-weight: 700;
  font-size: 15px;
}
.detail {
  font-size: 12px;
  color: var(--muted);
  margin-top: 3px;
}
.service-alert.ok {
  border-color: var(--good);
  background: rgba(74, 222, 128, 0.08);
}
.service-alert.ok .icon,
.service-alert.ok .headline {
  color: var(--good);
}
.service-alert.due_soon {
  border-color: var(--warn);
  background: rgba(250, 204, 21, 0.08);
}
.service-alert.due_soon .icon,
.service-alert.due_soon .headline {
  color: var(--warn);
}
.service-alert.overdue {
  border-color: var(--accent3);
  background: rgba(248, 113, 113, 0.08);
}
.service-alert.overdue .icon,
.service-alert.overdue .headline {
  color: var(--accent3);
}
</style>
