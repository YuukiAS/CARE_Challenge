#!/usr/bin/env python3
"""Lane A Round9 one-case gradient smoke for checkpoint-initialized model."""

from __future__ import annotations

import csv
import math
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
CASE_METRICS = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def bool_csv(value: object) -> bool:
    return str(value).strip().lower() == "true"


def selected_cases() -> list[str]:
    rows = read_csv(CASE_METRICS)
    out: list[str] = []
    for predicate in [
        lambda r: r["center"] == "CenterB" and bool_csv(r["edema_gt_positive"]),
        lambda r: r["center"] == "CenterC" and bool_csv(r["edema_gt_positive"]),
        lambda r: r["modality_group"] == "LGE-only" and not bool_csv(r["edema_gt_positive"]),
        lambda r: r["modality_group"] == "C0+LGE" and not bool_csv(r["edema_gt_positive"]),
    ]:
        for row in rows:
            cid = row["case_id"]
            if predicate(row) and (PREPROCESSED_3D / f"{cid}.b2nd").is_file() and cid not in out:
                out.append(cid)
                break
    return out


def crop_or_pad(data: np.ndarray, seg: np.ndarray, shape: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    mask = seg[0] == 4
    center = np.argwhere(mask).mean(axis=0).round().astype(int) if mask.any() else np.asarray(seg.shape[1:]) // 2
    out_data = np.zeros((data.shape[0], *shape), dtype=np.float32)
    out_seg = np.zeros((1, *shape), dtype=np.int64)
    starts = [int(center[i] - shape[i] // 2) for i in range(3)]
    src_slices = []
    dst_slices = []
    for axis, size in enumerate(shape):
        start = starts[axis]
        end = start + size
        src_start = max(0, start)
        src_end = min(data.shape[axis + 1], end)
        dst_start = src_start - start
        dst_end = dst_start + (src_end - src_start)
        src_slices.append(slice(src_start, src_end))
        dst_slices.append(slice(dst_start, dst_end))
    out_data[:, dst_slices[0], dst_slices[1], dst_slices[2]] = np.asarray(
        data[:, src_slices[0], src_slices[1], src_slices[2]],
        dtype=np.float32,
    )
    out_seg[:, dst_slices[0], dst_slices[1], dst_slices[2]] = np.asarray(
        seg[:, src_slices[0], src_slices[1], src_slices[2]],
        dtype=np.int64,
    )
    return out_data, out_seg


def grad_norm(parameters) -> float:
    total = 0.0
    for p in parameters:
        if p.grad is None:
            continue
        total += float(p.grad.detach().float().pow(2).sum().cpu())
    return math.sqrt(total)


def segmentation_head_grad_norms(network: torch.nn.Module) -> tuple[float | None, float | None]:
    class4 = []
    class5 = []
    for name, p in network.named_parameters():
        if p.grad is None or p.ndim < 1 or p.shape[0] != 6:
            continue
        if "seg" not in name and "decoder" not in name:
            continue
        class4.append(p.grad[4].detach())
        class5.append(p.grad[5].detach())
    def _norm(items: list[torch.Tensor]) -> float | None:
        if not items:
            return None
        return math.sqrt(sum(float(i.float().pow(2).sum().cpu()) for i in items))
    return _norm(class4), _norm(class5)


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
    case_meta = load_case_modality_map(REPO_ROOT)
    dataset = nnUNetDatasetBlosc2(str(PREPROCESSED_3D), identifiers=selected_cases())
    rows: list[dict[str, object]] = []
    network.train()
    for cid in dataset.identifiers:
        data, seg, _, _ = dataset.load_case(cid)
        data_crop, seg_crop = crop_or_pad(np.asarray(data), np.asarray(seg), (16, 128, 128))
        # The diagnostic crop may include nnU-Net padding voxels marked -1.
        # They are outside the sampled image support, so map them to background
        # for this smoke instead of changing Dataset501 label semantics.
        seg_crop = np.where(seg_crop < 0, 0, seg_crop)
        x = torch.from_numpy(data_crop[None]).float().to(device)
        y = torch.from_numpy(seg_crop[None]).long().to(device)
        x = append_modality_presence_channels(x, [cid], case_meta)
        loss_fn.set_current_keys([cid])
        network.zero_grad(set_to_none=True)
        output = network(x)
        loss = loss_fn(output, y)
        loss.backward()
        total_norm = grad_norm(network.parameters())
        head4, head5 = segmentation_head_grad_norms(network)
        first_param = next(network.parameters())
        first_extra_grad = None
        if first_param.grad is not None and first_param.ndim >= 2 and first_param.shape[1] >= 6:
            first_extra_grad = float(first_param.grad[:, 3:, ...].detach().float().norm().cpu())
        rows.append(
            {
                "case_id": cid,
                "center": case_meta.get(cid, {}).get("center"),
                "modality_group": case_meta.get(cid, {}).get("modality_group"),
                "t2_present": case_meta.get(cid, {}).get("T2_present"),
                "edema_gt_voxels": int((seg_crop == 4).sum()),
                "scar_gt_voxels": int((seg_crop == 5).sum()),
                "loss": float(loss.detach().cpu()),
                "loss_is_finite": bool(torch.isfinite(loss).detach().cpu()),
                "total_grad_norm": total_norm,
                "head_class4_grad_norm": head4,
                "head_class5_grad_norm": head5,
                "first_conv_modality_channel_grad_norm": first_extra_grad,
            }
        )
    write_csv(OUT_ROOT / "round9_unit_gradient_smoke.csv", rows)
    pass_gate = all(r["loss_is_finite"] for r in rows) and all(float(r["total_grad_norm"]) > 0 for r in rows)
    current = (OUT_ROOT / "round9_checkpoint_loader_audit.md").read_text(encoding="utf-8") if (OUT_ROOT / "round9_checkpoint_loader_audit.md").is_file() else ""
    with (OUT_ROOT / "round9_checkpoint_loader_audit.md").open("a", encoding="utf-8") as f:
        f.write("\n## One-Batch Gradient Smoke\n\n")
        f.write(f"Decision: `{'pass_continue_to_tiny_or_fold0_very_short' if pass_gate else 'fail_fix_gradient_before_training'}`\n\n")
        f.write(f"- Cases: `{[r['case_id'] for r in rows]}`\n")
        f.write(f"- Device: `{device}`\n")
        f.write("- Losses and gradient norms are written to `round9_unit_gradient_smoke.csv`.\n")


if __name__ == "__main__":
    main()
