#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _find_worktree_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "AGENTS.md").is_file():
            return parent
    return start.parents[2]


WORKTREE_ROOT = _find_worktree_root(Path(__file__).resolve())
import sys as _sys
_sys.path.insert(0, str(WORKTREE_ROOT))

from src.care_myocardium.training.care_myopath_pilot.contracts import known_bad_matrix

REQUIRED = [
    "controller_context.json",
    "controller_ledger.csv",
    "implementation_snapshot.md",
    "a0_identity_report.json",
    "a1_summary.json",
    "a2_summary.json",
    "a3_summary.json",
    "casewise_metrics.csv",
    "proposal_metrics.csv",
    "component_intervention.csv",
    "help_harm.csv",
    "slurm_accounting.csv",
    "finalizer_state.json",
    "known_bad_report.json",
    "mapper_report_final.md",
    "controller_report.md",
    "completion_check.md",
    "MANIFEST.md",
]
FORBIDDEN = {"PENDING", "RUNNING", "NEEDS_MONITOR", "JOB_SUBMITTED", "AWAITING_SACCT"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(results_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    missing = [name for name in REQUIRED if not (results_dir / name).exists()]
    if missing:
        errors.append(f"missing required outputs: {missing}")
    finalizer = load_json(results_dir / "finalizer_state.json") if (results_dir / "finalizer_state.json").exists() else {}
    decision = finalizer.get("controller_verification_decision")
    if decision not in {"VERIFIED_COMPLETE", "NEEDS_REPAIR", "OPERATIONALLY_BLOCKED"}:
        errors.append("invalid controller_verification_decision")
    if decision == "VERIFIED_COMPLETE":
        errors.append("VERIFIED_COMPLETE is not allowed for blocked pre-training packet")
    if finalizer.get("final_status") != "blocked":
        errors.append("blocked packet final_status must be blocked")
    if any(str(v) in FORBIDDEN for v in finalizer.values()):
        errors.append("finalizer_state contains forbidden monitor/pending completion state")
    a0 = load_json(results_dir / "a0_identity_report.json") if (results_dir / "a0_identity_report.json").exists() else {}
    if a0.get("status") != "PASS":
        errors.append("A0 identity report must PASS")
    if float(a0.get("fp32_max_abs_error", 1.0)) > 1e-6:
        errors.append("A0 fp32 max_abs_error exceeds 1e-6")
    if int(a0.get("changed_argmax_voxels", 1)) != 0:
        errors.append("A0 changed_argmax_voxels must be 0")
    for name in ["a1_summary.json", "a2_summary.json", "a3_summary.json"]:
        payload = load_json(results_dir / name) if (results_dir / name).exists() else {}
        if payload.get("formal_training_started"):
            errors.append(f"{name} claims formal training started despite blocked metric receipt")
        if payload.get("fold1_outer_accessed"):
            errors.append(f"{name} claims fold1 outer access")
    kb_rows = known_bad_matrix()
    if not all(row["rejected"] for row in kb_rows):
        errors.append("known-bad matrix did not reject every fixture")
    return {
        "status": "PASS" if not errors else "FAIL",
        "controller_verification_decision": decision,
        "errors": errors,
        "required_outputs_checked": REQUIRED,
        "known_bad_cases": kb_rows,
        "blocked_packet_semantics": "PASS" if decision == "OPERATIONALLY_BLOCKED" and not errors else "FAIL",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, default=Path("results/20260731_care_myopath_pr_a0_a3_feasibility"))
    ap.add_argument("--write-report", action="store_true")
    args = ap.parse_args()
    report = validate(args.results_dir)
    if args.write_report:
        (args.results_dir / "strict_validator_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
