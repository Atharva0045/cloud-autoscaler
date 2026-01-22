import os
import requests
import pandas as pd
import time
import logging
from backend.config import WINDOW_SECONDS
from aws.monitoring_setup import get_instance_ip

STEP = "5s"

METRICS = {
    "cpu": "100 - (avg by(instance)(rate(node_cpu_seconds_total{mode='idle'}[1m])) * 100)",
    "ram": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100",
    "disk": "rate(node_disk_read_bytes_total[1m]) + rate(node_disk_written_bytes_total[1m])"
}


def get_prometheus_url() -> str:
    """
    Build the Prometheus query_range URL for the *current* instance.
    This makes the autoscaler always follow the active machine's IP.
    """
    ip = get_instance_ip()
    return f"http://{ip}:9090/api/v1/query_range"

def fetch_metric(query, name, start, end):
    """Fetch a single metric from Prometheus."""
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": STEP
    }
    
    try:
        prom_url = get_prometheus_url()
        r = requests.get(prom_url, params=params, timeout=10)
        r.raise_for_status()

        data = r.json().get("data", {}).get("result", [])
        
        if not data:
            logging.warning(f"No data returned for metric {name}")
            return pd.DataFrame(columns=["timestamp", name])

        values = data[0]["values"]
        df = pd.DataFrame(values, columns=["timestamp", name])
        
        # Convert timestamp to datetime and value to float
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="s")
        df[name] = df[name].astype(float)
        
        return df

    except Exception as e:
        logging.error(f"Failed to fetch metric {name}: {e}")
        # Return empty DF on failure to prevent pipeline crash, or raise if critical
        raise e

def fetch_live_metrics():
    """
    Fetch last 5 minutes of metrics from Prometheus.
    Returns:
        DataFrame with columns ['timestamp', 'cpu', 'ram', 'disk']
    """
    end = int(time.time())
    start = end - WINDOW_SECONDS

    dfs = {}
    for name, q in METRICS.items():
        try:
            dfs[name] = fetch_metric(q, name, start, end)
        except Exception:
            # If a metric fails, we might want to return an empty DF or handle gracefully
            logging.error(f"Skipping metric {name} due to fetch error.")
            dfs[name] = pd.DataFrame(columns=["timestamp", name])

    # Merge all metrics on timestamp
    # Start with CPU as the base
    df = dfs.get("cpu", pd.DataFrame(columns=["timestamp", "cpu"]))
    
    for k in ["ram", "disk"]:
        if k in dfs and not dfs[k].empty:
            df = df.merge(dfs[k], on="timestamp", how="outer")

    if df.empty:
        raise ValueError("No metrics fetched from Prometheus.")

    df.sort_values("timestamp", inplace=True)
    df.ffill(inplace=True)
    df.bfill(inplace=True)  # Fill any remaining NaNs

    return df

def save_live_buffer(df, csv_path="data/live_buffer.csv"):
    """
    Atomically overwrite live_buffer.csv with new metrics.
    
    Args:
        df: DataFrame to save
        csv_path: Path to CSV file
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        # Write to temporary file first, then rename (atomic on most filesystems)
        temp_path = csv_path + ".tmp"
        df.to_csv(temp_path, index=False)
        os.replace(temp_path, csv_path)
        
        logging.info(f"Saved {len(df)} rows to {csv_path}")
    except Exception as e:
        logging.error(f"Failed to save live buffer: {e}")
        raise