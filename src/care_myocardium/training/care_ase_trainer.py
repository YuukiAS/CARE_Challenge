"""Training helpers for CARE-ASE."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import os
import json
import random
import re
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage
import torch
from torch import nn
import torch.nn.functional as F

from src.care_myocardium.models.care_ase import CAREASE, CAREASEConfig, compute_slice_extent_statistics


CHECKPOINT_SCHEMA_VERSION = 3
FULL_CASE_TARGET_KEYS = (
    "signed_endo_distance",
    "signed_epi_distance",
    "wall_depth_rho",
    "geometry_valid",
    "scar_context_target",
    "edema_context_target",
    "scar_center_fullres",
    "edema_boundary",
    "edema_boundary_raw_mm",
    "edema_boundary_valid",
    "scar_slice_presence",
    "scar_slice_area",
    "scar_slice_area_valid",
    "scar_slice_pathology_voxels",
    "scar_slice_wall_voxels",
    "edema_slice_presence",
    "edema_slice_area",
    "edema_slice_area_valid",
    "edema_slice_pathology_voxels",
    "edema_slice_wall_voxels",
)
REQUIRED_CHECKPOINT_FIELDS = (
    "schema_version",
    "model",
    "optimizer",
    "scheduler",
    "training_source_commit_sha",
    "origin_main_sha",
    "effective_contract_sha256",
    "external_review_permit_sha256",
    "critical_source_manifest_sha256",
    "split_file_sha256",
    "split_case_lists_sha256",
    "actual_train_case_ids_sha256",
    "hard_negative_manifest_sha256",
    "area_reference_receipt_sha256",
    "case_metadata_sha256",
    "plans_sha256",
    "stock_checkpoint_sha256",
    "augmentation_contract_sha256",
    "full_case_target_cache_manifest_sha256",
    "formal_resumable",
    "augmentation_rng_state",
    "fold",
    "precision_mode",
    "global_optimizer_step",
    "stage_id",
    "stage_step",
    "accumulation_microbatch_cursor",
    "python_rng",
    "numpy_rng",
    "torch_cpu_rng",
    "torch_cuda_rng_all_devices",
    "dataloader_worker_seed_state",
    "case_group_cursor",
    "complete_center_selector_cursor",
    "complete_centerB_case_cursor",
    "complete_centerC_case_cursor",
    "complete_center_cursor",
    "complete_pathology_cursor",
    "partial_case_cursors",
    "micro_case_cursors_by_group",
    "micro_case_rng_state_by_group",
    "micro_patch_cursor",
    "micro_patch_rng_state",
    "next_optimizer_step_micro_descriptor_bundle",
    "next_optimizer_step_micro_descriptor_sha256",
    "center_cursor",
    "pathology_focus_cursor",
    "scar_focus_cursor",
    "edema_focus_cursor",
    "sampler_rng_state",
    "batch_descriptor_cursor",
    "next_batch_descriptor_sha256",
    "extent_wall_ramp_value",
    "code_hash",
    "config_hash",
    "split_hash",
    "plans_hash",
    "stock_checkpoint_hash",
)
REQUIRED_LOSS_WEIGHTS = {
    "final_competition": 1.00,
    "anatomy4": 0.50,
    "wall": 0.25,
    "distance": 0.10,
    "scar_dense": 1.00,
    "scar_component": 0.25,
    "scar_center": 0.10,
    "scar_extent": 0.15,
    "scar_context": 0.10,
    "edema_dense": 1.00,
    "injury": 0.40,
    "edema_boundary": 0.10,
    "edema_extent": 0.20,
    "edema_context": 0.10,
    "relation": 0.05,
}


def dice_loss_softmax(logits: torch.Tensor, target: torch.Tensor, *, classes: tuple[int, ...], eps: float = 1.0e-5) -> torch.Tensor:
    probs = torch.softmax(logits.float(), dim=1)
    valid_mask = (target >= 0).to(probs)
    losses = []
    for cls in classes:
        p = probs[:, cls] * valid_mask
        g = (target == int(cls)).to(p) * valid_mask
        valid = (p.sum(dim=(1, 2, 3)) + g.sum(dim=(1, 2, 3))) > 0
        if bool(valid.any()):
            inter = (p[valid] * g[valid]).sum(dim=(1, 2, 3))
            denom = p[valid].sum(dim=(1, 2, 3)) + g[valid].sum(dim=(1, 2, 3))
            losses.append(1.0 - ((2.0 * inter + eps) / (denom + eps)).mean())
    if losses:
        return torch.stack(losses).mean()
    return logits.sum() * 0.0


def binary_dice_bce(logit: torch.Tensor, target: torch.Tensor, valid_mask: torch.Tensor | None = None) -> torch.Tensor:
    logit = logit.float()
    target = target.to(logit)
    mask = torch.ones_like(target) if valid_mask is None else valid_mask.to(logit)
    prob = torch.sigmoid(logit)
    dims = tuple(range(1, prob.ndim))
    inter = (prob * target * mask).sum(dim=dims)
    gt_positive = (target * mask).sum(dim=dims)
    denom = (prob * mask).sum(dim=dims) + gt_positive
    dice_values = torch.where(gt_positive > 0, 1.0 - (2.0 * inter + 1.0e-5) / (denom + 1.0e-5), torch.zeros_like(denom))
    dice = dice_values.mean()
    bce = F.binary_cross_entropy_with_logits(logit, target, reduction="none")
    return dice + ((bce * mask).sum() / mask.sum().clamp_min(1.0))


def _five_class_logits_and_target(logits: torch.Tensor, target: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    five = torch.cat([logits[:, :4], logits[:, 5:6]], dim=1)
    mapped = target.clone()
    mapped = torch.where(mapped == 5, torch.full_like(mapped, 4), mapped)
    mapped = torch.where(mapped == 4, torch.full_like(mapped, -1), mapped)
    return five, mapped


def binary_dice_focal(
    logit: torch.Tensor,
    target: torch.Tensor,
    valid_mask: torch.Tensor | None = None,
    *,
    alpha: float,
    gamma: float,
) -> torch.Tensor:
    logit = logit.float()
    target = target.to(logit)
    mask = torch.ones_like(target) if valid_mask is None else valid_mask.to(logit)
    prob = torch.sigmoid(logit)
    dims = tuple(range(1, prob.ndim))
    inter = (prob * target * mask).sum(dim=dims)
    gt_positive = (target * mask).sum(dim=dims)
    denom = (prob * mask).sum(dim=dims) + gt_positive
    dice_values = torch.where(gt_positive > 0, 1.0 - (2.0 * inter + 1.0e-5) / (denom + 1.0e-5), torch.zeros_like(denom))
    dice = dice_values.mean()
    bce = F.binary_cross_entropy_with_logits(logit, target, reduction="none")
    p_t = prob * target + (1.0 - prob) * (1.0 - target)
    alpha_t = alpha * target + (1.0 - alpha) * (1.0 - target)
    focal = alpha_t * (1.0 - p_t).pow(gamma) * bce
    return dice + ((focal * mask).sum() / mask.sum().clamp_min(1.0))


def normalized_focal_bce(
    logit: torch.Tensor,
    target: torch.Tensor,
    valid_mask: torch.Tensor | None = None,
    *,
    alpha: float,
    gamma: float,
) -> torch.Tensor:
    """Contract center loss: positive and negative focal BCE normalized separately."""

    logit = logit.float()
    target = target.to(logit)
    mask = torch.ones_like(target) if valid_mask is None else valid_mask.to(logit)
    prob = torch.sigmoid(logit)
    bce = F.binary_cross_entropy_with_logits(logit, target, reduction="none")
    p_t = prob * target + (1.0 - prob) * (1.0 - target)
    focal = (1.0 - p_t).pow(gamma) * bce
    pos = mask * (target > 0.5).to(mask)
    neg = mask * (target <= 0.5).to(mask)
    pos_loss = alpha * (focal * pos).sum() / pos.sum().clamp_min(1.0)
    neg_loss = (1.0 - alpha) * (focal * neg).sum() / neg.sum().clamp_min(1.0)
    return pos_loss + neg_loss


def component_tversky(logit: torch.Tensor, target: torch.Tensor, valid_mask: torch.Tensor, *, alpha: float = 0.3, beta: float = 0.7) -> torch.Tensor:
    logit = logit.float()
    target = target.to(logit)
    mask = valid_mask.to(logit)
    prob = torch.sigmoid(logit)
    tp = (prob * target * mask).sum()
    fp = (prob * (1.0 - target) * mask).sum()
    fn = ((1.0 - prob) * target * mask).sum()
    return 1.0 - (tp + 1.0e-5) / (tp + alpha * fp + beta * fn + 1.0e-5)


def _masked_mean_loss(value: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    mask = mask.to(value)
    return (value * mask).sum() / mask.sum().clamp_min(1.0)


def _downsample_target(target: torch.Tensor, size: tuple[int, int, int]) -> torch.Tensor:
    return F.interpolate(target.float(), size=size, mode="nearest").to(dtype=target.dtype)


def _downsample_slice_presence_any(target_presence: torch.Tensor, out_z: int) -> torch.Tensor:
    """Downsample per-z presence by bin-wise any/max, never linear interpolation."""

    source = target_presence.float()
    if source.shape[-1] == int(out_z):
        return source
    bins = []
    in_z = int(source.shape[-1])
    for out_idx in range(int(out_z)):
        start = int(np.floor(out_idx * in_z / int(out_z)))
        stop = int(np.ceil((out_idx + 1) * in_z / int(out_z)))
        stop = max(stop, start + 1)
        bins.append(source[..., start:stop].amax(dim=-1, keepdim=True))
    return torch.cat(bins, dim=-1)


def _downsample_slice_area_by_physical_bin(
    pathology_voxels: torch.Tensor,
    wall_voxels: torch.Tensor,
    out_z: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Recompute area fraction inside each target z-bin from pathology/wall counts."""

    path = pathology_voxels.float()
    wall = wall_voxels.float()
    if path.shape[-1] != wall.shape[-1]:
        raise ValueError("pathology_voxels and wall_voxels must share z length")
    if path.shape[-1] == int(out_z):
        valid = (wall > 0).float()
        return path / wall.clamp_min(1.0), valid
    areas = []
    valids = []
    in_z = int(path.shape[-1])
    for out_idx in range(int(out_z)):
        start = int(np.floor(out_idx * in_z / int(out_z)))
        stop = int(np.ceil((out_idx + 1) * in_z / int(out_z)))
        stop = max(stop, start + 1)
        path_count = path[..., start:stop].sum(dim=-1, keepdim=True)
        wall_count = wall[..., start:stop].sum(dim=-1, keepdim=True)
        valid = (wall_count > 0).float()
        areas.append(path_count / wall_count.clamp_min(1.0))
        valids.append(valid)
    return torch.cat(areas, dim=-1), torch.cat(valids, dim=-1)


