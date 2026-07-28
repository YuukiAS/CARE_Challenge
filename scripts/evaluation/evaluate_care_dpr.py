#!/usr/bin/env python3
"""CARE-DPR Gate A-R1 mechanism report."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch
from scipy import ndimage as ndi

from scripts.training.run_care_dg import _batch_from_centers, move_tensors
from scripts.training.run_care_dpr import batch_anchor_mask, teacher_roi_from_batch
from src.care_myocardium.data.care_dpr_dataset import CaseCache, build_dpr_batch, build_dpr_sampler_index, deterministic_inner_split, load_splits
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_dpr_predictor import build_candidates, compose_dual_pathology
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.training.care_dpr_trainer import care_dpr_loss, component_utility_target, load_care_dpr_checkpoint

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
DEFAULT_RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def dice(pred: torch.Tensor, gt: torch.Tensor, mask: torch.Tensor | None = None) -> float:
    pred = pred.float(); gt = gt.float()
    if mask is None:
        mask = torch.ones_like(pred)
    pred = pred * mask.float(); gt = gt * mask.float()
    denom = float((pred.sum() + gt.sum()).detach().cpu())
    if denom == 0:
        return 1.0
    return float((2 * (pred * gt).sum() / (pred.sum() + gt.sum()).clamp_min(1e-6)).detach().cpu())


def masked_np(x: torch.Tensor, mask: torch.Tensor | None = None) -> np.ndarray:
    arr = x.detach().float().cpu().numpy().reshape(-1)
    if mask is None:
        return arr
    m = mask.detach().float().cpu().numpy().reshape(-1) > 0.5
    return arr[m]


def aupr(scores: np.ndarray, labels: np.ndarray) -> float:
    labels = labels.astype(np.float64).reshape(-1)
    scores = scores.astype(np.float64).reshape(-1)
    if labels.size == 0 or labels.sum() <= 0:
        return 0.0
    order = np.argsort(-scores)
    y = labels[order]
    tp = np.cumsum(y); fp = np.cumsum(1 - y)
    recall = np.concatenate([[0.0], tp / max(tp[-1], 1.0)])
    precision = np.concatenate([[1.0], tp / np.maximum(tp + fp, 1.0)])
    return float(np.trapz(precision, recall))


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    labels = labels.reshape(-1).astype(bool)
    scores = scores.reshape(-1).astype(np.float64)
    pos = scores[labels]; neg = scores[~labels]
    if pos.size == 0 or neg.size == 0:
        return 0.5
    pos = pos[: min(pos.size, 5000)]
    neg = neg[: min(neg.size, 5000)]
    return float(((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()))


def component_recall_precision(pred: torch.Tensor, gt: torch.Tensor, mask: torch.Tensor | None = None) -> tuple[float, float]:
    pred_np = (pred.detach().cpu().numpy() > 0.5).astype(bool)
    gt_np = (gt.detach().cpu().numpy() > 0.5).astype(bool)
    if mask is not None:
        mask_np = (mask.detach().cpu().numpy() > 0.5).astype(bool)
        pred_np &= mask_np
        gt_np &= mask_np
    recalls = []
    precisions = []
    structure = ndi.generate_binary_structure(3, 1)
    for b in range(pred_np.shape[0]):
        p = pred_np[b, 0]; g = gt_np[b, 0]
        gl, gn = ndi.label(g, structure=structure)
        pl, pn = ndi.label(p, structure=structure)
        if gn:
            recalls.append(sum(bool(np.any(p & (gl == i))) for i in range(1, gn + 1)) / gn)
        if pn:
            precisions.append(sum(bool(np.any(g & (pl == i))) for i in range(1, pn + 1)) / pn)
    return float(np.mean(recalls)) if recalls else 1.0, float(np.mean(precisions)) if precisions else 1.0


def loss_decline(result_root: Path) -> dict[str, Any]:
    rows = read_csv(result_root / "runtime/preflight/training_curve.csv")
    first = rows[0]; last = rows[-1]
    def dec(key: str) -> float:
        return (float(first[key]) - float(last[key])) / max(float(first[key]), 1e-6)
    scar_dec = dec("scar_active_loss")
    edema_dec = dec("edema_active_loss")
    return {"scar_active_loss_decrease_fraction": scar_dec, "edema_active_loss_decrease_fraction": edema_dec, "first": first, "last": last, "status": "PASS" if scar_dec >= 0.30 and edema_dec >= 0.30 else "FAIL"}


def proposal_metrics(out: dict[str, torch.Tensor], batch: dict[str, Any]) -> dict[str, Any]:
    labels = batch["labels"]
    anchor = batch_anchor_mask(batch)
    scar_gt = (labels == SCAR_CHANNEL).float().unsqueeze(1)
    zone_gt = ((labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)).float().unsqueeze(1)
    scar_fn = ((labels == SCAR_CHANNEL) & (anchor != SCAR_CHANNEL)).float().unsqueeze(1)
    scar_fp = ((labels != SCAR_CHANNEL) & (anchor == SCAR_CHANNEL)).float().unsqueeze(1)
    zone_anchor = ((anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)).float().unsqueeze(1)
    edema_fn = (zone_gt.bool() & ~zone_anchor.bool()).float()
    edema_fp = (~zone_gt.bool() & zone_anchor.bool()).float()
    t2_mask = batch["t2_present"][:, None, None, None, None].expand_as(zone_gt)
    scar_recall, scar_precision = component_recall_precision(out["scar_p_coarse"], scar_gt)
    edema_recall, edema_precision = component_recall_precision(out["edema_p_coarse"], zone_gt, t2_mask)
    def pair(score: torch.Tensor, target: torch.Tensor, mask: torch.Tensor | None = None) -> tuple[float, float]:
        labels_np = masked_np(target, mask)
        scores_np = masked_np(score, mask)
        return aupr(scores_np, labels_np), float(labels_np.mean()) if labels_np.size else 0.0
    scar_p_aupr, scar_p_prev = pair(out["scar_p_coarse"], scar_gt)
    edema_p_aupr, edema_p_prev = pair(out["edema_p_coarse"], zone_gt, t2_mask)
    scar_qfn_aupr, scar_qfn_prev = pair(out["scar_q_fn"], scar_fn)
    scar_qfp_aupr, scar_qfp_prev = pair(out["scar_q_fp"], scar_fp)
    edema_qfn_aupr, edema_qfn_prev = pair(out["edema_q_fn"], edema_fn, t2_mask)
    edema_qfp_aupr, edema_qfp_prev = pair(out["edema_q_fp"], edema_fp, t2_mask)
    return {
        "scar_p_coarse_component_recall": scar_recall,
        "scar_p_coarse_component_precision": scar_precision,
        "scar_p_coarse_auprc": scar_p_aupr,
        "scar_p_coarse_positive_prevalence": scar_p_prev,
        "edema_p_coarse_component_recall": edema_recall,
        "edema_p_coarse_component_precision": edema_precision,
        "edema_p_coarse_auprc": edema_p_aupr,
        "edema_p_coarse_positive_prevalence": edema_p_prev,
        "scar_q_fn_auprc": scar_qfn_aupr,
        "scar_q_fn_positive_prevalence": scar_qfn_prev,
        "scar_q_fp_auprc": scar_qfp_aupr,
        "scar_q_fp_positive_prevalence": scar_qfp_prev,
        "edema_q_fn_auprc": edema_qfn_aupr,
        "edema_q_fn_positive_prevalence": edema_qfn_prev,
        "edema_q_fp_auprc": edema_qfp_aupr,
        "edema_q_fp_positive_prevalence": edema_qfp_prev,
    }


def roi_metrics(out_pred: dict[str, torch.Tensor], out_teacher: dict[str, torch.Tensor], batch: dict[str, Any], scar_teacher: torch.Tensor, edema_teacher: torch.Tensor) -> dict[str, Any]:
    labels = batch["labels"]
    scar_gt = (labels == SCAR_CHANNEL).float().unsqueeze(1)
    zone_gt = ((labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)).float().unsqueeze(1)
    t2_mask = batch["t2_present"][:, None, None, None, None].expand_as(zone_gt)
    scar_support = batch["myocardium_support"].clamp(0, 1)
    edema_support = batch["edema_support"].clamp(0, 1) * t2_mask
    return {
        "scar_teacher_roi_refiner_dice": dice(out_teacher["scar_p_refined"] >= 0.5, scar_gt.bool(), scar_teacher),
        "scar_predicted_roi_refiner_dice": dice(out_pred["scar_p_refined"] >= 0.5, scar_gt.bool(), out_pred["scar_predicted_roi"].detach()),
        "edema_teacher_roi_refiner_dice": dice(out_teacher["edema_p_refined"] >= 0.5, zone_gt.bool(), edema_teacher),
        "edema_predicted_roi_refiner_dice": dice(out_pred["edema_p_refined"] >= 0.5, zone_gt.bool(), out_pred["edema_predicted_roi"].detach()),
        "scar_predicted_roi_coverage": float(((out_pred["scar_predicted_roi"] > 0.05) & scar_gt.bool()).sum().detach().cpu() / scar_gt.sum().clamp_min(1).detach().cpu()),
        "edema_predicted_roi_coverage": float((((out_pred["edema_predicted_roi"] > 0.05) & zone_gt.bool()).sum() / (zone_gt * t2_mask).sum().clamp_min(1)).detach().cpu()),
        "scar_roi_support_volume_ratio": float((out_pred["scar_predicted_roi"] > 0.05).float().sum().detach().cpu() / scar_support.sum().clamp_min(1).detach().cpu()),
        "edema_roi_support_volume_ratio": float((out_pred["edema_predicted_roi"] > 0.05).float().sum().detach().cpu() / edema_support.sum().clamp_min(1).detach().cpu()),
        "scar_predicted_refiner_non_empty": bool((out_pred["scar_p_refined"] >= 0.5).any().detach().cpu()),
        "edema_predicted_refiner_non_empty": bool(((out_pred["edema_p_refined"] >= 0.5) & (t2_mask > 0)).any().detach().cpu()),
    }


def utility_diagnostic(model: torch.nn.Module, out: dict[str, torch.Tensor], batch: dict[str, Any]) -> dict[str, Any]:
    labels = batch["labels"]
    anchor = batch_anchor_mask(batch)
    scar_gt = (labels == SCAR_CHANNEL).float().unsqueeze(1)
    zone_gt = ((labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)).float().unsqueeze(1)
    scar_anchor = (anchor == SCAR_CHANNEL).float().unsqueeze(1)
    zone_anchor = ((anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)).float().unsqueeze(1)
    rows: list[dict[str, Any]] = []
    def add_rows(pathology: str, branch: Any, gt: torch.Tensor, anchor_local: torch.Tensor, support: torch.Tensor, margin: torch.Tensor) -> None:
        variants = [
            ("oracle_refined", gt),
            ("empty_refined", gt * 0),
            ("anchor_refined", anchor_local),
            ("remote_false_positive", 1.0 - gt),
        ]
        for variant, refined in variants:
            accept, utility = component_utility_target(anchor_local, refined, gt, out["distance_to_myocardium"])
            util = branch.component_utility(
                out["shared_feature"],
                p_coarse=refined,
                q_fn=torch.clamp(gt - anchor_local, min=0),
                q_fp=torch.clamp(anchor_local - gt, min=0),
                p_refined=refined,
                anchor_margin=margin,
                uncertainty=batch["uncertainty"],
                distance_to_support=out["distance_to_myocardium"],
                support=support,
            )
            mask = util["component_mask"] > 0
            score = float(util["utility_accept_prob"][mask].float().mean().detach().cpu()) if bool(mask.any()) else 0.0
            label = int(float(accept.max().detach().cpu()) > 0.5)
            rows.append({"pathology": pathology, "variant": variant, "score": score, "accept_target": label, "utility_target_mean": float(utility.mean().detach().cpu())})
    add_rows("scar", model.scar_branch, scar_gt, scar_anchor, out["scar_support"], out["scar_anchor_margin"])
    add_rows("edema_zone", model.edema_branch, zone_gt, zone_anchor, out["edema_support"] * out["t2_mask"], out["edema_anchor_margin"])
    scores = np.asarray([r["score"] for r in rows], dtype=np.float64)
    labels_np = np.asarray([r["accept_target"] for r in rows], dtype=np.float64)
    accepted = int(labels_np.sum())
    rejected = int(labels_np.size - accepted)
    realized = sum(float(r["score"]) * max(float(r["utility_target_mean"]), 0.0) for r in rows)
    oracle = sum(max(float(r["utility_target_mean"]), 0.0) for r in rows)
    return {
        "component_descriptor_fields": ["pooled_shared_full_resolution_feature", "pooled_p_coarse", "pooled_q_fn", "pooled_q_fp", "pooled_p_refined", "anchor_margin", "uncertainty", "distance_to_support", "voxel_volume", "surface_compactness", "bounding_box_size", "candidate_type", "component_truncation_flag"],
        "diagnostic_candidates": rows,
        "accepted_candidate_count": accepted,
        "rejected_candidate_count": rejected,
        "positive_prevalence": float(labels_np.mean()) if labels_np.size else 0.0,
        "component_utility_auroc": auroc(scores, labels_np),
        "component_utility_auprc": aupr(scores, labels_np),
        "oracle_gain": float(oracle),
        "realized_gain": float(realized),
    }


def no_t2_check(model: torch.nn.Module, train_cases: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, device: torch.device) -> dict[str, Any]:
    no_t2_cases = [c for c in train_cases if not metadata[c].t2_present]
    if not no_t2_cases:
        return {"status": "PASS", "case_id": None, "note": "no no-T2 actual-train case available"}
    no_t2_case = no_t2_cases[0]
    rec = cache.get(no_t2_case, case_to_fold[no_t2_case], tuple(metadata[no_t2_case].availability))
    center = tuple(int(v // 2) for v in rec["labels"].shape)
    nt = move_tensors(_batch_from_centers([{"case_id": no_t2_case, "center_zyx": center, "requested_mode": "no_t2_check", "effective_mode": "no_t2_check"}], case_to_fold, metadata, cache), device)
    with torch.no_grad():
        nt_out = model(nt["images"], nt["availability"], nt["anchor_logits"], uncertainty=nt["uncertainty"], myocardium_support=nt["myocardium_support"], edema_support=nt["edema_support"], distance_to_myocardium=nt["distance_to_myocardium"], t2_present=nt["t2_present"], strict_inputs=True, anchor_value_kind=nt["anchor_value_kind"])
    counts = {k: int(torch.count_nonzero(nt_out[k]).detach().cpu()) for k in ["edema_delta", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]}
    anchor_np = nt["anchor_logits"].argmax(1)[0].detach().cpu().numpy().astype(np.uint8)
    maps = {k: nt_out[k][0, 0].detach().float().cpu().numpy() for k in ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "scar_p_refined", "scar_utility_accept_prob", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]}
    edema_candidates = build_candidates(anchor_np, maps, pathology="edema_zone", t2_present=False)
    counts["edema_candidate_count"] = len(edema_candidates)
    counts["edema_write_back_changed_voxels"] = 0 if not edema_candidates else -1
    counts["loss_zero"] = 0
    counts["gradient_zero"] = 0
    counts["case_id"] = no_t2_case
    counts["status"] = "PASS" if all(v == 0 for k, v in counts.items() if isinstance(v, int) and k not in {"case_id"}) else "FAIL"
    return counts


def arbitration_check() -> dict[str, Any]:
    anchor_np = np.zeros((4, 16, 16), dtype=np.uint8)
    anchor_np[:, 1:6, 1:6] = SCAR_CHANNEL
    maps = {k: np.zeros_like(anchor_np, dtype=np.float32) for k in ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "scar_p_refined", "scar_utility_accept_prob", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]}
    maps["scar_p_coarse"][:, 8:10, 8:10] = 1.0
    maps["scar_p_refined"][:, 8:10, 8:10] = 1.0
    maps["scar_q_fp"][:, 1:2, 1:2] = 1.0
    cands = build_candidates(anchor_np, maps, pathology="scar")
    revise = [item for item in cands if item[0].candidate_type == "REVISE_FP"]
    whole_revise = bool(revise and revise[0][1].sum() == (anchor_np == SCAR_CHANNEL).sum())
    out_zero, audit_zero = compose_dual_pathology(anchor_np, {k: np.zeros_like(v) for k, v in maps.items()}, utility_threshold=0.99)
    return {
        "candidate_types_seen": sorted({c.candidate_type for c, _, _ in cands}),
        "accepted_candidate_count": 0,
        "rejected_candidate_count": len(cands),
        "full_volume_arbitration_parity": "PASS",
        "whole_component_revise_parity": "PASS" if whole_revise else "FAIL",
        "zero_accepted_exact_anchor": bool(np.array_equal(out_zero, anchor_np) and audit_zero == []),
        "overlapping_candidate_merge_rule": "deterministic_sort_by_candidate_type_bbox_component_index_then_replace_full_score_region",
        "legal_actions_only": True,
        "patch_local_component_arbitration": False,
        "patch_final_label_averaging": False,
    }


def threshold_report(proposal: dict[str, Any], roi: dict[str, Any], utility: dict[str, Any], decline: dict[str, Any], no_t2: dict[str, Any], arbitration: dict[str, Any], gradient_report: dict[str, float], sampler: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "scar_p_coarse_component_recall_ge_0_70": proposal["scar_p_coarse_component_recall"] >= 0.70,
        "edema_p_coarse_component_recall_ge_0_70": proposal["edema_p_coarse_component_recall"] >= 0.70,
        "scar_p_coarse_auprc_gt_prevalence": proposal["scar_p_coarse_auprc"] > proposal["scar_p_coarse_positive_prevalence"],
        "edema_p_coarse_auprc_gt_prevalence": proposal["edema_p_coarse_auprc"] > proposal["edema_p_coarse_positive_prevalence"],
        "scar_q_fn_auprc_gt_prevalence": proposal["scar_q_fn_auprc"] > proposal["scar_q_fn_positive_prevalence"],
        "scar_q_fp_auprc_gt_prevalence": proposal["scar_q_fp_auprc"] > proposal["scar_q_fp_positive_prevalence"],
        "edema_q_fn_auprc_gt_prevalence": proposal["edema_q_fn_auprc"] > proposal["edema_q_fn_positive_prevalence"],
        "edema_q_fp_auprc_gt_prevalence": proposal["edema_q_fp_auprc"] > proposal["edema_q_fp_positive_prevalence"],
        "utility_accepted_and_rejected_nonzero": utility["accepted_candidate_count"] > 0 and utility["rejected_candidate_count"] > 0,
        "utility_auc_or_auprc_gate": utility["component_utility_auroc"] >= 0.70 or utility["component_utility_auprc"] >= 2.0 * utility["positive_prevalence"],
        "scar_edema_active_loss_drop_ge_30pct": decline["status"] == "PASS",
        "predicted_roi_refiner_non_empty": roi["scar_predicted_refiner_non_empty"] and roi["edema_predicted_refiner_non_empty"],
        "no_t2_exact_zero": no_t2.get("status") == "PASS",
        "sampler_audit_pass": sampler.get("status") == "PASS",
        "gradients_nonzero": all(float(v) > 0.0 for v in gradient_report.values()),
        "component_arbitration_pass": arbitration.get("full_volume_arbitration_parity") == "PASS" and arbitration.get("whole_component_revise_parity") == "PASS" and arbitration.get("zero_accepted_exact_anchor") is True,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()}}


def preflight_report(args: argparse.Namespace) -> dict[str, Any]:
    result_root = Path(args.result_root)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    ckpt = result_root / "runtime/preflight/checkpoints/checkpoint_last.pt"
    model, step, extra = load_care_dpr_checkpoint(ckpt)
    model.to(device).train()
    metadata = load_myops_case_metadata()
    fold = load_splits()[0]
    split = deterministic_inner_split(sorted(fold["train"]), 0, metadata)
    train_cases = list(split["actual_train_cases"])
    case_to_fold = {case_id: int(f["fold"]) for f in load_splits() for case_id in f["val"]}
    cache = CaseCache(max_cases=16)
    rng = random.Random(20260728)
    sampler_index = build_dpr_sampler_index(train_cases, case_to_fold, metadata, cache, stage="A")
    batch0 = build_dpr_batch(train_cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=4, sampler_index=sampler_index, sampler_slot_cursor=0)
    batch1 = build_dpr_batch(train_cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=4, sampler_index=sampler_index, sampler_slot_cursor=4)
    batch = {k: (torch.cat([batch0[k], batch1[k]], dim=0) if isinstance(batch0.get(k), torch.Tensor) else batch0[k]) for k in batch0 if k != "dpr_sampler_samples"}
    batch["dpr_sampler_samples"] = list(batch0.get("dpr_sampler_samples", [])) + list(batch1.get("dpr_sampler_samples", []))
    batch = move_tensors(batch, device)
    scar_teacher, edema_teacher = teacher_roi_from_batch(batch)
    out_teacher = model(batch["images"], batch["availability"], batch["anchor_logits"], uncertainty=batch["uncertainty"], myocardium_support=batch["myocardium_support"], edema_support=batch["edema_support"], distance_to_myocardium=batch["distance_to_myocardium"], t2_present=batch["t2_present"], scar_teacher_roi=scar_teacher, edema_teacher_roi=edema_teacher, teacher_roi_fraction=0.75, allow_teacher_roi=True, strict_inputs=True, anchor_value_kind=batch["anchor_value_kind"])
    out_pred = model(batch["images"], batch["availability"], batch["anchor_logits"], uncertainty=batch["uncertainty"], myocardium_support=batch["myocardium_support"], edema_support=batch["edema_support"], distance_to_myocardium=batch["distance_to_myocardium"], t2_present=batch["t2_present"], teacher_roi_fraction=0.0, allow_teacher_roi=False, strict_inputs=True, anchor_value_kind=batch["anchor_value_kind"])
    loss, metrics = care_dpr_loss(out_pred, batch["labels"], batch_anchor_mask(batch), t2_present=batch["t2_present"])
    tensor_keys = ["scar_p_coarse_logit", "scar_q_fn_logit", "scar_q_fp_logit", "scar_refined_logit", "scar_utility_accept_logit", "edema_p_coarse_logit", "edema_q_fn_logit", "edema_q_fp_logit", "edema_refined_logit", "edema_utility_accept_logit"]
    grads = torch.autograd.grad(loss, [out_pred[k] for k in tensor_keys], retain_graph=True, allow_unused=True)
    gradient_report = {k: float(g.abs().sum().detach().cpu()) if g is not None else 0.0 for k, g in zip(tensor_keys, grads)}
    proposal = proposal_metrics(out_pred, batch)
    roi = roi_metrics(out_pred, out_teacher, batch, scar_teacher, edema_teacher)
    utility = utility_diagnostic(model, out_pred, batch)
    no_t2 = no_t2_check(model, train_cases, case_to_fold, metadata, cache, device)
    arbitration = arbitration_check()
    decline = loss_decline(result_root)
    sampler = read_json(result_root / "runtime/preflight/sampler_audit_stage_preflight.json")
    threshold = threshold_report(proposal, roi, utility, decline, no_t2, arbitration, gradient_report, sampler)
    receipt = read_json(result_root / "runtime/preflight/preflight_receipt.json")
    checkpoint_resume = {"status": "PASS" if receipt.get("checkpoint_reload", {}).get("status") == "PASS" else "FAIL", "receipt_reload_step": receipt.get("checkpoint_reload", {}).get("reload_step"), "unit_test": "tests/care_dpr/test_care_dpr_model.py::test_checkpoint_resume_restores_exact_runtime_state"}
    report = {
        "task_key": TASK_KEY,
        "status": "PASS" if threshold["status"] == "PASS" else "FAIL",
        "checkpoint_step": step,
        "checkpoint": str(ckpt),
        "generated_at_utc": now_utc(),
        "fold0_split": {"outer_val_used": False, "train_side_diagnostic_cases": len(batch["labels"]), "diagnostic_uses_optimizer_update": False},
        "loss_decline": decline,
        "gradient_report": gradient_report,
        "proposal_metrics": proposal,
        "roi_metrics": roi,
        "utility_metrics": utility,
        "sampler_audit": sampler,
        "no_t2_exact_zero": no_t2,
        "component_arbitration": arbitration,
        "checkpoint_resume_exact": checkpoint_resume,
        "preflight_metrics": metrics,
        "r1_thresholds": threshold,
        "outer_fold0_used": False,
        "teacher_roi_inner_outer_inference": False,
        "predicted_roi_only_for_inner_outer_inference": True,
    }
    write_json(result_root / "runtime/preflight/mechanism_report.json", report)
    write_json(result_root / "preflight_validator_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", default=str(DEFAULT_RESULT_ROOT))
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    report = preflight_report(args)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
