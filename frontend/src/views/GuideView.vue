<template>
  <div class="wrap">
    <h1>🐾 Traveler Guide</h1>
    <p class="sub">Dog parks, playgrounds, trailheads and more — searchable near any city.</p>

    <div v-if="configError" class="config-error">
      Google Maps isn't configured: set <code>GOOGLE_MAPS_API_KEY</code> in your <code>.env</code> file
      (Maps JavaScript API, Places API (New), and Geocoding API must be enabled with billing active), then
      restart the frontend.
    </div>

    <div v-else class="guide-layout">
      <aside class="sidebar">
        <div class="type-select">
          <button
            type="button"
            class="type-select-btn"
            aria-haspopup="true"
            :aria-expanded="typeMenuOpen"
            @click="typeMenuOpen = !typeMenuOpen"
          >
            <span class="type-select-label">{{ typeSelectLabel }}</span>
            <span class="type-select-caret" :class="{ open: typeMenuOpen }">▾</span>
          </button>
          <div v-if="typeMenuOpen" class="type-select-menu" ref="typeMenuEl">
            <label v-for="c in CATEGORIES" :key="c.key" class="type-option">
              <input type="checkbox" :value="c.key" v-model="selectedCategories" />
              <span>{{ c.bullet }} {{ c.label }}</span>
            </label>
          </div>
        </div>

        <div class="search-row">
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Search a city or address…"
            aria-label="Search a city or address"
            @keydown.enter.prevent="runSearchQuery"
          />
          <button type="button" class="btn" @click="runSearchQuery">Go</button>
        </div>
        <button type="button" class="btn secondary locate-btn" @click="useMyLocation">📍 Use my location</button>

        <div class="status" :class="{ error: statusIsError }" role="status" aria-live="polite">{{ status }}</div>

        <ul class="park-list">
          <li
            v-for="park in parks"
            :key="park.name + park.lat + park.lon"
            class="park-card"
            :class="{ active: park === activePark }"
            tabindex="0"
            role="button"
            @click="activatePark(park)"
            @keydown.enter.prevent="activatePark(park)"
            @keydown.space.prevent="activatePark(park)"
          >
            <div class="park-name"><span class="bullet">{{ CATEGORY_BY_KEY[park.categoryKey].bullet }}</span>{{ park.name }}</div>
            <div class="park-addr">{{ park.address }}</div>
            <div class="park-dist">{{ park.distance.toFixed(1) }} mi away</div>
          </li>
          <li v-if="!loading && parks.length === 0" class="empty-state">{{ emptyStateText }}</li>
        </ul>
      </aside>

      <div class="map-wrap">
        <div ref="mapEl" class="map"></div>
        <button v-if="showSearchAreaBtn" type="button" class="search-area-btn" @click="searchThisArea">
          🔍 Search this area
        </button>
      </div>
    </div>
  </div>
</template>

<script>
// Runs once per module load (not per component instance) -- defines
// google.maps.importLibrary as a lazy loader. Safe to call multiple times
// (it no-ops with a console warning once the real library has loaded), but
// only worth doing at all if a key is actually configured.
const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY

if (GOOGLE_MAPS_API_KEY) {
  ;(g => {
    var h, a, k, p = 'The Google Maps JavaScript API', c = 'google', l = 'importLibrary', q = '__ib__', m = document, b = window
    b = b[c] || (b[c] = {})
    var d = b.maps || (b.maps = {}), r = new Set(), e = new URLSearchParams(),
      u = () =>
        h ||
        (h = new Promise(async (f, n) => {
          await (a = m.createElement('script'))
          e.set('libraries', [...r] + '')
          for (k in g) e.set(k.replace(/[A-Z]/g, t => '_' + t[0].toLowerCase()), g[k])
          e.set('callback', c + '.maps.' + q)
          a.src = `https://maps.${c}apis.com/maps/api/js?` + e
          d[q] = f
          a.onerror = () => (h = n(Error(p + ' could not load.')))
          a.nonce = m.querySelector('script[nonce]')?.nonce || ''
          m.head.append(a)
        }))
    d[l] ? console.warn(p + ' only loads once. Ignoring:', g) : (d[l] = (f, ...n) => r.add(f) && u().then(() => d[l](f, ...n)))
  })({ key: GOOGLE_MAPS_API_KEY, v: 'weekly', loading: 'async' })
}

