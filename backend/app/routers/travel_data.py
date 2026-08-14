from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import TravelData
from app.schemas import TravelDataOut

router = APIRouter(prefix="/api/travel-data", tags=["travel-data"])


@router.get("", response_model=list[TravelDataOut])
def list_travel_data(db: Session = Depends(get_db)) -> list[TravelData]:
    return list(db.execute(select(TravelData).order_by(TravelData.date)).scalars().all())
