#!/usr/bin/env python3
"""Train the pinned MyoPS-Net C0/LGE/T2-only CARE adapter on Dataset501 slices."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import blosc2
import numpy as np
import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[3]
PINNED_ROOT = REPO_ROOT / "third_party/MyoPS-Net_PINNED"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(PINNED_ROOT) not in sys.path:
    sys.path.insert(0, str(PINNED_ROOT))

from network.unet import UNet, UNetDecoderPlus, UNetEncoder  # type: ignore  # noqa: E402


TASK_KEY = "20260801_care_target_domain_race_gap_closure"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY / "m1_myopsnet_l_care"
RUNTIME_ROOT = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK_KEY / "m1_myopsnet_l_care"
DATA_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"


class CARETriModalMyoPSNet(torch.nn.Module):
    """C0/LGE/T2-only CARE adapter using pinned MyoPS-Net components."""

    def __init__(self) -> None:
        super().__init__()
        self.unet_C0 = UNet(in_ch=3, out_ch=6)
        self.encoder_LGE = UNetEncoder(in_ch=2)
        self.decoder_LGE = UNetDecoderPlus(out_ch=2)
        self.encoder_T2 = UNetEncoder(in_ch=2)
        self.decoder_T2 = UNetDecoderPlus(out_ch=2)

    def forward(self, c0: torch.Tensor, lge: torch.Tensor, t2: torch.Tensor):
        image = torch.cat([c0, lge, t2], dim=1)
        seg_c0 = self.unet_C0(image)
        mask_c0 = torch.argmax(seg_c0, dim=1, keepdim=True)
        f_lge = self.encoder_LGE(torch.cat([lge, mask_c0.detach()], dim=1))
        f_t2 = self.encoder_T2(torch.cat([t2, mask_c0.detach()], dim=1))
        seg_lge = self.decoder_LGE(list(f_t2), f_lge)
        seg_t2 = self.decoder_T2(list(f_lge), f_t2)
        return seg_c0, seg_lge, seg_t2


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


def load_slice(case_id: str, step: int, dim: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    data = read_b2nd(DATA_ROOT / f"{case_id}.b2nd")
    seg = read_b2nd(DATA_ROOT / f"{case_id}_seg.b2nd")[0].astype(np.int64)
    z = (step + sum(ord(c) for c in case_id)) % data.shape[1]
    image = data[:, z]
    label = seg[z]
    pad_y = max(0, dim - image.shape[1])
    pad_x = max(0, dim - image.shape[2])
    if pad_y or pad_x:
        image = np.pad(image, [(0, 0), (pad_y // 2, pad_y - pad_y // 2), (pad_x // 2, pad_x - pad_x // 2)], mode="constant")
        label = np.pad(label, [(pad_y // 2, pad_y - pad_y // 2), (pad_x // 2, pad_x - pad_x // 2)], mode="constant")
    y0 = max(0, (image.shape[1] - dim) // 2)
    x0 = max(0, (image.shape[2] - dim) // 2)
    image = image[:, y0 : y0 + dim, x0 : x0 + dim]
    label = label[y0 : y0 + dim, x0 : x0 + dim]
    lge = torch.from_numpy(image[0:1]).unsqueeze(0)
    t2 = torch.from_numpy(image[1:2]).unsqueeze(0)
    c0 = torch.from_numpy(image[2:3]).unsqueeze(0)
    return c0, lge, t2, torch.from_numpy(label).unsqueeze(0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=[2, 3])
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--steps-per-epoch", type=int, default=100)
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1.0e-4)
    args = parser.parse_args()

    manifest_path = REPO_ROOT / "results" / TASK_KEY / f"batch_manifest_fold{args.fold}.jsonl"
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CARETriModalMyoPSNet().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=5.0e-4)
    ckpt_dir = RUNTIME_ROOT / f"fold{args.fold}" / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    append_csv(RESULT_ROOT / "training_accounting.csv", {"fold": args.fold, "event": "start", "timestamp": now_utc(), "epochs": args.epochs, "steps_per_epoch": args.steps_per_epoch, "device": str(device)})
    last_loss = None
    total_steps = args.epochs * args.steps_per_epoch
    for step_idx in range(total_steps):
        row = rows[step_idx % len(rows)]
        c0, lge, t2, labels = load_slice(row["case_id"], int(row["step"]), args.dim)
        c0 = c0.to(device=device, dtype=torch.float32)
        lge = lge.to(device=device, dtype=torch.float32)
        t2 = t2.to(device=device, dtype=torch.float32)
        labels = labels.to(device=device)
        opt.zero_grad(set_to_none=True)
        seg_c0, seg_lge, seg_t2 = model(c0, lge, t2)
        scar_target = (labels == 5).long()
        edema_target = (labels == 4).long()
        loss = F.nll_loss(torch.log(seg_c0.clamp_min(1e-6)), labels.clamp(0, 5))
        loss = loss + F.nll_loss(torch.log(seg_lge.clamp_min(1e-6)), scar_target)
        loss = loss + F.nll_loss(torch.log(seg_t2.clamp_min(1e-6)), edema_target)
        loss.backward()
        opt.step()
        last_loss = float(loss.detach().cpu())
        step = step_idx + 1
        if step % args.steps_per_epoch == 0:
            epoch = step // args.steps_per_epoch
            append_csv(RESULT_ROOT / "training_accounting.csv", {"fold": args.fold, "event": "epoch", "timestamp": now_utc(), "epoch": epoch, "step": step, "loss": last_loss, "device": str(device)})
        if step % 500 == 0 or step == total_steps:
            torch.save({"model": model.state_dict(), "optimizer": opt.state_dict(), "step": step, "fold": args.fold}, ckpt_dir / f"checkpoint_step{step:05d}.pt")
    receipt = {
        "created_at": now_utc(),
        "lane_id": "M1_MYOPSNET_L_CARE",
        "fold": args.fold,
        "status": "TRAINING_COMPLETE",
        "formal_training_credit": args.epochs >= 60,
        "epochs": args.epochs,
        "steps_per_epoch": args.steps_per_epoch,
        "checkpoint_dir": str(ckpt_dir),
        "last_loss": last_loss,
        "device": str(device),
        "batch_manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "adapter": "CARETriModalMyoPSNet_from_pinned_official_components",
        "uses_t1_or_t2star_placeholders": False,
    }
    write_json(RESULT_ROOT / f"fold{args.fold}_training_receipt.json", receipt)
    append_csv(RESULT_ROOT / "training_accounting.csv", {"fold": args.fold, "event": "complete", "timestamp": receipt["created_at"], "epochs": args.epochs, "steps": total_steps, "loss": last_loss, "device": str(device)})
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
