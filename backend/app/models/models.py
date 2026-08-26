from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    farms = relationship("Farm", back_populates="owner")

class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="farms")
    fields = relationship("Field", back_populates="farm")

class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    farm_id = Column(Integer, ForeignKey("farms.id"))
    crop = Column(String)
    area = Column(Float)
    soil_type = Column(String)
    planting_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    farm = relationship("Farm", back_populates="fields")
    devices = relationship("Device", back_populates="field")

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"))
    firmware_version = Column(String)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))
    registered_at = Column(DateTime(timezone=True), server_default=func.now())

    field = relationship("Field", back_populates="devices")
    measurements = relationship("Measurement", back_populates="device")
    commands = relationship("Command", back_populates="device")
    irrigation_events = relationship("IrrigationEvent", back_populates="device")
    alerts = relationship("Alert", back_populates="device")
    sensors = relationship("Sensor", back_populates="device")

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    sensor_type = Column(String)
    calibration_id = Column(Integer, ForeignKey("calibrations.id"))

    device = relationship("Device", back_populates="sensors")

class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    temperature = Column(Float)
    humidity = Column(Float)
    soil_moisture = Column(Integer)
    target_moisture = Column(Integer)
    rain_detected = Column(Boolean, default=False)
    motion_detected = Column(Boolean, default=False)
    pump_active = Column(Boolean, default=False)
    manual_override = Column(Boolean, default=False)
    sequence = Column(Integer)
    soil_raw = Column(Integer)
    rain_raw = Column(Integer)

    device = relationship("Device", back_populates="measurements")

class IrrigationEvent(Base):
    __tablename__ = "irrigation_events"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    mode = Column(String)
    trigger = Column(String)
    soil_before = Column(Integer)
    soil_after = Column(Integer)
    rain_before = Column(Boolean)
    fault_state = Column(String)

    device = relationship("Device", back_populates="irrigation_events")

class Command(Base):
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    requested_by = Column(String)
    command = Column(String, nullable=False)
    payload = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    executed = Column(Boolean, default=False)
    executed_at = Column(DateTime(timezone=True))

    device = relationship("Device", back_populates="commands")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    severity = Column(String)
    message = Column(String)
    forecast_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="alerts")

class BlockchainRecord(Base):
    __tablename__ = "blockchain_records"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(String, index=True)
    device_id = Column(String)
    field_id = Column(Integer)
    data_hash = Column(String)
    stellar_transaction = Column(String)
    soroban_contract = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    verified = Column(Boolean, default=False)

class Calibration(Base):
    __tablename__ = "calibrations"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    sensor_type = Column(String)
    calibration_version = Column(String)
    dry_reference = Column(Integer)
    wet_reference = Column(Integer)
    parameters = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SoilSample(Base):
    __tablename__ = "soil_samples"
    
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    latitude = Column(Float)
    longitude = Column(Float)
    depth_cm = Column(Float)
    ph = Column(Float)
    nitrogen = Column(Float)
    phosphorus = Column(Float)
    potassium = Column(Float)
    organic_matter = Column(Float)
    source = Column(String)
    operator_id = Column(Integer)
