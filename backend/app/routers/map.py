from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import GasFillup, MaintenanceRecord, TravelData
from app.schemas import RouteData
from app.services import mapping

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("/routes", response_model=RouteData)
def get_routes(db: Session = Depends(get_db)) -> RouteData:
    fillups = db.execute(select(GasFillup).options(joinedload(GasFillup.location))).scalars().all()
    maintenance_records = (
        db.execute(select(MaintenanceRecord).options(joinedload(MaintenanceRecord.location))).scalars().all()
    )
    travel_data_rows = db.execute(select(TravelData)).scalars().all()
    return mapping.build_route_data(list(fillups), list(maintenance_records), list(travel_data_rows))
