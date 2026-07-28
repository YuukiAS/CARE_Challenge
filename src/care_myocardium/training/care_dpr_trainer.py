"""Training losses and checkpoint helpers for CARE-DPR."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import random
import numpy as np
import torch
import torch.nn.functional as F

from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.models.care_dpr import CAREDPR, CAREDPRConfig, edema_zone_margin, pathology_margin
from src.care_myocardium.training.care_dg_trainer import (
    _restore_rng_payload,
    binary_dice_loss,
    focal_bce,
    masked_bce_with_logits,
    masked_mean,
)

UTILITY_THRESHOLD_CANDIDATES = (0.30, 0.40, 0.50, 0.60, 0.70)
ACCEPT_MIN_UTILITY = 0.02
REMOTE_REJECT_MM = 20.0


def _squeeze_labels(x: torch.Tensor) -> torch.Tensor:
    return x[:, 0] if x.ndim == 5 else x


def _case_mask(mask: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    if mask.ndim == 1:
        mask = mask[:, None, None, None, None]
    elif mask.ndim == 2:
        mask = mask[:, :1, None, None, None]
    return mask.to(device=reference.device, dtype=reference.dtype).expand(-1, 1, *reference.shape[-3:])


def dpr_targets(labels: torch.Tensor, anchor_mask: torch.Tensor) -> dict[str, torch.Tensor]:
    labels = _squeeze_labels(labels)
    anchor_mask = _squeeze_labels(anchor_mask)
    scar_gt = labels == SCAR_CHANNEL
    scar_pred = anchor_mask == SCAR_CHANNEL
    zone_gt = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
    zone_pred = (anchor_mask == SCAR_CHANNEL) | (anchor_mask == EDEMA_CHANNEL)
    return {
        "scar_gt": scar_gt.float().unsqueeze(1),
        "scar_fn": (scar_gt & ~scar_pred).float().unsqueeze(1),
        "scar_fp": (~scar_gt & scar_pred).float().unsqueeze(1),
        "edema_gt": zone_gt.float().unsqueeze(1),
        "edema_fn": (zone_gt & ~zone_pred).float().unsqueeze(1),
        "edema_fp": (~zone_gt & zone_pred).float().unsqueeze(1),
        "scar_anchor": scar_pred.float().unsqueeze(1),
        "edema_anchor": zone_pred.float().unsqueeze(1),
    }


def dense_utility_target(anchor_local: torch.Tensor, refined_prob: torch.Tensor, gt: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Dense surrogate for amendment utility target, bounded to [-1, 1].

    The full component target is built during full-volume candidate arbitration.
    For patch training this computes the same E(A)-E(R) semantics per voxel and
    is used only on actual-train batches.
    """
    refined = (refined_prob.detach() >= 0.5).to(gt.dtype)
    anchor = anchor_local.detach().to(gt.dtype)
    gt = gt.detach().to(gt.dtype)
    fn_anchor = ((gt > 0.5) & (anchor <= 0.5)).float()
    fp_anchor = ((gt <= 0.5) & (anchor > 0.5)).float()
    fn_refined = ((gt > 0.5) & (refined <= 0.5)).float()
    fp_refined = ((gt <= 0.5) & (refined > 0.5)).float()
    e_anchor = 2.0 * fn_anchor + fp_anchor
    e_refined = 2.0 * fn_refined + fp_refined
    utility = torch.clamp(e_anchor - e_refined, -1.0, 1.0)
    accept = (utility >= ACCEPT_MIN_UTILITY).float()
    gt_positive_empty = ((gt.flatten(2).sum(dim=2) > 0) & (refined.flatten(2).sum(dim=2) == 0)).view(gt.shape[0], 1, 1, 1, 1)
    accept = torch.where(gt_positive_empty, torch.zeros_like(accept), accept)
    utility = torch.where(gt_positive_empty, torch.full_like(utility, -1.0), utility)
    return accept.detach(), utility.detach()


