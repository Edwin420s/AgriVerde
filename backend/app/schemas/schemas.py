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
    model_config = {"extra": "allow"}
    device_id: str
    hardware_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    temperature: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity: Optional[float] = None
    humidity_percent: Optional[float] = None
    soil_moisture: Optional[float] = None
    soil_moisture_percent: Optional[float] = None
    target_moisture: Optional[float] = None
    target_moisture_percent: Optional[float] = None
    rain_detected: bool = False
    motion_detected: bool = False
    pump_active: bool = False
    pump_state: Optional[bool] = None
    relay_state: Optional[bool] = None
    manual_override: bool = False
    touch_override: Optional[bool] = None
    sequence: Optional[int] = None
    seq: Optional[int] = None
    soil_raw: Optional[int] = None
    soil_adc: Optional[int] = None
    raw_soil_adc: Optional[int] = None
    rain_raw: Optional[int] = None
    rain_adc: Optional[int] = None
    raw_rain_adc: Optional[int] = None
    rain_percentage: Optional[float] = None
    pir_raw: Optional[int] = None
    raw_touch_val: Optional[int] = None
    rssi: Optional[int] = None
    boot_count: Optional[int] = None
    uptime_sec: Optional[int] = None
    free_heap: Optional[int] = None
    firmware_version: Optional[str] = None

# Measurement (response)
class MeasurementResponse(BaseModel):
    id: int
    device_id: int
    timestamp: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    soil_moisture: Optional[float] = None
    target_moisture: Optional[float] = None
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

class CommandAckSchema(BaseModel):
    status: str
    received_at: Optional[datetime] = None

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
    created_at: datetime