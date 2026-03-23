#!/usr/bin/env bash
set -euo pipefail

# Installs and configures connectcatt automation on Ubuntu.

SERVICE_USER="connectcatt"
PROJECT_ROOT="/opt/connectcatt"
SCRIPT_SRC="./scripts/cast_dashboards.sh"
CRON_SRC="./deploy/connectcatt.cron"
LOGROTATE_SRC="./deploy/connectcatt.logrotate"

echo "[1/8] Installing dependencies"
sudo apt-get update
sudo apt-get install -y python3 python3-pip curl util-linux

echo "[2/8] Installing catt"
sudo python3 -m pip install --upgrade pip
sudo python3 -m pip install catt

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  echo "[3/8] Creating service user: $SERVICE_USER"
  sudo useradd --system --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
else
  echo "[3/8] Service user already exists: $SERVICE_USER"
fi

echo "[4/8] Creating directories"
sudo mkdir -p "$PROJECT_ROOT/scripts" /var/log/connectcatt
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$PROJECT_ROOT" /var/log/connectcatt
sudo chmod 750 /var/log/connectcatt

echo "[5/8] Deploying cast script"
sudo cp "$SCRIPT_SRC" "$PROJECT_ROOT/scripts/cast_dashboards.sh"
sudo chown "$SERVICE_USER":"$SERVICE_USER" "$PROJECT_ROOT/scripts/cast_dashboards.sh"
sudo chmod 750 "$PROJECT_ROOT/scripts/cast_dashboards.sh"

echo "[6/8] Deploying cron"
sudo cp "$CRON_SRC" /etc/cron.d/connectcatt
sudo sed -i "s#^55 7 \* \* 1-5 connectcatt /opt/connectcatt/scripts/cast_dashboards.sh#55 7 * * 1-5 $SERVICE_USER $PROJECT_ROOT/scripts/cast_dashboards.sh#" /etc/cron.d/connectcatt
sudo chmod 644 /etc/cron.d/connectcatt

echo "[7/8] Deploying logrotate"
sudo cp "$LOGROTATE_SRC" /etc/logrotate.d/connectcatt
sudo chmod 644 /etc/logrotate.d/connectcatt

echo "[8/8] Verifying cron file"
sudo run-parts --test /etc/cron.d >/dev/null

echo "Install complete."
echo "Next steps:"
echo "  1) Configure catt aliases as $SERVICE_USER (equipment, secondary)."
echo "  2) Run manual test: sudo -u $SERVICE_USER $PROJECT_ROOT/scripts/cast_dashboards.sh"
echo "  3) Check logs: sudo tail -f /var/log/connectcatt/cast.log"
