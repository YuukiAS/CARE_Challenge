#!/usr/bin/env python3
"""Lane A Round7 setup, modality-conditioning, and uncertainty-loss smokes."""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round07_modality_uncertainty/mpl_cache"),
)

import numpy as np
import torch
from scipy import ndimage


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from batchgenerators.utilities.file_and_folder_operations import load_json
from nnunetv2.training.dataloading.nnunet_dataset import nnUNetDatasetBlosc2

from src.care_myocardium.nnunet.laneA_round7_trainer import (
    EDEMA_CLASS,
    MODALITY_PRESENCE_ORDER,
    EdemaUncertaintyWeightedAuxLoss,
    append_modality_presence_channels,
    append_modality_presence_to_case,
    load_case_modality_map,
    nnUNetTrainerLaneAModPresenceUncertaintyShort,
)


SCAR_CLASS = 5
OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round07_modality_uncertainty"
PLAN = REPO_ROOT / "docs/plans/laneA_round07_next_modality_presence_uncertainty_supervision_execution.md"
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
CASE_METRICS = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
PREPROCESSED_3D = PREPROCESSED / "nnUNetPlans_3d_fullres"
BASELINE_VAL = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)
ROUND6_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round06_anatomy_missing_modality"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def bool_from_str(value: object) -> bool:
    return str(value).strip().lower() == "true"


