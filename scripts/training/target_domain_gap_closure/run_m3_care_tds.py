#!/usr/bin/env python3
"""Train CARE-TDS M3 heads on Dataset501 target-domain patches."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import blosc2
import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.target_domain_gap_closure import CARETargetDomainSpecialist, care_tds_loss  # noqa: E402


TASK_KEY = "20260801_care_target_domain_race_gap_closure"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY / "m3_care_tds"
RUNTIME_ROOT = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK_KEY / "m3_care_tds"
DATA_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def append_csv(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()), lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def crop_or_pad(arr: np.ndarray, out_shape: tuple[int, int, int], seed: int) -> np.ndarray:
    channels = arr.shape[0]
    spatial = arr.shape[1:]
    pads = []
    for dim, target in zip(spatial, out_shape):
        extra = max(0, target - dim)
        pads.append((extra // 2, extra - extra // 2))
    if any(a or b for a, b in pads):
        arr = np.pad(arr, [(0, 0), *pads], mode="constant")
        spatial = arr.shape[1:]
    starts = []
    value = seed
    for dim, target in zip(spatial, out_shape):
        max_start = max(0, dim - target)
        starts.append(value % (max_start + 1))
        value = value * 1103515245 + 12345
    z, y, x = starts
    dz, dy, dx = out_shape
    return arr[:, z : z + dz, y : y + dy, x : x + dx].reshape((channels, dz, dy, dx))


def load_patch(case_id: str, step: int, patch_size: tuple[int, int, int]) -> tuple[torch.Tensor, torch.Tensor]:
    data = read_b2nd(DATA_ROOT / f"{case_id}.b2nd")
    seg = read_b2nd(DATA_ROOT / f"{case_id}_seg.b2nd")
    seed = int(sum(ord(c) for c in case_id) + step * 7919)
    image_patch = crop_or_pad(data, patch_size, seed)
    label_patch = crop_or_pad(seg, patch_size, seed)[0].astype(np.int64)
    return torch.from_numpy(image_patch).unsqueeze(0), torch.from_numpy(label_patch).unsqueeze(0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=[2, 3])
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument("--save-every", type=int, default=500)
    parser.add_argument("--lr", type=float, default=1.0e-4)
    parser.add_argument("--patch-size", default="16,64,64")
    args = parser.parse_args()

    manifest_path = REPO_ROOT / "results" / TASK_KEY / f"batch_manifest_fold{args.fold}.jsonl"
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    patch_size = tuple(int(v) for v in args.patch_size.split(","))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CARETargetDomainSpecialist(fold=args.fold, map_location=device).to(device)
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.lr, weight_decay=1.0e-4)
    ckpt_dir = RUNTIME_ROOT / f"fold{args.fold}" / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    append_csv(RESULT_ROOT / "training_accounting.csv", {"fold": args.fold, "event": "start", "timestamp": now_utc(), "steps": args.steps, "device": str(device)})
    last_loss = None
    for i in range(args.steps):
        row = rows[i % len(rows)]
        images, labels = load_patch(row["case_id"], int(row["step"]), patch_size)
        images = images.to(device=device, dtype=torch.float32)
        labels = labels.to(device=device)
        opt.zero_grad(set_to_none=True)
        losses = care_tds_loss(model(images), labels)
        losses["total"].backward()
        opt.step()
        last_loss = float(losses["total"].detach().cpu())
        step = i + 1
        if step % args.save_every == 0 or step == args.steps:
            torch.save({"model": model.state_dict(), "optimizer": opt.state_dict(), "step": step, "fold": args.fold}, ckpt_dir / f"checkpoint_step{step:05d}.pt")
            append_csv(RESULT_ROOT / "training_accounting.csv", {"fold": args.fold, "event": "checkpoint", "timestamp": now_utc(), "steps": step, "device": str(device), "loss": last_loss})
    receipt = {
        "created_at": now_utc(),
        "lane_id": "M3_CARE_TDS",
        "fold": args.fold,
        "status": "TRAINING_COMPLETE",
        "formal_training_credit": args.steps >= 4000,
        "optimizer_steps": args.steps,
        "checkpoint_dir": str(ckpt_dir),
        "last_loss": last_loss,
        "device": str(device),
        "batch_manifest": str(manifest_path.relative_to(REPO_ROOT)),
    }
    write_json(RESULT_ROOT / f"fold{args.fold}_training_receipt.json", receipt)
    append_csv(RESULT_ROOT / "training_accounting.csv", {"fold": args.fold, "event": "complete", "timestamp": receipt["created_at"], "steps": args.steps, "device": str(device), "loss": last_loss})
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
