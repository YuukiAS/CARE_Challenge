#!/usr/bin/env python3
"""CARE-DPR Gate B-R2 full-volume candidate calibration stages C1/C2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch
import torch.nn.functional as F
from torch.amp import autocast

from scripts.evaluation.evaluate_care_dpr import candidate_utility_target, dice_np
from scripts.evaluation.evaluate_care_dpr_gate_b import sha256_file, stable_json_sha256
from scripts.training.run_care_dpr import PATCH_SHAPE, source_hashes
from src.care_myocardium.data.care_dpr_dataset import CaseCache, deterministic_inner_split, distance_to_reliable_gt, load_splits
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_dpr_predictor import _anchor_margin_np, _center_of, _torch_map, aggregate_patch_outputs, build_candidate_rois
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.training.care_dpr_trainer import load_care_dpr_checkpoint, save_care_dpr_checkpoint

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
DEFAULT_RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
DEFAULT_R1_STEP2000 = DEFAULT_RESULT_ROOT / "runtime/formal_fold0_r1/checkpoints/checkpoint_step02000.pt"
PATHOLOGIES = ("scar", "edema_zone")
CANDIDATE_TYPES = ("ADD_FN", "REVISE_FP")
PROPOSAL_THRESHOLD_FOR_TRAINING = 0.50
UTILITY_THRESHOLD_CANDIDATES = (0.00, 0.02, 0.05, 0.10, 0.20)
PROPOSAL_THRESHOLD_CANDIDATES = {"scar": (0.30, 0.40, 0.50), "edema_zone": (0.20, 0.30, 0.40, 0.50)}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key); fields.append(key)
    fields = fields or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def set_trainability(model: torch.nn.Module, stage: str) -> None:
    for name, param in model.named_parameters():
        if stage == "C1":
            param.requires_grad = ".local_refiner." in name
        elif stage == "C2":
            param.requires_grad = ".component_utility." in name
        else:
            raise ValueError(stage)


def trainable_names(model: torch.nn.Module) -> list[str]:
    return [name for name, param in model.named_parameters() if param.requires_grad]


def optimizer_for(model: torch.nn.Module, lr: float, weight_decay: float) -> torch.optim.Optimizer:
    params = [param for param in model.parameters() if param.requires_grad]
    if not params:
        raise RuntimeError("CARE_DPR_R2_NO_TRAINABLE_PARAMETERS")
    return torch.optim.AdamW(params, lr=float(lr), weight_decay=float(weight_decay))


def batch_np_from_record(rec: dict[str, np.ndarray], *, t2_present: bool) -> dict[str, np.ndarray]:
    return {
        "images": rec["images"],
        "availability": rec["availability"],
        "anchor_logits": rec["anchor_logits"],
        "anchor_mask": rec["anchor_mask"],
        "uncertainty": rec["uncertainty"],
        "myocardium_support": rec["myocardium_support"],
        "edema_support": rec["edema_support"],
        "distance_to_myocardium": rec["distance_to_myocardium"],
        "t2_present": bool(t2_present),
    }


def gt_mask(rec: dict[str, np.ndarray], pathology: str) -> np.ndarray:
    labels = rec["labels"]
    if pathology == "scar":
        return labels == SCAR_CHANNEL
    return (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)


def support_mask(rec: dict[str, np.ndarray], pathology: str, t2_present: bool) -> np.ndarray:
    if pathology == "scar":
        return rec["myocardium_support"][0] > 0.1
    return (rec["edema_support"][0] > 0.1) & bool(t2_present)


def make_full_input(maps: dict[str, np.ndarray], batch_np: dict[str, np.ndarray], pathology: str, device: torch.device) -> tuple[torch.Tensor, Any, np.ndarray]:
    feature = torch.from_numpy(maps["shared_full_resolution_feature"][None].astype(np.float32)).to(device)
    if pathology == "scar":
        branch_prefix = "scar"
        extras = [
            batch_np["images"][0],
            _anchor_margin_np(batch_np["anchor_logits"], pathology="scar"),
            maps["scar_p_coarse"],
            maps["scar_q_fn"],
            maps["scar_q_fp"],
            batch_np["uncertainty"][0],
            batch_np["myocardium_support"][0],
            batch_np["distance_to_myocardium"][0],
        ]
        support = batch_np["myocardium_support"][0]
    else:
        branch_prefix = "edema"
        extras = [
            batch_np["images"][1],
            batch_np["images"][0],
            _anchor_margin_np(batch_np["anchor_logits"], pathology="edema_zone"),
            maps["edema_p_coarse"],
            maps["edema_q_fn"],
            maps["edema_q_fp"],
            batch_np["uncertainty"][0],
            batch_np["edema_support"][0],
            batch_np["distance_to_myocardium"][0],
        ]
        support = batch_np["edema_support"][0]
    full_input = torch.cat([feature, torch.from_numpy(np.stack(extras, axis=0)[None].astype(np.float32)).to(device)], dim=1)
    return full_input, branch_prefix, support


class FullVolumeCandidateCache:
    def __init__(self, *, max_cases: int) -> None:
        self.max_cases = int(max_cases)
        self.items: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def clear(self) -> None:
        self.items.clear()

    def get(self, *, case_id: str, model: torch.nn.Module, case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, device: torch.device) -> dict[str, Any]:
        if case_id in self.items:
            self.items.move_to_end(case_id)
            return self.items[case_id]
        meta = metadata[case_id]
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        batch_np = batch_np_from_record(rec, t2_present=bool(meta.t2_present))
        maps = aggregate_patch_outputs(model, batch_np, patch_shape=PATCH_SHAPE, overlap=0.5, device=device)
        anchor = rec["anchor_mask"].astype(np.uint8, copy=False)
        candidates: dict[tuple[str, str], list[tuple[Any, np.ndarray, np.ndarray, np.ndarray]]] = {}
        for pathology in PATHOLOGIES:
            for threshold in sorted(set(PROPOSAL_THRESHOLD_CANDIDATES[pathology] + (PROPOSAL_THRESHOLD_FOR_TRAINING,))):
                cands = build_candidate_rois(anchor, maps, pathology=pathology, threshold=float(threshold), t2_present=bool(meta.t2_present), margin=3)
                for c in cands:
                    candidates.setdefault((pathology, c[0].candidate_type), []).append(c)
        payload = {"record": rec, "batch_np": batch_np, "maps": maps, "candidates": candidates, "t2_present": bool(meta.t2_present)}
        self.items[case_id] = payload
        while len(self.items) > self.max_cases:
            self.items.popitem(last=False)
        return payload


def c2_target_info(model: torch.nn.Module, item: dict[str, Any], cand_tuple: tuple[Any, np.ndarray, np.ndarray, np.ndarray], *, device: torch.device) -> dict[str, Any]:
    cand, anchor_local, seed, roi = cand_tuple
    rec = item["record"]
    batch_np = item["batch_np"]
    maps = item["maps"]
    full_input, _, _ = make_full_input(maps, batch_np, cand.pathology, device)
    branch = model.scar_branch if cand.pathology == "scar" else model.edema_branch
    with torch.no_grad():
        refined_logit, _ = branch.local_refiner.forward_at_center(full_input, _center_of(seed | anchor_local))
        refined_prob_np = torch.sigmoid(refined_logit)[0, 0].detach().cpu().numpy() * roi.astype(np.float32)
        refined_mask = refined_prob_np >= 0.5
    dist = distance_to_reliable_gt(rec, pathology=cand.pathology, t2_present=bool(item["t2_present"]))[0]
    accept_target, utility_target, reason = candidate_utility_target(anchor_local, refined_mask, gt_mask(rec, cand.pathology), dist, cand.candidate_type, roi)
    return {
        "accept_target": int(accept_target),
        "utility_target": float(utility_target),
        "target_reason": reason,
    }


def choose_case_candidate(*, model: torch.nn.Module, train_cases: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, fv_cache: FullVolumeCandidateCache, rng: random.Random, pathology: str, candidate_type: str, device: torch.device, desired_utility_positive: bool | None = None) -> tuple[str, dict[str, Any], tuple[Any, np.ndarray, np.ndarray, np.ndarray], str, dict[str, Any] | None]:
    requested_type = candidate_type
    candidate_types = [candidate_type] + [c for c in CANDIDATE_TYPES if c != candidate_type]
    sign_mismatch: tuple[str, dict[str, Any], tuple[Any, np.ndarray, np.ndarray, np.ndarray], str, dict[str, Any]] | None = None
    for ctype in candidate_types:
        shuffled = list(train_cases)
        rng.shuffle(shuffled)
        for case_id in shuffled[: min(len(shuffled), 32)]:
            if pathology == "edema_zone" and not bool(metadata[case_id].t2_present):
                continue
            item = fv_cache.get(case_id=case_id, model=model, case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device)
            pool = item["candidates"].get((pathology, ctype), [])
            if not pool:
                continue
            candidates = list(pool)
            rng.shuffle(candidates)
            for cand_tuple in candidates[: min(len(candidates), 32)]:
                fallback = "" if ctype == requested_type else f"candidate_type_fallback:{requested_type}->{ctype}"
                target_info = None
                if desired_utility_positive is not None:
                    target_info = c2_target_info(model, item, cand_tuple, device=device)
                    is_positive = float(target_info["utility_target"]) > 0.0
                    if is_positive != bool(desired_utility_positive):
                        if sign_mismatch is None:
                            sign_mismatch = (case_id, item, cand_tuple, fallback, target_info)
                        continue
                return case_id, item, cand_tuple, fallback, target_info
    if sign_mismatch is not None:
        case_id, item, cand_tuple, fallback, target_info = sign_mismatch
        sign = "positive" if desired_utility_positive else "negative"
        reason = f"utility_target_sign_fallback:{sign}"
        return case_id, item, cand_tuple, ";".join([x for x in (fallback, reason) if x]), target_info
    raise RuntimeError(f"CARE_DPR_R2_NO_FULL_VOLUME_CANDIDATE:{pathology}:{candidate_type}")


def dice_loss_from_prob(prob: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    p = prob * mask
    t = target * mask
    inter = (p * t).sum()
    denom = p.sum() + t.sum()
    return 1.0 - (2.0 * inter + 1.0) / (denom + 1.0)


def c1_loss(model: torch.nn.Module, item: dict[str, Any], cand_tuple: tuple[Any, np.ndarray, np.ndarray, np.ndarray], *, device: torch.device) -> tuple[torch.Tensor, dict[str, Any]]:
    cand, anchor_local, seed, roi = cand_tuple
    rec = item["record"]
    batch_np = item["batch_np"]
    maps = item["maps"]
    full_input, pfx, _ = make_full_input(maps, batch_np, cand.pathology, device)
    branch = model.scar_branch if cand.pathology == "scar" else model.edema_branch
    refined_logit, _ = branch.local_refiner.forward_at_center(full_input, _center_of(seed | anchor_local))
    target_np = gt_mask(rec, cand.pathology).astype(np.float32)
    train_mask_np = (roi & support_mask(rec, cand.pathology, bool(item["t2_present"]))).astype(np.float32)
    target = _torch_map(target_np, device)
    train_mask = _torch_map(train_mask_np, device)
    if float(train_mask.sum().detach().cpu()) <= 0.0:
        train_mask = _torch_map(roi.astype(np.float32), device)
    bce = F.binary_cross_entropy_with_logits(refined_logit, target, reduction="none")
    prob = torch.sigmoid(refined_logit)
    loss = (bce * train_mask).sum() / train_mask.sum().clamp_min(1.0) + dice_loss_from_prob(prob, target, train_mask)
    refined_mask = (prob.detach().cpu().numpy()[0, 0] >= 0.5) & roi
    coverage = float((gt_mask(rec, cand.pathology) & roi).sum() / max(int(gt_mask(rec, cand.pathology).sum()), 1))
    return loss, {"p_refined_positive_voxels": int(refined_mask.sum()), "roi_gt_coverage": coverage, "branch_prefix": pfx}


def c2_loss(model: torch.nn.Module, item: dict[str, Any], cand_tuple: tuple[Any, np.ndarray, np.ndarray, np.ndarray], *, device: torch.device) -> tuple[torch.Tensor, dict[str, Any]]:
    cand, anchor_local, seed, roi = cand_tuple
    rec = item["record"]
    batch_np = item["batch_np"]
    maps = item["maps"]
    full_input, pfx, support_np = make_full_input(maps, batch_np, cand.pathology, device)
    branch = model.scar_branch if cand.pathology == "scar" else model.edema_branch
    with torch.no_grad():
        refined_logit, _ = branch.local_refiner.forward_at_center(full_input, _center_of(seed | anchor_local))
        refined_prob_np = torch.sigmoid(refined_logit)[0, 0].detach().cpu().numpy() * roi.astype(np.float32)
        refined_mask = refined_prob_np >= 0.5
    dist = distance_to_reliable_gt(rec, pathology=cand.pathology, t2_present=bool(item["t2_present"]))[0]
    accept_target, utility_target, reason = candidate_utility_target(anchor_local, refined_mask, gt_mask(rec, cand.pathology), dist, cand.candidate_type, roi)
    feature = torch.from_numpy(maps["shared_full_resolution_feature"][None].astype(np.float32)).to(device)
    component_mask = (seed | anchor_local | refined_mask | roi).astype(np.float32)
    scored = branch.component_utility.score_candidate(
        feature,
        p_coarse=_torch_map(maps[f"{pfx}_p_coarse"], device),
        q_fn=_torch_map(maps[f"{pfx}_q_fn"], device),
        q_fp=_torch_map(maps[f"{pfx}_q_fp"], device),
        p_refined=_torch_map(refined_prob_np, device),
        anchor_margin=_torch_map(_anchor_margin_np(batch_np["anchor_logits"], pathology=cand.pathology), device),
        uncertainty=_torch_map(batch_np["uncertainty"][0], device),
        distance_to_support=_torch_map(batch_np["distance_to_myocardium"][0], device),
        support=_torch_map(support_np, device),
        component_mask=_torch_map(component_mask, device),
        candidate_type=cand.candidate_type,
        truncation_flag=torch.tensor([[float(cand.truncation_flag)]], device=device),
    )
    target = torch.tensor([[float(utility_target)]], device=device, dtype=scored["utility_regression"].dtype)
    loss = F.smooth_l1_loss(scored["utility_regression"], target)
    return loss, {"utility_target": float(utility_target), "accept_target": int(accept_target), "target_reason": reason, "predicted_signed_utility": float(scored["utility_regression"].detach().cpu()[0, 0])}


def run_stage(*, model: torch.nn.Module, stage: str, optimizer: torch.optim.Optimizer, train_cases: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, fv_cache: FullVolumeCandidateCache, rng: random.Random, device: torch.device, runtime_root: Path, start_step: int, steps: int, checkpoint_every: int, lr: float, weight_decay: float, amp_dtype: str) -> tuple[int, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    start_time = time.time()
    total_step = int(start_step)
    model.train()
    c2_sign_cursor = {p: 0 for p in PATHOLOGIES}
    for local_step in range(1, int(steps) + 1):
        pathology = "scar" if (local_step - 1) % 2 == 0 else "edema_zone"
        requested_type = CANDIDATE_TYPES[((local_step - 1) // 2) % len(CANDIDATE_TYPES)]
        desired_positive = None
        if stage == "C2":
            desired_positive = (c2_sign_cursor[pathology] % 2) == 0
            c2_sign_cursor[pathology] += 1
        case_id, item, cand_tuple, fallback, precomputed_target = choose_case_candidate(model=model, train_cases=train_cases, case_to_fold=case_to_fold, metadata=metadata, cache=cache, fv_cache=fv_cache, rng=rng, pathology=pathology, candidate_type=requested_type, device=device, desired_utility_positive=desired_positive)
        cand = cand_tuple[0]
        optimizer.zero_grad(set_to_none=True)
        with autocast(device_type="cuda", dtype=torch.bfloat16, enabled=(device.type == "cuda" and amp_dtype == "bfloat16")):
            loss, metrics = c1_loss(model, item, cand_tuple, device=device) if stage == "C1" else c2_loss(model, item, cand_tuple, device=device)
        if not torch.isfinite(loss):
            raise RuntimeError(f"CARE_DPR_R2_NONFINITE_LOSS:{stage}:{local_step}")
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
        optimizer.step()
        total_step += 1
        row = {
            "stage": stage,
            "local_step": local_step,
            "total_step": total_step,
            "case_id": case_id,
            "pathology": cand.pathology,
            "requested_pathology": pathology,
            "candidate_type": cand.candidate_type,
            "requested_candidate_type": requested_type,
            "fallback_reason": fallback,
            "loss": float(loss.detach().cpu()),
            "grad_norm": float(grad_norm.detach().cpu()),
            "candidate_voxels": int(cand.voxel_count),
            "component_truncation_flag": bool(cand.truncation_flag),
            "elapsed_seconds": round(time.time() - start_time, 1),
            **metrics,
        }
        if desired_positive is not None:
            actual_positive = float(metrics.get("utility_target", 0.0)) > 0.0
            row.update(
                {
                    "requested_utility_target_sign": "positive" if desired_positive else "negative",
                    "matched_requested_utility_target_sign": bool(actual_positive == desired_positive),
                    "precomputed_utility_target": None if precomputed_target is None else float(precomputed_target["utility_target"]),
                }
            )
        rows.append(row)
        if local_step == 1 or local_step % 25 == 0 or local_step == steps:
            write_csv(runtime_root / f"stage_{stage.lower()}_training_curve.csv", rows)
            print(json.dumps(row, ensure_ascii=False), flush=True)
        if local_step % int(checkpoint_every) == 0 or local_step == steps:
            ckpt = runtime_root / "checkpoints" / f"checkpoint_step{total_step:05d}.pt"
            save_care_dpr_checkpoint(
                ckpt,
                model,
                optimizer,
                total_step,
                {"stage": stage, "gate": "DPR_GATE_B_R2", "outer_val_used_for_selection": False, "candidate_source": "model_pass1_full_volume"},
                local_rng=rng,
                stage=stage,
                local_step=local_step,
                sampler_slot_cursor=0,
                hard_negative_subtype_cursor={"scar": 0, "edema_zone": 0},
                teacher_roi_schedule_cursor=0,
                resolved_training_contract_hash="DPR_GATE_B_R2_C1_C2",
            )
    return total_step, rows


def summarize_stage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = defaultdict(int)
    fallbacks = 0
    roi_cov = defaultdict(list)
    utility_targets = defaultdict(lambda: {"positive": 0, "negative": 0})
    utility_sign_requested = defaultdict(lambda: {"positive": 0, "negative": 0})
    utility_sign_matched = defaultdict(int)
    utility_sign_fallbacks = 0
    for row in rows:
        counts[f"{row.get('pathology')}_{row.get('candidate_type')}"] += 1
        fallback_reason = str(row.get("fallback_reason") or "")
        if fallback_reason:
            fallbacks += 1
        if "utility_target_sign_fallback" in fallback_reason:
            utility_sign_fallbacks += 1
        if "roi_gt_coverage" in row:
            roi_cov[str(row.get("pathology"))].append(float(row["roi_gt_coverage"]))
        if "utility_target" in row:
            key = str(row.get("pathology"))
            if float(row["utility_target"]) > 0:
                utility_targets[key]["positive"] += 1
            else:
                utility_targets[key]["negative"] += 1
        if "requested_utility_target_sign" in row:
            key = str(row.get("pathology"))
            sign = str(row.get("requested_utility_target_sign"))
            utility_sign_requested[key][sign] += 1
            if bool(row.get("matched_requested_utility_target_sign")):
                utility_sign_matched[key] += 1
    return {
        "sample_count": len(rows),
        "candidate_counts": dict(counts),
        "fallback_count": fallbacks,
        "pathology_fraction": {p: sum(v for k, v in counts.items() if k.startswith(p + "_")) / max(len(rows), 1) for p in PATHOLOGIES},
        "add_revise_counts": {ctype: sum(v for k, v in counts.items() if k.endswith("_" + ctype)) for ctype in CANDIDATE_TYPES},
        "roi_gt_coverage_mean": {k: float(np.mean(v)) if v else 0.0 for k, v in roi_cov.items()},
        "utility_target_balance": dict(utility_targets),
        "utility_target_sign_requested": dict(utility_sign_requested),
        "utility_target_sign_match_count": dict(utility_sign_matched),
        "utility_target_sign_fallback_count": utility_sign_fallbacks,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    result_root = Path(args.result_root)
    runtime_root = result_root / "runtime" / args.runtime_name
    runtime_root.mkdir(parents=True, exist_ok=True)
    metadata = load_myops_case_metadata(REPO_ROOT)
    splits = load_splits()
    fold = next(row for row in splits if int(row["fold"]) == int(args.fold))
    split_payload = deterministic_inner_split(sorted(fold["train"]), int(args.fold), metadata)
    inner12 = set(split_payload["complete_inner_select_cases"])
    train_cases = [c for c in split_payload["actual_train_cases"] if c not in inner12]
    if not train_cases:
        raise RuntimeError("CARE_DPR_R2_EMPTY_C1C2_TRAIN_CASES")
    case_to_fold = {case_id: int(row["fold"]) for row in splits for case_id in row["val"]}
    cache = CaseCache(max_cases=int(args.case_cache))
    model, start_step, extra = load_care_dpr_checkpoint(Path(args.start_checkpoint))
    model.to(device)
    contract = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_B_R2",
        "fold": int(args.fold),
        "seed": int(args.seed),
        "start_checkpoint": str(args.start_checkpoint),
        "start_checkpoint_sha256": sha256_file(Path(args.start_checkpoint)),
        "start_checkpoint_step": int(start_step),
        "stage_c1_steps": int(args.stage_c1_steps),
        "stage_c2_steps": int(args.stage_c2_steps),
        "stage_c1_freeze": "stems_encoder_proposal_heads_utility_heads_frozen; local_refiners_only_trainable",
        "stage_c2_freeze": "proposal_and_refiner_frozen; component_utility_heads_only_trainable",
        "candidate_source": "model_self_pass1_full_volume_candidates",
        "actual_train_excludes_inner12": True,
        "train_case_count": len(train_cases),
        "inner12_sha256": stable_json_sha256(sorted(inner12)),
        "train_cases_sha256": stable_json_sha256(sorted(train_cases)),
        "proposal_threshold_candidates": PROPOSAL_THRESHOLD_CANDIDATES,
        "utility_threshold_candidates": list(UTILITY_THRESHOLD_CANDIDATES),
        "final_arbitration_score": "predicted_signed_utility",
        "accept_probability_threshold_forbidden": True,
        "utility_regression_min_forbidden": True,
        "two_pass_full_volume_contract": {"overlap": 0.5, "gaussian_blending": True, "pass1_candidate_construction": True, "patch_final_label_averaging": False},
        "source_hashes": source_hashes(),
    }
    write_json(runtime_root / "gate_b_r2_resolved_contract.json", contract)
    write_json(runtime_root / "gate_b_r2_case_split.json", {"train_cases": sorted(train_cases), "excluded_inner12": sorted(inner12), "outer_val_cases": sorted(fold["val"]), "fold": int(args.fold)})
    rng = random.Random(int(args.seed) + int(args.fold) * 1000 + 2)

    set_trainability(model, "C1")
    c1_trainable = trainable_names(model)
    opt = optimizer_for(model, args.lr_c1, args.weight_decay)
    fv_cache = FullVolumeCandidateCache(max_cases=int(args.full_volume_cache_cases))
    total_step, c1_rows = run_stage(model=model, stage="C1", optimizer=opt, train_cases=train_cases, case_to_fold=case_to_fold, metadata=metadata, cache=cache, fv_cache=fv_cache, rng=rng, device=device, runtime_root=runtime_root, start_step=start_step, steps=int(args.stage_c1_steps), checkpoint_every=int(args.checkpoint_every), lr=args.lr_c1, weight_decay=args.weight_decay, amp_dtype=args.amp_dtype)

    fv_cache.clear()
    set_trainability(model, "C2")
    c2_trainable = trainable_names(model)
    opt = optimizer_for(model, args.lr_c2, args.weight_decay)
    total_step, c2_rows = run_stage(model=model, stage="C2", optimizer=opt, train_cases=train_cases, case_to_fold=case_to_fold, metadata=metadata, cache=cache, fv_cache=fv_cache, rng=rng, device=device, runtime_root=runtime_root, start_step=total_step, steps=int(args.stage_c2_steps), checkpoint_every=int(args.checkpoint_every), lr=args.lr_c2, weight_decay=args.weight_decay, amp_dtype=args.amp_dtype)

    last = runtime_root / "checkpoints" / "checkpoint_last.pt"
    save_care_dpr_checkpoint(last, model, opt, total_step, {"gate": "DPR_GATE_B_R2", "stage": "C2", "candidate_source": "model_pass1_full_volume"}, local_rng=rng, stage="C2", local_step=int(args.stage_c2_steps), resolved_training_contract_hash=stable_json_sha256(contract))
    receipt = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_B_R2_C1_C2",
        "status": "PASS",
        "fold": int(args.fold),
        "device": str(device),
        "start_step": int(start_step),
        "terminal_step": int(total_step),
        "stage_c1_optimizer_steps": int(args.stage_c1_steps),
        "stage_c2_optimizer_steps": int(args.stage_c2_steps),
        "stage_c1_trainable_parameter_names": c1_trainable,
        "stage_c2_trainable_parameter_names": c2_trainable,
        "c1_summary": summarize_stage(c1_rows),
        "c2_summary": summarize_stage(c2_rows),
        "no_t2_edema_candidates_excluded": True,
        "full_volume_candidate_source": "model_self_pass1_full_volume_candidates",
        "final_arbitration_score": "predicted_signed_utility",
        "accept_probability_threshold_used": False,
        "utility_regression_min_used": False,
        "checkpoint_every": int(args.checkpoint_every),
        "last_checkpoint": str(last),
        "last_checkpoint_sha256": sha256_file(last),
        "completed_at_utc": now_utc(),
    }
    write_json(runtime_root / "gate_b_r2_c1c2_receipt.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--result-root", default=str(DEFAULT_RESULT_ROOT))
    parser.add_argument("--runtime-name", default="formal_fold0_r2")
    parser.add_argument("--start-checkpoint", default=str(DEFAULT_R1_STEP2000))
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--stage-c1-steps", type=int, default=1000)
    parser.add_argument("--stage-c2-steps", type=int, default=1000)
    parser.add_argument("--checkpoint-every", type=int, default=250)
    parser.add_argument("--lr-c1", type=float, default=5e-5)
    parser.add_argument("--lr-c2", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--amp-dtype", default="bfloat16", choices=["bfloat16", "none"])
    parser.add_argument("--case-cache", type=int, default=12)
    parser.add_argument("--full-volume-cache-cases", type=int, default=3)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
