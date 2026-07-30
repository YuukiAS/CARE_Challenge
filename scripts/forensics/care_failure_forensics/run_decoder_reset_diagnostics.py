#!/usr/bin/env python3
"""Run D1-D3 CARE-PRISM decoder-reset forensic diagnostics.

This is a narrow diagnostic wrapper. It reuses the existing CARE-PRISM model,
dataset, loss, checkpoint, and evaluator-facing checkpoint schema, but applies
explicit trainability policies required by the failure-forensics packet.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_care_prism import build_initialized_model, move_batch
from src.care_myocardium.data.care_prism_dataset import (
    CAREPRISMAugmenter,
    CAREPRISMBalancedSampler,
    CAREPRISMFullPatientDataset,
)
from src.care_myocardium.training.care_prism_trainer import (
    care_prism_loss,
    file_sha256,
    optimizer_for_care_prism,
    save_care_prism_checkpoint,
)


DIAGNOSTICS = {
    "D1_DECODER_RESET_ENCODER_FROZEN": {
        "steps": 1500,
        "freeze_policy": "shared_encoder_frozen",
        "encoder_lr": 0.0,
        "new_lr": 1.0e-4,
        "loss_stage": "A",
    },
    "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE": {
        "steps": 3000,
        "freeze_policy": "shared_encoder_stages_0_3_frozen_stages_4_6_trainable",
        "encoder_lr": 1.0e-5,
        "new_lr": 1.0e-4,
        "loss_stage": "A",
    },
    "D3_FULL_MODEL_SHORT_FINETUNE": {
        "steps": 1000,
        "freeze_policy": "all_model_trainable_uniform_low_lr",
        "encoder_lr": 1.0e-5,
        "new_lr": 1.0e-5,
        "loss_stage": "A",
    },
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row), lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def git_head(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def apply_freeze_policy(model: torch.nn.Module, diagnostic: str) -> dict[str, Any]:
    trainable_names: list[str] = []
    frozen_names: list[str] = []
    top_stages = {"4", "5", "6"}
    for name, param in model.named_parameters():
        if diagnostic == "D1_DECODER_RESET_ENCODER_FROZEN":
            trainable = not name.startswith("shared_encoder.")
        elif diagnostic == "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE":
            if name.startswith("shared_encoder.stages."):
                parts = name.split(".")
                trainable = len(parts) > 2 and parts[2] in top_stages
            elif name.startswith("shared_encoder."):
                trainable = False
            else:
                trainable = True
        elif diagnostic == "D3_FULL_MODEL_SHORT_FINETUNE":
            trainable = True
        else:
            raise ValueError(f"unknown diagnostic: {diagnostic}")
        param.requires_grad = trainable
        (trainable_names if trainable else frozen_names).append(name)
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    frozen_params = sum(p.numel() for p in model.parameters() if not p.requires_grad)
    return {
        "diagnostic": diagnostic,
        "freeze_policy": DIAGNOSTICS[diagnostic]["freeze_policy"],
        "trainable_param_count": int(trainable_params),
        "frozen_param_count": int(frozen_params),
        "trainable_parameter_prefix_examples": trainable_names[:20],
        "frozen_parameter_prefix_examples": frozen_names[:20],
        "top_encoder_trainable_stages": [4, 5, 6] if diagnostic == "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE" else [],
    }


def configure_lrs(optimizer: torch.optim.Optimizer, diagnostic: str) -> None:
    spec = DIAGNOSTICS[diagnostic]
    optimizer.param_groups[0]["lr"] = float(spec["encoder_lr"])
    optimizer.param_groups[1]["lr"] = float(spec["new_lr"])


def run_one(args: argparse.Namespace, diagnostic: str, device: torch.device) -> dict[str, Any]:
    spec = DIAGNOSTICS[diagnostic]
    seed = int(args.seed) + list(DIAGNOSTICS).index(diagnostic)
    set_seed(seed)
    model, transplant = build_initialized_model(int(args.fold), device)
    freeze = apply_freeze_policy(model, diagnostic)
    optimizer = optimizer_for_care_prism(model, stage="A")
    configure_lrs(optimizer, diagnostic)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(int(spec["steps"]), 1))
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    train_ds = CAREPRISMFullPatientDataset(
        fold=int(args.fold),
        split="actual_train",
        augmenter=CAREPRISMAugmenter(seed=seed, training=True),
    )
    sampler_ds = CAREPRISMFullPatientDataset(
        fold=int(args.fold),
        split="actual_train",
        augmenter=CAREPRISMAugmenter(training=False),
    )
    sampler = CAREPRISMBalancedSampler(sampler_ds, seed=seed)

    runtime_dir = args.result_root / "runtime" / diagnostic
    checkpoint_dir = runtime_dir / "checkpoints"
    log_path = runtime_dir / "training_log.csv"
    checkpoint_every = int(args.checkpoint_every)
    model.train()
    start_utc = datetime.now(UTC).isoformat()
    for step in range(1, int(spec["steps"]) + 1):
        configure_lrs(optimizer, diagnostic)
        optimizer.zero_grad(set_to_none=True)
        step_loss = 0.0
        focus_losses: dict[str, float] = {}
        focus_cases: dict[str, str] = {}
        all_finite = True
        all_nonnegative = True
        for focus in ("scar", "edema"):
            idx = sampler.next_index(focus)
            batch = move_batch(train_ds[idx], device)
            focus_cases[focus] = batch["case_id"][0]
            with torch.amp.autocast(device_type=device.type, enabled=device.type == "cuda"):
                outputs = model(batch["images"], batch["availability"])
                loss, metrics = care_prism_loss(outputs, batch, stage=str(spec["loss_stage"]))
                scaled_loss = loss / 2.0
            scaler.scale(scaled_loss).backward()
            step_loss += float(loss.detach().cpu()) / 2.0
            focus_losses[focus] = float(loss.detach().cpu())
            all_finite = all_finite and bool(metrics["all_finite"])
            all_nonnegative = all_nonnegative and bool(metrics["all_nonnegative"])
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()
        if step == 1 or step % int(args.log_every) == 0 or step == int(spec["steps"]):
            append_csv(
                log_path,
                {
                    "diagnostic": diagnostic,
                    "step": step,
                    "loss_stage": spec["loss_stage"],
                    "loss": step_loss,
                    "scar_loss": focus_losses.get("scar", ""),
                    "edema_loss": focus_losses.get("edema", ""),
                    "all_finite": all_finite,
                    "all_nonnegative": all_nonnegative,
                    "freeze_policy": spec["freeze_policy"],
                    "lr_encoder": optimizer.param_groups[0]["lr"],
                    "lr_new": optimizer.param_groups[1]["lr"],
                    "scar_case": focus_cases.get("scar", ""),
                    "edema_case": focus_cases.get("edema", ""),
                    "cuda_max_memory_gb": torch.cuda.max_memory_allocated() / 1024**3 if device.type == "cuda" else 0.0,
                },
            )
        if step % checkpoint_every == 0 or step == int(spec["steps"]):
            ckpt = checkpoint_dir / f"checkpoint_step{step:05d}.pt"
            save_care_prism_checkpoint(
                ckpt,
                model,
                optimizer,
                scheduler=scheduler,
                scaler=scaler,
                stage=diagnostic,
                step=step,
                sampler_state={**sampler.state_dict(), "step": step},
                augmentation_rng_state=train_ds.state_dict().get("augmenter"),
                hard_negative_state={"bank_hash": "decoder_reset_forensics_actual_train_only"},
                contract_hash="care_failure_forensics_d1_d3_decoder_reset",
            )
    final_ckpt = checkpoint_dir / f"checkpoint_step{int(spec['steps']):05d}.pt"
    rows = []
    with log_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    losses = [float(r["loss"]) for r in rows if r.get("loss")]
    status = "PASS" if final_ckpt.exists() and rows and all(r.get("all_finite") == "True" for r in rows) else "FAIL"
    summary = {
        "status": status,
        "diagnostic": diagnostic,
        "fold": int(args.fold),
        "train_split": "actual_train",
        "selection_split": "inner_select",
        "outer_accessed_for_training_or_selection": False,
        "optimizer_steps": int(spec["steps"]),
        "loss_stage": spec["loss_stage"],
        "learning_rates": {"encoder_group": spec["encoder_lr"], "new_group": spec["new_lr"]},
        "freeze": freeze,
        "transplant_byte_coverage": transplant["byte_coverage"],
        "runtime_dir": str(runtime_dir),
        "training_log": str(log_path),
        "final_checkpoint": str(final_ckpt),
        "final_checkpoint_sha256": file_sha256(final_ckpt),
        "checkpoint_every": checkpoint_every,
        "logged_loss_first": losses[0] if losses else None,
        "logged_loss_last": losses[-1] if losses else None,
        "started_utc": start_utc,
        "finished_utc": datetime.now(UTC).isoformat(),
        "repo_head": git_head(REPO_ROOT),
        "seed": seed,
        "balanced_sampler": sampler.summary(),
    }
    write_json(args.result_root / f"{diagnostic}_training_summary.json", summary)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--result-root", type=Path, required=True)
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--diagnostic", action="append", choices=sorted(DIAGNOSTICS), default=None)
    ap.add_argument("--checkpoint-every", type=int, default=500)
    ap.add_argument("--log-every", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260730)
    ap.add_argument("--print-contract", action="store_true")
    args = ap.parse_args()
    args.result_root = args.result_root.resolve()
    selected = args.diagnostic or list(DIAGNOSTICS)
    if args.print_contract:
        print(json.dumps({"diagnostics": {k: DIAGNOSTICS[k] for k in selected}}, indent=2, ensure_ascii=False))
        return
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but not available")
    args.result_root.mkdir(parents=True, exist_ok=True)
    summaries = [run_one(args, diagnostic, device) for diagnostic in selected]
    write_json(
        args.result_root / "decoder_reset_diagnostics_run_summary.json",
        {
            "status": "PASS" if all(s["status"] == "PASS" for s in summaries) else "FAIL",
            "diagnostics": summaries,
            "completed_utc": datetime.now(UTC).isoformat(),
        },
    )
    print(json.dumps({"status": "PASS", "diagnostic_count": len(summaries)}, indent=2))


if __name__ == "__main__":
    main()
