#!/usr/bin/env python3
"""Smoke-test Lane A Round9 3-channel checkpoint to 6-channel model loading."""

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
    str(REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round9_baseline_initialized_adaptation/mpl_cache"),
)

import numpy as np
import torch

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from batchgenerators.utilities.file_and_folder_operations import load_json
from nnunetv2.training.dataloading.nnunet_dataset import nnUNetDatasetBlosc2
from nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs import nnUNetTrainer_500epochs
from nnunetv2.utilities.dataset_name_id_conversion import maybe_convert_to_dataset_name

from src.care_myocardium.nnunet.laneA_round7_trainer import append_modality_presence_channels, load_case_modality_map
from src.care_myocardium.nnunet.laneA_round8_trainer import nnUNetTrainerLaneAT2EdemaExpertShort
from src.care_myocardium.nnunet.laneA_round9_checkpoint_loader import load_adapted_checkpoint, load_checkpoint_state


OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round9_baseline_initialized_adaptation"
CHECKPOINT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth"
)
PREPROCESSED_3D = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
CASE_METRICS = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/myops_modality_center_case_metrics.csv"


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def bool_csv(value: object) -> bool:
    return str(value).strip().lower() == "true"


def select_cases() -> list[str]:
    rows = read_csv(CASE_METRICS)
    selected: list[str] = []

    def add(predicate) -> None:
        for row in rows:
            cid = row["case_id"]
            if predicate(row) and (PREPROCESSED_3D / f"{cid}.b2nd").is_file() and cid not in selected:
                selected.append(cid)
                return

    add(lambda r: r["center"] == "CenterB" and bool_csv(r["edema_gt_positive"]))
    add(lambda r: r["center"] == "CenterC" and bool_csv(r["edema_gt_positive"]))
    add(lambda r: r["modality_group"] == "LGE-only" and not bool_csv(r["edema_gt_positive"]))
    add(lambda r: r["modality_group"] == "C0+LGE" and not bool_csv(r["edema_gt_positive"]))
    return selected


def center_crop(data: np.ndarray, shape: tuple[int, int, int]) -> np.ndarray:
    out = np.zeros((data.shape[0], *shape), dtype=np.float32)
    center = np.asarray(data.shape[1:]) // 2
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
    out[:, dst_slices[0], dst_slices[1], dst_slices[2]] = np.asarray(
        data[:, src_slices[0], src_slices[1], src_slices[2]],
        dtype=np.float32,
    )
    return out


