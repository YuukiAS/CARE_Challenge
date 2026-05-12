#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import SimpleITK as sitk

CARE_ROOT = Path(__file__).resolve().parents[2]
_CINE_DIR = Path(__file__).resolve().parent
for _p in (_CINE_DIR, CARE_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from task026_utils import DEFAULT_BENCHMARK_OUTPUT, log_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sanity check benchmark Task026_Cine_4D export.")
    parser.add_argument(
        "--task-root",
        type=Path,
        default=DEFAULT_BENCHMARK_OUTPUT,
        help="Benchmark Task026 directory containing dataset.json, imagesTr, and labelsTr.",
    )
    parser.add_argument(
        "--sample-cases",
        type=int,
        default=10,
        help="Number of deterministic cases used for morphology consistency checks.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for morphology sample selection.")
    return parser.parse_args()


def dice_score(lhs: np.ndarray, rhs: np.ndarray) -> float:
    lhs_sum = int(lhs.sum())
    rhs_sum = int(rhs.sum())
    if lhs_sum == 0 and rhs_sum == 0:
        return 1.0
    if lhs_sum == 0 or rhs_sum == 0:
        return 0.0
    intersection = int(np.logical_and(lhs, rhs).sum())
    return 2.0 * intersection / float(lhs_sum + rhs_sum)


def main() -> int:
    args = parse_args()
    task_root = args.task_root.resolve()
    dataset_json = task_root / "dataset.json"
    log_path("sanity task root", task_root)
    log_path("sanity dataset json", dataset_json)
    if not dataset_json.is_file():
        raise FileNotFoundError(f"Missing dataset.json: {dataset_json}")

    payload = json.loads(dataset_json.read_text(encoding="utf-8"))
    care_meta = payload.get("care")
    if care_meta is None:
        raise KeyError(f"Missing care metadata block in {dataset_json}")
    frame_indices_per_case = care_meta.get("frame_indices_per_case")
    expected_frames = int(care_meta.get("num_frames"))
    if frame_indices_per_case is None:
        raise KeyError(f"Missing care.frame_indices_per_case in {dataset_json}")
    if payload["labels"] != {
        "0": "background",
        "1": "myocardium",
        "2": "LV_blood",
        "3": "scar",
    }:
        raise ValueError(f"Unexpected label definition in {dataset_json}: {payload['labels']}")

    failures: list[str] = []
    training = payload["training"]
    for item in training:
        case_key = Path(item["label"]).name.replace(".nii.gz", "")
        image_path = task_root / item["image"].replace("./", "")
        label_path = task_root / item["label"].replace("./", "")
        if not image_path.is_file():
            raise FileNotFoundError(f"Missing image for {case_key}: {image_path}")
        if not label_path.is_file():
            raise FileNotFoundError(f"Missing label for {case_key}: {label_path}")

        image = sitk.ReadImage(str(image_path))
        label = sitk.ReadImage(str(label_path))
        if image.GetDimension() != 4:
            failures.append(f"{case_key}: expected 4D image, got {image.GetDimension()}D")
            continue
        if label.GetDimension() != 3:
            failures.append(f"{case_key}: expected 3D label, got {label.GetDimension()}D")
            continue
        if image.GetSize()[3] != expected_frames:
            failures.append(
                f"{case_key}: expected T={expected_frames}, got T={image.GetSize()[3]}"
            )
        if frame_indices_per_case.get(case_key, [None])[0] != 0:
            failures.append(f"{case_key}: frame_indices do not start with ED t=0")
        label_values = set(np.unique(sitk.GetArrayFromImage(label)).tolist())
        if not label_values.issubset({0, 1, 2, 3}):
            failures.append(f"{case_key}: unexpected compact labels {sorted(label_values)}")

    if failures:
        for line in failures:
            print(f"FAIL {line}")
        return 1

    rng = np.random.default_rng(args.seed)
    sampled_items = training if args.sample_cases <= 0 or args.sample_cases >= len(training) else [
        training[index] for index in sorted(rng.choice(len(training), size=args.sample_cases, replace=False).tolist())
    ]
    morph_failures: list[str] = []
    for item in sampled_items:
        case_key = Path(item["label"]).name.replace(".nii.gz", "")
        image = sitk.ReadImage(str((task_root / item["image"].replace("./", "")).resolve()))
        label = sitk.ReadImage(str((task_root / item["label"].replace("./", "")).resolve()))
        cine_array = sitk.GetArrayFromImage(image)
        label_mask = sitk.GetArrayFromImage(label) > 0
        ed_volume = cine_array[0]
        coords = np.where(label_mask)
        if len(coords[0]) == 0:
            morph_failures.append(f"{case_key}: empty foreground label")
            continue
        crop_mask = np.zeros_like(label_mask, dtype=bool)
        mins = [max(0, int(axis.min()) - 5) for axis in coords]
        maxs = [min(ed_volume.shape[idx], int(coords[idx].max()) + 6) for idx in range(3)]
        crop_mask[mins[0] : maxs[0], mins[1] : maxs[1], mins[2] : maxs[2]] = True
        threshold = float(np.median(ed_volume[crop_mask]))
        intensity_mask = np.logical_and(ed_volume > threshold, crop_mask)
        score = dice_score(label_mask, intensity_mask)
        print(f"sanity morphology: case={case_key} dice={score:.4f}")
        if score <= 0.3:
            morph_failures.append(f"{case_key}: morphology dice {score:.4f} <= 0.3")

    if morph_failures:
        for line in morph_failures:
            print(f"FAIL {line}")
        return 1

    print(
        f"sanity summary: checked {len(training)} cases for shape/labels and "
        f"{len(sampled_items)} cases for morphology"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
