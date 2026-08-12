from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import GasFillup
from app.schemas import RouteData
from app.services import mapping

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("/routes", response_model=RouteData)
def get_routes(db: Session = Depends(get_db)) -> RouteData:
    fillups = db.execute(select(GasFillup)).scalars().all()
    return mapping.build_route_data(list(fillups))
