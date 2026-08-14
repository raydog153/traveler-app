from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import GasFillup, split_city_state
from app.schemas import GasFillupIn, GasFillupOut, OdometerScanResult
from app.services import analytics, exif_extract, geocoding, vision

router = APIRouter(prefix="/api/gas", tags=["gas"])


def _get_fillup_or_404(db: Session, fillup_id: int) -> GasFillup:
    fillup = db.get(GasFillup, fillup_id)
    if fillup is None:
        raise HTTPException(status_code=404, detail="Fill-up not found")
    return fillup


@router.get("/fillups", response_model=list[GasFillupOut])
def list_fillups(db: Session = Depends(get_db)) -> list[GasFillupOut]:
    fillups = db.execute(select(GasFillup).options(joinedload(GasFillup.location))).scalars().all()
    computed = analytics.compute_fillups(list(fillups))
    return [analytics.to_gas_out(c) for c in computed]


@router.post("/fillups/scan-odometer", response_model=OdometerScanResult)
async def scan_odometer(photo: UploadFile = File(...)) -> OdometerScanResult:
    """Best-effort extraction from an odometer photo, for prefilling the
    add-fillup form -- odometer reading via Gemini vision, GPS/date via EXIF,
    city/state via reverse-geocoding the GPS. Pure inference: no DB session,
    no Location/GasFillup row created, since the user may edit or cancel
    before actually saving. The photo bytes are read into memory and never
    stored."""
    image_bytes = await photo.read()

    odometer_miles, warnings = vision.scan_odometer_photo(image_bytes)

    date_, latitude, longitude = None, None, None
    try:
        image = Image.open(BytesIO(image_bytes))
        gps = exif_extract.extract_gps(image)
        date_ = exif_extract.extract_capture_date(image)
        if gps is not None:
            latitude, longitude = gps
    except Exception:
        pass  # not a decodable image -- odometer_miles from Gemini may still be usable

    if latitude is None:
        warnings.append("No location found in photo")
    if date_ is None:
        warnings.append("No date found in photo")

    city, state = None, None
    if latitude is not None:
        reverse = geocoding.reverse_geocode_via_nominatim(latitude, longitude)
        if reverse is not None:
            city, state = reverse

    return OdometerScanResult(
        odometer_miles=odometer_miles,
        date=date_,
        latitude=latitude,
        longitude=longitude,
        city=city,
        state=state,
        warnings=warnings,
    )


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
        gps_latitude=payload.gps_latitude,
        gps_longitude=payload.gps_longitude,
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


@router.put("/fillups/{fillup_id}", response_model=GasFillupOut)
def update_fillup(fillup_id: int, payload: GasFillupIn, db: Session = Depends(get_db)) -> GasFillupOut:
    fillup = _get_fillup_or_404(db, fillup_id)
    city, state = split_city_state(payload.city)
    location = geocoding.get_or_create_location(db, city, state)
    fillup.date = payload.date
    fillup.odometer_miles = payload.odometer_miles
    fillup.gallons = payload.gallons
    fillup.price = payload.price
    fillup.notes = payload.notes
    fillup.location = location
    fillup.gps_latitude = payload.gps_latitude
    fillup.gps_longitude = payload.gps_longitude
    db.commit()
    db.refresh(fillup)

    # Same reasoning as create: only the immediately preceding fill-up is
    # needed to compute *this* row's driven/mpg for the response. A later
    # row's derived values may now be stale, but GET /fillups recomputes
    # every row from scratch on every read, so nothing is left inconsistent.
    previous = _find_previous_fillup(db, fillup)
    prev_odometer = float(previous.odometer_miles) if previous else None
    computed = analytics.compute_from_previous(fillup, prev_odometer)
    return analytics.to_gas_out(computed)


@router.delete("/fillups/{fillup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fillup(fillup_id: int, db: Session = Depends(get_db)) -> None:
    fillup = _get_fillup_or_404(db, fillup_id)
    db.delete(fillup)
    db.commit()
