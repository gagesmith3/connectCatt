#!/usr/bin/env python3
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


SUPPORTED_TARGET_TYPES = {"chromecast"}


@dataclass
class CastJob:
    name: str
    device: str
    url: str
    time_hhmm: str
    target_type: str = "chromecast"
    timeout_seconds: int = 25
    retries: int = 1

    def target_label(self) -> str:
        return self.device


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def normalize_target_type(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "": "chromecast",
        "cast": "chromecast",
        "google_cast": "chromecast",
        "googlecast": "chromecast",
    }
    result = aliases.get(normalized, normalized)
    if result not in SUPPORTED_TARGET_TYPES:
        supported = ", ".join(sorted(SUPPORTED_TARGET_TYPES))
        raise ValueError(f"Unsupported target_type '{value}'. Expected one of: {supported}")
    return result


def clean_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def validate_hhmm(value: str) -> None:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {value}. Expected HH:MM")
    hour, minute = parts
    if not (hour.isdigit() and minute.isdigit()):
        raise ValueError(f"Invalid time format: {value}. Expected HH:MM")
    h = int(hour)
    m = int(minute)
    if h < 0 or h > 23 or m < 0 or m > 59:
        raise ValueError(f"Invalid time value: {value}. Expected 00:00-23:59")


def build_job_from_mapping(item: dict[str, object], idx: int) -> CastJob:
    target_type = normalize_target_type(str(item.get("target_type", item.get("platform", "chromecast"))))
    device = str(item.get("device", "")).strip()
    url = str(item.get("url", "")).strip()
    time_hhmm = str(item.get("time", "")).strip()
    name = str(item.get("name", f"Dashboard #{idx}")).strip() or f"Dashboard #{idx}"
    timeout_seconds = int(item.get("timeout_seconds", 25))
    retries = int(item.get("retries", 1))

    if not url or not time_hhmm:
        raise ValueError(f"CAST_JOBS item {idx} is missing url/time fields")

    validate_hhmm(time_hhmm)

    if target_type != "chromecast":
        raise ValueError(f"CAST_JOBS item {idx} target_type must be 'chromecast'")
    if not device:
        raise ValueError(f"CAST_JOBS item {idx} is missing a Chromecast device name")

    return CastJob(
        name=name,
        device=device,
        url=url,
        time_hhmm=time_hhmm,
        target_type=target_type,
        timeout_seconds=max(5, timeout_seconds),
        retries=max(1, retries),
    )


def load_jobs_from_json(raw: str, source_label: str) -> list[CastJob]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source_label} must be valid JSON: {exc}") from exc

    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{source_label} must be a non-empty JSON list")

    jobs: list[CastJob] = []
    for idx, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{source_label} item {idx} must be an object")
        jobs.append(build_job_from_mapping(item, idx))
    return jobs


def load_jobs() -> list[CastJob]:
    jobs_file = os.getenv("CAST_JOBS_FILE", "").strip()
    if jobs_file:
        path = Path(jobs_file)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent / path
        if not path.exists():
            raise ValueError(f"CAST_JOBS_FILE does not exist: {path}")
        raw = path.read_text(encoding="utf-8")
        return load_jobs_from_json(raw, f"CAST_JOBS_FILE ({path})")

    raw = os.getenv("CAST_JOBS", "").strip()
    if raw:
        return load_jobs_from_json(raw, "CAST_JOBS")

    raise ValueError("Set CAST_JOBS_FILE or CAST_JOBS in .env")


def get_state_path() -> Path:
    raw = os.getenv("CAST_STATE_FILE", "cast_scheduler_state.json")
    path = Path(raw)
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parent / path).resolve()


def load_state(state_path: Path) -> dict[str, str]:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logging.warning("State file invalid or unreadable. Resetting state.")
        return {}