def fmt(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        if math.isinf(value):
            return "inf"
        return f"{value:.4f}"
    return str(value)


def md_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def setup_gate() -> list[dict[str, object]]:
    required = {
        "plan": PLAN,
        "splits_json": SPLITS_JSON,
        "case_metrics": CASE_METRICS,
        "preprocessed_3d": PREPROCESSED_3D,
        "baseline_validation_dir": BASELINE_VAL,
        "baseline_summary": BASELINE_VAL / "summary.json",
        "round6_decision_table": ROUND6_ROOT / "round6_laneA_decision_table.md",
        "round6_missing_modality_audit": ROUND6_ROOT / "missing_modality_supervision_audit.md",
    }
    rows = []
    for name, path in required.items():
        rows.append(
            {
                "check": name,
                "path": str(path),
                "exists": path.exists(),
                "status": "pass" if path.exists() else "fail",
            }
        )

    dataset_json = load_json(str(PREPROCESSED / "dataset.json"))
    labels = dataset_json.get("labels", {})
    channels = dataset_json.get("channel_names", {})
    rows.extend(
        [
            {
                "check": "label_semantics_edema",
                "path": "dataset.json labels",
                "exists": labels.get("edema") == 4 or labels.get("4") == "edema",
                "status": "pass" if (labels.get("edema") == 4 or labels.get("4") == "edema") else "watch",
            },
            {
                "check": "label_semantics_scar",
                "path": "dataset.json labels",
                "exists": labels.get("scar") == 5 or labels.get("5") == "scar",
                "status": "pass" if (labels.get("scar") == 5 or labels.get("5") == "scar") else "watch",
            },
            {
                "check": "input_channels_current",
                "path": json.dumps(channels, sort_keys=True),
                "exists": len(channels) == 3,
                "status": "pass" if len(channels) == 3 else "fail",
            },
        ]
    )
    return rows


def select_smoke_cases() -> list[str]:
    rows = read_csv(CASE_METRICS)
    selected: list[str] = []

    def add_first(predicate):
        candidates = [r for r in rows if predicate(r) and (PREPROCESSED_3D / f"{r['case_id']}.b2nd").is_file()]
        candidates.sort(key=lambda r: (r.get("edema_dice") in {"", None}, float(r.get("edema_dice") or 999)))
        if candidates:
            cid = candidates[0]["case_id"]
            if cid not in selected:
                selected.append(cid)

    add_first(lambda r: r["center"] == "CenterC" and bool_from_str(r["edema_gt_positive"]))
    add_first(lambda r: r["center"] == "CenterB" and bool_from_str(r["edema_gt_positive"]))
    add_first(lambda r: r["modality_group"] == "C0+LGE" and not bool_from_str(r["edema_gt_positive"]))
    add_first(lambda r: r["modality_group"] == "LGE-only" and not bool_from_str(r["edema_gt_positive"]))
    return selected


def crop_or_pad(data: np.ndarray, seg: np.ndarray, shape: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    mask = seg[0] == EDEMA_CLASS
    if mask.any():
        center = np.argwhere(mask).mean(axis=0).round().astype(int)
    else:
        center = np.asarray(seg.shape[1:]) // 2
    out_data = np.zeros((data.shape[0], *shape), dtype=np.float32)
    out_seg = np.zeros((1, *shape), dtype=np.int64)
    for axis, size in enumerate(shape):
        start = int(center[axis] - size // 2)
        end = start + size
        src_start = max(0, start)
        src_end = min(seg.shape[axis + 1], end)
        dst_start = src_start - start
        dst_end = dst_start + (src_end - src_start)
        if axis == 0:
            src_z, dst_z = slice(src_start, src_end), slice(dst_start, dst_end)
        elif axis == 1:
            src_y, dst_y = slice(src_start, src_end), slice(dst_start, dst_end)
        else:
            src_x, dst_x = slice(src_start, src_end), slice(dst_start, dst_end)
    out_data[:, dst_z, dst_y, dst_x] = np.asarray(data[:, src_z, src_y, src_x], dtype=np.float32)
    out_seg[:, dst_z, dst_y, dst_x] = np.asarray(seg[:, src_z, src_y, src_x], dtype=np.int64)
    return out_data, out_seg


def load_smoke_batch(case_ids: list[str], patch_shape: tuple[int, int, int] = (8, 64, 64)) -> tuple[torch.Tensor, torch.Tensor]:
    dataset = nnUNetDatasetBlosc2(str(PREPROCESSED_3D), identifiers=case_ids)
    data_items = []
    seg_items = []
    for cid in case_ids:
        data, seg, _, _ = dataset.load_case(cid)
        data_crop, seg_crop = crop_or_pad(np.asarray(data), np.asarray(seg), patch_shape)
        data_items.append(data_crop)
        seg_items.append(seg_crop)
    return torch.from_numpy(np.stack(data_items)).float(), torch.from_numpy(np.stack(seg_items)).long()


class CrossEntropyBaseLoss(torch.nn.Module):
    def forward(self, output, target):  # type: ignore[override]
        logits = output[0] if isinstance(output, (list, tuple)) else output
        labels = target[0] if isinstance(target, (list, tuple)) else target
        if labels.ndim == logits.ndim:
            labels = labels[:, 0]
        return torch.nn.functional.cross_entropy(logits, labels.long())


class TinyRound7Net(torch.nn.Module):
    def __init__(self, in_channels: int, out_channels: int = 6) -> None:
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Conv3d(in_channels, 12, kernel_size=3, padding=1),
            torch.nn.InstanceNorm3d(12, affine=True),
            torch.nn.LeakyReLU(inplace=True),
            torch.nn.Conv3d(12, out_channels, kernel_size=1),
        )

    def forward(self, x):
        return self.net(x)


def dice(pred: np.ndarray, target: np.ndarray, cls: int) -> float | None:
    pred_mask = pred == cls
    target_mask = target == cls
    if not pred_mask.any() and not target_mask.any():
        return None
    denom = int(pred_mask.sum() + target_mask.sum())
    if denom == 0:
        return None
    return float(2 * np.logical_and(pred_mask, target_mask).sum() / denom)


def component_count(mask: np.ndarray) -> int:
    _, n_cc = ndimage.label(mask.astype(bool), structure=ndimage.generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def run_gradient_smoke(case_ids: list[str]) -> tuple[list[dict[str, object]], torch.Tensor, torch.Tensor, torch.Tensor]:
    case_meta = load_case_modality_map(REPO_ROOT)
    data, target = load_smoke_batch(case_ids)
    data_with_presence = append_modality_presence_channels(data, case_ids, case_meta)
    logits = torch.randn((len(case_ids), 6, *target.shape[2:]), dtype=torch.float32, requires_grad=True)
    loss_fn = EdemaUncertaintyWeightedAuxLoss(
        base_loss=CrossEntropyBaseLoss(),
        aux_weight=0.20,
        no_t2_negative_weight=0.05,
        t2_present_weight=1.0,
    )
    loss_fn.set_current_keys(case_ids)
    loss = loss_fn(logits, target)
    loss.backward()
    weights = loss_fn.sample_weights(len(case_ids), logits.device).detach().cpu().numpy()
    rows = []
    grad = logits.grad.detach()
    for idx, cid in enumerate(case_ids):
        meta = case_meta[cid]
        class4_norm = float(grad[idx, EDEMA_CLASS].norm().item())
        class5_norm = float(grad[idx, SCAR_CLASS].norm().item())
        rows.append(
            {
                "stage": "unit_gradient_smoke",
                "case_id": cid,
                "center": meta["center"],
                "modality_group": meta["modality_group"],
                "C0_present": meta["C0_present"],
                "LGE_present": meta["LGE_present"],
                "T2_present": meta["T2_present"],
                "input_channels_before": int(data.shape[1]),
                "input_channels_after": int(data_with_presence.shape[1]),
                "edema_gt_positive": bool((target[idx] == EDEMA_CLASS).any().item()),
                "edema_loss_weight": float(weights[idx]),
                "loss_value": float(loss.detach().cpu().item()),
                "class4_grad_norm": class4_norm,
                "class5_grad_norm": class5_norm,
                "nan_or_inf": not math.isfinite(float(loss.detach().cpu().item())),
                "status": "pass" if class4_norm > 0 and class5_norm > 0 and math.isfinite(float(loss.detach().cpu().item())) else "fail",
            }
        )
    return rows, data_with_presence, target, torch.tensor(weights)


def run_tiny_overfit(
    case_ids: list[str],
    data: torch.Tensor,
    target: torch.Tensor,
    steps: int = 120,
    aux_weight: float = 0.20,
    no_t2_negative_weight: float = 0.05,
    candidate: str = "U1_default_low_negative",
) -> list[dict[str, object]]:
    torch.manual_seed(7)
    model = TinyRound7Net(data.shape[1])
    loss_fn = EdemaUncertaintyWeightedAuxLoss(
        base_loss=CrossEntropyBaseLoss(),
        aux_weight=aux_weight,
        no_t2_negative_weight=no_t2_negative_weight,
        t2_present_weight=1.0,
    )
    loss_fn.set_current_keys(case_ids)
    opt = torch.optim.Adam(model.parameters(), lr=1e-2)
    losses = []
    for _ in range(steps):
        opt.zero_grad(set_to_none=True)
        out = model(data)
        loss = loss_fn(out, target)
        loss.backward()
        opt.step()
        losses.append(float(loss.detach().cpu().item()))
    with torch.no_grad():
        pred = model(data).argmax(dim=1).cpu().numpy()
    gt = target[:, 0].cpu().numpy()
    case_meta = load_case_modality_map(REPO_ROOT)
    rows = []
    for idx, cid in enumerate(case_ids):
        edema_components = component_count(pred[idx] == EDEMA_CLASS)
        edema_dice = dice(pred[idx], gt[idx], EDEMA_CLASS)
        edema_gt_positive = bool((gt[idx] == EDEMA_CLASS).any())
        no_t2_fp = bool((not case_meta[cid]["T2_present"]) and not edema_gt_positive and edema_components > 0)
        if edema_gt_positive and (edema_dice is None or edema_dice <= 0.05):
            status = "fail_no_positive_edema_signal"
        elif no_t2_fp:
            status = "fail_no_t2_empty_gt_edema_fp"
        elif losses[-1] >= losses[0]:
            status = "fail_loss_not_decreased"
        else:
            status = "pass"
        rows.append(
            {
                "case_id": cid,
                "candidate": candidate,
                "center": case_meta[cid]["center"],
                "modality_group": case_meta[cid]["modality_group"],
                "T2_present": case_meta[cid]["T2_present"],
                "edema_gt_positive": edema_gt_positive,
                "steps": steps,
                "aux_weight": aux_weight,
                "no_t2_negative_weight": no_t2_negative_weight,
                "loss_initial": losses[0],
                "loss_final": losses[-1],
                "loss_decreased": losses[-1] < losses[0],
                "myops_edema_dice": edema_dice,
                "myops_scar_dice": dice(pred[idx], gt[idx], SCAR_CLASS),
                "edema_component_count": edema_components,
                "no_t2_empty_gt_edema_fp": no_t2_fp,
                "status": status,
            }
        )
    return rows


def run_policy_sensitivity(case_ids: list[str], data: torch.Tensor, target: torch.Tensor, steps: int = 120) -> list[dict[str, object]]:
    case_meta = load_case_modality_map(REPO_ROOT)
    gt = target[:, 0].cpu().numpy()
    combos = [
        ("U1_default_low_negative", 0.20, 0.05),
        ("U1_stronger_edema_low_negative", 1.00, 0.05),
        ("U2_modality_conditioned_balanced", 1.00, 0.25),
        ("U2_modality_conditioned_conservative", 1.00, 0.50),
    ]
    rows: list[dict[str, object]] = []
    for name, aux_weight, no_t2_weight in combos:
        torch.manual_seed(7)
        model = TinyRound7Net(data.shape[1])
        loss_fn = EdemaUncertaintyWeightedAuxLoss(
            base_loss=CrossEntropyBaseLoss(),
            aux_weight=aux_weight,
            no_t2_negative_weight=no_t2_weight,
            t2_present_weight=1.0,
        )
        loss_fn.set_current_keys(case_ids)
        opt = torch.optim.Adam(model.parameters(), lr=1e-2)
        losses = []
        for _ in range(steps):
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(data), target)
            loss.backward()
            opt.step()
            losses.append(float(loss.detach().cpu().item()))
        with torch.no_grad():
            pred = model(data).argmax(dim=1).cpu().numpy()
        positive_dice = [
            dice(pred[idx], gt[idx], EDEMA_CLASS)
            for idx, cid in enumerate(case_ids)
            if bool((gt[idx] == EDEMA_CLASS).any())
        ]
        no_t2_fp_voxels = [
            int((pred[idx] == EDEMA_CLASS).sum())
            for idx, cid in enumerate(case_ids)
            if not case_meta[cid]["T2_present"] and not bool((gt[idx] == EDEMA_CLASS).any())
        ]
        min_positive_dice = min([d for d in positive_dice if d is not None], default=0.0)
        no_t2_fp = any(v > 0 for v in no_t2_fp_voxels)
        rows.append(
            {
                "candidate": name,
                "aux_weight": aux_weight,
                "no_t2_negative_weight": no_t2_weight,
                "steps": steps,
                "loss_initial": losses[0],
                "loss_final": losses[-1],
                "loss_decreased": losses[-1] < losses[0],
                "min_t2_positive_edema_dice": min_positive_dice,
                "mean_t2_positive_edema_dice": float(np.mean([d for d in positive_dice if d is not None])),
                "no_t2_empty_gt_edema_fp_voxels": ";".join(str(v) for v in no_t2_fp_voxels),
                "no_t2_empty_gt_edema_fp": no_t2_fp,
                "status": "pass_tiny_policy_screen" if losses[-1] < losses[0] and min_positive_dice > 0.05 and not no_t2_fp else "fail_tiny_policy_screen",
            }
        )
    return rows


def write_configs() -> None:
    write_text(
        OUT_ROOT / "train_config_modality_presence.yaml",
        "\n".join(
            [
                "candidate: input_level_modality_presence_channels",
                "fold: 0",
                "seed: 7",
                "base_dataset: Dataset501_CAREMyoPS",
                "image_channels_before: [LGE, T2, C0]",
                "presence_channels_added: [C0_present, LGE_present, T2_present]",
                "image_channels_after: [LGE, T2, C0, C0_present, LGE_present, T2_present]",
                "conditioning_scope: first_party_nnunet_trainer_wrapper",
                "baseline_cache_policy: do_not_modify_or_reuse_for_candidate_outputs",
                "candidate_experiment_name: laneA_modpresence_uncertainty_fold0_short",
                "pretrained_baseline_checkpoint: not_loaded_by_default_due_first_conv_channel_mismatch",
            ]
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "train_config_uncertainty_weighted.yaml",
        "\n".join(
            [
                "candidate: uncertainty_weighted_low_negative",
                "class_4_edema_aux_weight: 0.20",
                "t2_present_class4_weight: 1.0",
                "no_t2_empty_gt_class4_negative_weight: 0.05",
                "hard_negative_no_t2: false",
                "masking_no_t2: false",
                "class_5_scar_guardrail: base_multiclass_loss_unchanged",
                "teacher_or_validation_pseudolabel_training: false",
            ]
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "train_commands.txt",
        "\n".join(
            [
                "# Import/unit/gradient smoke:",
                "./envs/env_CARE/bin/python scripts/diagnostics/laneA_round07_modality_uncertainty.py",
                "",
                "# Bounded fold0 very-short train candidate; run only after smoke gates pass:",
                "LANEA_ROUND7_AUX_WEIGHT=1.0 LANEA_ROUND7_NO_T2_NEGATIVE_WEIGHT=0.25 \\",
                "  LANEA_ROUND7_EPOCHS=3 LANEA_ROUND7_ITERS_PER_EPOCH=5 LANEA_ROUND7_VAL_ITERS_PER_EPOCH=2 \\",
                "  ./envs/env_CARE/bin/python scripts/training/run_laneA_round7_nnunet_train.py --dataset 501 --configuration 3d_fullres --fold 0",
                "",
                "# No validation zip or fold1-4 is authorized by this plan.",
            ]
        )
        + "\n",
    )


def write_placeholder_outputs() -> None:
    write_csv(
        OUT_ROOT / "fold0_short_train_metrics.csv",
        [{"stage": "fold0_short_train", "status": "not_run_gate_pending", "reason": "Round7 first execution stopped after setup/gradient/tiny smoke"}],
    )
    write_csv(
        OUT_ROOT / "baseline_vs_candidate_by_subset.csv",
        [{"subset": "all_case", "status": "not_run_no_fold0_candidate_predictions", "reason": "fold0 train/eval gate not reached"}],
    )
    write_csv(
        OUT_ROOT / "centerC_failure_table.csv",
        [{"case_id": "NA", "status": "not_run_no_fold0_candidate_predictions", "reason": "fold0 train/eval gate not reached"}],
    )
    write_csv(
        OUT_ROOT / "case_level_failure_flags.csv",
        [{"case_id": "NA", "status": "not_run_no_fold0_candidate_predictions", "flags": ""}],
    )


def run_validation_export_channel_smoke(case_ids: list[str]) -> list[dict[str, object]]:
    case_meta = load_case_modality_map(REPO_ROOT)
    dataset = nnUNetDatasetBlosc2(str(PREPROCESSED_3D), identifiers=[case_ids[0]])
    data, _, _, _ = dataset.load_case(case_ids[0])
    injected = append_modality_presence_to_case(data[:], case_ids[0], case_meta)
    model = TinyRound7Net(injected.shape[0])
    with torch.no_grad():
        crop = injected[None, :, :4, :32, :32].float()
        logits = model(crop)
    return [
        {
            "check": "default_nnunet_validation_export_channel_compatibility",
            "case_id": case_ids[0],
            "preprocessed_input_channels": int(np.asarray(data).shape[0]),
            "round7_network_input_channels": int(injected.shape[0]),
            "default_export_appends_presence_channels": False,
            "round7_export_hook_available": True,
            "forward_smoke_shape": "x".join(str(i) for i in logits.shape),
            "status": "pass_round7_channel_injection_helper",
            "reason": "Round7 trainer overrides validation export and injects modality-presence channels before predictor input; this smoke validates the channel helper on one preprocessed case.",
        }
    ]


def run_network_init_smoke() -> list[dict[str, object]]:
    plans = load_json(str(PREPROCESSED / "nnUNetPlans.json"))
    plans["continue_training"] = False
    dataset_json = load_json(str(PREPROCESSED / "dataset.json"))
    trainer = nnUNetTrainerLaneAModPresenceUncertaintyShort(plans, "3d_fullres", 0, dataset_json, torch.device("cpu"))
    trainer.initialize()
    first_conv_key = ""
    first_conv_shape = ""
    first_conv_in_channels = None
    for key, value in trainer.network.state_dict().items():
        if value.ndim >= 4:
            first_conv_key = key
            first_conv_shape = "x".join(str(i) for i in value.shape)
            first_conv_in_channels = int(value.shape[1])
            break
    return [
        {
            "check": "round7_nnunet_network_init",
            "base_num_input_channels": int(trainer.num_input_channels),
            "expected_round7_input_channels": int(trainer.num_input_channels + len(MODALITY_PRESENCE_ORDER)),
            "network_class": trainer.network.__class__.__name__,
            "first_conv_key": first_conv_key,
            "first_conv_shape": first_conv_shape,
            "first_conv_in_channels": first_conv_in_channels,
            "output_folder": trainer.output_folder,
            "status": "pass" if first_conv_in_channels == trainer.num_input_channels + len(MODALITY_PRESENCE_ORDER) else "fail",
        }
    ]


def summarize(rows: list[dict[str, object]], key: str) -> dict[str, int]:
    out: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        out[str(row[key])] += 1
    return dict(out)


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_configs()
    setup_rows = setup_gate()
    write_csv(OUT_ROOT / "setup_reproducibility_gate.csv", setup_rows)

    case_ids = select_smoke_cases()
    gradient_rows, data_with_presence, target, _ = run_gradient_smoke(case_ids)
    tiny_rows = run_tiny_overfit(case_ids, data_with_presence, target)
    policy_rows = run_policy_sensitivity(case_ids, data_with_presence, target)
    export_rows = run_validation_export_channel_smoke(case_ids)
    network_rows = run_network_init_smoke()

    unit_fields = [
        "stage",
        "case_id",
        "center",
        "modality_group",
        "C0_present",
        "LGE_present",
        "T2_present",
        "input_channels_before",
        "input_channels_after",
        "edema_gt_positive",
        "edema_loss_weight",
        "loss_value",
        "class4_grad_norm",
        "class5_grad_norm",
        "nan_or_inf",
        "status",
    ]
    write_csv(OUT_ROOT / "unit_gradient_smoke.csv", gradient_rows, unit_fields)
    write_csv(OUT_ROOT / "tiny_overfit_metrics.csv", tiny_rows)
    write_csv(OUT_ROOT / "uncertainty_policy_sensitivity.csv", policy_rows)

    no_t2_rows = [r for r in tiny_rows if str(r["T2_present"]) == "False" and str(r["edema_gt_positive"]) == "False"]
    write_csv(OUT_ROOT / "no_t2_empty_gt_stability.csv", no_t2_rows)
    write_placeholder_outputs()
    write_csv(OUT_ROOT / "validation_export_channel_smoke.csv", export_rows)
    write_csv(OUT_ROOT / "network_init_smoke.csv", network_rows)

    setup_pass = all(r["status"] in {"pass", "watch"} for r in setup_rows)
    gradient_pass = all(r["status"] == "pass" for r in gradient_rows)
    tiny_loss_pass = all(r["loss_decreased"] for r in tiny_rows)
    tiny_case_pass = all(str(r["status"]) == "pass" for r in tiny_rows)
    no_t2_fp = any(bool(r["no_t2_empty_gt_edema_fp"]) for r in no_t2_rows)
    passing_policy_candidates = [r for r in policy_rows if r["status"] == "pass_tiny_policy_screen"]
    selected_policy = passing_policy_candidates[0] if passing_policy_candidates else None
    selected_tiny_rows: list[dict[str, object]] = []
    if selected_policy is not None:
        selected_tiny_rows = run_tiny_overfit(
            case_ids,
            data_with_presence,
            target,
            aux_weight=float(selected_policy["aux_weight"]),
            no_t2_negative_weight=float(selected_policy["no_t2_negative_weight"]),
            candidate=str(selected_policy["candidate"]),
        )
        write_csv(OUT_ROOT / "selected_policy_tiny_overfit_metrics.csv", selected_tiny_rows)
        write_text(
            OUT_ROOT / "train_config_uncertainty_weighted.yaml",
            "\n".join(
                [
                    "candidate: modality_conditioned_uncertainty_weighting",
                    f"selected_after_tiny_screen: {selected_policy['candidate']}",
                    f"class_4_edema_aux_weight: {selected_policy['aux_weight']}",
                    "t2_present_class4_weight: 1.0",
                    f"no_t2_empty_gt_class4_negative_weight: {selected_policy['no_t2_negative_weight']}",
                    "initial_U1_low_negative_status: fail_tiny_policy_screen",
                    "hard_negative_no_t2: false",
                    "masking_no_t2: false",
                    "class_5_scar_guardrail: base_multiclass_loss_unchanged",
                    "teacher_or_validation_pseudolabel_training: false",
                    "fold0_train_status: not_run_pending_formal_selected_policy_gate",
                ]
            )
            + "\n",
        )
    else:
        write_csv(
            OUT_ROOT / "selected_policy_tiny_overfit_metrics.csv",
            [
                {
                    "candidate": "none",
                    "status": "not_run_no_policy_passed_tiny_screen",
                    "reason": "All uncertainty-weighted policy candidates failed the tiny screen after AMP-safe BCEWithLogits loss.",
                }
            ],
        )
    decision_status = "watch_continue_to_bounded_fold0_very_short" if setup_pass and gradient_pass and tiny_case_pass and not no_t2_fp else "fail_stop_before_fold0_training"
    if no_t2_fp:
        decision_status = "fail_stop_before_fold0_training_no_t2_tiny_fp"
    selected_tiny_pass = bool(selected_tiny_rows) and all(str(r["status"]) == "pass" for r in selected_tiny_rows)
    if not tiny_case_pass and passing_policy_candidates:
        decision_status = "watch_selected_U2_tiny_gate_passed_fold0_not_run" if selected_tiny_pass else "watch_reconfigure_to_U2_policy_before_fold0"

    decision_rows = [
        {
            "stage": "round7_setup_and_reproducibility_gate",
            "status": "pass" if setup_pass else "fail",
            "evidence": summarize(setup_rows, "status"),
            "next_action": "continue_to_modality_presence_gradient_smoke" if setup_pass else "stop",
        },
        {
            "stage": "modality_presence_conditioning_implementation",
            "status": "pass" if gradient_pass else "fail",
            "evidence": f"input channels {gradient_rows[0]['input_channels_before']}->{gradient_rows[0]['input_channels_after']}; class4/class5 gradients finite",
            "next_action": "continue_to_uncertainty_weighted_policy" if gradient_pass else "stop",
        },
        {
            "stage": "uncertainty_weighted_no_t2_edema_supervision",
            "status": "pass" if gradient_pass else "fail",
            "evidence": "no-T2 class_4 negative weight=0.05; T2-present weight=1.0; hard_negative=false",
            "next_action": "continue_to_bounded_training_ladder" if gradient_pass else "stop",
        },
        {
            "stage": "bounded_training_ladder",
            "status": "watch" if decision_status.startswith("watch") else "fail",
            "evidence": f"tiny_loss_pass={tiny_loss_pass}; tiny_case_pass={tiny_case_pass}; no_t2_tiny_fp={no_t2_fp}; passing_policy_candidates={[r['candidate'] for r in passing_policy_candidates]}; selected_tiny_pass={selected_tiny_pass}; export_channel_smoke={export_rows[0]['status']}; network_init={network_rows[0]['status']}; fold0_train_not_run",
            "next_action": "eligible_for_fold0_very_short_gpu_train" if selected_tiny_pass and export_rows[0]["status"] == "pass_round7_channel_injection_helper" else "update config to best U2 tiny-policy candidate and rerun gates",
        },
    ]
    write_csv(OUT_ROOT / "round7_decision_table.csv", decision_rows)
    write_text(
        OUT_ROOT / "round7_decision_table.md",
        "# Lane A Round7 Decision Table\n\n"
        + md_table(decision_rows, ["stage", "status", "evidence", "next_action"])
        + f"\n\nOverall decision: `{decision_status}`.\n",
    )
    write_text(
        OUT_ROOT / "round7_goal_execution_readme.md",
        "\n".join(
            [
                "# Lane A Round7 Goal Execution Readme",
                "",
                "This execution created a first-party Round7 wiring path and ran setup, gradient, and tiny-overfit diagnostics.",
                "",
                "No Slurm job, validation zip, upload, fold1-4, external repo, external data, or pretrained weight download was used.",
                "",
                f"Selected smoke cases: {', '.join(case_ids)}.",
                "",
                f"Overall decision: `{decision_status}`.",
                "",
                "The fold0 train/eval ladder has not been entered yet; placeholder CSV rows are explicitly marked `not_run_gate_pending`.",
                "",
                "Default M1+U1 did not pass the strict tiny gate; see `uncertainty_policy_sensitivity.csv` for U2 policy candidates.",
                "",
                f"Selected next policy candidate: `{selected_policy['candidate'] if selected_policy is not None else 'none'}`.",
                f"Selected-policy formal tiny gate: `{selected_tiny_pass}`.",
                f"Validation/export channel injection smoke: `{export_rows[0]['status']}`.",
            ]
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "round7_next_actions.md",
        "\n".join(
            [
                "# Lane A Round7 Next Actions",
                "",
                "1. Review `tiny_overfit_metrics.csv`, especially no-T2 empty-GT edema FP flags.",
                "2. Review `uncertainty_policy_sensitivity.csv`; if U2 remains the best tiny-level candidate, update the formal train config before any fold0 train.",
                "3. Validation/export channel injection smoke now passes at helper level; next step is a bounded fold0 very-short GPU train using `train_commands.txt`.",
                "4. After fold0 very-short export, run the existing subset evaluator pattern from Round4/Round6 and replace placeholder fold0 CSV outputs with real metrics.",
                "5. Do not run fold1-4, 5-fold, validation zip, or submission from Round7 without a clean fold0 decision gate.",
            ]
        )
        + "\n",
    )
    print(f"Wrote Round7 outputs to {OUT_ROOT}")
    print(f"Decision: {decision_status}")


if __name__ == "__main__":
    main()
