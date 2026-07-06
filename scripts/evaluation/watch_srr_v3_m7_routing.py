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


def all_jobs_pending(rows: list[tuple[str, str, str, str]], job_ids: list[str]) -> bool:
    if not rows:
        return False
    return all(any(row_job.startswith(job_id) and row_state == "PENDING" for row_job, _, row_state, _ in rows) for job_id in job_ids)


def read_pending_streak(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return 0


def write_pending_streak(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{value}\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a100-job", default="58003931")
    parser.add_argument("--htzhulab-job", default="58003950")
    parser.add_argument("--interval-seconds", type=float, default=7200.0)
    parser.add_argument("--max-iterations", type=int, default=1080)
    parser.add_argument("--pending-block-threshold", type=int, default=12)
    parser.add_argument("--pending-streak-file", default="results/20260705_srr_v3_m7_training_and_cine_utilization/runtime/routing_locks/pending_streak.txt")
    parser.add_argument("--log-file", required=True)
    args = parser.parse_args()

    log_path = Path(args.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    streak_path = Path(args.pending_streak_file)
    job_ids = [args.a100_job, args.htzhulab_job]
    with log_path.open("a", encoding="utf-8") as log:
        log.write(
            f"{now()} watcher_start a100={args.a100_job} htzhulab={args.htzhulab_job} "
            f"interval_seconds={args.interval_seconds:g} pending_block_threshold={args.pending_block_threshold}\n"
        )
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
            if all_jobs_pending(rows, job_ids):
                streak = read_pending_streak(streak_path) + 1
                write_pending_streak(streak_path, streak)
                log.write(f"{now()} all_routing_partitions_pending_streak={streak}/{args.pending_block_threshold}\n")
                if streak >= args.pending_block_threshold:
                    log.write(f"{now()} block_allowed_by_pending_policy=true\n")
                log.flush()
            else:
                write_pending_streak(streak_path, 0)
                log.write(f"{now()} pending_streak_reset_non_pending_state\n")
                log.flush()
            time.sleep(args.interval_seconds)
        log.write(f"{now()} watcher_timeout_no_running_partition\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
