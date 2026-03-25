#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

import launch_casts


def parse_scan_output(output: str) -> list[str]:
    devices: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # catt scan often prints plain names; keep parser permissive.
        line = line.lstrip("*- ").strip()
        if not line:
            continue

        if line not in devices:
            devices.append(line)
    return devices


def choose_index(prompt: str, count: int) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.lower() in {"q", "quit", "exit"}:
            raise KeyboardInterrupt
        if not raw.isdigit():
            print("Enter a number from the list, or q to quit.")
            continue
        idx = int(raw)
        if idx < 1 or idx > count:
            print(f"Choose a value between 1 and {count}.")
            continue
        return idx - 1


def main() -> int:
    load_dotenv()

    try:
        jobs = launch_casts.load_jobs()
    except Exception as exc:
        print(f"Failed to load jobs: {exc}")
        return 2

    try:
        catt_path = launch_casts.require_command(
            "catt",
            "Install it in the active environment with 'pip install catt' or ensure it is on PATH.",
        )
    except Exception as exc:
        print(exc)
        return 2

    timeout = int(os.getenv("CAST_MANUAL_SCAN_TIMEOUT_SECONDS", "20"))

    print("Scan: looking for Chromecast devices...")
    scan_result = launch_casts.run_subprocess([catt_path, "scan"], timeout)
    scan_text = f"{scan_result.stdout}\n{scan_result.stderr}".strip()
    scanned_devices = parse_scan_output(scan_text)

    if scanned_devices:
        print("\nSelect device:")
        for idx, device in enumerate(scanned_devices, start=1):
            print(f"{idx}. {device}")
        selected_device = scanned_devices[choose_index("Device number: ", len(scanned_devices))]
    else:
        print("No devices found from scan output. Falling back to devices from config.")
        config_devices = sorted({job.device for job in jobs})
        if not config_devices:
            print("No devices in config either; cannot continue.")
            return 2
        print("\nSelect device:")
        for idx, device in enumerate(config_devices, start=1):
            print(f"{idx}. {device}")
        selected_device = config_devices[choose_index("Device number: ", len(config_devices))]

    print("\nSelect cast target (URL/job):")
    for idx, job in enumerate(jobs, start=1):
        print(f"{idx}. {job.name} [{job.time_hhmm}] -> {job.url}")
    selected_job = jobs[choose_index("Job number: ", len(jobs))]

    manual_job = launch_casts.CastJob(
        name=f"Manual: {selected_job.name}",
        device=selected_device,
        url=selected_job.url,
        time_hhmm="00:00",
        timeout_seconds=selected_job.timeout_seconds,
        retries=selected_job.retries,
    )

    print(f"\nCasting now: {manual_job.url} -> {manual_job.device}")
    try:
        ok = launch_casts.execute_job(manual_job)
    except KeyboardInterrupt:
        print("Cancelled.")
        return 130

    if not ok:
        print("Manual cast failed.")
        return 1

    print("Manual cast complete.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
