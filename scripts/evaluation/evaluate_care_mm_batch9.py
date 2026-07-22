#!/usr/bin/env python3
"""Evaluate CARE Batch9 checkpoints on fold0 validation cases."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import SimpleITK as sitk
import torch
from scipy.ndimage import binary_erosion, distance_transform_edt, generate_binary_structure, label, zoom

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class  # noqa: E402
from src.care_myocardium.data.care_mm_batch9 import (  # noqa: E402
    PREPROCESSED,
    RAW_LABEL_DIR,
    STANDARD_NNUNET_VAL,
    build_case_records,
    load_fold_cases,
    sha256_file,
    write_csv,
    write_json,
)
from src.care_myocardium.models.care_mm_reliable_distill import (  # noqa: E402
    CAREMMReliableDistillResEnc,
    crop_from_pad,
    pad_to_stride,
)


TASK_KEY = "20260722_care_myops_batch9_reliable_label_distillation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
LABELS = {"edema": 4, "scar": 5}


def read_label(path: Path, reference: sitk.Image | None = None) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    if reference is not None:
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(reference)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        img = resampler.Execute(img)
    return img, sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def load_preprocessed(case_id: str) -> np.ndarray:
    return np.asarray(blosc2.open(urlpath=str(PREPROCESSED / f"{case_id}.b2nd"), mode="r", dparams={"nthreads": 1})).astype(np.float32, copy=False)


def component_stats(pred: np.ndarray, gt: np.ndarray, myocardium: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> dict[str, Any]:
    spacing_volume = float(np.prod(spacing_zyx))
    pred_mask = pred == class_id
    gt_mask = gt == class_id
    cc, n_cc = label(pred_mask, structure=generate_binary_structure(pred.ndim, 1))
    if myocardium.any():
        dist_to_myo = distance_transform_edt(~myocardium.astype(bool), sampling=spacing_zyx)
        remote_fp = pred_mask & ~gt_mask & (dist_to_myo > 10.0)
    else:
        remote_fp = pred_mask & ~gt_mask
    return {
        "component_count": int(n_cc),
        "remote_fp_volume_mm3": float(np.count_nonzero(remote_fp) * spacing_volume),
        "pred_volume_mm3": float(np.count_nonzero(pred_mask) * spacing_volume),
        "gt_volume_mm3": float(np.count_nonzero(gt_mask) * spacing_volume),
        "volume_ratio": None if not gt_mask.any() else float(np.count_nonzero(pred_mask) / max(1, np.count_nonzero(gt_mask))),
        "empty_prediction": int(not pred_mask.any()),
    }


def precision_recall(pred: np.ndarray, gt: np.ndarray, class_id: int) -> tuple[float | None, float | None]:
    p = pred == class_id
    g = gt == class_id
    tp = int(np.count_nonzero(p & g))
    fp = int(np.count_nonzero(p & ~g))
    fn = int(np.count_nonzero(~p & g))
    precision = None if tp + fp == 0 else float(tp / (tp + fp))
    recall = None if tp + fn == 0 else float(tp / (tp + fn))
    return precision, recall


def mean(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get(key) not in ("", None) and not (isinstance(r.get(key), float) and math.isnan(r[key]))]
    return float(np.mean(vals)) if vals else None



def align_prediction_to_reference(pred: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Nearest-neighbor align model output array to the raw-label grid shape."""
    if pred.shape == reference.shape:
        return pred.astype(np.uint8, copy=False)
    if any(dim <= 0 for dim in pred.shape) or any(dim <= 0 for dim in reference.shape):
        raise ValueError(f"invalid prediction/reference shape: {pred.shape} vs {reference.shape}")
    factors = tuple(float(dst) / float(src) for src, dst in zip(pred.shape, reference.shape))
    aligned = zoom(pred, zoom=factors, order=0)
    slices = tuple(slice(0, size) for size in reference.shape)
    aligned = aligned[slices]
    if aligned.shape != reference.shape:
        fixed = np.zeros(reference.shape, dtype=aligned.dtype)
        common = tuple(slice(0, min(a, b)) for a, b in zip(aligned.shape, reference.shape))
        fixed[common] = aligned[common]
        aligned = fixed
    return aligned.astype(np.uint8, copy=False)