def build_trainers(device: torch.device):
    dataset_name = maybe_convert_to_dataset_name(501)
    preprocessed = Path(os.environ["nnUNet_preprocessed"]) / dataset_name
    plans = load_json(str(preprocessed / "nnUNetPlans.json"))
    plans["continue_training"] = False
    dataset_json = load_json(str(preprocessed / "dataset.json"))
    base_trainer = nnUNetTrainer_500epochs(dict(plans), "3d_fullres", 0, dataset_json, device)
    r9_trainer = nnUNetTrainerLaneAT2EdemaExpertShort(dict(plans), "3d_fullres", 0, dataset_json, device)
    return base_trainer, r9_trainer


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    base_trainer, r9_trainer = build_trainers(device)
    base_input_channels = len(base_trainer.dataset_json["channel_names"])
    base_net = nnUNetTrainer_500epochs.build_network_architecture(
        base_trainer.plans_manager,
        base_trainer.configuration_manager,
        base_input_channels,
        base_trainer.label_manager.num_segmentation_heads,
        enable_deep_supervision=False,
    ).to(device)
    r9_net = r9_trainer.build_network_architecture(
        r9_trainer.plans_manager,
        r9_trainer.configuration_manager,
        base_input_channels,
        r9_trainer.label_manager.num_segmentation_heads,
        enable_deep_supervision=False,
    ).to(device)

    source = load_checkpoint_state(CHECKPOINT)
    base_net.load_state_dict(source, strict=True)
    report = load_adapted_checkpoint(r9_net, CHECKPOINT, modality_init=0.0)
    write_csv(OUT_ROOT / "round9_checkpoint_key_report.csv", report)

    status_counts: dict[str, int] = {}
    for row in report:
        status_counts[str(row["status"])] = status_counts.get(str(row["status"]), 0) + 1
    expanded = [r for r in report if r["status"] == "expanded_first_conv"]
    shape_mismatch = [r for r in report if r["status"] == "shape_mismatch"]
    missing = [r for r in report if r["status"] == "missing"]

    case_meta = load_case_modality_map(REPO_ROOT)
    dataset = nnUNetDatasetBlosc2(str(PREPROCESSED_3D), identifiers=select_cases())
    reproduction_rows: list[dict[str, object]] = []
    base_net.eval()
    r9_net.eval()
    for cid in dataset.identifiers:
        data, _, _, _ = dataset.load_case(cid)
        crop = center_crop(np.asarray(data), (8, 64, 64))
        x3 = torch.from_numpy(crop[None]).float().to(device)
        x6 = append_modality_presence_channels(x3, [cid], case_meta)
        with torch.no_grad():
            base_logits = base_net(x3)
            r9_logits = r9_net(x6)
        diff = (base_logits - r9_logits).abs()
        base_pred = base_logits.argmax(1).detach().cpu().numpy()[0]
        r9_pred = r9_logits.argmax(1).detach().cpu().numpy()[0]
        reproduction_rows.append(
            {
                "case_id": cid,
                "center": case_meta.get(cid, {}).get("center"),
                "modality_group": case_meta.get(cid, {}).get("modality_group"),
                "device": str(device),
                "crop_shape": "8,64,64",
                "max_abs_logit_delta": float(diff.max().detach().cpu()),
                "mean_abs_logit_delta": float(diff.mean().detach().cpu()),
                "pred_voxel_mismatch_fraction": float(np.mean(base_pred != r9_pred)),
                "base_class4_voxels": int((base_pred == 4).sum()),
                "r9_class4_voxels": int((r9_pred == 4).sum()),
                "base_class5_voxels": int((base_pred == 5).sum()),
                "r9_class5_voxels": int((r9_pred == 5).sum()),
            }
        )
    write_csv(OUT_ROOT / "round9_initial_inference_baseline_reproduction.csv", reproduction_rows)

    max_delta = max(float(r["max_abs_logit_delta"]) for r in reproduction_rows) if reproduction_rows else float("inf")
    max_mismatch = max(float(r["pred_voxel_mismatch_fraction"]) for r in reproduction_rows) if reproduction_rows else float("inf")
    pass_gate = bool(expanded) and not shape_mismatch and max_delta <= 1e-4 and max_mismatch <= 1e-6
    decision = "pass_continue_to_one_batch_gradient" if pass_gate else "fail_fix_checkpoint_loader_before_training"

    lines = [
        "# Lane A Round9 Checkpoint Loader Audit",
        "",
        f"Decision: `{decision}`",
        "",
        f"- Source checkpoint: `{CHECKPOINT}`",
        f"- Device: `{device}`",
        f"- Status counts: `{status_counts}`",
        f"- Expanded input keys: `{[r['key'] for r in expanded]}`",
        f"- Shape mismatches: `{len(shape_mismatch)}`",
        f"- Missing model keys: `{len(missing)}`",
        f"- Max crop logit delta vs baseline net: `{max_delta:.8g}`",
        f"- Max crop prediction mismatch fraction: `{max_mismatch:.8g}`",
        "",
        "Interpretation:",
        "",
    ]
    if pass_gate:
        lines.extend(
            [
                "- The 3-channel nnU-Net501 checkpoint was loaded into the 6-channel model with expanded input weights.",
                "- Added modality-presence channels were initialized inertly.",
                "- Cropped initial forward outputs match the 3-channel baseline network to numerical precision.",
                "- It is safe to proceed to one-batch gradient smoke before any fold0 training.",
            ]
        )
    else:
        lines.append("- Checkpoint loader reproduction failed. Do not train until the loader/channel-order issue is fixed.")
    (OUT_ROOT / "round9_checkpoint_loader_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    config = [
        "candidate: ckptinit_6ch_A1_lowlr_separated_edema",
        f"source_checkpoint: {CHECKPOINT}",
        "dataset: 501",
        "configuration: 3d_fullres",
        "fold: 0",
        "input_channels: 6",
        "modality_presence_order: [C0, LGE, T2]",
        "modality_channel_init: 0.0",
        "initial_lr: 0.00001",
        "edema_expert_weight: 1.0",
        "no_t2_confidence_weight: 0.0",
        "t2_absent_logit_bias: 0.0",
        "output_experiment: laneA_r9_ckptinit_6ch_edema_adapt_fold0_very_short",
    ]
    (OUT_ROOT / "round9_train_config_checkpoint_initialized.yaml").write_text("\n".join(config) + "\n", encoding="utf-8")
    (OUT_ROOT / "round9_train_commands.txt").write_text(
        "\n".join(
            [
                "# Commands are staged; do not run Slurm until non-training gates pass.",
                f"{REPO_ROOT}/envs/env_CARE/bin/python scripts/diagnostics/laneA_round9_failure_audit.py",
                f"{REPO_ROOT}/envs/env_CARE/bin/python scripts/diagnostics/laneA_round9_checkpoint_loader_smoke.py",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
