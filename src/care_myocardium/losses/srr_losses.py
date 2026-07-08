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
    edema_mask = valid & t2_present
    loss_edema_prop = (
        _masked_bce_with_logits(outputs["edema_proposal_logits"][:, 0], edema_target.float(), edema_mask)
        if bool(edema_mask.any())
        else outputs["logits"].sum() * 0.0
    )
    loss_scar_ref = scar_loss(outputs["scar_logits"], labels)
    loss_edema_ref = t2_masked_edema_loss(outputs["edema_logits"], labels, availability)

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
    loss_proto = _prototype_margin_loss(outputs, labels, availability)

    scar_refiner_residual = outputs.get("scar_refiner_residual", outputs.get("scar_refinement_residual", outputs["logits"][:, :1] * 0.0))
    edema_refiner_residual = outputs.get("edema_refiner_residual", outputs.get("edema_refinement_residual", outputs["logits"][:, :1] * 0.0))
    scar_refiner_effect = _masked_abs_mean(scar_refiner_residual, valid.unsqueeze(1))
    edema_refiner_effect = _masked_abs_mean(edema_refiner_residual, (valid & t2_present).unsqueeze(1))
    loss_refiner_final_label_effect = 0.5 * (scar_refiner_effect + edema_refiner_effect)

    component_weights = {
        "loss_anatomy_union_lv_rv": component_weight("loss_anatomy_union_lv_rv", 1.0, "anatomy"),
        "loss_scar_proposal": component_weight("loss_scar_proposal", 1.0, "scar_proposal", "proposal"),
        "loss_edema_proposal_t2_present_only": component_weight("loss_edema_proposal_t2_present_only", 1.0, "edema_proposal", "proposal"),
        "loss_scar_refiner_roi": component_weight("loss_scar_refiner_roi", 1.0, "loss_scar_refiner_small_roi", "scar_refiner"),
        "loss_edema_refiner_t2_present_roi": component_weight(
            "loss_edema_refiner_t2_present_roi",
            1.0,
            "loss_edema_refiner_large_roi_t2_present",
            "edema_refiner",
        ),
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
        "loss_refiner_final_label_effect": component_weight("loss_refiner_final_label_effect", 0.02),
        "loss_cine_temporal_consistency": component_weight("loss_cine_temporal_consistency", 0.0),
        "loss_cine_reference_warp_consistency": component_weight("loss_cine_reference_warp_consistency", 0.0),
    }
    components = {
        "loss_anatomy_union_lv_rv": loss_anatomy,
        "loss_scar_proposal": loss_scar_prop,
        "loss_edema_proposal_t2_present_only": loss_edema_prop,
        "loss_scar_refiner_roi": loss_scar_ref,
        "loss_edema_refiner_t2_present_roi": loss_edema_ref,
        "loss_anchor_preservation_outside_roi": loss_anchor,
        "loss_correction_opportunity": loss_correction_opportunity,
        "loss_branch_arbitration_consistency": loss_arbitration,
        "loss_bounded_correction": loss_bounded,
        "loss_component_remote_fp": loss_remote_fp,
        "loss_no_t2_edema_safety": loss_no_t2,
        "loss_dictionary_entropy_coverage_load_balance": dict_loss,
        "loss_pattern_sip_integrativeness": dict_loss,
        "loss_prototype_diversity_margin": loss_proto,
        "loss_memory_bank_update_or_alignment": loss_proto,
        "loss_refiner_final_label_effect": loss_refiner_final_label_effect,
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
    metrics["m6_expanded_total_loss"] = total.detach() if detach_metrics else total
    return total, metrics
