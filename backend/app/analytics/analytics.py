import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.models.models import Measurement, IrrigationEvent
from app.core.logging import logger
import warnings
warnings.filterwarnings('ignore')

# --- Optional ML / Statistical imports ---
try:
    from prophet import Prophet
except ImportError:
    Prophet = None

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
except ImportError:
    SARIMAX = None

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
except ImportError:
    IsolationForest = None
    StandardScaler = None

try:
    from scipy.stats import pearsonr
except ImportError:
    pearsonr = None

# --- Existing functions (drying_rate, efficiency, anomalies, forecast) ---
from app.analytics.moisture_analysis import calculate_drying_rate
from app.analytics.irrigation_analysis import irrigation_efficiency


def get_full_measurements_df(device_id: int, hours: int, db: Session) -> pd.DataFrame:
    """Fetch measurements with temperature and humidity for multivariate analysis."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(Measurement).filter(
        Measurement.device_id == device_id,
        Measurement.timestamp >= cutoff
    ).order_by(Measurement.timestamp)
    data = [
        (m.timestamp, m.soil_moisture, m.temperature, m.humidity) 
        for m in query
    ]
    if not data:
        return pd.DataFrame(columns=['ds', 'y', 'temperature', 'humidity'])
    df = pd.DataFrame(data, columns=['ds', 'y', 'temperature', 'humidity'])
    df['ds'] = pd.to_datetime(df['ds'])
    return df

# ============================================================
# 1. ADVANCED FORECASTING
# ============================================================

def forecast_moisture_prophet(
    device_id: int, 
    days_ahead: int = 3,
    db: Session = None
) -> Dict[str, Any]:
    """
    Forecast soil moisture using Facebook Prophet with weekly seasonality.
    """
    if Prophet is None:
        return {"error": "Prophet is not installed on this server"}
    df = get_full_measurements_df(device_id, hours=days_ahead*24, db=db)
    if len(df) < 48:  # need at least 2 days of data
        return {"error": "Insufficient data for Prophet (need >48 points)"}
    
    # Prophet requires columns 'ds' and 'y'
    prophet_df = df[['ds', 'y']].rename(columns={'y': 'y'})
    model = Prophet(
        daily_seasonality=False,
        weekly_seasonality=True,
        yearly_seasonality=False,
        changepoint_prior_scale=0.05
    )
    model.fit(prophet_df)
    
    # Create future dataframe
    future = model.make_future_dataframe(periods=days_ahead*24, freq='H')
    forecast = model.predict(future)
    
    # Extract predictions for the future period
    last_known = df['ds'].max()
    future_forecast = forecast[forecast['ds'] > last_known]
    
    forecast_list = [
        {"timestamp": row['ds'].isoformat(), 
         "predicted_moisture": round(row['yhat'], 2),
         "lower_bound": round(row['yhat_lower'], 2),
         "upper_bound": round(row['yhat_upper'], 2)}
        for _, row in future_forecast.iterrows()
    ]
    
    # Evaluate trend
    trend_slope = (forecast['trend'].iloc[-1] - forecast['trend'].iloc[0]) / len(forecast) * 24  # per hour
    
    return {
        "forecast": forecast_list,
        "trend_per_hour": round(trend_slope, 2),
        "model": "Prophet"
    }

forecast_moisture = forecast_moisture_prophet



def forecast_moisture_sarima(
    device_id: int, 
    hours_ahead: int = 12,
    db: Session = None
) -> Dict[str, Any]:
    """
    Short-term forecast using SARIMA (Seasonal ARIMA).
    Faster than Prophet for small horizons.
    """
    if SARIMAX is None:
        return {"error": "statsmodels SARIMAX is not installed on this server"}
    df = get_full_measurements_df(device_id, hours=48, db=db)
    if len(df) < 30:
        return {"error": "Insufficient data for SARIMA"}
    
    # Resample to hourly (take mean) to reduce noise
    df_resampled = df.set_index('ds').resample('H').mean().dropna()
    if len(df_resampled) < 24:
        return {"error": "Need at least 24 hourly points"}
    
    series = df_resampled['y']
    # Fit a simple SARIMA model (order may be tuned later)
    try:
        model = SARIMAX(series, order=(1, 1, 1), seasonal_order=(1, 0, 1, 24))
        fitted = model.fit(disp=False)
        forecast = fitted.forecast(steps=hours_ahead)
        
        forecast_list = [
            {"timestamp": (series.index[-1] + timedelta(hours=i+1)).isoformat(),
             "predicted_moisture": round(float(pred), 2)}
            for i, pred in enumerate(forecast)
        ]
        return {
            "forecast": forecast_list,
            "model": "SARIMA",
            "aic": round(fitted.aic, 2) if hasattr(fitted, 'aic') else None
        }
    except Exception as e:
        logger.error(f"SARIMA failed: {e}")
        return {"error": str(e)}


# ============================================================
# 2. MULTIVARIATE ANOMALY DETECTION
# ============================================================

def detect_anomalies_iforest(
    device_id: int,
    window_hours: int = 48,
    contamination: float = 0.05,
    db: Session = None
) -> List[Dict]:
    """
    Detect multivariate anomalies using Isolation Forest on [moisture, temp, humidity].
    """
    df = get_full_measurements_df(device_id, window_hours, db)
    if len(df) < 20:
        return []
    
    # Features
    features = df[['y', 'temperature', 'humidity']].values
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # Train Isolation Forest
    iso_forest = IsolationForest(contamination=contamination, random_state=42)
    preds = iso_forest.fit_predict(features_scaled)
    
    # Extract anomalies (where prediction is -1)
    anomalies = df[preds == -1]
    
    result = []
    for _, row in anomalies.iterrows():
        result.append({
            "timestamp": row['ds'].isoformat(),
            "soil_moisture": round(row['y'], 2),
            "temperature": round(row['temperature'], 2),
            "humidity": round(row['humidity'], 2)
        })
    return result

detect_anomalies = detect_anomalies_iforest



# ============================================================
# 3. IRRIGATION SCHEDULING SUGGESTION
# ============================================================

def suggest_irrigation_schedule(
    device_id: int,
    target_moisture: int = 30,
    db: Session = None
) -> Dict[str, Any]:
    """
    Uses the Prophet forecast to suggest when to irrigate.
    Returns the earliest time moisture is predicted to drop below target.
    """
    # Get forecast for next 2 days
    forecast_data = forecast_moisture_prophet(device_id, days_ahead=2, db=db)
    if "error" in forecast_data:
        return {"error": forecast_data["error"]}
    
    forecast_list = forecast_data["forecast"]
    if not forecast_list:
        return {"suggestion": "No forecast available"}
    
    # Find first time moisture drops below target
    for entry in forecast_list:
        if entry["predicted_moisture"] < target_moisture:
            return {
                "suggestion": "IRRIGATE",
                "scheduled_time": entry["timestamp"],
                "predicted_moisture": entry["predicted_moisture"],
                "confidence_lower": entry["lower_bound"],
                "confidence_upper": entry["upper_bound"]
            }
    
    # If always above target
    return {
        "suggestion": "NO_IRRIGATION_NEEDED",
        "message": f"Moisture predicted to stay above {target_moisture}% for next 2 days"
    }


# ============================================================
# 4. ENVIRONMENTAL CORRELATION
# ============================================================

def environmental_correlation(
    device_id: int,
    hours: int = 72,
    db: Session = None
) -> Dict[str, float]:
    """
    Calculate Pearson correlation between:
    - Soil moisture & Temperature
    - Soil moisture & Humidity
    - Temperature & Humidity
    """
    df = get_full_measurements_df(device_id, hours, db)
    if len(df) < 10:
        return {"error": "Insufficient data for correlation"}
    
    # Drop NaN
    clean_df = df[['y', 'temperature', 'humidity']].dropna()
    if len(clean_df) < 10:
        return {"error": "Not enough clean data points"}
    
    if pearsonr:
        corr_moist_temp, _ = pearsonr(clean_df['y'], clean_df['temperature'])
        corr_moist_hum, _ = pearsonr(clean_df['y'], clean_df['humidity'])
        corr_temp_hum, _ = pearsonr(clean_df['temperature'], clean_df['humidity'])
    else:
        corr_moist_temp = float(clean_df['y'].corr(clean_df['temperature']))
        corr_moist_hum = float(clean_df['y'].corr(clean_df['humidity']))
        corr_temp_hum = float(clean_df['temperature'].corr(clean_df['humidity']))
    
    return {
        "moisture_temperature_correlation": round(corr_moist_temp, 3),
        "moisture_humidity_correlation": round(corr_moist_hum, 3),
        "temperature_humidity_correlation": round(corr_temp_hum, 3)
    }