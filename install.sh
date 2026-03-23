#!/usr/bin/env bash
# Usage: bash install.sh
set -euo pipefail

SERVICE_USER="connectcatt"
PROJECT_ROOT="/opt/connectcatt"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/7] Installing system dependencies..."
sudo apt-get update -q
sudo apt-get install -y python3 python3-venv curl util-linux

echo "[2/7] Installing catt into venv..."
sudo python3 -m venv "$PROJECT_ROOT/venv"
sudo "$PROJECT_ROOT/venv/bin/pip" install --upgrade pip --quiet
sudo "$PROJECT_ROOT/venv/bin/pip" install catt --quiet

echo "[3/7] Creating service user..."
if ! id "$SERVICE_USER" &>/dev/null; then
  sudo useradd --system --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
else
  echo "  User '$SERVICE_USER' already exists, skipping."
fi

echo "[4/7] Creating directories..."
sudo mkdir -p "$PROJECT_ROOT/scripts" /var/log/connectcatt
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_ROOT" /var/log/connectcatt
sudo chmod 750 "$PROJECT_ROOT/venv" /var/log/connectcatt

echo "[5/7] Deploying cast script..."
sudo cp "$REPO_DIR/scripts/cast_dashboards.sh" "$PROJECT_ROOT/scripts/cast_dashboards.sh"
sudo chown "$SERVICE_USER:$SERVICE_USER" "$PROJECT_ROOT/scripts/cast_dashboards.sh"
sudo chmod 750 "$PROJECT_ROOT/scripts/cast_dashboards.sh"

echo "[6/7] Installing cron and logrotate..."
sudo cp "$REPO_DIR/deploy/connectcatt.cron" /etc/cron.d/connectcatt
sudo chmod 644 /etc/cron.d/connectcatt
sudo cp "$REPO_DIR/deploy/connectcatt.logrotate" /etc/logrotate.d/connectcatt
sudo chmod 644 /etc/logrotate.d/connectcatt

echo "[7/7] Deploying catt config..."
CATT_CFG_DIR="/home/$SERVICE_USER/.config/catt"
sudo mkdir -p "$CATT_CFG_DIR"
if [ ! -f "$CATT_CFG_DIR/catt.cfg" ]; then
  sudo cp "$REPO_DIR/deploy/catt.cfg.example" "$CATT_CFG_DIR/catt.cfg"
  sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$CATT_CFG_DIR"
  echo "  Config deployed. Edit $CATT_CFG_DIR/catt.cfg to match your device names (run 'catt ls' to find them)."
else
  echo "  Config already exists at $CATT_CFG_DIR/catt.cfg, skipping."
fi

echo ""
echo "Install complete."
echo ""
echo "Verify device names in $CATT_CFG_DIR/catt.cfg match 'catt ls' output, then test:"
echo "  sudo -u $SERVICE_USER $PROJECT_ROOT/scripts/cast_dashboards.sh"
