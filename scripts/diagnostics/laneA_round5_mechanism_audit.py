#!/usr/bin/env python3
"""Lane A Round5 CARE-only mechanism feasibility audits.

This script is intentionally diagnostic-only. It reads existing Dataset501
fold0 validation images, labels, nnU-Net baseline predictions, and the failed
Round4 candidate predictions. It does not train, write predictions, create
submissions, or touch model checkpoints.
"""

from __future__ import annotations

import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/diagnostics/care_myocardium/laneA_myops/round05_mechanism_integration_audit"
PLAN_PATH = ROOT / "docs/plans/laneA_round05_active_controlled_mechanism_integration_execution.md"
METRICS_CSV = ROOT / "results/diagnostics/care_myocardium/laneA_myops/round04_fold0_short_train/fold0_short_train_metrics.csv"
FOLD0_VAL = ROOT / "data/CARE_Challenge_folds/MyoPS/fold0/val"
LABELS_TR = ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
BASELINE_PRED = ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
ROUND4_PRED = ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/laneA_edema_focal_tversky_t2down_fold0_short__nnUNetPlans__3d_fullres/fold_0/validation"

MODEL_DIRS = {
    "baseline_nnunet501_fold0": BASELINE_PRED,
    "candidate_laneA_round4": ROUND4_PRED,
}


def read_image(path: Path) -> tuple[sitk.Image, np.ndarray]:
    image = sitk.ReadImage(str(path))
    return image, sitk.GetArrayFromImage(image)


def bbox(mask: np.ndarray):
    pts = np.argwhere(mask)
    if pts.size == 0:
        return None
    lo = pts.min(axis=0)
    hi = pts.max(axis=0)
    return lo, hi


def bbox_center_mm(mask: np.ndarray, spacing_zyx: tuple[float, float, float]):
    box = bbox(mask)
    if box is None:
        return None
    lo, hi = box
    return ((lo + hi) / 2.0) * np.asarray(spacing_zyx)


def bbox_volume_vox(mask: np.ndarray) -> int:
    box = bbox(mask)
    if box is None:
        return 0
    lo, hi = box
    return int(np.prod(hi - lo + 1))


def dice(a: np.ndarray, b: np.ndarray) -> float:
    denom = int(a.sum()) + int(b.sum())
    if denom == 0:
        return math.nan
    return 2.0 * float(np.logical_and(a, b).sum()) / denom


def connected_components(mask: np.ndarray):
    structure = np.ones((3, 3, 3), dtype=bool)
    return ndimage.label(mask, structure=structure)


def case_center_from_symlink(case_id: str) -> str:
    target = (FOLD0_VAL / case_id).resolve()
    return target.parent.name


def raw_modality_path(case_id: str, modality: str) -> Path:
    return FOLD0_VAL / case_id / f"{case_id}_{modality}.nii.gz"


def safe_corr(x: pd.Series, y: pd.Series) -> float:
    valid = x.notna() & y.notna()
    if valid.sum() < 4 or x[valid].nunique() < 2 or y[valid].nunique() < 2:
        return math.nan
    return float(x[valid].corr(y[valid], method="spearman"))


def summarize_bool(value: bool) -> str:
    return "yes" if value else "no"


def md_table(df: pd.DataFrame) -> str:
    """Render a small dataframe as a GitHub-style markdown table without tabulate."""
    if df.empty:
        return "_No rows._"
    work = df.copy()
    for col in work.columns:
        work[col] = work[col].map(format_cell)
    header = "| " + " | ".join(map(str, work.columns)) + " |"
    sep = "| " + " | ".join(["---"] * len(work.columns)) + " |"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in work.to_numpy()]
    return "\n".join([header, sep] + rows)


