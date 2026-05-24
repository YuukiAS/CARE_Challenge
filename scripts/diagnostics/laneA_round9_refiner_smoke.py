#!/usr/bin/env python3
"""Lane A Round9 edema-only residual refiner smoke."""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round9_baseline_initialized_adaptation/mpl_cache"),
)

import numpy as np
import SimpleITK as sitk
import torch

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics.laneA_round9_unit_gradient_smoke import crop_or_pad, selected_cases
from src.care_myocardium.nnunet.laneA_round7_trainer import MODALITY_PRESENCE_ORDER, load_case_modality_map
from src.care_myocardium.nnunet.laneA_round9_refiner import EdemaResidualRefiner, fuse_edema_only


OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round9_baseline_initialized_adaptation"
BASELINE_PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
RAW_ROOT = REPO_ROOT / "data/CARE_Challenge/MyoPS_train"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def load_array(path: Path) -> np.ndarray:
    return sitk.GetArrayFromImage(sitk.ReadImage(str(path))).astype(np.float32)


def one_hot(seg: np.ndarray, n_classes: int = 6) -> np.ndarray:
    return np.stack([(seg == cls).astype(np.float32) for cls in range(n_classes)], axis=0)


def minmax(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32, copy=False)
    lo = float(np.percentile(arr, 1))
    hi = float(np.percentile(arr, 99))
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0, 1).astype(np.float32)


def raw_modalities(case_id: str, meta: dict[str, object], target_shape: tuple[int, int, int]) -> np.ndarray:
    center = str(meta["center"])
    case_dir = RAW_ROOT / center / case_id
    channels = []
    for modality in MODALITY_PRESENCE_ORDER:
        path = case_dir / f"{case_id}_{modality}.nii.gz"
        if path.is_file():
            arr = minmax(load_array(path))
        else:
            arr = np.zeros(target_shape, dtype=np.float32)
        if arr.shape != target_shape:
            arr = np.resize(arr, target_shape).astype(np.float32)
        channels.append(arr)
    return np.stack(channels, axis=0)


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    case_meta = load_case_modality_map(REPO_ROOT)
    rows: list[dict[str, object]] = []
    model = EdemaResidualRefiner(in_channels=12).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=1e-3)
    bce = torch.nn.BCEWithLogitsLoss()
    for cid in selected_cases():
        meta = case_meta[cid]
        gt = load_array(GT_DIR / f"{cid}.nii.gz").astype(np.int64)[None]
        baseline = load_array(BASELINE_PRED_DIR / f"{cid}.nii.gz").astype(np.int64)[None]
        baseline_crop, gt_crop = crop_or_pad(baseline.astype(np.float32), gt, (16, 128, 128))
        baseline_crop = baseline_crop.astype(np.int64)
        gt_crop = np.where(gt_crop < 0, 0, gt_crop).astype(np.int64)
        image_channels = raw_modalities(cid, meta, tuple(gt.shape[1:]))
        image_crop, _ = crop_or_pad(image_channels, gt, (16, 128, 128))
        presence = np.asarray(
            [1.0 if meta.get(f"{m}_present", False) else 0.0 for m in MODALITY_PRESENCE_ORDER],
            dtype=np.float32,
        )[:, None, None, None]
        presence = np.broadcast_to(presence, (3, 16, 128, 128)).copy()
        features = np.concatenate([one_hot(baseline_crop[0]), image_crop, presence], axis=0)
        x = torch.from_numpy(features[None]).float().to(device)
        y = torch.from_numpy((gt_crop == 4).astype(np.float32)[None]).to(device)
        baseline_t = torch.from_numpy(baseline_crop).long().to(device)
        optim.zero_grad(set_to_none=True)
        logits = model(x)
        loss = bce(logits, y)
        loss.backward()
        optim.step()
        refined = fuse_edema_only(baseline_t, logits.detach(), threshold=0.5)
        scar_changed = int(((refined == 5) != (baseline_t == 5)).sum().detach().cpu())
        non_edema_non_scar_changed = int(
            (((refined != baseline_t) & (refined != 4) & (baseline_t != 4))).sum().detach().cpu()
        )
        rows.append(
            {
                "case_id": cid,
                "center": meta.get("center"),
                "modality_group": meta.get("modality_group"),
                "t2_present": meta.get("T2_present"),
                "loss": float(loss.detach().cpu()),
                "loss_is_finite": bool(torch.isfinite(loss).detach().cpu()),
                "baseline_edema_voxels_crop": int((baseline_t == 4).sum().detach().cpu()),
                "refined_edema_voxels_crop": int((refined == 4).sum().detach().cpu()),
                "scar_changed_voxels": scar_changed,
                "non_edema_non_scar_changed_voxels": non_edema_non_scar_changed,
            }
        )
    write_csv(OUT_ROOT / "round9_refiner_smoke.csv", rows)
    pass_gate = all(r["loss_is_finite"] for r in rows) and all(int(r["scar_changed_voxels"]) == 0 for r in rows)
    (OUT_ROOT / "round9_train_config_edema_refiner.yaml").write_text(
        "\n".join(
            [
                "candidate: edema_only_residual_refiner_smoke",
                "input_channels: 12",
                "inputs: [baseline_one_hot_0_to_5, raw_C0_or_zero, raw_LGE_or_zero, raw_T2_or_zero, C0_present, LGE_present, T2_present]",
                "output: class_4_edema_logit_only",
                "fusion_rule: class_4_only; class_5 scar unchanged by construction",
                f"smoke_decision: {'pass_refiner_baseline_preserving_gate' if pass_gate else 'fail_refiner_smoke'}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with (OUT_ROOT / "round9_next_actions.md").open("a", encoding="utf-8") as f:
        f.write("\n## Edema-Only Refiner Smoke\n\n")
        f.write(f"Decision: `{'pass_refiner_baseline_preserving_gate' if pass_gate else 'fail_refiner_smoke'}`\n\n")
        f.write("- Metrics: `round9_refiner_smoke.csv`\n")
        f.write("- Config: `round9_train_config_edema_refiner.yaml`\n")
        f.write("- This smoke verifies class_4-only fusion and scar preservation; it is not a fold0 performance result.\n")


if __name__ == "__main__":
    main()
