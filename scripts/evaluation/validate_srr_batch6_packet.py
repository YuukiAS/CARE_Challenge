#!/usr/bin/env python3
"""Validate Batch6 final-objective alignment packet after formal300 gate."""

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
TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "PREEMPTED"}
REQUIRED_FILES = (
    "controller_context.json",
    "controller_ledger.csv",
    "controller_bootstrap_snapshot.md",
    "batch5_reconciliation.md",
    "resolved_loss_weights.csv",
    "pure_intervention_metrics.csv",
    "proposal_roi_metrics.csv",
    "implementation_snapshot.md",
    "fixed_batch_overfit.json",
    "fixed_batch_overfit_trace.csv",
    "loss_gradient_authority.csv",
    "training_adequacy.json",
    "checkpoint_selection.csv",
    "subgroup_metrics.csv",
    "help_harm.csv",
    "casewise_metrics.csv",
    "final_mechanism_interventions.csv",
    "slurm_attempts.csv",
    "finalizer_state.json",
    "mapper_report_draft.md",
    "architecture_delta_draft.md",
    "mapper_report_final.md",
    "architecture_delta_final.md",
    "controller_report.md",
    "completion_check.md",
    "commands_run.md",
    "MANIFEST.md",
)
REQUIRED_JOB_IDS = {"59743323", "59743935", "59744053", "59744540", "59744941"}
REQUIRED_MODES = {
    "anchor_identity_control",
    "full_learned_gate",
    "full_gate_one",
    "full_gate_zero",
    "proposal_only_gate_one",
    "refiner_only_gate_one",
}

