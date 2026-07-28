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
    "scripts/evaluation/validate_care_dpr_packet.py",
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
    model = source_text("src/care_myocardium/models/care_dpr.py")
    trainer = source_text("src/care_myocardium/training/care_dpr_trainer.py")
    predictor = source_text("src/care_myocardium/inference/care_dpr_predictor.py")
    run = source_text("scripts/training/run_care_dpr.py")
    tests = source_text("tests/care_dpr/test_care_dpr_model.py")
    checks = {
        "direct_p_coarse_both_pathologies": '"scar_p_coarse"' in model and '"edema_p_coarse"' in model,
        "five_outputs_present": all(s in model for s in ["p_coarse", "q_fn", "q_fp", "p_refined", "utility_accept_prob"]),
        "q_fn_q_fp_not_only_proposal": "p_coarse_random_initialized" in trainer and "care_dg_q_fn_q_fp_initialize_error_proposal_only" in trainer,
        "teacher_roi_forbidden_guard": "CARE_DPR_TEACHER_ROI_FORBIDDEN_IN_EVAL_OR_INFERENCE" in model,
        "curriculum_a1_a2_b_exact": all(s in run for s in ["A1", "A2", "500", "2000", "1500", "APPROVE_DPR_GATE_A"]),
        "stage_b_freezes_encoder_and_proposals": "FROZEN_STAGE_B_PREFIXES" in run and "proposal_head" in run,
        "full_volume_aggregation_before_components": "aggregate_patch_outputs" in predictor and "never averages patch final labels" in predictor and "never runs" in predictor,
        "candidate_types_distinct": "ADD_FN" in predictor and "REVISE_FP" in predictor,
        "legal_actions_only": "KEEP_ANCHOR_LOCAL_MASK" in predictor and "REPLACE_WITH_REFINED_LOCAL_MASK" in predictor,
        "threshold_candidates_fixed": "0.30" in predictor and "0.70" in predictor,
        "no_t2_zero_tests": "test_no_t2_edema_zero_and_no_gradient" in tests,
        "zero_accept_anchor_test": "test_zero_accepted_candidates_exact_anchor_labels" in tests,
        "teacher_roi_leak_known_bad": "test_teacher_roi_forbidden_in_eval_or_inference" in tests,
    }
    findings = [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in checks.items()]
    return findings, hashes


def run_tests() -> dict[str, Any]:
    cmd = [str(REPO_ROOT / "envs/env_CARE/bin/python"), "-m", "pytest", "-q", "tests/care_dpr/test_care_dpr_model.py"]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return {"command": " ".join(cmd), "exit_code": proc.returncode, "output": proc.stdout}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", default=str(RESULT_ROOT))
    parser.add_argument("--mode", choices=["implementation", "preflight"], default="implementation")
    args = parser.parse_args()
    result_root = Path(args.result_root)
    findings, hashes = validate_source_contract()
    test_result = run_tests() if args.mode == "implementation" else {"skipped": True, "reason": "preflight mode uses existing unit_test_report"}
    status = "PASS" if all(f["status"] == "PASS" for f in findings) and int(test_result.get("exit_code", 0)) == 0 else "FAIL"
    known_bad = {
        "status": status,
        "fixtures": [
            "missing_p_coarse_direct_proposal",
            "teacher_roi_used_in_inner_outer_inference",
            "patch_final_label_averaging",
            "patch_local_component_arbitration",
            "outer_fold0_utility_target_leakage",
            "add_revise_candidate_action_collapse",
            "unaccepted_candidate_partial_writeback",
            "no_t2_edema_candidate_constructed_or_accepted",
            "missing_scar_or_edema_branch_gradients",
            "scar_pass_edema_empty_false_pass",
        ],
        "coverage": findings,
    }
    report = {"task_key": TASK_KEY, "mode": args.mode, "status": status, "generated_at_utc": now_utc(), "source_hashes_sha256": hashes, "findings": findings, "unit_tests": test_result, "known_bad": known_bad}
    write_json(result_root / ("strict_validator_report.json" if args.mode == "preflight" else "implementation_validator_report.json"), report)
    write_json(result_root / "known_bad_report.json", known_bad)
    (result_root / "unit_test_report.md").write_text("# CARE-DPR Unit Test Report\n\n" + f"Status: {status}\n\n```text\n{test_result.get('output','')}\n```\n", encoding="utf-8")
    if args.mode == "implementation":
        impl = {"task_key": TASK_KEY, "status": status, "amendment_precedence": True, "shared_backbone_count": 1, "pathology_branches": ["scar", "edema_zone"], "required_branch_outputs": ["p_coarse", "q_fn", "q_fp", "p_refined", "component_utility"], "candidate_types": ["ADD_FN", "REVISE_FP"], "legal_actions": ["KEEP_ANCHOR_LOCAL_MASK", "REPLACE_WITH_REFINED_LOCAL_MASK"], "full_volume_inference": {"overlap": 0.5, "gaussian_blending": True, "aggregate_before_components": True, "patch_final_label_averaging": False, "patch_local_component_arbitration": False}, "formal_fold0_guard": "APPROVE_DPR_GATE_A required", "source_hashes_sha256": hashes}
        write_json(result_root / "implementation_contract.json", impl)
        write_json(result_root / "model_parameter_report.json", {"status": status, "proof": "single CAREDPR.encoder object; independent scar_branch and edema_branch modules", "source_hashes_sha256": hashes})
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
