import datetime

import pytest

from app.models import GasFillup
from app.services import analytics
from app.services.narrative import ENGINE_REPLACEMENT_DATE, TRANSMISSION_REPLACEMENT_DATE, era_mpg_summary


def make_fillup(id: int, date: str, odometer_miles: float, gallons: float, price: float, notes: str = "") -> GasFillup:
    return GasFillup(
        id=id,
        date=datetime.date.fromisoformat(date),
        odometer_miles=odometer_miles,
        gallons=gallons,
        price=price,
        notes=notes,
    )


class TestEraMpgSummary:
    def test_buckets_before_and_after_each_replacement_date(self):
        fillups = [
            make_fillup(1, "2025-01-01", 100000, 20, 60),  # before engine, no driven yet
            make_fillup(2, "2025-01-08", 100200, 20, 60),  # before engine: 10 mpg
            make_fillup(3, "2025-08-01", 100400, 20, 60),  # engine->trans: 10 mpg
            make_fillup(4, "2025-08-08", 100600, 20, 60),  # engine->trans: 10 mpg
            make_fillup(5, "2025-10-01", 100800, 20, 60),  # since trans: 10 mpg
            make_fillup(6, "2025-10-08", 101000, 20, 60),  # since trans: 10 mpg
        ]
        computed = analytics.compute_fillups(fillups)

        summary = era_mpg_summary(computed)

        assert summary.before_engine == pytest.approx(10.0)
        assert summary.engine_to_transmission == pytest.approx(10.0)
        assert summary.since_transmission == pytest.approx(10.0)
        assert summary.engine_replacement_date == ENGINE_REPLACEMENT_DATE
        assert summary.transmission_replacement_date == TRANSMISSION_REPLACEMENT_DATE

    def test_none_when_a_bucket_has_no_clean_points(self):
        fillups = [make_fillup(1, "2025-01-01", 100000, 20, 60)]
        computed = analytics.compute_fillups(fillups)

        summary = era_mpg_summary(computed)

        assert summary.before_engine is None
        assert summary.engine_to_transmission is None
        assert summary.since_transmission is None

    def test_excluded_fillups_do_not_count_toward_era_averages(self):
        fillups = [
            make_fillup(1, "2025-01-01", 100000, 20, 60),
            make_fillup(2, "2025-01-08", 100200, 20, 60, notes="Not a full fillup"),
        ]
        computed = analytics.compute_fillups(fillups)

        summary = era_mpg_summary(computed)

        assert summary.before_engine is None