def predict_case(model: CAREMMReliableDistillResEnc, case_id: str, availability: tuple[float, float, float], device: torch.device) -> np.ndarray:
    x = torch.from_numpy(load_preprocessed(case_id)[None]).to(device)
    for ch, present in enumerate(availability):
        if present < 0.5:
            x[:, ch] = 0
    x, added = pad_to_stride(x)
    avail = torch.tensor([availability], device=device, dtype=torch.float32)
    with torch.no_grad():
        logits = model(x, avail)["six_class_logits"]
        logits = crop_from_pad(logits, added)
        pred = logits.argmax(1)[0].detach().cpu().numpy().astype(np.uint8)
    return pred


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    device = torch.device(args.device)
    ckpt_path = REPO_ROOT / args.checkpoint
    payload = torch.load(ckpt_path, map_location=device, weights_only=False)
    model = CAREMMReliableDistillResEnc().to(device)
    model.load_state_dict(payload["model"])
    model.eval()
    records = {r.case_id: r for r in build_case_records(0)}
    _train, val = load_fold_cases(0)
    pred_dir = REPO_ROOT / args.prediction_dir
    pred_dir.mkdir(parents=True, exist_ok=True)
    baseline_dir = STANDARD_NNUNET_VAL
    case_rows: list[dict[str, Any]] = []
    help_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    for case_id in sorted(val):
        record = records[case_id]
        gt_img, gt = read_label(RAW_LABEL_DIR / f"{case_id}.nii.gz")
        pred_raw = predict_case(model, case_id, record.availability, device)
        pred = align_prediction_to_reference(pred_raw, gt)
        ref_img = gt_img
        out_img = sitk.GetImageFromArray(pred)
        out_img.CopyInformation(ref_img)
        out_path = pred_dir / f"{case_id}.nii.gz"
        sitk.WriteImage(out_img, str(out_path))
        _base_img, base = read_label(baseline_dir / f"{case_id}.nii.gz", gt_img)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        myocardium = (gt >= 1) & (gt <= 5)
        manifest_rows.append(
            {
                "case_id": case_id,
                "prediction_path": str(out_path.relative_to(REPO_ROOT)),
                "prediction_sha256": sha256_file(out_path),
                "checkpoint_path": str(ckpt_path.relative_to(REPO_ROOT)),
                "checkpoint_sha256": sha256_file(ckpt_path),
                "center": record.center,
                "modality_group": record.modality_group,
            }
        )
        for pathology, class_id in LABELS.items():
            dice = dice_per_class(pred, gt, class_id, skip_if_gt_empty=True)
            base_dice = dice_per_class(base, gt, class_id, skip_if_gt_empty=True)
            prec, rec = precision_recall(pred, gt, class_id)
            row = {
                "variant": args.variant,
                "seed": args.seed,
                "case_id": case_id,
                "pathology": pathology,
                "class_id": class_id,
                "dice": dice,
                "baseline_dice": base_dice,
                "dice_delta_vs_standard_nnunet": None if dice is None or base_dice is None else float(dice - base_dice),
                "hd95": hd95_class(pred, gt, class_id, spacing),
                "precision": prec,
                "recall": rec,
                "changed_voxels_vs_standard_nnunet": int(np.count_nonzero((pred == class_id) != (base == class_id))),
                "gt_positive": int(bool(np.any(gt == class_id))),
                "prediction_positive": int(bool(np.any(pred == class_id))),
                "center": record.center,
                "modality_group": record.modality_group,
                "complete_trimodal": int(record.t2_present and record.c0_present),
                "scar_positive": int(record.scar_positive),
                "edema_positive": int(record.edema_positive),
            }
            row.update(component_stats(pred, gt, myocardium, class_id, spacing))
            case_rows.append(row)
            help_rows.append(
                {
                    "variant": args.variant,
                    "seed": args.seed,
                    "case_id": case_id,
                    "pathology": pathology,
                    "dice_delta_vs_standard_nnunet": row["dice_delta_vs_standard_nnunet"],
                    "changed_voxels_vs_standard_nnunet": row["changed_voxels_vs_standard_nnunet"],
                    "help_harm": "identity" if row["changed_voxels_vs_standard_nnunet"] == 0 else ("help" if (row["dice_delta_vs_standard_nnunet"] or 0) > 0 else "harm_or_neutral"),
                }
            )
    subgroup_defs = {
        "all_cases": lambda r: True,
        "positive_gt": lambda r: bool(r["gt_positive"]),
        "complete_trimodal": lambda r: bool(r["complete_trimodal"]),
        "CenterB": lambda r: r["center"] == "CenterB",
        "CenterC": lambda r: r["center"] == "CenterC",
        "lge_only": lambda r: r["modality_group"] == "LGE-only",
        "lge_c0": lambda r: r["modality_group"] == "C0+LGE",
        "small_scar": lambda r: r["pathology"] == "scar" and bool(r["gt_positive"]) and float(r["gt_volume_mm3"]) < 500,
        "large_scar": lambda r: r["pathology"] == "scar" and bool(r["gt_positive"]) and float(r["gt_volume_mm3"]) >= 500,
        "low_baseline": lambda r: r["baseline_dice"] is not None and float(r["baseline_dice"]) < 0.5,
        "high_baseline": lambda r: r["baseline_dice"] is not None and float(r["baseline_dice"]) >= 0.5,
    }
    subgroup_rows: list[dict[str, Any]] = []
    for pathology in LABELS:
        rows_p = [r for r in case_rows if r["pathology"] == pathology]
        for subgroup, pred in subgroup_defs.items():
            rows_s = [r for r in rows_p if pred(r)]
            subgroup_rows.append(
                {
                    "variant": args.variant,
                    "seed": args.seed,
                    "pathology": pathology,
                    "subgroup": subgroup,
                    "case_rows": len(rows_s),
                    "mean_dice": mean(rows_s, "dice"),
                    "mean_baseline_dice": mean(rows_s, "baseline_dice"),
                    "mean_dice_delta_vs_standard_nnunet": mean(rows_s, "dice_delta_vs_standard_nnunet"),
                    "mean_hd95": mean(rows_s, "hd95"),
                    "mean_remote_fp_volume_mm3": mean(rows_s, "remote_fp_volume_mm3"),
                    "empty_prediction_rate": mean(rows_s, "empty_prediction"),
                }
            )
    out_dir = REPO_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / f"{args.prefix}_casewise_metrics.csv", case_rows)
    write_csv(out_dir / f"{args.prefix}_subgroup_metrics.csv", subgroup_rows)
    write_csv(out_dir / f"{args.prefix}_help_harm.csv", help_rows)
    write_csv(out_dir / f"{args.prefix}_prediction_manifest.csv", manifest_rows)
    receipt = {
        "schema_version": 1,
        "status": "PASS",
        "variant": args.variant,
        "seed": args.seed,
        "case_count": len(val),
        "checkpoint_reloaded": True,
        "prediction_dir": str(pred_dir.relative_to(REPO_ROOT)),
        "checkpoint": str(ckpt_path.relative_to(REPO_ROOT)),
    }
    write_json(out_dir / f"{args.prefix}_evaluation_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--prediction-dir", required=True)
    parser.add_argument("--output-dir", default=str(RESULT_ROOT))
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    result = evaluate(args)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
