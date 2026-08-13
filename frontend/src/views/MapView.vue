<template>
  <div class="map-view">
    <div class="map-pane">
      <div ref="mapEl" class="map"></div>

      <div v-if="years.length" class="overlay-stack">
        <div class="panel card--overlay title-card">
          <div class="title-text">The bus's road trip</div>
          <p class="title-sub">{{ subhead }}</p>
        </div>

        <div class="panel card--overlay filter-card">
          <div class="filter-header">
            <span>Years</span>
            <span class="filter-actions">
              <button type="button" class="link-btn" @click="showAll">Show all</button>
              <button type="button" class="link-btn" @click="hideAll">Hide all</button>
            </span>
          </div>
          <div class="year-chips">
            <label
              v-for="y in years"
              :key="y.year"
              class="year-chip"
              :class="{ off: !visible[y.year] }"
              :style="visible[y.year] ? { borderColor: colorFor(y.year), background: tintFor(y.year) } : {}"
            >
              <input type="checkbox" v-model="visible[y.year]" @change="toggleYear(y.year)" />
              <span class="dot" :style="{ background: colorFor(y.year) }" />
              {{ y.year }} <span class="count">{{ y.locations.length }}</span>
            </label>
          </div>
          <hr />
          <div class="type-legend">
            <span class="type-item"><span class="legend-dot gas" />Gas fill-up</span>
            <span class="type-item"><span class="legend-diamond" />Maintenance</span>
          </div>
        </div>
      </div>

      <div class="zoom-control">
        <button type="button" @click="map && map.zoomIn()">+</button>
        <button type="button" @click="map && map.zoomOut()">−</button>
      </div>

      <div class="attribution">Leaflet · &copy; OpenStreetMap contributors &copy; CARTO</div>
    </div>

    <MapDetailRail
      :stop="selectedStop"
      :trip-stats="tripStats"
      :recent-stops="recentStops"
      :visible-stop-count="visibleStopCount"
      @select="selectStop"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, shallowRef } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useMapStore } from '../stores/mapStore'
import MapDetailRail from '../components/map/MapDetailRail.vue'
import { yearColor } from '../theme'

const store = useMapStore()
const mapEl = ref(null)
let map = null
const yearLayers = {}
const markersByStopId = {}
const visible = reactive({})
const selectedStop = shallowRef(null)

const TYPE_COLOR = { gas: 'oklch(0.6 0.14 258)', maintenance: 'oklch(0.6 0.14 35)' }

function colorFor(year) {
  const yearList = store.routeData?.years.map((y) => y.year) || []
  return yearColor(yearList.indexOf(year))
}
function tintFor(year) {
  return colorFor(year).replace('oklch(0.6 0.14', 'oklch(0.99 0.01')
}

const years = computed(() => store.routeData?.years || [])
const tripStats = computed(
  () =>
    store.routeData?.trip_stats || {
      states_visited: 0,
      longest_leg_miles: null,
      longest_stay_days: null,
      avg_miles_between_fillups: null,
      maintenance_stops: 0,
    },
)
const subhead = computed(() =>
  store.routeData
    ? `${store.routeData.total_stops} stops — fill-ups and maintenance visits — in chronological order, colored by year.`
    : 'Loading…',
)

const visibleStopCount = computed(() =>
  years.value.filter((y) => visible[y.year]).reduce((sum, y) => sum + y.locations.length, 0),
)

const recentStops = computed(() => {
  const flat = years.value.filter((y) => visible[y.year]).flatMap((y) => y.locations)
  return [...flat].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0)).slice(0, 30)
})

function selectStop(stop) {
  selectedStop.value = stop
  if (map && stop) {
    map.panTo([stop.latitude, stop.longitude])
  }
}

function gasIcon(color) {
  return L.divIcon({
    className: '',
    html: `<span style="display:block;width:8px;height:8px;border-radius:50%;background:${color};box-shadow:0 0 0 1.5px #fff, 0 1px 4px oklch(0.3 0.03 255 / .22);"></span>`,
    iconSize: [8, 8],
    iconAnchor: [4, 4],
  })
}
function maintIcon(color) {
  return L.divIcon({
    className: '',
    html: `<span style="display:block;width:9px;height:9px;background:#fff;border:2px solid ${color};transform:rotate(45deg);box-shadow:0 1px 4px oklch(0.3 0.03 255 / .22);"></span>`,
    iconSize: [9, 9],
    iconAnchor: [4.5, 4.5],
  })
}

