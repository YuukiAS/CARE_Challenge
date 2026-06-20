#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy import ndimage


CARE_RAW_TO_COMPACT = {0: 0, 200: 1, 500: 2, 2221: 3}
CINEMA_LABELS = {0: "background", 1: "RV", 2: "myocardium", 3: "LV"}


def add_dependency_paths(extra_paths: list[Path]) -> None:
    for path in extra_paths:
        if path and path.exists() and str(path.resolve()) not in sys.path:
            sys.path.insert(0, str(path.resolve()))


def dependency_report(cinema_repo: Path) -> dict[str, Any]:
    modules = [
        "torch",
        "monai",
        "huggingface_hub",
        "safetensors",
        "omegaconf",
        "einops",
        "timm",
        "torchvision",
        "SimpleITK",
        "scipy",
    ]
    report: dict[str, Any] = {}
    for module in modules:
        report[module] = importlib.util.find_spec(module) is not None
    report["cinema_repo_exists"] = cinema_repo.is_dir()
    report["cinema_package_exists"] = (cinema_repo / "cinema").is_dir()
    return report


def discover_train_pairs(root: Path) -> list[tuple[str, str, Path, Path]]:
    pairs: list[tuple[str, str, Path, Path]] = []
    for cine_path in sorted(root.glob("*/*_Cine.nii.gz")):
        case_id = cine_path.name.replace("_Cine.nii.gz", "")
        label_path = cine_path.parent / f"{case_id}_gd.nii.gz"
        if label_path.is_file():
            pairs.append((cine_path.parent.name, case_id, cine_path, label_path))
    return pairs


def discover_val_images(root: Path) -> list[tuple[str, str, Path, None]]:
    return [(p.parent.name, p.name.replace("_Cine.nii.gz", ""), p, None) for p in sorted(root.glob("*/*_Cine.nii.gz"))]


def round_robin_limit(items: list[tuple[str, str, Path, Any]], max_items: int) -> list[tuple[str, str, Path, Any]]:
    if max_items <= 0 or len(items) <= max_items:
        return items
    buckets: dict[str, list[tuple[str, str, Path, Any]]] = {}
    for item in items:
        buckets.setdefault(item[0], []).append(item)
    selected: list[tuple[str, str, Path, Any]] = []
    while len(selected) < max_items and any(buckets.values()):
        for center in sorted(buckets):
            if buckets[center] and len(selected) < max_items:
                selected.append(buckets[center].pop(0))
    return selected


def extract_frame(image4d: sitk.Image, frame_index: int) -> sitk.Image:
    size = list(image4d.GetSize())
    extractor = sitk.ExtractImageFilter()
    extractor.SetSize([size[0], size[1], size[2], 0])
    extractor.SetIndex([0, 0, 0, int(frame_index)])
    return extractor.Execute(image4d)


