#!/usr/bin/env python3
"""Watch an M8 htzhulab/a100 race and cancel the still-pending mirror."""

from __future__ import annotations

import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path


def run(command: list[str]) -> tuple[int, str]:
    proc = subprocess.run(command, text=True, capture_output=True, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def states(job_id: str) -> list[tuple[str, str, str, str]]:
    code, out = run(["squeue", "-h", "-j", job_id, "-o", "%i|%P|%T|%R"])
    if code != 0:
        return [(job_id, "UNKNOWN", "SQUEUE_FAILED", out)]
    rows: list[tuple[str, str, str, str]] = []
    for line in out.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            rows.append((parts[0], parts[1], parts[2], parts[3]))
    return rows


def any_state(rows: list[tuple[str, str, str, str]], state: str) -> bool:
    return any(row[2] == state for row in rows)


def all_gone(rows: list[tuple[str, str, str, str]]) -> bool:
    return not rows


def log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--htzhulab-job-id", required=True)
    parser.add_argument("--a100-job-id", required=True)
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--check-interval-seconds", type=int, default=120)
    parser.add_argument("--max-checks", type=int, default=720)
    args = parser.parse_args()

    log_path = Path(args.log_path)
    log(log_path, f"watch_start htzhulab={args.htzhulab_job_id} a100={args.a100_job_id}")
    for check_idx in range(1, args.max_checks + 1):
        h_rows = states(args.htzhulab_job_id)
        a_rows = states(args.a100_job_id)
        log(log_path, f"check={check_idx} htzhulab={h_rows} a100={a_rows}")
        h_running = any_state(h_rows, "RUNNING")
        a_running = any_state(a_rows, "RUNNING")
        h_pending = any_state(h_rows, "PENDING")
        a_pending = any_state(a_rows, "PENDING")
        if h_running and a_pending and not a_running:
            code, out = run(["scancel", args.a100_job_id])
            log(log_path, f"cancel_a100 code={code} output={out}")
            return
        if a_running and h_pending and not h_running:
            code, out = run(["scancel", args.htzhulab_job_id])
            log(log_path, f"cancel_htzhulab code={code} output={out}")
            return
        if h_running and a_running:
            log(log_path, "both_partitions_running manual_intervention_required")
            return
        if all_gone(h_rows) and all_gone(a_rows):
            log(log_path, "both_jobs_gone watcher_exit")
            return
        time.sleep(max(1, args.check_interval_seconds))
    log(log_path, "max_checks_reached no_cancellation")


if __name__ == "__main__":
    main()
