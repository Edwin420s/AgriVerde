from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.session import get_db
from app.models.models import Device, Measurement, Alert
from app.schemas.schemas import TelemetryData
from app.core.logging import logger

router = APIRouter()

@router.post("/telemetry")
def ingest_telemetry(data: TelemetryData, db: Session = Depends(get_db)):
    # Find device
    device = db.query(Device).filter(Device.device_id == data.device_id).first()
    if not device:
        # Optionally auto-register or raise
        raise HTTPException(status_code=404, detail="Device not registered")
    
    # Update last_seen
    device.last_seen = datetime.utcnow()
    
    # Create measurement record
    measurement = Measurement(
        device_id=device.id,
        timestamp=data.timestamp or datetime.utcnow(),
        temperature=data.temperature,
        humidity=data.humidity,
        soil_moisture=data.soil_moisture,
        target_moisture=data.target_moisture,
        rain_detected=data.rain_detected,
        motion_detected=data.motion_detected,
        pump_active=data.pump_active,
        manual_override=data.manual_override,
        sequence=data.sequence,
        raw_soil=data.soil_raw,
        raw_rain=data.rain_raw
    )
    db.add(measurement)
    
    # Check for anomalies and create alert if needed
    if data.temperature > 40.0:
        alert = Alert(
            device_id=device.id,
            severity="WARNING",
            message=f"High temperature: {data.temperature}°C"
        )
        db.add(alert)
    
    db.commit()
    return {"status": "success", "measurement_id": measurement.id}