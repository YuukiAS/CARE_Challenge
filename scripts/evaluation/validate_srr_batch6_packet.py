#!/usr/bin/env python3
"""Validate Batch6 executor stop packet for fixed-overfit failure."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results/20260721_srr_batch6_final_objective_alignment"
REQUIRED_FILES = (
    "batch5_reconciliation.md",
    "resolved_loss_weights.csv",
    "pure_intervention_metrics.csv",
    "proposal_roi_metrics.csv",
    "implementation_snapshot.md",
    "fixed_batch_overfit.json",
    "loss_gradient_authority.csv",
    "training_adequacy.json",
    "slurm_attempts.csv",
    "finalizer_state.json",
    "completion_check.md",
    "commands_run.md",
    "MANIFEST.md",
)
REQUIRED_JOB_IDS = {"59737558", "59737686", "59737738"}
TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "PREEMPTED"}


class ValidationError(RuntimeError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValidationError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def finite_cell(row: dict[str, str], key: str) -> bool:
    value = str(row.get(key, "")).strip()
    if value == "":
        return False
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise ValidationError(f"missing JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_packet(result_root: Path) -> dict[str, Any]:
    for name in REQUIRED_FILES:
        expect((result_root / name).is_file(), f"missing required packet file: {name}")

    weights = read_csv(result_root / "resolved_loss_weights.csv")
    for component, expected in (
        ("loss_final_scar_pathology", 1.0),
        ("loss_final_edema_t2_present_pathology", 1.0),
        ("loss_production_gate_repair_preserve", 0.2),
        ("loss_correction_opportunity", 0.0),
        ("loss_branch_arbitration_consistency", 0.0),
        ("loss_bounded_correction", 0.0),
        ("loss_refiner_final_label_effect", 0.0),
    ):
        matches = [row for row in weights if row.get("loss_component") == component]
        expect(matches, f"missing resolved loss component: {component}")
        expect(float(matches[0]["resolved_weight"]) == expected, f"wrong resolved weight for {component}")

    pure = read_csv(result_root / "pure_intervention_metrics.csv")
    expect({row.get("mode") for row in pure} >= {
        "anchor_identity_control",
        "full_learned_gate",
        "full_gate_one",
        "full_gate_zero",
        "proposal_only_gate_one",
        "refiner_only_gate_one",
    }, "pure intervention modes incomplete")
    for mode, proposal, refiner in (
        ("proposal_only_gate_one", "True", "False"),
        ("refiner_only_gate_one", "False", "True"),
    ):
        rows = [row for row in pure if row.get("mode") == mode]
        expect(rows, f"missing pure intervention row for {mode}")
        expect(all(row.get("proposal_consumed") == proposal for row in rows), f"{mode} proposal purity failed")
        expect(all(row.get("refiner_consumed") == refiner for row in rows), f"{mode} refiner purity failed")

    proposal_roi = read_csv(result_root / "proposal_roi_metrics.csv")
    expect(len(proposal_roi) >= 44 * 2 * 6, "proposal/ROI rows do not cover 44 cases x 2 pathologies x 6 modes")
    for key in (
        "proposal_voxel_precision",
        "proposal_voxel_recall",
        "proposal_lesion_recall",
        "proposal_component_count",
        "proposal_remote_fp_count",
        "proposal_remote_fp_volume_mm3",
        "roi_gt_coverage",
        "roi_outside_ratio",
        "refiner_residual_abs_mean",
        "changed_voxels_vs_anchor",
        "dice_delta_vs_anchor",
        "hd95_delta_vs_anchor",
        "component_delta",
        "remote_fp_delta_mm3",
    ):
        expect(all(finite_cell(row, key) for row in proposal_roi), f"proposal/ROI field blank or nonfinite: {key}")

    overfit = load_json(result_root / "fixed_batch_overfit.json")
    expect(overfit.get("status") == "FAIL", "fixed overfit should be a recorded failed gate")
    expect(overfit.get("optimizer_steps") == 60, "fixed overfit optimizer steps must remain 60")
    expect(overfit.get("case_ids") == ["Case2002", "Case1002"], "fixed overfit case IDs drifted")
    checks = overfit.get("checks", {})
    expect(checks.get("all_losses_finite") is True, "overfit losses not finite")
    expect(checks.get("no_t2_edema_exact_zero") is True, "no-T2 edema exact-zero failed")
    expect(float(checks.get("scar_final_pathology_loss_relative_decrease", 0.0)) < 0.15, "stop reason no longer matches scar gate failure")

    adequacy = load_json(result_root / "training_adequacy.json")
    expect(adequacy.get("experiment_adequacy_decision") == "OVERFIT_OR_IMPLEMENTATION_FAILED", "wrong adequacy decision")
    expect(adequacy.get("formal_training_submitted") is False, "formal training was submitted despite failed overfit")
    expect(adequacy.get("formal_300_step_status") == "NOT_SUBMITTED_FIXED_OVERFIT_GATE_FAILED", "wrong formal 300 status")

    attempts = read_csv(result_root / "slurm_attempts.csv")
    job_ids = {row.get("job_id") for row in attempts}
    expect(REQUIRED_JOB_IDS <= job_ids, f"missing required Slurm attempts: {sorted(REQUIRED_JOB_IDS - job_ids)}")
    expect(all(row.get("state") in TERMINAL_STATES for row in attempts), "non-terminal Slurm attempt in packet")
    expect(all(row.get("stage") == "fixed_batch_overfit" for row in attempts), "unexpected Slurm stage submitted")
    expect(all(row.get("formal_training_credit") == "0" for row in attempts), "formal training credit recorded before overfit pass")

    finalizer = load_json(result_root / "finalizer_state.json")
    expect(finalizer.get("all_submitted_jobs_terminal") is True, "finalizer state does not mark jobs terminal")
    expect(finalizer.get("formal_300_step_submitted") is False, "finalizer says formal 300 submitted")
    expect(finalizer.get("no_push") is True, "finalizer no_push missing")

    completion = (result_root / "completion_check.md").read_text(encoding="utf-8")
    expect("Formal 300-step calibration was not submitted" in completion, "completion check missing formal stop")
    expect("fixed overfit gate failed" in completion.lower(), "completion check missing overfit failure")

    return {
        "status": "BATCH6_STOP_PACKET_VALIDATION_PASS",
        "result_root": str(result_root.relative_to(REPO_ROOT)),
        "slurm_attempt_count": len(attempts),
        "required_job_ids": sorted(REQUIRED_JOB_IDS),
        "formal_training_submitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", default=str(RESULT_ROOT.relative_to(REPO_ROOT)))
    args = parser.parse_args()
    try:
        payload = validate_packet(REPO_ROOT / args.result_root)
    except ValidationError as exc:
        print(json.dumps({"status": "BATCH6_STOP_PACKET_VALIDATION_FAIL", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
