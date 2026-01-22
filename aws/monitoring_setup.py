import logging
import boto3

from aws.aws_config import AWS_REGION, INSTANCE_ID
from backend.config import DRY_RUN


ec2 = boto3.client("ec2", region_name=AWS_REGION)
ssm = boto3.client("ssm", region_name=AWS_REGION)


def get_instance_ip(instance_id: str | None = None, use_public: bool = True) -> str:
    """
    Resolve the current IP address of the monitored instance.

    This is used so Prometheus queries always point at the *current* machine,
    even if the instance was replaced or its IP changed.
    """
    target_id = instance_id or INSTANCE_ID
    try:
        res = ec2.describe_instances(InstanceIds=[target_id])
        instance = res["Reservations"][0]["Instances"][0]

        if use_public:
            ip_key = "PublicIpAddress"
        else:
            ip_key = "PrivateIpAddress"

        ip = instance.get(ip_key)
        if not ip:
            # Fall back to private IP if public isn't available
            ip = instance.get("PrivateIpAddress")

        if not ip:
            raise ValueError(f"No IP address found for instance {target_id}")

        return ip
    except Exception as e:
        logging.error(f"Failed to resolve IP for instance {target_id}: {e}")
        raise


def setup_monitoring_on_instance(instance_id: str | None = None) -> None:
    """
    Install / (re)start Prometheus and node exporter on the target instance.

    This uses AWS SSM to run a shell script on the instance. It assumes:
      - The instance has the SSM agent installed
      - The instance IAM role allows SSM RunCommand

    In DRY_RUN mode, this only logs what would be done.
    """
    target_id = instance_id or INSTANCE_ID

    if DRY_RUN:
        logging.info(
            f"[DRY RUN] Would (re)configure Prometheus + node_exporter on instance {target_id}"
        )
        return

    logging.info(f"Configuring Prometheus + node_exporter on instance {target_id} via SSM")

    # Very lightweight, demo-focused install script.
    # Adjust to match your OS / security guidelines.
    commands = [
        "#!/bin/bash",
        "set -e",
        "echo 'Starting Prometheus/node_exporter setup...'",
        "sudo mkdir -p /opt/monitoring",
        "cd /opt/monitoring",
        # Install Docker if not present
        "if ! command -v docker >/dev/null 2>&1; then",
        "  echo 'Installing Docker...'",
        "  curl -fsSL https://get.docker.com | sh",
        "  sudo usermod -aG docker ec2-user || true",
        "fi",
        "sudo systemctl enable docker || true",
        "sudo systemctl start docker || true",
        # Run node_exporter
        "echo 'Starting node_exporter (Docker)...'",
        "sudo docker rm -f node_exporter || true",
        "sudo docker run -d --name node_exporter --restart unless-stopped "
        "-p 9100:9100 prom/node-exporter",
        # Run Prometheus scraping localhost:9100
        "echo 'Starting Prometheus (Docker)...'",
        "sudo docker rm -f prometheus || true",
        "cat > prometheus.yml <<'EOF'",
        "global:",
        "  scrape_interval: 5s",
        "scrape_configs:",
        "  - job_name: 'node'",
        "    static_configs:",
        "      - targets: ['localhost:9100']",
        "EOF",
        "sudo docker run -d --name prometheus --restart unless-stopped "
        "-p 9090:9090 -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml "
        "prom/prometheus",
        "echo 'Prometheus/node_exporter setup complete.'",
    ]

    try:
        resp = ssm.send_command(
            InstanceIds=[target_id],
            DocumentName="AWS-RunShellScript",
            Parameters={"commands": commands},
        )
        command_id = resp["Command"]["CommandId"]
        logging.info(
            f"SSM command {command_id} sent to configure monitoring on instance {target_id}"
        )
    except Exception as e:
        logging.error(f"Failed to send SSM monitoring setup command to {target_id}: {e}")
        # Fail-safe: monitoring may be degraded, but scaling has already happened

