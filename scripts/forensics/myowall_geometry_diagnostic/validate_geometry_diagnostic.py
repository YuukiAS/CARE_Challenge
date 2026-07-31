#!/usr/bin/env python3
"""Fail-closed validator for MyoWall geometry diagnostic closure."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_KEY = "20260731_care_myowall_geometry_diagnostic_closure"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
PREV_TASK_KEY = "20260731_care_myowall_if_mechanism_pilot"
PREV_RESULT_ROOT = REPO_ROOT / "results" / PREV_TASK_KEY
REQUIRED = [
    "controller_context.json",
    "frozen_input_manifest.json",
    "pilot_train_threshold_search.csv",
    "frozen_repair_contract.json",
    "geometry_casewise_all_modes.csv",
    "geometry_summary_all_modes.csv",
    "anatomy_casewise_metrics.csv",
    "anatomy_subgroup_metrics.csv",
    "failed_reason_counts.csv",
    "case_attribution.csv",
    "geometry_diagnostic_atlas.pdf",
    "geometry_diagnostic_contact_sheet.png",
    "case_visual_findings.md",
    "gt_geometry_safety_receipt.json",
    "known_bad_report.json",
    "mapper_report_final.md",
    "controller_report.md",
    "completion_check.md",
    "MANIFEST.md",
    "notification_brief.json",
]
MODES = {"G0_current_predicted", "G1_GT_anatomy", "G2_supported_denominator", "G3_repaired_predicted"}
FAILED_FIVE = {"Case3029", "Case8003", "Case8022", "Case8027", "Case8028"}
ALLOWED_DECISIONS = {"GEOMETRY_EXTRACTION_REPAIRABLE", "PREDICTED_ANATOMY_SOURCE_INSUFFICIENT", "HARD_WALL_REPRESENTATION_INVALID", "MIXED_GATE_AND_ANATOMY_FAILURE", "OPERATIONALLY_BLOCKED_ASSET_MISSING", "OPERATIONALLY_BLOCKED_CURRENT_GEOMETRY_NOT_REPRODUCIBLE"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=RESULT_ROOT / "strict_validator_report.json")
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    for name in REQUIRED:
        path = RESULT_ROOT / name
        if not path.is_file():
            errors.append(f"missing_required_output:{name}")
        elif path.stat().st_size == 0:
            errors.append(f"empty_required_output:{name}")
    if errors:
        write_json(args.output, {"status": "FAIL", "errors": errors, "warnings": warnings})
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2, ensure_ascii=False))
        return 1

    manifest = read_json(RESULT_ROOT / "frozen_input_manifest.json")
    if manifest.get("pilot_inner_count") != 32:
        errors.append("pilot_inner_count_not_32")
    if manifest.get("pilot_train_count") != 144:
        errors.append("pilot_train_count_not_144")
    if manifest.get("fold1_outer_accessed") is not False:
        errors.append("fold1_outer_accessed_not_false")
    if manifest.get("previous_stock_parity_status") != "PASS":
        errors.append("stock_parity_not_PASS")
    if abs(float(manifest.get("previous_case_geometry_valid_rate", -1)) - 0.84375) > 1e-9:
        errors.append("previous_case_geometry_valid_rate_not_frozen")

    repair = read_json(RESULT_ROOT / "frozen_repair_contract.json")
    if repair.get("selected_on") != "pilot_train_only" or repair.get("pilot_inner_used_for_selection") is not False:
        errors.append("pilot_inner_used_for_threshold_selection")
    for key in ("center_specific_threshold", "modality_specific_threshold", "case_specific_threshold", "gt_assisted_cleanup"):
        if repair.get(key) is not False:
            errors.append(f"forbidden_repair_contract:{key}")
    winner = repair.get("winner", {})
    if winner.get("case_count") != 144:
        errors.append("threshold_search_not_all_144_pilot_train")

    rows = read_csv(RESULT_ROOT / "geometry_casewise_all_modes.csv")
    if len(rows) != 32 * 4:
        errors.append(f"geometry_casewise_row_count:{len(rows)}")
    if {r["mode"] for r in rows} != MODES:
        errors.append("missing_required_geometry_modes")
    for mode in MODES:
        cases = {r["case_id"] for r in rows if r["mode"] == mode}
        if len(cases) != 32:
            errors.append(f"mode_case_count_not_32:{mode}:{len(cases)}")
    g0 = [r for r in rows if r["mode"] == "G0_current_predicted"]
    old = {r["case_id"]: r for r in read_csv(PREV_RESULT_ROOT / "geometry_casewise_metrics.csv")}
    for row in g0:
        ref = old.get(row["case_id"])
        if not ref:
            errors.append(f"g0_missing_old_case:{row['case_id']}")
            continue
        for field in ("raw_valid_angle_fraction", "valid_angle_fraction", "active_slice_count", "wall_roundtrip_dice"):
            if abs(float(row[field]) - float(ref[field])) > 1e-6:
                errors.append(f"g0_not_reproduced:{row['case_id']}:{field}")
        if str(row["geometry_valid"]) != str(ref["geometry_valid"]):
            errors.append(f"g0_geometry_valid_not_reproduced:{row['case_id']}")
    failed_cases = {r["case_id"] for r in g0 if str(r["geometry_valid"]) in {"False", "false", "0"}}
    if failed_cases != FAILED_FIVE:
        errors.append(f"failed_five_not_preserved:{sorted(failed_cases)}")
    if not any(r["case_id"] == "Case3029" and r["mode"] == "G2_supported_denominator" for r in rows):
        errors.append("case3029_g2_denominator_missing")
    if not any(r["center"] == "CenterH" for r in rows):
        errors.append("centerh_missing_from_casewise")

    anatomy = read_csv(RESULT_ROOT / "anatomy_casewise_metrics.csv")
    if len(anatomy) < 64:
        errors.append("predicted_anatomy_vs_gt_metrics_missing")
    for field in ("lv_dice", "lv_hd95_mm", "myocardium_union_dice", "myocardium_union_hd95_mm", "lv_empty_slice_count", "wall_empty_slice_count", "lv_component_count", "wall_component_count"):
        if field not in anatomy[0]:
            errors.append(f"anatomy_metric_field_missing:{field}")

    gt_receipt = read_json(RESULT_ROOT / "gt_geometry_safety_receipt.json")
    if gt_receipt.get("gt_geometry_runtime_only") is not True:
        errors.append("gt_geometry_not_runtime_only")
    if gt_receipt.get("gt_geometry_written_to_training_cache") is not False:
        errors.append("gt_geometry_written_to_training_cache")
    if gt_receipt.get("gt_geometry_used_as_formal_prediction") is not False:
        errors.append("gt_geometry_used_as_formal_prediction")

    decision = read_json(RESULT_ROOT / "diagnostic_decision.json")
    if decision.get("scientific_decision") not in ALLOWED_DECISIONS:
        errors.append("scientific_decision_not_allowed")
    report_text = (RESULT_ROOT / "controller_report.md").read_text(encoding="utf-8")
    if "controller_verification_decision: VERIFIED_COMPLETE" not in report_text:
        errors.append("controller_report_missing_verified_complete")
    if "PENDING_STRICT_VALIDATOR" in report_text:
        warnings.append("controller_report_validator_status_placeholder_present")

    changed = run(["git", "status", "--short", "--untracked-files=all"])
    forbidden_prefixes = [
        "src/care_myocardium/models/myowall_if/geometry.py",
        "src/care_myocardium/models/myowall_if/",
        "prompts/routes/handoffs/CURRENT.md",
        "wiki/README.md",
    ]
    allowed_prefixes = (
        "scripts/forensics/myowall_geometry_diagnostic/",
        "tests/forensics/myowall_geometry_diagnostic/",
        f"results/{TASK_KEY}/",
    )
    for line in changed.stdout.splitlines():
        if not line:
            continue
        name = line[3:] if len(line) > 3 else line
        if " -> " in name:
            name = name.split(" -> ", 1)[1]
        if name and not name.startswith(allowed_prefixes):
            errors.append(f"changed_path_outside_allowed_scope:{name}")
        if name in forbidden_prefixes or any(name.startswith(prefix) for prefix in forbidden_prefixes if prefix.endswith("/")):
            errors.append(f"forbidden_production_or_state_change:{name}")
    for forbidden in ("arm_C0_training_summary.json", "arm_W1_training_summary.json", "arm_W2_training_summary.json", "arm_W3_training_summary.json"):
        if (RESULT_ROOT / forbidden).exists():
            errors.append(f"formal_arm_training_artifact_present:{forbidden}")
    brief = read_json(RESULT_ROOT / "notification_brief.json")
    if brief.get("final_status") not in {"complete", "blocked"}:
        errors.append("notification_final_status_invalid")
    forbidden_tokens = ["PENDING", "RUNNING", "NEEDS_MONITOR", "JOB_SUBMITTED", "AWAITING_SACCT"]
    brief_text = json.dumps(brief)
    for token in forbidden_tokens:
        if token in brief_text:
            errors.append(f"notification_contains_forbidden_monitor_token:{token}")
    known_bad = read_json(RESULT_ROOT / "known_bad_report.json")
    if known_bad.get("status") != "PASS" or len(known_bad.get("known_bad", [])) < 21:
        errors.append("known_bad_report_incomplete")
    status = "PASS" if not errors else "FAIL"
    payload = {"status": status, "errors": errors, "warnings": warnings, "checked_required_outputs": REQUIRED}
    write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