def care_dpr_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    anchor_mask: torch.Tensor,
    *,
    t2_present: torch.Tensor,
    scar_reliable: torch.Tensor | None = None,
    edema_reliable: torch.Tensor | None = None,
    containment_weight: float = 0.1,
) -> tuple[torch.Tensor, dict[str, float]]:
    final_logits = outputs["final_logits"].float()
    anchor_logits = outputs["anchor_logits"].detach().float()
    if scar_reliable is None:
        scar_reliable = torch.ones_like(t2_present)
    if edema_reliable is None:
        edema_reliable = t2_present
    scar_mask = _case_mask(scar_reliable, final_logits)
    edema_mask = _case_mask(edema_reliable, final_logits)
    targets = dpr_targets(labels, anchor_mask)

    scar_final_margin = pathology_margin(final_logits, SCAR_CHANNEL)
    scar_anchor_margin = pathology_margin(anchor_logits, SCAR_CHANNEL)
    edema_final_margin = edema_zone_margin(final_logits)
    edema_anchor_margin = edema_zone_margin(anchor_logits)

    scar_coarse = binary_dice_loss(outputs["scar_p_coarse_logit"].float(), targets["scar_gt"], scar_mask) + masked_bce_with_logits(outputs["scar_p_coarse_logit"].float(), targets["scar_gt"], scar_mask)
    edema_coarse = binary_dice_loss(outputs["edema_p_coarse_logit"].float(), targets["edema_gt"], edema_mask) + masked_bce_with_logits(outputs["edema_p_coarse_logit"].float(), targets["edema_gt"], edema_mask)
    scar_refine = binary_dice_loss(outputs["scar_refined_logit"].float(), targets["scar_gt"], scar_mask * outputs["scar_training_roi"].detach().clamp(0, 1)) + masked_bce_with_logits(outputs["scar_refined_logit"].float(), targets["scar_gt"], scar_mask * outputs["scar_training_roi"].detach().clamp(0, 1))
    edema_refine = binary_dice_loss(outputs["edema_refined_logit"].float(), targets["edema_gt"], edema_mask * outputs["edema_training_roi"].detach().clamp(0, 1)) + masked_bce_with_logits(outputs["edema_refined_logit"].float(), targets["edema_gt"], edema_mask * outputs["edema_training_roi"].detach().clamp(0, 1))
    scar_prop = focal_bce(outputs["scar_q_fn"].float(), targets["scar_fn"], scar_mask) + focal_bce(outputs["scar_q_fp"].float(), targets["scar_fp"], scar_mask)
    edema_prop = focal_bce(outputs["edema_q_fn"].float(), targets["edema_fn"], edema_mask) + focal_bce(outputs["edema_q_fp"].float(), targets["edema_fp"], edema_mask)

    scar_accept_target, scar_utility_target = dense_utility_target(targets["scar_anchor"], outputs["scar_p_refined"], targets["scar_gt"])
    edema_accept_target, edema_utility_target = dense_utility_target(targets["edema_anchor"], outputs["edema_p_refined"], targets["edema_gt"])
    scar_util = masked_bce_with_logits(outputs["scar_utility_accept_logit"].float(), scar_accept_target, scar_mask) + F.huber_loss(outputs["scar_utility_regression"].float() * scar_mask, scar_utility_target * scar_mask, reduction="sum") / scar_mask.sum().clamp_min(1.0)
    edema_util = masked_bce_with_logits(outputs["edema_utility_accept_logit"].float(), edema_accept_target, edema_mask) + F.huber_loss(outputs["edema_utility_regression"].float() * edema_mask, edema_utility_target * edema_mask, reduction="sum") / edema_mask.sum().clamp_min(1.0)

    scar_boundary = masked_mean((scar_final_margin - scar_anchor_margin).abs(), (targets["scar_fn"] + targets["scar_fp"]).clamp(0, 1) * scar_mask)
    edema_boundary = masked_mean((edema_final_margin - edema_anchor_margin).abs(), (targets["edema_fn"] + targets["edema_fp"]).clamp(0, 1) * edema_mask)
    correct = (_squeeze_labels(labels) == _squeeze_labels(anchor_mask)).float().unsqueeze(1)
    identity = masked_mean(outputs["scar_delta"].abs(), correct * scar_mask) + masked_mean(outputs["edema_delta"].abs(), correct * edema_mask)
    remote = masked_mean(outputs["scar_delta"].abs(), (1.0 - outputs["scar_support"]) * scar_mask) + masked_mean(outputs["edema_delta"].abs(), (1.0 - outputs["edema_support"]) * edema_mask)
    containment = masked_mean(F.relu(outputs["scar_p_refined"].float() - outputs["edema_p_refined"].float()), edema_mask)

    scar_active = scar_coarse + scar_refine + 0.5 * scar_prop + 0.5 * scar_util
    edema_active = edema_coarse + edema_refine + 0.5 * edema_prop + 0.5 * edema_util
    total = scar_active + edema_active + 0.1 * (scar_boundary + edema_boundary) + 0.1 * identity + 0.1 * remote + float(containment_weight) * containment
    metrics = {
        "loss": float(total.detach().cpu()),
        "scar_active_loss": float(scar_active.detach().cpu()),
        "edema_active_loss": float(edema_active.detach().cpu()),
        "scar_p_coarse": float(scar_coarse.detach().cpu()),
        "edema_p_coarse": float(edema_coarse.detach().cpu()),
        "scar_refiner": float(scar_refine.detach().cpu()),
        "edema_refiner": float(edema_refine.detach().cpu()),
        "scar_proposal": float(scar_prop.detach().cpu()),
        "edema_proposal": float(edema_prop.detach().cpu()),
        "scar_utility": float(scar_util.detach().cpu()),
        "edema_utility": float(edema_util.detach().cpu()),
        "containment": float(containment.detach().cpu()),
        "identity": float(identity.detach().cpu()),
        "remote": float(remote.detach().cpu()),
    }
    return total, metrics


