"""Dataset helpers for Lane A Round10 edema refiner."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))

from src.care_myocardium.nnunet.laneA_round7_trainer import MODALITY_PRESENCE_ORDER, load_case_modality_map


BASELINE_RESULTS_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
RAW_ROOT = REPO_ROOT / "data/CARE_Challenge/MyoPS_train"
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
CASE_METRICS = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/myops_modality_center_case_metrics.csv"


@dataclass(frozen=True)
class RefinerCase:
    case_id: str
    fold0_split: str
    source_fold: int
    center: str
    modality_group: str
    c0_present: bool
    lge_present: bool
    t2_present: bool
    edema_gt_positive: bool
    scar_gt_positive: bool
    prediction_path: Path
    probability_path: Path
    gt_path: Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def bool_csv(value: object) -> bool:
    return str(value).strip().lower() == "true"


def load_splits() -> dict[str, object]:
    return json.loads(SPLITS_JSON.read_text(encoding="utf-8"))


def fold0_split_map() -> dict[str, str]:
    fold0 = load_splits()["folds"][0]
    out = {str(cid): "train" for cid in fold0["train"]}
    out.update({str(cid): "val" for cid in fold0["val"]})
    return out


def case_to_validation_fold() -> dict[str, int]:
    out: dict[str, int] = {}
    for fold in load_splits()["folds"]:
        fold_id = int(fold["fold"])
        for cid in fold["val"]:
            out[str(cid)] = fold_id
    return out


def load_gt_flags() -> dict[str, dict[str, bool]]:
    out: dict[str, dict[str, bool]] = {}
    for row in read_csv(CASE_METRICS):
        out[row["case_id"]] = {
            "edema_gt_positive": bool_csv(row.get("edema_gt_positive", "")),
            "scar_gt_positive": bool_csv(row.get("scar_gt_positive", "")),
        }
    return out


def gt_flags_from_label(path: Path) -> dict[str, bool]:
    if not path.is_file():
        return {"edema_gt_positive": False, "scar_gt_positive": False}
    arr = sitk.GetArrayFromImage(sitk.ReadImage(str(path)))
    return {
        "edema_gt_positive": bool(np.any(arr == 4)),
        "scar_gt_positive": bool(np.any(arr == 5)),
    }


def build_cases() -> list[RefinerCase]:
    split_map = fold0_split_map()
    val_fold_map = case_to_validation_fold()
    meta = load_case_modality_map(REPO_ROOT)
    flags = load_gt_flags()
    cases: list[RefinerCase] = []
    for cid, fold0_split in sorted(split_map.items()):
        source_fold = val_fold_map[cid]
        pred_dir = BASELINE_RESULTS_ROOT / f"fold_{source_fold}" / "validation"
        case_meta = meta[cid]
        gt_path = GT_DIR / f"{cid}.nii.gz"
        case_flags = flags.get(cid) or gt_flags_from_label(gt_path)
        cases.append(
            RefinerCase(
                case_id=cid,
                fold0_split=fold0_split,
                source_fold=source_fold,
                center=str(case_meta["center"]),
                modality_group=str(case_meta["modality_group"]),
                c0_present=bool(case_meta["C0_present"]),
                lge_present=bool(case_meta["LGE_present"]),
                t2_present=bool(case_meta["T2_present"]),
                edema_gt_positive=bool(case_flags.get("edema_gt_positive", False)),
                scar_gt_positive=bool(case_flags.get("scar_gt_positive", False)),
                prediction_path=pred_dir / f"{cid}.nii.gz",
                probability_path=pred_dir / f"{cid}.npz",
                gt_path=gt_path,
            )
        )
    return cases


def case_to_row(case: RefinerCase) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "fold": 0,
        "split": case.fold0_split,
        "baseline_source_fold": case.source_fold,
        "center": case.center,
        "modality_group": case.modality_group,
        "C0_present": case.c0_present,
        "LGE_present": case.lge_present,
        "T2_present": case.t2_present,
        "edema_gt_positive": case.edema_gt_positive,
        "scar_gt_positive": case.scar_gt_positive,
        "no_t2_empty_gt": (not case.t2_present) and (not case.edema_gt_positive),
        "baseline_prediction_path": str(case.prediction_path),
        "baseline_probability_path": str(case.probability_path),
        "gt_path": str(case.gt_path),
        "prediction_available": case.prediction_path.is_file(),
        "probability_available": case.probability_path.is_file(),
        "gt_available": case.gt_path.is_file(),
        "feature_channel_order": "baseline_prob_0..5,C0,LGE,T2,C0_present,LGE_present,T2_present,baseline_anatomy_support",
        "target": "gt_class_4_edema_binary",
    }


def load_label(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    arr = sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)
    return img, arr


def load_probabilities(path: Path) -> np.ndarray:
    with np.load(path) as data:
        probs = np.asarray(data["probabilities"], dtype=np.float32)
    return probs


def resample_to_reference(path: Path, reference: sitk.Image, *, label: bool) -> np.ndarray:
    img = sitk.ReadImage(str(path))
    if (
        img.GetSize() != reference.GetSize()
        or img.GetSpacing() != reference.GetSpacing()
        or img.GetOrigin() != reference.GetOrigin()
        or img.GetDirection() != reference.GetDirection()
    ):
        interpolator = sitk.sitkNearestNeighbor if label else sitk.sitkLinear
        img = sitk.Resample(img, reference, sitk.Transform(), interpolator, 0, img.GetPixelID())
    return sitk.GetArrayFromImage(img)


def normalize_image(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32, copy=False)
    nonzero = arr[np.isfinite(arr)]
    if nonzero.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    lo = float(np.percentile(nonzero, 1))
    hi = float(np.percentile(nonzero, 99))
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def raw_modality_path(case: RefinerCase, modality: str) -> Path:
    return RAW_ROOT / case.center / case.case_id / f"{case.case_id}_{modality}.nii.gz"


def load_case_features(case: RefinerCase) -> tuple[np.ndarray, np.ndarray, np.ndarray, sitk.Image]:
    """Return features, GT edema mask, baseline seg, and reference image.

    Feature order: baseline probabilities 0..5, raw C0/LGE/T2, three constant
    presence channels, and baseline anatomy support from classes 1/2/3.
    """

    gt_img, gt = load_label(case.gt_path)
    baseline_seg = resample_to_reference(case.prediction_path, gt_img, label=True).astype(np.uint8, copy=False)
    probs = load_probabilities(case.probability_path)
    if probs.shape[1:] != gt.shape:
        raise ValueError(f"{case.case_id}: probability shape {probs.shape[1:]} != GT shape {gt.shape}")
    channels: list[np.ndarray] = [probs[i].astype(np.float32, copy=False) for i in range(probs.shape[0])]
    for modality, present in zip(MODALITY_PRESENCE_ORDER, [case.c0_present, case.lge_present, case.t2_present]):
        path = raw_modality_path(case, modality)
        if present and path.is_file():
            channels.append(normalize_image(resample_to_reference(path, gt_img, label=False)))
        else:
            channels.append(np.zeros_like(gt, dtype=np.float32))
    for present in [case.c0_present, case.lge_present, case.t2_present]:
        channels.append(np.full(gt.shape, 1.0 if present else 0.0, dtype=np.float32))
    channels.append(np.clip(probs[1] + probs[2] + probs[3], 0.0, 1.0).astype(np.float32))
    features = np.stack(channels, axis=0).astype(np.float32, copy=False)
    target = (gt == 4).astype(np.float32)
    return features, target, baseline_seg, gt_img


def summarize_geometry(cases: Iterable[RefinerCase]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in cases:
        row = case_to_row(case)
        if case.gt_path.is_file():
            img = sitk.ReadImage(str(case.gt_path))
            row.update(
                {
                    "gt_size": "x".join(map(str, img.GetSize())),
                    "gt_spacing": "x".join(f"{v:.6g}" for v in img.GetSpacing()),
                    "gt_origin": "x".join(f"{v:.6g}" for v in img.GetOrigin()),
                    "gt_direction": "x".join(f"{v:.6g}" for v in img.GetDirection()),
                }
            )
        rows.append(row)
    return rows
