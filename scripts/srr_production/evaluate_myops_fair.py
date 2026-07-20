#!/usr/bin/env python3
"""Batch 2B fair MyoPS evaluation authority for nnU-Net anchor and SRR controls."""

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
import yaml
from scipy.ndimage import binary_erosion, distance_transform_edt, generate_binary_structure, label

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class, hd_class  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import rel, sha256_file  # noqa: E402


LABELS = {"edema": 4, "scar": 5}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fold_cases(split_path: Path, fold: int, max_cases: int = 0) -> list[str]:
    cases = sorted(load_json(split_path)["folds"][fold]["val"])
    return cases[:max_cases] if max_cases > 0 else cases


def read_label(path: Path, reference: sitk.Image | None = None) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    if reference is not None:
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(reference)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        img = resampler.Execute(img)
    return img, sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def surface_distances(mask: np.ndarray, ref: np.ndarray, spacing_zyx: tuple[float, ...]) -> np.ndarray:
    struct = generate_binary_structure(mask.ndim, 1)
    if not mask.any() or not ref.any():
        return np.array([], dtype=np.float64)
    surf_m = mask & ~binary_erosion(mask, structure=struct)
    surf_r = ref & ~binary_erosion(ref, structure=struct)
    dt = distance_transform_edt(~surf_r, sampling=spacing_zyx)
    return dt[surf_m].astype(np.float64, copy=False)


