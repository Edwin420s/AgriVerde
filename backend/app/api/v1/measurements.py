from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Measurement
from app.schemas.schemas import MeasurementResponse
from typing import List, Optional
from datetime import datetime

router = APIRouter()

@router.get("/measurements", response_model=List[MeasurementResponse])
def get_measurements(
    device_id: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Measurement)
    if device_id:
        query = query.filter(Measurement.device_id == device_id)
    if start:
        query = query.filter(Measurement.timestamp >= start)
    if end:
        query = query.filter(Measurement.timestamp <= end)
    return query.order_by(Measurement.timestamp.desc()).limit(limit).all()