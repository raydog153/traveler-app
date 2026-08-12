from fastapi import APIRouter, Depends, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import GasFillup, split_city_state
from app.schemas import GasFillupIn, GasFillupOut
from app.services import analytics, geocoding

router = APIRouter(prefix="/api/gas", tags=["gas"])


@router.get("/fillups", response_model=list[GasFillupOut])
def list_fillups(db: Session = Depends(get_db)) -> list[GasFillupOut]:
    fillups = db.execute(select(GasFillup).options(joinedload(GasFillup.location))).scalars().all()
    computed = analytics.compute_fillups(list(fillups))
    return [analytics.to_gas_out(c) for c in computed]


def _find_previous_fillup(db: Session, fillup: GasFillup) -> GasFillup | None:
    """The fill-up immediately before this one in (date, id) order -- the
    only row its own driven/mpg computation depends on."""
    return db.execute(
        select(GasFillup)
        .where(
            or_(
                GasFillup.date < fillup.date,
                and_(GasFillup.date == fillup.date, GasFillup.id < fillup.id),
            )
        )
        .order_by(GasFillup.date.desc(), GasFillup.id.desc())
        .limit(1)
    ).scalar_one_or_none()


@router.post("/fillups", response_model=GasFillupOut, status_code=status.HTTP_201_CREATED)
def create_fillup(payload: GasFillupIn, db: Session = Depends(get_db)) -> GasFillupOut:
    city, state = split_city_state(payload.city)
    location = geocoding.get_or_create_location(db, city, state)
    fillup = GasFillup(
        date=payload.date,
        odometer_miles=payload.odometer_miles,
        gallons=payload.gallons,
        price=payload.price,
        notes=payload.notes,
        location=location,
    )
    db.add(fillup)
    db.commit()
    db.refresh(fillup)

    # Only the immediately preceding fill-up affects this row's own
    # driven/mpg -- no need to refetch and recompute the whole table just to
    # return one row. (A backdated insert can still shift a *later* row's
    # driven/mpg, but GET /fillups already recomputes correctly for every
    # read, so no other row is left stale.)
    previous = _find_previous_fillup(db, fillup)
    prev_odometer = float(previous.odometer_miles) if previous else None
    computed = analytics.compute_from_previous(fillup, prev_odometer)
    return analytics.to_gas_out(computed)
