import datetime as dt
import enum
import re

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

_LOCATION_ID_STRIP_RE = re.compile(r"[^a-z0-9\s]")


def location_id(city: str, state: str) -> str:
    """Natural primary key for Location: lowercase "city state", punctuation
    stripped, whitespace collapsed to single underscores -- e.g.
    ("D'Iberville", "MS") -> "diberville_ms"."""
    text_ = _LOCATION_ID_STRIP_RE.sub("", f"{city} {state}".lower())
    return "_".join(text_.split())


def split_city_state(raw: str) -> tuple[str, str]:
    """Splits a free-text "City, State" string (as typed into the fill-up
    form, or as stored in gas_raw.json) on its first comma."""
    city, _, state = raw.partition(",")
    return city.strip(), state.strip()


class GasFillup(Base):
    __tablename__ = "gas_fillups"
    __table_args__ = (
        CheckConstraint("gallons > 0", name="ck_gas_fillups_gallons_positive"),
        CheckConstraint("price >= 0", name="ck_gas_fillups_price_nonnegative"),
        UniqueConstraint("odometer_miles", name="uq_gas_fillups_odometer_miles"),
        Index("idx_gas_fillups_date", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    odometer_miles: Mapped[float] = mapped_column(Numeric(10, 1), nullable=False)
    gallons: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    location_id: Mapped[str] = mapped_column(Text, ForeignKey("locations.id"), nullable=False)
    # Exact GPS coordinates from the fill-up photo's EXIF data, when a photo
    # was used to create this row -- an optional per-fillup override of the
    # coarser location.lat/long, resolved at read time (analytics.to_gas_out,
    # mapping.build_route_data) rather than copied/denormalized. Named
    # gps_latitude/gps_longitude, not latitude/longitude, because this table
    # already had (and dropped, in b624a2cb494e) columns by that name that
    # were always a stale copy of the location's coordinates -- these are a
    # genuinely independent value instead.
    gps_latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    gps_longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    location: Mapped["Location"] = relationship()


class Location(Base):
    __tablename__ = "locations"

    # location_id(city, state) -- callers are responsible for setting this
    # explicitly on insert (it's derived, not DB- or ORM-generated), and for
    # recomputing it if a row's city/state is ever corrected after the fact.
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    long: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"
    # No non-negative check on `cost`: the historical log includes at least one
    # legitimate refund/credit entry (a negative cost for an over-charge refund).
    __table_args__ = (Index("idx_maintenance_records_date", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    expense: Mapped[str] = mapped_column(Text, nullable=False)
    location_id: Mapped[str] = mapped_column(Text, ForeignKey("locations.id"), nullable=False)
    odometer_miles: Mapped[float | None] = mapped_column(Numeric(10, 1), nullable=True)
    vendor: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    location: Mapped["Location"] = relationship()


class TravelEntryType(enum.StrEnum):
    """gas_fillup and maintenance_event are defined for a future migration of
    GasFillup/MaintenanceRecord into this table -- not populated yet."""

    GAS_FILLUP = "gas_fillup"
    GROCERY_PICKUP = "grocery_pickup"
    OVERNIGHT_STAY = "overnight_stay"
    MAINTENANCE_EVENT = "maintenance_event"


class TravelData(Base):
    """A general-purpose, dated + located event log -- unlike GasFillup and
    MaintenanceRecord, not FK'd to the deduped `locations` table: each row
    is a one-off visit (e.g. a single grocery pickup), not a place that's
    revisited and worth deduping, so address and lat/long are stored
    directly on the row."""

    __tablename__ = "travel_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    time: Mapped[dt.time | None] = mapped_column(Time, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    entry_type: Mapped[TravelEntryType] = mapped_column(
        Enum(TravelEntryType, name="travel_entry_type", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    # Misc per-entry-type data, e.g. {"store_name": ..., "store_number": ...}
    # for a grocery_pickup -- deliberately unstructured since each entry_type
    # has its own shape.
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # True when geocoding the address failed (or the location was hand-
    # corrected afterward) -- latitude/longitude are a best guess, not
    # confirmed against the address.
    is_estimated_location: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
