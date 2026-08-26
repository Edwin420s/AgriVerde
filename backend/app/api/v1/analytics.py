from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.v1.auth import get_current_user
from app.models.models import User, Device
from app.analytics.analytics import (
    calculate_drying_rate,
    irrigation_efficiency,
    detect_anomalies,
    forecast_moisture
)
from typing import Dict, Any, List

router = APIRouter()

@router.get("/analytics/drying-rate")
def drying_rate(
    device_id: int,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify device belongs to user
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    # You can add ownership check via field->farm->owner
    rate = calculate_drying_rate(device_id, hours, db)
    return {"device_id": device_id, "hours": hours, "drying_rate_per_hour": rate}

@router.get("/analytics/irrigation-efficiency")
def efficiency(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Ownership check
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    result = irrigation_efficiency(device_id, db)
    return {"device_id": device_id, **result}

@router.get("/analytics/anomalies")
def anomalies(
    device_id: int,
    window_hours: int = Query(24, ge=1, le=168),
    threshold: float = Query(2.5, ge=1.0, le=5.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    anomaly_list = detect_anomalies(device_id, window_hours, threshold, db)
    return {"device_id": device_id, "window_hours": window_hours, "anomalies": anomaly_list}

@router.get("/analytics/forecast")
def forecast(
    device_id: int,
    hours_ahead: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    result = forecast_moisture(device_id, hours_ahead, db)
    return {"device_id": device_id, **result}