function buildMap() {
  if (!store.routeData || map || !mapEl.value) return

  map = L.map(mapEl.value, { zoomControl: false }).setView([39, -98], 4)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map)

  const allBounds = []
  store.routeData.years.forEach((y) => {
    const color = colorFor(y.year)
    const layerGroup = L.layerGroup()
    const latlngs = y.locations.map((loc) => [loc.latitude, loc.longitude])
    L.polyline(latlngs, { color, weight: 2, opacity: 0.45 }).addTo(layerGroup)

    y.locations.forEach((loc) => {
      const icon = loc.type === 'gas' ? gasIcon(color) : maintIcon(color)
      const marker = L.marker([loc.latitude, loc.longitude], { icon })
      marker.on('click', () => selectStop(loc))
      marker.addTo(layerGroup)
      markersByStopId[loc.id] = marker
      allBounds.push([loc.latitude, loc.longitude])
    })

    layerGroup.addTo(map)
    yearLayers[y.year] = layerGroup
    visible[y.year] = true
  })

  if (allBounds.length) map.fitBounds(allBounds, { padding: [30, 30] })
}

function toggleYear(year) {
  if (!map || !yearLayers[year]) return
  if (visible[year]) yearLayers[year].addTo(map)
  else map.removeLayer(yearLayers[year])
}

function showAll() {
  Object.keys(visible).forEach((y) => {
    visible[y] = true
    toggleYear(y)
  })
}
function hideAll() {
  Object.keys(visible).forEach((y) => {
    visible[y] = false
    toggleYear(y)
  })
}

onMounted(async () => {
  await store.fetchAll()
  await nextTick()
  buildMap()
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<style scoped>
.map-view {
  height: calc(100vh - 62px);
  min-height: 460px;
  display: flex;
}
.map-pane {
  flex: 1;
  position: relative;
  min-width: 0;
}
.map {
  width: 100%;
  height: 100%;
}
.overlay-stack {
  position: absolute;
  left: 22px;
  top: 20px;
  max-width: 340px;
  display: flex;
  flex-direction: column;
  gap: 11px;
  z-index: 1000;
}
.title-card {
  padding: 16px 18px;
  margin-bottom: 0;
}
.title-text {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
}
.title-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}
.filter-card {
  padding: 14px 16px;
  margin-bottom: 0;
}
.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 10px;
}
.filter-actions {
  display: flex;
  gap: 10px;
}
.link-btn {
  background: none;
  border: none;
  color: var(--ac);
  font-size: 11.5px;
  font-weight: 500;
  cursor: pointer;
  padding: 0;
}
.year-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.year-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  border-radius: 20px;
  border: 1px solid oklch(0.85 0.01 255);
  background: #fff;
  color: oklch(0.68 0.012 255);
  font-size: 11.5px;
  cursor: pointer;
}
.year-chip:not(.off) {
  color: var(--text-primary);
}
.year-chip input {
  display: none;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.count {
  color: inherit;
  opacity: 0.7;
}
.filter-card hr {
  border: none;
  border-top: 1px solid var(--row-border);
  margin: 10px 0;
}
.type-legend {
  display: flex;
  gap: 14px;
  font-size: 12px;
  color: var(--text-muted);
}
.type-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: oklch(0.6 0.14 258);
}
.legend-diamond {
  width: 8px;
  height: 8px;
  background: #fff;
  border: 2px solid var(--rust);
  transform: rotate(45deg);
}
.zoom-control {
  position: absolute;
  top: 20px;
  right: 22px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  background: oklch(0.93 0.005 255);
  border-radius: 9px;
  padding: 1px;
  gap: 1px;
  box-shadow: var(--shadow-overlay);
}
.zoom-control button {
  width: 34px;
  height: 34px;
  border: none;
  background: #fff;
  font-size: 16px;
  cursor: pointer;
  color: var(--text-primary);
}
.zoom-control button:first-child {
  border-radius: 8px 8px 0 0;
}
.zoom-control button:last-child {
  border-radius: 0 0 8px 8px;
}
.attribution {
  position: absolute;
  right: 0;
  bottom: 0;
  z-index: 1000;
  font-size: 10px;
  color: var(--text-secondary);
  background: oklch(1 0 0 / 0.8);
  padding: 4px 8px;
  border-radius: 5px 0 0 0;
}
</style>
