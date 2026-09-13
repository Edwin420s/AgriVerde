import io
import csv
from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

import pandas as pd
import numpy as np
try:
    from pmdarima import auto_arima
except ImportError:
    auto_arima = None

try:
    from sklearn.preprocessing import MinMaxScaler
except ImportError:
    MinMaxScaler = None

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
except ImportError:
    Sequential = None
    LSTM = None
    Dense = None
    Dropout = None
    EarlyStopping = None

from app.models.models import Alert
from app.core.logging import logger
from app.analytics.analytics import get_full_measurements_df, forecast_moisture_prophet

# === 1. AUTO-SARIMA FORECAST ===

def auto_sarima_forecast(
    device_id: int,
    hours_ahead: int = 24,
    db: Session = None
) -> Dict[str, Any]:
    """
    Auto-select SARIMA order using pmdarima and forecast.
    """
    if auto_arima is None:
        return {"error": "pmdarima is not installed on this server"}
    df = get_full_measurements_df(device_id, hours=72, db=db)  # use last 3 days
    if len(df) < 48:
        return {"error": "Insufficient data for auto-SARIMA (need >48 points)"}
    
    # Resample to hourly and fill missing
    df_resampled = df.set_index('ds').resample('H').mean().interpolate().dropna()
    if len(df_resampled) < 24:
        return {"error": "Not enough hourly points after resampling"}
    
    series = df_resampled['y']
    
    # Auto-ARIMA with seasonality (period=24)
    try:
        model = auto_arima(
            series,
            start_p=0, max_p=3,
            start_q=0, max_q=3,
            seasonal=True, m=24,
            start_P=0, max_P=2,
            start_Q=0, max_Q=2,
            trace=False,
            error_action='ignore',
            suppress_warnings=True,
            stepwise=True,
            random_state=42
        )
        forecast = model.predict(n_periods=hours_ahead)
        forecast_index = pd.date_range(
            start=series.index[-1] + pd.Timedelta(hours=1),
            periods=hours_ahead,
            freq='H'
        )
        forecast_list = [
            {"timestamp": ts.isoformat(), "predicted_moisture": round(val, 2)}
            for ts, val in zip(forecast_index, forecast)
        ]
        return {
            "forecast": forecast_list,
            "model": f"SARIMA{model.order}{model.seasonal_order}",
            "aic": round(model.aic(), 2)
        }
    except Exception as e:
        logger.error(f"Auto-SARIMA failed: {e}")
        return {"error": str(e)}


# === 2. LSTM FORECAST (with data length check) ===

def lstm_forecast(
    device_id: int,
    hours_ahead: int = 24,
    lookback: int = 48,
    db: Session = None
) -> Dict[str, Any]:
    """
    LSTM forecast – only if we have at least 6 months of data (4320 hourly points).
    """
    if Sequential is None or MinMaxScaler is None:
        return {"error": "tensorflow and/or scikit-learn are not installed on this server"}
    df = get_full_measurements_df(device_id, hours=4320, db=db)  # 180 days
    if len(df) < 4320:
        return {"error": f"Insufficient data for LSTM. Need 4320 hourly points, got {len(df)}"}
    
    # Resample to hourly
    df_resampled = df.set_index('ds').resample('H').mean().interpolate().dropna()
    if len(df_resampled) < 4320:
        return {"error": f"After resampling, only {len(df_resampled)} points (need 4320)"}
    
    series = df_resampled['y'].values.reshape(-1, 1)
    
    # Scale data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(series)
    
    # Prepare sequences
    X, y = [], []
    for i in range(lookback, len(scaled)):
        X.append(scaled[i-lookback:i, 0])
        y.append(scaled[i, 0])
    X = np.array(X).reshape(-1, lookback, 1)
    y = np.array(y)
    
    # Train/test split (80/20)
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    # Build LSTM model
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(lookback, 1)),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    
    # Train with early stopping
    early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
    model.fit(X_train, y_train, epochs=50, batch_size=32, 
              validation_data=(X_test, y_test), callbacks=[early_stop], verbose=0)
    
    # Predict next hours_ahead steps recursively
    last_sequence = scaled[-lookback:].reshape(1, lookback, 1)
    predictions = []
    for _ in range(hours_ahead):
        pred = model.predict(last_sequence, verbose=0)[0, 0]
        predictions.append(pred)
        # Update sequence
        last_sequence = np.append(last_sequence[0, 1:, 0], pred).reshape(1, lookback, 1)
    
    # Inverse transform
    predicted = scaler.inverse_transform(np.array(predictions).reshape(-1, 1)).flatten()
    
    last_time = df_resampled.index[-1]
    forecast_index = pd.date_range(start=last_time + pd.Timedelta(hours=1), periods=hours_ahead, freq='H')
    forecast_list = [
        {"timestamp": ts.isoformat(), "predicted_moisture": round(val, 2)}
        for ts, val in zip(forecast_index, predicted)
    ]
    
    return {
        "forecast": forecast_list,
        "model": "LSTM",
        "lookback": lookback,
        "rmse": round(np.sqrt(model.evaluate(X_test, y_test, verbose=0)), 2)
    }


# === 3. REAL-TIME ALERT TRIGGER ===

def trigger_alert_on_forecast_drop(
    device_id: int,
    target_moisture: int = 30,
    db: Session = None
) -> Dict[str, Any]:
    """
    Check if forecast predicts moisture below target within next 24 hours.
    If so, create an Alert record.
    """
    # Use Prophet forecast (or any other) – we'll use auto-sarima for speed
    forecast_result = auto_sarima_forecast(device_id, hours_ahead=24, db=db)
    if "error" in forecast_result:
        return {"error": forecast_result["error"]}
    
    forecast_list = forecast_result["forecast"]
    if not forecast_list:
        return {"message": "No forecast available"}
    
    # Find first time moisture drops below target
    for entry in forecast_list:
        if entry["predicted_moisture"] < target_moisture:
            # Create an alert
            new_alert = Alert(
                device_id=device_id,
                severity="WARNING",
                message=f"Forecast predicts moisture below {target_moisture}% at {entry['timestamp']}",
                forecast_data=entry
            )
            db.add(new_alert)
            db.commit()
            return {
                "alert_created": True,
                "alert_id": new_alert.id,
                "timestamp": entry["timestamp"],
                "predicted_moisture": entry["predicted_moisture"]
            }
    
    return {"alert_created": False, "message": "Moisture predicted above target for next 24 hours"}


# === 4. CSV EXPORT ===

def forecast_to_csv(device_id: int, hours_ahead: int = 24, db: Session = None) -> StreamingResponse:
    """
    Export forecast as CSV.
    """
    # Use Prophet (or any) for forecast
    result = forecast_moisture_prophet(device_id, days_ahead=hours_ahead//24 + 1, db=db)
    if "error" in result:
        return StreamingResponse(
            io.StringIO("error,message\n" + result["error"]),
            media_type="text/csv"
        )
    
    forecast_list = result["forecast"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "predicted_moisture", "lower_bound", "upper_bound"])
    for entry in forecast_list:
        writer.writerow([
            entry["timestamp"],
            entry["predicted_moisture"],
            entry["lower_bound"],
            entry["upper_bound"]
        ])
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=forecast_device_{device_id}.csv"}
    )