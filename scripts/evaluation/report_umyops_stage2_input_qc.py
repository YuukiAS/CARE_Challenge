#!/usr/bin/env python3
"""Input/prior QC for U-MyoPS Stage2 fold0 tasks."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import SimpleITK as sitk


CHANNELS = {
    0: "prior",
    1: "c0",
    2: "t2",
    3: "lge",
}

FOCUS_CASES = [
    "Case2002",
    "Case2007",
    "Case2020",
    "Case2031",
    "Case2033",
    "Case3004",
    "Case3012",
    "Case3040",
    "Case3044",
    "Case7005",
    "Case8021",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def read_arr(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    return img, sitk.GetArrayFromImage(img)


def mask_for(arr: np.ndarray, cls: int) -> np.ndarray:
    if cls == 4:
        return (arr == 4) | (arr == 1220)
    if cls == 5:
        return (arr == 5) | (arr == 2221)
    return arr == cls


def dice(a: np.ndarray, b: np.ndarray) -> float:
    aa = a.astype(bool)
    bb = b.astype(bool)
    denom = int(aa.sum() + bb.sum())
    if denom == 0:
        return 1.0
    return float(2 * np.logical_and(aa, bb).sum() / denom)


def geometry_match(a: sitk.Image, b: sitk.Image) -> bool:
    return (
        a.GetSize() == b.GetSize()
        and np.allclose(a.GetSpacing(), b.GetSpacing(), atol=1e-5)
        and np.allclose(a.GetOrigin(), b.GetOrigin(), atol=1e-5)
        and np.allclose(a.GetDirection(), b.GetDirection(), atol=1e-5)
    )


def stats(arr: np.ndarray, support: np.ndarray) -> dict[str, float | int | None]:
    vals = arr[support.astype(bool)]
    if vals.size == 0:
        return {"support_voxels": 0, "min": None, "mean": None, "max": None, "std": None}
    return {
        "support_voxels": int(vals.size),
        "min": float(vals.min()),
        "mean": float(vals.mean()),
        "max": float(vals.max()),
        "std": float(vals.std()),
    }


def subject_meta_by_case(staged_root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for meta_path in staged_root.glob("*/subject_meta.json"):
        meta = read_json(meta_path)
        out[meta["case_id"]] = meta
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Report Stage2 input/prior QC for U-MyoPS fold0.")
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--task-name", default="Task901_CARE_UmyopsPathology_fold0")
    ap.add_argument("--pred-dir", type=Path, default=repo_root() / "results/predictions/U-MyoPS_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/fold_0")
    ap.add_argument("--split-json", type=Path, default=repo_root() / "data/benchmarks/protocol/splits_MyoPS.json")
    ap.add_argument("--gt-dir", type=Path, default=repo_root() / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr")
    ap.add_argument("--raw-root", type=Path, default=repo_root() / "third_party/U-MyoPS_myops/outputs/nnunet/raw/nnUNet_raw_data")
    ap.add_argument("--staged-root", type=Path, default=repo_root() / "data/benchmarks/U-MyoPS/gen_ZS_unaligned/data")
    ap.add_argument("--out-dir", type=Path, default=repo_root() / "results/metrics/unified/U-MyoPS_stage2_input_qc/fold_0")
    args = ap.parse_args()

    image_dir = args.raw_root / args.task_name / "imagesTr"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    val_cases = sorted(read_json(args.split_json)["folds"][args.fold]["val"])
    meta = subject_meta_by_case(args.staged_root)
    focus = set(FOCUS_CASES)

    channel_rows = []
    case_rows = []
    for case_id in val_cases:
        gt_img, gt = read_arr(args.gt_dir / f"{case_id}.nii.gz")
        pred_img, pred = read_arr(args.pred_dir / f"{case_id}.nii.gz") if (args.pred_dir / f"{case_id}.nii.gz").is_file() else (None, None)
        prior_img, prior = read_arr(image_dir / f"{case_id}_0000.nii.gz")
        prior_support = prior != 0
        gt_myo_support = (gt != 0)
        gt_pathology = mask_for(gt, 4) | mask_for(gt, 5)
        mods = meta[case_id]["modalities_present"]
        pred_scar = int(mask_for(pred, 5).sum()) if pred is not None else None
        row = {
            "case": case_id,
            "focus_case": case_id in focus,
            "modalities_present": json.dumps(mods, sort_keys=True),
            "complete_modalities": bool(mods.get("c0") and mods.get("t2") and mods.get("de")),
            "prior_nonzero_voxels": int(prior_support.sum()),
            "prior_gt_support_dice": dice(prior_support, gt_myo_support),
            "prior_gt_pathology_overlap_voxels": int(np.logical_and(prior_support, gt_pathology).sum()),
            "gt_scar_voxels": int(mask_for(gt, 5).sum()),
            "pred_scar_voxels": pred_scar,
        }
        case_rows.append(row)

        for idx, name in CHANNELS.items():
            img, arr = read_arr(image_dir / f"{case_id}_{idx:04d}.nii.gz")
            st = stats(arr.astype(np.float64), prior_support)
            channel_rows.append(
                {
                    "case": case_id,
                    "focus_case": case_id in focus,
                    "channel": name,
                    "geometry_match_gt": geometry_match(img, gt_img),
                    "nonzero_voxels": int(np.count_nonzero(arr)),
                    "support_voxels": st["support_voxels"],
                    "support_min": st["min"],
                    "support_mean": st["mean"],
                    "support_max": st["max"],
                    "support_std": st["std"],
                    "modalities_present": json.dumps(mods, sort_keys=True),
                }
            )

    with (args.out_dir / "case_qc.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(case_rows[0].keys()))
        writer.writeheader()
        writer.writerows(case_rows)
    with (args.out_dir / "channel_qc.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(channel_rows[0].keys()))
        writer.writeheader()
        writer.writerows(channel_rows)

    focus_rows = [r for r in case_rows if r["focus_case"]]
    lines = [
        "# U-MyoPS Stage2 input/prior QC",
        "",
        f"Task: `{args.task_name}`",
        f"Predictions: `{args.pred_dir}`",
        "",
        "| case | complete | prior vox | prior/support Dice | prior/pathology overlap | pred scar | GT scar | modalities |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in focus_rows:
        lines.append(
            f"| {row['case']} | {int(row['complete_modalities'])} | {row['prior_nonzero_voxels']} | "
            f"{row['prior_gt_support_dice']:.4f} | {row['prior_gt_pathology_overlap_voxels']} | "
            f"{row['pred_scar_voxels']} | {row['gt_scar_voxels']} | {row['modalities_present']} |"
        )
    lines += ["", "## Focus Case Channel Nonzero Counts", "", "| case | prior | c0 | t2 | lge |", "| --- | ---: | ---: | ---: | ---: |"]
    by_case = {}
    for row in channel_rows:
        by_case.setdefault(row["case"], {})[row["channel"]] = row
    for case_id in FOCUS_CASES:
        if case_id not in by_case:
            continue
        lines.append(
            f"| {case_id} | {by_case[case_id]['prior']['nonzero_voxels']} | "
            f"{by_case[case_id]['c0']['nonzero_voxels']} | {by_case[case_id]['t2']['nonzero_voxels']} | "
            f"{by_case[case_id]['lge']['nonzero_voxels']} |"
        )
    (args.out_dir / "input_qc.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote Stage2 input QC to {args.out_dir}")


if __name__ == "__main__":
    main()
