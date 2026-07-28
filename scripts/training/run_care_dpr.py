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
from src.care_myocardium.data.care_dpr_dataset import CaseCache, build_dpr_batch, build_dpr_sampler_index, deterministic_inner_split, load_splits
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


def run_steps(*, model: torch.nn.Module, optimizer: torch.optim.Optimizer, cases: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, rng: random.Random, args: argparse.Namespace, device: torch.device, stage: str, steps: int, total_step: int, runtime_root: Path, checkpoint_rows: list[dict[str, Any]], curve_rows: list[dict[str, Any]], preflight: bool) -> int:
    sampler_index = build_dpr_sampler_index(cases, case_to_fold, metadata, cache, stage="B" if stage == "B" else "A")
    write_json(runtime_root / f"sampler_index_stage_{stage.lower()}.json", {k: v for k, v in sampler_index.items() if k not in {"eligible", "target_counts_by_case"}})
    fixed_batch = None
    if preflight:
        fixed_batch = move_tensors(build_dpr_batch(cases, case_to_fold, metadata, cache, rng, stage="A", batch_size=args.batch_size, sampler_index=sampler_index), device)
    started = time.time()
    for local_step in range(1, int(steps) + 1):
        batch = fixed_batch or move_tensors(build_dpr_batch(cases, case_to_fold, metadata, cache, rng, stage="B" if stage == "B" else "A", batch_size=args.batch_size, sampler_index=sampler_index), device)
        scar_teacher, edema_teacher = teacher_roi_from_batch(batch)
        teacher_fraction = teacher_fraction_for(stage, local_step, int(steps), preflight=preflight)
        optimizer.zero_grad(set_to_none=True)
        with autocast(device_type="cuda", dtype=torch.bfloat16, enabled=(device.type == "cuda" and args.amp_dtype == "bfloat16")):
            outputs = model(
                batch["images"], batch["availability"], batch["anchor_logits"],
                uncertainty=batch["uncertainty"], myocardium_support=batch["myocardium_support"], edema_support=batch["edema_support"], distance_to_myocardium=batch["distance_to_myocardium"], t2_present=batch["t2_present"],
                scar_teacher_roi=scar_teacher, edema_teacher_roi=edema_teacher, teacher_roi_fraction=teacher_fraction, allow_teacher_roi=teacher_fraction > 0,
                strict_inputs=True, anchor_value_kind=batch["anchor_value_kind"],
            )
            loss, metrics = care_dpr_loss(outputs, batch["labels"], batch_anchor_mask(batch), t2_present=batch["t2_present"])
        if not torch.isfinite(loss):
            raise RuntimeError(f"CARE_DPR_NONFINITE_LOSS:{stage}:{local_step}:{float(loss.detach().cpu())}")
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip_norm)
        optimizer.step(); total_step += 1
        if local_step == 1 or total_step % int(args.log_every) == 0 or local_step == steps:
            curve_rows.append({"stage": stage, "local_step": local_step, "total_step": total_step, "teacher_roi_fraction": teacher_fraction, **metrics, "grad_norm": float(grad_norm.detach().cpu()), "elapsed_seconds": round(time.time() - started, 1)})
            write_csv(runtime_root / "training_curve.csv", curve_rows)
        if total_step % int(args.checkpoint_every) == 0 or local_step == steps:
            ckpt = runtime_root / "checkpoints" / f"checkpoint_step{total_step:05d}.pt"
            save_care_dpr_checkpoint(ckpt, model, optimizer, total_step, {"stage": stage, "outer_val_used_for_selection": False, "teacher_roi_for_inner_outer_inference": False}, local_rng=rng, stage=stage, local_step=local_step)
            checkpoint_rows.append({"stage": stage, "step": total_step, "local_step": local_step, "checkpoint_path": str(ckpt), "checkpoint_sha256": sha256_file(ckpt), "outer_val_used": False, "teacher_roi_fraction": teacher_fraction})
            write_csv(runtime_root / "checkpoint_manifest.csv", checkpoint_rows)
    return total_step


