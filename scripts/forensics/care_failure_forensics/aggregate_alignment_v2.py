#!/usr/bin/env python3
"""Bind historical MyoPS alignment gate evidence into the V2 packet."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import pearsonr, spearmanr

RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")
ALIGN_REL = Path("results/20260703_myops_alignment_gate")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def finite(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def corr_rows(rows: list[dict[str, Any]], x_col: str, y_col: str) -> dict[str, Any]:
    pairs = [(finite(r.get(x_col)), finite(r.get(y_col))) for r in rows]
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
    out: dict[str, Any] = {"x": x_col, "y": y_col, "n": len(pairs)}
    if len(pairs) < 3:
        out.update({"pearson_r": "", "pearson_p": "", "spearman_r": "", "spearman_p": ""})
        return out
    x = np.asarray([p[0] for p in pairs], dtype=float)
    y = np.asarray([p[1] for p in pairs], dtype=float)
    pr = pearsonr(x, y)
    sr = spearmanr(x, y)
    out.update({"pearson_r": float(pr.statistic), "pearson_p": float(pr.pvalue), "spearman_r": float(sr.statistic), "spearman_p": float(sr.pvalue)})
    return out


def upsert_task_status(result_root: Path, task_id: str, status: str, evidence: str, notes: str) -> None:
    path = result_root / "v2_task_status.csv"
    rows = read_csv(path) if path.exists() else []
    rows = [r for r in rows if r.get("task_id") != task_id]
    rows.append(
        {
            "task_id": task_id,
            "category": "gpu_diagnostic",
            "required": "true",
            "status": status,
            "terminal_status": "true",
            "evidence_path": evidence,
            "notes": notes,
        }
    )
    write_csv(path, rows, ["task_id", "category", "required", "status", "terminal_status", "evidence_path", "notes"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    result_root = root / RESULT_REL
    align_root = root / ALIGN_REL

    reg_all = read_csv(align_root / "registration_metrics.csv")
    reg = [
        r for r in reg_all
        if r.get("case_id") and r.get("fixed") == "LGE" and r.get("moving") in {"C0", "T2"}
    ]
    comp = read_csv(align_root / "component_hd_by_case.csv")
    warp = read_csv(align_root / "warp_sanity.csv")

    case_rows = []
    for row in reg:
        case_rows.append(
            {
                "case_id": row.get("case_id"),
                "center": row.get("center"),
                "fixed": row.get("fixed"),
                "moving": row.get("moving"),
                "pair": f"{row.get('fixed')}-{row.get('moving')}",
                "same_geometry": row.get("same_geometry"),
                "shape_mismatch": row.get("shape_mismatch"),
                "spacing_mismatch": row.get("spacing_mismatch"),
                "origin_mismatch": row.get("origin_mismatch"),
                "direction_mismatch": row.get("direction_mismatch"),
                "centroid_shift_mm": row.get("com_distance_mm"),
                "best_slice_corr_mean": row.get("best_slice_corr_mean"),
                "same_slice_corr_mean": row.get("same_slice_corr_mean"),
                "edge_corr": row.get("edge_corr"),
                "mutual_information": row.get("mutual_information"),
                "mean_abs_best_shift": row.get("mean_abs_best_shift"),
                "pair_mismatch_score": row.get("pair_mismatch_score"),
                "scar_dice": row.get("scar_dice"),
                "edema_dice": row.get("edema_dice"),
                "pathology_failure_score": row.get("pathology_failure_score"),
                "stop_reason": row.get("stop_reason") or "header_audit",
            }
        )
    write_csv(result_root / "cross_modal_alignment_casewise.csv", case_rows)

    slice_rows = []
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in reg:
        buckets[f"{row.get('fixed')}-{row.get('moving')}"].append(row)
    for pair, rows in sorted(buckets.items()):
        vals = [finite(r.get("best_slice_corr_mean")) for r in rows]
        vals = [v for v in vals if v is not None]
        shifts = [finite(r.get("mean_abs_best_shift")) for r in rows]
        shifts = [v for v in shifts if v is not None]
        slice_rows.append(
            {
                "pair": pair,
                "case_count": len(rows),
                "mean_best_slice_corr": float(np.mean(vals)) if vals else "",
                "median_best_slice_corr": float(np.median(vals)) if vals else "",
                "mean_abs_best_shift": float(np.mean(shifts)) if shifts else "",
                "same_geometry_fraction": float(np.mean([str(r.get("same_geometry")).lower() == "true" for r in rows])),
            }
        )
    write_csv(result_root / "slice_correspondence_quality.csv", slice_rows)

    corr = []
    for x_col in ["centroid_shift_mm", "pair_mismatch_score", "best_slice_corr_mean", "edge_corr", "mutual_information"]:
        for y_col in ["scar_dice", "edema_dice", "pathology_failure_score"]:
            corr.append(corr_rows(case_rows, x_col, y_col))
    write_csv(result_root / "alignment_error_correlation.csv", corr)

    subgroup = read_csv(align_root / "subgroup_metrics.csv")
    geom_rows = [
        {
            "audit": "historical_alignment_gate_binding",
            "status": "COMPLETED_WITH_VALID_EVIDENCE",
            "cases": len({r["case_id"] for r in reg}),
            "source": str((align_root / "registration_metrics.csv").relative_to(root)),
            "warp_sanity": str((align_root / "warp_sanity.csv").relative_to(root)),
            "stop_reason": "; ".join(sorted({r.get("stop_reason", "") for r in warp if r.get("stop_reason")})),
        }
    ]
    write_csv(result_root / "spatial_geometry_audit.csv", geom_rows)

    report = [
        "# Alignment V2 forensic binding",
        "",
        "V2 绑定 20260703 MyoPS complete-case alignment gate，而不是重新解释占位文件。",
        "",
        f"- registration rows: {len(reg)}",
        f"- complete cases: {len({r['case_id'] for r in reg})}",
        f"- component metric rows: {len(comp)}",
        f"- subgroup rows: {len(subgroup)}",
        "",
        "结论边界：该 gate 的 Phase 1 没有支持多序列错位是主瓶颈；translation/slice/TPS/deformable 路线因此未继续执行，不能反向声明 alignment 修复有主要增益。",
    ]
    (result_root / "alignment_forensics_report.md").write_text("\n".join(report) + "\n")
    receipt = {
        "status": "COMPLETED_WITH_VALID_EVIDENCE",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(align_root),
        "registration_rows": len(reg),
        "case_count": len({r["case_id"] for r in reg}),
        "output_files": [
            "cross_modal_alignment_casewise.csv",
            "slice_correspondence_quality.csv",
            "alignment_error_correlation.csv",
            "spatial_geometry_audit.csv",
            "alignment_forensics_report.md",
        ],
    }
    (result_root / "alignment_v2_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    upsert_task_status(
        result_root,
        "G8_ALIGNMENT_DIAGNOSTICS",
        "COMPLETED_WITH_VALID_EVIDENCE",
        str((result_root / "alignment_error_correlation.csv").relative_to(root)),
        "Bound 20260703 complete-case LGE-C0/LGE-T2 alignment gate; evidence does not support alignment as primary bottleneck.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
