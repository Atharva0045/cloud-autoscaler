# ml/load_models.py

import os
import joblib
import xgboost as xgb

# Lazy-loaded model instances (singleton pattern)
_xgb_model = None
_tab_scaler = None
_y_scaler = None

def get_xgb_model():
    """Load XGBoost model (lazy-loaded, cached after first call)."""
    global _xgb_model
    if _xgb_model is None:
        model_path = os.path.join(os.path.dirname(__file__), "..", "artifacts", "xgboost_model_final.json")
        _xgb_model = xgb.XGBRegressor()
        _xgb_model.load_model(model_path)
    return _xgb_model

def get_tab_scaler():
    """Load tabular feature scaler (lazy-loaded, cached after first call)."""
    global _tab_scaler
    if _tab_scaler is None:
        scaler_path = os.path.join(os.path.dirname(__file__), "..", "artifacts", "tab_scaler_final.joblib")
        _tab_scaler = joblib.load(scaler_path)
    return _tab_scaler

def get_y_scaler():
    """Load target scaler (lazy-loaded, cached after first call)."""
    global _y_scaler
    if _y_scaler is None:
        scaler_path = os.path.join(os.path.dirname(__file__), "..", "artifacts", "y_scaler_final.joblib")
        _y_scaler = joblib.load(scaler_path)
    return _y_scaler
