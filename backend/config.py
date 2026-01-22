# backend/config.py

import os

FETCH_INTERVAL_SECONDS = 300  # 5 minutes
WINDOW_SECONDS = 300          # 5 minutes history
PREDICTION_HORIZON = 60       # predict +60s

# Scaling thresholds (as per spec)
SCALE_UP_CPU = 75.0           # Scale up if predicted CPU > 75%
SCALE_DOWN_CPU = 30.0         # Scale down if predicted CPU < 30%
MIN_CONFIDENCE = 0.6          # Minimum confidence required for scaling

# Cooldown to avoid thrashing (10 minutes as per spec)
COOLDOWN_SECONDS = 600  # 10 minutes

# Dry-run mode (set to False for actual scaling)
DRY_RUN = os.getenv("DRY_RUN", "True").lower() == "true"

LOG_FILE = "logs/autoscaler.log"
