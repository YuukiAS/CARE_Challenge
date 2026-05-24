#!/usr/bin/env python3
"""Lane A Round6 anatomy soft-prior and missing-modality diagnostics.

This script implements the first Round6 execution step as a diagnostic
upper-bound smoke. It uses existing nnU-Net501 fold0 probabilities and GT
anatomy labels to apply a soft, non-binary penalty to class_4 edema probability
far from myocardium support. The resulting candidate is explicitly oracle /
diagnostic and not submission-eligible. It also writes missing-modality and
complete-case teacher feasibility audits.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk
from scipy import ndimage


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class, hd_class


EDEMA = 4
SCAR = 5
MYO = 1
ANATOMY = (1, 2, 3)

OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round06_anatomy_missing_modality"
PRED_OUT = OUT_ROOT / "predictions/anatomy_soft_prior_oracle_diagnostic"
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
BASELINE_PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)
BASELINE_PROB_DIR = BASELINE_PRED_DIR
CASE_METRICS = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv"
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
CASES_JSON = REPO_ROOT / "data/benchmarks/protocol/cases_MyoPS.json"
RAW_ROOT = REPO_ROOT / "data/CARE_Challenge/MyoPS_train"
FOLD0_VAL_ROOT = REPO_ROOT / "data/CARE_Challenge_folds/MyoPS/fold0/val"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def bool_csv(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() == "true"


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


def md_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


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


def fold0_cases() -> list[str]:
    return list(read_json(SPLITS_JSON)["folds"][0]["val"])


def train_cases() -> list[str]:
    return list(read_json(SPLITS_JSON)["folds"][0]["train"])


def load_case_meta() -> dict[str, dict[str, object]]:
    cases = read_json(CASES_JSON)["cases"]
    center = {row["case_id"]: row["center"] for row in cases}
    out: dict[str, dict[str, object]] = {}
    for case_id, c in center.items():
        case_dir = RAW_ROOT / c / case_id
        has_lge = (case_dir / f"{case_id}_LGE.nii.gz").is_file()
        has_t2 = (case_dir / f"{case_id}_T2.nii.gz").is_file()
        has_c0 = (case_dir / f"{case_id}_C0.nii.gz").is_file()
        if has_lge and has_t2 and has_c0:
            group = "C0+LGE+T2"
        elif has_lge and has_c0:
            group = "C0+LGE"
        elif has_lge:
            group = "LGE-only"
        else:
            group = "other"
        label_path = GT_DIR / f"{case_id}.nii.gz"
        edema_gt_positive = False
        scar_gt_positive = False
        if label_path.is_file():
            _, label = read_label(label_path)
            edema_gt_positive = bool((label == EDEMA).any())
            scar_gt_positive = bool((label == SCAR).any())
        out[case_id] = {
            "center": c,
            "modality_group": group,
            "lge_present": has_lge,
            "t2_present": has_t2,
            "c0_present": has_c0,
            "edema_gt_positive": edema_gt_positive,
            "scar_gt_positive": scar_gt_positive,
        }
    # Prefer existing audit labels for exact fold0 metadata if available.
    if CASE_METRICS.is_file():
        for row in read_csv(CASE_METRICS):
            cid = row["case_id"]
            out.setdefault(cid, {})
            out[cid].update(
                {
                    "center": row["center"],
                    "modality_group": row["modality_group"],
                    "t2_present": row["modality_group"] == "C0+LGE+T2",
                    "c0_present": row["modality_group"] in {"C0+LGE+T2", "C0+LGE"},
                    "lge_present": True,
                    "edema_gt_positive": bool_csv(row["edema_gt_positive"]),
                    "scar_gt_positive": bool_csv(row["scar_gt_positive"]),
                }
            )
    return out


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


def save_pred_like(array: np.ndarray, reference: sitk.Image, path: Path) -> None:
    img = sitk.GetImageFromArray(array.astype(np.uint8, copy=False))
    img.CopyInformation(reference)
    path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(path))


def component_count(mask: np.ndarray) -> int:
    _, n_cc = ndimage.label(mask.astype(bool), structure=ndimage.generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def bbox(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    return coords.min(axis=0), coords.max(axis=0)


def bbox_gap_mm(
    a: tuple[np.ndarray, np.ndarray] | None,
    b: tuple[np.ndarray, np.ndarray] | None,
    spacing: tuple[float, ...],
) -> float | None:
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
    cc, n_cc = ndimage.label(pred_mask.astype(bool), structure=ndimage.generate_binary_structure(pred_mask.ndim, 1))
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


def anatomy_soft_prior_multiplier(gt: np.ndarray, spacing: tuple[float, ...], radius_mm: float, scale_mm: float, penalty_strength: float) -> tuple[np.ndarray, np.ndarray]:
    myo = gt == MYO
    if not myo.any():
        dist = np.full(gt.shape, radius_mm, dtype=np.float32)
        return np.ones(gt.shape, dtype=np.float32), dist
    dist = ndimage.distance_transform_edt(~myo, sampling=spacing).astype(np.float32)
    logistic = 1.0 / (1.0 + np.exp(-(dist - radius_mm) / max(scale_mm, 1e-3)))
    multiplier = 1.0 - penalty_strength * logistic
    return multiplier.astype(np.float32), dist


def build_soft_prior_predictions(config: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    PRED_OUT.mkdir(parents=True, exist_ok=True)
    radius_mm = float(config["soft_support_radius_mm"])
    scale_mm = float(config["soft_penalty_scale_mm"])
    penalty = float(config["remote_edema_probability_penalty_strength"])
    for cid in fold0_cases():
        gt_img, gt = read_label(GT_DIR / f"{cid}.nii.gz")
        baseline_pred = read_pred(BASELINE_PRED_DIR / f"{cid}.nii.gz", gt_img)
        prob_path = BASELINE_PROB_DIR / f"{cid}.npz"
        if not prob_path.is_file():
            candidate = baseline_pred.copy()
            note = "missing_probabilities_used_baseline"
            mean_multiplier = None
        else:
            probs = np.load(prob_path)["probabilities"].astype(np.float32, copy=True)
            spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
            multiplier, dist = anatomy_soft_prior_multiplier(gt, spacing, radius_mm, scale_mm, penalty)
            probs[EDEMA] *= multiplier
            sums = probs.sum(axis=0, keepdims=True)
            probs = probs / np.clip(sums, 1e-6, None)
            candidate = np.argmax(probs, axis=0).astype(np.uint8)
            note = "oracle_gt_myo_soft_probability_penalty_not_submission_eligible"
            baseline_edema = baseline_pred == EDEMA
            mean_multiplier = float(np.mean(multiplier[baseline_edema])) if baseline_edema.any() else None
        save_pred_like(candidate, gt_img, PRED_OUT / f"{cid}.nii.gz")
        rows.append({"case_id": cid, "candidate_note": note, "mean_multiplier_on_baseline_edema": mean_multiplier})
    return rows


def build_case_rows(pred_dir: Path, model: str, meta: dict[str, dict[str, object]]) -> list[dict[str, object]]:
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
    if name.startswith("modality:"):
        group = name.split(":", 1)[1]
        return lambda r: r.get("modality_group") == group
    raise ValueError(name)


def aggregate_subset(rows: list[dict[str, object]], subset: str, model: str) -> dict[str, object]:
    items = [r for r in rows if r["model"] == model and not r.get("missing_prediction") and subset_filter(subset)(r)]
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
    subsets = [
        "all_case",
        "t2_present",
        "t2_present_gt_positive",
        "complete_modality",
        "CenterC",
        "no_t2_empty_gt",
        "modality:C0+LGE+T2",
        "modality:C0+LGE",
        "modality:LGE-only",
    ]
    for subset in subsets:
        b = by_key[("baseline_nnunet501_fold0", subset)]
        c = by_key[("anatomy_soft_prior_oracle_diagnostic", subset)]
        out.append(
            {
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
        )
    return out


def build_failure_flags(all_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_case: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in all_rows:
        by_case[str(row["case_id"])][str(row["model"])] = row
    out = []
    for cid, pair in sorted(by_case.items()):
        b = pair.get("baseline_nnunet501_fold0")
        c = pair.get("anatomy_soft_prior_oracle_diagnostic")
        if not b or not c:
            out.append({"case_id": cid, "flags": "missing_baseline_or_candidate"})
            continue
        flags = []
        ed_dice_delta = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
        ed_hd95_delta = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
        comp_delta = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
        remote_delta = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
        scar_dice_delta = delta(c.get("myops_scar_dice"), b.get("myops_scar_dice"))
        scar_hd95_delta = delta(c.get("myops_scar_hd95"), b.get("myops_scar_hd95"), lower_is_better=True)
        if ed_dice_delta is not None and ed_dice_delta < -0.005:
            flags.append("edema_dice_drop")
        if ed_dice_delta is not None and ed_dice_delta > 0.005 and ed_hd95_delta is not None and ed_hd95_delta < -0.5:
            flags.append("edema_dice_up_hd95_worse")
        if ed_hd95_delta is not None and ed_hd95_delta < -0.5:
            flags.append("edema_hd95_worse")
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


def supervision_audit(all_rows: list[dict[str, object]], meta: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    baseline_rows = [r for r in all_rows if r["model"] == "baseline_nnunet501_fold0"]
    groups = []
    for field in ("modality_group", "center"):
        values = sorted({str(r.get(field)) for r in baseline_rows})
        for value in values:
            items = [r for r in baseline_rows if str(r.get(field)) == value]
            groups.append(group_supervision_row(field, value, items))
    for value in ("all", "t2_present", "no_t2", "no_t2_empty_gt"):
        if value == "all":
            items = baseline_rows
        elif value == "t2_present":
            items = [r for r in baseline_rows if r.get("t2_present") is True]
        elif value == "no_t2":
            items = [r for r in baseline_rows if r.get("t2_present") is False]
        else:
            items = [r for r in baseline_rows if r.get("t2_present") is False and r.get("edema_gt_positive") is False]
        groups.append(group_supervision_row("policy_group", value, items))
    groups.extend(no_t2_policy_rows(baseline_rows))
    groups.extend(modality_mask_feasibility_rows(baseline_rows))
    return groups


def group_supervision_row(group_type: str, group: str, items: list[dict[str, object]]) -> dict[str, object]:
    n = len(items)
    edema_pos = sum(1 for r in items if r.get("edema_gt_positive") is True)
    scar_pos = sum(1 for r in items if r.get("scar_gt_positive") is True)
    edema_fp = sum(1 for r in items if r.get("edema_gt_positive") is False and float(r.get("myops_edema_component_count") or 0) > 0)
    scar_fp = sum(1 for r in items if r.get("scar_gt_positive") is False and float(r.get("myops_scar_component_count") or 0) > 0)
    no_t2 = sum(1 for r in items if r.get("t2_present") is False)
    hard_negative_risk = "high" if no_t2 and edema_pos == 0 else "medium" if no_t2 else "low"
    return {
        "group_type": group_type,
        "group": group,
        "n": n,
        "edema_gt_positive_n": edema_pos,
        "edema_gt_prevalence": (edema_pos / n) if n else None,
        "scar_gt_positive_n": scar_pos,
        "scar_gt_prevalence": (scar_pos / n) if n else None,
        "baseline_edema_fp_cases": edema_fp,
        "baseline_scar_fp_cases": scar_fp,
        "baseline_edema_dice_gt_positive": avg([r.get("myops_edema_dice") for r in items if r.get("edema_gt_positive") is True]),
        "baseline_edema_hd95_gt_positive": avg([r.get("myops_edema_hd95") for r in items if r.get("edema_gt_positive") is True]),
        "baseline_scar_dice_gt_positive": avg([r.get("myops_scar_dice") for r in items if r.get("scar_gt_positive") is True]),
        "baseline_scar_hd95_gt_positive": avg([r.get("myops_scar_hd95") for r in items if r.get("scar_gt_positive") is True]),
        "mean_edema_components": avg([r.get("myops_edema_component_count") for r in items]),
        "mean_edema_remote_fp": avg([r.get("myops_edema_remote_fp") for r in items]),
        "hard_negative_policy_risk": hard_negative_risk,
        "recommended_policy": "uncertainty_weighted_or_masked" if hard_negative_risk == "high" else "standard_supervision_ok",
        "modality_mask_signal": "go" if hard_negative_risk == "high" or group in {"C0+LGE+T2", "C0+LGE", "LGE-only"} else "watch",
    }


def no_t2_policy_rows(items: list[dict[str, object]]) -> list[dict[str, object]]:
    no_t2 = [r for r in items if r.get("t2_present") is False]
    no_t2_empty = [r for r in no_t2 if r.get("edema_gt_positive") is False]
    t2_pos = [r for r in items if r.get("t2_present") is True and r.get("edema_gt_positive") is True]
    no_t2_fp_cases = sum(1 for r in no_t2_empty if float(r.get("myops_edema_component_count") or 0) > 0)
    policies = [
        (
            "hard_negative",
            "reject",
            "Treating no-T2 empty-GT as full edema-negative supervision encodes center/modality shortcut.",
        ),
        (
            "masking",
            "watch",
            "Safer than hard negative, but may remove regularization from 28 no-T2 fold0 validation cases.",
        ),
        (
            "downweighting",
            "watch",
            "Round4 used downweighting and still failed via remote FP / no-T2 FP in candidate predictions.",
        ),
        (
            "uncertainty_weighted",
            "go",
            "Best next policy: combine modality presence, anatomy reliability, and low no-T2 edema weight without hard negatives.",
        ),
    ]
    rows = []
    for policy, decision, reason in policies:
        rows.append(
            {
                "group_type": "no_t2_policy",
                "group": policy,
                "n": len(no_t2),
                "edema_gt_positive_n": sum(1 for r in no_t2 if r.get("edema_gt_positive") is True),
                "edema_gt_prevalence": (sum(1 for r in no_t2 if r.get("edema_gt_positive") is True) / len(no_t2)) if no_t2 else None,
                "scar_gt_positive_n": sum(1 for r in no_t2 if r.get("scar_gt_positive") is True),
                "scar_gt_prevalence": (sum(1 for r in no_t2 if r.get("scar_gt_positive") is True) / len(no_t2)) if no_t2 else None,
                "baseline_edema_fp_cases": no_t2_fp_cases,
                "baseline_scar_fp_cases": sum(1 for r in no_t2 if r.get("scar_gt_positive") is False and float(r.get("myops_scar_component_count") or 0) > 0),
                "baseline_edema_dice_gt_positive": avg([r.get("myops_edema_dice") for r in t2_pos]),
                "baseline_edema_hd95_gt_positive": avg([r.get("myops_edema_hd95") for r in t2_pos]),
                "baseline_scar_dice_gt_positive": avg([r.get("myops_scar_dice") for r in no_t2 if r.get("scar_gt_positive") is True]),
                "baseline_scar_hd95_gt_positive": avg([r.get("myops_scar_hd95") for r in no_t2 if r.get("scar_gt_positive") is True]),
                "mean_edema_components": avg([r.get("myops_edema_component_count") for r in no_t2]),
                "mean_edema_remote_fp": avg([r.get("myops_edema_remote_fp") for r in no_t2]),
                "hard_negative_policy_risk": "high" if policy == "hard_negative" else "medium" if policy in {"masking", "downweighting"} else "low_medium",
                "recommended_policy": decision,
                "modality_mask_signal": reason,
            }
        )
    return rows


def modality_mask_feasibility_rows(items: list[dict[str, object]]) -> list[dict[str, object]]:
    groups = defaultdict(list)
    for row in items:
        groups[str(row.get("modality_group"))].append(row)
    no_t2 = [r for r in items if r.get("t2_present") is False]
    complete = [r for r in items if r.get("t2_present") is True]
    center_confounded = sorted({str(r.get("center")) for r in no_t2}) != sorted({str(r.get("center")) for r in complete})
    return [
        {
            "group_type": "modality_mask_feasibility",
            "group": "explicit_presence_channel_or_film",
            "n": len(items),
            "edema_gt_positive_n": sum(1 for r in complete if r.get("edema_gt_positive") is True),
            "edema_gt_prevalence": (sum(1 for r in complete if r.get("edema_gt_positive") is True) / len(complete)) if complete else None,
            "scar_gt_positive_n": sum(1 for r in items if r.get("scar_gt_positive") is True),
            "scar_gt_prevalence": (sum(1 for r in items if r.get("scar_gt_positive") is True) / len(items)) if items else None,
            "baseline_edema_fp_cases": sum(1 for r in no_t2 if float(r.get("myops_edema_component_count") or 0) > 0),
            "baseline_scar_fp_cases": sum(1 for r in items if r.get("scar_gt_positive") is False and float(r.get("myops_scar_component_count") or 0) > 0),
            "baseline_edema_dice_gt_positive": avg([r.get("myops_edema_dice") for r in complete if r.get("edema_gt_positive") is True]),
            "baseline_edema_hd95_gt_positive": avg([r.get("myops_edema_hd95") for r in complete if r.get("edema_gt_positive") is True]),
            "baseline_scar_dice_gt_positive": avg([r.get("myops_scar_dice") for r in items if r.get("scar_gt_positive") is True]),
            "baseline_scar_hd95_gt_positive": avg([r.get("myops_scar_hd95") for r in items if r.get("scar_gt_positive") is True]),
            "mean_edema_components": avg([r.get("myops_edema_component_count") for r in items]),
            "mean_edema_remote_fp": avg([r.get("myops_edema_remote_fp") for r in items]),
            "hard_negative_policy_risk": "high" if center_confounded else "medium",
            "recommended_policy": "go",
            "modality_mask_signal": f"center_confounded={center_confounded}; groups={','.join(sorted(groups))}",
        }
    ]


def teacher_feasibility(meta: dict[str, dict[str, object]], all_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    baseline = {r["case_id"]: r for r in all_rows if r["model"] == "baseline_nnunet501_fold0"}
    rows = []
    for split_name, cases in [("fold0_train", train_cases()), ("fold0_val", fold0_cases())]:
        complete = [cid for cid in cases if meta.get(cid, {}).get("modality_group") == "C0+LGE+T2"]
        for group_type, values in [
            ("all_complete", ["all"]),
            ("center", sorted({str(meta[cid]["center"]) for cid in complete})),
        ]:
            for group in values:
                cids = complete if group == "all" else [cid for cid in complete if meta[cid]["center"] == group]
                metric_items = [baseline[cid] for cid in cids if cid in baseline]
                edema_pos = [cid for cid in cids if meta.get(cid, {}).get("edema_gt_positive") is True]
                rows.append(
                    {
                        "split": split_name,
                        "group_type": group_type,
                        "group": group,
                        "complete_cases": len(cids),
                        "edema_gt_positive_cases": len(edema_pos),
                        "center_distribution": center_distribution(cids, meta),
                        "teacher_metric_cases_available": len(metric_items),
                        "baseline_teacher_edema_dice": avg([r.get("myops_edema_dice") for r in metric_items]),
                        "baseline_teacher_edema_hd95": avg([r.get("myops_edema_hd95") for r in metric_items]),
                        "baseline_teacher_edema_remote_fp": avg([r.get("myops_edema_remote_fp") for r in metric_items]),
                        "baseline_teacher_scar_dice": avg([r.get("myops_scar_dice") for r in metric_items]),
                        "teacher_feasibility": teacher_status(split_name, len(cids), len(metric_items), avg([r.get("myops_edema_dice") for r in metric_items]), avg([r.get("myops_edema_hd95") for r in metric_items])),
                    }
                )
    return rows


def center_distribution(cids: list[str], meta: dict[str, dict[str, object]]) -> str:
    counts = Counter(str(meta[cid]["center"]) for cid in cids if cid in meta)
    return ";".join(f"{k}:{v}" for k, v in sorted(counts.items()))


def teacher_status(split: str, n_complete: int, n_metric: int, edema_dice: float | None, edema_hd95: float | None) -> str:
    if split == "fold0_train":
        if n_complete >= 50:
            return "watch_train_count_sufficient_but_metrics_unavailable"
        return "postpone_insufficient_complete_train_cases"
    if n_metric < 8:
        return "postpone_too_few_complete_val_metric_cases"
    if edema_dice is not None and edema_hd95 is not None and edema_dice >= 0.4 and edema_hd95 <= 20:
        return "watch_possible_teacher"
    return "postpone_teacher_not_reliable_for_edema_distillation"


def write_config(config: dict[str, object]) -> None:
    lines = []
    for key, value in config.items():
        if isinstance(value, str):
            lines.append(f"{key}: {json.dumps(value)}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        else:
            lines.append(f"{key}: {value}")
    (OUT_ROOT / "anatomy_soft_prior_train_config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_ROOT / "anatomy_soft_prior_train_command.txt").write_text(
        "./envs/env_CARE/bin/python scripts/diagnostics/laneA_round06_anatomy_missing_modality.py\n",
        encoding="utf-8",
    )


def write_summaries(
    comparison: list[dict[str, object]],
    flags: list[dict[str, object]],
    supervision: list[dict[str, object]],
    teacher: list[dict[str, object]],
    decision: str,
    reasons: list[str],
) -> None:
    comp_cols = [
        "subset",
        "n",
        "delta_edema_dice",
        "delta_edema_hd95_improvement",
        "delta_edema_component_count_improvement",
        "delta_edema_remote_fp_improvement",
        "delta_scar_dice",
        "delta_scar_hd95_improvement",
    ]
    (OUT_ROOT / "anatomy_soft_prior_summary.md").write_text(
        "# Lane A Round6 Anatomy Soft Prior Diagnostic Summary\n\n"
        "Candidate: `anatomy_soft_prior_oracle_diagnostic`.\n\n"
        "This is an oracle/diagnostic upper-bound smoke using GT myocardium-derived soft distance support and existing nnU-Net501 probabilities. It is not submission-eligible and does not train a model.\n\n"
        "## Baseline vs Candidate\n\n"
        + md_table(comparison, comp_cols)
        + "\n\n## Decision\n\n"
        + f"Decision: `{decision}`\n\n"
        + "\n".join(f"- {r}" for r in reasons)
        + "\n",
        encoding="utf-8",
    )
    sup_cols = [
        "group_type",
        "group",
        "n",
        "edema_gt_positive_n",
        "edema_gt_prevalence",
        "baseline_edema_fp_cases",
        "baseline_edema_dice_gt_positive",
        "baseline_edema_hd95_gt_positive",
        "mean_edema_remote_fp",
        "hard_negative_policy_risk",
        "recommended_policy",
        "modality_mask_signal",
    ]
    (OUT_ROOT / "missing_modality_supervision_audit.md").write_text(
        "# Lane A Round6 Missing-Modality Supervision Audit\n\n"
        "This audit is CARE-only. It does not implement AdaMM/UniME/CoPeDiT/I-MMSeg and does not use external data or validation pseudo-labels.\n\n"
        + md_table(supervision, sup_cols)
        + "\n\nInterpretation:\n\n"
        "- no-T2 groups with zero edema GT remain unsafe as strong negative supervision.\n"
        "- explicit modality mask or uncertainty-weighted supervision should stay in the next model route if no-T2 policy remains high risk.\n",
        encoding="utf-8",
    )
    teacher_cols = [
        "split",
        "group_type",
        "group",
        "complete_cases",
        "edema_gt_positive_cases",
        "center_distribution",
        "teacher_metric_cases_available",
        "baseline_teacher_edema_dice",
        "baseline_teacher_edema_hd95",
        "baseline_teacher_edema_remote_fp",
        "teacher_feasibility",
    ]
    (OUT_ROOT / "complete_case_teacher_feasibility.md").write_text(
        "# Lane A Round6 Complete-Case Teacher Feasibility\n\n"
        "Teacher feasibility is CARE-only and uses current fold0 nnU-Net501 metrics as a proxy. It does not start distillation.\n\n"
        + md_table(teacher, teacher_cols)
        + "\n\nInterpretation:\n\n"
        "- A future AdaMM-style route needs a reliable complete-case teacher, especially on CenterC edema HD95/remote-FP behavior.\n"
        "- If the teacher is only watch/postpone, missing-modality distillation should not be the next training route.\n",
        encoding="utf-8",
    )
    (OUT_ROOT / "round6_laneA_decision_table.md").write_text(
        "# Lane A Round6 Decision Table\n\n"
        + md_table(
            [
                {
                    "route": "anatomy_guided_soft_prior_bounded_smoke",
                    "status": decision_status(decision),
                    "evidence": "; ".join(reasons[:3]),
                    "next_action": anatomy_next_action(decision),
                },
                {
                    "route": "missing_modality_routing_and_supervision_audit",
                    "status": missing_modality_status(supervision, teacher),
                    "evidence": missing_modality_evidence(supervision, teacher),
                    "next_action": "Keep explicit modality mask / uncertainty-weighted policy under controlled first-party route; do not integrate AdaMM/UniME yet.",
                },
                {
                    "route": "controlled_repo_integration_readiness",
                    "status": "postpone",
                    "evidence": "Round06 used CARE-only diagnostics; no external repo/weights were needed.",
                    "next_action": "Only start metadata-level external repo screen after a first-party fold0 signal is clean.",
                },
            ],
            ["route", "status", "evidence", "next_action"],
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT_ROOT / "round6_next_goal_prompt.md").write_text(
        "# Next Goal Prompt Draft\n\n"
        "你现在在 `/overflow/htzhu/CARE` 中工作。请基于 "
        "`results/diagnostics/care_myocardium/laneA_myops/round06_anatomy_missing_modality/round6_laneA_decision_table.md` "
        "继续 Lane A。若 anatomy soft-prior diagnostic 为 `go/watch`，下一步只能实现非 oracle first-party anatomy source 或 tiny trainable smoke；"
        "不得使用 GT anatomy 作为 submission path。禁止 fold1-4、5-fold、validation zip、上传、外部数据训练、validation pseudo-label supervised training、硬 ROI 删除和大型 repo/weights 下载。"
        "继续分别报告 `myops_edema` 与 `myops_scar`，并按 T2-present GT-positive、complete-modality、CenterC、no-T2 empty-GT、modality group、center 分组。\n",
        encoding="utf-8",
    )


def generate_failure_overlays(flags: list[dict[str, object]]) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - optional diagnostic
        (OUT_ROOT / "failure_overlays_skipped.txt").write_text(f"matplotlib unavailable: {exc}\n", encoding="utf-8")
        return

    overlay_dir = OUT_ROOT / "failure_overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    flagged = [row for row in flags if row.get("flags")]
    selected = flagged[:8]
    for row in selected:
        cid = str(row["case_id"])
        try:
            gt_img, gt = read_label(GT_DIR / f"{cid}.nii.gz")
            baseline = read_pred(BASELINE_PRED_DIR / f"{cid}.nii.gz", gt_img)
            candidate = read_pred(PRED_OUT / f"{cid}.nii.gz", gt_img)
            lge_path = FOLD0_VAL_ROOT / cid / f"{cid}_LGE.nii.gz"
            if lge_path.is_file():
                _, lge = read_label(lge_path)
                image = lge.astype(np.float32)
            else:
                image = gt.astype(np.float32)
            edema_slices = np.where(((gt == EDEMA) | (baseline == EDEMA) | (candidate == EDEMA)).reshape(gt.shape[0], -1).any(axis=1))[0]
            z = int(edema_slices[len(edema_slices) // 2]) if len(edema_slices) else gt.shape[0] // 2
            base = image[z]
            lo, hi = np.percentile(base[np.isfinite(base)], [1, 99]) if np.isfinite(base).any() else (0, 1)
            fig, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)
            panels = [
                ("GT edema/scar", gt),
                ("baseline edema", baseline),
                ("soft prior edema", candidate),
            ]
            for ax, (title, arr) in zip(axes, panels):
                ax.imshow(base, cmap="gray", vmin=lo, vmax=hi)
                ax.contour(gt[z] == EDEMA, colors="lime", linewidths=0.7)
                ax.contour(arr[z] == EDEMA, colors="red", linewidths=0.7)
                ax.set_title(title, fontsize=9)
                ax.axis("off")
            fig.suptitle(f"{cid} z={z} flags={row.get('flags')}", fontsize=10)
            fig.savefig(overlay_dir / f"{cid}_round6_soft_prior_overlay.png", dpi=150)
            plt.close(fig)
        except Exception as exc:  # pragma: no cover - optional diagnostic
            (overlay_dir / f"{cid}_overlay_error.txt").write_text(str(exc) + "\n", encoding="utf-8")


def decision_status(decision: str) -> str:
    if decision.startswith("pass"):
        return "go"
    if decision.startswith("watch"):
        return "watch"
    return "stop"


def anatomy_next_action(decision: str) -> str:
    if decision.startswith("pass"):
        return "Implement non-oracle first-party anatomy source and run bounded trainable smoke."
    if decision.startswith("watch"):
        return "Do not expand; refine non-oracle anatomy source or lower penalty and repeat tiny smoke."
    return "Stop current soft prior configuration; do not train longer."


def missing_modality_status(supervision: list[dict[str, object]], teacher: list[dict[str, object]]) -> str:
    high_risk = [r for r in supervision if r.get("hard_negative_policy_risk") == "high"]
    possible_teacher = [r for r in teacher if str(r.get("teacher_feasibility", "")).startswith("watch_possible_teacher")]
    if high_risk:
        return "go"
    if possible_teacher:
        return "watch"
    return "watch"


def missing_modality_evidence(supervision: list[dict[str, object]], teacher: list[dict[str, object]]) -> str:
    high_risk = [r for r in supervision if r.get("hard_negative_policy_risk") == "high"]
    teacher_counts = Counter(str(r.get("teacher_feasibility")) for r in teacher)
    return f"hard_negative_high_risk_groups={len(high_risk)}; teacher_feasibility={dict(teacher_counts)}"


def decide(comparison: list[dict[str, object]], flags: list[dict[str, object]]) -> tuple[str, list[str]]:
    by_subset = {r["subset"]: r for r in comparison}
    reasons = []
    hard_flags = [r for r in flags if r.get("flags")]
    if hard_flags:
        for item in hard_flags[:10]:
            reasons.append(f"{item['case_id']}: {item['flags']}")
    center = by_subset["CenterC"]
    t2pos = by_subset["t2_present_gt_positive"]
    no_t2 = by_subset["no_t2_empty_gt"]
    scar_all = by_subset["all_case"]
    center_signal = positive_edema_signal(center)
    t2_signal = positive_edema_signal(t2pos)
    no_t2_ok = (no_t2.get("delta_edema_component_count_improvement") is None or float(no_t2.get("delta_edema_component_count_improvement") or 0) >= 0) and (
        no_t2.get("delta_edema_remote_fp_improvement") is None or float(no_t2.get("delta_edema_remote_fp_improvement") or 0) >= 0
    )
    scar_ok = (scar_all.get("delta_scar_dice") is None or float(scar_all.get("delta_scar_dice") or 0) >= -0.02) and (
        scar_all.get("delta_scar_hd95_improvement") is None or float(scar_all.get("delta_scar_hd95_improvement") or 0) >= -1.0
    )
    remote_ok = float(center.get("delta_edema_remote_fp_improvement") or 0) >= 0
    comp_ok = float(center.get("delta_edema_component_count_improvement") or 0) >= -0.5
    if hard_flags:
        return "fail_stop_no_expand", reasons
    if (center_signal or t2_signal) and no_t2_ok and scar_ok and remote_ok and comp_ok:
        return "pass_watch_non_oracle_trainable_smoke_next", ["positive edema signal with no no-T2/scar/component guardrail regression"]
    if no_t2_ok and scar_ok:
        return "watch_no_clear_trainable_promotion", ["guardrails mostly clean, but CenterC/T2-positive signal is not strong enough"]
    return "fail_stop_no_expand", ["guardrail or subgroup criteria failed"]


def positive_edema_signal(row: dict[str, object]) -> bool:
    dice_delta = row.get("delta_edema_dice")
    hd95_delta = row.get("delta_edema_hd95_improvement")
    dice_ok = dice_delta is not None and float(dice_delta) > 0.005
    hd95_ok = hd95_delta is not None and float(hd95_delta) > 0.5
    dice_not_bad = dice_delta is None or float(dice_delta) >= -0.005
    hd95_not_bad = hd95_delta is None or float(hd95_delta) >= -0.5
    return (dice_ok and hd95_not_bad) or (hd95_ok and dice_not_bad)


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    config = {
        "candidate": "anatomy_soft_prior_oracle_diagnostic",
        "submission_eligible": False,
        "fold": 0,
        "seed": 42,
        "baseline_prob_dir": str(BASELINE_PROB_DIR),
        "candidate_pred_dir": str(PRED_OUT),
        "anatomy_source": "GT compact class_1 myocardium oracle; diagnostic upper-bound only",
        "soft_support_radius_mm": 10.0,
        "soft_penalty_scale_mm": 5.0,
        "remote_edema_probability_penalty_strength": 0.35,
        "hard_deletion": False,
        "fold1_4": False,
        "validation_zip": False,
        "external_data": False,
        "validation_pseudo_label_supervised_training": False,
    }
    write_config(config)
    adjustment_rows = build_soft_prior_predictions(config)
    write_csv(OUT_ROOT / "anatomy_soft_prior_adjustments.csv", adjustment_rows)

    meta = load_case_meta()
    baseline_rows = build_case_rows(BASELINE_PRED_DIR, "baseline_nnunet501_fold0", meta)
    candidate_rows = build_case_rows(PRED_OUT, "anatomy_soft_prior_oracle_diagnostic", meta)
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
    write_csv(OUT_ROOT / "anatomy_soft_prior_metrics.csv", all_rows, metric_fields)
    subset_rows = []
    for model in ["baseline_nnunet501_fold0", "anatomy_soft_prior_oracle_diagnostic"]:
        for subset in [
            "all_case",
            "t2_present",
            "t2_present_gt_positive",
            "complete_modality",
            "CenterC",
            "no_t2_empty_gt",
            "modality:C0+LGE+T2",
            "modality:C0+LGE",
            "modality:LGE-only",
        ]:
            subset_rows.append(aggregate_subset(all_rows, subset, model))
    comparison = build_subset_comparison(subset_rows)
    write_csv(OUT_ROOT / "baseline_vs_anatomy_prior_by_subset.csv", comparison)
    flags = build_failure_flags(all_rows)
    write_csv(OUT_ROOT / "case_level_anatomy_failure_flags.csv", flags)
    supervision = supervision_audit(all_rows, meta)
    write_csv(OUT_ROOT / "missing_modality_supervision_audit.csv", supervision)
    teacher = teacher_feasibility(meta, all_rows)
    write_csv(OUT_ROOT / "complete_case_teacher_feasibility.csv", teacher)
    decision, reasons = decide(comparison, flags)
    write_summaries(comparison, flags, supervision, teacher, decision, reasons)
    generate_failure_overlays(flags)
    print(f"Wrote Lane A Round6 outputs to {OUT_ROOT}")
    print(f"Decision: {decision}")


if __name__ == "__main__":
    main()
