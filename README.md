# connectCatt

A TV dashboard scheduler for Ubuntu/Linux focused on Chromecast devices via `catt`.

## Repo Layout

- `launch_casts.py`: Scheduler runtime.
- `install.sh`: One-time setup script (venv, dependencies, `.env`, sample jobs file).
- `run.sh`: Starts the scheduler with the project virtual environment.
- `.env.example`: Environment template copied to `.env` on install.
- `config/cast_jobs.example.json`: Sample schedule copied to `config/cast_jobs.json` on install.

## Quick Start (Ubuntu)

```bash
git clone <YOUR_REPO_URL>
cd connectCatt
chmod +x install.sh run.sh
./install.sh
```

After install:

1. Edit `.env`
2. Edit `config/cast_jobs.json`
3. Start with `./run.sh`

## Environment

`install.sh` creates `.env` from `.env.example` if missing.

Default `.env` values:

- `CAST_CHECK_INTERVAL_SECONDS=20`
- `CAST_STATE_FILE=cast_scheduler_state.json`
- `CAST_JOBS_FILE=config/cast_jobs.json`
- `CAST_JOBS=` (optional inline JSON alternative)

Use either:

- `CAST_JOBS_FILE` (recommended), or
- `CAST_JOBS` as JSON string.

## Job Config

`config/cast_jobs.json` must be a JSON array. Example item:

```json
{
  "name": "Equipment Dashboard",
  "target_type": "chromecast",
  "device": "equipment-tv",
  "url": "http://192.168.1.6:8080/EQUIP/equipment-tv.php",
  "time": "07:55"
}
```

Supported fields:

- `name`: Friendly log name.
- `target_type`: `chromecast` (or omit it; Chromecast is the default).
- `device`: Chromecast device name.
- `url`: URL to open.
- `time`: `HH:MM` 24-hour.
- `timeout_seconds`: Optional, minimum `5`.
- `retries`: Optional, minimum `1`.

## Optional Systemd Service

Copy and edit the sample service:

```bash
sudo cp deploy/connectcatt.service /etc/systemd/system/connectcatt.service
sudo systemctl daemon-reload
sudo systemctl enable --now connectcatt
sudo systemctl status connectcatt
```

## External Dependencies

Python dependencies are installed by `install.sh`:

- Chromecast: `catt` (installed via pip).

Note: device names in `config/cast_jobs.json` must match what `catt` sees on the network.

## Logs and State

- Logs are printed to stdout/stderr (systemd captures them with `journalctl`).
- State file defaults to `cast_scheduler_state.json` to avoid duplicate runs in the same day.
