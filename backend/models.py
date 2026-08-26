from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base

class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float)
    humidity = Column(Float)
    soil_moisture = Column(Integer)
    rain_sensor = Column(Integer)
    potentiometer = Column(Integer)
    motion_detected = Column(Boolean)
    touch_detected = Column(Boolean)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
