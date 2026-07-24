"""Resolved lightweight loss formulas for CARE SRR cascade rescue."""

from __future__ import annotations

import torch
from torch.nn import functional as F


IGNORE_LABEL = -1
EDEMA_CHANNEL = 4
SCAR_CHANNEL = 5


def pathology_margin(final_logits: torch.Tensor, class_index: int) -> torch.Tensor:
    keep = [idx for idx in range(final_logits.shape[1]) if idx != int(class_index)]
    return final_logits[:, int(class_index) : int(class_index) + 1] - torch.logsumexp(final_logits[:, keep], dim=1, keepdim=True)


def _target(labels: torch.Tensor, class_index: int) -> torch.Tensor:
    return (labels == int(class_index)).to(dtype=torch.float32).unsqueeze(1)


def _valid(labels: torch.Tensor, like: torch.Tensor) -> torch.Tensor:
    return (labels != IGNORE_LABEL).to(device=like.device, dtype=like.dtype).unsqueeze(1)


def _masked_mean(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    weights = mask.to(device=values.device, dtype=values.dtype)
    return (values * weights).sum() / weights.sum().clamp_min(1.0)


def soft_dice_loss(prob: torch.Tensor, target: torch.Tensor, mask: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    weights = mask.to(device=prob.device, dtype=prob.dtype)
    prob = prob * weights
    target = target.to(device=prob.device, dtype=prob.dtype) * weights
    axes = tuple(range(1, prob.ndim))
    inter = (prob * target).sum(dim=axes)
    denom = prob.sum(dim=axes) + target.sum(dim=axes)
    return (1.0 - (2.0 * inter + eps) / (denom + eps)).mean()


def final_margin_bce_dice(
    final_logits: torch.Tensor,
    labels: torch.Tensor,
    class_index: int,
    mask: torch.Tensor | None = None,
) -> torch.Tensor:
    margin = pathology_margin(final_logits, class_index)
    target = _target(labels, class_index).to(device=final_logits.device)
    valid = _valid(labels, final_logits)
    if mask is not None:
        valid = valid * mask.to(device=final_logits.device, dtype=final_logits.dtype)
    bce = F.binary_cross_entropy_with_logits(margin, target, reduction="none")
    return _masked_mean(bce, valid) + soft_dice_loss(torch.sigmoid(margin), target, valid)


def anchor_error_directional(
    final_logits: torch.Tensor,
    anchor_logits: torch.Tensor,
    labels: torch.Tensor,
    class_index: int,
    mask: torch.Tensor | None = None,
) -> torch.Tensor:
    margin = pathology_margin(final_logits, class_index)
    anchor_pred = anchor_logits.argmax(dim=1, keepdim=True)
    target = labels.to(device=final_logits.device).unsqueeze(1)
    valid = _valid(labels, final_logits)
    if mask is not None:
        valid = valid * mask.to(device=final_logits.device, dtype=final_logits.dtype)
    false_negative = valid * ((target == int(class_index)) & (anchor_pred != int(class_index))).to(dtype=valid.dtype)
    false_positive = valid * ((target != int(class_index)) & (anchor_pred == int(class_index))).to(dtype=valid.dtype)
    return _masked_mean(F.softplus(-margin), false_negative) + _masked_mean(F.softplus(margin), false_positive)


def confident_anchor_preserve(
    final_logits: torch.Tensor,
    anchor_logits: torch.Tensor,
    labels: torch.Tensor,
    class_index: int,
    confidence_threshold: float = 0.80,
) -> torch.Tensor:
    probs = torch.softmax(anchor_logits.detach(), dim=1)
    conf, pred = probs.max(dim=1, keepdim=True)
    target = labels.to(device=final_logits.device).unsqueeze(1)
    mask = ((pred == target) & (conf >= float(confidence_threshold))).to(dtype=final_logits.dtype)
    raw = F.smooth_l1_loss(
        final_logits[:, int(class_index) : int(class_index) + 1],
        anchor_logits[:, int(class_index) : int(class_index) + 1].detach(),
        reduction="none",
    )
    return _masked_mean(raw, mask)


def scar_remote_fp_suppression(
    final_logits: torch.Tensor,
    labels: torch.Tensor,
    distance_to_gt_union_mm: torch.Tensor,
) -> torch.Tensor:
    margin = pathology_margin(final_logits, SCAR_CHANNEL)
    target_not_scar = (labels.to(device=final_logits.device).unsqueeze(1) != SCAR_CHANNEL)
    far = distance_to_gt_union_mm.to(device=final_logits.device, dtype=final_logits.dtype) > 10.0
    valid = _valid(labels, final_logits)
    mask = valid * (target_not_scar & far).to(dtype=valid.dtype)
    return _masked_mean(F.softplus(margin), mask)


def surface_distance_surrogate(
    final_logits: torch.Tensor,
    labels: torch.Tensor,
    class_index: int,
    distance_to_gt_pathology_surface_mm: torch.Tensor,
    distance_cap_mm: float = 20.0,
) -> torch.Tensor:
    margin = pathology_margin(final_logits, class_index)
    target = _target(labels, class_index).to(device=final_logits.device)
    valid = _valid(labels, final_logits)
    distance_weight = (distance_to_gt_pathology_surface_mm.to(device=final_logits.device, dtype=final_logits.dtype) / float(distance_cap_mm)).clamp(0.0, 1.0)
    raw = (torch.sigmoid(margin) - target).abs() * distance_weight
    return _masked_mean(raw, valid)


def edema_zone_aux(
    edema_zone_aux_logit: torch.Tensor,
    labels: torch.Tensor,
    mask: torch.Tensor | None = None,
) -> torch.Tensor:
    target = ((labels == EDEMA_CHANNEL) | (labels == SCAR_CHANNEL)).to(device=edema_zone_aux_logit.device, dtype=edema_zone_aux_logit.dtype).unsqueeze(1)
    valid = _valid(labels, edema_zone_aux_logit)
    if mask is not None:
        valid = valid * mask.to(device=edema_zone_aux_logit.device, dtype=edema_zone_aux_logit.dtype)
    bce = F.binary_cross_entropy_with_logits(edema_zone_aux_logit, target, reduction="none")
    return _masked_mean(bce, valid) + soft_dice_loss(torch.sigmoid(edema_zone_aux_logit), target, valid)


def care_srr_cascade_rescue_loss_terms(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    *,
    anchor_logits: torch.Tensor | None = None,
    distance_to_gt_union_mm: torch.Tensor,
    distance_to_gt_pathology_surface_mm: torch.Tensor,
    t2_present_mask: torch.Tensor | None = None,
) -> dict[str, torch.Tensor]:
    final_logits = outputs["final_logits"] if "final_logits" in outputs else outputs["logits"]
    anchor = anchor_logits if anchor_logits is not None else outputs["anchor_logits"]
    edema_mask = t2_present_mask if t2_present_mask is not None else outputs.get("t2_present_mask")
    return {
        "scar_final_margin_bce_dice": final_margin_bce_dice(final_logits, labels, SCAR_CHANNEL),
        "edema_final_margin_bce_dice": final_margin_bce_dice(final_logits, labels, EDEMA_CHANNEL, edema_mask),
        "scar_anchor_error_directional": anchor_error_directional(final_logits, anchor, labels, SCAR_CHANNEL),
        "edema_anchor_error_directional": anchor_error_directional(final_logits, anchor, labels, EDEMA_CHANNEL, edema_mask),
        "scar_confident_anchor_preserve": confident_anchor_preserve(final_logits, anchor, labels, SCAR_CHANNEL),
        "edema_confident_anchor_preserve": confident_anchor_preserve(final_logits, anchor, labels, EDEMA_CHANNEL),
        "scar_remote_fp_suppression": scar_remote_fp_suppression(final_logits, labels, distance_to_gt_union_mm),
        "scar_surface_distance_surrogate": surface_distance_surrogate(final_logits, labels, SCAR_CHANNEL, distance_to_gt_pathology_surface_mm),
        "edema_surface_distance_surrogate": surface_distance_surrogate(final_logits, labels, EDEMA_CHANNEL, distance_to_gt_pathology_surface_mm),
        "edema_zone_aux": edema_zone_aux(outputs["edema_zone_aux_logit"], labels, edema_mask),
    }
