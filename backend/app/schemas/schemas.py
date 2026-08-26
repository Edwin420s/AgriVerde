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