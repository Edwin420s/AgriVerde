from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import IrrigationEvent
from app.schemas.schemas import IrrigationEventCreate, IrrigationEventResponse
from typing import List

router = APIRouter()

@router.post("/irrigation-events", response_model=IrrigationEventResponse)
def create_event(event: IrrigationEventCreate, db: Session = Depends(get_db)):
    new_event = IrrigationEvent(**event.dict())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

@router.get("/irrigation-events", response_model=List[IrrigationEventResponse])
def list_events(device_id: int, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(IrrigationEvent).filter(IrrigationEvent.device_id == device_id)\
             .order_by(IrrigationEvent.start_time.desc()).limit(limit).all()