#!/usr/bin/env python3
"""Validate lightweight CARE-DPR Gate B evidence."""

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
RUNTIME_ROOT = RESULT_ROOT / "runtime" / "formal_fold0"


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


def validate(result_root: Path) -> dict[str, Any]:
    runtime = result_root / "runtime" / "formal_fold0"
    eval_root = runtime / "gate_b_evaluation"
    receipt = read_json(runtime / "fold_training_receipt.json")
    gate = read_json(eval_root / "gate_b_summary.json")
    mechanism = read_json(eval_root / "gate_b_mechanism_report.json")
    selection = read_json(eval_root / "gate_b_checkpoint_threshold_selection.json")
    scientific = read_json(eval_root / "gate_b_scientific_gate.json")
    a2 = read_json(runtime / "sampler_audit_stage_a2.json")
    b = read_json(runtime / "sampler_audit_stage_b.json")
    preflight_validator = read_json(result_root / "preflight_validator_report.json")
    consistency = read_json(result_root / "gate_a_r2_consistency_validator_report.json")
    casewise = read_csv(eval_root / "gate_b_casewise_metrics.csv")
    summary = read_csv(eval_root / "gate_b_model_summary.csv")
    candidate_rows = read_csv(eval_root / "gate_b_outer_candidate_rows.csv")
    activation = read_csv(eval_root / "gate_b_activation_audit.csv")
    no_t2 = read_csv(eval_root / "gate_b_no_t2_safety_audit.csv")

    by_summary = {(r["population"], r["model"], r["pathology"]): r for r in summary}
    checks: dict[str, bool] = {
        "formal_receipt_pass_4000": receipt.get("status") == "PASS" and int(receipt.get("actual_optimizer_steps", -1)) == 4000,
        "preflight_credit_zero": int(gate.get("preflight_credit", -1)) == 0,
        "outer_selection_forbidden": gate.get("outer_fold0_used_for_checkpoint_or_threshold_selection") is False and selection.get("outer_fold0_used_for_checkpoint_or_threshold_selection") is False,
        "predicted_roi_inner_outer_only": gate.get("teacher_roi_inner_outer_inference") is False and gate.get("predicted_roi_only_for_inner_outer_inference") is True,
        "outer44_complete16_counts": int(gate.get("outer_heldout_cases", -1)) == 44 and int(gate.get("complete_trimodal_heldout_cases", -1)) == 16,
        "casewise_contains_anchor_and_dpr": bool(by_summary.get(("fold0_outer44", "A0_nnunet_anchor", "scar"))) and bool(by_summary.get(("fold0_outer44", "A2_care_dpr_gate_b_selected", "scar"))) and bool(by_summary.get(("fold0_complete_trimodal16", "A2_care_dpr_gate_b_selected", "edema_zone"))),
        "two_pass_contract_pass": (gate.get("two_pass_full_volume_inference_contract") or {}).get("status") == "PASS" and all(str(r.get("two_pass_full_volume_candidate_pipeline")).lower() == "true" for r in activation),
        "no_patch_final_label_averaging": all(str(r.get("pass1_aggregates_patch_final_labels")).lower() == "false" for r in activation),
        "pass2_refines_each_candidate": all(str(r.get("pass2_refines_each_candidate")).lower() == "true" for r in activation),
        "real_candidate_rows_nonzero": len(candidate_rows) > 0 and (mechanism.get("utility_metrics") or {}).get("primary_metric_source") == "model_real_full_volume_candidates_only",
        "utility_targets_both_classes": int((mechanism.get("utility_metrics") or {}).get("accept_target_positive_count", 0)) > 0 and int((mechanism.get("utility_metrics") or {}).get("accept_target_negative_count", 0)) > 0,
        "threshold_has_accept_reject": any(bool(row.get("has_nonzero_accepted_and_rejected")) for row in (mechanism.get("utility_metrics") or {}).get("threshold_candidates", [])),
        "no_t2_exact_zero": bool(no_t2) and all(r.get("status") == "PASS" for r in no_t2) and (gate.get("no_t2_exact_zero") or {}).get("status") == "PASS",
        "checkpoint_reload_exact": (receipt.get("checkpoint_reload") or {}).get("status") == "PASS" and (receipt.get("checkpoint_reload") or {}).get("parameter_values_exact") is True and (receipt.get("checkpoint_reload") or {}).get("fixed_outputs_exact") is True,
        "sampler_stage_a2_b_pass": a2.get("status") == "PASS" and b.get("status") == "PASS",
        "gate_a_r2_validators_passed": preflight_validator.get("status") == "PASS" and consistency.get("status") == "PASS",
        "notification_json_present": (result_root / "checkpoint_notifications" / "dpr_gate_b.json").is_file(),
        "scientific_gate_recorded": scientific.get("status") in {"PASS", "FAIL"} and scientific.get("scientific_expansion_authorized") is False,
    }
    report = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_B_VALIDATOR",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()},
        "casewise_rows": len(casewise),
        "summary_rows": len(summary),
        "outer_candidate_rows": len(candidate_rows),
        "scientific_gate_status": scientific.get("status"),
        "scientific_gate_failures": scientific.get("failures", []),
    }
    write_json(eval_root / "gate_b_validator_report.json", report)
    write_json(result_root / "gate_b_validator_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", default=str(RESULT_ROOT))
    args = parser.parse_args()
    report = validate(Path(args.result_root))
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
