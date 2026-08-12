from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import MaintenanceRecord, split_city_state
from app.schemas import MaintenanceRecordIn, MaintenanceRecordOut
from app.services import analytics, geocoding

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


def _get_record_or_404(db: Session, record_id: int) -> MaintenanceRecord:
    record = db.get(MaintenanceRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    return record


@router.get("/records", response_model=list[MaintenanceRecordOut])
def list_records(db: Session = Depends(get_db)) -> list[MaintenanceRecordOut]:
    records = (
        db.execute(
            select(MaintenanceRecord)
            .options(joinedload(MaintenanceRecord.location))
            .order_by(MaintenanceRecord.date)
        )
        .scalars()
        .all()
    )
    return [analytics.to_maintenance_out(r) for r in records]


@router.post("/records", response_model=MaintenanceRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(payload: MaintenanceRecordIn, db: Session = Depends(get_db)) -> MaintenanceRecordOut:
    city, state = split_city_state(payload.place)
    location = geocoding.get_or_create_location(db, city, state)
    record = MaintenanceRecord(
        date=payload.date,
        expense=payload.expense,
        location=location,
        odometer_miles=payload.odometer_miles,
        vendor=payload.vendor,
        cost=payload.cost,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return analytics.to_maintenance_out(record)


@router.put("/records/{record_id}", response_model=MaintenanceRecordOut)
def update_record(record_id: int, payload: MaintenanceRecordIn, db: Session = Depends(get_db)) -> MaintenanceRecordOut:
    record = _get_record_or_404(db, record_id)
    city, state = split_city_state(payload.place)
    location = geocoding.get_or_create_location(db, city, state)
    record.date = payload.date
    record.expense = payload.expense
    record.location = location
    record.odometer_miles = payload.odometer_miles
    record.vendor = payload.vendor
    record.cost = payload.cost
    db.commit()
    db.refresh(record)
    return analytics.to_maintenance_out(record)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, db: Session = Depends(get_db)) -> None:
    record = _get_record_or_404(db, record_id)
    db.delete(record)
    db.commit()
