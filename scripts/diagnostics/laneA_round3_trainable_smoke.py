#!/usr/bin/env python3
"""Lane A Round3 trainable edema smoke diagnostics.

This is a bounded diagnostic runner. It reads existing Dataset501 labels and
nnU-Net fold0 predictions, then performs class_4 edema loss/gradient and tiny
logit-overfit smoke tests. It does not run nnU-Net training, submit Slurm jobs,
download weights, create validation zips, or modify model artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Callable

import numpy as np
import SimpleITK as sitk
import torch
import torch.nn.functional as F
from scipy.ndimage import binary_erosion, distance_transform_edt, generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class, hd_class


EDEMA = 4
SCAR = 5
N_CLASSES = 6

OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round03_trainable_smoke"
CASE_METRICS = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv"
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)


@dataclass(frozen=True)
class CaseInfo:
    case_id: str
    center: str
    modality_group: str
    t2_present: bool
    edema_gt_positive: bool


@dataclass(frozen=True)
class LossCandidate:
    name: str
    aux_weight: float
    description: str


LOSS_CANDIDATES = [
    LossCandidate("edema_only_weighted_dice_ce", 0.25, "class_4 weighted Dice+BCE auxiliary loss"),
    LossCandidate("edema_focal_tversky", 0.25, "class_4 focal Tversky auxiliary loss"),
    LossCandidate("edema_unified_focal", 0.25, "class_4 unified focal-style auxiliary loss"),
    LossCandidate("edema_surface_or_distance_loss", 0.15, "class_4 boundary/distance auxiliary loss"),
]


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
    if value is None:
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
        if isinstance(value, (int, float)):
            v = float(value)
            if not math.isnan(v) and not math.isinf(v):
                out.append(v)
    return out


def avg(values: list[object]) -> float | None:
    vals = finite(values)
    return float(mean(vals)) if vals else None


def bool_from_csv(value: str) -> bool:
    return value.strip().lower() == "true"


def load_case_pool() -> list[CaseInfo]:
    rows = read_csv(CASE_METRICS)
    infos = []
    for row in rows:
        group = row["modality_group"]
        infos.append(
            CaseInfo(
                case_id=row["case_id"],
                center=row["center"],
                modality_group=group,
                t2_present=group == "C0+LGE+T2",
                edema_gt_positive=bool_from_csv(row["edema_gt_positive"]),
            )
        )
    return infos


def select_smoke_cases(max_cases: int) -> list[CaseInfo]:
    pool = load_case_pool()
    selected: list[CaseInfo] = []

    # Include hard CenterC complete edema cases first, then CenterB complete
    # controls, then no-T2 empty-GT stability monitors.
    preferences = [
        lambda x: x.center == "CenterC" and x.edema_gt_positive,
        lambda x: x.center == "CenterB" and x.edema_gt_positive,
        lambda x: x.modality_group == "C0+LGE" and not x.edema_gt_positive,
        lambda x: x.modality_group == "LGE-only" and not x.edema_gt_positive,
    ]
    per_bucket = max(1, max_cases // len(preferences))
    for pred in preferences:
        matches = [x for x in pool if pred(x)]
        # Sort deterministically; for positive edema, prefer lower baseline Dice
        # when the CSV contains cases in baseline-evidence order.
        for item in matches[:per_bucket]:
            if item.case_id not in {s.case_id for s in selected}:
                selected.append(item)
            if len(selected) >= max_cases:
                return selected

    for item in pool:
        if item.case_id not in {s.case_id for s in selected}:
            selected.append(item)
        if len(selected) >= max_cases:
            break
    return selected


def read_label(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    arr = sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)
    return img, arr


def read_pred_resampled(path: Path, gt_img: sitk.Image) -> np.ndarray:
    pred_img = sitk.ReadImage(str(path))
    if (
        pred_img.GetSize() != gt_img.GetSize()
        or pred_img.GetSpacing() != gt_img.GetSpacing()
        or pred_img.GetOrigin() != gt_img.GetOrigin()
        or pred_img.GetDirection() != gt_img.GetDirection()
    ):
        pred_img = sitk.Resample(pred_img, gt_img, sitk.Transform(), sitk.sitkNearestNeighbor, 0, pred_img.GetPixelID())
    return sitk.GetArrayFromImage(pred_img).astype(np.uint8, copy=False)


def crop_slices(gt: np.ndarray, pred: np.ndarray, patch_shape: tuple[int, int, int]) -> tuple[slice, slice, slice]:
    focus = np.isin(gt, [EDEMA, SCAR, 1, 2, 3]) | np.isin(pred, [EDEMA, SCAR])
    coords = np.argwhere(focus)
    shape = np.array(gt.shape)
    size = np.minimum(np.array(patch_shape), shape)
    if coords.size:
        center = np.round((coords.min(axis=0) + coords.max(axis=0)) / 2.0).astype(int)
    else:
        center = shape // 2
    start = np.maximum(0, center - size // 2)
    end = np.minimum(shape, start + size)
    start = np.maximum(0, end - size)
    return tuple(slice(int(s), int(e)) for s, e in zip(start, end))  # type: ignore[return-value]


def load_case_patch(info: CaseInfo, patch_shape: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray, tuple[float, ...]]:
    gt_img, gt = read_label(GT_DIR / f"{info.case_id}.nii.gz")
    pred = read_pred_resampled(PRED_DIR / f"{info.case_id}.nii.gz", gt_img)
    sl = crop_slices(gt, pred, patch_shape)
    spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
    return gt[sl].copy(), pred[sl].copy(), spacing


def logits_from_prediction(pred: np.ndarray, high: float = 3.0, low: float = -3.0) -> torch.Tensor:
    logits = torch.full((1, N_CLASSES, *pred.shape), low, dtype=torch.float32)
    pred_t = torch.from_numpy(pred.astype(np.int64, copy=False)).unsqueeze(0)
    logits.scatter_(1, pred_t.unsqueeze(1), high)
    return logits


def target_tensor(gt: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(gt.astype(np.int64, copy=False)).unsqueeze(0)


def binary_dice_loss(prob: torch.Tensor, target: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    p = prob.reshape(prob.shape[0], -1)
    g = target.reshape(target.shape[0], -1)
    inter = (p * g).sum(dim=1)
    denom = p.sum(dim=1) + g.sum(dim=1)
    return (1.0 - (2.0 * inter + eps) / (denom + eps)).mean()


def edema_weighted_dice_ce(logits: torch.Tensor, target: torch.Tensor, _: np.ndarray | None = None) -> torch.Tensor:
    logit = logits[:, EDEMA]
    gt = (target == EDEMA).float()
    pos = gt.sum()
    neg = gt.numel() - pos
    pos_weight = torch.clamp(neg / torch.clamp(pos, min=1.0), max=20.0).to(logits.device)
    bce = F.binary_cross_entropy_with_logits(logit, gt, pos_weight=pos_weight)
    dice = binary_dice_loss(torch.sigmoid(logit), gt)
    return 0.5 * bce + 0.5 * dice


def edema_focal_tversky(logits: torch.Tensor, target: torch.Tensor, _: np.ndarray | None = None) -> torch.Tensor:
    prob = torch.sigmoid(logits[:, EDEMA])
    gt = (target == EDEMA).float()
    alpha = 0.7
    beta = 0.3
    gamma = 0.75
    eps = 1e-6
    tp = (prob * gt).sum()
    fp = (prob * (1.0 - gt)).sum()
    fn = ((1.0 - prob) * gt).sum()
    tversky = (tp + eps) / (tp + alpha * fn + beta * fp + eps)
    return torch.pow(1.0 - tversky, gamma)


def edema_unified_focal(logits: torch.Tensor, target: torch.Tensor, _: np.ndarray | None = None) -> torch.Tensor:
    logit = logits[:, EDEMA]
    gt = (target == EDEMA).float()
    prob = torch.sigmoid(logit)
    bce = F.binary_cross_entropy_with_logits(logit, gt, reduction="none")
    pt = prob * gt + (1.0 - prob) * (1.0 - gt)
    focal_bce = (torch.pow(1.0 - pt, 0.5) * bce).mean()
    focal_dice = torch.pow(binary_dice_loss(prob, gt), 0.5)
    return 0.5 * focal_bce + 0.5 * focal_dice


def boundary_weight(gt_edema: np.ndarray) -> np.ndarray:
    if not gt_edema.any():
        return np.zeros_like(gt_edema, dtype=np.float32)
    surface = gt_edema & ~binary_erosion(gt_edema, structure=generate_binary_structure(gt_edema.ndim, 1))
    if not surface.any():
        surface = gt_edema
    dist = distance_transform_edt(~surface)
    weight = 1.0 / (1.0 + dist)
    weight = weight.astype(np.float32, copy=False)
    return 1.0 + weight / max(float(weight.max()), 1e-6)


def edema_surface_or_distance(logits: torch.Tensor, target: torch.Tensor, gt_np: np.ndarray | None = None) -> torch.Tensor:
    logit = logits[:, EDEMA]
    gt = (target == EDEMA).float()
    if gt_np is None or not np.any(gt_np == EDEMA):
        return logit.sum() * 0.0
    weight_np = boundary_weight(gt_np == EDEMA)
    weight = torch.from_numpy(weight_np).to(logits.device).unsqueeze(0)
    bce = F.binary_cross_entropy_with_logits(logit, gt, weight=weight)
    return bce + 0.2 * binary_dice_loss(torch.sigmoid(logit), gt)


LOSS_FNS: dict[str, Callable[[torch.Tensor, torch.Tensor, np.ndarray | None], torch.Tensor]] = {
    "edema_only_weighted_dice_ce": edema_weighted_dice_ce,
    "edema_focal_tversky": edema_focal_tversky,
    "edema_unified_focal": edema_unified_focal,
    "edema_surface_or_distance_loss": edema_surface_or_distance,
}


def grad_norm(tensor: torch.Tensor) -> float:
    return float(torch.linalg.vector_norm(tensor.detach()).cpu().item())


def loss_and_grad_row(candidate: LossCandidate, info: CaseInfo, gt: np.ndarray, pred: np.ndarray) -> dict[str, object]:
    target = target_tensor(gt)
    base_logits = logits_from_prediction(pred).requires_grad_(True)
    base_loss = F.cross_entropy(base_logits, target)
    base_loss.backward()
    base_grad = base_logits.grad.detach().clone()

    logits = logits_from_prediction(pred).requires_grad_(True)
    base = F.cross_entropy(logits, target)
    aux = LOSS_FNS[candidate.name](logits, target, gt)
    total = base + candidate.aux_weight * aux
    total.backward()
    grad = logits.grad.detach()

    nan_or_inf = not (
        torch.isfinite(total).item()
        and torch.isfinite(base).item()
        and torch.isfinite(aux).item()
        and torch.isfinite(grad).all().item()
    )
    class4_norm = grad_norm(grad[:, EDEMA])
    class5_norm = grad_norm(grad[:, SCAR])
    base_class5_norm = grad_norm(base_grad[:, SCAR])
    interference = (class5_norm - base_class5_norm) / max(base_class5_norm, 1e-12)

    empty_gt = not bool(np.any(gt == EDEMA))
    if empty_gt and abs(float(aux.detach().cpu().item())) < 1e-8:
        empty_behavior = "zero_aux_no_background_pressure"
    elif empty_gt:
        empty_behavior = "empty_gt_background_pressure"
    else:
        empty_behavior = "gt_positive_aux_active"

    fail_reasons = []
    if nan_or_inf:
        fail_reasons.append("nan_or_inf")
    if info.edema_gt_positive and class4_norm < 1e-8:
        fail_reasons.append("zero_class4_gradient_on_gt_positive")
    if abs(interference) > 0.2:
        fail_reasons.append("class5_interference_gt_20pct")
    if empty_gt and candidate.name == "edema_surface_or_distance_loss" and abs(float(aux.detach().cpu().item())) > 1e-8:
        fail_reasons.append("surface_loss_nonzero_on_empty_gt")

    return {
        "candidate": candidate.name,
        "case_id": info.case_id,
        "center": info.center,
        "modality_group": info.modality_group,
        "t2_present": info.t2_present,
        "edema_gt_positive": info.edema_gt_positive,
        "loss_value": float(total.detach().cpu().item()),
        "base_loss_value": float(base.detach().cpu().item()),
        "aux_loss_value": float(aux.detach().cpu().item()),
        "total_grad_norm": grad_norm(grad),
        "class4_logit_grad_norm": class4_norm,
        "class5_logit_grad_norm": class5_norm,
        "class5_interference_ratio": float(interference),
        "nan_or_inf": nan_or_inf,
        "empty_gt_behavior": empty_behavior,
        "pass_fail": "fail" if fail_reasons else "pass",
        "fail_reason": ";".join(fail_reasons),
    }


def run_loss_gradient_smoke(cases: list[CaseInfo], patch_shape: tuple[int, int, int]) -> tuple[list[dict[str, object]], dict[str, tuple[np.ndarray, np.ndarray, tuple[float, ...]]]]:
    loaded: dict[str, tuple[np.ndarray, np.ndarray, tuple[float, ...]]] = {}
    rows = []
    for info in cases:
        gt, pred, spacing = load_case_patch(info, patch_shape)
        loaded[info.case_id] = (gt, pred, spacing)
        for candidate in LOSS_CANDIDATES:
            rows.append(loss_and_grad_row(candidate, info, gt, pred))
    return rows, loaded


def strategy_weight(strategy: str, t2_present: bool) -> float:
    if strategy == "report_only":
        return 1.0
    if strategy == "no_t2_edema_loss_masking":
        return 1.0 if t2_present else 0.0
    if strategy == "no_t2_edema_loss_downweighting":
        return 1.0 if t2_present else 0.25
    raise ValueError(strategy)


def run_t2_strategy_smoke(
    cases: list[CaseInfo],
    loaded: dict[str, tuple[np.ndarray, np.ndarray, tuple[float, ...]]],
    candidate: LossCandidate,
) -> list[dict[str, object]]:
    rows = []
    for strategy in ["report_only", "no_t2_edema_loss_masking", "no_t2_edema_loss_downweighting"]:
        for info in cases:
            gt, pred, _ = loaded[info.case_id]
            target = target_tensor(gt)
            weight = strategy_weight(strategy, info.t2_present)
            logits = logits_from_prediction(pred).requires_grad_(True)
            aux = LOSS_FNS[candidate.name](logits, target, gt)
            base = F.cross_entropy(logits, target)
            total = base + candidate.aux_weight * weight * aux
            total.backward()
            grad = logits.grad.detach()
            class4_norm = grad_norm(grad[:, EDEMA])
            class5_norm = grad_norm(grad[:, SCAR])
            nan_or_inf = not (torch.isfinite(total).item() and torch.isfinite(grad).all().item())
            stability = "not_no_t2"
            if not info.t2_present and not info.edema_gt_positive:
                if weight == 0.0:
                    stability = "masked_no_t2_empty_gt_aux"
                elif weight < 1.0:
                    stability = "downweighted_no_t2_empty_gt_aux"
                else:
                    stability = "reported_no_t2_empty_gt_no_strategy_change"
            fail_reasons = []
            if nan_or_inf:
                fail_reasons.append("nan_or_inf")
            if info.edema_gt_positive and class4_norm < 1e-8:
                fail_reasons.append("weak_t2_present_gt_positive_gradient")
            rows.append(
                {
                    "strategy": strategy,
                    "case_id": info.case_id,
                    "center": info.center,
                    "modality_group": info.modality_group,
                    "t2_present": info.t2_present,
                    "edema_gt_positive": info.edema_gt_positive,
                    "edema_loss_weight": weight,
                    "class4_loss_value": float(aux.detach().cpu().item()),
                    "class5_loss_value": float(base.detach().cpu().item()),
                    "class4_grad_norm": class4_norm,
                    "class5_grad_norm": class5_norm,
                    "no_t2_empty_gt_stability": stability,
                    "pass_fail": "fail" if fail_reasons else "pass",
                    "fail_reason": ";".join(fail_reasons),
                }
            )
    return rows


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
    return small_fp, remote_fp


def volume_ratio(pred_mask: np.ndarray, gt_mask: np.ndarray) -> float | None:
    pred_voxels = int(pred_mask.sum())
    gt_voxels = int(gt_mask.sum())
    if gt_voxels == 0:
        return None if pred_voxels == 0 else float("inf")
    return float(pred_voxels / gt_voxels)


def metric_row(pred: np.ndarray, gt: np.ndarray, spacing: tuple[float, ...], cls: int) -> dict[str, object]:
    mask_p = pred == cls
    mask_g = gt == cls
    small_fp, remote_fp = fp_counts(mask_p, mask_g, spacing)
    return {
        "dice": dice_per_class(pred, gt, cls, skip_if_gt_empty=True),
        "hd": hd_class(pred, gt, cls, spacing),
        "hd95": hd95_class(pred, gt, cls, spacing),
        "component_count": component_count(mask_p),
        "small_fp_count": small_fp,
        "remote_fp_count": remote_fp,
        "pred_gt_volume_ratio": volume_ratio(mask_p, mask_g),
    }


def run_tiny_overfit(
    cases: list[CaseInfo],
    loaded: dict[str, tuple[np.ndarray, np.ndarray, tuple[float, ...]]],
    candidate: LossCandidate,
    strategy: str,
    steps: int,
) -> list[dict[str, object]]:
    rows = []
    for info in cases:
        gt, pred, spacing = loaded[info.case_id]
        target = target_tensor(gt)
        weight = strategy_weight(strategy, info.t2_present)
        logits = logits_from_prediction(pred).requires_grad_(True)
        optimizer = torch.optim.Adam([logits], lr=0.35)
        for _ in range(steps):
            optimizer.zero_grad(set_to_none=True)
            base = F.cross_entropy(logits, target)
            aux = LOSS_FNS[candidate.name](logits, target, gt)
            loss = base + candidate.aux_weight * weight * aux
            loss.backward()
            optimizer.step()
        final_pred = torch.argmax(logits.detach(), dim=1).squeeze(0).cpu().numpy().astype(np.uint8)

        edema = metric_row(final_pred, gt, spacing, EDEMA)
        scar = metric_row(final_pred, gt, spacing, SCAR)
        fail_reasons = []
        if info.edema_gt_positive and (edema["dice"] is None or float(edema["dice"]) < 0.8):
            fail_reasons.append("tiny_overfit_edema_dice_below_0p8")
        if scar["dice"] is not None and float(scar["dice"]) < 0.8:
            fail_reasons.append("scar_tiny_overfit_dice_below_0p8")
        if not info.edema_gt_positive and edema["component_count"] != 0:
            fail_reasons.append("no_t2_or_empty_gt_edema_fp")

        rows.append(
            {
                "candidate": candidate.name,
                "strategy": strategy,
                "case_id": info.case_id,
                "center": info.center,
                "modality_group": info.modality_group,
                "t2_present": info.t2_present,
                "edema_gt_positive": info.edema_gt_positive,
                "myops_edema_dice": edema["dice"],
                "myops_edema_hd": edema["hd"],
                "myops_edema_hd95": edema["hd95"],
                "myops_scar_dice": scar["dice"],
                "myops_scar_hd": scar["hd"],
                "myops_scar_hd95": scar["hd95"],
                "edema_component_count": edema["component_count"],
                "edema_small_fp_count": edema["small_fp_count"],
                "edema_remote_fp_count": edema["remote_fp_count"],
                "edema_pred_gt_volume_ratio": edema["pred_gt_volume_ratio"],
                "scar_component_count": scar["component_count"],
                "scar_pred_gt_volume_ratio": scar["pred_gt_volume_ratio"],
                "pass_fail": "fail" if fail_reasons else "pass",
                "fail_reason": ";".join(fail_reasons),
            }
        )
    return rows


def summarize_by(rows: list[dict[str, object]], key: str, value_fields: list[str]) -> list[dict[str, object]]:
    groups: dict[object, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    out = []
    for group, items in sorted(groups.items(), key=lambda x: str(x[0])):
        line: dict[str, object] = {key: group, "n": len(items)}
        for field in value_fields:
            line[field] = avg([item.get(field) for item in items])
        line["fails"] = sum(1 for item in items if item.get("pass_fail") == "fail")
        out.append(line)
    return out


def md_table(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col)) for col in columns) + " |")
    return lines


def write_loss_config(path: Path) -> None:
    lines = [
        "round: laneA_round03",
        "scope: trainable_edema_smoke_only",
        "label_semantics:",
        "  class_4: edema / myops_edema",
        "  class_5: scar / myops_scar",
        "base_loss: multiclass_cross_entropy_on_classes_0_to_5",
        "candidate_losses:",
    ]
    for item in LOSS_CANDIDATES:
        lines += [
            f"  - name: {item.name}",
            f"    aux_weight: {item.aux_weight}",
            f"    description: {item.description}",
            "    scope: class_4_edema_auxiliary_only",
            "    scar_protection: class_5_kept_in_base_loss_and_interference_logged",
        ]
    lines += [
        "t2_aware_strategies:",
        "  - report_only",
        "  - no_t2_edema_loss_masking",
        "  - no_t2_edema_loss_downweighting",
        "forbidden:",
        "  - full_5_fold_training",
        "  - validation_submission",
        "  - external_data",
        "  - pretrained_weight_download",
        "  - large_external_repo_integration",
        "  - foreground_mean_success_metric",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def choose_candidate(rows: list[dict[str, object]]) -> LossCandidate:
    passed = [c for c in LOSS_CANDIDATES if all(r["pass_fail"] == "pass" for r in rows if r["candidate"] == c.name)]
    preferred = ["edema_focal_tversky", "edema_unified_focal", "edema_only_weighted_dice_ce", "edema_surface_or_distance_loss"]
    for name in preferred:
        for cand in passed:
            if cand.name == name:
                return cand
    return passed[0] if passed else LOSS_CANDIDATES[0]


def write_loss_markdown(path: Path, rows: list[dict[str, object]], cases: list[CaseInfo], selected: LossCandidate) -> None:
    summary = summarize_by(
        rows,
        "candidate",
        ["loss_value", "base_loss_value", "aux_loss_value", "class4_logit_grad_norm", "class5_interference_ratio"],
    )
    subgroup_rows = []
    for label_name, pred in [
        ("T2-present GT-positive edema", lambda r: r["t2_present"] is True and r["edema_gt_positive"] is True),
        ("complete-modality edema", lambda r: r["modality_group"] == "C0+LGE+T2" and r["edema_gt_positive"] is True),
        ("CenterC edema", lambda r: r["center"] == "CenterC" and r["edema_gt_positive"] is True),
        ("no-T2 empty-GT stability", lambda r: r["t2_present"] is False and r["edema_gt_positive"] is False),
    ]:
        items = [r for r in rows if pred(r)]
        subgroup_rows.append(
            {
                "subgroup": label_name,
                "n": len(items),
                "mean_class4_grad": avg([x["class4_logit_grad_norm"] for x in items]),
                "mean_class5_interference": avg([x["class5_interference_ratio"] for x in items]),
                "fails": sum(1 for x in items if x["pass_fail"] == "fail"),
            }
        )
    lines = [
        "# Lane A Round3 Edema Loss Gradient Smoke",
        "",
        "| item | value |",
        "| --- | --- |",
        f"| cases | {len(cases)} |",
        "| split/source | Dataset501 fold0 validation cases, existing nnU-Net fold0 predictions as logit initialization |",
        "| label semantics | compact 4=edema/myops_edema, 5=scar/myops_scar |",
        "| training scope | tensor/logit smoke only; no nnU-Net training |",
        "",
        "## Candidate Summary",
        "",
        *md_table(summary, ["candidate", "n", "loss_value", "aux_loss_value", "class4_logit_grad_norm", "class5_interference_ratio", "fails"]),
        "",
        "## Subgroup Summary",
        "",
        *md_table(subgroup_rows, ["subgroup", "n", "mean_class4_grad", "mean_class5_interference", "fails"]),
        "",
        f"Decision: `{selected.name}` may enter tiny-overfit smoke if the T2-aware strategy smoke also passes.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_t2_markdown(path: Path, rows: list[dict[str, object]], selected_strategy: str) -> None:
    summary = summarize_by(rows, "strategy", ["class4_loss_value", "class5_loss_value", "class4_grad_norm", "class5_grad_norm"])
    no_t2 = [r for r in rows if r["t2_present"] is False and r["edema_gt_positive"] is False]
    no_t2_summary = summarize_by(no_t2, "strategy", ["edema_loss_weight", "class4_grad_norm", "class5_grad_norm"])
    lines = [
        "# Lane A Round3 T2-aware Edema Training Strategy Smoke",
        "",
        "This is training-side loss weighting only. It does not add inference suppression.",
        "",
        "## Strategy Summary",
        "",
        *md_table(summary, ["strategy", "n", "class4_loss_value", "class4_grad_norm", "class5_grad_norm", "fails"]),
        "",
        "## no-T2 Empty-GT Stability",
        "",
        *md_table(no_t2_summary, ["strategy", "n", "edema_loss_weight", "class4_grad_norm", "class5_grad_norm", "fails"]),
        "",
        f"Recommendation for tiny-overfit: `{selected_strategy}`.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_decision_table(path: Path, loss_rows: list[dict[str, object]], strategy_rows: list[dict[str, object]], tiny_rows: list[dict[str, object]], selected: LossCandidate, strategy: str) -> str:
    loss_fail = any(r["pass_fail"] == "fail" for r in loss_rows if r["candidate"] == selected.name)
    strategy_fail = any(r["pass_fail"] == "fail" for r in strategy_rows if r["strategy"] == strategy)
    tiny_fail = any(r["pass_fail"] == "fail" for r in tiny_rows)
    if loss_fail:
        decision = "revise_loss_and_repeat_gradient_smoke"
    elif strategy_fail:
        decision = "keep_report_only_t2_strategy"
    elif tiny_fail:
        decision = "revise_loss_and_repeat_gradient_smoke"
    else:
        decision = "advance_to_fold0_short_train"

    rows = [
        {"gate": "loss_gradient_smoke", "selected": selected.name, "pass_fail": "fail" if loss_fail else "pass", "decision": "continue" if not loss_fail else "revise loss"},
        {"gate": "t2_aware_training_strategy_smoke", "selected": strategy, "pass_fail": "fail" if strategy_fail else "pass", "decision": "continue" if not strategy_fail else "fallback report_only"},
        {"gate": "tiny_overfit_or_fold0_short_train_gate", "selected": f"{selected.name}+{strategy}", "pass_fail": "fail" if tiny_fail else "pass", "decision": decision},
    ]
    lines = [
        "# Lane A Round3 Decision Table",
        "",
        *md_table(rows, ["gate", "selected", "pass_fail", "decision"]),
        "",
        f"Final decision: `{decision}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return decision


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Lane A Round3 bounded edema trainable smoke diagnostics.")
    parser.add_argument("--max-cases", type=int, default=8)
    parser.add_argument("--patch-shape", type=str, default="16,96,96")
    parser.add_argument("--tiny-steps", type=int, default=40)
    args = parser.parse_args()

    patch_shape = tuple(int(x) for x in args.patch_shape.split(","))
    if len(patch_shape) != 3:
        raise ValueError("--patch-shape must be z,y,x")

    torch.manual_seed(42)
    np.random.seed(42)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    cases = select_smoke_cases(args.max_cases)
    if not cases:
        raise RuntimeError("No smoke cases selected.")

    write_loss_config(OUT_ROOT / "loss_config_candidates.yaml")
    loss_rows, loaded = run_loss_gradient_smoke(cases, patch_shape)
    loss_fields = [
        "candidate",
        "case_id",
        "center",
        "modality_group",
        "t2_present",
        "edema_gt_positive",
        "loss_value",
        "base_loss_value",
        "aux_loss_value",
        "total_grad_norm",
        "class4_logit_grad_norm",
        "class5_logit_grad_norm",
        "class5_interference_ratio",
        "nan_or_inf",
        "empty_gt_behavior",
        "pass_fail",
        "fail_reason",
    ]
    write_csv(OUT_ROOT / "edema_loss_gradient_smoke.csv", loss_rows, loss_fields)
    selected_candidate = choose_candidate(loss_rows)
    write_loss_markdown(OUT_ROOT / "edema_loss_gradient_smoke.md", loss_rows, cases, selected_candidate)

    strategy_rows = run_t2_strategy_smoke(cases, loaded, selected_candidate)
    strategy_fields = [
        "strategy",
        "case_id",
        "center",
        "modality_group",
        "t2_present",
        "edema_gt_positive",
        "edema_loss_weight",
        "class4_loss_value",
        "class5_loss_value",
        "class4_grad_norm",
        "class5_grad_norm",
        "no_t2_empty_gt_stability",
        "pass_fail",
        "fail_reason",
    ]
    write_csv(OUT_ROOT / "t2_aware_training_strategy_smoke.csv", strategy_rows, strategy_fields)
    selected_strategy = "no_t2_edema_loss_downweighting"
    if any(r["pass_fail"] == "fail" for r in strategy_rows if r["strategy"] == selected_strategy):
        selected_strategy = "report_only"
    write_t2_markdown(OUT_ROOT / "t2_aware_training_strategy_smoke.md", strategy_rows, selected_strategy)

    tiny_rows = run_tiny_overfit(cases, loaded, selected_candidate, selected_strategy, args.tiny_steps)
    tiny_fields = [
        "candidate",
        "strategy",
        "case_id",
        "center",
        "modality_group",
        "t2_present",
        "edema_gt_positive",
        "myops_edema_dice",
        "myops_edema_hd",
        "myops_edema_hd95",
        "myops_scar_dice",
        "myops_scar_hd",
        "myops_scar_hd95",
        "edema_component_count",
        "edema_small_fp_count",
        "edema_remote_fp_count",
        "edema_pred_gt_volume_ratio",
        "scar_component_count",
        "scar_pred_gt_volume_ratio",
        "pass_fail",
        "fail_reason",
    ]
    write_csv(OUT_ROOT / "tiny_overfit_case_table.csv", tiny_rows, tiny_fields)

    decision = write_decision_table(
        OUT_ROOT / "round3_laneA_decision_table.md",
        loss_rows,
        strategy_rows,
        tiny_rows,
        selected_candidate,
        selected_strategy,
    )

    manifest = {
        "scope": "Lane A Round3 bounded trainable edema smoke",
        "cases": [case.__dict__ for case in cases],
        "patch_shape_zyx": patch_shape,
        "tiny_steps": args.tiny_steps,
        "selected_candidate": selected_candidate.name,
        "selected_strategy": selected_strategy,
        "decision": decision,
        "forbidden_actions_avoided": [
            "full_5_fold_training",
            "slurm_submission",
            "validation_zip",
            "pretrained_weight_download",
            "external_data",
            "large_external_repo_integration",
        ],
    }
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote Lane A Round3 smoke outputs to {OUT_ROOT}")
    print(f"Selected candidate: {selected_candidate.name}")
    print(f"Selected strategy: {selected_strategy}")
    print(f"Decision: {decision}")


if __name__ == "__main__":
    main()
