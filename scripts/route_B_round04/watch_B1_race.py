#!/usr/bin/env python3
"""Watch the Route B Round04 B1 routing race and record controller state."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ROUND_ROOT = REPO_ROOT / "results" / "route_B" / "round04"
LEDGER = ROUND_ROOT / "controller_ledger.csv"
STATE = ROUND_ROOT / "b1_race_state.json"
B1_DIR = ROUND_ROOT / "executors" / "B1"
WINNER = REPO_ROOT / "results" / "route_B" / "runtime" / "round04" / "B1" / "B1_winner.lock" / "winner.txt"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_ledger(row: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    exists = LEDGER.is_file()
    fields = [
        "timestamp_utc",
        "phase",
        "git_head",
        "job_ids",
        "job_states",
        "decision",
        "next_action",
    ]
    with LEDGER.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fields})


def squeue_state(job_id: str) -> dict[str, str]:
    proc = run(["squeue", "-h", "-j", job_id, "-o", "%i|%P|%T|%M|%R|%S"])
    if proc.returncode == 0 and proc.stdout.strip():
        parts = proc.stdout.strip().splitlines()[0].split("|")
        return {
            "job_id": parts[0],
            "partition": parts[1],
            "state": parts[2],
            "time": parts[3],
            "reason": parts[4],
            "start_time": parts[5] if len(parts) > 5 else "",
        }
    sacct = run(["sacct", "-j", job_id, "--format=JobIDRaw,Partition,State,ExitCode,Elapsed,Start,End,NodeList", "-P", "-n"])
    if sacct.returncode == 0 and sacct.stdout.strip():
        line = sacct.stdout.strip().splitlines()[0]
        parts = line.split("|")
        return {
            "job_id": parts[0],
            "partition": parts[1] if len(parts) > 1 else "",
            "state": parts[2] if len(parts) > 2 else "UNKNOWN",
            "exit_code": parts[3] if len(parts) > 3 else "",
            "elapsed": parts[4] if len(parts) > 4 else "",
            "start": parts[5] if len(parts) > 5 else "",
            "end": parts[6] if len(parts) > 6 else "",
            "node": parts[7] if len(parts) > 7 else "",
        }
    return {"job_id": job_id, "state": "UNKNOWN"}


def completion_pass() -> bool:
    path = B1_DIR / "completion.json"
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return payload.get("completion_token") == "ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_IMPLEMENTED" and payload.get("status") == "PASS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", action="append", required=True, help="partition:jobid")
    parser.add_argument("--poll-seconds", type=int, default=300)
    args = parser.parse_args()
    jobs = dict(item.split(":", 1) for item in args.job)
    git_head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    cancelled: set[str] = set()
    append_ledger(
        {
            "timestamp_utc": utc_now(),
            "phase": "B1_RACE_SUBMITTED",
            "git_head": git_head,
            "job_ids": json.dumps(jobs, sort_keys=True),
            "job_states": "SUBMITTED",
            "decision": "NEEDS_MONITOR",
            "next_action": "watch B1 race; cancel pending loser when a job starts",
        }
    )
    while True:
        states = {partition: squeue_state(job_id) for partition, job_id in jobs.items()}
        running = [partition for partition, state in states.items() if state.get("state") == "RUNNING"]
        pending = [partition for partition, state in states.items() if state.get("state") == "PENDING"]
        if running:
            winner_partition = running[0]
            for partition in pending:
                if partition not in cancelled:
                    scancel = run(["scancel", jobs[partition]])
                    states[partition]["cancel_command"] = f"scancel {jobs[partition]}"
                    states[partition]["cancel_exit"] = str(scancel.returncode)
                    states[partition]["cancel_stdout"] = scancel.stdout.strip()
                    states[partition]["cancel_stderr"] = scancel.stderr.strip()
                    cancelled.add(partition)
            append_ledger(
                {
                    "timestamp_utc": utc_now(),
                    "phase": "B1_RACE_RUNNING",
                    "git_head": git_head,
                    "job_ids": json.dumps(jobs, sort_keys=True),
                    "job_states": json.dumps(states, sort_keys=True),
                    "decision": "NEEDS_MONITOR",
                    "next_action": f"monitor running winner candidate {winner_partition}",
                }
            )
        elif all(state.get("state") not in {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING"} for state in states.values()):
            decision = "ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_IMPLEMENTED" if completion_pass() else "ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_NEEDS_REVISION"
            append_ledger(
                {
                    "timestamp_utc": utc_now(),
                    "phase": "B1_RACE_TERMINAL",
                    "git_head": git_head,
                    "job_ids": json.dumps(jobs, sort_keys=True),
                    "job_states": json.dumps(states, sort_keys=True),
                    "decision": decision,
                    "next_action": "controller resume B2 if B1 pass; otherwise register global terminal and launch B10",
                }
            )
            write_json(
                STATE,
                {
                    "status": decision,
                    "updated_at_utc": utc_now(),
                    "jobs": jobs,
                    "states": states,
                    "winner_file": str(WINNER),
                    "canonical_completion": str(B1_DIR / "completion.json"),
                    "canonical_completion_pass": completion_pass(),
                },
            )
            return 0 if completion_pass() else 1
        else:
            append_ledger(
                {
                    "timestamp_utc": utc_now(),
                    "phase": "B1_RACE_PENDING",
                    "git_head": git_head,
                    "job_ids": json.dumps(jobs, sort_keys=True),
                    "job_states": json.dumps(states, sort_keys=True),
                    "decision": "NEEDS_MONITOR",
                    "next_action": "poll again",
                }
            )
        write_json(
            STATE,
            {
                "status": "NEEDS_MONITOR",
                "updated_at_utc": utc_now(),
                "jobs": jobs,
                "states": states,
                "cancelled_partitions": sorted(cancelled),
                "winner_file": str(WINNER),
                "canonical_completion": str(B1_DIR / "completion.json"),
                "canonical_completion_pass": completion_pass(),
            },
        )
        time.sleep(max(30, args.poll_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
