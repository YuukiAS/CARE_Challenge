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
from scipy import ndimage

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.data.care_ase_splits import PREPROCESSED_REL, SPLITS_REL, build_care_ase_case_roles


DEFAULT_STOCK_OOF_ANCHOR_MANIFEST = REPO_ROOT / "results/20260727_care_dg_dual_pathology_validation/nnunet_oof_anchor_manifest.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_seg(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])[0].astype(np.uint8, copy=False)


def read_prediction_from_roots(case_id: str, roots: list[Path]) -> tuple[np.ndarray, str, str, dict[str, Any]]:
    for root in roots:
        for suffix in (".nii.gz", ".npz", ".npy"):
            path = root / f"{case_id}{suffix}"
            if not path.is_file():
                continue
            meta: dict[str, Any] = {"source_kind": suffix}
            if suffix == ".nii.gz":
                image = nib.load(str(path))
                pred = np.asarray(image.get_fdata()).astype(np.uint8)
                meta["affine"] = np.asarray(image.affine).round(8).tolist()
                meta["header_zooms"] = [float(v) for v in image.header.get_zooms()[:3]]
            elif suffix == ".npz":
                data = np.load(path)
                key = "prediction" if "prediction" in data else list(data.keys())[0]
                pred = np.asarray(data[key]).astype(np.uint8)
                meta["array_key"] = key
            else:
                pred = np.asarray(np.load(path)).astype(np.uint8)
            return pred, str(path), sha256_file(path), meta
    raise FileNotFoundError(f"no held-out stock prediction found for {case_id}")


