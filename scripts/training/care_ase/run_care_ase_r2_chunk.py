#!/usr/bin/env python
"""Formal CARE-ASE R2 exact-resume chunk training entrypoint."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.care_ase import build_care_ase_for_fold_with_area_references
from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
from src.care_myocardium.training.care_ase_sampler import CAREASEDeterministicSampler, compute_actual_train_area_references
from src.care_myocardium.training.care_ase_trainer import (
    CAREASEStageScheduler,
    build_optimizer,
    care_ase_loss,
    checkpoint_receipt,
    load_care_ase_checkpoint,
    save_care_ase_checkpoint,
    set_stage_trainability,
    write_json,
)


PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
SPLITS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
RESULT_DIR = REPO_ROOT / "results/20260803_care_ase_r2_full_fidelity_execution"
CRITICAL_SOURCE_PATHS = (
    "src/care_myocardium/models/care_ase.py",
    "src/care_myocardium/training/care_ase_trainer.py",
    "src/care_myocardium/training/care_ase_sampler.py",
    "src/care_myocardium/inference/care_ase_r2_decode.py",
    "scripts/training/care_ase/run_care_ase_r2_chunk.py",
    "scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py",
    "jobs/care_ase_r2/run_fold_chunk_htzhulab.sh",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def combined_source_hash() -> str:
    payload = {path: sha256_file(REPO_ROOT / path) for path in CRITICAL_SOURCE_PATHS if (REPO_ROOT / path).is_file()}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def parse_patch_size(text: str) -> tuple[int, int, int]:
    parts = tuple(int(v) for v in text.replace("x", ",").split(",") if v)
    if len(parts) != 3:
        raise ValueError(f"patch size must have 3 dimensions, got {text}")
    return parts


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def crop_or_pad(array: np.ndarray, center: tuple[int, int, int], patch_size: tuple[int, int, int]) -> np.ndarray:
    spatial = array.shape[-3:]
    src_slices: list[slice] = []
    dst_slices: list[slice] = []
    for c, dim, size in zip(center, spatial, patch_size):
        start = int(c) - size // 2
        stop = start + size
        src_start = max(0, start)
        src_stop = min(dim, stop)
        dst_start = src_start - start
        dst_stop = dst_start + (src_stop - src_start)
        src_slices.append(slice(src_start, src_stop))
        dst_slices.append(slice(dst_start, dst_stop))
    out = np.zeros(array.shape[:-3] + patch_size, dtype=array.dtype)
    out[(..., *dst_slices)] = array[(..., *src_slices)]
    return out


def deterministic_center(
    seg: np.ndarray,
    *,
    descriptor_sha: str,
    pathology_focus: str,
    within_focus: str,
    micro: int,
    patch_size: tuple[int, int, int],
) -> tuple[int, int, int]:
    wall = (seg == 1) | (seg == 4) | (seg == 5)
    background = seg == 0
    if pathology_focus == "scar":
        primary = seg == 5
        fallback = wall | background
    else:
        primary = seg == 4
        fallback = wall
    if within_focus in {"oof_fp", "safe_fp"}:
        mask = background
    elif within_focus in {"boundary", "random_wall"}:
        mask = fallback
    elif within_focus in {"random"}:
        mask = wall | background
    else:
        mask = primary
    if not bool(mask.any()):
        mask = fallback
    coords = np.argwhere(mask)
    if coords.size == 0:
        return tuple(int(v // 2) for v in seg.shape)
    idx = int(hashlib.sha256(f"{descriptor_sha}|micro={micro}|{patch_size}".encode("utf-8")).hexdigest()[:16], 16) % len(coords)
    return tuple(int(v) for v in coords[idx])


def make_batch(descriptor: Any, *, descriptor_sha: str, micro: int, patch_size: tuple[int, int, int], device: torch.device) -> dict[str, torch.Tensor]:
    image = read_b2nd(PREPROCESSED / f"{descriptor.case_id}.b2nd").astype(np.float32, copy=False)
    seg = read_b2nd(PREPROCESSED / f"{descriptor.case_id}_seg.b2nd")[0].astype(np.int64, copy=False)
    center = deterministic_center(
        seg,
        descriptor_sha=descriptor_sha,
        pathology_focus=descriptor.pathology_focus,
        within_focus=descriptor.within_focus,
        micro=micro,
        patch_size=patch_size,
    )
    return {
        "image": torch.from_numpy(crop_or_pad(image, center, patch_size)[None]).to(device=device, dtype=torch.float32),
        "seg": torch.from_numpy(crop_or_pad(seg[None], center, patch_size)[0][None]).to(device=device, dtype=torch.long),
        "availability": torch.tensor([descriptor.availability], device=device, dtype=torch.float32),
    }


def append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _load_previous(path: Path, device: torch.device) -> tuple[torch.nn.Module, dict[str, Any]]:
    model, payload = load_care_ase_checkpoint(path, map_location=device, restore_rng=True)
    return model.to(device), payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--start-step", type=int, required=True)
    parser.add_argument("--end-step", type=int, required=True)
    parser.add_argument("--patch-size", default="20,256,256")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260803)
    parser.add_argument("--resume-checkpoint", type=Path, default=None)
    parser.add_argument("--allow-short-smoke", action="store_true")
    args = parser.parse_args()

    if args.start_step < 0 or args.end_step > 14000 or args.start_step >= args.end_step:
        raise ValueError("CARE-ASE R2 chunk must satisfy 0 <= start < end <= 14000")
    if not args.allow_short_smoke and (args.end_step - args.start_step) != 2000:
        raise ValueError("formal CARE-ASE R2 chunks must be exactly 2000 optimizer steps")
    if not args.allow_short_smoke and args.start_step % 2000 != 0:
        raise ValueError("formal CARE-ASE R2 chunk start must align to 2000 optimizer steps")

    patch_size = parse_patch_size(args.patch_size)
    fold = int(args.fold)
    random.seed(args.seed + fold)
    np.random.seed(args.seed + fold)
    torch.manual_seed(args.seed + fold)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = (args.output_dir or RESULT_DIR / "runtime" / f"fold_{fold}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    lock_dir = out_dir / f"lock_{args.start_step:05d}_{args.end_step:05d}"
    try:
        lock_dir.mkdir()
        write_json(lock_dir / "owner.json", {"pid": os.getpid(), "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"), "fold": fold, "start_step": args.start_step, "end_step": args.end_step})
    except FileExistsError:
        owner = json.loads((lock_dir / "owner.json").read_text(encoding="utf-8")) if (lock_dir / "owner.json").is_file() else {}
        write_json(out_dir / f"lock_lost_{os.getpid()}_{args.start_step:05d}_{args.end_step:05d}.json", {"status": "LOCK_HELD", "owner": owner})
        return 2

    area = compute_actual_train_area_references(REPO_ROOT, fold)
    if args.resume_checkpoint is not None:
        model, prior = _load_previous(args.resume_checkpoint, device)
        if int(prior["global_optimizer_step"]) != int(args.start_step):
            raise RuntimeError(f"resume checkpoint step {prior['global_optimizer_step']} != requested start {args.start_step}")
    elif args.start_step == 0:
        model = build_care_ase_for_fold_with_area_references(
            fold,
            scar_area_reference=area["scar_reference"],
            edema_area_reference=area["edema_reference"],
            map_location="cpu",
        ).to(device)
        prior = None
    else:
        raise RuntimeError("nonzero start-step requires --resume-checkpoint")

    sampler = CAREASEDeterministicSampler(REPO_ROOT, fold, seed=args.seed)
    for step in range(args.start_step):
        sampler.descriptor_for_step(step)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    if prior is not None:
        optimizer.load_state_dict(prior["optimizer"])
        scheduler.load_state_dict(prior["scheduler"])
        sampler.load_state_dict(
            {
                "case_group_cursor": prior["case_group_cursor"],
                "center_cursor": prior["center_cursor"],
                "pathology_focus_cursor": prior["pathology_focus_cursor"],
                "scar_focus_cursor": prior["scar_focus_cursor"],
                "edema_focus_cursor": prior["edema_focus_cursor"],
                "batch_descriptor_cursor": prior["batch_descriptor_cursor"],
            }
        )

    write_json(
        out_dir / f"chunk_start_{args.start_step:05d}_{args.end_step:05d}.json",
        {
            "status": "STARTED",
            "formal_training_entrypoint": "scripts/training/care_ase/run_care_ase_r2_chunk.py",
            "fold": fold,
            "start_step": int(args.start_step),
            "end_step": int(args.end_step),
            "device": str(device),
            "patch_size": list(patch_size),
            "gradient_accumulation": 4,
            "area_reference": area,
            "source_hash": combined_source_hash(),
            "split_hash": sha256_file(SPLITS),
            "plans_hash": sha256_file(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json"),
            "outer_access_before_freeze": 0,
            "fixed_decode_function": decode_care_ase_r2_logits.__name__,
        },
    )

    log_path = out_dir / f"training_log_{args.start_step:05d}_{args.end_step:05d}.csv"
    history: list[dict[str, Any]] = []
    for step in range(int(args.start_step), int(args.end_step)):
        stage = set_stage_trainability(model, global_step=step)
        scheduler.step(step)
        optimizer.zero_grad(set_to_none=True)
        descriptor = sampler.descriptor_for_step(step)
        desc_sha = descriptor.sha256()
        loss_total = 0.0
        metrics: dict[str, float] = {}
        for micro in range(4):
            batch = make_batch(descriptor, descriptor_sha=desc_sha, micro=micro, patch_size=patch_size, device=device)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=(device.type == "cuda")):
                outputs = model(batch["image"], batch["availability"], global_step=step)
                loss, metrics = care_ase_loss(outputs, batch)
            (loss / 4.0).backward()
            loss_total += float(loss.detach().cpu())
        grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], max_norm=12.0)
        optimizer.step()
        row = {
            "optimizer_step": step + 1,
            "stage": stage,
            "case_id": descriptor.case_id,
            "case_group": descriptor.case_group,
            "center": descriptor.center,
            "pathology_focus": descriptor.pathology_focus,
            "within_focus": descriptor.within_focus,
            "descriptor_sha256": desc_sha,
            "loss": loss_total / 4.0,
            "grad_norm": float(grad_norm.detach().cpu() if torch.is_tensor(grad_norm) else grad_norm),
            "lr_new_modules": CAREASEStageScheduler.lr_for(group_name="new_modules", global_step=step),
            "extent_wall_ramp_value": model.extent_wall_ramp(step + 1),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
        }
        append_csv(log_path, row)
        history.append(row)

        if (step + 1) % 1000 == 0 or (step + 1) == int(args.end_step):
            next_descriptor = sampler.peek_descriptor_for_step(step + 1) if (step + 1) < 14000 else None
            sampler_state = sampler.state_dict(next_descriptor=next_descriptor)
            ckpt_name = "checkpoint_step14000.pt" if (step + 1) == 14000 else f"checkpoint_step{step + 1:05d}.pt"
            ckpt = out_dir / ckpt_name
            save_care_ase_checkpoint(
                ckpt,
                model=model,
                optimizer=optimizer,
                scheduler=scheduler,
                global_step=step + 1,
                microbatch_cursor=0,
                stage_id=CAREASEStageScheduler.stage_for_step(step + 1 if step + 1 < 14000 else 13999),
                next_batch_hash=sampler_state.get("next_batch_descriptor_sha256", "TRAINING_COMPLETE"),
                loss_history_tail=history,
                sampler_state=sampler_state,
                code_hash=combined_source_hash(),
                split_hash=sha256_file(SPLITS),
            )
            payload = torch.load(ckpt, map_location="cpu", weights_only=False)
            write_json(out_dir / f"{ckpt.stem}_receipt.json", checkpoint_receipt(ckpt, payload))

    terminal = out_dir / f"checkpoint_step{args.end_step:05d}.pt" if args.end_step < 14000 else out_dir / "checkpoint_step14000.pt"
    payload = torch.load(terminal, map_location="cpu", weights_only=False)
    write_json(
        out_dir / f"chunk_terminal_{args.start_step:05d}_{args.end_step:05d}.json",
        {"status": "PASS", "log_path": str(log_path), **checkpoint_receipt(terminal, payload)},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
