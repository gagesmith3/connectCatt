#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if [[ ! -f "$VENV_DIR/bin/python" ]]; then
  echo "Virtual environment not found at $VENV_DIR"
  echo "Run ./install.sh first."
  exit 1
fi

mkdir -p "$ROOT_DIR/logs"

source "$VENV_DIR/bin/activate"
exec "$VENV_DIR/bin/python" "$ROOT_DIR/launch_casts.py"
