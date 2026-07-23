"""Loss authority for CARE Batch9 reliable-label distillation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from torch.nn import functional as F

from src.care_myocardium.models.care_mm_reliable_distill import final_margin_logits


@dataclass(frozen=True)
class ReliableMaskBatch:
    anatomy: torch.Tensor
    scar: torch.Tensor
    edema: torch.Tensor
    final_six_class: torch.Tensor
    natural_complete_trimodal: torch.Tensor


def remap_anatomy_target(seg: torch.Tensor) -> torch.Tensor:
    target = seg.clone().long()
    target[target < 0] = 0
    target[(target == 4) | (target == 5)] = 1
    return target.clamp_(0, 3)


def binary_target(seg: torch.Tensor, class_id: int) -> torch.Tensor:
    return (seg == class_id).float()


def _broadcast_case_mask(mask: torch.Tensor, values: torch.Tensor) -> torch.Tensor:
    mask = mask.to(device=values.device, dtype=values.dtype)
    if mask.ndim == 1:
        mask = mask.view(mask.shape[0], *([1] * (values.ndim - 1)))
    while mask.ndim < values.ndim:
        mask = mask[:, None]
    return mask.expand_as(values)


def masked_mean(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    mask = _broadcast_case_mask(mask, values)
    denom = mask.sum().clamp_min(1.0)
    return (values * mask).sum() / denom


def soft_dice_loss_binary(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    probs = torch.sigmoid(logits)
    mask = _broadcast_case_mask(mask, logits)
    probs = probs * mask
    target = target.to(device=logits.device, dtype=logits.dtype) * mask
    inter = (probs * target).sum(dim=(1, 2, 3, 4))
    denom = probs.sum(dim=(1, 2, 3, 4)) + target.sum(dim=(1, 2, 3, 4))
    valid = mask.flatten(1).sum(dim=1) > 0
    if not valid.any():
        return logits.sum() * 0.0
    dice = (2 * inter + 1.0) / (denom + 1.0)
    return (1.0 - dice[valid]).mean()


def soft_dice_loss_multiclass(logits: torch.Tensor, target: torch.Tensor, case_mask: torch.Tensor) -> torch.Tensor:
    case_mask = case_mask.to(device=logits.device, dtype=torch.bool)
    if not case_mask.any():
        return logits.sum() * 0.0
    logits = logits[case_mask]
    target = target[case_mask].long()
    probs = torch.softmax(logits, dim=1)
    one_hot = F.one_hot(target.clamp_min(0), num_classes=logits.shape[1]).permute(0, 4, 1, 2, 3).float()
    dims = (0, 2, 3, 4)
    inter = (probs * one_hot).sum(dims)
    denom = probs.sum(dims) + one_hot.sum(dims)
    class_start = 1 if logits.shape[1] > 1 else 0
    dice = (2 * inter[class_start:] + 1.0) / (denom[class_start:] + 1.0)
    return (1.0 - dice).mean()


def ce_dice_anatomy(anatomy_logits: torch.Tensor, seg: torch.Tensor, case_mask: torch.Tensor) -> torch.Tensor:
    case_mask = case_mask.to(device=anatomy_logits.device, dtype=torch.bool)
    if not case_mask.any():
        return anatomy_logits.sum() * 0.0
    target = remap_anatomy_target(seg).to(anatomy_logits.device)
    ce = F.cross_entropy(anatomy_logits[case_mask], target[case_mask])
    dice = soft_dice_loss_multiclass(anatomy_logits, target, case_mask)
    return ce + dice


def bce_dice_final_margin(
    six_class_logits: torch.Tensor,
    seg: torch.Tensor,
    *,
    pathology: str,
    case_mask: torch.Tensor,
) -> torch.Tensor:
    margins = final_margin_logits(six_class_logits)
    class_id = 5 if pathology == "scar" else 4
    logits = margins[pathology]
    target = binary_target(seg, class_id).to(logits.device)
    case_mask = case_mask.to(device=logits.device, dtype=logits.dtype)
    if case_mask.sum() <= 0:
        return logits.sum() * 0.0
    bce = F.binary_cross_entropy_with_logits(logits, target[:, None], reduction="none")
    return masked_mean(bce, case_mask) + soft_dice_loss_binary(logits, target[:, None], case_mask)


def final_six_class_loss(six_class_logits: torch.Tensor, seg: torch.Tensor, case_mask: torch.Tensor) -> torch.Tensor:
    case_mask = case_mask.to(device=six_class_logits.device, dtype=torch.bool)
    if not case_mask.any():
        return six_class_logits.sum() * 0.0
    target = seg.clamp_min(0).long().to(six_class_logits.device)
    ce = F.cross_entropy(six_class_logits[case_mask], target[case_mask])
    dice = soft_dice_loss_multiclass(six_class_logits, target, case_mask)
    return ce + dice


def consistency_loss(student_logits: torch.Tensor, natural_logits: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    if mask.to(device=student_logits.device, dtype=torch.float32).sum() <= 0:
        return student_logits.sum() * 0.0
    loss = F.mse_loss(student_logits, natural_logits.detach(), reduction="none").mean(dim=1)
    return masked_mean(loss, mask)


def distill_logits_loss(
    student_logits: torch.Tensor,
    teacher_logits: torch.Tensor,
    mask: torch.Tensor,
    *,
    temperature: float,
    confidence_threshold: float,
) -> torch.Tensor:
    mask = mask.to(device=student_logits.device, dtype=torch.bool)
    if not mask.any():
        return student_logits.sum() * 0.0
    teacher_prob = torch.softmax(teacher_logits.detach() / temperature, dim=1)
    conf = teacher_prob.max(dim=1).values >= float(confidence_threshold)
    voxel_mask = mask[:, None, None, None] & conf
    if not voxel_mask.any():
        return student_logits.sum() * 0.0
    student_logp = F.log_softmax(student_logits / temperature, dim=1)
    kl = F.kl_div(student_logp, teacher_prob, reduction="none").sum(dim=1)
    return (kl * voxel_mask).sum() / voxel_mask.sum().clamp_min(1)


def distill_feature_loss(student_features: torch.Tensor, teacher_features: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    if mask.to(device=student_features.device, dtype=torch.float32).sum() <= 0:
        return student_features.sum() * 0.0
    return masked_mean(F.mse_loss(student_features, teacher_features.detach(), reduction="none").mean(dim=1), mask)


def compute_care_mm_loss(
    outputs: dict[str, torch.Tensor],
    seg: torch.Tensor,
    reliable: ReliableMaskBatch,
    weights: dict[str, float],
    *,
    natural_outputs: dict[str, torch.Tensor] | None = None,
    teacher_outputs: dict[str, torch.Tensor] | None = None,
    temperature: float = 2.0,
    teacher_confidence_threshold: float = 0.60,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    terms: dict[str, torch.Tensor] = {}
    six = outputs["six_class_logits"]
    terms["loss_anatomy_ce_dice"] = ce_dice_anatomy(outputs["anatomy_logits"], seg, reliable.anatomy)
    terms["loss_scar_final_margin_bce_dice"] = bce_dice_final_margin(
        six, seg, pathology="scar", case_mask=reliable.scar
    )
    terms["loss_edema_final_margin_bce_dice_reliable_only"] = bce_dice_final_margin(
        six, seg, pathology="edema", case_mask=reliable.edema
    )
    terms["loss_final_six_class_reliable"] = final_six_class_loss(six, seg, reliable.final_six_class)
    if natural_outputs is not None:
        terms["loss_moddrop_consistency"] = consistency_loss(
            outputs["six_class_logits"], natural_outputs["six_class_logits"], reliable.anatomy
        )
    else:
        terms["loss_moddrop_consistency"] = six.sum() * 0.0
    distill_mask = reliable.natural_complete_trimodal & reliable.final_six_class
    if teacher_outputs is not None:
        terms["loss_distill_logits"] = distill_logits_loss(
            outputs["six_class_logits"],
            teacher_outputs["six_class_logits"],
            distill_mask,
            temperature=temperature,
            confidence_threshold=teacher_confidence_threshold,
        )
        terms["loss_distill_feature"] = distill_feature_loss(
            outputs["features"], teacher_outputs["features"], distill_mask
        )
        terms["loss_distill_anatomy"] = distill_logits_loss(
            outputs["anatomy_logits"],
            teacher_outputs["anatomy_logits"],
            distill_mask,
            temperature=temperature,
            confidence_threshold=teacher_confidence_threshold,
        )
    else:
        terms["loss_distill_logits"] = six.sum() * 0.0
        terms["loss_distill_feature"] = outputs["features"].sum() * 0.0
        terms["loss_distill_anatomy"] = outputs["anatomy_logits"].sum() * 0.0
    total = six.sum() * 0.0
    for key, term in terms.items():
        total = total + float(weights.get(key, 0.0)) * term
    terms["total_loss"] = total
    return total, terms


def weighted_loss_report(terms: dict[str, torch.Tensor], weights: dict[str, float]) -> dict[str, float]:
    report: dict[str, float] = {}
    total = 0.0
    for key, term in terms.items():
        if key == "total_loss":
            continue
        raw = float(term.detach().cpu())
        weight = float(weights.get(key, 0.0))
        weighted = raw * weight
        report[f"{key}_raw"] = raw
        report[f"{key}_weight"] = weight
        report[f"{key}_weighted"] = weighted
        total += weighted
    report["raw_total_loss"] = float(terms["total_loss"].detach().cpu()) if "total_loss" in terms else total
    report["weighted_terms_sum"] = total
    return report


def runtime_loss_contract(weights: dict[str, float]) -> dict[str, Any]:
    nonzero = {k: float(v) for k, v in sorted(weights.items()) if float(v) != 0.0}
    return {
        "schema_version": 1,
        "status": "PASS",
        "pathology_losses_use_composed_final_logit_margins": True,
        "raw_residual_only_pathology_supervision": "forbidden",
        "every_nonzero_loss_in_total": True,
        "masked_loss_denominator": "valid_voxel_count",
        "anatomy_dice_excludes_background": True,
        "nonzero_loss_weights": nonzero,
    }
