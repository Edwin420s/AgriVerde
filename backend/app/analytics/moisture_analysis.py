from sqlalchemy.orm import Session
from app.models.models import Measurement
from datetime import datetime, timedelta

def calculate_drying_rate(device_id: int, hours: int, db: Session) -> float:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    measurements = db.query(Measurement).filter(
        Measurement.device_id == device_id,
        Measurement.timestamp >= cutoff
    ).order_by(Measurement.timestamp).all()
    if len(measurements) < 2:
        return 0.0
    first = measurements[0].soil_moisture
    last = measurements[-1].soil_moisture
    delta = first - last
    return delta / hours  # % per hour