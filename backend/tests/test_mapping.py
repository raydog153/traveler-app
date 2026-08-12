import datetime

from app.models import GasFillup, Location, MaintenanceRecord
from app.services import mapping


def make_location(id: str, city: str, state: str = "MS", lat: float | None = 30.0, long: float | None = -89.0) -> Location:
    return Location(id=id, city=city, state=state, lat=lat, long=long)


def make_fillup(id: int, date: str, location: Location, notes: str = "") -> GasFillup:
    f = GasFillup(id=id, date=datetime.date.fromisoformat(date), odometer_miles=100, gallons=10, price=30, notes=notes)
    f.location = location
    return f


def make_record(id: int, date: str, location: Location | None, expense: str = "Oil change") -> MaintenanceRecord:
    r = MaintenanceRecord(id=id, date=datetime.date.fromisoformat(date), expense=expense, cost=50)
    r.location = location
    return r


class TestBuildRouteData:
    def test_merges_gas_and_maintenance_into_one_year(self):
        gulfport = make_location("gulfport_ms", "Gulfport")
        mobile = make_location("mobile_al", "Mobile", "AL")

        fillups = [make_fillup(1, "2022-03-01", gulfport, notes="full tank")]
        records = [make_record(1, "2022-05-01", mobile)]

        data = mapping.build_route_data(fillups, records)

        assert data.total_stops == 2
        assert len(data.years) == 1
        [year] = data.years
        assert year.year == "2022"
        assert [loc.type for loc in year.locations] == ["gas", "maintenance"]
        assert year.locations[0].detail == "full tank"
        assert year.locations[1].detail == "Oil change"

    def test_same_location_produces_separate_points_per_type(self):
        loc = make_location("gulfport_ms", "Gulfport")
        fillups = [make_fillup(1, "2022-01-01", loc)]
        records = [make_record(1, "2022-01-05", loc)]

        data = mapping.build_route_data(fillups, records)

        assert data.total_stops == 2
        types = {p.type for y in data.years for p in y.locations}
        assert types == {"gas", "maintenance"}

    def test_repeat_visits_to_same_location_each_get_their_own_point(self):
        # Regression: a location revisited later in the year used to be
        # collapsed down to its earliest visit and dropped from the map.
        loc = make_location("gulfport_ms", "Gulfport")
        fillups = [
            make_fillup(1, "2025-01-01", loc),
            make_fillup(2, "2025-10-11", loc),
        ]

        data = mapping.build_route_data(fillups, [])

        [year] = data.years
        assert [p.date for p in year.locations] == [
            datetime.date(2025, 1, 1),
            datetime.date(2025, 10, 11),
        ]
        assert year.locations[0].id != year.locations[1].id

    def test_points_within_a_year_are_sorted_by_date(self):
        loc = make_location("gulfport_ms", "Gulfport")
        fillups = [make_fillup(2, "2022-03-01", loc), make_fillup(1, "2022-01-01", loc)]

        data = mapping.build_route_data(fillups, [])

        [year] = data.years
        assert [p.date for p in year.locations] == [datetime.date(2022, 1, 1), datetime.date(2022, 3, 1)]

    def test_ungeocoded_location_is_omitted(self):
        loc = make_location("nowhere", "Nowhere", lat=None, long=None)
        fillups = [make_fillup(1, "2022-01-01", loc)]

        data = mapping.build_route_data(fillups, [])

        assert data.total_stops == 0

    def test_maintenance_record_with_no_location_is_skipped(self):
        records = [make_record(1, "2022-01-01", None)]

        data = mapping.build_route_data([], records)

        assert data.total_stops == 0
