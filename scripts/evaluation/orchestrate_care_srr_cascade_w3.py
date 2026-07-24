#!/usr/bin/env python
"""Durable W3 orchestration for CARE SRR cascade source-cache race and formal jobs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
LOCK_DIR = RESULT / "source_cache_full_runtime.winner.lock"
FINAL_CACHE_DIR = RESULT / "source_cache_full_runtime"
RACE_GROUP = "care_srr_cache_full_all220_20260724_locked"
CACHE_JOBS = {
    "60451021": {"attempt_id": "cache_htzhulab_20260724a", "partition": "htzhulab", "job_name": "CareSRRCacheH"},
    "60451022": {"attempt_id": "cache_a100_20260724a", "partition": "a100-gpu", "job_name": "CareSRRCacheA"},
}
FORMAL_JOBS = [
    {
        "logical_run_id": "scar_seed20260724",
        "partition": "htzhulab",
        "pathology": "scar",
        "seed": 20260724,
        "variants": ["scar_cascade_control", "scar_srr_cascade"],
        "job_name": "SRRScar24",
        "gres": "gpu:1",
    },
    {
        "logical_run_id": "edema_seed20260724",
        "partition": "htzhulab",
        "pathology": "edema",
        "seed": 20260724,
        "variants": ["edema_zone_control", "edema_srr_zone_cascade"],
        "job_name": "SRREdema24",
        "gres": "gpu:1",
    },
    {
        "logical_run_id": "scar_seed20260725",
        "partition": "a100-gpu",
        "pathology": "scar",
        "seed": 20260725,
        "variants": ["scar_cascade_control", "scar_srr_cascade"],
        "job_name": "SRRScar25",
        "gres": "gpu:nvidia_a100-pcie-40gb:1",
    },
    {
        "logical_run_id": "edema_seed20260725",
        "partition": "a100-gpu",
        "pathology": "edema",
        "seed": 20260725,
        "variants": ["edema_zone_control", "edema_srr_zone_cascade"],
        "job_name": "SRREdema25",
        "gres": "gpu:nvidia_a100-pcie-40gb:1",
    },
]
WATCHER_SCRIPT = ROOT / "jobs/care_mm/watch_care_srr_cascade_w3.sh"
WATCHER_LOG_GLOB = "logs/care_myops_srr_cascade_submission_rescue/SRRW3Watch_*.log"
FORMAL_ENTRYPOINT_STATUS = "NEEDS_REPAIR_FORMAL_ENTRYPOINT_MISSING"
FORMAL_ENTRYPOINT_NOTES = (
    "Formal topology is specified, but no real W3 formal training runtime is implemented. "
    "The orchestrator must not submit formal jobs until this is repaired."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def git_value(*args: str) -> str:
    return run(["git", *args]).stdout.strip()


def squeue_states(job_ids: list[str]) -> dict[str, dict[str, str]]:
    if not job_ids:
        return {}
    proc = run(["squeue", "-h", "-j", ",".join(job_ids), "-o", "%i|%P|%j|%T|%M|%l|%R"], check=False)
    out: dict[str, dict[str, str]] = {}
    for line in proc.stdout.splitlines():
        parts = line.split("|")
        if len(parts) >= 7:
            out[parts[0]] = {
                "job_id": parts[0],
                "partition": parts[1],
                "job_name": parts[2],
                "state": parts[3],
                "elapsed": parts[4],
                "time_limit": parts[5],
                "reason": parts[6],
            }
    return out


def sacct_states(job_ids: list[str]) -> dict[str, dict[str, str]]:
    if not job_ids:
        return {}
    proc = run(
        [
            "sacct",
            "-j",
            ",".join(job_ids),
            "--format=JobID,JobName,Partition,Account,QOS,State,ExitCode,Elapsed,Start,End",
            "-P",
        ],
        check=False,
    )
    rows: dict[str, dict[str, str]] = {}
    lines = proc.stdout.splitlines()
    if not lines:
        return rows
    headers = lines[0].split("|")
    for line in lines[1:]:
        values = line.split("|")
        if len(values) == len(headers):
            row = dict(zip(headers, values))
            if "." not in row["JobID"]:
                rows[row["JobID"]] = row
    return rows


def read_cache_receipts() -> dict[str, Any]:
    manifest_path = RESULT / "source_cache_manifest.csv"
    parity_path = RESULT / "source_cache_parity_checks.csv"
    hashes_path = RESULT / "source_cache_hashes.json"
    status = {
        "manifest_exists": manifest_path.exists(),
        "parity_exists": parity_path.exists(),
        "hashes_exists": hashes_path.exists(),
        "final_cache_dir_exists": FINAL_CACHE_DIR.is_dir(),
        "decision": "NEEDS_MONITOR",
    }
    if not (manifest_path.exists() and parity_path.exists() and hashes_path.exists()):
        return status
    with manifest_path.open(newline="") as f:
        manifest_rows = list(csv.DictReader(f))
    with parity_path.open(newline="") as f:
        parity_rows = list(csv.DictReader(f))
    hashes = json.loads(hashes_path.read_text())
    full_pass = (
        hashes.get("status") == "PASS"
        and hashes.get("decision") == "PASS"
        and int(hashes.get("case_count_observed", -1)) == 220
        and len(manifest_rows) == 880
        and len(parity_rows) == 880
        and all(row.get("decision") == "PASS" for row in parity_rows)
        and FINAL_CACHE_DIR.is_dir()
    )
    full_attempt_finished_bad = hashes.get("scope") == "full_all_220_internal_source_cache" or int(hashes.get("case_count_observed", -1)) == 220
    status.update(
        {
            "hashes_status": hashes.get("status"),
            "hashes_decision": hashes.get("decision"),
            "hashes_scope": hashes.get("scope"),
            "case_count_observed": hashes.get("case_count_observed"),
            "manifest_row_count": len(manifest_rows),
            "parity_row_count": len(parity_rows),
            "parity_decisions": sorted(set(row.get("decision", "") for row in parity_rows)),
            "decision": "PASS" if full_pass else ("NEEDS_REPAIR" if full_attempt_finished_bad else "NEEDS_MONITOR"),
        }
    )
    return status


def winner_from_lock() -> dict[str, Any] | None:
    winner_path = LOCK_DIR / "winner.json"
    if not winner_path.exists():
        return None
    return json.loads(winner_path.read_text())


def cancel_pending_losers(winner_job_id: str | None, states: dict[str, dict[str, str]], *, dry_run: bool) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for job_id in CACHE_JOBS:
        if job_id == winner_job_id:
            continue
        state = states.get(job_id, {}).get("state", "")
        if state == "PENDING":
            cmd = ["scancel", job_id]
            if dry_run:
                actions.append({"job_id": job_id, "action": "DRY_RUN_SCANCEL_PENDING_LOSER", "command": " ".join(cmd)})
            else:
                proc = run(cmd, check=False)
                actions.append(
                    {
                        "job_id": job_id,
                        "action": "SCANCEL_PENDING_LOSER",
                        "returncode": proc.returncode,
                        "stdout": proc.stdout.strip(),
                        "stderr": proc.stderr.strip(),
                    }
                )
    return actions


def submit_formal_job(job: dict[str, Any], cache_job_id: str, *, dry_run: bool) -> dict[str, Any]:
    export_vars = (
        f"ALL,CARE_FORMAL_LOGICAL_RUN_ID={job['logical_run_id']},CARE_FORMAL_PATHOLOGY={job['pathology']},"
        f"CARE_FORMAL_SEED={job['seed']},CARE_FORMAL_VARIANTS={'|'.join(job['variants'])},"
        "CARE_FORMAL_STEPS=6250,CARE_FORMAL_VALIDATION_STEPS=1250|2500|3750|5000|6250,"
        f"CARE_SOURCE_CACHE_JOB_ID={cache_job_id}"
    )
    cmd = [
        "sbatch",
        "--parsable",
        f"--dependency=afterok:{cache_job_id}",
        f"--job-name={job['job_name']}",
        f"--partition={job['partition']}",
        "--qos=gpu_access",
        f"--gres={job['gres']}",
        f"--export={export_vars}",
        "jobs/care_mm/run_care_srr_cascade_formal_training.sh",
    ]
    if dry_run:
        return {"logical_run_id": job["logical_run_id"], "dry_run": True, "command": " ".join(cmd), "job_id": "DRY_RUN"}
    proc = run(cmd)
    return {"logical_run_id": job["logical_run_id"], "dry_run": False, "command": " ".join(cmd), "job_id": proc.stdout.strip()}


def submit_finalizer(formal_job_ids: list[str], *, dry_run: bool) -> dict[str, Any]:
    dependency = "afterany:" + ":".join(formal_job_ids)
    cmd = [
        "sbatch",
        "--parsable",
        f"--dependency={dependency}",
        "--job-name=SRRW3Final",
        "--partition=general",
        "--time=01:00:00",
        "--cpus-per-task=2",
        "--mem=8G",
        "--export=ALL",
        "jobs/care_mm/finalize_care_srr_cascade_w3.sh",
    ]
    if dry_run:
        return {"dry_run": True, "command": " ".join(cmd), "job_id": "DRY_RUN"}
    proc = run(cmd)
    return {"dry_run": False, "command": " ".join(cmd), "job_id": proc.stdout.strip()}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def append_ledger(decision: str, job_states: str, next_action: str, notes: str) -> None:
    ledger = RESULT / "controller_ledger.csv"
    contract = RESULT / "resolved_execution_contract.json"
    row = {
        "timestamp_utc": utc_now(),
        "phase": "RESCUE_W3_DURABLE_ORCHESTRATOR_UPDATE",
        "git_head": git_value("rev-parse", "HEAD"),
        "origin_main": git_value("rev-parse", "origin/main"),
        "task_hash": sha256_file(contract),
        "job_states": job_states,
        "decision": decision,
        "next_action": next_action,
        "notes": notes,
    }
    with ledger.open(newline="") as f:
        fields = csv.DictReader(f).fieldnames
    if fields != list(row):
        raise RuntimeError(f"controller_ledger.csv schema mismatch: {fields}")
    with ledger.open("a", newline="") as f:
        csv.DictWriter(f, fieldnames=fields).writerow(row)


def update_monitor_receipts(
    *,
    states: dict[str, dict[str, str]],
    accounting: dict[str, dict[str, str]],
    cache_status: dict[str, Any],
    winner: dict[str, Any] | None,
    cancel_actions: list[dict[str, Any]],
    formal_submissions: list[dict[str, Any]],
    finalizer: dict[str, Any] | None,
    decision: str,
) -> None:
    script_sha = sha256_file(ROOT / "jobs/care_mm/precompute_care_srr_cascade_source_cache.sh")
    formal_script_sha = sha256_file(ROOT / "jobs/care_mm/run_care_srr_cascade_formal_training.sh")
    watcher_script_sha = sha256_file(WATCHER_SCRIPT)
    watcher_active = os.environ.get("CARE_W3_WATCHER_ACTIVE") == "1"
    watcher_state = {
        "job_id": os.environ.get("SLURM_JOB_ID", "NOT_SUBMITTED_LOCAL_ORCHESTRATOR") if watcher_active else "NOT_SUBMITTED_LOCAL_ORCHESTRATOR",
        "state": "RUNNING_SLURM_WATCHER" if watcher_active else "LOCAL_DRY_RUN_OR_ONCE",
        "script": str(WATCHER_SCRIPT.relative_to(ROOT)),
        "script_sha256": watcher_script_sha,
        "log_path_glob": WATCHER_LOG_GLOB,
        "submit_command": "sbatch --parsable jobs/care_mm/watch_care_srr_cascade_w3.sh",
        "notes": "Watcher wrapper is durable; this receipt may be produced by local --once execution without submitting the watcher.",
    }
    rows = [
        {
            "attempt_id": "source_cache_precompute_001_superseded_no_lock",
            "logical_run_id": "source_cache_full_all220_precompute",
            "job_kind": "PREREQUISITE_SOURCE_CACHE_NOT_FORMAL_TRAINING_SUPERSEDED",
            "slurm_job_id": "60450660",
            "partition": "htzhulab",
            "qos": "gpu_access",
            "account": "rc_htzhu_pi",
            "job_state": accounting.get("60450660", {}).get("State", "CANCELLED"),
            "exit_code": accounting.get("60450660", {}).get("ExitCode", "0:0"),
            "dependency": "none",
            "script_sha256": script_sha,
            "winner_lock_path": "MISSING_IN_SUPERSEDED_ATTEMPT",
            "submit_command": "sbatch --parsable jobs/care_mm/precompute_care_srr_cascade_source_cache.sh",
            "log_path_glob": "logs/care_myops_srr_cascade_submission_rescue/CareSRRCache_60450660_*.log",
            "decision": "SUPERSEDED_CANCELLED",
            "notes": "Unsafe no-lock pending job cancelled and replaced by locked race.",
        }
    ]
    rows.append(
        {
            "attempt_id": "w3_cache_race_and_formal_watcher",
            "logical_run_id": "w3_orchestration",
            "job_kind": "WATCHER_ORCHESTRATOR",
            "slurm_job_id": watcher_state["job_id"],
            "partition": "general",
            "qos": "default",
            "account": "rc_htzhu_pi",
            "job_state": watcher_state["state"],
            "exit_code": "NOT_TERMINAL_OR_LOCAL",
            "dependency": "none",
            "script_sha256": watcher_script_sha,
            "winner_lock_path": str(LOCK_DIR.relative_to(ROOT)),
            "submit_command": watcher_state["submit_command"],
            "log_path_glob": WATCHER_LOG_GLOB,
            "decision": "NEEDS_MONITOR",
            "notes": watcher_state["notes"],
        }
    )
    for job_id, meta in CACHE_JOBS.items():
        live = states.get(job_id, {})
        acct = accounting.get(job_id, {})
        rows.append(
            {
                "attempt_id": meta["attempt_id"],
                "logical_run_id": "source_cache_full_all220_precompute",
                "job_kind": "PREREQUISITE_SOURCE_CACHE_NOT_FORMAL_TRAINING_LOCKED_RACE",
                "slurm_job_id": job_id,
                "partition": meta["partition"],
                "qos": acct.get("QOS", "gpu_access"),
                "account": acct.get("Account", "rc_htzhu_pi"),
                "job_state": live.get("state") or acct.get("State", "UNKNOWN"),
                "exit_code": acct.get("ExitCode", "AWAITING_TERMINAL_ACCOUNTING"),
                "dependency": "none",
                "script_sha256": script_sha,
                "winner_lock_path": str(LOCK_DIR.relative_to(ROOT)),
                "submit_command": f"locked race attempt {meta['attempt_id']}",
                "log_path_glob": f"logs/care_myops_srr_cascade_submission_rescue/CareSRRCache_{meta['attempt_id']}_{job_id}_*.log",
                "decision": "NEEDS_REPAIR" if cache_status.get("decision") == "NEEDS_REPAIR" else "NEEDS_MONITOR",
                "notes": f"state={live.get('state') or acct.get('State', 'UNKNOWN')} reason={live.get('reason', '')}",
            }
        )
    for submit in formal_submissions:
        logical = submit["logical_run_id"]
        rows.append(
            {
                "attempt_id": f"formal_{logical}",
                "logical_run_id": logical,
                "job_kind": "FORMAL_TRAINING",
                "slurm_job_id": submit.get("job_id", ""),
                "partition": next(j["partition"] for j in FORMAL_JOBS if j["logical_run_id"] == logical),
                "qos": "gpu_access",
                "account": "rc_htzhu_pi",
                "job_state": "SUBMITTED_NEEDS_MONITOR",
                "exit_code": "AWAITING_TERMINAL_ACCOUNTING",
                "dependency": submit["command"].split("--dependency=", 1)[1].split()[0] if "--dependency=" in submit["command"] else "",
                "script_sha256": formal_script_sha,
                "winner_lock_path": str(LOCK_DIR.relative_to(ROOT)),
                "submit_command": submit["command"],
                "log_path_glob": f"logs/care_myops_srr_cascade_submission_rescue/{logical}_*.log",
                "decision": "NEEDS_MONITOR",
                "notes": "control then SRR only; 6250 optimizer steps each; validation at 1250|2500|3750|5000|6250",
            }
        )
    write_csv(RESULT / "slurm_attempts.csv", rows)

    training_rows = []
    submitted_by_logical = {row["logical_run_id"]: row for row in formal_submissions}
    for job in FORMAL_JOBS:
        submitted = submitted_by_logical.get(job["logical_run_id"])
        training_rows.append(
            {
                "logical_run_id": job["logical_run_id"],
                "partition": job["partition"],
                "pathology": job["pathology"],
                "seed": job["seed"],
                "variants": "|".join(job["variants"]),
                "formal_training_job_id": submitted.get("job_id", "NOT_SUBMITTED_SOURCE_CACHE_OR_FORMAL_ENTRYPOINT_MISSING")
                if submitted
                else "NOT_SUBMITTED_SOURCE_CACHE_OR_FORMAL_ENTRYPOINT_MISSING",
                "control_steps_completed": 0,
                "srr_steps_completed": 0,
                "required_steps_each": 6250,
                "validation_steps_required": "1250|2500|3750|5000|6250",
                "validation_events_completed": 0,
                "state": "SUBMITTED_NEEDS_MONITOR" if submitted else "NOT_SUBMITTED_SOURCE_CACHE_OR_FORMAL_ENTRYPOINT_MISSING",
                "source_cache_dependency_job_id": winner.get("slurm_job_id", "") if winner else "PENDING_WINNER",
                "decision": "NEEDS_REPAIR" if decision == "NEEDS_REPAIR" else "NEEDS_MONITOR",
                "notes": FORMAL_ENTRYPOINT_NOTES,
            }
        )
    write_csv(RESULT / "training_adequacy.csv", training_rows)

    state = {
        "status": decision,
        "decision": decision,
        "w3_blockers": [FORMAL_ENTRYPOINT_STATUS],
        "generated_utc": utc_now(),
        "race_group": RACE_GROUP,
        "cache_jobs": CACHE_JOBS,
        "live_states": states,
        "accounting": accounting,
        "winner": winner,
        "winner_lock_path": str(LOCK_DIR.relative_to(ROOT)),
        "cache_receipts": cache_status,
        "source_cache_monitor_decision": cache_status.get("decision"),
        "cancel_actions": cancel_actions,
        "watcher": watcher_state,
        "formal_submissions": formal_submissions,
        "finalizer_submission": finalizer,
        "formal_training_submitted": bool(formal_submissions),
        "formal_entrypoint_status": FORMAL_ENTRYPOINT_STATUS,
        "formal_entrypoint_notes": FORMAL_ENTRYPOINT_NOTES,
        "script_sha256": script_sha,
        "formal_script_sha256": formal_script_sha,
    }
    (RESULT / "source_cache_race_state.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    matched = {
        "status": decision,
        "decision": decision,
        "w3_blockers": [FORMAL_ENTRYPOINT_STATUS],
        "generated_utc": utc_now(),
        "source_cache_status": cache_status,
        "source_cache_race_state": str((RESULT / "source_cache_race_state.json").relative_to(ROOT)),
        "formal_topology": FORMAL_JOBS,
        "formal_submissions": formal_submissions,
        "finalizer_submission": finalizer,
        "formal_entrypoint_status": FORMAL_ENTRYPOINT_STATUS,
        "formal_entrypoint_notes": FORMAL_ENTRYPOINT_NOTES,
        "matching_contract": {
            "same_source_checkpoints": True,
            "same_case_and_patch_sequence_within_pathology": "BOUND_BY_FORMAL_ENTRYPOINT_CASE_SEQUENCE_HASH",
            "same_spatial_and_intensity_augmentation_within_pathology": "BOUND_BY_FORMAL_ENTRYPOINT_AUGMENTATION_SEED_HASH",
            "same_common_head_initialization_within_seed": "BOUND_BY_FORMAL_ENTRYPOINT_INITIAL_STATE_HASH",
            "same_optimizer_budget_decode_evaluator": True,
        },
    }
    (RESULT / "matched_run_hashes.json").write_text(json.dumps(matched, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cache-monitor-only", action="store_true")
    parser.add_argument("--submit-formal-if-ready", action="store_true", help="Deprecated guard: current runtime records NEEDS_REPAIR instead of submitting formal jobs.")
    args = parser.parse_args()

    states = squeue_states(list(CACHE_JOBS))
    accounting = sacct_states(["60450660", *CACHE_JOBS])
    winner = winner_from_lock()
    winner_job_id = str(winner.get("slurm_job_id")) if winner else None
    running = [job_id for job_id, row in states.items() if row.get("state") in {"RUNNING", "COMPLETING"}]
    if not winner_job_id and running:
        winner_job_id = running[0]
        winner = {"slurm_job_id": winner_job_id, "attempt_id": CACHE_JOBS[winner_job_id]["attempt_id"], "partition": CACHE_JOBS[winner_job_id]["partition"], "source": "RUNNING_STATE"}
    cancel_actions = cancel_pending_losers(winner_job_id, states, dry_run=args.dry_run) if winner_job_id else []
    if cancel_actions and not args.dry_run:
        states = squeue_states(list(CACHE_JOBS))
        accounting = sacct_states(["60450660", *CACHE_JOBS])

    cache_status = read_cache_receipts()
    formal_submissions: list[dict[str, Any]] = []
    finalizer = None
    decision = "NEEDS_MONITOR"
    if args.cache_monitor_only and cache_status.get("decision") == "NEEDS_MONITOR":
        decision = "NEEDS_MONITOR"
    elif cache_status.get("decision") == "PASS":
        terminal = accounting.get(winner_job_id or "", {}).get("State", "")
        if terminal in {"COMPLETED"} and args.submit_formal_if_ready:
            decision = "NEEDS_REPAIR"
        elif terminal not in {"COMPLETED"}:
            decision = "NEEDS_MONITOR"
        else:
            decision = "NEEDS_REPAIR"
    elif cache_status.get("decision") == "NEEDS_REPAIR":
        decision = "NEEDS_REPAIR"
    if decision != "NEEDS_REPAIR" and not (args.cache_monitor_only and cache_status.get("decision") == "NEEDS_MONITOR"):
        decision = "NEEDS_REPAIR"

    update_monitor_receipts(
        states=states,
        accounting=accounting,
        cache_status=cache_status,
        winner=winner,
        cancel_actions=cancel_actions,
        formal_submissions=formal_submissions,
        finalizer=finalizer,
        decision=decision,
    )
    job_state_summary = ";".join(f"{jid}:{states.get(jid, {}).get('state', accounting.get(jid, {}).get('State', 'UNKNOWN'))}" for jid in CACHE_JOBS)
    append_ledger(
        decision,
        job_state_summary,
        "MONITOR_CACHE_RACE_ONLY_FORMAL_ENTRYPOINT_REPAIR_REQUIRED",
        "durable orchestrator update; formal jobs are not submitted because real formal runtime is missing",
    )
    print(json.dumps({"decision": decision, "blocker": FORMAL_ENTRYPOINT_STATUS, "cache_states": states, "cache_receipts": cache_status, "formal_submissions": formal_submissions}, indent=2, sort_keys=True))
    return 0 if decision == "NEEDS_MONITOR" else 2


if __name__ == "__main__":
    raise SystemExit(main())
