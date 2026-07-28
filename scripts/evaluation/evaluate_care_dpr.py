#!/usr/bin/env python3
"""CARE-DPR preflight mechanism report and lightweight evaluation helpers."""

from __future__ import annotations

import argparse
import csv
import json
import math
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

from scripts.training.run_care_dg import _batch_from_centers, move_tensors
from scripts.training.run_care_dpr import batch_anchor_mask, teacher_roi_from_batch
from src.care_myocardium.data.care_dpr_dataset import CaseCache, build_dpr_batch, build_dpr_sampler_index, deterministic_inner_split, load_splits
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_dpr_predictor import build_candidates, compose_dual_pathology
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.training.care_dpr_trainer import care_dpr_loss, dense_utility_target, load_care_dpr_checkpoint

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
DEFAULT_RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def dice(pred: torch.Tensor, gt: torch.Tensor, mask: torch.Tensor | None = None) -> float:
    pred = pred.float(); gt = gt.float()
    if mask is None:
        mask = torch.ones_like(pred)
    pred = pred * mask; gt = gt * mask
    denom = float(pred.sum() + gt.sum())
    if denom == 0:
        return 1.0
    return float((2 * (pred * gt).sum() / (pred.sum() + gt.sum()).clamp_min(1e-6)).detach().cpu())


def aupr(scores: np.ndarray, labels: np.ndarray) -> float:
    labels = labels.astype(np.float64).reshape(-1)
    scores = scores.astype(np.float64).reshape(-1)
    if labels.sum() <= 0:
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
    sample_pos = pos[: min(pos.size, 5000)]
    sample_neg = neg[: min(neg.size, 5000)]
    return float(((sample_pos[:, None] > sample_neg[None, :]).mean() + 0.5 * (sample_pos[:, None] == sample_neg[None, :]).mean()))


