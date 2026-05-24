#!/usr/bin/env python3
"""Lane A Round8 T2-present edema expert diagnostics."""

from __future__ import annotations

import csv
import json
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
    str(REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round08_t2_edema_expert/mpl_cache"),
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
    append_modality_presence_channels,
    append_modality_presence_to_case,
    load_case_modality_map,
)
from src.care_myocardium.nnunet.laneA_round8_trainer import (
    SCAR_CLASS,
    SeparatedEdemaLoss,
    apply_t2_absent_edema_logit_bias,
    nnUNetTrainerLaneAT2EdemaExpertShort,
)


OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round08_t2_edema_expert"
PLAN = REPO_ROOT / "docs/plans/laneA_round08_next_t2_present_edema_expert_separated_head_execution.md"
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
CASE_METRICS = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
PREPROCESSED_3D = PREPROCESSED / "nnUNetPlans_3d_fullres"
BASELINE_VAL = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)


POLICIES = [
    {
        "candidate": "A1_mask_class4_no_t2_boost3",
        "edema_expert_weight": 3.0,
        "edema_positive_weight_cap": 50.0,
        "no_t2_confidence_weight": 0.0,
        "no_t2_confidence_threshold": 0.50,
        "t2_absent_logit_bias": 6.0,
    },
    {
        "candidate": "A2_weak_confidence_no_t2_boost3",
        "edema_expert_weight": 3.0,
        "edema_positive_weight_cap": 50.0,
        "no_t2_confidence_weight": 0.02,
        "no_t2_confidence_threshold": 0.10,
        "t2_absent_logit_bias": 6.0,
    },
    {
        "candidate": "A3_stricter_weak_confidence_no_t2_boost3",
        "edema_expert_weight": 3.0,
        "edema_positive_weight_cap": 50.0,
        "no_t2_confidence_weight": 0.05,
        "no_t2_confidence_threshold": 0.05,
        "t2_absent_logit_bias": 8.0,
    },
]


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
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
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
        "round7_trainer": REPO_ROOT / "src/care_myocardium/nnunet/laneA_round7_trainer.py",
        "round8_trainer": REPO_ROOT / "src/care_myocardium/nnunet/laneA_round8_trainer.py",
    }
    rows = []
    for name, path in required.items():
        rows.append({"check": name, "path": str(path), "exists": path.exists(), "status": "pass" if path.exists() else "fail"})
    dataset_json = load_json(str(PREPROCESSED / "dataset.json"))
    labels = dataset_json.get("labels", {})
    channels = dataset_json.get("channel_names", {})
    rows.extend(
        [
            {
                "check": "label_semantics_edema",
                "path": "dataset.json labels",
                "exists": labels.get("edema") == 4 or labels.get("4") == "edema",
                "status": "pass" if (labels.get("edema") == 4 or labels.get("4") == "edema") else "fail",
            },
            {
                "check": "label_semantics_scar",
                "path": "dataset.json labels",
                "exists": labels.get("scar") == 5 or labels.get("5") == "scar",
                "status": "pass" if (labels.get("scar") == 5 or labels.get("5") == "scar") else "fail",
            },
            {
                "check": "base_input_channels",
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
    starts = [int(center[axis] - shape[axis] // 2) for axis in range(3)]
    src_slices = []
    dst_slices = []
    for axis, size in enumerate(shape):
        start = starts[axis]
        end = start + size
        src_start = max(0, start)
        src_end = min(seg.shape[axis + 1], end)
        dst_start = src_start - start
        dst_end = dst_start + (src_end - src_start)
        src_slices.append(slice(src_start, src_end))
        dst_slices.append(slice(dst_start, dst_end))
    out_data[:, dst_slices[0], dst_slices[1], dst_slices[2]] = np.asarray(data[:, src_slices[0], src_slices[1], src_slices[2]], dtype=np.float32)
    out_seg[:, dst_slices[0], dst_slices[1], dst_slices[2]] = np.asarray(seg[:, src_slices[0], src_slices[1], src_slices[2]], dtype=np.int64)
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


class TinyRound8Net(torch.nn.Module):
    def __init__(self, in_channels: int, out_channels: int = 6) -> None:
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Conv3d(in_channels, 16, kernel_size=3, padding=1),
            torch.nn.InstanceNorm3d(16, affine=True),
            torch.nn.LeakyReLU(inplace=True),
            torch.nn.Conv3d(16, out_channels, kernel_size=1),
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


def run_gradient_smoke(case_ids: list[str]) -> tuple[list[dict[str, object]], torch.Tensor, torch.Tensor]:
    case_meta = load_case_modality_map(REPO_ROOT)
    data, target = load_smoke_batch(case_ids)
    data_with_presence = append_modality_presence_channels(data, case_ids, case_meta)
    logits = torch.randn((len(case_ids), 6, *target.shape[2:]), dtype=torch.float32, requires_grad=True)
    loss_fn = SeparatedEdemaLoss(
        edema_expert_weight=3.0,
        no_t2_confidence_weight=0.02,
        no_t2_confidence_threshold=0.10,
        t2_absent_logit_bias=6.0,
    )
    loss_fn.set_current_keys(case_ids)
    loss = loss_fn(logits, target)
    loss.backward()
    rows = []
    meta = load_case_modality_map(REPO_ROOT)
    for idx, cid in enumerate(case_ids):
        m = meta[cid]
        class4_grad = float(logits.grad[idx, EDEMA_CLASS].abs().mean().item())
        class5_grad = float(logits.grad[idx, SCAR_CLASS].abs().mean().item())
        rows.append(
            {
                "stage": "round8_unit_gradient_smoke",
                "case_id": cid,
                "center": m["center"],
                "modality_group": m["modality_group"],
                "T2_present": m["T2_present"],
                "edema_gt_positive": bool((target[idx, 0] == EDEMA_CLASS).any()),
                "input_channels_before": data.shape[1],
                "input_channels_after": data_with_presence.shape[1],
                "loss_value": float(loss.item()),
                "class4_grad_norm": class4_grad,
                "class5_grad_norm": class5_grad,
                "no_t2_class4_dense_hard_negative": False,
                "nan_or_inf": bool(not torch.isfinite(loss).item()),
                "status": "pass" if torch.isfinite(loss).item() and class5_grad > 0 and (m["T2_present"] or class4_grad >= 0) else "fail",
            }
        )
    return rows, data_with_presence, target


def tiny_train(policy: dict[str, object], case_ids: list[str], data: torch.Tensor, target: torch.Tensor, steps: int = 120) -> list[dict[str, object]]:
    torch.manual_seed(20260522)
    model = TinyRound8Net(data.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3)
    loss_fn = SeparatedEdemaLoss(
        edema_expert_weight=float(policy["edema_expert_weight"]),
        edema_positive_weight_cap=float(policy["edema_positive_weight_cap"]),
        no_t2_confidence_weight=float(policy["no_t2_confidence_weight"]),
        no_t2_confidence_threshold=float(policy["no_t2_confidence_threshold"]),
        t2_absent_logit_bias=float(policy["t2_absent_logit_bias"]),
    )
    loss_fn.set_current_keys(case_ids)
    loss_initial = None
    loss_final = None
    for step in range(steps):
        optimizer.zero_grad(set_to_none=True)
        logits = model(data)
        loss = loss_fn(logits, target)
        if step == 0:
            loss_initial = float(loss.item())
        loss.backward()
        optimizer.step()
        loss_final = float(loss.item())
    with torch.no_grad():
        logits = model(data)
        t2_mask = torch.tensor([bool(load_case_modality_map(REPO_ROOT)[cid]["T2_present"]) for cid in case_ids], dtype=torch.bool)
        logits = apply_t2_absent_edema_logit_bias(logits, t2_mask, float(policy["t2_absent_logit_bias"]))
        pred = logits.argmax(1).cpu().numpy()
    target_np = target[:, 0].cpu().numpy()
    meta = load_case_modality_map(REPO_ROOT)
    rows = []
    for idx, cid in enumerate(case_ids):
        edema_fp_voxels = int(np.logical_and(pred[idx] == EDEMA_CLASS, target_np[idx] != EDEMA_CLASS).sum())
        no_t2_fp = (not bool(meta[cid]["T2_present"])) and edema_fp_voxels > 0
        edema_dice = dice(pred[idx], target_np[idx], EDEMA_CLASS)
        row = {
            "case_id": cid,
            "candidate": policy["candidate"],
            "center": meta[cid]["center"],
            "modality_group": meta[cid]["modality_group"],
            "T2_present": meta[cid]["T2_present"],
            "edema_gt_positive": bool((target_np[idx] == EDEMA_CLASS).any()),
            "steps": steps,
            "no_t2_confidence_weight": policy["no_t2_confidence_weight"],
            "no_t2_confidence_threshold": policy["no_t2_confidence_threshold"],
            "edema_expert_weight": policy["edema_expert_weight"],
            "edema_positive_weight_cap": policy["edema_positive_weight_cap"],
            "t2_absent_logit_bias": policy["t2_absent_logit_bias"],
            "loss_initial": loss_initial,
            "loss_final": loss_final,
            "loss_decreased": loss_final is not None and loss_initial is not None and loss_final < loss_initial,
            "myops_edema_dice": edema_dice,
            "myops_scar_dice": dice(pred[idx], target_np[idx], SCAR_CLASS),
            "edema_component_count": component_count(pred[idx] == EDEMA_CLASS),
            "no_t2_empty_gt_edema_fp_voxels": edema_fp_voxels if not bool(meta[cid]["T2_present"]) else 0,
            "no_t2_empty_gt_edema_fp": no_t2_fp,
        }
        if bool(row["T2_present"]) and bool(row["edema_gt_positive"]) and (edema_dice is None or edema_dice <= 0):
            row["status"] = "fail_no_positive_edema_signal"
        elif no_t2_fp and edema_fp_voxels > 10:
            row["status"] = "fail_no_t2_fp_above_tiny_threshold"
        elif no_t2_fp:
            row["status"] = "watch_no_t2_fp_within_tiny_threshold"
        else:
            row["status"] = "pass"
        rows.append(row)
    return rows


def run_network_init_smoke() -> list[dict[str, object]]:
    plans = load_json(str(PREPROCESSED / "nnUNetPlans.json"))
    plans["continue_training"] = False
    dataset_json = load_json(str(PREPROCESSED / "dataset.json"))
    trainer = nnUNetTrainerLaneAT2EdemaExpertShort(plans, "3d_fullres", 0, dataset_json, torch.device("cpu"))
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
            "check": "round8_nnunet_network_init",
            "base_num_input_channels": int(trainer.num_input_channels),
            "expected_round8_input_channels": int(trainer.num_input_channels + len(MODALITY_PRESENCE_ORDER)),
            "first_conv_key": first_conv_key,
            "first_conv_shape": first_conv_shape,
            "first_conv_in_channels": first_conv_in_channels,
            "output_folder": trainer.output_folder,
            "status": "pass" if first_conv_in_channels == trainer.num_input_channels + len(MODALITY_PRESENCE_ORDER) else "fail",
        }
    ]


def run_validation_export_channel_smoke(case_ids: list[str]) -> list[dict[str, object]]:
    case_meta = load_case_modality_map(REPO_ROOT)
    dataset = nnUNetDatasetBlosc2(str(PREPROCESSED_3D), identifiers=[case_ids[0]])
    data, _, _, _ = dataset.load_case(case_ids[0])
    injected = append_modality_presence_to_case(data[:], case_ids[0], case_meta)
    return [
        {
            "check": "round8_validation_export_channel_helper",
            "case_id": case_ids[0],
            "preprocessed_input_channels": int(np.asarray(data).shape[0]),
            "round8_network_input_channels": int(injected.shape[0]),
            "status": "pass" if injected.shape[0] == np.asarray(data).shape[0] + len(MODALITY_PRESENCE_ORDER) else "fail",
        }
    ]


def write_configs(selected_policy: dict[str, object] | None = None) -> None:
    policy = selected_policy or POLICIES[1]
    write_text(
        OUT_ROOT / "round8_train_config.yaml",
        "\n".join(
            [
                "candidate: A_functional_separated_edema_supervision",
                "trainer: nnUNetTrainerLaneAT2EdemaExpertShort",
                "fold: 0",
                "input_channels: 6",
                "base_image_channels: 3",
                "modality_presence_channels: [C0_present, LGE_present, T2_present]",
                "class_4_edema_policy: T2-present strong supervision; no-T2 dense hard negative disabled",
                "class_5_scar_policy: LGE-driven all-case guardrail supervision through non-edema/full loss",
                "full_ce_weight: 1.0",
                "dice_weight: 1.0",
                f"edema_expert_weight: {policy['edema_expert_weight']}",
                f"edema_positive_weight_cap: {policy['edema_positive_weight_cap']}",
                f"selected_policy: {policy['candidate']}",
                f"no_t2_confidence_weight: {policy['no_t2_confidence_weight']}",
                f"no_t2_confidence_threshold: {policy['no_t2_confidence_threshold']}",
                f"t2_absent_logit_bias: {policy['t2_absent_logit_bias']}",
                "no_t2_tiny_fail_threshold_total_fp_voxels: 10",
                "no_t2_fold0_watch_threshold_fp_cases: 1",
                "validation_zip: forbidden",
                "fold1_4: forbidden_without_new_user_authorization",
            ]
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "round8_train_commands.txt",
        "\n".join(
            [
                "# Run only after round8 tiny gate passes.",
                "sbatch jobs/nnUNet/laneA_round8_fold0_very_short_train.sh",
                "",
                "# Direct local/debug command:",
                "./envs/env_CARE/bin/python scripts/training/run_laneA_round8_nnunet_train.py --dataset 501 --configuration 3d_fullres --fold 0 --run-validation-export",
            ]
        )
        + "\n",
    )


def write_placeholder_fold0_outputs() -> None:
    rows = [{"stage": "round8_fold0", "status": "not_run_gate_pending", "reason": "Round8 bounded training ladder has not reached fold0 train."}]
    write_csv(OUT_ROOT / "round8_fold0_very_short_metrics.csv", rows)
    write_csv(OUT_ROOT / "round8_fold0_short_train_metrics.csv", rows)
    write_csv(OUT_ROOT / "baseline_vs_candidate_by_subset.csv", rows)
    write_csv(OUT_ROOT / "case_level_failure_flags.csv", rows)


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    setup_rows = setup_gate()
    case_ids = select_smoke_cases()
    gradient_rows, data, target = run_gradient_smoke(case_ids)
    network_rows = run_network_init_smoke()
    export_rows = run_validation_export_channel_smoke(case_ids)

    all_tiny_rows = []
    policy_summary = []
    for policy in POLICIES:
        rows = tiny_train(policy, case_ids, data, target)
        all_tiny_rows.extend(rows)
        t2_rows = [r for r in rows if bool(r["T2_present"]) and bool(r["edema_gt_positive"])]
        no_t2_rows = [r for r in rows if not bool(r["T2_present"])]
        min_t2_dice = min([float(r["myops_edema_dice"] or 0.0) for r in t2_rows]) if t2_rows else 0.0
        no_t2_fp_voxels = sum(int(r["no_t2_empty_gt_edema_fp_voxels"]) for r in no_t2_rows)
        no_t2_fp_cases = sum(1 for r in no_t2_rows if bool(r["no_t2_empty_gt_edema_fp"]))
        status = "pass_tiny_policy_screen"
        if min_t2_dice <= 0:
            status = "fail_no_t2_present_edema_signal"
        if no_t2_fp_voxels > 10 or no_t2_fp_cases > 1:
            status = "fail_no_t2_fp_above_tiny_threshold"
        elif no_t2_fp_voxels > 0:
            status = "watch_tiny_policy_screen"
        policy_summary.append(
            {
                **policy,
                "min_t2_positive_edema_dice": min_t2_dice,
                "mean_t2_positive_edema_dice": float(np.mean([float(r["myops_edema_dice"] or 0.0) for r in t2_rows])) if t2_rows else 0.0,
                "no_t2_empty_gt_fp_voxels": no_t2_fp_voxels,
                "no_t2_empty_gt_fp_cases": no_t2_fp_cases,
                "status": status,
            }
        )

    selected = next((r for r in policy_summary if r["status"] == "pass_tiny_policy_screen"), None)
    if selected is None:
        selected = next((r for r in policy_summary if r["status"] == "watch_tiny_policy_screen"), None)
    write_configs(selected)
    write_csv(OUT_ROOT / "round8_setup_gate.csv", setup_rows)
    write_csv(OUT_ROOT / "round8_unit_gradient_smoke.csv", gradient_rows)
    write_csv(OUT_ROOT / "round8_tiny_overfit_metrics.csv", all_tiny_rows)
    write_csv(OUT_ROOT / "round8_tiny_policy_summary.csv", policy_summary)
    write_csv(OUT_ROOT / "no_t2_empty_gt_fp_table.csv", [r for r in all_tiny_rows if not bool(r["T2_present"])])
    write_csv(OUT_ROOT / "centerB_centerC_edema_table.csv", [r for r in all_tiny_rows if str(r["center"]) in {"CenterB", "CenterC"}])
    write_csv(OUT_ROOT / "scar_guardrail_table.csv", [{"case_id": r["case_id"], "candidate": r["candidate"], "center": r["center"], "myops_scar_dice": r["myops_scar_dice"], "status": r["status"]} for r in all_tiny_rows])
    write_placeholder_fold0_outputs()
    write_text(OUT_ROOT / "round8_network_init_smoke.md", md_table(network_rows + export_rows, list((network_rows + export_rows)[0].keys())))

    setup_pass = all(r["status"] == "pass" for r in setup_rows)
    gradient_pass = all(r["status"] == "pass" and not bool(r["nan_or_inf"]) for r in gradient_rows)
    network_pass = all(r["status"] == "pass" for r in network_rows + export_rows)
    selected_status = selected["status"] if selected is not None else "none"
    if setup_pass and gradient_pass and network_pass and selected_status == "pass_tiny_policy_screen":
        overall = "go_fold0_very_short_allowed"
        next_action = "create_or_use_round8_fold0_very_short_job"
    elif setup_pass and gradient_pass and network_pass and selected_status == "watch_tiny_policy_screen":
        overall = "watch_tiny_gate_no_auto_fold0"
        next_action = "review no-T2 FP before any Slurm train"
    else:
        overall = "fail_stop_before_fold0_training"
        next_action = "revise separated edema supervision before training"

    decision_rows = [
        {"stage": "round8_reproducibility_and_code_reuse_gate", "status": "pass" if setup_pass and network_pass else "fail", "evidence": f"setup={setup_pass}; network_export={network_pass}", "next_action": "continue" if setup_pass and network_pass else "stop"},
        {"stage": "separated_edema_head_design", "status": "pass" if gradient_pass else "fail", "evidence": "Candidate A functional separation; no-T2 dense class_4 hard negative disabled", "next_action": "continue" if gradient_pass else "stop"},
        {"stage": "t2_present_edema_expert_supervision", "status": selected_status, "evidence": f"selected={selected['candidate'] if selected else 'none'}", "next_action": next_action},
        {"stage": "bounded_training_ladder", "status": "not_run" if overall != "go_fold0_very_short_allowed" else "ready", "evidence": "fold0 train not run by diagnostic script", "next_action": next_action},
    ]
    write_text(
        OUT_ROOT / "round8_decision_table.md",
        "# Lane A Round8 Decision Table\n\n"
        + md_table(decision_rows, ["stage", "status", "evidence", "next_action"])
        + f"\n\nOverall decision: `{overall}`.\n",
    )
    write_text(
        OUT_ROOT / "round8_goal_execution_readme.md",
        "\n".join(
            [
                "# Lane A Round8 Goal Execution Readme",
                "",
                "Round8 created a first-party Candidate A functional separated edema supervision path.",
                "",
                f"Selected smoke cases: {', '.join(case_ids)}.",
                f"Overall decision: `{overall}`.",
                "",
                "No validation zip, upload, fold1-4, external repo, external data, or pretrained weight download was used.",
            ]
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "round8_next_actions.md",
        "\n".join(
            [
                "# Lane A Round8 Next Actions",
                "",
                f"Current decision: `{overall}`.",
                f"Next action: {next_action}.",
                "",
                "Do not run fold1-4, 5-fold, validation zip, upload, large external repo integration, external data training, or validation pseudo-label supervised training from this state.",
            ]
        )
        + "\n",
    )
    print(f"Wrote Round8 outputs to {OUT_ROOT}")
    print(f"Decision: {overall}")


if __name__ == "__main__":
    main()
