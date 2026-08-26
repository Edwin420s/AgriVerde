import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.models import Measurement, IrrigationEvent
from typing import List, Dict, Any
from app.core.logging import logger

def get_measurements_df(device_id: int, hours: int, db: Session) -> pd.DataFrame:
    """Fetch measurements for a device within the last N hours and return as DataFrame."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(Measurement).filter(
        Measurement.device_id == device_id,
        Measurement.timestamp >= cutoff
    ).order_by(Measurement.timestamp)
    data = [(m.timestamp, m.soil_moisture, m.temperature, m.humidity) for m in query]
    if not data:
        return pd.DataFrame(columns=['timestamp', 'soil_moisture', 'temperature', 'humidity'])
    df = pd.DataFrame(data, columns=['timestamp', 'soil_moisture', 'temperature', 'humidity'])
    df = df.set_index('timestamp')
    return df

def calculate_drying_rate(device_id: int, hours: int, db: Session) -> float:
    """
    Compute the drying rate (% per hour) using linear regression on soil moisture over time.
    Returns negative slope if moisture is decreasing.
    """
    df = get_measurements_df(device_id, hours, db)
    if len(df) < 2:
        return 0.0
    # Convert index to numeric (seconds since epoch)
    X = df.index.astype(np.int64).values.reshape(-1, 1)
    y = df['soil_moisture'].values.reshape(-1, 1)
    model = LinearRegression()
    model.fit(X, y)
    slope = model.coef_[0][0]
    # slope is per nanosecond, convert to per hour
    slope_per_hour = slope * 3600 * 1e9  # nanoseconds to hours
    return round(slope_per_hour, 2)

def irrigation_efficiency(device_id: int, db: Session) -> Dict[str, Any]:
    """
    Compute irrigation efficiency: average moisture increase per minute of irrigation.
    Analyzes the last 10 irrigation events.
    """
    events = db.query(IrrigationEvent).filter(
        IrrigationEvent.device_id == device_id,
        IrrigationEvent.end_time.isnot(None),
        IrrigationEvent.duration_seconds > 0
    ).order_by(IrrigationEvent.start_time.desc()).limit(10).all()
    
    if not events:
        return {"efficiency": 0.0, "events_analyzed": 0}
    
    total_gain = 0.0
    total_duration = 0.0
    for event in events:
        # Get moisture before and after
        before_measurement = db.query(Measurement).filter(
            Measurement.device_id == device_id,
            Measurement.timestamp < event.start_time
        ).order_by(Measurement.timestamp.desc()).first()
        after_measurement = db.query(Measurement).filter(
            Measurement.device_id == device_id,
            Measurement.timestamp > event.end_time
        ).order_by(Measurement.timestamp).first()
        if before_measurement and after_measurement:
            gain = after_measurement.soil_moisture - before_measurement.soil_moisture
            duration_minutes = event.duration_seconds / 60.0
            if duration_minutes > 0:
                total_gain += gain
                total_duration += duration_minutes
    
    if total_duration == 0:
        return {"efficiency": 0.0, "events_analyzed": len(events)}
    
    avg_efficiency = total_gain / total_duration  # % per minute
    return {
        "efficiency": round(avg_efficiency, 2),
        "events_analyzed": len(events),
        "total_gain": round(total_gain, 2),
        "total_duration_minutes": round(total_duration, 2)
    }

def detect_anomalies(device_id: int, window_hours: int = 24, threshold: float = 2.5, db: Session) -> List[Dict]:
    """
    Detect anomalies in soil moisture using Z-score.
    Returns list of anomalous measurements with timestamps and deviations.
    """
    df = get_measurements_df(device_id, window_hours, db)
    if len(df) < 5:
        return []
    
    mean = df['soil_moisture'].mean()
    std = df['soil_moisture'].std()
    if std == 0:
        return []
    
    df['zscore'] = (df['soil_moisture'] - mean) / std
    anomalies = df[abs(df['zscore']) > threshold]
    
    result = []
    for idx, row in anomalies.iterrows():
        result.append({
            "timestamp": idx.isoformat(),
            "soil_moisture": float(row['soil_moisture']),
            "zscore": float(row['zscore']),
            "deviation": float(row['soil_moisture'] - mean)
        })
    return result

def forecast_moisture(device_id: int, hours_ahead: int = 6, db: Session) -> Dict[str, Any]:
    """
    Forecast soil moisture using simple exponential smoothing (Holt-Winters) or linear trend.
    For simplicity, we use linear regression to predict future values.
    """
    df = get_measurements_df(device_id, 48, db)  # use last 2 days
    if len(df) < 5:
        return {"forecast": [], "error": "Insufficient data"}
    
    # Prepare data
    X = df.index.astype(np.int64).values.reshape(-1, 1)
    y = df['soil_moisture'].values
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict next hours_ahead hours
    last_time = df.index[-1]
    future_timestamps = [last_time + timedelta(hours=i) for i in range(1, hours_ahead+1)]
    future_seconds = np.array([ts.timestamp() for ts in future_timestamps]).reshape(-1, 1)
    predictions = model.predict(future_seconds)
    
    forecast = [
        {"timestamp": ts.isoformat(), "predicted_moisture": round(pred, 2)}
        for ts, pred in zip(future_timestamps, predictions)
    ]
    
    # Also return current trend
    slope = model.coef_[0] * 3600 * 1e9  # per hour
    return {
        "forecast": forecast,
        "current_trend_per_hour": round(slope, 2),
        "r2_score": round(model.score(X, y), 3)
    }