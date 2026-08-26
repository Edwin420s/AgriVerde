from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    farms = relationship("Farm", back_populates="owner")

class Farm(Base):
    __tablename__ = "farms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    location = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="farms")
    fields = relationship("Field", back_populates="farm")

class Field(Base):
    __tablename__ = "fields"
    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"))
    name = Column(String, nullable=False)
    crop = Column(String)
    area = Column(Float)
    soil_type = Column(String)
    planting_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    farm = relationship("Farm", back_populates="fields")
    devices = relationship("Device", back_populates="field")
    soil_samples = relationship("SoilSample", back_populates="field")

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"))
    device_type = Column(String, default="ESP32")
    firmware_version = Column(String)
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime)
    field = relationship("Field", back_populates="devices")
    measurements = relationship("Measurement", back_populates="device")
    irrigation_events = relationship("IrrigationEvent", back_populates="device")
    calibrations = relationship("Calibration", back_populates="device")

class Sensor(Base):
    __tablename__ = "sensors"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    sensor_type = Column(String)  # soil, temperature, humidity, rain, pir
    calibration_id = Column(Integer, ForeignKey("calibrations.id"))

class Measurement(Base):
    __tablename__ = "measurements"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    temperature = Column(Float)
    humidity = Column(Float)
    soil_moisture = Column(Integer)  # percent
    target_moisture = Column(Integer)
    rain_detected = Column(Boolean)
    motion_detected = Column(Boolean)
    pump_active = Column(Boolean)
    manual_override = Column(Boolean)
    sequence = Column(Integer)
    raw_soil = Column(Integer)       # raw ADC value
    raw_rain = Column(Integer)
    device = relationship("Device", back_populates="measurements")

class IrrigationEvent(Base):
    __tablename__ = "irrigation_events"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    mode = Column(String)  # AUTO, MANUAL, REMOTE
    trigger = Column(String)  # LOW_SOIL, RAIN_STOP, etc.
    soil_before = Column(Integer)
    soil_after = Column(Integer)
    rain_before = Column(Boolean)
    fault_state = Column(String)
    device = relationship("Device", back_populates="irrigation_events")

class SoilSample(Base):
    __tablename__ = "soil_samples"
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    latitude = Column(Float)
    longitude = Column(Float)
    depth_cm = Column(Float)
    ph = Column(Float)
    nitrogen = Column(Float)
    phosphorus = Column(Float)
    potassium = Column(Float)
    organic_matter = Column(Float)
    source = Column(String)  # Scanner, Lab, Manual
    operator_id = Column(Integer, ForeignKey("users.id"))
    field = relationship("Field", back_populates="soil_samples")

class Calibration(Base):
    __tablename__ = "calibrations"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    sensor_type = Column(String)
    calibration_version = Column(String)
    dry_reference = Column(Integer)
    wet_reference = Column(Integer)
    parameters = Column(JSON)  # store extra calibration data
    created_at = Column(DateTime, default=datetime.utcnow)
    device = relationship("Device", back_populates="calibrations")

class Command(Base):
    __tablename__ = "commands"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    command = Column(String)  # PUMP_ON, PUMP_OFF, SET_THRESHOLD
    payload = Column(JSON)
    requested_by = Column(String)  # user_id or system
    timestamp = Column(DateTime, default=datetime.utcnow)
    executed = Column(Boolean, default=False)
    executed_at = Column(DateTime)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    severity = Column(String)  # INFO, WARNING, CRITICAL
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)

class BlockchainRecord(Base):
    __tablename__ = "blockchain_records"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(String, unique=True)
    device_id = Column(String)
    field_id = Column(Integer)
    data_hash = Column(String)
    stellar_transaction = Column(String)
    soroban_contract = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)