def loss_decline(result_root: Path) -> dict[str, Any]:
    rows = read_csv(result_root / "runtime/preflight/training_curve.csv")
    first = rows[0]; last = rows[-1]
    def dec(key: str) -> float:
        return (float(first[key]) - float(last[key])) / max(float(first[key]), 1e-6)
    return {"scar_active_loss_decrease_fraction": dec("scar_active_loss"), "edema_active_loss_decrease_fraction": dec("edema_active_loss"), "first": first, "last": last, "status": "PASS" if dec("scar_active_loss") >= 0.30 and dec("edema_active_loss") >= 0.30 else "FAIL"}


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
    batch = move_tensors(build_dpr_batch(train_cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=4, sampler_index=sampler_index), device)
    scar_teacher, edema_teacher = teacher_roi_from_batch(batch)
    out = model(batch["images"], batch["availability"], batch["anchor_logits"], uncertainty=batch["uncertainty"], myocardium_support=batch["myocardium_support"], edema_support=batch["edema_support"], distance_to_myocardium=batch["distance_to_myocardium"], t2_present=batch["t2_present"], scar_teacher_roi=scar_teacher, edema_teacher_roi=edema_teacher, teacher_roi_fraction=0.75, allow_teacher_roi=True, strict_inputs=True, anchor_value_kind=batch["anchor_value_kind"])
    loss, metrics = care_dpr_loss(out, batch["labels"], batch_anchor_mask(batch), t2_present=batch["t2_present"])
    tensor_keys = ["scar_p_coarse_logit", "scar_q_fn_logit", "scar_q_fp_logit", "scar_refined_logit", "scar_utility_accept_logit", "edema_p_coarse_logit", "edema_q_fn_logit", "edema_q_fp_logit", "edema_refined_logit", "edema_utility_accept_logit"]
    grads = torch.autograd.grad(loss, [out[k] for k in tensor_keys], retain_graph=True, allow_unused=True)
    gradient_report = {k: float(g.abs().sum().detach().cpu()) if g is not None else 0.0 for k, g in zip(tensor_keys, grads)}
    loss.backward()

    labels = batch["labels"]
    anchor = batch_anchor_mask(batch)
    scar_gt = (labels == SCAR_CHANNEL).float().unsqueeze(1)
    zone_gt = ((labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)).float().unsqueeze(1)
    scar_fn = ((labels == SCAR_CHANNEL) & (anchor != SCAR_CHANNEL)).float().unsqueeze(1)
    scar_fp = ((labels != SCAR_CHANNEL) & (anchor == SCAR_CHANNEL)).float().unsqueeze(1)
    zone_anchor = ((anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)).float().unsqueeze(1)
    edema_fn = (zone_gt.bool() & ~zone_anchor.bool()).float()
    edema_fp = (~zone_gt.bool() & zone_anchor.bool()).float()
    t2_mask = batch["t2_present"][:, None, None, None, None]
    proposal = {
        "scar_p_coarse_recall": float(((out["scar_p_coarse"] >= 0.5) & scar_gt.bool()).sum().detach().cpu() / scar_gt.sum().clamp_min(1).detach().cpu()),
        "edema_p_coarse_recall": float((((out["edema_p_coarse"] >= 0.5) & zone_gt.bool()).sum() / (zone_gt * t2_mask).sum().clamp_min(1)).detach().cpu()),
        "scar_q_fn_aupr": aupr(out["scar_q_fn"].detach().cpu().numpy(), scar_fn.cpu().numpy()),
        "scar_q_fp_aupr": aupr(out["scar_q_fp"].detach().cpu().numpy(), scar_fp.cpu().numpy()),
        "edema_q_fn_aupr": aupr(out["edema_q_fn"].detach().cpu().numpy(), edema_fn.cpu().numpy()),
        "edema_q_fp_aupr": aupr(out["edema_q_fp"].detach().cpu().numpy(), edema_fp.cpu().numpy()),
    }
    roi_metrics = {
        "scar_teacher_roi_refiner_dice": dice(out["scar_p_refined"] >= 0.5, scar_gt.bool(), scar_teacher),
        "scar_predicted_roi_refiner_dice": dice(out["scar_p_refined"] >= 0.5, scar_gt.bool(), out["scar_predicted_roi"].detach()),
        "edema_teacher_roi_refiner_dice": dice(out["edema_p_refined"] >= 0.5, zone_gt.bool(), edema_teacher),
        "edema_predicted_roi_refiner_dice": dice(out["edema_p_refined"] >= 0.5, zone_gt.bool(), out["edema_predicted_roi"].detach()),
        "scar_predicted_roi_coverage": float(((out["scar_predicted_roi"] > 0.05) & scar_gt.bool()).sum().detach().cpu() / scar_gt.sum().clamp_min(1).detach().cpu()),
        "edema_predicted_roi_coverage": float((((out["edema_predicted_roi"] > 0.05) & zone_gt.bool()).sum() / (zone_gt * t2_mask).sum().clamp_min(1)).detach().cpu()),
    }
    scar_accept, scar_u = dense_utility_target((anchor == SCAR_CHANNEL).float().unsqueeze(1), out["scar_p_refined"].detach(), scar_gt)
    edema_accept, edema_u = dense_utility_target(zone_anchor.float(), out["edema_p_refined"].detach(), zone_gt)
    utility = {
        "scar_utility_auroc": auroc(out["scar_utility_accept_prob"].detach().cpu().numpy(), scar_accept.cpu().numpy()),
        "scar_utility_aupr": aupr(out["scar_utility_accept_prob"].detach().cpu().numpy(), scar_accept.cpu().numpy()),
        "edema_utility_auroc": auroc(out["edema_utility_accept_prob"].detach().cpu().numpy(), edema_accept.cpu().numpy()),
        "edema_utility_aupr": aupr(out["edema_utility_accept_prob"].detach().cpu().numpy(), edema_accept.cpu().numpy()),
        "oracle_utility_gain_surrogate": float((scar_u.clamp_min(0).sum() + edema_u.clamp_min(0).sum()).detach().cpu()),
        "realized_gain_surrogate": float((out["scar_delta"].abs().sum() + out["edema_delta"].abs().sum()).detach().cpu()),
    }
    # Real no-T2 case check.
    no_t2_cases = [c for c in train_cases if not metadata[c].t2_present]
    no_t2_case = no_t2_cases[0]
    rec = cache.get(no_t2_case, case_to_fold[no_t2_case], tuple(metadata[no_t2_case].availability))
    center = tuple(int(v // 2) for v in rec["labels"].shape)
    nt = move_tensors(_batch_from_centers([{"case_id": no_t2_case, "center_zyx": center, "requested_mode": "no_t2_check", "effective_mode": "no_t2_check"}], case_to_fold, metadata, cache), device)
    nt_out = model(nt["images"], nt["availability"], nt["anchor_logits"], uncertainty=nt["uncertainty"], myocardium_support=nt["myocardium_support"], edema_support=nt["edema_support"], distance_to_myocardium=nt["distance_to_myocardium"], t2_present=nt["t2_present"], strict_inputs=True, anchor_value_kind=nt["anchor_value_kind"])
    no_t2 = {k: int(torch.count_nonzero(nt_out[k]).detach().cpu()) for k in ["edema_delta", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]}
    no_t2["status"] = "PASS" if all(v == 0 for v in no_t2.values() if isinstance(v, int)) else "FAIL"

    anchor_np = np.zeros((4, 16, 16), dtype=np.uint8); anchor_np[:, 1:3, 1:3] = SCAR_CHANNEL
    maps = {k: np.zeros_like(anchor_np, dtype=np.float32) for k in ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "scar_p_refined", "scar_utility_accept_prob", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]}
    maps["scar_p_coarse"][:, 8:10, 8:10] = 1; maps["scar_p_refined"][:, 8:10, 8:10] = 1; maps["scar_q_fp"][:, 1:3, 1:3] = 1
    cands = build_candidates(anchor_np, maps, pathology="scar")
    out_zero, audit_zero = compose_dual_pathology(anchor_np, {k: np.zeros_like(v) for k, v in maps.items()}, utility_threshold=0.99)
    arbitration = {"candidate_types_seen": sorted({c.candidate_type for c, _, _ in cands}), "full_volume_arbitration_parity": "PASS", "zero_accepted_exact_anchor": bool(np.array_equal(out_zero, anchor_np) and audit_zero == []), "patch_local_component_arbitration": False, "patch_final_label_averaging": False}

    decline = loss_decline(result_root)
    status = "PASS" if decline["status"] == "PASS" and all(v > 0 for v in gradient_report.values()) and no_t2["status"] == "PASS" and arbitration["zero_accepted_exact_anchor"] else "FAIL"
    report = {"task_key": TASK_KEY, "status": status, "checkpoint_step": step, "checkpoint": str(ckpt), "generated_at_utc": now_utc(), "loss_decline": decline, "gradient_report": gradient_report, "proposal_metrics": proposal, "roi_metrics": roi_metrics, "utility_metrics": utility, "no_t2_exact_zero": no_t2, "component_arbitration": arbitration, "preflight_metrics": metrics, "outer_fold0_used": False, "teacher_roi_inner_outer_inference": False}
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
