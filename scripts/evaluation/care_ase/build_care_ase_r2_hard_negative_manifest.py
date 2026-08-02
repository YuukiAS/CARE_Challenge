#!/usr/bin/env python
"""Build CARE-ASE R2 spatial hard-negative manifest for actual-train cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import blosc2
import nibabel as nib
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_ase_splits import PREPROCESSED_REL, build_care_ase_case_roles


DEFAULT_STOCK_PRED_ROOTS = (
    REPO_ROOT / "results/20260629_cascade_teacher_route/revision_signal_seek/variants/nnunet_pathology_teacher_srr_refiner_signal_seek/predictions/nnunet_pathology_teacher_srr_refiner_signal_seek/validation",
    REPO_ROOT / "results/20260629_cascade_teacher_route/revision_postprocess_sweep/variants/nnunet_pathology_teacher_srr_refiner_signal_seek__pathology_overlap_dilate2/predictions/nnunet_pathology_teacher_srr_refiner_signal_seek__pathology_overlap_dilate2/validation",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_seg(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])[0].astype(np.uint8, copy=False)


def read_prediction(case_id: str, roots: list[Path]) -> tuple[np.ndarray, str, str]:
    for root in roots:
        for suffix in (".nii.gz", ".npz", ".npy"):
            path = root / f"{case_id}{suffix}"
            if not path.is_file():
                continue
            if suffix == ".nii.gz":
                pred = np.asarray(nib.load(str(path)).get_fdata()).astype(np.uint8)
            elif suffix == ".npz":
                data = np.load(path)
                key = "prediction" if "prediction" in data else list(data.keys())[0]
                pred = np.asarray(data[key]).astype(np.uint8)
            else:
                pred = np.asarray(np.load(path)).astype(np.uint8)
            return pred, str(path), sha256_file(path)
    raise FileNotFoundError(f"no held-out stock prediction found for {case_id}")


def align(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    shape = tuple(min(int(a.shape[i]), int(b.shape[i])) for i in range(3))
    slices = tuple(slice(0, n) for n in shape)
    return a[slices], b[slices]


def sample_coords(mask: np.ndarray, *, key: str, limit: int) -> list[list[int]]:
    coords = np.argwhere(mask)
    if len(coords) == 0:
        return []
    order = np.argsort([hashlib.sha256(f"{key}|{int(z)}|{int(y)}|{int(x)}".encode("utf-8")).hexdigest() for z, y, x in coords])
    coords = coords[order[: int(limit)]]
    return [[int(z), int(y), int(x)] for z, y, x in coords]


def build_case(case_id: str, gt: np.ndarray, pred: np.ndarray, *, coord_limit: int) -> dict[str, Any]:
    gt, pred = align(gt, pred)
    scar_gt = gt == 5
    edema_gt = gt == 4
    scar_pred = pred == 5
    edema_pred = pred == 4
    scar_fn = scar_gt & ~scar_pred
    scar_fp = scar_pred & ~scar_gt
    edema_fn = edema_gt & ~edema_pred
    edema_fp = edema_pred & ~edema_gt
    targets = {
        "scar_oof_fn": sample_coords(scar_fn, key=f"{case_id}|scar_fn", limit=coord_limit),
        "scar_oof_fp": sample_coords(scar_fp, key=f"{case_id}|scar_fp", limit=coord_limit),
        "edema_oof_fn_or_low_volume": sample_coords(edema_fn, key=f"{case_id}|edema_fn", limit=coord_limit),
        "edema_safe_fp": sample_coords(edema_fp, key=f"{case_id}|edema_fp", limit=coord_limit),
    }
    return {
        "scar_fp_voxels": int(scar_fp.sum()),
        "scar_fn_voxels": int(scar_fn.sum()),
        "edema_fp_voxels": int(edema_fp.sum()),
        "edema_fn_voxels": int(edema_fn.sum()),
        "targets": targets,
        "target_coordinate_counts": {name: len(coords) for name, coords in targets.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--stock-pred-root", type=Path, action="append", default=[])
    parser.add_argument("--coord-limit", type=int, default=128)
    args = parser.parse_args()

    roots = [p.resolve() for p in args.stock_pred_root] or list(DEFAULT_STOCK_PRED_ROOTS)
    rows = [row for row in build_care_ase_case_roles(REPO_ROOT, args.fold) if row.role == "actual-train"]
    preprocessed = REPO_ROOT / PREPROCESSED_REL
    cases: dict[str, Any] = {}
    prediction_sources: dict[str, dict[str, str]] = {}
    missing: list[str] = []
    for row in rows:
        try:
            pred, pred_path, pred_sha = read_prediction(row.case_id, roots)
        except FileNotFoundError:
            missing.append(row.case_id)
            continue
        gt = read_seg(preprocessed / f"{row.case_id}_seg.b2nd")
        cases[row.case_id] = build_case(row.case_id, gt, pred, coord_limit=args.coord_limit)
        prediction_sources[row.case_id] = {"path": pred_path, "sha256": pred_sha}
    if missing:
        raise RuntimeError(f"missing held-out stock predictions for actual-train cases: {missing[:10]} count={len(missing)}")
    payload = {
        "status": "PASS",
        "fold": int(args.fold),
        "source": "actual_train_only_hard_negative_manifest_from_configured_prediction_roots",
        "prediction_root_count": len(roots),
        "prediction_roots": [str(path) for path in roots],
        "case_count": len(cases),
        "coord_limit_per_target": int(args.coord_limit),
        "prediction_sources": prediction_sources,
        "cases": cases,
    }
    payload["payload_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    output = args.output or REPO_ROOT / f"results/20260803_care_ase_r2_full_fidelity_execution/hard_negative_manifest_fold{args.fold}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(output), "case_count": len(cases)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
