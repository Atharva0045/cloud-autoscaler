# decision/scaling_policy.py

import time
import logging
from backend.config import (
    SCALE_UP_CPU, 
    SCALE_DOWN_CPU, 
    MIN_CONFIDENCE,
    COOLDOWN_SECONDS
)

# Module-level state for cooldown tracking
_last_action_time = 0
_last_action = None

def decide_action(predicted_cpu, confidence, anomaly_severity=0.0):
    """
    Decide scaling action based on predicted CPU, confidence, and anomaly severity.
    
    Args:
        predicted_cpu: Predicted CPU usage percentage
        confidence: Confidence score (0-1)
        anomaly_severity: Anomaly severity indicator (0-1, optional)
        
    Returns:
        dict with keys:
            - action: "scale_up" | "scale_down" | "noop"
            - reason: str (explanation)
    """
    global _last_action_time, _last_action
    
    now = time.time()

    # Check cooldown
    time_since_last_action = now - _last_action_time
    if time_since_last_action < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - time_since_last_action)
        return {
            "action": "noop",
            "reason": f"Cooldown active: {remaining}s remaining"
        }
    
    # Check confidence threshold
    if confidence < MIN_CONFIDENCE:
        return {
            "action": "noop",
            "reason": f"Low confidence: {confidence:.3f} < {MIN_CONFIDENCE}"
        }
    
    # Scale up decision
    if predicted_cpu > SCALE_UP_CPU:
        return {
            "action": "scale_up",
            "reason": f"Predicted CPU {predicted_cpu:.2f}% > {SCALE_UP_CPU}% (confidence: {confidence:.3f})"
        }
    
    # Scale down decision
    if predicted_cpu < SCALE_DOWN_CPU:
        return {
            "action": "scale_down",
            "reason": f"Predicted CPU {predicted_cpu:.2f}% < {SCALE_DOWN_CPU}% (confidence: {confidence:.3f})"
        }
    
    # No action
    return {
        "action": "noop",
        "reason": f"CPU {predicted_cpu:.2f}% within safe range [{SCALE_DOWN_CPU}%, {SCALE_UP_CPU}%]"
    }

def record_action(action):
    """Record that an action was taken (for cooldown tracking)."""
    global _last_action_time, _last_action
    _last_action_time = time.time()
    _last_action = action
