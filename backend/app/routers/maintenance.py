from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MaintenanceRecord
from app.schemas import MaintenanceRecordIn, MaintenanceRecordOut
from app.services import analytics

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


@router.get("/records", response_model=list[MaintenanceRecordOut])
def list_records(db: Session = Depends(get_db)) -> list[MaintenanceRecordOut]:
    records = db.execute(select(MaintenanceRecord).order_by(MaintenanceRecord.date)).scalars().all()
    return [analytics.to_maintenance_out(r) for r in records]


@router.post("/records", response_model=MaintenanceRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(payload: MaintenanceRecordIn, db: Session = Depends(get_db)) -> MaintenanceRecordOut:
    record = MaintenanceRecord(
        date=payload.date,
        expense=payload.expense,
        place=payload.place,
        odometer_miles=payload.odometer_miles,
        vendor=payload.vendor,
        cost=payload.cost,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return analytics.to_maintenance_out(record)
