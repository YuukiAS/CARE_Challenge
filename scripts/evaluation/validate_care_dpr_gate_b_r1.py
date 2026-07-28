#!/usr/bin/env python3
"""Validate CARE-DPR Gate B-R1 lightweight evidence."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() == "true"


def validate(result_root: Path, runtime_root: Path | None = None) -> dict[str, Any]:
    runtime_root = runtime_root or result_root / "runtime/formal_fold0"
    eval_root = runtime_root / "gate_b_r1_evaluation"
    summary = read_json(eval_root / "gate_b_r1_summary.json")
    selection = read_json(eval_root / "gate_b_r1_checkpoint_threshold_selection.json")
    mechanism = read_json(eval_root / "gate_b_r1_mechanism_report.json")
    scientific = read_json(eval_root / "gate_b_r1_scientific_gate.json")
    activation = read_csv(eval_root / "gate_b_r1_activation_audit.csv")
    candidates = read_csv(eval_root / "gate_b_r1_outer_candidate_rows.csv")
    threshold_rows = read_csv(eval_root / "gate_b_r1_threshold_rows.csv")
    selected = selection.get("selected") or {}
    utility = mechanism.get("utility_metrics") or {}
    source_hashes = summary.get("source_hashes") or {}
    checks = {
        "gate_is_r1": summary.get("gate") == "DPR_GATE_B_R1",
        "no_outer_selection": summary.get("outer_fold0_used_for_checkpoint_or_threshold_selection") is False and selection.get("outer_fold0_used") is False,
        "predicted_roi_only": summary.get("teacher_roi_inner_outer_inference") is False and summary.get("predicted_roi_only_for_inner_outer_inference") is True,
        "all_8_checkpoints_considered": len({r.get("checkpoint_step") for r in selection.get("rows", [])}) == 8,
        "independent_thresholds": float(selected.get("scar_utility_threshold", -1)) != -1 and float(selected.get("edema_utility_threshold", -1)) != -1,
        "selected_thresholds_nonzero_accept_reject": int(selected.get("scar_accepted", 0)) > 0 and int(selected.get("scar_rejected", 0)) > 0 and int(selected.get("edema_accepted", 0)) > 0 and int(selected.get("edema_rejected", 0)) > 0,
        "selected_signed_net_positive": float(selected.get("scar_signed_net_utility", 0.0)) > 0.0 and float(selected.get("edema_signed_net_utility", 0.0)) > 0.0,
        "threshold_rows_signed_fields": bool(threshold_rows) and all("signed_net_utility" in r and "negative_accepted_utility" in r and "harmful_accepted_candidate_count" in r for r in threshold_rows),
        "real_candidates_only": bool(candidates) and utility.get("primary_metric_source") == "model_real_full_volume_candidates_only" and utility.get("synthetic_utility_variants_used_for_primary_gate") is False,
        "two_pass_contract": (summary.get("two_pass_full_volume_inference_contract") or {}).get("status") == "PASS" and all(as_bool(r.get("two_pass_full_volume_candidate_pipeline")) for r in activation),
        "no_patch_final_label_averaging": all(not as_bool(r.get("pass1_aggregates_patch_final_labels")) for r in activation),
        "pass2_refines_each_candidate": all(as_bool(r.get("pass2_refines_each_candidate")) for r in activation),
        "no_t2_exact_zero": (summary.get("no_t2_exact_zero") or {}).get("status") == "PASS",
        "source_hashes_include_r1": "scripts/evaluation/evaluate_care_dpr_gate_b_r1.py" in source_hashes,
        "scientific_gate_recorded_no_expansion": scientific.get("fold_expansion_authorized") is False,
        "scientific_gate_pass": scientific.get("status") == "PASS" and not scientific.get("failures"),
        "help_harm_material_threshold_recorded": all("help_harm_dice_delta_threshold" in row for row in read_csv(eval_root / "gate_b_r1_help_harm.csv")),
    }
    known_bad_rejections = {
        "terminal_only_eval_rejected": checks["all_8_checkpoints_considered"],
        "global_threshold_rejected": checks["independent_thresholds"],
        "positive_only_realized_gain_rejected": checks["threshold_rows_signed_fields"],
        "selected_threshold_accepts_zero_rejected": checks["selected_thresholds_nonzero_accept_reject"],
        "outer_threshold_masquerading_inner_rejected": checks["no_outer_selection"],
        "synthetic_variants_primary_gate_rejected": checks["real_candidates_only"],
        "patch_candidate_decision_rejected": checks["two_pass_contract"] and checks["pass2_refines_each_candidate"],
        "patch_final_label_averaging_rejected": checks["no_patch_final_label_averaging"],
    }
    checks["known_bad_rejections_pass"] = all(known_bad_rejections.values())
    report = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_B_R1_VALIDATOR",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()},
        "known_bad_rejections": {k: "PASS" if v else "FAIL" for k, v in known_bad_rejections.items()},
        "scientific_gate_status": scientific.get("status"),
        "scientific_gate_failures": scientific.get("failures", []),
    }
    write_json(eval_root / "gate_b_r1_validator_report.json", report)
    write_json(result_root / "gate_b_r1_validator_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", default=str(RESULT_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--runtime-name", default="formal_fold0")
    args = parser.parse_args()
    result_root = Path(args.result_root)
    runtime_root = Path(args.runtime_root) if args.runtime_root else result_root / "runtime" / args.runtime_name
    report = validate(result_root, runtime_root)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
