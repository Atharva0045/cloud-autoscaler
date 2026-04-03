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

    # Calculate confidence based on coefficient of variation (CV = std/mean)
    # This normalizes the std by the mean, giving more reasonable confidence values
    rolling_std = latest["cpu_roll_std_past"].values[0]
    
    # Try to get rolling mean (prefer long-term for stability)
    # Fallback to median if mean not available
    if "cpu_roll_mean_long" in latest.columns:
        rolling_mean = latest["cpu_roll_mean_long"].values[0]
    elif "cpu_roll_mean_med" in latest.columns:
        rolling_mean = latest["cpu_roll_mean_med"].values[0]
    elif "cpu_roll_median_past" in latest.columns:
        rolling_mean = latest["cpu_roll_median_past"].values[0]
    else:
        # Fallback: use current CPU value as proxy for mean
        rolling_mean = latest["cpu"].values[0] if "cpu" in latest.columns else 50.0
    
    # Avoid division by zero or very small mean
    if rolling_mean < 1.0:
        # If mean is too small, normalize std by typical CPU range (0-100)
        # Assume max reasonable std is ~50% of range
        normalized_std = rolling_std / 50.0
    else:
        # Use coefficient of variation (CV = std/mean)
        # This gives a normalized measure of variability
        cv = rolling_std / rolling_mean
        normalized_std = cv
    
    # Convert to confidence: lower variability = higher confidence
    # confidence = 1 / (1 + normalized_std)
    # Examples:
    #   CV=0.1 (10% variability) → confidence = 1/(1+0.1) = 0.91 (high)
    #   CV=0.3 (30% variability) → confidence = 1/(1+0.3) = 0.77 (good)
    #   CV=0.5 (50% variability) → confidence = 1/(1+0.5) = 0.67 (medium)
    #   CV=1.0 (100% variability) → confidence = 1/(1+1.0) = 0.5 (low)
    confidence = float(1.0 / (1.0 + normalized_std))
    confidence = max(0.0, min(1.0, confidence))  # clamp to [0, 1]
    
    return {
        "predicted_cpu": float(y_pred),
        "confidence": confidence
    }