class ValidationError(RuntimeError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise ValidationError(f"missing JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValidationError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def finite(value: str | None, *, allow_blank: bool = False) -> bool:
    value = "" if value is None else str(value).strip()
    if value == "":
        return bool(allow_blank)
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False


def row_for(rows: list[dict[str, str]], **query: str) -> dict[str, str]:
    for row in rows:
        if all(str(row.get(k)) == str(v) for k, v in query.items()):
            return row
    raise ValidationError(f"missing row: {query}")


def validate_packet(result_root: Path) -> dict[str, Any]:
    for name in REQUIRED_FILES:
        expect((result_root / name).is_file(), f"missing required packet file: {name}")

    weights = read_csv(result_root / "resolved_loss_weights.csv")
    for component, expected in (
        ("loss_final_scar_pathology", 1.0),
        ("loss_final_scar_correction_directionality", 1.0),
        ("loss_final_scar_anchor_error_pathology", 20.0),
        ("loss_final_edema_t2_present_pathology", 1.0),
        ("loss_final_edema_anchor_error_pathology", 20.0),
        ("loss_production_gate_repair_preserve", 0.2),
        ("loss_correction_opportunity", 0.0),
        ("loss_branch_arbitration_consistency", 0.0),
        ("loss_bounded_correction", 0.0),
        ("loss_refiner_final_label_effect", 0.0),
    ):
        row = row_for(weights, loss_component=component)
        expect(float(row["resolved_weight"]) == expected, f"wrong resolved weight for {component}")

    pure = read_csv(result_root / "pure_intervention_metrics.csv")
    expect({row.get("mode") for row in pure} >= REQUIRED_MODES, "pure intervention modes incomplete")
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
        "proposal_voxel_precision", "proposal_voxel_recall", "proposal_lesion_recall",
        "proposal_component_count", "proposal_remote_fp_count", "proposal_remote_fp_volume_mm3",
        "roi_gt_coverage", "roi_outside_ratio", "refiner_residual_abs_mean",
        "changed_voxels_vs_anchor", "dice_delta_vs_anchor", "hd95_delta_vs_anchor",
        "component_delta", "remote_fp_delta_mm3",
    ):
        expect(all(finite(row.get(key)) for row in proposal_roi), f"proposal/ROI field blank or nonfinite: {key}")

    overfit = load_json(result_root / "fixed_batch_overfit.json")
    expect(overfit.get("status") == "PASS", "fixed overfit must pass before formal300")
    expect(overfit.get("optimizer_steps") == 60, "fixed overfit optimizer steps must be 60")
    expect(overfit.get("formal_training_credit") == 0, "fixed overfit must have zero formal credit")
    expect(overfit.get("case_ids") == ["Case2002", "Case1002"], "fixed overfit case IDs drifted")
    checks = overfit.get("checks", {})
    expect(float(checks.get("combined_final_pathology_loss_relative_decrease", 0.0)) >= 0.20, "combined overfit gate failed")
    expect(float(checks.get("scar_final_pathology_loss_relative_decrease", 0.0)) >= 0.15, "scar overfit gate failed")
    expect(float(checks.get("edema_final_pathology_loss_relative_decrease", 0.0)) >= 0.15, "edema overfit gate failed")
    expect(float(checks.get("gate_loss_relative_decrease", 0.0)) >= 0.10, "gate overfit gate failed")
    expect(float(checks.get("production_gate_repair_gradient_l2_max", 0.0)) > 0.0, "missing production gate repair gradient")
    expect(float(checks.get("final_logits_max_abs_change_from_step0", 0.0)) > 0.0, "final logits did not change")
    expect(checks.get("no_t2_edema_exact_zero") is True, "no-T2 edema exact-zero failed")
    expect(float(checks.get("save_reload_final_logits_max_abs_delta", 1.0)) <= 1e-6, "fixed overfit checkpoint roundtrip failed")

    adequacy = load_json(result_root / "training_adequacy.json")
    expect(adequacy.get("formal_training_submitted") is True, "formal300 should be recorded as submitted")
    expect(adequacy.get("formal_300_step_status") == "COMPLETED", "formal300 did not complete")
    expect(adequacy.get("actual_optimizer_steps") == 300, "formal300 optimizer steps must be exactly 300")
    expect(adequacy.get("train_cases") == 176 and adequacy.get("val_cases") == 44 and adequacy.get("eval_cases") == 44, "formal300 split/case counts drifted")
    expect(adequacy.get("full_volume_eval_steps") == [100, 200, 300], "formal300 eval cadence drifted")
    gate = adequacy.get("continuation_gate", {})
    expect(gate.get("decision") == "FAIL", "current packet should stop at failed step300 gate")
    expect(adequacy.get("formal_900_step_status") == "SKIPPED_STEP300_GATE_FAILED", "900 must be skipped after failed step300 gate")
    expect(gate.get("checks", {}).get("mean_delta") is False, "mean-delta check should be the failing gate")
    for name in ("each_delta", "help_harm", "hd95", "remote_fp", "no_t2", "finite_and_grad"):
        expect(gate.get("checks", {}).get(name) is True, f"unexpected failed continuation subgate: {name}")
    expect(float(gate.get("mean_scar_edema_positive_dice_delta", 0.0)) < float(gate.get("minimum_mean_scar_edema_positive_dice_delta", 0.003)), "mean gate failure not self-consistent")
    expect(gate.get("no_t2_edema_exact_zero") is True, "formal300 no-T2 exact-zero failed")
    expect(gate.get("gradient_gate", {}).get("pass") is True, "formal300 gradient gate failed")

    selection = read_csv(result_root / "checkpoint_selection.csv")
    expect(len(selection) == 6, "checkpoint selection must contain 3 steps x 2 pathologies")
    for step in ("100", "200", "300"):
        for pathology in ("myops_scar", "myops_edema"):
            row = row_for(selection, total_step=step, pathology=pathology, group="gt_positive_only")
            expect(finite(row.get("dice_delta_mean")), f"missing dice delta for {pathology} step {step}")
    row_for(selection, total_step="300", pathology="myops_scar", selected_for_stage300_gate="True")
    row_for(selection, total_step="300", pathology="myops_edema", selected_for_stage300_gate="True")

    casewise = read_csv(result_root / "casewise_metrics.csv")
    expect(len(casewise) == 3 * 44 * 2, "casewise metrics must cover 3 eval steps x 44 cases x 2 pathologies")
    help_rows = read_csv(result_root / "help_harm.csv")
    expect(len(help_rows) >= 59, "help/harm rows missing positive pathology cases")

    interventions = read_csv(result_root / "final_mechanism_interventions.csv")
    expect(len(interventions) == 24, "final interventions must cover 6 modes x 2 pathologies x 2 populations")
    expect({row.get("mode") for row in interventions} == REQUIRED_MODES, "final intervention modes drifted")
    for row in interventions:
        expect(row.get("checkpoint_global_step") == "300", "final interventions did not use selected step300 checkpoint")
        expect(row.get("checkpoint_sha256") == adequacy.get("selected_checkpoint_sha256"), "final intervention checkpoint sha mismatch")
        expect(row.get("slurm_state") == "COMPLETED" and row.get("slurm_exit_code") == "0:0", "final intervention Slurm status not terminal success")
        expect(finite(row.get("mean_dice_delta_vs_anchor")), "intervention dice delta missing")
    identity = [row for row in interventions if row.get("mode") == "anchor_identity_control"]
    expect(identity and all(abs(float(row["mean_dice_delta_vs_anchor"])) == 0.0 for row in identity), "anchor identity control not exact")

    attempts = read_csv(result_root / "slurm_attempts.csv")
    job_ids = {row.get("job_id") for row in attempts}
    expect(REQUIRED_JOB_IDS <= job_ids, f"missing required Slurm attempts: {sorted(REQUIRED_JOB_IDS - job_ids)}")
    expect(all(row.get("state") in TERMINAL_STATES for row in attempts), "non-terminal Slurm attempt in packet")
    expect(any(row.get("stage") == "formal_300" and row.get("state") == "COMPLETED" and row.get("formal_training_credit") == "300" for row in attempts), "missing completed formal300 credit row")
    expect(not any(row.get("stage") == "formal_900" for row in attempts), "formal900 attempt exists despite failed gate")
    expect(all(row.get("formal_training_credit") == "0" for row in attempts if row.get("stage") != "formal_300" or row.get("state") != "COMPLETED"), "failed/nonformal attempts have formal credit")

    finalizer = load_json(result_root / "finalizer_state.json")
    expect(finalizer.get("all_submitted_jobs_terminal") is True, "finalizer does not mark jobs terminal")
    expect(finalizer.get("formal_300_step_submitted") is True, "finalizer missing formal300 submission")
    expect(finalizer.get("formal_900_step_submitted") is False, "finalizer wrongly submitted 900")
    expect(finalizer.get("controller_verification_decision") == "VERIFIED_COMPLETE", "controller decision not verified complete")
    expect(finalizer.get("no_push") is True, "finalizer no_push missing")

    completion = (result_root / "completion_check.md").read_text(encoding="utf-8")
    for text in ("fixed Case2002+Case1002 60-step overfit: PASS", "Formal 300 Gate", "no 900-step extension was submitted", "controller_verification_decision: VERIFIED_COMPLETE"):
        expect(text in completion, f"completion check missing: {text}")

    return {
        "status": "BATCH6_PACKET_VALIDATION_PASS",
        "result_root": str(result_root.relative_to(REPO_ROOT)),
        "fixed_overfit_status": overfit.get("status"),
        "formal300_status": adequacy.get("formal_300_step_status"),
        "formal900_status": adequacy.get("formal_900_step_status"),
        "continuation_gate_decision": gate.get("decision"),
        "mean_scar_edema_positive_dice_delta": gate.get("mean_scar_edema_positive_dice_delta"),
        "slurm_attempt_count": len(attempts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", default=str(RESULT_ROOT.relative_to(REPO_ROOT)))
    args = parser.parse_args()
    try:
        payload = validate_packet(REPO_ROOT / args.result_root)
    except ValidationError as exc:
        print(json.dumps({"status": "BATCH6_PACKET_VALIDATION_FAIL", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
