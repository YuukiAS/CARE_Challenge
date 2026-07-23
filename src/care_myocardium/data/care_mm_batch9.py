"""Runtime data helpers for CARE Batch9."""

from __future__ import annotations

import csv
import hashlib
import json
import pickle
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import blosc2
import numpy as np
import torch

from src.care_myocardium.data.case_metadata import MyoPSCaseMetadata, load_myops_case_metadata


REPO_ROOT = Path(__file__).resolve().parents[3]
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
SPLIT_PATH = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
RAW_LABEL_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    split: str
    center: str
    modality_group: str
    lge_present: bool
    t2_present: bool
    c0_present: bool
    anatomy_reliable: bool
    scar_reliable: bool
    edema_reliable: bool
    final_six_class_reliable: bool
    scar_positive: bool
    edema_positive: bool

    @property
    def availability(self) -> tuple[float, float, float]:
        return (float(self.lge_present), float(self.t2_present), float(self.c0_present))


def load_fold_cases(fold: int = 0) -> tuple[list[str], list[str]]:
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))[fold]
    return list(split["train"]), list(split["val"])


def case_center_from_metadata(meta: MyoPSCaseMetadata) -> str:
    return meta.center


def label_presence(case_id: str) -> dict[str, bool]:
    pkl_path = PREPROCESSED / f"{case_id}.pkl"
    with pkl_path.open("rb") as f:
        props = pickle.load(f)
    loc = props.get("class_locations", {})
    return {
        "scar_positive": bool(len(loc.get(5, [])) > 0),
        "edema_positive": bool(len(loc.get(4, [])) > 0),
    }


def build_case_records(fold: int = 0) -> list[CaseRecord]:
    train, val = load_fold_cases(fold)
    split_by_case = {case_id: "train" for case_id in train}
    split_by_case.update({case_id: "val" for case_id in val})
    metadata = load_myops_case_metadata(REPO_ROOT)
    records: list[CaseRecord] = []
    for case_id in sorted(split_by_case):
        meta = metadata[case_id]
        labels = label_presence(case_id)
        edema_reliable = bool(meta.t2_present)
        final_reliable = bool(meta.t2_present)
        records.append(
            CaseRecord(
                case_id=case_id,
                split=split_by_case[case_id],
                center=meta.center,
                modality_group=meta.modality_group,
                lge_present=meta.lge_present,
                t2_present=meta.t2_present,
                c0_present=meta.c0_present,
                anatomy_reliable=True,
                scar_reliable=True,
                edema_reliable=edema_reliable,
                final_six_class_reliable=final_reliable,
                scar_positive=labels["scar_positive"],
                edema_positive=labels["edema_positive"],
            )
        )
    return records


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def generate_inventory(result_root: Path, fold: int = 0) -> dict[str, Any]:
    records = build_case_records(fold)
    manifest_rows = [
        {
            "case_id": r.case_id,
            "split": r.split,
            "center": r.center,
            "modality_group": r.modality_group,
            "lge_present": int(r.lge_present),
            "t2_present": int(r.t2_present),
            "c0_present": int(r.c0_present),
            "anatomy_reliable": int(r.anatomy_reliable),
            "scar_reliable": int(r.scar_reliable),
            "edema_reliable": int(r.edema_reliable),
            "final_six_class_reliable": int(r.final_six_class_reliable),
            "scar_positive": int(r.scar_positive),
            "edema_positive": int(r.edema_positive),
        }
        for r in records
    ]
    write_csv(result_root / "fold0_case_manifest.csv", manifest_rows)

    inventory: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in records:
        key = (r.split, r.center, r.modality_group)
        row = inventory.setdefault(
            key,
            {
                "split": r.split,
                "center": r.center,
                "modality_group": r.modality_group,
                "case_count": 0,
                "scar_positive_cases": 0,
                "edema_positive_cases": 0,
                "edema_reliable_cases": 0,
                "no_t2_cases": 0,
            },
        )
        row["case_count"] += 1
        row["scar_positive_cases"] += int(r.scar_positive)
        row["edema_positive_cases"] += int(r.edema_positive)
        row["edema_reliable_cases"] += int(r.edema_reliable)
        row["no_t2_cases"] += int(not r.t2_present)
    write_csv(result_root / "center_modality_label_inventory.csv", list(inventory.values()))

    supervision_rows = [
        {
            "case_id": r.case_id,
            "split": r.split,
            "center": r.center,
            "natural_availability_lge_t2_c0": "".join(str(int(v)) for v in r.availability),
            "anatomy_supervision": int(r.anatomy_reliable),
            "scar_supervision": int(r.scar_reliable),
            "edema_supervision": int(r.edema_reliable),
            "edema_distillation_eligible": int(r.final_six_class_reliable and r.t2_present),
            "no_t2_edema_supervised_voxel_count": 0 if not r.t2_present else "NA",
            "center_enters_network": 0,
        }
        for r in records
    ]
    write_csv(result_root / "reliable_supervision_inventory.csv", supervision_rows)
    train = [r for r in records if r.split == "train"]
    val = [r for r in records if r.split == "val"]
    return {
        "schema_version": 1,
        "status": "PASS",
        "fold": fold,
        "train_count": len(train),
        "validation_count": len(val),
        "total_count": len(records),
        "no_t2_edema_reliable_count": sum((not r.t2_present) and r.edema_reliable for r in records),
        "natural_availability_source": "data/CARE_Challenge/MyoPS_train center/case modality files",
    }


