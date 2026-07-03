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
    batch_from_cases,
    collect_case_metrics,
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
from src.care_myocardium.losses.srr_losses import anatomy_loss, retrieval_regularization, scar_loss, t2_masked_edema_loss  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402


OUT_ROOT = REPO_ROOT / "results/20260703_srr_propref_repair"
IGNORE_LABEL = -1
DEFAULT_PROPOSAL_THRESHOLDS = "0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90"


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
    if reg is not None:
        evidence = evidence + reg

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
        ("edema", edema_target & valid & t2_present, ((~edema_target) & valid & t2_present) | ((labels == 0) & valid & (~t2_present))),
    ]:
        pos = outputs[f"{prefix}_pos_similarity"][:, 0]
        neg = outputs[f"{prefix}_neg_similarity"][:, 0]
        if bool(pos_mask.any()):
            margin_terms.append(_masked_mean(torch.relu(args.proposal_margin - pos + neg), pos_mask))
        if bool(safe_neg.any()):
            margin_terms.append(_masked_mean(torch.relu(args.proposal_margin + pos - neg), safe_neg))
    margin = torch.stack(margin_terms).mean() if margin_terms else outputs["logits"].sum() * 0.0

    scar_roi = outputs["scar_soft_roi"][:, 0]
    edema_roi = outputs["edema_soft_roi"][:, 0]
    roi_cover = 0.5 * _masked_bce_dice(torch.logit(scar_roi.clamp(1e-4, 1 - 1e-4)), scar_target, valid)
    if bool(edema_mask.any()):
        roi_cover = roi_cover + 0.5 * _masked_bce_dice(torch.logit(edema_roi.clamp(1e-4, 1 - 1e-4)), edema_target, edema_mask)
    roi_remote = (scar_roi * (labels == 0).to(scar_roi.dtype)).mean()
    if bool(t2_present.any()):
        roi_remote = roi_remote + (edema_roi * (labels == 0).to(edema_roi.dtype) * t2_present.to(edema_roi.dtype)).mean()

    if stage == "evidence_warmup":
        total = evidence
        proposal_weight = 0.0
        refine_weight = 0.0
    elif stage == "proposal_dictionary":
        proposal_weight = args.proposal_weight
        refine_weight = 0.20
        total = evidence + proposal_weight * (scar_proposal + edema_proposal + args.margin_weight * margin)
    else:
        proposal_weight = args.proposal_weight
        refine_weight = 1.0
        total = (
            0.35 * evidence
            + refine_weight * final
            + proposal_weight * (scar_proposal + edema_proposal + args.margin_weight * margin)
            + args.roi_weight * roi_cover
            + args.roi_remote_weight * roi_remote
        )
    return total, {
        "evidence_loss": evidence.detach(),
        "final_loss": final.detach(),
        "scar_proposal_loss": scar_proposal.detach(),
        "edema_proposal_loss": edema_proposal.detach(),
        "proposal_margin_loss": margin.detach(),
        "roi_cover_loss": roi_cover.detach(),
        "roi_remote_loss": roi_remote.detach(),
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
    pred = torch.argmax(outputs["anatomy_logits"], dim=1)
    scar_prob = torch.sigmoid(outputs["scar_logits"][:, 0])
    edema_prob = torch.sigmoid(outputs["edema_logits"][:, 0])
    scar_mask = scar_prob >= scar_threshold
    edema_mask = edema_prob >= edema_threshold
    conflict = scar_mask & edema_mask
    pred = torch.where(edema_mask, torch.full_like(pred, 4), pred)
    pred = torch.where(scar_mask, torch.full_like(pred, 5), pred)
    pred = torch.where(conflict & (edema_prob > scar_prob), torch.full_like(pred, 4), pred)
    pred = torch.where(conflict & (scar_prob >= edema_prob), torch.full_like(pred, 5), pred)
    return pred


def predict_case(
    model: SRRProposeRefineMyoPS,
    case: CaseData,
    device: torch.device,
    *,
    scar_decode_threshold: float,
    edema_decode_threshold: float,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(case.image[None]).float().to(device)
        av = torch.from_numpy(case.availability[None]).float().to(device)
        outputs = model(x, av)
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
        ):
            aux[key] = outputs[key][0, 0].detach().cpu().numpy()
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
    checkpoint_name: str,
    proposal_thresholds: list[float],
    scar_decode_threshold: float,
    edema_decode_threshold: float,
) -> None:
    case_rows: list[dict[str, object]] = []
    proposal: list[dict[str, object]] = []
    roi: list[dict[str, object]] = []
    sanity: list[dict[str, object]] = []
    for case in cases:
        preds, aux = predict_case(
            model,
            case,
            device,
            scar_decode_threshold=scar_decode_threshold,
            edema_decode_threshold=edema_decode_threshold,
        )
        proposal.extend(proposal_rows(variant, case, aux, checkpoint_name=checkpoint_name, thresholds=proposal_thresholds))
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
    write_csv(variant_dir / f"prediction_sanity_{checkpoint_name}.csv", sanity)


