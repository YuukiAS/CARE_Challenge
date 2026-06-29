"""Losses and safety metrics for SRR-MyoPS."""

from __future__ import annotations

import torch
import torch.nn.functional as F


EDEMA_CLASS = 4
SCAR_CLASS = 5
IGNORE_LABEL = -1


def _binary_dice_loss(
    prob: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor | None = None,
    eps: float = 1e-6,
) -> torch.Tensor:
    if mask is not None:
        mask_f = mask.to(device=prob.device, dtype=prob.dtype)
        prob = prob * mask_f
        target = target * mask_f
    axes = tuple(range(1, prob.ndim))
    inter = (prob * target).sum(dim=axes)
    denom = prob.sum(dim=axes) + target.sum(dim=axes)
    return (1.0 - (2.0 * inter + eps) / (denom + eps)).mean()


def _masked_bce_with_logits(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    mask_f = mask.to(device=logits.device, dtype=logits.dtype)
    loss = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    return (loss * mask_f).sum() / mask_f.sum().clamp_min(1.0)


def t2_masked_edema_loss(edema_logits: torch.Tensor, labels: torch.Tensor, availability: torch.Tensor) -> torch.Tensor:
    """Dense edema supervision only for T2-present samples."""

    t2_present = availability[:, 1].to(dtype=torch.bool, device=edema_logits.device)
    if not bool(t2_present.any()):
        return edema_logits.sum() * 0.0
    logits = edema_logits[t2_present, 0]
    valid = labels[t2_present] != IGNORE_LABEL
    if not bool(valid.any()):
        return edema_logits.sum() * 0.0
    target = (labels[t2_present] == EDEMA_CLASS).float()
    bce = _masked_bce_with_logits(logits, target, valid)
    dice = _binary_dice_loss(torch.sigmoid(logits), target, valid)
    return 0.5 * bce + 0.5 * dice


def scar_loss(scar_logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    valid = labels != IGNORE_LABEL
    if not bool(valid.any()):
        return scar_logits.sum() * 0.0
    target = (labels == SCAR_CLASS).float()
    logits = scar_logits[:, 0]
    bce = _masked_bce_with_logits(logits, target, valid)
    dice = _binary_dice_loss(torch.sigmoid(logits), target, valid)
    return 0.5 * bce + 0.5 * dice


def anatomy_loss(anatomy_logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    anatomy_target = labels.clone()
    anatomy_target = torch.where(anatomy_target == EDEMA_CLASS, torch.ones_like(anatomy_target), anatomy_target)
    anatomy_target = torch.where(anatomy_target == SCAR_CLASS, torch.ones_like(anatomy_target), anatomy_target)
    anatomy_target = torch.where(
        anatomy_target == IGNORE_LABEL,
        anatomy_target,
        anatomy_target.clamp(0, 3),
    )
    return F.cross_entropy(anatomy_logits, anatomy_target.long(), ignore_index=IGNORE_LABEL)


def retrieval_regularization(
    gates: dict[str, torch.Tensor],
    eps: float = 1e-6,
    entropy_floor: float = 0.5,
    entropy_weight: float = 0.05,
    coverage_weight: float = 0.05,
    max_weight_penalty: float = 0.02,
) -> tuple[torch.Tensor | None, dict[str, torch.Tensor]]:
    if not gates:
        return None, {}
    entropy_floor_terms = []
    coverage_terms = []
    max_weight_terms = []
    metrics: dict[str, torch.Tensor] = {}
    for name, gate in gates.items():
        entropy = -(gate * torch.log(gate.clamp_min(eps))).sum(dim=1).mean()
        usage = gate.mean(dim=0)
        target = torch.full_like(usage, 1.0 / max(1, usage.numel()))
        coverage = torch.mean((usage - target).square())
        max_weight = gate.max(dim=1).values.mean()
        entropy_floor_terms.append(torch.relu(gate.new_tensor(float(entropy_floor)) - entropy))
        coverage_terms.append(coverage)
        max_weight_terms.append(torch.relu(max_weight - 0.9).square())
        metrics[f"{name}_entropy"] = entropy.detach()
        metrics[f"{name}_coverage_mse"] = coverage.detach()
        metrics[f"{name}_max_weight"] = max_weight.detach()
    return (
        float(entropy_weight) * torch.stack(entropy_floor_terms).mean()
        + float(coverage_weight) * torch.stack(coverage_terms).mean()
        + float(max_weight_penalty) * torch.stack(max_weight_terms).mean()
    ), metrics


def soft_anatomy_prior_loss(outputs: dict[str, torch.Tensor], labels: torch.Tensor) -> torch.Tensor:
    union = torch.sigmoid(outputs["union_prior_logits"][:, 0])
    scar = torch.sigmoid(outputs["scar_logits"][:, 0])
    edema = torch.sigmoid(outputs["edema_logits"][:, 0])
    outside = (1.0 - union.detach()).clamp(0, 1)
    valid = (labels != IGNORE_LABEL).to(dtype=scar.dtype, device=scar.device)
    denom = valid.sum().clamp_min(1.0)
    scar_loss_value = (scar * outside * valid).sum() / denom
    edema_loss_value = (edema * outside * valid).sum() / denom
    return 0.5 * scar_loss_value + 0.5 * edema_loss_value


def srr_total_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    availability: torch.Tensor,
    weights: dict[str, float] | None = None,
    retrieval_config: dict[str, float] | None = None,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    weights = weights or {}
    retrieval_config = retrieval_config or {}
    components = {
        "anatomy": anatomy_loss(outputs["anatomy_logits"], labels),
        "scar": scar_loss(outputs["scar_logits"], labels),
        "edema": t2_masked_edema_loss(outputs["edema_logits"], labels, availability),
        "prior": soft_anatomy_prior_loss(outputs, labels),
    }
    reg, reg_metrics = retrieval_regularization(outputs["gates"], **retrieval_config)
    components["retrieval"] = reg if reg is not None else outputs["logits"].sum() * 0.0
    total = (
        weights.get("anatomy", 1.0) * components["anatomy"]
        + weights.get("scar", 1.0) * components["scar"]
        + weights.get("edema", 1.0) * components["edema"]
        + weights.get("prior", 0.1) * components["prior"]
        + weights.get("retrieval", 1.0) * components["retrieval"]
    )
    metrics = {**components, **reg_metrics}
    return total, metrics
