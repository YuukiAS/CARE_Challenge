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


def _binary_boundary(mask: torch.Tensor) -> torch.Tensor:
    mask = mask.float()
    dil = F.max_pool3d(mask, 3, stride=1, padding=1)
    ero = -F.max_pool3d(-mask, 3, stride=1, padding=1)
    return (dil - ero).abs().clamp(0, 1)


def component_utility_target(anchor_local: torch.Tensor, refined_prob: torch.Tensor, gt: torch.Tensor, distance_to_reliable_gt: torch.Tensor | None = None, candidate_mask: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """Component-level amendment utility target broadcast over candidate support.

    E(M)=2*FN+1*FP+0.25*boundary_error and
    U=clip((E(A)-E(R))/max(|A union R union G|,1),-1,1).
    The returned maps are constant over the candidate support so training uses a
    component descriptor MLP instead of a dense voxel utility surrogate.
    """
    refined = (refined_prob.detach() >= 0.5).to(gt.dtype)
    anchor = anchor_local.detach().to(gt.dtype)
    gt = gt.detach().to(gt.dtype)
    candidate_support = ((anchor + refined + gt) > 0).to(gt.dtype)
    if candidate_mask is not None:
        candidate_support = candidate_support * candidate_mask.detach().to(gt.dtype).clamp(0, 1)
    accept_map = torch.zeros_like(gt)
    utility_map = torch.zeros_like(gt)
    for b in range(gt.shape[0]):
        support = candidate_support[b : b + 1]
        denom = support.sum().clamp_min(1.0)
        a = anchor[b : b + 1]
        r = refined[b : b + 1]
        g = gt[b : b + 1]
        fn_a = ((g > 0.5) & (a <= 0.5)).float().sum()
        fp_a = ((g <= 0.5) & (a > 0.5)).float().sum()
        fn_r = ((g > 0.5) & (r <= 0.5)).float().sum()
        fp_r = ((g <= 0.5) & (r > 0.5)).float().sum()
        boundary_a = (_binary_boundary(a) != _binary_boundary(g)).float().sum()
        boundary_r = (_binary_boundary(r) != _binary_boundary(g)).float().sum()
        e_anchor = 2.0 * fn_a + fp_a + 0.25 * boundary_a
        e_refined = 2.0 * fn_r + fp_r + 0.25 * boundary_r
        utility = torch.clamp((e_anchor - e_refined) / denom, -1.0, 1.0)
        accept = (utility >= ACCEPT_MIN_UTILITY).float()
        gt_positive_empty = bool((g.sum() > 0) and (r.sum() == 0))
        if gt_positive_empty:
            accept = torch.zeros_like(accept)
            utility = torch.full_like(utility, -1.0)
        if distance_to_reliable_gt is not None:
            dist = distance_to_reliable_gt[b : b + 1].detach().to(gt.dtype)
            new_remote = ((r > 0.5) & (a <= 0.5) & (dist > REMOTE_REJECT_MM)).any()
            if bool(new_remote):
                accept = torch.zeros_like(accept)
                utility = torch.minimum(utility, torch.full_like(utility, -1.0))
        accept_map[b : b + 1] = accept.view(1, 1, 1, 1, 1) * support
        utility_map[b : b + 1] = utility.view(1, 1, 1, 1, 1) * support
    return accept_map.detach(), utility_map.detach()


# Backward-compatible alias used by earlier evidence scripts; implementation is component-level.
dense_utility_target = component_utility_target


def care_dpr_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    anchor_mask: torch.Tensor,
    *,
    t2_present: torch.Tensor,
    scar_reliable: torch.Tensor | None = None,
    edema_reliable: torch.Tensor | None = None,
    containment_weight: float = 0.1,
    batch_candidates: dict[str, Any] | None = None,
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

    scar_candidate_mask = None
    edema_candidate_mask = None
    distance_to_gt = outputs.get("distance_to_myocardium")
    if batch_candidates is not None and "primary_candidate_mask" in batch_candidates:
        cmask = batch_candidates["primary_candidate_mask"].to(device=final_logits.device, dtype=final_logits.dtype)
        pathologies = list(batch_candidates.get("primary_candidate_pathology", []))
        if pathologies:
            scar_case = torch.tensor([1.0 if p == "scar" else 0.0 for p in pathologies], device=final_logits.device, dtype=final_logits.dtype)[:, None, None, None, None]
            edema_case = torch.tensor([1.0 if p == "edema_zone" else 0.0 for p in pathologies], device=final_logits.device, dtype=final_logits.dtype)[:, None, None, None, None]
            scar_candidate_mask = cmask * scar_case
            edema_candidate_mask = cmask * edema_case
        distance_to_gt = batch_candidates.get("distance_to_reliable_gt", distance_to_gt)
        if isinstance(distance_to_gt, torch.Tensor):
            distance_to_gt = distance_to_gt.to(device=final_logits.device, dtype=final_logits.dtype)
    scar_accept_target, scar_utility_target = component_utility_target(targets["scar_anchor"], outputs["scar_p_refined"], targets["scar_gt"], distance_to_gt, scar_candidate_mask)
    edema_accept_target, edema_utility_target = component_utility_target(targets["edema_anchor"], outputs["edema_p_refined"], targets["edema_gt"], distance_to_gt, edema_candidate_mask)
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


def save_care_dpr_checkpoint(path: Path, model: CAREDPR, optimizer: torch.optim.Optimizer, step: int, extra: dict[str, Any] | None = None, *, local_rng: random.Random | None = None, stage: str | None = None, local_step: int | None = None, sampler_slot_cursor: int = 0, hard_negative_subtype_cursor: dict[str, int] | None = None, teacher_roi_schedule_cursor: int = 0, resolved_training_contract_hash: str = "") -> None:
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
            "optimizer_stage": stage,
            "local_step": local_step,
            "total_step": int(step),
            "sampler_slot_cursor": int(sampler_slot_cursor),
            "hard_negative_subtype_cursor": dict(hard_negative_subtype_cursor or {"scar": 0, "edema_zone": 0}),
            "teacher_roi_schedule_cursor": int(teacher_roi_schedule_cursor),
            "resolved_training_contract_hash": str(resolved_training_contract_hash),
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
        "random_initialized_modules": ["scar_branch.local_refiner", "scar_branch.component_utility", "edema_branch.local_refiner", "edema_branch.component_utility", "scar_branch.proposal_head.p_coarse", "edema_branch.proposal_head.p_coarse"],
    }
