#!/usr/bin/env python3
"""Lane A hard-case failure analysis from existing outputs only.

This script reads existing CARE Myocardium Lane A diagnostics and predictions,
then writes cross-round hard-case tables and legend-bearing overlays. It does
not train models, submit jobs, create validation packages, or modify existing
predictions.
"""

from __future__ import annotations

import csv
import math
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import SimpleITK as sitk
from matplotlib.patches import Patch
from scipy.ndimage import generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/hard_case_analysis_20260525"
OVERLAY_ROOT = OUT_ROOT / "overlays"
os.environ.setdefault("MPLCONFIGDIR", str(OUT_ROOT / "mpl_cache"))

FOCUS_CASES = ["Case2031", "Case3011", "Case3012", "Case3040"]
EDEMA_COMPACT = 4
SCAR_COMPACT = 5
RAW_EDEMA = 1220
RAW_SCAR = 2221
RAW_ANATOMY = {200, 500, 600}

BASELINE_PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)
R10_PRED_DIR = (
    REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/round10_edema_refiner/"
    "predictions/laneA_r10_edema_residual_refiner_fold0_very_short/validation"
)
R11_PRED_DIR = (
    REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/round11_component_safe_refiner/"
    "predictions/laneA_r11_bidirectional_edema_refiner_fold0_very_short/validation"
)
R16F_PRED_DIR = (
    REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/"
    "R16_F_small_modality_conditioned_moe_fold0_vs/validation_predictions"
)

