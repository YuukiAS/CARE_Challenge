#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable
import sys

import numpy as np
import SimpleITK as sitk

CARE_ROOT = Path(__file__).resolve().parents[2]
if str(CARE_ROOT) not in sys.path:
    sys.path.insert(0, str(CARE_ROOT))

from scripts.nnUNet.nnunet_label_utils import remap_segmentation

DEFAULT_INPUT = CARE_ROOT / "data/CARE_Challenge/CineMyoPS_train"
DEFAULT_BENCHMARK_OUTPUT = CARE_ROOT / "data/benchmarks/CineMyoPS/Task026_Cine_4D"
DEFAULT_NNUNET_RAW_OUTPUT = CARE_ROOT / "data/nnUNet/nnUNet_raw/Task026_Cine_4D"
DEFAULT_VERIFY_CSV_NAME = "verify_ed_at_t0.csv"
COMPACT_LABEL_MAP = {0: 0, 1: 1, 2: 2, 5: 3}


def log_path(label: str, path: Path) -> None:
    print(f"{label}: {path.resolve()}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def discover_case_pairs(input_root: Path) -> list[tuple[str, str, Path, Path]]:
    pairs: list[tuple[str, str, Path, Path]] = []
    for cine_path in sorted(input_root.glob("*/*_Cine.nii.gz")):
        center = cine_path.parent.name
        case_id = cine_path.name.replace("_Cine.nii.gz", "")
        label_path = cine_path.parent / f"{case_id}_gd.nii.gz"
        if not label_path.is_file():
            raise FileNotFoundError(f"Missing label for {cine_path.resolve()}: {label_path.resolve()}")
        pairs.append((center, case_id, cine_path, label_path))
    if not pairs:
        raise FileNotFoundError(f"No cine cases found under {input_root.resolve()}")
    return pairs


def round_robin_limit(
    pairs: list[tuple[str, str, Path, Path]],
    max_cases: int,
) -> list[tuple[str, str, Path, Path]]:
    if max_cases <= 0 or max_cases >= len(pairs):
        return pairs
    grouped: dict[str, list[tuple[str, str, Path, Path]]] = defaultdict(list)
    for item in pairs:
        grouped[item[0]].append(item)
    selected: list[tuple[str, str, Path, Path]] = []
    while len(selected) < max_cases:
        progressed = False
        for center in sorted(grouped):
            if grouped[center] and len(selected) < max_cases:
                selected.append(grouped[center].pop(0))
                progressed = True
        if not progressed:
            break
    if len(selected) != max_cases:
        raise RuntimeError(
            f"Unable to select exactly {max_cases} cases from grouped centers; selected {len(selected)}"
        )
    return selected


def read_image_4d(path: Path) -> sitk.Image:
    image = sitk.ReadImage(str(path))
    if image.GetDimension() != 4:
        raise ValueError(f"Expected 4D cine at {path.resolve()}, got dimension {image.GetDimension()}")
    return image


def extract_frame(image_4d: sitk.Image, time_index: int) -> sitk.Image:
    size = list(image_4d.GetSize())
    if not 0 <= time_index < size[3]:
        raise ValueError(f"time_index={time_index} out of range for size={size}")
    extractor = sitk.ExtractImageFilter()
    extractor.SetSize([size[0], size[1], size[2], 0])
    extractor.SetIndex([0, 0, 0, time_index])
    return extractor.Execute(image_4d)


def sample_frame_indices(num_total_frames: int, num_sampled_frames: int) -> list[int]:
    if num_total_frames < 1:
        raise ValueError(f"Invalid total frame count: {num_total_frames}")
    if not 1 <= num_sampled_frames <= num_total_frames:
        raise ValueError(
            f"Requested num_sampled_frames={num_sampled_frames}, but cine only has {num_total_frames} frames"
        )
    targets = np.linspace(0.0, float(num_total_frames - 1), num=num_sampled_frames)
    indices: list[int] = []
    used: set[int] = set()
    for position, target in enumerate(targets):
        candidates = sorted(range(num_total_frames), key=lambda idx: (abs(idx - target), idx))
        chosen = next((idx for idx in candidates if idx not in used), None)
        if chosen is None:
            raise RuntimeError(
                f"Could not assign a unique sampled frame for target={target} with T={num_total_frames}"
            )
        indices.append(chosen)
        used.add(chosen)
        if position == 0 and chosen != 0:
            raise RuntimeError(f"Expected ED frame at t=0, but sampling chose {chosen}")
    if indices[0] != 0:
        raise RuntimeError(f"Sampled indices must start at ED frame t=0, got {indices}")
    if len(indices) != len(set(indices)):
        raise RuntimeError(f"Sampled indices are not unique: {indices}")
    return indices


def remap_label_to_compact(label_image: sitk.Image, reference_image: sitk.Image) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference_image)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    resampler.SetDefaultPixelValue(0)
    aligned = resampler.Execute(label_image)
    remapped = remap_segmentation(sitk.GetArrayFromImage(aligned))
    compact = np.zeros_like(remapped, dtype=np.uint8)
    for source_id, target_id in COMPACT_LABEL_MAP.items():
        compact[remapped == source_id] = target_id
    compact_image = sitk.GetImageFromArray(compact)
    compact_image.CopyInformation(aligned)
    return compact_image


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def sync_expected_files(directory: Path, expected_names: Iterable[str]) -> None:
    ensure_dir(directory)
    expected = set(expected_names)
    for existing in directory.glob("*.nii.gz"):
        if existing.name not in expected:
            existing.unlink()


def build_benchmark_dataset_json(
    training_entries: list[dict[str, str]],
    frame_indices_per_case: dict[str, list[int]],
    num_frames: int,
) -> dict:
    return {
        "name": "Task026_Cine_4D",
        "description": "CARE CineMyoPS cine sequence export with ED-first sampled frames",
        "tensorImageSize": "4D",
        "reference": "CARE",
        "licence": "",
        "release": "0.0",
        "modality": {"0": "Cine"},
        "labels": {
            "0": "background",
            "1": "myocardium",
            "2": "LV_blood",
            "3": "scar",
        },
        "numTraining": len(training_entries),
        "numTest": 0,
        "training": training_entries,
        "test": [],
        "care": {
            "num_frames": num_frames,
            "frame_layout": "ED-first(t=0)",
            "frame_indices_per_case": frame_indices_per_case,
        },
    }


def build_raw_dataset_json(
    training_entries: list[dict[str, str]],
    frame_indices_per_case: dict[str, list[int]],
    num_frames: int,
) -> dict:
    modality = {}
    for idx in range(num_frames):
        modality[str(idx)] = "Cine_ED" if idx == 0 else f"Cine_frame_{idx:02d}"
    return {
        "name": "Task026_Cine_4D",
        "description": "CARE CineMyoPS split-channel raw task for nnU-Net v1",
        "tensorImageSize": "3D",
        "reference": "CARE",
        "licence": "",
        "release": "0.0",
        "modality": modality,
        "labels": {
            "0": "background",
            "1": "myocardium",
            "2": "LV_blood",
            "3": "scar",
        },
        "numTraining": len(training_entries),
        "numTest": 0,
        "training": training_entries,
        "test": [],
        "care": {
            "num_frames": num_frames,
            "frame_layout": "ED-first(t=0)",
            "frame_indices_per_case": frame_indices_per_case,
            "source_benchmark_task": str(DEFAULT_BENCHMARK_OUTPUT.resolve()),
        },
    }