def format_cell(value) -> str:
    if pd.isna(value):
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def alignment_audit(metrics: pd.DataFrame) -> pd.DataFrame:
    baseline = metrics[metrics["model"] == "baseline_nnunet501_fold0"].copy()
    rows = []
    for _, row in baseline[baseline["modality_group"] == "C0+LGE+T2"].iterrows():
        case_id = row["case_id"]
        images = {}
        arrays = {}
        available = {}
        for mod in ("LGE", "T2", "C0"):
            path = raw_modality_path(case_id, mod)
            available[mod] = path.exists()
            if path.exists():
                images[mod], arrays[mod] = read_image(path)
        if not all(available.values()):
            rows.append({
                "case_id": case_id,
                "center": row["center"],
                "all_modalities_available": False,
                "audit_note": "complete_modality_metadata_but_raw_file_missing",
            })
            continue

        ref = images["LGE"]
        ref_shape = arrays["LGE"].shape
        ref_spacing = ref.GetSpacing()
        ref_origin = np.asarray(ref.GetOrigin())
        ref_direction = np.asarray(ref.GetDirection())
        shape_match = all(arrays[m].shape == ref_shape for m in ("T2", "C0"))
        spacing_diffs = [float(np.max(np.abs(np.asarray(images[m].GetSpacing()) - np.asarray(ref_spacing)))) for m in ("T2", "C0")]
        origin_diffs = [float(np.linalg.norm(np.asarray(images[m].GetOrigin()) - ref_origin)) for m in ("T2", "C0")]
        direction_diffs = [float(np.max(np.abs(np.asarray(images[m].GetDirection()) - ref_direction))) for m in ("T2", "C0")]
        geometry_mismatch = (not shape_match) or max(spacing_diffs) > 1e-4 or max(origin_diffs) > 1e-3 or max(direction_diffs) > 1e-4

        spacing_zyx = tuple(reversed(ref_spacing))
        masks = {}
        centers = {}
        for mod, arr in arrays.items():
            finite = np.isfinite(arr)
            nonzero = finite & (arr != 0)
            if nonzero.sum() == 0:
                masks[mod] = nonzero
            else:
                vals = arr[nonzero]
                threshold = np.percentile(vals, 1)
                masks[mod] = finite & (arr > threshold)
            centers[mod] = bbox_center_mm(masks[mod], spacing_zyx)

        center_dists = []
        for mod in ("T2", "C0"):
            if centers["LGE"] is None or centers[mod] is None:
                center_dists.append(math.nan)
            else:
                center_dists.append(float(np.linalg.norm(centers[mod] - centers["LGE"])))
        body_overlap_lge_t2 = dice(masks["LGE"], masks["T2"])
        body_overlap_lge_c0 = dice(masks["LGE"], masks["C0"])

        label_path = LABELS_TR / f"{case_id}.nii.gz"
        _, label = read_image(label_path)
        anatomy = np.isin(label, [1, 2, 3])
        if anatomy.sum() > 10:
            vals = {}
            for mod, arr in arrays.items():
                v = arr[anatomy]
                vals[mod] = v[np.isfinite(v)]
            corr_lge_t2 = float(np.corrcoef(vals["LGE"], vals["T2"])[0, 1]) if len(vals["LGE"]) > 2 and np.std(vals["LGE"]) > 0 and np.std(vals["T2"]) > 0 else math.nan
            corr_lge_c0 = float(np.corrcoef(vals["LGE"], vals["C0"])[0, 1]) if len(vals["LGE"]) > 2 and np.std(vals["LGE"]) > 0 and np.std(vals["C0"]) > 0 else math.nan
        else:
            corr_lge_t2 = math.nan
            corr_lge_c0 = math.nan

        rows.append({
            "case_id": case_id,
            "center": row["center"],
            "modality_group": row["modality_group"],
            "all_modalities_available": True,
            "slice_count_lge": ref_shape[0],
            "shape_lge": "x".join(map(str, ref_shape)),
            "spacing_lge_xyz": "x".join(f"{x:.6g}" for x in ref_spacing),
            "shape_match_all": shape_match,
            "max_spacing_diff": max(spacing_diffs),
            "max_origin_distance": max(origin_diffs),
            "max_direction_diff": max(direction_diffs),
            "geometry_mismatch": geometry_mismatch,
            "body_bbox_volume_lge": bbox_volume_vox(masks["LGE"]),
            "body_bbox_volume_t2": bbox_volume_vox(masks["T2"]),
            "body_bbox_volume_c0": bbox_volume_vox(masks["C0"]),
            "max_body_bbox_center_distance_mm": np.nanmax(center_dists),
            "body_overlap_lge_t2_dice": body_overlap_lge_t2,
            "body_overlap_lge_c0_dice": body_overlap_lge_c0,
            "anatomy_intensity_corr_lge_t2": corr_lge_t2,
            "anatomy_intensity_corr_lge_c0": corr_lge_c0,
            "baseline_edema_dice": row["myops_edema_dice"],
            "baseline_edema_hd95": row["myops_edema_hd95"],
            "baseline_edema_remote_fp": row["myops_edema_remote_fp"],
            "baseline_edema_volume_ratio": row["myops_edema_pred_gt_volume_ratio"],
            "edema_hd95_failure": bool(row["myops_edema_hd95"] >= 20 or row["myops_edema_remote_fp"] > 0),
            "audit_note": "ok",
        })
    return pd.DataFrame(rows)


