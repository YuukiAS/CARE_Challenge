#!/usr/bin/env python3
"""Watch M7 routing arrays and cancel the pending mirror once one starts."""

from __future__ import annotations

import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run_command(cmd: list[str], *, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(cmd, 124, (exc.stdout or "") + f"\nTIMEOUT after {timeout} seconds")


def job_lines(job_ids: list[str]) -> list[tuple[str, str, str, str]]:
    proc = run_command(["squeue", "-h", "-j", ",".join(job_ids), "-o", "%i|%P|%T|%R"])
    rows: list[tuple[str, str, str, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            rows.append((parts[0], parts[1], parts[2], parts[3]))
    return rows


def job_has_state(rows: list[tuple[str, str, str, str]], job_id: str, state: str) -> bool:
    return any(row_job.startswith(job_id) and row_state == state for row_job, _, row_state, _ in rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a100-job", default="58003931")
    parser.add_argument("--htzhulab-job", default="58003950")
    parser.add_argument("--interval-seconds", type=float, default=120.0)
    parser.add_argument("--max-iterations", type=int, default=1080)
    parser.add_argument("--log-file", required=True)
    args = parser.parse_args()

    log_path = Path(args.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    job_ids = [args.a100_job, args.htzhulab_job]
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"{now()} watcher_start a100={args.a100_job} htzhulab={args.htzhulab_job}\n")
        log.flush()
        for _ in range(args.max_iterations):
            log.write(f"{now()} poll_begin\n")
            log.flush()
            rows = job_lines(job_ids)
            snapshot = "; ".join("|".join(row) for row in rows) or "NO_ROWS"
            log.write(f"{now()} snapshot {snapshot}\n")
            log.flush()
            if job_has_state(rows, args.a100_job, "RUNNING"):
                proc = run_command(["scancel", args.htzhulab_job])
                log.write(f"{now()} a100_running_cancel_htzhulab exit={proc.returncode} output={proc.stdout.strip()}\n")
                return 0
            if job_has_state(rows, args.htzhulab_job, "RUNNING"):
                proc = run_command(["scancel", args.a100_job])
                log.write(f"{now()} htzhulab_running_cancel_a100 exit={proc.returncode} output={proc.stdout.strip()}\n")
                return 0
            if not rows:
                log.write(f"{now()} no_jobs_left\n")
                return 0
            time.sleep(args.interval_seconds)
        log.write(f"{now()} watcher_timeout_no_running_partition\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
