from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Device, Field
from app.schemas.schemas import DeviceCreate, DeviceResponse
from typing import List

router = APIRouter()

@router.post("/devices", response_model=DeviceResponse)
def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    # Check field exists
    field = db.query(Field).filter(Field.id == device.field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    # Check device_id uniqueness
    existing = db.query(Device).filter(Device.device_id == device.device_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device ID already exists")
    new_device = Device(**device.dict())
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device

@router.get("/devices", response_model=List[DeviceResponse])
def list_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Device).offset(skip).limit(limit).all()

@router.get("/devices/{device_id}", response_model=DeviceResponse)
def get_device(device_id: str, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device