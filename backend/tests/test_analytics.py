import datetime
import json
from pathlib import Path

import pytest

from app.models import GasFillup, MaintenanceRecord
from app.services import analytics
from app.services.dashboard_summary import build_dashboard_summary

FIXTURES_DIR = Path(__file__).parent.parent / "seed" / "fixtures"


def make_fillup(id: int, date: str, odometer_miles: float, gallons: float, price: float, notes: str = "") -> GasFillup:
    return GasFillup(
        id=id,
        date=datetime.date.fromisoformat(date),
        odometer_miles=odometer_miles,
        gallons=gallons,
        price=price,
        notes=notes,
    )


def make_record(
    id: int, date: str, cost: float, expense: str = "Repair", odometer_miles: float | None = None
) -> MaintenanceRecord:
    return MaintenanceRecord(
        id=id, date=datetime.date.fromisoformat(date), expense=expense, cost=cost, odometer_miles=odometer_miles
    )


class TestComputeFillups:
    def test_first_fillup_has_no_driven_or_mpg(self):
        [c] = analytics.compute_fillups([make_fillup(1, "2021-01-01", 100000, 20, 60)])
        assert c.driven is None
        assert c.mpg is None
        assert c.cost_per_gal == pytest.approx(3.0)

    def test_driven_and_mpg_from_previous_odometer(self):
        fillups = [
            make_fillup(1, "2021-01-01", 100000, 20, 60),
            make_fillup(2, "2021-01-08", 100300, 15, 45),
        ]
        computed = analytics.compute_fillups(fillups)
        assert computed[1].driven == pytest.approx(300)
        assert computed[1].mpg == pytest.approx(20.0)

    def test_sorts_out_of_order_input_by_date(self):
        fillups = [
            make_fillup(2, "2021-01-08", 100300, 15, 45),
            make_fillup(1, "2021-01-01", 100000, 20, 60),
        ]
        computed = analytics.compute_fillups(fillups)
        assert [c.fillup.id for c in computed] == [1, 2]

    def test_non_positive_driven_yields_no_mpg(self):
        # A backdated/erroneous odometer reading (equal or lower than the
        # previous one) shouldn't produce a nonsensical or divide-by-zero mpg.
        fillups = [
            make_fillup(1, "2021-01-01", 100000, 20, 60),
            make_fillup(2, "2021-01-08", 100000, 15, 45),
        ]
        computed = analytics.compute_fillups(fillups)
        assert computed[1].driven is None
        assert computed[1].mpg is None


class TestYearlySummary:
    def test_aggregates_per_year_and_averages_mpg_across_all_fillups(self):
        fillups = [
            make_fillup(1, "2021-01-01", 100000, 20, 60),
            # notes text (e.g. "Not a full fillup") no longer affects the average.
            make_fillup(2, "2021-01-08", 100300, 10, 30, notes="Not a full fillup"),
            make_fillup(3, "2021-01-15", 100700, 20, 60),
            make_fillup(4, "2022-01-01", 101000, 20, 60),
        ]
        computed = analytics.compute_fillups(fillups)
        summary = {y.year: y for y in analytics.yearly_summary(computed, [])}

        assert summary["2021"].fillups == 3
        assert summary["2021"].miles == pytest.approx(700)
        # avg mpg across both mpg-bearing rows: 300/10=30 and 400/20=20 -> 25
        assert summary["2021"].avg_mpg == pytest.approx(25.0)
        assert summary["2022"].fillups == 1

    def test_aggregates_maintenance_cost_per_year(self):
        fillups = [make_fillup(1, "2021-01-01", 100000, 20, 60)]
        records = [
            make_record(1, "2021-03-01", 500),
            make_record(2, "2021-06-01", 250),
            make_record(3, "2022-01-01", 1000),
        ]
        computed = analytics.compute_fillups(fillups)
        summary = {y.year: y for y in analytics.yearly_summary(computed, records)}

        assert summary["2021"].maintenance_cost == pytest.approx(750)
        assert summary["2022"].maintenance_cost == pytest.approx(1000)

    def test_year_with_only_maintenance_and_no_fillups_still_appears(self):
        records = [make_record(1, "2023-05-01", 300)]

        summary = {y.year: y for y in analytics.yearly_summary([], records)}

        assert summary["2023"].maintenance_cost == pytest.approx(300)
        assert summary["2023"].fillups == 0


class TestMajorEvents:
    def test_filters_by_threshold(self):
        records = [make_record(1, "2021-01-01", 500), make_record(2, "2021-02-01", 2500)]
        events = analytics.major_events(records)
        assert len(events) == 1
        assert events[0].cost == 2500


