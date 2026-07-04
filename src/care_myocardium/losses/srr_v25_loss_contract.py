"""Preflight SRR-v2.5 loss contract helpers for CARE MyoPS."""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F

from src.care_myocardium.anchors.myops_decode import canonical_t2_present, count_no_t2_edema_voxels, decode_compact_logits
from src.care_myocardium.losses.srr_losses import EDEMA_CLASS, IGNORE_LABEL, SCAR_CLASS, anatomy_loss, retrieval_regularization


@dataclass(frozen=True)
class SRRV25LossWeights:
    anatomy: float = 1.0
    scar_refine: float = 1.4
    scar_proposal: float = 0.9
    scar_precision: float = 0.7
    scar_boundary: float = 0.25
    scar_remote_fp: float = 0.35
    edema_refine: float = 1.0
    edema_proposal: float = 0.7
    edema_boundary: float = 0.20
    edema_uncertainty: float = 0.05
    prototype_margin: float = 0.45
    soft_roi: float = 0.20
    retrieval: float = 0.25


def _valid(labels: torch.Tensor) -> torch.Tensor:
    return labels != IGNORE_LABEL


def _masked_mean(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    mask_f = mask.to(device=values.device, dtype=values.dtype)
    return (values * mask_f).sum() / mask_f.sum().clamp_min(1.0)


def _masked_bce_dice(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor, *, fp_weight: float = 1.0) -> torch.Tensor:
    target_f = target.to(device=logits.device, dtype=logits.dtype)
    mask_f = mask.to(device=logits.device, dtype=logits.dtype)
    weight = torch.where(target_f > 0.5, torch.ones_like(target_f), torch.full_like(target_f, float(fp_weight)))
    bce = F.binary_cross_entropy_with_logits(logits, target_f, reduction="none")
    bce = (bce * weight * mask_f).sum() / (weight * mask_f).sum().clamp_min(1.0)
    prob = torch.sigmoid(logits)
    axes = tuple(range(1, prob.ndim))
    inter = (prob * target_f * mask_f).sum(dim=axes)
    denom = (prob * mask_f).sum(dim=axes) + (target_f * mask_f).sum(dim=axes)
    dice = (1.0 - (2.0 * inter + 1e-6) / (denom + 1e-6)).mean()
    return 0.5 * bce + 0.5 * dice


def _boundary_surrogate(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    prob = torch.sigmoid(logits)
    target_f = target.to(device=prob.device, dtype=prob.dtype)
    mask_f = mask.to(device=prob.device, dtype=prob.dtype)
    if min(prob.shape[-3:]) < 3:
        return prob.sum() * 0.0
    prob_edge = (prob - F.avg_pool3d(prob[:, None], kernel_size=3, stride=1, padding=1)[:, 0]).abs()
    target_edge = (target_f - F.avg_pool3d(target_f[:, None], kernel_size=3, stride=1, padding=1)[:, 0]).abs()
    return _masked_mean((prob_edge - target_edge).abs(), mask_f)


def _outside_myocardium_mask(labels: torch.Tensor) -> torch.Tensor:
    valid = _valid(labels)
    anatomy = (labels >= 1) & (labels <= 5)
    return valid & (~anatomy)


def _blood_pool_mask(labels: torch.Tensor) -> torch.Tensor:
    return _valid(labels) & ((labels == 2) | (labels == 3))


def _normal_myo_mask(labels: torch.Tensor) -> torch.Tensor:
    return _valid(labels) & (labels == 1)


def _prototype_margin(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    availability: torch.Tensor,
    *,
    prefix: str,
    margin: float,
) -> torch.Tensor:
    pos_key = f"{prefix}_pos_similarity"
    neg_key = f"{prefix}_neg_similarity"
    if pos_key not in outputs or neg_key not in outputs:
        return outputs["logits"].sum() * 0.0
    pos = outputs[pos_key][:, 0]
    neg = outputs[neg_key][:, 0]
    valid = _valid(labels)
    if prefix == "scar":
        positive = valid & (labels == SCAR_CLASS)
        safe_negative = valid & (labels != SCAR_CLASS)
    elif prefix == "edema":
        t2 = canonical_t2_present(availability).to(device=labels.device).view(-1, 1, 1, 1)
        positive = valid & t2 & (labels == EDEMA_CLASS)
        safe_negative = valid & t2 & (labels != EDEMA_CLASS)
    else:
        raise ValueError(f"unknown prefix {prefix!r}")
    terms = []
    if bool(positive.any()):
        terms.append(_masked_mean(torch.relu(float(margin) - pos + neg), positive))
    if bool(safe_negative.any()):
        terms.append(_masked_mean(torch.relu(float(margin) + pos - neg), safe_negative))
    return torch.stack(terms).mean() if terms else outputs["logits"].sum() * 0.0


def _roi_loss(outputs: dict[str, torch.Tensor], labels: torch.Tensor, availability: torch.Tensor) -> torch.Tensor:
    valid = _valid(labels)
    terms = []
    if "scar_soft_roi" in outputs:
        scar_roi = outputs["scar_soft_roi"][:, 0].clamp(1e-4, 1.0 - 1e-4)
        terms.append(_masked_bce_dice(torch.logit(scar_roi), labels == SCAR_CLASS, valid, fp_weight=1.5))
    if "edema_soft_roi" in outputs:
        t2 = canonical_t2_present(availability).to(device=labels.device).view(-1, 1, 1, 1)
        edema_mask = valid & t2
        if bool(edema_mask.any()):
            edema_roi = outputs["edema_soft_roi"][:, 0].clamp(1e-4, 1.0 - 1e-4)
            terms.append(_masked_bce_dice(torch.logit(edema_roi), labels == EDEMA_CLASS, edema_mask, fp_weight=1.0))
    return torch.stack(terms).mean() if terms else outputs["logits"].sum() * 0.0


def srr_v25_preflight_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    availability: torch.Tensor,
    *,
    weights: SRRV25LossWeights | None = None,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Return named SRR-v2.5 preflight loss terms.

    The edema terms deliberately use only T2-present samples. No-T2 samples
    contribute neither edema positives nor edema negatives.
    """

    w = weights or SRRV25LossWeights()
    labels = labels.to(device=outputs["logits"].device)
    availability = availability.to(device=outputs["logits"].device, dtype=outputs["logits"].dtype)
    valid = _valid(labels)
    t2 = canonical_t2_present(availability).to(device=labels.device).view(-1, 1, 1, 1)

    scar_target = labels == SCAR_CLASS
    edema_target = labels == EDEMA_CLASS
    edema_mask = valid & t2
    outside = _outside_myocardium_mask(labels)
    blood = _blood_pool_mask(labels)
    normal_myo = _normal_myo_mask(labels)

    scar_logits = outputs["scar_logits"][:, 0]
    edema_logits = outputs["edema_logits"][:, 0]
    scar_proposal = outputs.get("scar_proposal_logits", outputs["scar_logits"])[:, 0]
    edema_proposal = outputs.get("edema_proposal_logits", outputs["edema_logits"])[:, 0]

    terms: dict[str, torch.Tensor] = {
        "anatomy_dice_ce": anatomy_loss(outputs["anatomy_logits"], labels),
        "scar_refine_precision_bce_dice": _masked_bce_dice(scar_logits, scar_target, valid, fp_weight=2.5),
        "scar_proposal_precision_bce_dice": _masked_bce_dice(scar_proposal, scar_target, valid, fp_weight=3.0),
        "scar_boundary_surrogate": _boundary_surrogate(scar_logits, scar_target, valid),
        "scar_outside_myocardium_fp": _masked_mean(torch.sigmoid(scar_logits), outside) if bool(outside.any()) else scar_logits.sum() * 0.0,
        "scar_blood_pool_fp": _masked_mean(torch.sigmoid(scar_logits), blood) if bool(blood.any()) else scar_logits.sum() * 0.0,
        "scar_normal_myo_fp": _masked_mean(torch.sigmoid(scar_logits), normal_myo & (~scar_target)) if bool((normal_myo & (~scar_target)).any()) else scar_logits.sum() * 0.0,
        "scar_positive_negative_margin": _prototype_margin(outputs, labels, availability, prefix="scar", margin=0.35),
        "edema_refine_t2_masked_bce_dice": _masked_bce_dice(edema_logits, edema_target, edema_mask, fp_weight=1.0) if bool(edema_mask.any()) else edema_logits.sum() * 0.0,
        "edema_proposal_t2_masked_bce_dice": _masked_bce_dice(edema_proposal, edema_target, edema_mask, fp_weight=1.0) if bool(edema_mask.any()) else edema_logits.sum() * 0.0,
        "edema_boundary_context_surrogate": _boundary_surrogate(edema_logits, edema_target, edema_mask) if bool(edema_mask.any()) else edema_logits.sum() * 0.0,
        "edema_positive_negative_margin": _prototype_margin(outputs, labels, availability, prefix="edema", margin=0.25),
        "soft_roi_containment": _roi_loss(outputs, labels, availability),
    }

    retrieval, retrieval_metrics = retrieval_regularization(
        outputs.get("gates", {}),
        entropy_floor=0.55,
        entropy_weight=0.04,
        coverage_weight=0.04,
        max_weight_penalty=0.02,
    )
    terms["dictionary_entropy_load_balance"] = retrieval if retrieval is not None else outputs["logits"].sum() * 0.0

    decoded = decode_compact_logits(outputs["logits"], availability, policy="block_edema")
    metrics: dict[str, torch.Tensor] = {
        **terms,
        **retrieval_metrics,
        "no_T2_edema_voxels": outputs["logits"].new_tensor(float(count_no_t2_edema_voxels(decoded, availability))),
        "edema_t2_supervised_voxels": outputs["logits"].new_tensor(float(edema_mask.sum().detach().cpu().item())),
        "edema_no_t2_negative_voxels": outputs["logits"].new_tensor(0.0),
        "scar_remote_fp_proxy": terms["scar_outside_myocardium_fp"],
        "component_count_status": outputs["logits"].new_tensor(float("nan")),
        "hd95_status": outputs["logits"].new_tensor(float("nan")),
    }

    total = (
        w.anatomy * terms["anatomy_dice_ce"]
        + w.scar_refine * terms["scar_refine_precision_bce_dice"]
        + w.scar_proposal * terms["scar_proposal_precision_bce_dice"]
        + w.scar_precision
        * (terms["scar_outside_myocardium_fp"] + terms["scar_blood_pool_fp"] + terms["scar_normal_myo_fp"])
        + w.scar_boundary * terms["scar_boundary_surrogate"]
        + w.scar_remote_fp * terms["scar_outside_myocardium_fp"]
        + w.edema_refine * terms["edema_refine_t2_masked_bce_dice"]
        + w.edema_proposal * terms["edema_proposal_t2_masked_bce_dice"]
        + w.edema_boundary * terms["edema_boundary_context_surrogate"]
        + w.prototype_margin * (terms["scar_positive_negative_margin"] + terms["edema_positive_negative_margin"])
        + w.soft_roi * terms["soft_roi_containment"]
        + w.retrieval * terms["dictionary_entropy_load_balance"]
    )
    return total, metrics
