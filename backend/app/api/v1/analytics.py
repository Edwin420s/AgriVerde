from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.v1.auth import get_current_user
from app.models.models import User, Device
from app.analytics.analytics import (
    calculate_drying_rate,
    irrigation_efficiency,
    detect_anomalies,
    forecast_moisture,
    # --- New imports ---
    forecast_moisture_prophet,
    forecast_moisture_sarima,
    detect_anomalies_iforest,
    suggest_irrigation_schedule,
    environmental_correlation
)
from typing import Dict, Any, List

router = APIRouter()

# --- Existing endpoints (drying_rate, efficiency, anomalies, forecast) stay ---

@router.get("/analytics/forecast/prophet")
def prophet_forecast(
    device_id: int,
    days_ahead: int = Query(3, ge=1, le=7),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    result = forecast_moisture_prophet(device_id, days_ahead, db)
    return {"device_id": device_id, **result}


@router.get("/analytics/forecast/sarima")
def sarima_forecast(
    device_id: int,
    hours_ahead: int = Query(12, ge=1, le=48),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    result = forecast_moisture_sarima(device_id, hours_ahead, db)
    return {"device_id": device_id, **result}


@router.get("/analytics/anomalies/iforest")
def isolation_forest_anomalies(
    device_id: int,
    window_hours: int = Query(48, ge=6, le=168),
    contamination: float = Query(0.05, ge=0.01, le=0.2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    anomalies = detect_anomalies_iforest(device_id, window_hours, contamination, db)
    return {"device_id": device_id, "anomalies": anomalies}


@router.get("/analytics/schedule")
def irrigation_schedule(
    device_id: int,
    target_moisture: int = Query(30, ge=10, le=80),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    result = suggest_irrigation_schedule(device_id, target_moisture, db)
    return {"device_id": device_id, **result}


@router.get("/analytics/correlation")
def correlation(
    device_id: int,
    hours: int = Query(72, ge=12, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    result = environmental_correlation(device_id, hours, db)
    return {"device_id": device_id, **result}