"""Derived/computed logic ported from the original bus_gas_dashboard.html and
bus_data_reference.html: per-fill-up cost/gallon/driven/mpg, yearly
aggregates, major maintenance events, and the chart-ready series used by the
dashboard.

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
    CostOfOwnership,
    GasFillupOut,
    MaintenanceRecordOut,
    MajorEvent,
    MonthlySummary,
    ServiceAlert,
    StatCard,
    YearlySummary,
)

MAJOR_EVENT_THRESHOLD = 2000.0
MPG_ROLLING_WINDOW = 7
SERVICE_INTERVAL_MILES = 5000.0
SERVICE_DUE_SOON_MILES = 1000.0

_SERVICE_RECORD_RE = re.compile(r"oil change|\bpm\b", re.IGNORECASE)


@dataclass
class ComputedFillup:
    fillup: GasFillup
    cost_per_gal: float
    driven: float | None
    mpg: float | None


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

    return ComputedFillup(f, cost_per_gal, driven, mpg)


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


def mpg_fillups(computed: list[ComputedFillup]) -> list[ComputedFillup]:
    """Fill-ups with a usable mpg reading -- the shared "counts toward MPG
    stats" filter used by yearly/stat-card aggregation."""
    return [c for c in computed if c.mpg is not None]


def display_city(location: Location) -> str:
    return f"{location.city}, {location.state}" if location.state else location.city