class TestIsServiceRecord:
    def test_matches_oil_change(self):
        assert analytics.is_service_record("Glow PLugs, oil change") is True

    def test_matches_pm_as_whole_word(self):
        assert analytics.is_service_record("PM Service, shocks") is True
        assert analytics.is_service_record("Oil change/ PM maintance check") is True

    def test_does_not_match_pm_as_substring(self):
        # "pm" must match as a whole word -- e.g. a made-up "Pump replacement"
        # shouldn't trigger it.
        assert analytics.is_service_record("Pump replacement") is False

    def test_unrelated_expense_not_a_service(self):
        assert analytics.is_service_record("New Transmission") is False


class TestServiceStatus:
    def test_ok_when_well_under_the_interval(self):
        fillups = [make_fillup(1, "2021-06-01", 101500, 20, 60)]
        records = [make_record(1, "2021-01-01", 100, expense="Oil change", odometer_miles=100000)]
        status = analytics.service_status(analytics.compute_fillups(fillups), records)

        assert status.level == "ok"
        assert status.miles_since_service == pytest.approx(1500)
        assert status.miles_until_next == pytest.approx(3500)
        assert status.last_service_odometer == pytest.approx(100000)
        assert status.current_odometer == pytest.approx(101500)

    def test_due_soon_within_1000_miles_of_interval(self):
        fillups = [make_fillup(1, "2021-06-01", 104200, 20, 60)]
        records = [make_record(1, "2021-01-01", 100, expense="PM Service", odometer_miles=100000)]
        status = analytics.service_status(analytics.compute_fillups(fillups), records)

        assert status.level == "due_soon"
        assert status.miles_until_next == pytest.approx(800)

    def test_overdue_past_the_interval(self):
        fillups = [make_fillup(1, "2021-06-01", 106000, 20, 60)]
        records = [make_record(1, "2021-01-01", 100, expense="Oil change", odometer_miles=100000)]
        status = analytics.service_status(analytics.compute_fillups(fillups), records)

        assert status.level == "overdue"
        assert status.miles_until_next == pytest.approx(-1000)

    def test_ignores_service_record_with_no_odometer_in_favor_of_an_earlier_one(self):
        fillups = [make_fillup(1, "2021-06-01", 101500, 20, 60)]
        records = [
            make_record(1, "2021-01-01", 100, expense="Oil change", odometer_miles=100000),
            make_record(2, "2021-05-01", 100, expense="PM Service", odometer_miles=None),
        ]
        status = analytics.service_status(analytics.compute_fillups(fillups), records)

        # Anchors to the 2021-01-01 record since the more recent one has no
        # odometer reading to anchor to.
        assert status.last_service_date == datetime.date(2021, 1, 1)

    def test_non_service_maintenance_records_are_ignored(self):
        fillups = [make_fillup(1, "2021-06-01", 101500, 20, 60)]
        records = [make_record(1, "2021-01-01", 40000, expense="New Transmission", odometer_miles=100000)]
        status = analytics.service_status(analytics.compute_fillups(fillups), records)

        assert status is None

    def test_none_when_no_service_records_at_all(self):
        fillups = [make_fillup(1, "2021-06-01", 101500, 20, 60)]
        status = analytics.service_status(analytics.compute_fillups(fillups), [])

        assert status is None


class TestServiceStatusProgress:
    def test_progress_pct_partway_through_interval(self):
        fillups = [make_fillup(1, "2021-06-01", 101500, 20, 60)]
        records = [make_record(1, "2021-01-01", 100, expense="Oil change", odometer_miles=100000)]
        status = analytics.service_status(analytics.compute_fillups(fillups), records)

        assert status.interval_miles == pytest.approx(analytics.SERVICE_INTERVAL_MILES)
        assert status.progress_pct == pytest.approx(30.0)

    def test_progress_pct_clamped_at_100_when_overdue(self):
        fillups = [make_fillup(1, "2021-06-01", 110000, 20, 60)]
        records = [make_record(1, "2021-01-01", 100, expense="Oil change", odometer_miles=100000)]
        status = analytics.service_status(analytics.compute_fillups(fillups), records)

        assert status.progress_pct == pytest.approx(100.0)

    def test_progress_pct_clamped_at_0_when_serviced_this_instant(self):
        fillups = [make_fillup(1, "2021-06-01", 100000, 20, 60)]
        records = [make_record(1, "2021-06-01", 100, expense="Oil change", odometer_miles=100000)]
        status = analytics.service_status(analytics.compute_fillups(fillups), records)

        assert status.progress_pct == pytest.approx(0.0)


