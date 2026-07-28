#!/usr/bin/env python3
"""Validate CARE-DPR Gate B-R1 superseded/failure evidence."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.care_dpr_gate_b_science import PATHOLOGIES, scientific_gate_from_casewise

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
MODEL_NAME = "A2_care_dpr_gate_b_r1_selected"
ANCHOR_NAME = "A0_nnunet_anchor"


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


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def model_summary_deltas(summary_rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    by = {(r.get("population"), r.get("model"), r.get("pathology")): r for r in summary_rows}
    out: dict[str, dict[str, float]] = {}
    for pathology in PATHOLOGIES:
        anchor = by.get(("fold0_complete_trimodal16", ANCHOR_NAME, pathology))
        pred = by.get(("fold0_complete_trimodal16", MODEL_NAME, pathology))
        if not anchor or not pred:
            out[pathology] = {"missing": 1.0}
            continue
        out[pathology] = {
            "dice_delta_mean": as_float(pred.get("dice_mean")) - as_float(anchor.get("dice_mean")),
            "hd95_ratio_of_means": as_float(pred.get("hd95_mean_mm")) / max(as_float(anchor.get("hd95_mean_mm")), 1e-6),
            "remote_fp_ratio_of_means": as_float(pred.get("remote_fp_volume_mean_mm3")) / max(as_float(anchor.get("remote_fp_volume_mean_mm3")), 1e-6),
            "component_count_ratio_of_means": as_float(pred.get("component_count_mean")) / max(as_float(anchor.get("component_count_mean")), 1.0),
            "pred_exact_hd_infinite_cases": as_float(pred.get("exact_hd_infinite_cases")),
            "anchor_exact_hd_infinite_cases": as_float(anchor.get("exact_hd_infinite_cases")),
        }
    return out


def unauthorized_regression_gate_present(summary: dict[str, Any], selection: dict[str, Any], threshold_rows: list[dict[str, str]]) -> bool:
    selected = selection.get("selected") or summary.get("selected_checkpoint") or {}
    contract = summary.get("two_pass_full_volume_inference_contract") or {}
    if selected.get("scar_utility_regression_min") is not None or selected.get("edema_utility_regression_min") is not None:
        return True
    if summary.get("scar_utility_regression_min") is not None or summary.get("edema_utility_regression_min") is not None:
        return True
    if "utility_regression_min" in str(contract.get("acceptance_rule", "")):
        return True
    return any(row.get("utility_regression_min") not in {None, "", "None", "null"} for row in threshold_rows)


def validate(result_root: Path, runtime_root: Path | None = None) -> dict[str, Any]:
    runtime_root = runtime_root or result_root / "runtime/formal_fold0_r1"
    eval_root = runtime_root / "gate_b_r1_evaluation"
    summary = read_json(eval_root / "gate_b_r1_summary.json")
    root_summary = read_json(result_root / "gate_b_r1_summary.json")
    selection = read_json(eval_root / "gate_b_r1_checkpoint_threshold_selection.json")
    mechanism = read_json(eval_root / "gate_b_r1_mechanism_report.json")
    scientific_recorded = read_json(eval_root / "gate_b_r1_scientific_gate.json")
    activation = read_csv(eval_root / "gate_b_r1_activation_audit.csv")
    candidates = read_csv(eval_root / "gate_b_r1_outer_candidate_rows.csv")
    threshold_rows = read_csv(eval_root / "gate_b_r1_threshold_rows.csv")
    casewise = read_csv(eval_root / "gate_b_r1_casewise_metrics.csv")
    model_summary = read_csv(eval_root / "gate_b_r1_model_summary.csv")
    no_t2_rows = read_csv(eval_root / "gate_b_r1_no_t2_safety_audit.csv")
    recomputed_gate, recomputed_help_harm = scientific_gate_from_casewise(
        casewise,
        no_t2_rows,
        population="fold0_complete_trimodal16",
        model_name=MODEL_NAME,
    )
    summary_deltas = model_summary_deltas(model_summary)
    selected = selection.get("selected") or {}
    utility = mechanism.get("utility_metrics") or {}
    source_hashes = summary.get("source_hashes") or {}
    unauthorized_regression = unauthorized_regression_gate_present(summary, selection, threshold_rows)
    recorded_failures = set(scientific_recorded.get("failures") or [])
    recomputed_failures = set(recomputed_gate.get("failures") or [])
    no_plus005_summary = all(summary_deltas[p].get("dice_delta_mean", 0.0) < 0.005 for p in PATHOLOGIES)
    safety_noninferior = all(recomputed_gate["complete16_delta_summary"][p]["not_below_anchor_by_more_than_0.005"] for p in PATHOLOGIES)
    checks = {
        "gate_is_r1": summary.get("gate") == "DPR_GATE_B_R1",
        "superseded_by_r2_recorded": summary.get("status") == "SUPERSEDED_BY_DPR_GATE_B_R2" and root_summary.get("status") == "SUPERSEDED_BY_DPR_GATE_B_R2",
        "scientific_credit_zero": summary.get("scientific_final_output_credit") == 0 and scientific_recorded.get("scientific_final_output_credit") == 0,
        "fold_expansion_false": summary.get("fold_expansion_authorized") is False and scientific_recorded.get("fold_expansion_authorized") is False,
        "scientific_gate_independently_recomputed_fail": recomputed_gate.get("status") == "FAIL" and "no_pathology_improves_by_at_least_0.005" in recomputed_failures,
        "recorded_scientific_matches_recompute": scientific_recorded.get("status") == recomputed_gate.get("status") and recomputed_failures.issubset(recorded_failures),
        "model_summary_confirms_no_plus005": no_plus005_summary,
        "model_summary_all_three_present": all("missing" not in summary_deltas[p] for p in PATHOLOGIES),
        "no_outer_selection": summary.get("outer_fold0_used_for_checkpoint_or_threshold_selection") is False and selection.get("outer_fold0_used") is False,
        "predicted_roi_only": summary.get("teacher_roi_inner_outer_inference") is False and summary.get("predicted_roi_only_for_inner_outer_inference") is True,
        "all_8_checkpoints_considered": len({r.get("checkpoint_step") for r in selection.get("rows", [])}) == 8,
        "independent_thresholds_recorded": float(selected.get("scar_utility_threshold", -1)) != -1 and float(selected.get("edema_utility_threshold", -1)) != -1,
        "threshold_rows_signed_fields": bool(threshold_rows) and all("signed_net_utility" in r and "negative_accepted_utility" in r and "harmful_accepted_candidate_count" in r for r in threshold_rows),
        "real_candidates_only": bool(candidates) and utility.get("primary_metric_source") == "model_real_full_volume_candidates_only" and utility.get("synthetic_utility_variants_used_for_primary_gate") is False,
        "two_pass_contract": (summary.get("two_pass_full_volume_inference_contract") or {}).get("status") == "PASS" and all(as_bool(r.get("two_pass_full_volume_candidate_pipeline")) for r in activation),
        "no_patch_final_label_averaging": all(not as_bool(r.get("pass1_aggregates_patch_final_labels")) for r in activation),
        "pass2_refines_each_candidate": all(as_bool(r.get("pass2_refines_each_candidate")) for r in activation),
        "no_t2_exact_zero": (summary.get("no_t2_exact_zero") or {}).get("status") == "PASS" and recomputed_gate["contract_checks"]["no_t2_exact_zero"],
        "source_hashes_include_r1": "scripts/evaluation/evaluate_care_dpr_gate_b_r1.py" in source_hashes,
        "unauthorized_regression_min_acknowledged": unauthorized_regression and summary.get("status") == "SUPERSEDED_BY_DPR_GATE_B_R2" and summary.get("scientific_final_output_credit") == 0,
    }
    known_bad_rejections = {
        "three_improves_false_but_status_pass_rejected": not (no_plus005_summary and scientific_recorded.get("status") == "PASS"),
        "missing_plus005_requirement_rejected": "no_pathology_improves_by_at_least_0.005" in recomputed_failures and summary.get("status") == "SUPERSEDED_BY_DPR_GATE_B_R2",
        "safety_noninferiority_as_scientific_gain_rejected": safety_noninferior and recomputed_gate.get("status") == "FAIL",
        "unauthorized_utility_regression_min_rejected": checks["unauthorized_regression_min_acknowledged"],
        "validator_independent_of_scientific_json_status": scientific_recorded.get("status") == recomputed_gate.get("status") and recomputed_failures.issubset(recorded_failures),
        "terminal_only_eval_rejected": checks["all_8_checkpoints_considered"],
        "patch_final_label_averaging_rejected": checks["no_patch_final_label_averaging"],
    }
    checks["known_bad_rejections_pass"] = all(known_bad_rejections.values())
    report = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_B_R1_VALIDATOR",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()},
        "known_bad_rejections": {k: "PASS" if v else "FAIL" for k, v in known_bad_rejections.items()},
        "scientific_gate_recorded_status": scientific_recorded.get("status"),
        "scientific_gate_recorded_failures": scientific_recorded.get("failures", []),
        "scientific_gate_recomputed_status": recomputed_gate.get("status"),
        "scientific_gate_recomputed_failures": recomputed_gate.get("failures", []),
        "model_summary_deltas": summary_deltas,
        "recomputed_help_harm_rows": len(recomputed_help_harm),
        "unauthorized_regression_gate_present": unauthorized_regression,
    }
    write_json(eval_root / "gate_b_r1_validator_report.json", report)
    write_json(result_root / "gate_b_r1_validator_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", default=str(RESULT_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--runtime-name", default="formal_fold0_r1")
    args = parser.parse_args()
    result_root = Path(args.result_root)
    runtime_root = Path(args.runtime_root) if args.runtime_root else result_root / "runtime" / args.runtime_name
    report = validate(result_root, runtime_root)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