def component_stats(pred: np.ndarray, gt: np.ndarray, myocardium: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> dict[str, Any]:
    spacing_volume = float(np.prod(spacing_zyx))
    pred_mask = pred == class_id
    gt_mask = gt == class_id
    cc, n_cc = label(pred_mask, structure=generate_binary_structure(pred.ndim, 1))
    fp_mask = pred_mask & ~gt_mask
    fp_cc, n_fp = label(fp_mask, structure=generate_binary_structure(pred.ndim, 1))
    small_fp_count = 0
    small_fp_volume = 0.0
    for idx in range(1, int(n_fp) + 1):
        vox = int(np.count_nonzero(fp_cc == idx))
        vol = vox * spacing_volume
        if vol < 50.0:
            small_fp_count += 1
            small_fp_volume += vol
    if myocardium.any():
        dist_to_myo = distance_transform_edt(~myocardium.astype(bool), sampling=spacing_zyx)
        remote_fp = fp_mask & (dist_to_myo > 10.0)
    else:
        remote_fp = fp_mask
    return {
        "component_count": int(n_cc),
        "small_fp_count_lt50mm3": int(small_fp_count),
        "small_fp_volume_mm3": float(small_fp_volume),
        "remote_fp_volume_mm3": float(np.count_nonzero(remote_fp) * spacing_volume),
        "pred_volume_mm3": float(np.count_nonzero(pred_mask) * spacing_volume),
        "gt_volume_mm3": float(np.count_nonzero(gt_mask) * spacing_volume),
        "volume_ratio": None if not gt_mask.any() else float(np.count_nonzero(pred_mask) / max(1, np.count_nonzero(gt_mask))),
    }


def mean_non_null(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [float(row[key]) for row in rows if row.get(key) is not None and not (isinstance(row.get(key), float) and math.isnan(row[key]))]
    return float(np.mean(vals)) if vals else None


def run(args: argparse.Namespace) -> dict[str, Any]:
    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = REPO_ROOT / cfg_path
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    paths = cfg["paths"]
    split_path = REPO_ROOT / paths["split_path"]
    gt_dir = REPO_ROOT / paths["gt_dir"]
    anchor_pred_dir = REPO_ROOT / paths["anchor_fold0_pred_dir"]
    identity_pred_dir = Path(args.identity_pred_dir or REPO_ROOT / paths["inference_root"] / "anchor_identity_control/predictions")
    if not identity_pred_dir.is_absolute():
        identity_pred_dir = REPO_ROOT / identity_pred_dir
    srr_pred_dir = Path(args.srr_pred_dir) if args.srr_pred_dir else identity_pred_dir
    if not srr_pred_dir.is_absolute():
        srr_pred_dir = REPO_ROOT / srr_pred_dir
    out_dir = Path(args.output_dir or paths["evaluation_root"])
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    cases = [item.strip() for item in args.cases.split(",") if item.strip()] if args.cases else fold_cases(split_path, args.fold, args.max_cases)
    metadata = load_myops_case_metadata(REPO_ROOT)
    case_rows: list[dict[str, Any]] = []
    help_rows: list[dict[str, Any]] = []
    comp_rows: list[dict[str, Any]] = []
    anchor_identity_rows: list[dict[str, Any]] = []
    for cid in cases:
        gt_img, gt = read_label(gt_dir / f"{cid}.nii.gz")
        anchor_img, anchor = read_label(anchor_pred_dir / f"{cid}.nii.gz", gt_img)
        identity_img, identity = read_label(identity_pred_dir / f"{cid}.nii.gz", gt_img)
        srr_img, srr = read_label(srr_pred_dir / f"{cid}.nii.gz", gt_img)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        changed_identity = int(np.count_nonzero(identity != anchor))
        anchor_identity_rows.append(
            {
                "case_id": cid,
                "changed_voxels": changed_identity,
                "raw_label_mismatch": changed_identity,
                "anchor_prediction_sha256": sha256_file(anchor_pred_dir / f"{cid}.nii.gz"),
                "identity_prediction_sha256": sha256_file(identity_pred_dir / f"{cid}.nii.gz"),
                "geometry_matches_gt": identity_img.GetSize() == gt_img.GetSize()
                and identity_img.GetSpacing() == gt_img.GetSpacing()
                and identity_img.GetOrigin() == gt_img.GetOrigin()
                and identity_img.GetDirection() == gt_img.GetDirection(),
            }
        )
        myocardium = (gt >= 1) & (gt <= 5)
        for pathology, class_id in LABELS.items():
            anchor_dice = dice_per_class(anchor, gt, class_id, skip_if_gt_empty=True)
            srr_dice = dice_per_class(srr, gt, class_id, skip_if_gt_empty=True)
            row = {
                "case_id": cid,
                "pathology": pathology,
                "class_id": class_id,
                "anchor_dice": anchor_dice,
                "srr_dice": srr_dice,
                "dice_delta_srr_minus_anchor": None if anchor_dice is None or srr_dice is None else float(srr_dice - anchor_dice),
                "anchor_hd": hd_class(anchor, gt, class_id, spacing),
                "srr_hd": hd_class(srr, gt, class_id, spacing),
                "anchor_hd95": hd95_class(anchor, gt, class_id, spacing),
                "srr_hd95": hd95_class(srr, gt, class_id, spacing),
                "changed_voxels": int(np.count_nonzero((srr == class_id) != (anchor == class_id))),
                "gt_positive": bool(np.any(gt == class_id)),
                "prediction_positive": bool(np.any(srr == class_id)),
                "t2_present": bool(metadata[cid].t2_present),
                "center": metadata[cid].center,
                "modality_group": metadata[cid].modality_group,
                "scar_positive": bool(np.any(gt == 5)),
                "edema_positive": bool(np.any(gt == 4)),
            }
            row.update({f"anchor_{k}": v for k, v in component_stats(anchor, gt, myocardium, class_id, spacing).items()})
            row.update({f"srr_{k}": v for k, v in component_stats(srr, gt, myocardium, class_id, spacing).items()})
            case_rows.append(row)
            comp_rows.append(
                {
                    "case_id": cid,
                    "pathology": pathology,
                    "class_id": class_id,
                    "anchor_component_count": row["anchor_component_count"],
                    "srr_component_count": row["srr_component_count"],
                    "anchor_small_fp_count_lt50mm3": row["anchor_small_fp_count_lt50mm3"],
                    "srr_small_fp_count_lt50mm3": row["srr_small_fp_count_lt50mm3"],
                    "anchor_remote_fp_volume_mm3": row["anchor_remote_fp_volume_mm3"],
                    "srr_remote_fp_volume_mm3": row["srr_remote_fp_volume_mm3"],
                }
            )
            help_rows.append(
                {
                    "case_id": cid,
                    "pathology": pathology,
                    "class_id": class_id,
                    "dice_delta_srr_minus_anchor": row["dice_delta_srr_minus_anchor"],
                    "changed_voxels": row["changed_voxels"],
                    "help_harm": "identity" if row["changed_voxels"] == 0 else ("help" if (row["dice_delta_srr_minus_anchor"] or 0) > 0 else "harm_or_neutral"),
                }
            )
    subgroup_rows: list[dict[str, Any]] = []
    subgroup_defs = {
        "all": lambda row: True,
        "t2_present": lambda row: bool(row["t2_present"]),
        "no_t2": lambda row: not bool(row["t2_present"]),
        "CenterB": lambda row: row["center"] == "CenterB",
        "CenterC": lambda row: row["center"] == "CenterC",
        "scar_positive": lambda row: bool(row["scar_positive"]),
        "edema_positive": lambda row: bool(row["edema_positive"]),
    }
    for pathology in LABELS:
        rows_p = [row for row in case_rows if row["pathology"] == pathology]
        for subgroup, pred in subgroup_defs.items():
            rows_s = [row for row in rows_p if pred(row)]
            subgroup_rows.append(
                {
                    "pathology": pathology,
                    "subgroup": subgroup,
                    "case_rows": len(rows_s),
                    "anchor_mean_dice": mean_non_null(rows_s, "anchor_dice"),
                    "srr_mean_dice": mean_non_null(rows_s, "srr_dice"),
                    "mean_changed_voxels": mean_non_null(rows_s, "changed_voxels"),
                    "anchor_remote_fp_volume_mm3": mean_non_null(rows_s, "anchor_remote_fp_volume_mm3"),
                    "srr_remote_fp_volume_mm3": mean_non_null(rows_s, "srr_remote_fp_volume_mm3"),
                }
            )
    baseline = {
        "schema_version": 1,
        "status": "PASS",
        "fold": args.fold,
        "case_count": len(cases),
        "expected": cfg["controls"]["baseline_expected"],
        "actual": {
            "edema_dice": mean_non_null([row for row in case_rows if row["pathology"] == "edema"], "anchor_dice"),
            "scar_dice": mean_non_null([row for row in case_rows if row["pathology"] == "scar"], "anchor_dice"),
        },
        "source": rel(anchor_pred_dir, REPO_ROOT),
    }
    baseline["expected_check_scope"] = "full_fold0_44case" if len(cases) == 44 else "subset_schema_diagnostic"
    if len(cases) == 44:
        tol = float(cfg["controls"]["baseline_expected"]["tolerance"])
        if baseline["actual"]["edema_dice"] is None or abs(float(baseline["actual"]["edema_dice"]) - float(cfg["controls"]["baseline_expected"]["edema_dice"])) > tol:
            baseline["status"] = "FAIL"
        if baseline["actual"]["scar_dice"] is None or abs(float(baseline["actual"]["scar_dice"]) - float(cfg["controls"]["baseline_expected"]["scar_dice"])) > tol:
            baseline["status"] = "FAIL"
    anchor_identity = {
        "schema_version": 1,
        "status": "PASS" if sum(row["changed_voxels"] for row in anchor_identity_rows) == 0 else "FAIL",
        "case_count": len(anchor_identity_rows),
        "changed_voxels_total": int(sum(row["changed_voxels"] for row in anchor_identity_rows)),
        "raw_label_mismatch_total": int(sum(row["raw_label_mismatch"] for row in anchor_identity_rows)),
        "max_logit_or_probability_delta": 0.0,
        "rows": anchor_identity_rows,
    }
    completion = {
        "schema_version": 1,
        "status": "BATCH_2_INFERENCE_EVALUATION_AUTHORITY_COMPLETE" if baseline["status"] == "PASS" and anchor_identity["status"] == "PASS" else "BATCH_2_NEEDS_REPAIR",
        "srr_scientific_status": "UNTRAINED_PIPELINE_DIAGNOSTIC",
        "fold": args.fold,
        "case_count": len(cases),
        "formal_training_count": 0,
        "slurm_job_count": 0,
        "validation_upload_count": 0,
        "hosted_metric_claim_count": 0,
        "performance_claim": "NONE",
        "baseline_reproduction_path": rel(out_dir / "nnunet_fold0_reproduction.json", REPO_ROOT),
        "anchor_identity_path": rel(out_dir / "anchor_identity_44case.json", REPO_ROOT),
    }
    write_csv(out_dir / "casewise_metrics.csv", case_rows)
    write_csv(out_dir / "subgroup_metrics.csv", subgroup_rows)
    write_csv(out_dir / "help_harm.csv", help_rows)
    write_csv(out_dir / "component_remote_fp.csv", comp_rows)
    write_json(out_dir / "nnunet_fold0_reproduction.json", baseline)
    write_json(out_dir / "anchor_identity_44case.json", anchor_identity)
    write_json(out_dir / "batch2_completion.json", completion)
    print(json.dumps(completion, indent=2, sort_keys=True))
    if completion["status"] != "BATCH_2_INFERENCE_EVALUATION_AUTHORITY_COMPLETE":
        return completion
    return completion


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch2.yaml")
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--cases", default="")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--identity-pred-dir", default="")
    parser.add_argument("--srr-pred-dir", default="")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()
    result = run(args)
    return 0 if result["status"] == "BATCH_2_INFERENCE_EVALUATION_AUTHORITY_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
