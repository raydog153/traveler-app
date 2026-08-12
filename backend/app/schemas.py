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
    cost_per_gal: float
    driven: float | None
    mpg: float | None
    is_clean: bool


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
    avg_mpg_clean: float | None
    fillups: int


class MajorEvent(BaseModel):
    date: dt.date
    cost: float
    label: str


class ChartPoint(BaseModel):
    x: dt.date
    y: float


class DashboardSummary(BaseModel):
    subhead: str
    stats: list[StatCard]
    yearly: list[YearlySummary]
    major_events: list[MajorEvent]
    narrative: str
    price_per_gallon_series: list[ChartPoint]
    mpg_clean_points: list[ChartPoint]
    mpg_excluded_points: list[ChartPoint]
    mpg_rolling_avg: list[ChartPoint]
    cumulative_gas: list[ChartPoint]
    cumulative_maintenance: list[ChartPoint]


class RouteLocation(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    date: dt.date
    type: Literal["gas", "maintenance"]
    detail: str | None = None


class RouteYear(BaseModel):
    year: str
    locations: list[RouteLocation]


class RouteData(BaseModel):
    total_stops: int
    years: list[RouteYear]
