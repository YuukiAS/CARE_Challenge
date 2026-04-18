#!/usr/bin/env python3
"""
Unified offline evaluation: resample predictions to GT (nearest), then Dice per class
and foreground mean (macro mean over foreground classes). Optional HD95 (medpy).

CARE MyoPS label space: 0=bg, 1..5 foreground (see scripts/nnUNet/nnunet_label_utils.py).
Cine compact (Dataset502): 0=bg, 1=myocardium, 2=LV_blood, 3=scar — use --foreground-classes 1,2,3.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk


def _read_sitk(path: str | Path) -> sitk.Image:
    return sitk.ReadImage(str(path))


def _resample_to_reference(moving: sitk.Image, reference: sitk.Image, is_label: bool) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor if is_label else sitk.sitkLinear)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(moving)


def dice_per_class(pred: np.ndarray, gt: np.ndarray, class_id: int) -> float:
    p = pred == class_id
    g = gt == class_id
    inter = np.logical_and(p, g).sum(dtype=np.float64)
    denom = float(p.sum() + g.sum())
    if denom < 1e-8:
        return 1.0 if inter < 1e-8 else 0.0
    return float(2.0 * inter / denom)


def apply_remap(arr: np.ndarray, remap: dict[int, int]) -> np.ndarray:
    out = np.zeros_like(arr, dtype=np.uint8)
    for src, dst in remap.items():
        out[arr == int(src)] = int(dst)
    return out


def _hd95_scipy(pred_bin: np.ndarray, gt_bin: np.ndarray, spacing_zyx: tuple[float, ...]) -> float:
    """95th percentile symmetric Hausdorff distance on binary masks (z,y,x)."""
    from scipy.ndimage import binary_erosion, distance_transform_edt, generate_binary_structure

    struct = generate_binary_structure(pred_bin.ndim, 1)
    p = pred_bin.astype(bool)
    g = gt_bin.astype(bool)
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return float("inf")

    surf_p = p & ~binary_erosion(p, structure=struct)
    surf_g = g & ~binary_erosion(g, structure=struct)
    sp = tuple(float(x) for x in spacing_zyx)

    dt_g = distance_transform_edt(~g, sampling=sp)
    dt_p = distance_transform_edt(~p, sampling=sp)
    d1 = dt_g[surf_p] if surf_p.any() else np.array([0.0])
    d2 = dt_p[surf_g] if surf_g.any() else np.array([0.0])
    all_d = np.concatenate([d1.ravel(), d2.ravel()])
    return float(np.percentile(all_d, 95))


def hd95_class(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx) -> float | None:
    p = (pred == class_id).astype(np.uint8)
    g = (gt == class_id).astype(np.uint8)
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    try:
        from medpy.metric.binary import hd95 as medpy_hd95

        return float(medpy_hd95(p, g, voxelspacing=tuple(float(x) for x in spacing_zyx)))
    except ImportError:
        v = _hd95_scipy(p > 0, g > 0, spacing_zyx)
        if np.isinf(v):
            return None
        return float(v)


def collect_pairs(
    pred_dir: Path,
    gt_dir: Path,
    fold_json: Path | None,
    fold: int | None,
    case_ids: list[str] | None,
) -> list[str]:
    if case_ids is not None:
        return sorted(case_ids)
    if fold_json is not None and fold is not None:
        with fold_json.open(encoding="utf-8") as f:
            data = json.load(f)
        folds = data["folds"]
        if fold < 0 or fold >= len(folds):
            raise ValueError(f"fold {fold} out of range [0, {len(folds)})")
        return sorted(folds[fold]["val"])
    # all preds that have matching gt
    ids = []
    for p in sorted(pred_dir.glob("*.nii.gz")):
        cid = p.name.replace(".nii.gz", "")
        if (gt_dir / f"{cid}.nii.gz").is_file():
            ids.append(cid)
    return sorted(ids)


def main() -> None:
    ap = argparse.ArgumentParser(description="Unified CARE prediction evaluation vs GT")
    ap.add_argument("--pred-dir", type=Path, required=True)
    ap.add_argument("--gt-dir", type=Path, required=True)
    ap.add_argument("--fold-json", type=Path, default=None, help="Protocol splits JSON from generate_splits.py")
    ap.add_argument("--fold", type=int, default=None, help="Fold index for val case list")
    ap.add_argument(
        "--cases",
        type=str,
        default=None,
        help="Comma-separated case ids (overrides fold-json)",
    )
    ap.add_argument(
        "--foreground-classes",
        type=str,
        default="1,2,3,4,5",
        help="Comma-separated class ids for Dice / mean (default MyoPS 1-5)",
    )
    ap.add_argument("--pred-remap-json", type=Path, help="JSON object mapping raw pred label -> CARE id")
    ap.add_argument("--hd95", action="store_true")
    ap.add_argument("--output-dir", type=Path, default=None, help="Write JSON metrics here")
    args = ap.parse_args()

    fg = [int(x.strip()) for x in args.foreground_classes.split(",") if x.strip()]
    pred_dir = args.pred_dir
    gt_dir = args.gt_dir

    case_ids = None
    if args.cases:
        case_ids = [x.strip() for x in args.cases.split(",") if x.strip()]

    remap: dict[int, int] | None = None
    if args.pred_remap_json:
        with args.pred_remap_json.open(encoding="utf-8") as f:
            raw = json.load(f)
        remap = {int(k): int(v) for k, v in raw.items()}

    ids = collect_pairs(pred_dir, gt_dir, args.fold_json, args.fold, case_ids)
    if not ids:
        print("No cases to evaluate.", file=sys.stderr)
        sys.exit(1)

    per_case_dice: dict[str, dict[str, float]] = {}
    per_case_hd95: dict[str, dict[str, float | None]] = {}

    for cid in ids:
        pred_path = pred_dir / f"{cid}.nii.gz"
        gt_path = gt_dir / f"{cid}.nii.gz"
        if not pred_path.is_file():
            print(f"Missing pred: {pred_path}", file=sys.stderr)
            continue
        if not gt_path.is_file():
            print(f"Missing gt: {gt_path}", file=sys.stderr)
            continue

        gt_img = _read_sitk(gt_path)
        pr_img = _read_sitk(pred_path)
        pr_rs = _resample_to_reference(pr_img, gt_img, is_label=True)
        gt_arr = sitk.GetArrayFromImage(gt_img).astype(np.uint8, copy=False)
        pr_arr = sitk.GetArrayFromImage(pr_rs).astype(np.uint8, copy=False)

        if remap is not None:
            pr_arr = apply_remap(pr_arr.astype(np.int32), remap)

        dices: dict[str, float] = {}
        hd_map: dict[str, float | None] = {}
        spacing = gt_img.GetSpacing()[::-1]  # z,y,x for medpy with numpy z,y,x arrays

        for c in fg:
            dices[f"class_{c}"] = dice_per_class(pr_arr, gt_arr, c)
            if args.hd95:
                h = hd95_class(pr_arr, gt_arr, c, spacing)
                hd_map[f"class_{c}"] = h

        vals = [dices[f"class_{c}"] for c in fg if f"class_{c}" in dices]
        dices["foreground_mean"] = float(np.mean(vals)) if vals else 0.0
        per_case_dice[cid] = dices
        if args.hd95:
            hvals = [v for v in hd_map.values() if v is not None]
            hd_map["foreground_mean_hd95"] = float(np.mean(hvals)) if hvals else None
            per_case_hd95[cid] = hd_map

    # aggregate across cases
    agg_dice: dict[str, float] = {}
    for k in [f"class_{c}" for c in fg] + ["foreground_mean"]:
        vs = [per_case_dice[c][k] for c in per_case_dice if k in per_case_dice[c]]
        if vs:
            agg_dice[k] = float(np.mean(vs))

    summary = {
        "n_cases": len(per_case_dice),
        "foreground_classes": fg,
        "mean_dice": agg_dice,
        "per_case": per_case_dice,
    }
    if args.hd95:
        summary["per_case_hd95"] = per_case_hd95

    out_dir = args.output_dir
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "evaluation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (out_dir / "dice_per_class.json").write_text(
            json.dumps({"mean": agg_dice, "per_case": per_case_dice}, indent=2),
            encoding="utf-8",
        )
        fg_mean = agg_dice.get("foreground_mean", 0.0)
        (out_dir / "foreground_mean.json").write_text(
            json.dumps({"foreground_mean": fg_mean, "per_fold_or_run": agg_dice}, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote JSON under {out_dir}")
    else:
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
