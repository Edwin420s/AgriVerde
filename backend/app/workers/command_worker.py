from app.workers.celery_app import celery_app
from app.database.database import SessionLocal
from app.models.models import Command, Device
from app.core.logging import logger
from datetime import datetime
try:
    import httpx
    RequestException = (httpx.HTTPError, Exception)
    http_client = httpx
except ImportError:
    import requests
    RequestException = (requests.exceptions.RequestException, Exception)
    http_client = requests
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
        
        # Retrieve device IP (we'll use a mocked local IP or fallback for demonstration)
        # In a real system, the device's current IP might be stored in Redis or DB.
        device_ip = "192.168.1.100" 
        
        # Dispatch command to the edge node
        try:
            response = http_client.post(
                f"http://{device_ip}/command",
                json={"command": cmd.command, "payload": cmd.payload},
                timeout=5
            )
            response.raise_for_status()
        except RequestException as req_err:
            logger.warning(f"Failed to reach device {device.device_id} at {device_ip}: {req_err}")
            # Instead of failing, we can queue it for next check-in or mark as pending.
            # We'll let it stay un-executed so it retries or gets picked up.
            return
            
        cmd.executed = True
        cmd.executed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Command {command_id} executed for device {device.device_id}")
    except Exception as e:
        logger.error(f"Failed to execute command {command_id}: {e}")
    finally:
        db.close()