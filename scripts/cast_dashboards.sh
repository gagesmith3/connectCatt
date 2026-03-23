#!/usr/bin/env bash
set -u

# ConnectCatt dashboard casting automation.
# Casts different dashboard URLs to different Chromecast devices.

# Use catt from the project venv
export PATH="/opt/connectcatt/venv/bin:$PATH"

LOG_DIR="/var/log/connectcatt"
LOG_FILE="$LOG_DIR/cast.log"
LOCK_FILE="/tmp/connectcatt-cast.lock"

# Retry behavior
MAX_ATTEMPTS=3
RETRY_DELAY_SECONDS=8

# Connection checks
DEVICE_STATUS_TIMEOUT=12
CAST_TIMEOUT=35
URL_CHECK_TIMEOUT=10

# TV -> URL mapping
# IMPORTANT: aliases must exist in catt config or be resolvable device names.
declare -A TV_URLS=(
  [equipment]="http://192.168.1.6:8080/EQUIP/equipment-tv.php"
  [secondary]="http://192.168.1.6:8080/SECONDARY/TrimmingDashboard.php"
)

log() {
  local level="$1"
  local message="$2"
  mkdir -p "$LOG_DIR"
  printf '%s [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$message" | tee -a "$LOG_FILE"
}

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log "ERROR" "Required command not found: $cmd"
    return 1
  fi
}

check_url() {
  local url="$1"
  if curl --fail --silent --show-error --max-time "$URL_CHECK_TIMEOUT" "$url" >/dev/null; then
    return 0
  fi
  return 1
}

check_device_ready() {
  local device="$1"
  if timeout "$DEVICE_STATUS_TIMEOUT" catt -d "$device" status >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

cast_with_retry() {
  local device="$1"
  local url="$2"

  local attempt=1
  while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
    log "INFO" "Attempt $attempt/$MAX_ATTEMPTS for $device -> $url"

    if ! check_device_ready "$device"; then
      log "WARN" "Device status check failed for $device"
    else
      if timeout "$CAST_TIMEOUT" catt -d "$device" cast_site "$url" >/dev/null 2>&1; then
        log "INFO" "Cast succeeded for $device"
        return 0
      fi
      log "WARN" "Cast command failed for $device"
    fi

    if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
      log "INFO" "Retrying $device in ${RETRY_DELAY_SECONDS}s"
      sleep "$RETRY_DELAY_SECONDS"
    fi

    attempt=$((attempt + 1))
  done

  log "ERROR" "Cast failed after $MAX_ATTEMPTS attempts for $device"
  return 1
}

main() {
  local overall_status=0

  mkdir -p "$LOG_DIR"

  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    log "WARN" "Another connectcatt run is active; exiting"
    exit 0
  fi

  log "INFO" "Run started"

  require_command catt || exit 2
  require_command curl || exit 2
  require_command timeout || exit 2
  require_command flock || exit 2

  local device
  for device in "${!TV_URLS[@]}"; do
    local url="${TV_URLS[$device]}"

    if ! check_url "$url"; then
      log "ERROR" "URL unreachable for $device: $url"
      overall_status=1
      continue
    fi

    if ! cast_with_retry "$device" "$url"; then
      overall_status=1
    fi
  done

  if [ "$overall_status" -eq 0 ]; then
    log "INFO" "Run completed successfully"
  else
    log "ERROR" "Run completed with failures"
  fi

  exit "$overall_status"
}

main "$@"
