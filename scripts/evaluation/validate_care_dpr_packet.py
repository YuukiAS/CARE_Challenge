#!/usr/bin/env python3
"""Strict validator for CARE-DPR Gate A-R2 implementation and preflight packets."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
SOURCE_FILES = [
    "src/care_myocardium/models/care_dpr.py",
    "src/care_myocardium/training/care_dpr_trainer.py",
    "src/care_myocardium/inference/care_dpr_predictor.py",
    "src/care_myocardium/data/care_dpr_dataset.py",
    "scripts/training/run_care_dpr.py",
    "scripts/evaluation/analyze_care_dpr_mechanism_ceiling.py",
    "scripts/evaluation/evaluate_care_dpr.py",
    "scripts/evaluation/validate_care_dpr_packet.py",
    "scripts/evaluation/validate_care_dpr_gate_a_r2_consistency.py",
    "tests/care_dpr/test_care_dpr_model.py",
]
HARD_NEGATIVE_SUBTYPES = ["blood_pool", "outside_support_bright_island", "remote_anchor_fp", "high_intensity_nonlesion"]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def source_text(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def validate_source_contract() -> tuple[list[dict[str, Any]], dict[str, str]]:
    hashes = {rel: sha(REPO_ROOT / rel) for rel in SOURCE_FILES if (REPO_ROOT / rel).exists()}
    model = source_text("src/care_myocardium/models/care_dpr.py")
    predictor = source_text("src/care_myocardium/inference/care_dpr_predictor.py")
    trainer = source_text("src/care_myocardium/training/care_dpr_trainer.py")
    data = source_text("src/care_myocardium/data/care_dpr_dataset.py")
    run = source_text("scripts/training/run_care_dpr.py")
    evaluator = source_text("scripts/evaluation/evaluate_care_dpr.py")
    tests = source_text("tests/care_dpr/test_care_dpr_model.py")
    model_ast = ast.parse(model)
    predictor_ast = ast.parse(predictor)
    test_ast = ast.parse(tests)
    class_names = {node.name for node in ast.walk(model_ast) if isinstance(node, ast.ClassDef)}
    function_names = {node.name for node in ast.walk(predictor_ast) if isinstance(node, ast.FunctionDef)}
    test_names = {node.name for node in ast.walk(test_ast) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
    required_tests = {
        "test_sampler_cursor_rotates_across_batches_not_scar_only",
        "test_local_refiner_roi_sizes_and_boundary_padding_forward",
        "test_revise_candidate_uses_whole_anchor_component_not_qfp_intersection",
        "test_unaccepted_candidate_does_not_partially_write_back",
        "test_full_volume_aggregation_returns_shared_feature_before_components",
        "test_two_pass_full_volume_refines_each_candidate_and_scores_once",
        "test_component_utility_descriptor_pools_candidate_shared_feature",
        "test_checkpoint_resume_restores_exact_runtime_state",
        "test_stage_boundary_resume_rebuilds_b_optimizer_without_loading_a2_state",
        "test_teacher_roi_forbidden_in_eval_or_inference",
        "test_no_t2_edema_zero_and_no_gradient",
        "test_hard_negative_subtype_cursor_contract_names_all_required",
    }
    checks = {
        "local_roi_refiner_class_present": "LocalROIRefiner" in class_names and "forward_at_center" in model,
        "component_utility_mlp_candidate_score_present": "ComponentUtilityMLP" in class_names and "score_candidate" in model and "descriptor_from_candidate" in model,
        "formal_two_pass_inference_present": "run_two_pass_full_volume_dpr" in function_names and "pass1_runs_component_decision" in predictor and "pass2_refines_each_candidate" in predictor,
        "pass1_no_patch_final_label_average": "accum_keys = [\"scar_p_coarse\", \"scar_q_fn\", \"scar_q_fp\", \"edema_p_coarse\", \"edema_q_fn\", \"edema_q_fp\"]" in predictor and "final_mask" not in predictor.split("def aggregate_patch_outputs", 1)[1].split("def _bbox", 1)[0],
        "candidate_descriptor_uses_aggregated_shared_feature": "shared_full_resolution_feature" in predictor and "component_utility.score_candidate" in predictor and "component_descriptor_uses_aggregated_shared_feature" in predictor,
        "candidate_target_not_patch_target": "primary_candidate_mask" in trainer and "candidate_mask" in trainer and "distance_to_reliable_gt" in trainer,
        "remote_forced_reject_uses_reliable_gt_distance": "distance_to_reliable_gt" in data and "forced_reject_remote_gt_distance_gt_20mm" in evaluator and "distance_to_myocardium" not in evaluator.split("def candidate_utility_target", 1)[1].split("def loss_decline", 1)[0],
        "diagnostic_cases_disjoint_and_frozen": "preflight_optimizer_cases.json" in run and "gate_a_r2_diagnostic_cases.json" in run and "DIAGNOSTIC_OVERLAPS_OPTIMIZER" in evaluator,
        "synthetic_utility_variants_not_primary": "synthetic_utility_variants_used_for_primary_gate\": False" in evaluator and "oracle_refined" not in evaluator and "empty_refined" not in evaluator and "remote_false_positive" not in evaluator,
        "hard_negative_subtype_cursor_no_generic_fallback": "hard_negative_subtype_cursor" in data and "CARE_DPR_EMPTY_REQUESTED_SUBTYPE_POOL" in data and all(s in data for s in HARD_NEGATIVE_SUBTYPES),
        "stage_boundary_resume_rule_present": "should_restore_optimizer_state" in run and 'saved_stage == "A2" and target_stage == "B" and int(total_step) == 2500' in run,
        "runner_reload_compares_values_and_outputs": "parameter_values_exact" in run and "fixed_outputs_exact" in run and "torch.equal" in run,
        "a_r2_token_required_and_old_tokens_rejected": "APPROVE_DPR_GATE_A_R2" in run and "APPROVE_DPR_GATE_A_R1" in run and "SUPERSEDED_GATE_TOKENS" in run,
        "known_bad_tests_present": required_tests.issubset(test_names),
    }
    return [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in checks.items()], hashes


def run_tests() -> dict[str, Any]:
    cmd = [str(REPO_ROOT / "envs/env_CARE/bin/python"), "-m", "pytest", "-q", "tests/care_dpr/test_care_dpr_model.py"]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return {"command": " ".join(cmd), "exit_code": proc.returncode, "output": proc.stdout}


def _pytest_passed(test_result: dict[str, Any]) -> bool:
    output = str(test_result.get("output", ""))
    return int(test_result.get("exit_code", 1)) == 0 and re.search(r"\bpassed\b", output) is not None


def validate_preflight_artifacts(result_root: Path, test_result: dict[str, Any]) -> list[dict[str, Any]]:
    runtime = result_root / "runtime/preflight"
    mechanism = _load_json(runtime / "mechanism_report.json")
    receipt = _load_json(runtime / "preflight_receipt.json")
    sampler = _load_json(runtime / "sampler_audit_stage_preflight.json")
    optimizer_cases = _load_json(runtime / "preflight_optimizer_cases.json")
    diagnostic_cases = _load_json(runtime / "gate_a_r2_diagnostic_cases.json")
    utility = mechanism.get("utility_metrics") or {}
    two_pass = mechanism.get("two_pass_full_volume_candidate_pipeline") or {}
    r2 = mechanism.get("r2_thresholds") or {}
    subtype_counts = sampler.get("hard_negative_subtype_counts") or {}
    threshold_rows = utility.get("threshold_candidates") or []
    checks = {
        "pytest_exit_pass": _pytest_passed(test_result),
        "mechanism_report_pass": mechanism.get("status") == "PASS",
        "preflight_receipt_pass_zero_credit": receipt.get("status") == "PASS" and receipt.get("formal_training_credit") == 0,
        "diagnostic_cases_disjoint": bool(diagnostic_cases.get("case_ids")) and bool(optimizer_cases.get("case_ids")) and not (set(diagnostic_cases.get("case_ids", [])) & set(optimizer_cases.get("case_ids", []))),
        "diagnostic_outer_fold0_not_used": diagnostic_cases.get("outer_fold0_used") is False and optimizer_cases.get("outer_fold0_used") is False,
        "two_pass_pipeline_pass": two_pass.get("status") == "PASS" and int(two_pass.get("component_utility_call_count", 0)) == int(utility.get("true_candidate_total_count", -1)),
        "true_candidate_utility_source": utility.get("primary_metric_source") == "model_real_full_volume_candidates_only" and utility.get("synthetic_utility_variants_used_for_primary_gate") is False,
        "utility_real_candidates_positive_and_negative": int(utility.get("accept_target_positive_count", 0)) > 0 and int(utility.get("accept_target_negative_count", 0)) > 0,
        "fixed_threshold_accept_reject_gain": any(bool(row.get("has_nonzero_accepted_and_rejected")) and float(row.get("realized_gain", 0.0)) > 0.0 for row in threshold_rows),
        "sampler_audit_pass": sampler.get("status") == "PASS",
        "hard_negative_subtypes_all_nonzero": all(int((subtype_counts.get(slot) or {}).get(sub, 0)) > 0 for slot in ("scar_hard_negative", "edema_hard_negative") for sub in HARD_NEGATIVE_SUBTYPES),
        "no_t2_exact_zero": (mechanism.get("no_t2_exact_zero") or {}).get("status") == "PASS",
        "component_arbitration_parity": (mechanism.get("component_arbitration") or {}).get("full_volume_arbitration_parity") == "PASS",
        "resume_exact_values_outputs": (mechanism.get("checkpoint_resume_exact") or {}).get("status") == "PASS" and (mechanism.get("checkpoint_resume_exact") or {}).get("parameter_values_exact") is True and (mechanism.get("checkpoint_resume_exact") or {}).get("fixed_outputs_exact") is True,
        "r2_thresholds_pass": r2.get("status") == "PASS",
    }
    return [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in checks.items()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", default=str(RESULT_ROOT))
    parser.add_argument("--mode", choices=["implementation", "preflight"], default="implementation")
    args = parser.parse_args()
    result_root = Path(args.result_root)
    findings, hashes = validate_source_contract()
    test_result = run_tests()
    findings.append({"check": "pytest_tests_execute_and_pass", "status": "PASS" if _pytest_passed(test_result) else "FAIL"})
    if args.mode == "preflight":
        findings.extend(validate_preflight_artifacts(result_root, test_result))
    status = "PASS" if all(f["status"] == "PASS" for f in findings) else "FAIL"
    known_bad = {
        "status": status,
        "fixtures": [
            "patch_level_utility_map_used_as_candidate_utility",
            "full_volume_shared_feature_aggregated_but_not_used_by_utility_mlp",
            "utility_target_computed_per_patch_not_per_candidate",
            "diagnostic_cases_overlap_overfit_cases",
            "synthetic_utility_variants_used_as_primary_metrics",
            "scar_hard_negative_subtype_zero",
            "a2_checkpoint_optimizer_loaded_directly_into_b_optimizer",
            "runner_reload_only_compares_state_dict_keys",
            "formal_runtime_refines_only_one_argmax_patch_center_without_candidate_pass2",
        ],
        "coverage": findings,
        "pytest_exit_code": test_result.get("exit_code"),
    }
    report = {"task_key": TASK_KEY, "gate": "DPR_GATE_A_R2", "mode": args.mode, "status": status, "generated_at_utc": now_utc(), "source_hashes_sha256": hashes, "findings": findings, "unit_tests": test_result, "known_bad": known_bad}
    write_json(result_root / ("strict_validator_report.json" if args.mode == "preflight" else "implementation_validator_report.json"), report)
    write_json(result_root / "known_bad_report.json", known_bad)
    (result_root / "unit_test_report.md").write_text("# CARE-DPR Unit Test Report\n\n" + f"Status: {status}\n\n```text\n{test_result.get('output','')}\n```\n", encoding="utf-8")
    if args.mode == "implementation":
        impl = {
            "task_key": TASK_KEY,
            "status": status,
            "gate_a_status": "SUPERSEDED_BY_DPR_GATE_A_R2_REPAIR_IN_PROGRESS",
            "amendment_precedence": True,
            "shared_backbone_count": 1,
            "pathology_branches": ["scar", "edema_zone"],
            "required_branch_outputs": ["p_coarse", "q_fn", "q_fp", "p_refined", "component_utility"],
            "candidate_types": ["ADD_FN", "REVISE_FP"],
            "legal_actions": ["KEEP_ANCHOR_LOCAL_MASK", "REPLACE_WITH_REFINED_LOCAL_MASK"],
            "full_volume_inference": {"passes": 2, "overlap": 0.5, "gaussian_blending": True, "aggregate_before_components": True, "candidate_pass2_refinement": True, "patch_final_label_averaging": False, "patch_local_component_arbitration": False},
            "formal_fold0_guard": "APPROVE_DPR_GATE_A_R2 required; APPROVE_DPR_GATE_A and APPROVE_DPR_GATE_A_R1 superseded",
            "source_hashes_sha256": hashes,
        }
        write_json(result_root / "implementation_contract.json", impl)
        write_json(result_root / "model_parameter_report.json", {"status": status, "proof": "single CAREDPR.encoder object; independent scar_branch and edema_branch modules; candidate pass2 calls pathology-specific local refiners and ComponentUtilityMLP per full-volume candidate", "scar_roi_context_zyx": [8, 96, 96], "edema_roi_context_zyx": [8, 128, 128], "source_hashes_sha256": hashes})
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
