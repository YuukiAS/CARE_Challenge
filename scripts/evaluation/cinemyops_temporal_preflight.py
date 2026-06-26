#!/usr/bin/env python3
"""CineMyoPS safe-subset temporal/anatomy retrieval preflight."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy import ndimage


DEFAULT_SAFE_CASES = Path("results/20260625_cine_geometry/safe_cases.csv")
DEFAULT_MISMATCH_CASES = Path("results/20260625_cine_geometry/mismatch_cases.csv")
DEFAULT_ADAPTER_METRICS = Path("results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv")
DEFAULT_OUTPUT_DIR = Path("results/20260626_cine_temporal")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compact_gt(raw: np.ndarray) -> np.ndarray:
    out = np.zeros(raw.shape, dtype=np.uint8)
    out[raw == 200] = 1
    out[raw == 500] = 2
    out[raw == 2221] = 3
    return out


def compact_pred_from_cinema(raw: np.ndarray) -> np.ndarray:
    out = np.zeros(raw.shape, dtype=np.uint8)
    out[raw == 2] = 1
    out[raw == 3] = 2
    return out


def dice(pred: np.ndarray, gt: np.ndarray) -> float | None:
    pred_sum = int(pred.sum())
    gt_sum = int(gt.sum())
    if pred_sum == 0 and gt_sum == 0:
        return None
    denom = pred_sum + gt_sum
    if denom == 0:
        return 0.0
    return float(2.0 * np.logical_and(pred, gt).sum() / denom)


def hd95(pred: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, float, float]) -> float | None:
    if not np.any(pred) or not np.any(gt):
        return None
    pred_border = np.logical_xor(pred, ndimage.binary_erosion(pred))
    gt_border = np.logical_xor(gt, ndimage.binary_erosion(gt))
    dt_gt = ndimage.distance_transform_edt(~gt_border, sampling=spacing_zyx)
    dt_pred = ndimage.distance_transform_edt(~pred_border, sampling=spacing_zyx)
    distances = np.concatenate([dt_gt[pred_border], dt_pred[gt_border]])
    return float(np.percentile(distances, 95)) if distances.size else 0.0


def component_count(mask: np.ndarray) -> int:
    if not np.any(mask):
        return 0
    _, count = ndimage.label(mask)
    return int(count)


def finite_mean(values: list[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None and not math.isnan(float(v)) and not math.isinf(float(v))]
    return float(np.mean(vals)) if vals else None


def load_adapter_index(metrics_csv: Path) -> dict[tuple[str, str], list[dict[str, str]]]:
    by_case: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(metrics_csv):
        if row.get("split") != "train":
            continue
        by_case[(row["center"], row["case_id"])].append(row)
    for rows in by_case.values():
        rows.sort(key=lambda r: int(r["frame_index"]))
    return by_case


def agreement(a: np.ndarray, b: np.ndarray) -> float:
    scores = []
    for cls in (1, 2):
        val = dice(a == cls, b == cls)
        if val is not None:
            scores.append(val)
    return float(np.mean(scores)) if scores else 0.0


def softmax(values: list[float], temperature: float = 0.15) -> list[float]:
    arr = np.asarray(values, dtype=np.float64) / max(temperature, 1e-6)
    arr = arr - np.max(arr)
    exp = np.exp(arr)
    probs = exp / np.sum(exp)
    return [float(x) for x in probs]


def fuse_predictions(preds: list[np.ndarray], weights: list[float], threshold: float) -> np.ndarray:
    out = np.zeros_like(preds[0], dtype=np.uint8)
    for cls in (1, 2):
        score = np.zeros(preds[0].shape, dtype=np.float32)
        for pred, weight in zip(preds, weights):
            score += float(weight) * (pred == cls)
        out[score >= threshold] = cls
    return out


def case_metrics(variant: str, row: dict[str, str], pred: np.ndarray) -> list[dict[str, Any]]:
    label = sitk.ReadImage(row["label_path"])
    gt = compact_gt(sitk.GetArrayFromImage(label))
    spacing = label.GetSpacing()
    spacing_zyx = (float(spacing[2]), float(spacing[1]), float(spacing[0]))
    rows = []
    for cls, name in [(1, "class_1_myocardium"), (2, "class_2_lv"), (3, "class_3_scar_sanity")]:
        pred_mask = pred == cls
        gt_mask = gt == cls
        rows.append(
            {
                "variant": variant,
                "case_id": row["case_id"],
                "center": row["center"],
                "class_id": cls,
                "metric_name": name,
                "dice": dice(pred_mask, gt_mask),
                "hd95": hd95(pred_mask, gt_mask, spacing_zyx),
                "component_count": component_count(pred_mask),
                "pred_voxels": int(pred_mask.sum()),
                "gt_voxels": int(gt_mask.sum()),
                "empty_prediction": not bool(pred_mask.any()),
            }
        )
    return rows


def summarize_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    variants = sorted({str(r["variant"]) for r in rows})
    for variant in variants:
        for cls, name in [(1, "class_1_myocardium"), (2, "class_2_lv"), (3, "class_3_scar_sanity")]:
            subset = [r for r in rows if r["variant"] == variant and int(r["class_id"]) == cls]
            out.append(
                {
                    "variant": variant,
                    "class_id": cls,
                    "metric_name": name,
                    "n": len(subset),
                    "dice_mean": finite_mean([r["dice"] for r in subset]),
                    "hd95_mean": finite_mean([r["hd95"] for r in subset]),
                    "component_count_mean": finite_mean([float(r["component_count"]) for r in subset]),
                    "empty_prediction_rate": finite_mean([1.0 if r["empty_prediction"] else 0.0 for r in subset]),
                }
            )
    return out


def write_summary(summary_rows: list[dict[str, Any]], frame_rows: list[dict[str, Any]], mismatch_count: int, path: Path) -> None:
    lines = [
        "# CineMyoPS Temporal Preflight Metrics",
        "",
        "## Setup",
        "",
        "- safe subset: `results/20260625_cine_geometry/safe_cases.csv`",
        "- source predictions: existing CineMA frame0/mid/representative predictions from `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/`",
        "- C0 `reference_control_safe`: frame0 anatomy prediction only.",
        "- C1 `keyframe_context_retrieval`: frame agreement softmax over frame0/mid/representative predictions, fused at reference geometry.",
        "- C2 `anatomy_consistency_temporal`: majority-style temporal consistency fusion; no nonreference frame is directly scored against GT.",
        "",
        "## Metrics",
        "",
        "| variant | metric | n | Dice | HD95 | components | empty rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        dice_text = "NA" if row["dice_mean"] is None else f"{float(row['dice_mean']):.4f}"
        hd95_text = "NA" if row["hd95_mean"] is None else f"{float(row['hd95_mean']):.4f}"
        comp_text = "NA" if row["component_count_mean"] is None else f"{float(row['component_count_mean']):.4f}"
        empty_text = "NA" if row["empty_prediction_rate"] is None else f"{float(row['empty_prediction_rate']):.4f}"
        lines.append(f"| {row['variant']} | {row['metric_name']} | {row['n']} | {dice_text} | {hd95_text} | {comp_text} | {empty_text} |")
    ref_dom = finite_mean([float(r["reference_weight"]) for r in frame_rows])
    entropy = finite_mean([float(r["temporal_entropy"]) for r in frame_rows])
    lines.extend(
        [
            "",
            "## Temporal Diagnostics",
            "",
            f"- safe cases evaluated: `{len({r['case_id'] for r in frame_rows})}`",
            f"- mismatch cases kept out of evaluation: `{mismatch_count}`",
            f"- mean reference weight in C1: `{ref_dom:.4f}`" if ref_dom is not None else "- mean reference weight in C1: `NA`",
            f"- mean temporal entropy in C1: `{entropy:.4f}`" if entropy is not None else "- mean temporal entropy in C1: `NA`",
            "- class_3 remains a negative control because CineMA anatomy predictions have no scar head.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_decision(summary_rows: list[dict[str, Any]], path: Path) -> None:
    def get(variant: str, cls: int, key: str) -> float | None:
        for row in summary_rows:
            if row["variant"] == variant and int(row["class_id"]) == cls:
                val = row.get(key)
                return None if val is None else float(val)
        return None

    ref_myo = get("reference_control_safe", 1, "dice_mean")
    ref_lv = get("reference_control_safe", 2, "dice_mean")
    c1_myo = get("keyframe_context_retrieval", 1, "dice_mean")
    c1_lv = get("keyframe_context_retrieval", 2, "dice_mean")
    c2_myo = get("anatomy_consistency_temporal", 1, "dice_mean")
    c2_lv = get("anatomy_consistency_temporal", 2, "dice_mean")

    positive = False
    reasons = []
    for name, myo, lv in [("keyframe_context_retrieval", c1_myo, c1_lv), ("anatomy_consistency_temporal", c2_myo, c2_lv)]:
        if None in (ref_myo, ref_lv, myo, lv):
            continue
        myo_delta = float(myo) - float(ref_myo)
        lv_delta = float(lv) - float(ref_lv)
        reasons.append(f"{name}.myocardium_delta={myo_delta:.4f}")
        reasons.append(f"{name}.lv_delta={lv_delta:.4f}")
        if (myo_delta > 0.002 and lv_delta > -0.02) or (lv_delta > 0.002 and myo_delta > -0.02):
            positive = True
    status = "GO_CINE_TEMPORAL_NEXT" if positive else "KEEP_REFERENCE_CONTROL"
    lines = ["# Decision 20260626 Cine Temporal", "", f"status: `{status}`", "", "## Reasons", ""]
    lines.extend(f"- {reason}" for reason in reasons)
    if not positive:
        lines.append("- Temporal fusion did not beat the frame0 reference control on class_1/class_2 local proxies without tradeoff.")
    lines.append("- class_3 scar sanity is not used as the sole failure reason because the source model has no scar head.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safe-cases", type=Path, default=DEFAULT_SAFE_CASES)
    parser.add_argument("--mismatch-cases", type=Path, default=DEFAULT_MISMATCH_CASES)
    parser.add_argument("--adapter-metrics", type=Path, default=DEFAULT_ADAPTER_METRICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    safe_rows = read_rows(args.safe_cases)
    mismatch_rows = read_rows(args.mismatch_cases)
    adapter = load_adapter_index(args.adapter_metrics)
    case_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    for row in safe_rows:
        key = (row["center"], row["case_id"])
        pred_rows = adapter.get(key, [])
        if len(pred_rows) < 2:
            raise RuntimeError(f"expected >=2 adapter frames for {key}, found {len(pred_rows)}")
        selected_rows = pred_rows[:3]
        preds = [compact_pred_from_cinema(sitk.GetArrayFromImage(sitk.ReadImage(p["prediction_path"]))) for p in selected_rows]
        ref = preds[0]
        agreements = [1.0, *[agreement(ref, pred) for pred in preds[1:]]]
        weights = softmax(agreements)
        c1 = fuse_predictions(preds, weights, threshold=0.50)
        c2 = fuse_predictions(preds, [1.0 / len(preds)] * len(preds), threshold=0.50)
        for variant, pred in [
            ("reference_control_safe", ref),
            ("keyframe_context_retrieval", c1),
            ("anatomy_consistency_temporal", c2),
        ]:
            case_rows.extend(case_metrics(variant, row, pred))
        entropy = -sum(w * math.log(max(w, 1e-8)) for w in weights)
        frame_rows.append(
            {
                "case_id": row["case_id"],
                "center": row["center"],
                "n_frames": len(selected_rows),
                "frame_indices": ",".join(p["frame_index"] for p in selected_rows),
                "frame_agreements": ",".join(f"{x:.6f}" for x in agreements),
                "frame_weights": ",".join(f"{x:.6f}" for x in weights),
                "reference_weight": weights[0],
                "temporal_entropy": entropy,
                "reference_dominance": weights[0] >= 0.80,
                "source_prediction_paths": ";".join(p["prediction_path"] for p in selected_rows),
            }
        )
    summary_rows = summarize_metrics(case_rows)
    write_csv(case_rows, args.output_dir / "case_metrics.csv")
    write_csv(frame_rows, args.output_dir / "frame_retrieval.csv")
    write_csv(summary_rows, args.output_dir / "summary_metrics.csv")
    write_summary(summary_rows, frame_rows, len(mismatch_rows), args.output_dir / "metrics_summary.md")
    write_decision(summary_rows, args.output_dir / "decision.md")
    (args.output_dir / "safe_split.md").write_text(
        "\n".join(
            [
                "# Cine Temporal Safe Split",
                "",
                f"- safe cases: `{len(safe_rows)}` from `results/20260625_cine_geometry/safe_cases.csv`",
                f"- mismatch cases held out: `{len(mismatch_rows)}` from `results/20260625_cine_geometry/mismatch_cases.csv`",
                "- split policy: all strict safe cases are evaluated as a fixed preflight set; mismatch cases remain repair-only.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "failure_interpretation.md").write_text(
        "\n".join(
            [
                "# Cine Temporal Failure Interpretation",
                "",
                "This preflight uses existing frozen CineMA anatomy predictions. It can test whether keyframe anatomy context improves frame0 myocardium/LV proxies, but it cannot validate scar because the source anatomy prior has no scar head.",
                "",
                "If temporal variants underperform the reference control, the likely mechanisms are: nonreference features are not motion-registered into the ED/reference frame; frame agreement favors the reference frame too strongly; and the current keyframe selection was produced by the previous adapter rather than an optimized motion descriptor.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"safe_cases": len(safe_rows), "mismatch_held_out": len(mismatch_rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