def load_anchor_entries(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"canonical stock nnU-Net OOF anchor manifest is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    return {str(row["case_id"]): row for row in entries if row.get("prediction_exists")}


def read_prediction_from_anchor(case_id: str, entries: dict[str, dict[str, Any]]) -> tuple[np.ndarray, str, str, dict[str, Any]]:
    if case_id not in entries:
        raise FileNotFoundError(f"case {case_id} is missing from canonical stock nnU-Net OOF anchor manifest")
    entry = entries[case_id]
    path = REPO_ROOT / str(entry["prediction_path"])
    image = nib.load(str(path))
    pred = np.asarray(image.get_fdata()).astype(np.uint8)
    return pred, str(path), str(entry.get("prediction_sha256") or sha256_file(path)), {
        "source_kind": "canonical_stock_nnunet_oof_anchor_manifest",
        "source_stock_fold": int(entry["source_fold"]),
        "affine": np.asarray(image.affine).round(8).tolist(),
        "header_zooms": [float(v) for v in image.header.get_zooms()[:3]],
        "anchor_probability_sha256": entry.get("probability_sha256"),
    }


def bind_prediction_to_preprocessed_grid(gt: np.ndarray, pred: np.ndarray, *, source_meta: dict[str, Any], preprocessed_geometry: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
    if pred.shape == gt.shape:
        return pred, {
            "binding": "exact_preprocessed_grid_shape_match",
            "source_prediction_shape": list(pred.shape),
            "preprocessed_shape": list(gt.shape),
        }
    if pred.ndim == 3 and pred.shape == (gt.shape[2], gt.shape[1], gt.shape[0]):
        converted = np.transpose(pred, (2, 1, 0))
        return converted, {
            "binding": "nifti_xyz_to_preprocessed_zyx_shape_match",
            "source_prediction_shape": list(pred.shape),
            "preprocessed_shape": list(gt.shape),
            "axis_transform": [2, 1, 0],
            "no_min_shape_crop": True,
        }
    raise RuntimeError(
        "stock OOF prediction is not already bound to the preprocessed grid. "
        "CARE-ASE R2 forbids min(shape) crops and ad hoc ndimage.zoom; provide a canonical "
        "patient-held-out stock nnU-Net OOF array in preprocessed-grid shape or an exact xyz->zyx "
        f"shape match. prediction_shape={tuple(pred.shape)} preprocessed_shape={tuple(gt.shape)} "
        f"source_meta={source_meta} preprocessed_geometry={preprocessed_geometry}"
    )


def load_preprocessed_geometry(preprocessed: Path, case_id: str, shape: tuple[int, int, int]) -> dict[str, Any]:
    props_path = preprocessed / f"{case_id}.pkl"
    spacing = (1.0, 1.0, 1.0)
    if props_path.is_file():
        import pickle

        with props_path.open("rb") as f:
            props = pickle.load(f)
        spacing = tuple(float(v) for v in props.get("spacing", spacing))
    return {"shape_zyx": list(shape), "spacing_zyx": list(spacing)}


def sample_coords(mask: np.ndarray, *, key: str, limit: int) -> list[list[int]]:
    coords = np.argwhere(mask)
    if len(coords) == 0:
        return []
    order = np.argsort([hashlib.sha256(f"{key}|{int(z)}|{int(y)}|{int(x)}".encode("utf-8")).hexdigest() for z, y, x in coords])
    coords = coords[order[: int(limit)]]
    return [[int(z), int(y), int(x)] for z, y, x in coords]


def _component_masks(mask: np.ndarray) -> list[np.ndarray]:
    labeled, count = ndimage.label(mask.astype(bool), structure=np.ones((3, 3, 3), dtype=np.uint8))
    return [labeled == idx for idx in range(1, int(count) + 1)]


def _component_metric_targets(gt_mask: np.ndarray, pred_mask: np.ndarray, *, threshold: float, mode: str) -> tuple[np.ndarray, list[dict[str, Any]]]:
    target = np.zeros_like(gt_mask if mode == "fn_recall" else pred_mask, dtype=bool)
    rows = []
    components = _component_masks(gt_mask if mode == "fn_recall" else pred_mask)
    for idx, comp in enumerate(components, start=1):
        denom = int(comp.sum())
        if denom <= 0:
            continue
        overlap = int((comp & (pred_mask if mode == "fn_recall" else gt_mask)).sum())
        value = float(overlap / max(denom, 1))
        if value <= threshold:
            target |= comp
            rows.append({"component_id": idx, "denominator_voxels": denom, "overlap_voxels": overlap, "metric_value": value, "threshold": threshold})
    return target, rows


def _small_components(mask: np.ndarray, spacing: tuple[float, float, float], *, max_volume_mm3: float = 1000.0) -> tuple[np.ndarray, list[dict[str, Any]]]:
    out = np.zeros_like(mask, dtype=bool)
    rows = []
    voxel_volume = float(np.prod(np.asarray(spacing, dtype=np.float64)))
    for idx, comp in enumerate(_component_masks(mask), start=1):
        volume = float(comp.sum() * voxel_volume)
        if volume < max_volume_mm3:
            out |= comp
            rows.append({"component_id": idx, "volume_mm3": volume, "threshold_mm3": max_volume_mm3})
    return out, rows


def build_case(case_id: str, gt: np.ndarray, pred: np.ndarray, *, spacing: tuple[float, float, float], t2_present: bool, coord_limit: int) -> dict[str, Any]:
    scar_gt = gt == 5
    edema_gt = gt == 4
    scar_pred = pred == 5
    edema_pred = pred == 4
    scar_fn, scar_fn_components = _component_metric_targets(scar_gt, scar_pred, threshold=0.50, mode="fn_recall")
    scar_fp, scar_fp_components = _component_metric_targets(scar_gt, scar_pred, threshold=0.10, mode="fp_precision")
    edema_fn_component, edema_fn_components = _component_metric_targets(edema_gt, edema_pred, threshold=0.50, mode="fn_recall")
    edema_fp, edema_fp_components = _component_metric_targets(edema_gt, edema_pred, threshold=0.10, mode="fp_precision")
    edema_predicted = int(edema_pred.sum())
    edema_gt_voxels = int(edema_gt.sum())
    edema_low_volume = edema_gt if edema_gt_voxels > 0 and (edema_predicted / max(edema_gt_voxels, 1)) <= 0.25 else np.zeros_like(edema_gt, dtype=bool)
    edema_fn = edema_fn_component | edema_low_volume
    scar_small, scar_small_components = _small_components(scar_gt, spacing)
    edema_safe_fp = edema_fp if bool(t2_present) else np.zeros_like(edema_fp, dtype=bool)
    targets = {
        "scar_oof_fn": sample_coords(scar_fn, key=f"{case_id}|scar_fn", limit=coord_limit),
        "scar_oof_fp": sample_coords(scar_fp, key=f"{case_id}|scar_fp", limit=coord_limit),
        "edema_oof_fn_or_low_volume": sample_coords(edema_fn, key=f"{case_id}|edema_fn", limit=coord_limit),
        "edema_safe_fp": sample_coords(edema_safe_fp, key=f"{case_id}|edema_fp", limit=coord_limit),
        "scar_small_component": sample_coords(scar_small, key=f"{case_id}|scar_small", limit=coord_limit),
    }
    return {
        "scar_fp_voxels": int(scar_fp.sum()),
        "scar_fn_voxels": int(scar_fn.sum()),
        "edema_fp_voxels": int(edema_safe_fp.sum()),
        "edema_fn_voxels": int(edema_fn.sum()),
        "oof_definitions": {
            "scar_fn_component_recall_lte": 0.50,
            "scar_fp_component_precision_lte": 0.10,
            "edema_fn_component_recall_lte": 0.50,
            "edema_low_volume_predicted_over_gt_lte": 0.25,
            "edema_safe_fp_component_precision_lte": 0.10,
            "edema_safe_fp_t2_present_only": True,
            "small_component_volume_mm3_lt": 1000.0,
        },
        "component_receipts": {
            "scar_fn": scar_fn_components,
            "scar_fp": scar_fp_components,
            "edema_fn": edema_fn_components,
            "edema_safe_fp": edema_fp_components if bool(t2_present) else [],
            "scar_small_component": scar_small_components,
        },
        "targets": targets,
        "target_coordinate_counts": {name: len(coords) for name, coords in targets.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--anchor-manifest", type=Path, default=DEFAULT_STOCK_OOF_ANCHOR_MANIFEST)
    parser.add_argument("--stock-pred-root", type=Path, action="append", default=[])
    parser.add_argument("--coord-limit", type=int, default=128)
    args = parser.parse_args()

    roots = [p.resolve() for p in args.stock_pred_root]
    if roots:
        raise RuntimeError("CARE-ASE R2 hard-negative source must be canonical stock nnU-Net OOF anchor manifest; --stock-pred-root is forbidden")
    anchor_entries = load_anchor_entries(args.anchor_manifest.resolve())
    splits = json.loads((REPO_ROOT / SPLITS_REL).read_text(encoding="utf-8"))
    fold_train = {idx: {str(case_id) for case_id in split["train"]} for idx, split in enumerate(splits)}
    stock_manifest = json.loads(args.anchor_manifest.read_text(encoding="utf-8")) if args.anchor_manifest.is_file() else {}
    stock_checkpoints = stock_manifest.get("checkpoints", {})
    metadata = load_myops_case_metadata(REPO_ROOT)
    rows = [row for row in build_care_ase_case_roles(REPO_ROOT, args.fold) if row.role == "actual-train"]
    preprocessed = REPO_ROOT / PREPROCESSED_REL
    cases: dict[str, Any] = {}
    prediction_sources: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for row in rows:
        try:
            pred_raw, pred_path, pred_sha, pred_meta = read_prediction_from_anchor(row.case_id, anchor_entries)
        except FileNotFoundError:
            missing.append(row.case_id)
            continue
        gt = read_seg(preprocessed / f"{row.case_id}_seg.b2nd")
        geometry = load_preprocessed_geometry(preprocessed, row.case_id, tuple(int(v) for v in gt.shape))
        pred, binding = bind_prediction_to_preprocessed_grid(gt, pred_raw, source_meta=pred_meta, preprocessed_geometry=geometry)
        source_fold = int(pred_meta.get("source_stock_fold", -1))
        if source_fold < 0:
            raise RuntimeError(f"source stock fold is unavailable for {row.case_id}; use the canonical anchor manifest or add source fold metadata")
        proof = row.case_id not in fold_train[source_fold]
        if not proof:
            raise RuntimeError(f"stock prediction for {row.case_id} was produced by fold {source_fold}, but the case is in that fold train split")
        spacing = tuple(float(v) for v in geometry["spacing_zyx"])
        cases[row.case_id] = build_case(row.case_id, gt, pred, spacing=spacing, t2_present=bool(metadata[row.case_id].t2_present), coord_limit=args.coord_limit)
        source_ckpt = stock_checkpoints.get(str(source_fold), {}).get("checkpoint_final_sha256") or stock_checkpoints.get(str(source_fold), {}).get("checkpoint_best_sha256")
        prediction_sources[row.case_id] = {
            "case_id": row.case_id,
            "path": pred_path,
            "source_stock_fold": source_fold,
            "source_checkpoint_sha": source_ckpt,
            "source_prediction_sha": pred_sha,
            "proof_case_not_in_source_fold_train": proof,
            "source_geometry": {
                "raw_prediction_shape": list(pred_raw.shape),
                "affine": pred_meta.get("affine"),
                "header_zooms": pred_meta.get("header_zooms"),
            },
            "preprocessed_geometry": geometry,
            "transform_or_exact_array_binding": binding,
        }
    if missing:
        raise RuntimeError(f"missing held-out stock predictions for actual-train cases: {missing[:10]} count={len(missing)}")
    payload = {
        "status": "PASS",
        "fold": int(args.fold),
        "source": "canonical_patient_held_out_stock_nnunet_oof_only",
        "anchor_manifest": str(args.anchor_manifest.resolve()),
        "prediction_root_count": 0,
        "prediction_roots": [],
        "case_count": len(cases),
        "coord_limit_per_target": int(args.coord_limit),
        "forbidden_sources_removed": ["MoSAIC", "SRR", "cascade_prediction_roots"],
        "geometry_policy": "fail_closed_no_min_shape_crop",
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
