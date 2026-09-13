import pytest
from datetime import datetime, timedelta
from app.models.models import Device, Measurement, Field, Farm, User
from app.analytics.moisture_analysis import calculate_drying_rate
from app.analytics.irrigation_analysis import irrigation_efficiency
from app.analytics.analytics import environmental_correlation, detect_anomalies

def test_drying_rate_calculation(db_session):
    # Setup test device
    user = User(email="analytics_user@agriverde.io", hashed_password="pw", full_name="Analytics User")
    db_session.add(user)
    db_session.commit()

    farm = Farm(name="Analytics Farm", location="Farm Loc", owner_id=user.id)
    db_session.add(farm)
    db_session.commit()

    field = Field(name="Analytics Field", farm_id=farm.id)
    db_session.add(field)
    db_session.commit()

    device = Device(device_id="AGR-TEST-ANALYTICS", field_id=field.id, status="active")
    db_session.add(device)
    db_session.commit()

    # Add measurements over 10 hours: starting at 60%, dropping to 40%
    now = datetime.utcnow()
    m1 = Measurement(
        device_id=device.id,
        soil_moisture=60.0,
        temperature=25.0,
        humidity=50.0,
        timestamp=now - timedelta(hours=10)
    )
    m2 = Measurement(
        device_id=device.id,
        soil_moisture=40.0,
        temperature=28.0,
        humidity=45.0,
        timestamp=now
    )
    db_session.add_all([m1, m2])
    db_session.commit()

    rate = calculate_drying_rate(device.id, hours=12, db=db_session)
    # delta is 20% over 12 hours -> ~1.667% / hour
    assert rate > 0
    assert abs(rate - (20.0 / 12)) < 0.01

def test_irrigation_efficiency(db_session):
    eff = irrigation_efficiency(1, db_session)
    assert 0.0 <= eff <= 1.0

def test_environmental_correlation_insufficient_data(db_session):
    # With fewer than 10 measurements, correlation returns an error payload
    res = environmental_correlation(99999, hours=72, db=db_session)
    assert "error" in res
