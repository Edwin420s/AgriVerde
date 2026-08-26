from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import SoilSample
from app.schemas.schemas import SoilSampleCreate, SoilSampleResponse
from typing import List

router = APIRouter()

@router.post("/soil-samples", response_model=SoilSampleResponse)
def create_sample(sample: SoilSampleCreate, db: Session = Depends(get_db)):
    new_sample = SoilSample(**sample.dict())
    db.add(new_sample)
    db.commit()
    db.refresh(new_sample)
    return new_sample

@router.get("/soil-samples", response_model=List[SoilSampleResponse])
def list_samples(field_id: int, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(SoilSample).filter(SoilSample.field_id == field_id)\
             .order_by(SoilSample.timestamp.desc()).limit(limit).all()