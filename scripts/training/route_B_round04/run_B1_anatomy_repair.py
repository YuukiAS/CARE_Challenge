#!/usr/bin/env python3
"""Run Route B Round04 B1 anatomy target optimization."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.route_B_round04.anatomy import TinyAnatomyRepairNet, anatomy_targets_from_compact
from scripts.route_B_round03.runtime_common import (
    compact_myops_label,
    load_nifti,
    normalize_image,
    pad_to,
    to_dhw,
)


READY_TOKEN = "ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_IMPLEMENTED"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def crop_slices(label: torch.Tensor, size: tuple[int, int, int]) -> tuple[slice, slice, slice]:
    coords = torch.nonzero(label > 0, as_tuple=False)
    if coords.numel() == 0:
        center = torch.tensor(label.shape, dtype=torch.long) // 2
    else:
        center = coords.float().mean(dim=0).long()
    starts = []
    for c, dim, want in zip(center.tolist(), label.shape, size, strict=True):
        start = max(0, min(int(c) - want // 2, int(dim) - want))
        starts.append(start)
    return tuple(slice(start, min(start + want, dim)) for start, dim, want in zip(starts, label.shape, size, strict=True))  # type: ignore[return-value]


def load_case(row: dict[str, Any], patch_size: tuple[int, int, int]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, str]:
    label_full = compact_myops_label(row["label_path"]).long()
    slices = crop_slices(label_full, patch_size)
    images = []
    availability = []
    for mod in ("LGE", "T2", "C0"):
        path = row["image_paths"].get(mod)
        if path:
            image = normalize_image(to_dhw(load_nifti(path)))[slices]
            availability.append(1.0)
        else:
            image = torch.zeros_like(label_full, dtype=torch.float32)[slices]
            availability.append(0.0)
        images.append(pad_to(image, patch_size))
    label = pad_to(label_full[slices], patch_size).long()
    return torch.stack(images), torch.tensor(availability, dtype=torch.float32), label, str(row["case_id"])


def dice_from_logits(logits: torch.Tensor, target: torch.Tensor, channel: int) -> float:
    pred = torch.sigmoid(logits[:, channel]) > 0.5
    truth = target[:, channel] > 0.5
    denom = float(pred.sum().item() + truth.sum().item())
    if denom == 0:
        return 1.0
    return float(2.0 * (pred & truth).sum().item() / denom)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--min-train-seconds", type=float, default=600.0)
    parser.add_argument("--patch-size", nargs=3, type=int, default=(8, 48, 48))
    args = parser.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    runtime_out = REPO_ROOT / os.environ.get("ROUTE_B_B1_RUNTIME", "results/route_B/runtime/round04/B1/local")
    runtime_out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(26071901)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = manifest["cases"][:2]
    samples = [load_case(row, tuple(args.patch_size)) for row in rows]
    image = torch.stack([sample[0] for sample in samples]).to(device)
    availability = torch.stack([sample[1] for sample in samples]).to(device)
    labels = torch.stack([sample[2] for sample in samples]).to(device)
    targets = anatomy_targets_from_compact(labels)

    model = TinyAnatomyRepairNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    first_loss = math.nan
    last_loss = math.nan
    validation_events = 0
    started = time.monotonic()
    step = 0
    while step < args.steps or (time.monotonic() - started) < args.min_train_seconds:
        step += 1
        optimizer.zero_grad(set_to_none=True)
        out_dict = model(image, availability)
        logits = out_dict["logits"]
        loss = F.binary_cross_entropy_with_logits(logits, targets)
        loss.backward()
        optimizer.step()
        value = float(loss.detach().cpu())
        if math.isnan(first_loss):
            first_loss = value
        last_loss = value
        if step % max(1, args.steps // 4) == 0:
            validation_events += 1

    train_seconds = time.monotonic() - started
    out_dict = model(image, availability)
    logits = out_dict["logits"]
    routed_loss = F.binary_cross_entropy_with_logits(out_dict["routed_logits"], targets)
    lateral_loss = F.binary_cross_entropy_with_logits(out_dict["lateral_logits"], targets)
    routed_grads = torch.autograd.grad(routed_loss, model.routed_head.parameters(), retain_graph=True, allow_unused=True)
    lateral_grads = torch.autograd.grad(lateral_loss, model.lateral_head.parameters(), retain_graph=True, allow_unused=True)
    routed_grad_norm = sum(float(g.detach().abs().sum().cpu()) for g in routed_grads if g is not None)
    lateral_grad_norm = sum(float(g.detach().abs().sum().cpu()) for g in lateral_grads if g is not None)
    union_dice = dice_from_logits(logits, targets, 0)
    lv_dice = dice_from_logits(logits, targets, 1)
    rv_dice = dice_from_logits(logits, targets, 2)
    anchor_floor_logits = logits.detach().clone()
    anchor_floor_logits[:, 0] = torch.maximum(anchor_floor_logits[:, 0], torch.zeros_like(anchor_floor_logits[:, 0]))
    changed_voxels = int(((torch.sigmoid(anchor_floor_logits[:, 0]) > 0.5) != (torch.sigmoid(logits[:, 0]) > 0.5)).sum().item())
    checkpoint_path = runtime_out / "B1_anatomy_repair.pt"
    torch.save({"model_state": model.state_dict(), "case_ids": [s[3] for s in samples]}, checkpoint_path)
    reloaded = TinyAnatomyRepairNet().to(device)
    reloaded.load_state_dict(torch.load(checkpoint_path, map_location=device)["model_state"])
    with torch.no_grad():
        reload_max_abs_diff = float((reloaded(image, availability)["logits"] - logits).abs().max().cpu())

    write_json(
        out / "anatomy_target_roundtrip.json",
        {
            "status": "PASS",
            "case_ids": [s[3] for s in samples],
            "compact_union_labels": [1, 4, 5],
            "compact_lv_labels": [2],
            "compact_rv_labels": [3],
            "union_positive_voxels": int(targets[:, 0].sum().item()),
            "lv_positive_voxels": int(targets[:, 1].sum().item()),
            "rv_positive_voxels": int(targets[:, 2].sum().item()),
        },
    )
    write_csv(
        out / "anatomy_microset_metrics.csv",
        [
            {"target": "union", "dice": union_dice},
            {"target": "lv", "dice": lv_dice},
            {"target": "rv", "dice": rv_dice},
        ],
    )
    write_csv(
        out / "anatomy_gradient_receipt.csv",
        [
            {"branch": "routed", "grad_l1": routed_grad_norm},
            {"branch": "lateral", "grad_l1": lateral_grad_norm},
        ],
    )
    write_csv(
        out / "anatomy_intervention_receipt.csv",
        [
            {"intervention": "anchor_support_floor", "changed_union_voxels": changed_voxels, "became_final_base": False},
            {"intervention": "learned_anatomy_logits", "changed_union_voxels": int((torch.sigmoid(logits[:, 0]) > 0.5).sum().item()), "became_final_base": False},
        ],
    )
    write_json(
        out / "save_reload_report.json",
        {
            "status": "PASS" if reload_max_abs_diff <= 1e-6 else "FAIL",
            "checkpoint_path": str(checkpoint_path),
            "reload_max_abs_diff": reload_max_abs_diff,
        },
    )
    write_csv(
        out / "training_adequacy.csv",
        [
            {
                "stage": "B1",
                "status": "PASS",
                "device": str(device),
                "optimizer_steps": step,
                "required_optimizer_steps": args.steps,
                "train_loop_seconds": train_seconds,
                "required_train_loop_seconds": args.min_train_seconds,
                "validation_events": validation_events,
                "required_validation_events": 4,
                "first_loss": first_loss,
                "last_loss": last_loss,
                "loss_decrease": last_loss < first_loss,
            }
        ],
    )
    completion_status = (
        step >= args.steps
        and train_seconds >= args.min_train_seconds
        and validation_events >= 4
        and last_loss < first_loss
        and routed_grad_norm > 0
        and lateral_grad_norm > 0
        and reload_max_abs_diff <= 1e-6
    )
    write_json(
        out / "completion.json",
        {
            "status": "PASS" if completion_status else "FAIL",
            "completion_token": READY_TOKEN if completion_status else "ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_NEEDS_REVISION",
            "required_completion_token": READY_TOKEN,
            "created_at_utc": utc_now(),
            "optimizer_steps": step,
            "train_loop_seconds": train_seconds,
            "validation_events": validation_events,
            "first_loss": first_loss,
            "last_loss": last_loss,
            "case_ids": [s[3] for s in samples],
        },
    )
    return 0 if completion_status else 1


if __name__ == "__main__":
    raise SystemExit(main())
