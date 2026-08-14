import httpx
import pytest

from app.models import Location, location_id
from app.services import geocoding


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_data


class FakeSession:
    """Minimal stand-in for the DB location lookup."""

    def __init__(self, existing: Location | None = None):
        self._existing = existing
        self.added = []

    def get(self, _model, loc_id):
        if self._existing is not None and self._existing.id == loc_id:
            return self._existing
        return None

    def add(self, obj):
        self.added.append(obj)


@pytest.fixture(autouse=True)
def reset_rate_limit_clock():
    geocoding._last_request_time = 0.0
    yield


def test_geocode_success(monkeypatch):
    def fake_get(*_args, **_kwargs):
        return FakeResponse([{"lat": "41.8781", "lon": "-87.6298"}])

    monkeypatch.setattr(geocoding.httpx, "get", fake_get)

    location = geocoding.get_or_create_location(FakeSession(), "Chicago", "IL")
    assert location.lat == pytest.approx(41.8781)
    assert location.long == pytest.approx(-87.6298)
    assert location.id == location_id("Chicago", "IL")


def test_geocode_no_results_returns_none(monkeypatch):
    monkeypatch.setattr(geocoding.httpx, "get", lambda *a, **k: FakeResponse([]))

    location = geocoding.get_or_create_location(FakeSession(), "Nowhereville", "XX")
    assert (location.lat, location.long) == (None, None)


def test_geocode_request_error_does_not_raise(monkeypatch):
    def raise_error(*_args, **_kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(geocoding.httpx, "get", raise_error)

    location = geocoding.get_or_create_location(FakeSession(), "Somewhere", "YY")
    assert (location.lat, location.long) == (None, None)


def test_geocode_malformed_payload_does_not_raise(monkeypatch):
    monkeypatch.setattr(geocoding.httpx, "get", lambda *a, **k: FakeResponse([{"unexpected": "shape"}]))

    location = geocoding.get_or_create_location(FakeSession(), "Somewhere", "ZZ")
    assert (location.lat, location.long) == (None, None)


def test_reverse_geocode_success(monkeypatch):
    monkeypatch.setattr(
        geocoding.httpx, "get", lambda *a, **k: FakeResponse({"address": {"city": "Chicago", "state": "Illinois"}})
    )

    result = geocoding.reverse_geocode_via_nominatim(41.8781, -87.6298)
    assert result == ("Chicago", "Illinois")


def test_reverse_geocode_falls_back_through_town_village_hamlet(monkeypatch):
    monkeypatch.setattr(
        geocoding.httpx, "get", lambda *a, **k: FakeResponse({"address": {"town": "Lancaster", "state": "MA"}})
    )

    result = geocoding.reverse_geocode_via_nominatim(42.0, -71.0)
    assert result == ("Lancaster", "MA")


def test_reverse_geocode_no_address_in_response_returns_none(monkeypatch):
    monkeypatch.setattr(geocoding.httpx, "get", lambda *a, **k: FakeResponse({}))

    assert geocoding.reverse_geocode_via_nominatim(0.0, 0.0) is None


def test_reverse_geocode_no_usable_city_returns_none(monkeypatch):
    monkeypatch.setattr(geocoding.httpx, "get", lambda *a, **k: FakeResponse({"address": {"country": "USA"}}))

    assert geocoding.reverse_geocode_via_nominatim(0.0, 0.0) is None


def test_reverse_geocode_request_error_does_not_raise(monkeypatch):
    def raise_error(*_args, **_kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(geocoding.httpx, "get", raise_error)

    assert geocoding.reverse_geocode_via_nominatim(0.0, 0.0) is None


def test_reuse_from_db_skips_external_call(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("should not call Nominatim when DB has a match")

    monkeypatch.setattr(geocoding.httpx, "get", fail_if_called)

    existing = Location(id=location_id("Lancaster", "MA"), city="Lancaster", state="MA", lat=42.0, long=-71.0)
    location = geocoding.get_or_create_location(FakeSession(existing=existing), "Lancaster", "MA")
    assert (location.lat, location.long) == (42.0, -71.0)
