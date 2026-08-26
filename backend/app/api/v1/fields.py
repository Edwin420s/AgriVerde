from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.models import Field, Farm
from app.schemas.schemas import FieldCreate, FieldResponse, FieldUpdate
from app.api.v1.auth import get_current_user

router = APIRouter()

@router.post("/fields", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
def create_field(
    field: FieldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify farm belongs to current user
    farm = db.query(Farm).filter(Farm.id == field.farm_id, Farm.owner_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found or not owned by you")
    new_field = Field(**field.dict())
    db.add(new_field)
    db.commit()
    db.refresh(new_field)
    return new_field

@router.get("/fields", response_model=List[FieldResponse])
def list_fields(
    farm_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Field).join(Farm).filter(Farm.owner_id == current_user.id)
    if farm_id:
        query = query.filter(Field.farm_id == farm_id)
    return query.offset(skip).limit(limit).all()

@router.get("/fields/{field_id}", response_model=FieldResponse)
def get_field(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    field = db.query(Field).join(Farm).filter(
        Field.id == field_id,
        Farm.owner_id == current_user.id
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return field

@router.put("/fields/{field_id}", response_model=FieldResponse)
def update_field(
    field_id: int,
    field_update: FieldUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    field = db.query(Field).join(Farm).filter(
        Field.id == field_id,
        Farm.owner_id == current_user.id
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    for key, value in field_update.dict(exclude_unset=True).items():
        setattr(field, key, value)
    db.commit()
    db.refresh(field)
    return field

@router.delete("/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    field = db.query(Field).join(Farm).filter(
        Field.id == field_id,
        Farm.owner_id == current_user.id
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    db.delete(field)
    db.commit()
    return None