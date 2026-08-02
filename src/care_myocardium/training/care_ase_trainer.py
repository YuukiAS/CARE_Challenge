"""Training helpers for CARE-ASE."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import os
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage
import torch
from torch import nn
import torch.nn.functional as F

from src.care_myocardium.models.care_ase import CAREASE, CAREASEConfig


CHECKPOINT_SCHEMA_VERSION = 1
REQUIRED_CHECKPOINT_FIELDS = (
    "model",
    "optimizer",
    "scheduler",
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
    probs = torch.softmax(logits, dim=1)
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
    target = target.to(logit)
    mask = torch.ones_like(target) if valid_mask is None else valid_mask.to(logit)
    prob = torch.sigmoid(logit)
    dims = tuple(range(1, prob.ndim))
    inter = (prob * target * mask).sum(dim=dims)
    denom = (prob * mask).sum(dim=dims) + (target * mask).sum(dim=dims)
    dice = (1.0 - (2.0 * inter + 1.0e-5) / (denom + 1.0e-5)).mean()
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
    target = target.to(logit)
    mask = torch.ones_like(target) if valid_mask is None else valid_mask.to(logit)
    prob = torch.sigmoid(logit)
    dims = tuple(range(1, prob.ndim))
    inter = (prob * target * mask).sum(dim=dims)
    denom = (prob * mask).sum(dim=dims) + (target * mask).sum(dim=dims)
    dice = (1.0 - (2.0 * inter + 1.0e-5) / (denom + 1.0e-5)).mean()
    bce = F.binary_cross_entropy_with_logits(logit, target, reduction="none")
    p_t = prob * target + (1.0 - prob) * (1.0 - target)
    focal = alpha * (1.0 - p_t).pow(gamma) * bce
    return dice + ((focal * mask).sum() / mask.sum().clamp_min(1.0))


def component_tversky(logit: torch.Tensor, target: torch.Tensor, valid_mask: torch.Tensor, *, alpha: float = 0.3, beta: float = 0.7) -> torch.Tensor:
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


def _context_target(target: torch.Tensor) -> torch.Tensor:
    out = torch.full_like(target, -1)
    out = torch.where(target == 5, torch.zeros_like(out), out)
    out = torch.where((target == 2) | (target == 3), torch.ones_like(out), out)
    out = torch.where(target == 1, torch.full_like(out, 2), out)
    out = torch.where(target == 0, torch.full_like(out, 3), out)
    return out


def _signed_distance(mask: np.ndarray, *, clip: float = 10.0) -> np.ndarray:
    mask = np.asarray(mask, dtype=bool)
    outside = ndimage.distance_transform_edt(~mask)
    inside = ndimage.distance_transform_edt(mask)
    return np.clip(outside - inside, -clip, clip).astype(np.float32) / float(clip)


def _geometry_targets_numpy(seg: np.ndarray) -> dict[str, np.ndarray]:
    wall = (seg == 1) | (seg == 4) | (seg == 5)
    lv = seg == 2
    exterior = ~(wall | lv | (seg == 3))
    d_endo = np.abs(_signed_distance(lv, clip=10.0))
    d_epi = np.abs(_signed_distance(exterior, clip=10.0))
    rho = d_endo / (d_endo + d_epi + 1.0e-6)
    valid = wall.astype(np.float32)
    return {
        "signed_endo_distance": _signed_distance(lv, clip=10.0),
        "signed_epi_distance": _signed_distance(exterior, clip=10.0),
        "wall_depth_rho": rho.astype(np.float32),
        "geometry_valid": valid,
    }


def _context_target_numpy(seg: np.ndarray, *, edema: bool) -> np.ndarray:
    out = np.full(seg.shape, -1, dtype=np.int64)
    pathology = seg == (4 if edema else 5)
    blood = (seg == 2) | (seg == 3)
    wall_union = (seg == 1) | (seg == 4) | (seg == 5)
    dist_blood = ndimage.distance_transform_edt(~blood)
    dist_wall = ndimage.distance_transform_edt(~wall_union)
    out[pathology] = 0
    out[(out < 0) & (dist_blood <= 3.0)] = 1
    normal = (seg == 1) & (dist_blood > 3.0)
    out[(out < 0) & normal] = 2
    remote = (seg == 0) & (dist_wall >= 10.0)
    out[(out < 0) & remote] = 3
    if edema:
        out[seg == 5] = -1
    return out


def _component_center_heatmap(seg: np.ndarray, label_value: int, out_shape: tuple[int, int, int]) -> np.ndarray:
    mask = seg == int(label_value)
    labels, count = ndimage.label(mask, structure=np.ones((3, 3, 3), dtype=np.uint8))
    heat = np.zeros(seg.shape, dtype=np.float32)
    zz, yy, xx = np.indices(seg.shape)
    for comp_id in range(1, int(count) + 1):
        coords = np.argwhere(labels == comp_id)
        if coords.size == 0:
            continue
        cz, cy, cx = coords.mean(axis=0)
        gaussian = np.exp(-(((zz - cz) ** 2) / (2.0 * 1.0**2) + ((yy - cy) ** 2 + (xx - cx) ** 2) / (2.0 * 4.0**2)))
        heat = np.maximum(heat, gaussian.astype(np.float32))
    tensor = torch.from_numpy(heat[None, None])
    return F.interpolate(tensor, size=out_shape, mode="trilinear", align_corners=False)[0, 0].numpy().astype(np.float32)


def build_care_ase_targets(target: torch.Tensor, availability: torch.Tensor, outputs: dict[str, Any]) -> dict[str, torch.Tensor]:
    device = target.device
    rows = []
    scar_context = []
    edema_context = []
    scar_center_quarter = []
    scar_center_half = []
    for item in target.detach().cpu().numpy().astype(np.int16):
        rows.append(_geometry_targets_numpy(item))
        scar_context.append(_context_target_numpy(item, edema=False))
        edema_context.append(_context_target_numpy(item, edema=True))
        scar_center_quarter.append(_component_center_heatmap(item, 5, outputs["components"]["scar_quarter_center"].shape[-3:]))
        scar_center_half.append(_component_center_heatmap(item, 5, outputs["components"]["scar_half_center"].shape[-3:]))
    stacked = {
        key: torch.from_numpy(np.stack([row[key] for row in rows])[:, None]).to(device=device, dtype=torch.float32)
        for key in ("signed_endo_distance", "signed_epi_distance", "wall_depth_rho", "geometry_valid")
    }
    stacked["scar_context_target"] = torch.from_numpy(np.stack(scar_context)).to(device=device, dtype=torch.long)
    stacked["edema_context_target"] = torch.from_numpy(np.stack(edema_context)).to(device=device, dtype=torch.long)
    stacked["scar_center_quarter"] = torch.from_numpy(np.stack(scar_center_quarter)[:, None]).to(device=device, dtype=torch.float32)
    stacked["scar_center_half"] = torch.from_numpy(np.stack(scar_center_half)[:, None]).to(device=device, dtype=torch.float32)
    stacked["availability"] = availability
    return stacked


def per_gt_component_tversky(logit: torch.Tensor, target: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
    losses: list[torch.Tensor] = []
    labels_np = target.detach().cpu().numpy().astype(bool)
    for b, mask in enumerate(labels_np[:, 0]):
        comp, count = ndimage.label(mask, structure=np.ones((3, 3, 3), dtype=np.uint8))
        for comp_id in range(1, int(count) + 1):
            comp_mask_np = comp == comp_id
            volume = float(comp_mask_np.sum())
            weight = min(max((1000.0 / max(volume, 1.0)) ** 0.5, 1.0), 4.0)
            comp_mask = torch.from_numpy(comp_mask_np[None, None]).to(device=logit.device, dtype=logit.dtype)
            losses.append(float(weight) * component_tversky(logit[b : b + 1], comp_mask, valid_mask[b : b + 1]))
    if not losses:
        return logit.sum() * 0.0
    return torch.stack(losses).mean()


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
    anatomy_target = target.clone()
    anatomy_target = torch.where((anatomy_target == 4) | (anatomy_target == 5), torch.ones_like(anatomy_target), anatomy_target)
    anatomy_ce = F.cross_entropy(outputs["anatomy_logits_0_3"], anatomy_target.clamp(-1, 3), ignore_index=-1)
    anatomy_dice = dice_loss_softmax(outputs["anatomy_logits_0_3"], anatomy_target.clamp(-1, 3), classes=(1, 2, 3))
    valid_binary = (target >= 0).unsqueeze(1).to(logits)
    wall_target = ((target == 1) | (target == 4) | (target == 5)).unsqueeze(1)
    scar_target = (target == 5).unsqueeze(1)
    edema_target = (target == 4).unsqueeze(1)
    injury_target = ((target == 4) | (target == 5)).unsqueeze(1)
    t2_mask = availability[:, 1].view(-1, 1, 1, 1, 1)
    edema_valid = valid_binary * t2_mask
    p_wall = outputs["p_wall_union"]
    components = outputs["components"]
    built_targets = build_care_ase_targets(target, availability, outputs)
    wall_loss = binary_dice_bce(torch.logit(p_wall.clamp(1.0e-4, 1.0 - 1.0e-4)), wall_target, valid_binary)
    distance_loss = (
        _masked_mean_loss(F.smooth_l1_loss(outputs["signed_endo_distance"], built_targets["signed_endo_distance"], reduction="none"), built_targets["geometry_valid"])
        + _masked_mean_loss(F.smooth_l1_loss(outputs["signed_epi_distance"], built_targets["signed_epi_distance"], reduction="none"), built_targets["geometry_valid"])
        + _masked_mean_loss(F.smooth_l1_loss(outputs["wall_depth_rho"], built_targets["wall_depth_rho"], reduction="none"), built_targets["geometry_valid"])
    ) / 3.0
    scar_full = binary_dice_focal(outputs["z_scar"], scar_target, valid_binary, alpha=0.25, gamma=2.0)
    scar_half_logit = F.interpolate(outputs["scar"]["half_logits6"][:, 5:6], size=target.shape[-3:], mode="trilinear", align_corners=False)
    scar_half_dense = binary_dice_focal(scar_half_logit, scar_target, valid_binary, alpha=0.25, gamma=2.0)
    scar_dense = 0.5 * scar_full + 0.5 * scar_half_dense
    edema_full = binary_dice_focal(outputs["z_pure_edema"], edema_target, edema_valid, alpha=0.35, gamma=2.0)
    edema_half_logit = F.interpolate(outputs["edema"]["half_logits6"][:, 4:5], size=target.shape[-3:], mode="trilinear", align_corners=False)
    edema_half_dense = binary_dice_focal(edema_half_logit, edema_target, edema_valid, alpha=0.35, gamma=2.0)
    edema_dense = 0.5 * edema_full + 0.5 * edema_half_dense
    scar_half = F.interpolate(outputs["scar"]["half_logits6"][:, 5:6], size=target.shape[-3:], mode="trilinear", align_corners=False)
    edema_half = F.interpolate(outputs["edema"]["half_logits6"][:, 4:5], size=target.shape[-3:], mode="trilinear", align_corners=False)
    scar_component = per_gt_component_tversky(scar_half, scar_target.float(), valid_binary)
    scar_occ_quarter = _downsample_target(scar_target, components["scar_quarter_occupancy"].shape[-3:])
    scar_occ_half = _downsample_target(scar_target, components["scar_half_occupancy"].shape[-3:])
    scar_center = 0.5 * binary_dice_focal(components["scar_quarter_center"], built_targets["scar_center_quarter"], None, alpha=0.25, gamma=2.0) + 0.5 * binary_dice_focal(components["scar_half_center"], built_targets["scar_center_half"], None, alpha=0.25, gamma=2.0)
    scar_occupancy = 0.5 * binary_dice_focal(components["scar_quarter_occupancy"], scar_occ_quarter, None, alpha=0.25, gamma=2.0) + 0.5 * binary_dice_focal(components["scar_half_occupancy"], scar_occ_half, None, alpha=0.25, gamma=2.0)
    edema_boundary_target = torch.from_numpy(
        np.stack([_signed_distance((item.detach().cpu().numpy() == 4), clip=10.0) for item in target])
    )[:, None].to(device=logits.device, dtype=logits.dtype)
    edema_boundary_valid = ((edema_boundary_target.abs() <= 1.0) | edema_target).to(logits) * t2_mask
    edema_boundary = _masked_mean_loss(F.smooth_l1_loss(torch.tanh(edema_half), edema_boundary_target, reduction="none"), edema_boundary_valid)
    injury_logit = F.interpolate(components["edema_injury"], size=target.shape[-3:], mode="trilinear", align_corners=False)
    injury = binary_dice_focal(injury_logit, injury_target, edema_valid, alpha=0.35, gamma=2.0)
    scar_presence = F.binary_cross_entropy_with_logits(components["scar_extent_presence"].mean(dim=(-3, -2, -1)), (scar_target.flatten(1).any(1)).float().unsqueeze(1))
    edema_presence_raw = F.binary_cross_entropy_with_logits(components["edema_extent_presence"].mean(dim=(-3, -2, -1)), (edema_target.flatten(1).any(1)).float().unsqueeze(1), reduction="none")
    edema_presence = (edema_presence_raw * availability[:, 1:2]).sum() / availability[:, 1:2].sum().clamp_min(1.0)
    scar_area = F.smooth_l1_loss(torch.sigmoid(components["scar_extent_area"]).mean(dim=(-3, -2, -1)), scar_target.float().mean(dim=(-3, -2, -1)))
    edema_area_raw = F.smooth_l1_loss(torch.sigmoid(components["edema_extent_area"]).mean(dim=(-3, -2, -1)), edema_target.float().mean(dim=(-3, -2, -1)), reduction="none")
    edema_area = (edema_area_raw * availability[:, 1:2]).sum() / availability[:, 1:2].sum().clamp_min(1.0)
    scar_context_target = _downsample_target(built_targets["scar_context_target"].unsqueeze(1), components["scar_context"].shape[-3:]).squeeze(1)
    edema_context_target = _downsample_target(built_targets["edema_context_target"].unsqueeze(1), components["edema_context"].shape[-3:]).squeeze(1)
    scar_context = F.cross_entropy(components["scar_context"], scar_context_target, ignore_index=-1)
    edema_context_raw = F.cross_entropy(components["edema_context"], edema_context_target, ignore_index=-1, reduction="none")
    edema_context = (edema_context_raw * availability[:, 1].view(-1, 1, 1, 1)).sum() / availability[:, 1].sum().clamp_min(1.0)
    relation = F.relu(outputs["z_scar"].detach().sigmoid() + outputs["z_pure_edema"].sigmoid().detach() - torch.sigmoid(injury_logit)).mul(edema_valid).sum() / edema_valid.sum().clamp_min(1.0)
    zero = logits.sum() * 0.0
    if not final_terms:
        final_terms.append(zero)
    scar_extent = 0.5 * scar_presence + 0.5 * scar_area
    edema_extent = 0.5 * edema_presence + 0.5 * edema_area
    weighted_terms = {
        "final_competition": REQUIRED_LOSS_WEIGHTS["final_competition"] * torch.stack(final_terms).mean(),
        "anatomy4": REQUIRED_LOSS_WEIGHTS["anatomy4"] * (anatomy_ce + anatomy_dice),
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


def set_stage_trainability(model: CAREASE, *, global_step: int) -> str:
    step = int(global_step)
    stage = "A" if step < model.config.stage_a_steps else "B" if step < model.config.stage_a_steps + model.config.stage_b_steps else "C"
    for name, param in model.named_parameters():
        trainable = True
        if stage == "A" and (name.startswith("encoder.") or name.startswith("low_mid_") or name.startswith("anatomy_decoder.")):
            trainable = False
        if stage == "B" and name.startswith("encoder.") and not _is_upper_encoder_parameter(name):
            trainable = False
        param.requires_grad_(trainable)
    return stage


def _is_upper_encoder_parameter(name: str) -> bool:
    return any(token in name for token in ("stages.4", "stages.5", "stages.6", "stages.7"))


def optimizer_parameter_groups(model: CAREASE) -> list[dict[str, Any]]:
    groups: dict[str, list[nn.Parameter]] = {name: [] for name in (
        "new_modules",
        "cloned_pathology_blocks",
        "cloned_pathology_classifiers",
        "anatomy_top",
        "shared_low_mid_decoder",
        "upper_two_encoder_stages",
        "lower_encoder_and_bottleneck",
    )}
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if name.startswith(("component_heads.", "scar_lge_adapter.", "scar_c0_adapter.", "edema_t2_adapter.", "edema_c0_adapter.")):
            groups["new_modules"].append(param)
        elif name.startswith(("scar_branch.seg_layers.", "edema_branch.seg_layers.")):
            groups["cloned_pathology_classifiers"].append(param)
        elif name.startswith(("scar_branch.", "edema_branch.")):
            groups["cloned_pathology_blocks"].append(param)
        elif name.startswith("anatomy_decoder.") and any(token in name for token in ("transpconvs.4", "transpconvs.5", "stages.4", "stages.5", "seg_layers.5")):
            groups["anatomy_top"].append(param)
        elif name.startswith(("low_mid_transpconvs.", "low_mid_stages.")):
            groups["shared_low_mid_decoder"].append(param)
        elif name.startswith("encoder.") and _is_upper_encoder_parameter(name):
            groups["upper_two_encoder_stages"].append(param)
        elif name.startswith("encoder."):
            groups["lower_encoder_and_bottleneck"].append(param)
        else:
            groups["new_modules"].append(param)
    lr = {
        "new_modules": 5.0e-4,
        "cloned_pathology_blocks": 1.0e-4,
        "cloned_pathology_classifiers": 2.0e-4,
        "anatomy_top": 1.0e-4,
        "shared_low_mid_decoder": 1.0e-4,
        "upper_two_encoder_stages": 5.0e-5,
        "lower_encoder_and_bottleneck": 1.0e-5,
    }
    return [{"name": name, "params": params, "lr": lr[name], "weight_decay": 1.0e-4} for name, params in groups.items() if params]


def build_optimizer(model: CAREASE) -> torch.optim.Optimizer:
    return torch.optim.AdamW(optimizer_parameter_groups(model))


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
            "anatomy_top": 1.0e-4,
            "shared_low_mid_decoder": 1.0e-4,
            "upper_two_encoder_stages": 5.0e-5,
        },
        "C": {
            "new_modules": 1.0e-4,
            "cloned_pathology_blocks": 5.0e-5,
            "cloned_pathology_classifiers": 5.0e-5,
            "anatomy_top": 5.0e-5,
            "shared_low_mid_decoder": 5.0e-5,
            "upper_two_encoder_stages": 5.0e-5,
            "lower_encoder_and_bottleneck": 1.0e-5,
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
    precision_mode: str = "fp32_guarded_mixed_precision_allowed",
) -> None:
    rng = capture_rng_state()
    sampler_state = dict(sampler_state or {})
    next_sha = str(next_batch_hash or sampler_state.get("next_batch_descriptor_sha256", "UNSET"))
    config_payload = asdict(model.config)
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict() if scheduler is not None else {"last_global_step": int(global_step), "type": "CAREASEStageScheduler"},
        "precision_mode": precision_mode,
        "global_optimizer_step": int(global_step),
        "stage_id": str(stage_id),
        "stage_step": int(global_step) - CAREASEStageScheduler.stage_ranges.get(str(stage_id), (0, 0))[0],
        "accumulation_microbatch_cursor": int(microbatch_cursor),
        "python_rng": rng["python"],
        "numpy_rng": rng["numpy"],
        "torch_cpu_rng": rng["torch_cpu"],
        "torch_cuda_rng_all_devices": rng["torch_cuda"],
        "dataloader_worker_seed_state": dataloader_worker_seed_state or {},
        "case_group_cursor": int(sampler_state.get("case_group_cursor", 0)),
        "center_cursor": int(sampler_state.get("center_cursor", 0)),
        "pathology_focus_cursor": int(sampler_state.get("pathology_focus_cursor", 0)),
        "scar_focus_cursor": int(sampler_state.get("scar_focus_cursor", 0)),
        "edema_focus_cursor": int(sampler_state.get("edema_focus_cursor", 0)),
        "sampler_rng_state": sampler_state.get("sampler_rng_state", {}),
        "batch_descriptor_cursor": int(sampler_state.get("batch_descriptor_cursor", 0)),
        "next_batch_descriptor_sha256": next_sha,
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
    payload = torch.load(path, map_location=map_location, weights_only=False)
    if int(payload.get("schema_version", 0)) != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(f"unsupported CARE-ASE checkpoint schema_version: {payload.get('schema_version')}")
    missing = [field for field in REQUIRED_CHECKPOINT_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"CARE-ASE checkpoint missing required fields: {missing}")
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
        "extent_wall_ramp_value": float(payload["extent_wall_ramp_value"]),
        "next_batch_hash": payload["next_batch_descriptor_sha256"],
        "has_optimizer_state": "optimizer" in payload,
        "has_scheduler_state": "scheduler" in payload,
        "has_rng_state": all(k in payload for k in ("python_rng", "numpy_rng", "torch_cpu_rng", "torch_cuda_rng_all_devices")),
        "required_fields_present": all(field in payload for field in REQUIRED_CHECKPOINT_FIELDS),
        "checkpoint_sha256": _sha256_file_or_missing(path),
        "fixed_terminal_step14000": int(payload["global_optimizer_step"]) == 14000,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
