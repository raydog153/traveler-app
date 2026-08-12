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
from typing import Callable, Literal, TypeVar

from app.models import GasFillup, Location, MaintenanceRecord
from app.schemas import RouteData, RouteLocation, RouteYear
from app.services.analytics import display_city

RecordT = TypeVar("RecordT", GasFillup, MaintenanceRecord)


def _points_from(
    records: list[RecordT],
    location_of: Callable[[RecordT], Location | None],
    type_: Literal["gas", "maintenance"],
    detail_of: Callable[[RecordT], str | None],
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
            )
        )
    return points


def build_route_data(fillups: list[GasFillup], maintenance_records: list[MaintenanceRecord]) -> RouteData:
    points = _points_from(fillups, lambda f: f.location, "gas", lambda f: f.notes or None)
    points += _points_from(maintenance_records, lambda m: m.location, "maintenance", lambda m: m.expense)

    by_year: dict[int, list[RouteLocation]] = defaultdict(list)
    for p in points:
        by_year[p.date.year].append(p)

    years = [
        RouteYear(year=str(year), locations=sorted(by_year[year], key=lambda p: (p.date, p.id)))
        for year in sorted(by_year)
    ]

    return RouteData(total_stops=len(points), years=years)
