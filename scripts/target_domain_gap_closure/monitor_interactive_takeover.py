#!/usr/bin/env python3
"""Monitor the target-domain gap-closure interactive takeover loop."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260801_care_target_domain_race_gap_closure"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
RUNTIME_ROOT = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK_KEY


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{now()} {message}\n")


def squeue_state(job_id: str) -> str:
    proc = run(["squeue", "-h", "-j", job_id, "-o", "%T"])
    text = proc.stdout.strip()
    return text.splitlines()[0].strip() if text else "NOT_IN_SQUEUE"


def sacct_state(job_id: str) -> str:
    proc = run(["sacct", "-n", "-j", job_id, "--format=State", "-P"])
    states = [line.strip().split("|")[0] for line in proc.stdout.splitlines() if line.strip()]
    return states[0] if states else "NO_SACCT"


def pid_running(pid: int) -> bool:
    return run(["ps", "-p", str(pid), "-o", "pid="]).stdout.strip() != ""


def launch_m1(interactive_job_id: str, log_path: Path) -> tuple[int | None, str]:
    launch_log = RUNTIME_ROOT / "logs/m1_lane_interactive_61220581_launcher.log"
    cmd = [
        "setsid",
        "srun",
        f"--jobid={interactive_job_id}",
        "--overlap",
        "--ntasks=1",
        "--cpus-per-task=8",
        "--gres=gpu:1",
        "bash",
        "-lc",
        "cd /users/a/e/aereinh/CARE && bash jobs/target_domain_gap_closure/run_m1_myopsnet_l_care_lane.sh",
    ]
    with launch_log.open("ab") as out, open(os.devnull, "rb") as devnull:
        proc = subprocess.Popen(cmd, cwd=REPO_ROOT, stdin=devnull, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    append_log(log_path, f"launched M1 interactive takeover pid={proc.pid} log={launch_log}")
    return proc.pid, str(launch_log)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive-job-id", default="61220581")
    parser.add_argument("--m0r-interactive-pid", type=int, default=4039804)
    parser.add_argument("--m1-queue-job-id", default="61576324")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--max-polls", type=int, default=10000)
    args = parser.parse_args()

    log_path = RUNTIME_ROOT / "logs/interactive_takeover_monitor.log"
    state_path = RESULT_ROOT / "interactive_takeover_monitor_state.json"
    append_log(log_path, "monitor_start")
    for poll in range(args.max_polls):
        interactive_state = squeue_state(args.interactive_job_id)
        m1_state = squeue_state(args.m1_queue_job_id)
        m0r_running = pid_running(args.m0r_interactive_pid)
        state = {
            "created_at": now(),
            "interactive_job_id": args.interactive_job_id,
            "interactive_state": interactive_state,
            "m0r_interactive_pid": args.m0r_interactive_pid,
            "m0r_interactive_pid_running": m0r_running,
            "m1_queue_job_id": args.m1_queue_job_id,
            "m1_queue_state": m1_state,
            "poll": poll,
            "status": "MONITORING",
        }
        write_json(state_path, state)
        append_log(log_path, json.dumps(state, sort_keys=True))

        if m1_state in {"RUNNING", "COMPLETED"}:
            state["status"] = f"M1_QUEUE_{m1_state}_NO_TAKEOVER"
            write_json(state_path, state)
            append_log(log_path, state["status"])
            return 0

        if m1_state == "PENDING" and not m0r_running and interactive_state == "RUNNING":
            append_log(log_path, f"interactive free; cancelling pending M1 queue job {args.m1_queue_job_id}")
            cancel = run(["scancel", args.m1_queue_job_id])
            append_log(log_path, "scancel output=" + shlex.quote(cancel.stdout.strip()))
            terminal = "UNKNOWN"
            for _ in range(60):
                terminal = sacct_state(args.m1_queue_job_id)
                if "CANCELLED" in terminal:
                    break
                time.sleep(5)
            if "CANCELLED" not in terminal:
                state["status"] = "M1_CANCEL_ACCOUNTING_NOT_CONFIRMED"
                state["m1_sacct_state"] = terminal
                write_json(state_path, state)
                append_log(log_path, state["status"])
                return 2
            pid, launch_log = launch_m1(args.interactive_job_id, log_path)
            state.update(
                {
                    "status": "M1_INTERACTIVE_TAKEOVER_LAUNCHED",
                    "m1_sacct_state": terminal,
                    "m1_interactive_launcher_pid": pid,
                    "m1_interactive_launcher_log": launch_log,
                }
            )
            write_json(state_path, state)
            return 0

        time.sleep(args.poll_seconds)

    append_log(log_path, "monitor_max_polls_reached")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
