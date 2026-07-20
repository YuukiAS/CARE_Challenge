"""Shared runtime helpers for Route B Round03 executors."""

from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_CARE_ROOT = Path("/users/a/e/aereinh/CARE")
RESULT_ROOT = REPO_ROOT / "results" / "route_B"
ROUND_ROOT = RESULT_ROOT / "round03"
ANCHOR_ROOT = (
    MAIN_CARE_ROOT
    / "results/20260704_myops_anchor_srr_fold0_formal/variants/srr_propref_shared_dual_dict"
    / "predictions/fold_0/checkpoint_best/pathology_aware"
)

MYOPS_LABEL_MAP = {0: 0, 200: 1, 500: 2, 600: 3, 1220: 4, 2221: 5}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def monotonic() -> float:
    return time.monotonic()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_nifti(path: str | Path) -> np.ndarray:
    return np.asarray(nib.load(str(path)).dataobj)


def to_dhw(array: np.ndarray) -> torch.Tensor:
    if array.ndim == 4:
        array = array[..., 0]
    if array.ndim != 3:
        raise ValueError(f"expected 3D image, got shape {array.shape}")
    return torch.from_numpy(np.ascontiguousarray(array.transpose(2, 0, 1))).float()


def normalize_image(tensor: torch.Tensor) -> torch.Tensor:
    mask = torch.isfinite(tensor)
    values = tensor[mask]
    if values.numel() == 0:
        return torch.zeros_like(tensor)
    lo = torch.quantile(values, 0.01)
    hi = torch.quantile(values, 0.99)
    tensor = tensor.clamp(float(lo), float(hi))
    mean = tensor[mask].mean()
    std = tensor[mask].std().clamp_min(1.0e-6)
    return (tensor - mean) / std


def compact_myops_label(path: str | Path) -> torch.Tensor:
    raw = to_dhw(load_nifti(path)).long()
    out = torch.zeros_like(raw)
    for raw_value, compact in MYOPS_LABEL_MAP.items():
        out[raw == raw_value] = int(compact)
    return out


def crop_bounds(shape: tuple[int, int, int], size: tuple[int, int, int], seed: int) -> tuple[slice, slice, slice]:
    starts: list[int] = []
    for dim, want in zip(shape, size, strict=True):
        if dim <= want:
            starts.append(0)
        else:
            starts.append(int((seed * 1103515245 + dim * 12345) % (dim - want + 1)))
    return tuple(slice(start, min(start + want, dim)) for start, dim, want in zip(starts, shape, size, strict=True))  # type: ignore[return-value]


def pad_to(tensor: torch.Tensor, size: tuple[int, int, int], value: float = 0.0) -> torch.Tensor:
    pads: list[int] = []
    for dim, want in zip(reversed(tensor.shape[-3:]), reversed(size), strict=True):
        extra = max(0, want - dim)
        pads.extend([0, extra])
    if any(pads):
        tensor = F.pad(tensor, pads, value=value)
    return tensor[..., : size[0], : size[1], : size[2]]


def label_logits(label: torch.Tensor, channels: int, confidence: float = 3.0) -> torch.Tensor:
    one_hot = F.one_hot(label.clamp(0, channels - 1), channels).permute(3, 0, 1, 2).float()
    return confidence * (2.0 * one_hot - 1.0)


class MyoPSPatchCache:
    def __init__(self, manifest_path: Path, patch_size: tuple[int, int, int] = (16, 32, 32)) -> None:
        self.rows = read_json(manifest_path)["cases"]
        self.patch_size = patch_size
        self._cache: dict[str, tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]] = {}
        self._case_index = {str(row["case_id"]): idx for idx, row in enumerate(self.rows)}

    def __len__(self) -> int:
        return len(self.rows)

    def row(self, index: int) -> dict[str, Any]:
        return self.rows[index % len(self.rows)]

    def get(self, index: int, seed: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, str]:
        row = self.row(index)
        case_id = row["case_id"]
        cache_key = f"{case_id}:{seed % 17}"
        if cache_key in self._cache:
            x, avail, label, anchor = self._cache[cache_key]
            return x.clone(), avail.clone(), label.clone(), anchor.clone(), case_id
        label_full = compact_myops_label(row["label_path"])
        shape = tuple(int(v) for v in label_full.shape)
        slices = crop_bounds(shape, self.patch_size, seed)
        images = []
        availability = []
        for mod in ("LGE", "T2", "C0"):
            path = row["image_paths"].get(mod)
            if path:
                image = normalize_image(to_dhw(load_nifti(path)))[slices]
                availability.append(1.0)
            else:
                image = torch.zeros_like(label_full, dtype=torch.float32)[slices]
                availability.append(0.0)
            images.append(pad_to(image, self.patch_size))
        label = pad_to(label_full[slices], self.patch_size).long()
        anchor_path = ANCHOR_ROOT / f"{case_id}.nii.gz"
        if anchor_path.is_file():
            anchor_label = compact_myops_label(anchor_path)[slices]
            anchor = label_logits(pad_to(anchor_label, self.patch_size).long(), 6)
        else:
            anchor = torch.zeros(6, *self.patch_size)
        x = torch.stack(images, dim=0)
        avail = torch.tensor(availability, dtype=torch.float32)
        self._cache[cache_key] = (x, avail, label, anchor)
        return x.clone(), avail.clone(), label.clone(), anchor.clone(), case_id

    def get_case(self, case_id: str, seed: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, str]:
        if case_id not in self._case_index:
            raise KeyError(f"case {case_id} is absent from the frozen MyoPS manifest")
        return self.get(self._case_index[case_id], seed=seed)


class FrozenMyoPSSampler:
    """Frozen Route B Round03 sampler: E,E,S,R with Philox replacement draws."""

    def __init__(self, strata_path: Path) -> None:
        payload = read_json(strata_path)
        self.strata_path = strata_path
        self.draw_cycle = tuple(str(v) for v in payload.get("draw_cycle", []))
        self.seed = int(payload.get("philox_seed", 26071821))
        self.strata = {
            key: tuple(str(case_id) for case_id in payload.get("strata", {}).get(key, []))
            for key in ("E", "S", "R")
        }
        if self.draw_cycle != ("E", "E", "S", "R"):
            raise ValueError(f"Route B B3 sampler draw_cycle must be E,E,S,R, got {self.draw_cycle}")
        for key in self.draw_cycle:
            if not self.strata.get(key):
                raise ValueError(f"Route B B3 sampler stratum {key} is empty")
        self._rng = np.random.Generator(np.random.Philox(self.seed))

    def draw(self, step: int) -> tuple[str, str, int]:
        expected = self.draw_cycle[(step - 1) % len(self.draw_cycle)]
        cases = self.strata[expected]
        index = int(self._rng.integers(0, len(cases), endpoint=False))
        return expected, cases[index], index


def expected_frozen_sampler_counts(steps: int) -> dict[str, int]:
    full, rem = divmod(int(steps), 4)
    counts = {"E": full * 2, "S": full, "R": full}
    if rem >= 1:
        counts["E"] += 1
    if rem >= 2:
        counts["E"] += 1
    if rem >= 3:
        counts["S"] += 1
    return counts


def dice(pred: torch.Tensor, target: torch.Tensor, label: int) -> float:
    p = pred == label
    t = target == label
    denom = int(p.sum().item() + t.sum().item())
    if denom == 0:
        return 0.0
    return float((2.0 * (p & t).sum().item()) / denom)
