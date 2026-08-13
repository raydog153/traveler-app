<template>
  <div class="wrap">
    <div v-if="configError" class="config-error">
      Google Maps isn't configured: set <code>GOOGLE_MAPS_API_KEY</code> in your <code>.env</code> file
      (Maps JavaScript API, Places API (New), and Geocoding API must be enabled with billing active), then
      restart the frontend.
    </div>

    <div v-else class="guide-layout">
      <aside class="sidebar">
        <div class="panel-header">
          <h1>🐾 Find places</h1>
          <p class="sub">Dog parks, playgrounds and trailheads near wherever the bus is parked.</p>
        </div>

        <div class="location-row">
          <input
            v-model="searchQuery"
            type="text"
            class="location-input"
            placeholder="Search a city or address…"
            aria-label="Search a city or address"
            @keydown.enter.prevent="runSearchQuery"
          />
          <button type="button" class="btn go-btn" @click="runSearchQuery">Go</button>
        </div>

        <div class="filter-row">
          <button type="button" class="chip locate-chip" @click="useMyLocation">📍 Use my location</button>
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
        </div>

        <div class="radius-row">
          <span class="radius-label">Within {{ radiusMiles }} mi</span>
          <input
            v-model.number="radiusMiles"
            type="range"
            min="5"
            max="50"
            step="1"
            class="radius-slider"
            :style="{ '--fill-pct': radiusFillPct + '%' }"
          />
          <span class="radius-max">50 mi</span>
        </div>

        <div class="list-header">
          <span>{{ parks.length }} places within {{ radiusMiles }} miles</span>
          <span class="sorted-label">Sorted by distance</span>
        </div>

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
            <span class="icon-tile" :class="tileClass(park.categoryKey)">{{ CATEGORY_BY_KEY[park.categoryKey].bullet }}</span>
            <div class="park-text">
              <div class="park-name truncate">{{ park.name }}</div>
              <div class="park-addr truncate">{{ park.address }}</div>
            </div>
            <div class="park-dist-col">
              <div class="park-dist mono">{{ park.distance.toFixed(1) }}</div>
              <div class="park-dist-label">mi away</div>
            </div>
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
  { key: 'dog_park', label: 'Dog Parks', includedPrimaryTypes: ['dog_park'], bullet: '🐾', singular: 'dog park', plural: 'dog parks' },
  { key: 'playground', label: 'Kid Playgrounds', includedPrimaryTypes: ['playground'], bullet: '🛝', singular: 'playground', plural: 'playgrounds' },
  { key: 'boat_launch', label: 'Boat Launches', includedPrimaryTypes: ['marina'], bullet: '⚓', singular: 'boat launch', plural: 'boat launches' },
  { key: 'trailhead', label: 'Trailheads', includedPrimaryTypes: ['hiking_area'], bullet: '🥾', singular: 'trailhead', plural: 'trailheads' },
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

// Tints named in the design spec; every other category falls back to a
// neutral tile rather than inventing colors the design doesn't specify.
const TILE_TINT_BY_KEY = { dog_park: 'tint-amber', trailhead: 'tint-green', hiking_area: 'tint-green' }

const ACCENT = '#1f6feb'
const RING_GREY = '#c9ccd3'

const emojiIconCache = {}
function emojiIconUrl(emoji, selected) {
  const cacheKey = emoji + (selected ? ':sel' : '')
  if (emojiIconCache[cacheKey]) return emojiIconCache[cacheKey]
  const ring = selected ? ACCENT : RING_GREY
  const strokeWidth = selected ? 2.5 : 2
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><circle cx="20" cy="20" r="17" fill="#fff" stroke="' +
    ring + '" stroke-width="' + strokeWidth + '"/><text x="20" y="27" font-size="19" text-anchor="middle">' + emoji + '</text></svg>'
  const url = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg)
  emojiIconCache[cacheKey] = url
  return url
}