const CATEGORIES = [
  { key: 'dog_park', label: 'Dog Parks', includedPrimaryTypes: ['dog_park'], iconGlyph: 'paw', bullet: '🐾', singular: 'dog park', plural: 'dog parks' },
  { key: 'playground', label: 'Kid Playgrounds', includedPrimaryTypes: ['playground'], iconGlyph: 'playground', bullet: '🛝', singular: 'playground', plural: 'playgrounds' },
  { key: 'boat_launch', label: 'Boat Launches', includedPrimaryTypes: ['marina'], iconGlyph: 'anchor', bullet: '⚓', singular: 'boat launch', plural: 'boat launches' },
  { key: 'trailhead', label: 'Trailheads', includedPrimaryTypes: ['hiking_area'], iconGlyph: 'trailhead', bullet: '🥾', singular: 'trailhead', plural: 'trailheads' },
  { key: 'park', label: 'Parks', includedPrimaryTypes: ['park'], bullet: '🍃', singular: 'park', plural: 'parks' },
  { key: 'city_park', label: 'City Parks', includedPrimaryTypes: ['city_park'], bullet: '🌳', singular: 'city park', plural: 'city parks' },
  { key: 'state_park', label: 'State Parks', includedPrimaryTypes: ['state_park'], bullet: '🌲', singular: 'state park', plural: 'state parks' },
  { key: 'national_park', label: 'National Parks', includedPrimaryTypes: ['national_park'], bullet: '🏞️', singular: 'national park', plural: 'national parks' },
  { key: 'wildlife_park', label: 'Wildlife Parks', includedPrimaryTypes: ['wildlife_park'], bullet: '🦌', singular: 'wildlife park', plural: 'wildlife parks' },
  { key: 'wildlife_refuge', label: 'Wildlife Refuges', includedPrimaryTypes: ['wildlife_refuge'], bullet: '🦉', singular: 'wildlife refuge', plural: 'wildlife refuges' },
  { key: 'nature_preserve', label: 'Nature Preserves', includedPrimaryTypes: ['nature_preserve'], bullet: '🌿', singular: 'nature preserve', plural: 'nature preserves' },
  { key: 'scenic_spot', label: 'Scenic Spots', includedPrimaryTypes: ['scenic_spot'], bullet: '📸', singular: 'scenic spot', plural: 'scenic spots' },
  { key: 'water_park', label: 'Water Parks', includedPrimaryTypes: ['water_park'], bullet: '🌊', singular: 'water park', plural: 'water parks' },
  { key: 'cycling_park', label: 'Cycling Parks', includedPrimaryTypes: ['cycling_park'], bullet: '🚴', singular: 'cycling park', plural: 'cycling parks' },
  { key: 'skateboard_park', label: 'Skate Parks', includedPrimaryTypes: ['skateboard_park'], bullet: '🛹', singular: 'skate park', plural: 'skate parks' },
  { key: 'off_roading_area', label: 'Off-Roading Areas', includedPrimaryTypes: ['off_roading_area'], bullet: '🚙', singular: 'off-roading area', plural: 'off-roading areas' },
  { key: 'picnic_ground', label: 'Picnic Grounds', includedPrimaryTypes: ['picnic_ground'], bullet: '🧺', singular: 'picnic ground', plural: 'picnic grounds' },
  { key: 'campground', label: 'Campgrounds', includedPrimaryTypes: ['campground'], bullet: '⛺', singular: 'campground', plural: 'campgrounds' },
  { key: 'farmstay', label: 'Farmstays', includedPrimaryTypes: ['farmstay'], bullet: '🚜', singular: 'farmstay', plural: 'farmstays' },
  { key: 'visitor_center', label: 'Visitor Centers', includedPrimaryTypes: ['visitor_center'], bullet: 'ℹ️', singular: 'visitor center', plural: 'visitor centers' },
  { key: 'park_and_ride', label: 'Park & Ride', includedPrimaryTypes: ['park_and_ride'], bullet: '🅿️', singular: 'park & ride lot', plural: 'park & ride lots' },
  { key: 'farmers_market', label: 'Farmers Markets', includedPrimaryTypes: ['farmers_market'], bullet: '🥕', singular: 'farmers market', plural: 'farmers markets' },
  { key: 'thrift_store', label: 'Thrift Stores', includedPrimaryTypes: ['thrift_store'], bullet: '👕', singular: 'thrift store', plural: 'thrift stores' },
]
const CATEGORY_BY_KEY = Object.fromEntries(CATEGORIES.map(c => [c.key, c]))

