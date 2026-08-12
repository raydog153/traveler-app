<template>
  <div class="wrap">
    <h1>🚌 The Bus's Road Trip</h1>
    <p class="sub">{{ subhead }}</p>

    <div v-if="years.length" class="legend">
      <label v-for="y in years" :key="y.year" class="legend-item" :class="{ off: !visible[y.year] }">
        <input type="checkbox" v-model="visible[y.year]" @change="toggleYear(y.year)" />
        <span class="swatch" :style="{ background: colorFor(y.year) }"></span>
        {{ y.year }} <span class="count">({{ y.locations.length }})</span>
      </label>
      <div class="legend-actions">
        <button class="btn secondary" @click="showAll">Show all</button>
        <button class="btn secondary" @click="hideAll">Hide all</button>
      </div>
    </div>

    <div v-if="years.length" class="type-legend">
      <span class="type-item"><span class="swatch" :style="{ background: TYPE_COLORS.gas }"></span>Gas fill-up</span>
      <span class="type-item"
        ><span class="swatch" :style="{ background: TYPE_COLORS.maintenance }"></span>Maintenance</span
      >
    </div>

    <div ref="mapEl" class="map"></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useMapStore } from '../stores/mapStore'

const store = useMapStore()
const mapEl = ref(null)
let map = null
const yearLayers = {}
const visible = reactive({})

const YEAR_COLORS = ['#facc15', '#ff8a3d', '#3ddcff', '#a78bfa', '#4ade80', '#f87171']
const TYPE_COLORS = { gas: '#9ca3af', maintenance: '#ef4444' }

function colorFor(year) {
  const years = store.routeData?.years.map((y) => y.year) || []
  const idx = years.indexOf(year)
  return YEAR_COLORS[idx % YEAR_COLORS.length]
}

const years = computed(() => store.routeData?.years || [])
const subhead = computed(() =>
  store.routeData
    ? `${store.routeData.total_stops} stops (fill-ups and maintenance visits), connected in chronological order and colored by year.`
    : 'Loading…',
)

function popupHtml(loc) {
  const detail = loc.detail ? `<br>${loc.detail}` : ''
  return `<b>${loc.name}</b><br>${loc.date}${detail}`
}

function buildMap() {
  if (!store.routeData || map || !mapEl.value) return

  map = L.map(mapEl.value, { zoomControl: true }).setView([39, -98], 4)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map)

  const allBounds = []
  store.routeData.years.forEach((y) => {
    const color = colorFor(y.year)
    const layerGroup = L.layerGroup()
    const latlngs = y.locations.map((loc) => [loc.latitude, loc.longitude])
    L.polyline(latlngs, { color, weight: 2.5, opacity: 0.8 }).addTo(layerGroup)

    y.locations.forEach((loc) => {
      const marker = L.circleMarker([loc.latitude, loc.longitude], {
        radius: 5,
        fillColor: TYPE_COLORS[loc.type],
        color: '#0f1720',
        weight: 1,
        fillOpacity: 0.9,
      })
      marker.bindPopup(popupHtml(loc))
      marker.addTo(layerGroup)
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
.wrap {
  max-width: 1180px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 180px);
  min-height: 500px;
}
h1 {
  font-size: 19px;
  margin: 0 0 4px;
}
.sub {
  font-size: 12.5px;
  color: var(--muted);
  margin: 0 0 12px;
}
.legend {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--grid);
  font-size: 12.5px;
  margin-bottom: 12px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
  background: var(--panel);
  border: 1px solid var(--grid);
  border-radius: 20px;
  padding: 5px 12px 5px 8px;
  transition: opacity 0.15s;
}
.legend-item.off {
  opacity: 0.4;
}
.legend-item input {
  display: none;
}
.legend-item .count {
  color: var(--muted);
  font-size: 11px;
}
.swatch {
  width: 11px;
  height: 11px;
  border-radius: 3px;
  display: inline-block;
  flex-shrink: 0;
}
.legend-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}
.type-legend {
  display: flex;
  gap: 14px;
  font-size: 12px;
  color: var(--muted);
  margin: -4px 0 12px;
}
.type-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.map {
  flex: 1;
  min-height: 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--grid);
}
</style>

<style>
/* Leaflet injects popup DOM outside Vue's render tree, so these can't be
   scoped -- they style the popup to match the app's dark theme. */
.leaflet-popup-content-wrapper {
  background: #1c2733;
  color: var(--text);
  border-radius: 8px;
}
.leaflet-popup-tip {
  background: #1c2733;
}
.leaflet-popup-content {
  font-size: 12.5px;
  margin: 10px 12px;
}
.leaflet-popup-content b {
  color: #ff8a3d;
}
.leaflet-popup-close-button {
  color: var(--muted) !important;
}
</style>
