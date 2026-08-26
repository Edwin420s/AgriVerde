from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database.session import get_db
from app.models.models import Command, Device
from app.schemas.schemas import CommandCreate, CommandResponse
from app.api.v1.auth import get_current_user
from app.models.models import User
from app.workers.command_worker import execute_command

router = APIRouter()

@router.post("/commands/{command_id}/ack")
def acknowledge_command(
    command_id: int,
    ack: CommandAckSchema,  # { status: str, received_at: datetime? }
    db: Session = Depends(get_db)
):
    cmd = db.query(Command).filter(Command.id == command_id).first()
    if not cmd:
        raise HTTPException(404, "Command not found")
    cmd.status = ack.status
    if ack.status == "received":
        cmd.received_at = datetime.utcnow()
    elif ack.status == "executed":
        cmd.executed_at = datetime.utcnow()
    db.commit()
    return {"status": "acknowledged"}
@router.post("/commands", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
def create_command(
    cmd: CommandCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify device belongs to user
    device = db.query(Device).join(Field).join(Farm).filter(
        Device.id == cmd.device_id,
        Farm.owner_id == current_user.id
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found or not owned")
    new_cmd = Command(
        device_id=cmd.device_id,
        command=cmd.command,
        payload=cmd.payload,
        requested_by=f"user_{current_user.id}"
    )
    db.add(new_cmd)
    db.commit()
    db.refresh(new_cmd)
    # Trigger async execution (via Celery)
    execute_command.delay(new_cmd.id)
    return new_cmd

@router.get("/commands", response_model=List[CommandResponse])
def list_commands(
    device_id: int = None,
    executed: bool = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Command).join(Device).join(Field).join(Farm).filter(Farm.owner_id == current_user.id)
    if device_id:
        query = query.filter(Command.device_id == device_id)
    if executed is not None:
        query = query.filter(Command.executed == executed)
    return query.order_by(Command.timestamp.desc()).limit(limit).all()

@router.get("/commands/{command_id}", response_model=CommandResponse)
def get_command(
    command_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cmd = db.query(Command).join(Device).join(Field).join(Farm).filter(
        Command.id == command_id,
        Farm.owner_id == current_user.id
    ).first()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    return cmd