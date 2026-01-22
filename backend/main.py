import os
import logging
import traceback
import datetime  # Added missing import
from fastapi import FastAPI, HTTPException
from data.fetch_live_metrics import fetch_live_metrics, save_live_buffer
from ml.inference import predict_cpu
from decision.scaling_policy import decide_action, record_action
from aws.ec2_controller import get_instance_type, scale_up, scale_down
from backend.config import DRY_RUN, LOG_FILE

# Setup logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

app = FastAPI(title="AI Cloud Resource Allocator")

@app.get("/autoscale")
def autoscale():
    """
    Main autoscaling endpoint.
    """
    try:
        # Step 1: Fetch metrics from Prometheus
        logging.info("Fetching live metrics from Prometheus...")
        df = fetch_live_metrics()
        
        # Step 2: Save to live_buffer.csv atomically
        save_live_buffer(df)
        
        # Step 3 & 4: Build features and predict CPU
        logging.info("Running inference...")
        prediction_result = predict_cpu()
        predicted_cpu = prediction_result["predicted_cpu"]
        confidence = prediction_result["confidence"]
        
        # Step 5: Apply scaling policy
        logging.info(f"Predicted CPU: {predicted_cpu:.2f}%, Confidence: {confidence:.3f}")
        decision = decide_action(
            predicted_cpu=predicted_cpu,
            confidence=confidence,
            anomaly_severity=0.0
        )
        
        # Step 6: Get current instance type
        try:
            current_instance_type, current_state = get_instance_type()
        except Exception as e:
            logging.error(f"Failed to get instance type: {e}")
            current_instance_type = "unknown"
            current_state = "unknown"
        
        # Step 7: Execute scaling action
        action_taken = "none"
        aws_result = None
        
        if decision["action"] == "scale_up":
            logging.info(f"Decision: SCALE UP - {decision['reason']}")
            try:
                aws_result = scale_up()
                if aws_result.get("success"):
                    action_taken = "scale_up"
                    record_action("scale_up")
                    logging.info(f"✅ Scale up successful: {aws_result.get('old_type')} -> {aws_result.get('new_type')}")
                else:
                    logging.warning(f"Scale up skipped: {aws_result.get('reason')}")
            except Exception as e:
                logging.error(f"Scale up failed: {e}")
                logging.error(traceback.format_exc())
                
        elif decision["action"] == "scale_down":
            logging.info(f"Decision: SCALE DOWN - {decision['reason']}")
            try:
                aws_result = scale_down()
                if aws_result.get("success"):
                    action_taken = "scale_down"
                    record_action("scale_down")
                    logging.info(f"✅ Scale down successful: {aws_result.get('old_type')} -> {aws_result.get('new_type')}")
                else:
                    logging.warning(f"Scale down skipped: {aws_result.get('reason')}")
            except Exception as e:
                logging.error(f"Scale down failed: {e}")
                logging.error(traceback.format_exc())
                
        else:
            logging.info(f"Decision: NO ACTION - {decision['reason']}")
        
        # Structured log entry
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = (
            f"timestamp={timestamp} | "
            f"current_instance_type={current_instance_type} | "
            f"predicted_cpu={predicted_cpu:.2f} | "
            f"confidence={confidence:.3f} | "
            f"decision={decision['action']} | "
            f"action_taken={action_taken} | "
            f"reason={decision['reason']}"
        )
        logging.info(log_entry)
        
        # Return response
        response = {
            "predicted_cpu": predicted_cpu,
            "confidence": confidence,
            "decision": decision["action"],
            "reason": decision["reason"],
            "current_instance_type": current_instance_type,
            "action_taken": action_taken,
            "dry_run": DRY_RUN
        }
        
        if aws_result:
            response["aws_result"] = aws_result
        
        return response
        
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logging.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Autoscaling error: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/health")
def health():
    return {"status": "ok"}