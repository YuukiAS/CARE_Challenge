#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy import ndimage


DEFAULT_TRAIN_ROOT = Path("data/CARE_Challenge/CineMyoPS_train")
DEFAULT_VAL_ROOT = Path("data/CARE_Challenge/CineMyoPS_val")
DEFAULT_DATASET502 = Path("data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS")
DEFAULT_OUTPUT = Path("results/diagnostics/cinemyops_raw_structure_audit_20260620")


def rounded_tuple(values: tuple[float, ...], digits: int = 4) -> tuple[float, ...]:
    return tuple(round(float(v), digits) for v in values)


def direction_hash(direction: tuple[float, ...]) -> str:
    payload = ",".join(f"{float(v):.8f}" for v in direction)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def read_meta(path: Path) -> dict[str, Any]:
    image = sitk.ReadImage(str(path))
    return {
        "dimension": image.GetDimension(),
        "size": tuple(int(v) for v in image.GetSize()),
        "spacing": rounded_tuple(image.GetSpacing()),
        "origin": rounded_tuple(image.GetOrigin()),
        "direction_hash": direction_hash(image.GetDirection()),
        "direction": rounded_tuple(image.GetDirection(), digits=6),
    }


def unique_values_and_counts(path: Path) -> tuple[list[int], dict[int, int]]:
    arr = sitk.GetArrayFromImage(sitk.ReadImage(str(path)))
    values, counts = np.unique(arr, return_counts=True)
    values_i = [int(v) for v in values.tolist()]
    return values_i, {int(v): int(c) for v, c in zip(values.tolist(), counts.tolist(), strict=True)}


def component_count(path: Path, value: int) -> int:
    arr = sitk.GetArrayFromImage(sitk.ReadImage(str(path)))
    mask = arr == value
    if not np.any(mask):
        return 0
    _, n_components = ndimage.label(mask)
    return int(n_components)


def discover_train_pairs(root: Path) -> list[tuple[str, str, Path, Path]]:
    pairs: list[tuple[str, str, Path, Path]] = []
    for cine_path in sorted(root.glob("*/*_Cine.nii.gz")):
        case_id = cine_path.name.replace("_Cine.nii.gz", "")
        label_path = cine_path.parent / f"{case_id}_gd.nii.gz"
        if label_path.is_file():
            pairs.append((cine_path.parent.name, case_id, cine_path, label_path))
    return pairs


def discover_val_images(root: Path) -> list[tuple[str, str, Path]]:
    images: list[tuple[str, str, Path]] = []
    for cine_path in sorted(root.glob("*/*_Cine.nii.gz")):
        case_id = cine_path.name.replace("_Cine.nii.gz", "")
        images.append((cine_path.parent.name, case_id, cine_path))
    return images


def audit_train_case(center: str, case_id: str, cine_path: Path, label_path: Path) -> dict[str, Any]:
    cine = read_meta(cine_path)
    label = read_meta(label_path)
    label_values, label_counts = unique_values_and_counts(label_path)
    cine_size = cine["size"]
    label_size = label["size"]
    label_matches_frame = label["dimension"] == 3 and tuple(label_size) == tuple(cine_size[:3])
    return {
        "split": "train",
        "center": center,
        "case_id": case_id,
        "cine_path": str(cine_path),
        "label_path": str(label_path),
        "cine_dimension": cine["dimension"],
        "cine_size": list(cine_size),
        "cine_spacing": list(cine["spacing"]),
        "cine_direction_hash": cine["direction_hash"],
        "frame_count": int(cine_size[3]) if len(cine_size) == 4 else None,
        "label_dimension": label["dimension"],
        "label_size": list(label_size),
        "label_spacing": list(label["spacing"]),
        "label_direction_hash": label["direction_hash"],
        "label_matches_single_3d_frame_geometry": bool(label_matches_frame),
        "label_values": label_values,
        "label_counts": label_counts,
        "components_200": component_count(label_path, 200),
        "components_500": component_count(label_path, 500),
        "components_2221": component_count(label_path, 2221),
    }


def audit_val_case(center: str, case_id: str, cine_path: Path) -> dict[str, Any]:
    cine = read_meta(cine_path)
    cine_size = cine["size"]
    return {
        "split": "val",
        "center": center,
        "case_id": case_id,
        "cine_path": str(cine_path),
        "cine_dimension": cine["dimension"],
        "cine_size": list(cine_size),
        "cine_spacing": list(cine["spacing"]),
        "cine_direction_hash": cine["direction_hash"],
        "frame_count": int(cine_size[3]) if len(cine_size) == 4 else None,
    }


