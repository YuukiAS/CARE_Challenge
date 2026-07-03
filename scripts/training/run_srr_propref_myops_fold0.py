#!/usr/bin/env python3
"""Train/evaluate SRR-ProposeRefine MyoPS fold0 variants."""

from __future__ import annotations

import argparse
import csv
import json
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


OUT_ROOT = REPO_ROOT / "results/20260703_myops_srr_propose_refine"
IGNORE_LABEL = -1


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


def predict_case(model: SRRProposeRefineMyoPS, case: CaseData, device: torch.device) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(case.image[None]).float().to(device)
        av = torch.from_numpy(case.availability[None]).float().to(device)
        outputs = model(x, av)
        pred = torch.argmax(outputs["logits"], dim=1)[0].detach().cpu().numpy().astype(np.uint8)
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
    return pred, aux


def write_prediction(path: Path, pred: np.ndarray, reference: sitk.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(pred)
    img.CopyInformation(reference)
    sitk.WriteImage(img, str(path))


def proposal_rows(variant: str, case: CaseData, aux: dict[str, np.ndarray]) -> list[dict[str, object]]:
    gt = case.label_arr.astype(np.uint8, copy=False)
    rows = []
    for cls, metric_name, prefix in [(5, "myops_scar", "scar"), (4, "myops_edema", "edema")]:
        logits = aux[f"{prefix}_proposal_logits"]
        prob = 1.0 / (1.0 + np.exp(-logits))
        proposal = prob >= 0.50
        gt_mask = gt == cls
        inter = int(np.logical_and(proposal, gt_mask).sum())
        proposal_voxels = int(proposal.sum())
        gt_voxels = int(gt_mask.sum())
        small_fp, remote_fp = _fp_counts(proposal, gt_mask)
        outside_union = int(np.logical_and(proposal, gt == 0).sum())
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": case.metadata.t2_present,
                "class_id": cls,
                "metric_name": metric_name,
                "proposal_threshold": 0.50,
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


def roi_rows(variant: str, case: CaseData, pred: np.ndarray, aux: dict[str, np.ndarray]) -> list[dict[str, object]]:
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


def evaluate(model: SRRProposeRefineMyoPS, cases: list[CaseData], variant_dir: Path, variant: str, device: torch.device) -> None:
    pred_dir = variant_dir / "predictions/fold_0/checkpoint_best"
    case_rows: list[dict[str, object]] = []
    proposal: list[dict[str, object]] = []
    roi: list[dict[str, object]] = []
    for case in cases:
        pred, aux = predict_case(model, case, device)
        write_prediction(pred_dir / f"{case.case_id}.nii.gz", pred, case.label_img)
        case_rows.extend(collect_case_metrics(variant, case, pred))
        proposal.extend(proposal_rows(variant, case, aux))
        roi.extend(roi_rows(variant, case, pred, aux))
    write_csv(variant_dir / "component_hd_by_case.csv", case_rows)
    write_csv(variant_dir / "subgroup_metrics.csv", summarize_subgroups(variant, case_rows))
    write_csv(variant_dir / "proposal_metrics.csv", proposal)
    write_csv(variant_dir / "roi_coverage.csv", roi)


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
    hardneg_path = Path(args.hardneg_components_csv) if args.hardneg_components_csv else None
    if hardneg_path is not None and not hardneg_path.is_absolute():
        hardneg_path = REPO_ROOT / hardneg_path
    hardneg_targets = load_hard_negative_targets(hardneg_path, args.variant)

    model = SRRProposeRefineMyoPS(base_channels=args.base_channels, variant=args.variant).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    rng = np.random.default_rng(args.seed)
    best_val = float("inf")
    best_step = 0
    stop_reason = "max_steps"
    train_rows: list[dict[str, object]] = []
    usage_rows: list[dict[str, object]] = []
    start = time.monotonic()
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
        optimizer.zero_grad(set_to_none=True)
        outputs = model(x, av)
        loss, metrics = propref_loss(outputs, y, av, stage, args)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        optimizer.step()
        if step == 1 or step % args.log_every == 0:
            train_rows.append(
                {
                    "variant": args.variant,
                    "step": step,
                    "stage": stage,
                    "loss": float(loss.detach().cpu()),
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
        if step == 1 or step % args.val_every == 0:
            val_loss = validate_patch_loss(model, val_cases, patch_shape, device, args.seed + step, args)
            train_rows.append(
                {
                    "variant": args.variant,
                    "step": step,
                    "stage": stage,
                    "event": "validation",
                    "val_patch_loss": val_loss,
                    "elapsed_seconds": time.monotonic() - start,
                }
            )
            if val_loss < best_val:
                best_val = val_loss
                best_step = step
                save_checkpoint(
                    {"variant": args.variant, "step": step, "model_state_dict": model.state_dict(), "args": vars(args), "val_patch_loss": best_val},
                    checkpoint_dir / "checkpoint_best.pt",
                )

    elapsed = time.monotonic() - start
    save_checkpoint({"variant": args.variant, "model_state_dict": model.state_dict(), "args": vars(args)}, checkpoint_dir / "checkpoint_final.pt")
    best_path = checkpoint_dir / "checkpoint_best.pt"
    if best_path.is_file():
        state = torch.load(best_path, map_location=device, weights_only=False)
        model.load_state_dict(state["model_state_dict"])
    else:
        save_checkpoint({"variant": args.variant, "model_state_dict": model.state_dict(), "args": vars(args)}, best_path)
        best_step = args.max_steps
    if not args.skip_export:
        evaluate(model, val_cases, variant_dir, args.variant, device)
    write_csv(variant_dir / "training_log.csv", train_rows)
    write_csv(variant_dir / "retrieval_usage.csv", usage_rows)
    write_csv(variant_dir / "hardneg_memory.csv", memory_rows(args.variant, hardneg_path, len(hardneg_targets), sum(len(v) for v in hardneg_targets.values())))
    summary = {
        "variant": args.variant,
        "fold": args.fold,
        "device": str(device),
        "train_cases": len(train_cases),
        "val_cases": len(val_cases),
        "best_step": best_step,
        "best_val_patch_loss": best_val,
        "stop_reason": stop_reason,
        "elapsed_seconds": elapsed,
        "max_runtime_seconds": args.max_runtime_seconds,
        "max_steps": args.max_steps,
        "checkpoint_best": str(best_path),
        "checkpoint_final": str(checkpoint_dir / "checkpoint_final.pt"),
        "prediction_dir": str(variant_dir / "predictions/fold_0/checkpoint_best"),
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
    parser.add_argument("--hardneg-components-csv", default="results/20260629_proposal_memory_hardneg/mined_components.csv")
    parser.add_argument("--hardneg-sample-prob", type=float)
    parser.add_argument("--skip-export", action="store_true")
    args = parser.parse_args()
    train_variant(args)


if __name__ == "__main__":
    main()
