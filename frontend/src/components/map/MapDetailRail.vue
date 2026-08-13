<template>
  <aside class="rail">
    <div v-if="stop" class="detail-block">
      <div class="detail-top">
        <span class="detail-date mono">{{ stop.date }}</span>
        <span class="kind-badge" :class="stop.type">{{ stop.type === 'gas' ? 'Gas fill-up' : 'Maintenance' }}</span>
      </div>
      <div class="detail-city">{{ stop.name }}</div>

      <div class="fact-grid">
        <template v-if="stop.type === 'gas'">
          <div class="fact-tile">
            <div class="fact-label">Total</div>
            <div class="fact-value">{{ formatCurrency(stop.amount, { decimals: 2 }) }}</div>
          </div>
          <div class="fact-tile">
            <div class="fact-label">Volume</div>
            <div class="fact-value">{{ stop.gallons != null ? stop.gallons.toFixed(1) + ' gal' : '—' }}</div>
          </div>
          <div class="fact-tile">
            <div class="fact-label">Odometer</div>
            <div class="fact-value">{{ formatMiles(stop.odometer_miles) }}</div>
          </div>
          <div class="fact-tile">
            <div class="fact-label">Economy</div>
            <div class="fact-value">{{ stop.mpg != null ? stop.mpg.toFixed(1) + ' mpg' : '—' }}</div>
          </div>
        </template>
        <template v-else>
          <div class="fact-tile">
            <div class="fact-label">Total</div>
            <div class="fact-value">{{ formatCurrency(stop.amount, { decimals: 0 }) }}</div>
          </div>
          <div class="fact-tile">
            <div class="fact-label">Work</div>
            <div class="fact-value truncate">{{ stop.detail || '—' }}</div>
          </div>
          <div class="fact-tile">
            <div class="fact-label">Odometer</div>
            <div class="fact-value">{{ stop.odometer_miles != null ? formatMiles(stop.odometer_miles) : '—' }}</div>
          </div>
          <div class="fact-tile">
            <div class="fact-label">Since service</div>
            <div class="fact-value">
              {{ stop.since_service_miles != null ? formatMiles(stop.since_service_miles) + ' mi' : '—' }}
            </div>
          </div>
        </template>
      </div>
    </div>
    <div v-else class="empty-block">Click a stop on the map or in the list below to see its details.</div>

    <div class="trip-stats">
      <div class="section-header">
        <span>Trip stats</span>
        <span class="visible-count">{{ visibleStopCount }} stops shown</span>
      </div>
      <div class="stat-row">
        <span>States visited</span>
        <span class="mono">{{ tripStats.states_visited }}</span>
      </div>
      <div class="stat-row">
        <span>Longest leg</span>
        <span class="mono">{{ tripStats.longest_leg_miles != null ? Math.round(tripStats.longest_leg_miles) + ' mi' : '—' }}</span>
      </div>
      <div class="stat-row">
        <span>Longest stay</span>
        <span class="mono">{{ tripStats.longest_stay_days != null ? tripStats.longest_stay_days + ' days' : '—' }}</span>
      </div>
      <div class="stat-row">
        <span>Avg between fill-ups</span>
        <span class="mono">{{ tripStats.avg_miles_between_fillups != null ? Math.round(tripStats.avg_miles_between_fillups) + ' mi' : '—' }}</span>
      </div>
      <div class="stat-row">
        <span>Maintenance stops</span>
        <span class="mono">{{ tripStats.maintenance_stops }}</span>
      </div>
    </div>

    <div class="recent-stops">
      <div class="section-header"><span>Recent stops</span></div>
      <div class="stops-list">
        <button
          v-for="s in recentStops"
          :key="s.id"
          type="button"
          class="stop-row"
          :class="{ selected: stop && stop.id === s.id }"
          @click="$emit('select', s)"
        >
          <span class="kind-dot" :class="s.type" />
          <span class="stop-date mono">{{ s.date.slice(5) }}</span>
          <span class="stop-city truncate">{{ s.name }}</span>
          <span class="stop-amount mono">{{ s.amount != null ? formatCurrency(s.amount, { decimals: 2 }) : '' }}</span>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { formatCurrency, formatMiles } from '../../utils/format'

defineProps({
  stop: { type: Object, default: null },
  tripStats: { type: Object, required: true },
  recentStops: { type: Array, required: true },
  visibleStopCount: { type: Number, required: true },
})
defineEmits(['select'])
</script>

<style scoped>
.rail {
  flex: 0 0 344px;
  background: #fff;
  border-left: 1px solid var(--card-border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.detail-block {
  padding: 20px;
  border-bottom: 1px solid var(--row-border);
}
.empty-block {
  padding: 20px;
  font-size: 12.5px;
  color: var(--text-muted);
  line-height: 1.5;
  border-bottom: 1px solid var(--row-border);
}
.detail-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.detail-date {
  font-size: 11.5px;
  color: var(--text-muted);
}
.kind-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 6px 11px;
  border-radius: 20px;
}
.kind-badge.gas {
  color: var(--ac);
  background: var(--ac-tint);
}
.kind-badge.maintenance {
  color: var(--rust);
  background: var(--rust-tint);
}
.detail-city {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 14px;
}
.fact-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 9px;
}
.fact-tile {
  background: var(--fill-subtle);
  border-radius: 10px;
  padding: 11px 12px;
}
.fact-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 3px;
}
.fact-value {
  font-size: 16px;
  font-weight: 600;
}
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trip-stats {
  padding: 16px 20px;
  border-bottom: 1px solid var(--row-border);
}
.section-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}
.visible-count {
  font-weight: 400;
  color: var(--text-muted);
}
.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 7px 0;
  border-bottom: 1px solid oklch(0.96 0.004 255);
  font-size: 12.5px;
}
.stat-row:last-child {
  border-bottom: none;
}
.stat-row span:first-child {
  color: var(--text-secondary);
}
.stat-row .mono {
  font-weight: 600;
}

.recent-stops {
  padding: 16px 20px;
  flex: 1;
}
.stops-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stop-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 6px;
  border-radius: 9px;
  border: none;
  background: none;
  cursor: pointer;
  text-align: left;
  width: 100%;
  font-size: 12px;
}
.stop-row.selected {
  background: var(--ac-tint);
}
.kind-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.kind-dot.gas {
  background: oklch(0.6 0.14 258);
}
.kind-dot.maintenance {
  background: var(--rust);
  border-radius: 2px;
  transform: rotate(45deg);
}
.stop-date {
  width: 40px;
  flex-shrink: 0;
  color: var(--text-muted);
}
.stop-city {
  flex: 1;
}
.stop-amount {
  flex-shrink: 0;
  color: var(--text-secondary);
}
</style>
