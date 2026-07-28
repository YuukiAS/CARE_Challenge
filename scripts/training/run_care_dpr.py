#!/usr/bin/env python3
"""CARE-DPR training/preflight entrypoint."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch
from torch.amp import autocast

from scripts.training.run_care_dg import move_tensors, stable_json_sha256
from src.care_myocardium.data.care_dpr_dataset import HARD_NEGATIVE_SUBTYPES, DPR_SAMPLER_PATTERN, CaseCache, build_dpr_batch, build_dpr_sampler_index, deterministic_inner_split, load_splits
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.models.care_dpr import build_care_dpr
from src.care_myocardium.training.care_dpr_trainer import care_dpr_loss, initialize_from_care_dg, load_care_dpr_checkpoint, save_care_dpr_checkpoint

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
DEFAULT_RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
DEFAULT_CARE_DG_INIT = REPO_ROOT / "results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/checkpoints/checkpoint_step04000.pt"
PATCH_SHAPE = (8, 128, 128)
REPRESENTATION_PREFIXES = ("lge_stem", "t2_stem", "c0_stem", "anchor_context", "encoder")
FROZEN_STAGE_B_PREFIXES = REPRESENTATION_PREFIXES + ("scar_branch.proposal_head", "edema_branch.proposal_head")
FORMAL_GATE_TOKEN = "APPROVE_DPR_GATE_A_R2"
SUPERSEDED_GATE_TOKENS = ("APPROVE_DPR_GATE_A", "APPROVE_DPR_GATE_A_R1")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: set[str] = set(); fieldnames = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key); fieldnames.append(key)
        fieldnames = fieldnames or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()



def source_hashes() -> dict[str, str]:
    files = [
        "src/care_myocardium/models/care_dpr.py",
        "src/care_myocardium/training/care_dpr_trainer.py",
        "src/care_myocardium/inference/care_dpr_predictor.py",
        "src/care_myocardium/data/care_dpr_dataset.py",
        "scripts/training/run_care_dpr.py",
        "scripts/evaluation/evaluate_care_dpr.py",
        "scripts/evaluation/validate_care_dpr_packet.py",
        "scripts/evaluation/validate_care_dpr_gate_a_r2_consistency.py",
        "tests/care_dpr/test_care_dpr_model.py",
    ]
    return {rel: sha256_file(REPO_ROOT / rel) for rel in files if (REPO_ROOT / rel).is_file()}


def choose_gate_a_r2_case_sets(train_cases: list[str]) -> tuple[list[str], list[str]]:
    ranked = sorted(train_cases, key=lambda c: hashlib.sha256(f"gate-a-r2:{c}:optimizer".encode()).hexdigest())
    diagnostic_ranked = sorted(train_cases, key=lambda c: hashlib.sha256(f"gate-a-r2:{c}:diagnostic".encode()).hexdigest())
    optimizer_cases = sorted(ranked[: max(16, min(32, len(ranked) // 4))])
    diagnostic_cases = []
    used = set(optimizer_cases)
    for case_id in diagnostic_ranked:
        if case_id not in used:
            diagnostic_cases.append(case_id)
        if len(diagnostic_cases) >= max(8, min(16, len(train_cases) // 8)):
            break
    if set(optimizer_cases) & set(diagnostic_cases):
        raise ValueError("CARE_DPR_GATE_A_R2_DIAGNOSTIC_OVERLAPS_OPTIMIZER_CASES")
    return optimizer_cases, sorted(diagnostic_cases)


def sampler_audit_from_samples(stage: str, samples: list[dict[str, Any]], *, cursor_start: int, cursor_end: int) -> dict[str, Any]:
    counts = {slot: 0 for slot in DPR_SAMPLER_PATTERN}
    hits = {slot: 0 for slot in DPR_SAMPLER_PATTERN}
    no_t2_edema_violations = []
    fallback = []
    hard_counts = {slot: {sub: 0 for sub in HARD_NEGATIVE_SUBTYPES} for slot in ("scar_hard_negative", "edema_hard_negative")}
    for sample in samples:
        slot = str(sample.get("requested_mode"))
        if slot in counts:
            counts[slot] += 1
            if int(sample.get("target_voxel_count_in_patch", 0)) > 0 and sample.get("effective_mode") == slot:
                hits[slot] += 1
        if sample.get("fallback_reason"):
            fallback.append(sample)
        if slot.startswith("edema_") and not bool(sample.get("t2_present", True)):
            no_t2_edema_violations.append(sample)
        if slot in hard_counts:
            for sub, value in dict(sample.get("hard_negative_subtype_counts") or {}).items():
                if sub in hard_counts[slot]:
                    hard_counts[slot][sub] += int(value)
    total = max(1, sum(counts.values()))
    fractions = {slot: counts[slot] / total for slot in DPR_SAMPLER_PATTERN}
    hit_rates = {slot: (hits[slot] / counts[slot] if counts[slot] else 0.0) for slot in DPR_SAMPLER_PATTERN}
    long_cycle_ok = all(abs(fractions[slot] - 0.125) <= 0.125 for slot in DPR_SAMPLER_PATTERN if counts[slot])
    hard_negative_ok = all(all(int(v) > 0 for v in hard_counts[slot].values()) for slot in hard_counts)
    return {
        "stage": stage,
        "status": "PASS" if all(hit_rates[slot] == 1.0 for slot in DPR_SAMPLER_PATTERN if counts[slot]) and not fallback and not no_t2_edema_violations and hard_negative_ok else "FAIL",
        "sampler_slot_cursor_start": int(cursor_start),
        "sampler_slot_cursor_end": int(cursor_end),
        "slot_counts": counts,
        "slot_fractions": fractions,
        "slot_hit_rates": hit_rates,
        "long_cycle_each_slot_target_fraction": 0.125,
        "long_cycle_fraction_ok": bool(long_cycle_ok),
        "silent_fallback_count": len(fallback),
        "no_t2_edema_slot_violations": no_t2_edema_violations,
        "hard_negative_subtype_counts": hard_counts,
        "hard_negative_subtype_audit_pass": bool(hard_negative_ok),
    }

def batch_anchor_mask(batch: dict[str, Any]) -> torch.Tensor:
    return batch["anchor_logits"].argmax(dim=1)


def teacher_roi_from_batch(batch: dict[str, Any]) -> tuple[torch.Tensor, torch.Tensor]:
    labels = batch["labels"]
    anchor = batch_anchor_mask(batch)
    scar_gt = (labels == SCAR_CHANNEL).float().unsqueeze(1)
    scar_err = (((labels == SCAR_CHANNEL) != (anchor == SCAR_CHANNEL)).float().unsqueeze(1))
    zone_gt = ((labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)).float().unsqueeze(1)
    zone_anchor = ((anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)).float().unsqueeze(1)
    edema_err = (zone_gt != zone_anchor).float()
    scar_teacher = torch.maximum(scar_gt, scar_err) * batch["myocardium_support"].clamp(0, 1)
    edema_teacher = torch.maximum(zone_gt, edema_err) * batch["edema_support"].clamp(0, 1) * batch["t2_present"][:, None, None, None, None]
    return scar_teacher, edema_teacher


def set_stage_trainability(model: torch.nn.Module, stage: str) -> None:
    for name, param in model.named_parameters():
        if stage in {"A1", "A2", "PREFLIGHT"}:
            param.requires_grad = True
        elif stage == "B":
            param.requires_grad = not name.startswith(FROZEN_STAGE_B_PREFIXES)
        else:
            raise ValueError(stage)


def build_optimizer(model: torch.nn.Module, args: argparse.Namespace, *, stage: str) -> torch.optim.Optimizer:
    enc, branch = [], []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if name.startswith(REPRESENTATION_PREFIXES):
            enc.append(param)
        else:
            branch.append(param)
    if stage == "B":
        return torch.optim.AdamW([{"params": branch, "lr": args.lr_stage_b_branch, "weight_decay": args.weight_decay, "name": "refiner_utility"}], weight_decay=args.weight_decay)
    return torch.optim.AdamW([
        {"params": enc, "lr": args.lr_stage_a_encoder, "weight_decay": args.weight_decay, "name": "encoder"},
        {"params": branch, "lr": args.lr_stage_a_branch, "weight_decay": args.weight_decay, "name": "proposal_refiner_utility"},
    ], weight_decay=args.weight_decay)


def teacher_fraction_for(stage: str, local_step: int, steps: int, *, preflight: bool) -> float:
    if preflight:
        return 0.75
    if stage == "A1":
        return 0.75
    if stage == "A2":
        if local_step > steps - 500:
            return 0.0
        return 0.75 * max(0.0, 1.0 - (local_step - 1) / max(1, steps - 500))
    if stage == "B":
        return 0.0
    raise ValueError(stage)


def run_steps(*, model: torch.nn.Module, optimizer: torch.optim.Optimizer, cases: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, rng: random.Random, args: argparse.Namespace, device: torch.device, stage: str, steps: int, total_step: int, sampler_slot_cursor: int, hard_negative_subtype_cursor: dict[str, int], runtime_root: Path, checkpoint_rows: list[dict[str, Any]], curve_rows: list[dict[str, Any]], preflight: bool, resolved_training_contract_hash: str, local_step_offset: int = 0) -> tuple[int, int, dict[str, int]]:
    sampler_index = build_dpr_sampler_index(cases, case_to_fold, metadata, cache, stage="B" if stage == "B" else "A")
    write_json(runtime_root / f"sampler_index_stage_{stage.lower()}.json", {k: v for k, v in sampler_index.items() if k not in {"eligible", "target_counts_by_case"}})
    audit_samples: list[dict[str, Any]] = []
    audit_cursor_start = int(sampler_slot_cursor)
    fixed_batches = None
    if preflight:
        b0 = build_dpr_batch(cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=args.batch_size, sampler_index=sampler_index, sampler_slot_cursor=0, hard_negative_subtype_cursor={"scar": 0, "edema_zone": 0})
        b1 = build_dpr_batch(cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=args.batch_size, sampler_index=sampler_index, sampler_slot_cursor=args.batch_size, hard_negative_subtype_cursor={"scar": 0, "edema_zone": 0})
        fixed_batches = [move_tensors(b0, device), move_tensors(b1, device)]
    started = time.time()
    for local_step in range(1, int(steps) + 1):
        stage_local_step = int(local_step_offset) + int(local_step)
        if fixed_batches is not None:
            batch = fixed_batches[(local_step - 1) % len(fixed_batches)]
            batch["sampler_slot_cursor_before"] = sampler_slot_cursor
            batch["sampler_slot_cursor_after"] = (sampler_slot_cursor + int(args.batch_size)) % len(DPR_SAMPLER_PATTERN)
        else:
            batch = move_tensors(build_dpr_batch(cases, case_to_fold, metadata, cache, rng, stage="B" if stage == "B" else "A", batch_size=args.batch_size, sampler_index=sampler_index, sampler_slot_cursor=sampler_slot_cursor, hard_negative_subtype_cursor=hard_negative_subtype_cursor), device)
        audit_samples.extend(batch.get("dpr_sampler_samples", []))
        sampler_slot_cursor = int(batch.get("sampler_slot_cursor_after", (sampler_slot_cursor + int(args.batch_size)) % len(DPR_SAMPLER_PATTERN)))
        hard_negative_subtype_cursor = dict(batch.get("hard_negative_subtype_cursor_after", hard_negative_subtype_cursor))
        scar_teacher, edema_teacher = teacher_roi_from_batch(batch)
        teacher_fraction = teacher_fraction_for(stage, stage_local_step, int(steps) + int(local_step_offset), preflight=preflight)
        optimizer.zero_grad(set_to_none=True)
        with autocast(device_type="cuda", dtype=torch.bfloat16, enabled=(device.type == "cuda" and args.amp_dtype == "bfloat16")):
            outputs = model(
                batch["images"], batch["availability"], batch["anchor_logits"],
                uncertainty=batch["uncertainty"], myocardium_support=batch["myocardium_support"], edema_support=batch["edema_support"], distance_to_myocardium=batch["distance_to_myocardium"], t2_present=batch["t2_present"],
                scar_teacher_roi=scar_teacher, edema_teacher_roi=edema_teacher, teacher_roi_fraction=teacher_fraction, allow_teacher_roi=teacher_fraction > 0,
                primary_candidate_mask=batch.get("primary_candidate_mask"), primary_candidate_type=batch.get("primary_candidate_type"), primary_candidate_pathology=batch.get("primary_candidate_pathology"), distance_to_reliable_gt=batch.get("distance_to_reliable_gt"),
                strict_inputs=True, anchor_value_kind=batch["anchor_value_kind"],
            )
            loss, metrics = care_dpr_loss(outputs, batch["labels"], batch_anchor_mask(batch), t2_present=batch["t2_present"], batch_candidates=batch)
        if not torch.isfinite(loss):
            nan_keys = [k for k, v in outputs.items() if isinstance(v, torch.Tensor) and torch.isnan(v.float()).any()]
            print(json.dumps({"nonfinite_loss_debug": {"stage": stage, "local_step": local_step, "sampler_samples": batch.get("dpr_sampler_samples", []), "nan_output_keys": nan_keys, "metrics": metrics}}, ensure_ascii=False), flush=True)
            raise RuntimeError(f"CARE_DPR_NONFINITE_LOSS:{stage}:{local_step}:{float(loss.detach().cpu())}")
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip_norm)
        optimizer.step(); total_step += 1
        if local_step == 1 or total_step % int(args.log_every) == 0 or local_step == steps:
            curve_rows.append({"stage": stage, "local_step": stage_local_step, "total_step": total_step, "teacher_roi_fraction": teacher_fraction, **metrics, "grad_norm": float(grad_norm.detach().cpu()), "elapsed_seconds": round(time.time() - started, 1)})
            write_csv(runtime_root / "training_curve.csv", curve_rows)
        if total_step % int(args.checkpoint_every) == 0 or local_step == steps:
            ckpt = runtime_root / "checkpoints" / f"checkpoint_step{total_step:05d}.pt"
            save_care_dpr_checkpoint(ckpt, model, optimizer, total_step, {"stage": stage, "outer_val_used_for_selection": False, "teacher_roi_for_inner_outer_inference": False}, local_rng=rng, stage=stage, local_step=stage_local_step, sampler_slot_cursor=sampler_slot_cursor, hard_negative_subtype_cursor=hard_negative_subtype_cursor, teacher_roi_schedule_cursor=stage_local_step, resolved_training_contract_hash=resolved_training_contract_hash)
            checkpoint_rows.append({"stage": stage, "optimizer_stage": stage, "step": total_step, "local_step": stage_local_step, "sampler_slot_cursor": sampler_slot_cursor, "hard_negative_subtype_cursor": json.dumps(hard_negative_subtype_cursor, sort_keys=True), "checkpoint_path": str(ckpt), "checkpoint_sha256": sha256_file(ckpt), "outer_val_used": False, "teacher_roi_fraction": teacher_fraction})
            write_csv(runtime_root / "checkpoint_manifest.csv", checkpoint_rows)
    audit = sampler_audit_from_samples(stage, audit_samples, cursor_start=audit_cursor_start, cursor_end=sampler_slot_cursor)
    if preflight:
        probe_samples = []
        probe_cursor = {"scar": 0, "edema_zone": 0}
        for offset in (0, args.batch_size) * len(HARD_NEGATIVE_SUBTYPES):
            probe = build_dpr_batch(cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=args.batch_size, sampler_index=sampler_index, sampler_slot_cursor=offset, hard_negative_subtype_cursor=probe_cursor)
            probe_cursor = dict(probe.get("hard_negative_subtype_cursor_after", probe_cursor))
            probe_samples.extend(probe.get("dpr_sampler_samples", []))
        audit["r2_hard_negative_subtype_probe"] = sampler_audit_from_samples(stage + "_R2_SUBTYPE_PROBE", probe_samples, cursor_start=0, cursor_end=0)
        audit["hard_negative_subtype_audit_pass"] = audit["r2_hard_negative_subtype_probe"].get("hard_negative_subtype_audit_pass") is True
        audit["hard_negative_subtype_counts"] = audit["r2_hard_negative_subtype_probe"].get("hard_negative_subtype_counts", audit.get("hard_negative_subtype_counts", {}))
        audit["status"] = "PASS" if audit.get("status") == "PASS" and audit["hard_negative_subtype_audit_pass"] else "FAIL"
    write_json(runtime_root / f"sampler_audit_stage_{stage.lower()}.json", audit)
    return total_step, sampler_slot_cursor, hard_negative_subtype_cursor



def remaining_stage_plan(*, preflight_steps: int, total_step: int, train_cases: list[str], complete_train_cases: list[str]) -> list[tuple[str, int, list[str], bool, int]]:
    if preflight_steps:
        remaining = max(0, int(preflight_steps) - int(total_step))
        offset = min(int(total_step), int(preflight_steps))
        return [("PREFLIGHT", remaining, train_cases, True, offset)] if remaining else []
    formal = [("A1", 500, train_cases, False), ("A2", 2000, train_cases, False), ("B", 1500, complete_train_cases, False)]
    plan: list[tuple[str, int, list[str], bool, int]] = []
    consumed = 0
    for stage, steps, cases, preflight in formal:
        stage_start = consumed
        stage_end = consumed + int(steps)
        consumed = stage_end
        if total_step >= stage_end:
            continue
        offset = max(0, int(total_step) - stage_start)
        remaining = int(steps) - offset
        if remaining > 0:
            plan.append((stage, remaining, cases, preflight, offset))
    return plan


def stage_for_total_step(total_step: int, *, preflight_steps: int) -> str:
    if preflight_steps:
        return "PREFLIGHT"
    if total_step < 500:
        return "A1"
    if total_step < 2500:
        return "A2"
    return "B"


def optimizer_family(stage: str | None) -> str:
    return "B" if stage == "B" else "A"


def should_restore_optimizer_state(saved_stage: str | None, target_stage: str, total_step: int) -> bool:
    if saved_stage == target_stage:
        return True
    if optimizer_family(saved_stage) == "A" and optimizer_family(target_stage) == "A" and int(total_step) == 500:
        return True
    if saved_stage == "A2" and target_stage == "B" and int(total_step) == 2500:
        return False
    return optimizer_family(saved_stage) == optimizer_family(target_stage)


def exact_reload_check(model: torch.nn.Module, reloaded: torch.nn.Module, batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    model.eval(); reloaded.to(device).eval()
    params_exact = all(torch.equal(a.detach().cpu(), b.detach().cpu()) for (_, a), (_, b) in zip(model.named_parameters(), reloaded.named_parameters()))
    keys = ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "scar_p_refined", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined"]
    with torch.no_grad():
        out_a = model(batch["images"], batch["availability"], batch["anchor_logits"], uncertainty=batch["uncertainty"], myocardium_support=batch["myocardium_support"], edema_support=batch["edema_support"], distance_to_myocardium=batch["distance_to_myocardium"], t2_present=batch["t2_present"], strict_inputs=True, anchor_value_kind=batch["anchor_value_kind"])
        out_b = reloaded(batch["images"], batch["availability"], batch["anchor_logits"], uncertainty=batch["uncertainty"], myocardium_support=batch["myocardium_support"], edema_support=batch["edema_support"], distance_to_myocardium=batch["distance_to_myocardium"], t2_present=batch["t2_present"], strict_inputs=True, anchor_value_kind=batch["anchor_value_kind"])
    outputs_exact = all(torch.equal(out_a[k].detach().cpu(), out_b[k].detach().cpu()) for k in keys)
    model.train(); reloaded.train()
    return {"status": "PASS" if params_exact and outputs_exact else "FAIL", "parameters_exact": bool(params_exact), "outputs_exact": bool(outputs_exact), "parameter_values_exact": bool(params_exact), "fixed_outputs_exact": bool(outputs_exact), "checked_output_keys": keys}

def train_fold(args: argparse.Namespace) -> dict[str, Any]:
    if not args.preflight_steps:
        if args.approval_token in SUPERSEDED_GATE_TOKENS:
            raise SystemExit(f"CARE_DPR_FORMAL_FOLD0_BLOCKED_SUPERSEDED_{args.approval_token}")
        if args.approval_token != FORMAL_GATE_TOKEN:
            raise SystemExit("CARE_DPR_FORMAL_FOLD0_BLOCKED_PENDING_APPROVE_DPR_GATE_A_R2")
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    result_root = Path(args.result_root)
    runtime_root = result_root / ("runtime/preflight" if args.preflight_steps else f"runtime/{args.runtime_name}")
    runtime_root.mkdir(parents=True, exist_ok=True)

    metadata = load_myops_case_metadata()
    fold = load_splits()[args.fold]
    outer_train = sorted(fold["train"]); outer_val = sorted(fold["val"])
    split_payload = deterministic_inner_split(outer_train, args.fold, metadata)
    train_cases = list(split_payload["actual_train_cases"])
    complete_train_cases = list(split_payload["complete_actual_train_cases"])
    preflight_optimizer_cases, gate_a_r2_diagnostic_cases = choose_gate_a_r2_case_sets(train_cases)
    case_to_fold = {case_id: int(f["fold"]) for f in load_splits() for case_id in f["val"]}
    cache = CaseCache(max_cases=args.cache_cases)
    model = build_care_dpr().to(device)

    init_checkpoint_hash = sha256_file(Path(args.init_checkpoint)) if args.init_checkpoint and Path(args.init_checkpoint).is_file() else ""
    resolved_training_contract = {
        "task_key": TASK_KEY,
        "gate_token": FORMAL_GATE_TOKEN,
        "superseded_tokens": list(SUPERSEDED_GATE_TOKENS),
        "total_optimizer_steps": 4000,
        "seed": args.seed,
        "batch_size": args.batch_size,
        "patch_shape_zyx": list(PATCH_SHAPE),
        "roi_sizes": {"scar": [8, 96, 96], "edema_zone": [8, 128, 128]},
        "stage_plan": {"A1": 500, "A2": 2000, "B": 1500},
        "stage_lrs": {"lr_stage_a_encoder": args.lr_stage_a_encoder, "lr_stage_a_branch": args.lr_stage_a_branch, "lr_stage_b_branch": args.lr_stage_b_branch},
        "freeze_groups": {"stage_b": list(FROZEN_STAGE_B_PREFIXES)},
        "weight_decay": args.weight_decay,
        "grad_clip_norm": args.grad_clip_norm,
        "amp_dtype": args.amp_dtype,
        "sampler_pattern": list(DPR_SAMPLER_PATTERN),
        "sampler_subtype_cursor_semantics": {"scar_hard_negative": list(HARD_NEGATIVE_SUBTYPES), "edema_hard_negative": list(HARD_NEGATIVE_SUBTYPES)},
        "loss_weights": {"proposal": 0.5, "utility": 0.5, "boundary": 0.1, "identity": 0.1, "remote": 0.1, "containment": 0.1},
        "utility_formula": "U=clip((E(A)-E(R))/max(|A union R union G|,1),-1,1); E=2*FN+FP+0.25*boundary_error",
        "utility_threshold_candidates": [0.30, 0.40, 0.50, 0.60, 0.70],
        "full_volume_inference_contract": {"passes": 2, "overlap": 0.5, "gaussian_blending": True, "pass1_aggregates": ["shared_full_resolution_feature", "p_coarse", "q_fn", "q_fp"], "pass2_candidate_refinement": True, "patch_final_label_averaging": False, "patch_component_decision": False},
        "split_hashes": split_payload.get("sha256", {}),
        "preflight_optimizer_cases_sha256": stable_json_sha256(preflight_optimizer_cases),
        "gate_a_r2_diagnostic_cases_sha256": stable_json_sha256(gate_a_r2_diagnostic_cases),
        "init_checkpoint": str(args.init_checkpoint),
        "init_checkpoint_sha256": init_checkpoint_hash,
        "source_config_test_hashes": source_hashes(),
    }
    resolved_training_contract_hash = stable_json_sha256(resolved_training_contract)
    write_json(runtime_root / "resolved_training_contract.json", {**resolved_training_contract, "resolved_training_contract_hash": resolved_training_contract_hash})
    write_json(runtime_root / "preflight_optimizer_cases.json", {"case_ids": preflight_optimizer_cases, "case_ids_sha256": stable_json_sha256(preflight_optimizer_cases), "outer_fold0_used": False})
    write_json(runtime_root / "gate_a_r2_diagnostic_cases.json", {"case_ids": gate_a_r2_diagnostic_cases, "case_ids_sha256": stable_json_sha256(gate_a_r2_diagnostic_cases), "disjoint_from_preflight_optimizer_cases": not bool(set(preflight_optimizer_cases) & set(gate_a_r2_diagnostic_cases)), "outer_fold0_used": False})
    total_step = 0
    sampler_slot_cursor = 0
    hard_negative_subtype_cursor = {"scar": 0, "edema_zone": 0}
    curve_rows: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    rng = random.Random(args.seed + args.fold)
    resume_extra: dict[str, Any] = {}
    resume_optimizer_pending = False
    if args.resume_checkpoint:
        resume_path = Path(args.resume_checkpoint)
        model, total_step, resume_extra = load_care_dpr_checkpoint(resume_path, model=model, local_rng=rng, restore_rng=True)
        runtime_state = dict(resume_extra.get("runtime_state") or {})
        ckpt_contract_hash = str(runtime_state.get("resolved_training_contract_hash") or "")
        if ckpt_contract_hash and ckpt_contract_hash != resolved_training_contract_hash:
            raise SystemExit(f"CARE_DPR_RESUME_CONTRACT_HASH_MISMATCH:{ckpt_contract_hash}:{resolved_training_contract_hash}")
        sampler_slot_cursor = int(runtime_state.get("sampler_slot_cursor", 0))
        hard_negative_subtype_cursor = dict(runtime_state.get("hard_negative_subtype_cursor") or hard_negative_subtype_cursor)
        init_receipt = {
            "status": "RESUMED_FROM_CHECKPOINT",
            "resume_checkpoint": str(resume_path),
            "resume_step": int(total_step),
            "resume_stage": runtime_state.get("stage"),
            "resume_local_step": runtime_state.get("local_step"),
            "sampler_slot_cursor": sampler_slot_cursor,
            "teacher_roi_schedule_cursor": runtime_state.get("teacher_roi_schedule_cursor"),
            "optimizer_stage": runtime_state.get("optimizer_stage"),
            "hard_negative_subtype_cursor": hard_negative_subtype_cursor,
            "resolved_training_contract_hash": ckpt_contract_hash or resolved_training_contract_hash,
        }
        resume_optimizer_pending = True
    else:
        init_receipt = initialize_from_care_dg(model, Path(args.init_checkpoint)) if args.init_checkpoint else {"status": "RANDOM_INIT"}
    model.to(device)
    stage_plan = remaining_stage_plan(preflight_steps=int(args.preflight_steps), total_step=int(total_step), train_cases=preflight_optimizer_cases if args.preflight_steps else train_cases, complete_train_cases=complete_train_cases)
    optimizer: torch.optim.Optimizer | None = None
    optimizer_restored = False
    for stage, steps, cases, preflight, local_step_offset in stage_plan:
        set_stage_trainability(model, stage)
        optimizer = build_optimizer(model, args, stage="B" if stage == "B" else "A1")
        if resume_optimizer_pending and not optimizer_restored and stage == stage_for_total_step(int(total_step), preflight_steps=int(args.preflight_steps)):
            saved_stage = (resume_extra.get("runtime_state") or {}).get("optimizer_stage") or (resume_extra.get("runtime_state") or {}).get("stage")
            if should_restore_optimizer_state(str(saved_stage), stage, int(total_step)):
                load_care_dpr_checkpoint(Path(args.resume_checkpoint), model=model, optimizer=optimizer, local_rng=rng, restore_rng=False)
                model.to(device)
                optimizer_restored = True
        total_step, sampler_slot_cursor, hard_negative_subtype_cursor = run_steps(model=model, optimizer=optimizer, cases=cases, case_to_fold=case_to_fold, metadata=metadata, cache=cache, rng=rng, args=args, device=device, stage=stage, steps=steps, total_step=total_step, sampler_slot_cursor=sampler_slot_cursor, hard_negative_subtype_cursor=hard_negative_subtype_cursor, runtime_root=runtime_root, checkpoint_rows=checkpoint_rows, curve_rows=curve_rows, preflight=preflight, resolved_training_contract_hash=resolved_training_contract_hash, local_step_offset=local_step_offset)
    if optimizer is None:
        set_stage_trainability(model, stage_for_total_step(int(total_step), preflight_steps=int(args.preflight_steps)))
        optimizer = build_optimizer(model, args, stage="B" if stage_for_total_step(int(total_step), preflight_steps=int(args.preflight_steps)) == "B" else "A1")
        if resume_optimizer_pending:
            saved_stage = (resume_extra.get("runtime_state") or {}).get("optimizer_stage") or (resume_extra.get("runtime_state") or {}).get("stage")
            target_stage = stage_for_total_step(int(total_step), preflight_steps=int(args.preflight_steps))
            if should_restore_optimizer_state(str(saved_stage), target_stage, int(total_step)):
                load_care_dpr_checkpoint(Path(args.resume_checkpoint), model=model, optimizer=optimizer, local_rng=rng, restore_rng=False)
                model.to(device)
                optimizer_restored = True
    last_path = runtime_root / "checkpoints" / "checkpoint_last.pt"
    terminal_optimizer_stage = stage_for_total_step(max(int(total_step) - 1, 0), preflight_steps=int(args.preflight_steps))
    save_care_dpr_checkpoint(last_path, model, optimizer, total_step, {"outer_val_used_for_selection": False, "teacher_roi_for_inner_outer_inference": False}, local_rng=rng, stage=terminal_optimizer_stage, local_step=total_step, sampler_slot_cursor=sampler_slot_cursor, hard_negative_subtype_cursor=hard_negative_subtype_cursor, teacher_roi_schedule_cursor=total_step, resolved_training_contract_hash=resolved_training_contract_hash)
    reloaded, reload_step, _ = load_care_dpr_checkpoint(last_path)
    reload_cases = preflight_optimizer_cases if args.preflight_steps else train_cases
    reload_index = build_dpr_sampler_index(reload_cases, case_to_fold, metadata, cache, stage="A")
    reload_batch = move_tensors(build_dpr_batch(reload_cases, case_to_fold, metadata, cache, random.Random(args.seed + 999), stage="A", batch_size=min(args.batch_size, 4), sampler_index=reload_index, sampler_slot_cursor=0, hard_negative_subtype_cursor={"scar": 0, "edema_zone": 0}), device)
    reload_exact = exact_reload_check(model, reloaded, reload_batch, device)
    reload_ok = reload_step == total_step and reload_exact["status"] == "PASS"
    receipt = {
        "status": "PASS" if reload_ok else "NEEDS_REPAIR",
        "fold": args.fold, "seed": args.seed, "device": str(device), "preflight_only": bool(args.preflight_steps),
        "formal_training_credit": 0 if args.preflight_steps else total_step,
        "stage_plan": [{"stage": s, "steps": st, "local_step_offset": offset} for s, st, _, _, offset in stage_plan],
        "resume_checkpoint": str(args.resume_checkpoint) if args.resume_checkpoint else "",
        "resume_optimizer_restored": bool(optimizer_restored),
        "hard_negative_subtype_cursor_terminal": hard_negative_subtype_cursor,
        "preflight_optimizer_cases": len(preflight_optimizer_cases),
        "gate_a_r2_diagnostic_cases": len(gate_a_r2_diagnostic_cases),
        "diagnostic_cases_overlap_optimizer_cases": bool(set(preflight_optimizer_cases) & set(gate_a_r2_diagnostic_cases)),
        "stage_a1_optimizer_steps": 500 if not args.preflight_steps else 0,
        "stage_a2_optimizer_steps": 2000 if not args.preflight_steps else 0,
        "stage_b_optimizer_steps": 1500 if not args.preflight_steps else 0,
        "actual_optimizer_steps": total_step, "batch_size": args.batch_size, "patch_shape_zyx": list(PATCH_SHAPE), "amp_dtype": args.amp_dtype, "grad_clip_norm": args.grad_clip_norm,
        "outer_val_used_for_selection": False, "teacher_roi_inner_outer_inference": False, "predicted_roi_only_for_inner_outer_inference": True, "sampler_slot_cursor_terminal": sampler_slot_cursor, "resolved_training_contract_hash": resolved_training_contract_hash,
        "outer_val_cases": len(outer_val), "actual_train_cases": len(train_cases), "complete_actual_train_cases": len(complete_train_cases), "inner_select_cases": len(split_payload["inner_select_cases"]),
        "init_receipt": init_receipt, "checkpoint_reload": {"status": "PASS" if reload_ok else "FAIL", "reload_step": reload_step, **reload_exact}, "last_checkpoint": str(last_path), "last_checkpoint_sha256": sha256_file(last_path), "terminal_time_utc": now_utc(),
    }
    write_json(runtime_root / ("preflight_receipt.json" if args.preflight_steps else "fold_training_receipt.json"), receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--result-root", default=str(DEFAULT_RESULT_ROOT))
    parser.add_argument("--init-checkpoint", default=str(DEFAULT_CARE_DG_INIT))
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--preflight-steps", type=int, default=0)
    parser.add_argument("--approval-token", default="")
    parser.add_argument("--resume-checkpoint", default="")
    parser.add_argument("--runtime-name", default="formal_fold0")
    parser.add_argument("--lr-stage-a-encoder", type=float, default=2e-5)
    parser.add_argument("--lr-stage-a-branch", type=float, default=1e-4)
    parser.add_argument("--lr-stage-b-branch", type=float, default=5e-5)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--grad-clip-norm", type=float, default=1.0)
    parser.add_argument("--amp-dtype", default="bfloat16", choices=["bfloat16", "none"])
    parser.add_argument("--checkpoint-every", type=int, default=500)
    parser.add_argument("--log-every", type=int, default=25)
    parser.add_argument("--cache-cases", type=int, default=32)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    receipt = train_fold(args)
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
