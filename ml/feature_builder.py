# ml/feature_builder.py

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ROLL_WIN = 60
RANDOM_SEED = 42

def build_features(df):
    """
    Build features EXACTLY matching training pipeline (from model_training.ipynb).
    
    Args:
        df: DataFrame with columns ['timestamp', 'cpu', 'ram', 'disk']
        
    Returns:
        DataFrame with engineered features (1 row after dropna)
        
    Raises:
        ValueError: If insufficient rows for feature engineering
    """
    df = df.copy()

    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # Validate minimum rows needed (max lag is 12, rolling window is 60)
    min_rows_required = max(ROLL_WIN, 12) + 1
    if len(df) < min_rows_required:
        raise ValueError(
            f"Insufficient rows for feature engineering: "
            f"got {len(df)}, need at least {min_rows_required}"
        )
    
    # --- Anomaly detection (Cell 13) ---
    # Rolling statistics (past-only, shifted to avoid leakage)
    df["cpu_roll_median_past"] = df["cpu"].rolling(window=ROLL_WIN, min_periods=1).median().shift(1)
    df["cpu_roll_std_past"] = df["cpu"].rolling(window=ROLL_WIN, min_periods=1).std().shift(1).fillna(1e-6)
    
    # Z-score (past-only)
    df["cpu_zscore_past"] = (df["cpu"] - df["cpu_roll_median_past"]) / df["cpu_roll_std_past"]

    # Z-score based anomaly
    df["is_anomaly_z"] = (df["cpu_zscore_past"].abs() > 3).astype(int)

    # IsolationForest anomaly (fit on available data)
    iso = IsolationForest(contamination=0.02, random_state=RANDOM_SEED)
    iso_labels = iso.fit_predict(df[["cpu", "ram", "disk"]].ffill().values)
    df["is_anomaly_iso"] = (iso_labels == -1).astype(int)
    
    # Anomaly severity (MUST be included as feature)
    df["anomaly_severity"] = df["is_anomaly_z"] * np.abs(df["cpu_zscore_past"]) + df["is_anomaly_iso"] * 1.0
    
    # --- Tabular features (Cell 15: build_tabular) ---
    # Time features
    df["hour"] = df["timestamp"].dt.hour
    df["minute"] = df["timestamp"].dt.minute
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    # Lag features (past-only)
    lags = [1, 2, 3, 6, 12]
    for lag in lags:
        df[f"cpu_lag_{lag}"] = df["cpu"].shift(lag)
        df[f"ram_lag_{lag}"] = df["ram"].shift(lag)
        df[f"disk_lag_{lag}"] = df["disk"].shift(lag)

    # Rolling windows (past-only, shifted)
    windows = {"short": 3, "med": 12, "long": 60}  # ~15s, 60s, 5min
    for name, w in windows.items():
        df[f"cpu_roll_mean_{name}"] = df["cpu"].rolling(window=w, min_periods=1).mean().shift(1)
        df[f"cpu_roll_std_{name}"] = df["cpu"].rolling(window=w, min_periods=1).std().shift(1).fillna(0)
        df[f"ram_roll_mean_{name}"] = df["ram"].rolling(window=w, min_periods=1).mean().shift(1)
        df[f"disk_roll_mean_{name}"] = df["disk"].rolling(window=w, min_periods=1).mean().shift(1)
    
    # EWM (past-only, shifted) - adjust=False to match training
    df["cpu_ewm_30"] = df["cpu"].ewm(span=30, adjust=False).mean().shift(1)
    
    # Cross features
    df["cpu_x_ram"] = df["cpu"] * df["ram"]

    # Drop rows with NaN (from lag/rolling features)
    df.dropna(inplace=True)
    
    # Final validation: ensure we have at least 1 row
    if len(df) == 0:
        raise ValueError("Feature engineering resulted in 0 rows after dropna")
    
    # Ensure no NaN values remain
    if df.isnull().any().any():
        raise ValueError("NaN values detected after feature engineering")
    
    return df
