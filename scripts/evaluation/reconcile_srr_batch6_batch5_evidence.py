#!/usr/bin/env python3
"""Build Batch6 reconciliation tables from Batch5 and Batch4 selected-checkpoint evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
B5_TO_B6_MODE = {
    "anchor_identity_control": "anchor_identity_control",
    "anchor_bounded_full": "full_learned_gate",
    "production_gate_open_bounded_control": "full_gate_one",
    "production_gate_closed": "full_gate_zero",
    "anchor_bounded_proposal_only": "proposal_only_gate_one",
    "anchor_bounded_refiner_only": "refiner_only_gate_one",
}
B6_MODES = set(B5_TO_B6_MODE.values())


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def finite(value: str, default: float = 0.0) -> float:
    text = str(value).strip()
    if not text:
        return float(default)
    try:
        out = float(text)
    except ValueError:
        return float(default)
    return out if math.isfinite(out) else float(default)


def mean(values: list[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    return sum(vals) / len(vals) if vals else 0.0


def index_batch4_proposal(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if row.get("checkpoint_name") != "step_1800":
            continue
        if str(row.get("proposal_threshold")) != "0.2":
            continue
        pathology = "scar" if str(row.get("class_id")) == "5" else "edema"
        out[(row["case_id"], pathology)] = row
    return out


def index_batch4_roi(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if row.get("checkpoint_name") != "step_1800" or row.get("decode_mode") != "argmax":
            continue
        pathology = "scar" if str(row.get("class_id")) == "5" else "edema"
        out[(row["case_id"], pathology)] = row
    return out


def build_tables(result_root: Path, batch5_root: Path, batch4_root: Path) -> dict[str, Any]:
    casewise = [row for row in read_csv(batch5_root / "casewise_mechanism_attribution.csv") if row.get("mode") in B5_TO_B6_MODE]
    proposal = index_batch4_proposal(read_csv(batch4_root / "proposal_diagnostics.csv"))
    roi = index_batch4_roi(read_csv(batch4_root / "roi_diagnostics.csv"))
    pure_rows: list[dict[str, Any]] = []
    proposal_roi_rows: list[dict[str, Any]] = []

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in casewise:
        mode = B5_TO_B6_MODE[row["mode"]]
        grouped[(mode, row["pathology"])].append(row)
        prop = proposal.get((row["case_id"], row["pathology"]), {})
        roi_row = roi.get((row["case_id"], row["pathology"]), {})
        gt_positive = str(row.get("gt_positive", "")).lower() == "true"
        t2_present = str(row.get("t2_present", "")).lower() == "true"
        applicability = "applicable"
        if row["pathology"] == "edema" and not t2_present:
            applicability = "not_applicable_no_t2"
        elif not gt_positive:
            applicability = "not_applicable_no_positive_gt"
        proposal_roi_rows.append(
            {
                "case_id": row["case_id"],
                "mode": mode,
                "pathology": row["pathology"],
                "class_id": row["class_id"],
                "metric_applicability": applicability,
                "proposal_voxel_precision": finite(prop.get("proposal_precision", ""), 0.0),
                "proposal_voxel_recall": finite(prop.get("proposal_recall", ""), 0.0),
                "proposal_lesion_recall": finite(prop.get("lesion_wise_recall", ""), 0.0),
                "proposal_component_count": int(finite(prop.get("proposal_component_count", row.get("proposal_component_count", "")), 0.0)),
                "proposal_remote_fp_count": int(finite(prop.get("proposal_remote_fp_count", row.get("proposal_remote_fp_count", "")), 0.0)),
                "proposal_remote_fp_volume_mm3": finite(row.get("mode_remote_fp_volume_mm3", ""), 0.0),
                "roi_gt_coverage": finite(roi_row.get("gt_coverage", row.get("roi_gt_coverage", "")), 0.0),
                "roi_outside_ratio": finite(roi_row.get("outside_myocardium_roi_ratio", row.get("roi_outside_ratio", "")), 0.0),
                "refiner_residual_abs_mean": finite(row.get("refiner_residual_abs_mean", ""), 0.0),
                "changed_voxels_vs_anchor": int(finite(row.get("changed_voxels_vs_anchor", ""), 0.0)),
                "dice_delta_vs_anchor": finite(row.get("dice_delta_vs_anchor", ""), 0.0),
                "hd95_delta_vs_anchor": finite(row.get("hd95_delta_vs_anchor", ""), 0.0),
                "component_delta": int(finite(row.get("component_delta", ""), 0.0)),
                "remote_fp_delta_mm3": finite(row.get("remote_fp_delta_mm3", ""), 0.0),
                "source_casewise_evidence": str(batch5_root / "casewise_mechanism_attribution.csv"),
                "source_proposal_evidence": str(batch4_root / "proposal_diagnostics.csv"),
                "source_roi_evidence": str(batch4_root / "roi_diagnostics.csv"),
            }
        )

    for (mode, pathology), rows in sorted(grouped.items()):
        pure_rows.append(
            {
                "mode": mode,
                "pathology": pathology,
                "population": "all_case_empty_safe",
                "case_count": len(rows),
                "mean_dice_delta_vs_anchor": mean([finite(row.get("dice_delta_vs_anchor", ""), 0.0) for row in rows]),
                "mean_hd95_delta_vs_anchor": mean([finite(row.get("hd95_delta_vs_anchor", ""), 0.0) for row in rows]),
                "mean_remote_fp_delta_mm3": mean([finite(row.get("remote_fp_delta_mm3", ""), 0.0) for row in rows]),
                "mean_changed_voxels_vs_anchor": mean([finite(row.get("changed_voxels_vs_anchor", ""), 0.0) for row in rows]),
                "proposal_consumed": mode != "refiner_only_gate_one",
                "refiner_consumed": mode != "proposal_only_gate_one",
                "purity_status": "PURE" if mode in {"proposal_only_gate_one", "refiner_only_gate_one"} else "NOT_COMPONENT_ISOLATION_MODE",
            }
        )
        positive = [row for row in rows if str(row.get("gt_positive", "")).lower() == "true"]
        pure_rows.append(
            {
                "mode": mode,
                "pathology": pathology,
                "population": "positive_gt_cases",
                "case_count": len(positive),
                "mean_dice_delta_vs_anchor": mean([finite(row.get("dice_delta_vs_anchor", ""), 0.0) for row in positive]),
                "mean_hd95_delta_vs_anchor": mean([finite(row.get("hd95_delta_vs_anchor", ""), 0.0) for row in positive]),
                "mean_remote_fp_delta_mm3": mean([finite(row.get("remote_fp_delta_mm3", ""), 0.0) for row in positive]),
                "mean_changed_voxels_vs_anchor": mean([finite(row.get("changed_voxels_vs_anchor", ""), 0.0) for row in positive]),
                "proposal_consumed": mode != "refiner_only_gate_one",
                "refiner_consumed": mode != "proposal_only_gate_one",
                "purity_status": "PURE" if mode in {"proposal_only_gate_one", "refiner_only_gate_one"} else "NOT_COMPONENT_ISOLATION_MODE",
            }
        )

    missing_modes = B6_MODES - {row["mode"] for row in pure_rows}
    if missing_modes:
        raise RuntimeError(f"missing Batch6 modes after reconciliation: {sorted(missing_modes)}")
    required = (
        "proposal_voxel_precision",
        "proposal_voxel_recall",
        "proposal_lesion_recall",
        "proposal_component_count",
        "proposal_remote_fp_count",
        "proposal_remote_fp_volume_mm3",
        "roi_gt_coverage",
        "roi_outside_ratio",
        "refiner_residual_abs_mean",
        "changed_voxels_vs_anchor",
        "dice_delta_vs_anchor",
        "hd95_delta_vs_anchor",
        "component_delta",
        "remote_fp_delta_mm3",
    )
    for row in proposal_roi_rows:
        for key in required:
            if str(row.get(key, "")).strip() == "":
                raise RuntimeError(f"blank reconciled field {key} for {row['case_id']} {row['mode']} {row['pathology']}")
    write_csv(result_root / "pure_intervention_metrics.csv", pure_rows)
    write_csv(result_root / "proposal_roi_metrics.csv", proposal_roi_rows)
    return {
        "status": "BATCH6_BATCH5_RECONCILIATION_TABLES_COMPLETE",
        "pure_intervention_rows": len(pure_rows),
        "proposal_roi_rows": len(proposal_roi_rows),
        "modes": sorted(B6_MODES),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", default="results/20260721_srr_batch6_final_objective_alignment")
    parser.add_argument("--batch5-root", default="results/20260721_srr_batch5_post_batch4_diagnostic_repair")
    parser.add_argument("--batch4-root", default="results/20260721_srr_batch4_forced_fold0_training")
    args = parser.parse_args()
    payload = build_tables(REPO_ROOT / args.result_root, REPO_ROOT / args.batch5_root, REPO_ROOT / args.batch4_root)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
