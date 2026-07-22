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


def _one_vs_rest_margin(final_logits: torch.Tensor, class_index: int) -> torch.Tensor:
    keep = [idx for idx in range(final_logits.shape[1]) if idx != int(class_index)]
    other = torch.logsumexp(final_logits[:, keep], dim=1)
    return final_logits[:, int(class_index)] - other


def final_pathology_loss_from_logits(
    final_logits: torch.Tensor,
    labels: torch.Tensor,
    availability: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Directly supervise deployed six-class logits for scar and T2-present edema."""

    valid = labels != IGNORE_LABEL
    scar_target = (labels == SCAR_CLASS).float()
    scar_margin = _one_vs_rest_margin(final_logits, SCAR_CLASS)
    if bool(valid.any()):
        scar_bce = _masked_bce_with_logits(scar_margin, scar_target, valid)
        scar_dice = _binary_dice_loss(torch.sigmoid(scar_margin), scar_target, valid)
        scar_final = 0.5 * scar_bce + 0.5 * scar_dice
    else:
        scar_final = final_logits.sum() * 0.0

    t2_present = availability[:, 1].to(device=labels.device, dtype=torch.bool).view(-1, 1, 1, 1)
    edema_mask = valid & t2_present
    edema_target = (labels == EDEMA_CLASS).float()
    edema_margin = _one_vs_rest_margin(final_logits, EDEMA_CLASS)
    if bool(edema_mask.any()):
        edema_bce = _masked_bce_with_logits(edema_margin, edema_target, edema_mask)
        edema_dice = _binary_dice_loss(torch.sigmoid(edema_margin), edema_target, edema_mask)
        edema_final = 0.5 * edema_bce + 0.5 * edema_dice
    else:
        edema_final = final_logits.sum() * 0.0
    return scar_final, edema_final


def _masked_mean(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    mask_f = mask.to(device=values.device, dtype=values.dtype)
    return (values * mask_f).sum() / mask_f.sum().clamp_min(1.0)


def scar_final_correction_directionality_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    *,
    preserve_confidence_threshold: float = 0.80,
    target_margin_delta: float = 1.0,
    preserve_weight: float = 0.05,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Force final scar logits to correct anchor scar FN/FP directions while preserving confident correct anchor margins."""

    final_logits = outputs.get("logits")
    anchor_logits = outputs.get("nnunet_anchor_logits")
    if not isinstance(final_logits, torch.Tensor) or not isinstance(anchor_logits, torch.Tensor):
        ref = outputs["logits"] if isinstance(outputs.get("logits"), torch.Tensor) else labels.float()
        zero = ref.sum() * 0.0
        return zero, {
            "scar_directionality_fn_voxels": zero.detach(),
            "scar_directionality_fp_voxels": zero.detach(),
            "scar_directionality_preserve_voxels": zero.detach(),
            "scar_margin_delta_on_fn": zero.detach(),
            "scar_margin_delta_on_fp": zero.detach(),
            "scar_margin_abs_delta_on_preserve": zero.detach(),
        }

    valid = labels != IGNORE_LABEL
    scar_target = labels == SCAR_CLASS
    anchor_probs = torch.softmax(anchor_logits, dim=1)
    anchor_conf, anchor_pred = anchor_probs.max(dim=1)
    anchor_scar = anchor_pred == SCAR_CLASS
    scar_fn = valid & scar_target & ~anchor_scar
    scar_fp = valid & ~scar_target & anchor_scar
    preserve = valid & (anchor_scar == scar_target) & (anchor_conf >= float(preserve_confidence_threshold))

    final_margin = _one_vs_rest_margin(final_logits, SCAR_CLASS)
    anchor_margin = _one_vs_rest_margin(anchor_logits, SCAR_CLASS).detach()
    margin_delta = final_margin - anchor_margin
    target_delta = final_margin.new_tensor(float(target_margin_delta))

    terms: list[torch.Tensor] = []
    if bool(scar_fn.any()):
        terms.append(_masked_mean(torch.relu(target_delta - margin_delta), scar_fn))
    if bool(scar_fp.any()):
        terms.append(_masked_mean(torch.relu(target_delta + margin_delta), scar_fp))
    if bool(preserve.any()) and preserve_weight > 0.0:
        terms.append(float(preserve_weight) * _masked_mean(F.smooth_l1_loss(margin_delta, torch.zeros_like(margin_delta), reduction="none"), preserve))

    zero = final_logits.sum() * 0.0
    loss = torch.stack(terms).sum() if terms else zero

    def diagnostic_mean(values: torch.Tensor, mask: torch.Tensor, *, absolute: bool = False) -> torch.Tensor:
        if not bool(mask.any()):
            return zero.detach()
        tensor = values.abs() if absolute else values
        return _masked_mean(tensor, mask).detach()

    return loss, {
        "scar_directionality_fn_voxels": scar_fn.to(device=final_logits.device, dtype=final_logits.dtype).sum().detach(),
        "scar_directionality_fp_voxels": scar_fp.to(device=final_logits.device, dtype=final_logits.dtype).sum().detach(),
        "scar_directionality_preserve_voxels": preserve.to(device=final_logits.device, dtype=final_logits.dtype).sum().detach(),
        "scar_margin_delta_on_fn": diagnostic_mean(margin_delta, scar_fn),
        "scar_margin_delta_on_fp": diagnostic_mean(margin_delta, scar_fp),
        "scar_margin_abs_delta_on_preserve": diagnostic_mean(margin_delta, preserve, absolute=True),
    }


def scar_final_anchor_error_pathology_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    *,
    target_margin_delta: float = 3.75,
    fn_weight: float = 8.0,
    fp_weight: float = 1.5,
    preserve_correction_weight: float = 2.0,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Direct deployed-logit scar supervision concentrated on anchor scar FN/FP voxels."""

    final_logits = outputs.get("logits")
    anchor_logits = outputs.get("nnunet_anchor_logits")
    if not isinstance(final_logits, torch.Tensor) or not isinstance(anchor_logits, torch.Tensor):
        ref = outputs["logits"] if isinstance(outputs.get("logits"), torch.Tensor) else labels.float()
        zero = ref.sum() * 0.0
        return zero, {
            "scar_anchor_error_voxels": zero.detach(),
            "scar_final_prob_on_anchor_fn": zero.detach(),
            "scar_final_prob_on_anchor_fp": zero.detach(),
            "scar_final_margin_on_anchor_fn": zero.detach(),
            "scar_final_margin_on_anchor_fp": zero.detach(),
            "scar_bounded_correction_on_anchor_fn": zero.detach(),
            "scar_bounded_correction_on_anchor_fp": zero.detach(),
            "scar_bounded_correction_on_preserve": zero.detach(),
            "scar_anchor_error_abs_margin_shortfall": zero.detach(),
        }

    valid = labels != IGNORE_LABEL
    scar_target_bool = labels == SCAR_CLASS
    anchor_probs = torch.softmax(anchor_logits, dim=1)
    anchor_conf, anchor_pred = anchor_probs.max(dim=1)
    anchor_scar = anchor_pred == SCAR_CLASS
    scar_fn = valid & scar_target_bool & ~anchor_scar
    scar_fp = valid & ~scar_target_bool & anchor_scar
    preserve = valid & (anchor_scar == scar_target_bool) & (anchor_conf >= 0.80)
    anchor_error = scar_fn | scar_fp
    zero = final_logits.sum() * 0.0
    if not bool(anchor_error.any()):
        return zero, {
            "scar_anchor_error_voxels": zero.detach(),
            "scar_final_prob_on_anchor_fn": zero.detach(),
            "scar_final_prob_on_anchor_fp": zero.detach(),
            "scar_final_margin_on_anchor_fn": zero.detach(),
            "scar_final_margin_on_anchor_fp": zero.detach(),
            "scar_bounded_correction_on_anchor_fn": zero.detach(),
            "scar_bounded_correction_on_anchor_fp": zero.detach(),
            "scar_bounded_correction_on_preserve": zero.detach(),
            "scar_anchor_error_abs_margin_shortfall": zero.detach(),
        }

    scar_margin = _one_vs_rest_margin(final_logits, SCAR_CLASS)
    scar_target = scar_target_bool.float()
    bce = _masked_bce_with_logits(scar_margin, scar_target, anchor_error)
    dice = _binary_dice_loss(torch.sigmoid(scar_margin), scar_target, anchor_error)
    anchor_margin = _one_vs_rest_margin(anchor_logits, SCAR_CLASS).detach()
    margin_delta = scar_margin - anchor_margin
    target = scar_margin.new_tensor(float(target_margin_delta))
    fn_shortfall = torch.relu(target - margin_delta)
    fp_shortfall = torch.relu(target + margin_delta)
    fn_margin_loss = _masked_mean(fn_shortfall.square(), scar_fn) if bool(scar_fn.any()) else zero
    fp_margin_loss = _masked_mean(fp_shortfall.square(), scar_fp) if bool(scar_fp.any()) else zero
    fn_logistic = _masked_mean(F.softplus(-scar_margin), scar_fn) if bool(scar_fn.any()) else zero
    fp_logistic = _masked_mean(F.softplus(scar_margin), scar_fp) if bool(scar_fp.any()) else zero
    margin_loss = float(fn_weight) * (fn_logistic + 0.25 * fn_margin_loss) + float(fp_weight) * (
        fp_logistic + 0.25 * fp_margin_loss
    )

    bounded_correction = outputs.get("bounded_scar_correction")
    correction_loss = zero
    bounded = None
    if isinstance(bounded_correction, torch.Tensor):
        bounded = bounded_correction[:, 0]
        max_correction = bounded.new_tensor(4.0)
        if bool(scar_fn.any()):
            fn_target = torch.full_like(bounded, float(max_correction))
            fn_raw = F.smooth_l1_loss(bounded, fn_target, reduction="none")
            correction_loss = correction_loss + float(fn_weight) * _masked_mean(fn_raw, scar_fn)
        if bool(scar_fp.any()):
            fp_target = torch.full_like(bounded, -float(max_correction))
            fp_raw = F.smooth_l1_loss(bounded, fp_target, reduction="none")
            correction_loss = correction_loss + float(fp_weight) * _masked_mean(fp_raw, scar_fp)
        if bool(preserve.any()):
            preserve_raw = F.smooth_l1_loss(bounded, torch.zeros_like(bounded), reduction="none")
            correction_loss = correction_loss + float(preserve_correction_weight) * _masked_mean(preserve_raw, preserve)
    loss = 0.25 * bce + 0.25 * dice + 0.50 * margin_loss + correction_loss

    prob = torch.sigmoid(scar_margin)

    def diagnostic_mean(values: torch.Tensor | None, mask: torch.Tensor) -> torch.Tensor:
        if values is None or not bool(mask.any()):
            return zero.detach()
        return _masked_mean(values, mask).detach()

    return loss, {
        "scar_anchor_error_voxels": anchor_error.to(device=final_logits.device, dtype=final_logits.dtype).sum().detach(),
        "scar_final_prob_on_anchor_fn": diagnostic_mean(prob, scar_fn),
        "scar_final_prob_on_anchor_fp": diagnostic_mean(prob, scar_fp),
        "scar_final_margin_on_anchor_fn": diagnostic_mean(scar_margin, scar_fn),
        "scar_final_margin_on_anchor_fp": diagnostic_mean(scar_margin, scar_fp),
        "scar_bounded_correction_on_anchor_fn": diagnostic_mean(bounded, scar_fn),
        "scar_bounded_correction_on_anchor_fp": diagnostic_mean(bounded, scar_fp),
        "scar_bounded_correction_on_preserve": diagnostic_mean(bounded, preserve),
        "scar_anchor_error_abs_margin_shortfall": (margin_loss + correction_loss).detach(),
    }


def edema_final_anchor_error_pathology_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    availability: torch.Tensor,
    *,
    target_margin_delta: float = 3.75,
    fn_weight: float = 8.0,
    fp_weight: float = 1.5,
    preserve_correction_weight: float = 2.0,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Direct deployed-logit edema correction on T2-present anchor edema FN/FP voxels."""

    final_logits = outputs.get("logits")
    anchor_logits = outputs.get("nnunet_anchor_logits")
    if not isinstance(final_logits, torch.Tensor) or not isinstance(anchor_logits, torch.Tensor):
        ref = outputs["logits"] if isinstance(outputs.get("logits"), torch.Tensor) else labels.float()
        zero = ref.sum() * 0.0
        return zero, {
            "edema_anchor_error_voxels": zero.detach(),
            "edema_final_prob_on_anchor_fn": zero.detach(),
            "edema_final_prob_on_anchor_fp": zero.detach(),
            "edema_final_margin_on_anchor_fn": zero.detach(),
            "edema_final_margin_on_anchor_fp": zero.detach(),
            "edema_bounded_correction_on_anchor_fn": zero.detach(),
            "edema_bounded_correction_on_anchor_fp": zero.detach(),
            "edema_bounded_correction_on_preserve": zero.detach(),
            "edema_anchor_error_abs_margin_shortfall": zero.detach(),
        }

    valid = labels != IGNORE_LABEL
    t2_present = availability[:, 1].to(device=labels.device, dtype=torch.bool).view(-1, 1, 1, 1)
    pathology_valid = valid & t2_present
    edema_target_bool = labels == EDEMA_CLASS
    anchor_probs = torch.softmax(anchor_logits, dim=1)
    anchor_conf, anchor_pred = anchor_probs.max(dim=1)
    anchor_edema = anchor_pred == EDEMA_CLASS
    edema_fn = pathology_valid & edema_target_bool & ~anchor_edema
    edema_fp = pathology_valid & ~edema_target_bool & anchor_edema
    preserve = pathology_valid & (anchor_edema == edema_target_bool) & (anchor_conf >= 0.80)
    anchor_error = edema_fn | edema_fp
    zero = final_logits.sum() * 0.0
    if not bool(anchor_error.any()):
        return zero, {
            "edema_anchor_error_voxels": zero.detach(),
            "edema_final_prob_on_anchor_fn": zero.detach(),
            "edema_final_prob_on_anchor_fp": zero.detach(),
            "edema_final_margin_on_anchor_fn": zero.detach(),
            "edema_final_margin_on_anchor_fp": zero.detach(),
            "edema_bounded_correction_on_anchor_fn": zero.detach(),
            "edema_bounded_correction_on_anchor_fp": zero.detach(),
            "edema_bounded_correction_on_preserve": zero.detach(),
            "edema_anchor_error_abs_margin_shortfall": zero.detach(),
        }

    edema_margin = _one_vs_rest_margin(final_logits, EDEMA_CLASS)
    edema_target = edema_target_bool.float()
    bce = _masked_bce_with_logits(edema_margin, edema_target, anchor_error)
    dice = _binary_dice_loss(torch.sigmoid(edema_margin), edema_target, anchor_error)
    anchor_margin = _one_vs_rest_margin(anchor_logits, EDEMA_CLASS).detach()
    margin_delta = edema_margin - anchor_margin
    target = edema_margin.new_tensor(float(target_margin_delta))
    fn_shortfall = torch.relu(target - margin_delta)
    fp_shortfall = torch.relu(target + margin_delta)
    fn_margin_loss = _masked_mean(fn_shortfall.square(), edema_fn) if bool(edema_fn.any()) else zero
    fp_margin_loss = _masked_mean(fp_shortfall.square(), edema_fp) if bool(edema_fp.any()) else zero
    fn_logistic = _masked_mean(F.softplus(-edema_margin), edema_fn) if bool(edema_fn.any()) else zero
    fp_logistic = _masked_mean(F.softplus(edema_margin), edema_fp) if bool(edema_fp.any()) else zero
    margin_loss = float(fn_weight) * (fn_logistic + 0.25 * fn_margin_loss) + float(fp_weight) * (
        fp_logistic + 0.25 * fp_margin_loss
    )

    bounded_correction = outputs.get("bounded_edema_correction")
    correction_loss = zero
    bounded = None
    if isinstance(bounded_correction, torch.Tensor):
        bounded = bounded_correction[:, 0]
        max_correction = bounded.new_tensor(4.0)
        if bool(edema_fn.any()):
            fn_target = torch.full_like(bounded, float(max_correction))
            fn_raw = F.smooth_l1_loss(bounded, fn_target, reduction="none")
            correction_loss = correction_loss + float(fn_weight) * _masked_mean(fn_raw, edema_fn)
        if bool(edema_fp.any()):
            fp_target = torch.full_like(bounded, -float(max_correction))
            fp_raw = F.smooth_l1_loss(bounded, fp_target, reduction="none")
            correction_loss = correction_loss + float(fp_weight) * _masked_mean(fp_raw, edema_fp)
        if bool(preserve.any()):
            preserve_raw = F.smooth_l1_loss(bounded, torch.zeros_like(bounded), reduction="none")
            correction_loss = correction_loss + float(preserve_correction_weight) * _masked_mean(preserve_raw, preserve)
    loss = 0.25 * bce + 0.25 * dice + 0.50 * margin_loss + correction_loss

    prob = torch.sigmoid(edema_margin)

    def diagnostic_mean(values: torch.Tensor | None, mask: torch.Tensor) -> torch.Tensor:
        if values is None or not bool(mask.any()):
            return zero.detach()
        return _masked_mean(values, mask).detach()

    return loss, {
        "edema_anchor_error_voxels": anchor_error.to(device=final_logits.device, dtype=final_logits.dtype).sum().detach(),
        "edema_final_prob_on_anchor_fn": diagnostic_mean(prob, edema_fn),
        "edema_final_prob_on_anchor_fp": diagnostic_mean(prob, edema_fp),
        "edema_final_margin_on_anchor_fn": diagnostic_mean(edema_margin, edema_fn),
        "edema_final_margin_on_anchor_fp": diagnostic_mean(edema_margin, edema_fp),
        "edema_bounded_correction_on_anchor_fn": diagnostic_mean(bounded, edema_fn),
        "edema_bounded_correction_on_anchor_fp": diagnostic_mean(bounded, edema_fp),
        "edema_bounded_correction_on_preserve": diagnostic_mean(bounded, preserve),
        "edema_anchor_error_abs_margin_shortfall": (margin_loss + correction_loss).detach(),
    }


def production_gate_repair_preserve_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    availability: torch.Tensor,
    *,
    preserve_confidence_threshold: float = 0.80,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Supervise production gate to open on anchor errors and preserve confident correct anchor voxels."""

    gate_logits = outputs.get("production_correction_gate_logits")
    anchor_logits = outputs.get("nnunet_anchor_logits")
    if not isinstance(gate_logits, torch.Tensor) or not isinstance(anchor_logits, torch.Tensor):
        zero = outputs["logits"].sum() * 0.0
        return zero, {
            "repair_mask_voxels": zero.detach(),
            "preserve_mask_voxels": zero.detach(),
            "gate_mean_on_repair": zero.detach(),
            "gate_mean_on_preserve": zero.detach(),
        }
    valid = labels != IGNORE_LABEL
    anchor_probs = torch.softmax(anchor_logits, dim=1)
    anchor_conf, anchor_pred = anchor_probs.max(dim=1)
    t2_present = availability[:, 1].to(device=labels.device, dtype=torch.bool).view(-1, 1, 1, 1)
    losses: list[torch.Tensor] = []
    repair_counts: list[torch.Tensor] = []
    preserve_counts: list[torch.Tensor] = []
    repair_means: list[torch.Tensor] = []
    preserve_means: list[torch.Tensor] = []
    gate_prob = torch.sigmoid(gate_logits)
    for gate_channel, class_index, pathology_valid in (
        (0, SCAR_CLASS, valid),
        (1, EDEMA_CLASS, valid & t2_present),
    ):
        target_binary = labels == class_index
        anchor_binary = anchor_pred == class_index
        repair = pathology_valid & (anchor_binary != target_binary)
        preserve = pathology_valid & ~repair & (anchor_conf >= float(preserve_confidence_threshold))
        supervised = repair | preserve
        repair_f = repair.to(device=gate_logits.device, dtype=gate_logits.dtype)
        preserve_f = preserve.to(device=gate_logits.device, dtype=gate_logits.dtype)
        repair_n = repair_f.sum()
        preserve_n = preserve_f.sum()
        repair_counts.append(repair_n.detach())
        preserve_counts.append(preserve_n.detach())
        if bool(supervised.any()):
            pos_weight = torch.clamp(preserve_n / repair_n.clamp_min(1.0), 1.0, 20.0)
            target = repair.to(device=gate_logits.device, dtype=gate_logits.dtype)
            raw = F.binary_cross_entropy_with_logits(
                gate_logits[:, gate_channel],
                target,
                reduction="none",
                pos_weight=pos_weight,
            )
            mask_f = supervised.to(device=gate_logits.device, dtype=gate_logits.dtype)
            losses.append((raw * mask_f).sum() / mask_f.sum().clamp_min(1.0))
        if bool(repair.any()):
            repair_means.append((gate_prob[:, gate_channel] * repair_f).sum() / repair_n.clamp_min(1.0))
        if bool(preserve.any()):
            preserve_means.append((gate_prob[:, gate_channel] * preserve_f).sum() / preserve_n.clamp_min(1.0))
    zero = gate_logits.sum() * 0.0
    loss = torch.stack(losses).mean() if losses else zero
    return loss, {
        "repair_mask_voxels": torch.stack(repair_counts).sum().detach() if repair_counts else zero.detach(),
        "preserve_mask_voxels": torch.stack(preserve_counts).sum().detach() if preserve_counts else zero.detach(),
        "gate_mean_on_repair": torch.stack(repair_means).mean().detach() if repair_means else zero.detach(),
        "gate_mean_on_preserve": torch.stack(preserve_means).mean().detach() if preserve_means else zero.detach(),
    }


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
        if gate.ndim == 5:
            gate = gate.flatten(2).mean(dim=2)
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


def _gate_task_name(name: str) -> str:
    for task in ("anatomy", "scar", "edema"):
        if name == task or name.startswith(f"{task}_"):
            return task
    return str(name).split("_", 1)[0]


def _semantic_slot_weight(task: str, group: str, kind: str) -> float:
    """Task-specific slot prior used by the semantic retrieval objective."""

    if task == "scar":
        if group == "lge_private":
            return 1.00
        if group in {"interaction_lge_t2", "interaction_lge_c0"}:
            return 0.70
        if group == "shared":
            return 0.35
        if group == "c0_private":
            return 0.15
        return 0.02
    if task == "edema":
        if group == "t2_private":
            return 1.00
        if group in {"interaction_lge_t2", "interaction_t2_c0"}:
            return 0.70
        if group == "shared":
            return 0.35
        if group == "c0_private":
            return 0.15
        return 0.02
    if task == "anatomy":
        if group == "shared":
            return 0.85
        if group == "c0_private":
            return 0.45
        if kind == "interaction":
            return 0.25
        return 0.12
    return 1.0


def _semantic_group_family(task: str) -> set[str]:
    if task == "scar":
        return {"lge_private", "interaction_lge_t2", "interaction_lge_c0"}
    if task == "edema":
        return {"t2_private", "interaction_lge_t2", "interaction_t2_c0"}
    if task == "anatomy":
        return {"shared", "c0_private", "interaction_lge_c0", "interaction_t2_c0"}
    return {"shared"}


def semantic_retrieval_regularization(
    gates: dict[str, torch.Tensor],
    metadata: dict[str, list[dict[str, object]]],
    valid_masks: dict[str, torch.Tensor] | None = None,
    *,
    semantic_weight: float = 0.04,
    coverage_weight: float = 0.03,
    integrative_weight: float = 0.02,
    coverage_floor: float = 0.35,
    interaction_floor: float = 0.08,
    eps: float = 1e-6,
    detach_metrics: bool = True,
) -> tuple[torch.Tensor | None, dict[str, torch.Tensor]]:
    """SIP-style semantic retrieval objective for multi-slot SRR dictionaries.

    The term is intentionally stronger than generic entropy/coverage: each task
    receives a slot-family prior, invalid missing-modality slots are masked out,
    and pathology tasks are encouraged to keep interaction slots active when
    available. It remains a soft objective; it should be paired with ablations
    and same-split metrics before making scientific claims.
    """

    if not gates:
        return None, {}
    valid_masks = valid_masks or {}
    alignment_terms = []
    coverage_terms = []
    integrative_terms = []
    metrics: dict[str, torch.Tensor] = {}
    for name, gate in gates.items():
        if gate.ndim == 5:
            gate = gate.flatten(2).mean(dim=2)
        specs = metadata.get(name)
        if not specs or len(specs) != gate.shape[1]:
            continue
        task = _gate_task_name(name)
        weights = gate.new_tensor(
            [
                _semantic_slot_weight(task, str(spec.get("group", "")), str(spec.get("kind", "")))
                for spec in specs
            ]
        )
        valid = valid_masks.get(name)
        if valid is None:
            valid_f = torch.ones_like(gate)
        else:
            if valid.ndim == 5:
                valid = valid.flatten(2).mean(dim=2)
            valid_f = valid.to(device=gate.device, dtype=gate.dtype)
        target = weights.view(1, -1) * valid_f
        fallback = valid_f / valid_f.sum(dim=1, keepdim=True).clamp_min(eps)
        target = torch.where(target.sum(dim=1, keepdim=True) > eps, target, fallback)
        target = target / target.sum(dim=1, keepdim=True).clamp_min(eps)

        alignment = ((gate - target).square() * valid_f).sum(dim=1).mean()
        alignment_terms.append(alignment)
        metrics[f"{name}_semantic_alignment_mse"] = alignment.detach() if detach_metrics else alignment

        family = _semantic_group_family(task)
        family_indices = [
            idx
            for idx, spec in enumerate(specs)
            if str(spec.get("group", "")) in family
        ]
        if family_indices:
            family_mass = (gate[:, family_indices] * valid_f[:, family_indices]).sum(dim=1).mean()
            coverage = torch.relu(gate.new_tensor(float(coverage_floor)) - family_mass).square()
            coverage_terms.append(coverage)
            metrics[f"{name}_semantic_family_mass"] = family_mass.detach() if detach_metrics else family_mass
            metrics[f"{name}_semantic_coverage_penalty"] = coverage.detach() if detach_metrics else coverage

        interaction_indices = [
            idx
            for idx, spec in enumerate(specs)
            if str(spec.get("kind", "")) == "interaction" and str(spec.get("group", "")) in family
        ]
        if interaction_indices:
            valid_interaction = valid_f[:, interaction_indices].sum(dim=1) > 0
            if bool(valid_interaction.any()):
                interaction_mass = gate[valid_interaction][:, interaction_indices].sum(dim=1).mean()
                integrative = torch.relu(gate.new_tensor(float(interaction_floor)) - interaction_mass).square()
                integrative_terms.append(integrative)
                metrics[f"{name}_semantic_interaction_mass"] = interaction_mass.detach() if detach_metrics else interaction_mass
                metrics[f"{name}_semantic_integrative_penalty"] = integrative.detach() if detach_metrics else integrative

    if not alignment_terms:
        return None, metrics
    loss = float(semantic_weight) * torch.stack(alignment_terms).mean()
    if coverage_terms:
        loss = loss + float(coverage_weight) * torch.stack(coverage_terms).mean()
    if integrative_terms:
        loss = loss + float(integrative_weight) * torch.stack(integrative_terms).mean()
    metrics["semantic_retrieval_loss"] = loss.detach() if detach_metrics else loss
    return loss, metrics


def _gate_voxel_mean(gate: torch.Tensor) -> torch.Tensor:
    if gate.ndim == 2:
        return gate
    if gate.ndim == 5:
        return gate.flatten(2).mean(dim=2)
    raise ValueError(f"gate must be BxK or BxKxDHW, got {tuple(gate.shape)}")


def pattern_sip_integrativeness_loss(
    gates: dict[str, torch.Tensor],
    metadata: dict[str, list[dict[str, object]]],
    valid_masks: dict[str, torch.Tensor] | None = None,
    *,
    gamma_min: float = 1.35,
    entropy_weight: float = 0.01,
    kl_weight: float = 0.05,
    gamma_weight: float = 0.05,
    collapse_weight: float = 0.02,
    eps: float = 1e-6,
    detach_metrics: bool = True,
) -> tuple[torch.Tensor | None, dict[str, torch.Tensor]]:
    """Independent M10 Pattern-SIP objective.

    This is deliberately not an alias for ``semantic_retrieval_regularization``:
    it computes group usage, integrativeness ``gamma``, target-prior KL, entropy,
    and collapse penalties directly from gate tensors.  It accepts both old
    global BxK gates and M10 spatial BxKxDHW gates.
    """

    if not gates:
        return None, {}
    valid_masks = valid_masks or {}
    gamma_terms = []
    kl_terms = []
    entropy_terms = []
    collapse_terms = []
    metrics: dict[str, torch.Tensor] = {}

    for name, gate in gates.items():
        specs = metadata.get(name)
        if not specs:
            continue
        gate_use = _gate_voxel_mean(gate)
        if gate_use.shape[1] != len(specs):
            continue
        valid = valid_masks.get(name)
        if valid is None:
            valid_use = torch.ones_like(gate_use)
        else:
            valid_use = _gate_voxel_mean(valid) if valid.ndim == 5 else valid
            valid_use = valid_use.to(device=gate_use.device, dtype=gate_use.dtype)
        gate_use = gate_use * valid_use
        gate_use = gate_use / gate_use.sum(dim=1, keepdim=True).clamp_min(eps)
        task = _gate_task_name(name)
        target_values = []
        for spec in specs:
            group = str(spec.get("group", ""))
            if group == "shared":
                target_values.append(0.50)
            elif task == "scar" and group == "lge_private":
                target_values.append(0.35)
            elif task == "edema" and group == "t2_private":
                target_values.append(0.35)
            elif str(spec.get("kind", "")) == "interaction":
                target_values.append(0.15)
            else:
                target_values.append(0.05)
        target = gate_use.new_tensor(target_values).view(1, -1) * valid_use
        target = torch.where(target.sum(dim=1, keepdim=True) > eps, target, valid_use)
        target = target / target.sum(dim=1, keepdim=True).clamp_min(eps)

        gamma = gate_use.sum(dim=0).square().sum() / gate_use.square().sum(dim=0).clamp_min(eps).sum()
        gamma_penalty = torch.relu(gate_use.new_tensor(float(gamma_min)) - gamma).square()
        kl = (target * (torch.log(target.clamp_min(eps)) - torch.log(gate_use.clamp_min(eps)))).sum(dim=1).mean()
        entropy = -(gate_use * torch.log(gate_use.clamp_min(eps))).sum(dim=1).mean()
        max_weight = gate_use.max(dim=1).values.mean()
        collapse = torch.relu(max_weight - 0.90).square()
        gamma_terms.append(gamma_penalty)
        kl_terms.append(kl)
        entropy_terms.append(entropy)
        collapse_terms.append(collapse)
        metrics[f"{name}_pattern_sip_gamma"] = gamma.detach() if detach_metrics else gamma
        metrics[f"{name}_pattern_sip_kl"] = kl.detach() if detach_metrics else kl
        metrics[f"{name}_pattern_sip_entropy"] = entropy.detach() if detach_metrics else entropy
        metrics[f"{name}_pattern_sip_collapse"] = collapse.detach() if detach_metrics else collapse

    if not gamma_terms:
        return None, metrics
    loss = (
        float(gamma_weight) * torch.stack(gamma_terms).mean()
        + float(kl_weight) * torch.stack(kl_terms).mean()
        + float(entropy_weight) * torch.stack(entropy_terms).mean()
        + float(collapse_weight) * torch.stack(collapse_terms).mean()
    )
    metrics["pattern_sip_integrativeness_loss"] = loss.detach() if detach_metrics else loss
    return loss, metrics


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
    sem_reg, sem_metrics = semantic_retrieval_regularization(
        outputs.get("gates", {}),
        outputs.get("dictionary_slot_metadata", {}),
        outputs.get("gate_valid_masks", {}),
    )
    components["retrieval"] = reg if reg is not None else outputs["logits"].sum() * 0.0
    components["semantic_retrieval"] = sem_reg if sem_reg is not None else outputs["logits"].sum() * 0.0
    total = (
        weights.get("anatomy", 1.0) * components["anatomy"]
        + weights.get("scar", 1.0) * components["scar"]
        + weights.get("edema", 1.0) * components["edema"]
        + weights.get("prior", 0.1) * components["prior"]
        + weights.get("retrieval", 1.0) * components["retrieval"]
        + weights.get("semantic_retrieval", 1.0) * components["semantic_retrieval"]
    )
    metrics = {**components, **reg_metrics, **sem_metrics}
    return total, metrics


def _masked_abs_mean(values: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
    if mask is None:
        return values.abs().mean()
    mask_f = mask.to(device=values.device, dtype=values.dtype)
    return (values.abs() * mask_f).sum() / mask_f.sum().clamp_min(1.0)


def _prototype_margin_loss(outputs: dict[str, torch.Tensor], labels: torch.Tensor, availability: torch.Tensor) -> torch.Tensor:
    valid = labels != IGNORE_LABEL
    t2_present = availability[:, 1].to(device=labels.device, dtype=torch.bool).view(-1, 1, 1, 1)
    terms = []
    for prefix, cls, mask in (
        ("scar", SCAR_CLASS, valid),
        ("edema", EDEMA_CLASS, valid & t2_present),
    ):
        pos = outputs.get(f"{prefix}_pos_similarity")
        neg = outputs.get(f"{prefix}_neg_similarity")
        if not isinstance(pos, torch.Tensor) or not isinstance(neg, torch.Tensor):
            continue
        target = (labels == cls) & mask
        safe_neg = (labels != cls) & mask
        if bool(target.any()):
            terms.append(_masked_abs_mean(torch.relu(0.25 - pos[:, 0] + neg[:, 0]), target))
        if bool(safe_neg.any()):
            terms.append(_masked_abs_mean(torch.relu(0.10 + pos[:, 0] - neg[:, 0]), safe_neg))
    if not terms:
        ref = outputs["logits"]
        return ref.sum() * 0.0
    return torch.stack(terms).mean()


def _memory_alignment_loss(outputs: dict[str, torch.Tensor], labels: torch.Tensor, availability: torch.Tensor) -> torch.Tensor:
    explicit = outputs.get("prototype_memory_alignment_loss")
    if isinstance(explicit, torch.Tensor):
        return explicit
    valid = labels != IGNORE_LABEL
    t2_present = availability[:, 1].to(device=labels.device, dtype=torch.bool).view(-1, 1, 1, 1)
    terms = []
    for prefix, cls, mask in (
        ("scar_memory", SCAR_CLASS, valid),
        ("edema_memory", EDEMA_CLASS, valid & t2_present),
    ):
        pos = outputs.get(f"{prefix}_positive_similarity")
        neg = outputs.get(f"{prefix}_negative_similarity")
        if not isinstance(pos, torch.Tensor) or not isinstance(neg, torch.Tensor):
            continue
        target = (labels == cls) & mask
        safe_neg = (labels != cls) & mask
        if bool(target.any()):
            terms.append(_masked_abs_mean(torch.relu(0.20 - pos[:, 0] + neg[:, 0]), target))
        if bool(safe_neg.any()):
            terms.append(_masked_abs_mean(torch.relu(0.20 + pos[:, 0] - neg[:, 0]), safe_neg))
    if not terms:
        return outputs["logits"].sum() * 0.0
    return torch.stack(terms).mean()


def _source_arbiter_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    availability: torch.Tensor,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    valid = labels != IGNORE_LABEL
    t2_present = availability[:, 1].to(device=labels.device, dtype=torch.bool).view(-1, 1, 1, 1)
    losses: list[torch.Tensor] = []
    metrics: dict[str, torch.Tensor] = {}
    for prefix, cls, mask in (
        ("scar", SCAR_CLASS, valid),
        ("edema", EDEMA_CLASS, valid & t2_present),
    ):
        proposal = outputs.get(f"{prefix}_proposal_logits")
        refiner = outputs.get(f"{prefix}_logits")
        arbiter_logits = outputs.get(f"{prefix}_source_arbiter_logits")
        if not isinstance(proposal, torch.Tensor) or not isinstance(refiner, torch.Tensor) or not isinstance(arbiter_logits, torch.Tensor):
            zero = outputs["logits"].sum() * 0.0
            metrics[f"{prefix}_source_arbiter_loss"] = zero.detach()
            metrics[f"{prefix}_source_arbiter_mask_voxels"] = zero.detach()
            continue
        target = (labels == cls).float().unsqueeze(1)
        proposal_loss = F.binary_cross_entropy_with_logits(proposal.detach(), target, reduction="none")
        refiner_loss = F.binary_cross_entropy_with_logits(refiner.detach(), target, reduction="none")
        best_refiner = (refiner_loss < proposal_loss).long()[:, 0]
        if bool(mask.any()):
            raw = F.cross_entropy(arbiter_logits, best_refiner, reduction="none")
            value = _masked_abs_mean(raw, mask)
        else:
            value = outputs["logits"].sum() * 0.0
        losses.append(value)
        metrics[f"{prefix}_source_arbiter_loss"] = value.detach()
        metrics[f"{prefix}_source_arbiter_mask_voxels"] = mask.to(device=proposal.device, dtype=proposal.dtype).sum().detach()
    return (torch.stack(losses).mean() if losses else outputs["logits"].sum() * 0.0), metrics


def _zero_like_output(outputs: dict[str, torch.Tensor]) -> torch.Tensor:
    ref = outputs.get("logits")
    if not isinstance(ref, torch.Tensor):
        raise KeyError("outputs must contain logits")
    return ref.sum() * 0.0


def br2_source_l1_sparsity_loss(outputs: dict[str, torch.Tensor], pathology: str) -> torch.Tensor:
    beta = outputs.get(f"{pathology}_br2_all_center_beta")
    mask = outputs.get(f"{pathology}_br2_source_eligibility_mask")
    if not isinstance(beta, torch.Tensor):
        beta = outputs.get(f"{pathology}_br2_effective_beta")
        mask = outputs.get(f"{pathology}_br2_availability_mask")
    if not isinstance(beta, torch.Tensor):
        return _zero_like_output(outputs)
    if isinstance(mask, torch.Tensor):
        denom = mask.to(device=beta.device, dtype=beta.dtype).sum().clamp_min(1.0)
        return (beta.abs() * mask.to(device=beta.device, dtype=beta.dtype)).sum() / denom
    return beta.abs().mean()


def br2_center_deviation_shrinkage_loss(outputs: dict[str, torch.Tensor], pathology: str) -> torch.Tensor:
    deviation = outputs.get(f"{pathology}_br2_all_center_deviation")
    if not isinstance(deviation, torch.Tensor):
        return _zero_like_output(outputs)
    return deviation.square().mean()


def br2_selective_integration_penalty(
    outputs: dict[str, torch.Tensor],
    pathology: str,
    *,
    tau: float = 0.10,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """SIP penalty over signed center-specific BR2 coefficients.

    The formal Batch7 decomposition uses the full training-center coefficient
    table, not the current batch's effective beta. Batch size is 1 in the formal
    runs, so using batch beta would make every eligible source set have size at
    most one and would silently turn SIP into a zero-valued batch proxy.
    """

    beta = outputs.get(f"{pathology}_br2_all_center_beta")
    mask = outputs.get(f"{pathology}_br2_source_eligibility_mask")
    if not isinstance(beta, torch.Tensor) or not isinstance(mask, torch.Tensor):
        zero = _zero_like_output(outputs)
        return zero, {f"{pathology}_br2_sip_terms": zero.detach()}
    mask_f = mask.to(device=beta.device, dtype=beta.dtype)
    terms = []
    tau_t = beta.new_tensor(float(tau))
    for ridx in range(beta.shape[1]):
        eligible = mask_f[:, ridx] > 0.5
        count = int(eligible.sum().detach().cpu().item())
        if count <= 1:
            continue
        selected = beta[eligible, ridx].abs()
        gamma = torch.minimum(torch.ones_like(selected), selected / tau_t).sum()
        terms.append(torch.minimum(torch.ones((), dtype=beta.dtype, device=beta.device), (count - gamma) / float(count - 1)))
    if not terms:
        zero = _zero_like_output(outputs)
        return zero, {f"{pathology}_br2_sip_terms": zero.detach()}
    loss = torch.stack(terms).sum()
    return loss, {
        f"{pathology}_br2_sip_terms": beta.new_tensor(float(len(terms))),
        f"{pathology}_br2_sip_tau": tau_t,
    }


def srr_m10_loss_component_contract(
    metrics: dict[str, torch.Tensor],
    weights: dict[str, float] | None = None,
) -> list[dict[str, object]]:
    """Classify M10 losses for alias/placeholder audit tables."""

    weights = weights or {}
    rows = []
    for name, value in metrics.items():
        if not name.startswith("loss_") or name.endswith("_weight"):
            continue
        if name in {"loss_cine_temporal_consistency", "loss_cine_reference_warp_consistency"}:
            status = "disabled_with_reason"
            reason = "wave1_shared_m10_myoPS_only"
        elif name in {"loss_pattern_sip_integrativeness", "loss_memory_bank_update_or_alignment"}:
            status = "real_optimized_loss" if bool(torch.isfinite(value.detach()).item()) else "invalid"
            reason = "independent_m10_component"
        elif float(weights.get(name, 1.0)) == 0.0:
            status = "disabled_with_reason"
            reason = "zero_configured_weight"
        else:
            status = "real_optimized_loss"
            reason = "active_component"
        rows.append(
            {
                "loss_name": name,
                "classification": status,
                "reason": reason,
                "value": float(value.detach().cpu()),
                "weight": float(weights.get(name, 1.0)),
            }
        )
    return rows


def srr_m6_expanded_total_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    availability: torch.Tensor,
    weights: dict[str, float] | None = None,
    *,
    detach_metrics: bool = True,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """M6 SRR-v3 total loss with explicit proposal/refiner/arbitration terms."""

    weights = weights or {}

    def component_weight(name: str, default: float, *aliases: str) -> float:
        for key in (name, *aliases):
            if key in weights:
                return float(weights[key])
        return float(default)

    valid = labels != IGNORE_LABEL
    t2_present = availability[:, 1].to(device=labels.device, dtype=torch.bool).view(-1, 1, 1, 1)
    scar_target = labels == SCAR_CLASS
    edema_target = labels == EDEMA_CLASS
    outside_roi = valid & (outputs["scar_soft_roi"][:, 0] < 0.05) & (outputs["edema_soft_roi"][:, 0] < 0.05)

    loss_anatomy = anatomy_loss(outputs["anatomy_logits"], labels)
    loss_scar_prop = _masked_bce_with_logits(outputs["scar_proposal_logits"][:, 0], scar_target.float(), valid)
    loss_scar_discovery = _masked_bce_with_logits(outputs["scar_discovery_logits"][:, 0], scar_target.float(), valid)
    loss_scar_confirmation = _masked_bce_with_logits(outputs["scar_confirmation_logits"][:, 0], scar_target.float(), valid)
    edema_mask = valid & t2_present
    loss_edema_prop = (
        _masked_bce_with_logits(outputs["edema_proposal_logits"][:, 0], edema_target.float(), edema_mask)
        if bool(edema_mask.any())
        else outputs["logits"].sum() * 0.0
    )
    loss_edema_discovery = (
        _masked_bce_with_logits(outputs["edema_discovery_logits"][:, 0], edema_target.float(), edema_mask)
        if bool(edema_mask.any())
        else outputs["logits"].sum() * 0.0
    )
    loss_edema_confirmation = (
        _masked_bce_with_logits(outputs["edema_confirmation_logits"][:, 0], edema_target.float(), edema_mask)
        if bool(edema_mask.any())
        else outputs["logits"].sum() * 0.0
    )
    loss_scar_ref = scar_loss(outputs["scar_logits"], labels)
    loss_edema_ref = t2_masked_edema_loss(outputs["edema_logits"], labels, availability)
    loss_final_scar, loss_final_edema = final_pathology_loss_from_logits(outputs["logits"], labels, availability)
    loss_scar_directionality, scar_directionality_metrics = scar_final_correction_directionality_loss(outputs, labels)
    loss_scar_anchor_error, scar_anchor_error_metrics = scar_final_anchor_error_pathology_loss(outputs, labels)
    loss_edema_anchor_error, edema_anchor_error_metrics = edema_final_anchor_error_pathology_loss(outputs, labels, availability)
    loss_gate_repair_preserve, gate_repair_metrics = production_gate_repair_preserve_loss(outputs, labels, availability)

    anchor_logits = outputs.get("nnunet_anchor_logits")
    loss_correction_opportunity = outputs["logits"].sum() * 0.0
    if isinstance(anchor_logits, torch.Tensor):
        anchor_probs = torch.softmax(anchor_logits, dim=1)
        final_probs = torch.softmax(outputs["logits"], dim=1)
        loss_anchor = _masked_abs_mean(final_probs - anchor_probs, outside_roi.unsqueeze(1))
        anchor_conf, anchor_pred = anchor_probs.max(dim=1)
        pathology_target = scar_target | (edema_target & t2_present)
        anchor_error = valid & pathology_target & ((anchor_pred != labels) | (anchor_conf < 0.70))
        segmentation_weight = outputs.get("segmentation_weight")
        if isinstance(segmentation_weight, torch.Tensor) and bool(anchor_error.any()):
            open_signal = (1.0 - segmentation_weight[:, 0]).clamp(0.0, 1.0)
            loss_correction_opportunity = _masked_abs_mean(1.0 - open_signal, anchor_error)
    else:
        loss_anchor = outputs["logits"].sum() * 0.0

    segmentation_weight = outputs.get("segmentation_weight")
    correction_mask = outputs.get("branch_correction_mask")
    if isinstance(segmentation_weight, torch.Tensor) and isinstance(correction_mask, torch.Tensor):
        loss_arbitration = _masked_abs_mean((1.0 - segmentation_weight) * (1.0 - correction_mask))
    else:
        loss_arbitration = outputs["logits"].sum() * 0.0

    loss_bounded = _masked_abs_mean(outputs.get("arbitration_bounded_delta", outputs.get("bounded_delta_srr", outputs["logits"] * 0.0)))
    loss_remote_fp = (
        _masked_abs_mean(torch.sigmoid(outputs["scar_logits"][:, 0]), (labels == 0) & valid)
        + _masked_abs_mean(torch.sigmoid(outputs["edema_logits"][:, 0]), (labels == 0) & valid & t2_present)
    )
    no_t2 = (~availability[:, 1].to(device=labels.device, dtype=torch.bool)).view(-1, 1, 1, 1)
    if bool(no_t2.any()):
        no_t2_edema = torch.sigmoid(outputs["edema_proposal_logits"][:, 0]) + torch.sigmoid(outputs["edema_logits"][:, 0])
        loss_no_t2 = _masked_abs_mean(no_t2_edema, no_t2)
    else:
        loss_no_t2 = outputs["logits"].sum() * 0.0

    dict_loss, dict_metrics = semantic_retrieval_regularization(
        outputs.get("gates", {}),
        outputs.get("dictionary_slot_metadata", {}),
        outputs.get("gate_valid_masks", {}),
        detach_metrics=detach_metrics,
    )
    if dict_loss is None:
        dict_loss = outputs["logits"].sum() * 0.0
    psip_loss, psip_metrics = pattern_sip_integrativeness_loss(
        outputs.get("gates", {}),
        outputs.get("dictionary_slot_metadata", {}),
        outputs.get("gate_valid_masks", {}),
        detach_metrics=detach_metrics,
    )
    if psip_loss is None:
        psip_loss = outputs["logits"].sum() * 0.0
    loss_proto = _prototype_margin_loss(outputs, labels, availability)
    loss_memory = _memory_alignment_loss(outputs, labels, availability)
    loss_source_arbiter, source_arbiter_metrics = _source_arbiter_loss(outputs, labels, availability)
    loss_br2_l1 = 0.5 * (
        br2_source_l1_sparsity_loss(outputs, "scar") + br2_source_l1_sparsity_loss(outputs, "edema")
    )
    loss_br2_center = 0.5 * (
        br2_center_deviation_shrinkage_loss(outputs, "scar") + br2_center_deviation_shrinkage_loss(outputs, "edema")
    )
    loss_scar_br2_sip, scar_br2_sip_metrics = br2_selective_integration_penalty(outputs, "scar")
    loss_edema_br2_sip, edema_br2_sip_metrics = br2_selective_integration_penalty(outputs, "edema")
    loss_br2_sip = 0.5 * (loss_scar_br2_sip + loss_edema_br2_sip)

    scar_refiner_residual = outputs.get("scar_refiner_residual", outputs.get("scar_refinement_residual", outputs["logits"][:, :1] * 0.0))
    edema_refiner_residual = outputs.get("edema_refiner_residual", outputs.get("edema_refinement_residual", outputs["logits"][:, :1] * 0.0))
    scar_refiner_effect = _masked_abs_mean(scar_refiner_residual, valid.unsqueeze(1))
    edema_refiner_effect = _masked_abs_mean(edema_refiner_residual, (valid & t2_present).unsqueeze(1))
    loss_refiner_final_label_effect = 0.5 * (scar_refiner_effect + edema_refiner_effect)

    component_weights = {
        "loss_anatomy_union_lv_rv": component_weight("loss_anatomy_union_lv_rv", 1.0, "anatomy"),
        "loss_scar_proposal": component_weight("loss_scar_proposal", 1.0, "scar_proposal", "proposal"),
        "loss_edema_proposal_t2_present_only": component_weight("loss_edema_proposal_t2_present_only", 1.0, "edema_proposal", "proposal"),
        "loss_scar_discovery_proposal": component_weight("loss_scar_discovery_proposal", 0.0),
        "loss_edema_discovery_proposal_t2_present": component_weight("loss_edema_discovery_proposal_t2_present", 0.0),
        "loss_scar_confirmation_proposal": component_weight("loss_scar_confirmation_proposal", 0.0),
        "loss_edema_confirmation_proposal_t2_present": component_weight("loss_edema_confirmation_proposal_t2_present", 0.0),
        "loss_scar_refiner_roi": component_weight("loss_scar_refiner_roi", 1.0, "loss_scar_refiner_small_roi", "scar_refiner"),
        "loss_edema_refiner_t2_present_roi": component_weight(
            "loss_edema_refiner_t2_present_roi",
            1.0,
            "loss_edema_refiner_large_roi_t2_present",
            "edema_refiner",
        ),
        "loss_final_scar_pathology": component_weight("loss_final_scar_pathology", 0.0),
        "loss_final_scar_correction_directionality": component_weight("loss_final_scar_correction_directionality", 0.0),
        "loss_final_scar_anchor_error_pathology": component_weight("loss_final_scar_anchor_error_pathology", 0.0),
        "loss_final_edema_t2_present_pathology": component_weight("loss_final_edema_t2_present_pathology", 0.0),
        "loss_final_edema_anchor_error_pathology": component_weight("loss_final_edema_anchor_error_pathology", 0.0),
        "loss_production_gate_repair_preserve": component_weight("loss_production_gate_repair_preserve", 0.0),
        "loss_anchor_preservation_outside_roi": component_weight("loss_anchor_preservation_outside_roi", 0.20, "baseline_preservation"),
        "loss_correction_opportunity": component_weight("loss_correction_opportunity", 0.20),
        "loss_branch_arbitration_consistency": component_weight("loss_branch_arbitration_consistency", 0.15),
        "loss_bounded_correction": component_weight("loss_bounded_correction", 0.02),
        "loss_component_remote_fp": component_weight("loss_component_remote_fp", 0.10, "component_remote_fp"),
        "loss_no_t2_edema_safety": component_weight("loss_no_t2_edema_safety", 0.50),
        "loss_dictionary_entropy_coverage_load_balance": component_weight(
            "loss_dictionary_entropy_coverage_load_balance",
            0.20,
            "semantic_retrieval",
        ),
        "loss_pattern_sip_integrativeness": component_weight("loss_pattern_sip_integrativeness", 0.05, "semantic_integrative"),
        "loss_prototype_diversity_margin": component_weight("loss_prototype_diversity_margin", 0.20, "prototype_margin"),
        "loss_memory_bank_update_or_alignment": component_weight("loss_memory_bank_update_or_alignment", 0.05),
        "loss_source_arbiter": component_weight("loss_source_arbiter", 0.0),
        "loss_refiner_final_label_effect": component_weight("loss_refiner_final_label_effect", 0.02),
        "loss_br2_source_l1_sparsity": component_weight("loss_br2_source_l1_sparsity", 0.0),
        "loss_br2_center_deviation_shrinkage": component_weight("loss_br2_center_deviation_shrinkage", 0.0),
        "loss_br2_selective_integration_penalty": component_weight("loss_br2_selective_integration_penalty", 0.0),
        "loss_cine_temporal_consistency": component_weight("loss_cine_temporal_consistency", 0.0),
        "loss_cine_reference_warp_consistency": component_weight("loss_cine_reference_warp_consistency", 0.0),
    }
    components = {
        "loss_anatomy_union_lv_rv": loss_anatomy,
        "loss_scar_proposal": loss_scar_prop,
        "loss_edema_proposal_t2_present_only": loss_edema_prop,
        "loss_scar_discovery_proposal": loss_scar_discovery,
        "loss_edema_discovery_proposal_t2_present": loss_edema_discovery,
        "loss_scar_confirmation_proposal": loss_scar_confirmation,
        "loss_edema_confirmation_proposal_t2_present": loss_edema_confirmation,
        "loss_scar_refiner_roi": loss_scar_ref,
        "loss_edema_refiner_t2_present_roi": loss_edema_ref,
        "loss_final_scar_pathology": loss_final_scar,
        "loss_final_scar_correction_directionality": loss_scar_directionality,
        "loss_final_scar_anchor_error_pathology": loss_scar_anchor_error,
        "loss_final_edema_t2_present_pathology": loss_final_edema,
        "loss_final_edema_anchor_error_pathology": loss_edema_anchor_error,
        "loss_production_gate_repair_preserve": loss_gate_repair_preserve,
        "loss_anchor_preservation_outside_roi": loss_anchor,
        "loss_correction_opportunity": loss_correction_opportunity,
        "loss_branch_arbitration_consistency": loss_arbitration,
        "loss_bounded_correction": loss_bounded,
        "loss_component_remote_fp": loss_remote_fp,
        "loss_no_t2_edema_safety": loss_no_t2,
        "loss_dictionary_entropy_coverage_load_balance": dict_loss,
        "loss_pattern_sip_integrativeness": psip_loss,
        "loss_prototype_diversity_margin": loss_proto,
        "loss_memory_bank_update_or_alignment": loss_memory,
        "loss_source_arbiter": loss_source_arbiter,
        "loss_refiner_final_label_effect": loss_refiner_final_label_effect,
        "loss_br2_source_l1_sparsity": loss_br2_l1,
        "loss_br2_center_deviation_shrinkage": loss_br2_center,
        "loss_br2_selective_integration_penalty": loss_br2_sip,
        "loss_cine_temporal_consistency": outputs["logits"].sum() * 0.0,
        "loss_cine_reference_warp_consistency": outputs["logits"].sum() * 0.0,
    }
    total = sum(float(component_weights[name]) * value for name, value in components.items())
    metrics = {name: value.detach() if detach_metrics else value for name, value in components.items()}
    metrics.update({f"{name}_weight": outputs["logits"].new_tensor(float(weight)) for name, weight in component_weights.items()})
    metrics["loss_scar_refiner_small_roi"] = metrics["loss_scar_refiner_roi"]
    metrics["loss_edema_refiner_large_roi_t2_present"] = metrics["loss_edema_refiner_t2_present_roi"]
    metrics["loss_scar_refiner_small_roi_weight"] = outputs["logits"].new_tensor(float(component_weights["loss_scar_refiner_roi"]))
    metrics["loss_edema_refiner_large_roi_t2_present_weight"] = outputs["logits"].new_tensor(
        float(component_weights["loss_edema_refiner_t2_present_roi"])
    )
    metrics.update(dict_metrics)
    metrics.update(psip_metrics)
    metrics.update(scar_br2_sip_metrics)
    metrics.update(edema_br2_sip_metrics)
    metrics.update(gate_repair_metrics)
    metrics.update(source_arbiter_metrics)
    metrics.update(scar_directionality_metrics)
    metrics.update(scar_anchor_error_metrics)
    metrics.update(edema_anchor_error_metrics)
    metrics["loss_component_contract_rows"] = srr_m10_loss_component_contract(metrics, component_weights)  # type: ignore[assignment]
    metrics["m6_expanded_total_loss"] = total.detach() if detach_metrics else total
    return total, metrics
