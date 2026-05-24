#!/usr/bin/env python3
"""Lane A Round9 tiny-overfit smoke for checkpoint-initialized model."""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round09_baseline_initialized_adaptation/mpl_cache"),
)

import numpy as np
import torch

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from batchgenerators.utilities.file_and_folder_operations import load_json
from nnunetv2.training.dataloading.nnunet_dataset import nnUNetDatasetBlosc2
from nnunetv2.utilities.dataset_name_id_conversion import maybe_convert_to_dataset_name

from scripts.diagnostics.laneA_round9_unit_gradient_smoke import crop_or_pad, selected_cases
from src.care_myocardium.nnunet.laneA_round7_trainer import append_modality_presence_channels, load_case_modality_map
from src.care_myocardium.nnunet.laneA_round9_checkpoint_loader import load_adapted_checkpoint
from src.care_myocardium.nnunet.laneA_round9_trainer import nnUNetTrainerLaneABaselineInitializedEdemaAdapt


OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round09_baseline_initialized_adaptation"
CHECKPOINT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth"
)
PREPROCESSED_3D = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def dice_from_logits(logits: torch.Tensor, target: torch.Tensor, cls: int) -> float | None:
    pred = logits.argmax(1)
    gt = target[:, 0] == cls
    pp = pred == cls
    denom = int(pp.sum().detach().cpu()) + int(gt.sum().detach().cpu())
    if denom == 0:
        return None
    inter = int((pp & gt).sum().detach().cpu())
    return float(2 * inter / denom)


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dataset_name = maybe_convert_to_dataset_name(501)
    preprocessed = Path(os.environ["nnUNet_preprocessed"]) / dataset_name
    plans = load_json(str(preprocessed / "nnUNetPlans.json"))
    plans["continue_training"] = False
    dataset_json = load_json(str(preprocessed / "dataset.json"))
    trainer = nnUNetTrainerLaneABaselineInitializedEdemaAdapt(dict(plans), "3d_fullres", 0, dataset_json, device)
    base_input_channels = len(dataset_json["channel_names"])
    network = trainer.build_network_architecture(
        trainer.plans_manager,
        trainer.configuration_manager,
        base_input_channels,
        trainer.label_manager.num_segmentation_heads,
        enable_deep_supervision=False,
    ).to(device)
    load_adapted_checkpoint(network, CHECKPOINT, modality_init=0.0)
    loss_fn = trainer._build_loss()
    optimizer = torch.optim.AdamW(network.parameters(), lr=1e-5, weight_decay=1e-5)
    case_meta = load_case_modality_map(REPO_ROOT)
    dataset = nnUNetDatasetBlosc2(str(PREPROCESSED_3D), identifiers=selected_cases())
    rows: list[dict[str, object]] = []
    epochs = int(os.environ.get("LANEA_ROUND9_TINY_EPOCHS", "2"))
    network.train()
    for epoch in range(epochs):
        for cid in dataset.identifiers:
            data, seg, _, _ = dataset.load_case(cid)
            data_crop, seg_crop = crop_or_pad(np.asarray(data), np.asarray(seg), (16, 128, 128))
            seg_crop = np.where(seg_crop < 0, 0, seg_crop)
            x = torch.from_numpy(data_crop[None]).float().to(device)
            y = torch.from_numpy(seg_crop[None]).long().to(device)
            x = append_modality_presence_channels(x, [cid], case_meta)
            loss_fn.set_current_keys([cid])
            optimizer.zero_grad(set_to_none=True)
            out = network(x)
            loss = loss_fn(out, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(network.parameters(), 12)
            optimizer.step()
            with torch.no_grad():
                eval_out = network(x)
            rows.append(
                {
                    "epoch": epoch,
                    "case_id": cid,
                    "center": case_meta.get(cid, {}).get("center"),
                    "modality_group": case_meta.get(cid, {}).get("modality_group"),
                    "t2_present": case_meta.get(cid, {}).get("T2_present"),
                    "edema_gt_voxels": int((seg_crop == 4).sum()),
                    "scar_gt_voxels": int((seg_crop == 5).sum()),
                    "loss": float(loss.detach().cpu()),
                    "loss_is_finite": bool(torch.isfinite(loss).detach().cpu()),
                    "edema_dice_on_crop": dice_from_logits(eval_out, y, 4),
                    "scar_dice_on_crop": dice_from_logits(eval_out, y, 5),
                    "pred_edema_voxels_on_crop": int((eval_out.argmax(1) == 4).sum().detach().cpu()),
                }
            )
    write_csv(OUT_ROOT / "round9_tiny_overfit_metrics.csv", rows)
    first_losses = {r["case_id"]: float(r["loss"]) for r in rows if r["epoch"] == 0}
    first_no_t2_edema_voxels = {
        r["case_id"]: int(r["pred_edema_voxels_on_crop"])
        for r in rows
        if r["epoch"] == 0 and not r["t2_present"]
    }
    last_rows = [r for r in rows if r["epoch"] == epochs - 1]
    improved = [
        r for r in last_rows
        if r["case_id"] in first_losses and float(r["loss"]) <= first_losses[r["case_id"]] + 1e-6
    ]
    no_t2_bad = [
        r for r in last_rows
        if (
            not r["t2_present"]
            and int(r["pred_edema_voxels_on_crop"]) > first_no_t2_edema_voxels.get(r["case_id"], 0) + 100
            and int(r["pred_edema_voxels_on_crop"]) > 100
        )
    ]
    pass_gate = len(improved) >= max(1, len(last_rows) // 2) and not no_t2_bad and all(r["loss_is_finite"] for r in rows)
    with (OUT_ROOT / "round9_checkpoint_loader_audit.md").open("a", encoding="utf-8") as f:
        f.write("\n## Tiny-Overfit Smoke\n\n")
        f.write(f"Decision: `{'pass_consider_fold0_very_short' if pass_gate else 'fail_stop_before_fold0_train'}`\n\n")
        f.write(f"- Epochs: `{epochs}`\n")
        f.write(f"- Cases: `{list(dataset.identifiers)}`\n")
        f.write(f"- no-T2 high edema FP rows: `{len(no_t2_bad)}`\n")
        f.write("- Metrics are written to `round9_tiny_overfit_metrics.csv`.\n")


if __name__ == "__main__":
    main()