def to_gas_out(c: ComputedFillup) -> GasFillupOut:
    f = c.fillup
    gps_lat = float(f.gps_latitude) if f.gps_latitude is not None else None
    gps_long = float(f.gps_longitude) if f.gps_longitude is not None else None
    location_lat = float(f.location.lat) if f.location.lat is not None else None
    location_long = float(f.location.long) if f.location.long is not None else None
    return GasFillupOut(
        id=f.id,
        date=f.date,
        odometer_miles=float(f.odometer_miles),
        gallons=float(f.gallons),
        price=float(f.price),
        notes=f.notes,
        city=display_city(f.location),
        # A photo's exact GPS (when captured) overrides the location's
        # coarser city-level geocode -- resolved here at read time, not
        # denormalized onto the row.
        latitude=gps_lat if gps_lat is not None else location_lat,
        longitude=gps_long if gps_long is not None else location_long,
        gps_latitude=gps_lat,
        gps_longitude=gps_long,
        cost_per_gal=c.cost_per_gal,
        driven=c.driven,
        mpg=c.mpg,
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


def yearly_summary(computed: list[ComputedFillup], records: list[MaintenanceRecord]) -> list[YearlySummary]:
    by_year: dict[int, list[ComputedFillup]] = defaultdict(list)
    for c in computed:
        by_year[c.fillup.date.year].append(c)

    maintenance_cost_by_year: dict[int, float] = defaultdict(float)
    for r in records:
        maintenance_cost_by_year[r.date.year] += float(r.cost)

    out = []
    for year in sorted(set(by_year) | set(maintenance_cost_by_year)):
        rows = by_year.get(year, [])
        cost = sum(float(c.fillup.price) for c in rows)
        gallons = sum(float(c.fillup.gallons) for c in rows)
        miles = sum(c.driven for c in rows if c.driven)
        # Weighted by miles/gallons (sum driven / sum gallons of the
        # mpg-bearing rows), not a plain mean of each row's mpg ratio -- a
        # mean-of-ratios gives a short/partial fill-up the same weight as a
        # long full-tank one, even though it represents far fewer miles.
        mpg_gallons = sum(float(c.fillup.gallons) for c in mpg_fillups(rows))
        avg_mpg = miles / mpg_gallons if mpg_gallons else None
        out.append(
            YearlySummary(
                year=str(year),
                cost=cost,
                miles=miles,
                gallons=gallons,
                avg_mpg=avg_mpg,
                fillups=len(rows),
                maintenance_cost=maintenance_cost_by_year.get(year, 0.0),
            )
        )
    return out


def major_events(records: list[MaintenanceRecord]) -> list[MajorEvent]:
    events = [r for r in records if float(r.cost) >= MAJOR_EVENT_THRESHOLD]
    events.sort(key=lambda r: r.date)
    return [MajorEvent(date=r.date, cost=float(r.cost), label=r.expense, is_major=True) for r in events]


def all_maintenance_events(records: list[MaintenanceRecord]) -> list[MajorEvent]:
    """Every maintenance record (not just those over MAJOR_EVENT_THRESHOLD),
    chronological, each flagged with whether it clears the threshold -- feeds
    the fuel-economy chart's maintenance markers, which color by that flag
    rather than dropping the smaller events entirely."""
    events = sorted(records, key=lambda r: r.date)
    return [
        MajorEvent(date=r.date, cost=float(r.cost), label=r.expense, is_major=float(r.cost) >= MAJOR_EVENT_THRESHOLD)
        for r in events
    ]


def is_service_record(expense: str) -> bool:
    """Matched by substring/regex on the expense field -- covers this log's
    actual wording for oil changes and "PM" (preventive maintenance) service
    visits, e.g. "Oil change/ PM maintance check" or "PM Service"."""
    return bool(_SERVICE_RECORD_RE.search(expense))


def sorted_service_records(records: list[MaintenanceRecord]) -> list[MaintenanceRecord]:
    """Service-type maintenance records that have an odometer reading,
    ordered by (date, id) -- the shared ordering both service_status (most
    recent one) and mapping._since_service_miles (nearest-prior at every
    historical point) key off of, so the "what counts as the anchoring
    service record" rule only lives in one place."""
    return sorted(
        (r for r in records if r.odometer_miles is not None and is_service_record(r.expense)),
        key=lambda r: (r.date, r.id),
    )


def service_status(computed: list[ComputedFillup], records: list[MaintenanceRecord]) -> ServiceAlert | None:
    """Miles until the next assumed-every-5000-miles service, based on the
    most recent service-type maintenance record that has an odometer
    reading. Records with no place aren't possible anymore, but odometer is
    still optional on a MaintenanceRecord, so a service logged without one
    can't anchor this calculation and is skipped in favor of an earlier
    record that has one. Returns None if there's no odometer reading at all,
    or no service record to anchor to."""
    odometers = [float(c.fillup.odometer_miles) for c in computed]
    odometers += [float(r.odometer_miles) for r in records if r.odometer_miles is not None]
    if not odometers:
        return None

    service_records = sorted_service_records(records)
    if not service_records:
        return None
    last = service_records[-1]

    current_odometer = max(odometers)
    last_odometer = float(last.odometer_miles)
    miles_since = current_odometer - last_odometer
    miles_until = SERVICE_INTERVAL_MILES - miles_since
    progress_pct = min(100.0, max(0.0, miles_since / SERVICE_INTERVAL_MILES * 100))

    if miles_until <= 0:
        level = "overdue"
    elif miles_until <= SERVICE_DUE_SOON_MILES:
        level = "due_soon"
    else:
        level = "ok"

    return ServiceAlert(
        level=level,
        miles_since_service=miles_since,
        miles_until_next=miles_until,
        last_service_date=last.date,
        last_service_odometer=last_odometer,
        current_odometer=current_odometer,
        interval_miles=SERVICE_INTERVAL_MILES,
        progress_pct=progress_pct,
    )


def cost_of_ownership(computed: list[ComputedFillup], records: list[MaintenanceRecord]) -> CostOfOwnership:
    gas_total = sum(float(c.fillup.price) for c in computed)
    gas_gallons = sum(float(c.fillup.gallons) for c in computed)
    gas_avg_cost_per_gal = gas_total / gas_gallons if gas_gallons else 0.0
    maintenance_total = sum(float(r.cost) for r in records)
    maintenance_visits = len(records)
    total_cost = gas_total + maintenance_total
    total_miles = sum(c.driven for c in computed if c.driven)

    # total_cost can go negative (e.g. a warranty credit logged as a
    # negative-cost maintenance record outweighs gas spend), and gas_total
    # alone can exceed total_cost when maintenance nets negative -- clamp so
    # the dashboard's gas/maintenance split bar never gets an out-of-range
    # width from either case.
    gas_share_pct = min(100.0, max(0.0, gas_total / total_cost * 100)) if total_cost > 0 else 0.0

    return CostOfOwnership(
        total_cost=total_cost,
        total_miles=total_miles,
        cost_per_mile=total_cost / total_miles if total_miles else 0.0,
        gas_total=gas_total,
        gas_gallons=gas_gallons,
        gas_avg_cost_per_gal=gas_avg_cost_per_gal,
        gas_share_pct=gas_share_pct,
        maintenance_total=maintenance_total,
        maintenance_visits=maintenance_visits,
        maintenance_cost_per_mile=maintenance_total / total_miles if total_miles else 0.0,
    )


def stat_cards(computed: list[ComputedFillup], records: list[MaintenanceRecord]) -> list[StatCard]:
    total_spent = sum(float(c.fillup.price) for c in computed)
    total_gal = sum(float(c.fillup.gallons) for c in computed)
    mpgs = [c.mpg for c in mpg_fillups(computed)]
    avg_mpg = sum(mpgs) / len(mpgs) if mpgs else 0.0
    avg_cpg = total_spent / total_gal if total_gal else 0.0
    total_maint = sum(float(r.cost) for r in records)
    total_combined = total_spent + total_maint

    return [
        StatCard(label="Total spent on gas", value=f"${total_spent:,.0f}"),
        StatCard(label="Total gallons", value=f"{total_gal:,.0f} gal"),
        StatCard(label="Avg cost / gallon", value=f"${avg_cpg:.2f}"),
        StatCard(label="Avg MPG", value=f"{avg_mpg:.1f} mpg"),
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


def rolling_weighted_mpg(computed: list[ComputedFillup], window: int) -> list[ChartPoint]:
    """Rolling mpg over the trailing `window` mpg-bearing fill-ups, weighted
    by miles/gallons (sum driven / sum gallons) rather than a plain mean of
    each fill-up's own mpg ratio -- see yearly_summary for why that matters.
    `computed` need not be pre-filtered to mpg-bearing rows."""
    rows = mpg_fillups(computed)
    out = []
    for i in range(len(rows)):
        start = max(0, i - window + 1)
        window_rows = rows[start : i + 1]
        driven_sum = sum(c.driven for c in window_rows)
        gallons_sum = sum(float(c.fillup.gallons) for c in window_rows)
        out.append(ChartPoint(x=rows[i].fillup.date, y=driven_sum / gallons_sum))
    return out


def monthly_summary(computed: list[ComputedFillup]) -> list[MonthlySummary]:
    """Calendar-month aggregates, mirroring yearly_summary but bucketed by
    month -- unlike a fill-up-count rolling window, a calendar month lines up
    with real-world seasonal effects (e.g. diesel heater draw in winter),
    so winter-vs-summer swings show up as their own signal instead of being
    smeared across a window that spans a variable amount of time."""
    by_month: dict[str, list[ComputedFillup]] = defaultdict(list)
    for c in computed:
        by_month[c.fillup.date.strftime("%Y-%m")].append(c)

    out = []
    for month in sorted(by_month):
        rows = by_month[month]
        miles = sum(c.driven for c in rows if c.driven)
        mpg_gallons = sum(float(c.fillup.gallons) for c in mpg_fillups(rows))
        avg_mpg = miles / mpg_gallons if mpg_gallons else None
        out.append(
            MonthlySummary(
                month=month,
                avg_mpg=avg_mpg,
                miles=miles,
                gallons=sum(float(c.fillup.gallons) for c in rows),
                fillups=len(rows),
            )
        )
    return out


def cumulative(dates_and_values: list[tuple[date, float]]) -> list[ChartPoint]:
    ordered = sorted(dates_and_values, key=lambda dv: dv[0])
    out = []
    running = 0.0
    for d, v in ordered:
        running += v
        out.append(ChartPoint(x=d, y=round(running, 2)))
    return out
