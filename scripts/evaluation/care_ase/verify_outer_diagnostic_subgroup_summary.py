#!/usr/bin/env python
"""Verify CARE-ASE user-authorized outer subgroup summaries.

This is a read-only reporting verifier. It recomputes subgroup means directly
from the existing outer casewise CSVs plus immutable MyoPS case metadata, then
checks the generated subgroup summary/reporting numbers. It does not run
inference, select checkpoints, tune thresholds, or modify training state.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.care_ase.summarize_outer_diagnostic_subgroups import (
    DEFAULT_OUTER_ROOT,
    load_rows,
    metadata_root,
)


DEFAULT_EXPECTED = {
    ("all_outer_scar", "combined"): (88, 0.45087787184295247, 0.5562721219785355),
    ("complete_tri_modal_scar", "fold2"): (16, 0.7041290341166848, 0.6979693557646723),
    ("complete_tri_modal_scar", "fold3"): (16, 0.6544408813826648, 0.6470501054260303),
    ("complete_tri_modal_scar", "combined"): (32, 0.6792849577496748, 0.6725097305953512),
    ("partial_modality_scar", "combined"): (56, 0.3203595370391111, 0.48985063134035506),
    ("pure_edema_t2_present", "combined"): (32, 0.4503308235062316, 0.4751955805756),
}


def parse_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    out = float(value)
    if math.isnan(out):
        return None
    return out


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average an empty value list")
    return sum(values) / len(values)


def close(a: float, b: float, tol: float) -> bool:
    return abs(float(a) - float(b)) <= tol


def load_table(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {(row["group"], row["split"]): row for row in rows}


def recompute(rows: list[dict[str, Any]], group: str, split: str) -> tuple[int, float, float]:
    fold = {"fold2": 2, "fold3": 3, "combined": None}[split]
    metric = "pure_edema" if "edema" in group else "scar"
    selected: list[dict[str, Any]] = []
    for row in rows:
        if fold is not None and int(row["fold"]) != fold:
            continue
        complete = bool(row["complete_tri_modal"])
        t2_present = bool(row["t2_present_metadata"])
        if group == "complete_tri_modal_scar" and not (complete and t2_present):
            continue
        if group == "partial_modality_scar" and complete:
            continue
        if group == "pure_edema_t2_present" and not t2_present:
            continue
        if group == "centerB_complete_scar" and not (complete and t2_present and row["center"] == "CenterB"):
            continue
        if group == "centerB_complete_edema" and not (complete and t2_present and row["center"] == "CenterB"):
            continue
        if group == "centerC_complete_scar" and not (complete and t2_present and row["center"] == "CenterC"):
            continue
        if group == "centerC_complete_edema" and not (complete and t2_present and row["center"] == "CenterC"):
            continue
        selected.append(row)
    care = [parse_float(row.get(f"care_{metric}_dice")) for row in selected]
    nnunet = [parse_float(row.get(f"nnunet_{metric}_dice")) for row in selected]
    pairs = [(c, n) for c, n in zip(care, nnunet) if c is not None and n is not None]
    return len(pairs), mean([c for c, _ in pairs]), mean([n for _, n in pairs])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, default=DEFAULT_OUTER_ROOT / "outer_diagnostic_subgroup_summary.json")
    parser.add_argument("--table", type=Path, default=DEFAULT_OUTER_ROOT / "outer_diagnostic_subgroup_table.csv")
    parser.add_argument("--fold2-csv", type=Path, default=DEFAULT_OUTER_ROOT / "fold_2/step05000/outer_casewise_metrics.csv")
    parser.add_argument("--fold3-csv", type=Path, default=DEFAULT_OUTER_ROOT / "fold_3/step04000/outer_casewise_metrics.csv")
    parser.add_argument("--metadata-repo-root", type=Path, default=None)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_OUTER_ROOT / "outer_diagnostic_subgroup_verification_receipt.json")
    parser.add_argument("--tolerance", type=float, default=1e-12)
    args = parser.parse_args()

    rows = load_rows({2: args.fold2_csv, 3: args.fold3_csv}, metadata_root(REPO_ROOT, args.metadata_repo_root))
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    table = load_table(args.table)

    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    for key, expected in DEFAULT_EXPECTED.items():
        group, split = key
        case_count, care, nnunet = recompute(rows, group, split)
        expected_cases, expected_care, expected_nnunet = expected
        summary_item = summary["subgroups"][group][split]
        table_item = table[key]
        ok = (
            case_count == expected_cases
            and close(care, expected_care, args.tolerance)
            and close(nnunet, expected_nnunet, args.tolerance)
            and int(summary_item["case_count"]) == case_count
            and close(summary_item["care_dice"], care, args.tolerance)
            and close(summary_item["nnunet_dice"], nnunet, args.tolerance)
            and int(table_item["case_count"]) == case_count
            and close(float(table_item["care_dice"]), care, args.tolerance)
            and close(float(table_item["nnunet_dice"]), nnunet, args.tolerance)
        )
        check = {
            "group": group,
            "split": split,
            "case_count": case_count,
            "care_dice": care,
            "nnunet_dice": nnunet,
            "delta_care_minus_nnunet": care - nnunet,
            "matches_expected_and_artifacts": ok,
        }
        checks.append(check)
        if not ok:
            failures.append(f"{group}/{split}")

    receipt = {
        "schema": "CARE_ASE_OUTER_DIAGNOSTIC_SUBGROUP_VERIFICATION_V1",
        "status": "PASS" if not failures else "FAIL",
        "source": "raw_outer_casewise_csv_plus_myops_metadata_join",
        "summary": str(args.summary.relative_to(REPO_ROOT)),
        "table": str(args.table.relative_to(REPO_ROOT)),
        "casewise_csvs": {
            "fold2": str(args.fold2_csv.relative_to(REPO_ROOT)),
            "fold3": str(args.fold3_csv.relative_to(REPO_ROOT)),
        },
        "checks": checks,
        "failures": failures,
        "interpretation_guard": {
            "scar": "mixed all-scar headline must be interpreted with complete tri-modal and partial-modality subgroup rows",
            "edema": "pure edema is already T2-present-only and remains a real fold-specific deficit when negative",
            "training": "diagnostic outer subgroup results must not alter frozen schedule or checkpoint selection",
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
