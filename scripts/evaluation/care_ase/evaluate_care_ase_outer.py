#!/usr/bin/env python
"""One-time CARE-ASE outer evaluation for a fixed fold checkpoint."""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch
from scipy.ndimage import binary_erosion, distance_transform_edt, label as cc_label

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.data.care_ase_splits import build_care_ase_case_roles
from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint, write_json


PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
SPLITS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
RESULT_DIR = REPO_ROOT / "results/20260801_care_ase_final_model"


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def read_spacing(case_id: str) -> tuple[float, float, float]:
    with (PREPROCESSED / f"{case_id}.pkl").open("rb") as f:
        props = pickle.load(f)
    return tuple(float(v) for v in props.get("spacing", (1.0, 1.0, 1.0)))


def crop_or_pad(array: np.ndarray, patch_size: tuple[int, int, int]) -> tuple[np.ndarray, tuple[slice, slice, slice], tuple[slice, slice, slice]]:
    spatial = array.shape[-3:]
    out_shape = array.shape[:-3] + patch_size
    out = np.zeros(out_shape, dtype=array.dtype)
    src = []
    dst = []
    for dim, size in zip(spatial, patch_size):
        src_start = max(0, (dim - size) // 2)
        src_stop = min(dim, src_start + size)
        dst_start = max(0, (size - dim) // 2)
        dst_stop = dst_start + (src_stop - src_start)
        src.append(slice(src_start, src_stop))
        dst.append(slice(dst_start, dst_stop))
    out[(..., *dst)] = array[(..., *src)]
    return out, tuple(src), tuple(dst)  # type: ignore[return-value]


def starts_for(dim: int, patch: int, overlap: float = 0.5) -> list[int]:
    if dim <= patch:
        return [0]
    stride = max(1, int(round(float(patch) * (1.0 - float(overlap)))))
    starts = list(range(0, dim - patch + 1, stride))
    last = dim - patch
    if starts[-1] != last:
        starts.append(last)
    return starts


def extract_start(array: np.ndarray, start: tuple[int, int, int], patch_size: tuple[int, int, int]) -> tuple[np.ndarray, tuple[slice, slice, slice], tuple[slice, slice, slice]]:
    spatial = array.shape[-3:]
    out_shape = array.shape[:-3] + patch_size
    out = np.zeros(out_shape, dtype=array.dtype)
    src = []
    dst = []
    for dim, start_dim, patch in zip(spatial, start, patch_size):
        if dim <= patch:
            src_start = 0
            src_stop = dim
            dst_start = (patch - dim) // 2
        else:
            src_start = min(max(int(start_dim), 0), dim - patch)
            src_stop = src_start + patch
            dst_start = 0
        dst_stop = dst_start + (src_stop - src_start)
        src.append(slice(src_start, src_stop))
        dst.append(slice(dst_start, dst_stop))
    out[(..., *dst)] = array[(..., *src)]
    return out, tuple(src), tuple(dst)  # type: ignore[return-value]


def sliding_window_final_logits(
    model: torch.nn.Module,
    image_np: np.ndarray,
    availability: torch.Tensor,
    *,
    patch_size: tuple[int, int, int],
    device: torch.device,
    global_step: int = 14000,
    overlap: float = 0.5,
    **model_flags: Any,
) -> tuple[np.ndarray, dict[str, Any]]:
    spatial = tuple(int(v) for v in image_np.shape[-3:])
    z_starts = starts_for(spatial[0], patch_size[0], overlap)
    y_starts = starts_for(spatial[1], patch_size[1], overlap)
    x_starts = starts_for(spatial[2], patch_size[2], overlap)
    patch_starts = [(z, y, x) for z in z_starts for y in y_starts for x in x_starts]
    logits_sum = np.zeros((6, *spatial), dtype=np.float32)
    weight = np.zeros(spatial, dtype=np.float32)
    for start in patch_starts:
        image_patch, src, dst = extract_start(image_np, start, patch_size)
        image = torch.from_numpy(image_patch[None]).to(device=device, dtype=torch.float32)
        logits = model(image, availability, global_step=global_step, **model_flags)["final_logits"].squeeze(0).detach().cpu().numpy().astype(np.float32, copy=False)
        logits_sum[(slice(None), *src)] += logits[(slice(None), *dst)]
        weight[src] += 1.0
    if np.any(weight <= 0):
        raise RuntimeError(f"sliding-window coverage hole for spatial shape {spatial}")
    logits_sum /= weight[None]
    return logits_sum, {
        "inference_method": "tiled_sliding_window_average_logits",
        "patch_size": list(patch_size),
        "overlap": float(overlap),
        "patch_count": len(patch_starts),
        "spatial_shape": list(spatial),
        "first_patch_start": list(patch_starts[0]),
        "last_patch_start": list(patch_starts[-1]),
    }


def decode_logits_np(logits: np.ndarray, *, t2_present: bool) -> np.ndarray:
    if not t2_present:
        five = np.concatenate([logits[:4], logits[5:6]], axis=0)
        pred5 = five.argmax(0).astype(np.int64, copy=False)
        pred = pred5.copy()
        pred[pred5 == 4] = 5
        return pred
    return logits.argmax(0).astype(np.int64, copy=False)


def dice(pred: np.ndarray, gt: np.ndarray, cls: int) -> float:
    valid = gt >= 0
    p = (pred == cls) & valid
    g = gt == cls
    denom = int(p.sum() + g.sum())
    if denom == 0:
        return 1.0
    return float(2 * int((p & g).sum()) / denom)


def surface(mask: np.ndarray) -> np.ndarray:
    mask = mask.astype(bool)
    if not mask.any():
        return mask
    return mask ^ binary_erosion(mask)


def hd_metrics(pred_mask: np.ndarray, gt_mask: np.ndarray, spacing: tuple[float, float, float]) -> tuple[float, float, float, float]:
    if not pred_mask.any() and not gt_mask.any():
        return 0.0, 0.0, 0.0, 0.0
    if not pred_mask.any() or not gt_mask.any():
        return math.inf, math.inf, math.inf, math.inf
    pred_surface = surface(pred_mask)
    gt_surface = surface(gt_mask)
    pred_to_gt = distance_transform_edt(~gt_surface)[pred_surface]
    gt_to_pred = distance_transform_edt(~pred_surface)[gt_surface]
    distances_vox = np.concatenate([pred_to_gt, gt_to_pred]).astype(np.float64)
    pred_to_gt_mm = distance_transform_edt(~gt_surface, sampling=spacing)[pred_surface]
    gt_to_pred_mm = distance_transform_edt(~pred_surface, sampling=spacing)[gt_surface]
    distances_mm = np.concatenate([pred_to_gt_mm, gt_to_pred_mm]).astype(np.float64)
    return float(distances_vox.max()), float(np.percentile(distances_vox, 95)), float(distances_mm.max()), float(np.percentile(distances_mm, 95))


def class_metrics(pred: np.ndarray, gt: np.ndarray, cls: int, spacing: tuple[float, float, float]) -> dict[str, Any]:
    valid = gt >= 0
    pred_mask = (pred == cls) & valid
    gt_mask = gt == cls
    tp = int((pred_mask & gt_mask).sum())
    fp = int((pred_mask & ~gt_mask & valid).sum())
    fn = int((~pred_mask & gt_mask).sum())
    exact_hd, hd95, exact_hd_mm, hd95_mm = hd_metrics(pred_mask, gt_mask, spacing)
    gt_distance_mm = distance_transform_edt(~gt_mask, sampling=spacing) if gt_mask.any() else np.full(gt.shape, math.inf, dtype=np.float32)
    blood_pool = (gt == 2) | (gt == 3)
    blood_distance_mm = distance_transform_edt(~blood_pool, sampling=spacing) if blood_pool.any() else np.full(gt.shape, math.inf, dtype=np.float32)
    fp_mask = pred_mask & ~gt_mask & valid
    voxel_volume_mm3 = float(math.prod(spacing))
    gt_volume_mm3 = float(gt_mask.sum() * voxel_volume_mm3)
    pred_volume_mm3 = float(pred_mask.sum() * voxel_volume_mm3)
    return {
        "Dice": dice(pred, gt, cls),
        "exact_HD_vox": exact_hd,
        "HD95_vox": hd95,
        "exact_HD_mm": exact_hd_mm,
        "HD95_mm": hd95_mm,
        "precision": float(tp / (tp + fp)) if tp + fp else (1.0 if not gt_mask.any() else 0.0),
        "sensitivity": float(tp / (tp + fn)) if tp + fn else (1.0 if not gt_mask.any() else 0.0),
        "lesion_present_recall": float((pred_mask & gt_mask).any()) if gt_mask.any() else math.nan,
        "small_lesion_recall": float((pred_mask & gt_mask).any()) if 0.0 < gt_volume_mm3 < 1000.0 else math.nan,
        "component_count": int(cc_label(pred_mask)[1]),
        "pred_voxels": int(pred_mask.sum()),
        "gt_voxels": int(gt_mask.sum()),
        "pred_volume_mm3": pred_volume_mm3,
        "gt_volume_mm3": gt_volume_mm3,
        "volume_ratio": float(pred_mask.sum() / max(gt_mask.sum(), 1)),
        "remote_fp_volume_mm3": float((fp_mask & (gt_distance_mm > 10.0)).sum() * voxel_volume_mm3),
        "blood_pool_adjacent_fp_volume_mm3": float((fp_mask & (blood_distance_mm <= 2.0)).sum() * voxel_volume_mm3),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["case_id"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--patch-size", default="20,256,256")
    parser.add_argument("--overlap", type=float, default=0.5)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    patch_size = tuple(int(v) for v in args.patch_size.replace("x", ",").split(",") if v)
    if len(patch_size) != 3:
        raise ValueError("--patch-size must contain exactly three integers")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    output_dir = args.output_dir.resolve()
    if (output_dir / "evaluation_receipt.json").exists() and not args.force:
        raise FileExistsError(f"outer evaluation already exists: {output_dir / 'evaluation_receipt.json'}")
    model, payload = load_care_ase_checkpoint(args.checkpoint, map_location="cpu", restore_rng=False)
    if int(payload["global_optimizer_step"]) != 14000:
        raise ValueError("outer evaluation requires fixed checkpoint_step14000.pt")
    model.to(device).eval()
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    val_cases = [str(v) for v in splits[int(args.fold)]["val"]]
    metadata = load_myops_case_metadata(REPO_ROOT)
    role_lookup = {(row.fold, row.case_id): row for row in build_care_ase_case_roles(REPO_ROOT, args.fold)}
    rows = []
    pred_voxels = []
    patch_counts = []
    with torch.no_grad():
        for case_id in val_cases:
            image_np = read_b2nd(PREPROCESSED / f"{case_id}.b2nd").astype(np.float32, copy=False)
            seg_np = read_b2nd(PREPROCESSED / f"{case_id}_seg.b2nd")[0].astype(np.int64, copy=False)
            spacing = read_spacing(case_id)
            availability = torch.tensor([metadata[case_id].availability], device=device, dtype=torch.float32)
            logits_np, infer_meta = sliding_window_final_logits(
                model,
                image_np,
                availability,
                patch_size=patch_size,
                device=device,
                global_step=14000,
                overlap=float(args.overlap),
            )
            t2_present = bool(float(availability[0, 1].detach().cpu()) > 0.0)
            pred = decode_logits_np(logits_np, t2_present=t2_present)
            scar = class_metrics(pred, seg_np, 5, spacing)
            edema = class_metrics(pred, seg_np, 4, spacing)
            patch_counts.append(int(infer_meta["patch_count"]))
            role = role_lookup[(int(args.fold), case_id)]
            common = {
                "case_id": case_id,
                "fold": int(args.fold),
                "role": role.role,
                "sentinel": role.sentinel,
                "center": metadata[case_id].center,
                "modality_group": metadata[case_id].modality_group,
                "spacing_zyx": "|".join(f"{v:.6g}" for v in spacing),
                "decode": "argmax_6class_t2_present" if t2_present else "argmax_5class_no_t2_excludes_class4",
                "inference_method": infer_meta["inference_method"],
                "patch_count": infer_meta["patch_count"],
            }
            rows.append({**common, "class": "scar", **scar})
            rows.append({**common, "class": "edema", **edema})
            pred_voxels.append(
                {
                    "case_id": case_id,
                    "scar_pred_voxels": scar["pred_voxels"],
                    "edema_pred_voxels": edema["pred_voxels"],
                    "inference_method": infer_meta["inference_method"],
                    "patch_count": infer_meta["patch_count"],
                    "spatial_shape": "|".join(str(v) for v in infer_meta["spatial_shape"]),
                    "patch_size": "|".join(str(v) for v in infer_meta["patch_size"]),
                    "overlap": infer_meta["overlap"],
                }
            )
    write_csv(output_dir / "casewise_metrics.csv", rows)
    write_csv(output_dir / "pred_voxels.csv", pred_voxels)
    summary: dict[str, Any] = {
        "status": "PASS",
        "fold": int(args.fold),
        "checkpoint": str(args.checkpoint),
        "global_optimizer_step": int(payload["global_optimizer_step"]),
        "case_count": len(val_cases),
        "one_time_outer_evaluation": True,
        "force_overwrite_used": bool(args.force),
        "inference_method": "tiled_sliding_window_average_logits",
        "patch_size": list(patch_size),
        "overlap": float(args.overlap),
        "patch_count_min": int(min(patch_counts)) if patch_counts else 0,
        "patch_count_max": int(max(patch_counts)) if patch_counts else 0,
    }
    for cls in ("scar", "edema"):
        cls_rows = [row for row in rows if row["class"] == cls]
        summary[f"{cls}_mean_Dice"] = float(np.mean([float(row["Dice"]) for row in cls_rows])) if cls_rows else math.nan
        summary[f"{cls}_mean_HD95_vox"] = float(np.mean([float(row["HD95_vox"]) for row in cls_rows if math.isfinite(float(row["HD95_vox"]))])) if cls_rows else math.nan
        summary[f"{cls}_mean_HD95_mm"] = float(np.mean([float(row["HD95_mm"]) for row in cls_rows if math.isfinite(float(row["HD95_mm"]))])) if cls_rows else math.nan
        summary[f"{cls}_mean_remote_fp_volume_mm3"] = float(np.mean([float(row["remote_fp_volume_mm3"]) for row in cls_rows])) if cls_rows else math.nan
        summary[f"{cls}_mean_blood_pool_adjacent_fp_volume_mm3"] = float(np.mean([float(row["blood_pool_adjacent_fp_volume_mm3"]) for row in cls_rows])) if cls_rows else math.nan
    write_json(output_dir / "evaluation_receipt.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
