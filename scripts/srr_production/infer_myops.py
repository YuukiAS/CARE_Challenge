#!/usr/bin/env python3
"""Batch 2B MyoPS full-volume inference/export authority."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.srr_production.anchor_manifest import build_anchor_manifest, find_anchor_paths, rel, sha256_file  # noqa: E402

SPLIT_NNUNET = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def fold_cases(split_path: Path, fold: int, max_cases: int = 0) -> list[str]:
    cases = sorted(load_json(split_path)["folds"][fold]["val"])
    return cases[:max_cases] if max_cases > 0 else cases


def image_geometry(path: Path) -> dict[str, Any]:
    img = sitk.ReadImage(str(path))
    return {
        "size_xyz": list(img.GetSize()),
        "spacing_xyz": list(img.GetSpacing()),
        "origin_xyz": list(img.GetOrigin()),
        "direction": list(img.GetDirection()),
    }


def copy_prediction_with_reference(pred_path: Path, out_path: Path) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pred_path, out_path)
    return {
        "prediction_sha256": sha256_file(pred_path),
        "output_sha256": sha256_file(out_path),
        "byte_identical": sha256_file(pred_path) == sha256_file(out_path),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = REPO_ROOT / cfg_path
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    paths = cfg["paths"]
    split_path = REPO_ROOT / paths["split_path"]
    raw_root = REPO_ROOT / paths["raw_root"]
    gt_dir = REPO_ROOT / paths["gt_dir"]
    anchor_root = REPO_ROOT / paths["anchor_root"]
    out_root = Path(args.output_root or paths["inference_root"])
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    mode = args.mode
    if mode not in set(cfg["modes"]):
        raise ValueError(f"unsupported inference mode {mode!r}")
    if mode != "anchor_identity_control" and not args.checkpoint and not args.allow_untrained_diagnostic:
        raise ValueError(
            f"{mode} requires --checkpoint, or --allow-untrained-diagnostic to write a zero-step diagnostic receipt"
        )
    case_ids = [item.strip() for item in args.cases.split(",") if item.strip()] if args.cases else fold_cases(split_path, args.fold, args.max_cases)
    manifest = build_anchor_manifest(
        repo_root=REPO_ROOT,
        anchor_root=anchor_root,
        protocol_split=split_path,
        nnunet_split=SPLIT_NNUNET,
        raw_root=raw_root,
        preprocessed_root=PREPROCESSED,
    )
    pred_dir = out_root / mode / "predictions"
    rows: list[dict[str, Any]] = []
    for cid in case_ids:
        source_fold, _prob_path, pred_path = find_anchor_paths(cid, anchor_root)
        gt_path = gt_dir / f"{cid}.nii.gz"
        out_path = pred_dir / f"{cid}.nii.gz"
        copied = copy_prediction_with_reference(pred_path, out_path)
        source_arr = sitk.GetArrayFromImage(sitk.ReadImage(str(pred_path)))
        out_arr = sitk.GetArrayFromImage(sitk.ReadImage(str(out_path)))
        mismatch = int(np.count_nonzero(source_arr != out_arr))
        geom_pred = image_geometry(pred_path)
        geom_out = image_geometry(out_path)
        geom_gt = image_geometry(gt_path)
        rows.append(
            {
                "case_id": cid,
                "mode": mode,
                "source_fold": source_fold,
                "source_prediction_path": rel(pred_path, REPO_ROOT),
                "output_prediction_path": rel(out_path, REPO_ROOT),
                "gt_path": rel(gt_path, REPO_ROOT),
                "raw_label_mismatch": mismatch,
                "changed_voxels": mismatch,
                "byte_identical": copied["byte_identical"],
                "geometry_matches_source": geom_pred == geom_out,
                "geometry_matches_gt": geom_out == geom_gt,
                "prediction_sha256": copied["prediction_sha256"],
                "output_sha256": copied["output_sha256"],
            }
        )
    geometry_csv = out_root / "batch2_geometry_roundtrip.csv"
    with geometry_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    contract = {
        "schema_version": 1,
        "status": "BATCH_2B_INFERENCE_CONTRACT_COMPLETE" if mode == "anchor_identity_control" else "UNTRAINED_PIPELINE_DIAGNOSTIC",
        "mode": mode,
        "fold": args.fold,
        "case_count": len(rows),
        "prediction_dir": rel(pred_dir, REPO_ROOT),
        "geometry_roundtrip_csv": rel(geometry_csv, REPO_ROOT),
        "raw_oof_anchor_manifest_status": manifest["status"],
        "anchor_identity_changed_voxels_total": int(sum(row["changed_voxels"] for row in rows)),
        "raw_label_mismatch_total": int(sum(row["raw_label_mismatch"] for row in rows)),
        "untrained_srr_policy": cfg["controls"]["untrained_srr_policy"],
        "formal_training_count": 0,
        "slurm_job_count": 0,
        "validation_upload_count": 0,
        "hosted_metric_claim_count": 0,
        "notes": (
            "anchor_identity_control copies raw OOF nnU-Net full-volume predictions byte-for-byte"
            if mode == "anchor_identity_control"
            else "no trusted trained SRR checkpoint was provided; output is diagnostic only and must not be interpreted as SRR performance"
        ),
    }
    write_json(out_root / "batch2_inference_contract.json", contract)
    print(json.dumps(contract, indent=2, sort_keys=True))
    return contract


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch2.yaml")
    parser.add_argument("--mode", choices=("anchor_identity_control", "srr_no_anchor_control", "anchor_bounded_srr_correction"), default="anchor_identity_control")
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--cases", default="")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--allow-untrained-diagnostic", action="store_true")
    parser.add_argument("--output-root", default="")
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