def train_fold(args: argparse.Namespace) -> dict[str, Any]:
    if not args.preflight_steps and args.approval_token != "APPROVE_DPR_GATE_A":
        raise SystemExit("CARE_DPR_FORMAL_FOLD0_BLOCKED_PENDING_APPROVE_DPR_GATE_A")
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    result_root = Path(args.result_root)
    runtime_root = result_root / ("runtime/preflight" if args.preflight_steps else "runtime/formal_fold0")
    runtime_root.mkdir(parents=True, exist_ok=True)

    metadata = load_myops_case_metadata()
    fold = load_splits()[args.fold]
    outer_train = sorted(fold["train"]); outer_val = sorted(fold["val"])
    split_payload = deterministic_inner_split(outer_train, args.fold, metadata)
    train_cases = list(split_payload["actual_train_cases"])
    complete_train_cases = list(split_payload["complete_actual_train_cases"])
    case_to_fold = {case_id: int(f["fold"]) for f in load_splits() for case_id in f["val"]}
    cache = CaseCache(max_cases=args.cache_cases)
    model = build_care_dpr().to(device)
    init_receipt = initialize_from_care_dg(model, Path(args.init_checkpoint)) if args.init_checkpoint else {"status": "RANDOM_INIT"}
    model.to(device)

    total_step = 0; curve_rows: list[dict[str, Any]] = []; checkpoint_rows: list[dict[str, Any]] = []
    rng = random.Random(args.seed + args.fold)
    if args.preflight_steps:
        stage_plan = [("PREFLIGHT", int(args.preflight_steps), train_cases, True)]
    else:
        stage_plan = [("A1", 500, train_cases, False), ("A2", 2000, train_cases, False), ("B", 1500, complete_train_cases, False)]
    for stage, steps, cases, preflight in stage_plan:
        set_stage_trainability(model, stage)
        optimizer = build_optimizer(model, args, stage="B" if stage == "B" else "A1")
        total_step = run_steps(model=model, optimizer=optimizer, cases=cases, case_to_fold=case_to_fold, metadata=metadata, cache=cache, rng=rng, args=args, device=device, stage=stage, steps=steps, total_step=total_step, runtime_root=runtime_root, checkpoint_rows=checkpoint_rows, curve_rows=curve_rows, preflight=preflight)
    last_path = runtime_root / "checkpoints" / "checkpoint_last.pt"
    save_care_dpr_checkpoint(last_path, model, optimizer, total_step, {"outer_val_used_for_selection": False, "teacher_roi_for_inner_outer_inference": False}, local_rng=rng, stage="terminal")
    reloaded, reload_step, _ = load_care_dpr_checkpoint(last_path)
    reload_ok = reload_step == total_step and stable_json_sha256({"keys": sorted(reloaded.state_dict())}) == stable_json_sha256({"keys": sorted(model.state_dict())})
    receipt = {
        "status": "PASS" if reload_ok else "NEEDS_REPAIR",
        "fold": args.fold, "seed": args.seed, "device": str(device), "preflight_only": bool(args.preflight_steps),
        "formal_training_credit": 0 if args.preflight_steps else total_step,
        "stage_plan": [{"stage": s, "steps": st} for s, st, _, _ in stage_plan],
        "stage_a1_optimizer_steps": 500 if not args.preflight_steps else 0,
        "stage_a2_optimizer_steps": 2000 if not args.preflight_steps else 0,
        "stage_b_optimizer_steps": 1500 if not args.preflight_steps else 0,
        "actual_optimizer_steps": total_step, "batch_size": args.batch_size, "patch_shape_zyx": list(PATCH_SHAPE), "amp_dtype": args.amp_dtype, "grad_clip_norm": args.grad_clip_norm,
        "outer_val_used_for_selection": False, "teacher_roi_inner_outer_inference": False, "predicted_roi_only_for_inner_outer_inference": True,
        "outer_val_cases": len(outer_val), "actual_train_cases": len(train_cases), "complete_actual_train_cases": len(complete_train_cases), "inner_select_cases": len(split_payload["inner_select_cases"]),
        "init_receipt": init_receipt, "checkpoint_reload": {"status": "PASS" if reload_ok else "FAIL", "reload_step": reload_step}, "last_checkpoint": str(last_path), "last_checkpoint_sha256": sha256_file(last_path), "terminal_time_utc": now_utc(),
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
