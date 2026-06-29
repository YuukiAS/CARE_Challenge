#!/usr/bin/env python3
"""Task-scoped fold0 runner for SRR-MyoPS variants."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk
import torch
from scipy.ndimage import generate_binary_structure, label
from torch import nn


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class, hd_class
from src.care_myocardium.data.case_metadata import MyoPSCaseMetadata, load_myops_case_metadata
from src.care_myocardium.losses.srr_losses import srr_total_loss
from src.care_myocardium.models.srr_myops import ConditionalDualHeadControl, SRRMyoPSLite


RAW_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS"
SPLIT_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
DEFAULT_OUT_ROOT = REPO_ROOT / "results/20260621_srr_fold0"
IGNORE_LABEL = -1
DICTIONARY_BANK_VARIANTS = {
    "multiscale_dictionary",
    "task_specific_dictionary",
    "cross_modal_interaction_dictionary",
    "anchor_guided_dictionary",
    "hierarchical_router_dictionary",
}
LESION_COMPACT_VARIANTS = {
    "soft_anatomy_containment",
    "component_compactness_loss",
    "scar_lge_fallback_boost",
    "edema_t2_center_balance",
}
PROPOSAL_VARIANTS = {
    "proposal_pos_neg_basic",
    "proposal_anatomy_distance",
    "proposal_uncertainty_gate",
    "proposal_hard_negative_replay_preflight",
}
LESION_BASE_DICTIONARY = "cross_modal_interaction_dictionary"


@dataclass
class CaseData:
    case_id: str
    image: np.ndarray
    label_arr: np.ndarray
    label_img: sitk.Image
    availability: np.ndarray
    metadata: MyoPSCaseMetadata


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_checkpoint_atomic(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    torch.save(payload, tmp_path)
    tmp_path.replace(path)


def load_split(fold: int) -> tuple[list[str], list[str]]:
    data = json.loads(SPLIT_JSON.read_text(encoding="utf-8"))
    split = data["folds"][fold]
    return list(split["train"]), list(split["val"])


def normalize_channel(arr: np.ndarray, present: bool) -> np.ndarray:
    arr = arr.astype(np.float32, copy=False)
    if not present:
        return np.zeros_like(arr, dtype=np.float32)
    mask = np.abs(arr) > 1e-6
    if not np.any(mask):
        return np.zeros_like(arr, dtype=np.float32)
    values = arr[mask]
    lo, hi = np.percentile(values, [0.5, 99.5])
    arr = np.clip(arr, lo, hi)
    mean_v = float(arr[mask].mean())
    std_v = float(arr[mask].std())
    if std_v < 1e-6:
        std_v = 1.0
    arr = (arr - mean_v) / std_v
    arr[~mask] = 0.0
    return arr.astype(np.float32, copy=False)


def read_case(case_id: str, metadata: dict[str, MyoPSCaseMetadata]) -> CaseData:
    meta = metadata[case_id]
    arrays = []
    for idx, present in enumerate(meta.availability):
        img = sitk.ReadImage(str(RAW_ROOT / "imagesTr" / f"{case_id}_{idx:04d}.nii.gz"))
        arrays.append(normalize_channel(sitk.GetArrayFromImage(img), bool(present)))
    label_img = sitk.ReadImage(str(RAW_ROOT / "labelsTr" / f"{case_id}.nii.gz"))
    label_arr = sitk.GetArrayFromImage(label_img).astype(np.int64, copy=False)
    return CaseData(
        case_id=case_id,
        image=np.stack(arrays, axis=0),
        label_arr=label_arr,
        label_img=label_img,
        availability=np.asarray(meta.availability, dtype=np.float32),
        metadata=meta,
    )


def crop_or_pad(array: np.ndarray, starts: tuple[int, int, int], patch_shape: tuple[int, int, int], pad_value: float | int) -> np.ndarray:
    slices = []
    pads = []
    for start, size, dim in zip(starts, patch_shape, array.shape[-3:]):
        lo = max(0, start)
        hi = min(dim, start + size)
        slices.append(slice(lo, hi))
        pads.append((max(0, -start), max(0, start + size - dim)))
    cropped = array[(..., *slices)]
    return np.pad(cropped, [(0, 0)] * (array.ndim - 3) + pads, mode="constant", constant_values=pad_value)


def sample_patch(
    case: CaseData,
    patch_shape: tuple[int, int, int],
    rng: np.random.Generator,
    oversample_foreground: float,
    modality_dropout: bool,
    focus_classes: tuple[int, ...] = (4, 5),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    label_arr = case.label_arr
    focus = np.argwhere(np.isin(label_arr, focus_classes))
    if len(focus) and rng.random() < oversample_foreground:
        center = focus[int(rng.integers(0, len(focus)))]
    else:
        valid = np.argwhere(label_arr >= 0)
        center = valid[int(rng.integers(0, len(valid)))] if len(valid) else np.asarray(label_arr.shape) // 2
    starts = tuple(int(c - p // 2) for c, p in zip(center, patch_shape))
    image = crop_or_pad(case.image, starts, patch_shape, 0.0).astype(np.float32, copy=False)
    target = crop_or_pad(label_arr[None], starts, patch_shape, IGNORE_LABEL).astype(np.int64, copy=False)[0]
    availability = case.availability.copy()
    if modality_dropout:
        # Preserve LGE. Drop T2/C0 only when originally present; dropped T2 also
        # disables edema dense loss through the availability vector.
        if availability[1] > 0 and rng.random() < 0.15:
            availability[1] = 0.0
            image[1] = 0.0
        if availability[2] > 0 and rng.random() < 0.15:
            availability[2] = 0.0
            image[2] = 0.0
    return image, target, availability


def parse_shape(text: str) -> tuple[int, int, int]:
    parts = [int(x) for x in text.lower().replace(",", "x").split("x") if x]
    if len(parts) != 3:
        raise ValueError(f"expected Dz,Y,X patch shape, got {text!r}")
    return tuple(parts)  # type: ignore[return-value]


def dictionary_mode_for_variant(variant: str) -> str:
    if variant in DICTIONARY_BANK_VARIANTS:
        return variant
    if variant in LESION_COMPACT_VARIANTS or variant in PROPOSAL_VARIANTS:
        return LESION_BASE_DICTIONARY
    return "standard"


def proposal_mode_for_variant(variant: str) -> str:
    if variant in PROPOSAL_VARIANTS:
        if variant == "proposal_pos_neg_basic":
            return "proposal_pos_neg_basic"
        if variant == "proposal_anatomy_distance":
            return "proposal_anatomy_distance"
        if variant == "proposal_uncertainty_gate":
            return "proposal_uncertainty_gate"
        if variant == "proposal_hard_negative_replay_preflight":
            return "proposal_uncertainty_gate"
    return "none"


def variant_router_settings(args: argparse.Namespace) -> tuple[dict[str, float], float]:
    temperature = float(args.router_temperature)
    dropout = float(args.expert_dropout)
    temps = {"anatomy": temperature, "scar": temperature, "edema": temperature}
    if args.variant == "srr_soft_entropy":
        temps = {"anatomy": 2.0, "scar": 1.8, "edema": 2.0}
    elif args.variant == "srr_expert_dropout":
        temps = {"anatomy": 1.6, "scar": 1.4, "edema": 1.8}
        dropout = 0.25 if args.expert_dropout == 0 else dropout
    elif args.variant == "srr_task_tempered":
        temps = {"anatomy": 2.2, "scar": 1.25, "edema": 2.4}
    elif args.variant == "retrieval_no_sip_or_weak_sip":
        temps = {"anatomy": 1.4, "scar": 1.25, "edema": 1.5}
    elif args.variant == "multiscale_dictionary":
        temps = {"anatomy": 1.7, "scar": 1.45, "edema": 1.9}
        dropout = 0.20 if args.expert_dropout == 0 else dropout
    elif args.variant == "task_specific_dictionary":
        temps = {"anatomy": 1.6, "scar": 1.35, "edema": 1.7}
        dropout = 0.20 if args.expert_dropout == 0 else dropout
    elif args.variant == "cross_modal_interaction_dictionary":
        temps = {"anatomy": 1.8, "scar": 1.45, "edema": 1.9}
        dropout = 0.20 if args.expert_dropout == 0 else dropout
    elif args.variant == "anchor_guided_dictionary":
        temps = {"anatomy": 1.5, "scar": 1.25, "edema": 1.5}
        dropout = 0.15 if args.expert_dropout == 0 else dropout
    elif args.variant == "hierarchical_router_dictionary":
        temps = {"anatomy": 1.8, "scar": 1.55, "edema": 2.0}
        dropout = 0.20 if args.expert_dropout == 0 else dropout
    elif args.variant == "soft_anatomy_containment":
        temps = {"anatomy": 1.8, "scar": 1.45, "edema": 1.9}
        dropout = 0.20 if args.expert_dropout == 0 else dropout
    elif args.variant == "component_compactness_loss":
        temps = {"anatomy": 1.8, "scar": 1.45, "edema": 1.9}
        dropout = 0.20 if args.expert_dropout == 0 else dropout
    elif args.variant == "scar_lge_fallback_boost":
        temps = {"anatomy": 1.7, "scar": 1.25, "edema": 1.9}
        dropout = 0.20 if args.expert_dropout == 0 else dropout
    elif args.variant == "edema_t2_center_balance":
        temps = {"anatomy": 1.8, "scar": 1.45, "edema": 2.1}
        dropout = 0.20 if args.expert_dropout == 0 else dropout
    elif args.variant in PROPOSAL_VARIANTS:
        temps = {"anatomy": 1.8, "scar": 1.35, "edema": 1.75}
        dropout = 0.20 if args.expert_dropout == 0 else dropout
    if args.anatomy_router_temperature is not None:
        temps["anatomy"] = float(args.anatomy_router_temperature)
    if args.scar_router_temperature is not None:
        temps["scar"] = float(args.scar_router_temperature)
    if args.edema_router_temperature is not None:
        temps["edema"] = float(args.edema_router_temperature)
    return temps, dropout


def make_model(args: argparse.Namespace, device: torch.device) -> nn.Module:
    variant = args.variant
    if variant == "conditional_dualhead_control":
        model: nn.Module = ConditionalDualHeadControl(base_channels=args.base_channels)
    elif variant == "late_fusion_no_dictionary":
        model = ConditionalDualHeadControl(base_channels=args.base_channels)
    elif variant in {"srr_minimal", "srr_soft_entropy", "srr_expert_dropout", "srr_task_tempered", "retrieval_no_sip_or_weak_sip"}:
        temps, dropout = variant_router_settings(args)
        model = SRRMyoPSLite(base_channels=args.base_channels, router_temperatures=temps, expert_dropout=dropout)
    elif variant in DICTIONARY_BANK_VARIANTS or variant in LESION_COMPACT_VARIANTS or variant in PROPOSAL_VARIANTS:
        temps, dropout = variant_router_settings(args)
        dictionary_mode = dictionary_mode_for_variant(variant)
        model = SRRMyoPSLite(
            base_channels=args.base_channels,
            router_temperatures=temps,
            expert_dropout=dropout,
            dictionary_mode=dictionary_mode,
            proposal_mode=proposal_mode_for_variant(variant),
        )
    else:
        raise ValueError(f"unknown variant {variant}")
    return model.to(device)


def retrieval_config_from_args(args: argparse.Namespace) -> dict[str, float]:
    return {
        "entropy_floor": float(args.retrieval_entropy_floor),
        "entropy_weight": float(args.retrieval_entropy_weight),
        "coverage_weight": float(args.retrieval_coverage_weight),
        "max_weight_penalty": float(args.retrieval_max_weight_penalty),
    }


def loss_weights_from_args(args: argparse.Namespace) -> dict[str, float]:
    return {
        "anatomy": float(args.anatomy_weight),
        "scar": float(args.scar_weight),
        "edema": float(args.edema_weight),
        "prior": float(args.prior_weight),
        "retrieval": float(args.retrieval_weight),
    }


def _tv3d(prob: torch.Tensor) -> torch.Tensor:
    dz = torch.abs(prob[:, :, 1:] - prob[:, :, :-1]).mean()
    dy = torch.abs(prob[:, :, :, 1:] - prob[:, :, :, :-1]).mean()
    dx = torch.abs(prob[:, :, :, :, 1:] - prob[:, :, :, :, :-1]).mean()
    return (dz + dy + dx) / 3.0


def lesion_auxiliary_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    availability: torch.Tensor,
    args: argparse.Namespace,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    zero = outputs["logits"].sum() * 0.0
    metrics: dict[str, torch.Tensor] = {
        "soft_containment": zero.detach(),
        "component_compactness": zero.detach(),
        "proposal_bce": zero.detach(),
        "proposal_margin": zero.detach(),
        "proposal_uncertainty": zero.detach(),
    }
    total = zero
    scar_prob = torch.sigmoid(outputs["scar_logits"][:, 0])
    edema_prob = torch.sigmoid(outputs["edema_logits"][:, 0])
    t2_present = availability[:, 1].to(device=labels.device, dtype=scar_prob.dtype).view(-1, 1, 1, 1)

    if args.variant == "soft_anatomy_containment" and args.containment_weight > 0:
        union_target = ((labels > 0) & (labels != IGNORE_LABEL)).to(dtype=scar_prob.dtype)
        outside_union = 1.0 - union_target
        scar_outside = (scar_prob * outside_union).mean()
        edema_denom = (outside_union * t2_present).sum().clamp_min(1.0)
        edema_outside = (edema_prob * outside_union * t2_present).sum() / edema_denom
        containment = 0.5 * scar_outside + 0.5 * edema_outside
        total = total + float(args.containment_weight) * containment
        metrics["soft_containment"] = containment.detach()

    if args.variant == "component_compactness_loss" and args.compactness_weight > 0:
        scar_tv = _tv3d(scar_prob[:, None])
        edema_tv = _tv3d(edema_prob[:, None] * t2_present[:, None])
        compactness = 0.5 * scar_tv + 0.5 * edema_tv
        total = total + float(args.compactness_weight) * compactness
        metrics["component_compactness"] = compactness.detach()

    if args.variant in PROPOSAL_VARIANTS and "scar_proposal_logits" in outputs:
        proposal_loss, proposal_metrics = proposal_auxiliary_loss(outputs, labels, availability, args)
        total = total + proposal_loss
        metrics.update(proposal_metrics)

    return total, metrics


def _masked_mean(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    mask = mask.to(device=values.device, dtype=values.dtype)
    return (values * mask).sum() / mask.sum().clamp_min(1.0)


def _proposal_bce_dice(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    target_f = target.to(device=logits.device, dtype=logits.dtype)
    mask_f = mask.to(device=logits.device, dtype=logits.dtype)
    bce = torch.nn.functional.binary_cross_entropy_with_logits(logits, target_f, reduction="none")
    bce = _masked_mean(bce, mask_f)
    prob = torch.sigmoid(logits)
    axes = tuple(range(1, prob.ndim))
    inter = (prob * target_f * mask_f).sum(dim=axes)
    denom = (prob * mask_f).sum(dim=axes) + (target_f * mask_f).sum(dim=axes)
    dice = (1.0 - (2.0 * inter + 1e-6) / (denom + 1e-6)).mean()
    return 0.5 * bce + 0.5 * dice


def proposal_auxiliary_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    availability: torch.Tensor,
    args: argparse.Namespace,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    zero = outputs["logits"].sum() * 0.0
    valid = labels != IGNORE_LABEL
    t2_present = availability[:, 1].to(device=labels.device, dtype=torch.bool).view(-1, 1, 1, 1)
    scar_target = labels == 5
    edema_target = labels == 4

    scar_bce = _proposal_bce_dice(outputs["scar_proposal_logits"][:, 0], scar_target, valid)
    edema_dense_mask = valid & t2_present
    edema_bce = (
        _proposal_bce_dice(outputs["edema_proposal_logits"][:, 0], edema_target, edema_dense_mask)
        if bool(edema_dense_mask.any())
        else zero
    )

    scar_pos = scar_target & valid
    scar_safe_neg = (~scar_target) & valid
    edema_pos = edema_target & valid & t2_present
    # On no-T2 cases, only true background is a safe edema negative; myocardium
    # and scar voxels are intentionally excluded from edema hard negatives.
    edema_safe_neg = ((~edema_target) & valid & t2_present) | ((labels == 0) & valid & (~t2_present))

    margin_terms = []
    margin = float(args.proposal_margin)
    for prefix, pos_mask, neg_mask in [
        ("scar", scar_pos, scar_safe_neg),
        ("edema", edema_pos, edema_safe_neg),
    ]:
        pos_sim = outputs[f"{prefix}_pos_similarity"][:, 0]
        neg_sim = outputs[f"{prefix}_neg_similarity"][:, 0]
        if bool(pos_mask.any()):
            margin_terms.append(_masked_mean(torch.relu(margin - pos_sim + neg_sim), pos_mask))
        if bool(neg_mask.any()):
            margin_terms.append(_masked_mean(torch.relu(margin + pos_sim - neg_sim), neg_mask))
    margin_loss = torch.stack(margin_terms).mean() if margin_terms else zero

    uncertainty_loss = zero
    if args.variant == "proposal_uncertainty_gate" or args.variant == "proposal_hard_negative_replay_preflight":
        scar_unc = outputs["scar_uncertainty"][:, 0]
        edema_unc = outputs["edema_uncertainty"][:, 0]
        confident_mask = scar_pos | edema_pos
        safe_bg = (labels == 0) & valid
        if bool(confident_mask.any()):
            uncertainty_loss = uncertainty_loss + _masked_mean(scar_unc + edema_unc, confident_mask)
        if bool(safe_bg.any()):
            uncertainty_loss = uncertainty_loss + 0.25 * _masked_mean((1.0 - scar_unc) + (1.0 - edema_unc), safe_bg)

    total = (
        float(args.proposal_bce_weight) * (0.5 * scar_bce + 0.5 * edema_bce)
        + float(args.proposal_margin_weight) * margin_loss
        + float(args.proposal_uncertainty_weight) * uncertainty_loss
    )
    metrics = {
        "proposal_bce": (0.5 * scar_bce + 0.5 * edema_bce).detach(),
        "proposal_margin": margin_loss.detach(),
        "proposal_uncertainty": uncertainty_loss.detach(),
    }
    return total, metrics


def has_label(case: CaseData, class_id: int) -> bool:
    return bool(np.any(case.label_arr == class_id))


def batch_from_cases(
    cases: list[CaseData],
    complete_cases: list[CaseData],
    scar_cases: list[CaseData],
    lge_only_scar_cases: list[CaseData],
    edema_t2_cases: list[CaseData],
    center_c_t2_edema_cases: list[CaseData],
    batch_size: int,
    patch_shape: tuple[int, int, int],
    rng: np.random.Generator,
    complete_oversample: float,
    oversample_foreground: float,
    modality_dropout: bool,
    lesion_mode: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[str]]:
    xs, ys, avs, keys = [], [], [], []
    for _ in range(batch_size):
        focus_classes = (4, 5)
        effective_oversample = oversample_foreground
        if lesion_mode == "scar_lge_fallback_boost":
            draw = rng.random()
            if lge_only_scar_cases and draw < 0.40:
                pool = lge_only_scar_cases
            elif scar_cases and draw < 0.85:
                pool = scar_cases
            else:
                pool = complete_cases if complete_cases and rng.random() < complete_oversample else cases
            focus_classes = (5,)
            effective_oversample = max(oversample_foreground, 0.90)
        elif lesion_mode == "edema_t2_center_balance":
            draw = rng.random()
            if center_c_t2_edema_cases and draw < 0.45:
                pool = center_c_t2_edema_cases
            elif edema_t2_cases and draw < 0.85:
                pool = edema_t2_cases
            else:
                pool = complete_cases if complete_cases and rng.random() < complete_oversample else cases
            focus_classes = (4,)
            effective_oversample = max(oversample_foreground, 0.90)
        else:
            pool = complete_cases if complete_cases and rng.random() < complete_oversample else cases
        case = pool[int(rng.integers(0, len(pool)))]
        x, y, av = sample_patch(case, patch_shape, rng, effective_oversample, modality_dropout, focus_classes=focus_classes)
        xs.append(x)
        ys.append(y)
        avs.append(av)
        keys.append(case.case_id)
    return (
        torch.from_numpy(np.stack(xs, axis=0)).float(),
        torch.from_numpy(np.stack(ys, axis=0)).long(),
        torch.from_numpy(np.stack(avs, axis=0)).float(),
        keys,
    )


def finite_mean(values: list[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None and not math.isnan(float(v)) and not math.isinf(float(v))]
    return float(mean(vals)) if vals else None


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def volume_ratio(pred: np.ndarray, gt: np.ndarray) -> float | None:
    p = int(pred.sum())
    g = int(gt.sum())
    if g == 0:
        return None if p == 0 else float("inf")
    return float(p / g)


def fp_counts(pred_mask: np.ndarray, gt_mask: np.ndarray, small_threshold: int = 20) -> tuple[int, int]:
    cc, n_cc = label(pred_mask.astype(bool), structure=generate_binary_structure(pred_mask.ndim, 1))
    small_fp = 0
    remote_fp = 0
    gt_coords = np.argwhere(gt_mask)
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


def predict_full_case(model: nn.Module, case: CaseData, device: torch.device) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(case.image[None]).float().to(device)
        av = torch.from_numpy(case.availability[None]).float().to(device)
        outputs = model(x, av)
        pred = torch.argmax(outputs["logits"], dim=1)[0].detach().cpu().numpy().astype(np.uint8)
        aux: dict[str, np.ndarray] = {}
        for key in (
            "scar_proposal_logits",
            "edema_proposal_logits",
            "scar_pos_similarity",
            "scar_neg_similarity",
            "edema_pos_similarity",
            "edema_neg_similarity",
            "scar_uncertainty",
            "edema_uncertainty",
            "local_anatomy_confidence",
        ):
            value = outputs.get(key)
            if isinstance(value, torch.Tensor):
                aux[key] = value[0, 0].detach().cpu().numpy()
    return pred, aux


def write_prediction(path: Path, pred: np.ndarray, reference: sitk.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(pred)
    img.CopyInformation(reference)
    sitk.WriteImage(img, str(path))


def collect_case_metrics(variant: str, case: CaseData, pred: np.ndarray) -> list[dict[str, object]]:
    gt = case.label_arr.astype(np.uint8, copy=False)
    invalid = sorted(set(np.unique(pred).tolist()) - {0, 1, 2, 3, 4, 5})
    spacing = tuple(float(x) for x in case.label_img.GetSpacing()[::-1])
    rows = []
    for cls, name in [(4, "myops_edema"), (5, "myops_scar")]:
        pred_mask = pred == cls
        gt_mask = gt == cls
        small_fp, remote_fp = fp_counts(pred_mask, gt_mask)
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": case.metadata.t2_present,
                "class_id": cls,
                "metric_name": name,
                "dice": dice_per_class(pred, gt, cls, skip_if_gt_empty=False),
                "hd": hd_class(pred, gt, cls, spacing),
                "hd95": hd95_class(pred, gt, cls, spacing),
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


def collect_proposal_metrics(
    variant: str,
    case: CaseData,
    aux: dict[str, np.ndarray],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if "scar_proposal_logits" not in aux:
        return [], []
    gt = case.label_arr.astype(np.uint8, copy=False)
    rows: list[dict[str, object]] = []
    usage_rows: list[dict[str, object]] = []
    for cls, name, prefix in [(4, "myops_edema", "edema"), (5, "myops_scar", "scar")]:
        logits = aux[f"{prefix}_proposal_logits"]
        gate = 1.0 / (1.0 + np.exp(-logits))
        proposal = gate >= 0.50
        gt_mask = gt == cls
        inter = int(np.logical_and(proposal, gt_mask).sum())
        proposal_vox = int(proposal.sum())
        gt_vox = int(gt_mask.sum())
        small_fp, remote_fp = fp_counts(proposal, gt_mask)
        outside_union_fp = int(np.logical_and(proposal, gt == 0).sum())
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": case.metadata.t2_present,
                "class_id": cls,
                "metric_name": name,
                "proposal_threshold": 0.50,
                "proposal_recall": None if gt_vox == 0 else inter / max(1, gt_vox),
                "proposal_precision": None if proposal_vox == 0 else inter / max(1, proposal_vox),
                "proposal_voxels": proposal_vox,
                "gt_voxels": gt_vox,
                "proposal_component_count": component_count(proposal),
                "proposal_small_fp_count": small_fp,
                "proposal_remote_fp_count": remote_fp,
                "proposal_outside_union_fp_voxels": outside_union_fp,
                "proposal_gate_mean": float(gate.mean()),
                "proposal_gate_p95": float(np.percentile(gate, 95)),
                "uncertainty_mean": float(aux.get(f"{prefix}_uncertainty", np.zeros_like(gate)).mean()),
                "local_anatomy_confidence_mean": float(aux.get("local_anatomy_confidence", np.zeros_like(gate)).mean()),
            }
        )
        usage_rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "task": prefix,
                "pos_similarity_mean": float(aux[f"{prefix}_pos_similarity"].mean()),
                "neg_similarity_mean": float(aux[f"{prefix}_neg_similarity"].mean()),
                "pos_minus_neg_mean": float((aux[f"{prefix}_pos_similarity"] - aux[f"{prefix}_neg_similarity"]).mean()),
                "proposal_gate_mean": float(gate.mean()),
                "proposal_gate_p95": float(np.percentile(gate, 95)),
                "uncertainty_mean": float(aux.get(f"{prefix}_uncertainty", np.zeros_like(gate)).mean()),
            }
        )
    return rows, usage_rows


def summarize_subgroups(variant: str, case_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    groups: list[tuple[str, callable]] = [
        ("all_cases", lambda r: True),
        ("gt_positive_only", lambda r: not bool(r["gt_empty"])),
        ("t2_present", lambda r: bool(r["t2_present"])),
        ("complete_modality", lambda r: r["modality_group"] == "C0+LGE+T2"),
        ("CenterB", lambda r: r["center"] == "CenterB"),
        ("CenterC", lambda r: r["center"] == "CenterC"),
        ("C0+LGE", lambda r: r["modality_group"] == "C0+LGE"),
        ("LGE-only", lambda r: r["modality_group"] == "LGE-only"),
        ("no_T2_empty_GT", lambda r: (not bool(r["t2_present"])) and bool(r["gt_empty"])),
    ]
    for cls, name in [(4, "myops_edema"), (5, "myops_scar")]:
        cls_rows = [r for r in case_rows if int(r["class_id"]) == cls]
        for group_name, pred in groups:
            subset = [r for r in cls_rows if pred(r)]
            if not subset:
                continue
            rows.append(
                {
                    "variant": variant,
                    "class_id": cls,
                    "metric_name": name,
                    "group": group_name,
                    "n": len(subset),
                    "dice_mean": finite_mean([r["dice"] for r in subset]),  # type: ignore[list-item]
                    "hd_mean": finite_mean([r["hd"] for r in subset]),  # type: ignore[list-item]
                    "hd95_mean": finite_mean([r["hd95"] for r in subset]),  # type: ignore[list-item]
                    "component_count_mean": finite_mean([float(r["component_count"]) for r in subset]),
                    "remote_fp_mean": finite_mean([float(r["remote_fp_count"]) for r in subset]),
                    "empty_prediction_rate": finite_mean([1.0 if r["pred_empty"] else 0.0 for r in subset]),
                }
            )
    return rows


def evaluate_and_export(model: nn.Module, cases: list[CaseData], variant_dir: Path, variant: str, device: torch.device) -> None:
    pred_dir = variant_dir / "predictions/fold_0/checkpoint_best"
    case_rows: list[dict[str, object]] = []
    proposal_rows: list[dict[str, object]] = []
    prototype_rows: list[dict[str, object]] = []
    for case in cases:
        pred, aux = predict_full_case(model, case, device)
        write_prediction(pred_dir / f"{case.case_id}.nii.gz", pred, case.label_img)
        case_rows.extend(collect_case_metrics(variant, case, pred))
        p_rows, u_rows = collect_proposal_metrics(variant, case, aux)
        proposal_rows.extend(p_rows)
        prototype_rows.extend(u_rows)
    write_csv(variant_dir / "component_hd_by_case.csv", case_rows)
    write_csv(variant_dir / "subgroup_metrics.csv", summarize_subgroups(variant, case_rows))
    if proposal_rows:
        write_csv(variant_dir / "proposal_metrics.csv", proposal_rows)
    if prototype_rows:
        write_csv(variant_dir / "prototype_usage.csv", prototype_rows)


def validate_patch_loss(
    model: nn.Module,
    val_cases: list[CaseData],
    patch_shape: tuple[int, int, int],
    device: torch.device,
    seed: int,
    weights: dict[str, float],
    retrieval_config: dict[str, float],
    args: argparse.Namespace,
) -> float:
    rng = np.random.default_rng(seed)
    model.eval()
    losses = []
    with torch.no_grad():
        for case in val_cases[: min(12, len(val_cases))]:
            x_np, y_np, av_np = sample_patch(case, patch_shape, rng, oversample_foreground=1.0, modality_dropout=False)
            x = torch.from_numpy(x_np[None]).float().to(device)
            y = torch.from_numpy(y_np[None]).long().to(device)
            av = torch.from_numpy(av_np[None]).float().to(device)
            outputs = model(x, av)
            loss, _ = srr_total_loss(outputs, y, av, weights=weights, retrieval_config=retrieval_config)
            aux_loss, _ = lesion_auxiliary_loss(outputs, y, av, args)
            loss = loss + aux_loss
            losses.append(float(loss.detach().cpu()))
    model.train()
    return float(mean(losses)) if losses else float("inf")


def record_gate_usage(rows: list[dict[str, object]], variant: str, step: int, keys: list[str], outputs: dict[str, object]) -> None:
    gates = outputs.get("gates", {})
    if not gates:
        rows.append({"variant": variant, "step": step, "task": "control_no_retrieval", "expert_index": "NA", "mean_weight": "NA", "batch_cases": ",".join(keys)})
        return
    for task, gate in gates.items():
        usage = gate.detach().mean(dim=0).cpu().tolist()
        for idx, value in enumerate(usage):
            rows.append({"variant": variant, "step": step, "task": task, "expert_index": idx, "mean_weight": float(value), "batch_cases": ",".join(keys)})


def train_variant(args: argparse.Namespace) -> None:
    if args.max_runtime_seconds < args.min_effective_seconds:
        raise ValueError("--max-runtime-seconds must be >= --min-effective-seconds")
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    train_ids, val_ids = load_split(args.fold)
    metadata = load_myops_case_metadata()
    train_cases = [read_case(cid, metadata) for cid in train_ids]
    val_cases = [read_case(cid, metadata) for cid in val_ids]
    complete_cases = [case for case in train_cases if case.metadata.modality_group == "C0+LGE+T2"]
    scar_cases = [case for case in train_cases if has_label(case, 5)]
    lge_only_scar_cases = [case for case in scar_cases if case.metadata.modality_group == "LGE-only"]
    edema_t2_cases = [case for case in train_cases if case.metadata.t2_present and has_label(case, 4)]
    center_c_t2_edema_cases = [case for case in edema_t2_cases if case.metadata.center == "CenterC"]
    out_root = Path(args.out_root)
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    variant_dir = out_root / "variants" / args.variant
    checkpoint_dir = variant_dir / "checkpoints/fold_0/srr_fold0_config"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    patch_shape = parse_shape(args.patch_shape)
    model = make_model(args, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    loss_weights = loss_weights_from_args(args)
    retrieval_config = retrieval_config_from_args(args)
    router_temperatures, effective_expert_dropout = variant_router_settings(args)
    rng = np.random.default_rng(args.seed)
    start = time.monotonic()
    best_val = float("inf")
    best_step = 0
    stop_reason = "max_steps"
    train_rows: list[dict[str, object]] = []
    usage_rows: list[dict[str, object]] = []
    model.train()
    for step in range(1, args.max_steps + 1):
        if time.monotonic() - start > args.max_runtime_seconds:
            stop_reason = "max_runtime_seconds"
            break
        x_cpu, y_cpu, av_cpu, keys = batch_from_cases(
            train_cases,
            complete_cases,
            scar_cases,
            lge_only_scar_cases,
            edema_t2_cases,
            center_c_t2_edema_cases,
            args.batch_size,
            patch_shape,
            rng,
            args.complete_oversample,
            args.oversample_foreground,
            modality_dropout=True,
            lesion_mode=args.variant if args.variant in LESION_COMPACT_VARIANTS else "",
        )
        x = x_cpu.to(device)
        y = y_cpu.to(device)
        av = av_cpu.to(device)
        optimizer.zero_grad(set_to_none=True)
        outputs = model(x, av)
        loss, metrics = srr_total_loss(outputs, y, av, weights=loss_weights, retrieval_config=retrieval_config)
        aux_loss, aux_metrics = lesion_auxiliary_loss(outputs, y, av, args)
        loss = loss + aux_loss
        metrics.update(aux_metrics)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        optimizer.step()
        if step == 1 or step % args.log_every == 0:
            supervised_fraction = float(av[:, 1].mean().detach().cpu())
            train_rows.append(
                {
                    "variant": args.variant,
                    "step": step,
                    "loss": float(loss.detach().cpu()),
                    "anatomy_loss": float(metrics["anatomy"].detach().cpu()),
                    "scar_loss": float(metrics["scar"].detach().cpu()),
                    "edema_loss": float(metrics["edema"].detach().cpu()),
                    "retrieval_loss": float(metrics["retrieval"].detach().cpu()),
                    "soft_containment_loss": float(metrics["soft_containment"].detach().cpu()),
                    "component_compactness_loss": float(metrics["component_compactness"].detach().cpu()),
                    "proposal_bce_loss": float(metrics["proposal_bce"].detach().cpu()),
                    "proposal_margin_loss": float(metrics["proposal_margin"].detach().cpu()),
                    "proposal_uncertainty_loss": float(metrics["proposal_uncertainty"].detach().cpu()),
                    "edema_supervised_batch_fraction": supervised_fraction,
                    "batch_cases": ",".join(keys),
                    "elapsed_seconds": time.monotonic() - start,
                }
            )
            record_gate_usage(usage_rows, args.variant, step, keys, outputs)
        if step == 1 or step % args.val_every == 0:
            val_loss = validate_patch_loss(model, val_cases, patch_shape, device, args.seed + step, loss_weights, retrieval_config, args)
            train_rows.append(
                {
                    "variant": args.variant,
                    "step": step,
                    "loss": float(loss.detach().cpu()),
                    "val_patch_loss": val_loss,
                    "elapsed_seconds": time.monotonic() - start,
                    "event": "validation",
                }
            )
            if val_loss < best_val:
                best_val = val_loss
                best_step = step
                save_checkpoint_atomic(
                    {
                        "variant": args.variant,
                        "step": step,
                        "model_state_dict": model.state_dict(),
                        "val_patch_loss": best_val,
                        "args": vars(args),
                    },
                    checkpoint_dir / "checkpoint_best.pt",
                )
    elapsed_seconds = time.monotonic() - start
    budget_status = "OK"
    if stop_reason == "max_steps" and elapsed_seconds < args.min_effective_seconds:
        budget_status = "UNDER_BUDGET_MAX_STEPS"
    final_ckpt = checkpoint_dir / "checkpoint_final.pt"
    save_checkpoint_atomic({"variant": args.variant, "model_state_dict": model.state_dict(), "args": vars(args)}, final_ckpt)
    best_path = checkpoint_dir / "checkpoint_best.pt"
    if best_path.is_file() and best_path.stat().st_size > 0:
        state = torch.load(best_path, map_location=device, weights_only=False)
        model.load_state_dict(state["model_state_dict"])
    else:
        save_checkpoint_atomic({"variant": args.variant, "model_state_dict": model.state_dict(), "args": vars(args)}, best_path)
        best_step = args.max_steps
        best_val = float("nan")
    if not args.skip_export:
        evaluate_and_export(model, val_cases, variant_dir, args.variant, device)
    write_csv(variant_dir / "training_log.csv", train_rows)
    write_csv(variant_dir / "retrieval_usage.csv", usage_rows)
    summary = {
        "variant": args.variant,
        "fold": args.fold,
        "device": str(device),
        "train_cases": len(train_cases),
        "val_cases": len(val_cases),
        "complete_train_cases": len(complete_cases),
        "scar_train_cases": len(scar_cases),
        "lge_only_scar_train_cases": len(lge_only_scar_cases),
        "edema_t2_train_cases": len(edema_t2_cases),
        "center_c_t2_edema_train_cases": len(center_c_t2_edema_cases),
        "best_step": best_step,
        "best_val_patch_loss": best_val,
        "stop_reason": stop_reason,
        "elapsed_seconds": elapsed_seconds,
        "budget_status": budget_status,
        "max_steps": args.max_steps,
        "max_runtime_seconds": args.max_runtime_seconds,
        "min_effective_seconds": args.min_effective_seconds,
        "out_root": str(out_root),
        "checkpoint_best": str(best_path),
        "checkpoint_final": str(final_ckpt),
        "prediction_dir": str(variant_dir / "predictions/fold_0/checkpoint_best"),
        "export_skipped": bool(args.skip_export),
        "loss_weights": loss_weights,
        "retrieval_config": retrieval_config,
        "router_temperatures": router_temperatures,
        "expert_dropout": effective_expert_dropout,
        "dictionary_mode": dictionary_mode_for_variant(args.variant),
        "proposal_mode": proposal_mode_for_variant(args.variant),
        "lesion_mode": args.variant if args.variant in LESION_COMPACT_VARIANTS else "none",
        "lesion_auxiliary_config": {
            "containment_weight": float(args.containment_weight),
            "compactness_weight": float(args.compactness_weight),
            "proposal_bce_weight": float(args.proposal_bce_weight),
            "proposal_margin_weight": float(args.proposal_margin_weight),
            "proposal_uncertainty_weight": float(args.proposal_uncertainty_weight),
            "proposal_margin": float(args.proposal_margin),
        },
    }
    (variant_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_text(
        variant_dir / "summary.md",
        "\n".join(
            [
                f"# {args.variant} Fold0 Summary",
                "",
                f"- stop_reason: `{stop_reason}`",
                f"- budget_status: `{budget_status}`",
                f"- best_step: `{best_step}`",
                f"- best_val_patch_loss: `{best_val}`",
                f"- elapsed_seconds: `{summary['elapsed_seconds']:.1f}`",
                f"- checkpoint_best: `{best_path}`",
                f"- predictions: `{summary['prediction_dir']}`",
            ]
        )
        + "\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--variant",
        required=True,
        choices=[
            "conditional_dualhead_control",
            "srr_minimal",
            "srr_soft_entropy",
            "srr_expert_dropout",
            "srr_task_tempered",
            "late_fusion_no_dictionary",
            "retrieval_no_sip_or_weak_sip",
            "multiscale_dictionary",
            "task_specific_dictionary",
            "cross_modal_interaction_dictionary",
            "anchor_guided_dictionary",
            "hierarchical_router_dictionary",
            "soft_anatomy_containment",
            "component_compactness_loss",
            "scar_lge_fallback_boost",
            "edema_t2_center_balance",
            "proposal_pos_neg_basic",
            "proposal_anatomy_distance",
            "proposal_uncertainty_gate",
            "proposal_hard_negative_replay_preflight",
        ],
    )
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260621)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--base-channels", type=int, default=16)
    parser.add_argument("--patch-shape", default="12,96,96")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=1000000)
    parser.add_argument("--max-runtime-seconds", type=float, default=16200.0)
    parser.add_argument("--min-effective-seconds", type=float, default=0.0)
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--grad-clip", type=float, default=12.0)
    parser.add_argument("--log-every", type=int, default=50)
    parser.add_argument("--val-every", type=int, default=500)
    parser.add_argument("--complete-oversample", type=float, default=0.55)
    parser.add_argument("--oversample-foreground", type=float, default=0.75)
    parser.add_argument("--router-temperature", type=float, default=1.0)
    parser.add_argument("--anatomy-router-temperature", type=float)
    parser.add_argument("--scar-router-temperature", type=float)
    parser.add_argument("--edema-router-temperature", type=float)
    parser.add_argument("--expert-dropout", type=float, default=0.0)
    parser.add_argument("--retrieval-entropy-floor", type=float, default=0.7)
    parser.add_argument("--retrieval-entropy-weight", type=float, default=0.08)
    parser.add_argument("--retrieval-coverage-weight", type=float, default=0.08)
    parser.add_argument("--retrieval-max-weight-penalty", type=float, default=0.04)
    parser.add_argument("--anatomy-weight", type=float, default=1.0)
    parser.add_argument("--scar-weight", type=float, default=1.2)
    parser.add_argument("--edema-weight", type=float, default=1.3)
    parser.add_argument("--prior-weight", type=float, default=0.1)
    parser.add_argument("--retrieval-weight", type=float, default=1.0)
    parser.add_argument("--containment-weight", type=float, default=0.0)
    parser.add_argument("--compactness-weight", type=float, default=0.0)
    parser.add_argument("--proposal-bce-weight", type=float, default=0.45)
    parser.add_argument("--proposal-margin-weight", type=float, default=0.20)
    parser.add_argument("--proposal-uncertainty-weight", type=float, default=0.05)
    parser.add_argument("--proposal-margin", type=float, default=0.25)
    parser.add_argument("--skip-export", action="store_true", help="Preflight only: skip full validation prediction export.")
    args = parser.parse_args()
    train_variant(args)


if __name__ == "__main__":
    main()
