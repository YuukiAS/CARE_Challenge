#!/usr/bin/env python3
"""Fail-closed validator for CARE metric-truth reconciliation packets."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_RESULT_FILES = [
    "source_inventory.csv",
    "score_occurrence_inventory.csv",
    "decoder_reset_score_semantics.json",
    "decoder_reset_score_lineage.csv",
    "metric_truth_table.csv",
    "metric_semantics_contract.json",
    "metric_truth_receipt.json",
    "score_lineage_report.md",
    "deep_research_score_corrections.md",
    "controller_report.md",
    "completion_check.md",
    "MANIFEST.md",
]

REQUIRED_TABLE_COLUMNS = [
    "score_contract_id",
    "model_id",
    "model_role",
    "checkpoint_sha256",
    "prediction_sha256",
    "case_set_id",
    "case_count",
    "train_relation",
    "population",
    "pathology",
    "label_semantics",
    "metric",
    "value",
    "ci_if_available",
    "threshold",
    "decode",
    "source_path",
    "evidence_grade",
    "allowed_comparison_group",
    "forbidden_comparison_group",
]

REQUIRED_OCCURRENCE_COLUMNS = [
    "score_id",
    "value",
    "source_path",
    "source_sha256",
    "source_row_or_key",
    "model_id",
    "checkpoint_sha256",
    "prediction_sha256",
    "case_set_id",
    "case_count",
    "train_case_relationship",
    "population_role",
    "pathology_object",
    "label_definition",
    "metric_name",
    "metric_implementation",
    "physical_spacing_used",
    "empty_gt_policy",
    "positive_gt_only",
    "threshold",
    "decode_rule",
    "is_hosted",
    "is_clean_oof",
    "is_train_on_case",
    "is_prediction_parity",
    "claim_allowed",
    "notes",
]

CORE_IDS = {
    "D0_INNER_SELECT_STOCK_GT_SCAR",
    "D0_INNER_SELECT_STOCK_GT_PURE_EDEMA",
    "D1_INNER_SELECT_DECODER_RESET_SCAR",
    "D1_INNER_SELECT_DECODER_RESET_PURE_EDEMA",
    "D2_INNER_SELECT_TOP_TRAIN_SCAR",
    "D2_INNER_SELECT_TOP_TRAIN_PURE_EDEMA",
    "D3_INNER_SELECT_FULL_SHORT_FT_SCAR",
    "D3_INNER_SELECT_FULL_SHORT_FT_PURE_EDEMA",
    "NNUNET_CLEAN_OOF_SCAR_220",
    "NNUNET_CLEAN_OOF_PURE_EDEMA_T2_80",
    "MOSAIC_CLEAN_OOF_SCAR_220",
    "MOSAIC_CLEAN_OOF_PURE_EDEMA_T2_80",
    "PRISM_W3_OUTER_ONCE_SCAR",
    "PRISM_W3_OUTER_ONCE_INTERNAL_EDEMA_ZONE",
    "NNUNET_FOLD0_OUTER_COMPARATOR_SCAR",
    "NNUNET_FOLD0_OUTER_COMPARATOR_INTERNAL_EDEMA_ZONE",
    "MOSAIC_HOSTED_SCAR_20260706_USER_ATTESTED",
    "MOSAIC_HOSTED_EDEMA_20260706_USER_ATTESTED",
    "MOSAIC_HOSTED_CINEMYOPS_20260708_CLOSEST_FINAL_RECIPE",
}

VALID_SHA_SENTINELS = {"NOT_APPLICABLE_HOSTED_HIDDEN", "NOT_RECOMPUTABLE_FROM_LOCAL_PREDICTION"}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def truth_errors(result_dir: Path) -> list[str]:
    errors: list[str] = []
    missing = [name for name in REQUIRED_RESULT_FILES if not (result_dir / name).exists()]
    if missing:
        errors.append("missing required result files: " + ", ".join(missing))
        return errors

    rows = read_csv(result_dir / "metric_truth_table.csv")
    occurrences = read_csv(result_dir / "score_occurrence_inventory.csv")
    receipt = read_json(result_dir / "metric_truth_receipt.json")
    contract = read_json(result_dir / "metric_semantics_contract.json")
    d0 = read_json(result_dir / "decoder_reset_score_semantics.json")

    if not rows:
        errors.append("metric_truth_table.csv has no rows")
    if not occurrences:
        errors.append("score_occurrence_inventory.csv has no rows")

    row_columns = set(rows[0].keys()) if rows else set()
    for col in REQUIRED_TABLE_COLUMNS:
        if col not in row_columns:
            errors.append(f"metric_truth_table missing column {col}")
    occ_columns = set(occurrences[0].keys()) if occurrences else set()
    for col in REQUIRED_OCCURRENCE_COLUMNS:
        if col not in occ_columns:
            errors.append(f"score_occurrence_inventory missing column {col}")

    row_by_id = {r.get("score_contract_id", ""): r for r in rows}
    missing_core = sorted(CORE_IDS - set(row_by_id))
    if missing_core:
        errors.append("missing core score_contract_id rows: " + ", ".join(missing_core))

    if receipt.get("canonical_t2_present_count") != 80:
        errors.append("canonical_t2_present_count must be 80")
    if contract.get("label_semantics", {}).get("official_pure_edema") != "internal label 4; official edema; T2-present denominator only":
        errors.append("official pure edema label semantics are not frozen to label 4 and T2-present")
    if contract.get("label_semantics", {}).get("internal_edema_zone") != "internal labels 4 or 5; internal diagnostic only; not official edema":
        errors.append("internal edema-zone semantics are not separated from official edema")
    d0_semantics = str(d0.get("d0_0p922_semantics", ""))
    d0_semantics_lower = d0_semantics.lower()
    if "GT Dice" not in d0_semantics:
        errors.append("D0 0.922 semantics must explicitly say GT Dice")
    if "prediction parity" in d0_semantics_lower and "not prediction parity" not in d0_semantics_lower:
        errors.append("D0 0.922 semantics must not be prediction parity")

    for r in rows:
        sid = r.get("score_contract_id", "")
        case_count = r.get("case_count", "")
        metric_impl = r.get("metric", "")
        source = r.get("source_path", "")
        evidence = r.get("evidence_grade", "")
        checkpoint = r.get("checkpoint_sha256", "")
        prediction = r.get("prediction_sha256", "")
        label = r.get("label_semantics", "")
        population = r.get("population", "")
        train_relation = r.get("train_relation", "")
        allowed = r.get("allowed_comparison_group", "")
        forbidden = r.get("forbidden_comparison_group", "")
        value = r.get("value", "")

        if not case_count:
            errors.append(f"{sid}: case_count missing")
        if not metric_impl:
            errors.append(f"{sid}: metric implementation missing")
        if not source:
            errors.append(f"{sid}: source_path missing")
        if not evidence:
            errors.append(f"{sid}: evidence_grade missing")
        if not value:
            errors.append(f"{sid}: value missing")
        if "checkpoint" in checkpoint.lower() and len(checkpoint) != 64:
            errors.append(f"{sid}: checkpoint name is not a SHA256")
        if checkpoint and checkpoint not in VALID_SHA_SENTINELS and len(checkpoint) not in {64, 71}:
            errors.append(f"{sid}: checkpoint_sha256 is neither SHA256 nor approved sentinel")
        if prediction and prediction not in VALID_SHA_SENTINELS and len(prediction) < 16:
            errors.append(f"{sid}: prediction_sha256 too weak")
        if "hd95" in metric_impl.lower() and "spacing=unknown" in metric_impl.lower():
            errors.append(f"{sid}: reports HD95 mm while physical spacing is unknown")
        if "edema-zone" in label.lower() and "official" in population.lower():
            errors.append(f"{sid}: edema-zone is reported as official edema")
        if "pure edema" in label.lower() and "T2-present" not in population:
            errors.append(f"{sid}: pure edema row is not restricted to T2-present denominator")
        if "clean OOF" in allowed and "train-on-case" in train_relation:
            errors.append(f"{sid}: train-on-case row is allowed in clean OOF comparison group")
        if "outer once" in allowed and "inner" in population.lower() and "inner-select" not in allowed:
            errors.append(f"{sid}: inner row placed in outer comparison group")
        if not forbidden:
            errors.append(f"{sid}: forbidden comparison group missing")

    occurrence_by_id = {r.get("score_id", ""): r for r in occurrences}
    for sid in CORE_IDS:
        if sid not in occurrence_by_id:
            errors.append(f"{sid}: missing occurrence inventory row")

    for o in occurrences:
        sid = o.get("score_id", "")
        if o.get("is_prediction_parity", "").lower() == "true" and o.get("claim_allowed", "").lower() == "true":
            errors.append(f"{sid}: prediction parity is claim-allowed as metric truth")
        if o.get("is_train_on_case", "").lower() == "true" and o.get("is_clean_oof", "").lower() == "true":
            errors.append(f"{sid}: train-on-case row is also marked clean OOF")
        if o.get("is_hosted", "").lower() == "true" and "hosted" not in o.get("population_role", "").lower():
            errors.append(f"{sid}: hosted row missing hosted population role")
        if not o.get("source_sha256", ""):
            errors.append(f"{sid}: source_sha256 missing")

    forbidden_pairs = set(receipt.get("forbidden_direct_comparisons", []))
    required_forbidden = {
        "D0 inner-select GT Dice vs clean OOF 220-case Dice",
        "MoSAIC M2-M10 full-data train-on-case probe vs hosted validation",
        "PRISM fold0 outer once vs future fold1 or validation selection",
        "internal edema-zone vs official pure edema leaderboard",
    }
    missing_forbidden = sorted(required_forbidden - forbidden_pairs)
    if missing_forbidden:
        errors.append("missing required forbidden comparisons: " + ", ".join(missing_forbidden))

    unresolved = receipt.get("remaining_blockers", [])
    status = receipt.get("metric_contract_status")
    if status == "PASS" and unresolved:
        errors.append("metric_contract_status PASS but remaining_blockers is non-empty")
    if status == "PASS":
        for r in rows:
            if r.get("evidence_grade") in {"UNRESOLVED", "PARTIAL_HOSTED_BIND"}:
                errors.append(f"{r.get('score_contract_id')}: PASS cannot include unresolved/partial hosted evidence")
    if status not in {"PASS", "FAIL"}:
        errors.append("metric_contract_status must be PASS or FAIL")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()

    errors = truth_errors(args.result_dir)
    report = {"status": "PASS" if not errors else "FAIL", "errors": errors, "result_dir": str(args.result_dir)}
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print("metric truth validator PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