def audit_dataset502(dataset_root: Path) -> dict[str, Any]:
    image_files = sorted((dataset_root / "imagesTr").glob("*.nii.gz"))
    label_files = sorted((dataset_root / "labelsTr").glob("*.nii.gz"))
    image_shapes = Counter()
    label_values = Counter()
    for path in image_files:
        image_shapes[str(read_meta(path)["size"])] += 1
    for path in label_files:
        values, _ = unique_values_and_counts(path)
        label_values[",".join(map(str, values))] += 1
    dataset_json = dataset_root / "dataset.json"
    dataset_meta = json.loads(dataset_json.read_text(encoding="utf-8")) if dataset_json.is_file() else {}
    return {
        "dataset_root": str(dataset_root),
        "dataset_json_exists": dataset_json.is_file(),
        "num_imagesTr": len(image_files),
        "num_labelsTr": len(label_files),
        "image_size_counts": dict(image_shapes),
        "label_value_set_counts": dict(label_values),
        "dataset_json": dataset_meta,
    }


def summarize(rows: list[dict[str, Any]], dataset502: dict[str, Any]) -> dict[str, Any]:
    train = [r for r in rows if r["split"] == "train"]
    val = [r for r in rows if r["split"] == "val"]
    train_label_values = defaultdict(int)
    for row in train:
        for value in row["label_values"]:
            train_label_values[int(value)] += 1
    return {
        "train_cases": len(train),
        "val_cases": len(val),
        "train_centers": dict(Counter(r["center"] for r in train)),
        "val_centers": dict(Counter(r["center"] for r in val)),
        "train_frame_counts": dict(Counter(r["frame_count"] for r in train)),
        "val_frame_counts": dict(Counter(r["frame_count"] for r in val)),
        "train_size_counts_top10": dict(Counter(str(r["cine_size"]) for r in train).most_common(10)),
        "val_size_counts_top10": dict(Counter(str(r["cine_size"]) for r in val).most_common(10)),
        "train_spacing_counts_top10": dict(Counter(str(r["cine_spacing"]) for r in train).most_common(10)),
        "val_spacing_counts_top10": dict(Counter(str(r["cine_spacing"]) for r in val).most_common(10)),
        "train_direction_unique": len({r["cine_direction_hash"] for r in train}),
        "val_direction_unique": len({r["cine_direction_hash"] for r in val}),
        "train_label_values_case_presence": dict(sorted(train_label_values.items())),
        "train_label_matches_single_3d_frame_geometry": dict(
            Counter(r["label_matches_single_3d_frame_geometry"] for r in train)
        ),
        "dataset502": dataset502,
    }


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = sorted({k for row in rows for k in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=True) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# CineMyoPS Raw Structure Audit",
        "",
        "## Summary",
        "",
        f"- train cases: {summary['train_cases']}",
        f"- validation cases: {summary['val_cases']}",
        f"- train frame counts: `{summary['train_frame_counts']}`",
        f"- validation frame counts: `{summary['val_frame_counts']}`",
        f"- train unique direction hashes: {summary['train_direction_unique']}",
        f"- validation unique direction hashes: {summary['val_direction_unique']}",
        f"- train label values by case presence: `{summary['train_label_values_case_presence']}`",
        f"- train labels match one 3D cine frame geometry: `{summary['train_label_matches_single_3d_frame_geometry']}`",
        "",
        "## Dataset502 Existing nnU-Net Raw",
        "",
        f"- imagesTr: {summary['dataset502']['num_imagesTr']}",
        f"- labelsTr: {summary['dataset502']['num_labelsTr']}",
        f"- dataset.json exists: {summary['dataset502']['dataset_json_exists']}",
        f"- dataset description: `{summary['dataset502'].get('dataset_json', {}).get('description', '')}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit CARE CineMyoPS raw 4D geometry and Dataset502 single-frame raw.")
    parser.add_argument("--train-root", type=Path, default=DEFAULT_TRAIN_ROOT)
    parser.add_argument("--val-root", type=Path, default=DEFAULT_VAL_ROOT)
    parser.add_argument("--dataset502-root", type=Path, default=DEFAULT_DATASET502)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for center, case_id, cine_path, label_path in discover_train_pairs(args.train_root):
        rows.append(audit_train_case(center, case_id, cine_path, label_path))
    for center, case_id, cine_path in discover_val_images(args.val_root):
        rows.append(audit_val_case(center, case_id, cine_path))

    dataset502 = audit_dataset502(args.dataset502_root)
    summary = summarize(rows, dataset502)

    write_csv(rows, output_dir / "cases.csv")
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(summary, output_dir / "summary.md")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
