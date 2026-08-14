import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GasFillupIn(BaseModel):
    date: dt.date
    odometer_miles: float = Field(gt=0)
    gallons: float = Field(gt=0)
    price: float = Field(ge=0)
    notes: str = ""
    city: str = Field(min_length=1)
    # Exact GPS from a fill-up photo's EXIF, if one was used -- see
    # GasFillup.gps_latitude/gps_longitude. None on every save that didn't
    # come from (or preserve) a photo scan.
    gps_latitude: float | None = None
    gps_longitude: float | None = None


class GasFillupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: dt.date
    odometer_miles: float
    gallons: float
    price: float
    notes: str
    city: str
    latitude: float | None
    longitude: float | None
    # Raw (un-fallback'd) photo GPS override, distinct from latitude/longitude
    # above -- exposed so the edit form can round-trip a previously-captured
    # value without re-scanning a photo. latitude/longitude remain the
    # fallback-resolved values used everywhere else (map, dashboard).
    gps_latitude: float | None
    gps_longitude: float | None
    cost_per_gal: float
    driven: float | None
    mpg: float | None


class OdometerScanResult(BaseModel):
    """Response from POST /api/gas/fillups/scan-odometer. Every field is
    best-effort and may be None -- `warnings` explains which pieces of the
    photo couldn't be read, but a partial result is never an error; the
    add-fillup form just leaves those fields for the user to fill in."""

    odometer_miles: float | None = None
    date: dt.date | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    warnings: list[str] = []


class MaintenanceRecordIn(BaseModel):
    date: dt.date
    expense: str = Field(min_length=1)
    place: str = Field(min_length=1)
    odometer_miles: float | None = None
    vendor: str = ""
    cost: float


class MaintenanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: dt.date
    expense: str
    place: str
    odometer_miles: float | None
    vendor: str
    cost: float
    is_major: bool


class StatCard(BaseModel):
    label: str
    value: str


class YearlySummary(BaseModel):
    year: str
    cost: float
    miles: float
    gallons: float
    avg_mpg: float | None
    fillups: int
    maintenance_cost: float


class MajorEvent(BaseModel):
    date: dt.date
    cost: float
    label: str


class ServiceAlert(BaseModel):
    level: Literal["ok", "due_soon", "overdue"]
    miles_since_service: float
    miles_until_next: float
    last_service_date: dt.date
    last_service_odometer: float
    current_odometer: float
    interval_miles: float
    progress_pct: float


class ChartPoint(BaseModel):
    x: dt.date
    y: float


class CostOfOwnership(BaseModel):
    total_cost: float
    total_miles: float
    cost_per_mile: float
    gas_total: float
    gas_gallons: float
    gas_avg_cost_per_gal: float
    gas_share_pct: float
    maintenance_total: float
    maintenance_visits: int
    maintenance_cost_per_mile: float


class TripStats(BaseModel):
    states_visited: int
    longest_leg_miles: float | None
    longest_stay_days: int | None
    avg_miles_between_fillups: float | None
    maintenance_stops: int


class DashboardSummary(BaseModel):
    subhead: str
    stats: list[StatCard]
    yearly: list[YearlySummary]
    major_events: list[MajorEvent]
    major_events_by_cost: list[MajorEvent]
    service_alert: ServiceAlert | None
    price_per_gallon_series: list[ChartPoint]
    mpg_points: list[ChartPoint]
    mpg_rolling_avg: list[ChartPoint]
    cumulative_gas: list[ChartPoint]
    cumulative_maintenance: list[ChartPoint]
    cost_of_ownership: CostOfOwnership


class RouteLocation(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    date: dt.date
    type: Literal["gas", "maintenance"]
    detail: str | None = None
    amount: float | None = None
    gallons: float | None = None
    mpg: float | None = None
    odometer_miles: float | None = None
    since_service_miles: float | None = None


class RouteYear(BaseModel):
    year: str
    locations: list[RouteLocation]


class RouteData(BaseModel):
    total_stops: int
    years: list[RouteYear]
    trip_stats: TripStats
