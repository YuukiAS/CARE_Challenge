#!/usr/bin/env python
"""User-authorized CARE-ASE outer diagnostic comparison.

This is not the formal one-time W5 evaluator. It exists for the deadline
recovery controller after explicit user override, and writes casewise CARE-ASE
vs same-fold stock nnU-Net metrics on the fold validation split.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pickle
import statistics
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
from scipy import ndimage

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
from src.care_myocardium.inference.care_ase_r2_full_volume import (
    CAREASEFullVolumeInferenceSettings,
    predict_care_ase_r2_full_volume_logits,
)
from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint_for_inference


PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
STOCK_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
SPLITS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def dice_for_class(pred: np.ndarray, gt: np.ndarray, cls: int) -> float:
    p = pred == cls
    g = gt == cls
    denom = int(p.sum() + g.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(p, g).sum() / denom)


def sensitivity_for_class(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    g = gt == cls
    total = int(g.sum())
    if total == 0:
        return None
    return float(np.logical_and(pred == cls, g).sum() / total)


def precision_for_class(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    p = pred == cls
    total = int(p.sum())
    if total == 0:
        return None
    return float(np.logical_and(p, gt == cls).sum() / total)


def hd95_for_class(pred: np.ndarray, gt: np.ndarray, cls: int, spacing: tuple[float, float, float]) -> float:
    p = pred == cls
    g = gt == cls
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return 1.0e6
    p_border = p ^ ndimage.binary_erosion(p)
    g_border = g ^ ndimage.binary_erosion(g)
    values = np.concatenate(
        [
            ndimage.distance_transform_edt(~g_border, sampling=spacing)[p_border],
            ndimage.distance_transform_edt(~p_border, sampling=spacing)[g_border],
        ]
    )
    return float(np.percentile(values, 95)) if values.size else 0.0


def mean(values: list[Any]) -> float | None:
    clean = [float(v) for v in values if v not in ("", None)]
    return statistics.fmean(clean) if clean else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--checkpoint-step", type=int, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--decision", default="USER_OVERRIDE_OUTER_DIAGNOSTIC")
    args = parser.parse_args()

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, payload = load_care_ase_checkpoint_for_inference(args.checkpoint, map_location=device)
    model.to(device).eval()
    if int(payload.get("global_optimizer_step", -1)) != int(args.checkpoint_step):
        raise RuntimeError(
            f"checkpoint step mismatch: payload={payload.get('global_optimizer_step')} cli={args.checkpoint_step}"
        )
    settings = CAREASEFullVolumeInferenceSettings(
        patch_size=(20, 256, 256),
        tile_step_size=0.5,
        use_gaussian=True,
        gaussian_sigma_scale=1.0 / 8.0,
        use_mirroring=True,
        allowed_mirror_axes=(0, 1, 2),
        precision="fp32",
    )
    stock = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=True,
        perform_everything_on_device=device.type == "cuda",
        device=device,
        verbose=False,
        allow_tqdm=False,
    )
    stock.initialize_from_trained_model_folder(
        str(STOCK_ROOT),
        use_folds=(int(args.fold),),
        checkpoint_name="checkpoint_final.pth",
    )
    cases = [str(case_id) for case_id in json.loads(SPLITS.read_text(encoding="utf-8"))[int(args.fold)]["val"]]
    metadata = load_myops_case_metadata(REPO_ROOT)
    rows: list[dict[str, Any]] = []
    for case_id in cases:
        image_np = read_b2nd(PREPROCESSED / f"{case_id}.b2nd").astype(np.float32, copy=False)
        seg = read_b2nd(PREPROCESSED / f"{case_id}_seg.b2nd")[0].astype(np.int64, copy=False)
        spacing = (1.0, 1.0, 1.0)
        pkl = PREPROCESSED / f"{case_id}.pkl"
        if pkl.is_file():
            with pkl.open("rb") as f:
                spacing = tuple(float(v) for v in pickle.load(f).get("spacing", spacing))
        image = torch.from_numpy(image_np[None]).to(device=device, dtype=torch.float32)
        availability = torch.tensor([metadata[case_id].availability], device=device, dtype=torch.float32)
        with torch.no_grad():
            care_logits = predict_care_ase_r2_full_volume_logits(
                model,
                image,
                availability,
                settings=settings,
                global_step=int(args.checkpoint_step),
            )
            care_pred = decode_care_ase_r2_logits(care_logits, availability).cpu().numpy().astype(np.uint8)[0]
            stock_logits = stock.predict_logits_from_preprocessed_data(
                torch.from_numpy(image_np).to(device=device, dtype=torch.float32)
            )
            stock_pred = torch.argmax(stock_logits.float(), dim=0).cpu().numpy().astype(np.uint8)
        t2_present = bool(metadata[case_id].t2_present)
        row: dict[str, Any] = {
            "case_id": case_id,
            "fold": int(args.fold),
            "role": "outer",
            "t2_present": t2_present,
            "care_scar_dice": dice_for_class(care_pred, seg, 5),
            "nnunet_scar_dice": dice_for_class(stock_pred, seg, 5),
            "care_scar_hd95": hd95_for_class(care_pred, seg, 5, spacing),
            "nnunet_scar_hd95": hd95_for_class(stock_pred, seg, 5, spacing),
            "care_scar_sensitivity": sensitivity_for_class(care_pred, seg, 5),
            "nnunet_scar_sensitivity": sensitivity_for_class(stock_pred, seg, 5),
            "care_scar_precision": precision_for_class(care_pred, seg, 5),
            "nnunet_scar_precision": precision_for_class(stock_pred, seg, 5),
        }
        if t2_present:
            row.update(
                {
                    "care_pure_edema_dice": dice_for_class(care_pred, seg, 4),
                    "nnunet_pure_edema_dice": dice_for_class(stock_pred, seg, 4),
                    "care_pure_edema_hd95": hd95_for_class(care_pred, seg, 4, spacing),
                    "nnunet_pure_edema_hd95": hd95_for_class(stock_pred, seg, 4, spacing),
                    "care_pure_edema_sensitivity": sensitivity_for_class(care_pred, seg, 4),
                    "nnunet_pure_edema_sensitivity": sensitivity_for_class(stock_pred, seg, 4),
                    "care_pure_edema_precision": precision_for_class(care_pred, seg, 4),
                    "nnunet_pure_edema_precision": precision_for_class(stock_pred, seg, 4),
                }
            )
        else:
            row.update(
                {
                    "care_pure_edema_dice": "",
                    "nnunet_pure_edema_dice": "",
                    "care_pure_edema_hd95": "",
                    "nnunet_pure_edema_hd95": "",
                    "care_pure_edema_sensitivity": "",
                    "nnunet_pure_edema_sensitivity": "",
                    "care_pure_edema_precision": "",
                    "nnunet_pure_edema_precision": "",
                }
            )
        rows.append(row)

    casewise_path = out_dir / "outer_casewise_metrics.csv"
    with casewise_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "care_scar_mean": mean([row["care_scar_dice"] for row in rows]),
        "nnunet_scar_mean": mean([row["nnunet_scar_dice"] for row in rows]),
        "care_pure_edema_mean": mean([row["care_pure_edema_dice"] for row in rows]),
        "nnunet_pure_edema_mean": mean([row["nnunet_pure_edema_dice"] for row in rows]),
    }
    summary["care_minus_nnunet_scar_mean"] = summary["care_scar_mean"] - summary["nnunet_scar_mean"]
    summary["care_minus_nnunet_pure_edema_mean"] = (
        summary["care_pure_edema_mean"] - summary["nnunet_pure_edema_mean"]
    )
    stock_checkpoint = STOCK_ROOT / f"fold_{int(args.fold)}" / "checkpoint_final.pth"
    packet = {
        "status": "PASS",
        "decision": args.decision,
        "fold": int(args.fold),
        "checkpoint_step": int(args.checkpoint_step),
        "case_count": len(rows),
        "edema_t2_case_count": sum(1 for row in rows if row["t2_present"]),
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": sha256_file(args.checkpoint),
        "stock_checkpoint": str(stock_checkpoint.relative_to(REPO_ROOT)),
        "stock_checkpoint_sha256": sha256_file(stock_checkpoint),
        "inference_settings": settings.to_json_dict(),
        "casewise_csv": str(casewise_path.relative_to(REPO_ROOT)),
        "casewise_csv_sha256": sha256_file(casewise_path),
        "summary": summary,
    }
    summary_path = out_dir / "outer_diagnostic_summary.json"
    summary_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