METRIC_FILES = {
    "round11_failure_case_table": REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/round11_component_safe_refiner/"
    "failure_case_summary/round11_failure_case_table.csv",
    "round11_residual_fusion_audit": REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/round11_component_safe_refiner/"
    "failure_case_summary/round11_residual_fusion_audit.csv",
    "round12_case_metrics": REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/round12_refiner_salvage_high_upside_transition/"
    "round12_baseline_round10_round11_case_metrics.csv",
    "round14_focus_table": REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/round14_feature_augmented_calibrator/"
    "case2031_3011_3012_3040_table.csv",
    "round15_focus_table": REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/round15_deepresearch_portfolio/"
    "case2031_3011_3012_3040_table.csv",
    "round16_flags": REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/"
    "round16_case_level_failure_flags.csv",
    "round16_f_case_metrics": REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/"
    "R16_F_small_modality_conditioned_moe_fold0_vs/fold0_very_short_case_metrics.csv",
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_img(path: Path) -> tuple[np.ndarray, sitk.Image]:
    img = sitk.ReadImage(str(path))
    return sitk.GetArrayFromImage(img), img


def compact_gt(raw: np.ndarray) -> np.ndarray:
    out = np.zeros(raw.shape, dtype=np.uint8)
    out[raw == 200] = 1
    out[raw == 500] = 2
    out[raw == 600] = 3
    out[raw == RAW_EDEMA] = EDEMA_COMPACT
    out[raw == RAW_SCAR] = SCAR_COMPACT
    return out


def case_center(case_id: str) -> str:
    return {"2": "CenterB", "3": "CenterC"}.get(case_id[4], f"Center{case_id[4]}")


def case_dir(case_id: str) -> Path:
    center = case_center(case_id)
    return REPO_ROOT / "data/CARE_Challenge/MyoPS_train" / center / case_id


def load_case(case_id: str) -> dict[str, np.ndarray]:
    cdir = case_dir(case_id)
    gt_raw, gt_img = read_img(cdir / f"{case_id}_gd.nii.gz")
    t2, _ = read_img(cdir / f"{case_id}_T2.nii.gz")
    lge, _ = read_img(cdir / f"{case_id}_LGE.nii.gz")
    baseline, _ = read_img(BASELINE_PRED_DIR / f"{case_id}.nii.gz")
    r10, _ = read_img(R10_PRED_DIR / f"{case_id}.nii.gz")
    r11, _ = read_img(R11_PRED_DIR / f"{case_id}.nii.gz")
    r16f, _ = read_img(R16F_PRED_DIR / f"{case_id}.nii.gz")
    probs = np.load(BASELINE_PRED_DIR / f"{case_id}.npz")["probabilities"]
    gt = compact_gt(gt_raw)
    spacing = tuple(float(v) for v in gt_img.GetSpacing())[::-1]
    return {
        "gt_raw": gt_raw,
        "gt": gt,
        "t2": t2.astype(np.float32),
        "lge": lge.astype(np.float32),
        "baseline": baseline,
        "round10": r10,
        "round11": r11,
        "round16f": r16f,
        "baseline_edema_prob": probs[EDEMA_COMPACT],
        "spacing": np.asarray(spacing, dtype=np.float32),
    }


def norm_slice(arr: np.ndarray, z: int) -> np.ndarray:
    sl = arr[z].astype(np.float32)
    vals = sl[np.isfinite(sl)]
    if vals.size == 0:
        return np.zeros_like(sl)
    lo, hi = np.percentile(vals, [1, 99])
    if hi <= lo:
        return np.zeros_like(sl)
    return np.clip((sl - lo) / (hi - lo), 0, 1)


def overlay_mask(ax, mask: np.ndarray, color: str, alpha: float = 0.30) -> None:
    if not mask.any():
        return
    rgba = np.zeros(mask.shape + (4,), dtype=float)
    colors = {
        "green": (0.0, 1.0, 0.0),
        "blue": (0.05, 0.25, 1.0),
        "orange": (1.0, 0.55, 0.0),
        "red": (1.0, 0.0, 0.0),
        "purple": (0.55, 0.0, 0.8),
        "cyan": (0.0, 1.0, 1.0),
        "yellow": (1.0, 0.95, 0.0),
    }[color]
    rgba[mask, :3] = colors
    rgba[mask, 3] = alpha
    ax.imshow(rgba)


def contour(ax, mask: np.ndarray, color: str, linewidth: float = 1.4, label: str | None = None) -> None:
    if mask.any():
        ax.contour(mask.astype(float), levels=[0.5], colors=[color], linewidths=linewidth)
    if label:
        ax.plot([], [], color=color, linewidth=linewidth, label=label)


def largest_component_fraction(mask: np.ndarray) -> float:
    cc, n = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    total = int(mask.sum())
    if total == 0 or n == 0:
        return 0.0
    sizes = [(cc == i).sum() for i in range(1, n + 1)]
    return float(max(sizes) / total)


def choose_slices(data: dict[str, np.ndarray]) -> list[int]:
    gt = data["gt"] == EDEMA_COMPACT
    union = gt.copy()
    for key in ("baseline", "round10", "round11", "round16f"):
        union |= data[key] == EDEMA_COMPACT
    scores = union.reshape(union.shape[0], -1).sum(axis=1)
    if scores.max() == 0:
        return [union.shape[0] // 2]
    best = int(np.argmax(scores))
    extras = [z for z in range(union.shape[0]) if z != best and scores[z] > 0]
    return [best] + extras[:1]


def make_overlay(case_id: str, data: dict[str, np.ndarray], z: int) -> Path:
    gt_e = data["gt"] == EDEMA_COMPACT
    gt_s = data["gt"] == SCAR_COMPACT
    base_e = data["baseline"] == EDEMA_COMPACT
    r11_e = data["round11"] == EDEMA_COMPACT
    r16_e = data["round16f"] == EDEMA_COMPACT
    base_s = data["baseline"] == SCAR_COMPACT
    anatomy = np.isin(data["gt_raw"], list(RAW_ANATOMY))

    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
    fig.suptitle(
        f"{case_id} hard-case overlay, slice z={z}; green=GT edema, blue=baseline, orange=Round11, red=Round16F",
        fontsize=13,
    )

    panels = [
        (axes[0, 0], "T2 + baseline vs GT", data["t2"], [(gt_e, "green", "GT edema"), (base_e, "blue", "baseline edema")]),
        (axes[0, 1], "T2 + Round11 vs GT", data["t2"], [(gt_e, "green", "GT edema"), (r11_e, "orange", "Round11 edema")]),
        (axes[0, 2], "T2 + Round16F vs GT", data["t2"], [(gt_e, "green", "GT edema"), (r16_e, "red", "Round16F edema")]),
        (axes[1, 0], "LGE + scar guardrail", data["lge"], [(gt_s, "yellow", "GT scar"), (base_s, "cyan", "baseline scar")]),
    ]
    for ax, title, img, masks in panels:
        ax.imshow(norm_slice(img, z), cmap="gray")
        for mask, color, label_name in masks:
            contour(ax, mask[z], color, label=label_name)
        ax.set_title(title)
        ax.axis("off")

    ax = axes[1, 1]
    ax.imshow(norm_slice(data["t2"], z), cmap="gray")
    added = r11_e & ~base_e
    removed = base_e & ~r11_e
    overlay_mask(ax, added[z], "orange", 0.42)
    overlay_mask(ax, removed[z], "purple", 0.42)
    contour(ax, gt_e[z], "green", label="GT edema")
    ax.set_title("Round11 diff vs baseline: orange=added, purple=removed")
    ax.axis("off")

    ax = axes[1, 2]
    ax.imshow(norm_slice(data["t2"], z), cmap="gray")
    added_f = r16_e & ~base_e
    removed_f = base_e & ~r16_e
    overlay_mask(ax, added_f[z], "red", 0.32)
    overlay_mask(ax, removed_f[z], "purple", 0.42)
    contour(ax, gt_e[z], "green", label="GT edema")
    contour(ax, anatomy[z], "cyan", linewidth=0.9, label="GT anatomy support")
    ax.set_title("Round16F diff + anatomy support")
    ax.axis("off")

    handles = [
        Patch(facecolor=(0, 1, 0, 0.3), edgecolor="green", label="GT edema"),
        Patch(facecolor=(0.05, 0.25, 1, 0.3), edgecolor="blue", label="baseline edema"),
        Patch(facecolor=(1, 0.55, 0, 0.35), edgecolor="orange", label="Round11 added/pred"),
        Patch(facecolor=(1, 0, 0, 0.3), edgecolor="red", label="Round16F added/pred"),
        Patch(facecolor=(0.55, 0, 0.8, 0.35), edgecolor="purple", label="removed vs baseline"),
        Patch(facecolor=(0, 1, 1, 0.0), edgecolor="cyan", label="anatomy/scar support"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=10)
    out = OVERLAY_ROOT / f"{case_id}_z{z:03d}_hard_case_overlay.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def summarize_prediction(case_id: str, model: str, pred: np.ndarray, gt: np.ndarray) -> dict[str, object]:
    pred_e = pred == EDEMA_COMPACT
    gt_e = gt == EDEMA_COMPACT
    inter = int((pred_e & gt_e).sum())
    denom = int(pred_e.sum() + gt_e.sum())
    dice = 1.0 if denom == 0 else 2.0 * inter / denom
    return {
        "case_id": case_id,
        "model": model,
        "pred_edema_voxels": int(pred_e.sum()),
        "gt_edema_voxels": int(gt_e.sum()),
        "quick_edema_dice": dice,
        "component_count": int(label(pred_e, structure=generate_binary_structure(pred_e.ndim, 1))[1]),
        "largest_component_fraction": largest_component_fraction(pred_e),
    }


def build_cross_round_tables() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    reason_rows: list[dict[str, object]] = []

    r11 = read_csv(METRIC_FILES["round11_failure_case_table"])
    if not r11.empty:
        for _, row in r11[r11["case_id"].isin(FOCUS_CASES)].iterrows():
            rows.append({"source": "round11_failure_case_table", **row.to_dict()})

    r12 = read_csv(METRIC_FILES["round12_case_metrics"])
    if not r12.empty:
        for _, row in r12[r12["case_id"].isin(FOCUS_CASES)].iterrows():
            rows.append({"source": "round12_case_metrics", **row.to_dict()})

    for source in ("round14_focus_table", "round15_focus_table"):
        df = read_csv(METRIC_FILES[source])
        if not df.empty:
            case_col = "case_id"
            for _, row in df[df[case_col].isin(FOCUS_CASES)].iterrows():
                rows.append({"source": source, **row.to_dict()})

    r16 = read_csv(METRIC_FILES["round16_flags"])
    if not r16.empty:
        for _, row in r16[r16["case_id"].isin(FOCUS_CASES)].iterrows():
            rows.append({"source": "round16_case_level_failure_flags", **row.to_dict()})

    residual = read_csv(METRIC_FILES["round11_residual_fusion_audit"])
    if not residual.empty:
        keep = residual[residual["case_id"].isin(FOCUS_CASES)]
        for _, row in keep.iterrows():
            reason_rows.append(
                {
                    "case_id": row.get("case_id"),
                    "stage": row.get("stage"),
                    "failure_reason_tag": row.get("failure_reason_tag"),
                    "added_voxels": row.get("added_voxels"),
                    "raw_added_voxels_before_component_fallback": row.get("raw_added_voxels_before_component_fallback"),
                    "component_fallback_applied": row.get("component_fallback_applied"),
                    "added_component_count": row.get("added_component_count"),
                    "added_components_with_gt_overlap": row.get("added_components_with_gt_overlap"),
                    "added_gt_overlap_voxels": row.get("added_gt_overlap_voxels"),
                    "added_mean_distance_to_gt_edema_mm": row.get("added_mean_distance_to_gt_edema_mm"),
                    "added_mean_t2_intensity_norm": row.get("added_mean_t2_intensity_norm"),
                    "delta_dice_vs_baseline": row.get("delta_dice_vs_baseline"),
                    "delta_hd95_improvement_vs_baseline": row.get("delta_hd95_improvement_vs_baseline"),
                }
            )
    return rows, reason_rows


def make_summary(metrics_rows: list[dict[str, object]], reason_rows: list[dict[str, object]], overlay_rows: list[dict[str, object]]) -> None:
    lines: list[str] = []
    lines.append("# Lane A hard-case failure analysis, 2026-05-25")
    lines.append("")
    lines.append("Scope: read-only analysis of existing Round10-Round16 outputs. No training, Slurm submission, validation zip, upload, weight download, or prediction mutation was performed.")
    lines.append("")
    lines.append("## Main conclusion")
    lines.append("")
    lines.append("- The recurring hard cases are not isolated postprocess errors. Case3011 and Case3040 are CenterC complete-modality T2-present GT-positive edema cases where residual/calibrator routes tend to add weakly supported remote or edge edema, while nnU-Net already has poor edema localization.")
    lines.append("- Case2031 has some Dice-positive local additions but remains fragmentation-dominated; HD95 does not become clean.")
    lines.append("- Case3012 is a large edema target with many small components; component-safe fallback prevents Round11 from changing it, which keeps safety but also prevents meaningful correction.")
    lines.append("- Round16 A/C/E mostly fell back to baseline with no target improvement. Round16 F changed edema aggressively and collapsed target metrics, producing enormous edema overprediction while scar stayed unchanged.")
    lines.append("")
    lines.append("## Focus case interpretation")
    lines.append("")
    focus = [
        {
            "case": "Case2031",
            "center": "CenterB",
            "reason": "threshold_fragmentation; refiner_random_edge_activation; T2_support_weak_or_ambiguous",
            "interpretation": "local additions can raise Dice slightly, but many tiny fragments keep component/HD95 unclean.",
        },
        {
            "case": "Case3011",
            "center": "CenterC",
            "reason": "add_residual_remote_island; T2_support_weak_or_ambiguous",
            "interpretation": "baseline already overpredicts volume; Round11 adds weakly supported voxels and remote FP worsens.",
        },
        {
            "case": "Case3012",
            "center": "CenterC",
            "reason": "component_safe_fallback_triggered; baseline undercoverage/fragmentation",
            "interpretation": "fallback protects component safety but blocks useful correction; large target remains undercovered.",
        },
        {
            "case": "Case3040",
            "center": "CenterC",
            "reason": "refiner_random_edge_activation; add_residual_remote_island; T2_support_weak_or_ambiguous",
            "interpretation": "very high baseline pred/GT volume ratio worsens under residual additions; Round11 remote FP rises.",
        },
    ]
    lines += md_table(focus, ["case", "center", "reason", "interpretation"])
    lines.append("")
    lines.append("## Key metric snippets")
    lines.append("")
    lines.append("- Round11 failure table: baseline vs Round10 vs Round11 edema Dice/HD95/component/remote FP is preserved in `hard_case_cross_round_metrics.csv`.")
    lines.append("- Round11 residual fusion audit: residual behavior and failure tags are preserved in `hard_case_failure_reasons.csv`.")
    lines.append("- Overlay PNGs are listed in `overlay_manifest.csv`; each image has a legend and uses T2/LGE backgrounds with GT, baseline, Round11, and Round16F overlays.")
    lines.append("- `hard_case_metric_panel.png` summarizes Dice, HD95, component count, and pred/GT volume ratio for the focus cases.")
    lines.append("")
    lines.append("## Why the segmentation is poor")
    lines.append("")
    lines.append("1. **CenterC T2-present edema localization is intrinsically weak**: baseline Dice is already low on Case3011/3040, and learned residuals add voxels in ambiguous T2 support regions rather than true connected edema.")
    lines.append("2. **Residual/refiner models were safe for scar/no-T2 but not effective for edema correction**: scar remains unchanged, but CenterC remote FP and HD/component guardrails fail.")
    lines.append("3. **Feature-only and fallback rules are too conservative**: strict support filters avoid hard failure but mostly reproduce baseline and do not fix CenterC.")
    lines.append("4. **The MoE-style Round16 F failure is a representation/fusion collapse, not a subtle metric issue**: Dice drops close to zero and pred/GT volume ratio explodes on focus cases.")
    lines.append("")
    lines.append("## Recommended next analysis before Round17 training")
    lines.append("")
    lines.append("- Use the overlay set to manually inspect whether CenterC edema ambiguity is T2 intensity, LGE/T2 mismatch, or label/topology ambiguity.")
    lines.append("- If continuing modeling, prioritize a stronger representation or pretrained backbone route with compliance audit, not another scalar loss/refiner threshold.")
    lines.append("- Keep refiner/calibrator only as a safe substrate or optional fallback; it is not the main route unless a new support signal changes CenterC behavior.")
    lines.append("")
    lines.append("## Overlay manifest")
    lines += md_table(overlay_rows, ["case_id", "slice_z", "overlay_path"])
    lines.append("")
    (OUT_ROOT / "hard_case_analysis_summary.md").write_text("\n".join(lines), encoding="utf-8")


def md_table(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(col, "")).replace("|", "\\|") for col in columns) + " |")
    return out


def make_metric_panel() -> Path:
    rows: list[dict[str, object]] = []
    r12 = read_csv(METRIC_FILES["round12_case_metrics"])
    if not r12.empty:
        focus = r12[r12["case_id"].isin(FOCUS_CASES)].copy()
        model_map = {
            "baseline_nnunet501_fold0": "baseline",
            "round10_add_only_refiner": "round10",
            "round11_bidirectional_refiner": "round11",
        }
        focus = focus[focus["model"].isin(model_map)]
        for _, row in focus.iterrows():
            rows.append(
                {
                    "case_id": row["case_id"],
                    "model": model_map[row["model"]],
                    "dice": float(row["myops_edema_dice"]),
                    "hd95": float(row["myops_edema_hd95"]),
                    "components": float(row["myops_edema_component_count"]),
                    "volume_ratio": float(row["myops_edema_pred_gt_volume_ratio"]),
                }
            )
    r16f = read_csv(METRIC_FILES["round16_f_case_metrics"])
    if not r16f.empty:
        focus = r16f[
            (r16f["case_id"].isin(FOCUS_CASES))
            & (r16f["model"] == "R16_F_small_modality_conditioned_moe_fold0_vs")
        ]
        for _, row in focus.iterrows():
            rows.append(
                {
                    "case_id": row["case_id"],
                    "model": "round16F",
                    "dice": float(row["myops_edema_dice"]),
                    "hd95": float(row["myops_edema_hd95"]),
                    "components": float(row["myops_edema_component_count"]),
                    "volume_ratio": float(row["myops_edema_pred_gt_volume_ratio"]),
                }
            )
    if not rows:
        raise RuntimeError("No metric rows available for metric panel")
    df = pd.DataFrame(rows)
    write_csv(
        OUT_ROOT / "hard_case_metric_panel_source.csv",
        df.to_dict("records"),
        ["case_id", "model", "dice", "hd95", "components", "volume_ratio"],
    )

    metrics = [
        ("dice", "Edema Dice", False),
        ("hd95", "Edema HD95", True),
        ("components", "Component count", True),
        ("volume_ratio", "Pred/GT volume ratio", True),
    ]
    models = ["baseline", "round10", "round11", "round16F"]
    colors = {"baseline": "#1f77b4", "round10": "#ff7f0e", "round11": "#9467bd", "round16F": "#d62728"}
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    fig.suptitle("Lane A hard-case metric panel; lower is better except Dice", fontsize=14)
    x = np.arange(len(FOCUS_CASES))
    width = 0.18
    for ax, (metric, title, log_y) in zip(axes.ravel(), metrics):
        for i, model in enumerate(models):
            sub = df[df["model"] == model].set_index("case_id")
            vals = [float(sub.loc[c, metric]) if c in sub.index else np.nan for c in FOCUS_CASES]
            ax.bar(x + (i - 1.5) * width, vals, width=width, label=model, color=colors[model])
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(FOCUS_CASES, rotation=25, ha="right")
        if log_y:
            ax.set_yscale("log")
        ax.grid(axis="y", alpha=0.25)
    axes[0, 0].legend(ncol=4, fontsize=9)
    out = OUT_ROOT / "hard_case_metric_panel.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    OVERLAY_ROOT.mkdir(parents=True, exist_ok=True)

    metrics_rows, reason_rows = build_cross_round_tables()
    if metrics_rows:
        fieldnames = sorted({key for row in metrics_rows for key in row})
        write_csv(OUT_ROOT / "hard_case_cross_round_metrics.csv", metrics_rows, fieldnames)
    if reason_rows:
        fieldnames = sorted({key for row in reason_rows for key in row})
        write_csv(OUT_ROOT / "hard_case_failure_reasons.csv", reason_rows, fieldnames)

    quick_rows: list[dict[str, object]] = []
    overlay_rows: list[dict[str, object]] = []
    for case_id in FOCUS_CASES:
        data = load_case(case_id)
        for name in ("baseline", "round10", "round11", "round16f"):
            quick_rows.append(summarize_prediction(case_id, name, data[name], data["gt"]))
        for z in choose_slices(data):
            overlay = make_overlay(case_id, data, z)
            overlay_rows.append({"case_id": case_id, "slice_z": z, "overlay_path": str(overlay.relative_to(REPO_ROOT))})

    write_csv(
        OUT_ROOT / "hard_case_quick_voxel_summary.csv",
        quick_rows,
        [
            "case_id",
            "model",
            "pred_edema_voxels",
            "gt_edema_voxels",
            "quick_edema_dice",
            "component_count",
            "largest_component_fraction",
        ],
    )
    write_csv(OUT_ROOT / "overlay_manifest.csv", overlay_rows, ["case_id", "slice_z", "overlay_path"])
    make_metric_panel()
    make_summary(metrics_rows, reason_rows, overlay_rows)

    print(f"Wrote {OUT_ROOT}")
    print(f"Overlays: {len(overlay_rows)}")


if __name__ == "__main__":
    main()
