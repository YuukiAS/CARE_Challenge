#!/usr/bin/env python3
"""Build leakage-gated CARE component datasets from MoSAIC/nnU-Net OOF evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import binary_erosion, generate_binary_structure
from scipy.ndimage import label as cc_label

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULT_ROOT = REPO_ROOT / "results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1"
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
SCAR = 5
EDEMA = 4


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({k for row in rows for k in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def require_oof_pass(result_root: Path) -> dict[str, Any]:
    audit_path = result_root / "mosaic_oof_no_leakage_audit.json"
    if not audit_path.is_file():
        raise FileNotFoundError(audit_path)
    audit = read_json(audit_path)
    if audit.get("status") != "PASS":
        raise RuntimeError(f"MoSAIC OOF no-leakage audit is not PASS: {audit}")
    if int(audit.get("expected_case_count", -1)) != 220 or int(audit.get("covered_unique_cases", -1)) != 220:
        raise RuntimeError(f"MoSAIC OOF audit is not 220-case complete: {audit}")
    return audit


def gt_hwz(case_id: str, target_shape: tuple[int, int, int] | None = None) -> tuple[np.ndarray, str]:
    arr = sitk.GetArrayFromImage(sitk.ReadImage(str(GT_DIR / f"{case_id}.nii.gz"))).astype(np.int16)
    candidates = [("zyx_raw", arr), ("yxz", np.transpose(arr, (1, 2, 0))), ("xyz", np.transpose(arr, (2, 1, 0)))]
    if target_shape is None:
        return candidates[1][1], candidates[1][0]
    for name, candidate in candidates:
        if tuple(candidate.shape) == target_shape:
            return candidate, name
    for axes in ((0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)):
        candidate = np.transpose(arr, axes)
        if tuple(candidate.shape) == target_shape:
            return candidate, "transpose_" + "".join(str(a) for a in axes)
    raise ValueError(f"cannot orient GT shape {arr.shape} to target {target_shape} for {case_id}")


def orient_prob_to_target(arr: np.ndarray, target_shape: tuple[int, int, int], path: Path) -> tuple[np.ndarray, str]:
    """Orient a 3D probability array to the target HWZ shape by exact permutation."""
    arr = np.asarray(arr, dtype=np.float32)
    if tuple(arr.shape) == target_shape:
        return arr, "identity"
    for axes in ((0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)):
        candidate = np.transpose(arr, axes)
        if tuple(candidate.shape) == target_shape:
            return candidate, "transpose_" + "".join(str(a) for a in axes)
    raise ValueError(f"cannot orient probability shape {arr.shape} to target {target_shape} in {path}")


def load_nnunet_prob_hwz(path: Path, class_id: int, target_shape: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray, str]:
    data = np.load(path)
    probs = np.asarray(data["probabilities"], dtype=np.float32)
    if probs.ndim != 4:
        raise ValueError(f"unexpected nnU-Net probability shape {probs.shape} in {path}")
    cls, cls_orientation = orient_prob_to_target(probs[class_id], target_shape, path)
    unc_raw = 1.0 - np.max(probs, axis=0)
    uncertainty, unc_orientation = orient_prob_to_target(unc_raw, target_shape, path)
    if unc_orientation != cls_orientation:
        raise ValueError(f"nnU-Net class/uncertainty orientation mismatch in {path}: {cls_orientation} vs {unc_orientation}")
    return cls, uncertainty, cls_orientation


def surface_voxels(mask: np.ndarray) -> int:
    if not mask.any():
        return 0
    struct = generate_binary_structure(mask.ndim, 1)
    return int(np.count_nonzero(mask & ~binary_erosion(mask, structure=struct)))


def bbox_features(coords: np.ndarray) -> dict[str, Any]:
    mn = coords.min(axis=0)
    mx = coords.max(axis=0)
    dims = (mx - mn + 1).astype(np.float32)
    return {
        "bbox_min_hwz": json.dumps([int(v) for v in mn]),
        "bbox_max_hwz": json.dumps([int(v) for v in mx]),
        "bbox_h": float(dims[0]),
        "bbox_w": float(dims[1]),
        "bbox_z": float(dims[2]),
        "bbox_volume_voxels": int(np.prod(dims)),
        "elongation": float(np.max(dims) / max(1.0, float(np.min(dims)))),
    }


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def add_leave_case_out_prototypes(rows: list[dict[str, Any]], feature_cols: list[str]) -> None:
    if not rows:
        return
    matrix = np.asarray([[float(r[c]) for c in feature_cols] for r in rows], dtype=np.float32)
    mu = matrix.mean(axis=0)
    sigma = matrix.std(axis=0)
    sigma[sigma < 1e-6] = 1.0
    z = (matrix - mu) / sigma
    for i, row in enumerate(rows):
        case_id = row["case_id"]
        same_case = np.asarray([r["case_id"] == case_id for r in rows], dtype=bool)
        others = ~same_case
        pos = others & np.asarray([int(r["component_label_positive"]) == 1 for r in rows], dtype=bool)
        neg = others & np.asarray([int(r["component_label_positive"]) == 0 for r in rows], dtype=bool)
        if pos.any():
            pos_proto = z[pos].mean(axis=0)
            row["positive_prototype_similarity"] = cosine(z[i], pos_proto)
            row["positive_prototype_source_count"] = int(pos.sum())
        else:
            row["positive_prototype_similarity"] = 0.0
            row["positive_prototype_source_count"] = 0
        if neg.any():
            neg_proto = z[neg].mean(axis=0)
            row["negative_prototype_similarity"] = cosine(z[i], neg_proto)
            row["negative_prototype_source_count"] = int(neg.sum())
        else:
            row["negative_prototype_similarity"] = 0.0
            row["negative_prototype_source_count"] = 0


def build_scar_dataset(result_root: Path) -> list[dict[str, Any]]:
    manifest = read_csv(result_root / "mosaic_oof_prediction_manifest.csv")
    rows: list[dict[str, Any]] = []
    mask_root = result_root / "component_masks/scar"
    for m in manifest:
        if m.get("pathology_component") != "scar":
            continue
        case_id = m["case_id"]
        fold = int(m["fold"])
        prob_path = REPO_ROOT / m["mosaic_probability"]
        nn_prob_path = REPO_ROOT / m["nnunet_probability"]
        if not prob_path.is_file() or not nn_prob_path.is_file():
            raise FileNotFoundError(f"probability missing for {case_id}: {prob_path} {nn_prob_path}")
        payload = np.load(prob_path)
        final_label = np.asarray(payload["final_label"], dtype=np.int16)
        scar_probs = np.asarray(payload["scar_probs"], dtype=np.float32)
        mosaic_prob = scar_probs[4]
        coarse = np.asarray(payload["coarse_scar"], dtype=np.int16)
        gt, gt_orientation = gt_hwz(case_id, tuple(final_label.shape))
        nn_prob, nn_unc, nnunet_probability_orientation = load_nnunet_prob_hwz(nn_prob_path, SCAR, tuple(final_label.shape))
        if nn_prob.shape != final_label.shape:
            raise ValueError(f"shape mismatch {case_id}: nnunet {nn_prob.shape} mosaic {final_label.shape}")
        if gt.shape != final_label.shape:
            raise ValueError(f"GT shape mismatch {case_id}: gt {gt.shape} mosaic {final_label.shape}")
        comp_mask = final_label == SCAR
        cc, n_cc = cc_label(comp_mask.astype(bool), structure=generate_binary_structure(3, 1))
        gt_scar = gt == SCAR
        anatomy = coarse > 0
        for idx in range(1, n_cc + 1):
            comp = cc == idx
            vox = int(comp.sum())
            if vox <= 0:
                continue
            coords = np.argwhere(comp)
            bbox = bbox_features(coords)
            gt_overlap = int(np.count_nonzero(comp & gt_scar))
            mask_path = mask_root / f"fold{fold}_{case_id}_scar_{idx:03d}.npz"
            mask_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(mask_path, mask=comp.astype(np.uint8))
            surf = surface_voxels(comp)
            bbox_vol = max(1, int(bbox["bbox_volume_voxels"]))
            row = {
                "fold": fold,
                "case_id": case_id,
                "component_id": f"fold{fold}:{case_id}:scar:{idx}",
                "pathology": "scar",
                "component_mask": rel(mask_path),
                "modality_availability": m.get("modality_availability", ""),
                "t2_present": int(m.get("t2_present", 0)),
                "center": m.get("center", ""),
                "gt_path": m.get("gt", ""),
                "gt_orientation": gt_orientation,
                "nnunet_prediction": m.get("nnunet_prediction", ""),
                "mosaic_prediction": m.get("mosaic_prediction_compact", ""),
                "nnunet_probability_orientation": nnunet_probability_orientation,
                "nnunet_probability_mean": float(np.mean(nn_prob[comp])),
                "nnunet_probability_max": float(np.max(nn_prob[comp])),
                "nnunet_uncertainty_mean": float(np.mean(nn_unc[comp])),
                "mosaic_probability_mean": float(np.mean(mosaic_prob[comp])),
                "mosaic_probability_max": float(np.max(mosaic_prob[comp])),
                "anatomy_overlap": float(np.count_nonzero(comp & anatomy) / max(1, vox)),
                "size_voxels": vox,
                "log_size": float(math.log1p(vox)),
                "surface_voxels": surf,
                "surface_to_volume": float(surf / max(1, vox)),
                "fill_fraction": float(vox / bbox_vol),
                "gt_overlap_voxels": gt_overlap,
                "gt_relationship": "overlaps_scar_gt" if gt_overlap > 0 else "no_scar_gt_overlap",
                "component_label_positive": int(gt_overlap > 0),
                **bbox,
            }
            rows.append(row)
    feature_cols = [
        "nnunet_probability_mean",
        "nnunet_uncertainty_mean",
        "mosaic_probability_mean",
        "anatomy_overlap",
        "log_size",
        "surface_to_volume",
        "fill_fraction",
        "elongation",
    ]
    add_leave_case_out_prototypes(rows, feature_cols)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--scar-only", action="store_true")
    args = parser.parse_args()
    result_root = args.result_root if args.result_root.is_absolute() else REPO_ROOT / args.result_root
    audit = require_oof_pass(result_root)
    scar_rows = build_scar_dataset(result_root)
    out_dir = result_root / "component_dataset"
    write_csv(out_dir / "scar_components.csv", scar_rows)
    receipt = {
        "status": "PASS" if scar_rows else "FAIL_EMPTY_SCAR_COMPONENTS",
        "oof_audit_status": audit.get("status"),
        "oof_case_count": audit.get("covered_unique_cases"),
        "scar_component_count": len(scar_rows),
        "feature_columns": [
            "nnunet_probability_mean",
            "mosaic_probability_mean",
            "nnunet_uncertainty_mean",
            "anatomy_overlap",
            "size_voxels",
            "surface_to_volume",
            "fill_fraction",
            "positive_prototype_similarity",
            "negative_prototype_similarity",
        ],
        "edema_dataset_status": "NOT_BUILT_IN_SCAR_ONLY_STAGE",
        "no_t2_as_edema_negative": True,
    }
    write_json(out_dir / "component_dataset_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
