#!/usr/bin/env python3
"""Strict validator for the CARE SRR Batch4 terminal packet."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260721_srr_batch4_forced_fold0_training"
ATTEMPT_ID = "srr_batch4_m10d3_full4scale_fold0_seed20260721_htzhulab_59682067"
EXPECTED_CHECKPOINT_SHA = "bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6"
EXPECTED_SOURCE_COMMIT = "0466260e3f4eb6c50b05a7f5a8b66652b873fe46"
EXPECTED_RAW_MANIFEST_HASH = "e67724c35ec13f50db394064184032a0ef6a785eff840235b9b0550a40ee8add"
EXPECTED_COMPACT_ANCHOR_HASH = "511f2f22150f40adadabb1b5b3541b4b04d0730d6905c55f612cfded54a78b8c"
EXPECTED_CONTROL_MODES = (
    "anchor_identity_control",
    "anchor_bounded_srr_correction",
    "srr_no_anchor_control",
)
SELECTION_STEPS = (600, 1200, 1800)


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise ValidationError(f"missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValidationError(f"missing required file: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def validate_packet(result_root: Path) -> dict[str, Any]:
    variant_dir = result_root / "runtime/attempts" / ATTEMPT_ID / "variants" / ATTEMPT_ID
    summary = load_json(variant_dir / "summary.json")
    adequacy = load_json(result_root / "training_adequacy.json")
    selected = load_json(result_root / "selected_checkpoint.json")
    slurm_rows = read_csv(result_root / "slurm_attempts.csv")

    expect(adequacy.get("status") == "TRAINING_BUDGET_VALID_AGGREGATED_FROM_59682067", "training adequacy status is not terminal-valid")
    expect(adequacy.get("job_id") == "59682067", "training adequacy is not bound to job 59682067")
    expect(adequacy.get("job_state") == "COMPLETED", "59682067 state is not COMPLETED in packet")
    expect(adequacy.get("job_exit_code") == "0:0", "59682067 exit code is not 0:0")
    expect(adequacy.get("elapsed") == "00:33:26", "59682067 elapsed accounting drifted")
    expect(adequacy.get("actual_optimizer_steps") == 1800, "actual_optimizer_steps is not exactly 1800")
    expect(adequacy.get("optimizer_steps") == 1800, "optimizer_steps is not exactly 1800")
    expect(adequacy.get("max_steps") == 1800, "max_steps is not exactly 1800")
    expect(float(adequacy.get("train_loop_seconds", 0.0)) >= 1800.0, "train_loop_seconds is below 1800")
    expect(float(adequacy.get("post_optimizer_wait_seconds", 0.0)) > 0.0, "post optimizer wait evidence is missing")
    expect(
        adequacy.get("stop_reason") == "max_steps_min_train_loop_seconds_satisfied_without_extra_optimizer_steps",
        "stop_reason does not prove no extra optimizer steps after max_steps",
    )
    expect(adequacy.get("train_cases") == 176, "train_cases is not 176")
    expect(adequacy.get("val_cases") == 44 and adequacy.get("eval_cases") == 44, "val/eval case counts are not 44")
    expect(adequacy.get("model_variant") == "m10_d3_hierarchical_memory_propref", "model variant drifted")
    expect(adequacy.get("encoder_profile") == "full_4scale", "encoder profile drifted")
    expect(adequacy.get("encoder_scale_channels") == [32, 64, 128, 256], "encoder channels drifted")
    expect(adequacy.get("selected_checkpoint") == "step_1800", "selected checkpoint is not step_1800")
    expect(adequacy.get("selected_checkpoint_sha256") == EXPECTED_CHECKPOINT_SHA, "selected checkpoint hash mismatch")

    coverage = adequacy.get("coverage_for_missing_summary_fields", {})
    expect(summary.get("source_commit") is None, "runtime summary source_commit unexpectedly exists; update validator/accounting")
    expect(coverage.get("summary_top_level_source_commit") is None, "coverage source_commit value should record top-level None")
    expect(
        coverage.get("summary_top_level_source_commit_status") == "MISSING_COVERED_BY_CHECKPOINT_PAYLOAD",
        "source_commit gap is not covered by checkpoint payload",
    )
    expect(summary.get("full_volume_eval_steps") is None, "runtime summary full_volume_eval_steps unexpectedly exists; update validator/accounting")
    expect(coverage.get("summary_top_level_full_volume_eval_steps") is None, "coverage full_volume_eval_steps should record top-level None")
    expect(
        coverage.get("summary_top_level_full_volume_eval_steps_status") == "MISSING_COVERED_BY_RUNTIME_STEP_FILES",
        "full_volume_eval_steps gap is not covered by runtime step files",
    )
    step_counts = coverage.get("runtime_full_volume_eval_case_counts", {})
    expect(step_counts == {f"step_{s}": 44 for s in SELECTION_STEPS}, "runtime full-volume eval case counts are incomplete")
    for step in SELECTION_STEPS:
        rows = read_csv(variant_dir / f"component_hd_by_case_step_{step}.csv")
        expect(len({row["case_id"] for row in rows}) == 44, f"step_{step} component file does not cover 44 cases")
        expect((variant_dir / "predictions/fold_0" / f"step_{step}" / "pathology_aware").is_dir(), f"step_{step} prediction directory missing")

    checkpoint_path = REPO_ROOT / adequacy["selected_checkpoint_path"]
    checkpoint_payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    expect(checkpoint_payload.get("global_step") == 1800, "checkpoint payload global_step is not 1800")
    expect(checkpoint_payload.get("source_commit") == EXPECTED_SOURCE_COMMIT, "checkpoint payload source_commit does not cover summary source_commit gap")
    expect(checkpoint_payload.get("oof_anchor_manifest_hash") == EXPECTED_COMPACT_ANCHOR_HASH, "checkpoint payload compact anchor hash mismatch")

    expect(selected.get("status") == "SELECTED_CHECKPOINT_RELOADED_THREE_MODE_CONTROLS_COMPLETE", "selected checkpoint controls are not complete")
    expect(selected.get("selected_checkpoint") == "step_1800", "selected control checkpoint is not step_1800")
    expect(selected.get("selected_checkpoint_sha256") == EXPECTED_CHECKPOINT_SHA, "selected control checkpoint hash mismatch")
    expect(selected.get("control_slurm_job_id") == "59686817", "selected control job id accounting missing 59686817")
    expect(selected.get("control_slurm_job_status") == "FAILED_1:0_ZERO_COMPLETION_CREDIT", "59686817 failure/zero-credit accounting missing")
    expect(selected.get("same_checkpoint_three_mode_controls_complete") is True, "same-checkpoint three-mode control gate failed")

    contracts = selected.get("control_contracts", {})
    expect(set(contracts.keys()) == set(EXPECTED_CONTROL_MODES), "control modes are missing")
    for mode in EXPECTED_CONTROL_MODES:
        contract = contracts[mode]
        expect(contract.get("status") == "SRR_MODEL_IN_LOOP_CHECKPOINT_INFERENCE", f"{mode} contract did not complete inference")
        expect(contract.get("case_count") == 44, f"{mode} contract case_count is not 44")
        expect(contract.get("checkpoint_global_step") == 1800, f"{mode} checkpoint step is not 1800")
        expect(contract.get("checkpoint_sha256") == EXPECTED_CHECKPOINT_SHA, f"{mode} checkpoint hash mismatch")
        expect(contract.get("checkpoint_oof_anchor_manifest_hash") == EXPECTED_COMPACT_ANCHOR_HASH, f"{mode} compact checkpoint anchor hash mismatch")
        expect(contract.get("training_summary_anchor_manifest_hash") == EXPECTED_COMPACT_ANCHOR_HASH, f"{mode} training-summary anchor hash mismatch")
        expect(contract.get("raw_oof_anchor_manifest_hash") == EXPECTED_RAW_MANIFEST_HASH, f"{mode} raw manifest hash missing or mismatched")
        pred_dir = REPO_ROOT / str(contract.get("prediction_dir", ""))
        expect(pred_dir.is_dir(), f"{mode} prediction directory missing")
        expect(len(list(pred_dir.glob("*.nii.gz"))) == 44, f"{mode} prediction count is not 44")
    identity = contracts["anchor_identity_control"]
    expect(identity.get("anchor_identity_changed_voxels_total") == 0, "identity control changed voxels")
    expect(float(identity.get("anchor_identity_softmax_max_abs_delta", 1.0)) <= 1e-8, "identity control softmax delta is nonzero")
    for mode in ("anchor_bounded_srr_correction", "srr_no_anchor_control"):
        expect(float(contracts[mode].get("nonidentity_downstream_tensor_max_abs_delta", 0.0)) > 0.0, f"{mode} nonidentity tensor delta missing")

    eval_completion = selected.get("control_evaluation_completion", {})
    expect(eval_completion.get("status") == "BATCH3A_MODEL_IN_LOOP_EVALUATION_COMPLETE", "local control evaluation did not complete after config repair")
    expect(eval_completion.get("case_count") == 44, "control evaluation case count is not 44")
    expect(eval_completion.get("validation_upload_count") == 0, "validation upload was performed")
    expect(eval_completion.get("hosted_metric_claim_count") == 0, "hosted metric claim was made")
    expect(eval_completion.get("performance_claim") == "NONE", "performance claim is not NONE")

    by_job = {row["job_id"]: row for row in slurm_rows}
    expect(by_job.get("59678596", {}).get("training_credit") == "0", "59678596 invalid optimizer overshoot is not zero-credit")
    expect(by_job.get("59680114", {}).get("training_credit") == "0", "59680114 failed selected-control is not zero-credit")
    expect(by_job.get("59682067", {}).get("state") == "COMPLETED", "59682067 Slurm row missing terminal completed state")
    expect(by_job.get("59682067", {}).get("training_credit") == "1800_VALID_OPTIMIZER_STEPS", "59682067 valid credit is missing")
    expect(by_job.get("59686817", {}).get("state") == "FAILED", "59686817 failed Slurm row missing")
    expect(by_job.get("59686817", {}).get("training_credit") == "0", "59686817 failed selected-control is not zero-credit")

    required_lightweight = (
        "training_adequacy.json",
        "training_log_summary.csv",
        "validation_checkpoint_metrics.csv",
        "selected_checkpoint.json",
        "casewise_metrics.csv",
        "subgroup_metrics.csv",
        "help_harm.csv",
        "component_remote_fp.csv",
        "proposal_diagnostics.csv",
        "roi_diagnostics.csv",
        "correction_gate_diagnostics.csv",
        "frozen_prototype_memory_manifest.json",
    )
    for name in required_lightweight:
        expect((result_root / name).is_file(), f"missing aggregated lightweight output: {name}")

    prototype_manifest = load_json(result_root / "frozen_prototype_memory_manifest.json")
    expect(prototype_manifest.get("status") == "FROZEN_PROTOTYPE_MEMORY_MANIFEST_READY", "prototype manifest is not ready")
    expect(prototype_manifest.get("source_case_count") == 176, "prototype manifest source_case_count is not 176")
    expect(prototype_manifest.get("expected_train_case_count") == 176, "prototype manifest expected_train_case_count is not 176")
    expect(len(prototype_manifest.get("source_case_ids", [])) == 176, "prototype manifest source_case_ids does not contain 176 cases")
    expect(prototype_manifest.get("missing_train_case_ids") == [], "prototype manifest has missing train cases")
    expect(prototype_manifest.get("validation_leakage_case_ids") == [], "prototype manifest has validation leakage")
    expect(prototype_manifest.get("source_commit") == EXPECTED_SOURCE_COMMIT, "prototype manifest source_commit mismatch")
    expect(prototype_manifest.get("no_t2_edema_positive_forbidden") is True, "prototype manifest no-T2 edema positive guard missing")
    expect(prototype_manifest.get("no_t2_edema_negative_forbidden") is True, "prototype manifest no-T2 edema negative guard missing")

    return {
        "status": "BATCH4_STRICT_VALIDATION_PASS",
        "result_root": rel(result_root),
        "job_id": "59682067",
        "selected_checkpoint": "step_1800",
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA,
        "source_commit_coverage": EXPECTED_SOURCE_COMMIT,
        "full_volume_eval_steps_coverage": list(SELECTION_STEPS),
        "control_job_59686817_credit": "FAILED_ZERO_CREDIT_WITH_VALID_LOCAL_EVALUATION_AFTER_CONFIG_REPAIR",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", default=f"results/{TASK_KEY}")
    args = parser.parse_args()
    try:
        payload = validate_packet(REPO_ROOT / args.result_root)
    except ValidationError as exc:
        print(json.dumps({"status": "BATCH4_STRICT_VALIDATION_FAIL", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
