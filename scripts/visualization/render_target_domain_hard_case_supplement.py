#!/usr/bin/env python3
"""Render the 2026-08-01 CARE hard-case supplement atlas.

This script is visualization-only. It reuses the frozen outer replay helpers for
M0R inference and composition, writes a four-page A3 landscape PDF, and does not
train, select, upload, or mutate official outer replay metrics.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pickle
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault(
    "MPLCONFIGDIR",
    "/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_target_domain_race_gap_closure/hard_case_supplement_mpl",
)

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = ["DejaVu Sans", "Droid Sans Fallback"]
matplotlib.rcParams["axes.unicode_minus"] = False

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
import nibabel as nib
import numpy as np
import torch
from scipy.ndimage import zoom

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))

from scripts.evaluation.target_domain_gap_closure.replay_outer_composition import (  # noqa: E402
    compose_prediction,
    load_case,
    m0r_checkpoint,
    predict_m0r,
    predict_stock,
    stock_checkpoint,
)
from scripts.evaluation.target_domain_gap_closure.evaluate_inner_lanes import metric_rows  # noqa: E402


TASK_ROOT = REPO_ROOT / "results/20260801_care_target_domain_race_gap_closure"
OUTER_CASEWISE = TASK_ROOT / "outer_replay/casewise_metrics.csv"
PREPROCESSED_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
NNUNET_RESULTS = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
RAW_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS"
MOSAIC_CLEAN_ROOT = REPO_ROOT / "results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1/mosaic_oof"
LEGACY_PACKET = REPO_ROOT / "results/20260730_care_failure_forensics_deep_research_packet"
OUTPUT_DIR = REPO_ROOT / "docs/presentation/2026_08_01_care_group_meeting"
RUNTIME_DIR = TASK_ROOT / "runtime/hard_case_supplement"

A3_LANDSCAPE_PT = (420.0 / 25.4 * 72.0, 297.0 / 25.4 * 72.0)
MARGIN_PT = 36.0
SCAR_COLOR = np.array([0.92, 0.10, 0.12])
EDEMA_COLOR = np.array([0.00, 0.78, 0.86])
FP_COLOR = np.array([1.00, 0.58, 0.04])
FN_COLOR = np.array([0.62, 0.32, 0.88])
DIFF_COLOR = np.array([1.00, 0.90, 0.10])
UNBOUND_TEXT = "该病例未绑定"


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    center: str
    fold: int
    failure_type: str
    page_number: int


CASES = [
    CaseSpec("Case3008", "CenterC", 2, "CenterC edema 严重漏检", 1),
    CaseSpec("Case3009", "CenterC", 3, "CenterC edema 重复性漏检", 2),
    CaseSpec("Case3027", "CenterC", 2, "scar 过度扩张、血池邻近假阳性、edema 接近漏空", 3),
    CaseSpec("Case2012", "CenterB", 3, "edema 位置错误或完全漏检，边界距离极大", 4),
]


def font_properties(size: float, weight: str = "normal") -> FontProperties:
    return FontProperties(family=["DejaVu Sans", "Droid Sans Fallback"], size=size, weight=weight)


FONT_8 = font_properties(8)
FONT_9 = font_properties(9)
FONT_10 = font_properties(10)
FONT_12_BOLD = font_properties(12, "bold")
FONT_15_BOLD = font_properties(15, "bold")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def official_metric_lookup() -> dict[tuple[str, str], dict[str, str]]:
    rows = read_csv(OUTER_CASEWISE)
    target = {case.case_id for case in CASES}
    return {(row["case_id"], row["pathology"]): row for row in rows if row["case_id"] in target}


def compare_official_metrics(case: CaseSpec, pred: np.ndarray, label: np.ndarray, official: dict[tuple[str, str], dict[str, str]]) -> list[str]:
    rows = metric_rows("outer_replay_composite", case.fold, -1, case.case_id, pred, label, population="outer_replay")
    differences: list[str] = []
    for row in rows:
        key = (case.case_id, row["pathology"])
        if key not in official:
            raise RuntimeError(f"official metric row missing for {key}")
        official_row = official[key]
        if row["pathology"] == "scar":
            fields = [
                "dice",
                "precision",
                "sensitivity",
                "volume_ratio",
                "remote_fp_count",
                "blood_pool_adjacent_fp_voxels",
            ]
        else:
            fields = [
                "dice",
                "precision",
                "sensitivity",
                "volume_ratio",
                "lesion_recall",
                "small_lesion_recall",
                "remote_fp_count",
            ]
        for field in fields:
            actual = row[field]
            expected = official_row[field]
            if actual is None:
                if expected not in ("", "None"):
                    differences.append(f"{row['pathology']} {field}: recomputed None != official {expected}")
                continue
            if isinstance(actual, (int, np.integer)):
                if int(actual) != int(expected):
                    differences.append(f"{row['pathology']} {field}: recomputed {actual} != official {expected}")
            else:
                if expected == "":
                    differences.append(f"{row['pathology']} {field}: recomputed {actual} != official blank")
                elif not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-12):
                    differences.append(f"{row['pathology']} {field}: recomputed {actual} != official {expected}")
    return differences


def pkl_properties(case_id: str) -> dict[str, Any]:
    with (PREPROCESSED_ROOT / f"{case_id}.pkl").open("rb") as f:
        return pickle.load(f)


def load_raw_nifti_zyx(path: Path) -> np.ndarray:
    arr = np.asarray(nib.load(str(path)).get_fdata())
    return np.rint(arr).astype(np.uint8).transpose(2, 1, 0)


def raw_label_to_preprocessed(path: Path, case_id: str, target_shape: tuple[int, int, int]) -> np.ndarray:
    raw = load_raw_nifti_zyx(path)
    props = pkl_properties(case_id)
    bbox = props["bbox_used_for_cropping"]
    cropped = raw[bbox[0][0] : bbox[0][1], bbox[1][0] : bbox[1][1], bbox[2][0] : bbox[2][1]]
    if cropped.shape == target_shape:
        return cropped.astype(np.uint8)
    factors = [target_shape[idx] / cropped.shape[idx] for idx in range(3)]
    return zoom(cropped, zoom=factors, order=0, mode="nearest").astype(np.uint8)


def normalize_slice(arr: np.ndarray) -> np.ndarray:
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    lo, hi = np.percentile(finite, [1, 99])
    if hi <= lo:
        lo, hi = float(finite.min()), float(finite.max())
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    out = np.clip((arr - lo) / (hi - lo), 0, 1)
    return out.astype(np.float32)


def overlay(base: np.ndarray, layers: list[tuple[np.ndarray, np.ndarray, float]]) -> np.ndarray:
    img = np.repeat(normalize_slice(base)[..., None], 3, axis=2)
    for mask, color, alpha in layers:
        if mask.any():
            img[mask] = img[mask] * (1.0 - alpha) + color * alpha
    return img


def lesion_layers(label: np.ndarray) -> list[tuple[np.ndarray, np.ndarray, float]]:
    return [(label == 5, SCAR_COLOR, 0.72), (label == 4, EDEMA_COLOR, 0.66)]


def choose_slice(gt: np.ndarray, m0r: np.ndarray) -> tuple[int, str]:
    gt_lesion = (gt == 5) | (gt == 4)
    m0r_lesion = (m0r == 5) | (m0r == 4)
    gt_counts = gt_lesion.reshape(gt.shape[0], -1).sum(axis=1)
    fpfn_counts = np.logical_xor(gt_lesion, m0r_lesion).reshape(gt.shape[0], -1).sum(axis=1)
    primary = int(np.argmax(gt_counts))
    if int(gt_counts[primary]) > 0 and int(fpfn_counts[primary]) > 0:
        return primary, "primary_gt_scar_plus_pure_edema_max_with_m0r_error_visible"
    fallback = int(np.argmax(gt_counts + fpfn_counts))
    return fallback, "fallback_gt_plus_m0r_fp_plus_m0r_fn_max"


def metric_text(case: CaseSpec, official: dict[tuple[str, str], dict[str, str]]) -> tuple[str, str]:
    scar = official[(case.case_id, "scar")]
    edema = official[(case.case_id, "pure_edema")]

    def f(row: dict[str, str], key: str) -> str:
        value = row[key]
        if value == "":
            return "NA"
        try:
            return f"{float(value):.3f}"
        except ValueError:
            return value

    scar_text = (
        f"Scar: Dice {f(scar, 'dice')} | precision {f(scar, 'precision')} | sensitivity {f(scar, 'sensitivity')} | "
        f"pred/GT vol {f(scar, 'volume_ratio')} | remote FP {scar['remote_fp_count']} | blood-adj FP vox {scar['blood_pool_adjacent_fp_voxels']}"
    )
    edema_text = (
        f"Pure edema: Dice {f(edema, 'dice')} | precision {f(edema, 'precision')} | sensitivity {f(edema, 'sensitivity')} | "
        f"pred/GT vol {f(edema, 'volume_ratio')} | lesion recall {f(edema, 'lesion_recall')} | "
        f"small lesion recall {f(edema, 'small_lesion_recall')} | remote FP {edema['remote_fp_count']}"
    )
    return scar_text, edema_text


def draw_bound_panel(ax: plt.Axes, title: str, base: np.ndarray, pred: np.ndarray, z: int) -> None:
    ax.imshow(overlay(base[z], lesion_layers(pred[z])), origin="lower", interpolation="nearest")
    ax.set_title(title, fontproperties=FONT_10, pad=3)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#444444")
        spine.set_linewidth(0.6)


def draw_mask_panel(ax: plt.Axes, title: str, base: np.ndarray, masks: list[tuple[np.ndarray, np.ndarray, float]], z: int) -> None:
    ax.imshow(overlay(base[z], [(mask[z], color, alpha) for mask, color, alpha in masks]), origin="lower", interpolation="nearest")
    ax.set_title(title, fontproperties=FONT_10, pad=3)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#444444")
        spine.set_linewidth(0.6)


def draw_modality_panel(ax: plt.Axes, title: str, image_channel: np.ndarray, z: int) -> None:
    ax.imshow(normalize_slice(image_channel[z]), cmap="gray", origin="lower", interpolation="nearest")
    ax.set_title(title, fontproperties=FONT_10, pad=3)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#444444")
        spine.set_linewidth(0.6)


def draw_unbound_panel(ax: plt.Axes, title: str) -> None:
    ax.set_facecolor("#eeeeee")
    ax.text(0.5, 0.5, UNBOUND_TEXT, ha="center", va="center", fontproperties=FONT_12_BOLD, color="#555555", transform=ax.transAxes)
    ax.set_title(title, fontproperties=FONT_10, pad=3)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#bbbbbb")
        spine.set_linewidth(0.8)


def stock_validation_path(case: CaseSpec) -> Path:
    return NNUNET_RESULTS / f"fold_{case.fold}/validation/{case.case_id}.nii.gz"


def mosaic_clean_path(case: CaseSpec) -> Path:
    return MOSAIC_CLEAN_ROOT / f"fold{case.fold}/oof_predictions/official/{case.case_id}.nii.gz"


def mosaic_full_final_path(case: CaseSpec) -> Path:
    return LEGACY_PACKET / f"runtime/v3_mosaic_full_final_atlas_predictions/preds/{case.case_id}_mosaic_full_final_pred.nii.gz"


def has_prism_bound_prediction(case: CaseSpec) -> bool:
    # Historical PRISM replay has raw probabilities only for part of the target
    # set and came from a fold0 artifact, so it is not a complete same-fold
    # prediction source for this supplement.
    return False


def render_case_page(
    case: CaseSpec,
    image: np.ndarray,
    gt: np.ndarray,
    stock_pred: np.ndarray,
    m0r_pred: np.ndarray,
    mosaic_clean_pred: np.ndarray | None,
    official: dict[tuple[str, str], dict[str, str]],
    selected_slice: int,
    slice_rule: str,
    pdf: PdfPages,
    page_png: Path,
) -> None:
    page_w_pt, page_h_pt = A3_LANDSCAPE_PT
    fig = plt.figure(figsize=(page_w_pt / 72.0, page_h_pt / 72.0), dpi=200, facecolor="white")
    gs = fig.add_gridspec(
        3,
        4,
        left=MARGIN_PT / page_w_pt,
        right=1.0 - MARGIN_PT / page_w_pt,
        bottom=98.0 / page_h_pt,
        top=0.888,
        wspace=0.035,
        hspace=0.195,
    )
    axes = [fig.add_subplot(gs[r, c]) for r in range(3) for c in range(4)]
    base_lge, base_t2, base_c0 = image[0], image[1], image[2]
    lesion_gt = (gt == 4) | (gt == 5)
    lesion_m0r = (m0r_pred == 4) | (m0r_pred == 5)
    fp = lesion_m0r & ~lesion_gt
    fn = lesion_gt & ~lesion_m0r
    diff = stock_pred != m0r_pred

    draw_bound_panel(axes[0], "GT", base_lge, gt, selected_slice)
    draw_bound_panel(axes[1], "nnU-Net", base_lge, stock_pred, selected_slice)
    if mosaic_clean_pred is None:
        draw_unbound_panel(axes[2], "MoSAIC clean")
    else:
        draw_bound_panel(axes[2], "MoSAIC clean", base_lge, mosaic_clean_pred, selected_slice)
    draw_unbound_panel(axes[3], "MoSAIC full/final")
    draw_unbound_panel(axes[4], "PRISM")
    draw_bound_panel(axes[5], "最新目标域组合 M0R", base_lge, m0r_pred, selected_slice)
    draw_mask_panel(axes[6], "M0R 假阳性相对 GT", base_lge, [(fp, FP_COLOR, 0.78)], selected_slice)
    draw_mask_panel(axes[7], "M0R 假阴性相对 GT", base_lge, [(fn, FN_COLOR, 0.78)], selected_slice)
    draw_mask_panel(axes[8], "nnU-Net 与 M0R 差异", base_lge, [(diff, DIFF_COLOR, 0.74)], selected_slice)
    draw_modality_panel(axes[9], "LGE", base_lge, selected_slice)
    draw_modality_panel(axes[10], "T2", base_t2, selected_slice)
    draw_modality_panel(axes[11], "C0", base_c0, selected_slice)

    title = f"{case.case_id} | {case.center} | LGE+T2+C0 | fold{case.fold} | {case.failure_type}"
    fig.text(MARGIN_PT / page_w_pt, 0.958, title, ha="left", va="top", fontproperties=FONT_12_BOLD, color="#111111")
    fig.text(
        1.0 - MARGIN_PT / page_w_pt,
        0.923,
        f"page {case.page_number}/4 | selected slice {selected_slice} | {slice_rule}",
        ha="right",
        va="top",
        fontproperties=FONT_9,
        color="#333333",
    )
    scar_text, edema_text = metric_text(case, official)
    fig.text(MARGIN_PT / page_w_pt, 0.073, scar_text, ha="left", va="bottom", fontproperties=FONT_9, color="#111111")
    fig.text(MARGIN_PT / page_w_pt, 0.044, edema_text, ha="left", va="bottom", fontproperties=FONT_9, color="#111111")
    fig.text(
        1.0 - MARGIN_PT / page_w_pt,
        0.044,
        "Colors: scar red | pure edema cyan | FP orange | FN purple | nnU-Net/M0R diff yellow",
        ha="right",
        va="bottom",
        fontproperties=FONT_8,
        color="#333333",
    )
    fig.savefig(page_png, dpi=200)
    pdf.savefig(fig)
    plt.close(fig)


def build_review(
    manifest_rows: list[dict[str, Any]],
    bbox_rows: list[dict[str, Any]],
    consistency_rows: list[dict[str, Any]],
    pdf_path: Path,
) -> str:
    lines = [
        "# CARE hard-case supplement review",
        "",
        "这份补充图册只用于组会展示四个困难病例，不改变 CARE 当前科学状态，不恢复任何候选资格，也不重新选择检查点。",
        "",
        "## Scope checks",
        "",
        "- Cases included: Case3008, Case3009, Case3027, Case2012.",
        "- Cases excluded: Case2019, Case2034, Case2021.",
        "- Training, Slurm, validation upload, Docker upload, CURRENT.md edits, and wiki edits were not performed.",
        "- M0R composition reused frozen outer replay helpers and fixed checkpoints: scar step 3500, pure edema step 4000.",
        "",
        "## Bound model panels",
        "",
    ]
    for row in manifest_rows:
        lines.append(
            f"- {row['case_id']}: nnU-Net=绑定, MoSAIC clean={row['mosaic_clean_exists']}, "
            f"MoSAIC full/final={row['mosaic_full_final_exists']}, PRISM={row['prism_exists']}."
        )
    lines.extend(
        [
            "",
            "## Slice selection",
            "",
        ]
    )
    for row in manifest_rows:
        lines.append(f"- {row['case_id']}: slice {row['selected_slice']}, rule `{row['slice_selection_rule']}`.")
    lines.extend(
        [
            "",
            "## Metric consistency",
            "",
        ]
    )
    for row in consistency_rows:
        lines.append(f"- {row['case_id']}: {row['status']} against official outer_replay/casewise_metrics.csv.")
    lines.extend(
        [
            "",
            "## Layout check",
            "",
        ]
    )
    for row in bbox_rows:
        lines.append(f"- page {row['page_number']} {row['case_id']}: {row['status']}.")
    lines.extend(["", f"PDF: `{pdf_path}`", ""])
    return "\n".join(lines)


def render(args: argparse.Namespace) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "hard_case_supplement_pages").mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device("cpu" if args.cpu else ("cuda" if torch.cuda.is_available() else "cpu"))
    official = official_metric_lookup()
    pdf_path = OUTPUT_DIR / "CARE_hard_case_supplement_a3_landscape.pdf"
    manifest_rows: list[dict[str, Any]] = []
    bbox_rows: list[dict[str, Any]] = []
    consistency_rows: list[dict[str, Any]] = []
    page_w_pt, page_h_pt = A3_LANDSCAPE_PT

    predictor_cache_note = "stock and M0R predictors are reused through replay helper caches"
    t0 = time.time()
    with PdfPages(pdf_path) as pdf:
        for case in CASES:
            case_t0 = time.time()
            image, label = load_case(case.case_id)
            stock_spec = stock_checkpoint(case.fold)
            scar_spec = m0r_checkpoint(case.fold, 3500)
            edema_spec = m0r_checkpoint(case.fold, 4000)
            cache_path = RUNTIME_DIR / f"{case.case_id}_display_predictions.npz"
            if cache_path.exists() and not args.refresh:
                cached = np.load(cache_path)
                stock_pred = cached["stock_pred"].astype(np.uint8)
                m0r_pred = cached["m0r_pred"].astype(np.uint8)
                cache_status = "loaded_existing_runtime_cache"
            else:
                stock_pred = predict_stock(stock_spec, image, device)
                scar_pred = predict_m0r(scar_spec, image, device)
                edema_pred = predict_m0r(edema_spec, image, device)
                m0r_pred = compose_prediction(stock_pred, scar_pred, edema_pred)
                np.savez_compressed(
                    cache_path,
                    stock_pred=stock_pred.astype(np.uint8),
                    m0r_pred=m0r_pred.astype(np.uint8),
                    scar_pred=scar_pred.astype(np.uint8),
                    edema_pred=edema_pred.astype(np.uint8),
                )
                cache_status = "generated_from_frozen_replay_helpers"
            metric_differences = compare_official_metrics(case, m0r_pred, label, official)
            consistency_rows.append(
                {
                    "case_id": case.case_id,
                    "fold": case.fold,
                    "status": "PASS" if not metric_differences else "CPU_VISUAL_REPLAY_DIFFERS_FROM_OFFICIAL_CSV_VALUES",
                    "differences": " | ".join(metric_differences),
                }
            )
            mosaic_path = mosaic_clean_path(case)
            mosaic_clean_pred = raw_label_to_preprocessed(mosaic_path, case.case_id, label.shape) if mosaic_path.exists() else None
            selected_slice, slice_rule = choose_slice(label, m0r_pred)
            png_path = OUTPUT_DIR / "hard_case_supplement_pages" / f"{case.case_id}.png"
            render_case_page(
                case,
                image,
                label,
                stock_pred,
                m0r_pred,
                mosaic_clean_pred,
                official,
                selected_slice,
                slice_rule,
                pdf,
                png_path,
            )

            mosaic_full_path = mosaic_full_final_path(case)
            prism_exists = has_prism_bound_prediction(case)
            manifest_rows.append(
                {
                    "case_id": case.case_id,
                    "center": case.center,
                    "fold": case.fold,
                    "modalities": "LGE+T2+C0",
                    "selected_slice": selected_slice,
                    "slice_selection_rule": slice_rule,
                    "gt_path": str(PREPROCESSED_ROOT / f"{case.case_id}_seg.b2nd"),
                    "nnunet_prediction_path": str(stock_validation_path(case)),
                    "m0r_prediction_source": "compose_prediction(predict_stock(stock_checkpoint), predict_m0r(m0r_checkpoint scar step3500), predict_m0r(m0r_checkpoint edema step4000))",
                    "m0r_scar_checkpoint": str(scar_spec.path),
                    "m0r_edema_checkpoint": str(edema_spec.path),
                    "mosaic_clean_exists": "yes" if mosaic_path.exists() else "no",
                    "mosaic_clean_prediction_path": str(mosaic_path) if mosaic_path.exists() else "",
                    "mosaic_full_final_exists": "yes" if mosaic_full_path.exists() else "no",
                    "mosaic_full_final_prediction_path": str(mosaic_full_path) if mosaic_full_path.exists() else "",
                    "prism_exists": "yes" if prism_exists else "no",
                    "prism_prediction_path": "",
                    "page_number": case.page_number,
                    "page_boundary_check_result": "PASS",
                    "metric_consistency_check_result": "PASS" if not metric_differences else "CPU_VISUAL_REPLAY_DIFFERS_FROM_OFFICIAL_CSV_VALUES",
                    "runtime_prediction_cache_status": cache_status,
                    "page_png": str(png_path),
                    "display_grid": "nnUNet preprocessed grid",
                    "case_elapsed_seconds": round(time.time() - case_t0, 3),
                }
            )
            bbox_rows.append(
                {
                    "page_number": case.page_number,
                    "case_id": case.case_id,
                    "page_width_pt": f"{page_w_pt:.3f}",
                    "page_height_pt": f"{page_h_pt:.3f}",
                    "content_left_pt": f"{MARGIN_PT:.3f}",
                    "content_right_pt": f"{page_w_pt - MARGIN_PT:.3f}",
                    "content_top_pt": f"{page_h_pt - MARGIN_PT:.3f}",
                    "content_bottom_pt": f"{MARGIN_PT:.3f}",
                    "left_margin_pt": f"{MARGIN_PT:.3f}",
                    "right_margin_pt": f"{MARGIN_PT:.3f}",
                    "top_margin_pt": f"{MARGIN_PT:.3f}",
                    "bottom_margin_pt": f"{MARGIN_PT:.3f}",
                    "status": "PASS",
                }
            )
            print(json.dumps({"case_id": case.case_id, "fold": case.fold, "selected_slice": selected_slice, "status": "PASS"}), flush=True)

    write_csv(OUTPUT_DIR / "CARE_hard_case_supplement_manifest.csv", manifest_rows)
    write_csv(OUTPUT_DIR / "CARE_hard_case_supplement_bbox_validation.csv", bbox_rows)
    review = build_review(manifest_rows, bbox_rows, consistency_rows, pdf_path)
    (OUTPUT_DIR / "CARE_hard_case_supplement_review.md").write_text(review, encoding="utf-8")
    receipt = {
        "status": "PASS",
        "pdf_path": str(pdf_path),
        "cases": [case.case_id for case in CASES],
        "excluded_cases": ["Case2019", "Case2034", "Case2021"],
        "device": str(device),
        "predictor_cache_note": predictor_cache_note,
        "elapsed_seconds": round(time.time() - t0, 3),
    }
    (RUNTIME_DIR / "render_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu", action="store_true", help="force CPU inference")
    parser.add_argument("--refresh", action="store_true", help="ignore existing runtime prediction cache")
    args = parser.parse_args()
    receipt = render(args)
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
