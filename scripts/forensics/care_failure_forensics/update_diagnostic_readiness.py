#!/usr/bin/env python3
"""Record readiness for the required CARE forensics diagnostic waves.

This script does not train, infer, upload, or select checkpoints. It records the
current operational state that determines whether the mandatory forensic
diagnostics may proceed.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


TASK_KEY = "20260730_care_failure_forensics_deep_research_packet"
DEFAULT_ROOT = Path("results") / TASK_KEY
REQUIRED_DIAGNOSTICS = [
    "D0_FULL_PRETRAINED_IDENTITY",
    "D1_DECODER_RESET_ENCODER_FROZEN",
    "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE",
    "D3_FULL_MODEL_SHORT_FINETUNE",
    "FEATURE_PROBE_HELDOUT",
    "MOSAIC_RECIPE_DECOMPOSITION",
    "CINE_TEMPORAL_PROBE",
]


def run(cmd: list[str], cwd: Path) -> str:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        return proc.stdout.strip()
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"ERROR: {exc}"


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_ledger(root: Path, repo: Path, phase: str, decision: str, next_action: str) -> None:
    path = root / "controller_ledger.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["timestamp_utc", "phase", "git_head", "task_hash", "job_states", "decision", "next_action"]
    new = not path.exists()
    head = run(["git", "rev-parse", "HEAD"], repo)
    task_path = repo / "prompts/tasks/20260730_care_failure_forensics_deep_research_packet.md"
    task_hash = run(["sha256sum", str(task_path)], repo).split()[0] if task_path.exists() else "MISSING"
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        if new:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "phase": phase,
                "git_head": head,
                "task_hash": task_hash,
                "job_states": "NO_NEW_JOB_PRELIGHT_ONLY",
                "decision": decision,
                "next_action": next_action,
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--allocation", default="61220581")
    parser.add_argument("--preflight-json", type=Path, required=True)
    args = parser.parse_args()

    root = args.root
    repo = args.repo
    preflight = read_json(args.preflight_json)
    timestamp = datetime.now(timezone.utc).isoformat()
    completed = set(read_json(root / "finalizer_state.json").get("completed_diagnostics", []))
    missing = [name for name in REQUIRED_DIAGNOSTICS if name not in completed]

    plan_rows = [
        {
            "diagnostic": "D0_FULL_PRETRAINED_IDENTITY",
            "phase": "F7B",
            "depends_on": "bound Dataset501 fold0 stock nnU-Net checkpoint and evaluator",
            "allowed_split": "fold0_inner_select",
            "forbidden_split": "fold0_outer",
            "execution_mode": "existing_allocation_overlap",
            "state": "READY_TO_START",
            "next_action": "run identity replay and compare against existing baseline before D1-D3",
        },
        {
            "diagnostic": "D1_DECODER_RESET_ENCODER_FROZEN",
            "phase": "F7B",
            "depends_on": "D0_FULL_PRETRAINED_IDENTITY terminal PASS",
            "allowed_split": "fold0_actual_train_to_inner_select",
            "forbidden_split": "fold0_outer",
            "execution_mode": "single_gpu_slurm_after_D0",
            "state": "BLOCKED_BY_D0",
            "next_action": "train 1500 optimizer steps only if D0 reproduces baseline",
        },
        {
            "diagnostic": "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE",
            "phase": "F7B",
            "depends_on": "D0_FULL_PRETRAINED_IDENTITY terminal PASS",
            "allowed_split": "fold0_actual_train_to_inner_select",
            "forbidden_split": "fold0_outer",
            "execution_mode": "single_gpu_slurm_after_D0",
            "state": "BLOCKED_BY_D0",
            "next_action": "train 3000 optimizer steps only if D0 reproduces baseline",
        },
        {
            "diagnostic": "D3_FULL_MODEL_SHORT_FINETUNE",
            "phase": "F7B",
            "depends_on": "D0_FULL_PRETRAINED_IDENTITY terminal PASS",
            "allowed_split": "fold0_actual_train_to_inner_select",
            "forbidden_split": "fold0_outer",
            "execution_mode": "single_gpu_slurm_after_D0",
            "state": "BLOCKED_BY_D0",
            "next_action": "fine-tune 1000 optimizer steps with lr=1e-5",
        },
        {
            "diagnostic": "FEATURE_PROBE_HELDOUT",
            "phase": "F7",
            "depends_on": "feature tensor binding for nnU-Net/PRISM/MoSAIC",
            "allowed_split": "actual_train_probe_train_inner_select_probe_eval",
            "forbidden_split": "fold0_outer",
            "execution_mode": "single_gpu_or_cpu_after_binding",
            "state": "NEEDS_FEATURE_BINDING",
            "next_action": "write feature extraction wrapper or mark missing features by model",
        },
        {
            "diagnostic": "MOSAIC_RECIPE_DECOMPOSITION",
            "phase": "F8",
            "depends_on": "MoSAIC source and 7 checkpoint roles bound",
            "allowed_split": "inner_select",
            "forbidden_split": "fold0_outer_tuning",
            "execution_mode": "single_gpu_fixed_recipe_replay",
            "state": "NEEDS_RECIPE_BINDING",
            "next_action": "bind checkpoint roles and implement M0-M10 fixed ablation replay",
        },
        {
            "diagnostic": "CINE_TEMPORAL_PROBE",
            "phase": "F9B",
            "depends_on": "Cine ED/reference frame and temporal feature binding",
            "allowed_split": "patient_level_train_eval",
            "forbidden_split": "hosted_validation",
            "execution_mode": "cpu_or_single_gpu_light_probe",
            "state": "NEEDS_CINE_BINDING",
            "next_action": "bind Cine manifests and run ED-only versus temporal lightweight probe",
        },
    ]

    with (root / "required_diagnostic_wave_status.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["diagnostic", "phase", "depends_on", "allowed_split", "forbidden_split", "execution_mode", "state", "next_action"]
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(plan_rows)

    plan = {
        "status": "NEEDS_REPAIR",
        "updated_utc": timestamp,
        "repo_head": run(["git", "rev-parse", "HEAD"], repo),
        "origin_main": run(["git", "rev-parse", "origin/main"], repo),
        "existing_allocation": args.allocation,
        "gpu_preflight": preflight,
        "missing_required_diagnostics": missing,
        "first_executable_wave": "D0_FULL_PRETRAINED_IDENTITY",
        "sequencing_rule": "D1-D3 must not start until D0 reproduces the bound stock nnU-Net baseline.",
        "no_outer_tuning": True,
        "no_new_architecture": True,
        "no_validation_upload": True,
        "notes": [
            "This file records readiness only; it is not completion evidence.",
            "User later explicitly requested commit/push of the partial packet; the original task contract remains no-auto-push for future runtime work.",
        ],
        "waves": plan_rows,
    }
    write_json(root / "diagnostic_execution_plan.json", plan)
    write_json(root / "slurm_diagnostic_preflight_receipt.json", {"status": "PASS", "updated_utc": timestamp, "allocation": args.allocation, **preflight})

    finalizer = read_json(root / "finalizer_state.json")
    finalizer.update(
        {
            "status": "NEEDS_REPAIR",
            "updated_utc": timestamp,
            "completed_diagnostics": sorted(completed),
            "missing_required_diagnostics": missing,
            "all_jobs_terminal": True,
            "new_slurm_jobs_submitted": False,
            "diagnostic_execution_plan": "diagnostic_execution_plan.json",
            "slurm_diagnostic_preflight_receipt": "slurm_diagnostic_preflight_receipt.json",
            "next_required_action": "run D0_FULL_PRETRAINED_IDENTITY using bound stock nnU-Net before any decoder-reset training",
        }
    )
    write_json(root / "finalizer_state.json", finalizer)
    append_ledger(root, repo, "F0B_DIAGNOSTIC_READINESS", "NEEDS_REPAIR_D0_READY", "run D0 identity replay before D1-D3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
