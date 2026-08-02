#!/usr/bin/env python
"""Formal CARE-ASE fold training entrypoint."""

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

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.data.care_ase_splits import actual_train_cases
from src.care_myocardium.models.care_ase import CAREASEConfig, build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import (
    build_optimizer,
    care_ase_loss,
    checkpoint_receipt,
    save_care_ase_checkpoint,
    set_stage_trainability,
    write_json,
)


PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
SPLITS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
RESULT_DIR = REPO_ROOT / "results/20260801_care_ase_final_model"


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def parse_patch_size(text: str) -> tuple[int, int, int]:
    parts = tuple(int(v) for v in text.replace("x", ",").split(",") if v)
    if len(parts) != 3:
        raise ValueError(f"patch size must have 3 dimensions, got {text}")
    return parts


def crop_or_pad(array: np.ndarray, center: tuple[int, int, int], patch_size: tuple[int, int, int]) -> np.ndarray:
    spatial = array.shape[-3:]
    src_slices = []
    dst_slices = []
    for c, dim, size in zip(center, spatial, patch_size):
        start = int(c) - size // 2
        stop = start + size
        src_start = max(0, start)
        src_stop = min(dim, stop)
        dst_start = src_start - start
        dst_stop = dst_start + (src_stop - src_start)
        src_slices.append(slice(src_start, src_stop))
        dst_slices.append(slice(dst_start, dst_stop))
    out_shape = array.shape[:-3] + patch_size
    out = np.zeros(out_shape, dtype=array.dtype)
    out[(..., *dst_slices)] = array[(..., *src_slices)]
    return out


