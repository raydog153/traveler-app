"""Assembles the full dashboard payload from the generic, dataset-agnostic
analytics primitives in analytics.py.
"""

from app.models import GasFillup, MaintenanceRecord
from app.schemas import ChartPoint, DashboardSummary
from app.services import analytics


def build_dashboard_summary(fillups: list[GasFillup], records: list[MaintenanceRecord]) -> DashboardSummary:
    computed = analytics.compute_fillups(fillups)

    price_series = [ChartPoint(x=c.fillup.date, y=c.cost_per_gal) for c in computed]
    mpg_pts = [ChartPoint(x=c.fillup.date, y=c.mpg) for c in analytics.mpg_fillups(computed)]

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
        price_per_gallon_series=price_series,
        mpg_points=mpg_pts,
        mpg_rolling_avg=analytics.rolling_avg(mpg_pts, analytics.MPG_ROLLING_WINDOW),
        cumulative_gas=analytics.cumulative([(c.fillup.date, float(c.fillup.price)) for c in computed]),
        cumulative_maintenance=analytics.cumulative([(r.date, float(r.cost)) for r in records]),
        cost_of_ownership=analytics.cost_of_ownership(computed, records),
    )
