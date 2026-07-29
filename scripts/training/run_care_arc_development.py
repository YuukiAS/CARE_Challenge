#!/usr/bin/env python3
"""Train CARE-ARC development/clean folds with the frozen full-volume contract."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.amp import autocast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_arc_dataset import CAREARCDataset, build_case_records, collate_single_case
from src.care_myocardium.models.care_arc import CAREARCConfig, build_care_arc, trainable_parameter_count
from src.care_myocardium.training.care_arc_trainer import (
    care_arc_loss,
    optimizer_for_care_arc,
    save_care_arc_checkpoint,
    sdf_target_from_mask,
    stable_json_sha256,
)

TASK_KEY = "20260729_care_arc_clean_fold1"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys or ["status"], extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in batch.items()}


def add_sdf_targets(batch: dict[str, Any]) -> dict[str, Any]:
    spacing = batch["spacing_zyx"]
    batch["scar_sdf_target"] = sdf_target_from_mask(batch["scar_target"], spacing)
    batch["edema_sdf_target"] = sdf_target_from_mask(batch["edema_zone_target"], spacing)
    return batch


def load_batches(fold: int, crop_hw: int, role: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = build_case_records(fold, role)
    ds = CAREARCDataset(records, crop_hw=crop_hw)
    batches: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for idx in range(len(ds)):
        batch = add_sdf_targets(collate_single_case([ds[idx]]))
        batches.append(batch)
        record = records[idx]
        manifest.append(
            {
                "case_id": record.case_id,
                "fold": fold,
                "role": role,
                "center": record.center,
                "modality_group": record.modality_group,
                "t2_present": record.t2_present,
                "scar_positive": record.scar_positive,
                "edema_positive": record.edema_positive,
                "shape_dhw": "x".join(str(v) for v in record.shape_dhw),
            }
        )
    return batches, manifest


def set_train_stage(model: torch.nn.Module, step: int) -> str:
    for param in model.parameters():
        param.requires_grad = True
    if step <= 500:
        for name, param in model.named_parameters():
            if name.startswith("encoder.e2.") or name.startswith("encoder.e3."):
                param.requires_grad = False
        return "A0"
    if step <= 4000:
        return "A1"
    return "B"


def build_strata(batches: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    strata = {
        "complete": [],
        "lge_c0": [],
        "lge_only": [],
        "scar_positive": [],
        "edema_positive": [],
        "hard_negative": [],
        "all": list(batches),
    }
    for batch in batches:
        av = tuple(float(x) for x in batch["availability"].flatten().tolist())
        scar_pos = float(batch["scar_positive"].flatten()[0]) > 0.5
        edema_pos = float(batch["edema_positive"].flatten()[0]) > 0.5 and float(batch["t2_present"].flatten()[0]) > 0.5
        if av == (1.0, 1.0, 1.0):
            strata["complete"].append(batch)
        if av == (1.0, 0.0, 1.0):
            strata["lge_c0"].append(batch)
        if av == (1.0, 0.0, 0.0):
            strata["lge_only"].append(batch)
        if scar_pos:
            strata["scar_positive"].append(batch)
        if edema_pos:
            strata["edema_positive"].append(batch)
        if not scar_pos and not edema_pos:
            strata["hard_negative"].append(batch)
    return strata


def choose_batch(strata: dict[str, list[dict[str, Any]]], step: int, micro: int, rng: random.Random, stage: str) -> tuple[str, dict[str, Any]]:
    if stage == "B":
        pool_name = "complete"
    else:
        order = ("edema_positive", "scar_positive", "complete", "lge_c0", "lge_only", "hard_negative")
        pool_name = order[(step + micro) % len(order)]
    pool = strata.get(pool_name) or strata["all"]
    return pool_name, rng.choice(pool)


def run(args: argparse.Namespace) -> int:
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    rng = random.Random(args.seed)
    device = torch.device(args.device)
    out_root = Path(args.output_root)
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    out_root.mkdir(parents=True, exist_ok=True)
    batches_cpu, manifest = load_batches(args.fold, args.crop_hw, "actual_train")
    strata = build_strata(batches_cpu)
    write_csv(out_root / "model_summary.csv", manifest)
    model = build_care_arc(CAREARCConfig()).to(device)
    contract_hash = stable_json_sha256(
        {
            "task_key": TASK_KEY,
            "fold": args.fold,
            "steps": args.steps,
            "crop_hw": args.crop_hw,
            "batch_size": 1,
            "gradient_accumulation": 2,
            "stage_schedule": "A0_1_500_A1_501_4000_B_4001_7000",
            "pathology_inputs": ["LGE", "T2", "C0", "availability"],
        }
    )
    current_stage = set_train_stage(model, 1)
    optimizer = optimizer_for_care_arc(model, stage="B" if current_stage == "B" else "A")
    rows: list[dict[str, Any]] = []
    checkpoints: list[str] = []
    stage_counts = {"A0": 0, "A1": 0, "B": 0}
    start = time.time()
    optimizer.zero_grad(set_to_none=True)
    for step in range(1, int(args.steps) + 1):
        stage = set_train_stage(model, step)
        if stage != current_stage:
            current_stage = stage
            optimizer = optimizer_for_care_arc(model, stage="B" if stage == "B" else "A")
            optimizer.zero_grad(set_to_none=True)
        stage_counts[stage] += 1
        accum: list[dict[str, float]] = []
        roles: list[str] = []
        for micro in range(2):
            role, batch_cpu = choose_batch(strata, step, micro, rng, stage)
            roles.append(role)
            batch = move_batch(batch_cpu, device)
            with autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                out = model(batch["images"], batch["availability"])
                loss, metrics = care_arc_loss(out, batch)
                loss = loss / 2.0
            loss.backward()
            accum.append(metrics)
        torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        row = {
            "step": step,
            "stage": stage,
            "micro_roles": "+".join(roles),
            "loss": float(np.mean([m["loss"] for m in accum])),
            "scar_active": float(np.mean([m["scar_active"] for m in accum])),
            "edema_active": float(np.mean([m["edema_active"] for m in accum])),
            "anatomy": float(np.mean([m["anatomy"] for m in accum])),
            "alignment": float(np.mean([m["alignment"] for m in accum])),
        }
        rows.append(row)
        if step % 50 == 0:
            print(json.dumps(row), flush=True)
        if step % int(args.save_every) == 0 or step == int(args.steps):
            checkpoint = out_root / f"checkpoint_step{step:05d}.pt"
            save_care_arc_checkpoint(checkpoint, model, optimizer, step=step, config=model.config, contract_hash=contract_hash)
            checkpoints.append(str(checkpoint.relative_to(REPO_ROOT)))
    elapsed = time.time() - start
    receipt = {
        "task_key": TASK_KEY,
        "created_at_utc": now_utc(),
        "status": "PASS",
        "fold": int(args.fold),
        "role": "actual_train",
        "formal_training_credit": 0 if args.zero_credit else 1,
        "optimizer_steps": int(args.steps),
        "gradient_accumulation": 2,
        "batch_size": 1,
        "crop_hw": int(args.crop_hw),
        "device": str(device),
        "cuda_available": torch.cuda.is_available(),
        "train_loop_seconds": elapsed,
        "median_seconds_per_optimizer_step": elapsed / max(1, int(args.steps)),
        "trainable_parameter_count": trainable_parameter_count(model),
        "stage_counts": stage_counts,
        "case_count": len(batches_cpu),
        "strata_counts": {k: len(v) for k, v in strata.items()},
        "checkpoints": checkpoints,
        "final_checkpoint": checkpoints[-1],
        "contract_hash": contract_hash,
    }
    write_csv(out_root / "training_curve.csv", rows)
    write_json(out_root / "training_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--crop-hw", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--save-every", type=int, default=500)
    parser.add_argument("--zero-credit", action="store_true")
    parser.add_argument("--output-root", required=True)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
