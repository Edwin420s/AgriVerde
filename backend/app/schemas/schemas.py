from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# Auth
class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: str
    password: str

# User
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    created_at: datetime

# Device
class DeviceCreate(BaseModel):
    device_id: str
    field_id: int
    firmware_version: Optional[str] = None

class DeviceResponse(BaseModel):
    id: int
    device_id: str
    field_id: int
    firmware_version: Optional[str]
    is_active: bool
    last_seen: Optional[datetime]
    registered_at: datetime

# Telemetry (ingestion)
class TelemetryData(BaseModel):
    device_id: str
    timestamp: Optional[datetime] = None
    temperature: float
    humidity: float
    soil_moisture: int
    target_moisture: Optional[int] = None
    rain_detected: bool
    motion_detected: bool
    pump_active: bool
    manual_override: bool
    sequence: Optional[int] = None
    soil_raw: Optional[int] = None
    rain_raw: Optional[int] = None

# Measurement (response)
class MeasurementResponse(BaseModel):
    id: int
    device_id: int
    timestamp: datetime
    temperature: float
    humidity: float
    soil_moisture: int
    target_moisture: int
    rain_detected: bool
    motion_detected: bool
    pump_active: bool
    manual_override: bool

# Irrigation Event
class IrrigationEventCreate(BaseModel):
    device_id: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    mode: str
    trigger: str
    soil_before: Optional[int]
    soil_after: Optional[int]
    rain_before: Optional[bool]
    fault_state: Optional[str]

class IrrigationEventResponse(BaseModel):
    id: int
    device_id: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    mode: str
    trigger: str
    soil_before: Optional[int]
    soil_after: Optional[int]
    rain_before: Optional[bool]
    fault_state: Optional[str]

# Soil Sample
class SoilSampleCreate(BaseModel):
    field_id: int
    latitude: float
    longitude: float
    depth_cm: float
    ph: float
    nitrogen: float
    phosphorus: float
    potassium: float
    organic_matter: float
    source: str

class SoilSampleResponse(BaseModel):
    id: int
    field_id: int
    timestamp: datetime
    latitude: float
    longitude: float
    depth_cm: float
    ph: float
    nitrogen: float
    phosphorus: float
    potassium: float
    organic_matter: float
    source: str
    operator_id: Optional[int]

# Blockchain Commitment
class DatasetCommit(BaseModel):
    dataset_id: str
    device_id: str
    field_id: int
    data_hash: str

class BlockchainRecordResponse(BaseModel):
    id: int
    dataset_id: str
    device_id: str
    field_id: int
    data_hash: str
    stellar_transaction: str
    soroban_contract: str
    timestamp: datetime
    verified: bool

    # Farm
class FarmBase(BaseModel):
    name: str
    location: Optional[str] = None

class FarmCreate(FarmBase):
    pass

class FarmUpdate(FarmBase):
    pass

class FarmResponse(FarmBase):
    id: int
    owner_id: int
    created_at: datetime

# Field
class FieldBase(BaseModel):
    name: str
    farm_id: int
    crop: Optional[str] = None
    area: Optional[float] = None
    soil_type: Optional[str] = None
    planting_date: Optional[datetime] = None

class FieldCreate(FieldBase):
    pass

class FieldUpdate(FieldBase):
    pass

class FieldResponse(FieldBase):
    id: int
    created_at: datetime

# Sensor
class SensorBase(BaseModel):
    device_id: int
    sensor_type: str  # soil, temperature, humidity, rain, pir
    calibration_id: Optional[int] = None

class SensorCreate(SensorBase):
    pass

class SensorUpdate(SensorBase):
    pass

class SensorResponse(SensorBase):
    id: int

# Command
class CommandBase(BaseModel):
    device_id: int
    command: str
    payload: Optional[dict] = None

class CommandCreate(CommandBase):
    pass

class CommandResponse(CommandBase):
    id: int
    requested_by: str
    timestamp: datetime
    executed: bool
    executed_at: Optional[datetime]

# Calibration
class CalibrationBase(BaseModel):
    device_id: int
    sensor_type: str
    calibration_version: str
    dry_reference: int
    wet_reference: int
    parameters: Optional[dict] = None

class CalibrationCreate(CalibrationBase):
    pass

class CalibrationResponse(CalibrationBase):
    id: int
    created_at: datetimes