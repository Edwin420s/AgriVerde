from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import models
from database import engine, get_db
from pydantic import BaseModel

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AgriVerde API")

class TelemetryCreate(BaseModel):
    temperature: float
    humidity: float
    soil_moisture: int
    rain_sensor: int
    potentiometer: int
    motion_detected: bool
    touch_detected: bool

@app.post("/telemetry/")
def create_telemetry(telemetry: TelemetryCreate, db: Session = Depends(get_db)):
    db_telemetry = models.Telemetry(**telemetry.dict())
    db.add(db_telemetry)
    db.commit()
    db.refresh(db_telemetry)
    return db_telemetry

@app.get("/telemetry/")
def read_telemetry(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    telemetry_data = db.query(models.Telemetry).order_by(models.Telemetry.timestamp.desc()).offset(skip).limit(limit).all()
    return telemetry_data
