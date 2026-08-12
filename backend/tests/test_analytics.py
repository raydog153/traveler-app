import datetime
import json
from pathlib import Path

import pytest

from app.models import GasFillup, MaintenanceRecord
from app.services import analytics
from app.services.dashboard_summary import build_dashboard_summary

FIXTURES_DIR = Path(__file__).parent.parent / "seed" / "fixtures"


def make_fillup(id: int, date: str, odometer_miles: float, gallons: float, price: float, notes: str = "", city: str = "Test City") -> GasFillup:
    return GasFillup(
        id=id,
        date=datetime.date.fromisoformat(date),
        odometer_miles=odometer_miles,
        gallons=gallons,
        price=price,
        notes=notes,
        city=city,
    )


def make_record(id: int, date: str, cost: float, expense: str = "Repair") -> MaintenanceRecord:
    return MaintenanceRecord(id=id, date=datetime.date.fromisoformat(date), expense=expense, cost=cost)


class TestIsClean:
    def test_blank_notes_is_clean(self):
        assert analytics.is_clean("") is True
        assert analytics.is_clean(None) is True

    def test_not_a_full_fillup_is_excluded(self):
        assert analytics.is_clean("Not a full fillup") is False

    def test_off_on_mileage_variants_excluded(self):
        assert analytics.is_clean("80 min off on milage") is False
        assert analytics.is_clean("off on mileage") is False

    def test_est_word_excluded(self):
        assert analytics.is_clean("Est mileage") is False

    def test_est_substring_not_excluded(self):
        # "est" must match as a whole word -- "Best guess" shouldn't trigger it.
        assert analytics.is_clean("Best guess on this one") is True

    def test_unrelated_notes_are_clean(self):
        assert analytics.is_clean("No reciept") is True


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
    def test_aggregates_per_year_and_excludes_dirty_mpg_from_average(self):
        fillups = [
            make_fillup(1, "2021-01-01", 100000, 20, 60),
            make_fillup(2, "2021-01-08", 100300, 15, 45, notes="Not a full fillup"),
            make_fillup(3, "2021-01-15", 100700, 20, 60),
            make_fillup(4, "2022-01-01", 101000, 20, 60),
        ]
        computed = analytics.compute_fillups(fillups)
        summary = {y.year: y for y in analytics.yearly_summary(computed)}

        assert summary["2021"].fillups == 3
        # miles: 300 (excluded row still counts toward miles) + 400 = 700
        assert summary["2021"].miles == pytest.approx(700)
        # avg mpg only from the clean 3rd row (400 driven / 20 gal = 20mpg)
        assert summary["2021"].avg_mpg_clean == pytest.approx(20.0)
        assert summary["2022"].fillups == 1


class TestMajorEvents:
    def test_filters_by_threshold(self):
        records = [make_record(1, "2021-01-01", 500), make_record(2, "2021-02-01", 2500)]
        events = analytics.major_events(records)
        assert len(events) == 1
        assert events[0].cost == 2500


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
            make_fillup(i, r["date"], r["odometer_miles"], r["gallons"], r["price"], r["notes"], r["city"])
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
