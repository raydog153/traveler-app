"""Bespoke dashboard narrative text tied to this specific vehicle's history
(the July 2025 engine replacement and September 2025 transmission
replacement). Kept separate from analytics.py, which computes generic,
dataset-agnostic stats -- this module is the one place that bakes in
knowledge of specific historical events and their dates.
"""

from datetime import date, timedelta

from app.schemas import EraMpgSummary
from app.services.analytics import ComputedFillup, clean_mpg_fillups

ENGINE_REPLACEMENT_DATE = date(2025, 7, 21)
TRANSMISSION_REPLACEMENT_DATE = date(2025, 9, 25)


def _avg_mpg_between(
    clean_points: list[tuple[date, float]], lo: date | None = None, hi: date | None = None
) -> float | None:
    vals = [mpg for d, mpg in clean_points if (lo is None or d >= lo) and (hi is None or d < hi)]
    return sum(vals) / len(vals) if vals else None


def era_mpg_summary(computed: list[ComputedFillup]) -> EraMpgSummary:
    """Average clean MPG bucketed by this vehicle's engine/transmission
    replacement dates -- the same bucketing narrative_text uses, exposed as
    discrete numeric fields for the dashboard's era chips."""
    clean_points = [(c.fillup.date, c.mpg) for c in clean_mpg_fillups(computed)]

    return EraMpgSummary(
        before_engine=_avg_mpg_between(clean_points, hi=ENGINE_REPLACEMENT_DATE),
        engine_to_transmission=_avg_mpg_between(
            clean_points, lo=ENGINE_REPLACEMENT_DATE, hi=TRANSMISSION_REPLACEMENT_DATE
        ),
        since_transmission=_avg_mpg_between(clean_points, lo=TRANSMISSION_REPLACEMENT_DATE),
        engine_replacement_date=ENGINE_REPLACEMENT_DATE,
        transmission_replacement_date=TRANSMISSION_REPLACEMENT_DATE,
    )


def narrative_text(computed: list[ComputedFillup]) -> str:
    clean_points = [(c.fillup.date, c.mpg) for c in clean_mpg_fillups(computed)]

    def avg_between(lo: date | None = None, hi: date | None = None) -> str:
        val = _avg_mpg_between(clean_points, lo, hi)
        return f"{val:.1f}" if val is not None else "n/a"

    before = avg_between(hi=ENGINE_REPLACEMENT_DATE)
    last_12mo = avg_between(lo=ENGINE_REPLACEMENT_DATE - timedelta(days=365), hi=ENGINE_REPLACEMENT_DATE)
    after_engine = avg_between(lo=ENGINE_REPLACEMENT_DATE, hi=TRANSMISSION_REPLACEMENT_DATE)
    after_trans = avg_between(lo=TRANSMISSION_REPLACEMENT_DATE)

    return (
        f"After the engine swap, MPG dropped. Average MPG before the July 21, 2025 engine "
        f"replacement: {before} (last 12 months prior: {last_12mo}). Between the new engine "
        f"and the September 25 transmission: {after_engine}. Since the new transmission: "
        f"{after_trans} — still running below the pre-engine average, though the sample "
        f"since is small."
    )
