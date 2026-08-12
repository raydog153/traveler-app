from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import GasFillup
from app.schemas import GasFillupIn, GasFillupOut
from app.services import analytics, geocoding

router = APIRouter(prefix="/api/gas", tags=["gas"])


@router.get("/fillups", response_model=list[GasFillupOut])
def list_fillups(db: Session = Depends(get_db)) -> list[GasFillupOut]:
    fillups = db.execute(select(GasFillup)).scalars().all()
    computed = analytics.compute_fillups(list(fillups))
    return [analytics.to_gas_out(c) for c in computed]


@router.post("/fillups", response_model=GasFillupOut, status_code=status.HTTP_201_CREATED)
def create_fillup(payload: GasFillupIn, db: Session = Depends(get_db)) -> GasFillupOut:
    latitude, longitude = geocoding.get_or_geocode(db, payload.city)
    fillup = GasFillup(
        date=payload.date,
        odometer_miles=payload.odometer_miles,
        gallons=payload.gallons,
        price=payload.price,
        notes=payload.notes,
        city=payload.city,
        latitude=latitude,
        longitude=longitude,
    )
    db.add(fillup)
    db.commit()
    db.refresh(fillup)

    # Recompute against the full set so driven/mpg reflect the correct
    # neighboring odometer readings regardless of where this entry sorts in.
    all_fillups = db.execute(select(GasFillup)).scalars().all()
    computed = analytics.compute_fillups(list(all_fillups))
    match = next(c for c in computed if c.fillup.id == fillup.id)
    return analytics.to_gas_out(match)