def validate_patch_loss(
    model: SRRProposeRefineMyoPS,
    cases: list[CaseData],
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
            x_np, y_np, av_np = sample_patch(case, patch_shape, rng, oversample_foreground=1.0, modality_dropout=False)
            x = torch.from_numpy(x_np[None]).float().to(device)
            y = torch.from_numpy(y_np[None]).long().to(device)
            av = torch.from_numpy(av_np[None]).float().to(device)
            outputs = model(x, av)
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
    train_cases: list[CaseData],
    patch_shape: tuple[int, int, int],
    device: torch.device,
    variant_dir: Path,
) -> tuple[bool, dict[str, object]]:
    if args.skip_overfit_sanity:
        summary = {
            "variant": args.variant,
            "status": "SKIPPED",
            "reason": "skip_overfit_sanity was set",
            "required_by_task": True,
        }
        (variant_dir / "one_batch_overfit.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return False, summary
    rng = np.random.default_rng(args.seed + 991)
    case_pool = [case for case in train_cases if np.any(np.isin(case.label_arr, [4, 5]))] or train_cases
    case = case_pool[int(rng.integers(0, len(case_pool)))]
    x_np, y_np, av_np = sample_patch(case, patch_shape, rng, oversample_foreground=1.0, modality_dropout=False)
    x = torch.from_numpy(x_np[None]).float().to(device)
    y = torch.from_numpy(y_np[None]).long().to(device)
    av = torch.from_numpy(av_np[None]).float().to(device)
    model = SRRProposeRefineMyoPS(base_channels=args.base_channels, variant=args.variant).to(device)
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
        outputs = model(x, av)
        loss, metrics = propref_loss(outputs, y, av, stage, args)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        optimizer.step()
        loss_value = float(loss.detach().cpu())
        if first_loss is None:
            first_loss = loss_value
        last_loss = loss_value
        if step == 1:
            proto_rows.extend(prototype_sanity_row(args.variant, step, before, model))
        if step == 1 or step == args.overfit_steps or step % max(1, args.overfit_log_every) == 0:
            rows.append(
                {
                    "variant": args.variant,
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
        "variant": args.variant,
        "status": "PASS" if passed else "FAIL",
        "case_id": case.case_id,
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
    hp = variant_hparams(args.variant)
    for key, value in hp.items():
        if getattr(args, key) is None:
            setattr(args, key, value)
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    train_ids, val_ids = load_split(args.fold)
    if args.limit_train_cases > 0:
        train_ids = train_ids[: args.limit_train_cases]
    if args.limit_val_cases > 0:
        val_ids = val_ids[: args.limit_val_cases]
    metadata = load_myops_case_metadata()
    train_cases = [read_case(cid, metadata) for cid in train_ids]
    val_cases = [read_case(cid, metadata) for cid in val_ids]
    complete_cases = [case for case in train_cases if case.metadata.modality_group == "C0+LGE+T2"]
    scar_cases = [case for case in train_cases if np.any(case.label_arr == 5)]
    lge_only_scar_cases = [case for case in scar_cases if case.metadata.modality_group == "LGE-only"]
    edema_t2_cases = [case for case in train_cases if case.metadata.t2_present and np.any(case.label_arr == 4)]
    center_c_t2_edema_cases = [case for case in edema_t2_cases if case.metadata.center == "CenterC"]
    out_root = Path(args.out_root)
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    variant_dir = out_root / "variants" / args.variant
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
            "variant": args.variant,
            "fold": args.fold,
            "device": str(device),
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
        }
        (variant_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return

    model = SRRProposeRefineMyoPS(base_channels=args.base_channels, variant=args.variant).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    rng = np.random.default_rng(args.seed)
    best_val = float("inf")
    best_step = 0
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
        x_cpu, y_cpu, av_cpu, keys = batch_from_cases(
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
            lesion_mode="",
            hardneg_targets=hardneg_targets,
            hardneg_sample_prob=float(args.hardneg_sample_prob),
        )
        x = x_cpu.to(device)
        y = y_cpu.to(device)
        av = av_cpu.to(device)
        before = {name: param.detach().clone() for name, param in prototype_parameters(model)} if step in {1, max(1, args.max_steps // 2)} else {}
        optimizer.zero_grad(set_to_none=True)
        outputs = model(x, av)
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
            proto_rows.extend(prototype_sanity_row(args.variant, step, before, model))
        if step == 1 or step % args.log_every == 0:
            train_rows.append(
                {
                    "variant": args.variant,
                    "step": step,
                    "stage": stage,
                    "loss": loss_value,
                    "evidence_loss": float(metrics["evidence_loss"].cpu()),
                    "final_loss": float(metrics["final_loss"].cpu()),
                    "scar_proposal_loss": float(metrics["scar_proposal_loss"].cpu()),
                    "edema_proposal_loss": float(metrics["edema_proposal_loss"].cpu()),
                    "proposal_margin_loss": float(metrics["proposal_margin_loss"].cpu()),
                    "roi_cover_loss": float(metrics["roi_cover_loss"].cpu()),
                    "roi_remote_loss": float(metrics["roi_remote_loss"].cpu()),
                    "proposal_weight": float(metrics["proposal_weight"].cpu()),
                    "refine_weight": float(metrics["refine_weight"].cpu()),
                    "edema_supervised_batch_fraction": float(av[:, 1].mean().detach().cpu()),
                    "batch_cases": ",".join(keys),
                    "elapsed_seconds": time.monotonic() - start,
                }
            )
            record_gate_usage(usage_rows, args.variant, step, keys, outputs)
        if step in validation_schedule:
            val_loss = validate_patch_loss(model, val_cases, patch_shape, device, args.seed + step, args)
            validation_row = {
                "variant": args.variant,
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
                    "variant": args.variant,
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
            if validation_row["eligible_for_best"] and val_loss < best_val:
                best_val = val_loss
                best_step = step
                save_checkpoint(
                    {
                        "variant": args.variant,
                        "step": step,
                        "model_state_dict": model.state_dict(),
                        "args": vars(args),
                        "val_patch_loss": best_val,
                        "checkpoint_role": "eligible_best",
                    },
                    checkpoint_dir / "checkpoint_best.pt",
                )

    elapsed = time.monotonic() - start
    process_elapsed = time.process_time() - process_start
    actual_steps = optimizer_steps
    save_checkpoint(
        {
            "variant": args.variant,
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
        eval_cases = val_cases[: args.max_eval_cases] if args.max_eval_cases > 0 else val_cases
        for checkpoint_name, checkpoint_path in [("checkpoint_best", best_path), ("checkpoint_final", checkpoint_dir / "checkpoint_final.pt")]:
            state = torch.load(checkpoint_path, map_location=device, weights_only=False)
            model.load_state_dict(state["model_state_dict"])
            evaluate(
                model,
                eval_cases,
                variant_dir,
                args.variant,
                device,
                checkpoint_name=checkpoint_name,
                proposal_thresholds=proposal_thresholds,
                scar_decode_threshold=args.scar_decode_threshold,
                edema_decode_threshold=args.edema_decode_threshold,
            )
    write_csv(variant_dir / "training_log.csv", train_rows)
    write_csv(variant_dir / "validation_events.csv", validation_rows)
    write_csv(variant_dir / "retrieval_usage.csv", usage_rows)
    write_csv(variant_dir / "prototype_update_sanity_formal.csv", proto_rows)
    write_csv(variant_dir / "hardneg_memory.csv", memory_rows(args.variant, hardneg_path, len(hardneg_targets), sum(len(v) for v in hardneg_targets.values())))
    loss_decrease = None if first_train_loss is None or last_train_loss is None else first_train_loss - last_train_loss
    summary = {
        "variant": args.variant,
        "fold": args.fold,
        "device": str(device),
        "train_cases": len(train_cases),
        "val_cases": len(val_cases),
        "eval_cases": args.max_eval_cases if args.max_eval_cases > 0 else len(val_cases),
        "best_step": best_step,
        "best_val_patch_loss": best_val,
        "stop_reason": stop_reason,
        "elapsed_seconds": elapsed,
        "train_loop_seconds": elapsed,
        "process_wall_seconds": process_elapsed,
        "max_runtime_seconds": args.max_runtime_seconds,
        "max_steps": args.max_steps,
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
        "hardneg_components_csv": str(hardneg_path) if hardneg_path else "evidence not found",
        "hardneg_case_count": len(hardneg_targets),
        "hardneg_component_count": sum(len(v) for v in hardneg_targets.values()),
        "three_stage_schedule": ["evidence_warmup", "proposal_dictionary", "soft_roi_refinement", "low_lr_calibration"],
        "skip_export": bool(args.skip_export),
    }
    (variant_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=["srr_propref_shared_dual_dict", "srr_propref_scar_precision", "srr_propref_no_proto_cascade"])
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260703)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--base-channels", type=int, default=10)
    parser.add_argument("--patch-shape", default="12,96,96")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=1800)
    parser.add_argument("--max-runtime-seconds", type=float, default=25200.0)
    parser.add_argument("--out-root", default=str(OUT_ROOT))
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--grad-clip", type=float, default=12.0)
    parser.add_argument("--log-every", type=int, default=50)
    parser.add_argument("--val-every", type=int, default=300)
    parser.add_argument("--min-best-step-fraction", type=float, default=0.20)
    parser.add_argument("--complete-oversample", type=float, default=0.55)
    parser.add_argument("--oversample-foreground", type=float, default=0.82)
    parser.add_argument("--anatomy-weight", type=float, default=1.0)
    parser.add_argument("--scar-weight", type=float)
    parser.add_argument("--edema-weight", type=float)
    parser.add_argument("--proposal-weight", type=float)
    parser.add_argument("--margin-weight", type=float, default=0.20)
    parser.add_argument("--proposal-margin", type=float, default=0.25)
    parser.add_argument("--roi-weight", type=float, default=0.25)
    parser.add_argument("--roi-remote-weight", type=float, default=0.05)
    parser.add_argument("--proposal-thresholds", default=DEFAULT_PROPOSAL_THRESHOLDS)
    parser.add_argument("--scar-decode-threshold", type=float, default=0.50)
    parser.add_argument("--edema-decode-threshold", type=float, default=0.50)
    parser.add_argument("--overfit-steps", type=int, default=40)
    parser.add_argument("--overfit-log-every", type=int, default=10)
    parser.add_argument("--min-overfit-loss-decrease", type=float, default=0.01)
    parser.add_argument("--skip-overfit-sanity", action="store_true")
    parser.add_argument("--max-eval-cases", type=int, default=0)
    parser.add_argument("--limit-train-cases", type=int, default=0)
    parser.add_argument("--limit-val-cases", type=int, default=0)
    parser.add_argument("--hardneg-components-csv", default="results/20260629_proposal_memory_hardneg/mined_components.csv")
    parser.add_argument("--hardneg-sample-prob", type=float)
    parser.add_argument("--skip-export", action="store_true")
    args = parser.parse_args()
    train_variant(args)


if __name__ == "__main__":
    main()
