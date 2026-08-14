"""Builds the route/map payload by merging gas_fillups and
maintenance_records into a single chronological list of stops: every record
with a geocoded location becomes its own point -- repeat visits to the same
location plot multiple times, since that's the actual travel history, not
just the first arrival. Marker color (set on the frontend) distinguishes
record type; points are grouped by year for the route line and the
show/hide-by-year legend. A record with no location, or one not yet
geocoded (null lat/lng), is simply omitted until a later edit fills it in.
"""

from collections import defaultdict
from collections.abc import Callable
from math import atan2, cos, radians, sin, sqrt
from typing import Literal, TypeVar

from app.models import GasFillup, Location, MaintenanceRecord
from app.schemas import RouteData, RouteLocation, RouteYear, TripStats
from app.services import analytics
from app.services.analytics import ComputedFillup, display_city

RecordT = TypeVar("RecordT", GasFillup, MaintenanceRecord)

_EARTH_RADIUS_MILES = 3958.8


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return _EARTH_RADIUS_MILES * 2 * atan2(sqrt(a), sqrt(1 - a))


def _route_sort_key(p: RouteLocation) -> tuple:
    """Chronological order for RouteLocation points, tie-broken by the
    underlying record's own numeric id. `p.id` is the string "{type}-{id}"
    (see _points_from below) -- sorting on that string directly is wrong
    once an id crosses a digit boundary ("gas-10" sorts before "gas-9"
    lexicographically), so parse the numeric id back out for the tie-break
    instead."""
    kind, _, num = p.id.partition("-")
    return (p.date, kind, int(num))


def _points_from(
    records: list[RecordT],
    location_of: Callable[[RecordT], Location | None],
    type_: Literal["gas", "maintenance"],
    detail_of: Callable[[RecordT], str | None],
    amount_of: Callable[[RecordT], float | None] = lambda r: None,
    gallons_of: Callable[[RecordT], float | None] = lambda r: None,
    mpg_of: Callable[[RecordT], float | None] = lambda r: None,
    odometer_of: Callable[[RecordT], float | None] = lambda r: None,
    since_service_of: Callable[[RecordT], float | None] = lambda r: None,
) -> list[RouteLocation]:
    points = []
    for r in records:
        loc = location_of(r)
        if loc is None or loc.lat is None or loc.long is None:
            continue
        points.append(
            RouteLocation(
                id=f"{type_}-{r.id}",
                name=display_city(loc),
                latitude=float(loc.lat),
                longitude=float(loc.long),
                date=r.date,
                type=type_,
                detail=detail_of(r),
                amount=amount_of(r),
                gallons=gallons_of(r),
                mpg=mpg_of(r),
                odometer_miles=odometer_of(r),
                since_service_miles=since_service_of(r),
            )
        )
    return points


def _since_service_miles(maintenance_records: list[MaintenanceRecord]) -> dict[int, float | None]:
    """Miles since the nearest prior service-type record (by date, id), for
    each maintenance record that has its own odometer reading. Uses the same
    service-record ordering as analytics.service_status (via
    analytics.sorted_service_records), just walked at every historical point
    instead of only the most recent one. Both `maintenance_records` and the
    service-only subset are already sorted the same way, so this is a single
    merge pass rather than rescanning the service list per record."""
    service_records = analytics.sorted_service_records(maintenance_records)
    ordered = sorted(maintenance_records, key=lambda r: (r.date, r.id))

    out: dict[int, float | None] = {}
    idx = 0
    last_service_odometer: float | None = None
    for m in ordered:
        while idx < len(service_records) and (service_records[idx].date, service_records[idx].id) < (m.date, m.id):
            last_service_odometer = float(service_records[idx].odometer_miles)
            idx += 1
        if m.odometer_miles is None or last_service_odometer is None:
            out[m.id] = None
        else:
            out[m.id] = float(m.odometer_miles) - last_service_odometer
    return out


def trip_stats(
    computed: list[ComputedFillup],
    fillups: list[GasFillup],
    maintenance_records: list[MaintenanceRecord],
    years: list[RouteYear],
) -> TripStats:
    states = {f.location.state for f in fillups if f.location and f.location.state}
    states |= {r.location.state for r in maintenance_records if r.location and r.location.state}

    flattened = sorted((p for y in years for p in y.locations), key=_route_sort_key)
    longest_leg: float | None = None
    longest_stay: int | None = None
    for prev, curr in zip(flattened, flattened[1:]):
        leg = _haversine_miles(prev.latitude, prev.longitude, curr.latitude, curr.longitude)
        longest_leg = leg if longest_leg is None else max(longest_leg, leg)
        stay = (curr.date - prev.date).days
        longest_stay = stay if longest_stay is None else max(longest_stay, stay)

    driven_vals = [c.driven for c in computed if c.driven]
    avg_between_fillups = sum(driven_vals) / len(driven_vals) if driven_vals else None

    return TripStats(
        states_visited=len(states),
        longest_leg_miles=longest_leg,
        longest_stay_days=longest_stay,
        avg_miles_between_fillups=avg_between_fillups,
        maintenance_stops=len(maintenance_records),
    )


def _fillup_location(f: GasFillup) -> Location | None:
    """A fill-up photo's exact GPS, when captured, overrides the location's
    coarser city-level geocode -- resolved here at read time (mirrors
    analytics.to_gas_out) rather than denormalized onto the row. Returns a
    transient, never-persisted Location standing in for f.location so
    _points_from's generic Location-shaped contract doesn't need to change;
    maintenance records (the other caller of _points_from) never have this
    override and keep using their location unmodified."""
    if f.gps_latitude is not None and f.gps_longitude is not None:
        return Location(
            id=f.location_id, city=f.location.city, state=f.location.state, lat=f.gps_latitude, long=f.gps_longitude
        )
    return f.location


def build_route_data(fillups: list[GasFillup], maintenance_records: list[MaintenanceRecord]) -> RouteData:
    computed = analytics.compute_fillups(fillups)
    computed_by_id = {c.fillup.id: c for c in computed}
    since_service = _since_service_miles(maintenance_records)

    points = _points_from(
        fillups,
        _fillup_location,
        "gas",
        lambda f: f.notes or None,
        amount_of=lambda f: float(f.price),
        gallons_of=lambda f: float(f.gallons),
        mpg_of=lambda f: computed_by_id[f.id].mpg,
        odometer_of=lambda f: float(f.odometer_miles),
    )
    points += _points_from(
        maintenance_records,
        lambda m: m.location,
        "maintenance",
        lambda m: m.expense,
        amount_of=lambda m: float(m.cost),
        odometer_of=lambda m: float(m.odometer_miles) if m.odometer_miles is not None else None,
        since_service_of=lambda m: since_service.get(m.id),
    )

    by_year: dict[int, list[RouteLocation]] = defaultdict(list)
    for p in points:
        by_year[p.date.year].append(p)

    years = [
        RouteYear(year=str(year), locations=sorted(by_year[year], key=_route_sort_key)) for year in sorted(by_year)
    ]

    return RouteData(
        total_stops=len(points),
        years=years,
        trip_stats=trip_stats(computed, fillups, maintenance_records, years),
    )
