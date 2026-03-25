#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required but not installed."
  exit 1
}

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "Created .env from .env.example"
fi

mkdir -p "$ROOT_DIR/config" "$ROOT_DIR/logs"

if [[ ! -f "$ROOT_DIR/config/cast_jobs.json" ]]; then
  cp "$ROOT_DIR/config/cast_jobs.example.json" "$ROOT_DIR/config/cast_jobs.json"
  echo "Created config/cast_jobs.json from example"
fi

chmod +x "$ROOT_DIR/install.sh" "$ROOT_DIR/run.sh" "$ROOT_DIR/run_force_cast.sh"

echo "Install complete."
echo "Next steps:"
echo "1) Edit .env"
echo "2) Edit config/cast_jobs.json"
echo "3) Run ./run.sh"
echo "4) Manual cast workflow: ./run_force_cast.sh"
