from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.models import Sensor, Device, Field, Farm, User
from app.schemas.schemas import SensorCreate, SensorResponse, SensorUpdate
from app.api.v1.auth import get_current_user

router = APIRouter()

@router.post("/sensors", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
def create_sensor(
    sensor: SensorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify device exists and belongs to current user via field->farm
    device = db.query(Device).join(Field).join(Farm).filter(
        Device.id == sensor.device_id,
        Farm.owner_id == current_user.id
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found or not owned")
    new_sensor = Sensor(**sensor.dict())
    db.add(new_sensor)
    db.commit()
    db.refresh(new_sensor)
    return new_sensor

@router.get("/sensors", response_model=List[SensorResponse])
def list_sensors(
    device_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Sensor).join(Device).join(Field).join(Farm).filter(Farm.owner_id == current_user.id)
    if device_id:
        query = query.filter(Sensor.device_id == device_id)
    return query.all()

@router.get("/sensors/{sensor_id}", response_model=SensorResponse)
def get_sensor(
    sensor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sensor = db.query(Sensor).join(Device).join(Field).join(Farm).filter(
        Sensor.id == sensor_id,
        Farm.owner_id == current_user.id
    ).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor

@router.put("/sensors/{sensor_id}", response_model=SensorResponse)
def update_sensor(
    sensor_id: int,
    sensor_update: SensorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sensor = db.query(Sensor).join(Device).join(Field).join(Farm).filter(
        Sensor.id == sensor_id,
        Farm.owner_id == current_user.id
    ).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    for key, value in sensor_update.dict(exclude_unset=True).items():
        setattr(sensor, key, value)
    db.commit()
    db.refresh(sensor)
    return sensor

@router.delete("/sensors/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sensor(
    sensor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sensor = db.query(Sensor).join(Device).join(Field).join(Farm).filter(
        Sensor.id == sensor_id,
        Farm.owner_id == current_user.id
    ).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    db.delete(sensor)
    db.commit()
    return None