def save_state(state_path: Path, state: dict[str, str]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def require_command(command_name: str, install_hint: str) -> str:
    command_path = shutil.which(command_name)
    if not command_path:
        raise RuntimeError(f"Required command '{command_name}' was not found. {install_hint}")
    return command_path


def run_subprocess(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )


def raise_for_failed_command(completed: subprocess.CompletedProcess[str], fallback: str) -> None:
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        details = stderr or stdout or fallback
        raise RuntimeError(details)


def run_chromecast_cast_site(job: CastJob) -> None:
    catt_path = require_command(
        "catt",
        "Install it in the active environment with 'pip install catt' or ensure it is on PATH.",
    )
    command = [catt_path, "-d", job.device, "cast_site", job.url]
    logging.info("Casting [%s] via Chromecast to [%s]: %s", job.name, job.target_label(), job.url)
    completed = run_subprocess(command, job.timeout_seconds)
    raise_for_failed_command(completed, "No output from catt")


def run_cast_site(job: CastJob) -> None:
    run_chromecast_cast_site(job)


def run_chromecast_stop(device: str, timeout_seconds: int) -> None:
    catt_path = require_command(
        "catt",
        "Install it in the active environment with 'pip install catt' or ensure it is on PATH.",
    )
    command = [catt_path, "-d", device, "stop"]
    logging.info("Stopping Chromecast device [%s]", device)
    completed = run_subprocess(command, timeout_seconds)
    raise_for_failed_command(completed, "No output from catt stop")


def should_run_now(current_dt: datetime, target_hhmm: str, last_run_date: str | None) -> bool:
    today = current_dt.strftime("%Y-%m-%d")
    now_hhmm = current_dt.strftime("%H:%M")
    return now_hhmm >= target_hhmm and last_run_date != today


def get_state_key(job: CastJob) -> str:
    return f"{job.target_type}|{job.target_label()}|{job.url}|{job.time_hhmm}"


def get_stop_state_key(device: str, stop_time_hhmm: str) -> str:
    return f"stop|chromecast|{device}|{stop_time_hhmm}"


def execute_job(job: CastJob) -> bool:
    for attempt in range(1, job.retries + 1):
        try:
            run_cast_site(job)
            return True
        except subprocess.TimeoutExpired:
            logging.error("Job [%s] timed out on attempt %s/%s", job.name, attempt, job.retries)
        except Exception as exc:
            logging.error("Job [%s] failed on attempt %s/%s: %s", job.name, attempt, job.retries, exc)
        if attempt < job.retries:
            time.sleep(2)
    return False


def execute_stop(device: str, timeout_seconds: int, retries: int) -> bool:
    for attempt in range(1, retries + 1):
        try:
            run_chromecast_stop(device, timeout_seconds)
            return True
        except subprocess.TimeoutExpired:
            logging.error("Stop for [%s] timed out on attempt %s/%s", device, attempt, retries)
        except Exception as exc:
            logging.error("Stop for [%s] failed on attempt %s/%s: %s", device, attempt, retries, exc)
        if attempt < retries:
            time.sleep(2)
    return False


def process_jobs(
    jobs: list[CastJob],
    state_path: Path,
    stop_time_hhmm: str | None,
    stop_timeout_seconds: int,
    stop_retries: int,
) -> None:
    state = load_state(state_path)
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    due_jobs: list[CastJob] = []

    for job in jobs:
        state_key = get_state_key(job)
        last_run_date = state.get(state_key)
        if not should_run_now(now, job.time_hhmm, last_run_date):
            continue
        due_jobs.append(job)

    if due_jobs:
        logging.info("Dispatching %s due job(s) in parallel", len(due_jobs))
        with ThreadPoolExecutor(max_workers=len(due_jobs), thread_name_prefix="cast-job") as executor:
            future_to_job = {executor.submit(execute_job, job): job for job in due_jobs}
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                state_key = get_state_key(job)
                try:
                    success = future.result()
                except Exception as exc:
                    success = False
                    logging.error("Job [%s] crashed unexpectedly: %s", job.name, exc)

                if success:
                    state[state_key] = today
                    logging.info("Job [%s] completed for %s", job.name, today)
                else:
                    logging.error("Job [%s] did not complete today", job.name)

    if stop_time_hhmm:
        devices = sorted({job.device for job in jobs})
        due_stop_devices: list[str] = []

        for device in devices:
            stop_state_key = get_stop_state_key(device, stop_time_hhmm)
            last_stop_date = state.get(stop_state_key)
            if should_run_now(now, stop_time_hhmm, last_stop_date):
                due_stop_devices.append(device)

        if due_stop_devices:
            logging.info("Dispatching stop to %s Chromecast device(s)", len(due_stop_devices))
            with ThreadPoolExecutor(max_workers=len(due_stop_devices), thread_name_prefix="stop-job") as executor:
                future_to_device = {
                    executor.submit(execute_stop, device, stop_timeout_seconds, stop_retries): device
                    for device in due_stop_devices
                }
                for future in as_completed(future_to_device):
                    device = future_to_device[future]
                    stop_state_key = get_stop_state_key(device, stop_time_hhmm)
                    try:
                        success = future.result()
                    except Exception as exc:
                        success = False
                        logging.error("Stop for [%s] crashed unexpectedly: %s", device, exc)

                    if success:
                        state[stop_state_key] = today
                        logging.info("Stop completed for [%s] on %s", device, today)
                    else:
                        logging.error("Stop did not complete for [%s]", device)

    save_state(state_path, state)


def parse_interval_seconds() -> int:
    raw = os.getenv("CAST_CHECK_INTERVAL_SECONDS", "20").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("CAST_CHECK_INTERVAL_SECONDS must be an integer") from exc
    if value < 5:
        raise ValueError("CAST_CHECK_INTERVAL_SECONDS must be >= 5")
    return value


def parse_stop_time_hhmm() -> str | None:
    raw = os.getenv("CAST_STOP_TIME", "17:15").strip()
    if not raw:
        return None
    validate_hhmm(raw)
    return raw


def parse_stop_timeout_seconds() -> int:
    raw = os.getenv("CAST_STOP_TIMEOUT_SECONDS", "20").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("CAST_STOP_TIMEOUT_SECONDS must be an integer") from exc
    if value < 5:
        raise ValueError("CAST_STOP_TIMEOUT_SECONDS must be >= 5")
    return value


def parse_stop_retries() -> int:
    raw = os.getenv("CAST_STOP_RETRIES", "2").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("CAST_STOP_RETRIES must be an integer") from exc
    if value < 1:
        raise ValueError("CAST_STOP_RETRIES must be >= 1")
    return value


def main() -> int:
    load_dotenv()
    setup_logging()

    try:
        jobs = load_jobs()
        interval = parse_interval_seconds()
        stop_time_hhmm = parse_stop_time_hhmm()
        stop_timeout_seconds = parse_stop_timeout_seconds()
        stop_retries = parse_stop_retries()
        state_path = get_state_path()
    except Exception as exc:
        logging.error("Configuration error: %s", exc)
        return 2

    logging.info("Loaded %s cast job(s)", len(jobs))
    logging.info("State file: %s", state_path)
    logging.info("Checking every %s seconds", interval)
    if stop_time_hhmm:
        logging.info(
            "Daily stop enabled at %s (timeout=%ss, retries=%s)",
            stop_time_hhmm,
            stop_timeout_seconds,
            stop_retries,
        )
    else:
        logging.info("Daily stop is disabled")
    for job in jobs:
        logging.info(
            "Configured job [%s]: type=%s target=%s schedule=%s",
            job.name,
            job.target_type,
            job.target_label(),
            job.time_hhmm,
        )

    while True:
        process_jobs(jobs, state_path, stop_time_hhmm, stop_timeout_seconds, stop_retries)
        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
