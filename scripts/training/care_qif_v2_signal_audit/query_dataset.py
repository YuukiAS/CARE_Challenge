#!/usr/bin/env python3
"""Dataset and deterministic split helpers for the CARE-QIF v2 query pilot."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.forensics.care_qif_v2_signal_audit.common import (  # noqa: E402
    RESULT_ROOT,
    SEED,
    deterministic_center_selection,
    feature_cache_path,
    load_image,
    load_seg,
    read_csv,
    spacing_zyx,
)
from scripts.forensics.care_qif_v2_signal_audit.intensity_features import local_contrast, percentile_rank  # noqa: E402


_INTENSITY_CACHE: dict[str, np.ndarray] = {}


def read_manifest() -> list[dict[str, str]]:
    return read_csv(RESULT_ROOT / "oof_backbone_manifest.csv")


def split_for_direction(direction: str) -> dict[str, list[str]]:
    rows = read_manifest()
    stats = {
        r["case_id"]: {
            "scar_voxels": int(r["scar_voxels"]),
            "scar_component_count": int(r["scar_component_count"]),
        }
        for r in rows
    }
    center_b = sorted(r["case_id"] for r in rows if r["center"] == "CenterB")
    center_c = sorted(r["case_id"] for r in rows if r["center"] == "CenterC")
    if direction == "BC":
        train, selection = deterministic_center_selection(center_b, stats)
        return {"train": train, "selection": selection, "test": center_c}
    if direction == "CB":
        train, selection = deterministic_center_selection(center_c, stats)
        return {"train": train, "selection": selection, "test": center_b}
    raise ValueError(f"unknown direction {direction}")


def descriptor_seed(direction: str, optimizer_step: int, accumulation_index: int) -> int:
    text = f"qif-v2:{SEED}:{direction}:{optimizer_step}:{accumulation_index}"
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def build_batch_descriptors(direction: str, steps: int = 4000, accumulation: int = 4) -> list[dict[str, Any]]:
    split = split_for_direction(direction)
    train_cases = split["train"]
    out: list[dict[str, Any]] = []
    for step in range(1, steps + 1):
        for acc in range(accumulation):
            seed = descriptor_seed(direction, step, acc)
            case = train_cases[seed % len(train_cases)]
            out.append(
                {
                    "direction": direction,
                    "optimizer_step": step,
                    "accumulation_index": acc,
                    "case_id": case,
                    "flip_y": False,
                    "flip_x": False,
                    "roll_z": 0,
                    "roll_y": 0,
                    "roll_x": 0,
                    "seed": seed,
                }
            )
    return out


def write_batch_manifest(path: Path, descriptors: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    with path.open("w", encoding="utf-8") as f:
        for row in descriptors:
            line = json.dumps(row, sort_keys=True, separators=(",", ":"))
            h.update(line.encode("utf-8"))
            h.update(b"\n")
            f.write(line + "\n")
    return h.hexdigest()


def apply_descriptor(t: torch.Tensor, desc: dict[str, Any]) -> torch.Tensor:
    if desc.get("flip_y"):
        t = torch.flip(t, dims=(-2,))
    if desc.get("flip_x"):
        t = torch.flip(t, dims=(-1,))
    shifts = (int(desc.get("roll_z", 0)), int(desc.get("roll_y", 0)), int(desc.get("roll_x", 0)))
    if any(shifts):
        t = torch.roll(t, shifts=shifts, dims=(-3, -2, -1))
    return t


def intensity_channels(case_id: str) -> np.ndarray:
    if case_id in _INTENSITY_CACHE:
        return _INTENSITY_CACHE[case_id]
    image = load_image(case_id)
    seg = load_seg(case_id)
    support = np.isin(seg, [1, 4, 5])
    rank = percentile_rank(image[0].astype(np.float32), support)
    contrast = local_contrast(image[0].astype(np.float32), spacing_zyx(case_id), 3.0)
    out = np.stack([rank, contrast], axis=0).astype(np.float32)
    _INTENSITY_CACHE[case_id] = out
    return out


class CrossCenterScarDataset:
    def __init__(self, case_ids: list[str], *, training: bool = False) -> None:
        self.case_ids = list(case_ids)
        self.training = bool(training)
        self._case_cache: dict[str, dict[str, torch.Tensor]] = {}
        if not self.case_ids:
            raise ValueError("empty case list")

    def __len__(self) -> int:
        return len(self.case_ids)

    def load_case(self, case_id: str, descriptor: dict[str, Any] | None = None, device: torch.device | None = None) -> dict[str, torch.Tensor]:
        path = feature_cache_path(case_id)
        if not path.exists():
            raise FileNotFoundError(f"feature cache missing for {case_id}: {path}")
        if case_id not in self._case_cache:
            data = np.load(path)
            seg = load_seg(case_id)
            self._case_cache[case_id] = {
                "f0": torch.from_numpy(data["f0"].astype(np.float32, copy=False)).unsqueeze(0),
                "f1": torch.from_numpy(data["f1"].astype(np.float32, copy=False)).unsqueeze(0),
                "p_myo": torch.from_numpy(data["p_myo"].astype(np.float32, copy=False)).unsqueeze(0).unsqueeze(0),
                "p_lv": torch.from_numpy(data["p_lv"].astype(np.float32, copy=False)).unsqueeze(0).unsqueeze(0),
                "intensity_channels": torch.from_numpy(intensity_channels(case_id)).unsqueeze(0),
                "scar_target": torch.from_numpy((seg == 5).astype(np.float32)).unsqueeze(0).unsqueeze(0),
                "myocardium_union": torch.from_numpy(np.isin(seg, [1, 4, 5]).astype(np.float32)).unsqueeze(0).unsqueeze(0),
                "lv_mask": torch.from_numpy((seg == 2).astype(np.float32)).unsqueeze(0).unsqueeze(0),
            }
        batch = {key: value for key, value in self._case_cache[case_id].items()}
        if descriptor is not None:
            for key in list(batch):
                if key not in {"f1"}:
                    batch[key] = apply_descriptor(batch[key], descriptor)
        if device is not None:
            batch = {key: value.to(device) for key, value in batch.items()}
        batch["case_id"] = case_id  # type: ignore[assignment]
        return batch

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        return self.load_case(self.case_ids[int(index) % len(self.case_ids)])


def infer_feature_channels(case_id: str) -> tuple[int, int]:
    path = feature_cache_path(case_id)
    if not path.exists():
        raise FileNotFoundError(path)
    data = np.load(path)
    return int(data["f0"].shape[0]), int(data["f1"].shape[0])