def deterministic_center(seg: np.ndarray, *, case_id: str, step: int, micro: int, patch_size: tuple[int, int, int]) -> tuple[int, int, int]:
    targets = [
        seg == 5,
        seg == 4,
        (seg == 1) | (seg == 4) | (seg == 5),
        seg == 0,
    ]
    mask = targets[(int(step) + int(micro)) % len(targets)]
    coords = np.argwhere(mask)
    if coords.size == 0:
        return tuple(int(v // 2) for v in seg.shape)
    key = f"{case_id}|{step}|{micro}|{patch_size}"
    index = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16) % len(coords)
    return tuple(int(v) for v in coords[index])


def make_batch(case_id: str, availability: tuple[float, float, float], *, step: int, micro: int, patch_size: tuple[int, int, int], device: torch.device) -> dict[str, torch.Tensor]:
    data = read_b2nd(PREPROCESSED / f"{case_id}.b2nd").astype(np.float32, copy=False)
    seg = read_b2nd(PREPROCESSED / f"{case_id}_seg.b2nd")[0].astype(np.int64, copy=False)
    center = deterministic_center(seg, case_id=case_id, step=step, micro=micro, patch_size=patch_size)
    image_patch = crop_or_pad(data, center, patch_size)
    seg_patch = crop_or_pad(seg[None], center, patch_size)[0]
    return {
        "image": torch.from_numpy(image_patch[None]).to(device=device, dtype=torch.float32),
        "seg": torch.from_numpy(seg_patch[None]).to(device=device, dtype=torch.long),
        "availability": torch.tensor([availability], device=device, dtype=torch.float32),
    }


def append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def batch_hash(case_id: str, step: int, micro: int, patch_size: tuple[int, int, int]) -> str:
    return hashlib.sha256(f"{case_id}|{step}|{micro}|{patch_size}".encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--optimizer-steps", type=int, default=14000)
    parser.add_argument("--patch-size", default="20,256,256")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260801)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--save-every", type=int, default=1000)
    args = parser.parse_args()

    if int(args.optimizer_steps) != 14000:
        raise ValueError("formal CARE-ASE training requires exactly 14000 optimizer steps")
    patch_size = parse_patch_size(args.patch_size)
    random.seed(args.seed + args.fold)
    np.random.seed(args.seed + args.fold)
    torch.manual_seed(args.seed + args.fold)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    output_dir = (args.output_dir or RESULT_DIR / "runtime" / f"fold_{args.fold}").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    lock_dir = output_dir / "atomic_lock"
    try:
        lock_dir.mkdir()
        write_json(lock_dir / "owner.json", {"pid": os.getpid(), "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"), "fold": args.fold})
    except FileExistsError:
        owner = json.loads((lock_dir / "owner.json").read_text(encoding="utf-8")) if (lock_dir / "owner.json").exists() else {}
        write_json(output_dir / f"lock_lost_{os.getpid()}.json", {"status": "LOCK_HELD", "owner": owner})
        return 2

    model = build_care_ase_for_fold(args.fold, map_location="cpu").to(device)
    set_stage_trainability(model, global_step=6000)
    optimizer = build_optimizer(model)
    start_step = 0
    history: list[dict[str, Any]] = []
    latest = output_dir / "checkpoint_latest.pt"
    if args.resume and latest.exists():
        payload = torch.load(latest, map_location=device, weights_only=False)
        model.load_state_dict(payload["model_state_dict"])
        optimizer.load_state_dict(payload["optimizer_state_dict"])
        start_step = int(payload["global_optimizer_step"])
        history = list(payload.get("loss_history_tail", []))
    cases = actual_train_cases(REPO_ROOT, args.fold, complete_only=True)
    write_json(
        output_dir / "training_start_receipt.json",
        {
            "status": "STARTED",
            "fold": int(args.fold),
            "device": str(device),
            "patch_size": list(patch_size),
            "optimizer_steps_required": 14000,
            "gradient_accumulation": CAREASEConfig.for_fold(args.fold).gradient_accumulation,
            "actual_train_complete_case_count": len(cases),
            "case_ids": [case_id for case_id, _ in cases],
            "inner_excluded": True,
            "split_authority": "src.care_myocardium.data.care_ase_splits.actual_train_cases",
        },
    )

    scaler_enabled = False
    log_path = output_dir / "training_log.csv"
    for step in range(start_step, int(args.optimizer_steps)):
        stage = set_stage_trainability(model, global_step=step)
        optimizer.zero_grad(set_to_none=True)
        step_loss = 0.0
        last_case = ""
        for micro in range(4):
            case_id, availability = cases[(step * 4 + micro) % len(cases)]
            last_case = case_id
            batch = make_batch(case_id, availability, step=step, micro=micro, patch_size=patch_size, device=device)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=(device.type == "cuda")):
                outputs = model(batch["image"], batch["availability"], global_step=step)
                loss, metrics = care_ase_loss(outputs, batch)
                scaled = loss / 4.0
            scaled.backward()
            step_loss += float(loss.detach().cpu())
        grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], max_norm=12.0)
        optimizer.step()
        row = {
            "optimizer_step": step + 1,
            "stage": stage,
            "case_id": last_case,
            "loss": step_loss / 4.0,
            "grad_norm": float(grad_norm.detach().cpu() if torch.is_tensor(grad_norm) else grad_norm),
            "extent_wall_ramp_value": model.extent_wall_ramp(step + 1),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
            "cuda": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        }
        append_csv(log_path, row)
        history.append(row)
        next_case, _ = cases[((step + 1) * 4) % len(cases)]
        if (step + 1) % int(args.save_every) == 0 or (step + 1) == int(args.optimizer_steps):
            ckpt_name = "checkpoint_step14000.pt" if (step + 1) == 14000 else f"checkpoint_step{step + 1:05d}.pt"
            ckpt = output_dir / ckpt_name
            save_care_ase_checkpoint(
                ckpt,
                model=model,
                optimizer=optimizer,
                global_step=step + 1,
                microbatch_cursor=0,
                stage_id=stage,
                next_batch_hash=batch_hash(next_case, step + 1, 0, patch_size),
                loss_history_tail=history,
            )
            latest.unlink(missing_ok=True)
            latest.symlink_to(ckpt.name)
            payload = torch.load(ckpt, map_location="cpu", weights_only=False)
            write_json(output_dir / f"{ckpt.stem}_receipt.json", checkpoint_receipt(ckpt, payload))

    terminal = output_dir / "checkpoint_step14000.pt"
    payload = torch.load(terminal, map_location="cpu", weights_only=False)
    write_json(output_dir / "training_terminal_receipt.json", {"status": "PASS", **checkpoint_receipt(terminal, payload), "log_path": str(log_path.relative_to(REPO_ROOT))})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
