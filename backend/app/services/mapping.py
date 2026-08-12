"""Builds the route/map payload from gas_fillups: for each unique city, plot
its earliest visit, grouped and colored by the year of that first visit --
the same derived view bus_route_map.html's `routeData` was, but computed
live instead of hand-curated. Cities with no lat/lng (not yet geocoded)
are simply omitted -- they'll appear once a future fill-up there gets
geocoded.
"""

from collections import defaultdict

from app.models import GasFillup
from app.schemas import RouteData, RouteLocation, RouteYear


def build_route_data(fillups: list[GasFillup]) -> RouteData:
    by_city: dict[str, list[GasFillup]] = defaultdict(list)
    for f in fillups:
        by_city[f.city].append(f)

    by_year: dict[int, list[tuple]] = defaultdict(list)
    for city, rows in by_city.items():
        rows.sort(key=lambda f: f.date)
        first = rows[0]
        if first.latitude is None or first.longitude is None:
            continue
        by_year[first.date.year].append((first.date, city, first, len(rows)))

    years = []
    for year in sorted(by_year):
        entries = sorted(by_year[year], key=lambda e: e[0])
        locations = [
            RouteLocation(
                name=city,
                latitude=float(first.latitude),
                longitude=float(first.longitude),
                arrival_date=arrival_date,
                visit_count=visit_count,
            )
            for arrival_date, city, first, visit_count in entries
        ]
        years.append(RouteYear(year=str(year), locations=locations))

    total_stops = sum(len(y.locations) for y in years)
    return RouteData(total_stops=total_stops, years=years)
