# Cloud Autoscaler

An AI-powered cloud resource autoscaler that uses machine learning to predict CPU usage and automatically scales EC2 instances based on predicted workload. The system fetches metrics from Prometheus, uses XGBoost for CPU prediction, and applies intelligent scaling policies to optimize resource allocation.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation with UV Package Manager](#installation-with-uv-package-manager)
- [EC2 Instance Setup](#ec2-instance-setup)
- [SSM IAM Role Setup](#ssm-iam-role-setup)
- [Monitoring Setup](#monitoring-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)

## Prerequisites

Before setting up the project, ensure you have:

- **Python 3.12+** installed
- **UV Package Manager** installed ([Installation Guide](https://github.com/astral-sh/uv))
- **AWS Account** with appropriate permissions
- **EC2 Instance** running Ubuntu/Debian (for monitoring setup)
- **AWS CLI** configured with credentials
- **IAM Permissions** for:
  - EC2 instance management (start, stop, modify instance type)
  - SSM (Systems Manager) access
  - CloudWatch (optional, for additional monitoring)

## Installation with UV Package Manager

### 1. Install UV Package Manager

If you haven't installed UV yet, run:

```bash
# On Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

### 2. Clone and Navigate to Project

```bash
cd "/home/ghost/Desktop/Cloud Autoscaler"
```

### 3. Create Virtual Environment with UV

UV can automatically create and manage virtual environments:

```bash
# Create virtual environment and install dependencies
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On Linux/macOS
# or
.venv\Scripts\activate  # On Windows
```

### 4. Install Dependencies

Using UV to install from requirements.txt:

```bash
uv pip install -r requirements.txt
```

Alternatively, you can use UV's native dependency management:

```bash
# Sync dependencies (if using pyproject.toml)
uv sync

# Or install directly
uv pip install fastapi uvicorn numpy pandas joblib scikit-learn xgboost tensorflow boto3 python-dotenv requests
```

### 5. Verify Installation

```bash
python -c "import fastapi, boto3, xgboost; print('All dependencies installed successfully!')"
```

## EC2 Instance Setup

### 1. Launch EC2 Instance

1. Log in to the AWS Console
2. Navigate to **EC2 Dashboard** → **Launch Instance**
3. Configure the instance:
   - **AMI**: Choose Ubuntu Server 22.04 LTS or Debian 11+
   - **Instance Type**: Start with `t2.small` (will be auto-scaled by the system)
   - **Key Pair**: Create or select an existing key pair for SSH access
   - **Network Settings**: 
     - Allow SSH (port 22) from your IP
     - Allow HTTP (port 80) and HTTPS (port 443) if needed
     - **Important**: Allow inbound traffic on ports:
       - **9100** (node_exporter metrics)
       - **9090** (Prometheus UI)
   - **Storage**: Configure as needed (minimum 8GB recommended)
   - **Security Group**: Create or use existing security group

4. Click **Launch Instance**

### 2. Note Instance Details

After launching, note down:
- **Instance ID** (e.g., `i-011239a2a67407e92`)
- **Instance Type** (should be `t2.small` initially)
- **Region** (e.g., `ap-south-1`)
- **Public IP** or **Public DNS**

### 3. Update Configuration

Edit `aws/aws_config.py` and update:

```python
AWS_REGION = "ap-south-1"  # Your AWS region
INSTANCE_ID = "i-011239a2a67407e92"  # Your instance ID
INSTANCE_SEQUENCE = [
    "t2.small",
    "t2.medium",
    "t2.large"
]
```

### 4. Configure AWS Credentials

Ensure AWS credentials are configured:

```bash
# Option 1: AWS CLI configuration
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-south-1

# Option 3: Using .env file (create .env in project root)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-south-1
```

## SSM IAM Role Setup

The autoscaler uses AWS Systems Manager (SSM) to remotely configure monitoring on EC2 instances. You need to attach an IAM role with SSM permissions to your EC2 instance.

### 1. Create IAM Role for EC2 Instance

1. Go to **IAM Console** → **Roles** → **Create Role**
2. Select **AWS Service** → **EC2** → **Next**
3. Attach the following policies:
   - **AmazonSSMManagedInstanceCore** (required for SSM)
   - **CloudWatchAgentServerPolicy** (optional, for enhanced monitoring)
4. Name the role: `EC2-SSM-Role` (or your preferred name)
5. Click **Create Role**

### 2. Attach IAM Role to EC2 Instance

**Option A: During Instance Launch**
- In the **Launch Instance** wizard, go to **Advanced Details**
- Under **IAM instance profile**, select the role you created

**Option B: Attach to Existing Instance**
1. Go to **EC2 Console** → Select your instance
2. Click **Actions** → **Security** → **Modify IAM role**
3. Select your IAM role (e.g., `EC2-SSM-Role`)
4. Click **Update IAM role**

### 3. Verify SSM Connection

After attaching the role, wait 1-2 minutes for SSM agent to register, then verify:

```bash
# List instances managed by SSM
aws ssm describe-instance-information --region ap-south-1

# You should see your instance ID in the output
```

### 4. Test SSM Command (Optional)

Test that SSM is working:

```bash
aws ssm send-command \
    --instance-ids i-011239a2a67407e92 \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["echo Hello from SSM"]' \
    --region ap-south-1
```

## Monitoring Setup

The project includes a monitoring setup script that installs Prometheus and node_exporter on your EC2 instance. The script is located at `ec2/setup-monitoring.sh`.

### Automated Setup (Recommended)

The monitoring setup is automatically triggered after a successful instance scaling operation. The system uses SSM to execute the setup script remotely.

### Manual Setup

If you need to set up monitoring manually:

1. **Transfer the script to your EC2 instance:**

```bash
# Using SCP
scp -i your-key.pem ec2/setup-monitoring.sh ubuntu@your-instance-ip:/tmp/

# Or using SSM Session Manager
aws ssm start-session --target i-011239a2a67407e92 --region ap-south-1
```

2. **SSH into your instance:**

```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

3. **Run the setup script:**

```bash
sudo bash /tmp/setup-monitoring.sh
```

The script will:
- Install node_exporter (exposes metrics on port 9100)
- Install Prometheus (scrapes node_exporter on port 9090)
- Configure both services to run as systemd services
- Set up automatic startup on boot

### Verify Monitoring

After setup, verify the services are running:

```bash
# Check node_exporter
curl http://localhost:9100/metrics | head

# Check Prometheus
curl http://localhost:9090/-/ready

# View Prometheus UI (if security group allows)
# Open browser: http://your-instance-ip:9090
```

### Accessing Metrics

- **node_exporter metrics**: `http://your-instance-ip:9100/metrics`
- **Prometheus UI**: `http://your-instance-ip:9090`
- **Prometheus targets**: `http://your-instance-ip:9090/targets`

**Note**: Ensure your EC2 security group allows inbound traffic on ports 9100 and 9090 from your IP or the autoscaler's IP.

## Configuration

### Environment Variables

Create a `.env` file in the project root (optional):

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-south-1

# Application Settings
DRY_RUN=True  # Set to False to enable actual scaling
```

### Application Configuration

Edit `backend/config.py` to customize scaling behavior:

```python
SCALE_UP_CPU = 75.0      # Scale up if predicted CPU > 75%
SCALE_DOWN_CPU = 30.0    # Scale down if predicted CPU < 30%
MIN_CONFIDENCE = 0.6     # Minimum confidence required for scaling
COOLDOWN_SECONDS = 600   # 10 minutes cooldown between scaling actions
```

### AWS Configuration

Edit `aws/aws_config.py`:

```python
AWS_REGION = "ap-south-1"
INSTANCE_ID = "i-011239a2a67407e92"  # Your instance ID
INSTANCE_SEQUENCE = [
    "t2.small",
    "t2.medium",
    "t2.large"
]
```

## Running the Application

### 1. Start the FastAPI Server

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the server
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: `http://localhost:8000`
- **Health Check**: `http://localhost:8000/health`
- **Autoscale Endpoint**: `http://localhost:8000/autoscale`
- **API Docs**: `http://localhost:8000/docs`

### 2. Run the Autoscaler Daemon

In a separate terminal:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the daemon
python backend/autoscaler_deamon.py
```

The daemon will:
- Call the `/autoscale` endpoint every 5 minutes (configurable)
- Display scaling decisions and actions
- Log all activities to `logs/autoscaler.log`

### 3. Test the System

```bash
# Test health endpoint
curl http://localhost:8000/health

# Trigger manual autoscaling
curl http://localhost:8000/autoscale
```

### 4. Monitor Logs

```bash
# View autoscaler logs
tail -f logs/autoscaler.log

# Or view in real-time
watch -n 1 'tail -20 logs/autoscaler.log'
```

## Project Structure

```
Cloud Autoscaler/
├── artifacts/              # Trained ML models
├── aws/                    # AWS integration
│   ├── aws_config.py      # AWS configuration
│   ├── ec2_controller.py  # EC2 scaling logic
│   └── monitoring_setup.py # SSM-based monitoring setup
├── backend/               # Main application
│   ├── main.py           # FastAPI application
│   ├── config.py         # Application configuration
│   └── autoscaler_deamon.py # Daemon process
├── data/                  # Data processing
│   └── fetch_live_metrics.py # Prometheus metrics fetcher
├── decision/              # Scaling decision logic
│   └── scaling_policy.py # Decision-making policies
├── ec2/                   # EC2 setup scripts
│   └── setup-monitoring.sh # Monitoring installation script
├── ml/                    # Machine learning
│   ├── inference.py      # CPU prediction
│   ├── feature_builder.py # Feature engineering
│   └── load_models.py    # Model loading utilities
├── logs/                  # Application logs
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Important Notes

1. **Dry Run Mode**: By default, the system runs in dry-run mode. Set `DRY_RUN=False` in your environment or `backend/config.py` to enable actual scaling.

2. **Instance State**: The autoscaler will automatically stop the instance before scaling (changing instance type requires the instance to be stopped).

3. **Cooldown Period**: The system enforces a 10-minute cooldown between scaling actions to prevent thrashing.

4. **Monitoring**: Ensure Prometheus and node_exporter are running on your EC2 instance before the autoscaler can fetch metrics.

5. **Security**: Keep your AWS credentials secure. Never commit `.env` files or credentials to version control.

6. **Costs**: Be aware of EC2 instance costs. The autoscaler will scale up/down based on predicted CPU usage, which may increase your AWS bill.

## Troubleshooting

### SSM Connection Issues

- Verify IAM role is attached to the instance
- Check that SSM agent is running: `sudo systemctl status amazon-ssm-agent`
- Ensure security group allows outbound HTTPS (port 443) for SSM communication

### Monitoring Not Working

- Check if ports 9100 and 9090 are open in security group
- Verify services are running: `sudo systemctl status node_exporter prometheus`
- Check Prometheus targets: `http://your-instance-ip:9090/targets`

### Scaling Failures

- Ensure instance is in a state that allows modification (stopped)
- Check IAM permissions for EC2 modify operations
- Review logs: `tail -f logs/autoscaler.log`

## License

[Add your license information here]

## Contributing

[Add contribution guidelines if applicable]
