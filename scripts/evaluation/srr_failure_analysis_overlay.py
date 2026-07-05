#!/usr/bin/env python3
"""Generate SRR-v2.5 failure overlays and mechanism traces from existing outputs."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/users/a/e/aereinh/.tmp/codex-care/matplotlib")

import matplotlib.pyplot as plt
import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import collect_case_metrics, read_case, write_csv  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402


DEFAULT_RUN_DIR = (
    REPO_ROOT
    / "results/20260704_srr_v25_local_refinement_ablation/runtime_smoke/variants/srr_propref_shared_dual_dict"
)
DEFAULT_NNUNET_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_pred(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(path)
    return sitk.GetArrayFromImage(sitk.ReadImage(str(path))).astype(np.uint8, copy=False)


def safe_float(value: object) -> float | None:
    if value in (None, "", "NA", "nan"):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def parse_case_ids(text: str) -> list[str]:
    return [item.strip() for item in str(text).replace(";", ",").split(",") if item.strip()]


def pick_slice(*masks: np.ndarray) -> int:
    scores = None
    for mask in masks:
        per_slice = mask.reshape(mask.shape[0], -1).sum(axis=1)
        scores = per_slice if scores is None else scores + per_slice
    if scores is None or float(scores.max()) <= 0.0:
        return int(masks[0].shape[0] // 2)
    return int(np.argmax(scores))


def normalize_slice(image: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(image, [1, 99])
    if hi <= lo:
        return np.zeros_like(image, dtype=np.float32)
    return np.clip((image - lo) / (hi - lo), 0.0, 1.0)


def draw_mask(ax: Any, mask2d: np.ndarray, color: str, label: str, alpha: float = 0.28) -> None:
    if not bool(mask2d.any()):
        return
    overlay = np.zeros((*mask2d.shape, 4), dtype=np.float32)
    rgba = {
        "green": (0.0, 1.0, 0.0, alpha),
        "blue": (0.0, 0.35, 1.0, alpha),
        "yellow": (1.0, 0.9, 0.0, alpha),
        "red": (1.0, 0.0, 0.0, alpha),
        "magenta": (1.0, 0.0, 1.0, alpha),
    }[color]
    overlay[mask2d.astype(bool)] = rgba
    ax.imshow(overlay)
    ax.contour(mask2d.astype(float), levels=[0.5], colors=[color], linewidths=0.8)
    ax.plot([], [], color=color, label=label)


def render_overlay(
    case_id: str,
    image: np.ndarray,
    gt: np.ndarray,
    nnunet: np.ndarray,
    srr_argmax: np.ndarray,
    srr_pathology: np.ndarray,
    crop_bounds: dict[str, str],
    out_path: Path,
    *,
    class_id: int,
    metric_name: str,
) -> int:
    z = pick_slice(gt == class_id, nnunet == class_id, srr_argmax == class_id, srr_pathology == class_id)
    lge = normalize_slice(image[0, z])
    fig, axes = plt.subplots(2, 3, figsize=(12, 8), dpi=140)
    label = "scar" if class_id == 5 else "edema"
    panels = [
        (f"LGE + GT {label}", [(gt[z] == class_id, "green", f"GT {label}")]),
        (f"nnU-Net context", [(gt[z] == class_id, "green", f"GT {label}"), (nnunet[z] == class_id, "blue", f"nnU-Net {label}")]),
        (f"SRR argmax", [(gt[z] == class_id, "green", f"GT {label}"), (srr_argmax[z] == class_id, "yellow", f"SRR argmax {label}")]),
        (
            "SRR pathology-aware",
            [(gt[z] == class_id, "green", f"GT {label}"), (srr_pathology[z] == class_id, "red", f"SRR pathology-aware {label}")],
        ),
        (
            "Harm map",
            [
                ((srr_pathology[z] == class_id) & (gt[z] != class_id), "red", f"SRR {label} FP"),
                ((gt[z] == class_id) & (srr_pathology[z] != class_id), "magenta", f"SRR {label} FN"),
            ],
        ),
        ("Crop bounds", [(gt[z] == class_id, "green", f"GT {label}"), (srr_argmax[z] == class_id, "yellow", f"SRR argmax {label}")]),
    ]
    for ax, (title, masks) in zip(axes.ravel(), panels, strict=True):
        ax.imshow(lge, cmap="gray")
        for mask, color, label in masks:
            draw_mask(ax, mask, color, label)
        ax.set_title(title, fontsize=9)
        ax.axis("off")
        if title == "Crop bounds" and crop_bounds:
            z0, z1 = int(crop_bounds["z0"]), int(crop_bounds["z1"])
            if z0 <= z < z1:
                y0, y1 = int(crop_bounds["y0"]), int(crop_bounds["y1"])
                x0, x1 = int(crop_bounds["x0"]), int(crop_bounds["x1"])
                ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor="cyan", linewidth=1.5))
    for ax in axes.ravel():
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, loc="lower right", fontsize=6)
            break
    fig.suptitle(f"{case_id} {metric_name} failure overlay, slice z={z}", fontsize=11)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return z


def taxonomy_rows(case_id: str, metrics: list[dict[str, str]], bounds_by_metric: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in metrics:
        if row.get("case_id") != case_id:
            continue
        variant = row["variant"]
        remote_fp = int(float(row.get("remote_fp_count") or 0))
        components = int(float(row.get("component_count") or 0))
        dice = safe_float(row.get("dice"))
        hd95 = safe_float(row.get("hd95"))
        pred_empty = str(row.get("pred_empty", "")).lower() == "true"
        gt_empty = str(row.get("gt_empty", "")).lower() == "true"
        category = "neutral_or_minor"
        if remote_fp > 0:
            category = "remote_island;proposal_flooding_or_decode_export;refiner_overcorrection"
        elif pred_empty and not gt_empty:
            category = "missed_lesion;residual_gate_under_open_or_proposal_miss"
        elif dice is not None and dice < 0.2:
            category = "missed_lesion_or_wrong_decode"
        elif hd95 is not None and hd95 > 25.0:
            category = "boundary_or_extent_error;crop_or_roi_undercoverage"
        bounds = bounds_by_metric.get(row.get("metric_name", ""), {})
        rows.append(
            {
                "case_id": case_id,
                "variant": variant,
                "metric_name": row["metric_name"],
                "dice": row.get("dice", ""),
                "hd95": row.get("hd95", ""),
                "component_count": components,
                "remote_fp_count": remote_fp,
                "crop_volume_ratio": bounds.get("crop_volume_ratio", ""),
                "is_full_volume_crop": bounds.get("is_full_volume_crop", ""),
                "taxonomy": category,
                "evidence_level": "hard_subgroup_spatial_overlay_and_metrics",
            }
        )
    return rows


def proposal_breakdown(metrics: list[dict[str, str]], roi_rows: list[dict[str, str]], proposal_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out = []
    for row in metrics:
        candidates = [
            r
            for r in proposal_rows
            if r.get("case_id") == row.get("case_id") and r.get("metric_name") == row.get("metric_name")
        ]
        threshold = min(candidates, key=lambda r: abs(float(r.get("proposal_threshold") or 0) - 0.5)) if candidates else {}
        decode_mode = "pathology_aware" if "pathology_aware" in row["variant"] else "argmax"
        roi = next(
            (
                r
                for r in roi_rows
                if r.get("case_id") == row.get("case_id")
                and r.get("metric_name") == row.get("metric_name")
                and r.get("decode_mode") == decode_mode
            ),
            {},
        )
        out.append(
            {
                "case_id": row["case_id"],
                "decode_mode": decode_mode,
                "metric_name": row.get("metric_name", ""),
                "final_dice": row.get("dice", ""),
                "final_hd95": row.get("hd95", ""),
                "final_component_count": row.get("component_count", ""),
                "final_remote_fp_count": row.get("remote_fp_count", ""),
                "proposal_threshold": threshold.get("proposal_threshold", ""),
                "proposal_recall": threshold.get("proposal_recall", ""),
                "proposal_precision": threshold.get("proposal_precision", ""),
                "lesion_wise_recall": threshold.get("lesion_wise_recall", ""),
                "proposal_remote_fp_count": threshold.get("proposal_remote_fp_count", ""),
                "roi_gt_coverage": roi.get("gt_coverage", ""),
                "roi_pred_coverage": roi.get("pred_coverage", ""),
                "roi_outside_myocardium_ratio": roi.get("outside_myocardium_roi_ratio", ""),
            }
        )
    return out


def dictionary_trace(run_dir: Path) -> list[dict[str, object]]:
    rows = read_rows(run_dir / "retrieval_usage.csv")
    groups: dict[tuple[str, str, str], list[float]] = {}
    valid: dict[tuple[str, str, str], list[float]] = {}
    for row in rows:
        key = (row.get("semantic_task", ""), row.get("slot_group", ""), row.get("slot_kind", ""))
        value = safe_float(row.get("mean_weight"))
        vf = safe_float(row.get("valid_fraction"))
        if value is not None:
            groups.setdefault(key, []).append(value)
        if vf is not None:
            valid.setdefault(key, []).append(vf)
    out = []
    for key in sorted(groups):
        values = groups[key]
        vf = valid.get(key, [])
        out.append(
            {
                "semantic_task": key[0],
                "slot_group": key[1],
                "slot_kind": key[2],
                "mean_weight_mean": float(np.mean(values)),
                "mean_weight_max": float(np.max(values)),
                "valid_fraction_mean": "" if not vf else float(np.mean(vf)),
                "trace_scope": "training_step_retrieval_usage_not_spatial_map",
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case-id", default="Case1002")
    ap.add_argument("--case-ids", default="", help="Comma/semicolon-separated case ids. Overrides --case-id when set.")
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--srr-run-dir", type=Path, default=DEFAULT_RUN_DIR)
    ap.add_argument("--nnunet-anchor-root", type=Path, default=DEFAULT_NNUNET_ROOT)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    output_dir = args.output_dir
    overlay_dir = output_dir / "overlays"
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = load_myops_case_metadata()
    case_ids = parse_case_ids(args.case_ids) if args.case_ids else [args.case_id]
    metrics = read_rows(args.srr_run_dir / "component_hd_by_case_checkpoint_final.csv")
    roi = read_rows(args.srr_run_dir / "roi_coverage_checkpoint_final.csv")
    proposal_rows = read_rows(args.srr_run_dir / "proposal_pr_sweep_checkpoint_final.csv")
    bounds_rows = read_rows(args.srr_run_dir / "crop_bounds_checkpoint_final.csv")
    taxonomy: list[dict[str, object]] = []
    nnunet_trace: list[dict[str, object]] = []
    manifest_lines = [
        "# Overlay Manifest",
        "",
        f"- srr_run_dir: `{args.srr_run_dir}`",
        f"- cases: `{','.join(case_ids)}`",
        "- panels: LGE+GT, nnU-Net context, SRR argmax, SRR pathology-aware, harm map, crop bounds",
        "- limitation: proposal and dictionary gates are summarized in CSV traces; spatial proposal/gate maps were not exported by the smoke run.",
        "",
        "## Overlays",
        "",
        "| case_id | metric_name | selected_slice_z | overlay |",
        "| --- | --- | ---: | --- |",
    ]
    for case_id in case_ids:
        case = read_case(case_id, metadata)  # type: ignore[arg-type]
        nnunet = read_pred(args.nnunet_anchor_root / f"fold_{args.fold}" / "validation" / f"{case_id}.nii.gz")
        srr_argmax = read_pred(args.srr_run_dir / "predictions/fold_0/checkpoint_final/argmax" / f"{case_id}.nii.gz")
        srr_pathology = read_pred(args.srr_run_dir / "predictions/fold_0/checkpoint_final/pathology_aware" / f"{case_id}.nii.gz")
        bounds_by_metric = {
            row.get("metric_name", ""): row for row in bounds_rows if row.get("case_id") == case_id
        }
        taxonomy.extend(taxonomy_rows(case_id, metrics, bounds_by_metric))
        nnunet_trace.extend(collect_case_metrics("nnUNet_same_split_anchor", case, nnunet))
        for class_id, metric_name in [(5, "myops_scar"), (4, "myops_edema")]:
            if not bool(
                np.any(case.label_arr == class_id)
                or np.any(nnunet == class_id)
                or np.any(srr_argmax == class_id)
                or np.any(srr_pathology == class_id)
            ):
                continue
            overlay_path = overlay_dir / f"{case_id}_{metric_name}_failure_overlay.png"
            slice_index = render_overlay(
                case_id,
                case.image,
                case.label_arr,
                nnunet,
                srr_argmax,
                srr_pathology,
                bounds_by_metric.get(metric_name, {}),
                overlay_path,
                class_id=class_id,
                metric_name=metric_name,
            )
            manifest_lines.append(
                f"| `{case_id}` | `{metric_name}` | {slice_index} | `{overlay_path.relative_to(output_dir)}` |"
            )

    write_csv(output_dir / "case_error_taxonomy.csv", taxonomy)
    write_csv(output_dir / "proposal_vs_refiner_breakdown.csv", proposal_breakdown(metrics, roi, proposal_rows))
    write_csv(output_dir / "dictionary_gate_trace.csv", dictionary_trace(args.srr_run_dir))
    write_csv(output_dir / "nnunet_context_trace.csv", nnunet_trace)
    train_rows = [r for r in read_rows(args.srr_run_dir / "training_log.csv") if r.get("loss")]
    residual_rows = []
    for row in train_rows:
        residual_rows.append(
            {
                "variant": row.get("variant", ""),
                "step": row.get("step", ""),
                "baseline_gate_mean": row.get("baseline_gate_mean", ""),
                "baseline_residual_abs_mean": row.get("baseline_residual_abs_mean", ""),
                "baseline_preservation_loss": row.get("baseline_preservation_loss", ""),
                "baseline_preserve_voxels": row.get("baseline_preserve_voxels", ""),
                "baseline_preserve_gate_mean": row.get("baseline_preserve_gate_mean", ""),
                "refine_weight": row.get("refine_weight", ""),
                "crop_residual_abs_mean_scar": "",
            }
        )
    write_csv(output_dir / "residual_gate_trace.csv", residual_rows)
    (output_dir / "overlay_manifest.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
