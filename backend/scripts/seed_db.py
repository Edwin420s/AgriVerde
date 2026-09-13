import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database.database import SessionLocal, engine, Base
from app.models.models import User, Farm, Field, Device
from app.core.security import get_password_hash
from datetime import datetime

def seed():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == "admin@agriverde.io").first()
        if not user:
            user = User(
                email="admin@agriverde.io",
                hashed_password=get_password_hash("admin123456"),
                full_name="AgriVerde Admin",
                is_active=True,
                is_superuser=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created admin user: {user.email}")
        else:
            print(f"User already exists: {user.email}")

        # Check if farm exists
        farm = db.query(Farm).filter(Farm.name == "AgriVerde Demo Farm").first()
        if not farm:
            farm = Farm(
                name="AgriVerde Demo Farm",
                location="Tunis, Tunisia (36.8065° N, 10.1815° E)",
                owner_id=user.id
            )
            db.add(farm)
            db.commit()
            db.refresh(farm)
            print(f"Created demo farm: {farm.name}")
        else:
            print(f"Farm already exists: {farm.name}")

        # Check if field exists
        field = db.query(Field).filter(Field.name == "North Field (Tomatoes)").first()
        if not field:
            field = Field(
                name="North Field (Tomatoes)",
                farm_id=farm.id,
                crop="Tomato",
                crop_type="Solanaceae",
                variety="Roma",
                growth_stage="Vegetative",
                area=2.5,
                soil_type="Loam",
                planting_date=datetime.utcnow()
            )
            db.add(field)
            db.commit()
            db.refresh(field)
            print(f"Created field: {field.name}")
        else:
            print(f"Field already exists: {field.name}")

        # Check if device exists
        device = db.query(Device).filter(Device.device_id == "AGR-NODE-001").first()
        if not device:
            device = Device(
                device_id="AGR-NODE-001",
                hardware_id="ESP32-D0WD-V3",
                field_id=field.id,
                firmware_version="0.5.0",
                status="online",
                is_active=True,
                last_seen=datetime.utcnow()
            )
            db.add(device)
            db.commit()
            db.refresh(device)
            print(f"Created device: {device.device_id}")
        else:
            print(f"Device already exists: {device.device_id}")

        print("Database seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