// Marker glyphs drawn in the app's accent color so pins read consistently
// with the rest of the UI regardless of place type.
const ACCENT = '#ff8a3d'
const INK = '#0f1720'

const ICON_PATHS = {
  paw: '<g fill="' + ACCENT + '" stroke="' + INK + '" stroke-width="1.5"><ellipse cx="20" cy="26" rx="10" ry="8"/><ellipse cx="9" cy="14" rx="4.2" ry="5.2"/><ellipse cx="18" cy="9" rx="4.2" ry="5.4"/><ellipse cx="28" cy="10" rx="4.2" ry="5.2"/><ellipse cx="34" cy="18" rx="4" ry="5"/></g>',
  playground:
    '<g fill="none" stroke="' + INK + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="34" x2="6" y2="9"/><line x1="34" y1="34" x2="34" y2="9"/><line x1="6" y1="9" x2="34" y2="9"/><line x1="16" y1="9" x2="12" y2="27"/><line x1="24" y1="9" x2="28" y2="27"/></g><g fill="' +
    ACCENT +
    '" stroke="' + INK + '" stroke-width="1.5" stroke-linejoin="round"><rect x="7" y="27" width="9" height="4" rx="1.5"/><rect x="24" y="27" width="9" height="4" rx="1.5"/></g>',
  anchor:
    '<g fill="none" stroke="' + INK + '" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="20" y1="13" x2="20" y2="32"/><line x1="11" y1="18" x2="29" y2="18"/><path d="M8 22 A12 12 0 0 0 20 34"/><path d="M32 22 A12 12 0 0 1 20 34"/></g><circle cx="20" cy="9" r="4.2" fill="' +
    ACCENT +
    '" stroke="' + INK + '" stroke-width="1.8"/>',
  trailhead:
    '<path d="M4 31 L15 12 L21 22 L25 16 L36 31 Z" fill="none" stroke="' +
    INK +
    '" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/><path d="M15 12 L19 18 L11 18 Z" fill="' +
    ACCENT +
    '" stroke="' + INK + '" stroke-width="1.5" stroke-linejoin="round"/>',
}

const emojiIconCache = {}
function emojiIconUrl(emoji) {
  if (emojiIconCache[emoji]) return emojiIconCache[emoji]
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><circle cx="20" cy="20" r="17" fill="' +
    ACCENT +
    '" stroke="' + INK + '" stroke-width="2"/><text x="20" y="27" font-size="19" text-anchor="middle">' + emoji + '</text></svg>'
  const url = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg)
  emojiIconCache[emoji] = url
  return url
}

function categoryIconUrl(category) {
  if (!category.iconGlyph) return emojiIconUrl(category.bullet)
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">' + ICON_PATHS[category.iconGlyph] + '</svg>'
  return 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg)
}

