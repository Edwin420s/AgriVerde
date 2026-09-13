from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.models import Calibration, Device, Field, Farm, User
from app.schemas.schemas import CalibrationCreate, CalibrationResponse
from app.api.v1.auth import get_current_user

router = APIRouter()

@router.post("/calibrations", response_model=CalibrationResponse, status_code=status.HTTP_201_CREATED)
def create_calibration(
    cal: CalibrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify device ownership
    device = db.query(Device).join(Field).join(Farm).filter(
        Device.id == cal.device_id,
        Farm.owner_id == current_user.id
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found or not owned")
    new_cal = Calibration(**cal.dict())
    db.add(new_cal)
    db.commit()
    db.refresh(new_cal)
    return new_cal

@router.get("/calibrations", response_model=List[CalibrationResponse])
def list_calibrations(
    device_id: int = None,
    sensor_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Calibration).join(Device).join(Field).join(Farm).filter(Farm.owner_id == current_user.id)
    if device_id:
        query = query.filter(Calibration.device_id == device_id)
    if sensor_type:
        query = query.filter(Calibration.sensor_type == sensor_type)
    return query.all()

@router.get("/calibrations/{calibration_id}", response_model=CalibrationResponse)
def get_calibration(
    calibration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cal = db.query(Calibration).join(Device).join(Field).join(Farm).filter(
        Calibration.id == calibration_id,
        Farm.owner_id == current_user.id
    ).first()
    if not cal:
        raise HTTPException(status_code=404, detail="Calibration record not found")
    return cal