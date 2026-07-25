#!/usr/bin/env python
"""Watch CARE-SRR-Cascade formal routing races and cancel pending losers."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
RC1_ROOT = RESULT / "runtime_closure_repair_rc1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def parse_pairs(text: str) -> list[dict[str, str]]:
    pairs = []
    for item in text.split(";"):
        if not item.strip():
            continue
        parts = item.split(":")
        if len(parts) != 3:
            raise ValueError(f"bad race pair: {item}")
        logical_id, a100_job, htzhulab_job = parts
        pairs.append({"logical_run_id": logical_id, "a100_job": a100_job, "htzhulab_job": htzhulab_job})
    return pairs


def squeue_snapshot(job_ids: list[str]) -> dict[str, dict[str, str]]:
    proc = run(["squeue", "-h", "-j", ",".join(job_ids), "-o", "%i|%P|%T|%R|%M|%l"])
    rows: dict[str, dict[str, str]] = {}
    for line in proc.stdout.splitlines():
        parts = line.split("|", 5)
        if len(parts) != 6:
            continue
        job_id = parts[0].split("_", 1)[0]
        rows[job_id] = {
            "job_id": parts[0],
            "partition": parts[1],
            "state": parts[2],
            "reason": parts[3],
            "elapsed": parts[4],
            "time_limit": parts[5],
            "source": "squeue",
        }
    return rows


def sacct_snapshot(job_ids: list[str]) -> dict[str, dict[str, str]]:
    proc = run(
        [
            "sacct",
            "-j",
            ",".join(job_ids),
            "--format=JobID,JobName%32,Partition,State,ExitCode,Elapsed,Start,End",
            "-P",
        ]
    )
    rows: dict[str, dict[str, str]] = {}
    lines = proc.stdout.splitlines()
    if not lines:
        return rows
    headers = lines[0].split("|")
    for line in lines[1:]:
        values = line.split("|")
        if len(values) != len(headers):
            continue
        row = dict(zip(headers, values))
        job_id = row.get("JobID", "")
        if "." in job_id:
            continue
        rows[job_id] = {
            "job_id": job_id,
            "job_name": row.get("JobName", ""),
            "partition": row.get("Partition", ""),
            "state": row.get("State", "").split()[0],
            "exit_code": row.get("ExitCode", ""),
            "elapsed": row.get("Elapsed", ""),
            "start": row.get("Start", ""),
            "end": row.get("End", ""),
            "source": "sacct",
        }
    return rows


def merged_snapshot(job_ids: list[str]) -> dict[str, dict[str, str]]:
    sacct = sacct_snapshot(job_ids)
    live = squeue_snapshot(job_ids)
    merged = dict(sacct)
    merged.update(live)
    return merged


def cancel_if_pending(job_id: str, snapshot: dict[str, dict[str, str]], *, dry_run: bool) -> dict[str, Any]:
    state = snapshot.get(job_id, {}).get("state", "")
    if state != "PENDING":
        return {"job_id": job_id, "action": "NOT_CANCELLED_NOT_PENDING", "state": state}
    cmd = ["scancel", job_id]
    if dry_run:
        return {"job_id": job_id, "action": "DRY_RUN_SCANCEL_PENDING_LOSER", "state": state, "command": " ".join(cmd)}
    proc = run(cmd)
    return {
        "job_id": job_id,
        "action": "SCANCEL_PENDING_LOSER",
        "state": state,
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def evaluate_once(pairs: list[dict[str, str]], *, dry_run: bool) -> dict[str, Any]:
    job_ids = sorted({pair["a100_job"] for pair in pairs} | {pair["htzhulab_job"] for pair in pairs})
    snapshot = merged_snapshot(job_ids)
    actions = []
    for pair in pairs:
        a100_state = snapshot.get(pair["a100_job"], {}).get("state", "")
        htz_state = snapshot.get(pair["htzhulab_job"], {}).get("state", "")
        if a100_state == "RUNNING" and htz_state == "PENDING":
            actions.append({**pair, "winner_job_id": pair["a100_job"], "winner_partition": "a100-gpu", **cancel_if_pending(pair["htzhulab_job"], snapshot, dry_run=dry_run)})
        elif htz_state == "RUNNING" and a100_state == "PENDING":
            actions.append({**pair, "winner_job_id": pair["htzhulab_job"], "winner_partition": "htzhulab", **cancel_if_pending(pair["a100_job"], snapshot, dry_run=dry_run)})
        elif a100_state == "COMPLETED" and htz_state == "PENDING":
            actions.append({**pair, "winner_job_id": pair["a100_job"], "winner_partition": "a100-gpu", **cancel_if_pending(pair["htzhulab_job"], snapshot, dry_run=dry_run)})
        elif htz_state == "COMPLETED" and a100_state == "PENDING":
            actions.append({**pair, "winner_job_id": pair["htzhulab_job"], "winner_partition": "htzhulab", **cancel_if_pending(pair["a100_job"], snapshot, dry_run=dry_run)})
        else:
            actions.append({**pair, "action": "NO_CANCEL", "a100_state": a100_state, "htzhulab_state": htz_state})
    active_states = {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING"}
    decision = "NEEDS_MONITOR" if any(row.get("state") in active_states for row in snapshot.values()) else "TERMINAL_NEEDS_ACCOUNTING"
    return {"timestamp_utc": utc_now(), "decision": decision, "pairs": pairs, "snapshot": snapshot, "actions": actions, "dry_run": dry_run}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", required=True, help="semicolon-separated logical:a100_job:htzhulab_job entries")
    parser.add_argument("--interval-seconds", type=float, default=300.0)
    parser.add_argument("--max-iterations", type=int, default=288)
    parser.add_argument("--state-file", type=Path, default=RC1_ROOT / "formal_race_watcher_state_v2.json")
    parser.add_argument("--history-file", type=Path, default=RC1_ROOT / "formal_race_watcher_history_v2.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    pairs = parse_pairs(args.pairs)
    iterations = 1 if args.once else args.max_iterations
    for index in range(iterations):
        payload = evaluate_once(pairs, dry_run=args.dry_run)
        payload["iteration"] = index + 1
        write_json(args.state_file, payload)
        append_jsonl(args.history_file, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        if args.once or payload["decision"] == "TERMINAL_NEEDS_ACCOUNTING":
            return 0
        time.sleep(args.interval_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
