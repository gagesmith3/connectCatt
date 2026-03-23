#!/usr/bin/env bash
set -euo pipefail

# Installs and configures connectcatt automation on Ubuntu.

SERVICE_USER="connectcatt"
PROJECT_ROOT="/opt/connectcatt"
SCRIPT_SRC="./scripts/cast_dashboards.sh"
CRON_SRC="./deploy/connectcatt.cron"
LOGROTATE_SRC="./deploy/connectcatt.logrotate"
GITHUB_RAW_BASE="${GITHUB_RAW_BASE:-}"
TMP_DIR=""

cleanup() {
  if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
    rm -rf "$TMP_DIR"
  fi
}

trap cleanup EXIT

fetch_from_github_if_missing() {
  local local_path="$1"
  local remote_suffix="$2"

  if [ -f "$local_path" ]; then
    return 0
  fi

  if [ -z "$GITHUB_RAW_BASE" ]; then
    echo "Missing file: $local_path"
    echo "Set GITHUB_RAW_BASE, for example:"
    echo "  export GITHUB_RAW_BASE=https://raw.githubusercontent.com/<owner>/<repo>/<branch>"
    exit 1
  fi

  if [ -z "$TMP_DIR" ]; then
    TMP_DIR="$(mktemp -d)"
  fi

  local destination="$TMP_DIR/$(basename "$local_path")"
  local remote_url="${GITHUB_RAW_BASE%/}/${remote_suffix}"

  echo "Downloading $remote_url"
  curl --fail --silent --show-error --location "$remote_url" -o "$destination"

  case "$local_path" in
    *cast_dashboards.sh)
      SCRIPT_SRC="$destination"
      ;;
    *connectcatt.cron)
      CRON_SRC="$destination"
      ;;
    *connectcatt.logrotate)
      LOGROTATE_SRC="$destination"
      ;;
  esac
}

fetch_from_github_if_missing "$SCRIPT_SRC" "scripts/cast_dashboards.sh"
fetch_from_github_if_missing "$CRON_SRC" "deploy/connectcatt.cron"
fetch_from_github_if_missing "$LOGROTATE_SRC" "deploy/connectcatt.logrotate"

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
