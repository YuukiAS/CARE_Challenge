#!/usr/bin/env python3
"""Train/evaluate SRR-ProposeRefine MyoPS fold0 variants."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk
import torch
import torch.nn.functional as F
from scipy.ndimage import generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import (  # noqa: E402
    CaseData,
    collect_case_metrics,
    crop_or_pad,
    load_hard_negative_targets,
    load_split,
    parse_shape,
    read_case,
    record_gate_usage,
    sample_patch,
    summarize_subgroups,
    write_csv,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.losses.srr_losses import anatomy_loss, retrieval_regularization, scar_loss, semantic_retrieval_regularization, t2_masked_edema_loss  # noqa: E402
from src.care_myocardium.models.proposal_prototypes import PrototypeBank, build_prototype_bank_from_labeled_features  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402


OUT_ROOT = REPO_ROOT / "results/20260703_srr_propref_repair"
IGNORE_LABEL = -1
DEFAULT_PROPOSAL_THRESHOLDS = "0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90"
DEFAULT_NNUNET_ANCHOR_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)


@dataclass
class AnchoredCaseData:
    case_id: str
    image: np.ndarray
    label_arr: np.ndarray
    label_img: sitk.Image
    availability: np.ndarray
    metadata: object
    anchor_probabilities: np.ndarray
    component_features: np.ndarray
    anchor_source: str
    anchor_fold: int


def _masked_bce_dice(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    target_f = target.to(dtype=logits.dtype, device=logits.device)
    mask_f = mask.to(dtype=logits.dtype, device=logits.device)
    bce = F.binary_cross_entropy_with_logits(logits, target_f, reduction="none")
    bce = (bce * mask_f).sum() / mask_f.sum().clamp_min(1.0)
    prob = torch.sigmoid(logits)
    axes = tuple(range(1, prob.ndim))
    inter = (prob * target_f * mask_f).sum(dim=axes)
    denom = (prob * mask_f).sum(dim=axes) + (target_f * mask_f).sum(dim=axes)
    dice = (1.0 - (2.0 * inter + 1e-6) / (denom + 1e-6)).mean()
    return 0.5 * bce + 0.5 * dice


def _masked_mean(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    mask_f = mask.to(dtype=values.dtype, device=values.device)
    return (values * mask_f).sum() / mask_f.sum().clamp_min(1.0)


def stage_for_step(step: int, max_steps: int) -> str:
    frac = (step - 1) / max(1, max_steps)
    if frac <= 0.20:
        return "evidence_warmup"
    if frac <= 0.60:
        return "proposal_dictionary"
    if frac <= 0.90:
        return "soft_roi_refinement"
    return "low_lr_calibration"


def parse_float_list(text: str) -> list[float]:
    values = [float(x) for x in str(text).replace(";", ",").split(",") if x.strip()]
    if not values:
        raise ValueError("at least one threshold is required")
    return sorted({min(max(v, 0.0), 1.0) for v in values})


def parse_case_id_list(text: str | None) -> list[str]:
    if text is None:
        return []
    return [item.strip() for item in str(text).replace(";", ",").split(",") if item.strip()]


def ensure_t2_edema_prototype_cases(
    train_cases: list[AnchoredCaseData],
    all_train_ids: list[str],
    metadata: dict[str, object],
    anchor_root: Path,
    args: argparse.Namespace,
) -> tuple[list[AnchoredCaseData], list[str]]:
    """Preserve T2-present edema prototype evidence after small train-subset limits.

    Earlier bounded smoke runs could pass only the first LGE-only cases through
    ``--limit-train-cases`` and then fit an empty edema prototype bank.  M2 keeps
    the smoke subset small but appends a few same-split T2 edema-positive cases
    when prototype fitting would otherwise have no valid edema positives.
    """

    if args.variant == "srr_propref_no_proto_cascade" or bool(getattr(args, "skip_prototype_bank_fit", False)):
        return train_cases, []
    if any(case.metadata.t2_present and np.any(case.label_arr == 4) for case in train_cases):
        return train_cases, []
    selected_ids = {case.case_id for case in train_cases}
    target = max(1, min(int(getattr(args, "prototype_bank_cases", 1)), 4))
    added: list[str] = []
    repaired = list(train_cases)
    for case_id in all_train_ids:
        if case_id in selected_ids:
            continue
        case = read_anchored_case(case_id, metadata, anchor_root)
        if not (case.metadata.t2_present and np.any(case.label_arr == 4)):
            continue
        repaired.append(case)
        selected_ids.add(case_id)
        added.append(case_id)
        if len(added) >= target:
            break
    return repaired, added


def _anchor_root(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def _find_anchor_paths(case_id: str, anchor_root: Path) -> tuple[int, Path, Path]:
    matches: list[tuple[int, Path, Path]] = []
    for fold_dir in sorted(anchor_root.glob("fold_*")):
        try:
            fold = int(fold_dir.name.split("_", 1)[1])
        except (IndexError, ValueError):
            continue
        prob_path = fold_dir / "validation" / f"{case_id}.npz"
        pred_path = fold_dir / "validation" / f"{case_id}.nii.gz"
        if prob_path.is_file() and pred_path.is_file():
            matches.append((fold, prob_path, pred_path))
    if not matches:
        raise FileNotFoundError(f"nnU-Net anchor probabilities/prediction not found for {case_id} under {anchor_root}")
    return matches[0]


def _load_anchor_probabilities(prob_path: Path, reference_shape: tuple[int, int, int]) -> np.ndarray:
    with np.load(prob_path) as data:
        if "probabilities" not in data:
            raise KeyError(f"{prob_path} does not contain a 'probabilities' array")
        probs = data["probabilities"].astype(np.float32, copy=False)
    if probs.ndim != 4 or probs.shape[0] < 6:
        raise ValueError(f"{prob_path} must have shape (C,D,H,W) with at least 6 classes, got {probs.shape}")
    probs = probs[:6]
    if tuple(probs.shape[-3:]) != tuple(reference_shape):
        raise ValueError(f"{prob_path} spatial shape {probs.shape[-3:]} does not match label shape {reference_shape}")
    return np.clip(probs, 0.0, 1.0).astype(np.float32, copy=False)


def _load_component_features(pred_path: Path, reference_shape: tuple[int, int, int]) -> np.ndarray:
    pred = sitk.GetArrayFromImage(sitk.ReadImage(str(pred_path))).astype(np.uint8, copy=False)
    if tuple(pred.shape) != tuple(reference_shape):
        raise ValueError(f"{pred_path} spatial shape {pred.shape} does not match label shape {reference_shape}")
    components = []
    for cls in (5, 4):
        cc, n_cc = label((pred == cls).astype(bool), structure=generate_binary_structure(pred.ndim, 1))
        components.append((cc > 0 if n_cc > 0 else np.zeros_like(pred, dtype=bool)).astype(np.float32, copy=False))
    return np.stack(components, axis=0).astype(np.float32, copy=False)


def read_anchored_case(case_id: str, metadata: dict[str, object], anchor_root: Path) -> AnchoredCaseData:
    base = read_case(case_id, metadata)  # type: ignore[arg-type]
    fold, prob_path, pred_path = _find_anchor_paths(case_id, anchor_root)
    anchor = _load_anchor_probabilities(prob_path, tuple(base.label_arr.shape))
    components = _load_component_features(pred_path, tuple(base.label_arr.shape))
    if not bool(base.availability[1] > 0):
        anchor[4] = 0.0
        components[1] = 0.0
    return AnchoredCaseData(
        case_id=base.case_id,
        image=base.image,
        label_arr=base.label_arr,
        label_img=base.label_img,
        availability=base.availability,
        metadata=base.metadata,
        anchor_probabilities=anchor,
        component_features=components,
        anchor_source=str(prob_path),
        anchor_fold=fold,
    )


def _crop_patch_arrays(
    case: AnchoredCaseData,
    patch_shape: tuple[int, int, int],
    rng: np.random.Generator,
    oversample_foreground: float,
    focus_classes: tuple[int, ...],
    forced_center_zyx: tuple[int, int, int] | None,
) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int]]:
    label_arr = case.label_arr
    focus = np.argwhere(np.isin(label_arr, focus_classes))
    if forced_center_zyx is not None:
        center = np.asarray(forced_center_zyx, dtype=np.int64)
    elif len(focus) and rng.random() < oversample_foreground:
        center = focus[int(rng.integers(0, len(focus)))]
    else:
        valid = np.argwhere(label_arr >= 0)
        center = valid[int(rng.integers(0, len(valid)))] if len(valid) else np.asarray(label_arr.shape) // 2
    starts = tuple(int(c - p // 2) for c, p in zip(center, patch_shape))
    image = crop_or_pad(case.image, starts, patch_shape, 0.0).astype(np.float32, copy=False)
    target = crop_or_pad(label_arr[None], starts, patch_shape, IGNORE_LABEL).astype(np.int64, copy=False)[0]
    return image, target, starts


def sample_patch_with_anchor(
    case: AnchoredCaseData,
    patch_shape: tuple[int, int, int],
    rng: np.random.Generator,
    oversample_foreground: float,
    modality_dropout: bool,
    focus_classes: tuple[int, ...] = (4, 5),
    forced_center_zyx: tuple[int, int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    image, target, starts = _crop_patch_arrays(case, patch_shape, rng, oversample_foreground, focus_classes, forced_center_zyx)
    anchor = crop_or_pad(case.anchor_probabilities, starts, patch_shape, 0.0).astype(np.float32, copy=False)
    components = crop_or_pad(case.component_features, starts, patch_shape, 0.0).astype(np.float32, copy=False)
    availability = case.availability.copy()
    original_availability = availability.copy()
    if modality_dropout:
        # Preserve LGE. If virtual dropout changes the observed modality set,
        # the precomputed nnU-Net anchor is no longer valid for that synthetic
        # missing-modality view, so anchor/component evidence is removed.
        if availability[1] > 0 and rng.random() < 0.15:
            availability[1] = 0.0
            image[1] = 0.0
        if availability[2] > 0 and rng.random() < 0.15:
            availability[2] = 0.0
            image[2] = 0.0
    if not np.array_equal(availability, original_availability):
        anchor[...] = 0.0
        components[...] = 0.0
    if not bool(availability[1] > 0):
        anchor[4] = 0.0
        components[1] = 0.0
    return image, target, availability, anchor, components


def anchor_dict_from_tensor(anchor: torch.Tensor) -> dict[str, torch.Tensor]:
    return {
        "probabilities": anchor,
        "scar_prob": anchor[:, 5:6],
        "edema_prob": anchor[:, 4:5],
    }


def component_dict_from_tensor(component: torch.Tensor) -> dict[str, torch.Tensor]:
    return {
        "scar_component": component[:, 0:1],
        "edema_component": component[:, 1:2],
    }


def batch_from_anchored_cases(
    cases: list[AnchoredCaseData],
    complete_cases: list[AnchoredCaseData],
    scar_cases: list[AnchoredCaseData],
    lge_only_scar_cases: list[AnchoredCaseData],
    edema_t2_cases: list[AnchoredCaseData],
    center_c_t2_edema_cases: list[AnchoredCaseData],
    batch_size: int,
    patch_shape: tuple[int, int, int],
    rng: np.random.Generator,
    complete_oversample: float,
    oversample_foreground: float,
    modality_dropout: bool,
    hardneg_targets: dict[str, list[object]] | None = None,
    hardneg_sample_prob: float = 0.0,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, dict[str, torch.Tensor], dict[str, torch.Tensor], list[str]]:
    xs, ys, avs, anchors, components, keys = [], [], [], [], [], []
    hardneg_targets = hardneg_targets or {}
    hardneg_cases = [case for case in cases if hardneg_targets.get(case.case_id)]
    for _ in range(batch_size):
        focus_classes = (4, 5)
        effective_oversample = oversample_foreground
        forced_center = None
        if hardneg_cases and rng.random() < hardneg_sample_prob:
            case = hardneg_cases[int(rng.integers(0, len(hardneg_cases)))]
            target = hardneg_targets[case.case_id][int(rng.integers(0, len(hardneg_targets[case.case_id])))]
            forced_center = target.center_zyx
            focus_classes = (target.class_id,)
            effective_oversample = 0.0
        else:
            pool = complete_cases if complete_cases and rng.random() < complete_oversample else cases
            case = pool[int(rng.integers(0, len(pool)))]
        x, y, av, anchor, component = sample_patch_with_anchor(
            case,
            patch_shape,
            rng,
            effective_oversample,
            modality_dropout,
            focus_classes=focus_classes,
            forced_center_zyx=forced_center,
        )
        xs.append(x)
        ys.append(y)
        avs.append(av)
        anchors.append(anchor)
        components.append(component)
        keys.append(case.case_id)
    anchor_t = torch.from_numpy(np.stack(anchors, axis=0)).float()
    component_t = torch.from_numpy(np.stack(components, axis=0)).float()
    return (
        torch.from_numpy(np.stack(xs, axis=0)).float(),
        torch.from_numpy(np.stack(ys, axis=0)).long(),
        torch.from_numpy(np.stack(avs, axis=0)).float(),
        anchor_dict_from_tensor(anchor_t),
        component_dict_from_tensor(component_t),
        keys,
    )


def full_case_anchor_tensors(case: AnchoredCaseData, device: torch.device) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
    anchor = case.anchor_probabilities.copy()
    component = case.component_features.copy()
    if not bool(case.availability[1] > 0):
        anchor[4] = 0.0
        component[1] = 0.0
    anchor_t = torch.from_numpy(anchor[None]).float().to(device)
    component_t = torch.from_numpy(component[None]).float().to(device)
    return anchor_dict_from_tensor(anchor_t), component_dict_from_tensor(component_t)


def output_variant_name(args: argparse.Namespace) -> str:
    label = str(getattr(args, "run_label", "") or "").strip()
    return label or str(args.variant)


def model_kwargs_from_args(args: argparse.Namespace) -> dict[str, object]:
    return {
        "base_channels": args.base_channels,
        "variant": args.variant,
        "encoder_profile": args.encoder_profile,
        "disable_local_refinement": bool(getattr(args, "disable_local_refinement", False)),
        "disable_anatomy_roi_prior": bool(getattr(args, "disable_anatomy_roi_prior", False)),
    }


def maybe_disable_context(
    args: argparse.Namespace,
    anchor_features: dict[str, torch.Tensor],
    component_features: dict[str, torch.Tensor],
) -> tuple[dict[str, torch.Tensor] | None, dict[str, torch.Tensor] | None]:
    if bool(getattr(args, "disable_nnunet_anchor", False)):
        return None, None
    return anchor_features, component_features


def context_present_fraction(context: dict[str, torch.Tensor] | None, keys: tuple[str, ...]) -> float:
    if context is None:
        return 0.0
    tensors = [context[key].flatten(1).abs().sum(dim=1) for key in keys if key in context and isinstance(context[key], torch.Tensor)]
    if not tensors:
        return 0.0
    summed = torch.stack(tensors, dim=0).sum(dim=0)
    return float((summed > 0).float().mean().detach().cpu())


def required_validation_steps(max_steps: int, val_every: int) -> set[int]:
    steps = {
        max(1, min(max_steps, int(math.ceil(max_steps * 0.20)))),
        max(1, min(max_steps, int(math.ceil(max_steps * 0.60)))),
        max(1, min(max_steps, int(math.ceil(max_steps * 0.90)))),
        max(1, max_steps),
    }
    if val_every > 0:
        steps.update(range(val_every, max_steps + 1, val_every))
    return steps


def stage_counts(actual_steps: int, max_steps: int) -> dict[str, int]:
    counts = {name: 0 for name in ("evidence_warmup", "proposal_dictionary", "soft_roi_refinement", "low_lr_calibration")}
    for step in range(1, actual_steps + 1):
        counts[stage_for_step(step, max_steps)] += 1
    return counts


def parameter_count(model: torch.nn.Module) -> int:
    return int(sum(param.numel() for param in model.parameters()))


def encoder_scale_channels_from_args(args: argparse.Namespace) -> list[int]:
    base = int(args.base_channels)
    if args.encoder_profile == "strong_4scale":
        return [base, base * 2, base * 4, base * 8]
    return [base, base * 2, base * 4]


def _component_proposal_ranking_loss(
    logits: torch.Tensor,
    target: torch.Tensor,
    valid: torch.Tensor,
    safe_negative: torch.Tensor,
    *,
    margin: float,
    max_negative_voxels: int = 64,
) -> torch.Tensor:
    """Rank each GT lesion component above safe-negative proposal islands.

    Connected-component labels are used only to choose fixed target voxels; the
    loss remains differentiable with respect to proposal logits selected by
    those masks. This gives the proposal decoder a component-level objective in
    addition to dense BCE/Dice.
    """

    losses: list[torch.Tensor] = []
    for bidx in range(int(logits.shape[0])):
        target_np = target[bidx].detach().cpu().numpy().astype(bool)
        cc, n_cc = label(target_np, structure=generate_binary_structure(target_np.ndim, 1))
        neg_mask = (safe_negative[bidx] & valid[bidx] & (~target[bidx])).to(device=logits.device, dtype=torch.bool)
        neg_values = logits[bidx][neg_mask]
        if neg_values.numel() == 0:
            continue
        topk = min(int(max_negative_voxels), int(neg_values.numel()))
        neg_score = torch.topk(neg_values, k=topk).values.mean()
        for comp_idx in range(1, int(n_cc) + 1):
            comp_mask_np = cc == comp_idx
            if not bool(comp_mask_np.any()):
                continue
            comp_mask = torch.from_numpy(comp_mask_np).to(device=logits.device, dtype=torch.bool)
            pos_values = logits[bidx][comp_mask]
            if pos_values.numel() == 0:
                continue
            pos_score = torch.logsumexp(pos_values, dim=0) - pos_values.new_tensor(float(pos_values.numel())).log()
            losses.append(torch.relu(logits.new_tensor(float(margin)) - pos_score + neg_score))
    if not losses:
        return logits.sum() * 0.0
    return torch.stack(losses).mean()


def _baseline_preservation_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    valid: torch.Tensor,
    *,
    confidence_threshold: float,
    gate_weight: float,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    anchor_logits = outputs.get("nnunet_anchor_logits")
    final_logits = outputs.get("logits")
    gate = outputs.get("baseline_residual_gate")
    if anchor_logits is None or final_logits is None or gate is None:
        zero = labels.new_tensor(0.0, dtype=torch.float32)
        return zero, {
            "baseline_preservation_loss": zero,
            "baseline_preserve_voxels": zero,
            "baseline_preserve_gate_mean": zero,
        }
    if str(outputs.get("baseline_gate_status", "")) != "baseline_preserving_residual":
        zero = final_logits.sum() * 0.0
        return zero, {
            "baseline_preservation_loss": zero.detach(),
            "baseline_preserve_voxels": zero.detach(),
            "baseline_preserve_gate_mean": zero.detach(),
        }
    anchor_prob = torch.softmax(anchor_logits, dim=1)
    final_prob = torch.softmax(final_logits, dim=1)
    anchor_conf, anchor_pred = anchor_prob.max(dim=1)
    preserve_mask = valid & (anchor_pred == labels) & (anchor_conf >= float(confidence_threshold))
    if not bool(preserve_mask.any()):
        zero = final_logits.sum() * 0.0
        return zero, {
            "baseline_preservation_loss": zero.detach(),
            "baseline_preserve_voxels": zero.detach(),
            "baseline_preserve_gate_mean": zero.detach(),
        }
    mask_f = preserve_mask.to(device=final_logits.device, dtype=final_logits.dtype).unsqueeze(1)
    prob_diff = ((final_prob - anchor_prob).abs() * mask_f).sum() / mask_f.sum().clamp_min(1.0)
    gate_penalty = (gate.abs() * mask_f).sum() / mask_f.sum().clamp_min(1.0)
    loss = prob_diff + float(gate_weight) * gate_penalty
    return loss, {
        "baseline_preservation_loss": loss.detach(),
        "baseline_preserve_voxels": preserve_mask.to(dtype=final_logits.dtype).sum().detach(),
        "baseline_preserve_gate_mean": gate_penalty.detach(),
    }


def propref_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    availability: torch.Tensor,
    stage: str,
    args: argparse.Namespace,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    valid = labels != IGNORE_LABEL
    t2_present = availability[:, 1].to(dtype=torch.bool, device=labels.device).view(-1, 1, 1, 1)
    evidence_outputs = {
        "anatomy_logits": outputs["anatomy_logits"],
        "scar_logits": outputs["scar_evidence_logits"],
        "edema_logits": outputs["edema_evidence_logits"],
        "union_prior_logits": outputs["union_prior_logits"],
        "logits": torch.cat([outputs["anatomy_logits"], outputs["edema_evidence_logits"], outputs["scar_evidence_logits"]], dim=1),
        "gates": outputs["gates"],
    }
    final_outputs = {
        "anatomy_logits": outputs["anatomy_logits"],
        "scar_logits": outputs["scar_logits"],
        "edema_logits": outputs["edema_logits"],
        "union_prior_logits": outputs["union_prior_logits"],
        "logits": outputs["logits"],
        "gates": outputs["gates"],
    }

    evidence = (
        args.anatomy_weight * anatomy_loss(evidence_outputs["anatomy_logits"], labels)
        + args.scar_weight * scar_loss(evidence_outputs["scar_logits"], labels)
        + args.edema_weight * t2_masked_edema_loss(evidence_outputs["edema_logits"], labels, availability)
    )
    reg, _ = retrieval_regularization(outputs["gates"], entropy_floor=0.55, entropy_weight=0.04, coverage_weight=0.04, max_weight_penalty=0.02)
    semantic_reg, semantic_metrics = semantic_retrieval_regularization(
        outputs.get("gates", {}),
        outputs.get("dictionary_slot_metadata", {}),
        outputs.get("gate_valid_masks", {}),
        semantic_weight=args.semantic_retrieval_weight,
        coverage_weight=args.semantic_coverage_weight,
        integrative_weight=args.semantic_integrative_weight,
    )
    if reg is not None:
        evidence = evidence + reg
    if semantic_reg is not None:
        evidence = evidence + semantic_reg

    final = (
        args.anatomy_weight * anatomy_loss(final_outputs["anatomy_logits"], labels)
        + args.scar_weight * scar_loss(final_outputs["scar_logits"], labels)
        + args.edema_weight * t2_masked_edema_loss(final_outputs["edema_logits"], labels, availability)
    )

    scar_target = labels == 5
    edema_target = labels == 4
    scar_proposal = _masked_bce_dice(outputs["scar_proposal_logits"][:, 0], scar_target, valid)
    edema_mask = valid & t2_present
    edema_proposal = (
        _masked_bce_dice(outputs["edema_proposal_logits"][:, 0], edema_target, edema_mask)
        if bool(edema_mask.any())
        else outputs["logits"].sum() * 0.0
    )

    margin_terms = []
    for prefix, pos_mask, safe_neg in [
        ("scar", scar_target & valid, (~scar_target) & valid),
        ("edema", edema_target & valid & t2_present, (~edema_target) & valid & t2_present),
    ]:
        pos = outputs[f"{prefix}_pos_similarity"][:, 0]
        neg = outputs[f"{prefix}_neg_similarity"][:, 0]
        if bool(pos_mask.any()):
            margin_terms.append(_masked_mean(torch.relu(args.proposal_margin - pos + neg), pos_mask))
        if bool(safe_neg.any()):
            margin_terms.append(_masked_mean(torch.relu(args.proposal_margin + pos - neg), safe_neg))
    margin = torch.stack(margin_terms).mean() if margin_terms else outputs["logits"].sum() * 0.0
    scar_component_rank = _component_proposal_ranking_loss(
        outputs["scar_proposal_logits"][:, 0],
        scar_target,
        valid,
        (~scar_target) & valid,
        margin=args.component_proposal_margin,
    )
    edema_component_rank = _component_proposal_ranking_loss(
        outputs["edema_proposal_logits"][:, 0],
        edema_target & t2_present,
        edema_mask,
        (~edema_target) & edema_mask,
        margin=args.component_proposal_margin,
    )
    component_rank = 0.5 * (scar_component_rank + edema_component_rank)

    scar_roi = outputs["scar_soft_roi"][:, 0]
    edema_roi = outputs["edema_soft_roi"][:, 0]
    roi_cover = 0.5 * _masked_bce_dice(torch.logit(scar_roi.clamp(1e-4, 1 - 1e-4)), scar_target, valid)
    if bool(edema_mask.any()):
        roi_cover = roi_cover + 0.5 * _masked_bce_dice(torch.logit(edema_roi.clamp(1e-4, 1 - 1e-4)), edema_target, edema_mask)
    roi_remote = (scar_roi * (labels == 0).to(scar_roi.dtype)).mean()
    if bool(t2_present.any()):
        roi_remote = roi_remote + (edema_roi * (labels == 0).to(edema_roi.dtype) * t2_present.to(edema_roi.dtype)).mean()

    baseline_preserve, baseline_metrics = _baseline_preservation_loss(
        outputs,
        labels,
        valid,
        confidence_threshold=args.baseline_preservation_confidence,
        gate_weight=args.baseline_gate_harm_weight,
    )

    if stage == "evidence_warmup":
        total = evidence
        proposal_weight = 0.0
        refine_weight = 0.0
    elif stage == "proposal_dictionary":
        proposal_weight = args.proposal_weight
        refine_weight = 0.20
        total = evidence + proposal_weight * (
            scar_proposal
            + edema_proposal
            + args.margin_weight * margin
            + args.component_proposal_weight * component_rank
        )
    else:
        proposal_weight = args.proposal_weight
        refine_weight = 1.0
        total = (
            0.35 * evidence
            + refine_weight * final
            + proposal_weight * (
                scar_proposal
                + edema_proposal
                + args.margin_weight * margin
                + args.component_proposal_weight * component_rank
            )
            + args.roi_weight * roi_cover
            + args.roi_remote_weight * roi_remote
        )
    total = total + args.baseline_preservation_weight * baseline_preserve

    return total, {
        "evidence_loss": evidence.detach(),
        "final_loss": final.detach(),
        "scar_proposal_loss": scar_proposal.detach(),
        "edema_proposal_loss": edema_proposal.detach(),
        "proposal_margin_loss": margin.detach(),
        "scar_component_ranking_loss": scar_component_rank.detach(),
        "edema_component_ranking_loss": edema_component_rank.detach(),
        "component_proposal_ranking_loss": component_rank.detach(),
        "roi_cover_loss": roi_cover.detach(),
        "roi_remote_loss": roi_remote.detach(),
        "semantic_retrieval_loss": semantic_metrics.get("semantic_retrieval_loss", outputs["logits"].sum().detach() * 0.0),
        "baseline_preservation_loss": baseline_metrics["baseline_preservation_loss"],
        "baseline_preserve_voxels": baseline_metrics["baseline_preserve_voxels"],
        "baseline_preserve_gate_mean": baseline_metrics["baseline_preserve_gate_mean"],
        "proposal_weight": outputs["logits"].new_tensor(proposal_weight),
        "refine_weight": outputs["logits"].new_tensor(refine_weight),
    }


def _safe_mean(values: list[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None and np.isfinite(float(v))]
    return float(mean(vals)) if vals else None


def _component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def _lesion_recall(proposal: np.ndarray, gt_mask: np.ndarray) -> float | None:
    cc, n_cc = label(gt_mask.astype(bool), structure=generate_binary_structure(gt_mask.ndim, 1))
    if n_cc == 0:
        return None
    hit = 0
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if np.logical_and(comp, proposal).any():
            hit += 1
    return float(hit / n_cc)


def _fp_counts(pred_mask: np.ndarray, gt_mask: np.ndarray, small_threshold: int = 20) -> tuple[int, int]:
    cc, n_cc = label(pred_mask.astype(bool), structure=generate_binary_structure(pred_mask.ndim, 1))
    small_fp = 0
    remote_fp = 0
    gt_coords = np.argwhere(gt_mask)
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if np.logical_and(comp, gt_mask).any():
            continue
        if int(comp.sum()) < small_threshold:
            small_fp += 1
        if len(gt_coords) == 0:
            remote_fp += 1
            continue
        coords = np.argwhere(comp)
        comp_center = coords.mean(axis=0)
        gt_min = gt_coords.min(axis=0)
        gt_max = gt_coords.max(axis=0)
        outside = np.maximum(0, np.maximum(gt_min - comp_center, comp_center - gt_max))
        if float(np.linalg.norm(outside)) > 20.0:
            remote_fp += 1
    return small_fp, remote_fp


def _decode_argmax(outputs: dict[str, torch.Tensor]) -> torch.Tensor:
    return torch.argmax(outputs["logits"], dim=1)


def _decode_pathology_aware(
    outputs: dict[str, torch.Tensor],
    *,
    scar_threshold: float,
    edema_threshold: float,
) -> torch.Tensor:
    pred = _decode_argmax(outputs)
    scar_prob = torch.sigmoid(outputs["scar_logits"][:, 0])
    edema_prob = torch.sigmoid(outputs["edema_logits"][:, 0])
    scar_support = (
        (torch.sigmoid(outputs["scar_proposal_logits"][:, 0]) >= scar_threshold)
        | (pred == 5)
    )
    edema_support = (
        (torch.sigmoid(outputs["edema_proposal_logits"][:, 0]) >= edema_threshold)
        | (pred == 4)
    )
    scar_mask = (scar_prob >= scar_threshold) & scar_support
    edema_mask = (edema_prob >= edema_threshold) & edema_support
    conflict = scar_mask & edema_mask
    pred = torch.where(edema_mask, torch.full_like(pred, 4), pred)
    pred = torch.where(scar_mask, torch.full_like(pred, 5), pred)
    pred = torch.where(conflict & (edema_prob > scar_prob), torch.full_like(pred, 4), pred)
    pred = torch.where(conflict & (scar_prob >= edema_prob), torch.full_like(pred, 5), pred)
    return pred


def predict_case(
    model: SRRProposeRefineMyoPS,
    case: AnchoredCaseData,
    device: torch.device,
    *,
    disable_nnunet_anchor: bool = False,
    scar_decode_threshold: float,
    edema_decode_threshold: float,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(case.image[None]).float().to(device)
        av = torch.from_numpy(case.availability[None]).float().to(device)
        anchor_features, component_features = full_case_anchor_tensors(case, device)
        if disable_nnunet_anchor:
            anchor_features, component_features = None, None
        outputs = model(x, av, anchor_features=anchor_features, component_features=component_features)
        preds = {
            "argmax": _decode_argmax(outputs)[0].detach().cpu().numpy().astype(np.uint8),
            "pathology_aware": _decode_pathology_aware(
                outputs,
                scar_threshold=scar_decode_threshold,
                edema_threshold=edema_decode_threshold,
            )[0]
            .detach()
            .cpu()
            .numpy()
            .astype(np.uint8),
        }
        aux = {}
        for key in (
            "scar_proposal_logits",
            "edema_proposal_logits",
            "scar_pos_similarity",
            "scar_neg_similarity",
            "edema_pos_similarity",
            "edema_neg_similarity",
            "scar_memory_negative_similarity",
            "edema_memory_negative_similarity",
            "scar_refinement_residual",
            "edema_refinement_residual",
            "scar_soft_roi",
            "edema_soft_roi",
            "scar_crop_region_mask",
            "edema_crop_region_mask",
        ):
            aux[key] = outputs[key][0, 0].detach().cpu().numpy()
        for key in ("scar_crop_bounds_zyx", "edema_crop_bounds_zyx", "scar_roi_stats", "edema_roi_stats"):
            aux[key] = outputs[key][0].detach().cpu().numpy()
    return preds, aux


def write_prediction(path: Path, pred: np.ndarray, reference: sitk.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(pred)
    img.CopyInformation(reference)
    sitk.WriteImage(img, str(path))


def proposal_rows(
    variant: str,
    case: CaseData,
    aux: dict[str, np.ndarray],
    *,
    checkpoint_name: str,
    thresholds: list[float],
) -> list[dict[str, object]]:
    gt = case.label_arr.astype(np.uint8, copy=False)
    rows = []
    for cls, metric_name, prefix in [(5, "myops_scar", "scar"), (4, "myops_edema", "edema")]:
        logits = aux[f"{prefix}_proposal_logits"]
        prob = 1.0 / (1.0 + np.exp(-logits))
        for threshold in thresholds:
            proposal = prob >= threshold
            gt_mask = gt == cls
            inter = int(np.logical_and(proposal, gt_mask).sum())
            proposal_voxels = int(proposal.sum())
            gt_voxels = int(gt_mask.sum())
            small_fp, remote_fp = _fp_counts(proposal, gt_mask)
            outside_union = int(np.logical_and(proposal, gt == 0).sum())
            rows.append(
                {
                    "variant": variant,
                    "checkpoint_name": checkpoint_name,
                    "case_id": case.case_id,
                    "center": case.metadata.center,
                    "modality_group": case.metadata.modality_group,
                    "t2_present": case.metadata.t2_present,
                    "class_id": cls,
                    "metric_name": metric_name,
                    "proposal_threshold": threshold,
                    "proposal_recall": None if gt_voxels == 0 else inter / max(1, gt_voxels),
                    "proposal_precision": None if proposal_voxels == 0 else inter / max(1, proposal_voxels),
                    "lesion_wise_recall": _lesion_recall(proposal, gt_mask),
                    "proposal_voxels": proposal_voxels,
                    "gt_voxels": gt_voxels,
                    "proposal_component_count": _component_count(proposal),
                    "proposal_small_fp_count": small_fp,
                    "proposal_remote_fp_count": remote_fp,
                    "outside_myocardium_fp_ratio": None if proposal_voxels == 0 else outside_union / max(1, proposal_voxels),
                    "proposal_gate_mean": float(prob.mean()),
                    "proposal_gate_p95": float(np.percentile(prob, 95)),
                    "pos_similarity_mean": float(aux[f"{prefix}_pos_similarity"].mean()),
                    "neg_similarity_mean": float(aux[f"{prefix}_neg_similarity"].mean()),
                    "memory_negative_similarity_mean": float(aux[f"{prefix}_memory_negative_similarity"].mean()),
                }
            )
    return rows


def roi_rows(variant: str, case: CaseData, pred: np.ndarray, aux: dict[str, np.ndarray], *, checkpoint_name: str, decode_mode: str) -> list[dict[str, object]]:
    gt = case.label_arr.astype(np.uint8, copy=False)
    rows = []
    for cls, metric_name, prefix in [(5, "myops_scar", "scar"), (4, "myops_edema", "edema")]:
        roi = aux[f"{prefix}_soft_roi"] >= 0.10
        gt_mask = gt == cls
        pred_mask = pred == cls
        roi_voxels = int(roi.sum())
        rows.append(
            {
                "variant": variant,
                "checkpoint_name": checkpoint_name,
                "decode_mode": decode_mode,
                "case_id": case.case_id,
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": case.metadata.t2_present,
                "class_id": cls,
                "metric_name": metric_name,
                "roi_threshold": 0.10,
                "roi_voxels": roi_voxels,
                "gt_coverage": None if not bool(gt_mask.any()) else int(np.logical_and(roi, gt_mask).sum()) / max(1, int(gt_mask.sum())),
                "pred_coverage": None if not bool(pred_mask.any()) else int(np.logical_and(roi, pred_mask).sum()) / max(1, int(pred_mask.sum())),
                "outside_myocardium_roi_ratio": None if roi_voxels == 0 else int(np.logical_and(roi, gt == 0).sum()) / max(1, roi_voxels),
                "roi_mean": float(aux[f"{prefix}_soft_roi"].mean()),
                "residual_abs_mean": float(np.abs(aux[f"{prefix}_refinement_residual"]).mean()),
            }
        )
    return rows


def crop_bounds_rows(variant: str, case: CaseData, aux: dict[str, np.ndarray], *, checkpoint_name: str) -> list[dict[str, object]]:
    spatial_shape = tuple(int(v) for v in case.label_arr.shape)
    total_voxels = int(np.prod(spatial_shape))
    rows: list[dict[str, object]] = []
    for cls, metric_name, prefix in [(5, "myops_scar", "scar"), (4, "myops_edema", "edema")]:
        z0, z1, y0, y1, x0, x1 = [int(v) for v in aux[f"{prefix}_crop_bounds_zyx"].tolist()]
        crop_voxels = max(0, z1 - z0) * max(0, y1 - y0) * max(0, x1 - x0)
        stats = aux[f"{prefix}_roi_stats"]
        crop_mask_voxels = int(np.count_nonzero(aux[f"{prefix}_crop_region_mask"]))
        rows.append(
            {
                "variant": variant,
                "checkpoint_name": checkpoint_name,
                "case_id": case.case_id,
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": case.metadata.t2_present,
                "class_id": cls,
                "metric_name": metric_name,
                "z0": z0,
                "z1": z1,
                "y0": y0,
                "y1": y1,
                "x0": x0,
                "x1": x1,
                "crop_voxels": crop_voxels,
                "crop_mask_voxels": crop_mask_voxels,
                "crop_volume_ratio": None if total_voxels == 0 else crop_voxels / max(1, total_voxels),
                "crop_mask_volume_ratio": None if total_voxels == 0 else crop_mask_voxels / max(1, total_voxels),
                "is_full_volume_crop": bool(crop_voxels >= total_voxels),
                "roi_mean": float(stats[0]),
                "roi_max": float(stats[1]),
                "roi_threshold_fraction": float(stats[2]),
                "stats_crop_volume_ratio": float(stats[3]),
                "post_refine_positive_fraction": float(stats[4]),
                "crop_residual_abs_mean": float(stats[5]),
                "stats_full_volume_flag": float(stats[6]),
                "crop_source_code": float(stats[7]),
            }
        )
    return rows


def prediction_sanity_rows(
    variant: str,
    case: CaseData,
    preds: dict[str, np.ndarray],
    *,
    checkpoint_name: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for decode_mode, pred in preds.items():
        values, counts = np.unique(pred, return_counts=True)
        volumes = {int(v): int(c) for v, c in zip(values.tolist(), counts.tolist(), strict=False)}
        total = max(1, int(pred.size))
        rows.append(
            {
                "variant": variant,
                "checkpoint_name": checkpoint_name,
                "decode_mode": decode_mode,
                "case_id": case.case_id,
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": case.metadata.t2_present,
                "compact_label_values": ",".join(str(v) for v in sorted(volumes)),
                "foreground_rate": float(np.count_nonzero(pred > 0) / total),
                "pathology_rate": float(np.count_nonzero(np.isin(pred, [4, 5])) / total),
                "edema_voxels": volumes.get(4, 0),
                "scar_voxels": volumes.get(5, 0),
                "no_t2_edema_voxels": volumes.get(4, 0) if not case.metadata.t2_present else 0,
                "empty_prediction": not bool(np.isin(pred, [4, 5]).any()),
                "class_0_voxels": volumes.get(0, 0),
                "class_1_voxels": volumes.get(1, 0),
                "class_2_voxels": volumes.get(2, 0),
                "class_3_voxels": volumes.get(3, 0),
                "class_4_voxels": volumes.get(4, 0),
                "class_5_voxels": volumes.get(5, 0),
            }
        )
    return rows


def summarize_context_subgroups(case_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    variants = sorted({str(row["variant"]) for row in case_rows})
    for context_variant in variants:
        subset = [row for row in case_rows if row["variant"] == context_variant]
        rows.extend(summarize_subgroups(context_variant, subset))
    return rows


def evaluate(
    model: SRRProposeRefineMyoPS,
    cases: list[CaseData],
    variant_dir: Path,
    variant: str,
    device: torch.device,
    *,
    disable_nnunet_anchor: bool = False,
    checkpoint_name: str,
    proposal_thresholds: list[float],
    scar_decode_threshold: float,
    edema_decode_threshold: float,
) -> None:
    case_rows: list[dict[str, object]] = []
    proposal: list[dict[str, object]] = []
    roi: list[dict[str, object]] = []
    bounds: list[dict[str, object]] = []
    sanity: list[dict[str, object]] = []
    for case in cases:
        preds, aux = predict_case(
            model,
            case,
            device,
            disable_nnunet_anchor=disable_nnunet_anchor,
            scar_decode_threshold=scar_decode_threshold,
            edema_decode_threshold=edema_decode_threshold,
        )
        proposal.extend(proposal_rows(variant, case, aux, checkpoint_name=checkpoint_name, thresholds=proposal_thresholds))
        bounds.extend(crop_bounds_rows(variant, case, aux, checkpoint_name=checkpoint_name))
        sanity.extend(prediction_sanity_rows(variant, case, preds, checkpoint_name=checkpoint_name))
        for decode_mode, pred in preds.items():
            pred_dir = variant_dir / "predictions/fold_0" / checkpoint_name / decode_mode
            write_prediction(pred_dir / f"{case.case_id}.nii.gz", pred, case.label_img)
            context_variant = f"{variant}__{checkpoint_name}__{decode_mode}"
            case_rows.extend(collect_case_metrics(context_variant, case, pred))
            roi.extend(roi_rows(variant, case, pred, aux, checkpoint_name=checkpoint_name, decode_mode=decode_mode))
    write_csv(variant_dir / f"component_hd_by_case_{checkpoint_name}.csv", case_rows)
    write_csv(variant_dir / f"subgroup_metrics_{checkpoint_name}.csv", summarize_context_subgroups(case_rows))
    write_csv(variant_dir / f"proposal_pr_sweep_{checkpoint_name}.csv", proposal)
    write_csv(variant_dir / f"roi_coverage_{checkpoint_name}.csv", roi)
    write_csv(variant_dir / f"crop_bounds_{checkpoint_name}.csv", bounds)
    write_csv(variant_dir / f"prediction_sanity_{checkpoint_name}.csv", sanity)


def validate_patch_loss(
    model: SRRProposeRefineMyoPS,
    cases: list[AnchoredCaseData],
    patch_shape: tuple[int, int, int],
    device: torch.device,
    seed: int,
    args: argparse.Namespace,
) -> float:
    rng = np.random.default_rng(seed)
    losses = []
    model.eval()
    with torch.no_grad():
        for case in cases[: min(10, len(cases))]:
            x_np, y_np, av_np, anchor_np, component_np = sample_patch_with_anchor(
                case,
                patch_shape,
                rng,
                oversample_foreground=1.0,
                modality_dropout=False,
            )
            x = torch.from_numpy(x_np[None]).float().to(device)
            y = torch.from_numpy(y_np[None]).long().to(device)
            av = torch.from_numpy(av_np[None]).float().to(device)
            anchor_t = torch.from_numpy(anchor_np[None]).float().to(device)
            component_t = torch.from_numpy(component_np[None]).float().to(device)
            anchor_features, component_features = maybe_disable_context(
                args,
                anchor_dict_from_tensor(anchor_t),
                component_dict_from_tensor(component_t),
            )
            outputs = model(
                x,
                av,
                anchor_features=anchor_features,
                component_features=component_features,
            )
            loss, _ = propref_loss(outputs, y, av, "soft_roi_refinement", args)
            losses.append(float(loss.detach().cpu()))
    model.train()
    return float(mean(losses)) if losses else float("inf")


def variant_hparams(variant: str) -> dict[str, float | int]:
    if variant == "srr_propref_scar_precision":
        return {"scar_weight": 1.65, "edema_weight": 1.10, "hardneg_sample_prob": 0.45, "proposal_weight": 0.55}
    if variant == "srr_propref_no_proto_cascade":
        return {"scar_weight": 1.20, "edema_weight": 1.20, "hardneg_sample_prob": 0.10, "proposal_weight": 0.25}
    return {"scar_weight": 1.35, "edema_weight": 1.35, "hardneg_sample_prob": 0.30, "proposal_weight": 0.45}


def save_checkpoint(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    torch.save(payload, tmp)
    tmp.replace(path)


def memory_rows(variant: str, mined_csv: Path | None, loaded_case_count: int, loaded_component_count: int) -> list[dict[str, object]]:
    rows = []
    if mined_csv is None or not mined_csv.is_file():
        return [
            {
                "variant": variant,
                "memory_source": "evidence not found",
                "class_id": "evidence not found",
                "safety_type": "evidence not found",
                "replay_safe_components": 0,
                "note": "hard-negative mined components file not available",
            }
        ]
    counts: dict[tuple[str, str], int] = {}
    with mined_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if str(row.get("replay_safe", "")).lower() != "true":
                continue
            key = (str(row.get("class_id", "")), str(row.get("safety_type", "")))
            counts[key] = counts.get(key, 0) + 1
    for (class_id, safety), count in sorted(counts.items()):
        rows.append(
            {
                "variant": variant,
                "memory_source": str(mined_csv),
                "class_id": class_id,
                "safety_type": safety,
                "replay_safe_components": count,
                "loaded_case_count": loaded_case_count,
                "loaded_component_count": loaded_component_count,
                "note": "no-T2 myocardium/scar unsafe edema entries remain excluded by replay_safe filter",
            }
        )
    return rows



def _prototype_bank_summary(bank: PrototypeBank, *, selected_case_ids: list[str], feature_stage: str) -> dict[str, object]:
    return {
        "source": bank.source,
        "feature_stage": feature_stage,
        "selected_case_ids": selected_case_ids,
        "case_count": len(selected_case_ids),
        "counts": bank.counts,
        "category_counts": bank.category_counts,
        "hard_negative_counts": bank.hard_negative_counts,
        "scar_positive_shape": list(bank.scar_positive.shape),
        "scar_negative_shape": list(bank.scar_negative.shape),
        "edema_positive_shape": list(bank.edema_positive.shape),
        "edema_negative_shape": list(bank.edema_negative.shape),
        "leakage_policy": "train split and OOF nnU-Net anchor probabilities only; validation labels are not used",
        "safe_negative_policy": "edema positives and negatives restricted to T2-present samples; no-T2 myocardium never contributes edema negatives",
    }


def fit_and_load_runtime_prototype_bank(
    model: SRRProposeRefineMyoPS,
    cases: list[AnchoredCaseData],
    patch_shape: tuple[int, int, int],
    device: torch.device,
    args: argparse.Namespace,
    variant_dir: Path,
) -> dict[str, object]:
    """Fit real train/OOF prototype banks and load them into the formal model."""

    if args.variant == "srr_propref_no_proto_cascade" or args.skip_prototype_bank_fit:
        summary = {
            "status": "SKIPPED",
            "reason": "no-prototype variant or skip_prototype_bank_fit",
            "source": "not_loaded",
            "case_count": 0,
            "counts": {},
            "leakage_policy": "not_applicable",
        }
        (variant_dir / "prototype_bank_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return summary

    rng = np.random.default_rng(args.seed + 1907)
    lesion_cases = [case for case in cases if np.any(np.isin(case.label_arr, [4, 5]))]
    t2_edema_cases = [case for case in cases if case.metadata.t2_present and np.any(case.label_arr == 4)]
    selected: list[AnchoredCaseData] = []
    for pool in (t2_edema_cases, lesion_cases, cases):
        for case in pool:
            if case.case_id not in {item.case_id for item in selected}:
                selected.append(case)
            if len(selected) >= max(1, int(args.prototype_bank_cases)):
                break
        if len(selected) >= max(1, int(args.prototype_bank_cases)):
            break
    if not selected:
        raise ValueError("cannot fit prototype bank without train cases")

    xs, ys, avs, anchors, keys = [], [], [], [], []
    for case in selected:
        if case.metadata.t2_present and np.any(case.label_arr == 4):
            focus_classes = (4,)
        elif np.any(case.label_arr == 5):
            focus_classes = (5,)
        else:
            focus_classes = (4, 5)
        x_np, y_np, av_np, anchor_np, _component_np = sample_patch_with_anchor(
            case,
            patch_shape,
            rng,
            oversample_foreground=1.0,
            modality_dropout=False,
            focus_classes=focus_classes,
        )
        xs.append(x_np)
        ys.append(y_np)
        avs.append(av_np)
        anchors.append(anchor_np)
        keys.append(case.case_id)
    x = torch.from_numpy(np.stack(xs, axis=0)).float().to(device)
    y = torch.from_numpy(np.stack(ys, axis=0)).long().to(device)
    av = torch.from_numpy(np.stack(avs, axis=0)).float().to(device)
    anchor_t = torch.from_numpy(np.stack(anchors, axis=0)).float().to(device)
    model_was_training = model.training
    model.eval()
    with torch.no_grad():
        anchor_for_fit = None if bool(getattr(args, "disable_nnunet_anchor", False)) else anchor_dict_from_tensor(anchor_t)
        features, _gates, _metadata, _valid = model._evidence_features(x, av, anchor_for_fit)
        bank = build_prototype_bank_from_labeled_features(
            scar_features=features["scar"].detach(),
            edema_features=features["edema"].detach(),
            labels=y,
            availability=av,
            anchor_probabilities=None if bool(getattr(args, "disable_nnunet_anchor", False)) else anchor_t,
            source="train_runtime_features_fold0_no_nnunet_anchor"
            if bool(getattr(args, "disable_nnunet_anchor", False))
            else "train_oof_runtime_features_fold0",
        )
    if model_was_training:
        model.train()
    model.scar_dictionary.load_prototype_bank(positive=bank.scar_positive, negative=bank.scar_negative, source=bank.source)
    model.edema_dictionary.load_prototype_bank(positive=bank.edema_positive, negative=bank.edema_negative, source=bank.source)
    summary = _prototype_bank_summary(bank, selected_case_ids=keys, feature_stage="SRRProposeRefineMyoPS._evidence_features")
    (variant_dir / "prototype_bank_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def prototype_parameters(model: SRRProposeRefineMyoPS) -> list[tuple[str, torch.nn.Parameter]]:
    return [
        (name, param)
        for name, param in model.named_parameters()
        if (
            "dictionary.positive" in name
            or "dictionary.negative" in name
            or "dictionary.negative_memory" in name
            or "dictionary.embedding" in name
            or "dictionary.conv_score" in name
        )
    ]


def prototype_sanity_row(
    variant: str,
    step: int,
    before: dict[str, torch.Tensor],
    model: SRRProposeRefineMyoPS,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for name, param in prototype_parameters(model):
        grad = param.grad
        after = param.detach()
        delta = after - before[name] if name in before else torch.zeros_like(after)
        rows.append(
            {
                "variant": variant,
                "step": step,
                "parameter": name,
                "grad_norm": None if grad is None else float(grad.detach().norm().cpu()),
                "update_norm": float(delta.norm().cpu()),
                "parameter_norm": float(after.norm().cpu()),
                "status": "tracked",
            }
        )
    if not rows:
        rows.append(
            {
                "variant": variant,
                "step": step,
                "parameter": "no prototype parameters",
                "grad_norm": None,
                "update_norm": None,
                "parameter_norm": None,
                "status": "not_applicable_no_proto_variant",
            }
        )
    return rows


def run_one_batch_overfit(
    args: argparse.Namespace,
    train_cases: list[AnchoredCaseData],
    patch_shape: tuple[int, int, int],
    device: torch.device,
    variant_dir: Path,
) -> tuple[bool, dict[str, object]]:
    output_variant = output_variant_name(args)
    if args.skip_overfit_sanity:
        summary = {
            "variant": output_variant,
            "model_variant": args.variant,
            "status": "SKIPPED",
            "reason": "skip_overfit_sanity was set",
            "required_by_task": True,
        }
        (variant_dir / "one_batch_overfit.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return False, summary
    rng = np.random.default_rng(args.seed + 991)
    case_pool = [case for case in train_cases if np.any(np.isin(case.label_arr, [4, 5]))] or train_cases
    case = case_pool[int(rng.integers(0, len(case_pool)))]
    x_np, y_np, av_np, anchor_np, component_np = sample_patch_with_anchor(case, patch_shape, rng, oversample_foreground=1.0, modality_dropout=False)
    x = torch.from_numpy(x_np[None]).float().to(device)
    y = torch.from_numpy(y_np[None]).long().to(device)
    av = torch.from_numpy(av_np[None]).float().to(device)
    anchor_t = torch.from_numpy(anchor_np[None]).float().to(device)
    component_t = torch.from_numpy(component_np[None]).float().to(device)
    anchor_features = anchor_dict_from_tensor(anchor_t)
    component_features = component_dict_from_tensor(component_t)
    anchor_features, component_features = maybe_disable_context(args, anchor_features, component_features)
    model = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
    fit_and_load_runtime_prototype_bank(model, [case], patch_shape, device, args, variant_dir)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    rows: list[dict[str, object]] = []
    proto_rows: list[dict[str, object]] = []
    first_loss: float | None = None
    last_loss: float | None = None
    start = time.monotonic()
    process_start = time.process_time()
    model.train()
    for step in range(1, args.overfit_steps + 1):
        stage = "soft_roi_refinement"
        before = {name: param.detach().clone() for name, param in prototype_parameters(model)} if step == 1 else {}
        optimizer.zero_grad(set_to_none=True)
        outputs = model(x, av, anchor_features=anchor_features, component_features=component_features)
        loss, metrics = propref_loss(outputs, y, av, stage, args)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        optimizer.step()
        loss_value = float(loss.detach().cpu())
        if first_loss is None:
            first_loss = loss_value
        last_loss = loss_value
        if step == 1:
            proto_rows.extend(prototype_sanity_row(output_variant, step, before, model))
        if step == 1 or step == args.overfit_steps or step % max(1, args.overfit_log_every) == 0:
            rows.append(
                {
                    "variant": output_variant,
                    "model_variant": args.variant,
                    "case_id": case.case_id,
                    "step": step,
                    "loss": loss_value,
                    "evidence_loss": float(metrics["evidence_loss"].cpu()),
                    "final_loss": float(metrics["final_loss"].cpu()),
                    "scar_proposal_loss": float(metrics["scar_proposal_loss"].cpu()),
                    "edema_proposal_loss": float(metrics["edema_proposal_loss"].cpu()),
                    "proposal_margin_loss": float(metrics["proposal_margin_loss"].cpu()),
                    "elapsed_seconds": time.monotonic() - start,
                }
            )
    loss_decrease = None if first_loss is None or last_loss is None else first_loss - last_loss
    passed = bool(loss_decrease is not None and loss_decrease >= args.min_overfit_loss_decrease)
    write_csv(variant_dir / "one_batch_overfit.csv", rows)
    write_csv(variant_dir / "prototype_update_sanity.csv", proto_rows)
    summary = {
        "variant": output_variant,
        "model_variant": args.variant,
        "encoder_profile": getattr(model, "encoder_profile", args.encoder_profile),
        "encoder_scale_channels": list(getattr(model, "encoder_scale_channels", encoder_scale_channels_from_args(args))),
        "parameter_count": parameter_count(model),
        "status": "PASS" if passed else "FAIL",
        "case_id": case.case_id,
        "anchor_source": case.anchor_source,
        "anchor_fold": case.anchor_fold,
        "anchor_present": bool(np.any(anchor_np)) and not bool(getattr(args, "disable_nnunet_anchor", False)),
        "component_present": bool(np.any(component_np)) and not bool(getattr(args, "disable_nnunet_anchor", False)),
        "disable_local_refinement": bool(getattr(args, "disable_local_refinement", False)),
        "disable_anatomy_roi_prior": bool(getattr(args, "disable_anatomy_roi_prior", False)),
        "disable_nnunet_anchor": bool(getattr(args, "disable_nnunet_anchor", False)),
        "steps": args.overfit_steps,
        "first_loss": first_loss,
        "last_loss": last_loss,
        "loss_decrease": loss_decrease,
        "min_required_loss_decrease": args.min_overfit_loss_decrease,
        "elapsed_seconds": time.monotonic() - start,
        "process_seconds": time.process_time() - process_start,
        "prototype_rows": str(variant_dir / "prototype_update_sanity.csv"),
    }
    (variant_dir / "one_batch_overfit.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return passed, summary


def train_variant(args: argparse.Namespace) -> None:
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    output_variant = output_variant_name(args)
    hp = variant_hparams(args.variant)
    for key, value in hp.items():
        if getattr(args, key) is None:
            setattr(args, key, value)
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    train_ids, full_val_ids = load_split(args.fold)
    full_train_ids = list(train_ids)
    val_ids = list(full_val_ids)
    explicit_train_ids = parse_case_id_list(args.train_case_ids)
    if explicit_train_ids:
        invalid_train_ids = [case_id for case_id in explicit_train_ids if case_id not in full_train_ids]
        if invalid_train_ids:
            raise ValueError(
                "--train-case-ids must be a subset of the requested fold training split; "
                f"invalid ids for fold {args.fold}: {','.join(invalid_train_ids)}"
            )
        train_ids = explicit_train_ids
    if args.limit_train_cases > 0:
        train_ids = train_ids[: args.limit_train_cases]
    if args.limit_val_cases > 0:
        val_ids = val_ids[: args.limit_val_cases]
    eval_case_ids = parse_case_id_list(args.eval_case_ids)
    if eval_case_ids:
        invalid_eval_ids = [case_id for case_id in eval_case_ids if case_id not in full_val_ids]
        if invalid_eval_ids:
            raise ValueError(
                "--eval-case-ids must be a subset of the requested fold validation split; "
                f"invalid ids for fold {args.fold}: {','.join(invalid_eval_ids)}"
            )
    metadata = load_myops_case_metadata()
    anchor_root = _anchor_root(args.nnunet_anchor_root)
    train_cases = [read_anchored_case(cid, metadata, anchor_root) for cid in train_ids]
    train_cases, prototype_t2_repair_added_case_ids = ensure_t2_edema_prototype_cases(
        train_cases,
        full_train_ids,
        metadata,
        anchor_root,
        args,
    )
    train_ids = [case.case_id for case in train_cases]
    val_cases = [read_anchored_case(cid, metadata, anchor_root) for cid in val_ids]
    eval_cases_override = [read_anchored_case(cid, metadata, anchor_root) for cid in eval_case_ids] if eval_case_ids else []
    anchor_fold_counts: dict[str, int] = {}
    for case in train_cases + val_cases:
        key = f"fold_{case.anchor_fold}"
        anchor_fold_counts[key] = anchor_fold_counts.get(key, 0) + 1
    anchor_manifest = {
        "anchor_root": str(anchor_root),
        "source_kind": "nnUNet fold validation probabilities; train cases use their OOF fold, fold0 validation cases use fold0 validation anchors",
        "train_anchor_case_count": len(train_cases),
        "val_anchor_case_count": len(val_cases),
        "eval_case_ids": eval_case_ids,
        "train_case_ids": train_ids,
        "train_case_selection": "explicit_train_case_ids" if explicit_train_ids else "fold_training_prefix_or_all",
        "anchor_fold_counts": anchor_fold_counts,
        "component_source": "connected components derived from nnU-Net hard predictions for compact scar class 5 and edema class 4",
        "no_t2_policy": "class-4 edema anchor/component evidence is zeroed when T2 is unavailable or virtual modality dropout removes T2",
        "prototype_t2_repair_added_case_ids": prototype_t2_repair_added_case_ids,
        "prototype_t2_repair_policy": "if a limited train subset lacks T2-present edema-positive cases, append same-split T2 edema-positive cases for prototype fitting evidence",
    }
    complete_cases = [case for case in train_cases if case.metadata.modality_group == "C0+LGE+T2"]
    scar_cases = [case for case in train_cases if np.any(case.label_arr == 5)]
    lge_only_scar_cases = [case for case in scar_cases if case.metadata.modality_group == "LGE-only"]
    edema_t2_cases = [case for case in train_cases if case.metadata.t2_present and np.any(case.label_arr == 4)]
    center_c_t2_edema_cases = [case for case in edema_t2_cases if case.metadata.center == "CenterC"]
    out_root = Path(args.out_root)
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    variant_dir = out_root / "variants" / output_variant
    checkpoint_dir = variant_dir / "checkpoints/fold_0/propref_config"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    patch_shape = parse_shape(args.patch_shape)
    proposal_thresholds = parse_float_list(args.proposal_thresholds)
    hardneg_path = Path(args.hardneg_components_csv) if args.hardneg_components_csv else None
    if hardneg_path is not None and not hardneg_path.is_absolute():
        hardneg_path = REPO_ROOT / hardneg_path
    hardneg_targets = load_hard_negative_targets(hardneg_path, args.variant)

    overfit_passed, overfit_summary = run_one_batch_overfit(args, train_cases, patch_shape, device, variant_dir)
    if not overfit_passed:
        summary = {
            "variant": output_variant,
            "model_variant": args.variant,
            "fold": args.fold,
            "device": str(device),
            "encoder_profile": args.encoder_profile,
            "encoder_scale_channels": encoder_scale_channels_from_args(args),
            "parameter_count": "evidence not found; overfit sanity stopped before model persisted",
            "train_cases": len(train_cases),
            "val_cases": len(val_cases),
            "stop_reason": "overfit_sanity_failed_or_skipped",
            "actual_optimizer_steps": 0,
            "optimizer_steps": 0,
            "train_loop_seconds": 0.0,
            "process_wall_seconds": 0.0,
            "validation_events": [],
            "stage_step_counts": stage_counts(0, args.max_steps),
            "first_train_loss": None,
            "last_train_loss": None,
            "loss_decrease": None,
            "one_batch_overfit": overfit_summary,
            "checkpoint_best": "evidence not found",
            "checkpoint_final": "evidence not found",
            "prediction_dirs": [],
            "skip_export": bool(args.skip_export),
            "disable_local_refinement": bool(getattr(args, "disable_local_refinement", False)),
            "disable_anatomy_roi_prior": bool(getattr(args, "disable_anatomy_roi_prior", False)),
            "disable_nnunet_anchor": bool(getattr(args, "disable_nnunet_anchor", False)),
        }
        (variant_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return

    model = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
    model_param_count = parameter_count(model)
    prototype_bank_summary = fit_and_load_runtime_prototype_bank(model, train_cases, patch_shape, device, args, variant_dir)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    rng = np.random.default_rng(args.seed)
    best_val = float("inf")
    best_step = 0
    no_improve_validation_events = 0
    stop_reason = "max_steps"
    train_rows: list[dict[str, object]] = []
    usage_rows: list[dict[str, object]] = []
    proto_rows: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    validation_events: list[dict[str, object]] = []
    first_train_loss: float | None = None
    last_train_loss: float | None = None
    optimizer_steps = 0
    validation_schedule = required_validation_steps(args.max_steps, args.val_every)
    start = time.monotonic()
    process_start = time.process_time()
    model.train()
    for step in range(1, args.max_steps + 1):
        if time.monotonic() - start > args.max_runtime_seconds:
            stop_reason = "max_runtime_seconds"
            break
        stage = stage_for_step(step, args.max_steps)
        if stage == "low_lr_calibration":
            for group in optimizer.param_groups:
                group["lr"] = args.lr * 0.20
        x_cpu, y_cpu, av_cpu, anchor_cpu, component_cpu, keys = batch_from_anchored_cases(
            train_cases,
            complete_cases,
            scar_cases,
            lge_only_scar_cases,
            edema_t2_cases,
            center_c_t2_edema_cases,
            args.batch_size,
            patch_shape,
            rng,
            args.complete_oversample,
            args.oversample_foreground,
            modality_dropout=True,
            hardneg_targets=hardneg_targets,
            hardneg_sample_prob=float(args.hardneg_sample_prob),
        )
        x = x_cpu.to(device)
        y = y_cpu.to(device)
        av = av_cpu.to(device)
        anchor_features = {key: value.to(device) for key, value in anchor_cpu.items()}
        component_features = {key: value.to(device) for key, value in component_cpu.items()}
        anchor_features, component_features = maybe_disable_context(args, anchor_features, component_features)
        before = {name: param.detach().clone() for name, param in prototype_parameters(model)} if step in {1, max(1, args.max_steps // 2)} else {}
        optimizer.zero_grad(set_to_none=True)
        outputs = model(x, av, anchor_features=anchor_features, component_features=component_features)
        loss, metrics = propref_loss(outputs, y, av, stage, args)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        optimizer.step()
        optimizer_steps += 1
        loss_value = float(loss.detach().cpu())
        if first_train_loss is None:
            first_train_loss = loss_value
        last_train_loss = loss_value
        if before:
            proto_rows.extend(prototype_sanity_row(output_variant, step, before, model))
        if step == 1 or step % args.log_every == 0:
            train_rows.append(
                {
                    "variant": output_variant,
                    "model_variant": args.variant,
                    "step": step,
                    "stage": stage,
                    "loss": loss_value,
                    "evidence_loss": float(metrics["evidence_loss"].cpu()),
                    "final_loss": float(metrics["final_loss"].cpu()),
                    "scar_proposal_loss": float(metrics["scar_proposal_loss"].cpu()),
                    "edema_proposal_loss": float(metrics["edema_proposal_loss"].cpu()),
                    "proposal_margin_loss": float(metrics["proposal_margin_loss"].cpu()),
                    "scar_component_ranking_loss": float(metrics["scar_component_ranking_loss"].cpu()),
                    "edema_component_ranking_loss": float(metrics["edema_component_ranking_loss"].cpu()),
                    "component_proposal_ranking_loss": float(metrics["component_proposal_ranking_loss"].cpu()),
                    "roi_cover_loss": float(metrics["roi_cover_loss"].cpu()),
                    "roi_remote_loss": float(metrics["roi_remote_loss"].cpu()),
                    "semantic_retrieval_loss": float(metrics["semantic_retrieval_loss"].cpu()),
                    "baseline_preservation_loss": float(metrics["baseline_preservation_loss"].cpu()),
                    "baseline_preserve_voxels": float(metrics["baseline_preserve_voxels"].cpu()),
                    "baseline_preserve_gate_mean": float(metrics["baseline_preserve_gate_mean"].cpu()),
                    "proposal_weight": float(metrics["proposal_weight"].cpu()),
                    "refine_weight": float(metrics["refine_weight"].cpu()),
                    "edema_supervised_batch_fraction": float(av[:, 1].mean().detach().cpu()),
                    "anchor_present_batch_fraction": context_present_fraction(anchor_features, ("probabilities",)),
                    "component_present_batch_fraction": context_present_fraction(component_features, ("scar_component", "edema_component")),
                    "baseline_gate_mean": float(outputs["baseline_residual_gate"].detach().mean().cpu()) if "baseline_residual_gate" in outputs else 0.0,
                    "baseline_residual_abs_mean": float(outputs["baseline_residual_magnitude"].detach().mean().cpu()) if "baseline_residual_magnitude" in outputs else 0.0,
                    "baseline_gate_status": str(outputs.get("baseline_gate_status", "evidence_not_found")),
                    "local_refinement_status": str(outputs.get("local_refinement_status", "evidence_not_found")),
                    "anatomy_roi_prior_status": str(outputs.get("anatomy_roi_prior_status", "evidence_not_found")),
                    "encoder_profile": str(outputs.get("encoder_profile", args.encoder_profile)),
                    "encoder_scale_channels": ";".join(str(v) for v in outputs.get("encoder_scale_channels", [])),
                    "p_union_mean": float(outputs["p_union"].detach().mean().cpu()) if "p_union" in outputs else 0.0,
                    "p_lv_mean": float(outputs["p_lv"].detach().mean().cpu()) if "p_lv" in outputs else 0.0,
                    "p_rv_mean": float(outputs["p_rv"].detach().mean().cpu()) if "p_rv" in outputs else 0.0,
                    "union_distance_mean": float(outputs["union_distance"].detach().mean().cpu()) if "union_distance" in outputs else 0.0,
                    "lv_distance_mean": float(outputs["lv_distance"].detach().mean().cpu()) if "lv_distance" in outputs else 0.0,
                    "rv_distance_mean": float(outputs["rv_distance"].detach().mean().cpu()) if "rv_distance" in outputs else 0.0,
                    "scar_anatomy_soft_gate_mean": float(outputs["scar_anatomy_soft_gate"].detach().mean().cpu()) if "scar_anatomy_soft_gate" in outputs else 0.0,
                    "edema_anatomy_soft_gate_mean": float(outputs["edema_anatomy_soft_gate"].detach().mean().cpu()) if "edema_anatomy_soft_gate" in outputs else 0.0,
                    "empty_union_fallback_fraction": float(outputs["empty_union_fallback"].detach().mean().cpu()) if "empty_union_fallback" in outputs else 0.0,
                    "prototype_source_scar": str(outputs["prototype_source"]["scar"]),
                    "prototype_source_edema": str(outputs["prototype_source"]["edema"]),
                    "batch_cases": ",".join(keys),
                    "elapsed_seconds": time.monotonic() - start,
                }
            )
            record_gate_usage(usage_rows, output_variant, step, keys, outputs)
        if step in validation_schedule:
            val_loss = validate_patch_loss(model, val_cases, patch_shape, device, args.seed + step, args)
            validation_row = {
                "variant": output_variant,
                "model_variant": args.variant,
                "step": step,
                "stage": stage,
                "event": "validation",
                "val_patch_loss": val_loss,
                "elapsed_seconds": time.monotonic() - start,
                "eligible_for_best": step >= max(2, int(math.ceil(args.max_steps * args.min_best_step_fraction))),
            }
            validation_rows.append(validation_row)
            train_rows.append(validation_row)
            checkpoint_step_path = checkpoint_dir / f"checkpoint_validation_step_{step}.pt"
            save_checkpoint(
                {
                    "variant": output_variant,
                    "model_variant": args.variant,
                    "step": step,
                    "model_state_dict": model.state_dict(),
                    "args": vars(args),
                    "val_patch_loss": val_loss,
                    "checkpoint_role": "validation_milestone",
                },
                checkpoint_step_path,
            )
            validation_event = dict(validation_row)
            validation_event["checkpoint_path"] = str(checkpoint_step_path)
            validation_events.append(validation_event)
            improved = bool(validation_row["eligible_for_best"] and val_loss < best_val - args.early_stop_min_delta)
            validation_row["best_improved"] = improved
            validation_event["best_improved"] = improved
            if improved:
                best_val = val_loss
                best_step = step
                no_improve_validation_events = 0
                save_checkpoint(
                    {
                        "variant": output_variant,
                        "model_variant": args.variant,
                        "step": step,
                        "model_state_dict": model.state_dict(),
                        "args": vars(args),
                        "val_patch_loss": best_val,
                        "checkpoint_role": "eligible_best",
                    },
                    checkpoint_dir / "checkpoint_best.pt",
                )
            elif validation_row["eligible_for_best"]:
                no_improve_validation_events += 1
            if (
                args.early_stop_patience > 0
                and no_improve_validation_events >= args.early_stop_patience
                and optimizer_steps >= args.min_optimizer_steps_for_plateau
                and time.monotonic() - start >= args.min_train_loop_seconds_for_plateau
            ):
                stop_reason = "validation_plateau_patience"
                break

    elapsed = time.monotonic() - start
    process_elapsed = time.process_time() - process_start
    actual_steps = optimizer_steps
    save_checkpoint(
        {
            "variant": output_variant,
            "model_variant": args.variant,
            "step": actual_steps,
            "model_state_dict": model.state_dict(),
            "args": vars(args),
            "checkpoint_role": "final",
        },
        checkpoint_dir / "checkpoint_final.pt",
    )
    best_path = checkpoint_dir / "checkpoint_best.pt"
    if not best_path.is_file():
        best_path = checkpoint_dir / "checkpoint_final.pt"
        best_step = actual_steps
    if not args.skip_export:
        eval_source_cases = eval_cases_override if eval_cases_override else val_cases
        eval_cases = eval_source_cases[: args.max_eval_cases] if args.max_eval_cases > 0 else eval_source_cases
        for checkpoint_name, checkpoint_path in [("checkpoint_best", best_path), ("checkpoint_final", checkpoint_dir / "checkpoint_final.pt")]:
            state = torch.load(checkpoint_path, map_location=device, weights_only=False)
            model.load_state_dict(state["model_state_dict"])
            evaluate(
                model,
                eval_cases,
                variant_dir,
                output_variant,
                device,
                disable_nnunet_anchor=bool(getattr(args, "disable_nnunet_anchor", False)),
                checkpoint_name=checkpoint_name,
                proposal_thresholds=proposal_thresholds,
                scar_decode_threshold=args.scar_decode_threshold,
                edema_decode_threshold=args.edema_decode_threshold,
            )
    write_csv(variant_dir / "training_log.csv", train_rows)
    write_csv(variant_dir / "validation_events.csv", validation_rows)
    write_csv(variant_dir / "retrieval_usage.csv", usage_rows)
    write_csv(variant_dir / "prototype_update_sanity_formal.csv", proto_rows)
    write_csv(variant_dir / "hardneg_memory.csv", memory_rows(output_variant, hardneg_path, len(hardneg_targets), sum(len(v) for v in hardneg_targets.values())))
    loss_decrease = None if first_train_loss is None or last_train_loss is None else first_train_loss - last_train_loss
    summary = {
        "variant": output_variant,
        "model_variant": args.variant,
        "fold": args.fold,
        "device": str(device),
        "encoder_profile": getattr(model, "encoder_profile", args.encoder_profile),
        "encoder_scale_channels": list(getattr(model, "encoder_scale_channels", encoder_scale_channels_from_args(args))),
        "parameter_count": model_param_count,
        "train_cases": len(train_cases),
        "train_case_ids": train_ids,
        "train_case_selection": "explicit_train_case_ids" if explicit_train_ids else "fold_training_prefix_or_all",
        "val_cases": len(val_cases),
        "eval_cases": len(eval_cases) if not args.skip_export else 0,
        "eval_case_ids": [case.case_id for case in eval_cases] if not args.skip_export else [],
        "eval_case_selection": "explicit_eval_case_ids" if eval_case_ids else "fold_validation_prefix_or_all",
        "best_step": best_step,
        "best_val_patch_loss": best_val,
        "stop_reason": stop_reason,
        "elapsed_seconds": elapsed,
        "train_loop_seconds": elapsed,
        "process_wall_seconds": process_elapsed,
        "max_runtime_seconds": args.max_runtime_seconds,
        "max_steps": args.max_steps,
        "early_stop_patience": args.early_stop_patience,
        "early_stop_min_delta": args.early_stop_min_delta,
        "min_optimizer_steps_for_plateau": args.min_optimizer_steps_for_plateau,
        "min_train_loop_seconds_for_plateau": args.min_train_loop_seconds_for_plateau,
        "no_improve_validation_events": no_improve_validation_events,
        "actual_optimizer_steps": actual_steps,
        "optimizer_steps": optimizer_steps,
        "validation_events": validation_events,
        "validation_event_count": len(validation_events),
        "validation_schedule": sorted(validation_schedule),
        "stage_step_counts": stage_counts(actual_steps, args.max_steps),
        "first_train_loss": first_train_loss,
        "last_train_loss": last_train_loss,
        "loss_decrease": loss_decrease,
        "one_batch_overfit": overfit_summary,
        "checkpoint_best": str(best_path),
        "checkpoint_final": str(checkpoint_dir / "checkpoint_final.pt"),
        "prediction_dirs": [
            str(variant_dir / "predictions/fold_0/checkpoint_best/argmax"),
            str(variant_dir / "predictions/fold_0/checkpoint_best/pathology_aware"),
            str(variant_dir / "predictions/fold_0/checkpoint_final/argmax"),
            str(variant_dir / "predictions/fold_0/checkpoint_final/pathology_aware"),
        ],
        "proposal_thresholds": proposal_thresholds,
        "scar_decode_threshold": args.scar_decode_threshold,
        "edema_decode_threshold": args.edema_decode_threshold,
        "disable_local_refinement": bool(getattr(args, "disable_local_refinement", False)),
        "disable_anatomy_roi_prior": bool(getattr(args, "disable_anatomy_roi_prior", False)),
        "disable_nnunet_anchor": bool(getattr(args, "disable_nnunet_anchor", False)),
        "hardneg_components_csv": str(hardneg_path) if hardneg_path else "evidence not found",
        "hardneg_case_count": len(hardneg_targets),
        "hardneg_component_count": sum(len(v) for v in hardneg_targets.values()),
        "nnunet_anchor_manifest": anchor_manifest,
        "nnunet_anchor_root": str(anchor_root),
        "nnunet_anchor_train_case_count": len(train_cases),
        "nnunet_anchor_val_case_count": len(val_cases),
        "prototype_t2_repair_added_case_ids": prototype_t2_repair_added_case_ids,
        "nnunet_anchor_fold_counts": anchor_fold_counts,
        "nnunet_anchor_usage_status": "disabled_for_ablation" if bool(getattr(args, "disable_nnunet_anchor", False)) else "enabled",
        "three_stage_schedule": ["evidence_warmup", "proposal_dictionary", "soft_roi_refinement", "low_lr_calibration"],
        "baseline_preserving_residual_gate": "final_logits = nnunet_anchor_logits + gate * bounded_delta_srr when anchor probabilities are present",
        "baseline_gate_init": "closed-biased 1x1 gate; summary/training_log record gate mean and residual magnitude",
        "anatomy_distance_roi_prior": {
            "status": "implemented_runtime_consumed_needs_formal_ablation",
            "maps": [
                "p_union",
                "p_lv",
                "p_rv",
                "union_distance",
                "lv_distance",
                "rv_distance",
                "anatomy_uncertainty",
                "scar_anatomy_soft_gate",
                "edema_anatomy_soft_gate",
            ],
            "proposal_consumption": "scar/edema dictionaries receive task-specific anatomy soft gate logits instead of union-only logits",
            "refinement_consumption": "crop refiner receives P_union/P_LV/P_RV, distance maps, uncertainty, and task gate channels",
            "empty_union_policy": "bounded center fallback crop, not full-volume ROI",
            "no_t2_policy": "edema anatomy soft gate is zero and edema refiner emits blocked logits on no-T2 samples",
        },
        "prototype_bank_summary": prototype_bank_summary,
        "prototype_bank_summary_path": str(variant_dir / "prototype_bank_summary.json"),
        "skip_export": bool(args.skip_export),
    }
    (variant_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=["srr_propref_shared_dual_dict", "srr_propref_scar_precision", "srr_propref_no_proto_cascade"])
    parser.add_argument("--run-label", default="", help="Optional isolated output label under variants/ without changing model hparams.")
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260703)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--base-channels", type=int, default=32)
    parser.add_argument("--encoder-profile", choices=["tiny_3scale", "strong_4scale"], default="strong_4scale")
    parser.add_argument("--patch-shape", default="12,96,96")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=1800)
    parser.add_argument("--max-runtime-seconds", type=float, default=25200.0)
    parser.add_argument("--out-root", default=str(OUT_ROOT))
    parser.add_argument("--nnunet-anchor-root", default=str(DEFAULT_NNUNET_ANCHOR_ROOT))
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--grad-clip", type=float, default=12.0)
    parser.add_argument("--log-every", type=int, default=50)
    parser.add_argument("--val-every", type=int, default=300)
    parser.add_argument("--min-best-step-fraction", type=float, default=0.20)
    parser.add_argument("--early-stop-patience", type=int, default=8)
    parser.add_argument("--early-stop-min-delta", type=float, default=1e-3)
    parser.add_argument("--min-optimizer-steps-for-plateau", type=int, default=1500)
    parser.add_argument("--min-train-loop-seconds-for-plateau", type=float, default=1800.0)
    parser.add_argument("--complete-oversample", type=float, default=0.55)
    parser.add_argument("--oversample-foreground", type=float, default=0.82)
    parser.add_argument("--anatomy-weight", type=float, default=1.0)
    parser.add_argument("--scar-weight", type=float)
    parser.add_argument("--edema-weight", type=float)
    parser.add_argument("--proposal-weight", type=float)
    parser.add_argument("--margin-weight", type=float, default=0.20)
    parser.add_argument("--proposal-margin", type=float, default=0.25)
    parser.add_argument("--component-proposal-margin", type=float, default=0.35)
    parser.add_argument("--component-proposal-weight", type=float, default=0.20)
    parser.add_argument("--semantic-retrieval-weight", type=float, default=0.04)
    parser.add_argument("--semantic-coverage-weight", type=float, default=0.03)
    parser.add_argument("--semantic-integrative-weight", type=float, default=0.02)
    parser.add_argument("--baseline-preservation-weight", type=float, default=0.10)
    parser.add_argument("--baseline-preservation-confidence", type=float, default=0.80)
    parser.add_argument("--baseline-gate-harm-weight", type=float, default=0.25)
    parser.add_argument("--roi-weight", type=float, default=0.25)
    parser.add_argument("--roi-remote-weight", type=float, default=0.05)
    parser.add_argument("--proposal-thresholds", default=DEFAULT_PROPOSAL_THRESHOLDS)
    parser.add_argument("--scar-decode-threshold", type=float, default=0.50)
    parser.add_argument("--edema-decode-threshold", type=float, default=0.50)
    parser.add_argument("--overfit-steps", type=int, default=40)
    parser.add_argument("--overfit-log-every", type=int, default=10)
    parser.add_argument("--min-overfit-loss-decrease", type=float, default=0.01)
    parser.add_argument("--skip-overfit-sanity", action="store_true")
    parser.add_argument("--prototype-bank-cases", type=int, default=16)
    parser.add_argument("--skip-prototype-bank-fit", action="store_true")
    parser.add_argument("--max-eval-cases", type=int, default=0)
    parser.add_argument("--eval-case-ids", default="", help="Comma/semicolon-separated fold validation case ids to export/evaluate.")
    parser.add_argument("--train-case-ids", default="", help="Comma/semicolon-separated fold training case ids for controlled pilot subsets.")
    parser.add_argument("--limit-train-cases", type=int, default=0)
    parser.add_argument("--limit-val-cases", type=int, default=0)
    parser.add_argument("--hardneg-components-csv", default="results/20260629_proposal_memory_hardneg/mined_components.csv")
    parser.add_argument("--hardneg-sample-prob", type=float)
    parser.add_argument("--disable-local-refinement", action="store_true", help="Bypass crop ROI refinement and use proposal logits for pathology heads.")
    parser.add_argument("--disable-anatomy-roi-prior", action="store_true", help="Replace P_union/P_LV/P_RV distance gates with neutral ROI context.")
    parser.add_argument("--disable-nnunet-anchor", action="store_true", help="Remove nnU-Net anchor/component context from training, prototype fitting, and evaluation.")
    parser.add_argument("--skip-export", action="store_true")
    args = parser.parse_args()
    train_variant(args)


if __name__ == "__main__":
    main()
