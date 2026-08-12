from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import GasFillup, MaintenanceRecord
from app.schemas import DashboardSummary
from app.services import analytics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    fillups = db.execute(select(GasFillup)).scalars().all()
    records = db.execute(select(MaintenanceRecord)).scalars().all()
    return analytics.build_dashboard_summary(list(fillups), list(records))
