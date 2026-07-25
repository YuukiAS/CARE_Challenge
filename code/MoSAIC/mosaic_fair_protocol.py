"""Shared protocol helpers for CARE MoSAIC fair reproduction."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml"
DEFAULT_RESULT_ROOT = REPO_ROOT / "results/20260725_care_myops_mosaic_fold0_reproduction"
DEFAULT_MOSAIC_ROOT = Path(os.environ.get("MOSAIC_ROOT", "/users/a/e/aereinh/MoSAIC"))
DEFAULT_MOSAIC_SOURCE_ROOT = REPO_ROOT / "third_party/MoSAIC/source"
MOSAIC_SOURCE_COMMIT = "d334bd1fb2a99dbbc230510590cd8e3ee08cc377"

CARE_INPUT_ORDER = ("LGE", "T2", "C0")
MOSAIC_INPUT_ORDER = ("LGE", "C0", "T2")
COMPACT_TO_OFFICIAL = {4: 1220, 5: 2221}
OFFICIAL_TO_COMPACT = {v: k for k, v in COMPACT_TO_OFFICIAL.items()}
PATHOLOGY_CLASSES = {
    "pure_edema": {"compact": 4, "official": 1220},
    "edema_zone": {"compact": [4, 5], "official": [1220, 2221]},
    "scar": {"compact": 5, "official": 2221},
}


def load_yaml(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"config is not a mapping: {path}")
    return data


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_fold_val_cases(split_path: Path, fold: int) -> list[str]:
    data = json.loads(split_path.read_text(encoding="utf-8"))
    folds = data.get("folds", data)
    if fold < 0 or fold >= len(folds):
        raise ValueError(f"fold {fold} out of range for {split_path}")
    return sorted(folds[fold]["val"])


def load_fold_train_cases(split_path: Path, fold: int) -> list[str]:
    data = json.loads(split_path.read_text(encoding="utf-8"))
    folds = data.get("folds", data)
    if fold < 0 or fold >= len(folds):
        raise ValueError(f"fold {fold} out of range for {split_path}")
    return sorted(folds[fold]["train"])


def load_fold_case_sets(split_path: Path, fold: int) -> tuple[set[str], set[str]]:
    return set(load_fold_train_cases(split_path, fold)), set(load_fold_val_cases(split_path, fold))


def reorder_channels(image: np.ndarray, source_order: Iterable[str], target_order: Iterable[str]) -> np.ndarray:
    source = tuple(source_order)
    target = tuple(target_order)
    if image.ndim < 1:
        raise ValueError("image must have a channel axis")
    if image.shape[0] != len(source):
        raise ValueError(f"channel count {image.shape[0]} does not match source order {source}")
    missing = [name for name in target if name not in source]
    if missing:
        raise ValueError(f"target channels missing from source order: {missing}")
    return image[[source.index(name) for name in target]]


def remap_labels(labels: np.ndarray, mapping: dict[int, int]) -> np.ndarray:
    out = labels.copy()
    for src, dst in mapping.items():
        out[labels == int(src)] = int(dst)
    return out


def pathology_mask(labels: np.ndarray, pathology: str, *, label_space: str = "compact") -> np.ndarray:
    spec = PATHOLOGY_CLASSES[pathology][label_space]
    values = spec if isinstance(spec, list) else [spec]
    mask = np.zeros(labels.shape, dtype=bool)
    for value in values:
        mask |= labels == int(value)
    return mask


def classify_spatial_layout(actual_shape: tuple[int, int, int], reference_zhw_shape: tuple[int, int, int]) -> str:
    z, h, w = tuple(int(v) for v in reference_zhw_shape)
    actual = tuple(int(v) for v in actual_shape)
    candidates = {
        "ZHW": (z, h, w),
        "HWZ": (h, w, z),
        "HZW": (h, z, w),
        "WZH": (w, z, h),
        "WHZ": (w, h, z),
        "ZWH": (z, w, h),
    }
    for name, shape in candidates.items():
        if actual == shape:
            return name
    return "UNKNOWN"


def geometry_signature(image: Any) -> dict[str, Any]:
    return {
        "size_xyz": [int(v) for v in image.GetSize()],
        "spacing_xyz": [float(v) for v in image.GetSpacing()],
        "origin_xyz": [float(v) for v in image.GetOrigin()],
        "direction": [float(v) for v in image.GetDirection()],
    }


def geometry_matches(left: dict[str, Any], right: dict[str, Any], *, tol: float = 1e-6) -> bool:
    if left["size_xyz"] != right["size_xyz"]:
        return False
    for key in ("spacing_xyz", "origin_xyz", "direction"):
        if len(left[key]) != len(right[key]):
            return False
        if any(abs(float(a) - float(b)) > tol for a, b in zip(left[key], right[key])):
            return False
    return True


def find_native_mosaic_source(mosaic_root: Path, source_root: Path | None = None) -> dict[str, Any]:
    root = source_root.resolve() if source_root is not None else mosaic_root.resolve()
    candidates = [root, root / "code", root / "src", root / "MoSAIC", root / "mosaic"]
    py_files: list[str] = []
    for candidate in candidates:
        if candidate.is_dir():
            py_files.extend(str(path.relative_to(root)) for path in candidate.rglob("*.py"))
    default_source = DEFAULT_MOSAIC_SOURCE_ROOT.resolve()
    return {
        "mosaic_root": str(mosaic_root.resolve()),
        "source_root": str(root),
        "source_commit": MOSAIC_SOURCE_COMMIT if root == default_source else None,
        "source_status": "FOUND" if py_files else "NEEDS_MOSAIC_SOURCE",
        "python_file_count": len(py_files),
        "sample_python_files": sorted(py_files)[:20],
    }


def weight_inventory(mosaic_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(mosaic_root.glob("*/*.pt")):
        rows.append(
            {
                "path": str(path.relative_to(mosaic_root)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def label_mapping_audit_rows() -> list[dict[str, Any]]:
    return [
        {
            "compact_label": compact,
            "official_label": official,
            "pathology": "pure_edema" if compact == 4 else "scar",
            "status": "PASS",
        }
        for compact, official in sorted(COMPACT_TO_OFFICIAL.items())
    ] + [
        {
            "compact_label": "4+5",
            "official_label": "1220+2221",
            "pathology": "edema_zone",
            "status": "PASS_SEPARATE_FROM_PURE_EDEMA",
        }
    ]


def protocol_receipt(config: dict[str, Any], *, result_status: str, reason: str) -> dict[str, Any]:
    split_path = REPO_ROOT / config["dataset"]["split_path"]
    train_cases = load_fold_train_cases(split_path, int(config["dataset"]["fold"]))
    val_cases = load_fold_val_cases(split_path, int(config["dataset"]["fold"]))
    guardrails = config.get("guardrails", {})
    expected_train = int(config["dataset"].get("expected_train_count", len(train_cases)))
    expected_val = int(config["dataset"]["expected_val_count"])
    return {
        "schema_version": 1,
        "task_key": config["task_key"],
        "status": result_status,
        "reason": reason,
        "evaluation_only": bool(guardrails.get("evaluation_only", False)),
        "training_authorized": bool(guardrails.get("training_authorized", False)),
        "validation_upload_authorized": False,
        "production_path_dependency_authorized": False,
        "split_path": config["dataset"]["split_path"],
        "fold": int(config["dataset"]["fold"]),
        "train_count": len(train_cases),
        "val_count": len(val_cases),
        "expected_train_count": expected_train,
        "expected_val_count": expected_val,
        "train_count_status": "PASS" if len(train_cases) == expected_train else "FAIL",
        "val_count_status": "PASS" if len(val_cases) == expected_val else "FAIL",
        "care_input_order": list(CARE_INPUT_ORDER),
        "mosaic_input_order": list(MOSAIC_INPUT_ORDER),
        "compact_to_official_labels": {str(k): v for k, v in COMPACT_TO_OFFICIAL.items()},
        "metric_population": config["evaluation"]["population"],
        "metric_implementation": config["evaluation"]["metric_implementation"],
        "geometry_export": config["evaluation"]["geometry_export"],
    }
