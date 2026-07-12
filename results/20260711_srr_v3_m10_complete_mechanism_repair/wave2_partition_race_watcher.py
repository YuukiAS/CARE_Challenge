#!/usr/bin/env python3
"""Watch the M10 Wave 2 partition race and cancel pending mirror chains."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
from typing import Any


RUNNING_STATES = {"RUNNING", "COMPLETING", "CONFIGURING"}
PENDING_STATES = {"PENDING"}


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def squeue_state(job_id: str) -> dict[str, str]:
    cp = run(["squeue", "-h", "-j", job_id, "-o", "%i|%P|%T|%R"])
    if cp.returncode != 0:
        return {"job_id": job_id, "partition": "", "state": "SQUEUE_FAILED", "reason": (cp.stderr or cp.stdout).strip()}
    line = cp.stdout.strip().splitlines()[0] if cp.stdout.strip() else ""
    if not line:
        return {"job_id": job_id, "partition": "", "state": "NOT_IN_SQUEUE", "reason": "not listed"}
    parts = line.split("|", 3)
    while len(parts) < 4:
        parts.append("")
    return {"job_id": parts[0], "partition": parts[1], "state": parts[2], "reason": parts[3]}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cancel_jobs(job_ids: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for job_id in job_ids:
        state = squeue_state(job_id)
        if state["state"] in PENDING_STATES:
            cp = run(["scancel", job_id])
            records.append(
                {
                    "job_id": job_id,
                    "state_before_cancel": state,
                    "cancel_exit_code": cp.returncode,
                    "cancel_stdout": cp.stdout.strip(),
                    "cancel_stderr": cp.stderr.strip(),
                }
            )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--state-path", required=True, type=Path)
    parser.add_argument("--check-interval-seconds", type=int, default=60)
    parser.add_argument("--max-checks", type=int, default=1440)
    args = parser.parse_args()

    submission = json.loads(args.submission.read_text(encoding="utf-8"))
    chains = submission["chains"]
    state: dict[str, Any] = {
        "started_at_utc": now(),
        "submission": str(args.submission),
        "checks": [],
        "winner_partition": "",
        "winner_reason": "",
        "cancel_records": [],
        "final_state": "NEEDS_MONITOR",
    }
    write_json(args.state_path, state)

    for check_idx in range(1, args.max_checks + 1):
        snapshot: dict[str, Any] = {"checked_at_utc": now(), "check_index": check_idx, "d0_states": {}}
        running: list[str] = []
        for partition, chain in chains.items():
            d0_job_id = str(chain["jobs"]["d0_control"])
            d0_state = squeue_state(d0_job_id)
            snapshot["d0_states"][partition] = d0_state
            if d0_state["state"] in RUNNING_STATES:
                running.append(partition)
        state["checks"].append(snapshot)
        if len(running) == 1:
            winner = running[0]
            state["winner_partition"] = winner
            state["winner_reason"] = "first_d0_running"
            loser_jobs: list[str] = []
            for partition, chain in chains.items():
                if partition == winner:
                    continue
                loser_jobs.extend(str(job_id) for job_id in chain.get("preflight_job_ids", []))
                loser_jobs.extend(str(job_id) for job_id in chain["jobs"].values())
            state["cancel_records"] = cancel_jobs(loser_jobs)
            state["final_state"] = "WINNER_SELECTED"
            write_json(args.state_path, state)
            return 0
        if len(running) > 1:
            state["winner_partition"] = running[0]
            state["winner_reason"] = "multiple_d0_running_selected_first_no_running_cancel"
            state["final_state"] = "MULTIPLE_RUNNING"
            write_json(args.state_path, state)
            return 0
        if all(squeue_state(str(chain["jobs"]["d0_control"]))["state"] == "NOT_IN_SQUEUE" for chain in chains.values()):
            state["final_state"] = "NO_RUNNING_D0_ALL_GONE"
            write_json(args.state_path, state)
            return 0
        write_json(args.state_path, state)
        time.sleep(max(1, args.check_interval_seconds))

    state["final_state"] = "MAX_CHECKS_REACHED"
    write_json(args.state_path, state)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
