#!/usr/bin/env python3
"""Compare SRR same-split case metrics against nnU-Net anchors."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import collect_case_metrics, load_split, read_case, write_csv  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402


DEFAULT_NNUNET_ANCHOR_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def safe_float(value: object) -> float | None:
    if value in (None, "", "NA", "nan"):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def load_nnunet_metrics(case_id: str, fold: int, anchor_root: Path, metadata: dict[str, Any]) -> dict[int, dict[str, object]]:
    pred_path = anchor_root / f"fold_{fold}" / "validation" / f"{case_id}.nii.gz"
    if not pred_path.is_file():
        raise FileNotFoundError(f"nnU-Net prediction not found: {pred_path}")
    case = read_case(case_id, metadata)  # type: ignore[arg-type]
    pred = sitk.GetArrayFromImage(sitk.ReadImage(str(pred_path))).astype(np.uint8, copy=False)
    rows = collect_case_metrics("nnUNet_same_split_anchor", case, pred)
    return {int(row["class_id"]): row for row in rows}


def decision_from_delta(metric: str, delta: float | None, eps: float) -> str:
    if delta is None:
        return "not_evaluable"
    if metric in {"dice"}:
        if delta > eps:
            return "help"
        if delta < -eps:
            return "harm"
        return "neutral"
    if metric in {"hd95", "remote_fp_count", "component_count"}:
        if delta < -eps:
            return "help"
        if delta > eps:
            return "harm"
        return "neutral"
    return "not_evaluable"


def compare_rows(
    srr_rows: list[dict[str, str]],
    *,
    fold: int,
    anchor_root: Path,
    metadata: dict[str, Any],
    eps: float,
) -> list[dict[str, object]]:
    baseline_cache: dict[str, dict[int, dict[str, object]]] = {}
    out: list[dict[str, object]] = []
    for row in srr_rows:
        case_id = row["case_id"]
        class_id = int(row["class_id"])
        if case_id not in baseline_cache:
            baseline_cache[case_id] = load_nnunet_metrics(case_id, fold, anchor_root, metadata)
        base = baseline_cache[case_id][class_id]
        for metric in ("dice", "hd95", "component_count", "remote_fp_count"):
            srr_value = safe_float(row.get(metric))
            base_value = safe_float(base.get(metric))
            delta = None if srr_value is None or base_value is None else srr_value - base_value
            out.append(
                {
                    "case_id": case_id,
                    "center": row.get("center", ""),
                    "modality_group": row.get("modality_group", ""),
                    "t2_present": row.get("t2_present", ""),
                    "class_id": class_id,
                    "metric_name": row.get("metric_name", ""),
                    "srr_variant": row.get("variant", ""),
                    "baseline_variant": "nnUNet_same_split_anchor",
                    "metric": metric,
                    "srr_value": srr_value,
                    "nnunet_value": base_value,
                    "delta_srr_minus_nnunet": delta,
                    "decision": decision_from_delta(metric, delta, eps),
                    "fold": fold,
                }
            )
    return out


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for row in rows:
        key = (str(row["srr_variant"]), str(row["metric_name"]), str(row["metric"]))
        groups.setdefault(key, []).append(row)
    out = []
    for (variant, metric_name, metric), subset in sorted(groups.items()):
        deltas = [safe_float(row["delta_srr_minus_nnunet"]) for row in subset]
        values = [d for d in deltas if d is not None]
        out.append(
            {
                "srr_variant": variant,
                "metric_name": metric_name,
                "metric": metric,
                "n": len(subset),
                "delta_mean": mean(values) if values else None,
                "help_count": sum(1 for row in subset if row["decision"] == "help"),
                "harm_count": sum(1 for row in subset if row["decision"] == "harm"),
                "neutral_count": sum(1 for row in subset if row["decision"] == "neutral"),
                "not_evaluable_count": sum(1 for row in subset if row["decision"] == "not_evaluable"),
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--srr-metrics", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--nnunet-anchor-root", type=Path, default=DEFAULT_NNUNET_ANCHOR_ROOT)
    ap.add_argument("--eps", type=float, default=1e-6)
    args = ap.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = load_myops_case_metadata()
    _, val_ids = load_split(args.fold)
    srr_rows = read_rows(args.srr_metrics)
    bad_cases = sorted({row["case_id"] for row in srr_rows} - set(val_ids))
    if bad_cases:
        raise ValueError(f"SRR metrics contain cases outside fold{args.fold} validation split: {bad_cases}")
    help_harm = compare_rows(
        srr_rows,
        fold=args.fold,
        anchor_root=args.nnunet_anchor_root,
        metadata=metadata,
        eps=args.eps,
    )
    summary = summarize(help_harm)
    write_csv(output_dir / "help_harm_vs_nnunet.csv", help_harm)
    write_csv(output_dir / "ablation_summary.csv", summary)
    (output_dir / "help_harm_manifest.json").write_text(
        json.dumps(
            {
                "srr_metrics": str(args.srr_metrics),
                "fold": args.fold,
                "nnunet_anchor_root": str(args.nnunet_anchor_root),
                "case_count": len({row["case_id"] for row in srr_rows}),
                "row_count": len(help_harm),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
