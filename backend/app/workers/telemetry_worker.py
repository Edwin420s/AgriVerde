from app.workers.celery_app import celery_app
from app.database.database import SessionLocal
from app.models.models import Measurement, Alert
from app.core.logging import logger

@celery_app.task
def process_telemetry(measurement_id: int):
    # Perform post-processing, e.g., check thresholds, trigger alerts
    db = SessionLocal()
    try:
        measurement = db.query(Measurement).filter(Measurement.id == measurement_id).first()
        if not measurement:
            return
        
        alerts = []
        # Check simple thresholds
        if measurement.temperature > 35.0:
            alerts.append("High temperature detected.")
        if measurement.soil_moisture < 20 and not measurement.rain_detected:
            alerts.append("Critical low soil moisture without rain.")
            
        for msg in alerts:
            alert = Alert(
                device_id=measurement.device_id,
                severity="WARNING",
                message=msg,
                forecast_data={"measurement_id": measurement.id}
            )
            db.add(alert)
        
        if alerts:
            db.commit()
            logger.info(f"Generated {len(alerts)} alerts for measurement {measurement_id}")
            
    except Exception as e:
        logger.error(f"Error processing telemetry {measurement_id}: {e}")
    finally:
        db.close()