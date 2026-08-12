"""Derived/computed logic ported from the original bus_gas_dashboard.html and
bus_data_reference.html: which fill-ups are "clean" for MPG purposes,
per-fill-up cost/gallon/driven/mpg, yearly aggregates, major maintenance
events, and the chart-ready series used by the dashboard.

Kept as plain Python over already-fetched rows rather than SQL window
functions: the dataset is a few hundred rows total, so this is simpler to
read/test than equivalent CTEs and the performance difference is immaterial.
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from app.models import GasFillup, Location, MaintenanceRecord
from app.schemas import (
    ChartPoint,
    GasFillupOut,
    MajorEvent,
    MaintenanceRecordOut,
    StatCard,
    YearlySummary,
)

MAJOR_EVENT_THRESHOLD = 2000.0
MPG_ROLLING_WINDOW = 7

_NOT_FULL_FILLUP = "not a full fillup"
_OFF_ON_MILEAGE = ("off on milage", "off on mileage")
_EST_WORD_RE = re.compile(r"\best\b")


def is_clean(notes: str | None) -> bool:
    if not notes:
        return True
    n = notes.lower()
    if _NOT_FULL_FILLUP in n:
        return False
    if any(phrase in n for phrase in _OFF_ON_MILEAGE):
        return False
    if _EST_WORD_RE.search(n):
        return False
    return True


@dataclass
class ComputedFillup:
    fillup: GasFillup
    cost_per_gal: float
    driven: float | None
    mpg: float | None
    is_clean: bool


def compute_from_previous(f: GasFillup, prev_odometer: float | None) -> ComputedFillup:
    """Derive one fill-up's cost/gal, miles driven, and mpg given the
    odometer reading of the fill-up immediately before it (by date, id
    order), or None if it's the very first fill-up on record."""
    gallons = float(f.gallons)
    cost_per_gal = float(f.price) / gallons if gallons else 0.0

    driven: float | None = None
    mpg: float | None = None
    if prev_odometer is not None:
        driven = float(f.odometer_miles) - prev_odometer
        if driven > 0 and gallons:
            mpg = driven / gallons
        else:
            driven = None

    return ComputedFillup(f, cost_per_gal, driven, mpg, is_clean(f.notes))


def compute_fillups(fillups: list[GasFillup]) -> list[ComputedFillup]:
    """Sort by (date, id) and derive cost/gal, miles driven, and mpg from the
    previous fill-up's odometer reading -- recomputed on every read so a
    backdated entry is naturally handled correctly."""
    ordered = sorted(fillups, key=lambda f: (f.date, f.id))
    out: list[ComputedFillup] = []
    prev_odometer: float | None = None
    for f in ordered:
        computed = compute_from_previous(f, prev_odometer)
        prev_odometer = float(f.odometer_miles)
        out.append(computed)
    return out


def clean_mpg_fillups(computed: list[ComputedFillup]) -> list[ComputedFillup]:
    """Fill-ups with a usable mpg reading that aren't flagged excluded --
    the shared "counts toward MPG stats" filter used by yearly/stat-card/
    narrative aggregation."""
    return [c for c in computed if c.mpg is not None and c.is_clean]


def display_city(location: Location) -> str:
    return f"{location.city}, {location.state}" if location.state else location.city


def to_gas_out(c: ComputedFillup) -> GasFillupOut:
    f = c.fillup
    return GasFillupOut(
        id=f.id,
        date=f.date,
        odometer_miles=float(f.odometer_miles),
        gallons=float(f.gallons),
        price=float(f.price),
        notes=f.notes,
        city=display_city(f.location),
        latitude=float(f.location.lat) if f.location.lat is not None else None,
        longitude=float(f.location.long) if f.location.long is not None else None,
        cost_per_gal=c.cost_per_gal,
        driven=c.driven,
        mpg=c.mpg,
        is_clean=c.is_clean,
    )


def to_maintenance_out(m: MaintenanceRecord) -> MaintenanceRecordOut:
    return MaintenanceRecordOut(
        id=m.id,
        date=m.date,
        expense=m.expense,
        place=display_city(m.location),
        odometer_miles=float(m.odometer_miles) if m.odometer_miles is not None else None,
        vendor=m.vendor,
        cost=float(m.cost),
        is_major=float(m.cost) >= MAJOR_EVENT_THRESHOLD,
    )


def yearly_summary(computed: list[ComputedFillup]) -> list[YearlySummary]:
    by_year: dict[int, list[ComputedFillup]] = defaultdict(list)
    for c in computed:
        by_year[c.fillup.date.year].append(c)

    out = []
    for year in sorted(by_year):
        rows = by_year[year]
        cost = sum(float(c.fillup.price) for c in rows)
        gallons = sum(float(c.fillup.gallons) for c in rows)
        miles = sum(c.driven for c in rows if c.driven)
        clean_mpgs = [c.mpg for c in clean_mpg_fillups(rows)]
        avg_mpg = sum(clean_mpgs) / len(clean_mpgs) if clean_mpgs else None
        out.append(
            YearlySummary(
                year=str(year),
                cost=cost,
                miles=miles,
                gallons=gallons,
                avg_mpg_clean=avg_mpg,
                fillups=len(rows),
            )
        )
    return out


def major_events(records: list[MaintenanceRecord]) -> list[MajorEvent]:
    events = [r for r in records if float(r.cost) >= MAJOR_EVENT_THRESHOLD]
    events.sort(key=lambda r: r.date)
    return [MajorEvent(date=r.date, cost=float(r.cost), label=r.expense) for r in events]


def stat_cards(computed: list[ComputedFillup], records: list[MaintenanceRecord]) -> list[StatCard]:
    total_spent = sum(float(c.fillup.price) for c in computed)
    total_gal = sum(float(c.fillup.gallons) for c in computed)
    clean_mpgs = [c.mpg for c in clean_mpg_fillups(computed)]
    avg_mpg = sum(clean_mpgs) / len(clean_mpgs) if clean_mpgs else 0.0
    avg_cpg = total_spent / total_gal if total_gal else 0.0
    total_maint = sum(float(r.cost) for r in records)
    total_combined = total_spent + total_maint

    return [
        StatCard(label="Total spent on gas", value=f"${total_spent:,.0f}"),
        StatCard(label="Total gallons", value=f"{total_gal:,.0f} gal"),
        StatCard(label="Avg cost / gallon", value=f"${avg_cpg:.2f}"),
        StatCard(label="Avg MPG (cleaned)", value=f"{avg_mpg:.1f} mpg"),
        StatCard(label="Total maintenance", value=f"${total_maint:,.0f}"),
        StatCard(label="Gas + maintenance", value=f"${total_combined:,.0f}"),
    ]


def rolling_avg(points: list[ChartPoint], window: int) -> list[ChartPoint]:
    out = []
    ys = [p.y for p in points]
    for i in range(len(points)):
        start = max(0, i - window + 1)
        window_vals = ys[start : i + 1]
        out.append(ChartPoint(x=points[i].x, y=sum(window_vals) / len(window_vals)))
    return out


def cumulative(dates_and_values: list[tuple[date, float]]) -> list[ChartPoint]:
    ordered = sorted(dates_and_values, key=lambda dv: dv[0])
    out = []
    running = 0.0
    for d, v in ordered:
        running += v
        out.append(ChartPoint(x=d, y=round(running, 2)))
    return out
