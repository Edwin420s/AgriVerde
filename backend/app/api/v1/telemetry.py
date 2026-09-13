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
    
    # Update last_seen and firmware_version if provided
    device.last_seen = datetime.utcnow()
    if data.firmware_version:
        device.firmware_version = data.firmware_version
    device.status = "online"
    
    # Normalize sequence
    sequence = data.sequence if data.sequence is not None else data.seq

    # Check for duplicate sequence if sequence is provided (store-and-forward idempotency)
    if sequence is not None:
        existing = db.query(Measurement).filter(
            Measurement.device_id == device.id,
            Measurement.sequence == sequence
        ).first()
        if existing:
            return {"status": "duplicate_skipped", "measurement_id": existing.id}
    
    # Normalize values between standard and research field names
    temperature = data.temperature if data.temperature is not None else data.temperature_c
    humidity = data.humidity if data.humidity is not None else data.humidity_percent
    soil_moisture = data.soil_moisture if data.soil_moisture is not None else data.soil_moisture_percent
    target_moisture = data.target_moisture if data.target_moisture is not None else data.target_moisture_percent
    soil_raw = data.soil_raw if data.soil_raw is not None else (data.soil_adc if data.soil_adc is not None else data.raw_soil_adc)
    rain_raw = data.rain_raw if data.rain_raw is not None else (data.rain_adc if data.rain_adc is not None else data.raw_rain_adc)
    pump_active = data.pump_active or (data.pump_state is True) or (data.relay_state is True)
    manual_override = data.manual_override or (data.touch_override is True)

    if data.firmware_version:
        device.firmware_version = data.firmware_version
    if data.hardware_id:
        device.hardware_id = data.hardware_id

    # Create measurement record
    measurement = Measurement(
        device_id=device.id,
        timestamp=data.timestamp or datetime.utcnow(),
        temperature=temperature,
        humidity=humidity,
        soil_moisture=soil_moisture,
        target_moisture=target_moisture,
        rain_detected=data.rain_detected,
        motion_detected=data.motion_detected,
        pump_active=pump_active,
        manual_override=manual_override,
        sequence=sequence,
        soil_raw=soil_raw,
        rain_raw=rain_raw,
        soil_adc=data.soil_adc if data.soil_adc is not None else soil_raw,
        rain_adc=data.rain_adc if data.rain_adc is not None else rain_raw,
        temperature_c=data.temperature_c if data.temperature_c is not None else temperature,
        humidity_percent=data.humidity_percent if data.humidity_percent is not None else humidity,
        soil_moisture_percent=data.soil_moisture_percent if data.soil_moisture_percent is not None else soil_moisture,
        target_moisture_percent=data.target_moisture_percent if data.target_moisture_percent is not None else target_moisture,
    )
    db.add(measurement)
    
    # Check for anomalies and create alert if needed
    if temperature is not None and temperature > 40.0:
        alert = Alert(
            device_id=device.id,
            severity="WARNING",
            message=f"High temperature: {temperature}°C"
        )
        db.add(alert)
    
    db.commit()
    db.refresh(measurement)
    return {"status": "success", "measurement_id": measurement.id}

@router.get("/telemetry/latest")
def get_latest_telemetry(device_id: str = "AGR-NODE-001", db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    latest = db.query(Measurement).filter(Measurement.device_id == device.id).order_by(Measurement.timestamp.desc()).first()
    if not latest:
        return {
            "device_id": device_id,
            "status": device.status,
            "has_data": False,
            "soil_moisture": 40.0,
            "target_moisture": 60.0,
            "temperature": 24.0,
            "humidity": 55.0,
            "rain_detected": False,
            "pump_active": False,
            "motion_detected": False,
        }
    return {
        "device_id": device_id,
        "status": device.status,
        "has_data": True,
        "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
        "soil_moisture": latest.soil_moisture,
        "target_moisture": latest.target_moisture or 60.0,
        "temperature": latest.temperature,
        "humidity": latest.humidity,
        "rain_detected": latest.rain_detected,
        "pump_active": latest.pump_active,
        "motion_detected": latest.motion_detected,
        "manual_override": latest.manual_override,
        "soil_raw": latest.soil_raw,
        "rain_raw": latest.rain_raw,
        "sequence": latest.sequence,
    }