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
