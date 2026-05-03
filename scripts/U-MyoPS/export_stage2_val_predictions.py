#!/usr/bin/env python3
"""Export U-MyoPS Stage2 validation predictions to CARE compact labels for unified evaluation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import SimpleITK as sitk
import numpy as np


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_stage2_task_name(base_task: str, fold: int, per_fold: bool) -> str:
    return f"{base_task}_fold{fold}" if per_fold else base_task


def val_case_ids(protocol_json: Path, fold: int) -> list[str]:
    with protocol_json.open(encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data["folds"][fold]["val"])


def find_prediction(src_dir: Path, case_id: str) -> Path:
    exact = src_dir / f"{case_id}.nii.gz"
    if exact.is_file():
        return exact
    matches = sorted(src_dir.glob(f"*{case_id}*.nii.gz"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"Could not uniquely resolve prediction for {case_id} in {src_dir}")


def remap_to_care(pred_img: sitk.Image) -> sitk.Image:
    arr = sitk.GetArrayFromImage(pred_img)
    out = np.zeros(arr.shape, dtype=np.uint8)
    out[arr == 1] = 4
    out[arr == 2] = 5
    img = sitk.GetImageFromArray(out)
    img.CopyInformation(pred_img)
    return img


def main() -> None:
    ap = argparse.ArgumentParser(description="Export U-MyoPS Stage2 validation predictions for unified evaluation")
    ap.add_argument("--fold", type=int, required=True)
    ap.add_argument("--base-task-name", type=str, default="Task901_CARE_UmyopsPathology")
    ap.add_argument("--per-fold-task", action="store_true", default=False)
    ap.add_argument("--trainer", type=str, default="nnUNetTrainerPSNV8")
    ap.add_argument("--dim", type=str, default="2d")
    ap.add_argument("--protocol-json", type=Path, default=repo_root() / "data" / "benchmarks" / "protocol" / "splits_MyoPS.json")
    ap.add_argument("--results-root", type=Path, default=repo_root() / "third_party" / "U-MyoPS_myops" / "outputs" / "nnunet" / "output" / "nnUNet")
    ap.add_argument("--output-dir", type=Path, default=None)
    args = ap.parse_args()

    task_name = resolve_stage2_task_name(args.base_task_name, args.fold, args.per_fold_task)
    src_dir = args.results_root / args.dim / task_name / f"{args.trainer}__nnUNetPlansv2.1" / f"fold_{args.fold}" / "validation_raw"
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Missing validation_raw for fold {args.fold}: {src_dir}")

    out_dir = args.output_dir or repo_root() / "results" / "predictions" / "U-MyoPS" / f"fold_{args.fold}"
    out_dir.mkdir(parents=True, exist_ok=True)

    for case_id in val_case_ids(args.protocol_json, args.fold):
        pred_path = find_prediction(src_dir, case_id)
        pred_img = sitk.ReadImage(str(pred_path))
        sitk.WriteImage(remap_to_care(pred_img), str(out_dir / f"{case_id}.nii.gz"))
        print(f"Wrote {out_dir / f'{case_id}.nii.gz'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI wrapper
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
