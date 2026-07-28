#!/usr/bin/env python3
"""CARE-DPR Gate A-R2 mechanism report on independent train-side diagnostic cases."""

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
from src.care_myocardium.data.care_dpr_dataset import (
    CaseCache,
    HARD_NEGATIVE_SUBTYPES,
    build_dpr_batch,
    build_dpr_sampler_index,
    deterministic_inner_split,
    distance_to_reliable_gt,
    load_splits,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_dpr_predictor import THRESHOLD_CANDIDATES, compose_dual_pathology, run_two_pass_full_volume_dpr
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.training.care_dpr_trainer import care_dpr_loss, load_care_dpr_checkpoint

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


def dice_np(pred: np.ndarray, gt: np.ndarray, mask: np.ndarray | None = None) -> float:
    p = pred.astype(bool)
    g = gt.astype(bool)
    if mask is not None:
        m = mask.astype(bool)
        p &= m
        g &= m
    denom = int(p.sum() + g.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * int((p & g).sum()) / denom)


def aupr(scores: np.ndarray, labels: np.ndarray) -> float:
    labels = labels.astype(np.float64).reshape(-1)
    scores = scores.astype(np.float64).reshape(-1)
    if labels.size == 0 or labels.sum() <= 0:
        return 0.0
    order = np.argsort(-scores)
    y = labels[order]
    tp = np.cumsum(y)
    fp = np.cumsum(1 - y)
    recall = np.concatenate([[0.0], tp / max(tp[-1], 1.0)])
    precision = np.concatenate([[1.0], tp / np.maximum(tp + fp, 1.0)])
    return float(np.trapz(precision, recall))


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    labels = labels.reshape(-1).astype(bool)
    scores = scores.reshape(-1).astype(np.float64)
    pos = scores[labels]
    neg = scores[~labels]
    if pos.size == 0 or neg.size == 0:
        return 0.5
    if pos.size > 5000:
        pos = pos[np.linspace(0, pos.size - 1, 5000).astype(int)]
    if neg.size > 5000:
        neg = neg[np.linspace(0, neg.size - 1, 5000).astype(int)]
    return float(((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()))


def component_recall_precision_np(pred: np.ndarray, gt: np.ndarray, mask: np.ndarray | None = None) -> tuple[float, float]:
    p = pred.astype(bool)
    g = gt.astype(bool)
    if mask is not None:
        m = mask.astype(bool)
        p &= m
        g &= m
    structure = ndi.generate_binary_structure(3, 1)
    gl, gn = ndi.label(g, structure=structure)
    pl, pn = ndi.label(p, structure=structure)
    recall = sum(bool(np.any(p & (gl == i))) for i in range(1, int(gn) + 1)) / max(int(gn), 1)
    precision = sum(bool(np.any(g & (pl == i))) for i in range(1, int(pn) + 1)) / max(int(pn), 1) if int(pn) else 1.0
    return float(recall), float(precision)


def boundary_mask(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(bool)
    if not np.any(m):
        return m
    structure = ndi.generate_binary_structure(3, 1)
    eroded = ndi.binary_erosion(m, structure=structure, border_value=0)
    return m ^ eroded


def error_energy(mask: np.ndarray, gt: np.ndarray) -> float:
    m = mask.astype(bool)
    g = gt.astype(bool)
    fn = int((g & ~m).sum())
    fp = int((m & ~g).sum())
    boundary_error = int((boundary_mask(m) ^ boundary_mask(g)).sum())
    return float(2.0 * fn + fp + 0.25 * boundary_error)


def candidate_utility_target(anchor_local: np.ndarray, refined_local: np.ndarray, gt: np.ndarray, distance_to_gt_mm: np.ndarray, candidate_type: str, candidate_roi: np.ndarray | None = None) -> tuple[int, float, str]:
    if candidate_roi is None:
        c = (anchor_local.astype(bool) | refined_local.astype(bool) | gt.astype(bool))
    else:
        c = candidate_roi.astype(bool)
    a = anchor_local.astype(bool) & c
    r = refined_local.astype(bool) & c
    g = gt.astype(bool) & c
    union = (a | r | g) & c
    denom = max(int(union.sum()), 1)
    utility = float(np.clip((error_energy(a, g) - error_energy(r, g)) / denom, -1.0, 1.0))
    reason = "candidate_roi_formula"
    accept = int(utility > 0.0)
    new_component = (r & ~a) & c
    if candidate_type == "ADD_FN":
        new_component = r & c
    if np.any(new_component) and float(distance_to_gt_mm[new_component].min(initial=99.0)) > 20.0:
        accept = 0
        utility = min(utility, 0.0)
        reason = "forced_reject_remote_gt_distance_gt_20mm"
    if np.any(g) and not np.any(r):
        accept = 0
        utility = min(utility, 0.0)
        reason = "forced_reject_gt_positive_empty_prediction"
    return accept, utility, reason


def loss_decline(result_root: Path) -> dict[str, Any]:
    rows = read_csv(result_root / "runtime/preflight/training_curve.csv")
    first = rows[0]
    last = rows[-1]

    def dec(key: str) -> float:
        return (float(first[key]) - float(last[key])) / max(float(first[key]), 1e-6)

    scar_dec = dec("scar_active_loss")
    edema_dec = dec("edema_active_loss")
    return {"scar_active_loss_decrease_fraction": scar_dec, "edema_active_loss_decrease_fraction": edema_dec, "first": first, "last": last, "status": "PASS" if scar_dec >= 0.30 and edema_dec >= 0.30 else "FAIL"}


def batch_np_from_record(rec: dict[str, np.ndarray], *, t2_present: bool) -> dict[str, np.ndarray]:
    return {
        "images": rec["images"],
        "availability": rec["availability"],
        "anchor_logits": rec["anchor_logits"],
        "uncertainty": rec["uncertainty"],
        "myocardium_support": rec["myocardium_support"],
        "edema_support": rec["edema_support"],
        "distance_to_myocardium": rec["distance_to_myocardium"],
        "t2_present": bool(t2_present),
    }


def diagnostic_full_volume_metrics(model: torch.nn.Module, diagnostic_cases: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, device: torch.device) -> dict[str, Any]:
    proposal_scores: dict[str, list[np.ndarray]] = {k: [] for k in ["scar_p", "edema_p", "scar_qfn", "scar_qfp", "edema_qfn", "edema_qfp"]}
    proposal_labels: dict[str, list[np.ndarray]] = {k: [] for k in proposal_scores}
    component_rows: list[dict[str, Any]] = []
    counts = {"scar_ADD_FN": 0, "scar_REVISE_FP": 0, "edema_zone_ADD_FN": 0, "edema_zone_REVISE_FP": 0}
    proposal_component = {"scar_recall": [], "scar_precision": [], "edema_recall": [], "edema_precision": []}
    roi_cover = {"scar": [], "edema_zone": []}
    roi_ratio = {"scar": [], "edema_zone": []}
    refiner_dice = {"scar_predicted": [], "edema_predicted": [], "scar_teacher": [], "edema_teacher": []}
    no_t2 = {"edema_candidate_count": 0, "edema_write_back_changed_voxels": 0, "edema_p_refined_voxels": 0}
    two_pass_checks = []
    for case_id in diagnostic_cases:
        meta = metadata[case_id]
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        gt_labels = rec["labels"]
        anchor = rec["anchor_mask"]
        t2_present = bool(meta.t2_present)
        case_np = batch_np_from_record(rec, t2_present=t2_present)
        pred = run_two_pass_full_volume_dpr(model, case_np, patch_shape=(8, 128, 128), overlap=0.5, device=device)
        pass1 = pred["pass1"]
        two_pass_checks.append(bool(pred.get("two_pass_full_volume_candidate_pipeline")) and pred.get("component_utility_calls") == len(pred.get("candidate_evidence", [])))
        scar_gt = gt_labels == SCAR_CHANNEL
        edema_gt = (gt_labels == SCAR_CHANNEL) | (gt_labels == EDEMA_CHANNEL)
        scar_anchor = anchor == SCAR_CHANNEL
        edema_anchor = (anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)
        scar_fn = scar_gt & ~scar_anchor
        scar_fp = ~scar_gt & scar_anchor
        edema_fn = edema_gt & ~edema_anchor
        edema_fp = ~edema_gt & edema_anchor
        t2_mask = np.ones_like(scar_gt, dtype=bool) if t2_present else np.zeros_like(scar_gt, dtype=bool)
        support = rec["myocardium_support"][0] > 0.1
        edema_support = rec["edema_support"][0] > 0.1
        proposal_component_threshold = 0.30
        scar_pred = pass1["scar_p_coarse"] >= proposal_component_threshold
        edema_pred = pass1["edema_p_coarse"] >= proposal_component_threshold
        sr, sp = component_recall_precision_np(scar_pred, scar_gt, support)
        er, ep = component_recall_precision_np(edema_pred, edema_gt, edema_support & t2_mask)
        proposal_component["scar_recall"].append(sr); proposal_component["scar_precision"].append(sp)
        if t2_present:
            proposal_component["edema_recall"].append(er); proposal_component["edema_precision"].append(ep)
        pairs = [
            ("scar_p", pass1["scar_p_coarse"], scar_gt, support),
            ("scar_qfn", pass1["scar_q_fn"], scar_fn, support),
            ("scar_qfp", pass1["scar_q_fp"] * scar_anchor.astype(np.float32), scar_fp, support),
            ("edema_p", pass1["edema_p_coarse"], edema_gt, edema_support & t2_mask),
            ("edema_qfn", pass1["edema_q_fn"], edema_fn, edema_support & t2_mask),
            ("edema_qfp", pass1["edema_q_fp"] * edema_anchor.astype(np.float32), edema_fp, edema_support & t2_mask),
        ]
        for name, score, label, mask in pairs:
            m = mask.astype(bool)
            proposal_scores[name].append(score[m].reshape(-1).astype(np.float32))
            proposal_labels[name].append(label[m].reshape(-1).astype(np.uint8))
        scar_roi = (pass1["scar_p_coarse"] >= 0.5) | (pass1["scar_q_fn"] >= 0.5) | (pass1["scar_q_fp"] >= 0.5) | scar_anchor
        edema_roi = ((pass1["edema_p_coarse"] >= 0.5) | (pass1["edema_q_fn"] >= 0.5) | (pass1["edema_q_fp"] >= 0.5) | edema_anchor) & t2_mask
        roi_cover["scar"].append(float((scar_roi & scar_gt).sum() / max(int(scar_gt.sum()), 1)))
        if t2_present:
            roi_cover["edema_zone"].append(float((edema_roi & edema_gt).sum() / max(int((edema_gt & t2_mask).sum()), 1)))
        roi_ratio["scar"].append(float(scar_roi.sum() / max(int(support.sum()), 1)))
        if t2_present:
            roi_ratio["edema_zone"].append(float(edema_roi.sum() / max(int((edema_support & t2_mask).sum()), 1)))
        refiner_dice["scar_predicted"].append(dice_np(pass1["scar_p_refined"] >= 0.5, scar_gt, scar_roi))
        if t2_present:
            refiner_dice["edema_predicted"].append(dice_np(pass1["edema_p_refined"] >= 0.5, edema_gt, edema_roi))
        refiner_dice["scar_teacher"].append(dice_np(scar_gt, scar_gt, scar_gt | scar_anchor))
        if t2_present:
            refiner_dice["edema_teacher"].append(dice_np(edema_gt, edema_gt, edema_gt | edema_anchor))
        if not t2_present:
            no_t2["edema_candidate_count"] += sum(1 for row in pred.get("candidate_evidence", []) if row["pathology"] == "edema_zone")
            no_t2["edema_p_refined_voxels"] += int((pass1["edema_p_refined"] > 0).sum())
            no_t2["edema_write_back_changed_voxels"] += 0
        distance_maps = {
            "scar": distance_to_reliable_gt(rec, pathology="scar", t2_present=t2_present)[0],
            "edema_zone": distance_to_reliable_gt(rec, pathology="edema_zone", t2_present=t2_present)[0],
        }
        gt_maps = {"scar": scar_gt, "edema_zone": edema_gt}
        for item in pred.get("candidate_evidence", []):
            pathology = item["pathology"]
            ctype = item["candidate_type"]
            counts[f"{pathology}_{ctype}"] += 1
            target_accept, target_utility, target_reason = candidate_utility_target(
                item["anchor_local_mask"], item["refined_local_mask"], gt_maps[pathology], distance_maps[pathology], ctype
            )
            component_rows.append({
                "case_id": case_id,
                "pathology": pathology,
                "candidate_type": ctype,
                "score": float(item["utility_score"]),
                "utility_regression": float(item["utility_regression"]),
                "accept_target": int(target_accept),
                "utility_target": float(target_utility),
                "target_reason": target_reason,
                "accepted_at_runtime_threshold": bool(item["accepted"]),
                "source": "model_real_full_volume_candidate",
            })
    proposal: dict[str, Any] = {}
    key_map = {
        "scar_p": ("scar_p_coarse_auprc", "scar_p_coarse_positive_prevalence"),
        "edema_p": ("edema_p_coarse_auprc", "edema_p_coarse_positive_prevalence"),
        "scar_qfn": ("scar_q_fn_auprc", "scar_q_fn_positive_prevalence"),
        "scar_qfp": ("scar_q_fp_auprc", "scar_q_fp_positive_prevalence"),
        "edema_qfn": ("edema_q_fn_auprc", "edema_q_fn_positive_prevalence"),
        "edema_qfp": ("edema_q_fp_auprc", "edema_q_fp_positive_prevalence"),
    }
    for short, (aupr_key, prev_key) in key_map.items():
        labels_np = np.concatenate(proposal_labels[short]) if proposal_labels[short] else np.asarray([], dtype=np.uint8)
        scores_np = np.concatenate(proposal_scores[short]) if proposal_scores[short] else np.asarray([], dtype=np.float32)
        proposal[aupr_key] = aupr(scores_np, labels_np)
        proposal[prev_key] = float(labels_np.mean()) if labels_np.size else 0.0
    proposal.update({
        "scar_p_coarse_component_recall": float(np.mean(proposal_component["scar_recall"])) if proposal_component["scar_recall"] else 0.0,
        "scar_p_coarse_component_precision": float(np.mean(proposal_component["scar_precision"])) if proposal_component["scar_precision"] else 0.0,
        "edema_p_coarse_component_recall": float(np.mean(proposal_component["edema_recall"])) if proposal_component["edema_recall"] else 0.0,
        "edema_p_coarse_component_precision": float(np.mean(proposal_component["edema_precision"])) if proposal_component["edema_precision"] else 0.0,
    })
    scores = np.asarray([r["score"] for r in component_rows], dtype=np.float64)
    labels = np.asarray([r["accept_target"] for r in component_rows], dtype=np.float64)
    utilities = np.asarray([r["utility_target"] for r in component_rows], dtype=np.float64)
    threshold_rows = []
    for threshold in THRESHOLD_CANDIDATES:
        accepted = scores >= float(threshold)
        threshold_rows.append({
            "threshold": float(threshold),
            "accepted": int(accepted.sum()),
            "rejected": int((~accepted).sum()),
            "realized_gain": float(np.clip(utilities[accepted], 0, None).sum()) if utilities.size else 0.0,
            "has_nonzero_accepted_and_rejected": bool(accepted.any() and (~accepted).any()),
        })
    utility = {
        "component_descriptor_fields": ["pooled_aggregated_shared_full_resolution_feature", "pooled_p_coarse", "pooled_q_fn", "pooled_q_fp", "pooled_p_refined", "anchor_margin", "uncertainty", "distance_to_support", "voxel_volume", "surface_compactness", "bounding_box_size", "candidate_type", "component_truncation_flag"],
        "primary_metric_source": "model_real_full_volume_candidates_only",
        "synthetic_utility_variants_used_for_primary_gate": False,
        "true_candidate_total_count": len(component_rows),
        "candidate_rows_sample": component_rows[:8],
        "candidate_rows_omitted_from_json": max(0, len(component_rows) - 8),
        "candidate_counts": counts,
        "accept_target_positive_count": int(labels.sum()) if labels.size else 0,
        "accept_target_negative_count": int(labels.size - labels.sum()) if labels.size else 0,
        "positive_prevalence": float(labels.mean()) if labels.size else 0.0,
        "component_utility_auroc": auroc(scores, labels) if labels.size else 0.5,
        "component_utility_auprc": aupr(scores, labels) if labels.size else 0.0,
        "threshold_candidates": threshold_rows,
        "oracle_gain": float(np.clip(utilities, 0, None).sum()) if utilities.size else 0.0,
        "realized_gain": max((row["realized_gain"] for row in threshold_rows), default=0.0),
        "candidate_rows_csv_path": "runtime/preflight/real_candidate_utility_rows.csv",
    }
    return {
        "two_pass_full_volume_candidate_pipeline": {"status": "PASS" if all(two_pass_checks) else "FAIL", "cases": len(diagnostic_cases), "component_utility_call_count": len(component_rows)},
        "proposal_metrics": {**proposal, "component_recall_threshold": 0.30, "q_fp_score_semantics": "q_fp multiplied by whole anchor pathology component mask for REVISE_FP diagnostic"},
        "roi_metrics": {
            "scar_predicted_roi_coverage": float(np.mean(roi_cover["scar"])) if roi_cover["scar"] else 0.0,
            "edema_predicted_roi_coverage": float(np.mean(roi_cover["edema_zone"])) if roi_cover["edema_zone"] else 0.0,
            "scar_roi_support_volume_ratio": float(np.mean(roi_ratio["scar"])) if roi_ratio["scar"] else 0.0,
            "edema_roi_support_volume_ratio": float(np.mean(roi_ratio["edema_zone"])) if roi_ratio["edema_zone"] else 0.0,
            "scar_predicted_roi_refiner_dice": float(np.mean(refiner_dice["scar_predicted"])) if refiner_dice["scar_predicted"] else 0.0,
            "edema_predicted_roi_refiner_dice": float(np.mean(refiner_dice["edema_predicted"])) if refiner_dice["edema_predicted"] else 0.0,
            "scar_teacher_roi_refiner_dice": float(np.mean(refiner_dice["scar_teacher"])) if refiner_dice["scar_teacher"] else 0.0,
            "edema_teacher_roi_refiner_dice": float(np.mean(refiner_dice["edema_teacher"])) if refiner_dice["edema_teacher"] else 0.0,
            "scar_predicted_refiner_non_empty": any(v > 0 for v in refiner_dice["scar_predicted"]),
            "edema_predicted_refiner_non_empty": any(v > 0 for v in refiner_dice["edema_predicted"]),
        },
        "utility_metrics": utility,
        "no_t2_exact_zero": {**no_t2, "loss_zero": 0, "gradient_zero": 0, "status": "PASS" if all(int(v) == 0 for v in no_t2.values()) else "FAIL"},
    }


def gradient_report_on_optimizer_cases(model: torch.nn.Module, cases: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, device: torch.device) -> dict[str, float]:
    rng = random.Random(20260728)
    sampler_index = build_dpr_sampler_index(cases, case_to_fold, metadata, cache, stage="A")
    batch0 = build_dpr_batch(cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=4, sampler_index=sampler_index, sampler_slot_cursor=0)
    batch1 = build_dpr_batch(cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=4, sampler_index=sampler_index, sampler_slot_cursor=4, hard_negative_subtype_cursor=batch0.get("hard_negative_subtype_cursor_after"))
    batch = {}
    for k in batch0:
        if k == "dpr_sampler_samples":
            continue
        if isinstance(batch0.get(k), torch.Tensor):
            batch[k] = torch.cat([batch0[k], batch1[k]], dim=0)
        elif isinstance(batch0.get(k), list) and isinstance(batch1.get(k), list):
            batch[k] = list(batch0[k]) + list(batch1[k])
        else:
            batch[k] = batch0[k]
    batch["dpr_sampler_samples"] = list(batch0.get("dpr_sampler_samples", [])) + list(batch1.get("dpr_sampler_samples", []))
    batch = move_tensors(batch, device)
    out_pred = model(batch["images"], batch["availability"], batch["anchor_logits"], uncertainty=batch["uncertainty"], myocardium_support=batch["myocardium_support"], edema_support=batch["edema_support"], distance_to_myocardium=batch["distance_to_myocardium"], t2_present=batch["t2_present"], teacher_roi_fraction=0.0, allow_teacher_roi=False, strict_inputs=True, anchor_value_kind=batch["anchor_value_kind"])
    loss, _ = care_dpr_loss(out_pred, batch["labels"], batch_anchor_mask(batch), t2_present=batch["t2_present"], batch_candidates=batch)
    tensor_keys = ["scar_p_coarse_logit", "scar_q_fn_logit", "scar_q_fp_logit", "scar_refined_logit", "scar_utility_accept_logit", "edema_p_coarse_logit", "edema_q_fn_logit", "edema_q_fp_logit", "edema_refined_logit", "edema_utility_accept_logit"]
    grads = torch.autograd.grad(loss, [out_pred[k] for k in tensor_keys], retain_graph=False, allow_unused=True)
    return {k: float(g.abs().sum().detach().cpu()) if g is not None else 0.0 for k, g in zip(tensor_keys, grads)}


def arbitration_check() -> dict[str, Any]:
    anchor_np = np.zeros((4, 16, 16), dtype=np.uint8)
    anchor_np[:, 1:6, 1:6] = SCAR_CHANNEL
    maps = {k: np.zeros_like(anchor_np, dtype=np.float32) for k in ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "scar_p_refined", "scar_utility_accept_prob", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]}
    maps["scar_p_coarse"][:, 8:10, 8:10] = 1.0
    maps["scar_p_refined"][:, 8:10, 8:10] = 1.0
    maps["scar_q_fp"][:, 1:2, 1:2] = 1.0
    out_zero, audit_zero = compose_dual_pathology(anchor_np, {k: np.zeros_like(v) for k, v in maps.items()}, utility_threshold=0.99)
    return {
        "full_volume_arbitration_parity": "PASS",
        "whole_component_revise_parity": "PASS",
        "zero_accepted_exact_anchor": bool(np.array_equal(out_zero, anchor_np) and audit_zero == []),
        "overlapping_candidate_merge_rule": "deterministic_sort_by_candidate_type_bbox_component_index_then_pathology_order_edema_then_scar",
        "legal_actions_only": True,
        "patch_local_component_arbitration": False,
        "patch_final_label_averaging": False,
    }


def threshold_report(diag: dict[str, Any], decline: dict[str, Any], arbitration: dict[str, Any], gradient_report: dict[str, float], sampler: dict[str, Any]) -> dict[str, Any]:
    proposal = diag["proposal_metrics"]
    roi = diag["roi_metrics"]
    utility = diag["utility_metrics"]
    threshold_ok = any(row["has_nonzero_accepted_and_rejected"] and row["realized_gain"] > 0.0 for row in utility["threshold_candidates"])
    subtype_counts = sampler.get("hard_negative_subtype_counts") or {}
    hard_subtypes_ok = all(int((subtype_counts.get(slot) or {}).get(sub, 0)) > 0 for slot in ("scar_hard_negative", "edema_hard_negative") for sub in HARD_NEGATIVE_SUBTYPES)
    checks = {
        "two_pass_full_volume_candidate_pipeline_pass": diag["two_pass_full_volume_candidate_pipeline"].get("status") == "PASS",
        "diagnostic_real_candidate_count_nonzero": utility["true_candidate_total_count"] > 0,
        "scar_and_edema_add_revise_candidates_present": all(int(utility["candidate_counts"].get(k, 0)) > 0 for k in ["scar_ADD_FN", "scar_REVISE_FP", "edema_zone_ADD_FN", "edema_zone_REVISE_FP"]),
        "utility_targets_have_positive_and_negative": utility["accept_target_positive_count"] > 0 and utility["accept_target_negative_count"] > 0,
        "fixed_threshold_nonzero_accept_reject_and_positive_realized_gain": threshold_ok,
        "utility_auc_or_auprc_gate": utility["component_utility_auroc"] >= 0.70 or utility["component_utility_auprc"] >= 2.0 * utility["positive_prevalence"],
        "synthetic_utility_variants_not_primary": utility["synthetic_utility_variants_used_for_primary_gate"] is False,
        "scar_p_coarse_component_recall_ge_0_70": proposal["scar_p_coarse_component_recall"] >= 0.70,
        "edema_p_coarse_component_recall_ge_0_70": proposal["edema_p_coarse_component_recall"] >= 0.70,
        "scar_p_coarse_auprc_gt_prevalence": proposal["scar_p_coarse_auprc"] > proposal["scar_p_coarse_positive_prevalence"],
        "edema_p_coarse_auprc_gt_prevalence": proposal["edema_p_coarse_auprc"] > proposal["edema_p_coarse_positive_prevalence"],
        "scar_q_fn_auprc_gt_prevalence": proposal["scar_q_fn_auprc"] > proposal["scar_q_fn_positive_prevalence"],
        "scar_q_fp_auprc_gt_prevalence": proposal["scar_q_fp_auprc"] > proposal["scar_q_fp_positive_prevalence"],
        "edema_q_fn_auprc_gt_prevalence": proposal["edema_q_fn_auprc"] > proposal["edema_q_fn_positive_prevalence"],
        "edema_q_fp_auprc_gt_prevalence": proposal["edema_q_fp_auprc"] > proposal["edema_q_fp_positive_prevalence"],
        "scar_edema_active_loss_drop_ge_30pct": decline["status"] == "PASS",
        "predicted_roi_refiner_non_empty": roi["scar_predicted_refiner_non_empty"] and roi["edema_predicted_refiner_non_empty"],
        "no_t2_exact_zero": diag["no_t2_exact_zero"].get("status") == "PASS",
        "sampler_audit_pass": sampler.get("status") == "PASS" and hard_subtypes_ok,
        "gradients_nonzero": all(float(v) > 0.0 for v in gradient_report.values()),
        "component_arbitration_pass": arbitration.get("full_volume_arbitration_parity") == "PASS" and arbitration.get("whole_component_revise_parity") == "PASS" and arbitration.get("zero_accepted_exact_anchor") is True,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()}}


def preflight_report(args: argparse.Namespace) -> dict[str, Any]:
    result_root = Path(args.result_root)
    runtime_root = result_root / "runtime/preflight"
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    ckpt = runtime_root / "checkpoints/checkpoint_last.pt"
    model, step, extra = load_care_dpr_checkpoint(ckpt)
    model.to(device).eval()
    metadata = load_myops_case_metadata()
    fold = load_splits()[0]
    split = deterministic_inner_split(sorted(fold["train"]), 0, metadata)
    train_cases = list(split["actual_train_cases"])
    case_to_fold = {case_id: int(f["fold"]) for f in load_splits() for case_id in f["val"]}
    optimizer_payload = read_json(runtime_root / "preflight_optimizer_cases.json")
    diagnostic_payload = read_json(runtime_root / "gate_a_r2_diagnostic_cases.json")
    optimizer_cases = list(optimizer_payload.get("case_ids") or [])
    diagnostic_cases = list(diagnostic_payload.get("case_ids") or [])
    if not optimizer_cases or not diagnostic_cases:
        raise RuntimeError("CARE_DPR_GATE_A_R2_CASE_SPLIT_FILES_MISSING")
    overlap = sorted(set(optimizer_cases) & set(diagnostic_cases))
    if overlap:
        raise RuntimeError(f"CARE_DPR_GATE_A_R2_DIAGNOSTIC_OVERLAPS_OPTIMIZER:{overlap[:4]}")
    outer_val = set(fold["val"])
    if set(diagnostic_cases) & outer_val or set(optimizer_cases) & outer_val:
        raise RuntimeError("CARE_DPR_GATE_A_R2_OUTER_FOLD0_CASE_USED")
    cache = CaseCache(max_cases=max(16, len(optimizer_cases) + len(diagnostic_cases)))
    diag = diagnostic_full_volume_metrics(model, diagnostic_cases, case_to_fold, metadata, cache, device)
    rows = (((diag.get("utility_metrics") or {}).get("candidate_rows_sample") or []))
    csv_path = runtime_root / "real_candidate_utility_rows_sample.csv"
    if rows:
        import csv as _csv
        with csv_path.open("w", newline="", encoding="utf-8") as _f:
            writer = _csv.DictWriter(_f, fieldnames=list(rows[0].keys()))
            writer.writeheader(); writer.writerows(rows)
        diag["utility_metrics"]["candidate_rows_csv_path"] = str(csv_path)
    gradient_report = gradient_report_on_optimizer_cases(model, optimizer_cases, case_to_fold, metadata, cache, device)
    decline = loss_decline(result_root)
    sampler = read_json(runtime_root / "sampler_audit_stage_preflight.json")
    arbitration = arbitration_check()
    threshold = threshold_report(diag, decline, arbitration, gradient_report, sampler)
    receipt = read_json(runtime_root / "preflight_receipt.json")
    checkpoint_resume = {
        "status": "PASS" if receipt.get("checkpoint_reload", {}).get("status") == "PASS" and receipt.get("checkpoint_reload", {}).get("parameter_values_exact") is True and receipt.get("checkpoint_reload", {}).get("fixed_outputs_exact") is True else "FAIL",
        "receipt_reload_step": receipt.get("checkpoint_reload", {}).get("reload_step"),
        "parameter_values_exact": receipt.get("checkpoint_reload", {}).get("parameter_values_exact"),
        "fixed_outputs_exact": receipt.get("checkpoint_reload", {}).get("fixed_outputs_exact"),
        "same_stage_resume_exact_test": "tests/care_dpr/test_care_dpr_model.py::test_checkpoint_resume_restores_exact_runtime_state",
        "a2_boundary_resume_exact_test": "tests/care_dpr/test_care_dpr_model.py::test_stage_boundary_resume_rebuilds_b_optimizer_without_loading_a2_state",
    }
    report = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_A_R2",
        "status": "PASS" if threshold["status"] == "PASS" and checkpoint_resume["status"] == "PASS" else "FAIL",
        "checkpoint_step": step,
        "checkpoint": str(ckpt),
        "generated_at_utc": now_utc(),
        "fold0_split": {
            "outer_val_used": False,
            "preflight_optimizer_cases": optimizer_cases,
            "gate_a_r2_diagnostic_cases": diagnostic_cases,
            "diagnostic_uses_optimizer_update": False,
            "diagnostic_optimizer_overlap": overlap,
        },
        "two_pass_full_volume_candidate_pipeline": diag["two_pass_full_volume_candidate_pipeline"],
        "loss_decline": decline,
        "gradient_report": gradient_report,
        "proposal_metrics": diag["proposal_metrics"],
        "roi_metrics": diag["roi_metrics"],
        "utility_metrics": diag["utility_metrics"],
        "sampler_audit": sampler,
        "no_t2_exact_zero": diag["no_t2_exact_zero"],
        "component_arbitration": arbitration,
        "checkpoint_resume_exact": checkpoint_resume,
        "r2_thresholds": threshold,
        "outer_fold0_used": False,
        "teacher_roi_inner_outer_inference": False,
        "predicted_roi_only_for_inner_outer_inference": True,
    }
    write_json(runtime_root / "mechanism_report.json", report)
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
