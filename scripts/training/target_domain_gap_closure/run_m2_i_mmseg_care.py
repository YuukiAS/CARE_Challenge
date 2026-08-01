#!/usr/bin/env python3
"""Train or preflight the pinned I-MMSeg CARE adapter on Dataset501 slices."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[3]
PINNED_ROOT = REPO_ROOT / "third_party/I_MMSeg_PINNED"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(PINNED_ROOT) not in sys.path:
    sys.path.insert(0, str(PINNED_ROOT))

from networks.vit_seg_modeling import CONFIGS as CONFIGS_VI_T_SEG  # type: ignore  # noqa: E402
from networks.vit_seg_modeling import VisionTransformer as I_MMSEG_VisionTransformer  # type: ignore  # noqa: E402
from utils import DiceLoss  # type: ignore  # noqa: E402


TASK_KEY = "20260801_care_target_domain_race_gap_closure"
LANE_ID = "M2_I_MMSEG_CARE"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY / "m2_i_mmseg_care"
RUNTIME_ROOT = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK_KEY / "m2_i_mmseg_care"
DATA_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
RELEASED_CKPT = (
    PINNED_ROOT
    / "weights/TU_Myops128/TU_pretrain_R50-ViT-B_16_skip3_epo300_bs24_lr0.001_128/epoch_299.pth"
)
VIT_NPZ = PINNED_ROOT / "model/vit_checkpoint/imagenet21k/R50-ViT-B_16.npz"
TEXT_FEATURES = [
    PINNED_ROOT / "text_features/embedding_class_information.pth",
    PINNED_ROOT / "text_features/embedding_MRI_information.pth",
]


@dataclass(frozen=True)
class SliceSample:
    c0: torch.Tensor
    lge: torch.Tensor
    t2: torch.Tensor
    label4: torch.Tensor
    case_id: str
    z_index: int
    crop_bounds: tuple[int, int, int, int]
    original_hw: tuple[int, int]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    fieldnames = list(row.keys())
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            for name in reader.fieldnames or []:
                if name not in fieldnames:
                    fieldnames.append(name)
            for existing in rows:
                for name in existing:
                    if name not in fieldnames:
                        fieldnames.append(name)
    normalized = [{name: existing.get(name, "") for name in fieldnames} for existing in rows]
    normalized.append({name: row.get(name, "") for name in fieldnames})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized)


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def compact_for_i_mmseg(label: np.ndarray) -> np.ndarray:
    """Map Dataset501 labels to I-MMSeg's 4-class MyoPS convention.

    I-MMSeg uses background, myocardium, scar, edema. Dataset501 labels are
    background, myocardium, LV blood, RV blood, edema, scar.
    """

    out = np.zeros_like(label, dtype=np.int64)
    out[label == 1] = 1
    out[label == 5] = 2
    out[label == 4] = 3
    return out


def center_crop_or_pad_2d(arr: np.ndarray, dim: int) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    h, w = arr.shape[-2:]
    pad_h = max(0, dim - h)
    pad_w = max(0, dim - w)
    if pad_h or pad_w:
        pad_spec = [(0, 0)] * arr.ndim
        pad_spec[-2] = (pad_h // 2, pad_h - pad_h // 2)
        pad_spec[-1] = (pad_w // 2, pad_w - pad_w // 2)
        arr = np.pad(arr, pad_spec, mode="constant")
        h, w = arr.shape[-2:]
    y0 = max(0, (h - dim) // 2)
    x0 = max(0, (w - dim) // 2)
    return arr[..., y0 : y0 + dim, x0 : x0 + dim], (y0, y0 + dim, x0, x0 + dim)


def load_case(case_id: str) -> tuple[np.ndarray, np.ndarray]:
    image = read_b2nd(DATA_ROOT / f"{case_id}.b2nd").astype(np.float32)
    label = read_b2nd(DATA_ROOT / f"{case_id}_seg.b2nd")[0].astype(np.int64)
    return image, label


def load_slice(case_id: str, step: int, dim: int) -> SliceSample:
    image, label = load_case(case_id)
    z = (step + sum(ord(c) for c in case_id)) % image.shape[1]
    crop_img, bounds = center_crop_or_pad_2d(image[:, z], dim)
    crop_lab, _ = center_crop_or_pad_2d(label[z], dim)
    label4 = compact_for_i_mmseg(crop_lab)
    # Official I-MMSeg forward order is bSSFP/C0, LGE, T2w.
    c0 = torch.from_numpy(crop_img[2:3]).unsqueeze(0)
    lge = torch.from_numpy(crop_img[0:1]).unsqueeze(0)
    t2 = torch.from_numpy(crop_img[1:2]).unsqueeze(0)
    return SliceSample(
        c0=c0,
        lge=lge,
        t2=t2,
        label4=torch.from_numpy(label4).unsqueeze(0),
        case_id=case_id,
        z_index=int(z),
        crop_bounds=bounds,
        original_hw=(int(image.shape[2]), int(image.shape[3])),
    )


def build_model(device: torch.device, *, load_released: bool = True) -> I_MMSEG_VisionTransformer:
    config = CONFIGS_VI_T_SEG["R50-ViT-B_16"]
    config.n_classes = 4
    config.n_skip = 3
    config.patches.grid = (8, 8)
    model = I_MMSEG_VisionTransformer(config, img_size=128, num_classes=config.n_classes).to(device)
    if load_released:
        checkpoint = torch.load(RELEASED_CKPT, map_location=device)
        state = {(key[7:] if key.startswith("module.") else key): value for key, value in checkpoint.items()}
        missing, unexpected = model.load_state_dict(state, strict=False)
        if missing or unexpected:
            raise RuntimeError(f"released checkpoint key mismatch: missing={len(missing)} unexpected={len(unexpected)}")
    return model


def model_loss(model: torch.nn.Module, sample: SliceSample, device: torch.device, dice_loss: DiceLoss) -> tuple[torch.Tensor, dict[str, float]]:
    c0 = sample.c0.to(device=device, dtype=torch.float32)
    lge = sample.lge.to(device=device, dtype=torch.float32)
    t2 = sample.t2.to(device=device, dtype=torch.float32)
    label = sample.label4.to(device=device, dtype=torch.long)
    out_pre, dec_seg, _features, _text = model(c0, lge, t2, False)
    out_ce = F.cross_entropy(out_pre, label)
    out_dice = dice_loss(out_pre, label, softmax=True)
    dec_ce = torch.zeros((), device=device)
    dec_dice = torch.zeros((), device=device)
    for dec_pred in dec_seg:
        dec_ce = dec_ce + F.cross_entropy(dec_pred, label)
        dec_dice = dec_dice + dice_loss(dec_pred, label, softmax=True)
    loss = 0.2 * out_ce + 0.8 * out_dice + 0.5 * (0.2 * dec_ce + 0.8 * dec_dice)
    return loss, {
        "out_ce": float(out_ce.detach().cpu()),
        "out_dice": float(out_dice.detach().cpu()),
        "dec_ce": float(dec_ce.detach().cpu()),
        "dec_dice": float(dec_dice.detach().cpu()),
        "total": float(loss.detach().cpu()),
    }


def first_actual_train_case(fold: int) -> str:
    manifest = REPO_ROOT / "results" / TASK_KEY / f"batch_manifest_fold{fold}.jsonl"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            return str(json.loads(line)["case_id"])
    raise RuntimeError(f"empty manifest: {manifest}")


def full_volume_center_crop_inference(model: torch.nn.Module, case_id: str, dim: int, device: torch.device) -> dict[str, Any]:
    image, label = load_case(case_id)
    pred = np.zeros_like(label, dtype=np.uint8)
    model.eval()
    with torch.no_grad():
        for z in range(image.shape[1]):
            crop_img, bounds = center_crop_or_pad_2d(image[:, z], dim)
            y0, y1, x0, x1 = bounds
            c0 = torch.from_numpy(crop_img[2:3]).unsqueeze(0).to(device=device, dtype=torch.float32)
            lge = torch.from_numpy(crop_img[0:1]).unsqueeze(0).to(device=device, dtype=torch.float32)
            t2 = torch.from_numpy(crop_img[1:2]).unsqueeze(0).to(device=device, dtype=torch.float32)
            logits = model(c0, lge, t2, False)
            decoded = torch.argmax(logits, dim=1)[0].detach().cpu().numpy().astype(np.uint8)
            h, w = label.shape[1:]
            yy0, yy1 = max(0, y0), min(h, y1)
            xx0, xx1 = max(0, x0), min(w, x1)
            pred[z, yy0:yy1, xx0:xx1] = decoded[(yy0 - y0) : (yy1 - y0), (xx0 - x0) : (xx1 - x0)]
    return {
        "case_id": case_id,
        "input_shape_zyx": [int(v) for v in label.shape],
        "prediction_shape_zyx": [int(v) for v in pred.shape],
        "unique_pred_labels": [int(v) for v in np.unique(pred)],
        "unique_target_labels_compact4": [int(v) for v in np.unique(compact_for_i_mmseg(label))],
        "center_crop_dim": dim,
        "reconstruction_scope": "slice_wise_center_crop_pasted_to_original_grid_for_preflight_only",
    }


def run_preflight(fold: int, dim: int, overfit_steps: int) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("M2 I-MMSeg preflight requires CUDA because upstream text features are CUDA-serialized")
    for required in [RELEASED_CKPT, VIT_NPZ, *TEXT_FEATURES]:
        if not required.exists():
            raise FileNotFoundError(required)
    device = torch.device("cuda")
    case_id = first_actual_train_case(fold)
    sample = load_slice(case_id, step=1, dim=dim)
    model = build_model(device, load_released=True)
    dice_loss = DiceLoss(4)
    model.train()
    loss, loss_terms = model_loss(model, sample, device, dice_loss)
    finite_loss = bool(torch.isfinite(loss).detach().cpu().item())
    loss.backward()
    grad_norm = 0.0
    grad_tensors = 0
    for param in model.parameters():
        if param.grad is not None:
            grad_tensors += 1
            grad_norm += float(param.grad.detach().norm().cpu())
    opt = torch.optim.AdamW(model.parameters(), lr=1.0e-5, weight_decay=1.0e-4)
    initial_loss = float(loss.detach().cpu())
    final_loss = initial_loss
    for _ in range(overfit_steps):
        opt.zero_grad(set_to_none=True)
        step_loss, _ = model_loss(model, sample, device, dice_loss)
        step_loss.backward()
        opt.step()
        final_loss = float(step_loss.detach().cpu())
    ckpt_path = RUNTIME_ROOT / "preflight" / f"fold{fold}_save_reload.pt"
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    with torch.no_grad():
        c0 = sample.c0.to(device=device, dtype=torch.float32)
        lge = sample.lge.to(device=device, dtype=torch.float32)
        t2 = sample.t2.to(device=device, dtype=torch.float32)
        before = model(c0, lge, t2, False).detach().cpu()
    torch.save({"model": model.state_dict(), "fold": fold, "created_at": now_utc()}, ckpt_path)
    reloaded = build_model(device, load_released=False)
    reloaded.load_state_dict(torch.load(ckpt_path, map_location=device)["model"])
    reloaded.eval()
    with torch.no_grad():
        after = reloaded(c0, lge, t2, False).detach().cpu()
    max_abs = float((before - after).abs().max().item())
    volume_report = full_volume_center_crop_inference(model, case_id, dim, device)
    return {
        "created_at": now_utc(),
        "lane_id": LANE_ID,
        "fold": fold,
        "status": "PREFLIGHT_PASS_READY_FOR_HTZHULAB_TRAINING",
        "domain_evidence_label": "PREFLIGHT_SMOKE_ONLY",
        "formal_training_credit": False,
        "device": torch.cuda.get_device_name(0),
        "case_id": sample.case_id,
        "z_index": sample.z_index,
        "input_order_to_model": ["C0/bSSFP", "LGE", "T2w"],
        "source_input_order": ["LGE", "T2", "C0"],
        "label_mapping": {"0": "background_or_blood", "1": "myocardium", "2": "scar_from_label5", "3": "edema_from_label4"},
        "finite_loss": finite_loss,
        "loss_terms": loss_terms,
        "gradient_tensors": grad_tensors,
        "gradient_norm_sum": grad_norm,
        "one_batch_overfit": {"steps": overfit_steps, "initial_loss": initial_loss, "final_loss": final_loss},
        "save_reload_max_abs_diff": max_abs,
        "save_reload_pass": max_abs <= 1.0e-6,
        "full_volume_one_case_inference": volume_report,
        "released_checkpoint_path": str(RELEASED_CKPT.relative_to(REPO_ROOT)),
        "vit_npz_path": str(VIT_NPZ.relative_to(REPO_ROOT)),
        "rank_channel_substitute_used": False,
        "runtime_gpt_call_used": False,
        "next_required_action": "submit/run M2 fold2+fold3 training, then checkpoint reload and canonical full-volume evaluation",
    }


def train_fold(fold: int, epochs: int, steps_per_epoch: int, dim: int, lr: float) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("M2 I-MMSeg training requires CUDA")
    device = torch.device("cuda")
    manifest_path = REPO_ROOT / "results" / TASK_KEY / f"batch_manifest_fold{fold}.jsonl"
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    model = build_model(device, load_released=True)
    dice_loss = DiceLoss(4)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1.0e-4)
    ckpt_dir = RUNTIME_ROOT / f"fold{fold}" / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    append_csv(
        RESULT_ROOT / "training_accounting.csv",
        {
            "fold": fold,
            "event": "start",
            "timestamp": now_utc(),
            "epochs": epochs,
            "steps_per_epoch": steps_per_epoch,
            "dim": dim,
            "lr": lr,
            "device": torch.cuda.get_device_name(0),
        },
    )
    last_loss = None
    total_steps = epochs * steps_per_epoch
    model.train()
    for step_idx in range(total_steps):
        row = rows[step_idx % len(rows)]
        sample = load_slice(str(row["case_id"]), int(row["step"]), dim)
        opt.zero_grad(set_to_none=True)
        loss, _terms = model_loss(model, sample, device, dice_loss)
        loss.backward()
        opt.step()
        last_loss = float(loss.detach().cpu())
        step = step_idx + 1
        if step % steps_per_epoch == 0:
            append_csv(
                RESULT_ROOT / "training_accounting.csv",
                {
                    "fold": fold,
                    "event": "epoch",
                    "timestamp": now_utc(),
                    "epoch": step // steps_per_epoch,
                    "step": step,
                    "loss": last_loss,
                    "device": torch.cuda.get_device_name(0),
                },
            )
        if step % 500 == 0 or step == total_steps:
            torch.save({"model": model.state_dict(), "optimizer": opt.state_dict(), "step": step, "fold": fold}, ckpt_dir / f"checkpoint_step{step:05d}.pt")
    receipt = {
        "created_at": now_utc(),
        "lane_id": LANE_ID,
        "fold": fold,
        "status": "TRAINING_COMPLETE",
        "formal_training_credit": epochs >= 60,
        "epochs": epochs,
        "steps_per_epoch": steps_per_epoch,
        "checkpoint_dir": str(ckpt_dir),
        "last_loss": last_loss,
        "device": torch.cuda.get_device_name(0),
        "batch_manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "released_checkpoint_init": str(RELEASED_CKPT.relative_to(REPO_ROOT)),
        "rank_channel_substitute_used": False,
        "runtime_gpt_call_used": False,
        "myops380_dataset_used": False,
    }
    write_json(RESULT_ROOT / f"fold{fold}_training_receipt.json", receipt)
    append_csv(
        RESULT_ROOT / "training_accounting.csv",
        {"fold": fold, "event": "complete", "timestamp": receipt["created_at"], "epochs": epochs, "steps": total_steps, "loss": last_loss, "device": torch.cuda.get_device_name(0)},
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, choices=[2, 3], default=2)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--steps-per-epoch", type=int, default=100)
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1.0e-5)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--overfit-steps", type=int, default=3)
    args = parser.parse_args()
    if args.preflight_only:
        payload = run_preflight(args.fold, args.dim, args.overfit_steps)
        write_json(RESULT_ROOT / "adapter_preflight_report.json", payload)
    else:
        payload = train_fold(args.fold, args.epochs, args.steps_per_epoch, args.dim, args.lr)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
