import datetime

import pytest

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

    def test_gas_points_carry_amount_gallons_mpg_and_odometer(self):
        loc = make_location("gulfport_ms", "Gulfport")
        fillups = [
            make_fillup(1, "2022-01-01", loc),
            make_fillup(2, "2022-01-08", loc),
        ]
        fillups[0].odometer_miles = 100000
        fillups[0].gallons = 20
        fillups[0].price = 60
        fillups[1].odometer_miles = 100200
        fillups[1].gallons = 20
        fillups[1].price = 60

        data = mapping.build_route_data(fillups, [])

        [year] = data.years
        second = year.locations[1]
        assert second.amount == pytest.approx(60)
        assert second.gallons == pytest.approx(20)
        assert second.mpg == pytest.approx(10.0)
        assert second.odometer_miles == pytest.approx(100200)

    def test_maintenance_point_carries_amount_and_since_service(self):
        loc = make_location("gulfport_ms", "Gulfport")
        records = [
            make_record(1, "2022-01-01", loc, expense="Oil change"),
            make_record(2, "2022-06-01", loc, expense="Brakes"),
        ]
        records[0].odometer_miles = 100000
        records[0].cost = 80
        records[1].odometer_miles = 100600
        records[1].cost = 300

        data = mapping.build_route_data([], records)

        [year] = data.years
        second = year.locations[1]
        assert second.amount == pytest.approx(300)
        assert second.since_service_miles == pytest.approx(600)


class TestTripStats:
    def test_states_visited_counts_distinct_states_across_gas_and_maintenance(self):
        gulfport = make_location("gulfport_ms", "Gulfport", state="MS")
        mobile = make_location("mobile_al", "Mobile", state="AL")
        fillups = [make_fillup(1, "2022-01-01", gulfport)]
        records = [make_record(1, "2022-02-01", mobile), make_record(2, "2022-03-01", gulfport)]

        data = mapping.build_route_data(fillups, records)

        assert data.trip_stats.states_visited == 2

    def test_longest_leg_is_the_farthest_consecutive_hop(self):
        # Roughly 1 degree of longitude at the equator is ~69 miles; use two
        # widely separated points and one nearby pair to get a clear max.
        near = make_location("a", "A", lat=30.0, long=-89.0)
        near2 = make_location("b", "B", lat=30.01, long=-89.0)
        far = make_location("c", "C", lat=40.0, long=-100.0)
        fillups = [
            make_fillup(1, "2022-01-01", near),
            make_fillup(2, "2022-01-02", near2),
            make_fillup(3, "2022-01-03", far),
        ]

        data = mapping.build_route_data(fillups, [])

        # near->near2 is under a mile; near2->far is several hundred miles.
        assert data.trip_stats.longest_leg_miles > 500

    def test_longest_stay_is_the_biggest_gap_between_consecutive_stops(self):
        loc = make_location("gulfport_ms", "Gulfport")
        fillups = [
            make_fillup(1, "2022-01-01", loc),
            make_fillup(2, "2022-01-10", loc),
            make_fillup(3, "2022-03-01", loc),
        ]

        data = mapping.build_route_data(fillups, [])

        assert data.trip_stats.longest_stay_days == 50

    def test_avg_miles_between_fillups(self):
        loc = make_location("gulfport_ms", "Gulfport")
        fillups = [
            make_fillup(1, "2022-01-01", loc),
            make_fillup(2, "2022-01-08", loc),
            make_fillup(3, "2022-01-15", loc),
        ]
        fillups[0].odometer_miles = 100000
        fillups[1].odometer_miles = 100300
        fillups[2].odometer_miles = 100500

        data = mapping.build_route_data(fillups, [])

        assert data.trip_stats.avg_miles_between_fillups == pytest.approx(250)

    def test_maintenance_stops_counts_all_records_regardless_of_geocoding(self):
        loc = make_location("gulfport_ms", "Gulfport")
        ungeocoded = make_location("nowhere", "Nowhere", lat=None, long=None)
        records = [make_record(1, "2022-01-01", loc), make_record(2, "2022-02-01", ungeocoded)]

        data = mapping.build_route_data([], records)

        assert data.trip_stats.maintenance_stops == 2

    def test_empty_dataset_returns_none_for_leg_and_stay(self):
        data = mapping.build_route_data([], [])

        assert data.trip_stats.states_visited == 0
        assert data.trip_stats.longest_leg_miles is None
        assert data.trip_stats.longest_stay_days is None
        assert data.trip_stats.avg_miles_between_fillups is None
        assert data.trip_stats.maintenance_stops == 0
