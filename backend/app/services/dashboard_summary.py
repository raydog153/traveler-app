"""Assembles the full dashboard payload from the generic analytics primitives
and the bespoke narrative text. Lives above both so neither has to import the
other -- analytics.py stays dataset-agnostic and narrative.py only depends on
analytics.py, not the reverse.
"""

from app.models import GasFillup, MaintenanceRecord
from app.schemas import ChartPoint, DashboardSummary
from app.services import analytics
from app.services.narrative import era_mpg_summary, narrative_text


def build_dashboard_summary(
    fillups: list[GasFillup], records: list[MaintenanceRecord]
) -> DashboardSummary:
    computed = analytics.compute_fillups(fillups)

    price_series = [ChartPoint(x=c.fillup.date, y=c.cost_per_gal) for c in computed]
    mpg_points = [c for c in computed if c.mpg is not None]
    clean_pts = [ChartPoint(x=c.fillup.date, y=c.mpg) for c in mpg_points if c.is_clean]
    excluded_pts = [ChartPoint(x=c.fillup.date, y=c.mpg) for c in mpg_points if not c.is_clean]

    subhead = ""
    if computed:
        subhead = (
            f"{len(computed)} fill-ups · {computed[0].fillup.date.isoformat()} to "
            f"{computed[-1].fillup.date.isoformat()} · cross-referenced with {len(records)} "
            f"maintenance records"
        )

    major_events = analytics.major_events(records)

    return DashboardSummary(
        subhead=subhead,
        stats=analytics.stat_cards(computed, records),
        yearly=analytics.yearly_summary(computed, records),
        major_events=major_events,
        major_events_by_cost=sorted(major_events, key=lambda e: -e.cost),
        service_alert=analytics.service_status(computed, records),
        narrative=narrative_text(computed),
        price_per_gallon_series=price_series,
        mpg_clean_points=clean_pts,
        mpg_excluded_points=excluded_pts,
        mpg_rolling_avg=analytics.rolling_avg(clean_pts, analytics.MPG_ROLLING_WINDOW),
        cumulative_gas=analytics.cumulative([(c.fillup.date, float(c.fillup.price)) for c in computed]),
        cumulative_maintenance=analytics.cumulative([(r.date, float(r.cost)) for r in records]),
        cost_of_ownership=analytics.cost_of_ownership(computed, records),
        era_mpg=era_mpg_summary(computed),
    )
