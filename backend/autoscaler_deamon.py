import os
import sys
import time
import signal
import logging
import requests
from backend.config import FETCH_INTERVAL_SECONDS, LOG_FILE, DRY_RUN

# Setup logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logging.info("Shutdown signal received, finishing current cycle...")
    shutdown_requested = True

def call_autoscale_endpoint():
    """Call the /autoscale endpoint."""
    try:
        # Try to call local FastAPI endpoint
        response = requests.get("http://localhost:8000/autoscale", timeout=60)
        response.raise_for_status()
        result = response.json()
        
        # Print result to console for visibility
        print(f"\n{'='*60}")
        print(f"Cycle completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Predicted CPU: {result.get('predicted_cpu', 'N/A'):.2f}%")
        print(f"Confidence: {result.get('confidence', 'N/A'):.3f}")
        print(f"Decision: {result.get('decision', 'N/A')}")
        print(f"Action Taken: {result.get('action_taken', 'N/A')}")
        print(f"Current Instance: {result.get('current_instance_type', 'N/A')}")
        if DRY_RUN:
            print(f"⚠️  DRY RUN MODE - No actual scaling performed")
        print(f"{'='*60}\n")
        
        return result
    except requests.exceptions.ConnectionError:
        logging.error("Cannot connect to FastAPI server. Is it running?")
        print("ERROR: Cannot connect to FastAPI server at http://localhost:8000")
        print("Please start the server first: uvicorn backend.main:app --host 0.0.0.0 --port 8000")
        return None
    except Exception as e:
        logging.error(f"Failed to call autoscale endpoint: {e}")
        return None

def autoscale_loop():
    """Main daemon loop."""
    global shutdown_requested
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logging.info("="*60)
    logging.info("Autoscaler daemon started")
    logging.info(f"Fetch interval: {FETCH_INTERVAL_SECONDS} seconds")
    logging.info(f"Dry run mode: {DRY_RUN}")
    logging.info("="*60)
    
    print(f"\n🚀 Autoscaler daemon started")
    print(f"   Interval: {FETCH_INTERVAL_SECONDS} seconds ({FETCH_INTERVAL_SECONDS/60:.1f} minutes)")
    print(f"   Dry run: {DRY_RUN}")
    print(f"   Log file: {LOG_FILE}")
    print(f"\nPress Ctrl+C to stop\n")
    
    cycle_count = 0
    
    while not shutdown_requested:
        try:
            cycle_count += 1
            logging.info(f"Starting autoscaling cycle #{cycle_count}")
            
            result = call_autoscale_endpoint()
            
            if result is None:
                logging.warning("Autoscale endpoint call failed, waiting before retry...")
                time.sleep(30)  # Wait 30s before retry if endpoint unavailable
                continue
            
            logging.info(f"Cycle #{cycle_count} completed successfully")
            
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received")
            break
        except Exception as e:
            logging.error(f"Unexpected error in autoscaling cycle: {e}")
            logging.error(f"Traceback: {traceback.format_exc()}")
        
        # Sleep until next cycle (unless shutdown requested)
        if not shutdown_requested:
            logging.info(f"Sleeping for {FETCH_INTERVAL_SECONDS} seconds...")
            time.sleep(FETCH_INTERVAL_SECONDS)
    
    logging.info("Autoscaler daemon stopped")
    print("\n✅ Autoscaler daemon stopped gracefully")

if __name__ == "__main__":
    import traceback
    try:
        autoscale_loop()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        logging.error(traceback.format_exc())
        sys.exit(1)
