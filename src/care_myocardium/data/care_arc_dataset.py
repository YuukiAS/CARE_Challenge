"""Dataset and split contracts for CARE-ARC."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch
from torch.utils.data import Dataset

from scripts.training.run_care_dg import deterministic_inner_split, load_splits
from src.care_myocardium.data.case_metadata import MyoPSCaseMetadata, load_myops_case_metadata


REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_TRAIN = REPO_ROOT / "data/CARE_Challenge/MyoPS_train"
LABEL_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
SCAR_LABEL = 5
EDEMA_LABEL = 4
MYOCARDIUM_LABELS = (1, 4, 5)


@dataclass(frozen=True)
class CAREARCCaseRecord:
    case_id: str
    fold: int
    split_role: str
    label_path: Path
    availability: tuple[float, float, float]
    center: str
    modality_group: str
    t2_present: bool
    scar_positive: bool
    edema_positive: bool
    shape_dhw: tuple[int, int, int]


def modality_path(case_id: str, suffix: str) -> Path | None:
    found = list(RAW_TRAIN.glob(f"*/{case_id}/{case_id}_{suffix}.nii.gz"))
    return found[0] if found else None


def read_resampled(path: Path | None, ref: sitk.Image) -> np.ndarray:
    if path is None:
        return np.zeros(tuple(reversed(ref.GetSize())), dtype=np.float32)
    img = sitk.ReadImage(str(path), sitk.sitkFloat32)
    if (
        img.GetSize() != ref.GetSize()
        or img.GetSpacing() != ref.GetSpacing()
        or img.GetOrigin() != ref.GetOrigin()
        or img.GetDirection() != ref.GetDirection()
    ):
        img = sitk.Resample(img, ref, sitk.Transform(), sitk.sitkLinear, 0.0, sitk.sitkFloat32)
    arr = sitk.GetArrayFromImage(img).astype(np.float32)
    return (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)


def center_inplane_crop_or_pad(arr: np.ndarray, crop_hw: int, fill: float = 0.0) -> np.ndarray:
    h, w = arr.shape[-2:]
    y0 = h // 2 - int(crop_hw) // 2
    x0 = w // 2 - int(crop_hw) // 2
    out_shape = arr.shape[:-2] + (int(crop_hw), int(crop_hw))
    out = np.full(out_shape, fill, dtype=arr.dtype)
    src_y0 = max(0, y0)
    src_x0 = max(0, x0)
    src_y1 = min(h, y0 + int(crop_hw))
    src_x1 = min(w, x0 + int(crop_hw))
    dst_y0 = max(0, -y0)
    dst_x0 = max(0, -x0)
    dst_y1 = dst_y0 + max(0, src_y1 - src_y0)
    dst_x1 = dst_x0 + max(0, src_x1 - src_x0)
    out[..., dst_y0:dst_y1, dst_x0:dst_x1] = arr[..., src_y0:src_y1, src_x0:src_x1]
    return out


def load_label(case_id: str) -> tuple[np.ndarray, sitk.Image]:
    path = LABEL_ROOT / f"{case_id}.nii.gz"
    if not path.exists():
        raise FileNotFoundError(path)
    ref = sitk.ReadImage(str(path))
    return sitk.GetArrayFromImage(ref).astype(np.int64), ref


def anatomy_target(label: np.ndarray) -> np.ndarray:
    out = np.zeros_like(label, dtype=np.int64)
    out[label == 1] = 1
    out[label == 2] = 2
    out[label == 3] = 3
    out[np.isin(label, [4, 5])] = 1
    return out


def load_case_record(case_id: str, fold: int, role: str, metadata: dict[str, MyoPSCaseMetadata]) -> CAREARCCaseRecord:
    label, _ref = load_label(case_id)
    meta = metadata[case_id]
    return CAREARCCaseRecord(
        case_id=case_id,
        fold=int(fold),
        split_role=role,
        label_path=LABEL_ROOT / f"{case_id}.nii.gz",
        availability=tuple(float(v) for v in meta.availability),
        center=str(meta.center),
        modality_group=str(meta.modality_group),
        t2_present=bool(meta.t2_present),
        scar_positive=bool(np.any(label == SCAR_LABEL)),
        edema_positive=bool(np.any(label == EDEMA_LABEL)),
        shape_dhw=tuple(int(v) for v in label.shape),
    )


def care_arc_split(fold: int, metadata: dict[str, MyoPSCaseMetadata] | None = None) -> dict[str, Any]:
    metadata = metadata or load_myops_case_metadata(REPO_ROOT)
    split = next(row for row in load_splits() if int(row["fold"]) == int(fold))
    inner = deterministic_inner_split(sorted(split["train"]), int(fold), metadata)
    return {**inner, "outer_cases": sorted(split["val"])}


class CAREARCDataset(Dataset[dict[str, Any]]):
    def __init__(self, records: list[CAREARCCaseRecord], *, crop_hw: int = 256) -> None:
        self.records = list(records)
        self.crop_hw = int(crop_hw)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, Any]:
        record = self.records[index]
        label, ref = load_label(record.case_id)
        images = np.stack([read_resampled(modality_path(record.case_id, suffix), ref) for suffix in ("LGE", "T2", "C0")], axis=0)
        images = center_inplane_crop_or_pad(images, self.crop_hw, fill=0.0)
        label = center_inplane_crop_or_pad(label, self.crop_hw, fill=0)
        scar = (label == SCAR_LABEL).astype(np.float32)
        edema_zone = ((label == EDEMA_LABEL) | (label == SCAR_LABEL)).astype(np.float32)
        myocardium = np.isin(label, MYOCARDIUM_LABELS).astype(np.float32)
        anatomy = anatomy_target(label)
        spacing = tuple(reversed([float(v) for v in ref.GetSpacing()]))
        return {
            "case_id": record.case_id,
            "images": torch.from_numpy(images.astype(np.float32)),
            "label": torch.from_numpy(label.astype(np.int64)),
            "anatomy_target": torch.from_numpy(anatomy.astype(np.int64)),
            "scar_target": torch.from_numpy(scar[None]),
            "edema_zone_target": torch.from_numpy(edema_zone[None]),
            "myocardium_target": torch.from_numpy(myocardium[None]),
            "availability": torch.tensor(record.availability, dtype=torch.float32),
            "spacing_zyx": torch.tensor(spacing, dtype=torch.float32),
            "t2_present": torch.tensor(float(record.t2_present), dtype=torch.float32),
            "scar_positive": torch.tensor(float(record.scar_positive), dtype=torch.float32),
            "edema_positive": torch.tensor(float(record.edema_positive), dtype=torch.float32),
            "shape_dhw": torch.tensor(record.shape_dhw, dtype=torch.int64),
            "center": record.center,
            "modality_group": record.modality_group,
        }


def build_case_records(fold: int, role: str, metadata: dict[str, MyoPSCaseMetadata] | None = None) -> list[CAREARCCaseRecord]:
    metadata = metadata or load_myops_case_metadata(REPO_ROOT)
    split = care_arc_split(fold, metadata)
    if role == "actual_train":
        cases = split["actual_train_cases"]
    elif role == "inner":
        cases = split["inner_select_cases"]
    elif role == "outer":
        cases = split["outer_cases"]
    else:
        raise ValueError(f"unknown CARE-ARC split role: {role}")
    return [load_case_record(case_id, int(fold), role, metadata) for case_id in cases]


def collate_single_case(batch: list[dict[str, Any]]) -> dict[str, Any]:
    if len(batch) != 1:
        raise ValueError("CARE-ARC formal loader requires batch size 1 because D varies by case")
    item = batch[0]
    tensor_keys = {
        "images",
        "label",
        "anatomy_target",
        "scar_target",
        "edema_zone_target",
        "myocardium_target",
        "availability",
        "spacing_zyx",
        "t2_present",
        "scar_positive",
        "edema_positive",
        "shape_dhw",
    }
    out: dict[str, Any] = {}
    for key, value in item.items():
        if key in tensor_keys:
            out[key] = value.unsqueeze(0)
        else:
            out[key] = [value]
    return out