def per_slice_extent_loss(
    presence_logits: torch.Tensor,
    area_logits: torch.Tensor,
    detached_p_wall: torch.Tensor,
    target_presence: torch.Tensor,
    target_pathology_voxels: torch.Tensor,
    target_wall_voxels: torch.Tensor,
    case_valid: torch.Tensor | None,
    valid_spatial_mask: torch.Tensor | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Per-z presence BCE and wall-denominator-valid area SmoothL1."""

    pred_presence_5d, pred_area_5d, _wall_slice, _fallback = compute_slice_extent_statistics(
        presence_logits.float(),
        area_logits.float(),
        detached_p_wall.detach(),
        valid_spatial_mask,
    )
    pred_presence = pred_presence_5d.squeeze(-1).squeeze(-1)
    pred_area = pred_area_5d.squeeze(-1).squeeze(-1)
    size = pred_presence.shape[-1:]
    target_presence_z = _downsample_slice_presence_any(target_presence, int(size[0]))
    target_area_z, target_area_valid_z = _downsample_slice_area_by_physical_bin(target_pathology_voxels, target_wall_voxels, int(size[0]))
    if case_valid is None:
        case_mask = torch.ones_like(target_presence_z)
    else:
        case_mask = case_valid.float().view(-1, 1, 1).to(target_presence_z)
    presence_raw = F.binary_cross_entropy(pred_presence.clamp(1.0e-6, 1.0 - 1.0e-6), target_presence_z, reduction="none")
    presence = (presence_raw * case_mask).sum() / case_mask.sum().clamp_min(1.0)
    area_mask = case_mask * target_area_valid_z
    area_raw = F.smooth_l1_loss(pred_area, target_area_z, reduction="none")
    area = (area_raw * area_mask).sum() / area_mask.sum().clamp_min(1.0)
    return presence, area


def _context_target(target: torch.Tensor) -> torch.Tensor:
    out = torch.full_like(target, -1)
    out = torch.where(target == 5, torch.zeros_like(out), out)
    out = torch.where((target == 2) | (target == 3), torch.ones_like(out), out)
    out = torch.where(target == 1, torch.full_like(out, 2), out)
    out = torch.where(target == 0, torch.full_like(out, 3), out)
    return out


def _signed_distance(mask: np.ndarray, *, clip: float = 10.0, sampling: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> np.ndarray:
    mask = np.asarray(mask, dtype=bool)
    outside = ndimage.distance_transform_edt(~mask, sampling=sampling)
    inside = ndimage.distance_transform_edt(mask, sampling=sampling)
    return np.clip(outside - inside, -clip, clip).astype(np.float32) / float(clip)


def _signed_distance_2d(mask: np.ndarray, *, clip: float = 10.0, sampling: tuple[float, float] = (1.0, 1.0)) -> np.ndarray:
    mask = np.asarray(mask, dtype=bool)
    outside = ndimage.distance_transform_edt(~mask, sampling=sampling)
    inside = ndimage.distance_transform_edt(mask, sampling=sampling)
    return np.clip(outside - inside, -clip, clip).astype(np.float32) / float(clip)


def _geometry_targets_numpy(seg: np.ndarray, spacing: tuple[float, float, float]) -> dict[str, np.ndarray]:
    valid_label = seg >= 0
    wall = (seg == 1) | (seg == 4) | (seg == 5)
    lv = seg == 2
    rv = seg == 3
    exterior = valid_label & ~(wall | lv | rv)
    d_endo = np.zeros(seg.shape, dtype=np.float32)
    d_epi = np.zeros(seg.shape, dtype=np.float32)
    signed_endo = np.zeros(seg.shape, dtype=np.float32)
    signed_epi = np.zeros(seg.shape, dtype=np.float32)
    valid = np.zeros(seg.shape, dtype=np.float32)
    inplane_spacing = (float(spacing[1]), float(spacing[2]))
    for z in range(int(seg.shape[0])):
        wall_z = wall[z]
        lv_z = lv[z]
        exterior_z = exterior[z]
        topology_valid_slice = bool(wall_z.any() and lv_z.any() and exterior_z.any())
        if not topology_valid_slice:
            continue
        d_endo[z] = ndimage.distance_transform_edt(~lv_z, sampling=inplane_spacing).astype(np.float32)
        d_epi[z] = ndimage.distance_transform_edt(~exterior_z, sampling=inplane_spacing).astype(np.float32)
        signed_endo[z] = _signed_distance_2d(lv_z, clip=10.0, sampling=inplane_spacing)
        signed_epi[z] = _signed_distance_2d(exterior_z, clip=10.0, sampling=inplane_spacing)
        valid[z] = (wall_z & valid_label[z]).astype(np.float32)
    rho = d_endo / (d_endo + d_epi + 1.0e-6)
    return {
        "signed_endo_distance": signed_endo,
        "signed_epi_distance": signed_epi,
        "wall_depth_rho": rho.astype(np.float32),
        "geometry_valid": valid,
    }


def _context_target_numpy(seg: np.ndarray, *, edema: bool, spacing: tuple[float, float, float]) -> np.ndarray:
    out = np.full(seg.shape, -1, dtype=np.int64)
    valid_label = seg >= 0
    pathology = seg == (4 if edema else 5)
    scar = seg == 5
    pure_edema = seg == 4
    blood = (seg == 2) | (seg == 3)
    wall_union = (seg == 1) | (seg == 4) | (seg == 5)
    dist_blood = ndimage.distance_transform_edt(~blood, sampling=spacing)
    dist_pathology_or_blood = ndimage.distance_transform_edt(~(blood | pure_edema | scar), sampling=spacing)
    dist_wall = ndimage.distance_transform_edt(~wall_union, sampling=spacing)
    out[pathology] = 0
    non_pathology = valid_label & ~(scar | pure_edema)
    out[(out < 0) & non_pathology & (dist_blood <= 3.0)] = 1
    normal = (seg == 1) & (dist_pathology_or_blood > 3.0)
    out[(out < 0) & normal] = 2
    remote = valid_label & (seg == 0) & (dist_wall >= 10.0)
    out[(out < 0) & remote] = 3
    if edema:
        out[seg == 5] = -1
    return out


def _component_center_heatmap(seg: np.ndarray, label_value: int, out_shape: tuple[int, int, int], spacing: tuple[float, float, float]) -> np.ndarray:
    mask = seg == int(label_value)
    labels, count = ndimage.label(mask, structure=np.ones((3, 3, 3), dtype=np.uint8))
    heat = np.zeros(seg.shape, dtype=np.float32)
    zz, yy, xx = np.indices(seg.shape)
    for comp_id in range(1, int(count) + 1):
        coords = np.argwhere(labels == comp_id)
        if coords.size == 0:
            continue
        cz, cy, cx = coords.mean(axis=0)
        sigma_z = 1.0
        sigma_y = max(4.0 / max(float(spacing[1]), 1.0e-6), 1.0e-6)
        sigma_x = max(4.0 / max(float(spacing[2]), 1.0e-6), 1.0e-6)
        gaussian = np.exp(
            -(
                ((zz - cz) ** 2) / (2.0 * sigma_z**2)
                + ((yy - cy) ** 2) / (2.0 * sigma_y**2)
                + ((xx - cx) ** 2) / (2.0 * sigma_x**2)
            )
        )
        heat = np.maximum(heat, gaussian.astype(np.float32))
    tensor = torch.from_numpy(heat[None, None])
    return F.interpolate(tensor, size=out_shape, mode="trilinear", align_corners=False)[0, 0].numpy().astype(np.float32)


def _spacing_rows(batch: dict[str, torch.Tensor], count: int) -> list[tuple[float, float, float]]:
    raw = batch.get("spacing")
    if raw is None:
        return [(1.0, 1.0, 1.0)] * int(count)
    if torch.is_tensor(raw):
        arr = raw.detach().cpu().numpy()
    else:
        arr = np.asarray(raw, dtype=np.float32)
    if arr.ndim == 1:
        arr = np.broadcast_to(arr[None], (count, 3))
    return [tuple(float(v) for v in row[:3]) for row in arr]


def _edema_boundary_numpy(seg: np.ndarray, spacing: tuple[float, float, float]) -> dict[str, np.ndarray]:
    valid_label = seg >= 0
    edema = seg == 4
    if not bool(edema.any()):
        zero = np.zeros(seg.shape, dtype=np.float32)
        return {"edema_boundary": zero, "edema_boundary_raw_mm": zero, "edema_boundary_valid": zero}
    if bool(edema.all()):
        raw = np.zeros(seg.shape, dtype=np.float32)
        return {"edema_boundary": np.ones(seg.shape, dtype=np.float32), "edema_boundary_raw_mm": raw, "edema_boundary_valid": np.ones(seg.shape, dtype=np.float32)}
    raw_mm = np.asarray(ndimage.distance_transform_edt(edema, sampling=spacing) - ndimage.distance_transform_edt(~edema, sampling=spacing), dtype=np.float32)
    clipped = np.clip(raw_mm, -10.0, 10.0).astype(np.float32) / 10.0
    valid = (((np.abs(raw_mm) <= 10.0) | edema) & valid_label).astype(np.float32)
    return {"edema_boundary": clipped, "edema_boundary_raw_mm": raw_mm, "edema_boundary_valid": valid}


def _slice_extent_targets_numpy(seg: np.ndarray) -> dict[str, np.ndarray]:
    valid_label = seg >= 0
    wall = (seg == 1) | (seg == 4) | (seg == 5)
    out: dict[str, np.ndarray] = {}
    for name, label_value in (("scar", 5), ("edema", 4)):
        pathology = (seg == label_value) & valid_label
        presence = pathology.any(axis=(1, 2)).astype(np.float32)
        wall_voxels = wall.sum(axis=(1, 2)).astype(np.float32)
        path_voxels = pathology.sum(axis=(1, 2)).astype(np.float32)
        area = np.zeros_like(presence, dtype=np.float32)
        valid = wall_voxels > 0
        area[valid] = path_voxels[valid] / wall_voxels[valid]
        out[f"{name}_slice_presence"] = presence
        out[f"{name}_slice_area"] = area
        out[f"{name}_slice_area_valid"] = valid.astype(np.float32)
        out[f"{name}_slice_pathology_voxels"] = path_voxels.astype(np.float32)
        out[f"{name}_slice_wall_voxels"] = wall_voxels.astype(np.float32)
    return out


def _crop_or_pad_numpy(array: np.ndarray, center: tuple[int, int, int], patch_size: tuple[int, int, int], *, pad_value: float | int) -> np.ndarray:
    spatial = array.shape[-3:]
    src_slices: list[slice] = []
    dst_slices: list[slice] = []
    for c, dim, size in zip(center, spatial, patch_size):
        start = int(c) - int(size) // 2
        stop = start + int(size)
        src_start = max(0, start)
        src_stop = min(int(dim), stop)
        dst_start = src_start - start
        dst_stop = dst_start + (src_stop - src_start)
        src_slices.append(slice(src_start, src_stop))
        dst_slices.append(slice(dst_start, dst_stop))
    out = np.full(array.shape[:-3] + tuple(int(v) for v in patch_size), pad_value, dtype=array.dtype)
    out[(..., *dst_slices)] = array[(..., *src_slices)]
    return out


def build_full_case_target_cache(seg: np.ndarray, spacing: tuple[float, float, float]) -> dict[str, np.ndarray]:
    """Build physical targets once on the full preprocessed case grid.

    Formal CARE-ASE training must slice these cached full-case target fields
    into patches instead of recomputing EDT, context, boundary, component, or
    extent targets from a crop.
    """

    seg = np.asarray(seg, dtype=np.int16)
    geometry = _geometry_targets_numpy(seg, spacing)
    boundary = _edema_boundary_numpy(seg, spacing)
    extent = _slice_extent_targets_numpy(seg)
    cache: dict[str, np.ndarray] = {
        **geometry,
        "scar_context_target": _context_target_numpy(seg, edema=False, spacing=spacing),
        "edema_context_target": _context_target_numpy(seg, edema=True, spacing=spacing),
        "scar_center_fullres": _component_center_heatmap(seg, 5, tuple(int(v) for v in seg.shape), spacing),
        **boundary,
        **extent,
    }
    cache["valid_label_mask"] = (seg >= 0).astype(np.float32)
    return cache


def slice_full_case_target_cache(
    cache: dict[str, np.ndarray],
    *,
    center: tuple[int, int, int],
    patch_size: tuple[int, int, int],
) -> dict[str, np.ndarray]:
    """Slice a full-case target cache with ignore-safe padding."""

    out: dict[str, np.ndarray] = {}
    for key in FULL_CASE_TARGET_KEYS:
        if key not in cache:
            raise KeyError(f"full-case target cache missing required key: {key}")
        value = np.asarray(cache[key])
        if value.ndim == 3:
            if np.issubdtype(value.dtype, np.integer):
                pad = -1 if key.endswith("_target") else 0
            else:
                pad = 0.0
            out[key] = _crop_or_pad_numpy(value, center, patch_size, pad_value=pad)
        elif value.ndim == 1:
            out[key] = value.astype(np.float32, copy=False)
        else:
            raise ValueError(f"unsupported full-case target cache field rank for {key}: {value.shape}")
    if "valid_label_mask" in cache:
        out["valid_label_mask"] = _crop_or_pad_numpy(np.asarray(cache["valid_label_mask"]), center, patch_size, pad_value=0.0)
    return out


def _tensor_cache_from_batch(batch: dict[str, Any], device: torch.device) -> dict[str, torch.Tensor] | None:
    raw = batch.get("full_case_target_cache") if batch is not None else None
    if raw is None:
        return None
    out: dict[str, torch.Tensor] = {}
    for key, value in raw.items():
        tensor = value if torch.is_tensor(value) else torch.as_tensor(value)
        if key.endswith("_target"):
            out[key] = tensor.to(device=device, dtype=torch.long)
        else:
            out[key] = tensor.to(device=device, dtype=torch.float32)
    return out


def _ensure_batch_channel(tensor: torch.Tensor, *, channel: bool, dtype: torch.dtype) -> torch.Tensor:
    value = tensor.to(dtype=dtype)
    if channel:
        if value.ndim == 1:
            value = value.unsqueeze(0).unsqueeze(0)
        elif value.ndim == 3:
            value = value.unsqueeze(0).unsqueeze(0)
        elif value.ndim == 4:
            value = value.unsqueeze(1)
    else:
        if value.ndim == 1:
            value = value.unsqueeze(0)
        elif value.ndim == 3:
            value = value.unsqueeze(0)
        elif value.ndim == 5 and value.shape[1] == 1:
            value = value[:, 0]
    return value


def build_care_ase_targets(target: torch.Tensor, availability: torch.Tensor, outputs: dict[str, Any], batch: dict[str, torch.Tensor] | None = None) -> dict[str, torch.Tensor]:
    device = target.device
    cache = _tensor_cache_from_batch(batch or {}, device)
    if cache is not None:
        stacked = {
            key: _ensure_batch_channel(cache[key], channel=True, dtype=torch.float32)
            for key in ("signed_endo_distance", "signed_epi_distance", "wall_depth_rho", "geometry_valid")
        }
        stacked["scar_context_target"] = _ensure_batch_channel(cache["scar_context_target"], channel=False, dtype=torch.long)
        stacked["edema_context_target"] = _ensure_batch_channel(cache["edema_context_target"], channel=False, dtype=torch.long)
        scar_center_fullres = _ensure_batch_channel(cache["scar_center_fullres"], channel=True, dtype=torch.float32)
        stacked["scar_center_quarter"] = F.interpolate(
            scar_center_fullres,
            size=outputs["components"]["scar_quarter_center"].shape[-3:],
            mode="trilinear",
            align_corners=False,
        )
        stacked["scar_center_half"] = F.interpolate(
            scar_center_fullres,
            size=outputs["components"]["scar_half_center"].shape[-3:],
            mode="trilinear",
            align_corners=False,
        )
        for key in ("edema_boundary", "edema_boundary_raw_mm", "edema_boundary_valid"):
            stacked[key] = _ensure_batch_channel(cache[key], channel=True, dtype=torch.float32)
        for key in (
            "scar_slice_presence",
            "scar_slice_area",
            "scar_slice_area_valid",
            "scar_slice_pathology_voxels",
            "scar_slice_wall_voxels",
            "edema_slice_presence",
            "edema_slice_area",
            "edema_slice_area_valid",
            "edema_slice_pathology_voxels",
            "edema_slice_wall_voxels",
        ):
            stacked[key] = _ensure_batch_channel(cache[key], channel=True, dtype=torch.float32)
        stacked["valid_label_mask"] = _ensure_batch_channel(cache.get("valid_label_mask", (target >= 0).float()), channel=True, dtype=torch.float32)
        stacked["availability"] = availability
        stacked["target_builder_provenance"] = "full_case_target_cache"
        return stacked
    rows = []
    scar_context = []
    edema_context = []
    scar_center_quarter = []
    scar_center_half = []
    edema_boundary = []
    edema_boundary_raw = []
    edema_boundary_valid = []
    extent_rows = []
    items = target.detach().cpu().numpy().astype(np.int16)
    spacings = _spacing_rows(batch or {}, len(items))
    for item, spacing in zip(items, spacings):
        rows.append(_geometry_targets_numpy(item, spacing))
        scar_context.append(_context_target_numpy(item, edema=False, spacing=spacing))
        edema_context.append(_context_target_numpy(item, edema=True, spacing=spacing))
        scar_center_quarter.append(_component_center_heatmap(item, 5, outputs["components"]["scar_quarter_center"].shape[-3:], spacing))
        scar_center_half.append(_component_center_heatmap(item, 5, outputs["components"]["scar_half_center"].shape[-3:], spacing))
        boundary = _edema_boundary_numpy(item, spacing)
        edema_boundary.append(boundary["edema_boundary"])
        edema_boundary_raw.append(boundary["edema_boundary_raw_mm"])
        edema_boundary_valid.append(boundary["edema_boundary_valid"])
        extent_rows.append(_slice_extent_targets_numpy(item))
    stacked = {
        key: torch.from_numpy(np.stack([row[key] for row in rows])[:, None]).to(device=device, dtype=torch.float32)
        for key in ("signed_endo_distance", "signed_epi_distance", "wall_depth_rho", "geometry_valid")
    }
    stacked["scar_context_target"] = torch.from_numpy(np.stack(scar_context)).to(device=device, dtype=torch.long)
    stacked["edema_context_target"] = torch.from_numpy(np.stack(edema_context)).to(device=device, dtype=torch.long)
    stacked["scar_center_quarter"] = torch.from_numpy(np.stack(scar_center_quarter)[:, None]).to(device=device, dtype=torch.float32)
    stacked["scar_center_half"] = torch.from_numpy(np.stack(scar_center_half)[:, None]).to(device=device, dtype=torch.float32)
    stacked["edema_boundary"] = torch.from_numpy(np.stack(edema_boundary)[:, None]).to(device=device, dtype=torch.float32)
    stacked["edema_boundary_raw_mm"] = torch.from_numpy(np.stack(edema_boundary_raw)[:, None]).to(device=device, dtype=torch.float32)
    stacked["edema_boundary_valid"] = torch.from_numpy(np.stack(edema_boundary_valid)[:, None]).to(device=device, dtype=torch.float32)
    stacked["valid_label_mask"] = (target >= 0).unsqueeze(1).to(device=device, dtype=torch.float32)
    for key in (
        "scar_slice_presence",
        "scar_slice_area",
        "scar_slice_area_valid",
        "scar_slice_pathology_voxels",
        "scar_slice_wall_voxels",
        "edema_slice_presence",
        "edema_slice_area",
        "edema_slice_area_valid",
        "edema_slice_pathology_voxels",
        "edema_slice_wall_voxels",
    ):
        stacked[key] = torch.from_numpy(np.stack([row[key] for row in extent_rows])[:, None]).to(device=device, dtype=torch.float32)
    stacked["availability"] = availability
    stacked["target_builder_provenance"] = "patch_local_fallback_for_tests_only"
    return stacked


def per_gt_component_tversky(logit: torch.Tensor, target: torch.Tensor, valid_mask: torch.Tensor, batch: dict[str, torch.Tensor] | None = None) -> torch.Tensor:
    losses: list[torch.Tensor] = []
    weights: list[float] = []
    labels_np = target.detach().cpu().numpy().astype(bool)
    spacings = _spacing_rows(batch or {}, labels_np.shape[0])
    for b, mask in enumerate(labels_np[:, 0]):
        comp, count = ndimage.label(mask, structure=np.ones((3, 3, 3), dtype=np.uint8))
        for comp_id in range(1, int(count) + 1):
            comp_mask_np = comp == comp_id
            other_components_np = mask & ~comp_mask_np
            volume = float(comp_mask_np.sum() * np.prod(spacings[b]))
            weight = min(max((1000.0 / max(volume, 1.0)) ** 0.5, 1.0), 4.0)
            comp_mask = torch.from_numpy(comp_mask_np[None, None]).to(device=logit.device, dtype=logit.dtype)
            other_components = torch.from_numpy(other_components_np[None, None]).to(device=logit.device, dtype=logit.dtype)
            comp_valid = valid_mask[b : b + 1].to(logit) * (1.0 - other_components)
            losses.append(component_tversky(logit[b : b + 1], comp_mask, comp_valid))
            weights.append(float(weight))
    if not losses:
        return logit.sum() * 0.0
    weight_tensor = torch.tensor(weights, device=logit.device, dtype=torch.float32)
    return (torch.stack(losses).float() * weight_tensor).sum() / weight_tensor.sum().clamp_min(1.0e-6)


def context_cross_entropy_valid_mean(logits: torch.Tensor, target: torch.Tensor, valid_mask: torch.Tensor | None = None) -> torch.Tensor:
    raw = F.cross_entropy(logits.float(), target, ignore_index=-1, reduction="none")
    valid = (target >= 0).to(raw)
    if valid_mask is not None:
        valid = valid * valid_mask.to(raw)
    denom = valid.sum()
    if float(denom.detach().cpu()) <= 0.0:
        return logits.sum() * 0.0
    return (raw * valid).sum() / denom


def care_ase_loss(outputs: dict[str, Any], batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, dict[str, float]]:
    logits = outputs["final_logits"]
    target = batch["seg"].to(device=logits.device, dtype=torch.long)
    availability = batch["availability"].to(logits)
    t2_present = availability[:, 1] > 0.5
    final_terms: list[torch.Tensor] = []
    metrics: dict[str, torch.Tensor] = {}
    if bool(t2_present.any()):
        idx = t2_present
        ce6 = F.cross_entropy(logits[idx], target[idx], ignore_index=-1)
        dice6 = dice_loss_softmax(logits[idx], target[idx], classes=(1, 2, 3, 4, 5))
        metrics["six_class_ce"] = ce6
        metrics["six_class_dice"] = dice6
        final_terms.append(ce6 + dice6)
    if bool((~t2_present).any()):
        idx = ~t2_present
        five_logits, five_target = _five_class_logits_and_target(logits[idx], target[idx])
        ce5 = F.cross_entropy(five_logits, five_target, ignore_index=-1)
        dice5 = dice_loss_softmax(five_logits, five_target, classes=(1, 2, 3, 4))
        metrics["five_class_ce_without_class4"] = ce5
        metrics["five_class_dice_without_class4"] = dice5
        final_terms.append(ce5 + dice5)
    if "pathology_deep_supervision_weights" not in outputs:
        raise KeyError("CARE-ASE loss requires pathology_deep_supervision_weights from the model forward output")
    dense_weights = outputs["pathology_deep_supervision_weights"]
    if "full" not in dense_weights or "half" not in dense_weights:
        raise KeyError("pathology_deep_supervision_weights must contain full and half weights")
    full_weight = float(dense_weights["full"])
    half_weight = float(dense_weights["half"])
    weight_sum = max(full_weight + half_weight, 1.0e-6)
    full_weight, half_weight = full_weight / weight_sum, half_weight / weight_sum
    anatomy_target = target.clone()
    anatomy_target = torch.where((anatomy_target == 4) | (anatomy_target == 5), torch.ones_like(anatomy_target), anatomy_target)
    anatomy_ce = F.cross_entropy(outputs["anatomy_logits_0_3"], anatomy_target.clamp(-1, 3), ignore_index=-1)
    anatomy_dice = dice_loss_softmax(outputs["anatomy_logits_0_3"], anatomy_target.clamp(-1, 3), classes=(1, 2, 3))
    anatomy_half_target = _downsample_target(anatomy_target.unsqueeze(1), outputs["anatomy"]["half_logits4"].shape[-3:]).squeeze(1).clamp(-1, 3)
    anatomy_half_ce = F.cross_entropy(outputs["anatomy"]["half_logits4"], anatomy_half_target, ignore_index=-1)
    anatomy_half_dice = dice_loss_softmax(outputs["anatomy"]["half_logits4"], anatomy_half_target, classes=(1, 2, 3))
    anatomy4_loss = full_weight * (anatomy_ce + anatomy_dice) + half_weight * (anatomy_half_ce + anatomy_half_dice)
    valid_binary = (target >= 0).unsqueeze(1).to(logits)
    wall_target = ((target == 1) | (target == 4) | (target == 5)).unsqueeze(1)
    scar_target = (target == 5).unsqueeze(1)
    edema_target = (target == 4).unsqueeze(1)
    injury_target = ((target == 4) | (target == 5)).unsqueeze(1)
    t2_mask = availability[:, 1].view(-1, 1, 1, 1, 1)
    edema_valid = valid_binary * t2_mask
    p_wall = outputs["p_wall_union"]
    components = outputs["components"]
    built_targets = build_care_ase_targets(target, availability, outputs, batch)
    wall_loss = binary_dice_bce(torch.logit(p_wall.clamp(1.0e-4, 1.0 - 1.0e-4)), wall_target, valid_binary)
    distance_loss = (
        _masked_mean_loss(F.smooth_l1_loss(outputs["signed_endo_distance"], built_targets["signed_endo_distance"], reduction="none"), built_targets["geometry_valid"])
        + _masked_mean_loss(F.smooth_l1_loss(outputs["signed_epi_distance"], built_targets["signed_epi_distance"], reduction="none"), built_targets["geometry_valid"])
        + _masked_mean_loss(F.smooth_l1_loss(outputs["wall_depth_rho"], built_targets["wall_depth_rho"], reduction="none"), built_targets["geometry_valid"])
    ) / 3.0
    scar_full = binary_dice_focal(outputs["z_scar"], scar_target, valid_binary, alpha=0.25, gamma=2.0)
    scar_half_logit = F.interpolate(outputs["scar"].get("half_logit", outputs["scar"]["half_logits6"][:, 5:6]), size=target.shape[-3:], mode="trilinear", align_corners=False)
    scar_half_dense = binary_dice_focal(scar_half_logit, scar_target, valid_binary, alpha=0.25, gamma=2.0)
    scar_dense = full_weight * scar_full + half_weight * scar_half_dense
    edema_full = binary_dice_focal(outputs["z_pure_edema"], edema_target, edema_valid, alpha=0.35, gamma=2.0)
    edema_half_logit = F.interpolate(outputs["edema"].get("half_logit", outputs["edema"]["half_logits6"][:, 4:5]), size=target.shape[-3:], mode="trilinear", align_corners=False)
    edema_half_dense = binary_dice_focal(edema_half_logit, edema_target, edema_valid, alpha=0.35, gamma=2.0)
    edema_dense = full_weight * edema_full + half_weight * edema_half_dense
    scar_half = F.interpolate(outputs["scar"].get("half_logit", outputs["scar"]["half_logits6"][:, 5:6]), size=target.shape[-3:], mode="trilinear", align_corners=False)
    edema_half = F.interpolate(outputs["edema"].get("half_logit", outputs["edema"]["half_logits6"][:, 4:5]), size=target.shape[-3:], mode="trilinear", align_corners=False)
    scar_component = per_gt_component_tversky(scar_half, scar_target.float(), valid_binary, batch)
    scar_occ_quarter = _downsample_target(scar_target, components["scar_quarter_occupancy"].shape[-3:])
    scar_occ_half = _downsample_target(scar_target, components["scar_half_occupancy"].shape[-3:])
    valid_quarter = _downsample_target(valid_binary, components["scar_quarter_center"].shape[-3:]).float()
    valid_half = _downsample_target(valid_binary, components["scar_half_center"].shape[-3:]).float()
    scar_center = 0.5 * normalized_focal_bce(components["scar_quarter_center"], built_targets["scar_center_quarter"], valid_quarter, alpha=0.25, gamma=2.0) + 0.5 * normalized_focal_bce(components["scar_half_center"], built_targets["scar_center_half"], valid_half, alpha=0.25, gamma=2.0)
    scar_occupancy = 0.5 * binary_dice_focal(components["scar_quarter_occupancy"], scar_occ_quarter, valid_quarter, alpha=0.25, gamma=2.0) + 0.5 * binary_dice_focal(components["scar_half_occupancy"], scar_occ_half, valid_half, alpha=0.25, gamma=2.0)
    edema_boundary_target = built_targets["edema_boundary"]
    edema_boundary_valid = built_targets["edema_boundary_valid"].to(logits) * t2_mask
    edema_boundary_logit = F.interpolate(components["edema_boundary"], size=target.shape[-3:], mode="trilinear", align_corners=False)
    edema_boundary = _masked_mean_loss(F.smooth_l1_loss(torch.tanh(edema_boundary_logit.float()), edema_boundary_target.float(), reduction="none"), edema_boundary_valid)
    injury_logit = F.interpolate(components["edema_injury"], size=target.shape[-3:], mode="trilinear", align_corners=False)
    injury = binary_dice_focal(injury_logit, injury_target, edema_valid, alpha=0.35, gamma=2.0)
    scar_presence, scar_area = per_slice_extent_loss(
        components["scar_extent_presence"],
        components["scar_extent_area"],
        outputs["p_wall_union"],
        built_targets["scar_slice_presence"],
        built_targets["scar_slice_pathology_voxels"],
        built_targets["scar_slice_wall_voxels"],
        None,
        built_targets["valid_label_mask"],
    )
    edema_presence, edema_area = per_slice_extent_loss(
        components["edema_extent_presence"],
        components["edema_extent_area"],
        outputs["p_wall_union"],
        built_targets["edema_slice_presence"],
        built_targets["edema_slice_pathology_voxels"],
        built_targets["edema_slice_wall_voxels"],
        availability[:, 1:2],
        built_targets["valid_label_mask"],
    )
    scar_context_target = _downsample_target(built_targets["scar_context_target"].unsqueeze(1), components["scar_context"].shape[-3:]).squeeze(1)
    edema_context_target = _downsample_target(built_targets["edema_context_target"].unsqueeze(1), components["edema_context"].shape[-3:]).squeeze(1)
    scar_context = context_cross_entropy_valid_mean(components["scar_context"], scar_context_target)
    edema_valid_context = availability[:, 1].view(-1, 1, 1, 1)
    edema_context = context_cross_entropy_valid_mean(components["edema_context"], edema_context_target, edema_valid_context)
    relation = F.relu(torch.maximum(outputs["z_scar"].detach().sigmoid(), outputs["z_pure_edema"].detach().sigmoid()) - torch.sigmoid(injury_logit.float())).mul(edema_valid).sum() / edema_valid.sum().clamp_min(1.0)
    zero = logits.sum() * 0.0
    if not final_terms:
        final_terms.append(zero)
    scar_extent = 0.5 * scar_presence + 0.5 * scar_area
    edema_extent = 0.5 * edema_presence + 0.5 * edema_area
    weighted_terms = {
        "final_competition": REQUIRED_LOSS_WEIGHTS["final_competition"] * torch.stack(final_terms).mean(),
        "anatomy4": REQUIRED_LOSS_WEIGHTS["anatomy4"] * anatomy4_loss,
        "wall": REQUIRED_LOSS_WEIGHTS["wall"] * wall_loss,
        "distance": REQUIRED_LOSS_WEIGHTS["distance"] * distance_loss,
        "scar_dense": REQUIRED_LOSS_WEIGHTS["scar_dense"] * scar_dense,
        "scar_component": REQUIRED_LOSS_WEIGHTS["scar_component"] * (0.5 * scar_component + 0.5 * scar_occupancy),
        "scar_center": REQUIRED_LOSS_WEIGHTS["scar_center"] * scar_center,
        "scar_extent": REQUIRED_LOSS_WEIGHTS["scar_extent"] * scar_extent,
        "scar_context": REQUIRED_LOSS_WEIGHTS["scar_context"] * scar_context,
        "edema_dense": REQUIRED_LOSS_WEIGHTS["edema_dense"] * edema_dense,
        "injury": REQUIRED_LOSS_WEIGHTS["injury"] * injury,
        "edema_boundary": REQUIRED_LOSS_WEIGHTS["edema_boundary"] * edema_boundary,
        "edema_extent": REQUIRED_LOSS_WEIGHTS["edema_extent"] * edema_extent,
        "edema_context": REQUIRED_LOSS_WEIGHTS["edema_context"] * edema_context,
        "relation": REQUIRED_LOSS_WEIGHTS["relation"] * relation,
    }
    total = torch.stack(list(weighted_terms.values())).sum()
    metrics.update(
        {
            "loss": total,
            "anatomy_ce": anatomy_ce,
            "anatomy_dice": anatomy_dice,
            "anatomy_half_ce": anatomy_half_ce,
            "anatomy_half_dice": anatomy_half_dice,
            "anatomy4_deep_supervised": anatomy4_loss,
            "wall": wall_loss,
            "distance": distance_loss,
            "scar_dense": scar_dense,
            "scar_component": scar_component,
            "scar_center": scar_center,
            "scar_extent_presence": scar_presence,
            "scar_extent_area": scar_area,
            "scar_extent": scar_extent,
            "scar_context": scar_context,
            "edema_dense": edema_dense,
            "edema_binary_t2_gated": edema_dense,
            "injury": injury,
            "edema_boundary": edema_boundary,
            "edema_extent_presence": edema_presence,
            "edema_extent_area": edema_area,
            "edema_extent": edema_extent,
            "edema_context": edema_context,
            "relation": relation,
            "no_t2_edema_exclusive_total_loss": zero if not bool(t2_present.any()) else edema_dense + injury + edema_boundary + edema_extent + edema_context + relation,
            "all_finite": torch.isfinite(total).to(total),
            "all_nonnegative": (total >= 0).to(total),
        }
    )
    return total, {k: float(v.detach().cpu()) for k, v in metrics.items()}


def _encoder_stage_index(name: str) -> int | None:
    match = re.search(r"(?:^|\.)stages\.(\d+)(?:\.|$)", name)
    return int(match.group(1)) if match else None


def _encoder_upper_stage_indices(all_names: list[str]) -> set[int]:
    indices = sorted({idx for name in all_names if name.startswith("encoder.") for idx in [_encoder_stage_index(name)] if idx is not None})
    return set(indices[-2:])


def _is_upper_encoder_parameter(name: str, upper_stage_indices: set[int]) -> bool:
    idx = _encoder_stage_index(name)
    return idx is not None and idx in upper_stage_indices


PARAMETER_GROUP_NAMES = (
    "new_modules",
    "cloned_pathology_blocks",
    "cloned_pathology_classifiers",
    "anatomy_decoder",
    "shared_low_mid_decoder",
    "upper_two_encoder",
    "lower_encoder_bottleneck",
)


GROUP_INITIAL_LRS = {
    "new_modules": 5.0e-4,
    "cloned_pathology_blocks": 1.0e-4,
    "cloned_pathology_classifiers": 2.0e-4,
    "anatomy_decoder": 1.0e-4,
    "shared_low_mid_decoder": 1.0e-4,
    "upper_two_encoder": 5.0e-5,
    "lower_encoder_bottleneck": 1.0e-5,
}


STAGE_TRAINABLE_GROUPS = {
    "A": {"new_modules", "cloned_pathology_blocks", "cloned_pathology_classifiers"},
    "B": {"new_modules", "cloned_pathology_blocks", "cloned_pathology_classifiers", "anatomy_decoder", "shared_low_mid_decoder", "upper_two_encoder"},
    "C": set(PARAMETER_GROUP_NAMES),
}


def _parameter_aliases(model: CAREASE) -> dict[int, list[str]]:
    aliases: dict[int, list[str]] = {}
    for name, param in model.named_parameters(remove_duplicate=False):
        aliases.setdefault(id(param), []).append(name)
    for names in aliases.values():
        names.sort()
    return aliases


def _parameter_group_registry(model: CAREASE) -> tuple[dict[int, str], dict[int, str], dict[int, list[str]]]:
    aliases = _parameter_aliases(model)
    upper_encoder_stage_indices = _encoder_upper_stage_indices([name for names in aliases.values() for name in names])
    group_by_id: dict[int, str] = {}
    canonical_by_id: dict[int, str] = {}
    for param_id, names in aliases.items():
        canonical = names[0]
        canonical_by_id[param_id] = canonical
        if any(".half_projections." in name or ".full_projections." in name for name in names):
            group = "new_modules"
        elif any(name.startswith(("component_heads.", "scar_lge_half_adapter.", "scar_lge_full_adapter.", "scar_c0_half_adapter.", "scar_c0_full_adapter.", "edema_t2_half_adapter.", "edema_t2_full_adapter.", "edema_c0_half_adapter.", "edema_c0_full_adapter.", "edema_lge_half_adapter.", "edema_lge_full_adapter.", "scar_c0_gate.", "edema_c0_gate.", "edema_lge_gate.", "anatomy_geometry_heads.", "edema_dilation_context.")) for name in names):
            group = "new_modules"
        elif any(name.startswith(("scar_branch.seg_layers.", "edema_branch.seg_layers.")) for name in names):
            group = "cloned_pathology_classifiers"
        elif any(name.startswith(("scar_branch.", "edema_branch.")) for name in names):
            group = "cloned_pathology_blocks"
        elif any(name.startswith("encoder.") and _is_upper_encoder_parameter(name, upper_encoder_stage_indices) for name in names):
            group = "upper_two_encoder"
        elif any(name.startswith("encoder.") for name in names):
            group = "lower_encoder_bottleneck"
        elif any(name.startswith(("low_mid_transpconvs.", "low_mid_stages.")) for name in names) or any(
            name.startswith("anatomy_decoder.") and any(token in name for token in ("transpconvs.0", "transpconvs.1", "transpconvs.2", "transpconvs.3", "stages.0", "stages.1", "stages.2", "stages.3"))
            for name in names
        ):
            group = "shared_low_mid_decoder"
        elif any(name.startswith(("anatomy_decoder.", "anatomy_top_transpconvs.", "anatomy_top_stages.", "anatomy_top_seg_layers.")) for name in names):
            group = "anatomy_decoder"
        else:
            group = "new_modules"
        group_by_id[param_id] = group
    return group_by_id, canonical_by_id, aliases


def set_stage_trainability(model: CAREASE, *, global_step: int) -> str:
    step = int(global_step)
    stage = "A" if step < model.config.stage_a_steps else "B" if step < model.config.stage_a_steps + model.config.stage_b_steps else "C"
    group_by_id, _canonical_by_id, _aliases = _parameter_group_registry(model)
    trainable_groups = STAGE_TRAINABLE_GROUPS[stage]
    for param in model.parameters():
        param.requires_grad_(group_by_id[id(param)] in trainable_groups)
    return stage


def optimizer_parameter_groups(model: CAREASE) -> list[dict[str, Any]]:
    groups: dict[str, list[nn.Parameter]] = {name: [] for name in PARAMETER_GROUP_NAMES}
    seen: set[int] = set()
    group_by_id, _canonical_by_id, _aliases = _parameter_group_registry(model)
    for param in model.parameters():
        param_id = id(param)
        if param_id in seen:
            continue
        seen.add(param_id)
        groups[group_by_id[param_id]].append(param)
    return [{"name": name, "params": params, "lr": GROUP_INITIAL_LRS[name], "weight_decay": 1.0e-4} for name, params in groups.items()]


def _expected_parameter_group_from_aliases(names: list[str], upper_stage_indices: set[int]) -> str | None:
    if any(".half_projections." in name or ".full_projections." in name for name in names):
        return "new_modules"
    if any(
        name.startswith(
            (
                "component_heads.",
                "scar_lge_half_adapter.",
                "scar_lge_full_adapter.",
                "scar_c0_half_adapter.",
                "scar_c0_full_adapter.",
                "edema_t2_half_adapter.",
                "edema_t2_full_adapter.",
                "edema_c0_half_adapter.",
                "edema_c0_full_adapter.",
                "edema_lge_half_adapter.",
                "edema_lge_full_adapter.",
                "scar_c0_gate.",
                "edema_c0_gate.",
                "edema_lge_gate.",
                "anatomy_geometry_heads.",
                "edema_dilation_context.",
            )
        )
        for name in names
    ):
        return "new_modules"
    if any(name.startswith(("scar_branch.seg_layers.", "edema_branch.seg_layers.")) for name in names):
        return "cloned_pathology_classifiers"
    if any(name.startswith(("scar_branch.", "edema_branch.")) for name in names):
        return "cloned_pathology_blocks"
    if any(name.startswith("encoder.") and _is_upper_encoder_parameter(name, upper_stage_indices) for name in names):
        return "upper_two_encoder"
    if any(name.startswith("encoder.") for name in names):
        return "lower_encoder_bottleneck"
    if any(name.startswith(("low_mid_transpconvs.", "low_mid_stages.")) for name in names) or any(
        name.startswith("anatomy_decoder.") and any(token in name for token in ("transpconvs.0", "transpconvs.1", "transpconvs.2", "transpconvs.3", "stages.0", "stages.1", "stages.2", "stages.3"))
        for name in names
    ):
        return "shared_low_mid_decoder"
    if any(name.startswith("anatomy_decoder.") for name in names):
        return "anatomy_decoder"
    return None


def parameter_group_coverage(model: CAREASE) -> dict[str, Any]:
    group_by_id, canonical_by_id, aliases = _parameter_group_registry(model)
    all_params = list(model.parameters())
    observed_ids = [id(param) for param in all_params]
    duplicate_count = len(observed_ids) - len(set(observed_ids))
    upper_stage_indices = _encoder_upper_stage_indices([name for names in aliases.values() for name in names])
    expected_by_id = {param_id: _expected_parameter_group_from_aliases(names, upper_stage_indices) for param_id, names in aliases.items()}
    missing_ids = sorted(param_id for param_id, expected in expected_by_id.items() if expected is None)
    wrong_ids = sorted(
        param_id
        for param_id, expected in expected_by_id.items()
        if expected is not None and group_by_id.get(param_id) != expected
    )
    sample_steps = (0, 199, 1999, 2000, 2499, 9999, 10000, 13999)
    rows = []
    for param in all_params:
        param_id = id(param)
        group = group_by_id[param_id]
        rows.append(
            {
                "parameter_id": param_id,
                "canonical_name": canonical_by_id[param_id],
                "aliases": aliases[param_id],
                "group": group,
                "expected_group": expected_by_id.get(param_id),
                "group_matches_expected": group == expected_by_id.get(param_id),
                "requires_grad": {stage: group in STAGE_TRAINABLE_GROUPS[stage] for stage in ("A", "B", "C")},
                "base_lr": {stage: CAREASEStageScheduler.stage_base_lrs[stage].get(group, 0.0) for stage in ("A", "B", "C")},
                "current_lr": {str(step): CAREASEStageScheduler.lr_for(group_name=group, global_step=step) for step in sample_steps},
            }
        )
    payload = {
        "status": "PASS" if duplicate_count == 0 and not missing_ids and not wrong_ids else "FAIL",
        "parameter_count": len(rows),
        "group_counts": {name: sum(1 for row in rows if row["group"] == name) for name in PARAMETER_GROUP_NAMES},
        "duplicate_count": int(duplicate_count),
        "missing_count": len(missing_ids),
        "wrong_group_count": len(wrong_ids),
        "missing_parameter_ids": missing_ids,
        "wrong_group_parameter_ids": wrong_ids,
        "all_parameters_in_optimizer_from_step0": True,
        "optimizer_created_once_moments_preserved_across_stages": True,
        "parameters": rows,
    }
    payload["payload_sha256"] = _json_sha(payload)
    return payload


def optimizer_parameter_groups_legacy_removed() -> list[dict[str, Any]]:
    return []


def _removed_name_prefix_only_grouping_reference() -> tuple[str, ...]:
    return (
        "new_modules",
        "cloned_pathology_blocks",
        "cloned_pathology_classifiers",
        "anatomy_decoder",
        "shared_low_mid_decoder",
        "upper_two_encoder",
        "lower_encoder_bottleneck",
    )


def build_optimizer(model: CAREASE) -> torch.optim.Optimizer:
    return torch.optim.AdamW(optimizer_parameter_groups(model))


def run_formal_optimizer_step(
    *,
    model: CAREASE,
    optimizer: torch.optim.Optimizer,
    scheduler: "CAREASEStageScheduler",
    microbatches: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    global_step: int,
    gradient_accumulation: int = 4,
    autocast_device_type: str = "cuda",
    autocast_dtype: torch.dtype = torch.bfloat16,
    autocast_enabled: bool = False,
) -> dict[str, Any]:
    """Single authoritative CARE-ASE optimizer-step implementation."""

    if not microbatches:
        raise ValueError("run_formal_optimizer_step requires at least one microbatch")
    stage = set_stage_trainability(model, global_step=int(global_step))
    scheduler.step(int(global_step))
    optimizer.zero_grad(set_to_none=True)
    loss_total = 0.0
    metrics: dict[str, float] = {}
    divisor = float(gradient_accumulation)
    for batch in microbatches:
        with torch.autocast(device_type=autocast_device_type, dtype=autocast_dtype, enabled=bool(autocast_enabled)):
            outputs = model(batch["image"], batch["availability"], global_step=int(global_step))
            loss, metrics = care_ase_loss(outputs, batch)
        (loss / divisor).backward()
        loss_total += float(loss.detach().cpu())
    grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], max_norm=float(model.config.gradient_clip_global_norm))
    optimizer.step()
    return {
        "stage": stage,
        "loss_mean": loss_total / max(float(len(microbatches)), 1.0),
        "metrics": dict(metrics),
        "grad_norm": float(grad_norm.detach().cpu() if torch.is_tensor(grad_norm) else grad_norm),
        "formal_step_api": "src.care_myocardium.training.care_ase_trainer.run_formal_optimizer_step",
        "microbatch_count": len(microbatches),
        "gradient_accumulation": int(gradient_accumulation),
    }


class CAREASEStageScheduler:
    """Stage-local warmup plus poly decay; optimizer object is never recreated."""

    power = 0.9
    stage_ranges = {"A": (0, 2000), "B": (2000, 10000), "C": (10000, 14000)}
    stage_warmup_steps = {"A": 200, "B": 500, "C": 0}
    stage_min_lrs = {"A": 5.0e-6, "B": 1.0e-6, "C": 1.0e-6}
    stage_base_lrs = {
        "A": {
            "new_modules": 5.0e-4,
            "cloned_pathology_blocks": 1.0e-4,
            "cloned_pathology_classifiers": 2.0e-4,
        },
        "B": {
            "new_modules": 3.0e-4,
            "cloned_pathology_blocks": 1.0e-4,
            "cloned_pathology_classifiers": 1.0e-4,
            "anatomy_decoder": 1.0e-4,
            "shared_low_mid_decoder": 1.0e-4,
            "upper_two_encoder": 5.0e-5,
        },
        "C": {
            "new_modules": 1.0e-4,
            "cloned_pathology_blocks": 5.0e-5,
            "cloned_pathology_classifiers": 5.0e-5,
            "anatomy_decoder": 5.0e-5,
            "shared_low_mid_decoder": 5.0e-5,
            "upper_two_encoder": 5.0e-5,
            "lower_encoder_bottleneck": 1.0e-5,
        },
    }

    def __init__(self, optimizer: torch.optim.Optimizer) -> None:
        self.optimizer = optimizer
        self.last_global_step = -1

    @classmethod
    def stage_for_step(cls, global_step: int) -> str:
        step = int(global_step)
        if step < 2000:
            return "A"
        if step < 10000:
            return "B"
        if step < 14000:
            return "C"
        return "complete"

    @classmethod
    def lr_for(cls, *, group_name: str, global_step: int) -> float:
        stage = cls.stage_for_step(global_step)
        if stage == "complete":
            stage = "C"
            global_step = 13999
        start, end = cls.stage_ranges[stage]
        base = cls.stage_base_lrs[stage].get(group_name, 0.0)
        if base <= 0.0:
            return 0.0
        stage_step = int(global_step) - start
        length = end - start
        warmup = min(cls.stage_warmup_steps[stage], length)
        min_lr = cls.stage_min_lrs[stage]
        if warmup > 0 and stage_step < warmup:
            return base * (0.1 + 0.9 * stage_step / max(warmup - 1, 1))
        t = (stage_step - warmup) / max(length - warmup - 1, 1)
        return min_lr + (base - min_lr) * ((1.0 - min(max(t, 0.0), 1.0)) ** cls.power)

    def step(self, global_step: int) -> None:
        self.last_global_step = int(global_step)
        for group in self.optimizer.param_groups:
            group["lr"] = self.lr_for(group_name=str(group.get("name", "")), global_step=global_step)

    def state_dict(self) -> dict[str, Any]:
        return {
            "last_global_step": self.last_global_step,
            "power": self.power,
            "stage_min_lrs": self.stage_min_lrs,
            "stage_warmup_steps": self.stage_warmup_steps,
            "stage_ranges": self.stage_ranges,
            "stage_base_lrs": self.stage_base_lrs,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.last_global_step = int(state["last_global_step"])


def capture_rng_state() -> dict[str, Any]:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.random.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def restore_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.random.set_rng_state(state["torch_cpu"].cpu() if torch.is_tensor(state["torch_cpu"]) else torch.as_tensor(state["torch_cpu"], dtype=torch.uint8))
    if torch.cuda.is_available() and state.get("torch_cuda"):
        torch.cuda.set_rng_state_all([s.cpu() if torch.is_tensor(s) else torch.as_tensor(s, dtype=torch.uint8) for s in state["torch_cuda"]])


def _sha256_file_or_missing(path: str | Path) -> str:
    p = Path(path)
    if not p.is_file():
        return "MISSING"
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_sha(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as f:
        os.fsync(f.fileno())


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_care_ase_checkpoint(
    path: Path,
    *,
    model: CAREASE,
    optimizer: torch.optim.Optimizer,
    scheduler: CAREASEStageScheduler | None = None,
    global_step: int,
    microbatch_cursor: int = 0,
    stage_id: str,
    next_batch_hash: str | None = None,
    loss_history_tail: list[dict[str, Any]],
    sampler_state: dict[str, Any] | None = None,
    dataloader_worker_seed_state: dict[str, Any] | None = None,
    code_hash: str | None = None,
    config_hash: str | None = None,
    split_hash: str | None = None,
    plans_hash: str | None = None,
    stock_checkpoint_hash: str | None = None,
    training_source_commit_sha: str | None = None,
    origin_main_sha: str | None = None,
    effective_contract_sha256: str | None = None,
    external_review_permit_sha256: str | None = None,
    critical_source_manifest_sha256: str | None = None,
    split_file_sha256: str | None = None,
    split_case_lists_sha256: str | None = None,
    actual_train_case_ids_sha256: str | None = None,
    hard_negative_manifest_sha256: str | None = None,
    area_reference_receipt_sha256: str | None = None,
    case_metadata_sha256: str | None = None,
    augmentation_contract_sha256: str | None = None,
    full_case_target_cache_manifest_sha256: str | None = None,
    augmentation_rng_state: dict[str, Any] | None = None,
    precision_mode: str = "fp32_guarded_mixed_precision_allowed",
    formal_resumable: bool = False,
) -> None:
    rng = capture_rng_state()
    sampler_state = dict(sampler_state or {})
    next_sha = str(next_batch_hash or sampler_state.get("next_batch_descriptor_sha256", "UNSET"))
    next_bundle_sha = str(sampler_state.get("next_optimizer_step_micro_descriptor_sha256", next_sha))
    if int(global_step) < int(model.config.max_optimizer_steps) and "TRAINING_COMPLETE" in {next_sha, next_bundle_sha}:
        raise ValueError("TRAINING_COMPLETE is forbidden before fixed global_step 14000")
    config_payload = asdict(model.config)
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict() if scheduler is not None else {"last_global_step": int(global_step), "type": "CAREASEStageScheduler"},
        "training_source_commit_sha": training_source_commit_sha or "UNSET",
        "origin_main_sha": origin_main_sha or "UNSET",
        "effective_contract_sha256": effective_contract_sha256 or "UNSET",
        "external_review_permit_sha256": external_review_permit_sha256 or "UNSET",
        "critical_source_manifest_sha256": critical_source_manifest_sha256 or code_hash or "UNSET",
        "split_file_sha256": split_file_sha256 or split_hash or "UNSET",
        "split_case_lists_sha256": split_case_lists_sha256 or "UNSET",
        "actual_train_case_ids_sha256": actual_train_case_ids_sha256 or "UNSET",
        "hard_negative_manifest_sha256": hard_negative_manifest_sha256 or str(sampler_state.get("hard_negative_manifest_sha256", "UNSET")),
        "area_reference_receipt_sha256": area_reference_receipt_sha256 or "UNSET",
        "case_metadata_sha256": case_metadata_sha256 or "UNSET",
        "plans_sha256": plans_hash or _sha256_file_or_missing(model.config.plans_path),
        "stock_checkpoint_sha256": stock_checkpoint_hash or _sha256_file_or_missing(model.config.checkpoint_path),
        "augmentation_contract_sha256": augmentation_contract_sha256 or "UNSET",
        "full_case_target_cache_manifest_sha256": full_case_target_cache_manifest_sha256 or "UNSET",
        "formal_resumable": bool(formal_resumable),
        "augmentation_rng_state": augmentation_rng_state
        or {
            "source": "global_python_numpy_torch_rng",
            "python": rng["python"],
            "numpy": rng["numpy"],
            "torch_cpu": rng["torch_cpu"],
            "torch_cuda": rng["torch_cuda"],
        },
        "fold": int(model.config.fold),
        "precision_mode": precision_mode,
        "global_optimizer_step": int(global_step),
        "stage_id": str(stage_id),
        "stage_step": int(global_step) - CAREASEStageScheduler.stage_ranges.get(str(stage_id), (0, 0))[0],
        "accumulation_microbatch_cursor": int(microbatch_cursor),
        "python_rng": rng["python"],
        "numpy_rng": rng["numpy"],
        "torch_cpu_rng": rng["torch_cpu"],
        "torch_cuda_rng_all_devices": rng["torch_cuda"],
        "dataloader_worker_seed_state": dataloader_worker_seed_state or {"worker_count": 0, "deterministic_single_process": True},
        "case_group_cursor": int(sampler_state.get("case_group_cursor", 0)),
        "complete_center_selector_cursor": int(sampler_state.get("complete_center_selector_cursor", sampler_state.get("complete_center_cursor", sampler_state.get("center_cursor", 0)))),
        "complete_centerB_case_cursor": int(sampler_state.get("complete_centerB_case_cursor", 0)),
        "complete_centerC_case_cursor": int(sampler_state.get("complete_centerC_case_cursor", 0)),
        "complete_center_cursor": int(sampler_state.get("complete_center_cursor", sampler_state.get("center_cursor", 0))),
        "complete_pathology_cursor": int(sampler_state.get("complete_pathology_cursor", sampler_state.get("pathology_focus_cursor", 0))),
        "partial_case_cursors": sampler_state.get("partial_case_cursors", {"lge_only": 0, "lge_c0": 0}),
        "micro_case_cursors_by_group": sampler_state.get("micro_case_cursors_by_group", {}),
        "micro_case_rng_state_by_group": sampler_state.get("micro_case_rng_state_by_group", {}),
        "micro_patch_cursor": int(sampler_state.get("micro_patch_cursor", 0)),
        "micro_patch_rng_state": sampler_state.get("micro_patch_rng_state", "UNSET"),
        "center_cursor": int(sampler_state.get("complete_center_cursor", sampler_state.get("center_cursor", 0))),
        "pathology_focus_cursor": int(sampler_state.get("complete_pathology_cursor", sampler_state.get("pathology_focus_cursor", 0))),
        "scar_focus_cursor": int(sampler_state.get("scar_focus_cursor", 0)),
        "edema_focus_cursor": int(sampler_state.get("edema_focus_cursor", 0)),
        "sampler_rng_state": sampler_state.get("sampler_rng_state", "UNSET"),
        "batch_descriptor_cursor": int(sampler_state.get("batch_descriptor_cursor", 0)),
        "next_batch_descriptor_sha256": next_sha,
        "next_optimizer_step_micro_descriptor_bundle": sampler_state.get("next_optimizer_step_micro_descriptor_bundle", []),
        "next_optimizer_step_micro_descriptor_sha256": next_bundle_sha,
        "extent_wall_ramp_value": CAREASE.extent_wall_ramp(global_step),
        "code_hash": code_hash or "UNSET",
        "config_hash": config_hash or _json_sha(config_payload),
        "split_hash": split_hash or "UNSET",
        "plans_hash": plans_hash or _sha256_file_or_missing(model.config.plans_path),
        "stock_checkpoint_hash": stock_checkpoint_hash or _sha256_file_or_missing(model.config.checkpoint_path),
        "config": config_payload,
        "loss_history_tail": loss_history_tail[-20:],
    }
    missing = [field for field in REQUIRED_CHECKPOINT_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"CARE-ASE checkpoint missing required fields: {missing}")
    if bool(formal_resumable):
        formal_fields = (
            "training_source_commit_sha",
            "origin_main_sha",
            "effective_contract_sha256",
            "external_review_permit_sha256",
            "critical_source_manifest_sha256",
            "split_file_sha256",
            "split_case_lists_sha256",
            "actual_train_case_ids_sha256",
            "hard_negative_manifest_sha256",
            "area_reference_receipt_sha256",
            "case_metadata_sha256",
            "plans_sha256",
            "stock_checkpoint_sha256",
            "augmentation_contract_sha256",
            "full_case_target_cache_manifest_sha256",
        )
        placeholders = [field for field in formal_fields if payload.get(field) in {None, "", "UNSET", "SHORT_SMOKE"}]
        if placeholders:
            raise ValueError(f"formal CARE-ASE checkpoint refuses placeholder provenance fields: {placeholders}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    torch.save(payload, tmp)
    _fsync_file(tmp)
    os.replace(tmp, path)
    _fsync_dir(path.parent)
    checkpoint_sha = _sha256_file_or_missing(path)
    sha_path = path.with_suffix(path.suffix + ".sha256")
    sha_tmp = sha_path.with_name(f".{sha_path.name}.tmp")
    sha_tmp.write_text(f"{checkpoint_sha}  {path.name}\n", encoding="utf-8")
    _fsync_file(sha_tmp)
    os.replace(sha_tmp, sha_path)
    _fsync_dir(path.parent)


def load_care_ase_checkpoint(
    path: Path,
    *,
    map_location: str | torch.device = "cpu",
    restore_rng: bool = True,
) -> tuple[CAREASE, dict[str, Any]]:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise ValueError(f"CARE-ASE checkpoint missing SHA sidecar: {sidecar}")
    expected_line = sidecar.read_text(encoding="utf-8").strip().split()
    expected_sha = expected_line[0] if expected_line else ""
    observed_sha = _sha256_file_or_missing(path)
    if expected_sha != observed_sha:
        raise ValueError(f"CARE-ASE checkpoint sidecar SHA mismatch: expected {expected_sha} observed {observed_sha}")
    payload = torch.load(path, map_location=map_location, weights_only=False)
    if int(payload.get("schema_version", 0)) != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(f"unsupported CARE-ASE checkpoint schema_version: {payload.get('schema_version')}")
    missing = [field for field in REQUIRED_CHECKPOINT_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"CARE-ASE checkpoint missing required fields: {missing}")
    if int(payload["global_optimizer_step"]) < 14000 and (
        payload.get("next_batch_descriptor_sha256") == "TRAINING_COMPLETE"
        or payload.get("next_optimizer_step_micro_descriptor_sha256") == "TRAINING_COMPLETE"
    ):
        raise ValueError("early checkpoint contains forbidden TRAINING_COMPLETE token")
    model = CAREASE(CAREASEConfig(**payload["config"]), map_location=map_location)
    model.load_state_dict(payload["model"])
    if restore_rng:
        restore_rng_state(
            {
                "python": payload["python_rng"],
                "numpy": payload["numpy_rng"],
                "torch_cpu": payload["torch_cpu_rng"],
                "torch_cuda": payload["torch_cuda_rng_all_devices"],
            }
        )
    return model, payload


def checkpoint_receipt(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "checkpoint_path": str(path),
        "schema_version": int(payload["schema_version"]),
        "global_optimizer_step": int(payload["global_optimizer_step"]),
        "microbatch_cursor": int(payload["accumulation_microbatch_cursor"]),
        "stage_id": payload["stage_id"],
        "stage_step": int(payload["stage_step"]),
        "complete_center_cursor": int(payload["complete_center_cursor"]),
        "complete_center_selector_cursor": int(payload.get("complete_center_selector_cursor", payload["complete_center_cursor"])),
        "complete_centerB_case_cursor": int(payload.get("complete_centerB_case_cursor", 0)),
        "complete_centerC_case_cursor": int(payload.get("complete_centerC_case_cursor", 0)),
        "complete_pathology_cursor": int(payload["complete_pathology_cursor"]),
        "partial_case_cursors": payload.get("partial_case_cursors", {}),
        "micro_case_cursors_by_group": payload.get("micro_case_cursors_by_group", {}),
        "micro_case_rng_state_by_group": payload.get("micro_case_rng_state_by_group", {}),
        "micro_patch_cursor": int(payload.get("micro_patch_cursor", 0)),
        "micro_patch_rng_state": payload.get("micro_patch_rng_state", "UNSET"),
        "next_optimizer_step_micro_descriptor_sha256": payload.get("next_optimizer_step_micro_descriptor_sha256", payload["next_batch_descriptor_sha256"]),
        "extent_wall_ramp_value": float(payload["extent_wall_ramp_value"]),
        "next_batch_hash": payload["next_batch_descriptor_sha256"],
        "has_optimizer_state": "optimizer" in payload,
        "has_scheduler_state": "scheduler" in payload,
        "has_rng_state": all(k in payload for k in ("python_rng", "numpy_rng", "torch_cpu_rng", "torch_cuda_rng_all_devices")),
        "has_sampler_rng_state": bool(payload.get("sampler_rng_state")) and payload.get("sampler_rng_state") != "UNSET",
        "has_dataloader_worker_seed_state": bool(payload.get("dataloader_worker_seed_state")),
        "required_fields_present": all(field in payload for field in REQUIRED_CHECKPOINT_FIELDS),
        "checkpoint_sha256": _sha256_file_or_missing(path),
        "fixed_terminal_step14000": int(payload["global_optimizer_step"]) == 14000,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    _fsync_file(tmp)
    os.replace(tmp, path)
    _fsync_dir(path.parent)
