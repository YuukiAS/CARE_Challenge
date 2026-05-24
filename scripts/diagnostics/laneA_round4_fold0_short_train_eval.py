#!/usr/bin/env python3
"""Evaluate Lane A Round4 fold0 short-train candidate against nnU-Net501 baseline."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class, hd_class


EDEMA = 4
SCAR = 5
OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round4_fold0_short_train"
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
BASELINE_PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)
CANDIDATE_PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "laneA_edema_focal_tversky_t2down_fold0_short__nnUNetPlans__3d_fullres/fold_0/validation"
)
CASE_METRICS = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/myops_modality_center_case_metrics.csv"
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: object) -> str:
    if value is None or value == "":
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        if math.isinf(value):
            return "inf"
        return f"{value:.4f}"
    return str(value)


def finite(values: list[object]) -> list[float]:
    out = []
    for value in values:
        if value in ("", None):
            continue
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isnan(v) and not math.isinf(v):
            out.append(v)
    return out


def avg(values: list[object]) -> float | None:
    vals = finite(values)
    return float(mean(vals)) if vals else None


def bool_csv(value: str) -> bool:
    return value.strip().lower() == "true"


def load_meta() -> dict[str, dict[str, object]]:
    rows = read_csv(CASE_METRICS)
    out = {}
    for row in rows:
        group = row["modality_group"]
        out[row["case_id"]] = {
            "center": row["center"],
            "modality_group": group,
            "t2_present": group == "C0+LGE+T2",
            "edema_gt_positive": bool_csv(row["edema_gt_positive"]),
            "scar_gt_positive": bool_csv(row["scar_gt_positive"]),
        }
    return out


def fold0_cases() -> list[str]:
    return list(read_json(SPLITS_JSON)["folds"][0]["val"])


def read_label(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    arr = sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)
    return img, arr


def read_pred(path: Path, gt_img: sitk.Image) -> np.ndarray:
    img = sitk.ReadImage(str(path))
    if (
        img.GetSize() != gt_img.GetSize()
        or img.GetSpacing() != gt_img.GetSpacing()
        or img.GetOrigin() != gt_img.GetOrigin()
        or img.GetDirection() != gt_img.GetDirection()
    ):
        img = sitk.Resample(img, gt_img, sitk.Transform(), sitk.sitkNearestNeighbor, 0, img.GetPixelID())
    return sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def bbox(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    return coords.min(axis=0), coords.max(axis=0)


def bbox_gap_mm(a: tuple[np.ndarray, np.ndarray] | None, b: tuple[np.ndarray, np.ndarray] | None, spacing: tuple[float, ...]) -> float | None:
    if a is None or b is None:
        return None
    gap = np.zeros(len(spacing), dtype=np.float64)
    for axis in range(len(spacing)):
        if a[1][axis] < b[0][axis]:
            gap[axis] = b[0][axis] - a[1][axis]
        elif b[1][axis] < a[0][axis]:
            gap[axis] = a[0][axis] - b[1][axis]
    return float(np.linalg.norm(gap * np.asarray(spacing, dtype=np.float64)))


def fp_counts(pred_mask: np.ndarray, gt_mask: np.ndarray, spacing: tuple[float, ...], small_threshold: int = 20, remote_mm: float = 20.0) -> tuple[int, int]:
    cc, n_cc = label(pred_mask.astype(bool), structure=generate_binary_structure(pred_mask.ndim, 1))
    small_fp = 0
    remote_fp = 0
    gt_bbox = bbox(gt_mask)
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if np.logical_and(comp, gt_mask).any():
            continue
        if int(comp.sum()) < small_threshold:
            small_fp += 1
        gap = bbox_gap_mm(bbox(comp), gt_bbox, spacing)
        if gap is None or gap > remote_mm:
            remote_fp += 1
    return int(small_fp), int(remote_fp)


def volume_ratio(pred_mask: np.ndarray, gt_mask: np.ndarray) -> float | None:
    pred_voxels = int(pred_mask.sum())
    gt_voxels = int(gt_mask.sum())
    if gt_voxels == 0:
        return None if pred_voxels == 0 else float("inf")
    return float(pred_voxels / gt_voxels)


def class_metrics(pred: np.ndarray, gt: np.ndarray, spacing: tuple[float, ...], cls: int, prefix: str) -> dict[str, object]:
    pred_mask = pred == cls
    gt_mask = gt == cls
    small_fp, remote_fp = fp_counts(pred_mask, gt_mask, spacing)
    return {
        f"{prefix}_dice": dice_per_class(pred, gt, cls, skip_if_gt_empty=True),
        f"{prefix}_hd": hd_class(pred, gt, cls, spacing),
        f"{prefix}_hd95": hd95_class(pred, gt, cls, spacing),
        f"{prefix}_component_count": component_count(pred_mask),
        f"{prefix}_small_fp": small_fp,
        f"{prefix}_remote_fp": remote_fp,
        f"{prefix}_pred_gt_volume_ratio": volume_ratio(pred_mask, gt_mask),
    }


def build_case_rows(pred_dir: Path, model: str) -> list[dict[str, object]]:
    meta = load_meta()
    rows = []
    for cid in fold0_cases():
        gt_img, gt = read_label(GT_DIR / f"{cid}.nii.gz")
        pred_path = pred_dir / f"{cid}.nii.gz"
        if not pred_path.is_file():
            rows.append({"model": model, "case_id": cid, "missing_prediction": True})
            continue
        pred = read_pred(pred_path, gt_img)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        row: dict[str, object] = {
            "model": model,
            "case_id": cid,
            "missing_prediction": False,
            **meta.get(cid, {}),
        }
        row.update(class_metrics(pred, gt, spacing, EDEMA, "myops_edema"))
        row.update(class_metrics(pred, gt, spacing, SCAR, "myops_scar"))
        rows.append(row)
    return rows


def subset_filter(name: str):
    if name == "all_case":
        return lambda r: True
    if name == "t2_present":
        return lambda r: r.get("t2_present") is True
    if name == "t2_present_gt_positive":
        return lambda r: r.get("t2_present") is True and r.get("edema_gt_positive") is True
    if name == "complete_modality":
        return lambda r: r.get("modality_group") == "C0+LGE+T2"
    if name == "CenterC":
        return lambda r: r.get("center") == "CenterC"
    if name == "no_t2_empty_gt":
        return lambda r: r.get("t2_present") is False and r.get("edema_gt_positive") is False
    raise ValueError(name)


def aggregate_subset(rows: list[dict[str, object]], subset: str, model: str) -> dict[str, object]:
    filt = subset_filter(subset)
    items = [r for r in rows if r["model"] == model and not r.get("missing_prediction") and filt(r)]
    return {
        "model": model,
        "subset": subset,
        "n": len(items),
        "myops_edema_dice": avg([r.get("myops_edema_dice") for r in items]),
        "myops_edema_hd": avg([r.get("myops_edema_hd") for r in items]),
        "myops_edema_hd95": avg([r.get("myops_edema_hd95") for r in items]),
        "myops_edema_component_count": avg([r.get("myops_edema_component_count") for r in items]),
        "myops_edema_small_fp": avg([r.get("myops_edema_small_fp") for r in items]),
        "myops_edema_remote_fp": avg([r.get("myops_edema_remote_fp") for r in items]),
        "myops_edema_pred_gt_volume_ratio": avg([r.get("myops_edema_pred_gt_volume_ratio") for r in items]),
        "myops_scar_dice": avg([r.get("myops_scar_dice") for r in items]),
        "myops_scar_hd": avg([r.get("myops_scar_hd") for r in items]),
        "myops_scar_hd95": avg([r.get("myops_scar_hd95") for r in items]),
    }


def delta(candidate: object, baseline: object, *, lower_is_better: bool = False) -> float | None:
    if candidate is None or baseline is None:
        return None
    try:
        c = float(candidate)
        b = float(baseline)
    except (TypeError, ValueError):
        return None
    if math.isnan(c) or math.isnan(b) or math.isinf(c) or math.isinf(b):
        return None
    return b - c if lower_is_better else c - b


def build_subset_comparison(metrics_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_key = {(r["model"], r["subset"]): r for r in metrics_rows}
    out = []
    for subset in ["all_case", "t2_present", "t2_present_gt_positive", "complete_modality", "CenterC", "no_t2_empty_gt"]:
        b = by_key[("baseline_nnunet501_fold0", subset)]
        c = by_key[("candidate_laneA_round4", subset)]
        row = {
            "subset": subset,
            "n": c["n"],
            "baseline_edema_dice": b["myops_edema_dice"],
            "candidate_edema_dice": c["myops_edema_dice"],
            "delta_edema_dice": delta(c["myops_edema_dice"], b["myops_edema_dice"]),
            "baseline_edema_hd95": b["myops_edema_hd95"],
            "candidate_edema_hd95": c["myops_edema_hd95"],
            "delta_edema_hd95_improvement": delta(c["myops_edema_hd95"], b["myops_edema_hd95"], lower_is_better=True),
            "baseline_edema_component_count": b["myops_edema_component_count"],
            "candidate_edema_component_count": c["myops_edema_component_count"],
            "delta_edema_component_count_improvement": delta(c["myops_edema_component_count"], b["myops_edema_component_count"], lower_is_better=True),
            "baseline_edema_remote_fp": b["myops_edema_remote_fp"],
            "candidate_edema_remote_fp": c["myops_edema_remote_fp"],
            "delta_edema_remote_fp_improvement": delta(c["myops_edema_remote_fp"], b["myops_edema_remote_fp"], lower_is_better=True),
            "baseline_scar_dice": b["myops_scar_dice"],
            "candidate_scar_dice": c["myops_scar_dice"],
            "delta_scar_dice": delta(c["myops_scar_dice"], b["myops_scar_dice"]),
            "baseline_scar_hd95": b["myops_scar_hd95"],
            "candidate_scar_hd95": c["myops_scar_hd95"],
            "delta_scar_hd95_improvement": delta(c["myops_scar_hd95"], b["myops_scar_hd95"], lower_is_better=True),
        }
        out.append(row)
    return out


def build_failure_flags(all_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_case: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in all_rows:
        by_case[str(row["case_id"])][str(row["model"])] = row
    out = []
    for cid, pair in sorted(by_case.items()):
        b = pair.get("baseline_nnunet501_fold0")
        c = pair.get("candidate_laneA_round4")
        if not b or not c:
            out.append({"case_id": cid, "flag": "missing_baseline_or_candidate"})
            continue
        flags = []
        ed_dice_delta = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
        ed_hd95_delta = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
        comp_delta = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
        remote_delta = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
        scar_dice_delta = delta(c.get("myops_scar_dice"), b.get("myops_scar_dice"))
        scar_hd95_delta = delta(c.get("myops_scar_hd95"), b.get("myops_scar_hd95"), lower_is_better=True)
        if ed_dice_delta is not None and ed_dice_delta > 0.005 and ed_hd95_delta is not None and ed_hd95_delta < -0.5:
            flags.append("edema_dice_up_hd95_worse")
        if comp_delta is not None and comp_delta < -0.5:
            flags.append("edema_component_worse")
        if remote_delta is not None and remote_delta < 0:
            flags.append("edema_remote_fp_worse")
        if scar_dice_delta is not None and scar_dice_delta < -0.02:
            flags.append("scar_dice_guardrail_drop")
        if scar_hd95_delta is not None and scar_hd95_delta < -1.0:
            flags.append("scar_hd95_guardrail_worse")
        if c.get("t2_present") is False and c.get("edema_gt_positive") is False:
            if float(c.get("myops_edema_component_count") or 0) > float(b.get("myops_edema_component_count") or 0):
                flags.append("no_t2_empty_gt_new_edema_fp")
        out.append(
            {
                "case_id": cid,
                "center": c.get("center"),
                "modality_group": c.get("modality_group"),
                "t2_present": c.get("t2_present"),
                "edema_gt_positive": c.get("edema_gt_positive"),
                "delta_edema_dice": ed_dice_delta,
                "delta_edema_hd95_improvement": ed_hd95_delta,
                "delta_edema_component_count_improvement": comp_delta,
                "delta_edema_remote_fp_improvement": remote_delta,
                "delta_scar_dice": scar_dice_delta,
                "delta_scar_hd95_improvement": scar_hd95_delta,
                "flags": ";".join(flags),
            }
        )
    return out


def decide(comparison: list[dict[str, object]], flags: list[dict[str, object]]) -> tuple[str, list[str]]:
    by_subset = {r["subset"]: r for r in comparison}
    reasons = []
    hard_flags = [r for r in flags if r.get("flags")]
    for item in hard_flags[:10]:
        reasons.append(f"{item['case_id']}: {item['flags']}")
    center = by_subset["CenterC"]
    t2pos = by_subset["t2_present_gt_positive"]
    center_dice = center.get("delta_edema_dice")
    center_hd95 = center.get("delta_edema_hd95_improvement")
    t2_dice = t2pos.get("delta_edema_dice")
    t2_hd95 = t2pos.get("delta_edema_hd95_improvement")
    comp_center = center.get("delta_edema_component_count_improvement")
    remote_center = center.get("delta_edema_remote_fp_improvement")
    scar_all = by_subset["all_case"].get("delta_scar_dice")
    scar_hd_all = by_subset["all_case"].get("delta_scar_hd95_improvement")

    positive = (
        ((isinstance(center_dice, float) and center_dice > 0.005) or (isinstance(center_hd95, float) and center_hd95 > 0.5))
        or ((isinstance(t2_dice, float) and t2_dice > 0.005) or (isinstance(t2_hd95, float) and t2_hd95 > 0.5))
    )
    no_component_regress = comp_center is None or float(comp_center) >= -0.5
    no_remote_regress = remote_center is None or float(remote_center) >= 0
    scar_ok = (scar_all is None or float(scar_all) >= -0.02) and (scar_hd_all is None or float(scar_hd_all) >= -1.0)

    if hard_flags:
        return "fail_stop_no_longer_train", reasons
    if positive and no_component_regress and no_remote_regress and scar_ok:
        return "pass_watch_consider_longer_fold0_train", ["positive T2/CenterC edema signal without guardrail regression"]
    return "watch_stop_no_clear_positive_signal", ["no clear positive CenterC or T2-present GT-positive edema signal"]


def md_table(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col)) for col in columns) + " |")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Lane A Round4 fold0 short train")
    parser.add_argument("--candidate-pred-dir", type=Path, default=CANDIDATE_PRED_DIR)
    parser.add_argument("--baseline-pred-dir", type=Path, default=BASELINE_PRED_DIR)
    args = parser.parse_args()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    baseline_rows = build_case_rows(args.baseline_pred_dir, "baseline_nnunet501_fold0")
    candidate_rows = build_case_rows(args.candidate_pred_dir, "candidate_laneA_round4")
    all_rows = baseline_rows + candidate_rows

    metric_fields = [
        "model",
        "case_id",
        "missing_prediction",
        "center",
        "modality_group",
        "t2_present",
        "edema_gt_positive",
        "scar_gt_positive",
        "myops_edema_dice",
        "myops_edema_hd",
        "myops_edema_hd95",
        "myops_edema_component_count",
        "myops_edema_small_fp",
        "myops_edema_remote_fp",
        "myops_edema_pred_gt_volume_ratio",
        "myops_scar_dice",
        "myops_scar_hd",
        "myops_scar_hd95",
        "myops_scar_component_count",
        "myops_scar_small_fp",
        "myops_scar_remote_fp",
        "myops_scar_pred_gt_volume_ratio",
    ]
    write_csv(OUT_ROOT / "fold0_short_train_metrics.csv", all_rows, metric_fields)

    subset_names = ["all_case", "t2_present", "t2_present_gt_positive", "complete_modality", "CenterC", "no_t2_empty_gt"]
    subset_rows = []
    for model in ["baseline_nnunet501_fold0", "candidate_laneA_round4"]:
        for subset in subset_names:
            subset_rows.append(aggregate_subset(all_rows, subset, model))
    comparison = build_subset_comparison(subset_rows)
    write_csv(OUT_ROOT / "baseline_vs_candidate_by_subset.csv", comparison)

    flags = build_failure_flags(all_rows)
    write_csv(OUT_ROOT / "case_level_failure_flags.csv", flags)
    decision, reasons = decide(comparison, flags)

    lines = [
        "# Lane A Round4 Fold0 Short Train Summary",
        "",
        "- Candidate: `edema_focal_tversky + no_t2_edema_loss_downweighting`",
        "- Baseline: existing `nnUNet501` fold0 validation predictions",
        "- Scope: fold0 only; no validation zip; no upload; no fold1-4 expansion",
        "",
        "## Baseline vs Candidate By Subset",
        "",
        *md_table(
            comparison,
            [
                "subset",
                "n",
                "delta_edema_dice",
                "delta_edema_hd95_improvement",
                "delta_edema_component_count_improvement",
                "delta_edema_remote_fp_improvement",
                "delta_scar_dice",
                "delta_scar_hd95_improvement",
            ],
        ),
        "",
        "## Decision",
        "",
        f"Decision: `{decision}`",
        "",
        "Reasons:",
        *[f"- {reason}" for reason in reasons],
    ]
    (OUT_ROOT / "fold0_short_train_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    decision_lines = [
        "# Lane A Round4 Decision",
        "",
        f"Decision: `{decision}`",
        "",
        "Required outputs:",
        "- `train_config.yaml`",
        "- `train_command.txt`",
        "- `fold0_short_train_metrics.csv`",
        "- `fold0_short_train_summary.md`",
        "- `baseline_vs_candidate_by_subset.csv`",
        "- `case_level_failure_flags.csv`",
        "- `round4_laneA_decision.md`",
        "",
        "Reasons:",
        *[f"- {reason}" for reason in reasons],
        "",
        "No validation zip was created. No upload was performed. No folds beyond fold0 were trained.",
    ]
    (OUT_ROOT / "round4_laneA_decision.md").write_text("\n".join(decision_lines) + "\n", encoding="utf-8")
    print(f"Wrote Round4 evaluation to {OUT_ROOT}")
    print(f"Decision: {decision}")


if __name__ == "__main__":
    main()
