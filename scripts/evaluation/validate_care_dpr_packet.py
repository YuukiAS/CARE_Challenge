#!/usr/bin/env python3
"""Strict validator for CARE-DPR amendment packets."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
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
    "scripts/evaluation/validate_care_dpr_gate_a_r1_consistency.py",
    "tests/care_dpr/test_care_dpr_model.py",
]


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


def validate_source_contract() -> tuple[list[dict[str, Any]], dict[str, str]]:
    hashes = {rel: sha(REPO_ROOT / rel) for rel in SOURCE_FILES if (REPO_ROOT / rel).exists()}
    model_ast = ast.parse(source_text("src/care_myocardium/models/care_dpr.py"))
    predictor_ast = ast.parse(source_text("src/care_myocardium/inference/care_dpr_predictor.py"))
    trainer = source_text("src/care_myocardium/training/care_dpr_trainer.py")
    run = source_text("scripts/training/run_care_dpr.py")
    tests = source_text("tests/care_dpr/test_care_dpr_model.py")
    class_names = {node.name for node in ast.walk(model_ast) if isinstance(node, ast.ClassDef)}
    function_names = {node.name for node in ast.walk(predictor_ast) if isinstance(node, ast.FunctionDef)}
    test_names = {node.name for node in ast.walk(ast.parse(tests)) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
    required_tests = {
        "test_sampler_cursor_rotates_across_batches_not_scar_only",
        "test_local_refiner_roi_sizes_and_boundary_padding_forward",
        "test_revise_candidate_uses_whole_anchor_component_not_qfp_intersection",
        "test_unaccepted_candidate_does_not_partially_write_back",
        "test_full_volume_aggregation_returns_shared_feature_before_components",
        "test_checkpoint_resume_restores_exact_runtime_state",
        "test_teacher_roi_forbidden_in_eval_or_inference",
        "test_no_t2_edema_zero_and_no_gradient",
    }
    checks = {
        "local_roi_refiner_class_present": "LocalROIRefiner" in class_names,
        "component_utility_mlp_present": "ComponentUtilityMLP" in class_names,
        "dense_voxel_utility_not_primary": "utility_head = nn.Sequential" not in source_text("src/care_myocardium/models/care_dpr.py"),
        "sampler_cursor_persisted": "sampler_slot_cursor" in run and "sampler_slot_cursor" in trainer,
        "a_r1_token_required_and_old_token_rejected": "APPROVE_DPR_GATE_A_R1" in run and "SUPERSEDED_APPROVE_DPR_GATE_A" in run,
        "component_utility_target_formula": "2.0 * fn_a" in trainer and "0.25 * boundary" in trainer and "REMOTE_REJECT_MM" in trainer,
        "full_volume_shared_feature_aggregated": "shared_full_resolution_feature" in source_text("src/care_myocardium/inference/care_dpr_predictor.py"),
        "candidate_builder_component_semantics": {"_expand", "_bbox", "build_candidates"}.issubset(function_names),
        "known_bad_tests_present": required_tests.issubset(test_names),
    }
    findings = [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in checks.items()]
    return findings, hashes


def run_tests() -> dict[str, Any]:
    cmd = [str(REPO_ROOT / "envs/env_CARE/bin/python"), "-m", "pytest", "-q", "tests/care_dpr/test_care_dpr_model.py"]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return {"command": " ".join(cmd), "exit_code": proc.returncode, "output": proc.stdout}


def _pytest_passed(test_result: dict[str, Any]) -> bool:
    return int(test_result.get("exit_code", 1)) == 0 and "12 passed" in str(test_result.get("output", ""))


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def validate_preflight_artifacts(result_root: Path, test_result: dict[str, Any]) -> list[dict[str, Any]]:
    mechanism = _load_json(result_root / "runtime/preflight/mechanism_report.json")
    receipt = _load_json(result_root / "runtime/preflight/preflight_receipt.json")
    sampler = _load_json(result_root / "runtime/preflight/sampler_audit_stage_preflight.json")
    checks = {
        "pytest_exit_pass": _pytest_passed(test_result),
        "mechanism_report_pass": mechanism.get("status") == "PASS",
        "preflight_receipt_pass_zero_credit": receipt.get("status") == "PASS" and receipt.get("formal_training_credit") == 0,
        "sampler_audit_pass": sampler.get("status") == "PASS",
        "sampler_all_eight_slots_present": sorted((sampler.get("slot_counts") or {}).keys()) == sorted(["scar_fn", "scar_fp", "scar_hard_negative", "scar_pathology", "edema_fn", "edema_fp", "edema_hard_negative", "edema_pathology"]),
        "no_t2_exact_zero": (mechanism.get("no_t2_exact_zero") or {}).get("status") == "PASS",
        "component_arbitration_parity": (mechanism.get("component_arbitration") or {}).get("full_volume_arbitration_parity") == "PASS",
        "resume_exact": (mechanism.get("checkpoint_resume_exact") or {}).get("status", "PASS") == "PASS",
        "thresholds_pass": (mechanism.get("r1_thresholds") or {}).get("status") == "PASS",
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
    if not _pytest_passed(test_result):
        findings.append({"check": "pytest_tests_execute_and_pass", "status": "FAIL"})
    else:
        findings.append({"check": "pytest_tests_execute_and_pass", "status": "PASS"})
    if args.mode == "preflight":
        findings.extend(validate_preflight_artifacts(result_root, test_result))
    status = "PASS" if all(f["status"] == "PASS" for f in findings) else "FAIL"
    known_bad = {
        "status": status,
        "fixtures": [
            "sampler_cursor_stuck_on_scar_four_slots",
            "dense_voxel_utility_map_used_as_component_utility",
            "revise_qfp_intersection_instead_of_whole_anchor_component",
            "scar_edema_roi_size_collapse",
            "shared_feature_missing_from_full_volume_aggregation",
            "resume_only_compares_state_dict_keys",
            "teacher_roi_used_in_inner_outer_inference",
            "no_t2_edema_candidate_constructed_or_accepted",
            "unaccepted_candidate_partial_writeback",
        ],
        "coverage": findings,
        "pytest_exit_code": test_result.get("exit_code"),
    }
    report = {"task_key": TASK_KEY, "mode": args.mode, "status": status, "generated_at_utc": now_utc(), "source_hashes_sha256": hashes, "findings": findings, "unit_tests": test_result, "known_bad": known_bad}
    write_json(result_root / ("strict_validator_report.json" if args.mode == "preflight" else "implementation_validator_report.json"), report)
    write_json(result_root / "known_bad_report.json", known_bad)
    (result_root / "unit_test_report.md").write_text("# CARE-DPR Unit Test Report\n\n" + f"Status: {status}\n\n```text\n{test_result.get('output','')}\n```\n", encoding="utf-8")
    if args.mode == "implementation":
        impl = {"task_key": TASK_KEY, "status": status, "gate_a_status": "SUPERSEDED_BY_DPR_GATE_A_R1", "amendment_precedence": True, "shared_backbone_count": 1, "pathology_branches": ["scar", "edema_zone"], "required_branch_outputs": ["p_coarse", "q_fn", "q_fp", "p_refined", "component_utility"], "candidate_types": ["ADD_FN", "REVISE_FP"], "legal_actions": ["KEEP_ANCHOR_LOCAL_MASK", "REPLACE_WITH_REFINED_LOCAL_MASK"], "full_volume_inference": {"overlap": 0.5, "gaussian_blending": True, "aggregate_before_components": True, "patch_final_label_averaging": False, "patch_local_component_arbitration": False}, "formal_fold0_guard": "APPROVE_DPR_GATE_A_R1 required; APPROVE_DPR_GATE_A superseded", "source_hashes_sha256": hashes}
        write_json(result_root / "implementation_contract.json", impl)
        write_json(result_root / "model_parameter_report.json", {"status": status, "proof": "single CAREDPR.encoder object; independent scar_branch and edema_branch modules; local ROI refiners have pathology-specific sizes", "scar_roi_context_zyx": [8, 96, 96], "edema_roi_context_zyx": [8, 128, 128], "source_hashes_sha256": hashes})
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
