import pytest
from datetime import datetime
from app.models.models import User, Farm, Field, Device, Measurement, Alert, Command

@pytest.fixture(autouse=True)
def setup_device(db_session):
    # Ensure test user, farm, field, and device exist in the test session
    user = User(
        email="tester@agriverde.io",
        hashed_password="hashed_pw_dummy",
        full_name="Test User"
    )
    db_session.add(user)
    db_session.flush()

    farm = Farm(name="Test Farm", owner_id=user.id)
    db_session.add(farm)
    db_session.flush()

    field = Field(
        name="Test Field",
        farm_id=farm.id,
        crop="Tomato",
        crop_type="Solanaceae",
        variety="Roma",
        growth_stage="Vegetative"
    )
    db_session.add(field)
    db_session.flush()

    device = Device(
        device_id="AGR-NODE-001",
        hardware_id="ESP32-D0WD-V3",
        field_id=field.id,
        firmware_version="0.5.0",
        status="online"
    )
    db_session.add(device)
    db_session.commit()

def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "ok"]
    assert data.get("components", {}).get("database") == "ok"

def test_telemetry_ingestion_standard_payload(client, db_session):
    payload = {
        "device_id": "AGR-NODE-001",
        "temperature": 24.5,
        "humidity": 65.0,
        "soil_moisture": 55,
        "target_moisture": 60,
        "rain_detected": False,
        "motion_detected": False,
        "pump_active": False,
        "manual_override": False,
        "sequence": 1,
        "soil_raw": 2200,
        "rain_raw": 1850,
        "firmware_version": "0.5.0"
    }
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "measurement_id" in data

    # Verify in db
    m = db_session.query(Measurement).filter(Measurement.id == data["measurement_id"]).first()
    assert m is not None
    assert m.temperature == 24.5
    assert m.humidity == 65.0
    assert m.soil_moisture == 55
    assert m.sequence == 1

def test_telemetry_ingestion_firmware_research_keys(client, db_session):
    # Tests the exact JSON format produced by ESP32 firmware v0.5.0
    payload = {
        "device_id": "AGR-NODE-001",
        "firmware_version": "0.5.0",
        "sequence": 2,
        "temperature_c": 26.2,
        "humidity_percent": 58.4,
        "soil_moisture_percent": 48,
        "target_moisture_percent": 60,
        "soil_adc": 2350,
        "rain_adc": 1800,
        "rain_detected": False,
        "motion_detected": False,
        "pump_active": True,
        "manual_override": False
    }
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    m = db_session.query(Measurement).filter(Measurement.id == data["measurement_id"]).first()
    assert m is not None
    assert m.temperature == 26.2
    assert m.humidity == 58.4
    assert m.soil_moisture == 48
    assert m.soil_adc == 2350
    assert m.pump_active is True

def test_telemetry_store_and_forward_idempotency(client):
    payload = {
        "device_id": "AGR-NODE-001",
        "sequence": 100,
        "temperature": 22.0,
        "humidity": 50.0,
        "soil_moisture": 40
    }
    # First send
    r1 = client.post("/api/v1/telemetry", json=payload)
    assert r1.status_code == 200
    assert r1.json()["status"] == "success"
    m_id = r1.json()["measurement_id"]

    # Replay buffered duplicate with same sequence
    r2 = client.post("/api/v1/telemetry", json=payload)
    assert r2.status_code == 200
    assert r2.json()["status"] == "duplicate_skipped"
    assert r2.json()["measurement_id"] == m_id

def test_telemetry_high_temperature_alert(client, db_session):
    payload = {
        "device_id": "AGR-NODE-001",
        "sequence": 200,
        "temperature": 42.5,
        "humidity": 20.0,
        "soil_moisture": 15
    }
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200

    alert = db_session.query(Alert).filter(Alert.severity == "WARNING").first()
    assert alert is not None
    assert "High temperature" in alert.message

def test_telemetry_unregistered_device(client):
    payload = {
        "device_id": "UNKNOWN-NODE-999",
        "temperature": 25.0
    }
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 404
