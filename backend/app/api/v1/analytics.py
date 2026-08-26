from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.analytics.moisture_analysis import calculate_drying_rate
from app.analytics.irrigation_analysis import irrigation_efficiency
from typing import Dict

router = APIRouter()

@router.get("/analytics/drying-rate")
def drying_rate(device_id: int, hours: int = 24, db: Session = Depends(get_db)):
    rate = calculate_drying_rate(device_id, hours, db)
    return {"drying_rate_per_hour": rate}

@router.get("/analytics/irrigation-efficiency")
def efficiency(device_id: int, db: Session = Depends(get_db)):
    eff = irrigation_efficiency(device_id, db)
    return {"efficiency": eff}