#!/usr/bin/env python3
"""Freeze global scar/edema sources from completed inner lane evaluations."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.target_domain_gap_closure.evaluate_inner_lanes import is_better_global_selection  # noqa: E402

TASK_KEY = "20260801_care_target_domain_race_gap_closure"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
INNER_ROOT = RESULT_ROOT / "inner_evaluation"
LANE_SUMMARY_PATHS = {
    "m0r_faithful_control": INNER_ROOT / "m0r_faithful_control" / "global_summary_metrics.csv",
    "m1_myopsnet_l_care": INNER_ROOT / "m1_myopsnet_l_care" / "global_summary_metrics.csv",
    "m2_i_mmseg_care": INNER_ROOT / "global_summary_metrics.csv",
    "m3_care_tds": INNER_ROOT / "m3_care_tds" / "global_summary_metrics.csv",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return [dict(row) for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def coerce(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if value == "":
            out[key] = None
        elif key in {
            "checkpoint_step",
            "case_count",
            "remote_fp_count_sum",
            "remote_fp_voxels_sum",
            "blood_pool_adjacent_fp_count_sum",
            "blood_pool_adjacent_fp_voxels_sum",
            "pred_component_count_sum",
            "gt_component_count_sum",
        }:
            out[key] = int(value)
        elif key.endswith("_mean") or key in {"hd95_vox_mean", "exact_hd_vox_mean"}:
            out[key] = float(value)
        else:
            out[key] = value
    return out


def main() -> int:
    all_rows: list[dict[str, Any]] = []
    missing = [str(path) for path in LANE_SUMMARY_PATHS.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing lane global summaries: {missing}")
    for lane, path in LANE_SUMMARY_PATHS.items():
        for row in read_rows(path):
            parsed = coerce(row)
            parsed["lane"] = lane
            all_rows.append(parsed)

    selected_rows: list[dict[str, Any]] = []
    for pathology in ("scar", "pure_edema"):
        selected: dict[str, Any] | None = None
        for row in [r for r in all_rows if r["pathology"] == pathology]:
            if is_better_global_selection(row, selected, pathology):
                selected = row
        if selected is None:
            raise RuntimeError(f"no inner candidates for {pathology}")
        selected_rows.append(
            {
                **selected,
                "source_freeze_scope": "all_lanes_fold2_fold3_inner_only",
                "source_freeze_rule": "blueprint_global_source_selection",
                "outer_cases_accessed": False,
            }
        )

    write_csv(INNER_ROOT / "all_lane_global_summary_metrics.csv", all_rows)
    write_csv(INNER_ROOT / "global_source_selection.csv", selected_rows)
    receipt = {
        "created_at": now_utc(),
        "status": "PASS",
        "population": "fold2_fold3_inner_only",
        "outer_cases_accessed": False,
        "lanes": sorted(LANE_SUMMARY_PATHS),
        "candidate_rows": len(all_rows),
        "selection_rows": len(selected_rows),
        "global_scar_source": selected_rows[0],
        "global_edema_source": selected_rows[1],
    }
    (INNER_ROOT / "global_source_selection.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