class TestCostOfOwnership:
    def test_arithmetic_across_gas_and_maintenance(self):
        fillups = [
            make_fillup(1, "2021-01-01", 100000, 20, 60),
            make_fillup(2, "2021-01-08", 100300, 15, 45),
        ]
        records = [make_record(1, "2021-03-01", 500)]
        computed = analytics.compute_fillups(fillups)

        result = analytics.cost_of_ownership(computed, records)

        assert result.gas_total == pytest.approx(105)
        assert result.gas_gallons == pytest.approx(35)
        assert result.gas_avg_cost_per_gal == pytest.approx(3.0)
        assert result.maintenance_total == pytest.approx(500)
        assert result.maintenance_visits == 1
        assert result.total_cost == pytest.approx(605)
        assert result.total_miles == pytest.approx(300)
        assert result.cost_per_mile == pytest.approx(605 / 300)
        assert result.gas_share_pct == pytest.approx(105 / 605 * 100)
        assert result.maintenance_cost_per_mile == pytest.approx(500 / 300)

    def test_handles_no_data_without_dividing_by_zero(self):
        result = analytics.cost_of_ownership([], [])

        assert result.total_cost == 0
        assert result.cost_per_mile == 0
        assert result.gas_share_pct == 0
        assert result.maintenance_cost_per_mile == 0

    def test_handles_no_driven_miles_without_dividing_by_zero(self):
        # A single fill-up has no previous odometer to derive miles driven from.
        fillups = [make_fillup(1, "2021-01-01", 100000, 20, 60)]
        computed = analytics.compute_fillups(fillups)

        result = analytics.cost_of_ownership(computed, [])

        assert result.total_miles == 0
        assert result.cost_per_mile == 0


class TestRollingAvgAndCumulative:
    def test_rolling_avg_widens_until_window_full(self):
        points = [analytics.ChartPoint(x=datetime.date(2021, 1, i + 1), y=v) for i, v in enumerate([10, 20, 30])]
        avg = analytics.rolling_avg(points, window=2)
        assert avg[0].y == pytest.approx(10)
        assert avg[1].y == pytest.approx(15)
        assert avg[2].y == pytest.approx(25)

    def test_cumulative_sums_in_date_order_regardless_of_input_order(self):
        result = analytics.cumulative([(datetime.date(2021, 1, 2), 5.0), (datetime.date(2021, 1, 1), 10.0)])
        assert [p.y for p in result] == [10.0, 15.0]


class TestFixtureRegression:
    """Sanity-checks computed totals against the real seeded historical
    dataset, independently re-summed here from the same fixture files."""

    @pytest.fixture(scope="class")
    def fixtures(self):
        gas_raw = json.loads((FIXTURES_DIR / "gas_raw.json").read_text())
        maint_raw = json.loads((FIXTURES_DIR / "maint_raw.json").read_text())
        fillups = [
            make_fillup(i, r["date"], r["odometer_miles"], r["gallons"], r["price"], r["notes"])
            for i, r in enumerate(gas_raw, start=1)
        ]
        records = [
            make_record(i, r["date"], r["cost"], r["expense"]) for i, r in enumerate(maint_raw, start=1)
        ]
        return fillups, records, gas_raw, maint_raw

    def test_row_counts(self, fixtures):
        fillups, records, gas_raw, maint_raw = fixtures
        assert len(fillups) == 198
        assert len(records) == 74

    def test_total_spend_matches_independent_sum(self, fixtures):
        fillups, records, gas_raw, maint_raw = fixtures
        summary = build_dashboard_summary(fillups, records)
        stat_by_label = {s.label: s.value for s in summary.stats}

        expected_gas_total = round(sum(r["price"] for r in gas_raw))
        expected_maint_total = round(sum(r["cost"] for r in maint_raw))

        assert stat_by_label["Total spent on gas"] == f"${expected_gas_total:,}"
        assert stat_by_label["Total maintenance"] == f"${expected_maint_total:,}"

    def test_major_events_include_known_engine_replacement(self, fixtures):
        fillups, records, gas_raw, maint_raw = fixtures
        events = analytics.major_events(records)
        assert any(e.date == datetime.date(2025, 7, 21) and e.cost > 40000 for e in events)

    def test_includes_negative_refund_row(self, fixtures):
        fillups, records, gas_raw, maint_raw = fixtures
        assert any(r.cost < 0 for r in records)
