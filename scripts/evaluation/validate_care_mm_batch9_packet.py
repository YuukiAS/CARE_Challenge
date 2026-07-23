#!/usr/bin/env python3
"""Fail-closed validator for CARE Batch9 controller packet."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = os.environ.get("CARE_MM_TASK_KEY", "20260723_care_myops_batch9_exposed_issues_repair")
RESULT_ROOT = Path(os.environ["CARE_MM_RESULT_ROOT"]) if os.environ.get("CARE_MM_RESULT_ROOT") else REPO_ROOT / "results" / TASK_KEY
PENDING_TOKENS = ("PENDING", "RUNNING", "NEEDS_MONITOR", "JOB_SUBMITTED", "AWAITING_SACCT", "PLACEHOLDER", "STATIC_INITIAL")
PENDING_SLURM_STATES = {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING", "REQUEUED", "RESIZING", "SUSPENDED", "AWAITING_SACCT"}
ALLOWED_FINAL = {
    "BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER",
    "BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER",
    "BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def has_pending_text(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for allowed in ALLOWED_FINAL:
        text = text.replace(allowed, "")
    return any(tok in text for tok in PENDING_TOKENS)




def validate_slurm_terminal_accounting(errors: list[str]) -> None:
    path = RESULT_ROOT / "slurm_terminal_accounting.json"
    if not path.is_file():
        fail(errors, "missing Slurm terminal accounting evidence")
        return
    payload = read_json(path)
    if payload.get("status") != "PASS" or payload.get("required_jobs_terminal") is not True:
        fail(errors, "Slurm terminal accounting did not PASS")
    required = {str(v) for v in payload.get("required_training_job_ids", [])}
    if not required:
        fail(errors, "Slurm accounting has no required training job ids")
        return
    records = payload.get("records", [])
    parent = {str(row.get("JobIDRaw", "")): row for row in records if str(row.get("JobIDRaw", "")) in required}
    missing = sorted(required - set(parent))
    if missing:
        fail(errors, f"Slurm accounting missing parent job rows: {missing}")
    for job_id, row in parent.items():
        state = str(row.get("State", "")).split()[0]
        if state in PENDING_SLURM_STATES or not state:
            fail(errors, f"Slurm job {job_id} is not terminal: {row.get('State', '')}")
        if not str(row.get("ExitCode", "")):
            fail(errors, f"Slurm job {job_id} missing exit code")



def validate_teacher_stage(errors: list[str]) -> None:
    for name in ["teacher_training_adequacy.csv", "teacher_initialization_checks.csv", "distillation_effective_coverage.csv", "teacher_confidence_pathology_coverage.csv", "distillation_coverage_gate.json", "distillation_coverage_gate.csv"]:
        if not (RESULT_ROOT / name).is_file():
            fail(errors, f"missing teacher/coverage output: {name}")
    if errors:
        return
    teachers = read_csv(RESULT_ROOT / "teacher_training_adequacy.csv")
    for seed in ("20260723", "20260724"):
        rows = [r for r in teachers if r.get("seed") == seed and r.get("variant") == "teacher_full_view"]
        if len(rows) != 1 or rows[0].get("status") != "PASS" or int(float(rows[0].get("epochs") or 0)) != 100 or int(float(rows[0].get("optimizer_steps") or 0)) != 25000:
            fail(errors, f"teacher formal budget incomplete for seed {seed}")
    init = read_csv(RESULT_ROOT / "teacher_initialization_checks.csv")
    for seed in ("20260723", "20260724"):
        rows = [r for r in init if r.get("seed") == seed]
        if len(rows) != 1 or rows[0].get("status") != "PASS" or str(rows[0].get("teacher_not_random_init", "0")) not in {"1", "True", "true"}:
            fail(errors, f"teacher initialization did not prove same-seed direct warm start for seed {seed}")


def validate_matched_stage(errors: list[str]) -> None:
    for name in ["matched_manifest_hashes.json", "matched_run_manifest_summary.csv", "training_adequacy.csv", "matched_run_manifest.csv", "per_seed_decision_matrix.csv", "prediction_manifest.csv", "casewise_metrics.csv", "subgroup_metrics.csv"]:
        if not (RESULT_ROOT / name).is_file():
            fail(errors, f"missing matched terminal output: {name}")
    if errors:
        return
    gate = read_json(RESULT_ROOT / "distillation_coverage_gate.json")
    if gate.get("matched_control_distill_authorized") is not True:
        fail(errors, "matched stage ran without a PASS distillation coverage gate")
    cont = read_csv(RESULT_ROOT / "training_adequacy.csv")
    for seed in ("20260723", "20260724"):
        for variant in ("student_moddrop_control", "student_reliable_distill"):
            rows = [r for r in cont if r.get("seed") == seed and r.get("variant") == variant]
            if len(rows) != 1 or rows[0].get("status") != "PASS" or int(float(rows[0].get("epochs") or 0)) != 100 or int(float(rows[0].get("optimizer_steps") or 0)) != 25000:
                fail(errors, f"matched continuation budget incomplete for {seed}/{variant}")
    hashes = read_json(RESULT_ROOT / "matched_manifest_hashes.json")
    if hashes.get("status") != "PASS":
        fail(errors, "matched manifest hashes did not PASS")
    summary = read_csv(RESULT_ROOT / "matched_run_manifest_summary.csv")
    for seed in ("20260723", "20260724"):
        rows = [r for r in summary if r.get("seed") == seed]
        if len(rows) != 1:
            fail(errors, f"matched manifest summary missing for seed {seed}")
            continue
        row = rows[0]
        if row.get("status") != "PASS" or int(float(row.get("mismatch_count") or 0)) != 0 or int(float(row.get("row_count_control") or 0)) != 25000 or int(float(row.get("row_count_distill") or 0)) != 25000:
            fail(errors, f"matched manifest mismatch or row count failure for seed {seed}")
    matched = read_csv(RESULT_ROOT / "matched_run_manifest.csv")
    for seed in ("20260723", "20260724"):
        rows = [r for r in matched if r.get("seed") == seed]
        if len(rows) != 1 or rows[0].get("status") != "PASS" or str(rows[0].get("same_student_initial_checkpoint", "0")) not in {"1", "True", "true"}:
            fail(errors, f"matched initial state check failed for seed {seed}")
    pred = read_csv(RESULT_ROOT / "prediction_manifest.csv")
    casewise = read_csv(RESULT_ROOT / "casewise_metrics.csv")
    if len(pred) < 2 * 4 * 44:
        fail(errors, "terminal prediction manifest does not cover direct, teacher, control, and distill for two 44-case evaluations")
    if len(casewise) < 2 * 4 * 44 * 2:
        fail(errors, "terminal casewise metrics do not cover scar/edema for all direct, teacher, control, and distill evaluations")
    if any(int(float(r.get("no_t2_edema_predicted_voxels") or 0)) > 0 for r in casewise):
        fail(errors, "no-T2 edema voxels nonzero in terminal matched casewise metrics")

def validate_repair() -> dict[str, Any]:
    errors: list[str] = []
    common = [
        "controller_context.json", "controller_ledger.csv", "fold0_case_manifest.csv",
        "center_modality_label_inventory.csv", "reliable_supervision_inventory.csv",
        "formal_trainer_contract.json", "plans_resolution.json", "augmentation_contract.json",
        "deep_supervision_checks.csv", "formal_entrypoint_import_graph.json",
        "loss_scale_checks.csv", "loss_gradient_conflict_audit.csv", "resolved_loss_contract.json",
        "sampler_distribution_checks.csv", "no_t2_decode_checks.csv", "real_known_bad_report.json",
        "unit_test_report.md", "fixed_real_case_overfit.json", "fixed_overfit_isolation_checks.csv",
        "lr_schedule_checks.csv", "checkpoint_roundtrip.json", "gpu_preflight_attempts.csv",
    ]
    for name in common:
        if not (RESULT_ROOT / name).is_file():
            fail(errors, f"missing repair output: {name}")
    if errors:
        return {"status": "FAIL", "errors": errors}
    if read_json(RESULT_ROOT / "plans_resolution.json").get("plans_name") != "nnUNetResEncUNetMPlans":
        fail(errors, "ResEnc M plans not resolved")
    known_bad = read_json(RESULT_ROOT / "real_known_bad_report.json")
    if known_bad.get("status") != "PASS":
        fail(errors, "real known-bad did not PASS")
    if not all(row.get("rejected") and row.get("expected_error_matched") for row in known_bad.get("known_bad_cases", [])):
        fail(errors, "known-bad fixtures were not rejected for the expected validator errors")
    if read_json(RESULT_ROOT / "fixed_real_case_overfit.json").get("status") != "PASS":
        fail(errors, "fixed overfit did not PASS")
    audit = read_csv(RESULT_ROOT / "loss_gradient_conflict_audit.csv")
    if not audit:
        fail(errors, "loss conflict audit is empty")
    else:
        first_audit = audit[0]
        if int(float(first_audit.get("audited_batches") or 0)) < 32:
            fail(errors, "loss conflict audit did not cover 32 real batches")
        if first_audit.get("audit_mode") != "real_runtime_batches":
            fail(errors, "loss conflict audit is not marked as real runtime batches")
        if first_audit.get("status") != "PASS":
            fail(errors, "loss conflict audit did not PASS")
    pre = read_csv(RESULT_ROOT / "gpu_preflight_attempts.csv")
    if not {r.get("partition") for r in pre if r.get("status") == "PASS"}.issuperset({"htzhulab", "a100-gpu"}):
        fail(errors, "both htzhulab and a100 preflight PASS required")
    terminal_files = ["finalizer_state.json", "controller_report.md", "completion_check.md", "MANIFEST.md"]
    terminal_present = all((RESULT_ROOT / name).is_file() for name in terminal_files)
    if not terminal_present:
        fail(errors, "terminal repair packet not present yet")
        return {"status": "FAIL", "errors": errors}
    state = read_json(RESULT_ROOT / "finalizer_state.json")
    if state.get("status") == "CONTINUATION_ALLOWED_NOT_COMPLETE":
        fail(errors, "direct gate passed but continuation has not been run; this is not terminal completion")
        return {"status": "FAIL", "errors": errors}
    validate_slurm_terminal_accounting(errors)
    direct_required = ["direct_training_adequacy.csv", "direct_validation_history.csv", "direct_checkpoint_selection.csv", "direct_prediction_manifest.csv", "direct_casewise_metrics.csv", "direct_subgroup_metrics.csv", "direct_gate.json", "direct_gate.csv"]
    for name in direct_required:
        if not (RESULT_ROOT / name).is_file():
            fail(errors, f"missing direct terminal output: {name}")
    for seed in ("20260723", "20260724"):
        receipt_path = RESULT_ROOT / f"seed{seed}_student_direct_reliable_selected_reload_evaluation_receipt.json"
        if not receipt_path.is_file():
            fail(errors, f"missing selected reload evaluation receipt for seed {seed}")
        else:
            receipt = read_json(receipt_path)
            if receipt.get("checkpoint_reloaded") is not True:
                fail(errors, f"selected reload checkpoint not reloaded for seed {seed}")
            if receipt.get("standard_nnunet_checkpoint_logits_or_predictions_loaded") is not False:
                fail(errors, f"standard nnU-Net artifact was loaded in selected reload evaluation for seed {seed}")
    if errors:
        return {"status": "FAIL", "errors": errors}
    direct = read_csv(RESULT_ROOT / "direct_training_adequacy.csv")
    selection = read_csv(RESULT_ROOT / "direct_checkpoint_selection.csv")
    for seed in ("20260723", "20260724"):
        rows = [r for r in direct if r.get("seed") == seed and r.get("variant") == "student_direct_reliable" and r.get("status") == "PASS"]
        if not rows or int(float(rows[0].get("epochs") or 0)) != 500 or int(float(rows[0].get("optimizer_steps") or 0)) != 125000:
            fail(errors, f"direct formal budget incomplete for seed {seed}")
        if rows and str(rows[0].get("selected_checkpoint_reloaded")).lower() not in {"true", "1"}:
            fail(errors, f"selected checkpoint not reloaded for seed {seed}")
        selected = [
            r for r in selection
            if r.get("seed") == seed and r.get("variant") == "student_direct_reliable"
            and (
                str(r.get("selected", "")).lower() in {"1", "true", "yes"}
                or r.get("status") == "SELECTED"
            )
        ]
        if not selected:
            fail(errors, f"post-hoc selected checkpoint missing for seed {seed}")
    pred = read_csv(RESULT_ROOT / "direct_prediction_manifest.csv")
    casewise = read_csv(RESULT_ROOT / "direct_casewise_metrics.csv")
    if len(pred) < 2 * 44:
        fail(errors, "direct prediction manifest does not cover two 44-case evaluations")
    if len(casewise) < 2 * 44 * 2:
        fail(errors, "direct casewise metrics do not cover scar/edema for two 44-case evaluations")
    if any(int(float(r.get("no_t2_edema_predicted_voxels") or 0)) > 0 for r in casewise):
        fail(errors, "no-T2 edema voxels nonzero")
    gate = read_json(RESULT_ROOT / "direct_gate.json")
    state_status = state.get("status")
    allowed_terminal_states = {"TERMINAL_DIRECT_GATE_FAILED", "TERMINAL_TEACHER_COVERAGE_FAILED", "TERMINAL_MATCHED_COMPLETE"}
    if state_status not in allowed_terminal_states:
        fail(errors, f"repair finalizer_state is not an allowed terminal state: {state_status}")
    if state_status == "TERMINAL_DIRECT_GATE_FAILED" and gate.get("continuation_allowed") is True:
        fail(errors, "terminal direct-gate-failed state conflicts with PASS gate")
    if state_status in {"TERMINAL_TEACHER_COVERAGE_FAILED", "TERMINAL_MATCHED_COMPLETE"}:
        if gate.get("continuation_allowed") is not True:
            fail(errors, "teacher/matched terminal state exists without PASS direct gate")
        validate_teacher_stage(errors)
    if state_status == "TERMINAL_MATCHED_COMPLETE":
        validate_matched_stage(errors)
    completion_text = (RESULT_ROOT / "completion_check.md").read_text(encoding="utf-8")
    final_tokens = [tok for tok in ALLOWED_FINAL if tok in completion_text]
    if len(final_tokens) != 1:
        fail(errors, "completion_check must contain exactly one allowed Batch9 final token")
    final_token = final_tokens[0] if final_tokens else ""
    if state_status == "TERMINAL_DIRECT_GATE_FAILED" and final_token != "BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER":
        fail(errors, "direct-gate terminal state must return the no-usable-signal token")
    if state_status == "TERMINAL_TEACHER_COVERAGE_FAILED" and final_token != "BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER":
        fail(errors, "teacher-coverage terminal state must return the direct-only pending-planner token")
    gt_positive_empty = [r for r in casewise if r.get("gt_positive") == "1" and r.get("prediction_positive") == "0"]
    if gt_positive_empty and final_token != "BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER":
        fail(errors, "GT-positive empty pathology prediction present outside no-usable-signal terminal decision")
    if any(has_pending_text(RESULT_ROOT / name) for name in ["finalizer_state.json", "controller_report.md", "completion_check.md"]):
        fail(errors, "pending/running token appears in terminal repair packet")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def validate() -> dict[str, Any]:
    if "exposed_issues_repair" in TASK_KEY:
        return validate_repair()
    errors: list[str] = []
    required = [
        "controller_context.json",
        "controller_ledger.csv",
        "controller_bootstrap_snapshot.md",
        "batch8_supersession.md",
        "fold0_case_manifest.csv",
        "center_modality_label_inventory.csv",
        "reliable_supervision_inventory.csv",
        "resenc_environment_contract.json",
        "standard_nnunet_baseline_contract.json",
        "clean_model_import_graph.json",
        "legacy_module_call_counters.csv",
        "availability_hard_mask_checks.csv",
        "reliable_supervision_mask_checks.csv",
        "resolved_loss_contract.json",
        "loss_gradient_matrix.csv",
        "final_logit_authority_checks.csv",
        "fixed_real_case_overfit.json",
        "checkpoint_roundtrip.json",
        "known_bad_report.json",
        "direct_training_adequacy.csv",
        "teacher_initialization_checks.csv",
        "teacher_training_adequacy.csv",
        "matched_run_manifest.csv",
        "distillation_mechanism.csv",
        "training_adequacy.csv",
        "checkpoint_selection.csv",
        "prediction_manifest.csv",
        "casewise_metrics.csv",
        "subgroup_metrics.csv",
        "help_harm.csv",
        "supervision_audit.csv",
        "finalizer_state.json",
        "decision_matrix.csv",
        "controller_report.md",
        "completion_check.md",
        "MANIFEST.md",
    ]
    for name in required:
        p = RESULT_ROOT / name
        if not p.is_file():
            fail(errors, f"missing required output: {name}")
    if errors:
        return {"status": "FAIL", "errors": errors}

    manifest = read_csv(RESULT_ROOT / "fold0_case_manifest.csv")
    if len([r for r in manifest if r["split"] == "train"]) != 176:
        fail(errors, "fold0 train case count is not 176")
    if len([r for r in manifest if r["split"] == "val"]) != 44:
        fail(errors, "fold0 val case count is not 44")
    if any(r["t2_present"] == "0" and r["edema_reliable"] != "0" for r in manifest):
        fail(errors, "no-T2 case marked edema reliable")
    if any(r["center"] and r.get("center_enters_network") == "1" for r in read_csv(RESULT_ROOT / "reliable_supervision_inventory.csv")):
        fail(errors, "center enters network according to supervision inventory")

    legacy = read_csv(RESULT_ROOT / "legacy_module_call_counters.csv")
    if any(int(r["import_count"]) or int(r["instance_count"]) or int(r["forward_call_count"]) for r in legacy):
        fail(errors, "legacy SRR component count is nonzero")
    if read_json(RESULT_ROOT / "clean_model_import_graph.json").get("legacy_module_import_instance_forward_counts_all_zero") is not True:
        fail(errors, "clean import graph does not prove zero legacy counts")

    loss_contract = read_json(RESULT_ROOT / "resolved_loss_contract.json")
    if loss_contract.get("pathology_losses_use_composed_final_logit_margins") is not True:
        fail(errors, "pathology losses are not bound to final logit margins")
    grad_rows = read_csv(RESULT_ROOT / "loss_gradient_matrix.csv")
    if any(r["declared_weight"] not in {"0.0", "0"} and r["status"] != "PASS" for r in grad_rows):
        fail(errors, "nonzero loss missing authorized gradient")

    overfit = read_json(RESULT_ROOT / "fixed_real_case_overfit.json")
    if overfit.get("status") != "PASS" or overfit.get("formal_training_credit") != 0:
        fail(errors, "fixed real-case overfit is not PASS with zero formal credit")
    if read_json(RESULT_ROOT / "checkpoint_roundtrip.json").get("status") != "PASS":
        fail(errors, "checkpoint roundtrip failed")
    known_bad = read_json(RESULT_ROOT / "known_bad_report.json")
    if known_bad.get("status") != "PASS" or not all(row.get("rejected") for row in known_bad.get("known_bad_cases", [])):
        fail(errors, "known-bad fixtures did not all reject")

    direct = read_csv(RESULT_ROOT / "direct_training_adequacy.csv")
    for seed in ("20260723", "20260724"):
        rows = [r for r in direct if r["seed"] == seed and r["variant"] == "student_direct_reliable"]
        if len(rows) != 1 or rows[0]["status"] != "PASS" or int(rows[0]["epochs"]) != 500 or int(rows[0]["optimizer_steps"]) != 125000:
            fail(errors, f"direct formal run incomplete for seed {seed}")
    teachers = read_csv(RESULT_ROOT / "teacher_training_adequacy.csv")
    for seed in ("20260723", "20260724"):
        rows = [r for r in teachers if r["seed"] == seed and r["variant"] == "teacher_full_view"]
        if len(rows) != 1 or rows[0]["status"] != "PASS" or int(rows[0]["epochs"]) != 100 or int(rows[0]["optimizer_steps"]) != 25000:
            fail(errors, f"teacher formal run incomplete for seed {seed}")
    cont = read_csv(RESULT_ROOT / "training_adequacy.csv")
    for seed in ("20260723", "20260724"):
        for variant in ("student_moddrop_control", "student_reliable_distill"):
            rows = [r for r in cont if r["seed"] == seed and r["variant"] == variant]
            if len(rows) != 1 or rows[0]["status"] != "PASS" or int(rows[0]["epochs"]) != 100 or int(rows[0]["optimizer_steps"]) != 25000:
                fail(errors, f"matched continuation incomplete for {seed}/{variant}")

    pred = read_csv(RESULT_ROOT / "prediction_manifest.csv")
    expected_predictions = 2 * 4 * 44
    if len(pred) != expected_predictions:
        fail(errors, f"prediction manifest row count {len(pred)} != {expected_predictions}")
    if len({r["prediction_sha256"] for r in pred}) != len(pred):
        fail(errors, "prediction hashes are reused")
    casewise = read_csv(RESULT_ROOT / "casewise_metrics.csv")
    if len(casewise) != expected_predictions * 2:
        fail(errors, "casewise metrics row count does not cover scar and edema for all predictions")
    completion_text = (RESULT_ROOT / "completion_check.md").read_text(encoding="utf-8")
    final_tokens = [tok for tok in ALLOWED_FINAL if tok in completion_text]
    if len(final_tokens) != 1:
        fail(errors, "completion_check must contain exactly one allowed Batch9 final token")
    final_token = final_tokens[0] if final_tokens else ""
    gt_positive_empty = [r for r in casewise if r["gt_positive"] == "1" and r["prediction_positive"] == "0"]
    if gt_positive_empty and final_token != "BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER":
        fail(errors, "GT-positive empty pathology prediction present outside no-usable-signal terminal decision")

    if any(has_pending_text(RESULT_ROOT / name) for name in ["finalizer_state.json", "controller_report.md", "completion_check.md"]):
        fail(errors, "pending/running/placeholder token appears in terminal packet")

    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = validate()
    out = RESULT_ROOT / "strict_validator_report.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