class Batch9PatchSampler:
    def __init__(
        self,
        records: list[CaseRecord],
        *,
        patch_size: tuple[int, int, int] = (20, 128, 128),
        seed: int = 0,
        complete_only: bool = False,
        edema_pool_probability: float = 0.5,
        target_probabilities: dict[str, float] | None = None,
    ) -> None:
        self.records = [r for r in records if r.split == "train"]
        if complete_only:
            self.records = [r for r in self.records if r.t2_present and r.c0_present and r.edema_reliable]
        if not self.records:
            raise ValueError("no training records available")
        self.patch_size = patch_size
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        self.by_id = {r.case_id: r for r in self.records}
        self.target_probabilities = target_probabilities or {
            "scar": 0.35,
            "edema_reliable": float(edema_pool_probability),
            "anatomy": 0.20,
            "background": 0.10,
        }
        self.target_pools: dict[str, list[CaseRecord]] = {
            "scar": [r for r in self.records if r.scar_reliable and r.scar_positive],
            "edema_reliable": [r for r in self.records if r.edema_reliable and r.t2_present and r.edema_positive],
            "anatomy": list(self.records),
            "background": list(self.records),
        }

    def sample_target(self) -> str:
        available = [(k, float(v)) for k, v in self.target_probabilities.items() if self.target_pools.get(k) and float(v) > 0]
        if not available:
            return "anatomy"
        total = sum(v for _, v in available)
        draw = self.rng.random() * total
        running = 0.0
        for key, prob in available:
            running += prob
            if draw <= running:
                return key
        return available[-1][0]

    def sample_record(self, target: str | None = None) -> CaseRecord:
        target = target or self.sample_target()
        pool = self.target_pools.get(target) or self.records
        return self.rng.choice(pool)

    def load_case(self, case_id: str) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
        data = np.asarray(blosc2.open(urlpath=str(PREPROCESSED / f"{case_id}.b2nd"), mode="r", dparams={"nthreads": 1}))
        seg = np.asarray(blosc2.open(urlpath=str(PREPROCESSED / f"{case_id}_seg.b2nd"), mode="r", dparams={"nthreads": 1}))
        with (PREPROCESSED / f"{case_id}.pkl").open("rb") as f:
            props = pickle.load(f)
        return data, seg[0], props

    def _class_location(self, props: dict[str, Any], class_ids: tuple[int, ...]) -> np.ndarray | None:
        for key in class_ids:
            loc = props.get("class_locations", {}).get(key, [])
            if len(loc):
                return loc[self.np_rng.integers(0, len(loc))][1:].astype(int)
        return None

    def _patch_bounds(self, shape: tuple[int, int, int], props: dict[str, Any], target: str = "anatomy") -> tuple[tuple[int, int], ...]:
        class_ids = {
            "scar": (5,),
            "edema_reliable": (4,),
            "anatomy": (1, 2, 3, 4, 5),
            "background": (0,),
        }.get(target, (4, 5, 1, 2, 3))
        center = self._class_location(props, class_ids)
        if center is None:
            center = np.array([self.np_rng.integers(0, max(1, s)) for s in shape], dtype=int)
        bounds = []
        for c, size, patch in zip(center, shape, self.patch_size):
            lo = int(max(0, min(size - patch, c - patch // 2))) if size > patch else 0
            hi = lo + patch
            bounds.append((lo, hi))
        return tuple(bounds)

    def sample_batch(
        self,
        batch_size: int,
        *,
        variant: str,
        step: int,
        matched_seed: int,
        force_case_ids: Iterable[str] | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, list[CaseRecord], list[dict[str, Any]]]:
        rows: list[dict[str, Any]] = []
        xs: list[np.ndarray] = []
        natural_xs: list[np.ndarray] = []
        ys: list[np.ndarray] = []
        records: list[CaseRecord] = []
        forced = list(force_case_ids or [])
        for b in range(batch_size):
            target = "forced" if forced else self.sample_target()
            record = self.by_id[forced[b % len(forced)]] if forced else self.sample_record(target)
            data, seg, props = self.load_case(record.case_id)
            bounds = self._patch_bounds(tuple(seg.shape), props, target=target)
            slices = tuple(slice(lo, hi) for lo, hi in bounds)
            x = data[(slice(None), *slices)]
            y = seg[slices]
            x = _pad_spatial(x, self.patch_size, value=0)
            y = _pad_spatial(y[None], self.patch_size, value=0)[0]
            natural = np.array(record.availability, dtype=np.float32)
            x_natural = x.copy()
            for ch in range(3):
                if natural[ch] < 0.5:
                    x_natural[ch] = 0
            student = structured_student_availability(natural, variant=variant, rng=random.Random(matched_seed + step * 1009 + b))
            x = x.copy()
            for ch in range(3):
                if student[ch] < 0.5:
                    x[ch] = 0
            xs.append(x.astype(np.float32, copy=False))
            natural_xs.append(x_natural.astype(np.float32, copy=False))
            ys.append(y.astype(np.int64, copy=False))
            records.append(record)
            rows.append(
                {
                    "step": step,
                    "batch_index": b,
                    "case_id": record.case_id,
                    "center": record.center,
                    "patch_center": ";".join(str((lo + hi) // 2) for lo, hi in bounds),
                    "natural_availability": "".join(str(int(v)) for v in natural),
                    "student_availability": "".join(str(int(v)) for v in student),
                    "rng_state": str(matched_seed + step * 1009 + b),
                    "variant": variant,
                    "sample_target": target,
                    "patch_bounds": ";".join(f"{lo}:{hi}" for lo, hi in bounds),
                }
            )
        return (
            torch.from_numpy(np.stack(xs, axis=0)),
            torch.from_numpy(np.stack(natural_xs, axis=0)),
            torch.from_numpy(np.stack(ys, axis=0)),
            torch.from_numpy(np.stack([structured_student_availability(np.array(r.availability), variant=variant, rng=random.Random(matched_seed + step * 1009 + i)) for i, r in enumerate(records)], axis=0)).float(),
            records,
            rows,
        )


def _pad_spatial(arr: np.ndarray, patch_size: tuple[int, int, int], value: float) -> np.ndarray:
    pads = []
    for size, patch in zip(arr.shape[-3:][::-1], patch_size[::-1]):
        pads.append((0, max(0, patch - size)))
    pad_width = [(0, 0)] * (arr.ndim - 3) + list(reversed(pads))
    return np.pad(arr, pad_width, mode="constant", constant_values=value)


def structured_student_availability(natural: np.ndarray, *, variant: str, rng: random.Random) -> np.ndarray:
    natural = natural.astype(np.float32, copy=True)
    if variant in {"student_direct_reliable", "teacher_full_view"}:
        return natural
    if natural.tolist() == [1.0, 1.0, 1.0]:
        draw = rng.random()
        if draw < 0.50:
            return np.array([1, 1, 1], dtype=np.float32)
        if draw < 0.75:
            return np.array([1, 0, 1], dtype=np.float32)
        return np.array([1, 0, 0], dtype=np.float32)
    if natural.tolist() == [1.0, 0.0, 1.0]:
        return np.array([1, 0, 1], dtype=np.float32) if rng.random() < 0.75 else np.array([1, 0, 0], dtype=np.float32)
    return np.array([1, 0, 0], dtype=np.float32)


def reliable_masks_for_records(records: list[CaseRecord], device: torch.device) -> dict[str, torch.Tensor]:
    return {
        "anatomy": torch.tensor([r.anatomy_reliable for r in records], device=device, dtype=torch.bool),
        "scar": torch.tensor([r.scar_reliable for r in records], device=device, dtype=torch.bool),
        "edema": torch.tensor([r.edema_reliable and r.t2_present for r in records], device=device, dtype=torch.bool),
        "final_six_class": torch.tensor([r.final_six_class_reliable and r.t2_present for r in records], device=device, dtype=torch.bool),
        "natural_complete_trimodal": torch.tensor(
            [r.lge_present and r.t2_present and r.c0_present for r in records], device=device, dtype=torch.bool
        ),
    }