def anatomy_audit(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, mrow in metrics.iterrows():
        case_id = mrow["case_id"]
        model = mrow["model"]
        pred_path = MODEL_DIRS[model] / f"{case_id}.nii.gz"
        label_path = LABELS_TR / f"{case_id}.nii.gz"
        if not pred_path.exists() or not label_path.exists():
            continue
        image, pred = read_image(pred_path)
        _, gt = read_image(label_path)
        spacing_zyx = tuple(reversed(image.GetSpacing()))
        pred_edema = pred == 4
        gt_edema = gt == 4
        myo = gt == 1
        anatomy = np.isin(gt, [1, 2, 3])
        dist_to_myo = ndimage.distance_transform_edt(~myo, sampling=spacing_zyx) if myo.any() else np.full(gt.shape, np.nan)
        dist_to_anatomy = ndimage.distance_transform_edt(~anatomy, sampling=spacing_zyx) if anatomy.any() else np.full(gt.shape, np.nan)
        dilated_myo = dist_to_myo <= 10.0 if myo.any() else np.zeros_like(gt, dtype=bool)
        labeled, ncomp = connected_components(pred_edema)

        remote_fp = 0
        fp_components = 0
        comp_min_myo_dist = []
        comp_outside_support = []
        for cid in range(1, ncomp + 1):
            comp = labeled == cid
            if comp.sum() == 0:
                continue
            comp_is_fp = not np.logical_and(comp, gt_edema).any()
            if comp_is_fp:
                fp_components += 1
            min_myo = float(np.nanmin(dist_to_myo[comp])) if myo.any() else math.nan
            outside = float((comp & ~dilated_myo).sum() / comp.sum()) if comp.sum() else math.nan
            comp_min_myo_dist.append(min_myo)
            comp_outside_support.append(outside)
            if comp_is_fp and (outside > 0.5 or (not math.isnan(min_myo) and min_myo > 10.0)):
                remote_fp += 1

        pred_vox = int(pred_edema.sum())
        if pred_vox:
            pred_dist_myo = dist_to_myo[pred_edema]
            pred_dist_anat = dist_to_anatomy[pred_edema]
            pred_overlap_myo = float(np.logical_and(pred_edema, myo).sum() / pred_vox)
            pred_overlap_anatomy = float(np.logical_and(pred_edema, anatomy).sum() / pred_vox)
            pred_inside_dilated_myo = float(np.logical_and(pred_edema, dilated_myo).sum() / pred_vox)
            mean_dist_myo = float(np.nanmean(pred_dist_myo))
            p95_dist_myo = float(np.nanpercentile(pred_dist_myo, 95))
            max_dist_myo = float(np.nanmax(pred_dist_myo))
            mean_dist_anatomy = float(np.nanmean(pred_dist_anat))
        else:
            pred_overlap_myo = pred_overlap_anatomy = pred_inside_dilated_myo = math.nan
            mean_dist_myo = p95_dist_myo = max_dist_myo = mean_dist_anatomy = math.nan

        rows.append({
            "model": model,
            "case_id": case_id,
            "center": mrow["center"],
            "modality_group": mrow["modality_group"],
            "t2_present": bool(mrow["t2_present"]),
            "edema_gt_positive": bool(mrow["edema_gt_positive"]),
            "edema_dice": mrow["myops_edema_dice"],
            "edema_hd95": mrow["myops_edema_hd95"],
            "reported_remote_fp": mrow["myops_edema_remote_fp"],
            "pred_edema_voxels": pred_vox,
            "gt_edema_voxels": int(gt_edema.sum()),
            "pred_edema_components": int(ncomp),
            "fp_component_count": int(fp_components),
            "soft_anatomy_remote_fp_count": int(remote_fp),
            "pred_overlap_myo_ratio": pred_overlap_myo,
            "pred_overlap_anatomy_ratio": pred_overlap_anatomy,
            "pred_inside_dilated_myo_10mm_ratio": pred_inside_dilated_myo,
            "pred_mean_dist_to_myo_mm": mean_dist_myo,
            "pred_p95_dist_to_myo_mm": p95_dist_myo,
            "pred_max_dist_to_myo_mm": max_dist_myo,
            "pred_mean_dist_to_anatomy_mm": mean_dist_anatomy,
            "component_max_min_dist_to_myo_mm": float(np.nanmax(comp_min_myo_dist)) if comp_min_myo_dist else math.nan,
            "component_mean_outside_dilated_myo_ratio": float(np.nanmean(comp_outside_support)) if comp_outside_support else math.nan,
            "no_t2_empty_gt_new_fp_risk": bool((not mrow["t2_present"]) and (not mrow["edema_gt_positive"]) and pred_vox > 0),
        })
    return pd.DataFrame(rows)


def boundary_audit(metrics: pd.DataFrame, anatomy_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, mrow in metrics.iterrows():
        case_id = mrow["case_id"]
        model = mrow["model"]
        pred_path = MODEL_DIRS[model] / f"{case_id}.nii.gz"
        label_path = LABELS_TR / f"{case_id}.nii.gz"
        if not pred_path.exists() or not label_path.exists():
            continue
        image, pred = read_image(pred_path)
        _, gt = read_image(label_path)
        spacing_zyx = tuple(reversed(image.GetSpacing()))
        pred_edema = pred == 4
        gt_edema = gt == 4
        pred_vox = int(pred_edema.sum())
        gt_vox = int(gt_edema.sum())
        if gt_edema.any() and pred_edema.any():
            dist_to_gt = ndimage.distance_transform_edt(~gt_edema, sampling=spacing_zyx)
            pred_outside = pred_edema & ~gt_edema
            p95_pred_to_gt = float(np.percentile(dist_to_gt[pred_edema], 95))
            mean_outside_dist = float(np.mean(dist_to_gt[pred_outside])) if pred_outside.any() else 0.0
            max_pred_to_gt = float(np.max(dist_to_gt[pred_edema]))
        elif pred_edema.any():
            p95_pred_to_gt = mean_outside_dist = max_pred_to_gt = math.nan
        else:
            p95_pred_to_gt = mean_outside_dist = max_pred_to_gt = 0.0

        ratio = mrow["myops_edema_pred_gt_volume_ratio"]
        remote_fp = int(mrow["myops_edema_remote_fp"])
        hd95 = mrow["myops_edema_hd95"]
        dice_value = mrow["myops_edema_dice"]
        if not mrow["edema_gt_positive"] and pred_vox > 0:
            failure_mode = "empty_gt_false_positive"
        elif remote_fp > 0:
            failure_mode = "remote_component_dominant"
        elif pd.notna(ratio) and ratio > 2.0:
            failure_mode = "volume_overprediction"
        elif pd.notna(ratio) and ratio < 0.5:
            failure_mode = "undersegmentation"
        elif pd.notna(hd95) and hd95 >= 20 and pd.notna(p95_pred_to_gt) and p95_pred_to_gt >= 5:
            failure_mode = "boundary_overreach"
        elif pd.notna(dice_value) and dice_value < 0.3:
            failure_mode = "poor_localization_mixed"
        else:
            failure_mode = "acceptable_or_minor"

        anatomy_row = anatomy_df[(anatomy_df["model"] == model) & (anatomy_df["case_id"] == case_id)]
        soft_remote = int(anatomy_row["soft_anatomy_remote_fp_count"].iloc[0]) if not anatomy_row.empty else 0
        rows.append({
            "model": model,
            "case_id": case_id,
            "center": mrow["center"],
            "modality_group": mrow["modality_group"],
            "t2_present": bool(mrow["t2_present"]),
            "edema_gt_positive": bool(mrow["edema_gt_positive"]),
            "edema_dice": dice_value,
            "edema_hd": mrow["myops_edema_hd"],
            "edema_hd95": hd95,
            "edema_component_count": mrow["myops_edema_component_count"],
            "edema_remote_fp": remote_fp,
            "soft_anatomy_remote_fp_count": soft_remote,
            "pred_gt_volume_ratio": ratio,
            "pred_edema_voxels": pred_vox,
            "gt_edema_voxels": gt_vox,
            "p95_pred_to_gt_edema_distance_mm": p95_pred_to_gt,
            "mean_outside_gt_distance_mm": mean_outside_dist,
            "max_pred_to_gt_edema_distance_mm": max_pred_to_gt,
            "failure_mode": failure_mode,
            "boundary_loss_implication": boundary_implication(failure_mode),
        })
    return pd.DataFrame(rows)


def boundary_implication(failure_mode: str) -> str:
    if failure_mode == "boundary_overreach":
        return "candidate_for_small_weight_surface_distance_loss"
    if failure_mode == "remote_component_dominant":
        return "needs_anatomy_or_component_guard_before_boundary_loss"
    if failure_mode == "volume_overprediction":
        return "avoid_recall_heavy_loss_use_conservative_fp_penalty"
    if failure_mode == "undersegmentation":
        return "surface_loss_alone_insufficient_preserve_dice_ce"
    if failure_mode == "empty_gt_false_positive":
        return "do_not_use_no_t2_empty_gt_as_strong_negative; needs_t2_missing_guard"
    return "no_boundary_specific_action"


def write_alignment_md(df: pd.DataFrame, metrics: pd.DataFrame) -> None:
    path = OUT_DIR / "alignment_feasibility_audit.md"
    complete_n = len(df)
    center_c = df[df["center"] == "CenterC"]
    mismatch_n = int(df.get("geometry_mismatch", pd.Series(dtype=bool)).fillna(False).sum())
    corr_center_dist = safe_corr(df["max_body_bbox_center_distance_mm"], df["baseline_edema_hd95"]) if complete_n else math.nan
    corr_overlap = safe_corr(1 - df["body_overlap_lge_t2_dice"], df["baseline_edema_hd95"]) if complete_n else math.nan
    lines = [
        "# Lane A Round5 Alignment Feasibility Audit",
        "",
        "Scope: fold0 complete-modality validation cases only, using raw CARE C0/LGE/T2 images and existing nnU-Net/Round4 metrics. No registration, training, or external repo was run.",
        "",
        "## Key Counts",
        "",
        f"- Complete-modality audited cases: `{complete_n}`.",
        f"- CenterC audited cases: `{len(center_c)}`.",
        f"- Geometry mismatch cases: `{mismatch_n}`.",
        f"- Spearman(max body bbox center distance, baseline edema HD95): `{corr_center_dist:.4f}`." if not math.isnan(corr_center_dist) else "- Spearman(max body bbox center distance, baseline edema HD95): `NA`.",
        f"- Spearman(1 - LGE/T2 body overlap, baseline edema HD95): `{corr_overlap:.4f}`." if not math.isnan(corr_overlap) else "- Spearman(1 - LGE/T2 body overlap, baseline edema HD95): `NA`.",
        "",
        "## CenterC Worst Baseline Edema HD95",
        "",
    ]
    if not center_c.empty:
        cols = ["case_id", "baseline_edema_dice", "baseline_edema_hd95", "baseline_edema_remote_fp", "max_body_bbox_center_distance_mm", "body_overlap_lge_t2_dice", "anatomy_intensity_corr_lge_t2"]
        lines.append(md_table(center_c.sort_values("baseline_edema_hd95", ascending=False)[cols].head(8)))
    else:
        lines.append("No CenterC complete-modality cases found.")
    lines += [
        "",
        "## Interpretation",
        "",
        "- Geometry-level C0/LGE/T2 mismatch is treated as a strong `go` signal for SSA/alignment preprocessing.",
        "- If geometry is matched but body/intensity proxies correlate with CenterC HD95 failures, alignment remains `watch/go` as a slice-content or acquisition-mismatch hypothesis.",
        "- If proxies are flat or weak, anatomy and boundary audits should drive the next smoke before integrating CAA-Seg/SSA.",
    ]
    path.write_text("\n".join(lines) + "\n")


def write_anatomy_md(df: pd.DataFrame) -> None:
    path = OUT_DIR / "anatomy_soft_prior_feasibility.md"
    agg = df.groupby("model").agg(
        cases=("case_id", "count"),
        mean_components=("pred_edema_components", "mean"),
        mean_remote=("soft_anatomy_remote_fp_count", "mean"),
        mean_inside_dilated_myo=("pred_inside_dilated_myo_10mm_ratio", "mean"),
        no_t2_empty_gt_fp=("no_t2_empty_gt_new_fp_risk", "sum"),
        mean_p95_dist_myo=("pred_p95_dist_to_myo_mm", "mean"),
    ).reset_index()
    bad = df.sort_values(["soft_anatomy_remote_fp_count", "pred_p95_dist_to_myo_mm"], ascending=False).head(12)
    lines = [
        "# Lane A Round5 Anatomy Soft Prior Feasibility Audit",
        "",
        "Scope: existing fold0 baseline and failed Round4 predictions, GT anatomy labels, and 10 mm dilated myocardium support. This is an explanatory audit only; no hard deletion was applied.",
        "",
        "## Model Summary",
        "",
        md_table(agg),
        "",
        "## Highest Soft-Anatomy Remote FP / Distance Cases",
        "",
        md_table(bad[["model", "case_id", "center", "modality_group", "t2_present", "edema_gt_positive", "edema_hd95", "pred_edema_components", "soft_anatomy_remote_fp_count", "pred_inside_dilated_myo_10mm_ratio", "pred_p95_dist_to_myo_mm", "no_t2_empty_gt_new_fp_risk"]]),
        "",
        "## Interpretation",
        "",
        "- A useful soft prior signal is present when remote FP or HD95 outliers have low dilated-myocardium support or large distance to myocardium/anatomy.",
        "- This audit supports soft anatomy input/loss/penalty only. It does not justify deleting all edema outside myocardium.",
        "- No-T2 empty-GT false positives must remain a separate guardrail; they cannot be converted into strong negative training labels.",
    ]
    path.write_text("\n".join(lines) + "\n")


def write_boundary_md(df: pd.DataFrame) -> None:
    path = OUT_DIR / "boundary_distance_failure_audit.md"
    mode_counts = df.groupby(["model", "failure_mode"]).size().reset_index(name="n")
    center_c = df[(df["center"] == "CenterC") & (df["edema_gt_positive"])]
    lines = [
        "# Lane A Round5 Boundary / Distance Failure Audit",
        "",
        "Scope: baseline and Round4 fold0 validation predictions. Failure modes are heuristic labels for deciding the next trainable mechanism; they are not replacement metrics.",
        "",
        "## Failure Mode Counts",
        "",
        md_table(mode_counts),
        "",
        "## CenterC GT-positive Edema Cases",
        "",
        md_table(center_c[["model", "case_id", "edema_dice", "edema_hd95", "edema_remote_fp", "pred_gt_volume_ratio", "p95_pred_to_gt_edema_distance_mm", "failure_mode", "boundary_loss_implication"]].sort_values(["case_id", "model"])),
        "",
        "## Interpretation",
        "",
        "- If `remote_component_dominant` or `empty_gt_false_positive` dominates, do not lead with recall-heavy or focal losses.",
        "- If `boundary_overreach` dominates without remote FP, a small-weight surface/distance term paired with baseline Dice/CE is reasonable.",
        "- If `volume_overprediction` dominates, conservative FP control and anatomy support should come before any recall-emphasizing loss.",
    ]
    path.write_text("\n".join(lines) + "\n")


def write_decision_table(alignment_df: pd.DataFrame, anatomy_df: pd.DataFrame, boundary_df: pd.DataFrame) -> None:
    geometry_mismatch = int(alignment_df.get("geometry_mismatch", pd.Series(dtype=bool)).fillna(False).sum()) if not alignment_df.empty else 0
    corr_align = safe_corr(alignment_df["max_body_bbox_center_distance_mm"], alignment_df["baseline_edema_hd95"]) if not alignment_df.empty else math.nan
    center_c_failures = alignment_df[(alignment_df["center"] == "CenterC") & (alignment_df["baseline_edema_hd95"] >= 20)] if not alignment_df.empty else pd.DataFrame()
    if geometry_mismatch > 0 or (not math.isnan(corr_align) and abs(corr_align) >= 0.5):
        alignment_status = "go"
        alignment_next = "SSA/alignment preprocessing smoke on fold0 complete cases."
    elif len(center_c_failures) >= 4:
        alignment_status = "watch"
        alignment_next = "Do one small visual/metadata review before deciding SSA; current proxies alone are not enough."
    else:
        alignment_status = "postpone"
        alignment_next = "Do not prioritize SSA until anatomy/boundary evidence is exhausted."

    anatomy_remote_mean = anatomy_df.groupby("model")["soft_anatomy_remote_fp_count"].mean().to_dict()
    candidate_remote = anatomy_remote_mean.get("candidate_laneA_round4", 0.0)
    baseline_remote = anatomy_remote_mean.get("baseline_nnunet501_fold0", 0.0)
    no_t2_fp = int(anatomy_df[(anatomy_df["model"] == "candidate_laneA_round4")]["no_t2_empty_gt_new_fp_risk"].sum())
    if candidate_remote > baseline_remote or no_t2_fp > 0:
        anatomy_status = "go"
        anatomy_next = "Prototype soft anatomy support/penalty with no hard deletion and explicit no-T2 FP guard."
    else:
        anatomy_status = "watch"
        anatomy_next = "Keep anatomy as reliability feature, but do not make it the only Round5 mechanism."

    mode_counts = boundary_df.groupby(["model", "failure_mode"]).size().unstack(fill_value=0)
    cand_counts = mode_counts.loc["candidate_laneA_round4"].to_dict() if "candidate_laneA_round4" in mode_counts.index else {}
    remote_like = cand_counts.get("remote_component_dominant", 0) + cand_counts.get("empty_gt_false_positive", 0)
    boundary_like = cand_counts.get("boundary_overreach", 0)
    if boundary_like > remote_like:
        boundary_status = "go"
        boundary_next = "Use baseline Dice/CE plus small-weight surface/distance loss."
    elif boundary_like > 0:
        boundary_status = "watch"
        boundary_next = "Boundary loss only as small auxiliary after anatomy/remote-FP guard."
    else:
        boundary_status = "postpone"
        boundary_next = "Do not lead with boundary loss; remote FP/volume behavior is more urgent."

    rows = [
        {
            "route": "CAA-Seg/SSA-style alignment audit",
            "status": alignment_status,
            "evidence": f"geometry_mismatch={geometry_mismatch}; spearman_center_dist_hd95={corr_align if not math.isnan(corr_align) else 'NA'}; CenterC_hd95>=20_cases={len(center_c_failures)}",
            "next_action": alignment_next,
        },
        {
            "route": "anatomy-guided cascade / soft prior",
            "status": anatomy_status,
            "evidence": f"candidate_mean_soft_remote={candidate_remote:.3f}; baseline_mean_soft_remote={baseline_remote:.3f}; candidate_no_t2_empty_gt_fp_cases={no_t2_fp}",
            "next_action": anatomy_next,
        },
        {
            "route": "conservative boundary/distance objective",
            "status": boundary_status,
            "evidence": f"candidate_remote_or_empty_fp_modes={remote_like}; candidate_boundary_overreach_modes={boundary_like}",
            "next_action": boundary_next,
        },
    ]
    decision_df = pd.DataFrame(rows)
    (OUT_DIR / "round5_laneA_decision_table.md").write_text(
        "# Lane A Round5 Decision Table\n\n"
        + md_table(decision_df)
        + "\n\n"
        + "Decision rule: only `go` routes may enter a bounded one-mechanism smoke. No route is allowed to expand folds or create validation submissions from this audit alone.\n"
    )


def write_prompt() -> None:
    text = """# Next Implementation Prompt Draft

你现在在 `/overflow/htzhu/CARE` 中工作。请执行 Lane A Round5 的下一步 bounded one-mechanism smoke，只能基于 `results/diagnostics/care_myocardium/laneA_myops/round05_mechanism_integration_audit/round5_laneA_decision_table.md` 中标记为 `go` 的机制路线选择一个最小实验。

禁止训练 full schedule、禁止提交 validation zip、禁止上传、禁止下载权重、禁止拉大型外部 repo、禁止扩 fold1-4、禁止把 no-T2 empty-GT 当作强负样本、禁止 hard anatomy deletion。若选择 alignment，只做 CARE fold0 complete-case SSA/alignment preprocessing smoke；若选择 anatomy，只做 soft prior/input/loss/penalty smoke；若选择 boundary，只做 baseline Dice/CE + small-weight surface/distance auxiliary smoke，并保留 scar class_5 guardrail。

必须同时报告 `myops_edema` 和 `myops_scar`，并按 T2-present GT-positive、complete-modality、CenterC、no-T2 empty-GT 分组。Dice、HD、HD95、component count、remote FP、volume ratio 必须同时报告。任何 Dice gain 伴随 HD95/component/remote FP 回退，或任何来自 empty-GT artifact 的 improvement，都必须 fail。
"""
    (OUT_DIR / "round5_next_implementation_prompt.md").write_text(text)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PLAN_PATH, OUT_DIR / "round5_laneA_plan.md")
    metrics = pd.read_csv(METRICS_CSV)
    align = alignment_audit(metrics)
    anatomy = anatomy_audit(metrics)
    boundary = boundary_audit(metrics, anatomy)
    align.to_csv(OUT_DIR / "alignment_feasibility_audit.csv", index=False)
    anatomy.to_csv(OUT_DIR / "anatomy_soft_prior_feasibility.csv", index=False)
    boundary.to_csv(OUT_DIR / "boundary_distance_failure_audit.csv", index=False)
    write_alignment_md(align, metrics)
    write_anatomy_md(anatomy)
    write_boundary_md(boundary)
    write_decision_table(align, anatomy, boundary)
    write_prompt()
    print(f"Wrote Round5 mechanism audit outputs to {OUT_DIR}")


if __name__ == "__main__":
    main()
