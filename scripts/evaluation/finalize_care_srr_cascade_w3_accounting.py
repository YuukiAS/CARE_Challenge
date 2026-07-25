#!/usr/bin/env python
"""Terminal accounting for CARE-SRR-Cascade W3 formal attempts."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
RC1_ROOT = RESULT / "runtime_closure_repair_rc1"
FORMAL_ROOT = RESULT / "runtime/formal_v2"
STATE_PATH = RESULT / "w3_orchestrator_state_v2.json"

LOGICAL_JOBS = {
    "scar_seed20260724": ("scar", ("scar_cascade_control", "scar_srr_cascade")),
    "edema_seed20260724": ("edema", ("edema_zone_control", "edema_srr_zone_cascade")),
    "scar_seed20260725": ("scar", ("scar_cascade_control", "scar_srr_cascade")),
    "edema_seed20260725": ("edema", ("edema_zone_control", "edema_srr_zone_cascade")),
}

ACTIVE_STATES = {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING", "SUSPENDED", "REQUEUED"}
TERMINAL_STATES = {"COMPLETED", "CANCELLED", "FAILED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL", "PREEMPTED", "BOOT_FAIL", "DEADLINE", "REVOKED"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else ["logical_run_id"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_state(text: str) -> str:
    return str(text or "").split()[0].split("+", 1)[0]


def collect_training_attempt_ids(state: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for run in state.get("logical_runs", {}).values():
        job_id = str(run.get("job_id", ""))
        if job_id.isdigit():
            ids.append(job_id)
        for old in run.get("attempt_history", []):
            old_id = str(old.get("job_id", ""))
            if old_id.isdigit():
                ids.append(old_id)
        for mirror in run.get("race_mirrors", []):
            mirror_id = str(mirror.get("job_id", ""))
            if mirror_id.isdigit():
                ids.append(mirror_id)
    return sorted(dict.fromkeys(ids))


def collect_auxiliary_job_ids(state: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    finalizer = state.get("afterany_finalizer", {})
    finalizer_id = str(finalizer.get("job_id", ""))
    if finalizer_id.isdigit():
        ids.append(finalizer_id)
    watcher = state.get("formal_race_watcher", {})
    watcher_id = str(watcher.get("job_id", ""))
    if watcher_id.isdigit():
        ids.append(watcher_id)
    return sorted(dict.fromkeys(ids))


def sacct_rows(job_ids: list[str]) -> dict[str, dict[str, str]]:
    if not job_ids:
        return {}
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
        row["State"] = normalize_state(row.get("State", ""))
        rows[job_id] = row
    return rows


def squeue_rows(job_ids: list[str]) -> dict[str, dict[str, str]]:
    if not job_ids:
        return {}
    proc = run(["squeue", "-h", "-j", ",".join(job_ids), "-o", "%i|%P|%T|%R|%M|%l"])
    rows: dict[str, dict[str, str]] = {}
    for line in proc.stdout.splitlines():
        parts = line.split("|", 5)
        if len(parts) != 6:
            continue
        job_id = parts[0].split("_", 1)[0]
        rows[job_id] = {
            "JobID": parts[0],
            "Partition": parts[1],
            "State": normalize_state(parts[2]),
            "Reason": parts[3],
            "Elapsed": parts[4],
            "TimeLimit": parts[5],
        }
    return rows


def merged_slurm_rows(job_ids: list[str]) -> dict[str, dict[str, str]]:
    rows = sacct_rows(job_ids)
    rows.update(squeue_rows(job_ids))
    return rows


def variant_status(logical_id: str, variant: str) -> dict[str, Any]:
    run_dir = FORMAL_ROOT / logical_id / variant
    summary_path = run_dir / "training_summary.json"
    failure_path = run_dir / "runtime_failure.json"
    checkpoint_path = run_dir / "checkpoints/checkpoint_final.pt"
    row: dict[str, Any] = {
        "logical_run_id": logical_id,
        "variant": variant,
        "summary_path": str(summary_path.relative_to(ROOT)),
        "checkpoint_path": str(checkpoint_path.relative_to(ROOT)),
        "summary_exists": summary_path.exists(),
        "checkpoint_exists": checkpoint_path.exists(),
        "runtime_failure_exists": failure_path.exists(),
        "optimizer_step": 0,
        "validation_event_count": 0,
        "decision": "NEEDS_MONITOR",
    }
    if failure_path.exists():
        failure = load_json(failure_path)
        row.update({"decision": "NEEDS_REPAIR_RUNTIME_FAILURE", "runtime_failure_decision": failure.get("decision"), "runtime_failure_error": failure.get("error", "")})
        return row
    if not summary_path.exists():
        return row
    summary = load_json(summary_path)
    stats = summary.get("stats", {})
    checkpoint = summary.get("checkpoint", {})
    row.update(
        {
            "summary_decision": summary.get("decision", ""),
            "optimizer_step": int(stats.get("optimizer_step", 0) or 0),
            "microbatch_cursor": int(stats.get("microbatch_cursor", 0) or 0),
            "validation_event_count": len(stats.get("validation_events", []) or []),
            "checkpoint_record_path": checkpoint.get("path", ""),
            "checkpoint_optimizer_step": checkpoint.get("optimizer_step", ""),
        }
    )
    if (
        summary.get("decision") == "PASS"
        and int(stats.get("optimizer_step", 0) or 0) == 6250
        and len(stats.get("validation_events", []) or []) == 5
        and checkpoint_path.exists()
        and int(checkpoint.get("optimizer_step", 0) or 0) == 6250
    ):
        row["decision"] = "PASS"
    else:
        row["decision"] = "NEEDS_REPAIR_INCOMPLETE_SUMMARY"
    return row


def aggregate(*, finalizer_job_id: str = "", dependency_job_ids: str = "", log_file: str = "") -> dict[str, Any]:
    state = load_json(STATE_PATH, {"logical_runs": {}})
    job_ids = collect_training_attempt_ids(state)
    auxiliary_job_ids = collect_auxiliary_job_ids(state)
    if finalizer_job_id and finalizer_job_id.isdigit() and finalizer_job_id not in auxiliary_job_ids:
        auxiliary_job_ids.append(finalizer_job_id)
    slurm = merged_slurm_rows(sorted(job_ids))
    auxiliary_slurm = merged_slurm_rows(sorted(auxiliary_job_ids))
    active = {job_id: row for job_id, row in slurm.items() if normalize_state(row.get("State", "")) in ACTIVE_STATES}
    nonterminal_missing = [job_id for job_id in job_ids if job_id not in slurm]
    variant_rows: list[dict[str, Any]] = []
    for logical_id, (_, variants) in LOGICAL_JOBS.items():
        for variant in variants:
            variant_rows.append(variant_status(logical_id, variant))
    bad_variants = [row for row in variant_rows if row["decision"] != "PASS"]
    terminal_bad_jobs = {
        job_id: row
        for job_id, row in slurm.items()
        if normalize_state(row.get("State", "")) in TERMINAL_STATES and normalize_state(row.get("State", "")) not in {"COMPLETED", "CANCELLED"}
    }
    if active or nonterminal_missing:
        decision = "NEEDS_MONITOR"
    elif terminal_bad_jobs:
        decision = "NEEDS_REPAIR_TERMINAL_JOB_FAILURE"
    elif bad_variants:
        decision = "NEEDS_REPAIR_MISSING_OR_INCOMPLETE_TRAINING_OUTPUT"
    else:
        decision = "PASS_TERMINAL_TRAINING_READY_FOR_AGGREGATION"
    payload = {
        "schema_version": 1,
        "timestamp_utc": utc_now(),
        "decision": decision,
        "finalizer_job_id": finalizer_job_id,
        "dependency_job_ids": dependency_job_ids,
        "log_file": log_file,
        "job_ids": sorted(job_ids),
        "auxiliary_job_ids": sorted(auxiliary_job_ids),
        "auxiliary_slurm_rows": auxiliary_slurm,
        "active_or_nonterminal_jobs": active,
        "missing_accounting_jobs": nonterminal_missing,
        "terminal_bad_jobs": terminal_bad_jobs,
        "variant_rows": variant_rows,
        "completion_claim": decision == "PASS_TERMINAL_TRAINING_READY_FOR_AGGREGATION",
    }
    write_csv(RESULT / "formal_terminal_training_variants_v2.csv", variant_rows)
    write_json(RC1_ROOT / "formal_terminal_accounting_v2.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalizer-job-id", default="")
    parser.add_argument("--dependency-job-ids", default="")
    parser.add_argument("--log-file", default="")
    parser.add_argument("--output-json", type=Path, default=RC1_ROOT / "formal_terminal_accounting_v2.json")
    args = parser.parse_args()
    payload = aggregate(finalizer_job_id=args.finalizer_job_id, dependency_job_ids=args.dependency_job_ids, log_file=args.log_file)
    if args.output_json != RC1_ROOT / "formal_terminal_accounting_v2.json":
        write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["decision"] in {"PASS_TERMINAL_TRAINING_READY_FOR_AGGREGATION", "NEEDS_MONITOR"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
