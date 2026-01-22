# ml/inference.py

import os
import pandas as pd
import numpy as np
from ml.load_models import get_xgb_model, get_tab_scaler
from ml.feature_builder import build_features

def predict_cpu(csv_path="data/live_buffer.csv"):
    """
    Predict future CPU usage (+60s) using XGBoost model.
    
    Args:
        csv_path: Path to CSV file with columns ['timestamp', 'cpu', 'ram', 'disk']
                  Can be relative or absolute path
        
    Returns:
        dict with keys:
            - predicted_cpu: float (predicted CPU %)
            - confidence: float (confidence score 0-1)
    """
    # Load models (lazy-loaded)
    xgb_model = get_xgb_model()
    tab_scaler = get_tab_scaler()
    
    # Handle relative paths (relative to project root)
    if not os.path.isabs(csv_path):
        project_root = os.path.join(os.path.dirname(__file__), "..")
        csv_path = os.path.join(project_root, csv_path)
    
    # Read data
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Metrics file not found: {csv_path}")
    
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    # Validate required columns
    required_cols = ["timestamp", "cpu", "ram", "disk"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Build features
    feats = build_features(df)
    
    # Get latest row (most recent features)
    latest = feats.iloc[-1:]

    # Extract feature columns (exclude only timestamp, matching training)
    # Note: cpu, ram, disk ARE included as features (matching training notebook Cell 17)
    available_cols = [col for col in latest.columns 
                      if col not in ["timestamp"]]
    
    # Use scaler's expected feature names and order (if available, sklearn 1.0+)
    # This ensures exact match with training
    if hasattr(tab_scaler, 'feature_names_in_'):
        expected_cols = list(tab_scaler.feature_names_in_)
        # Check for missing features
        missing = set(expected_cols) - set(available_cols)
        if missing:
            raise ValueError(
                f"Missing features expected by scaler: {missing}. "
                f"Available: {available_cols}"
            )
        # Reorder to match scaler's expected order
        X = latest[expected_cols]
    else:
        # Fallback: use available columns (older sklearn versions)
        X = latest[available_cols]
    
    # Scale features (scaler expects same columns in same order as training)
    X_scaled = tab_scaler.transform(X)

    # Predict
    # Note: XGBoost was trained on UNSCALED targets (raw CPU %), so no inverse transform needed.
    # The y_scaler was only used for LSTM training, not XGBoost.
    y_pred = xgb_model.predict(X_scaled)[0]

    # Calculate confidence based on rolling std
    # confidence = 1 / (1 + rolling_std_cpu)
    rolling_std = latest["cpu_roll_std_past"].values[0]
    confidence = float(1.0 / (1.0 + rolling_std))
    confidence = max(0.0, min(1.0, confidence))  # clamp to [0, 1]
    
    return {
        "predicted_cpu": float(y_pred),
        "confidence": confidence
    }
