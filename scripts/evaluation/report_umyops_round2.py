#!/usr/bin/env python3
"""Grouped fold-0 diagnostics for U-MyoPS explicit checkpoint exports."""
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


def mask_for(arr: np.ndarray, cls: int) -> np.ndarray:
    if cls == 4:
        return (arr == 4) | (arr == 1220)
    if cls == 5:
        return (arr == 5) | (arr == 2221)
    return arr == cls


def dice(pred: np.ndarray, gt: np.ndarray, cls: int) -> float:
    p = mask_for(pred, cls)
    g = mask_for(gt, cls)
    ps = int(p.sum())
    gs = int(g.sum())
    if ps == 0 and gs == 0:
        return 1.0
    if ps + gs == 0:
        return 0.0
    return float(2 * np.logical_and(p, g).sum() / (ps + gs))


def subject_meta_by_case(staged_root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for meta_path in staged_root.glob("*/subject_meta.json"):
        meta = read_json(meta_path)
        meta["_subject_dir"] = str(meta_path.parent)
        out[meta["case_id"]] = meta
    return out


def geometry(img: sitk.Image) -> dict:
    return {
        "size": list(img.GetSize()),
        "spacing": [round(float(x), 6) for x in img.GetSpacing()],
        "origin": [round(float(x), 6) for x in img.GetOrigin()],
        "direction": [round(float(x), 6) for x in img.GetDirection()],
    }


def geometry_match(a: sitk.Image, b: sitk.Image) -> bool:
    return (
        a.GetSize() == b.GetSize()
        and np.allclose(a.GetSpacing(), b.GetSpacing(), atol=1e-5)
        and np.allclose(a.GetOrigin(), b.GetOrigin(), atol=1e-5)
        and np.allclose(a.GetDirection(), b.GetDirection(), atol=1e-5)
    )


def find_one(root: Path, pattern: str) -> Path | None:
    matches = sorted(root.glob(pattern))
    if len(matches) == 1:
        return matches[0]
    return None


def stage1_qc(case_ids: list[str], gt_dir: Path, staged_meta: dict[str, dict], stage1_gen: Path) -> list[dict]:
    rows: list[dict] = []
    for case_id in case_ids:
        meta = staged_meta[case_id]
        subject = Path(meta["_subject_dir"]).name
        gen_dir = stage1_gen / subject
        gt_img, gt = read_arr(gt_dir / f"{case_id}.nii.gz")
        prior_path = find_one(gen_dir, f"*img_de_branch_lab_{case_id}.nii.gz")
        c0_path = find_one(gen_dir, f"*img_c0_assn_img_{case_id}.nii.gz")
        t2_path = find_one(gen_dir, f"*img_t2_assn_img_{case_id}.nii.gz")
        lge_path = find_one(gen_dir, f"*img_de_assn_img_{case_id}.nii.gz")
        row = {
            "case": case_id,
            "subject": subject,
            "modalities_present": json.dumps(meta["modalities_present"], sort_keys=True),
            "gt_geometry": json.dumps(geometry(gt_img), sort_keys=True),
        }
        gt_support = gt != 0
        gt_pathology = mask_for(gt, 4) | mask_for(gt, 5)
        for name, path in (("prior", prior_path), ("c0", c0_path), ("t2", t2_path), ("lge", lge_path)):
            if path is None:
                row[f"{name}_exists"] = "0"
                continue
            img, arr = read_arr(path)
            nonzero = int(np.count_nonzero(arr))
            row[f"{name}_exists"] = "1"
            row[f"{name}_geometry_match_gt"] = "1" if geometry_match(img, gt_img) else "0"
            row[f"{name}_nonzero_voxels"] = nonzero
            if name == "prior":
                prior = arr != 0
                row["prior_gt_support_dice"] = dice(prior.astype(np.uint8), gt_support.astype(np.uint8), 1)
                row["prior_gt_pathology_overlap_voxels"] = int(np.logical_and(prior, gt_pathology).sum())
        rows.append(row)
    return rows


def summarize(values: list[float]) -> dict:
    return {"n": len(values), "mean": float(np.mean(values)) if values else None}


def write_markdown(path: Path, checkpoint: str, grouped: dict, low_cases: list[dict], qc_rows: list[dict]) -> None:
    lines = [
        f"# U-MyoPS fold0 grouped diagnostics ({checkpoint})",
        "",
        "Empty-GT rule: when prediction and GT are both empty for a class, Dice is counted as 1.0.",
        "",
        "| group | n | myops_edema | myops_scar |",
        "| --- | ---: | ---: | ---: |",
    ]
    for group, metrics in grouped.items():
        lines.append(
            f"| {group} | {metrics['n']} | {metrics['myops_edema']} | {metrics['myops_scar']} |"
        )
    lines += ["", "## Lowest Scar Cases", "", "| case | scar_dice | edema_dice | pred_scar | gt_scar | modalities |", "| --- | ---: | ---: | ---: | ---: | --- |"]
    for row in low_cases:
        lines.append(
            f"| {row['case']} | {row['dice_class_5']:.4f} | {row['dice_class_4']:.4f} | "
            f"{row['pred_class_5_voxels']} | {row['gt_class_5_voxels']} | {row['modalities_present']} |"
        )
    lines += ["", "## Stage1 Prior QC", "", "| case | geom_ok | prior_nonzero | prior_support_dice | prior_pathology_overlap | modalities |", "| --- | ---: | ---: | ---: | ---: | --- |"]
    for row in qc_rows:
        lines.append(
            f"| {row['case']} | {row.get('prior_geometry_match_gt', '0')} | "
            f"{row.get('prior_nonzero_voxels', '')} | {float(row.get('prior_gt_support_dice', 0)):.4f} | "
            f"{row.get('prior_gt_pathology_overlap_voxels', '')} | {row['modalities_present']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint-tag", default="model_final_checkpoint")
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--pred-dir", type=Path, default=None)
    ap.add_argument("--gt-dir", type=Path, default=repo_root() / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr")
    ap.add_argument("--split-json", type=Path, default=repo_root() / "data/benchmarks/protocol/splits_MyoPS.json")
    ap.add_argument("--staged-root", type=Path, default=repo_root() / "data/benchmarks/U-MyoPS/gen_ZS_unaligned/data")
    ap.add_argument("--stage1-gen", type=Path, default=repo_root() / "third_party/U-MyoPS_myops/outputs/asn_myo_tps_tps_ZS_unaligned_1.0_fold0/gen_res")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    pred_dir = args.pred_dir or repo_root() / "results/predictions" / f"U-MyoPS_{args.checkpoint_tag}" / f"fold_{args.fold}"
    out_dir = args.out_dir or repo_root() / "results/metrics/unified" / f"U-MyoPS_{args.checkpoint_tag}" / f"fold_{args.fold}"
    out_dir.mkdir(parents=True, exist_ok=True)

    split = read_json(args.split_json)["folds"][args.fold]["val"]
    meta = subject_meta_by_case(args.staged_root)
    per_case = []
    for case_id in sorted(split):
        pred_img, pred = read_arr(pred_dir / f"{case_id}.nii.gz")
        gt_img, gt = read_arr(args.gt_dir / f"{case_id}.nii.gz")
        mods = meta[case_id]["modalities_present"]
        row = {
            "case": case_id,
            "center": meta[case_id].get("center", Path(meta[case_id]["_subject_dir"]).name.split("_")[0]),
            "modalities_present": json.dumps(mods, sort_keys=True),
            "t2_present": bool(mods.get("t2")),
            "complete_modalities": bool(mods.get("c0") and mods.get("t2") and mods.get("de")),
            "geometry_match": geometry_match(pred_img, gt_img),
        }
        for cls in (4, 5):
            row[f"dice_class_{cls}"] = dice(pred, gt, cls)
            row[f"pred_class_{cls}_voxels"] = int(mask_for(pred, cls).sum())
            row[f"gt_class_{cls}_voxels"] = int(mask_for(gt, cls).sum())
            row[f"gt_class_{cls}_positive"] = row[f"gt_class_{cls}_voxels"] > 0
            row[f"empty_gt_class_{cls}_counted_1"] = (
                row[f"gt_class_{cls}_voxels"] == 0 and row[f"pred_class_{cls}_voxels"] == 0
            )
        per_case.append(row)

    groups = {
        "all_cases": per_case,
        "edema_gt_positive_only": [r for r in per_case if r["gt_class_4_positive"]],
        "edema_t2_present_only": [r for r in per_case if r["t2_present"]],
        "scar_gt_positive_only": [r for r in per_case if r["gt_class_5_positive"]],
        "scar_complete_modalities_only": [r for r in per_case if r["complete_modalities"]],
        "scar_missing_modality_only": [r for r in per_case if not r["complete_modalities"]],
    }
    grouped = {}
    for name, rows in groups.items():
        grouped[name] = {
            "n": len(rows),
            "myops_edema": summarize([r["dice_class_4"] for r in rows])["mean"],
            "myops_scar": summarize([r["dice_class_5"] for r in rows])["mean"],
        }

    low_cases = sorted(per_case, key=lambda r: (r["dice_class_5"], -r["gt_class_5_voxels"]))[:10]
    required = {"Case2002", "Case2007", "Case2020", "Case2031", "Case3012", "Case3044"}
    qc_case_ids = sorted({r["case"] for r in low_cases} | required)
    qc_rows = stage1_qc(qc_case_ids, args.gt_dir, meta, args.stage1_gen)

    with (out_dir / "per_case_counts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_case[0].keys()))
        writer.writeheader()
        writer.writerows(per_case)
    with (out_dir / "stage1_prior_qc.csv").open("w", newline="", encoding="utf-8") as f:
        fields = sorted({k for row in qc_rows for k in row.keys()})
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(qc_rows)
    (out_dir / "grouped_metrics.json").write_text(json.dumps(grouped, indent=2), encoding="utf-8")
    write_markdown(out_dir / "grouped_diagnostics.md", args.checkpoint_tag, grouped, low_cases, qc_rows)
    print(f"Wrote grouped U-MyoPS diagnostics to {out_dir}")


if __name__ == "__main__":
    main()
