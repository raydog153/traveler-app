import httpx
import pytest

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
    """Minimal stand-in for the DB reuse lookup -- no existing coordinates."""

    def execute(self, *_args, **_kwargs):
        class _Result:
            def first(self_inner):
                return None

        return _Result()


@pytest.fixture(autouse=True)
def reset_rate_limit_clock():
    geocoding._last_request_time = 0.0
    yield


def test_geocode_success(monkeypatch):
    def fake_get(*_args, **_kwargs):
        return FakeResponse([{"lat": "41.8781", "lon": "-87.6298"}])

    monkeypatch.setattr(geocoding.httpx, "get", fake_get)

    lat, lng = geocoding.get_or_geocode(FakeSession(), "Chicago, IL")
    assert lat == pytest.approx(41.8781)
    assert lng == pytest.approx(-87.6298)


def test_geocode_no_results_returns_none(monkeypatch):
    monkeypatch.setattr(geocoding.httpx, "get", lambda *a, **k: FakeResponse([]))

    lat, lng = geocoding.get_or_geocode(FakeSession(), "Nowhereville, XX")
    assert (lat, lng) == (None, None)


def test_geocode_request_error_does_not_raise(monkeypatch):
    def raise_error(*_args, **_kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(geocoding.httpx, "get", raise_error)

    lat, lng = geocoding.get_or_geocode(FakeSession(), "Somewhere, YY")
    assert (lat, lng) == (None, None)


def test_geocode_malformed_payload_does_not_raise(monkeypatch):
    monkeypatch.setattr(geocoding.httpx, "get", lambda *a, **k: FakeResponse([{"unexpected": "shape"}]))

    lat, lng = geocoding.get_or_geocode(FakeSession(), "Somewhere, ZZ")
    assert (lat, lng) == (None, None)


def test_reuse_from_db_skips_external_call(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("should not call Nominatim when DB has a match")

    monkeypatch.setattr(geocoding.httpx, "get", fail_if_called)

    class ReuseSession:
        def execute(self, *_args, **_kwargs):
            class _Result:
                def first(self_inner):
                    return (42.0, -71.0)

            return _Result()

    lat, lng = geocoding.get_or_geocode(ReuseSession(), "Lancaster, MA")
    assert (lat, lng) == (42.0, -71.0)
