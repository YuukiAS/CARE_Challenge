#!/usr/bin/env python3
"""Task-scoped fold0 runner for SRR-MyoPS variants."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk
import torch
from scipy.ndimage import generate_binary_structure, label
from torch import nn


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class, hd_class
from src.care_myocardium.data.case_metadata import MyoPSCaseMetadata, load_myops_case_metadata
from src.care_myocardium.losses.srr_losses import srr_total_loss
from src.care_myocardium.models.srr_myops import ConditionalDualHeadControl, SRRMyoPSLite


RAW_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS"
SPLIT_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
DEFAULT_OUT_ROOT = REPO_ROOT / "results/20260621_srr_fold0"
IGNORE_LABEL = -1


@dataclass
class CaseData:
    case_id: str
    image: np.ndarray
    label_arr: np.ndarray
    label_img: sitk.Image
    availability: np.ndarray
    metadata: MyoPSCaseMetadata


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


def load_split(fold: int) -> tuple[list[str], list[str]]:
    data = json.loads(SPLIT_JSON.read_text(encoding="utf-8"))
    split = data["folds"][fold]
    return list(split["train"]), list(split["val"])


def normalize_channel(arr: np.ndarray, present: bool) -> np.ndarray:
    arr = arr.astype(np.float32, copy=False)
    if not present:
        return np.zeros_like(arr, dtype=np.float32)
    mask = np.abs(arr) > 1e-6
    if not np.any(mask):
        return np.zeros_like(arr, dtype=np.float32)
    values = arr[mask]
    lo, hi = np.percentile(values, [0.5, 99.5])
    arr = np.clip(arr, lo, hi)
    mean_v = float(arr[mask].mean())
    std_v = float(arr[mask].std())
    if std_v < 1e-6:
        std_v = 1.0
    arr = (arr - mean_v) / std_v
    arr[~mask] = 0.0
    return arr.astype(np.float32, copy=False)


def read_case(case_id: str, metadata: dict[str, MyoPSCaseMetadata]) -> CaseData:
    meta = metadata[case_id]
    arrays = []
    for idx, present in enumerate(meta.availability):
        img = sitk.ReadImage(str(RAW_ROOT / "imagesTr" / f"{case_id}_{idx:04d}.nii.gz"))
        arrays.append(normalize_channel(sitk.GetArrayFromImage(img), bool(present)))
    label_img = sitk.ReadImage(str(RAW_ROOT / "labelsTr" / f"{case_id}.nii.gz"))
    label_arr = sitk.GetArrayFromImage(label_img).astype(np.int64, copy=False)
    return CaseData(
        case_id=case_id,
        image=np.stack(arrays, axis=0),
        label_arr=label_arr,
        label_img=label_img,
        availability=np.asarray(meta.availability, dtype=np.float32),
        metadata=meta,
    )


def crop_or_pad(array: np.ndarray, starts: tuple[int, int, int], patch_shape: tuple[int, int, int], pad_value: float | int) -> np.ndarray:
    slices = []
    pads = []
    for start, size, dim in zip(starts, patch_shape, array.shape[-3:]):
        lo = max(0, start)
        hi = min(dim, start + size)
        slices.append(slice(lo, hi))
        pads.append((max(0, -start), max(0, start + size - dim)))
    cropped = array[(..., *slices)]
    return np.pad(cropped, [(0, 0)] * (array.ndim - 3) + pads, mode="constant", constant_values=pad_value)


def sample_patch(
    case: CaseData,
    patch_shape: tuple[int, int, int],
    rng: np.random.Generator,
    oversample_foreground: float,
    modality_dropout: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    label_arr = case.label_arr
    focus = np.argwhere(np.isin(label_arr, [4, 5]))
    if len(focus) and rng.random() < oversample_foreground:
        center = focus[int(rng.integers(0, len(focus)))]
    else:
        valid = np.argwhere(label_arr >= 0)
        center = valid[int(rng.integers(0, len(valid)))] if len(valid) else np.asarray(label_arr.shape) // 2
    starts = tuple(int(c - p // 2) for c, p in zip(center, patch_shape))
    image = crop_or_pad(case.image, starts, patch_shape, 0.0).astype(np.float32, copy=False)
    target = crop_or_pad(label_arr[None], starts, patch_shape, IGNORE_LABEL).astype(np.int64, copy=False)[0]
    availability = case.availability.copy()
    if modality_dropout:
        # Preserve LGE. Drop C0/T2 only when originally present; dropped T2 also
        # disables edema dense loss through the availability vector.
        if availability[1] > 0 and rng.random() < 0.15:
            availability[1] = 0.0
            image[1] = 0.0
        if availability[2] > 0 and rng.random() < 0.15:
            availability[2] = 0.0
            image[2] = 0.0
    return image, target, availability


def parse_shape(text: str) -> tuple[int, int, int]:
    parts = [int(x) for x in text.lower().replace(",", "x").split("x") if x]
    if len(parts) != 3:
        raise ValueError(f"expected Dz,Y,X patch shape, got {text!r}")
    return tuple(parts)  # type: ignore[return-value]


def make_model(variant: str, base_channels: int, device: torch.device) -> nn.Module:
    if variant == "conditional_dualhead_control":
        model: nn.Module = ConditionalDualHeadControl(base_channels=base_channels)
    elif variant == "srr_minimal":
        model = SRRMyoPSLite(base_channels=base_channels)
    else:
        raise ValueError(f"unknown variant {variant}")
    return model.to(device)


def batch_from_cases(
    cases: list[CaseData],
    complete_cases: list[CaseData],
    batch_size: int,
    patch_shape: tuple[int, int, int],
    rng: np.random.Generator,
    complete_oversample: float,
    oversample_foreground: float,
    modality_dropout: bool,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[str]]:
    xs, ys, avs, keys = [], [], [], []
    for _ in range(batch_size):
        pool = complete_cases if complete_cases and rng.random() < complete_oversample else cases
        case = pool[int(rng.integers(0, len(pool)))]
        x, y, av = sample_patch(case, patch_shape, rng, oversample_foreground, modality_dropout)
        xs.append(x)
        ys.append(y)
        avs.append(av)
        keys.append(case.case_id)
    return (
        torch.from_numpy(np.stack(xs, axis=0)).float(),
        torch.from_numpy(np.stack(ys, axis=0)).long(),
        torch.from_numpy(np.stack(avs, axis=0)).float(),
        keys,
    )


def finite_mean(values: list[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None and not math.isnan(float(v)) and not math.isinf(float(v))]
    return float(mean(vals)) if vals else None


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def volume_ratio(pred: np.ndarray, gt: np.ndarray) -> float | None:
    p = int(pred.sum())
    g = int(gt.sum())
    if g == 0:
        return None if p == 0 else float("inf")
    return float(p / g)


def fp_counts(pred_mask: np.ndarray, gt_mask: np.ndarray, small_threshold: int = 20) -> tuple[int, int]:
    cc, n_cc = label(pred_mask.astype(bool), structure=generate_binary_structure(pred_mask.ndim, 1))
    small_fp = 0
    remote_fp = 0
    gt_coords = np.argwhere(gt_mask)
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if np.logical_and(comp, gt_mask).any():
            continue
        if int(comp.sum()) < small_threshold:
            small_fp += 1
        if not len(gt_coords):
            remote_fp += 1
            continue
        coords = np.argwhere(comp)
        comp_center = coords.mean(axis=0)
        gt_min = gt_coords.min(axis=0)
        gt_max = gt_coords.max(axis=0)
        outside = np.maximum(0, np.maximum(gt_min - comp_center, comp_center - gt_max))
        if float(np.linalg.norm(outside)) > 20.0:
            remote_fp += 1
    return small_fp, remote_fp


def predict_full_case(model: nn.Module, case: CaseData, device: torch.device) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(case.image[None]).float().to(device)
        av = torch.from_numpy(case.availability[None]).float().to(device)
        pred = torch.argmax(model(x, av)["logits"], dim=1)[0].detach().cpu().numpy().astype(np.uint8)
    return pred


def write_prediction(path: Path, pred: np.ndarray, reference: sitk.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(pred)
    img.CopyInformation(reference)
    sitk.WriteImage(img, str(path))


def collect_case_metrics(variant: str, case: CaseData, pred: np.ndarray) -> list[dict[str, object]]:
    gt = case.label_arr.astype(np.uint8, copy=False)
    invalid = sorted(set(np.unique(pred).tolist()) - {0, 1, 2, 3, 4, 5})
    spacing = tuple(float(x) for x in case.label_img.GetSpacing()[::-1])
    rows = []
    for cls, name in [(4, "myops_edema"), (5, "myops_scar")]:
        pred_mask = pred == cls
        gt_mask = gt == cls
        small_fp, remote_fp = fp_counts(pred_mask, gt_mask)
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": case.metadata.t2_present,
                "class_id": cls,
                "metric_name": name,
                "dice": dice_per_class(pred, gt, cls, skip_if_gt_empty=False),
                "hd": hd_class(pred, gt, cls, spacing),
                "hd95": hd95_class(pred, gt, cls, spacing),
                "component_count": component_count(pred_mask),
                "small_fp_count": small_fp,
                "remote_fp_count": remote_fp,
                "pred_gt_volume_ratio": volume_ratio(pred_mask, gt_mask),
                "pred_empty": not bool(pred_mask.any()),
                "gt_empty": not bool(gt_mask.any()),
                "invalid_label_values": ",".join(str(v) for v in invalid),
            }
        )
    return rows


def summarize_subgroups(variant: str, case_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    groups: list[tuple[str, callable]] = [
        ("all_cases", lambda r: True),
        ("gt_positive_only", lambda r: not bool(r["gt_empty"])),
        ("t2_present", lambda r: bool(r["t2_present"])),
        ("complete_modality", lambda r: r["modality_group"] == "C0+LGE+T2"),
        ("CenterB", lambda r: r["center"] == "CenterB"),
        ("CenterC", lambda r: r["center"] == "CenterC"),
        ("C0+LGE", lambda r: r["modality_group"] == "C0+LGE"),
        ("LGE-only", lambda r: r["modality_group"] == "LGE-only"),
        ("no_T2_empty_GT", lambda r: (not bool(r["t2_present"])) and bool(r["gt_empty"])),
    ]
    for cls, name in [(4, "myops_edema"), (5, "myops_scar")]:
        cls_rows = [r for r in case_rows if int(r["class_id"]) == cls]
        for group_name, pred in groups:
            subset = [r for r in cls_rows if pred(r)]
            if not subset:
                continue
            rows.append(
                {
                    "variant": variant,
                    "class_id": cls,
                    "metric_name": name,
                    "group": group_name,
                    "n": len(subset),
                    "dice_mean": finite_mean([r["dice"] for r in subset]),  # type: ignore[list-item]
                    "hd_mean": finite_mean([r["hd"] for r in subset]),  # type: ignore[list-item]
                    "hd95_mean": finite_mean([r["hd95"] for r in subset]),  # type: ignore[list-item]
                    "component_count_mean": finite_mean([float(r["component_count"]) for r in subset]),
                    "remote_fp_mean": finite_mean([float(r["remote_fp_count"]) for r in subset]),
                    "empty_prediction_rate": finite_mean([1.0 if r["pred_empty"] else 0.0 for r in subset]),
                }
            )
    return rows


def evaluate_and_export(model: nn.Module, cases: list[CaseData], variant_dir: Path, variant: str, device: torch.device) -> None:
    pred_dir = variant_dir / "predictions/fold_0/checkpoint_best"
    case_rows: list[dict[str, object]] = []
    for case in cases:
        pred = predict_full_case(model, case, device)
        write_prediction(pred_dir / f"{case.case_id}.nii.gz", pred, case.label_img)
        case_rows.extend(collect_case_metrics(variant, case, pred))
    write_csv(variant_dir / "component_hd_by_case.csv", case_rows)
    write_csv(variant_dir / "subgroup_metrics.csv", summarize_subgroups(variant, case_rows))


def validate_patch_loss(model: nn.Module, val_cases: list[CaseData], patch_shape: tuple[int, int, int], device: torch.device, seed: int) -> float:
    rng = np.random.default_rng(seed)
    model.eval()
    losses = []
    with torch.no_grad():
        for case in val_cases[: min(12, len(val_cases))]:
            x_np, y_np, av_np = sample_patch(case, patch_shape, rng, oversample_foreground=1.0, modality_dropout=False)
            x = torch.from_numpy(x_np[None]).float().to(device)
            y = torch.from_numpy(y_np[None]).long().to(device)
            av = torch.from_numpy(av_np[None]).float().to(device)
            outputs = model(x, av)
            loss, _ = srr_total_loss(outputs, y, av)
            losses.append(float(loss.detach().cpu()))
    model.train()
    return float(mean(losses)) if losses else float("inf")


def record_gate_usage(rows: list[dict[str, object]], variant: str, step: int, keys: list[str], outputs: dict[str, object]) -> None:
    gates = outputs.get("gates", {})
    if not gates:
        rows.append({"variant": variant, "step": step, "task": "control_no_retrieval", "expert_index": "NA", "mean_weight": "NA", "batch_cases": ",".join(keys)})
        return
    for task, gate in gates.items():
        usage = gate.detach().mean(dim=0).cpu().tolist()
        for idx, value in enumerate(usage):
            rows.append({"variant": variant, "step": step, "task": task, "expert_index": idx, "mean_weight": float(value), "batch_cases": ",".join(keys)})


def train_variant(args: argparse.Namespace) -> None:
    if args.max_runtime_seconds < args.min_effective_seconds:
        raise ValueError("--max-runtime-seconds must be >= --min-effective-seconds")
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    train_ids, val_ids = load_split(args.fold)
    metadata = load_myops_case_metadata()
    train_cases = [read_case(cid, metadata) for cid in train_ids]
    val_cases = [read_case(cid, metadata) for cid in val_ids]
    complete_cases = [case for case in train_cases if case.metadata.modality_group == "C0+LGE+T2"]
    out_root = Path(args.out_root)
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    variant_dir = out_root / "variants" / args.variant
    checkpoint_dir = variant_dir / "checkpoints/fold_0/srr_fold0_config"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    patch_shape = parse_shape(args.patch_shape)
    model = make_model(args.variant, args.base_channels, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    rng = np.random.default_rng(args.seed)
    start = time.monotonic()
    best_val = float("inf")
    best_step = 0
    stop_reason = "max_steps"
    train_rows: list[dict[str, object]] = []
    usage_rows: list[dict[str, object]] = []
    model.train()
    for step in range(1, args.max_steps + 1):
        if time.monotonic() - start > args.max_runtime_seconds:
            stop_reason = "max_runtime_seconds"
            break
        x_cpu, y_cpu, av_cpu, keys = batch_from_cases(
            train_cases,
            complete_cases,
            args.batch_size,
            patch_shape,
            rng,
            args.complete_oversample,
            args.oversample_foreground,
            modality_dropout=True,
        )
        x = x_cpu.to(device)
        y = y_cpu.to(device)
        av = av_cpu.to(device)
        optimizer.zero_grad(set_to_none=True)
        outputs = model(x, av)
        loss, metrics = srr_total_loss(outputs, y, av)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        optimizer.step()
        if step == 1 or step % args.log_every == 0:
            supervised_fraction = float(av[:, 1].mean().detach().cpu())
            train_rows.append(
                {
                    "variant": args.variant,
                    "step": step,
                    "loss": float(loss.detach().cpu()),
                    "anatomy_loss": float(metrics["anatomy"].detach().cpu()),
                    "scar_loss": float(metrics["scar"].detach().cpu()),
                    "edema_loss": float(metrics["edema"].detach().cpu()),
                    "retrieval_loss": float(metrics["retrieval"].detach().cpu()),
                    "edema_supervised_batch_fraction": supervised_fraction,
                    "batch_cases": ",".join(keys),
                    "elapsed_seconds": time.monotonic() - start,
                }
            )
            record_gate_usage(usage_rows, args.variant, step, keys, outputs)
        if step == 1 or step % args.val_every == 0:
            val_loss = validate_patch_loss(model, val_cases, patch_shape, device, args.seed + step)
            train_rows.append(
                {
                    "variant": args.variant,
                    "step": step,
                    "loss": float(loss.detach().cpu()),
                    "val_patch_loss": val_loss,
                    "elapsed_seconds": time.monotonic() - start,
                    "event": "validation",
                }
            )
            if val_loss < best_val:
                best_val = val_loss
                best_step = step
                torch.save(
                    {
                        "variant": args.variant,
                        "step": step,
                        "model_state_dict": model.state_dict(),
                        "val_patch_loss": best_val,
                        "args": vars(args),
                    },
                    checkpoint_dir / "checkpoint_best.pt",
                )
    elapsed_seconds = time.monotonic() - start
    budget_status = "OK"
    if stop_reason == "max_steps" and elapsed_seconds < args.min_effective_seconds:
        budget_status = "UNDER_BUDGET_MAX_STEPS"
    final_ckpt = checkpoint_dir / "checkpoint_final.pt"
    torch.save({"variant": args.variant, "model_state_dict": model.state_dict(), "args": vars(args)}, final_ckpt)
    best_path = checkpoint_dir / "checkpoint_best.pt"
    if best_path.is_file():
        state = torch.load(best_path, map_location=device, weights_only=False)
        model.load_state_dict(state["model_state_dict"])
    else:
        torch.save({"variant": args.variant, "model_state_dict": model.state_dict(), "args": vars(args)}, best_path)
        best_step = args.max_steps
        best_val = float("nan")
    if not args.skip_export:
        evaluate_and_export(model, val_cases, variant_dir, args.variant, device)
    write_csv(variant_dir / "training_log.csv", train_rows)
    write_csv(variant_dir / "retrieval_usage.csv", usage_rows)
    summary = {
        "variant": args.variant,
        "fold": args.fold,
        "device": str(device),
        "train_cases": len(train_cases),
        "val_cases": len(val_cases),
        "complete_train_cases": len(complete_cases),
        "best_step": best_step,
        "best_val_patch_loss": best_val,
        "stop_reason": stop_reason,
        "elapsed_seconds": elapsed_seconds,
        "budget_status": budget_status,
        "max_steps": args.max_steps,
        "max_runtime_seconds": args.max_runtime_seconds,
        "min_effective_seconds": args.min_effective_seconds,
        "out_root": str(out_root),
        "checkpoint_best": str(best_path),
        "checkpoint_final": str(final_ckpt),
        "prediction_dir": str(variant_dir / "predictions/fold_0/checkpoint_best"),
        "export_skipped": bool(args.skip_export),
    }
    (variant_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_text(
        variant_dir / "summary.md",
        "\n".join(
            [
                f"# {args.variant} Fold0 Summary",
                "",
                f"- stop_reason: `{stop_reason}`",
                f"- budget_status: `{budget_status}`",
                f"- best_step: `{best_step}`",
                f"- best_val_patch_loss: `{best_val}`",
                f"- elapsed_seconds: `{summary['elapsed_seconds']:.1f}`",
                f"- checkpoint_best: `{best_path}`",
                f"- predictions: `{summary['prediction_dir']}`",
            ]
        )
        + "\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=["conditional_dualhead_control", "srr_minimal"])
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260621)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--base-channels", type=int, default=16)
    parser.add_argument("--patch-shape", default="12,96,96")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=1000000)
    parser.add_argument("--max-runtime-seconds", type=float, default=16200.0)
    parser.add_argument("--min-effective-seconds", type=float, default=0.0)
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--grad-clip", type=float, default=12.0)
    parser.add_argument("--log-every", type=int, default=50)
    parser.add_argument("--val-every", type=int, default=500)
    parser.add_argument("--complete-oversample", type=float, default=0.55)
    parser.add_argument("--oversample-foreground", type=float, default=0.75)
    parser.add_argument("--skip-export", action="store_true", help="Preflight only: skip full validation prediction export.")
    args = parser.parse_args()
    train_variant(args)


if __name__ == "__main__":
    main()
