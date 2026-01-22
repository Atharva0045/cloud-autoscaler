#!/usr/bin/env bash
set -euo pipefail

# Native (non-Docker) install of:
# - node_exporter (systemd) on :9100
# - Prometheus (systemd) on :9090, scraping 127.0.0.1:9100
#
# Designed for Ubuntu/Debian with systemd.

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo $0"
  exit 1
fi

NODE_EXPORTER_VERSION="1.7.0"
PROMETHEUS_VERSION="2.49.1"

echo "=== Installing node_exporter v${NODE_EXPORTER_VERSION} and Prometheus v${PROMETHEUS_VERSION} (native) ==="

apt-get update -y
apt-get install -y curl tar gzip ca-certificates

# --- Users ---
id -u node_exporter >/dev/null 2>&1 || useradd --no-create-home --shell /usr/sbin/nologin node_exporter
id -u prometheus    >/dev/null 2>&1 || useradd --no-create-home --shell /usr/sbin/nologin prometheus

# --- Directories ---
mkdir -p /etc/prometheus /var/lib/prometheus
chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus

# --- Install node_exporter ---
echo "[1/4] Installing node_exporter..."
cd /tmp
curl -fsSLO "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar -xzf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
install -m 0755 "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" /usr/local/bin/node_exporter
rm -rf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64" "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"

cat >/etc/systemd/system/node_exporter.service <<'EOF'
[Unit]
Description=Prometheus Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

# --- Install Prometheus ---
echo "[2/4] Installing Prometheus..."
cd /tmp
curl -fsSLO "https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz"
tar -xzf "prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz"

install -m 0755 "prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus" /usr/local/bin/prometheus
install -m 0755 "prometheus-${PROMETHEUS_VERSION}.linux-amd64/promtool"   /usr/local/bin/promtool

mkdir -p /etc/prometheus/consoles /etc/prometheus/console_libraries
cp -r "prometheus-${PROMETHEUS_VERSION}.linux-amd64/consoles/."           /etc/prometheus/consoles/
cp -r "prometheus-${PROMETHEUS_VERSION}.linux-amd64/console_libraries/." /etc/prometheus/console_libraries/
chown -R prometheus:prometheus /etc/prometheus

rm -rf "prometheus-${PROMETHEUS_VERSION}.linux-amd64" "prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz"

# --- Prometheus config ---
echo "[3/4] Writing Prometheus config..."
cat >/etc/prometheus/prometheus.yml <<'EOF'
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "node"
    static_configs:
      - targets: ["127.0.0.1:9100"]
EOF

chown prometheus:prometheus /etc/prometheus/prometheus.yml

# --- Prometheus systemd service ---
cat >/etc/systemd/system/prometheus.service <<'EOF'
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus \
  --web.listen-address=0.0.0.0:9090

Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

# --- Enable and start services ---
echo "[4/4] Enabling and starting services..."
systemctl daemon-reload
systemctl enable --now node_exporter
systemctl enable --now prometheus

echo
echo "=== Done ==="
echo "node_exporter: http://localhost:9100/metrics"
echo "prometheus:    http://localhost:9090/"
echo "targets page:  http://localhost:9090/targets"
echo
echo "Quick checks:"
echo "  curl -s http://localhost:9100/metrics | head"
echo "  curl -s http://localhost:9090/-/ready ; echo"
echo "  curl -s http://localhost:9090/api/v1/targets | head -200"