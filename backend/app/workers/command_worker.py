from app.workers.celery_app import celery_app
from app.database.database import SessionLocal
from app.models.models import Command, Device
from app.core.logging import logger
import requests
import json

@celery_app.task
def execute_command(command_id: int):
    db = SessionLocal()
    try:
        cmd = db.query(Command).filter(Command.id == command_id).first()
        if not cmd or cmd.executed:
            return
        # Get device
        device = db.query(Device).filter(Device.id == cmd.device_id).first()
        if not device:
            logger.error(f"Device {cmd.device_id} not found for command {command_id}")
            return
        
        # Here we would send the command to the device via MQTT or HTTP.
        # For demonstration, we simulate sending to an HTTP endpoint.
        # The device would have a local HTTP server or WebSocket.
        # We use the device's registered IP/URL if stored.
        # For simplicity, we just mark as executed.
        cmd.executed = True
        cmd.executed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Command {command_id} executed for device {device.device_id}")
    except Exception as e:
        logger.error(f"Failed to execute command {command_id}: {e}")
    finally:
        db.close()