def save_care_dpr_checkpoint(path: Path, model: CAREDPR, optimizer: torch.optim.Optimizer, step: int, extra: dict[str, Any] | None = None, *, local_rng: random.Random | None = None, stage: str | None = None, local_step: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "step": int(step),
        "config": model.config.__dict__,
        "extra": dict(extra or {}),
        "runtime_state": {
            "python_random_state": random.getstate(),
            "local_random_state": local_rng.getstate() if local_rng is not None else None,
            "numpy_random_state": np.random.get_state(),
            "torch_cpu_rng_state": torch.get_rng_state(),
            "torch_cuda_rng_states": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
            "stage": stage,
            "local_step": local_step,
            "total_step": int(step),
        },
    }, path)


def load_care_dpr_checkpoint(path: Path, model: CAREDPR | None = None, optimizer: torch.optim.Optimizer | None = None, *, local_rng: random.Random | None = None, restore_rng: bool = False) -> tuple[CAREDPR, int, dict[str, Any]]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if model is None:
        model = CAREDPR(CAREDPRConfig(**payload["config"]))
    model.load_state_dict(payload["model_state"])
    if optimizer is not None and payload.get("optimizer_state") is not None:
        optimizer.load_state_dict(payload["optimizer_state"])
    runtime_state = dict(payload.get("runtime_state") or {})
    if restore_rng:
        _restore_rng_payload(runtime_state, local_rng)
    extra = dict(payload.get("extra") or {})
    extra["runtime_state"] = runtime_state
    return model, int(payload.get("step", 0)), extra


def initialize_from_care_dg(model: CAREDPR, checkpoint_path: Path) -> dict[str, Any]:
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    source = payload["model_state"]
    target = model.state_dict()
    remapped: dict[str, torch.Tensor] = {}
    skipped: list[str] = []
    for key, value in source.items():
        if key in target and target[key].shape == value.shape:
            remapped[key] = value
        else:
            skipped.append(key)
    # CARE-DG proposal head order was q_fn, q_fp, m_fn, m_fp. DPR keeps q_fn/q_fp
    # as error proposal only; p_coarse stays randomly initialized by design.
    mapping = {
        "scar_branch.proposal_head.weight": "scar_decoder.head.weight",
        "scar_branch.proposal_head.bias": "scar_decoder.head.bias",
        "edema_branch.proposal_head.weight": "edema_decoder.head.weight",
        "edema_branch.proposal_head.bias": "edema_decoder.head.bias",
    }
    for dst, src in mapping.items():
        if src in source and dst in target:
            src_tensor = source[src]
            dst_tensor = target[dst].clone()
            if src_tensor.shape[0] >= 2 and dst_tensor.shape[0] == 3 and dst_tensor.shape[1:] == src_tensor.shape[1:]:
                dst_tensor[1:3] = src_tensor[:2]
                remapped[dst] = dst_tensor
    target.update(remapped)
    model.load_state_dict(target)
    copied = sorted(remapped)
    return {
        "source_checkpoint_path": str(checkpoint_path),
        "source_step": int(payload.get("step", 0)),
        "copied_parameter_count": len(copied),
        "copied_parameters": copied,
        "skipped_source_parameter_count": len(skipped),
        "care_dg_q_fn_q_fp_initialize_error_proposal_only": True,
        "p_coarse_random_initialized": True,
        "random_initialized_modules": ["scar_branch.refiner_head", "scar_branch.utility_head", "edema_branch.refiner_head", "edema_branch.utility_head", "scar_branch.proposal_head.p_coarse", "edema_branch.proposal_head.p_coarse"],
    }
