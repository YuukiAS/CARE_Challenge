#!/usr/bin/env python3
"""Strict Route B Round04 B6 MyoPS terminal validator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


READY_TOKEN = "ROUTE_B_ROUND04_B6_MYOPS_TERMINAL_EVIDENCE_READY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def add(errors: list[dict[str, str]], key: str, detail: str) -> None:
    errors.append({"key": key, "detail": detail})


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def is_true(value: Any) -> bool:
    return value is True or str(value) == "True"


def validate(result_dir: Path, require_token: str) -> dict[str, Any]:
    required = [
        "training_adequacy.csv",
        "checkpoint_selection.csv",
        "selected_checkpoint_reload.json",
        "fresh_force_evaluation_receipt.json",
        "casewise_help_harm.csv",
        "hard_subgroup_matrix.csv",
        "myops_intervention_matrix.csv",
        "official_output_roundtrip.json",
        "completion.json",
    ]
    errors: list[dict[str, str]] = []
    for name in required:
        if not (result_dir / name).is_file():
            add(errors, "FRESH_FORCE_EVALUATION_MISSING", f"missing {name}")
    if errors:
        return {"status": "FAIL", "errors": errors, "failure_keys": sorted({e["key"] for e in errors})}

    training = read_csv_rows(result_dir / "training_adequacy.csv")[0]
    selection = read_csv_rows(result_dir / "checkpoint_selection.csv")
    reload = load_json(result_dir / "selected_checkpoint_reload.json")
    fresh = load_json(result_dir / "fresh_force_evaluation_receipt.json")
    cases = read_csv_rows(result_dir / "casewise_help_harm.csv")
    subgroups = read_csv_rows(result_dir / "hard_subgroup_matrix.csv")
    interventions = read_csv_rows(result_dir / "myops_intervention_matrix.csv")
    roundtrip = load_json(result_dir / "official_output_roundtrip.json")
    completion = load_json(result_dir / "completion.json")

    if fresh.get("same_split_baseline_status") != "PASS":
        add(errors, "SAME_SPLIT_BASELINE_MISSING", "same-split baseline receipt missing or nonpass")
    if fresh.get("fresh_force_evaluation") is not True or fresh.get("cache_isolation") is not True:
        add(errors, "FRESH_FORCE_EVALUATION_MISSING", "fresh forced evaluation/cache isolation missing")
    if fresh.get("summary_type") != "terminal_summary_not_ablation":
        add(errors, "SUMMARY_MISNAMED_AS_ABLATION", "terminal summary mislabeled as ablation")
    if fresh.get("hosted_metric_claim") is True or roundtrip.get("hosted_metric_claim") is True:
        add(errors, "PROXY_METRIC_AS_HOSTED", "hosted metric authority claimed")

    if as_float(training.get("optimizer_steps")) < 8000:
        add(errors, "FRESH_FORCE_EVALUATION_MISSING", "optimizer steps below B6 minimum")
    if as_float(training.get("train_loop_seconds")) < 2400:
        add(errors, "FRESH_FORCE_EVALUATION_MISSING", "train seconds below B6 minimum")
    if as_float(training.get("validation_events")) < 4:
        add(errors, "FRESH_FORCE_EVALUATION_MISSING", "validation events below B6 minimum")
    if as_float(training.get("eval_cases")) < 44 or len(cases) < 44:
        add(errors, "FRESH_FORCE_EVALUATION_MISSING", "eval case rows below B6 minimum")
    if as_float(training.get("full_case_events")) < 4:
        add(errors, "FRESH_FORCE_EVALUATION_MISSING", "full-case event rows below B6 minimum")
    if str(training.get("loss_decrease")) != "True":
        add(errors, "FRESH_FORCE_EVALUATION_MISSING", "loss did not decrease")

    if reload.get("status") != "PASS" or not any(row.get("selected") == "True" for row in selection):
        add(errors, "SELECTED_CHECKPOINT_NOT_RELOADED", "selected checkpoint reload/selection failed")
    if roundtrip.get("status") != "PASS" or roundtrip.get("raw_label_roundtrip") is not True:
        add(errors, "FRESH_FORCE_EVALUATION_MISSING", "official output roundtrip failed")

    if not any(row.get("scar_positive") == "True" for row in cases):
        add(errors, "SCAR_POSITIVE_ROWS_MISSING", "scar-positive case rows missing")
    if not any(row.get("t2_present") == "True" and row.get("t2_edema_positive") == "True" for row in cases):
        add(errors, "T2_PRESENT_EDEMA_POSITIVE_ROWS_MISSING", "T2-present edema-positive rows missing")
    if not any(row.get("no_t2") == "True" for row in cases):
        add(errors, "NO_T2_SAFETY_ROWS_MISSING", "no-T2 safety rows missing")
    if not any(row.get("center") == "CenterB" for row in cases) or not any(row.get("center") == "CenterC" for row in cases):
        add(errors, "CENTERB_OR_CENTERC_ROWS_MISSING", "CenterB/CenterC rows missing")
    if any(row.get("empty_gt_counted_as_help") == "True" for row in cases):
        add(errors, "EMPTY_GT_COUNTED_AS_HELP", "empty GT row counted as help")
    if any(row.get("proxy_metric_as_hosted") == "True" or row.get("metric_scope") == "hosted" for row in cases):
        add(errors, "PROXY_METRIC_AS_HOSTED", "local proxy presented as hosted metric")

    subgroup_counts = {row.get("subgroup"): int(as_float(row.get("row_count"))) for row in subgroups}
    for name, key in [
        ("scar_positive", "SCAR_POSITIVE_ROWS_MISSING"),
        ("t2_present_edema_positive", "T2_PRESENT_EDEMA_POSITIVE_ROWS_MISSING"),
        ("no_t2_safety", "NO_T2_SAFETY_ROWS_MISSING"),
        ("CenterB", "CENTERB_OR_CENTERC_ROWS_MISSING"),
        ("CenterC", "CENTERB_OR_CENTERC_ROWS_MISSING"),
    ]:
        if subgroup_counts.get(name, 0) <= 0:
            add(errors, key, f"subgroup {name} missing")
    if any(row.get("terminal_summary_not_ablation") != "True" for row in subgroups):
        add(errors, "SUMMARY_MISNAMED_AS_ABLATION", "subgroup summary marked as ablation")

    effect_rows = [row for row in interventions if row.get("component") in {"final_scar_logits", "final_edema_logits"}]
    if not effect_rows or all(as_float(row.get("final_output_delta_l1")) <= 0 for row in effect_rows):
        add(errors, "FINAL_OUTPUT_INTERVENTION_ZERO_OR_MISSING", "final output intervention effect missing")
    if any(row.get("component") == "no_t2_edema_guard" and as_float(row.get("final_output_delta_l1")) != 0.0 for row in interventions):
        add(errors, "NO_T2_SAFETY_ROWS_MISSING", "no-T2 edema guard changed output")
    if not all(is_true(row.get("intervention_changes_final_output")) for row in effect_rows):
        add(errors, "FINAL_OUTPUT_INTERVENTION_ZERO_OR_MISSING", "final output intervention flag missing")

    if completion.get("completion_token") != require_token or require_token != READY_TOKEN or completion.get("status") != "PASS":
        add(errors, "FRESH_FORCE_EVALUATION_MISSING", "completion token/status mismatch")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "failure_keys": sorted({e["key"] for e in errors}),
        "completion_token": completion.get("completion_token"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--require-token", default=READY_TOKEN)
    args = parser.parse_args()
    report = validate(args.input, args.require_token)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and report["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
