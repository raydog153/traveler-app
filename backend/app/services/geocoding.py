"""Best-effort geocoding for new fill-up cities.

Order of operations when a fill-up is created:
  1. Reuse coordinates from any existing fill-up at the same city (case
     insensitive) -- no external call.
  2. Otherwise call OpenStreetMap's Nominatim search API, rate-limited to a
     defensive floor of ~1 req/sec (moot in practice: this only fires on
     manual form submissions for genuinely new cities).
  3. On any failure (timeout, no results, bad payload), log a warning and
     return (None, None). Geocoding never blocks or fails a fill-up create --
     the row just saves with null coordinates and won't appear on the map
     until it's backfilled.
"""

import logging
import threading
import time

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import GasFillup

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
MIN_REQUEST_INTERVAL_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 10.0

_last_request_lock = threading.Lock()
_last_request_time = 0.0


def _reuse_from_db(db: Session, city: str) -> tuple[float, float] | None:
    stmt = (
        select(GasFillup.latitude, GasFillup.longitude)
        .where(func.lower(GasFillup.city) == city.lower())
        .where(GasFillup.latitude.is_not(None))
        .limit(1)
    )
    row = db.execute(stmt).first()
    if row is None:
        return None
    return float(row[0]), float(row[1])


def _rate_limit() -> None:
    global _last_request_time
    with _last_request_lock:
        elapsed = time.monotonic() - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)
        _last_request_time = time.monotonic()


def _geocode_via_nominatim(city: str) -> tuple[float, float] | None:
    _rate_limit()
    contact = settings.nominatim_contact_email or "no-contact-configured"
    headers = {"User-Agent": f"traveler-app ({contact})"}

    try:
        resp = httpx.get(
            NOMINATIM_URL,
            params={"q": city, "format": "json", "limit": 1},
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        results = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("geocoding request failed for city=%r: %s", city, exc)
        return None

    if not results:
        logger.warning("geocoding returned no results for city=%r", city)
        return None

    try:
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("geocoding returned an unexpected payload for city=%r: %s", city, exc)
        return None


def get_or_geocode(db: Session, city: str) -> tuple[float | None, float | None]:
    reused = _reuse_from_db(db, city)
    if reused is not None:
        return reused

    geocoded = _geocode_via_nominatim(city)
    if geocoded is not None:
        return geocoded
    return None, None
