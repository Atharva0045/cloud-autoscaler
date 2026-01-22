# aws/ec2_controller.py

import boto3
import time
import logging
from aws.aws_config import AWS_REGION, INSTANCE_ID, INSTANCE_SEQUENCE
from backend.config import DRY_RUN
from aws.monitoring_setup import setup_monitoring_on_instance

ec2 = boto3.client("ec2", region_name=AWS_REGION)


def get_instance_type():
    """Get current EC2 instance type and state."""
    try:
        res = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
        instance = res["Reservations"][0]["Instances"][0]
        return instance["InstanceType"], instance["State"]["Name"]
    except Exception as e:
        logging.error(f"Failed to get instance type: {e}")
        raise

def change_instance_type(new_type):
    """
    Change EC2 instance type (STOP → MODIFY → START).
    
    Args:
        new_type: Target instance type (e.g., "t2.medium")
        
    Returns:
        dict with scaling result
    """
    current_type, current_state = get_instance_type()
    
    # Safety check: cannot scale while running
    if current_state != "stopped":
        raise ValueError(
            f"Cannot scale instance while state is '{current_state}'. "
            f"Instance must be stopped first."
        )
    
    # Safety check: prevent same-type scaling
    if current_type == new_type:
        logging.warning(f"Instance already at {new_type}, skipping")
        return {
            "success": False,
            "reason": f"Instance already at {new_type}",
            "old_type": current_type,
            "new_type": new_type
        }
    
    if DRY_RUN:
        logging.info(f"[DRY RUN] Would scale EC2 from {current_type} to {new_type}")
        return {
            "success": True,
            "dry_run": True,
            "old_type": current_type,
            "new_type": new_type
        }
    
    logging.info(f"🚀 Scaling EC2 from {current_type} to {new_type}")
    
    try:
        # Modify instance type (instance must be stopped)
        ec2.modify_instance_attribute(
            InstanceId=INSTANCE_ID,
            InstanceType={"Value": new_type},
        )

        logging.info(f"✅ Instance type modified to {new_type}")

        # Start instance
        ec2.start_instances(InstanceIds=[INSTANCE_ID])
        waiter = ec2.get_waiter("instance_running")
        waiter.wait(InstanceIds=[INSTANCE_ID])

        logging.info(f"✅ Instance started with new type {new_type}")

        result = {
            "success": True,
            "dry_run": False,
            "old_type": current_type,
            "new_type": new_type,
        }

        # After a successful, non-dry-run change, ensure monitoring is set up
        try:
            setup_monitoring_on_instance(INSTANCE_ID)
        except Exception as monitor_err:
            logging.error(
                f"Monitoring setup failed after scaling to {new_type}: {monitor_err}"
            )

        return result
    except Exception as e:
        logging.error(f"Failed to change instance type: {e}")
        raise

def scale_up():
    """
    Scale EC2 instance up to next larger type in sequence.
    
    Returns:
        dict with scaling result
    """
    try:
        current_type, current_state = get_instance_type()
        
        if current_type not in INSTANCE_SEQUENCE:
            raise ValueError(f"Current instance type {current_type} not in sequence {INSTANCE_SEQUENCE}")
        
        idx = INSTANCE_SEQUENCE.index(current_type)
        if idx >= len(INSTANCE_SEQUENCE) - 1:
            return {
                "success": False,
                "reason": f"Already at maximum instance type: {current_type}",
                "old_type": current_type,
                "new_type": current_type
            }
        
        new_type = INSTANCE_SEQUENCE[idx + 1]
        
        # Check dry run BEFORE stopping instance
        if DRY_RUN:
            logging.info(f"[DRY RUN] Would scale EC2 from {current_type} to {new_type}")
            return {
                "success": True,
                "dry_run": True,
                "old_type": current_type,
                "new_type": new_type
            }
        
        # If instance is running, stop it first (only in non-dry-run mode)
        if current_state == "running":
            logging.info(f"Stopping instance {INSTANCE_ID} before scaling up...")
            ec2.stop_instances(InstanceIds=[INSTANCE_ID])
            waiter = ec2.get_waiter("instance_stopped")
            waiter.wait(InstanceIds=[INSTANCE_ID])
            logging.info("Instance stopped")

        return change_instance_type(new_type)
    except Exception as e:
        logging.error(f"Scale up failed: {e}")
        raise

def scale_down():
    """
    Scale EC2 instance down to next smaller type in sequence.
    
    Returns:
        dict with scaling result
    """
    try:
        current_type, current_state = get_instance_type()
        
        if current_type not in INSTANCE_SEQUENCE:
            raise ValueError(f"Current instance type {current_type} not in sequence {INSTANCE_SEQUENCE}")
        
        idx = INSTANCE_SEQUENCE.index(current_type)
        if idx <= 0:
            return {
                "success": False,
                "reason": f"Already at minimum instance type: {current_type}",
                "old_type": current_type,
                "new_type": current_type
            }
        
        new_type = INSTANCE_SEQUENCE[idx - 1]
        
        # Check dry run BEFORE stopping instance
        if DRY_RUN:
            logging.info(f"[DRY RUN] Would scale EC2 from {current_type} to {new_type}")
            return {
                "success": True,
                "dry_run": True,
                "old_type": current_type,
                "new_type": new_type
            }
        
        # If instance is running, stop it first (only in non-dry-run mode)
        if current_state == "running":
            logging.info(f"Stopping instance {INSTANCE_ID} before scaling down...")
            ec2.stop_instances(InstanceIds=[INSTANCE_ID])
            waiter = ec2.get_waiter("instance_stopped")
            waiter.wait(InstanceIds=[INSTANCE_ID])
            logging.info("Instance stopped")

        return change_instance_type(new_type)
    except Exception as e:
        logging.error(f"Scale down failed: {e}")
        raise
