"""Best-effort geocoding for new fill-up locations.

Order of operations when a fill-up is created:
  1. Look up the Location row by its natural key (city, state) --
     `locations` is already the deduped store, so no per-fill-up scan is
     needed; an existing row means it's already been geocoded (or
     deliberately left null).
  2. On a genuine miss, call OpenStreetMap's Nominatim search API,
     rate-limited to a defensive floor of ~1 req/sec (moot in practice: this
     only fires on manual form submissions for genuinely new city/state
     combinations), and insert a new Location row.
  3. On any geocoding failure (timeout, no results, bad payload), log a
     warning and create the Location with null coordinates. Geocoding never
     blocks or fails a fill-up create -- the row just saves with null
     coordinates and won't appear on the map until it's backfilled.

Also provides `reverse_geocode_via_nominatim`, the inverse direction: given
a lat/long (e.g. from a fill-up photo's EXIF GPS), best-effort resolve a
city/state to prefill the add-fillup form's City field. Same never-blocks
contract as forward geocoding.
"""

import logging
import threading
import time

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Location, location_id

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
GOOGLE_PLACES_SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
MIN_REQUEST_INTERVAL_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 10.0

_last_request_lock = threading.Lock()
_last_request_time = 0.0


def _rate_limit() -> None:
    global _last_request_time
    with _last_request_lock:
        elapsed = time.monotonic() - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)
        _last_request_time = time.monotonic()


def _geocode_via_nominatim(query: str) -> tuple[float, float] | None:
    _rate_limit()
    contact = settings.nominatim_contact_email or "no-contact-configured"
    headers = {"User-Agent": f"traveler-app ({contact})"}

    try:
        resp = httpx.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        results = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("geocoding request failed for query=%r: %s", query, exc)
        return None

    if not results:
        logger.warning("geocoding returned no results for query=%r", query)
        return None

    try:
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("geocoding returned an unexpected payload for query=%r: %s", query, exc)
        return None


def reverse_geocode_via_nominatim(lat: float, lon: float) -> tuple[str, str] | None:
    """Best-effort city/state lookup for a raw lat/long (e.g. a fill-up
    photo's EXIF GPS), used only to prefill the add-fillup form's City field
    -- never blocks, and the result is always user-editable before save.
    Same rate-limiting/User-Agent/never-raise contract as
    `_geocode_via_nominatim` above."""
    _rate_limit()
    contact = settings.nominatim_contact_email or "no-contact-configured"
    headers = {"User-Agent": f"traveler-app ({contact})"}

    try:
        resp = httpx.get(
            NOMINATIM_REVERSE_URL,
            params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1},
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        result = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("reverse geocoding request failed for (%s, %s): %s", lat, lon, exc)
        return None

    try:
        address = result["address"]
    except (KeyError, TypeError) as exc:
        logger.warning("reverse geocoding returned an unexpected payload for (%s, %s): %s", lat, lon, exc)
        return None

    city = address.get("city") or address.get("town") or address.get("village") or address.get("hamlet")
    if not city:
        logger.warning("reverse geocoding returned no usable city for (%s, %s)", lat, lon)
        return None

    return city, address.get("state", "")


def geocode_address_via_google_places(address: str) -> tuple[float, float] | None:
    """Best-effort address -> (lat, lng) for travel_data rows, via the
    Places API (New) Text Search endpoint -- unlike the city/state-only
    Nominatim lookup above, this handles addresses that name a specific
    place ("Walmart Waterloo Store #1496, 1334 Flammang Dr, ..."), which a
    plain address geocoder would ignore. Same never-raise contract as
    `_geocode_via_nominatim`: any failure logs a warning and returns None,
    it's on the caller to flag the row (e.g. is_estimated_location) rather
    than block. No rate limiting -- Places API is a paid, non-courtesy
    service, unlike Nominatim.

    Not currently called by any endpoint -- travel_data.json's seed fixture
    stores pre-resolved lat/long rather than geocoding at load time (see
    seed/seed.py), so this was used once to populate that fixture. Kept
    here for the next thing that needs it: geocoding a newly-added
    travel_data row (e.g. a future create endpoint/form) or regenerating
    the fixture after editing it.
    """
    if not settings.google_maps_api_key:
        logger.warning("geocoding via Google Places skipped for address=%r: no API key configured", address)
        return None

    headers = {
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": "places.location",
        "Content-Type": "application/json",
    }

    try:
        resp = httpx.post(
            GOOGLE_PLACES_SEARCH_TEXT_URL,
            json={"textQuery": address},
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Google Places geocoding request failed for address=%r: %s", address, exc)
        return None

    try:
        location = payload["places"][0]["location"]
        return float(location["latitude"]), float(location["longitude"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("Google Places geocoding returned an unexpected payload for address=%r: %s", address, exc)
        return None


def get_or_create_location(db: Session, city: str, state: str) -> Location:
    loc_id = location_id(city, state)
    location = db.get(Location, loc_id)
    if location is not None:
        return location

    query = f"{city}, {state}" if state else city
    geocoded = _geocode_via_nominatim(query)
    lat, lng = geocoded if geocoded is not None else (None, None)
    location = Location(id=loc_id, city=city, state=state, lat=lat, long=lng)
    db.add(location)
    return location
