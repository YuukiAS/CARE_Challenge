"""CARE-PRISM dataset helpers.

Synthetic fixtures are kept for known-bad/unit tests only. The formal dataset
loads full Dataset501 nnU-Net-preprocessed patients, preserves the native
``[LGE, T2, C0]`` channel order, applies split guards, and builds the pathology,
anatomy, burden, and safe-negative targets required by PRISM W1/W2.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
from typing import Any

import blosc2
import numpy as np
import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PREPROCESSED_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
DEFAULT_FULLRES_ROOT = DEFAULT_PREPROCESSED_ROOT / "nnUNetPlans_3d_fullres"
DEFAULT_SPLITS = DEFAULT_PREPROCESSED_ROOT / "splits_final.json"
DEFAULT_CENTER_METADATA_ROOT = REPO_ROOT / "data/benchmarks/U-MyoPS/gen_ZS_unaligned/data"
MODALITY_ORDER = ("LGE", "T2", "C0")
OUTER_LOCK_PATH = REPO_ROOT / "results/20260729_care_prism_v2_backbone_repair_and_resume/fold0_outer_once_lock.json"


@dataclass(frozen=True)
class CAREPRISMSyntheticCase:
    case_id: str
    images: torch.Tensor
    availability: torch.Tensor
    scar_target: torch.Tensor
    edema_zone_target: torch.Tensor
    anatomy_target: torch.Tensor
    t2_present: torch.Tensor


@dataclass(frozen=True)
class CAREPRISMPatientRecord:
    case_id: str
    image_path: Path
    seg_path: Path
    fold: int
    split: str
    center: str


class CAREPRISMAugmenter:
    """Deterministic, stateful full-patient augmentation.

    The spatial transform is shared across available modalities and labels.
    Intensity jitter is modality-specific. This class stores Python and NumPy
    RNG state so checkpoint/resume can reproduce the next augmented case.
    """

    def __init__(self, seed: int = 20260729, *, training: bool = True) -> None:
        self.training = bool(training)
        self._py = random.Random(seed)
        self._np = np.random.default_rng(seed)

    def state_dict(self) -> dict[str, Any]:
        return {
            "training": self.training,
            "python_random_state": self._py.getstate(),
            "numpy_bit_generator_state": self._np.bit_generator.state,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.training = bool(state.get("training", self.training))
        if "python_random_state" in state:
            self._py.setstate(state["python_random_state"])
        if "numpy_bit_generator_state" in state:
            self._np.bit_generator.state = state["numpy_bit_generator_state"]

    def __call__(self, images: torch.Tensor, seg: torch.Tensor, availability: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if not self.training:
            return images, seg, availability
        for dim in (-1, -2):
            if self._py.random() < 0.5:
                images = torch.flip(images, dims=(dim,))
                seg = torch.flip(seg, dims=(dim,))
        if self._py.random() < 0.25:
            shifts = (0, int(self._np.integers(-3, 4)), int(self._np.integers(-3, 4)))
            images = torch.roll(images, shifts=shifts, dims=(-3, -2, -1))
            seg = torch.roll(seg, shifts=shifts, dims=(-3, -2, -1))
        for channel in range(images.shape[0]):
            if float(availability[channel]) <= 0.0:
                continue
            gamma = float(self._np.uniform(0.7, 1.5))
            contrast = float(self._np.uniform(0.85, 1.15))
            noise = float(self._np.uniform(0.0, 0.03))
            x = images[channel]
            lo, hi = torch.quantile(x, torch.tensor([0.01, 0.99], device=x.device))
            x01 = ((x - lo) / (hi - lo).clamp_min(1.0e-6)).clamp(0, 1)
            x = torch.pow(x01, gamma) * contrast
            if noise > 0:
                noise_arr = self._np.normal(0.0, noise, size=tuple(x.shape)).astype(np.float32)
                x = x + torch.from_numpy(noise_arr).to(device=x.device, dtype=x.dtype)
            images[channel] = x
        if availability.sum() == 3 and self._py.random() < 0.10:
            images[1].zero_()
            availability[1] = 0.0
        if availability.sum() == 3 and self._py.random() < 0.20:
            images[2].zero_()
            availability[2] = 0.0
        return images, seg, availability


def _center_from_case(case_id: str, metadata_root: Path = DEFAULT_CENTER_METADATA_ROOT) -> str:
    matches = sorted(Path(metadata_root).glob(f"Center*_{case_id}/subject_meta.json"))
    if matches:
        meta = json.loads(matches[0].read_text(encoding="utf-8"))
        return str(meta["center"])
    raise FileNotFoundError(f"canonical center metadata not found for {case_id} under {metadata_root}")


def deterministic_case_partitions(train_cases: list[str], *, fold: int, inner_fraction: float = 0.20) -> dict[str, list[str]]:
    keyed = sorted((hashlib.sha256(f"care-prism-inner-v1:{fold}:{case_id}".encode("utf-8")).hexdigest(), case_id) for case_id in train_cases)
    inner_n = max(1, int(round(len(keyed) * inner_fraction)))
    inner = sorted(case for _key, case in keyed[:inner_n])
    actual = sorted(case for _key, case in keyed[inner_n:])
    return {"actual_train": actual, "inner_select": inner}


def _load_b2nd(path: Path) -> torch.Tensor:
    return torch.from_numpy(np.asarray(blosc2.open(str(path), mode="r")[:]))


def _burden_class(pathology: torch.Tensor, union: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    ratio = pathology.sum().float() / union.sum().float().clamp_min(1.0)
    if float(pathology.sum()) <= 0:
        klass = 0
    elif float(ratio) < 0.01:
        klass = 1
    elif float(ratio) < 0.05:
        klass = 2
    else:
        klass = 3
    return torch.tensor(klass, dtype=torch.long), torch.log1p(ratio).view(1)


def safe_negative_targets(images: torch.Tensor, seg: torch.Tensor, *, pathology: str, t2_present: bool) -> torch.Tensor:
    union = (seg == 1) | (seg == 4) | (seg == 5)
    normal_myocardium = seg == 1
    blood = (seg == 2) | (seg == 3)
    outside_union = ~union
    if pathology == "edema" and not t2_present:
        return torch.zeros(4, *seg.shape[-3:], dtype=torch.float32)
    channel = 1 if pathology == "edema" else 0
    x = images[channel]
    outside_vals = x[outside_union]
    if outside_vals.numel() > 0:
        threshold = torch.quantile(outside_vals.float(), 0.95)
        artifact = outside_union & (x >= threshold)
    else:
        artifact = torch.zeros_like(outside_union)
    return torch.stack([normal_myocardium, blood, outside_union, artifact]).float()


class CAREPRISMFullPatientDataset(torch.utils.data.Dataset[dict[str, Any]]):
    def __init__(
        self,
        *,
        fold: int = 0,
        split: str = "train",
        preprocessed_root: Path = DEFAULT_PREPROCESSED_ROOT,
        fullres_root: Path = DEFAULT_FULLRES_ROOT,
        splits_path: Path = DEFAULT_SPLITS,
        center_metadata_root: Path = DEFAULT_CENTER_METADATA_ROOT,
        augmenter: CAREPRISMAugmenter | None = None,
        outer_access_lock: Path | None = None,
    ) -> None:
        self.fold = int(fold)
        self.split = str(split)
        splits = json.loads(Path(splits_path).read_text(encoding="utf-8"))
        if self.fold < 0 or self.fold >= len(splits):
            raise ValueError(f"fold {self.fold} not available in {splits_path}")
        fold_split = splits[self.fold]
        partitioned = deterministic_case_partitions(list(fold_split["train"]), fold=self.fold)
        split_cases = {
            "train": list(fold_split["train"]),
            "actual_train": partitioned["actual_train"],
            "inner_select": partitioned["inner_select"],
            "val": list(fold_split["val"]),
            "outer": list(fold_split["val"]),
        }
        if self.split not in split_cases:
            raise ValueError(f"split {self.split!r} not available for fold {self.fold}")
        if self.split == "outer":
            lock = Path(outer_access_lock or OUTER_LOCK_PATH)
            if not lock.exists():
                raise PermissionError(f"outer split access requires one-time lock receipt: {lock}")
        overlap = set(partitioned["actual_train"]) & set(partitioned["inner_select"])
        if overlap:
            raise ValueError(f"split guard failed; actual_train and inner_select overlap: {sorted(overlap)[:5]}")
        if set(fold_split["train"]) & set(fold_split["val"]):
            raise ValueError("split guard failed; train and val/outer overlap")
        self.records = [
            CAREPRISMPatientRecord(
                case_id=case_id,
                image_path=Path(fullres_root) / f"{case_id}.b2nd",
                seg_path=Path(fullres_root) / f"{case_id}_seg.b2nd",
                fold=self.fold,
                split=self.split,
                center=_center_from_case(case_id, center_metadata_root),
            )
            for case_id in split_cases[self.split]
        ]
        missing = [r.case_id for r in self.records if not r.image_path.exists() or not r.seg_path.exists()]
        if missing:
            raise FileNotFoundError(f"missing preprocessed arrays for cases: {missing[:5]}")
        self.preprocessed_root = Path(preprocessed_root)
        self.augmenter = augmenter
        self.cursor = 0

    def __len__(self) -> int:
        return len(self.records)

    def state_dict(self) -> dict[str, Any]:
        return {
            "fold": self.fold,
            "split": self.split,
            "cursor": self.cursor,
            "augmenter": self.augmenter.state_dict() if self.augmenter is not None else None,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.cursor = int(state.get("cursor", self.cursor))
        if self.augmenter is not None and state.get("augmenter") is not None:
            self.augmenter.load_state_dict(state["augmenter"])

    def sample_next(self) -> dict[str, Any]:
        item = self[self.cursor % len(self.records)]
        self.cursor += 1
        return item

    def __getitem__(self, index: int) -> dict[str, Any]:
        record = self.records[int(index) % len(self.records)]
        images = _load_b2nd(record.image_path).float()
        seg = _load_b2nd(record.seg_path).long().squeeze(0)
        availability = (images.flatten(1).abs().amax(dim=1) > 1.0e-6).float()
        if self.augmenter is not None:
            images, seg, availability = self.augmenter(images, seg, availability)
        t2_present = bool(float(availability[1]) > 0.5)
        union = ((seg == 1) | (seg == 4) | (seg == 5)).float().unsqueeze(0)
        scar = (seg == 5).float().unsqueeze(0)
        edema = ((seg == 4) | (seg == 5)).float().unsqueeze(0)
        lv = (seg == 2).float().unsqueeze(0)
        rv = (seg == 3).float().unsqueeze(0)
        anatomy = torch.cat([union, lv, rv], dim=0)
        scar_class, scar_ratio = _burden_class(scar, union)
        edema_class, edema_ratio = _burden_class(edema, union)
        return {
            "case_id": [record.case_id],
            "center": [record.center],
            "fold": torch.tensor([record.fold], dtype=torch.long),
            "split": [record.split],
            "images": images.unsqueeze(0),
            "availability": availability.view(1, 3),
            "scar_target": scar.unsqueeze(0),
            "edema_zone_target": edema.unsqueeze(0),
            "anatomy_target": anatomy.unsqueeze(0),
            "t2_present": torch.tensor([[1.0 if t2_present else 0.0]], dtype=torch.float32),
            "scar_negative_targets": safe_negative_targets(images, seg, pathology="scar", t2_present=t2_present).unsqueeze(0),
            "edema_negative_targets": safe_negative_targets(images, seg, pathology="edema", t2_present=t2_present).unsqueeze(0),
            "scar_burden_class": scar_class.view(1),
            "edema_burden_class": edema_class.view(1),
            "scar_log_ratio": scar_ratio.view(1, 1),
            "edema_log_ratio": edema_ratio.view(1, 1),
        }


class CAREPRISMBalancedSampler:
    """Center x burden x positive/safe-negative case sampler for full patients."""

    def __init__(self, dataset: CAREPRISMFullPatientDataset, *, seed: int = 20260729) -> None:
        self.dataset = dataset
        self.seed = int(seed)
        self._py = random.Random(seed)
        self.center_bins: dict[str, dict[str, dict[str, list[int]]]] = {"scar": {}, "edema": {}}
        self.center_order: dict[str, list[str]] = {"scar": [], "edema": []}
        self.stratum_order: dict[str, dict[str, list[str]]] = {"scar": {}, "edema": {}}
        self.center_cursor: dict[str, int] = {"scar": 0, "edema": 0}
        self.stratum_cursor: dict[str, dict[str, int]] = {"scar": {}, "edema": {}}
        self.item_cursor: dict[str, int] = {}
        self.sample_counts: dict[str, dict[str, dict[str, int]]] = {"scar": {}, "edema": {}}
        self._build_bins()

    def _bucket(self, item: dict[str, Any], focus: str) -> str | None:
        if focus == "scar":
            positive = float(item["scar_target"].sum()) > 0.0
            negative = float(item["scar_negative_targets"].sum()) > 0.0
            burden = int(item["scar_burden_class"][0])
        else:
            if float(item["t2_present"][0, 0]) <= 0.5:
                return None
            positive = float(item["edema_zone_target"].sum()) > 0.0
            negative = float(item["edema_negative_targets"].sum()) > 0.0
            burden = int(item["edema_burden_class"][0])
        if positive:
            return f"positive_burden{burden}"
        if negative:
            return "safe_negative"
        return None

    def _build_bins(self) -> None:
        for idx in range(len(self.dataset)):
            item = self.dataset[idx]
            for focus in ("scar", "edema"):
                bucket = self._bucket(item, focus)
                if bucket is not None:
                    center = item["center"][0]
                    self.center_bins[focus].setdefault(center, {}).setdefault(bucket, []).append(idx)
        for focus in ("scar", "edema"):
            self.center_order[focus] = sorted(self.center_bins[focus])
            if not self.center_order[focus]:
                raise RuntimeError(f"no eligible {focus} bins for CARE-PRISM balanced sampling")
            for center, strata in self.center_bins[focus].items():
                self.stratum_order[focus][center] = sorted(strata)
                self.stratum_cursor[focus][center] = 0
                self.sample_counts[focus][center] = {stratum: 0 for stratum in self.stratum_order[focus][center]}
                for stratum, indices in strata.items():
                    self._py.shuffle(indices)
                    self.item_cursor[f"{focus}:{center}:{stratum}"] = 0

    def next_index(self, focus: str) -> int:
        focus = str(focus)
        centers = self.center_order[focus]
        center = centers[self.center_cursor[focus] % len(centers)]
        self.center_cursor[focus] += 1
        strata = self.stratum_order[focus][center]
        stratum = strata[self.stratum_cursor[focus][center] % len(strata)]
        self.stratum_cursor[focus][center] += 1
        key = f"{focus}:{center}:{stratum}"
        indices = self.center_bins[focus][center][stratum]
        cursor = self.item_cursor.get(key, 0)
        index = indices[cursor % len(indices)]
        self.item_cursor[key] = cursor + 1
        self.sample_counts[focus][center][stratum] = self.sample_counts[focus][center].get(stratum, 0) + 1
        return int(index)

    def state_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "center_bins": self.center_bins,
            "center_order": self.center_order,
            "stratum_order": self.stratum_order,
            "center_cursor": self.center_cursor,
            "stratum_cursor": self.stratum_cursor,
            "item_cursor": self.item_cursor,
            "sample_counts": self.sample_counts,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.seed = int(state.get("seed", self.seed))
        self.center_bins = {
            focus: {center: {stratum: [int(v) for v in vals] for stratum, vals in strata.items()} for center, strata in centers.items()}
            for focus, centers in state.get("center_bins", self.center_bins).items()
        }
        self.center_order = {focus: [str(v) for v in order] for focus, order in state.get("center_order", self.center_order).items()}
        self.stratum_order = {
            focus: {center: [str(v) for v in order] for center, order in centers.items()}
            for focus, centers in state.get("stratum_order", self.stratum_order).items()
        }
        self.center_cursor = {focus: int(v) for focus, v in state.get("center_cursor", self.center_cursor).items()}
        self.stratum_cursor = {
            focus: {center: int(v) for center, v in centers.items()} for focus, centers in state.get("stratum_cursor", self.stratum_cursor).items()
        }
        self.item_cursor = {str(k): int(v) for k, v in state.get("item_cursor", self.item_cursor).items()}
        self.sample_counts = {
            focus: {center: {stratum: int(v) for stratum, v in strata.items()} for center, strata in centers.items()}
            for focus, centers in state.get("sample_counts", self.sample_counts).items()
        }

    def summary(self) -> dict[str, Any]:
        return {
            focus: {
                "center_count": len(self.center_order[focus]),
                "case_count": int(sum(len(v) for strata in self.center_bins[focus].values() for v in strata.values())),
                "bins": {center: {k: len(v) for k, v in sorted(strata.items())} for center, strata in sorted(self.center_bins[focus].items())},
                "sample_counts": self.sample_counts[focus],
            }
            for focus in ("scar", "edema")
        }


def synthetic_w1_batch(
    *,
    batch_size: int = 1,
    shape: tuple[int, int, int] = (8, 128, 128),
    t2_present: bool = True,
    seed: int = 13,
) -> dict[str, Any]:
    generator = torch.Generator().manual_seed(seed)
    images = torch.randn(batch_size, 3, *shape, generator=generator)
    availability = torch.ones(batch_size, 3)
    if not t2_present:
        availability[:, 1] = 0.0
        images[:, 1] = 0.0
    scar = torch.zeros(batch_size, 1, *shape)
    edema = torch.zeros(batch_size, 1, *shape)
    z0, y0, x0 = max(shape[0] // 2 - 1, 0), shape[1] // 3, shape[2] // 3
    scar[:, :, z0 : z0 + 2, y0 : y0 + 12, x0 : x0 + 12] = 1.0
    if t2_present:
        edema[:, :, z0 : z0 + 2, y0 : y0 + 20, x0 : x0 + 20] = 1.0
    anatomy = torch.zeros(batch_size, 3, *shape)
    anatomy[:, 0:1] = torch.clamp(edema + scar, 0, 1)
    anatomy[:, 1:2, :, shape[1] // 4 : shape[1] // 2, shape[2] // 4 : shape[2] // 2] = 1.0
    anatomy[:, 2:3, :, shape[1] // 2 : 3 * shape[1] // 4, shape[2] // 2 : 3 * shape[2] // 4] = 1.0
    synthetic_seg = torch.zeros(batch_size, *shape, dtype=torch.long)
    synthetic_seg[anatomy[:, 0] > 0] = 1
    synthetic_seg[anatomy[:, 1] > 0] = 2
    synthetic_seg[anatomy[:, 2] > 0] = 3
    synthetic_seg[edema[:, 0] > 0] = 4
    synthetic_seg[scar[:, 0] > 0] = 5
    scar_neg = torch.stack([safe_negative_targets(images[i], synthetic_seg[i], pathology="scar", t2_present=t2_present) for i in range(batch_size)])
    edema_neg = torch.stack([safe_negative_targets(images[i], synthetic_seg[i], pathology="edema", t2_present=t2_present) for i in range(batch_size)])
    return {
        "case_id": [f"synthetic_w1_{'t2' if t2_present else 'no_t2'}"],
        "images": images,
        "availability": availability,
        "scar_target": scar,
        "edema_zone_target": edema,
        "anatomy_target": anatomy,
        "t2_present": torch.full((batch_size, 1), 1.0 if t2_present else 0.0),
        "scar_negative_targets": scar_neg,
        "edema_negative_targets": edema_neg,
        "scar_burden_class": torch.zeros(batch_size, dtype=torch.long),
        "edema_burden_class": torch.zeros(batch_size, dtype=torch.long),
        "scar_log_ratio": torch.zeros(batch_size, 1),
        "edema_log_ratio": torch.zeros(batch_size, 1),
    }


class CAREPRISMSyntheticDataset(torch.utils.data.Dataset[dict[str, Any]]):
    def __init__(self, *, length: int = 4, shape: tuple[int, int, int] = (8, 128, 128)) -> None:
        self.length = int(length)
        self.shape = shape

    def __len__(self) -> int:
        return self.length

    def __getitem__(self, index: int) -> dict[str, Any]:
        return synthetic_w1_batch(shape=self.shape, t2_present=(index % 2 == 0), seed=13 + index)


def collate_single_case(items: list[dict[str, Any]]) -> dict[str, Any]:
    if len(items) != 1:
        raise ValueError("CARE-PRISM W1 fixtures expect one full patient per batch")
    return items[0]