// Dark map theme matching the app's existing chart/panel palette (bg/panel/
// panel2/grid/muted from style.css) instead of Google's default light map.
const MAP_STYLES = [
  { elementType: 'geometry', stylers: [{ color: '#161f2b' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#8fa1b3' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#0f1720' }] },
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#1e3324' }] },
  { featureType: 'poi.park', elementType: 'labels', stylers: [{ visibility: 'off' }] },
  { featureType: 'transit', stylers: [{ visibility: 'off' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#26323f' }] },
  { featureType: 'road.arterial', elementType: 'geometry', stylers: [{ color: '#1c2733' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#2f3d4c' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#12202b' }] },
  { featureType: 'administrative', elementType: 'geometry.stroke', stylers: [{ color: '#26323f' }] },
]

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch])
}

function milesBetween(lat1, lon1, lat2, lon2) {
  const R = 3958.8
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLon = ((lon2 - lon1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

</script>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'

const US_CENTER = { lat: 39, lng: -98 } // fallback view when location isn't available
const SEARCH_RADIUS_M = 16000 // ~10 miles -- default for location/city searches
const METERS_PER_MILE = 1609.34
const GOOGLE_MAX_RADIUS_M = 50000 // Places API (New) locationRestriction.circle.radius cap
const MIN_VIEWPORT_RADIUS_M = 500 // floor so "search this area" at max zoom-in isn't a ~0m circle
const RESEARCH_TRIGGER_MI = 1.5
const LOCATION_DEFAULT_CATEGORIES = ['dog_park', 'wildlife_refuge', 'farmers_market']

const configError = ref(!GOOGLE_MAPS_API_KEY)
const mapEl = ref(null)
const typeMenuEl = ref(null)

const selectedCategories = ref([])
const typeMenuOpen = ref(false)
const searchQuery = ref('')
const status = ref('Getting your location…')
const statusIsError = ref(false)
// shallowRef, not ref: park objects carry a live google.maps Marker instance
// (place.marker below) -- deep-reactifying that would wrap it in a Proxy and
// risk breaking its internal state, and would make marker-click vs.
// list-click identity comparisons (`park === activePark`) fail since one
// side would be the raw object and the other the reactive proxy.
const parks = shallowRef([])
const activePark = shallowRef(null)
const showSearchAreaBtn = ref(false)
const loading = ref(false)

let map, Place, SearchNearbyRankPreference, Marker, InfoWindow, Geocoder
let geocoder, infoWindow
let markers = []
let userMarker = null
let lastSearchCenter = US_CENTER
let suppressNextIdle = false
let searchDebounceTimer = null
// Set right before a programmatic (non-user-click) change to
// selectedCategories, e.g. locateOnLoad's default categories -- lets that
// caller drive its own searchPlaces() call with fresh coordinates instead of
// racing the categories watcher below, which only knows the stale
// lastSearchCenter until that caller updates it.
let suppressCategoryWatch = false

const typeSelectLabel = computed(() => {
  if (selectedCategories.value.length === 0) return 'Select place types…'
  if (selectedCategories.value.length === 1) {
    const only = CATEGORY_BY_KEY[selectedCategories.value[0]]
    return only.bullet + ' ' + only.label
  }
  const bullets = selectedCategories.value.map(k => CATEGORY_BY_KEY[k].bullet).join(' ')
  return bullets + ' ' + selectedCategories.value.length + ' types selected'
})

const emptyStateText = computed(() =>
  selectedCategories.value.length === 0
    ? 'Select at least one place type above.'
    : 'Nothing here yet — pan the map or search another city to look elsewhere.',
)

function setStatus(text, isError) {
  status.value = text
  statusIsError.value = !!isError
}

function clearMarkers() {
  markers.forEach(m => m.setMap(null))
  markers = []
  parks.value = []
  activePark.value = null
  if (infoWindow) infoWindow.close()
}

function openPark(park) {
  const html =
    '<div class="popup-name">' +
    escapeHtml(park.name) +
    '</div><div class="popup-addr">' +
    escapeHtml(park.address) +
    '</div><a class="popup-link" target="_blank" rel="noopener" href="https://www.google.com/maps/dir/?api=1&destination=' +
    park.lat +
    ',' +
    park.lon +
    '">Get directions →</a>'
  infoWindow.setContent(html)
  infoWindow.open({ map, anchor: park.marker })
  if (park.marker.setAnimation) {
    park.marker.setAnimation(google.maps.Animation.BOUNCE)
    setTimeout(() => park.marker.setAnimation(null), 650)
  }
  activePark.value = park
}

function activatePark(park) {
  suppressNextIdle = true
  map.panTo({ lat: park.lat, lng: park.lon })
  map.setZoom(15)
  openPark(park)
}

function searchOneCategory(key, lat, lon, radiusM) {
  const category = CATEGORY_BY_KEY[key]
  const request = {
    fields: ['displayName', 'location', 'formattedAddress'],
    locationRestriction: { center: { lat, lng: lon }, radius: radiusM },
    includedPrimaryTypes: category.includedPrimaryTypes,
    maxResultCount: 20,
    rankPreference: SearchNearbyRankPreference.DISTANCE,
  }

  return Place.searchNearby(request)
    .then(result => {
      const places = result.places || []
      return places
        .filter(p => p.location)
        .map(p => {
          const plat = p.location.lat()
          const plon = p.location.lng()
          return {
            name: p.displayName || 'Unnamed ' + category.singular,
            address: p.formattedAddress || 'Address not listed',
            lat: plat,
            lon: plon,
            distance: milesBetween(lat, lon, plat, plon),
            categoryKey: key,
          }
        })
    })
    .catch(err => {
      console.error('Places Nearby Search failed for ' + key + ':', err)
      return { failedCategory: key }
    })
}

function summarizeCounts(places) {
  const counts = {}
  const order = []
  places.forEach(p => {
    if (!counts[p.categoryKey]) order.push(p.categoryKey)
    counts[p.categoryKey] = (counts[p.categoryKey] || 0) + 1
  })
  if (order.length <= 1) return ''
  return order
    .map(key => {
      const category = CATEGORY_BY_KEY[key]
      const n = counts[key]
      return n + ' ' + (n === 1 ? category.singular : category.plural)
    })
    .join(', ')
}

function searchPlaces(lat, lon, { fitBounds = true, radiusM = SEARCH_RADIUS_M } = {}) {
  if (loading.value) return
  if (selectedCategories.value.length === 0) {
    clearMarkers()
    setStatus('Select at least one place type above.')
    return
  }
  loading.value = true
  lastSearchCenter = { lat, lng: lon }
  showSearchAreaBtn.value = false
  setStatus('Finding places nearby…')
  clearMarkers()

  const radiusMiles = Math.round(radiusM / METERS_PER_MILE)
  const radiusLabel = radiusMiles + (radiusMiles === 1 ? ' mile' : ' miles')

  const categories = selectedCategories.value.slice()
  Promise.all(categories.map(key => searchOneCategory(key, lat, lon, radiusM))).then(resultsPerCategory => {
    const failedCategories = []
    let allPlaces = []
    resultsPerCategory.forEach(r => {
      if (r && r.failedCategory) failedCategories.push(r.failedCategory)
      else allPlaces = allPlaces.concat(r)
    })

    allPlaces.sort((a, b) => a.distance - b.distance)

    if (allPlaces.length === 0) {
      if (failedCategories.length === categories.length) {
        setStatus('Couldn\'t load places from Google. Check that "Places API (New)" is enabled and billing is active for this key.', true)
      } else {
        setStatus('Nothing found within ' + radiusLabel + ' for the selected types. Try different types or search another area.')
      }
      loading.value = false
      return
    }

    allPlaces.forEach(place => {
      const category = CATEGORY_BY_KEY[place.categoryKey]
      const marker = new Marker({
        position: { lat: place.lat, lng: place.lon },
        map,
        title: place.name,
        icon: {
          url: categoryIconUrl(category),
          scaledSize: new google.maps.Size(32, 32),
          anchor: new google.maps.Point(16, 29),
        },
      })
      marker.addListener('click', () => openPark(place))
      place.marker = marker
      markers.push(marker)
    })
    parks.value = allPlaces
    if (fitBounds) fitMapToResults(lat, lon, allPlaces)

    const summary = summarizeCounts(allPlaces)
    let statusMsg =
      allPlaces.length + (allPlaces.length === 1 ? ' place' : ' places') + ' found within ' + radiusLabel + (summary ? ' (' + summary + ')' : '') + '.'
    if (failedCategories.length > 0) statusMsg += ' Some types failed to load — see console.'
    setStatus(statusMsg)
    loading.value = false
  })
}

function moveMapTo(lat, lon, zoom) {
  suppressNextIdle = true
  map.panTo({ lat, lng: lon })
  if (zoom) map.setZoom(zoom)
}

// A fixed post-search zoom (as the original page used) leaves farther-out
// results genuinely found within the 10-mile radius -- and listed in the
// sidebar -- sitting outside the visible map, which reads as "the search
// isn't using the full radius" even though it is. Frame the map to whatever
// was actually found instead, capped so a single very-close result doesn't
// zoom in to street level.
function fitMapToResults(centerLat, centerLon, places) {
  const bounds = new google.maps.LatLngBounds()
  bounds.extend({ lat: centerLat, lng: centerLon })
  places.forEach(p => bounds.extend({ lat: p.lat, lng: p.lon }))
  suppressNextIdle = true
  map.fitBounds(bounds, 40)
  google.maps.event.addListenerOnce(map, 'idle', () => {
    if (map.getZoom() > 15) {
      suppressNextIdle = true
      map.setZoom(15)
    }
  })
}

function onMapIdle() {
  if (suppressNextIdle) {
    suppressNextIdle = false
    return
  }
  if (loading.value) return
  const c = map.getCenter()
  const dist = milesBetween(c.lat(), c.lng(), lastSearchCenter.lat, lastSearchCenter.lng)
  if (dist > RESEARCH_TRIGGER_MI) showSearchAreaBtn.value = true
}

// "Search this area" means the area actually on screen -- at a
// zoomed-out (e.g. multi-state) view the fixed default SEARCH_RADIUS_M
// (~10mi) would only ever cover a small dot in the middle of the viewport,
// which reads as "results only show in the center." Derive the radius from
// how far the current viewport actually spans instead.
function viewportRadiusMeters() {
  const bounds = map.getBounds()
  if (!bounds) return SEARCH_RADIUS_M
  const center = map.getCenter()
  const ne = bounds.getNorthEast()
  const milesToCorner = milesBetween(center.lat(), center.lng(), ne.lat(), ne.lng())
  const metersToCorner = milesToCorner * METERS_PER_MILE
  return Math.min(Math.max(metersToCorner, MIN_VIEWPORT_RADIUS_M), GOOGLE_MAX_RADIUS_M)
}

function searchThisArea() {
  // User explicitly framed the map before clicking this -- respect that
  // zoom/pan rather than re-fitting to whatever comes back, and search the
  // area actually visible rather than a fixed default radius.
  const c = map.getCenter()
  searchPlaces(c.lat(), c.lng(), { fitBounds: false, radiusM: viewportRadiusMeters() })
}

watch(selectedCategories, () => {
  if (suppressCategoryWatch) {
    suppressCategoryWatch = false
    return
  }
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  if (selectedCategories.value.length === 0) {
    clearMarkers()
    setStatus('Select at least one place type above.')
    return
  }
  searchDebounceTimer = setTimeout(() => {
    searchPlaces(lastSearchCenter.lat, lastSearchCenter.lng)
  }, 350)
})

function onDocumentClick(e) {
  if (typeMenuOpen.value && typeMenuEl.value && !typeMenuEl.value.contains(e.target) && !e.target.closest('.type-select-btn')) {
    typeMenuOpen.value = false
  }
}
function onDocumentKeydown(e) {
  if (e.key === 'Escape') typeMenuOpen.value = false
}

function placeUserMarker(lat, lon) {
  if (userMarker) userMarker.setMap(null)
  userMarker = new Marker({
    position: { lat, lng: lon },
    map,
    zIndex: 1000,
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 8,
      fillColor: '#3ddcff',
      fillOpacity: 1,
      strokeColor: '#0f1720',
      strokeWeight: 2,
    },
  })
}

function useMyLocation() {
  if (!navigator.geolocation) {
    setStatus("Location isn't supported in this browser. Try searching a city instead.", true)
    return
  }
  setStatus('Getting your location…')
  navigator.geolocation.getCurrentPosition(
    pos => {
      const lat = pos.coords.latitude
      const lon = pos.coords.longitude
      placeUserMarker(lat, lon)
      moveMapTo(lat, lon, 13)
      searchPlaces(lat, lon)
    },
    () => setStatus("Couldn't get your location. Check your browser's location permission, or search a city instead.", true),
    { enableHighAccuracy: true, timeout: 10000 },
  )
}

// Runs once on mount: centers on the user's current location and searches a
// small set of default categories, or -- if location isn't available or is
// denied -- leaves the map on its US-wide fallback view with nothing
// selected, letting the user pick types or search a city themselves.
function locateOnLoad() {
  if (!navigator.geolocation) {
    setStatus("Location isn't available in this browser. Pick place types above or search a city to get started.")
    return
  }
  navigator.geolocation.getCurrentPosition(
    pos => {
      const lat = pos.coords.latitude
      const lon = pos.coords.longitude
      placeUserMarker(lat, lon)
      moveMapTo(lat, lon, 13)
      suppressCategoryWatch = true
      selectedCategories.value = LOCATION_DEFAULT_CATEGORIES.slice()
      searchPlaces(lat, lon)
    },
    () => setStatus("Couldn't get your location. Pick place types above or search a city to get started.", true),
    { enableHighAccuracy: true, timeout: 10000 },
  )
}

function runSearchQuery() {
  const q = searchQuery.value.trim()
  if (!q) return
  setStatus('Looking up "' + q + '"…')
  geocoder
    .geocode({ address: q })
    .then(res => {
      const results = res.results
      if (!results || results.length === 0) {
        setStatus('No location found for "' + q + '". Try a different search.', true)
        return
      }
      const loc = results[0].geometry.location
      moveMapTo(loc.lat(), loc.lng(), 12)
      searchPlaces(loc.lat(), loc.lng())
    })
    .catch(() => setStatus('Location search failed. Check your connection and try again.', true))
}

async function initMap() {
  try {
    const libs = await Promise.all([
      google.maps.importLibrary('maps'),
      google.maps.importLibrary('marker'),
      google.maps.importLibrary('places'),
      google.maps.importLibrary('geocoding'),
    ])
    Marker = libs[1].Marker
    InfoWindow = libs[0].InfoWindow
    Place = libs[2].Place
    SearchNearbyRankPreference = libs[2].SearchNearbyRankPreference
    Geocoder = libs[3].Geocoder

    map = new libs[0].Map(mapEl.value, {
      center: US_CENTER,
      zoom: 4,
      styles: MAP_STYLES,
      mapTypeControl: true,
      mapTypeControlOptions: {
        style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
        position: google.maps.ControlPosition.TOP_LEFT,
      },
      zoomControl: true,
      zoomControlOptions: { position: google.maps.ControlPosition.RIGHT_BOTTOM },
      streetViewControl: false,
      fullscreenControl: false,
      clickableIcons: false,
    })

    infoWindow = new InfoWindow()
    geocoder = new Geocoder()

    map.addListener('idle', onMapIdle)

    locateOnLoad()
  } catch (err) {
    console.error('Google Maps failed to initialize:', err)
    setStatus('Google Maps failed to load. Check that the Maps JavaScript API is enabled and billing is active for this key.', true)
  }
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onDocumentKeydown)

  window.gm_authFailure = () => {
    setStatus(
      "Google Maps couldn't authenticate this key. Check that the Maps JavaScript API, Places API (New), and Geocoding API are enabled, billing is active, and any HTTP referrer restriction allows this page's URL.",
      true,
    )
  }

  if (!configError.value) initMap()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onDocumentKeydown)
  delete window.gm_authFailure
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  clearMarkers()
  if (userMarker) userMarker.setMap(null)
})
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
.config-error {
  background: var(--panel);
  border: 1px solid var(--accent3);
  color: var(--text);
  border-radius: 12px;
  padding: 16px 18px;
  font-size: 13.5px;
  line-height: 1.6;
}
.config-error code {
  background: var(--panel2);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12.5px;
}

.guide-layout {
  display: flex;
  gap: 14px;
  height: calc(100vh - 175px);
  min-height: 500px;
}

.sidebar {
  flex: 0 0 320px;
  background: var(--panel);
  border: 1px solid var(--grid);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.type-select {
  position: relative;
}
.type-select-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--grid);
  background: var(--panel2);
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}
.type-select-btn:hover {
  border-color: var(--muted);
}
.type-select-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.type-select-caret {
  flex: 0 0 auto;
  font-size: 11px;
  color: var(--muted);
  transition: transform 0.15s;
}
.type-select-caret.open {
  transform: rotate(180deg);
}
.type-select-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: var(--panel2);
  border: 1px solid var(--grid);
  border-radius: 8px;
  padding: 6px;
  z-index: 10;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: min(60vh, 420px);
  overflow-y: auto;
}
.type-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text);
}
.type-option:hover {
  background: var(--panel);
}
.type-option input {
  width: 15px;
  height: 15px;
  accent-color: var(--accent);
  cursor: pointer;
}

.search-row {
  display: flex;
  gap: 8px;
}
.search-input {
  flex: 1 1 auto;
  min-width: 0;
  background: var(--panel2);
  border: 1px solid var(--grid);
  color: var(--text);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
}
.locate-btn {
  width: 100%;
}

.status {
  font-size: 12px;
  color: var(--muted);
  min-height: 16px;
}
.status.error {
  color: var(--accent3);
}

.park-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.park-card {
  background: var(--panel2);
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 9px 11px;
  cursor: pointer;
}
.park-card:hover {
  border-color: var(--grid);
}
.park-card.active {
  background: var(--accent);
}
.park-card.active .park-name,
.park-card.active .park-addr,
.park-card.active .park-dist {
  color: #0f1720;
}
.park-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--text);
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.park-addr {
  font-size: 11.5px;
  color: var(--muted);
  margin-top: 2px;
}
.park-dist {
  font-size: 11px;
  color: var(--accent2);
  margin-top: 4px;
}
.park-card.active .park-dist {
  opacity: 0.85;
}
.empty-state {
  font-size: 12.5px;
  color: var(--muted);
  line-height: 1.5;
  padding: 8px 2px;
  list-style: none;
}

.map-wrap {
  flex: 1;
  min-width: 0;
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--grid);
}
.map {
  width: 100%;
  height: 100%;
  background: var(--panel2);
}
.search-area-btn {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
  background: var(--panel);
  color: var(--text);
  border: 1px solid var(--accent);
  border-radius: 999px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.35);
}
.search-area-btn:hover {
  background: var(--panel2);
}

@media (max-width: 760px) {
  .guide-layout {
    flex-direction: column;
    height: auto;
  }
  .sidebar {
    flex: 0 0 auto;
    max-height: 42vh;
  }
  .map-wrap {
    height: 50vh;
  }
}
</style>

<style>
/* Google's InfoWindow content/chrome is injected outside Vue's render tree
   (like Leaflet popups in MapView.vue) so it can't be scoped. */
.popup-name {
  font-weight: 700;
  font-size: 14px;
  margin: 0 0 4px 0;
  color: #0f1720;
}
.popup-addr {
  font-size: 12px;
  color: #3e4a42;
  margin: 0 0 8px 0;
}
.popup-link {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  color: #0f1720;
  background: #ff8a3d;
  padding: 6px 10px;
  border-radius: 6px;
  text-decoration: none;
}
.popup-link:hover {
  background: #ffa15e;
}
</style>
