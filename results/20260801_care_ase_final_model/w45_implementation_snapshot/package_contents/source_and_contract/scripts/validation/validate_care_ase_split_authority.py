#!/usr/bin/env python
"""Validate and freeze CARE-ASE fold2/fold3 actual-train/inner/outer roles."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_ase_splits import (
    SENTINEL_CASES,
    SPLITS_REL,
    actual_train_cases,
    build_care_ase_case_roles,
    sha256_file,
    write_case_roles_csv,
)
from src.care_myocardium.training.care_ase_trainer import write_json


RESULT_DIR = REPO_ROOT / "results/20260801_care_ase_final_model"


def summarize(rows: list[Any], fold: int) -> dict[str, Any]:
    role_sets = {
        role: {row.case_id for row in rows if row.role == role}
        for role in ("actual-train", "inner", "outer")
    }
    actual_complete = actual_train_cases(REPO_ROOT, fold, complete_only=True)
    intersections = {
        "actual_train_inner": sorted(role_sets["actual-train"] & role_sets["inner"]),
        "actual_train_outer": sorted(role_sets["actual-train"] & role_sets["outer"]),
        "inner_outer": sorted(role_sets["inner"] & role_sets["outer"]),
    }
    sentinel_rows = [asdict(row) for row in rows if row.case_id in SENTINEL_CASES]
    return {
        "fold": int(fold),
        "status": "PASS" if not any(intersections.values()) and len(role_sets["inner"]) == round(0.20 * (len(role_sets["actual-train"]) + len(role_sets["inner"]))) else "FAIL",
        "seed": 20260801 + int(fold),
        "role_counts": {role: len(values) for role, values in role_sets.items()},
        "actual_train_complete_case_count": len(actual_complete),
        "actual_train_complete_case_ids": [case_id for case_id, _availability in actual_complete],
        "intersections": intersections,
        "sentinel_rows": sentinel_rows,
    }


def main() -> int:
    out_dir = RESULT_DIR
    all_rows = []
    fold_summaries = []
    for fold in (2, 3):
        rows = build_care_ase_case_roles(REPO_ROOT, fold)
        all_rows.extend(rows)
        write_case_roles_csv(out_dir / f"split_authority_fold{fold}.csv", rows)
        fold_summaries.append(summarize(rows, fold))
    receipt = {
        "status": "PASS" if all(row["status"] == "PASS" for row in fold_summaries) else "FAIL",
        "split_source": str(SPLITS_REL),
        "split_source_sha256": sha256_file(REPO_ROOT / SPLITS_REL),
        "inner_fraction": 0.20,
        "inner_seed_formula": "20260801 + fold",
        "strata": "center|availability|t2_present|scar_volume_bin",
        "scar_volume_bins": ["scar_zero", "scar_small_lt1000mm3", "scar_medium_1000_5000mm3", "scar_large_ge5000mm3"],
        "folds": fold_summaries,
        "forbidden_training_roles": ["inner", "outer"],
        "stage_c_training_role": "actual-train complete tri-modal only",
    }
    write_json(out_dir / "split_authority_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True, default=str))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
