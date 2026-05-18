#!/usr/bin/env python3
"""Oracle-check U-MyoPS Task901 labels against Dataset501 fold GT."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import SimpleITK as sitk


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def read_arr(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    return img, sitk.GetArrayFromImage(img)


def geometry_match(a: sitk.Image, b: sitk.Image) -> bool:
    return (
        a.GetSize() == b.GetSize()
        and np.allclose(a.GetSpacing(), b.GetSpacing(), atol=1e-5)
        and np.allclose(a.GetOrigin(), b.GetOrigin(), atol=1e-5)
        and np.allclose(a.GetDirection(), b.GetDirection(), atol=1e-5)
    )


def mask_for_care(arr: np.ndarray, cls: int) -> np.ndarray:
    if cls == 4:
        return (arr == 4) | (arr == 1220)
    if cls == 5:
        return (arr == 5) | (arr == 2221)
    return arr == cls


def mask_for_stage2(arr: np.ndarray, care_cls: int) -> np.ndarray:
    if care_cls == 4:
        return arr == 1
    if care_cls == 5:
        return arr == 2
    raise ValueError(f"unsupported CARE class for Task901 oracle: {care_cls}")


def dice(pred_mask: np.ndarray, gt_mask: np.ndarray) -> float:
    ps = int(pred_mask.sum())
    gs = int(gt_mask.sum())
    if ps == 0 and gs == 0:
        return 1.0
    if ps + gs == 0:
        return 0.0
    return float(2 * np.logical_and(pred_mask, gt_mask).sum() / (ps + gs))


def subject_meta_by_case(staged_root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for meta_path in staged_root.glob("*/subject_meta.json"):
        meta = read_json(meta_path)
        out[meta["case_id"]] = meta
    return out


def summarize(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare Task901 compact labels against Dataset501 fold GT.")
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--base-task-name", default="Task901_CARE_UmyopsPathology")
    ap.add_argument("--per-fold-task", action="store_true", default=True)
    ap.add_argument("--split-json", type=Path, default=repo_root() / "data/benchmarks/protocol/splits_MyoPS.json")
    ap.add_argument("--stage2-label-dir", type=Path, default=None)
    ap.add_argument("--gt-dir", type=Path, default=repo_root() / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr")
    ap.add_argument("--staged-root", type=Path, default=repo_root() / "data/benchmarks/U-MyoPS/gen_ZS_unaligned/data")
    ap.add_argument("--out-dir", type=Path, default=repo_root() / "results/metrics/unified/U-MyoPS_stage2_oracle/fold_0")
    args = ap.parse_args()

    task_name = f"{args.base_task_name}_fold{args.fold}" if args.per_fold_task else args.base_task_name
    label_dir = args.stage2_label_dir or (
        repo_root()
        / "third_party/U-MyoPS_myops/outputs/nnunet/raw/nnUNet_raw_data"
        / task_name
        / "labelsTr"
    )
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    val_cases = sorted(read_json(args.split_json)["folds"][args.fold]["val"])
    meta = subject_meta_by_case(args.staged_root)
    rows = []
    for case_id in val_cases:
        stage2_img, stage2 = read_arr(label_dir / f"{case_id}.nii.gz")
        gt_img, gt = read_arr(args.gt_dir / f"{case_id}.nii.gz")
        mods = meta[case_id]["modalities_present"]
        row = {
            "case": case_id,
            "modalities_present": json.dumps(mods, sort_keys=True),
            "t2_present": bool(mods.get("t2")),
            "complete_modalities": bool(mods.get("c0") and mods.get("t2") and mods.get("de")),
            "geometry_match": geometry_match(stage2_img, gt_img),
        }
        for care_cls in (4, 5):
            pred_mask = mask_for_stage2(stage2, care_cls)
            gt_mask = mask_for_care(gt, care_cls)
            row[f"dice_class_{care_cls}"] = dice(pred_mask, gt_mask)
            row[f"stage2_class_{care_cls}_voxels"] = int(pred_mask.sum())
            row[f"gt_class_{care_cls}_voxels"] = int(gt_mask.sum())
            row[f"gt_class_{care_cls}_positive"] = bool(gt_mask.sum() > 0)
            row[f"empty_gt_class_{care_cls}_counted_1"] = bool(gt_mask.sum() == 0 and pred_mask.sum() == 0)
        rows.append(row)

    groups = {
        "all_cases": rows,
        "edema_gt_positive_only": [r for r in rows if r["gt_class_4_positive"]],
        "edema_t2_present_only": [r for r in rows if r["t2_present"]],
        "scar_gt_positive_only": [r for r in rows if r["gt_class_5_positive"]],
        "scar_complete_modalities_only": [r for r in rows if r["complete_modalities"]],
    }
    grouped = {
        name: {
            "n": len(group_rows),
            "myops_edema": summarize([r["dice_class_4"] for r in group_rows]),
            "myops_scar": summarize([r["dice_class_5"] for r in group_rows]),
        }
        for name, group_rows in groups.items()
    }

    with (out_dir / "per_case_counts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "grouped_metrics.json").write_text(json.dumps(grouped, indent=2), encoding="utf-8")

    lines = [
        "# U-MyoPS Task901 Stage2 label oracle",
        "",
        "Stage2 labels are remapped logically as `1->4 edema`, `2->5 scar` and compared with Dataset501 fold0 GT.",
        "",
        "| group | n | myops_edema | myops_scar |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, metrics in grouped.items():
        lines.append(f"| {name} | {metrics['n']} | {metrics['myops_edema']} | {metrics['myops_scar']} |")
    lines += ["", "## Geometry", ""]
    geom_bad = [r["case"] for r in rows if not r["geometry_match"]]
    lines.append(f"- geometry mismatches: {geom_bad if geom_bad else 'none'}")
    lines += ["", "## Lowest Scar Oracle Cases", "", "| case | scar_dice | stage2_scar | gt_scar | modalities |", "| --- | ---: | ---: | ---: | --- |"]
    for row in sorted(rows, key=lambda r: (r["dice_class_5"], -r["gt_class_5_voxels"]))[:10]:
        lines.append(
            f"| {row['case']} | {row['dice_class_5']:.4f} | {row['stage2_class_5_voxels']} | "
            f"{row['gt_class_5_voxels']} | {row['modalities_present']} |"
        )
    (out_dir / "grouped_diagnostics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote U-MyoPS Stage2 oracle diagnostics to {out_dir}")


if __name__ == "__main__":
    main()
