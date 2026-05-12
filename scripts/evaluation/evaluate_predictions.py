#!/usr/bin/env python3
"""
Unified offline evaluation: resample predictions to GT (nearest), then Dice per class
and foreground mean (macro mean over foreground classes). Optional Hausdorff
distance metrics use GT voxel spacing and are reported in mm.

CARE MyoPS label space: 0=bg, 1..5 foreground (see code/nnUNet/nnunet_label_utils.py).
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


def dice_per_class(
    pred: np.ndarray, gt: np.ndarray, class_id: int, *, skip_if_gt_empty: bool = False
) -> float | None:
    p = pred == class_id
    g = gt == class_id
    inter = np.logical_and(p, g).sum(dtype=np.float64)
    g_sum = float(g.sum())
    p_sum = float(p.sum())
    denom = p_sum + g_sum

    if skip_if_gt_empty:
        if g_sum < 1e-8:
            # No GT positives: exclude from pathology mean (CARE-style); penalize pure FP.
            return None if p_sum < 1e-8 else 0.0

    if denom < 1e-8:
        return 1.0 if inter < 1e-8 else 0.0
    return float(2.0 * inter / denom)


def apply_remap(arr: np.ndarray, remap: dict[int, int]) -> np.ndarray:
    out = np.zeros_like(arr, dtype=np.uint8)
    for src, dst in remap.items():
        out[arr == int(src)] = int(dst)
    return out


def _surface_distances_scipy(
    pred_bin: np.ndarray,
    gt_bin: np.ndarray,
    spacing_zyx: tuple[float, ...],
) -> np.ndarray:
    """Symmetric surface-to-surface distances for binary masks (z,y,x)."""
    from scipy.ndimage import binary_erosion, distance_transform_edt, generate_binary_structure

    struct = generate_binary_structure(pred_bin.ndim, 1)
    p = pred_bin.astype(bool)
    g = gt_bin.astype(bool)
    if not p.any() and not g.any():
        return np.array([0.0], dtype=np.float64)
    if not p.any() or not g.any():
        return np.array([np.inf], dtype=np.float64)

    surf_p = p & ~binary_erosion(p, structure=struct)
    surf_g = g & ~binary_erosion(g, structure=struct)
    sp = tuple(float(x) for x in spacing_zyx)

    dt_g = distance_transform_edt(~surf_g, sampling=sp)
    dt_p = distance_transform_edt(~surf_p, sampling=sp)
    d1 = dt_g[surf_p] if surf_p.any() else np.array([0.0])
    d2 = dt_p[surf_g] if surf_g.any() else np.array([0.0])
    return np.concatenate([d1.ravel(), d2.ravel()]).astype(np.float64, copy=False)


def _hd_scipy(pred_bin: np.ndarray, gt_bin: np.ndarray, spacing_zyx: tuple[float, ...]) -> float:
    """Exact symmetric Hausdorff distance on binary-mask surfaces (mm)."""
    return float(np.max(_surface_distances_scipy(pred_bin, gt_bin, spacing_zyx)))


def _hd95_scipy(pred_bin: np.ndarray, gt_bin: np.ndarray, spacing_zyx: tuple[float, ...]) -> float:
    """95th percentile symmetric Hausdorff distance on binary-mask surfaces (mm)."""
    return float(np.percentile(_surface_distances_scipy(pred_bin, gt_bin, spacing_zyx), 95))


def hd_class(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx) -> float | None:
    p = pred == class_id
    g = gt == class_id
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    try:
        from medpy.metric.binary import hd as medpy_hd

        return float(medpy_hd(p, g, voxelspacing=tuple(float(x) for x in spacing_zyx)))
    except ImportError:
        v = _hd_scipy(p, g, spacing_zyx)
        if np.isinf(v):
            return None
        return float(v)


def hd95_class(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx) -> float | None:
    p = pred == class_id
    g = gt == class_id
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    try:
        from medpy.metric.binary import hd95 as medpy_hd95

        return float(medpy_hd95(p, g, voxelspacing=tuple(float(x) for x in spacing_zyx)))
    except ImportError:
        v = _hd95_scipy(p, g, spacing_zyx)
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
    ap.add_argument(
        "--pred-remap-json",
        type=Path,
        default=None,
        help="JSON object mapping raw pred label ids to CARE ids before metrics",
    )
    ap.add_argument(
        "--skip-dice-if-gt-empty",
        action="store_true",
        help="For each class: if GT has no voxels of that class, omit that case from class-mean "
        "(JSON null per case); if GT empty but prediction has positives, score 0. Matches common "
        "pathology-leaderboard handling for myops_edema / myops_scar style metrics.",
    )
    ap.add_argument("--hd", action="store_true", help="Compute exact symmetric Hausdorff Distance in mm")
    ap.add_argument("--hd95", action="store_true", help="Compute 95th percentile Hausdorff Distance in mm")
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

    per_case_dice: dict[str, dict[str, float | None]] = {}
    per_case_hd: dict[str, dict[str, float | None]] = {}
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

        dices: dict[str, float | None] = {}
        hd_map: dict[str, float | None] = {}
        hd95_map: dict[str, float | None] = {}
        spacing = gt_img.GetSpacing()[::-1]  # z,y,x for medpy with numpy z,y,x arrays

        for c in fg:
            dices[f"class_{c}"] = dice_per_class(
                pr_arr, gt_arr, c, skip_if_gt_empty=args.skip_dice_if_gt_empty
            )
            if args.hd:
                hd_map[f"class_{c}"] = hd_class(pr_arr, gt_arr, c, spacing)
            if args.hd95:
                hd95_map[f"class_{c}"] = hd95_class(pr_arr, gt_arr, c, spacing)

        vals = [dices[f"class_{c}"] for c in fg if f"class_{c}" in dices and dices[f"class_{c}"] is not None]
        dices["foreground_mean"] = float(np.mean(vals)) if vals else None
        per_case_dice[cid] = dices
        if args.hd:
            hvals = [v for v in hd_map.values() if v is not None]
            hd_map["foreground_mean_hd"] = float(np.mean(hvals)) if hvals else None
            per_case_hd[cid] = hd_map
        if args.hd95:
            hvals = [v for v in hd95_map.values() if v is not None]
            hd95_map["foreground_mean_hd95"] = float(np.mean(hvals)) if hvals else None
            per_case_hd95[cid] = hd95_map

    # aggregate across cases
    agg_dice: dict[str, float | None] = {}
    for k in [f"class_{c}" for c in fg] + ["foreground_mean"]:
        vs = [
            per_case_dice[c][k]
            for c in per_case_dice
            if k in per_case_dice[c] and per_case_dice[c][k] is not None
        ]
        if vs:
            agg_dice[k] = float(np.mean(vs))
        elif k == "foreground_mean":
            agg_dice[k] = None

    agg_hd: dict[str, float] = {}
    if args.hd:
        for k in [f"class_{c}" for c in fg] + ["foreground_mean_hd"]:
            vs = [
                per_case_hd[c][k]
                for c in per_case_hd
                if k in per_case_hd[c] and per_case_hd[c][k] is not None
            ]
            if vs:
                agg_hd[k] = float(np.mean(vs))

    agg_hd95: dict[str, float] = {}
    if args.hd95:
        for k in [f"class_{c}" for c in fg] + ["foreground_mean_hd95"]:
            vs = [
                per_case_hd95[c][k]
                for c in per_case_hd95
                if k in per_case_hd95[c] and per_case_hd95[c][k] is not None
            ]
            if vs:
                agg_hd95[k] = float(np.mean(vs))

    summary = {
        "n_cases": len(per_case_dice),
        "foreground_classes": fg,
        "mean_dice": agg_dice,
        "per_case": per_case_dice,
    }
    if sorted(fg) == [4, 5]:
        summary["care2026_leaderboard_labels"] = {
            "class_4": "myops_edema",
            "class_5": "myops_scar",
        }
    if args.hd:
        summary["mean_hd"] = agg_hd
        summary["per_case_hd"] = per_case_hd
    if args.hd95:
        summary["mean_hd95"] = agg_hd95
        summary["per_case_hd95"] = per_case_hd95

    out_dir = args.output_dir
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "evaluation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (out_dir / "dice_per_class.json").write_text(
            json.dumps({"mean": agg_dice, "per_case": per_case_dice}, indent=2),
            encoding="utf-8",
        )
        fg_mean = agg_dice.get("foreground_mean")
        (out_dir / "foreground_mean.json").write_text(
            json.dumps({"foreground_mean": fg_mean, "per_fold_or_run": agg_dice}, indent=2),
            encoding="utf-8",
        )
        if args.hd:
            (out_dir / "hd_per_class.json").write_text(
                json.dumps({"mean": agg_hd, "per_case": per_case_hd}, indent=2),
                encoding="utf-8",
            )
        if args.hd95:
            (out_dir / "hd95_per_class.json").write_text(
                json.dumps({"mean": agg_hd95, "per_case": per_case_hd95}, indent=2),
                encoding="utf-8",
            )
        print(f"Wrote JSON under {out_dir}")
    else:
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
