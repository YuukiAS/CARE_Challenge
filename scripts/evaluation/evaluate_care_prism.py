#!/usr/bin/env python
"""Deterministic local CARE-PRISM evaluation helper."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt, label as connected_components
import torch
import torch.nn.functional as F

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_prism_dataset import CAREPRISMAugmenter, CAREPRISMFullPatientDataset
from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_care_prism, build_source_nnunet
from src.care_myocardium.training.care_prism_trainer import file_sha256


def dice(prob: torch.Tensor, target: torch.Tensor, threshold: float = 0.5) -> float:
    pred = prob >= threshold
    tgt = target > 0.5
    inter = (pred & tgt).sum().float()
    denom = pred.sum().float() + tgt.sum().float()
    if float(denom) == 0.0:
        return 1.0
    return float((2.0 * inter / denom).cpu())


def binary_metrics(pred: np.ndarray, target: np.ndarray, union: np.ndarray) -> dict[str, Any]:
    pred = pred.astype(bool)
    target = target.astype(bool)
    union = union.astype(bool)
    inter = float(np.logical_and(pred, target).sum())
    denom = float(pred.sum() + target.sum())
    dice_value = 1.0 if denom == 0 else 2.0 * inter / denom
    if pred.any() and target.any():
        pred_surface = np.logical_xor(pred, binary_erosion(pred))
        target_surface = np.logical_xor(target, binary_erosion(target))
        dt_target = distance_transform_edt(~target_surface)
        dt_pred = distance_transform_edt(~pred_surface)
        distances = np.concatenate([dt_target[pred_surface], dt_pred[target_surface]])
        hd95 = float(np.percentile(distances, 95)) if distances.size else 0.0
        exact_hd = float(distances.max()) if distances.size else 0.0
        infinite_hd = False
    elif pred.any() or target.any():
        hd95 = float("inf")
        exact_hd = float("inf")
        infinite_hd = True
    else:
        hd95 = 0.0
        exact_hd = 0.0
        infinite_hd = False
    labeled_gt, gt_count = connected_components(target)
    lesion_hits = 0
    for component_id in range(1, int(gt_count) + 1):
        component = labeled_gt == component_id
        if np.logical_and(component, pred).any():
            lesion_hits += 1
    lesion_recall = 1.0 if gt_count == 0 else lesion_hits / float(gt_count)
    labeled_pred, pred_count = connected_components(pred)
    remote_fp = 0
    if union.any():
        dist_union = distance_transform_edt(~union)
        for component_id in range(1, int(pred_count) + 1):
            component = labeled_pred == component_id
            if not np.logical_and(component, target).any() and float(dist_union[component].min(initial=0.0)) > 10.0:
                remote_fp += 1
    volume_ratio = float(pred.sum() / max(float(target.sum()), 1.0))
    return {
        "dice": dice_value,
        "hd95": hd95,
        "exact_hd": exact_hd,
        "infinite_hd": infinite_hd,
        "lesion_recall": lesion_recall,
        "gt_component_count": int(gt_count),
        "pred_component_count": int(pred_count),
        "remote_fp_count": int(remote_fp),
        "volume_ratio": volume_ratio,
        "empty_gt": bool(not target.any()),
        "empty_pred": bool(not pred.any()),
    }


def move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {key: value.to(device) if torch.is_tensor(value) else value for key, value in batch.items()}


def spatial_multiple(config: CAREPRISMConfig) -> tuple[int, int, int]:
    multiple = [1, 1, 1]
    for stride in config.strides:
        for axis, value in enumerate(stride):
            multiple[axis] *= int(value)
    return tuple(max(1, value) for value in multiple)


def pad_to_multiple(volume: torch.Tensor, multiple: tuple[int, int, int]) -> tuple[torch.Tensor, tuple[int, int, int]]:
    spatial = tuple(int(v) for v in volume.shape[-3:])
    pads = [int((m - (s % m)) % m) for s, m in zip(spatial, multiple)]
    if not any(pads):
        return volume, spatial
    return F.pad(volume, (0, pads[2], 0, pads[1], 0, pads[0])), spatial


def crop_to_shape(volume: torch.Tensor, spatial: tuple[int, int, int]) -> torch.Tensor:
    d, h, w = spatial
    return volume[..., :d, :h, :w]


def crop_outputs(outputs: dict[str, Any], spatial: tuple[int, int, int]) -> dict[str, Any]:
    cropped: dict[str, Any] = {}
    for key, value in outputs.items():
        if torch.is_tensor(value) and value.ndim >= 5:
            cropped[key] = crop_to_shape(value, spatial)
        else:
            cropped[key] = value
    return cropped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--split", default="inner_select")
    parser.add_argument("--max-cases", type=int, default=1)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--nnunet-checkpoint", type=Path)
    parser.add_argument("--select-inner", action="store_true")
    parser.add_argument("--write-freeze", action="store_true")
    parser.add_argument("--outer-lock", type=Path)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "results/20260729_care_prism_v2_backbone_repair_and_resume/eval_probe")
    args = parser.parse_args()
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but not available")
    checkpoints = []
    if args.checkpoint_dir is not None:
        checkpoints.extend(sorted(args.checkpoint_dir.glob("checkpoint_step*.pt")))
    if args.checkpoint is not None:
        checkpoints.append(args.checkpoint)
    if not checkpoints:
        raise SystemExit("no checkpoint or checkpoint-dir supplied")
    config = CAREPRISMConfig.from_nnunet_plans()
    pad_multiple = spatial_multiple(config)
    anchor = None
    if args.nnunet_checkpoint is not None:
        anchor = build_source_nnunet(config).to(device)
        anchor_payload = torch.load(args.nnunet_checkpoint, map_location="cpu", weights_only=False)
        anchor.load_state_dict(anchor_payload.get("network_weights", anchor_payload), strict=False)
        anchor.eval()
    ds = CAREPRISMFullPatientDataset(
        fold=args.fold,
        split=args.split,
        augmenter=CAREPRISMAugmenter(training=False),
        outer_access_lock=args.outer_lock,
    )
    rows: list[dict[str, Any]] = []
    summaries = []
    for checkpoint in checkpoints:
        model = build_care_prism(config).to(device)
        payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
        model.load_state_dict(payload["model_state"])
        model.eval()
        ckpt_rows = []
        with torch.no_grad():
            for idx in range(min(args.max_cases, len(ds))):
                batch = move_batch(ds[idx], device)
                images, original_spatial = pad_to_multiple(batch["images"].float(), pad_multiple)
                out = crop_outputs(model(images, batch["availability"]), original_spatial)
                anchor_pred = None
                if anchor is not None:
                    logits = anchor(images)
                    if isinstance(logits, (list, tuple)):
                        logits = logits[0]
                    logits = crop_to_shape(logits, original_spatial)
                    labels = logits.argmax(dim=1, keepdim=True)
                    anchor_pred = {
                        "scar": (labels == 5).detach().cpu().numpy()[0, 0],
                        "edema_zone": ((labels == 4) | (labels == 5)).detach().cpu().numpy()[0, 0],
                    }
                targets = {
                    "scar": batch["scar_target"].detach().cpu().numpy()[0, 0] > 0.5,
                    "edema_zone": batch["edema_zone_target"].detach().cpu().numpy()[0, 0] > 0.5,
                }
                preds = {
                    "scar": (out["scar_probability"].detach().cpu().numpy()[0, 0] >= 0.5),
                    "edema_zone": (out["edema_probability"].detach().cpu().numpy()[0, 0] >= 0.5),
                }
                union = batch["anatomy_target"][:, 0:1].detach().cpu().numpy()[0, 0] > 0.5
                for metric_name in ("scar", "edema_zone"):
                    metrics = binary_metrics(preds[metric_name], targets[metric_name], union)
                    anchor_metrics = binary_metrics(anchor_pred[metric_name], targets[metric_name], union) if anchor_pred is not None else {}
                    row = {
                        "checkpoint": str(checkpoint),
                        "checkpoint_sha256": file_sha256(checkpoint),
                        "case_id": batch["case_id"][0],
                        "split": args.split,
                        "metric_name": metric_name,
                        "t2_present": float(batch["t2_present"][0, 0]),
                        **metrics,
                        "nnunet_dice": anchor_metrics.get("dice"),
                        "dice_delta_vs_nnunet": None if not anchor_metrics else metrics["dice"] - anchor_metrics["dice"],
                        "nnunet_hd95": anchor_metrics.get("hd95"),
                        "hd95_delta_vs_nnunet": None if not anchor_metrics else metrics["hd95"] - anchor_metrics["hd95"],
                        "help_vs_nnunet": None if not anchor_metrics else metrics["dice"] > anchor_metrics["dice"],
                        "harm_vs_nnunet": None if not anchor_metrics else metrics["dice"] < anchor_metrics["dice"],
                    }
                    rows.append(row)
                    ckpt_rows.append(row)
        dice_scores = [float(r["dice"]) for r in ckpt_rows]
        summaries.append(
            {
                "checkpoint": str(checkpoint),
                "checkpoint_sha256": file_sha256(checkpoint),
                "case_count": len({r["case_id"] for r in ckpt_rows}),
                "row_count": len(ckpt_rows),
                "mean_dice": sum(dice_scores) / max(len(dice_scores), 1),
            }
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "case_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["case_id"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    selected = max(summaries, key=lambda r: r["mean_dice"]) if summaries else None
    summary_payload = {
        "status": "PASS",
        "split": args.split,
        "outer_accessed": args.split == "outer",
        "checkpoint_count": len(checkpoints),
        "case_count": len({r["case_id"] for r in rows}),
        "row_count": len(rows),
        "summaries": summaries,
        "selected_checkpoint": selected,
        "nnunet_comparator_bound": args.nnunet_checkpoint is not None,
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.select_inner and args.split != "inner_select":
        raise SystemExit("--select-inner requires --split inner_select")
    if args.write_freeze:
        if selected is None:
            raise SystemExit("cannot write freeze receipt without selected checkpoint")
        freeze = {
            "status": "PASS",
            "selected_checkpoint": selected["checkpoint"],
            "selected_checkpoint_sha256": selected["checkpoint_sha256"],
            "selection_split": args.split,
            "outer_accessed_before_freeze": False,
            "thresholds": {"scar": 0.5, "edema_zone": 0.5},
            "decode_rule": "edema_zone direct, scar priority, pure edema = edema_zone - scar",
        }
        (args.output_dir / "freeze_receipt.json").write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "case_count": summary_payload["case_count"], "output_dir": str(args.output_dir)}, sort_keys=True))


if __name__ == "__main__":
    main()
