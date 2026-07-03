"""nnU-Net anchored MyoPS pathology refiner/postprocessor utilities."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Callable

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import (
    binary_closing,
    binary_dilation,
    binary_erosion,
    distance_transform_edt,
    generate_binary_structure,
    label,
)


EDEMA = 4
SCAR = 5
PATHOLOGY = ((EDEMA, "myops_edema"), (SCAR, "myops_scar"))
VALID_LABELS = {0, 1, 2, 3, 4, 5}


@dataclass(frozen=True)
class CaseInfo:
    case_id: str
    center: str
    modality_group: str
    t2_present: bool
    gt_path: Path
    pred_path: Path
    prob_path: Path
    image_paths: dict[str, Path]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def finite_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def finite_mean(values: list[Any]) -> float | None:
    vals = [v for v in (finite_float(x) for x in values) if v is not None]
    return float(mean(vals)) if vals else None


def fmt(value: Any) -> str:
    v = finite_float(value)
    if v is None:
        return "NA"
    return f"{v:.6f}"


def load_fold_cases(splits_json: Path, fold: int, split: str) -> list[str]:
    with splits_json.open(encoding="utf-8") as f:
        data = json.load(f)
    return [str(c) for c in data["folds"][fold][split]]


def build_cases(
    *,
    fold_val_cases: list[str],
    case_meta_csv: Path,
    gt_dir: Path,
    baseline_pred_dir: Path,
    prob_dir: Path,
    image_dir: Path,
) -> list[CaseInfo]:
    meta_rows = {row["case_id"]: row for row in read_csv(case_meta_csv)}
    cases: list[CaseInfo] = []
    for cid in fold_val_cases:
        row = meta_rows.get(cid)
        if row is None:
            raise RuntimeError(f"missing case metadata for {cid}: {case_meta_csv}")
        cases.append(
            CaseInfo(
                case_id=cid,
                center=row["center"],
                modality_group=row["modality_group"],
                t2_present=row["modality_group"] == "C0+LGE+T2",
                gt_path=gt_dir / f"{cid}.nii.gz",
                pred_path=baseline_pred_dir / f"{cid}.nii.gz",
                prob_path=prob_dir / f"{cid}.npz",
                image_paths={
                    "LGE": image_dir / f"{cid}_0000.nii.gz",
                    "T2": image_dir / f"{cid}_0001.nii.gz",
                    "C0": image_dir / f"{cid}_0002.nii.gz",
                },
            )
        )
    return cases


def read_label(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    arr = sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)
    return img, arr


def read_image_array(path: Path, reference: sitk.Image) -> np.ndarray:
    img = sitk.ReadImage(str(path))
    if (
        img.GetSize() != reference.GetSize()
        or img.GetSpacing() != reference.GetSpacing()
        or img.GetOrigin() != reference.GetOrigin()
        or img.GetDirection() != reference.GetDirection()
    ):
        img = sitk.Resample(img, reference, sitk.Transform(), sitk.sitkLinear, 0, img.GetPixelID())
    return sitk.GetArrayFromImage(img).astype(np.float32, copy=False)


def resample_label(path: Path, reference: sitk.Image) -> np.ndarray:
    img = sitk.ReadImage(str(path))
    if (
        img.GetSize() != reference.GetSize()
        or img.GetSpacing() != reference.GetSpacing()
        or img.GetOrigin() != reference.GetOrigin()
        or img.GetDirection() != reference.GetDirection()
    ):
        img = sitk.Resample(img, reference, sitk.Transform(), sitk.sitkNearestNeighbor, 0, img.GetPixelID())
    return sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def load_probs(path: Path) -> np.ndarray:
    with np.load(path) as data:
        return np.asarray(data["probabilities"], dtype=np.float32)


def write_prediction(path: Path, arr: np.ndarray, reference: sitk.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(arr.astype(np.uint8, copy=False))
    img.CopyInformation(reference)
    sitk.WriteImage(img, str(path))


def zscore_in_mask(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    use = mask.astype(bool)
    if not use.any():
        return np.zeros_like(arr, dtype=np.float32)
    vals = arr[use]
    mu = float(np.mean(vals))
    sd = float(np.std(vals))
    if sd < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - mu) / sd).astype(np.float32, copy=False)


def anatomy_support_from_probs(probs: np.ndarray, baseline: np.ndarray) -> np.ndarray:
    anatomy = np.clip(probs[1] + probs[2] + probs[3], 0.0, 1.0)
    hard = binary_dilation(np.isin(baseline, [1, 2, 3, EDEMA, SCAR]), iterations=2)
    return np.maximum(anatomy, hard.astype(np.float32) * 0.45).astype(np.float32, copy=False)


def soft_roi_mask(probs: np.ndarray, baseline: np.ndarray, iterations: int = 4) -> np.ndarray:
    support = (
        np.clip(probs[1] + probs[2] + probs[3] + 0.7 * probs[EDEMA] + 0.7 * probs[SCAR], 0.0, 1.0) >= 0.06
    ) | np.isin(baseline, [1, 2, 3, EDEMA, SCAR])
    return binary_dilation(support, iterations=iterations)


def dice_per_class(pred: np.ndarray, gt: np.ndarray, class_id: int, *, skip_if_gt_empty: bool = False) -> float | None:
    p = pred == class_id
    g = gt == class_id
    inter = np.logical_and(p, g).sum(dtype=np.float64)
    p_sum = float(p.sum())
    g_sum = float(g.sum())
    if skip_if_gt_empty and g_sum < 1e-8:
        return None if p_sum < 1e-8 else 0.0
    denom = p_sum + g_sum
    if denom < 1e-8:
        return 1.0
    return float(2.0 * inter / denom)


def surface_distances(pred_bin: np.ndarray, gt_bin: np.ndarray, spacing_zyx: tuple[float, ...]) -> np.ndarray:
    p = pred_bin.astype(bool)
    g = gt_bin.astype(bool)
    if not p.any() and not g.any():
        return np.array([0.0], dtype=np.float64)
    if not p.any() or not g.any():
        return np.array([np.inf], dtype=np.float64)
    struct = generate_binary_structure(pred_bin.ndim, 1)
    surf_p = p & ~binary_erosion(p, structure=struct)
    surf_g = g & ~binary_erosion(g, structure=struct)
    dt_g = distance_transform_edt(~surf_g, sampling=tuple(float(x) for x in spacing_zyx))
    dt_p = distance_transform_edt(~surf_p, sampling=tuple(float(x) for x in spacing_zyx))
    return np.concatenate([dt_g[surf_p].ravel(), dt_p[surf_g].ravel()]).astype(np.float64, copy=False)


def hd_class(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> float | None:
    p = pred == class_id
    g = gt == class_id
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    d = surface_distances(p, g, spacing_zyx)
    return None if np.isinf(d).any() else float(np.max(d))


def hd95_class(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> float | None:
    p = pred == class_id
    g = gt == class_id
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    d = surface_distances(p, g, spacing_zyx)
    return None if np.isinf(d).any() else float(np.percentile(d, 95))


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def volume_ratio(pred: np.ndarray, gt: np.ndarray) -> float | str | None:
    p = int(pred.sum())
    g = int(gt.sum())
    if g == 0:
        return None if p == 0 else "inf"
    return float(p / g)


def fp_counts(pred_mask: np.ndarray, gt_mask: np.ndarray, small_threshold: int = 20) -> tuple[int, int]:
    cc, n_cc = label(pred_mask.astype(bool), structure=generate_binary_structure(pred_mask.ndim, 1))
    gt_coords = np.argwhere(gt_mask)
    small_fp = 0
    remote_fp = 0
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if np.logical_and(comp, gt_mask).any():
            continue
        if int(comp.sum()) < small_threshold:
            small_fp += 1
        if not len(gt_coords):
            remote_fp += 1
            continue
        coords = np.argwhere(comp)
        comp_center = coords.mean(axis=0)
        gt_min = gt_coords.min(axis=0)
        gt_max = gt_coords.max(axis=0)
        outside = np.maximum(0, np.maximum(gt_min - comp_center, comp_center - gt_max))
        if float(np.linalg.norm(outside)) > 20.0:
            remote_fp += 1
    return small_fp, remote_fp


def component_filter(
    *,
    variant: str,
    case: CaseInfo,
    class_id: int,
    metric_name: str,
    mask: np.ndarray,
    probs: np.ndarray,
    support: np.ndarray,
    selector: Callable[[dict[str, Any]], tuple[str, float]],
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    out = mask.copy()
    rows: list[dict[str, Any]] = []
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        voxels = int(comp.sum())
        mean_pathology_prob = float(np.mean(probs[class_id][comp]))
        mean_anatomy_support = float(np.mean(support[comp]))
        features = {
            "voxels": voxels,
            "decision_small_component": voxels < 20,
            "decision_low_anatomy_support": mean_anatomy_support < 0.10,
            "mean_pathology_prob": mean_pathology_prob,
            "mean_anatomy_support": mean_anatomy_support,
        }
        action, score = selector(features)
        if action == "suppress_component":
            out[comp] = False
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.center,
                "modality_group": case.modality_group,
                "t2_present": case.t2_present,
                "class_id": class_id,
                "metric_name": metric_name,
                "component_id": idx,
                "component_voxels": voxels,
                "decision_small_component": features["decision_small_component"],
                "decision_low_anatomy_support": features["decision_low_anatomy_support"],
                "decision_mean_pathology_prob": features["mean_pathology_prob"],
                "decision_mean_anatomy_support": features["mean_anatomy_support"],
                "component_score": score,
                "action": action,
                "changed_voxels": voxels if action == "suppress_component" else 0,
                "_component_mask": comp,
            }
        )
    return out, rows


def annotate_component_action_rows(rows: list[dict[str, Any]], gt: np.ndarray) -> list[dict[str, Any]]:
    """Add post-hoc evaluation annotations after prediction decisions are fixed."""
    out: list[dict[str, Any]] = []
    for row in rows:
        comp = np.asarray(row["_component_mask"]).astype(bool)
        class_id = int(row["class_id"])
        gt_mask = gt == class_id
        gt_coords = np.argwhere(gt_mask)
        overlaps_gt = bool(np.logical_and(comp, gt_mask).any())
        remote_distance = float("inf")
        if len(gt_coords):
            coords = np.argwhere(comp)
            center = coords.mean(axis=0)
            gt_min = gt_coords.min(axis=0)
            gt_max = gt_coords.max(axis=0)
            outside = np.maximum(0, np.maximum(gt_min - center, center - gt_max))
            remote_distance = float(np.linalg.norm(outside))
        clean = {k: v for k, v in row.items() if not k.startswith("_")}
        clean.update(
            {
                "evaluation_overlaps_gt": overlaps_gt,
                "evaluation_small_fp": (not overlaps_gt) and int(row["component_voxels"]) < 20,
                "evaluation_remote_fp": (not overlaps_gt)
                and (not len(gt_coords) or remote_distance > 20.0),
                "evaluation_remote_distance_vox": "inf" if math.isinf(remote_distance) else remote_distance,
                "evaluation_gt_empty": not bool(gt_mask.any()),
            }
        )
        out.append(clean)
    return out


def annotate_roi_coverage_rows(
    variant: str,
    case: CaseInfo,
    roi: np.ndarray,
    pred: np.ndarray,
    gt: np.ndarray,
) -> list[dict[str, Any]]:
    return roi_coverage_rows(variant, case, roi, pred, gt)


def variant_component_score_refiner(
    case: CaseInfo,
    baseline: np.ndarray,
    probs: np.ndarray,
    raw: dict[str, np.ndarray],
) -> tuple[np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
    del raw
    support = anatomy_support_from_probs(probs, baseline)
    mask = baseline == SCAR

    def select(features: dict[str, Any]) -> tuple[str, float]:
        score = float(2.5 * features["mean_pathology_prob"] + 0.5 * features["mean_anatomy_support"])
        if features["decision_low_anatomy_support"]:
            score -= 0.35
        if features["decision_small_component"]:
            score -= 0.25
        if features["voxels"] >= 80:
            score += 0.12
        return ("suppress_component" if score < 0.94 else "keep_component", score)

    kept, rows = component_filter(
        variant="nnunet_component_score_refiner",
        case=case,
        class_id=SCAR,
        metric_name="myops_scar",
        mask=mask,
        probs=probs,
        support=support,
        selector=select,
    )
    pred = baseline.copy()
    removed = mask & ~kept
    if removed.any():
        non_scar = probs.copy()
        non_scar[SCAR] = -1.0
        pred[removed] = np.argmax(non_scar[:, removed], axis=0).astype(np.uint8, copy=False)
    return pred, rows, []


def variant_roi_pathology_refiner(
    case: CaseInfo,
    baseline: np.ndarray,
    probs: np.ndarray,
    raw: dict[str, np.ndarray],
) -> tuple[np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
    roi = soft_roi_mask(probs, baseline, iterations=4)
    support = anatomy_support_from_probs(probs, baseline)
    lge_z = zscore_in_mask(raw["LGE"], roi)
    t2_z = zscore_in_mask(raw["T2"], roi) if case.t2_present else np.zeros_like(raw["LGE"], dtype=np.float32)
    pred = baseline.copy()
    rows: list[dict[str, Any]] = []

    scar_seed = roi & (probs[SCAR] >= 0.36) & (support >= 0.12) & ((lge_z >= 0.15) | (baseline == SCAR))
    scar_seed = binary_closing(scar_seed, iterations=1)
    pred[(pred == SCAR) | scar_seed] = SCAR

    if case.t2_present:
        edema_seed = (
            roi
            & (pred != SCAR)
            & (probs[EDEMA] >= 0.31)
            & (support >= 0.12)
            & ((t2_z >= 0.10) | (baseline == EDEMA))
        )
        edema_seed = binary_closing(edema_seed, iterations=1)
        pred[(pred == EDEMA) | edema_seed] = EDEMA

    roi_rows = [{"variant": "myocardium_roi_pathology_refiner", "case": case, "roi": roi}]
    return pred.astype(np.uint8, copy=False), rows, roi_rows


def variant_dual_refiner(
    case: CaseInfo,
    baseline: np.ndarray,
    probs: np.ndarray,
    raw: dict[str, np.ndarray],
) -> tuple[np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
    roi = soft_roi_mask(probs, baseline, iterations=5)
    support = anatomy_support_from_probs(probs, baseline)
    lge_z = zscore_in_mask(raw["LGE"], roi)
    t2_z = zscore_in_mask(raw["T2"], roi) if case.t2_present else np.zeros_like(raw["LGE"], dtype=np.float32)
    pred = baseline.copy()

    scar_candidate = roi & (probs[SCAR] >= 0.40) & (support >= 0.14) & ((lge_z >= 0.20) | (baseline == SCAR))
    scar_mask = (baseline == SCAR) | scar_candidate

    def scar_select(features: dict[str, Any]) -> tuple[str, float]:
        score = float(2.7 * features["mean_pathology_prob"] + 0.55 * features["mean_anatomy_support"])
        if features["decision_low_anatomy_support"]:
            score -= 0.42
        if features["decision_small_component"]:
            score -= 0.28
        return ("suppress_component" if score < 1.02 else "keep_component", score)

    scar_kept, rows = component_filter(
        variant="scar_precision_edema_recall_dual_refiner",
        case=case,
        class_id=SCAR,
        metric_name="myops_scar",
        mask=scar_mask,
        probs=probs,
        support=support,
        selector=scar_select,
    )
    pred[baseline == SCAR] = SCAR
    removed = (baseline == SCAR) & ~scar_kept
    if removed.any():
        non_scar = probs.copy()
        non_scar[SCAR] = -1.0
        pred[removed] = np.argmax(non_scar[:, removed], axis=0).astype(np.uint8, copy=False)
    pred[scar_kept] = SCAR

    if case.t2_present:
        edema_candidate = (
            roi
            & (pred != SCAR)
            & (probs[EDEMA] >= 0.26)
            & (support >= 0.10)
            & ((t2_z >= 0.0) | (baseline == EDEMA))
        )
        pred[(baseline == EDEMA) | edema_candidate] = EDEMA
    return pred.astype(np.uint8, copy=False), rows, [
        {"variant": "scar_precision_edema_recall_dual_refiner", "case": case, "roi": roi}
    ]


VARIANTS: dict[str, Callable[[CaseInfo, np.ndarray, np.ndarray, dict[str, np.ndarray]], tuple[np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]]] = {
    "nnunet_component_score_refiner": variant_component_score_refiner,
    "myocardium_roi_pathology_refiner": variant_roi_pathology_refiner,
    "scar_precision_edema_recall_dual_refiner": variant_dual_refiner,
}


def roi_coverage_rows(
    variant: str,
    case: CaseInfo,
    roi: np.ndarray,
    pred: np.ndarray,
    gt: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    roi_sum = float(roi.sum())
    volume = float(roi.size)
    for class_id, metric_name in PATHOLOGY:
        gt_mask = gt == class_id
        pred_mask = pred == class_id
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.center,
                "modality_group": case.modality_group,
                "t2_present": case.t2_present,
                "class_id": class_id,
                "metric_name": metric_name,
                "roi_voxels": int(roi_sum),
                "roi_fraction": roi_sum / volume if volume else None,
                "gt_voxels": int(gt_mask.sum()),
                "pred_voxels": int(pred_mask.sum()),
                "gt_covered_voxels": int(np.logical_and(roi, gt_mask).sum()),
                "pred_covered_voxels": int(np.logical_and(roi, pred_mask).sum()),
                "gt_roi_coverage": None if not gt_mask.any() else float(np.logical_and(roi, gt_mask).sum() / gt_mask.sum()),
                "pred_roi_coverage": None
                if not pred_mask.any()
                else float(np.logical_and(roi, pred_mask).sum() / pred_mask.sum()),
            }
        )
    return rows


def collect_case_metrics(variant: str, case: CaseInfo, pred: np.ndarray, gt: np.ndarray, gt_img: sitk.Image) -> list[dict[str, Any]]:
    spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
    invalid = sorted(set(np.unique(pred).tolist()) - VALID_LABELS)
    rows: list[dict[str, Any]] = []
    for class_id, metric_name in PATHOLOGY:
        pred_mask = pred == class_id
        gt_mask = gt == class_id
        small_fp, remote_fp = fp_counts(pred_mask, gt_mask)
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.center,
                "modality_group": case.modality_group,
                "t2_present": case.t2_present,
                "class_id": class_id,
                "metric_name": metric_name,
                "dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=False),
                "hd": hd_class(pred, gt, class_id, spacing),
                "hd95": hd95_class(pred, gt, class_id, spacing),
                "component_count": component_count(pred_mask),
                "small_fp_count": small_fp,
                "remote_fp_count": remote_fp,
                "pred_gt_volume_ratio": volume_ratio(pred_mask, gt_mask),
                "pred_empty": not bool(pred_mask.any()),
                "gt_empty": not bool(gt_mask.any()),
                "invalid_label_values": ",".join(str(v) for v in invalid),
            }
        )
    return rows


def summarize_subgroups(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("all_cases", lambda r: True),
        ("gt_positive_only", lambda r: not bool(r["gt_empty"])),
        ("t2_present", lambda r: bool(r["t2_present"])),
        ("complete_modality", lambda r: r["modality_group"] == "C0+LGE+T2"),
        ("CenterB", lambda r: r["center"] == "CenterB"),
        ("CenterC", lambda r: r["center"] == "CenterC"),
        ("LGE-only", lambda r: r["modality_group"] == "LGE-only"),
        ("no_T2_empty_GT", lambda r: (not bool(r["t2_present"])) and bool(r["gt_empty"])),
    ]
    rows: list[dict[str, Any]] = []
    for variant in sorted({str(r["variant"]) for r in case_rows}):
        for class_id, metric_name in PATHOLOGY:
            cls_rows = [r for r in case_rows if r["variant"] == variant and int(r["class_id"]) == class_id]
            for group, pred in groups:
                subset = [r for r in cls_rows if pred(r)]
                if not subset:
                    continue
                rows.append(
                    {
                        "variant": variant,
                        "class_id": class_id,
                        "metric_name": metric_name,
                        "group": group,
                        "n": len(subset),
                        "dice_mean": finite_mean([r["dice"] for r in subset]),
                        "hd_mean": finite_mean([r["hd"] for r in subset]),
                        "hd95_mean": finite_mean([r["hd95"] for r in subset]),
                        "component_count_mean": finite_mean([r["component_count"] for r in subset]),
                        "small_fp_mean": finite_mean([r["small_fp_count"] for r in subset]),
                        "remote_fp_mean": finite_mean([r["remote_fp_count"] for r in subset]),
                        "pred_gt_volume_ratio_mean": finite_mean([r["pred_gt_volume_ratio"] for r in subset]),
                        "empty_prediction_rate": finite_mean([1.0 if r["pred_empty"] else 0.0 for r in subset]),
                    }
                )
    return rows


def compare_to_baseline(subgroup_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    variants = sorted({r["variant"] for r in subgroup_rows if r["variant"] != "baseline_nnunet501_fold0"})
    groups = sorted({r["group"] for r in subgroup_rows})
    keys = (
        "dice_mean",
        "hd_mean",
        "hd95_mean",
        "component_count_mean",
        "small_fp_mean",
        "remote_fp_mean",
        "pred_gt_volume_ratio_mean",
        "empty_prediction_rate",
    )
    for variant in variants:
        for class_id, metric_name in PATHOLOGY:
            for group in groups:
                row: dict[str, Any] = {
                    "variant": variant,
                    "metric_name": metric_name,
                    "class_id": class_id,
                    "group": group,
                }
                for key in keys:
                    b = find_metric(subgroup_rows, "baseline_nnunet501_fold0", class_id, group, key)
                    c = find_metric(subgroup_rows, variant, class_id, group, key)
                    row[f"baseline_{key}"] = b
                    row[f"candidate_{key}"] = c
                    if b is not None and c is not None:
                        if key in {
                            "hd_mean",
                            "hd95_mean",
                            "component_count_mean",
                            "small_fp_mean",
                            "remote_fp_mean",
                            "empty_prediction_rate",
                        }:
                            row[f"delta_{key}_improvement"] = b - c
                        else:
                            row[f"delta_{key}"] = c - b
                out.append(row)
    return out


def find_metric(rows: list[dict[str, Any]], variant: str, class_id: int, group: str, key: str) -> float | None:
    for row in rows:
        if row["variant"] == variant and int(row["class_id"]) == class_id and row["group"] == group:
            return finite_float(row.get(key))
    return None


def decide_variant(variant: str, deltas: list[dict[str, Any]]) -> tuple[str, str]:
    def get(class_id: int, group: str, key: str) -> float:
        for row in deltas:
            if row["variant"] == variant and int(row["class_id"]) == class_id and row["group"] == group:
                val = finite_float(row.get(key))
                return 0.0 if val is None else val
        return 0.0

    scar_dice = get(SCAR, "all_cases", "delta_dice_mean")
    scar_remote = get(SCAR, "all_cases", "delta_remote_fp_mean_improvement")
    scar_hd95 = get(SCAR, "all_cases", "delta_hd95_mean_improvement")
    edema_dice = get(EDEMA, "gt_positive_only", "delta_dice_mean")
    edema_remote = get(EDEMA, "gt_positive_only", "delta_remote_fp_mean_improvement")
    edema_hd95 = get(EDEMA, "gt_positive_only", "delta_hd95_mean_improvement")
    if variant == "myocardium_roi_pathology_refiner" and (scar_hd95 < -0.25 or edema_dice < -0.002):
        return "DIAGNOSTIC_ONLY", "soft ROI route has FP signal but HD95 or edema regression blocks promotion framing"
    if scar_dice >= -0.01 and (scar_remote > 0 or scar_hd95 > 0.1):
        return "DIAGNOSTIC_ONLY", "clean scar secondary signal exists, but fixed postprocessing lacks train/OOF learned-refiner evidence"
    if edema_dice >= -0.01 and (edema_remote > 0 or edema_hd95 > 0.1):
        return "DIAGNOSTIC_ONLY", "clean edema secondary signal exists, but fixed postprocessing lacks train/OOF learned-refiner evidence"
    if scar_dice > 0 or edema_dice > 0 or scar_remote > 0 or edema_remote > 0:
        return "DIAGNOSTIC_ONLY", "some local signal exists but not enough for route promotion"
    return "STOP_NO_CLEAN_ANCHOR_SIGNAL", "no clean same-split nnU-Net improvement"
