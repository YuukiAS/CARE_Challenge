#!/usr/bin/env python
"""State-driven W3 orchestrator for CARE-SRR-Cascade formal jobs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
REPAIR_ROOT = RESULT / "runtime_closure_repair_rc1"
DEFAULT_STATE_PATH = RESULT / "w3_orchestrator_state_v2.json"
DEFAULT_FORMAL_GATE = REPAIR_ROOT / "formal_authorization_gate.json"
DEFAULT_SLURM_ATTEMPTS = RESULT / "slurm_attempts_v2.csv"
DEFAULT_TRAINING_ADEQUACY = RESULT / "training_adequacy_v2.csv"

FORMAL_JOBS = [
    {"logical_run_id": "scar_seed20260724", "pathology": "scar", "seed": 20260724, "partition": "htzhulab", "gres": "gpu:1", "variants": ["scar_cascade_control", "scar_srr_cascade"]},
    {"logical_run_id": "edema_seed20260724", "pathology": "edema", "seed": 20260724, "partition": "htzhulab", "gres": "gpu:1", "variants": ["edema_zone_control", "edema_srr_zone_cascade"]},
    {"logical_run_id": "scar_seed20260725", "pathology": "scar", "seed": 20260725, "partition": "a100-gpu", "gres": "gpu:nvidia_a100-pcie-40gb:1", "variants": ["scar_cascade_control", "scar_srr_cascade"]},
    {"logical_run_id": "edema_seed20260725", "pathology": "edema", "seed": 20260725, "partition": "a100-gpu", "gres": "gpu:nvidia_a100-pcie-40gb:1", "variants": ["edema_zone_control", "edema_srr_zone_cascade"]},
]

ACTIVE_STATES = {
    "BOOT_FAIL_REQUEUE_HOLD",
    "CONFIGURING",
    "COMPLETING",
    "PENDING",
    "PREEMPTED_REQUEUE_HOLD",
    "REQUEUED",
    "RESIZING",
    "RUNNING",
    "SIGNALING",
    "SPECIAL_EXIT",
    "STAGE_OUT",
    "STOPPED",
    "SUBMITTED_NEEDS_MONITOR",
    "SUSPENDED",
}

TERMINAL_REPLACEABLE_STATES = {
    "BOOT_FAIL",
    "CANCELLED",
    "COMPLETED",
    "DEADLINE",
    "FAILED",
    "NODE_FAIL",
    "OUT_OF_MEMORY",
    "PREEMPTED",
    "REVOKED",
    "TIMEOUT",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    return json.loads(path.read_text()) if path.exists() else dict(default)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def formal_gate_decision(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    payload = json.loads(path.read_text())
    return str(payload.get("decision", "UNKNOWN"))


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def submit_job(job: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    export_vars = (
        f"ALL,CARE_FORMAL_LOGICAL_RUN_ID={job['logical_run_id']},CARE_FORMAL_PATHOLOGY={job['pathology']},"
        f"CARE_FORMAL_SEED={job['seed']},CARE_FORMAL_VARIANTS={'|'.join(job['variants'])},"
        "CARE_FORMAL_STEPS=6250,CARE_FORMAL_VALIDATION_STEPS=1250|2500|3750|5000|6250"
    )
    cmd = [
        "sbatch",
        "--parsable",
        f"--job-name=SCRR1_{job['logical_run_id']}",
        f"--partition={job['partition']}",
        "--qos=gpu_access",
        f"--gres={job['gres']}",
        f"--export={export_vars}",
        "jobs/care_mm/run_care_srr_cascade_formal_training.sh",
    ]
    if dry_run:
        return {"job_id": "DRY_RUN", "command": " ".join(cmd), "state": "DRY_RUN_NOT_SUBMITTED"}
    proc = run(cmd)
    return {"job_id": proc.stdout.strip(), "command": " ".join(cmd), "state": "SUBMITTED_NEEDS_MONITOR"}


def normalize_slurm_state(state: str) -> str:
    text = str(state or "").strip()
    if not text:
        return ""
    return text.split()[0].split("+", 1)[0]


def live_slurm_state(job_id: str) -> str:
    if not str(job_id).isdigit():
        return ""
    sacct = run(["sacct", "-j", str(job_id), "--format=State", "-n", "-P"], check=False)
    if sacct.returncode == 0:
        for line in sacct.stdout.splitlines():
            state = normalize_slurm_state(line)
            if state:
                return state
    squeue = run(["squeue", "-j", str(job_id), "-h", "-o", "%T"], check=False)
    if squeue.returncode == 0:
        for line in squeue.stdout.splitlines():
            state = normalize_slurm_state(line)
            if state:
                return state
    return ""


def should_replace_existing(existing: dict[str, Any], *, dry_run: bool) -> tuple[bool, str]:
    job_id = str(existing.get("job_id", ""))
    recorded = normalize_slurm_state(str(existing.get("state", "")))
    if job_id == "DRY_RUN" or recorded == "DRY_RUN_NOT_SUBMITTED":
        return False, "dry_run_already_registered"
    if not job_id.isdigit():
        return True, "no_slurm_job_id"
    observed = recorded if dry_run else live_slurm_state(job_id)
    if observed in ACTIVE_STATES:
        return False, f"active_slurm_state:{observed}"
    if observed in TERMINAL_REPLACEABLE_STATES:
        return True, f"terminal_slurm_state:{observed}"
    if recorded in TERMINAL_REPLACEABLE_STATES:
        return True, f"recorded_terminal_state:{recorded}"
    return False, f"unknown_existing_state:{observed or recorded or 'missing'}"


def archive_replaced_attempt(existing: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "job_id": existing.get("job_id", ""),
        "state": existing.get("state", ""),
        "partition": existing.get("partition", ""),
        "command": existing.get("command", ""),
        "replacement_reason": reason,
        "formal_training_credit": 0,
        "archived_utc": utc_now(),
    }


def discover_live_job_ids(state: dict[str, Any]) -> list[str]:
    ids = []
    for run in state.get("logical_runs", {}).values():
        job_id = str(run.get("job_id", ""))
        if job_id.isdigit():
            ids.append(job_id)
    return ids


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["logical_run_id"])
        writer.writeheader()
        writer.writerows(rows)


def update_receipts(state: dict[str, Any], *, slurm_attempts: Path, training_adequacy: Path) -> None:
    attempt_rows = []
    adequacy_rows = []
    for job in FORMAL_JOBS:
        run_state = state.get("logical_runs", {}).get(job["logical_run_id"], {})
        for index, old in enumerate(run_state.get("attempt_history", []), start=1):
            attempt_rows.append(
                {
                    "logical_run_id": job["logical_run_id"],
                    "pathology": job["pathology"],
                    "seed": job["seed"],
                    "variants": "|".join(job["variants"]),
                    "partition": old.get("partition", job["partition"]),
                    "qos": "gpu_access",
                    "slurm_job_id": old.get("job_id", ""),
                    "attempt_number": index,
                    "state": old.get("state", ""),
                    "command": old.get("command", ""),
                    "script_sha256": sha256_file(ROOT / "jobs/care_mm/run_care_srr_cascade_formal_training.sh"),
                    "formal_training_credit": 0,
                    "replacement_reason": old.get("replacement_reason", ""),
                    "decision": "ZERO_CREDIT_REPLACED_ATTEMPT",
                }
            )
        job_id = str(run_state.get("job_id", "NOT_SUBMITTED_PREFORMAL_GATE"))
        status = str(run_state.get("state", "NOT_SUBMITTED_PREFORMAL_GATE"))
        attempt_number = len(run_state.get("attempt_history", [])) + 1
        attempt_rows.append(
            {
                "logical_run_id": job["logical_run_id"],
                "pathology": job["pathology"],
                "seed": job["seed"],
                "variants": "|".join(job["variants"]),
                "partition": job["partition"],
                "qos": "gpu_access",
                "slurm_job_id": job_id,
                "attempt_number": attempt_number,
                "state": status,
                "command": run_state.get("command", ""),
                "script_sha256": sha256_file(ROOT / "jobs/care_mm/run_care_srr_cascade_formal_training.sh"),
                "formal_training_credit": 0,
                "replacement_reason": run_state.get("replacement_reason", ""),
                "decision": "NEEDS_MONITOR" if job_id.isdigit() else "NOT_SUBMITTED_PREFORMAL_GATE",
            }
        )
        adequacy_rows.append(
            {
                "logical_run_id": job["logical_run_id"],
                "formal_training_job_id": job_id,
                "control_steps_completed": int(run_state.get("control_steps_completed", 0)),
                "srr_steps_completed": int(run_state.get("srr_steps_completed", 0)),
                "required_steps_each": 6250,
                "validation_steps_required": "1250|2500|3750|5000|6250",
                "validation_events_completed": int(run_state.get("validation_events_completed", 0)),
                "state": status,
                "decision": "PASS" if int(run_state.get("control_steps_completed", 0)) == 6250 and int(run_state.get("srr_steps_completed", 0)) == 6250 else "NEEDS_MONITOR",
            }
        )
    write_csv(slurm_attempts, attempt_rows)
    write_csv(training_adequacy, adequacy_rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--formal-gate", type=Path, default=DEFAULT_FORMAL_GATE)
    parser.add_argument("--slurm-attempts", type=Path, default=DEFAULT_SLURM_ATTEMPTS)
    parser.add_argument("--training-adequacy", type=Path, default=DEFAULT_TRAINING_ADEQUACY)
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps({"state_file": str(args.state_file), "hardcoded_job_ids": False, "formal_gate": str(args.formal_gate)}, indent=2))
        return 0

    state = load_json(args.state_file, {"schema_version": 2, "logical_runs": {}})
    gate = formal_gate_decision(args.formal_gate)
    state.update(
        {
            "schema_version": 2,
            "updated_utc": utc_now(),
            "formal_authorization_gate": gate,
            "hardcoded_job_ids": False,
            "discovered_job_ids": discover_live_job_ids(state),
        }
    )
    if gate != "PASS":
        state["decision"] = "NEEDS_REPAIR_PREFORMAL_GATE_NOT_PASS"
        state["notes"] = "Formal submission is forbidden until formal_authorization_gate.json decision PASS."
        write_json(args.state_file, state)
        update_receipts(state, slurm_attempts=args.slurm_attempts, training_adequacy=args.training_adequacy)
        print(json.dumps(state, indent=2, sort_keys=True))
        return 2
    if args.submit:
        state.setdefault("logical_runs", {})
        for job in FORMAL_JOBS:
            existing = state["logical_runs"].get(job["logical_run_id"], {})
            if existing:
                replace, reason = should_replace_existing(existing, dry_run=args.dry_run)
                if not replace:
                    continue
                history = list(existing.get("attempt_history", []))
                history.append(archive_replaced_attempt(existing, reason=reason))
            else:
                history = []
                reason = "initial_attempt"
            submitted = submit_job(job, dry_run=args.dry_run)
            state["logical_runs"][job["logical_run_id"]] = {
                **job,
                **submitted,
                "attempt_history": history,
                "attempt_number": len(history) + 1,
                "replacement_reason": reason,
            }
    state["decision"] = "NEEDS_MONITOR"
    state["notes"] = "Formal authorization gate PASS; logical jobs submitted or already registered and require terminal accounting before completion."
    state["discovered_job_ids"] = discover_live_job_ids(state)
    write_json(args.state_file, state)
    update_receipts(state, slurm_attempts=args.slurm_attempts, training_adequacy=args.training_adequacy)
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