// Light Positron-equivalent theme, inverted from the app's dark map style --
// matches the light card/text tokens in style.css / theme.js.
const MAP_STYLES = [
  { elementType: 'geometry', stylers: [{ color: '#f7f8fb' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#8a8f9c' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#ffffff' }] },
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#e3ecdf' }] },
  { featureType: 'poi.park', elementType: 'labels', stylers: [{ visibility: 'off' }] },
  { featureType: 'transit', stylers: [{ visibility: 'off' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#e7e9ee' }] },
  { featureType: 'road.arterial', elementType: 'geometry', stylers: [{ color: '#eef0f4' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#f3d9c8' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#dce6f0' }] },
  { featureType: 'administrative', elementType: 'geometry.stroke', stylers: [{ color: '#d7dae1' }] },
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
const radiusMiles = ref(10)
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
let geocoder, infoWindow, nameChip, radiusCircle
let markers = []
let userMarker = null
let lastSearchCenter = US_CENTER
let suppressNextIdle = false
let searchDebounceTimer = null
let radiusDebounceTimer = null
// Set right before a programmatic (non-user-click) change to
// selectedCategories, e.g. locateOnLoad's default categories -- lets that
// caller drive its own searchPlaces() call with fresh coordinates instead of
// racing the categories watcher below, which only knows the stale
// lastSearchCenter until that caller updates it.
let suppressCategoryWatch = false

const radiusFillPct = computed(() => ((radiusMiles.value - 5) / (50 - 5)) * 100)

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

function tileClass(categoryKey) {
  return TILE_TINT_BY_KEY[categoryKey] || 'tint-neutral'
}

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

function selectPark(park) {
  if (activePark.value && activePark.value.marker) {
    activePark.value.marker.setIcon({
      url: emojiIconUrl(CATEGORY_BY_KEY[activePark.value.categoryKey].bullet, false),
      scaledSize: new google.maps.Size(24, 24),
      anchor: new google.maps.Point(12, 12),
    })
  }
  park.marker.setIcon({
    url: emojiIconUrl(CATEGORY_BY_KEY[park.categoryKey].bullet, true),
    scaledSize: new google.maps.Size(30, 30),
    anchor: new google.maps.Point(15, 15),
  })
  park.marker.setZIndex(1000)

  const name = park.name.length > 20 ? park.name.slice(0, 20) + '…' : park.name
  const directionsUrl =
    'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(park.lat + ',' + park.lon)
  infoWindow.setContent(
    '<div class="park-chip">' +
      '<div class="park-chip-name">' + escapeHtml(name) + '</div>' +
      '<div class="park-chip-addr">' + escapeHtml(park.address) + '</div>' +
      '<a class="park-chip-directions" href="' + directionsUrl + '" target="_blank" rel="noopener noreferrer">Get directions →</a>' +
      '</div>',
  )
  infoWindow.open({ map, anchor: park.marker })
  activePark.value = park
}

function activatePark(park) {
  suppressNextIdle = true
  map.panTo({ lat: park.lat, lng: park.lon })
  map.setZoom(15)
  selectPark(park)
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

function updateRadiusCircle(lat, lon, radiusM) {
  const center = { lat, lng: lon }
  if (!radiusCircle) {
    radiusCircle = new google.maps.Circle({
      map,
      center,
      radius: radiusM,
      strokeColor: '#7fa8e8',
      strokeOpacity: 0.6,
      strokeWeight: 1.5,
      fillColor: ACCENT,
      fillOpacity: 0.07,
      clickable: false,
      zIndex: 1,
    })
  } else {
    radiusCircle.setCenter(center)
    radiusCircle.setRadius(radiusM)
  }
}

function currentRadiusM() {
  return radiusMiles.value * METERS_PER_MILE
}

function searchPlaces(lat, lon, { fitBounds = true, radiusM = currentRadiusM() } = {}) {
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
  updateRadiusCircle(lat, lon, radiusM)

  const radiusMi = Math.round(radiusM / METERS_PER_MILE)
  const radiusLabel = radiusMi + (radiusMi === 1 ? ' mile' : ' miles')

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
          url: emojiIconUrl(category.bullet, false),
          scaledSize: new google.maps.Size(24, 24),
          anchor: new google.maps.Point(12, 12),
        },
      })
      marker.addListener('click', () => selectPark(place))
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
// results genuinely found within the search radius -- and listed in the
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
// zoomed-out (e.g. multi-state) view the fixed default radius would only
// ever cover a small dot in the middle of the viewport, which reads as
// "results only show in the center." Derive the radius from how far the
// current viewport actually spans instead.
function viewportRadiusMeters() {
  const bounds = map.getBounds()
  if (!bounds) return currentRadiusM()
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

watch(radiusMiles, () => {
  if (radiusDebounceTimer) clearTimeout(radiusDebounceTimer)
  radiusDebounceTimer = setTimeout(() => {
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
      url: emojiIconUrl('🚌', true),
      scaledSize: new google.maps.Size(30, 30),
      anchor: new google.maps.Point(15, 15),
    },
  })
  if (nameChip) nameChip.close()
  nameChip = new InfoWindow({
    content: '<div class="name-chip">You are here</div>',
    disableAutoPan: true,
  })
  nameChip.open({ map, anchor: userMarker })
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
      mapTypeControl: false,
      zoomControl: true,
      zoomControlOptions: { position: google.maps.ControlPosition.RIGHT_BOTTOM },
      streetViewControl: false,
      fullscreenControl: false,
      clickableIcons: false,
    })

    infoWindow = new InfoWindow({ disableAutoPan: true })
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
  if (radiusDebounceTimer) clearTimeout(radiusDebounceTimer)
  clearMarkers()
  if (userMarker) userMarker.setMap(null)
})
</script>

<style scoped>
.wrap {
  height: calc(100vh - 62px);
  min-height: 460px;
}
.config-error {
  background: #fff;
  border: 1px solid var(--severe-red);
  color: var(--text-primary);
  border-radius: 12px;
  padding: 16px 18px;
  font-size: 13.5px;
  line-height: 1.6;
  margin: 26px;
}
.config-error code {
  background: var(--fill-subtle);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12.5px;
}

.guide-layout {
  display: flex;
  height: 100%;
}

.sidebar {
  flex: 0 0 452px;
  background: #fff;
  border-right: 1px solid var(--card-border);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-header {
  padding: 22px 22px 16px;
}
h1 {
  font-size: 21px;
  font-weight: 600;
  margin: 0 0 4px;
}
.sub {
  font-size: 12.5px;
  color: var(--text-muted);
  margin: 0;
}

.location-row {
  display: flex;
  gap: 8px;
  padding: 0 22px;
  margin-bottom: 12px;
}
.location-input {
  flex: 1;
  min-width: 0;
  background: var(--fill-subtle);
  border: 1px solid transparent;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
}
.location-input:focus {
  outline: none;
  background: #fff;
  border-color: var(--ac);
}
.go-btn {
  padding: 10px 16px;
}

.filter-row {
  display: flex;
  gap: 8px;
  padding: 0 22px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
}
.chip {
  border-radius: 20px;
  padding: 8px 14px;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  white-space: nowrap;
}
.locate-chip {
  background: var(--ac-tint);
  color: oklch(0.42 0.11 258);
}

.type-select {
  position: relative;
  flex: 1;
  min-width: 160px;
}
.type-select-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 20px;
  border: 1px solid var(--card-border);
  background: #fff;
  color: var(--text-primary);
  font-size: 12.5px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
}
.type-select-btn:hover {
  border-color: var(--ac);
}
.type-select-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.type-select-caret {
  flex: 0 0 auto;
  font-size: 11px;
  color: var(--text-muted);
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
  background: #fff;
  border: 1px solid var(--card-border);
  border-radius: 10px;
  padding: 6px;
  z-index: 10;
  box-shadow: var(--shadow-overlay);
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
}
.type-option:hover {
  background: var(--fill-subtle);
}
.type-option input {
  width: 15px;
  height: 15px;
  accent-color: var(--ac);
  cursor: pointer;
}

.radius-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 22px;
  margin-bottom: 14px;
  font-size: 11.5px;
  color: var(--text-muted);
}
.radius-label {
  white-space: nowrap;
}
.radius-max {
  white-space: nowrap;
}
.radius-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 5px;
  border-radius: 3px;
  background: linear-gradient(to right, var(--ac) 0%, var(--ac) var(--fill-pct), var(--track) var(--fill-pct), var(--track) 100%);
  cursor: pointer;
}
.radius-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--ac);
  box-shadow: 0 1px 3px oklch(0.2 0.02 255 / 0.3);
  cursor: pointer;
}
.radius-slider::-moz-range-thumb {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--ac);
  cursor: pointer;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--fill-subtle-2);
  padding: 10px 22px;
  font-size: 12px;
}
.list-header span:first-child {
  font-weight: 500;
}
.sorted-label {
  color: var(--text-muted);
  font-size: 11.5px;
}

.status {
  font-size: 12px;
  color: var(--text-muted);
  min-height: 16px;
  padding: 8px 22px 0;
}
.status.error {
  color: var(--severe-red);
}

.park-list {
  list-style: none;
  margin: 0;
  padding: 6px 14px 14px;
  overflow-y: auto;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.park-card {
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 11px;
  padding: 11px 10px;
  cursor: pointer;
}
.park-card:hover {
  background: var(--fill-subtle);
}
.park-card.active {
  background: var(--ac-tint);
}
.icon-tile {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
.icon-tile.tint-amber {
  background: var(--amber-tint);
}
.icon-tile.tint-green {
  background: var(--green-tint);
}
.icon-tile.tint-neutral {
  background: oklch(0.96 0.004 255);
}
.park-text {
  flex: 1;
  min-width: 0;
}
.park-name {
  font-weight: 500;
  font-size: 13px;
}
.park-addr {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-top: 2px;
}
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.park-dist-col {
  flex-shrink: 0;
  text-align: right;
}
.park-dist {
  font-weight: 600;
  font-size: 12.5px;
}
.park-dist-label {
  font-size: 10.5px;
  color: var(--text-muted);
}
.empty-state {
  font-size: 12.5px;
  color: var(--text-muted);
  line-height: 1.5;
  padding: 8px 8px;
  list-style: none;
}

.map-wrap {
  flex: 1;
  min-width: 0;
  position: relative;
}
.map {
  width: 100%;
  height: 100%;
}
.search-area-btn {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
  background: #fff;
  color: var(--text-primary);
  border: 1px solid var(--ac);
  border-radius: 999px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-overlay);
}
.search-area-btn:hover {
  background: var(--fill-subtle);
}

@media (max-width: 760px) {
  .guide-layout {
    flex-direction: column;
    height: auto;
  }
  .sidebar {
    flex: 0 0 auto;
    max-height: 55vh;
  }
  .map-wrap {
    height: 45vh;
  }
}
</style>

<style>
/* Google's InfoWindow content/chrome is injected outside Vue's render tree
   (like Leaflet popups in MapView.vue) so it can't be scoped. Strip its
   default bubble chrome down to a plain chip per the design -- 14px suits
   both the single-line "You are here" pill and the taller park popup
   (name + address + directions link) better than a full 20px pill radius. */
.gm-style .gm-style-iw-c {
  padding: 0;
  border-radius: 14px;
  box-shadow: 0 1px 4px oklch(0.3 0.03 255 / 0.22);
}
.gm-style .gm-style-iw-d {
  overflow: hidden !important;
}
.gm-style-iw-tc {
  display: none;
}
.gm-ui-hover-effect {
  display: none !important;
}
.name-chip {
  font-size: 12px;
  font-weight: 500;
  color: #33363e;
  background: #fff;
  padding: 6px 12px;
  white-space: nowrap;
}
.park-chip {
  font-size: 12px;
  color: #33363e;
  background: #fff;
  padding: 10px 14px;
  max-width: 220px;
}
.park-chip-name {
  font-weight: 600;
  white-space: normal;
  margin-bottom: 3px;
}
.park-chip-addr {
  color: #6b7280;
  white-space: normal;
  margin-bottom: 6px;
}
.park-chip-directions {
  display: inline-block;
  font-weight: 500;
  color: #1a73e8;
  text-decoration: none;
}
.park-chip-directions:hover {
  text-decoration: underline;
}
</style>
