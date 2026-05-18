#!/usr/bin/env python3
"""Round6 export-only scar calibration/routing for U-MyoPS fold0.

This script does not train. It compares U-MyoPS Task912 model_best against
nnU-Net501 fold0 predictions, writes per-case diagnostics, and emits calibrated
prediction directories for follow-up unified evaluation.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import deque
from pathlib import Path

import numpy as np
import SimpleITK as sitk


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def read_img(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    arr = sitk.GetArrayFromImage(img).astype(np.uint16, copy=False)
    return img, arr


def write_like(arr: np.ndarray, ref: sitk.Image, path: Path) -> None:
    out = sitk.GetImageFromArray(arr.astype(np.uint16, copy=False))
    out.CopyInformation(ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(out, str(path))


def mask_for(arr: np.ndarray, cls: int) -> np.ndarray:
    if cls == 4:
        return (arr == 4) | (arr == 1220)
    if cls == 5:
        return (arr == 5) | (arr == 2221)
    return arr == cls


def dice_masks(pred: np.ndarray, gt: np.ndarray) -> float:
    ps = int(pred.sum())
    gs = int(gt.sum())
    if ps == 0 and gs == 0:
        return 1.0
    denom = ps + gs
    if denom == 0:
        return 0.0
    return float(2.0 * np.logical_and(pred, gt).sum() / denom)


def subject_meta_by_case(staged_root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for meta_path in staged_root.glob("*/subject_meta.json"):
        meta = read_json(meta_path)
        out[meta["case_id"]] = meta
    return out


def is_complete(mods: dict) -> bool:
    return bool(mods.get("c0") and mods.get("t2") and mods.get("de"))


def label_components_6(mask: np.ndarray) -> tuple[np.ndarray, list[int]]:
    labels = np.zeros(mask.shape, dtype=np.int32)
    sizes: list[int] = []
    current = 0
    zz, yy, xx = np.nonzero(mask)
    shape = mask.shape
    for start in zip(zz.tolist(), yy.tolist(), xx.tolist()):
        if labels[start] != 0:
            continue
        current += 1
        q: deque[tuple[int, int, int]] = deque([start])
        labels[start] = current
        size = 0
        while q:
            z, y, x = q.popleft()
            size += 1
            for dz, dy, dx in (
                (-1, 0, 0),
                (1, 0, 0),
                (0, -1, 0),
                (0, 1, 0),
                (0, 0, -1),
                (0, 0, 1),
            ):
                nz, ny, nx = z + dz, y + dy, x + dx
                if (
                    0 <= nz < shape[0]
                    and 0 <= ny < shape[1]
                    and 0 <= nx < shape[2]
                    and mask[nz, ny, nx]
                    and labels[nz, ny, nx] == 0
                ):
                    labels[nz, ny, nx] = current
                    q.append((nz, ny, nx))
        sizes.append(size)
    return labels, sizes


def component_filter_scar(arr: np.ndarray, min_voxels: int, missing_only: bool) -> np.ndarray:
    out = arr.copy()
    scar = mask_for(out, 5)
    labels, sizes = label_components_6(scar)
    keep = np.zeros_like(scar, dtype=bool)
    for idx, size in enumerate(sizes, start=1):
        if size >= min_voxels:
            keep |= labels == idx
    remove = scar & ~keep
    if missing_only:
        out[remove] = 0
    else:
        out[remove] = 0
    return out


def volume_cap_scar(arr: np.ndarray, cap_voxels: int) -> np.ndarray:
    """Keep largest scar components until cap_voxels is reached."""
    out = arr.copy()
    scar = mask_for(out, 5)
    labels, sizes = label_components_6(scar)
    order = sorted(enumerate(sizes, start=1), key=lambda x: x[1], reverse=True)
    keep = np.zeros_like(scar, dtype=bool)
    remaining = cap_voxels
    for idx, size in order:
        if remaining <= 0:
            break
        comp = labels == idx
        if size <= remaining:
            keep |= comp
            remaining -= size
        elif not keep.any():
            # Avoid deleting all scar from a positive prediction just because
            # the largest component is slightly above the cap.
            keep |= comp
            remaining = 0
    out[scar & ~keep] = 0
    return out


def replace_scar(base: np.ndarray, scar_source: np.ndarray) -> np.ndarray:
    out = base.copy()
    out[mask_for(out, 5)] = 0
    out[mask_for(scar_source, 5)] = 5
    return out


def replace_edema(base: np.ndarray, edema_source: np.ndarray) -> np.ndarray:
    out = base.copy()
    out[mask_for(out, 4)] = 0
    out[mask_for(edema_source, 4)] = 4
    return out


def summarize(rows: list[dict], key: str) -> float:
    return float(np.mean([float(r[key]) for r in rows])) if rows else float("nan")


def write_case_report(path: Path, rows: list[dict]) -> None:
    lines = [
        "# U-MyoPS round6 per-case scar comparison",
        "",
        "| case | group | gt_scar | umyops_pred | nnunet_pred | umyops_scar | nnunet_scar | delta_u_minus_n | failure_hint |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in sorted(rows, key=lambda x: float(x["u_minus_n_scar"])):
        lines.append(
            f"| {r['case']} | {r['modality_group']} | {r['gt_scar_voxels']} | "
            f"{r['u_pred_scar_voxels']} | {r['n_pred_scar_voxels']} | "
            f"{float(r['u_scar_dice']):.4f} | {float(r['n_scar_dice']):.4f} | "
            f"{float(r['u_minus_n_scar']):.4f} | {r['u_failure_hint']} |"
        )
    lines += [
        "",
        "## Group means",
        "",
        "| group | n | U-MyoPS scar | nnU-Net scar | delta |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in ("all_cases", "complete", "missing_modality", "scar_positive"):
        subset = [
            r
            for r in rows
            if name == "all_cases"
            or (name == "complete" and r["complete_modalities"])
            or (name == "missing_modality" and not r["complete_modalities"])
            or (name == "scar_positive" and int(r["gt_scar_voxels"]) > 0)
        ]
        lines.append(
            f"| {name} | {len(subset)} | {summarize(subset, 'u_scar_dice'):.4f} | "
            f"{summarize(subset, 'n_scar_dice'):.4f} | "
            f"{summarize(subset, 'u_minus_n_scar'):.4f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    root = repo_root()
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--umyops-dir", type=Path, default=root / "results/predictions/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0")
    ap.add_argument("--nnunet-dir", type=Path, default=root / "results/predictions/nnUNet501/fold_0")
    ap.add_argument("--gt-dir", type=Path, default=root / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr")
    ap.add_argument("--split-json", type=Path, default=root / "data/benchmarks/protocol/splits_MyoPS.json")
    ap.add_argument("--staged-root", type=Path, default=root / "data/benchmarks/U-MyoPS/gen_ZS_unaligned/data")
    ap.add_argument("--out-root", type=Path, default=root / "results/diagnostics/U-MyoPS_round6")
    ap.add_argument("--pred-root", type=Path, default=root / "results/predictions")
    args = ap.parse_args()

    case_ids = sorted(read_json(args.split_json)["folds"][args.fold]["val"])
    meta = subject_meta_by_case(args.staged_root)
    args.out_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    loaded: dict[str, tuple[sitk.Image, np.ndarray, np.ndarray, np.ndarray, dict]] = {}
    for cid in case_ids:
        ref_img, gt = read_img(args.gt_dir / f"{cid}.nii.gz")
        _, u = read_img(args.umyops_dir / f"{cid}.nii.gz")
        _, n = read_img(args.nnunet_dir / f"{cid}.nii.gz")
        mods = meta[cid]["modalities_present"]
        complete = is_complete(mods)
        u_scar = mask_for(u, 5)
        n_scar = mask_for(n, 5)
        gt_scar = mask_for(gt, 5)
        u_d = dice_masks(u_scar, gt_scar)
        n_d = dice_masks(n_scar, gt_scar)
        gt_vox = int(gt_scar.sum())
        u_vox = int(u_scar.sum())
        n_vox = int(n_scar.sum())
        if gt_vox == 0 and u_vox > 0:
            hint = "false_positive_empty_gt"
        elif gt_vox > 0 and u_vox > gt_vox * 2.0:
            hint = "over_segmentation"
        elif gt_vox > 0 and u_vox < gt_vox * 0.5:
            hint = "under_segmentation"
        else:
            hint = "localization_or_mixed"
        row = {
            "case": cid,
            "modalities_present": json.dumps(mods, sort_keys=True),
            "complete_modalities": complete,
            "modality_group": "complete" if complete else "missing_modality",
            "gt_scar_voxels": gt_vox,
            "u_pred_scar_voxels": u_vox,
            "n_pred_scar_voxels": n_vox,
            "u_scar_dice": u_d,
            "n_scar_dice": n_d,
            "u_minus_n_scar": u_d - n_d,
            "u_failure_hint": hint,
        }
        rows.append(row)
        loaded[cid] = (ref_img, gt, u, n, mods)

    fields = list(rows[0].keys())
    with (args.out_root / "per_case_umyops_vs_nnunet_scar.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    write_case_report(args.out_root / "per_case_umyops_vs_nnunet_scar.md", rows)

    variants = {
        "U-MyoPS_round6_scar_component_filter_100": "pure",
        "U-MyoPS_round6_scar_component_filter_250": "pure",
        "U-MyoPS_round6_missing_volume_cap_1500": "pure",
        "U-MyoPS_round6_scar_complete_umyops_missing_nnunet": "hybrid_scar",
        "U-MyoPS_round6_complete_umyops_missing_nnunet": "hybrid_full",
    }
    for tag in variants:
        out_dir = args.pred_root / tag / f"fold_{args.fold}"
        out_dir.mkdir(parents=True, exist_ok=True)
        for cid, (ref_img, _gt, u, n, mods) in loaded.items():
            complete = is_complete(mods)
            pred = u.copy()
            if tag.endswith("component_filter_100"):
                pred = component_filter_scar(pred, 100, missing_only=False)
            elif tag.endswith("component_filter_250"):
                pred = component_filter_scar(pred, 250, missing_only=False)
            elif tag.endswith("missing_volume_cap_1500") and not complete:
                pred = volume_cap_scar(pred, 1500)
            elif tag.endswith("scar_complete_umyops_missing_nnunet") and not complete:
                pred = replace_scar(pred, n)
            elif tag.endswith("complete_umyops_missing_nnunet") and not complete:
                pred = replace_scar(pred, n)
                pred = replace_edema(pred, n)
            write_like(pred, ref_img, out_dir / f"{cid}.nii.gz")

    manifest = {
        "inputs": {
            "umyops_dir": str(args.umyops_dir),
            "nnunet_dir": str(args.nnunet_dir),
            "gt_dir": str(args.gt_dir),
            "split_json": str(args.split_json),
        },
        "variants": variants,
        "notes": [
            "pure variants only modify U-MyoPS predictions",
            "hybrid_scar replaces class_5 on missing-modality cases with nnU-Net501 class_5",
            "hybrid_full replaces class_4 and class_5 on missing-modality cases with nnU-Net501",
        ],
    }
    (args.out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote round6 diagnostics to {args.out_root}")
    for tag in variants:
        print(f"Wrote predictions: {args.pred_root / tag / f'fold_{args.fold}'}")


if __name__ == "__main__":
    main()