def frame_indices(image4d: sitk.Image, strategy: str) -> list[int]:
    nt = image4d.GetSize()[3]
    base = [0, nt // 2]
    if strategy == "ed_middle_representative":
        arr = sitk.GetArrayFromImage(image4d).astype(np.float32)  # t,z,y,x
        flat = arr.reshape(nt, -1)
        mean_frame = flat.mean(axis=0, keepdims=True)
        representative = int(np.argmax(np.mean(np.abs(flat - mean_frame), axis=1)))
        base.append(representative)
    elif strategy == "all":
        base = list(range(nt))
    return sorted(set(max(0, min(nt - 1, int(v))) for v in base))


def resample_label_to_reference(label: sitk.Image, reference: sitk.Image) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(label)


def remap_care_label(label: sitk.Image, reference: sitk.Image) -> np.ndarray:
    label = resample_label_to_reference(label, reference)
    arr = sitk.GetArrayFromImage(label)
    compact = np.zeros_like(arr, dtype=np.uint8)
    for src, dst in CARE_RAW_TO_COMPACT.items():
        compact[arr == src] = dst
    return compact


def dice(pred: np.ndarray, gt: np.ndarray) -> float | None:
    pred_sum = int(pred.sum())
    gt_sum = int(gt.sum())
    if pred_sum == 0 and gt_sum == 0:
        return None
    denom = pred_sum + gt_sum
    if denom == 0:
        return 0.0
    return float(2.0 * np.logical_and(pred, gt).sum() / denom)


def hd95(pred: np.ndarray, gt: np.ndarray, spacing_zyx: tuple[float, float, float]) -> float | None:
    if not np.any(pred) or not np.any(gt):
        return None
    pred_border = np.logical_xor(pred, ndimage.binary_erosion(pred))
    gt_border = np.logical_xor(gt, ndimage.binary_erosion(gt))
    dt_gt = ndimage.distance_transform_edt(~gt_border, sampling=spacing_zyx)
    dt_pred = ndimage.distance_transform_edt(~pred_border, sampling=spacing_zyx)
    distances = np.concatenate([dt_gt[pred_border], dt_pred[gt_border]])
    return float(np.percentile(distances, 95)) if distances.size else 0.0


def component_count(mask: np.ndarray) -> int:
    if not np.any(mask):
        return 0
    _, n_components = ndimage.label(mask)
    return int(n_components)


def sitk_frame_to_cinema_array(frame: sitk.Image) -> tuple[np.ndarray, tuple[int, int, int]]:
    arr_zyx = sitk.GetArrayFromImage(frame).astype(np.float32)
    arr_xyz = np.transpose(arr_zyx, (2, 1, 0))
    return arr_xyz, arr_xyz.shape


def scale_intensity(image: np.ndarray) -> np.ndarray:
    min_value = float(np.min(image))
    max_value = float(np.max(image))
    if max_value <= min_value:
        return np.zeros_like(image, dtype=np.float32)
    return ((image - min_value) / (max_value - min_value)).astype(np.float32)


def crop_or_pad_to_shape(image: np.ndarray, target_shape: tuple[int, int, int]) -> tuple[np.ndarray, tuple[slice, ...], tuple[slice, ...]]:
    output = np.zeros(target_shape, dtype=image.dtype)
    src_slices = []
    dst_slices = []
    for src_len, dst_len in zip(image.shape, target_shape, strict=True):
        if src_len >= dst_len:
            src_start = (src_len - dst_len) // 2
            src_end = src_start + dst_len
            dst_start = 0
            dst_end = dst_len
        else:
            src_start = 0
            src_end = src_len
            dst_start = (dst_len - src_len) // 2
            dst_end = dst_start + src_len
        src_slices.append(slice(src_start, src_end))
        dst_slices.append(slice(dst_start, dst_end))
    src_tuple = tuple(src_slices)
    dst_tuple = tuple(dst_slices)
    output[dst_tuple] = image[src_tuple]
    return output, src_tuple, dst_tuple


def invert_crop_or_pad(
    prediction: np.ndarray,
    original_shape: tuple[int, int, int],
    src_slices: tuple[slice, ...],
    dst_slices: tuple[slice, ...],
) -> np.ndarray:
    output = np.zeros(original_shape, dtype=prediction.dtype)
    output[src_slices] = prediction[dst_slices]
    return output


def import_cinema(cinema_repo: Path):
    add_dependency_paths([cinema_repo])
    from cinema import ConvUNetR  # type: ignore

    return ConvUNetR


def run_model_on_frame(
    model: Any,
    frame: sitk.Image,
    device: Any,
    dtype: Any,
    spatial_size: tuple[int, int, int],
) -> np.ndarray:
    import torch

    image_xyz, original_shape = sitk_frame_to_cinema_array(frame)
    image_xyz = scale_intensity(image_xyz)
    fitted_xyz, src_slices, dst_slices = crop_or_pad_to_shape(image_xyz, spatial_size)
    batch = {"sax": torch.from_numpy(fitted_xyz[None, None]).to(device=device, dtype=torch.float32)}
    with torch.no_grad(), torch.autocast("cuda", dtype=dtype, enabled=False):
        logits = model(batch)["sax"]
    labels_fitted_xyz = torch.argmax(logits, dim=1)[0].detach().cpu().numpy().astype(np.uint8)
    labels_xyz = invert_crop_or_pad(labels_fitted_xyz, original_shape, src_slices, dst_slices)
    return np.transpose(labels_xyz, (2, 1, 0))


def write_prediction(pred_zyx: np.ndarray, reference: sitk.Image, path: Path) -> None:
    image = sitk.GetImageFromArray(pred_zyx.astype(np.uint8))
    image.CopyInformation(reference)
    sitk.WriteImage(image, str(path))


def load_model(cinema_repo: Path, trained_dataset: str, seed: int, device_name: str):
    import torch

    ConvUNetR = import_cinema(cinema_repo)
    device = torch.device(device_name)
    dtype = torch.bfloat16 if device.type == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
    model = ConvUNetR.from_finetuned(
        repo_id="mathpluscode/CineMA",
        model_filename=f"finetuned/segmentation/{trained_dataset}_sax/{trained_dataset}_sax_{seed}.safetensors",
        config_filename=f"finetuned/segmentation/{trained_dataset}_sax/config.yaml",
    )
    model.eval()
    model.to(device)
    return model, device, dtype


def evaluate_prediction(pred: np.ndarray, label: np.ndarray, frame: sitk.Image) -> dict[str, Any]:
    spacing = frame.GetSpacing()
    spacing_zyx = (float(spacing[2]), float(spacing[1]), float(spacing[0]))
    metrics: dict[str, Any] = {}
    class_pairs = {
        "myocardium": (2, 1),
        "lv": (3, 2),
        "rv_vs_unlabeled": (1, None),
    }
    for name, (pred_value, gt_value) in class_pairs.items():
        pred_mask = pred == pred_value
        metrics[f"{name}_pred_voxels"] = int(pred_mask.sum())
        metrics[f"{name}_pred_components"] = component_count(pred_mask)
        if gt_value is not None:
            gt_mask = label == gt_value
            metrics[f"{name}_gt_voxels"] = int(gt_mask.sum())
            metrics[f"{name}_dice"] = dice(pred_mask, gt_mask)
            metrics[f"{name}_hd95"] = hd95(pred_mask, gt_mask, spacing_zyx)
    return metrics


def case_manifest_row(split: str, center: str, case_id: str, cine_path: Path, label_path: Path | None) -> dict[str, Any]:
    image = sitk.ReadImage(str(cine_path))
    return {
        "split": split,
        "center": center,
        "case_id": case_id,
        "cine_path": str(cine_path),
        "label_path": str(label_path) if label_path else "",
        "size": list(image.GetSize()),
        "spacing": [round(float(v), 5) for v in image.GetSpacing()],
        "frames": int(image.GetSize()[3]) if image.GetDimension() == 4 else None,
    }


def write_rows_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    keys = sorted({k for row in rows for k in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=True) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [jsonable(v) for v in value]
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an isolated CineMA SAX anatomy adapter on CARE CineMyoPS raw 4D cine.")
    parser.add_argument("--train-root", type=Path, default=Path("data/CARE_Challenge/CineMyoPS_train"))
    parser.add_argument("--val-root", type=Path, default=Path("data/CARE_Challenge/CineMyoPS_val"))
    parser.add_argument("--cinema-repo", type=Path, default=Path("results/cinema_adapter/external/CineMA"))
    parser.add_argument("--extra-pythonpath", action="append", type=Path, default=[Path("results/cinema_adapter/python_deps")])
    parser.add_argument("--output-dir", type=Path, default=Path("results/cinema_adapter/manual_run"))
    parser.add_argument("--max-train-cases", type=int, default=20)
    parser.add_argument("--max-val-cases", type=int, default=15)
    parser.add_argument("--frame-strategy", choices=["ed_middle_representative", "all"], default="ed_middle_representative")
    parser.add_argument("--trained-dataset", choices=["acdc", "mnms", "mnms2"], default="acdc")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--spatial-size", default="192,192,16")
    parser.add_argument("--metadata-only", action="store_true", help="Only write manifest/dependency report; do not load weights.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.time()
    add_dependency_paths(args.extra_pythonpath)
    output_dir = args.output_dir.resolve()
    pred_dir = output_dir / "predictions"
    pred_dir.mkdir(parents=True, exist_ok=True)

    train_items = round_robin_limit(discover_train_pairs(args.train_root), args.max_train_cases)
    val_items = round_robin_limit(discover_val_images(args.val_root), args.max_val_cases)
    manifest = [case_manifest_row("train", *item) for item in train_items] + [
        case_manifest_row("val", *item) for item in val_items
    ]

    dep_report = dependency_report(args.cinema_repo)
    run_info: dict[str, Any] = {
        "args": jsonable(vars(args) | {"output_dir": output_dir, "cinema_repo": args.cinema_repo}),
        "dependency_report": dep_report,
        "cinema_label_semantics": CINEMA_LABELS,
        "care_raw_to_compact": CARE_RAW_TO_COMPACT,
        "selected_cases": {"train": len(train_items), "val": len(val_items)},
    }
    (output_dir / "run_info.json").write_text(json.dumps(run_info, indent=2, ensure_ascii=False), encoding="utf-8")
    write_rows_csv(manifest, output_dir / "manifest.csv")

    if args.metadata_only:
        print(json.dumps(run_info, indent=2, ensure_ascii=False))
        return 0
    missing = [name for name, ok in dep_report.items() if not ok]
    if missing:
        (output_dir / "failure.json").write_text(
            json.dumps({"reason": "missing_dependencies", "missing": missing, "dependency_report": dep_report}, indent=2),
            encoding="utf-8",
        )
        print(f"Missing dependencies: {missing}", file=sys.stderr)
        return 2

    spatial_size = tuple(int(v) for v in args.spatial_size.split(","))
    if len(spatial_size) != 3:
        raise ValueError("--spatial-size must contain three comma-separated integers")
    model, device, dtype = load_model(args.cinema_repo, args.trained_dataset, args.seed, args.device)

    rows: list[dict[str, Any]] = []
    for split, items in (("train", train_items), ("val", val_items)):
        for center, case_id, cine_path, label_path in items:
            image4d = sitk.ReadImage(str(cine_path))
            indices = frame_indices(image4d, args.frame_strategy)
            for frame_index in indices:
                frame = extract_frame(image4d, frame_index)
                pred = run_model_on_frame(model, frame, device, dtype, spatial_size)
                pred_path = pred_dir / split / center / f"{case_id}_t{frame_index:02d}_cinema_{args.trained_dataset}_s{args.seed}.nii.gz"
                pred_path.parent.mkdir(parents=True, exist_ok=True)
                write_prediction(pred, frame, pred_path)
                row: dict[str, Any] = {
                    "split": split,
                    "center": center,
                    "case_id": case_id,
                    "frame_index": frame_index,
                    "prediction_path": str(pred_path),
                    "pred_label_values": sorted(int(v) for v in np.unique(pred).tolist()),
                    "pred_label_counts": dict(Counter(int(v) for v in pred.ravel().tolist())),
                }
                if label_path:
                    label = remap_care_label(sitk.ReadImage(str(label_path)), frame)
                    row.update(evaluate_prediction(pred, label, frame))
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False))

    write_rows_csv(rows, output_dir / "metrics.csv")
    metrics_summary = {
        "elapsed_sec": round(time.time() - started, 3),
        "rows": len(rows),
        "train_cases": len(train_items),
        "val_cases": len(val_items),
        "frame_strategy": args.frame_strategy,
        "trained_dataset": args.trained_dataset,
        "seed": args.seed,
    }
    for metric in ("myocardium_dice", "lv_dice", "myocardium_hd95", "lv_hd95"):
        values = [float(r[metric]) for r in rows if r.get("split") == "train" and r.get(metric) is not None]
        if values:
            metrics_summary[f"{metric}_mean_train_frames"] = float(np.mean(values))
            metrics_summary[f"{metric}_median_train_frames"] = float(np.median(values))
    (output_dir / "metrics_summary.json").write_text(
        json.dumps(metrics_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metrics_summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    raise SystemExit(main())
