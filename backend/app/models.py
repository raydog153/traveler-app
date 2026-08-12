import datetime as dt

from sqlalchemy import CheckConstraint, Date, DateTime, Index, Numeric, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GasFillup(Base):
    __tablename__ = "gas_fillups"
    __table_args__ = (
        CheckConstraint("gallons > 0", name="ck_gas_fillups_gallons_positive"),
        CheckConstraint("price >= 0", name="ck_gas_fillups_price_nonnegative"),
        Index("idx_gas_fillups_date", "date"),
        Index("idx_gas_fillups_city_lower", text("lower(city)")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    odometer_miles: Mapped[float] = mapped_column(Numeric(10, 1), nullable=False)
    gallons: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    city: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"
    # No non-negative check on `cost`: the historical log includes at least one
    # legitimate refund/credit entry (a negative cost for an over-charge refund).
    __table_args__ = (Index("idx_maintenance_records_date", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    expense: Mapped[str] = mapped_column(Text, nullable=False)
    place: Mapped[str] = mapped_column(Text, nullable=False, default="")
    odometer_miles: Mapped[float | None] = mapped_column(Numeric(10, 1), nullable=True)
    vendor: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
