#!/usr/bin/env python3
"""Lane A Round12 refiner salvage and high-upside transition diagnostics.

This script is diagnostic-only. It reads existing nnU-Net501, Round10, and
Round11 predictions/checkpoints, evaluates deployable fallback proxies, and
audits intensity/anatomy/boundary failure mechanisms. It does not train, submit
Slurm jobs, create validation zips, or modify existing predictions.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Callable

import numpy as np
import SimpleITK as sitk
import torch
from scipy.ndimage import binary_dilation, distance_transform_edt, generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round12_refiner_salvage_high_upside_transition/mpl_cache"),
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round4_fold0_short_train_eval as base_eval
from src.care_myocardium.refiner.laneA_round10_dataset import RefinerCase, build_cases, load_case_features, write_csv
from src.care_myocardium.refiner.laneA_round11_model import (
    BidirectionalEdemaResidualRefiner,
    bidirectional_edema_logit,
)


OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round12_refiner_salvage_high_upside_transition"
OVERLAY_ROOT = OUT_ROOT / "overlays"
R10_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner"
R11_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round11_component_safe_refiner"
R11_FAILURE_ROOT = R11_ROOT / "failure_case_summary"
R10_PRED_DIR = R10_ROOT / "predictions/laneA_r10_edema_residual_refiner_fold0_very_short/validation"
R11_PRED_DIR = R11_ROOT / "predictions/laneA_r11_bidirectional_edema_refiner_fold0_very_short/validation"
R11_CKPT = R11_ROOT / "checkpoints/laneA_r11_bidirectional_edema_refiner_fold0_very_short.pt"
PLAN_PATH = REPO_ROOT / "docs/plans/laneA_round12_next_refiner_salvage_and_high_upside_mechanism_transition_execution.md"

EDEMA = 4
SCAR = 5
BASELINE_MODEL = "baseline_nnunet501_fold0"
ROUND10_MODEL = "round10_add_only_refiner"
ROUND11_MODEL = "round11_bidirectional_refiner"

SUBSETS = [
    "all_case",
    "t2_present",
    "t2_present_gt_positive",
    "complete_modality",
    "CenterB",
    "CenterC",
    "no_t2_empty_gt",
    "modality:C0+LGE+T2",
    "modality:C0+LGE",
    "modality:LGE-only",
]


@dataclass(frozen=True)
class ReplayCase:
    case: RefinerCase
    gt_img: sitk.Image
    gt: np.ndarray
    baseline: np.ndarray
    round10: np.ndarray
    round11: np.ndarray
    baseline_edema_prob: np.ndarray
    anatomy_support_prob: np.ndarray
    c0_image: np.ndarray
    lge_image: np.ndarray
    t2_image: np.ndarray
    add_delta: np.ndarray
    remove_delta: np.ndarray
    refined_edema_prob: np.ndarray
    spacing: tuple[float, float, float]


@dataclass(frozen=True)
class FallbackRule:
    name: str
    description: str
    deployable: bool
    trigger: Callable[[dict[str, object]], bool]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fmt(value: object) -> str:
    if value is None or value == "":
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        if math.isinf(value):
            return "inf"
        return f"{value:.4f}"
    return str(value)


def finite(values: list[object]) -> list[float]:
    out: list[float] = []
    for value in values:
        if value in ("", None):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isnan(number) and not math.isinf(number):
            out.append(number)
    return out


def avg(values: list[object]) -> float | None:
    vals = finite(values)
    return float(mean(vals)) if vals else None


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        number = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(number) or math.isinf(number) else number


def delta(candidate: object, baseline: object, *, lower_is_better: bool = False) -> float | None:
    c = safe_float(candidate, math.nan)
    b = safe_float(baseline, math.nan)
    if math.isnan(c) or math.isnan(b):
        return None
    return b - c if lower_is_better else c - b


def md_table(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col)).replace("|", "\\|") for col in columns) + " |")
    return lines


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def component_sizes(mask: np.ndarray) -> list[int]:
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return [int((cc == idx).sum()) for idx in range(1, n_cc + 1)]


def component_distance_counts(
    mask: np.ndarray,
    support: np.ndarray,
    spacing: tuple[float, float, float],
    thresholds_mm: tuple[float, ...],
) -> dict[float, int]:
    out = {thr: 0 for thr in thresholds_mm}
    if not mask.any() or not support.any():
        return out
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    dist = distance_transform_edt(~support.astype(bool), sampling=spacing)
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if not comp.any():
            continue
        comp_min = float(dist[comp].min())
        for thr in thresholds_mm:
            if comp_min > thr:
                out[thr] += 1
    return out


def mean_dist_to_support(mask: np.ndarray, support: np.ndarray, spacing: tuple[float, float, float]) -> float | None:
    if not mask.any():
        return None
    if not support.any():
        return float("inf")
    dist = distance_transform_edt(~support.astype(bool), sampling=spacing)
    return float(dist[mask.astype(bool)].mean())


def max_dist_to_support(mask: np.ndarray, support: np.ndarray, spacing: tuple[float, float, float]) -> float | None:
    if not mask.any():
        return None
    if not support.any():
        return float("inf")
    dist = distance_transform_edt(~support.astype(bool), sampling=spacing)
    return float(dist[mask.astype(bool)].max())


def region_stats(arr: np.ndarray, mask: np.ndarray, prefix: str) -> dict[str, object]:
    if not mask.any():
        return {
            f"{prefix}_n": 0,
            f"{prefix}_mean": None,
            f"{prefix}_std": None,
            f"{prefix}_p25": None,
            f"{prefix}_p50": None,
            f"{prefix}_p75": None,
        }
    vals = arr[mask.astype(bool)].astype(np.float64, copy=False)
    return {
        f"{prefix}_n": int(vals.size),
        f"{prefix}_mean": float(vals.mean()),
        f"{prefix}_std": float(vals.std()),
        f"{prefix}_p25": float(np.percentile(vals, 25)),
        f"{prefix}_p50": float(np.percentile(vals, 50)),
        f"{prefix}_p75": float(np.percentile(vals, 75)),
    }


def load_round11_model(device: torch.device) -> BidirectionalEdemaResidualRefiner:
    ckpt = torch.load(R11_CKPT, map_location=device)
    args = ckpt.get("args", {})
    model = BidirectionalEdemaResidualRefiner(
        in_channels=13,
        hidden_channels=int(args.get("hidden_channels", 16)),
        delta_max=float(args.get("delta_max", 1.0)),
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model


def replay_case(case: RefinerCase) -> ReplayCase:
    features, _, baseline, gt_img = load_case_features(case)
    gt = sitk.GetArrayFromImage(sitk.ReadImage(str(case.gt_path))).astype(np.uint8, copy=False)
    round10 = base_eval.read_pred(R10_PRED_DIR / f"{case.case_id}.nii.gz", gt_img)
    round11 = base_eval.read_pred(R11_PRED_DIR / f"{case.case_id}.nii.gz", gt_img)
    spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
    # Round12 is a no-training/no-replay diagnostic. Use existing hard
    # predictions plus saved residual summary CSVs where available; do not run
    # full-volume model inference just to populate residual fields.
    zeros = np.zeros_like(features[4], dtype=np.float32)
    return ReplayCase(
        case=case,
        gt_img=gt_img,
        gt=gt,
        baseline=baseline.astype(np.uint8, copy=False),
        round10=round10.astype(np.uint8, copy=False),
        round11=round11.astype(np.uint8, copy=False),
        baseline_edema_prob=features[4].astype(np.float32, copy=False),
        anatomy_support_prob=features[-1].astype(np.float32, copy=False),
        c0_image=features[6].astype(np.float32, copy=False),
        lge_image=features[7].astype(np.float32, copy=False),
        t2_image=features[8].astype(np.float32, copy=False),
        add_delta=zeros,
        remove_delta=zeros,
        refined_edema_prob=features[4].astype(np.float32, copy=False),
        spacing=spacing,
    )


def replay_all_cases() -> list[ReplayCase]:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    val_cases = [c for c in build_cases() if c.fold0_split == "val"]
    return [replay_case(case) for case in val_cases]


def subset_filter(name: str) -> Callable[[dict[str, object]], bool]:
    if name == "all_case":
        return lambda r: True
    if name == "t2_present":
        return lambda r: r.get("t2_present") is True
    if name == "t2_present_gt_positive":
        return lambda r: r.get("t2_present") is True and r.get("edema_gt_positive") is True
    if name == "complete_modality":
        return lambda r: r.get("modality_group") == "C0+LGE+T2"
    if name == "CenterB":
        return lambda r: r.get("center") == "CenterB"
    if name == "CenterC":
        return lambda r: r.get("center") == "CenterC"
    if name == "no_t2_empty_gt":
        return lambda r: r.get("t2_present") is False and r.get("edema_gt_positive") is False
    if name.startswith("modality:"):
        group = name.split(":", 1)[1]
        return lambda r: r.get("modality_group") == group
    raise ValueError(name)


def class_row(replay: ReplayCase, pred: np.ndarray, model: str) -> dict[str, object]:
    row: dict[str, object] = {
        "model": model,
        "case_id": replay.case.case_id,
        "missing_prediction": False,
        "center": replay.case.center,
        "modality_group": replay.case.modality_group,
        "t2_present": replay.case.t2_present,
        "edema_gt_positive": replay.case.edema_gt_positive,
        "scar_gt_positive": replay.case.scar_gt_positive,
    }
    row.update(base_eval.class_metrics(pred, replay.gt, replay.spacing, EDEMA, "myops_edema"))
    row.update(base_eval.class_metrics(pred, replay.gt, replay.spacing, SCAR, "myops_scar"))
    return row


def evaluate_predictions(replays: list[ReplayCase], predictions: dict[str, np.ndarray], model: str) -> list[dict[str, object]]:
    return [class_row(replay, predictions[replay.case.case_id], model) for replay in replays]


def aggregate(rows: list[dict[str, object]], model: str, subset: str) -> dict[str, object]:
    filt = subset_filter(subset)
    items = [r for r in rows if r["model"] == model and not r.get("missing_prediction") and filt(r)]
    return {
        "model": model,
        "subset": subset,
        "n": len(items),
        "myops_edema_dice": avg([r.get("myops_edema_dice") for r in items]),
        "myops_edema_hd": avg([r.get("myops_edema_hd") for r in items]),
        "myops_edema_hd95": avg([r.get("myops_edema_hd95") for r in items]),
        "myops_edema_component_count": avg([r.get("myops_edema_component_count") for r in items]),
        "myops_edema_small_fp": avg([r.get("myops_edema_small_fp") for r in items]),
        "myops_edema_remote_fp": avg([r.get("myops_edema_remote_fp") for r in items]),
        "myops_edema_pred_gt_volume_ratio": avg([r.get("myops_edema_pred_gt_volume_ratio") for r in items]),
        "myops_scar_dice": avg([r.get("myops_scar_dice") for r in items]),
        "myops_scar_hd": avg([r.get("myops_scar_hd") for r in items]),
        "myops_scar_hd95": avg([r.get("myops_scar_hd95") for r in items]),
    }


def compare_to_baseline(baseline_rows: list[dict[str, object]], candidate_rows: list[dict[str, object]], candidate: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for subset in SUBSETS:
        b = aggregate(baseline_rows, BASELINE_MODEL, subset)
        c = aggregate(candidate_rows, candidate, subset)
        out.append(
            {
                "model": candidate,
                "subset": subset,
                "n": c["n"],
                "baseline_edema_dice": b["myops_edema_dice"],
                "candidate_edema_dice": c["myops_edema_dice"],
                "delta_edema_dice": delta(c["myops_edema_dice"], b["myops_edema_dice"]),
                "baseline_edema_hd95": b["myops_edema_hd95"],
                "candidate_edema_hd95": c["myops_edema_hd95"],
                "delta_edema_hd95_improvement": delta(c["myops_edema_hd95"], b["myops_edema_hd95"], lower_is_better=True),
                "baseline_edema_component_count": b["myops_edema_component_count"],
                "candidate_edema_component_count": c["myops_edema_component_count"],
                "delta_edema_component_count_improvement": delta(
                    c["myops_edema_component_count"], b["myops_edema_component_count"], lower_is_better=True
                ),
                "baseline_edema_remote_fp": b["myops_edema_remote_fp"],
                "candidate_edema_remote_fp": c["myops_edema_remote_fp"],
                "delta_edema_remote_fp_improvement": delta(c["myops_edema_remote_fp"], b["myops_edema_remote_fp"], lower_is_better=True),
                "baseline_scar_dice": b["myops_scar_dice"],
                "candidate_scar_dice": c["myops_scar_dice"],
                "delta_scar_dice": delta(c["myops_scar_dice"], b["myops_scar_dice"]),
                "baseline_scar_hd95": b["myops_scar_hd95"],
                "candidate_scar_hd95": c["myops_scar_hd95"],
                "delta_scar_hd95_improvement": delta(c["myops_scar_hd95"], b["myops_scar_hd95"], lower_is_better=True),
            }
        )
    return out


def failure_flags(
    baseline_rows: list[dict[str, object]],
    candidate_rows: list[dict[str, object]],
    candidate: str,
) -> list[dict[str, object]]:
    by_baseline = {str(row["case_id"]): row for row in baseline_rows}
    out: list[dict[str, object]] = []
    for c in sorted(candidate_rows, key=lambda x: str(x["case_id"])):
        cid = str(c["case_id"])
        b = by_baseline[cid]
        flags: list[str] = []
        ed_dice_delta = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
        ed_hd95_delta = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
        comp_delta = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
        remote_delta = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
        scar_dice_delta = delta(c.get("myops_scar_dice"), b.get("myops_scar_dice"))
        scar_hd95_delta = delta(c.get("myops_scar_hd95"), b.get("myops_scar_hd95"), lower_is_better=True)
        if ed_dice_delta is not None and ed_dice_delta > 0.005 and ed_hd95_delta is not None and ed_hd95_delta < -0.5:
            flags.append("edema_dice_up_hd95_worse")
        if comp_delta is not None and comp_delta < -0.5:
            flags.append("edema_component_worse")
        if remote_delta is not None and remote_delta < 0:
            flags.append("edema_remote_fp_worse")
        if c.get("t2_present") is False and c.get("edema_gt_positive") is False:
            if safe_float(c.get("myops_edema_component_count")) > safe_float(b.get("myops_edema_component_count")):
                flags.append("no_t2_empty_gt_new_edema_fp")
        if scar_dice_delta is not None and scar_dice_delta < -1e-8:
            flags.append("scar_dice_changed")
        if scar_hd95_delta is not None and abs(scar_hd95_delta) > 1e-8:
            flags.append("scar_hd95_changed")
        out.append(
            {
                "model": candidate,
                "case_id": cid,
                "center": c.get("center"),
                "modality_group": c.get("modality_group"),
                "t2_present": c.get("t2_present"),
                "edema_gt_positive": c.get("edema_gt_positive"),
                "delta_edema_dice": ed_dice_delta,
                "delta_edema_hd95_improvement": ed_hd95_delta,
                "delta_edema_component_count_improvement": comp_delta,
                "delta_edema_remote_fp_improvement": remote_delta,
                "delta_scar_dice": scar_dice_delta,
                "delta_scar_hd95_improvement": scar_hd95_delta,
                "flags": ";".join(flags),
            }
        )
    return out


def baseline_predictions(replays: list[ReplayCase]) -> dict[str, np.ndarray]:
    return {r.case.case_id: r.baseline.copy() for r in replays}


def round10_predictions(replays: list[ReplayCase]) -> dict[str, np.ndarray]:
    return {r.case.case_id: r.round10.copy() for r in replays}


def round11_predictions(replays: list[ReplayCase]) -> dict[str, np.ndarray]:
    return {r.case.case_id: r.round11.copy() for r in replays}


def case_proxy_features(replay: ReplayCase, candidate: np.ndarray) -> dict[str, object]:
    baseline_edema = replay.baseline == EDEMA
    cand_edema = candidate == EDEMA
    gt_edema = replay.gt == EDEMA
    added = cand_edema & ~baseline_edema
    removed = baseline_edema & ~cand_edema
    hard_anatomy = np.isin(replay.baseline, [1, 2, 3])
    dilated_baseline_edema = binary_dilation(baseline_edema, structure=generate_binary_structure(3, 1), iterations=2)
    sizes = sorted(component_sizes(added), reverse=True)
    added_dist_counts = component_distance_counts(added, baseline_edema, replay.spacing, (2.0, 5.0, 8.0, 10.0, 20.0))
    anatomy_dist_counts = component_distance_counts(added, hard_anatomy, replay.spacing, (2.0, 5.0, 8.0))
    baseline_metrics = base_eval.class_metrics(replay.baseline, replay.gt, replay.spacing, EDEMA, "baseline_edema")
    cand_metrics = base_eval.class_metrics(candidate, replay.gt, replay.spacing, EDEMA, "candidate_edema")
    return {
        "case_id": replay.case.case_id,
        "center": replay.case.center,
        "modality_group": replay.case.modality_group,
        "t2_present": replay.case.t2_present,
        "edema_gt_positive": replay.case.edema_gt_positive,
        "added_voxels": int(added.sum()),
        "removed_voxels": int(removed.sum()),
        "baseline_edema_voxels": int(baseline_edema.sum()),
        "candidate_edema_voxels": int(cand_edema.sum()),
        "gt_edema_voxels": int(gt_edema.sum()),
        "added_component_count": component_count(added),
        "added_component_sizes_top8": ";".join(map(str, sizes[:8])),
        "largest_added_component_fraction": float(sizes[0] / max(1, int(added.sum()))) if sizes else None,
        "added_components_gt2mm_from_baseline": added_dist_counts[2.0],
        "added_components_gt5mm_from_baseline": added_dist_counts[5.0],
        "added_components_gt8mm_from_baseline": added_dist_counts[8.0],
        "added_components_gt10mm_from_baseline": added_dist_counts[10.0],
        "added_components_gt20mm_from_baseline": added_dist_counts[20.0],
        "added_components_gt5mm_from_anatomy": anatomy_dist_counts[5.0],
        "added_mean_distance_to_baseline_edema_mm": mean_dist_to_support(added, baseline_edema, replay.spacing),
        "added_max_distance_to_baseline_edema_mm": max_dist_to_support(added, baseline_edema, replay.spacing),
        "added_mean_distance_to_anatomy_mm": mean_dist_to_support(added, hard_anatomy, replay.spacing),
        "added_mean_distance_to_gt_edema_mm": mean_dist_to_support(added, gt_edema, replay.spacing),
        "added_mean_baseline_edema_prob": float(replay.baseline_edema_prob[added].mean()) if added.any() else None,
        "added_mean_anatomy_support_prob": float(replay.anatomy_support_prob[added].mean()) if added.any() else None,
        "added_mean_t2_intensity_norm": float(replay.t2_image[added].mean()) if added.any() and replay.case.t2_present else None,
        "added_mean_lge_intensity_norm": float(replay.lge_image[added].mean()) if added.any() else None,
        "gt_mean_t2_intensity_norm": float(replay.t2_image[gt_edema].mean()) if gt_edema.any() and replay.case.t2_present else None,
        "gt_mean_lge_intensity_norm": float(replay.lge_image[gt_edema].mean()) if gt_edema.any() else None,
        "added_mean_add_delta": float(replay.add_delta[added].mean()) if added.any() else None,
        "added_mean_remove_delta": float(replay.remove_delta[added].mean()) if added.any() else None,
        "added_mean_residual_magnitude": float((np.abs(replay.add_delta) + np.abs(replay.remove_delta))[added].mean()) if added.any() else None,
        "removed_mean_add_delta": float(replay.add_delta[removed].mean()) if removed.any() else None,
        "removed_mean_remove_delta": float(replay.remove_delta[removed].mean()) if removed.any() else None,
        "added_outside_2dil_baseline_edema_voxels": int((added & ~dilated_baseline_edema).sum()),
        "added_gt_overlap_voxels": int((added & gt_edema).sum()),
        "baseline_component_count": baseline_metrics["baseline_edema_component_count"],
        "candidate_component_count": cand_metrics["candidate_edema_component_count"],
        "baseline_remote_fp": baseline_metrics["baseline_edema_remote_fp"],
        "candidate_remote_fp": cand_metrics["candidate_edema_remote_fp"],
        "delta_dice_vs_baseline": delta(cand_metrics["candidate_edema_dice"], baseline_metrics["baseline_edema_dice"]),
        "delta_hd95_improvement_vs_baseline": delta(
            cand_metrics["candidate_edema_hd95"], baseline_metrics["baseline_edema_hd95"], lower_is_better=True
        ),
        "delta_component_improvement_vs_baseline": delta(
            cand_metrics["candidate_edema_component_count"], baseline_metrics["baseline_edema_component_count"], lower_is_better=True
        ),
        "delta_remote_fp_improvement_vs_baseline": delta(
            cand_metrics["candidate_edema_remote_fp"], baseline_metrics["baseline_edema_remote_fp"], lower_is_better=True
        ),
    }


def build_fallback_rules() -> list[FallbackRule]:
    return [
        FallbackRule("round11_no_fallback", "Keep the Round11 prediction; reference only.", True, lambda p: False),
        FallbackRule(
            "oracle_component_or_remote_worse_non_deployable",
            "Oracle upper bound: fallback if GT-evaluated component or remote FP worsens. Non-deployable.",
            False,
            lambda p: safe_float(p.get("delta_component_improvement_vs_baseline")) < 0
            or safe_float(p.get("delta_remote_fp_improvement_vs_baseline")) < 0,
        ),
        FallbackRule(
            "component_count_increase_proxy",
            "Fallback if hard edema component count increases versus baseline, no GT needed.",
            True,
            lambda p: safe_float(p.get("candidate_component_count")) > safe_float(p.get("baseline_component_count")),
        ),
        FallbackRule(
            "new_component_many_fragments_proxy",
            "Fallback if additions create >=50 components and largest new component fraction <0.20.",
            True,
            lambda p: safe_float(p.get("added_component_count")) >= 50
            and safe_float(p.get("largest_added_component_fraction"), 1.0) < 0.20,
        ),
        FallbackRule(
            "remote_added_gt8mm_proxy",
            "Fallback if any new added component is >8 mm from baseline edema.",
            True,
            lambda p: safe_float(p.get("added_components_gt8mm_from_baseline")) > 0,
        ),
        FallbackRule(
            "remote_added_gt10mm_proxy",
            "Fallback if any new added component is >10 mm from baseline edema.",
            True,
            lambda p: safe_float(p.get("added_components_gt10mm_from_baseline")) > 0,
        ),
        FallbackRule(
            "remote_or_fragmented_proxy",
            "Fallback if component count increases, a new component is >8 mm from baseline, or additions are highly fragmented.",
            True,
            lambda p: safe_float(p.get("candidate_component_count")) > safe_float(p.get("baseline_component_count"))
            or safe_float(p.get("added_components_gt8mm_from_baseline")) > 0
            or (
                safe_float(p.get("added_component_count")) >= 50
                and safe_float(p.get("largest_added_component_fraction"), 1.0) < 0.25
            ),
        ),
        FallbackRule(
            "low_t2_or_remote_proxy",
            "Fallback if T2-present additions have low mean T2 support or any >8 mm remote component.",
            True,
            lambda p: (
                str(p.get("t2_present")).lower() == "true"
                and safe_float(p.get("added_voxels")) > 0
                and safe_float(p.get("added_mean_t2_intensity_norm"), 1.0) < 0.35
            )
            or safe_float(p.get("added_components_gt8mm_from_baseline")) > 0,
        ),
        FallbackRule(
            "baseline_prob_weak_or_remote_proxy",
            "Fallback if additions have low baseline edema support or are remote from baseline edema.",
            True,
            lambda p: (
                safe_float(p.get("added_voxels")) > 0
                and safe_float(p.get("added_mean_baseline_edema_prob"), 1.0) < 0.28
            )
            or safe_float(p.get("added_components_gt8mm_from_baseline")) > 0,
        ),
        FallbackRule(
            "strict_t2_anatomy_component_proxy",
            "Fallback if no-T2 adds, component count increases, remote addition, weak T2 support, or anatomy support is weak.",
            True,
            lambda p: (
                str(p.get("t2_present")).lower() == "false" and safe_float(p.get("added_voxels")) > 0
            )
            or safe_float(p.get("candidate_component_count")) > safe_float(p.get("baseline_component_count"))
            or safe_float(p.get("added_components_gt8mm_from_baseline")) > 0
            or (
                str(p.get("t2_present")).lower() == "true"
                and safe_float(p.get("added_voxels")) > 0
                and safe_float(p.get("added_mean_t2_intensity_norm"), 1.0) < 0.35
            )
            or (
                safe_float(p.get("added_voxels")) > 0
                and safe_float(p.get("added_mean_anatomy_support_prob"), 1.0) < 0.08
            ),
        ),
    ]


def apply_rule(replays: list[ReplayCase], proxies: dict[str, dict[str, object]], rule: FallbackRule) -> tuple[dict[str, np.ndarray], list[dict[str, object]]]:
    predictions: dict[str, np.ndarray] = {}
    decisions: list[dict[str, object]] = []
    for replay in replays:
        proxy = proxies[replay.case.case_id]
        trigger = rule.trigger(proxy)
        predictions[replay.case.case_id] = replay.baseline.copy() if trigger else replay.round11.copy()
        decisions.append(
            {
                "rule": rule.name,
                "case_id": replay.case.case_id,
                "fallback_to_baseline": trigger,
                "center": replay.case.center,
                "modality_group": replay.case.modality_group,
                "t2_present": replay.case.t2_present,
                "edema_gt_positive": replay.case.edema_gt_positive,
                "added_voxels": proxy.get("added_voxels"),
                "added_component_count": proxy.get("added_component_count"),
                "candidate_component_count": proxy.get("candidate_component_count"),
                "baseline_component_count": proxy.get("baseline_component_count"),
                "added_components_gt8mm_from_baseline": proxy.get("added_components_gt8mm_from_baseline"),
                "added_mean_t2_intensity_norm": proxy.get("added_mean_t2_intensity_norm"),
                "added_mean_baseline_edema_prob": proxy.get("added_mean_baseline_edema_prob"),
                "added_mean_anatomy_support_prob": proxy.get("added_mean_anatomy_support_prob"),
            }
        )
    return predictions, decisions


def write_reproducibility_gate(replays: list[ReplayCase]) -> None:
    expected_files = [
        PLAN_PATH,
        R11_FAILURE_ROOT / "round11_failure_case_summary.md",
        R11_FAILURE_ROOT / "round11_failure_case_table.csv",
        R11_FAILURE_ROOT / "round11_residual_fusion_audit.csv",
        R11_FAILURE_ROOT / "round11_salvage_feasibility.md",
        R11_FAILURE_ROOT / "round11_manual_fallback_case3011_3040.csv",
        R11_FAILURE_ROOT / "overlay_manifest.csv",
        R10_ROOT / "round10_fold0_very_short_metrics.csv",
        R11_ROOT / "round11_fold0_very_short_metrics.csv",
        R11_CKPT,
    ]
    failure_summary = (R11_FAILURE_ROOT / "round11_failure_case_summary.md").read_text(encoding="utf-8") if (R11_FAILURE_ROOT / "round11_failure_case_summary.md").is_file() else ""
    required_tags = {
        "Case2031": ["threshold_fragmentation", "refiner_random_edge_activation", "T2_support_weak_or_ambiguous"],
        "Case3012": ["component_safe_fallback_triggered"],
        "Case3011": ["add_residual_remote_island", "T2_support_weak_or_ambiguous"],
        "Case3040": ["refiner_random_edge_activation", "add_residual_remote_island", "T2_support_weak_or_ambiguous"],
    }
    rows: list[dict[str, object]] = []
    for path in expected_files:
        rows.append({"check": "required_file_exists", "item": str(path.relative_to(REPO_ROOT)), "status": path.is_file(), "detail": ""})
    rows.extend(
        [
            {"check": "fold0_validation_replayed", "item": "replay_cases", "status": len(replays) == 44, "detail": len(replays)},
            {
                "check": "round10_predictions_available",
                "item": str(R10_PRED_DIR.relative_to(REPO_ROOT)),
                "status": len(list(R10_PRED_DIR.glob("*.nii.gz"))) == 44,
                "detail": len(list(R10_PRED_DIR.glob("*.nii.gz"))),
            },
            {
                "check": "round11_predictions_available",
                "item": str(R11_PRED_DIR.relative_to(REPO_ROOT)),
                "status": len(list(R11_PRED_DIR.glob("*.nii.gz"))) == 44,
                "detail": len(list(R11_PRED_DIR.glob("*.nii.gz"))),
            },
        ]
    )
    for cid, tags in required_tags.items():
        ok = cid in failure_summary and all(tag in failure_summary for tag in tags)
        rows.append({"check": "round11_failure_reason_present", "item": cid, "status": ok, "detail": ";".join(tags)})
    write_csv(OUT_ROOT / "round12_reproducibility_gate.csv", rows)


def run_fallback_grid(replays: list[ReplayCase], baseline_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    proxies = {replay.case.case_id: case_proxy_features(replay, replay.round11) for replay in replays}
    write_csv(OUT_ROOT / "round12_round11_proxy_case_features.csv", list(proxies.values()))
    rules = build_fallback_rules()
    grid_rows: list[dict[str, object]] = []
    all_decisions: list[dict[str, object]] = []
    all_flags: list[dict[str, object]] = []
    for rule in rules:
        preds, decisions = apply_rule(replays, proxies, rule)
        candidate = f"rule:{rule.name}"
        cand_rows = evaluate_predictions(replays, preds, candidate)
        comparison = compare_to_baseline(baseline_rows, cand_rows, candidate)
        flags = failure_flags(baseline_rows, cand_rows, candidate)
        by_subset = {row["subset"]: row for row in comparison}
        hard_flags = [f for f in flags if f.get("flags")]
        fallback_cases = [d["case_id"] for d in decisions if d["fallback_to_baseline"]]
        grid_rows.append(
            {
                "rule": rule.name,
                "description": rule.description,
                "deployable": rule.deployable,
                "fallback_case_count": len(fallback_cases),
                "fallback_cases": ";".join(map(str, fallback_cases[:20])),
                "hard_flag_count": len(hard_flags),
                "flagged_cases": ";".join(f"{f['case_id']}:{f['flags']}" for f in hard_flags[:20]),
                "all_case_delta_edema_dice": by_subset["all_case"]["delta_edema_dice"],
                "all_case_delta_edema_hd95_improvement": by_subset["all_case"]["delta_edema_hd95_improvement"],
                "all_case_delta_component_improvement": by_subset["all_case"]["delta_edema_component_count_improvement"],
                "all_case_delta_remote_fp_improvement": by_subset["all_case"]["delta_edema_remote_fp_improvement"],
                "t2_gtpos_delta_edema_dice": by_subset["t2_present_gt_positive"]["delta_edema_dice"],
                "t2_gtpos_delta_edema_hd95_improvement": by_subset["t2_present_gt_positive"]["delta_edema_hd95_improvement"],
                "t2_gtpos_delta_component_improvement": by_subset["t2_present_gt_positive"]["delta_edema_component_count_improvement"],
                "t2_gtpos_delta_remote_fp_improvement": by_subset["t2_present_gt_positive"]["delta_edema_remote_fp_improvement"],
                "centerB_delta_edema_dice": by_subset["CenterB"]["delta_edema_dice"],
                "centerB_delta_edema_hd95_improvement": by_subset["CenterB"]["delta_edema_hd95_improvement"],
                "centerC_delta_edema_dice": by_subset["CenterC"]["delta_edema_dice"],
                "centerC_delta_edema_hd95_improvement": by_subset["CenterC"]["delta_edema_hd95_improvement"],
                "centerC_delta_component_improvement": by_subset["CenterC"]["delta_edema_component_count_improvement"],
                "centerC_delta_remote_fp_improvement": by_subset["CenterC"]["delta_edema_remote_fp_improvement"],
                "no_t2_empty_delta_component_improvement": by_subset["no_t2_empty_gt"]["delta_edema_component_count_improvement"],
                "delta_scar_dice_all": by_subset["all_case"]["delta_scar_dice"],
                "delta_scar_hd95_improvement_all": by_subset["all_case"]["delta_scar_hd95_improvement"],
            }
        )
        all_decisions.extend(decisions)
        all_flags.extend(flags)
    write_csv(OUT_ROOT / "round12_deployable_fallback_proxy_grid.csv", grid_rows)
    write_csv(OUT_ROOT / "round12_deployable_fallback_proxy_case_decisions.csv", all_decisions)
    write_csv(OUT_ROOT / "round12_case_level_failure_flags.csv", all_flags)
    return grid_rows, all_decisions, all_flags


def choose_salvage_status(grid_rows: list[dict[str, object]]) -> tuple[str, dict[str, object] | None, list[str]]:
    deployable = [r for r in grid_rows if str(r.get("deployable")).lower() == "true" and r["rule"] != "round11_no_fallback"]
    eligible: list[tuple[float, dict[str, object]]] = []
    for row in deployable:
        if int(safe_float(row.get("hard_flag_count"))) != 0:
            continue
        scar_ok = abs(safe_float(row.get("delta_scar_dice_all"))) < 1e-8 and abs(safe_float(row.get("delta_scar_hd95_improvement_all"))) < 1e-8
        no_t2_ok = safe_float(row.get("no_t2_empty_delta_component_improvement")) >= 0.0
        center_remote_ok = safe_float(row.get("centerC_delta_remote_fp_improvement")) >= 0.0
        center_component_ok = safe_float(row.get("centerC_delta_component_improvement")) >= 0.0
        center_hd95_ok = safe_float(row.get("centerC_delta_edema_hd95_improvement")) >= 0.0
        t2_hd95_ok = safe_float(row.get("t2_gtpos_delta_edema_hd95_improvement")) >= 0.0
        t2_dice = safe_float(row.get("t2_gtpos_delta_edema_dice"))
        center_dice = safe_float(row.get("centerC_delta_edema_dice"))
        if (
            scar_ok
            and no_t2_ok
            and center_remote_ok
            and center_component_ok
            and center_hd95_ok
            and t2_hd95_ok
            and max(t2_dice, center_dice) > 0
        ):
            score = t2_dice + center_dice + 0.001 * safe_float(row.get("centerC_delta_edema_hd95_improvement"))
            eligible.append((score, row))
    if not eligible:
        return (
            "refiner_stop_as_mainline_no_deployable_clean_salvage",
            None,
            [
                "No deployable proxy passed scar/no-T2/CenterC remote/component safety while keeping a positive edema signal.",
                "Oracle fallback remains non-deployable and cannot justify refiner continuation.",
            ],
        )
    best = sorted(eligible, key=lambda item: item[0], reverse=True)[0][1]
    t2_gain = safe_float(best.get("t2_gtpos_delta_edema_dice"))
    center_gain = safe_float(best.get("centerC_delta_edema_dice"))
    center_hd = safe_float(best.get("centerC_delta_edema_hd95_improvement"))
    if max(t2_gain, center_gain) < 0.005 and center_hd <= 0:
        return (
            "refiner_optional_calibration_only_tiny_gain",
            best,
            [
                f"Best deployable proxy `{best['rule']}` is clean but gain is tiny.",
                "Keep refiner only as optional baseline-preserving calibration; do not continue ordinary refiner training.",
            ],
        )
    return (
        "refiner_salvage_watch_requires_manual_review",
        best,
        [
            f"Best deployable proxy `{best['rule']}` has a positive signal but still needs overlay/proxy review before any export.",
            "Do not submit; treat as watch unless a future reviewer accepts deployable behavior.",
        ],
    )


def run_intensity_audit(replays: list[ReplayCase]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for replay in replays:
        masks = {
            "gt_edema": replay.gt == EDEMA,
            "baseline_fp": (replay.baseline == EDEMA) & (replay.gt != EDEMA),
            "baseline_missed_gt": (replay.gt == EDEMA) & (replay.baseline != EDEMA),
            "round11_added_all": (replay.round11 == EDEMA) & (replay.baseline != EDEMA),
            "round11_added_gt_overlap": (replay.round11 == EDEMA) & (replay.baseline != EDEMA) & (replay.gt == EDEMA),
            "round11_added_fp": (replay.round11 == EDEMA) & (replay.baseline != EDEMA) & (replay.gt != EDEMA),
        }
        for region, mask in masks.items():
            row: dict[str, object] = {
                "case_id": replay.case.case_id,
                "center": replay.case.center,
                "modality_group": replay.case.modality_group,
                "t2_present": replay.case.t2_present,
                "edema_gt_positive": replay.case.edema_gt_positive,
                "region": region,
                "voxels": int(mask.sum()),
            }
            row.update(region_stats(replay.t2_image, mask, "t2_norm"))
            row.update(region_stats(replay.lge_image, mask, "lge_norm"))
            row.update(region_stats(replay.c0_image, mask, "c0_norm"))
            row.update(region_stats(replay.baseline_edema_prob, mask, "baseline_edema_prob"))
            row.update(region_stats(replay.anatomy_support_prob, mask, "anatomy_support_prob"))
            rows.append(row)
    write_csv(OUT_ROOT / "round12_t2_lge_intensity_prior_audit.csv", rows)
    return rows


def run_anatomy_audit(replays: list[ReplayCase]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for replay in replays:
        hard_anatomy = np.isin(replay.baseline, [1, 2, 3])
        baseline_edema = replay.baseline == EDEMA
        masks = {
            "gt_edema": replay.gt == EDEMA,
            "baseline_fp": baseline_edema & (replay.gt != EDEMA),
            "round11_added_all": (replay.round11 == EDEMA) & ~baseline_edema,
            "round11_added_fp": (replay.round11 == EDEMA) & ~baseline_edema & (replay.gt != EDEMA),
            "round11_added_gt_overlap": (replay.round11 == EDEMA) & ~baseline_edema & (replay.gt == EDEMA),
        }
        for region, mask in masks.items():
            rows.append(
                {
                    "case_id": replay.case.case_id,
                    "center": replay.case.center,
                    "modality_group": replay.case.modality_group,
                    "t2_present": replay.case.t2_present,
                    "edema_gt_positive": replay.case.edema_gt_positive,
                    "region": region,
                    "voxels": int(mask.sum()),
                    "component_count": component_count(mask),
                    "mean_distance_to_hard_anatomy_mm": mean_dist_to_support(mask, hard_anatomy, replay.spacing),
                    "max_distance_to_hard_anatomy_mm": max_dist_to_support(mask, hard_anatomy, replay.spacing),
                    "mean_distance_to_baseline_edema_mm": mean_dist_to_support(mask, baseline_edema, replay.spacing),
                    "max_distance_to_baseline_edema_mm": max_dist_to_support(mask, baseline_edema, replay.spacing),
                    "mean_anatomy_support_prob": float(replay.anatomy_support_prob[mask].mean()) if mask.any() else None,
                    "mean_baseline_edema_prob": float(replay.baseline_edema_prob[mask].mean()) if mask.any() else None,
                }
            )
    write_csv(OUT_ROOT / "round12_anatomy_lesion_consistency_audit.csv", rows)
    return rows


def run_boundary_audit(replays: list[ReplayCase], baseline_rows: list[dict[str, object]], round11_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_base = {str(r["case_id"]): r for r in baseline_rows}
    by_r11 = {str(r["case_id"]): r for r in round11_rows}
    rows: list[dict[str, object]] = []
    for replay in replays:
        cid = replay.case.case_id
        proxy = case_proxy_features(replay, replay.round11)
        b = by_base[cid]
        c = by_r11[cid]
        d_dice = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
        d_hd95 = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
        d_comp = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
        d_remote = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
        tags: list[str] = []
        if safe_float(proxy.get("added_components_gt8mm_from_baseline")) > 0 or (d_remote is not None and d_remote < 0):
            tags.append("remote_component_or_edge_activation")
        if d_comp is not None and d_comp < 0:
            tags.append("component_fragmentation_or_split")
        if d_hd95 is not None and d_hd95 < 0 and (d_remote is None or d_remote >= 0):
            tags.append("boundary_hd95_worse_without_remote_flag")
        if safe_float(proxy.get("added_voxels")) > 0 and safe_float(proxy.get("added_gt_overlap_voxels")) == 0:
            tags.append("added_voxels_no_gt_overlap")
        if safe_float(proxy.get("candidate_edema_voxels")) > safe_float(proxy.get("gt_edema_voxels")) * 1.5 and safe_float(proxy.get("gt_edema_voxels")) > 0:
            tags.append("volume_overprediction")
        if not tags and d_dice is not None and d_dice > 0:
            tags.append("minor_overlap_gain")
        elif not tags:
            tags.append("no_clear_round11_boundary_signal")
        rows.append(
            {
                "case_id": cid,
                "center": replay.case.center,
                "modality_group": replay.case.modality_group,
                "t2_present": replay.case.t2_present,
                "edema_gt_positive": replay.case.edema_gt_positive,
                "delta_edema_dice": d_dice,
                "delta_edema_hd95_improvement": d_hd95,
                "delta_edema_component_improvement": d_comp,
                "delta_edema_remote_fp_improvement": d_remote,
                "added_voxels": proxy.get("added_voxels"),
                "added_component_count": proxy.get("added_component_count"),
                "added_components_gt8mm_from_baseline": proxy.get("added_components_gt8mm_from_baseline"),
                "added_gt_overlap_voxels": proxy.get("added_gt_overlap_voxels"),
                "pred_gt_volume_ratio": c.get("myops_edema_pred_gt_volume_ratio"),
                "failure_pattern_tags": ";".join(tags),
            }
        )
    write_csv(OUT_ROOT / "round12_boundary_hd_failure_audit.csv", rows)
    return rows


def write_overlay(replay: ReplayCase) -> dict[str, object] | None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return None
    OVERLAY_ROOT.mkdir(parents=True, exist_ok=True)
    union = (replay.gt == EDEMA) | (replay.baseline == EDEMA) | (replay.round11 == EDEMA)
    coords = np.argwhere(union)
    if coords.size == 0:
        return None
    z = int(np.median(coords[:, 0]))
    added = (replay.round11 == EDEMA) & (replay.baseline != EDEMA)
    removed = (replay.baseline == EDEMA) & (replay.round11 != EDEMA)
    panels = [
        ("T2 + GT", replay.gt[z] == EDEMA, "Greens"),
        ("baseline edema", replay.baseline[z] == EDEMA, "Blues"),
        ("Round11 edema", replay.round11[z] == EDEMA, "Reds"),
        ("added", added[z], "magma"),
        ("removed", removed[z], "Purples"),
    ]
    fig, axes = plt.subplots(1, len(panels), figsize=(16, 4), constrained_layout=True)
    for ax, (title, mask, cmap) in zip(axes, panels):
        ax.imshow(replay.t2_image[z], cmap="gray")
        ax.imshow(np.ma.masked_where(~mask, mask), cmap=cmap, alpha=0.45)
        ax.set_title(title)
        ax.axis("off")
    path = OVERLAY_ROOT / f"{replay.case.case_id}_round12_refiner_transition_overlay.png"
    fig.suptitle(f"{replay.case.case_id} z={z} center={replay.case.center}")
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return {"case_id": replay.case.case_id, "overlay_path": str(path.relative_to(REPO_ROOT)), "slice_z": z}


def write_markdown_reports(
    grid_rows: list[dict[str, object]],
    salvage_status: str,
    best_rule: dict[str, object] | None,
    salvage_reasons: list[str],
    intensity_rows: list[dict[str, object]],
    anatomy_rows: list[dict[str, object]],
    boundary_rows: list[dict[str, object]],
    overlay_manifest: list[dict[str, object]],
) -> None:
    grid_cols = [
        "rule",
        "deployable",
        "fallback_case_count",
        "hard_flag_count",
        "t2_gtpos_delta_edema_dice",
        "t2_gtpos_delta_edema_hd95_improvement",
        "centerC_delta_edema_dice",
        "centerC_delta_edema_hd95_improvement",
        "centerC_delta_remote_fp_improvement",
        "flagged_cases",
    ]
    write_text(
        OUT_ROOT / "round12_deployable_fallback_proxy_grid.md",
        "\n".join(
            [
                "# Lane A Round12 Deployable Fallback Proxy Grid",
                "",
                "Scope: no-training deployable proxy grid using existing Round11 outputs. Oracle rows are marked non-deployable and are not allowed for real selection.",
                "",
                *md_table(grid_rows, grid_cols),
            ]
        )
        + "\n",
    )
    decision_rows = [
        {
            "route": "deployable_refiner_fallback_salvage_diagnostic",
            "status": salvage_status,
            "best_rule": best_rule.get("rule") if best_rule else "none",
            "reason": " | ".join(salvage_reasons),
        }
    ]
    write_csv(OUT_ROOT / "round12_salvage_decision_table.csv", decision_rows)
    write_text(
        OUT_ROOT / "round12_salvage_decision_table.md",
        "\n".join(
            [
                "# Lane A Round12 Salvage Decision Table",
                "",
                *md_table(decision_rows, ["route", "status", "best_rule", "reason"]),
                "",
                "Interpretation: deployable fallback must not use GT/case IDs/hosted feedback. A tiny clean gain is optional calibration only, not a mainline.",
            ]
        )
        + "\n",
    )

    def region_summary(rows: list[dict[str, object]], value_col: str, group_col: str = "region") -> list[dict[str, object]]:
        out = []
        groups = sorted(set(str(r[group_col]) for r in rows))
        for group in groups:
            items = [r for r in rows if str(r[group_col]) == group and safe_float(r.get("voxels")) > 0]
            out.append({"region": group, "n_regions": len(items), f"mean_{value_col}": avg([r.get(value_col) for r in items])})
        return out

    intensity_summary = region_summary([r for r in intensity_rows if str(r.get("t2_present")).lower() == "true"], "t2_norm_mean")
    write_text(
        OUT_ROOT / "round12_t2_lge_intensity_prior_audit.md",
        "\n".join(
            [
                "# Lane A Round12 T2/LGE Intensity Prior Audit",
                "",
                "CARE-first intensity audit. No I-MMSeg/CLIP/GPT pipeline was used.",
                "",
                "## T2-present Region Summary",
                "",
                *md_table(intensity_summary, ["region", "n_regions", "mean_t2_norm_mean"]),
                "",
                "Decision hint: if `gt_edema` and `round11_added_fp` have separable T2/LGE support, Round13 should prioritize a T2/LGE intensity-prior route.",
            ]
        )
        + "\n",
    )
    anatomy_summary = region_summary(anatomy_rows, "mean_distance_to_hard_anatomy_mm")
    write_text(
        OUT_ROOT / "round12_anatomy_lesion_consistency_audit.md",
        "\n".join(
            [
                "# Lane A Round12 Anatomy-Lesion Consistency Audit",
                "",
                "Soft anatomy consistency audit only; no hard ROI deletion or Round6-style attenuation.",
                "",
                *md_table(anatomy_summary, ["region", "n_regions", "mean_mean_distance_to_hard_anatomy_mm"]),
            ]
        )
        + "\n",
    )
    tag_counts: dict[str, int] = {}
    for row in boundary_rows:
        for tag in str(row.get("failure_pattern_tags", "")).split(";"):
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    tag_rows = [{"failure_pattern_tag": k, "case_count": v} for k, v in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))]
    write_text(
        OUT_ROOT / "round12_boundary_hd_failure_audit.md",
        "\n".join(
            [
                "# Lane A Round12 Boundary/HD Failure Audit",
                "",
                "Boundary/HD audit is diagnostic only. It does not justify a recall-heavy loss or full training by itself.",
                "",
                *md_table(tag_rows, ["failure_pattern_tag", "case_count"]),
            ]
        )
        + "\n",
    )
    external_rows = external_method_readiness_rows(salvage_status, intensity_summary, anatomy_summary, tag_rows)
    write_csv(OUT_ROOT / "round12_external_method_readiness_matrix.csv", external_rows)
    write_text(
        OUT_ROOT / "round12_external_method_readiness_matrix.md",
        "\n".join(
            [
                "# Lane A Round12 External Method Readiness Matrix",
                "",
                "No external repo was cloned, built, or trained. This is a mechanism-slot readiness matrix.",
                "",
                *md_table(
                    external_rows,
                    [
                        "mechanism_slot",
                        "candidate_methods",
                        "round12_priority",
                        "status",
                        "next_smoke",
                        "compliance_notes",
                    ],
                ),
            ]
        )
        + "\n",
    )
    write_csv(OUT_ROOT / "overlay_manifest.csv", overlay_manifest)
    final_decision_rows = final_decision_rows_from_evidence(salvage_status, best_rule, intensity_summary, anatomy_summary, tag_rows)
    write_csv(OUT_ROOT / "round12_decision_table.csv", final_decision_rows)
    write_text(
        OUT_ROOT / "round12_decision_table.md",
        "\n".join(["# Lane A Round12 Decision Table", "", *md_table(final_decision_rows, ["route", "status", "evidence", "round13_action"])])
        + "\n",
    )
    recommendation = round13_recommendation(final_decision_rows)
    write_text(OUT_ROOT / "round12_round13_recommendation.md", recommendation)
    write_text(
        OUT_ROOT / "round12_goal_execution_readme.md",
        "\n".join(
            [
                "# Lane A Round12 Goal Execution Readme",
                "",
                "Executed diagnostic stages:",
                "- `round12_reproducibility_and_round11_failure_summary_gate`",
                "- `deployable_fallback_proxy_grid`",
                "- `refiner_salvage_decision_gate`",
                "- `T2_LGE_intensity_prior_audit`",
                "- `anatomy_lesion_consistency_audit`",
                "- `boundary_HD_failure_audit`",
                "- `external_method_readiness_matrix`",
                "- `round13_transition_recommendation_gate`",
                "",
                "Not executed:",
                "- training",
                "- Slurm submission",
                "- validation zip creation",
                "- upload",
                "- fold1-4 or 5-fold expansion",
                "- external repo cloning/training",
                "",
                f"Salvage status: `{salvage_status}`",
                f"Best deployable fallback rule: `{best_rule.get('rule') if best_rule else 'none'}`",
                "",
                "Output root:",
                f"- `{OUT_ROOT.relative_to(REPO_ROOT)}`",
            ]
        )
        + "\n",
    )


def external_method_readiness_rows(
    salvage_status: str,
    intensity_summary: list[dict[str, object]],
    anatomy_summary: list[dict[str, object]],
    tag_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    tags = {str(r["failure_pattern_tag"]): int(r["case_count"]) for r in tag_rows}
    remote_count = tags.get("remote_component_or_edge_activation", 0)
    fragmentation_count = tags.get("component_fragmentation_or_split", 0)
    gt_t2 = next((r for r in intensity_summary if r["region"] == "gt_edema"), {})
    fp_t2 = next((r for r in intensity_summary if r["region"] == "round11_added_fp"), {})
    t2_gap = safe_float(gt_t2.get("mean_t2_norm_mean")) - safe_float(fp_t2.get("mean_t2_norm_mean"))
    intensity_priority = "go" if abs(t2_gap) >= 0.05 or remote_count > 0 else "watch"
    anatomy_priority = "go" if remote_count > 0 else "watch"
    boundary_priority = "watch" if remote_count or fragmentation_count else "postpone"
    if salvage_status.startswith("refiner_stop"):
        refiner_status = "stop_as_mainline"
    else:
        refiner_status = "optional_calibration_only"
    return [
        {
            "mechanism_slot": "refiner_fallback_salvage",
            "candidate_methods": "first-party deployable proxy only",
            "round12_priority": "completed",
            "status": refiner_status,
            "next_smoke": "only keep if proxy remains deployable and clean",
            "compliance_notes": "CARE-only, no training, no external data",
        },
        {
            "mechanism_slot": "T2_LGE_intensity_prior_route",
            "candidate_methods": "I-MMSeg-inspired intensity prior, CARE-first feature maps",
            "round12_priority": intensity_priority,
            "status": "metadata_ready",
            "next_smoke": "one-case intensity-prior feature smoke on CenterC and failure cases",
            "compliance_notes": "no CLIP/GPT/foundation weights in first pass; no external data",
        },
        {
            "mechanism_slot": "anatomy_lesion_consistency_route",
            "candidate_methods": "Cascaded FSN/PT-Net-inspired soft consistency",
            "round12_priority": anatomy_priority,
            "status": "metadata_ready",
            "next_smoke": "soft lesion-anatomy feature/penalty diagnostic; no hard deletion",
            "compliance_notes": "CARE-only anatomy labels/probabilities",
        },
        {
            "mechanism_slot": "boundary_HD_objective_route",
            "candidate_methods": "InverseForm/surface/HD-aware auxiliary",
            "round12_priority": boundary_priority,
            "status": "watch",
            "next_smoke": "small-weight boundary auxiliary only after support features are validated",
            "compliance_notes": "do not replace Dice/CE; report HD95/components",
        },
        {
            "mechanism_slot": "missing_modality_representation_route",
            "candidate_methods": "AdaMM/UniME/CoPeDiT/MoE/MMPL-Seg",
            "round12_priority": "postpone_metadata_only",
            "status": "not_ready_for_training",
            "next_smoke": "license/compliance/input-output/one-case feasibility before any fold0 smoke",
            "compliance_notes": "external data training disallowed; complete-case teacher reliability unresolved",
        },
        {
            "mechanism_slot": "alignment_route",
            "candidate_methods": "CAA-Seg/SSA",
            "round12_priority": "watch",
            "status": "not_escalated",
            "next_smoke": "raise priority only if overlays/intensity audit show sequence mismatch",
            "compliance_notes": "CARE-only alignment audit before repo integration",
        },
    ]


def final_decision_rows_from_evidence(
    salvage_status: str,
    best_rule: dict[str, object] | None,
    intensity_summary: list[dict[str, object]],
    anatomy_summary: list[dict[str, object]],
    tag_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    tags = {str(r["failure_pattern_tag"]): int(r["case_count"]) for r in tag_rows}
    remote_count = tags.get("remote_component_or_edge_activation", 0)
    gt_t2 = next((r for r in intensity_summary if r["region"] == "gt_edema"), {})
    fp_t2 = next((r for r in intensity_summary if r["region"] == "round11_added_fp"), {})
    t2_gap = safe_float(gt_t2.get("mean_t2_norm_mean")) - safe_float(fp_t2.get("mean_t2_norm_mean"))
    rows = [
        {
            "route": "deployable_refiner_fallback_salvage",
            "status": salvage_status,
            "evidence": f"best_rule={best_rule.get('rule') if best_rule else 'none'}",
            "round13_action": "optional calibration only" if best_rule else "stop refiner as mainline",
        },
        {
            "route": "T2_LGE_intensity_prior",
            "status": "go" if abs(t2_gap) >= 0.05 or remote_count > 0 else "watch",
            "evidence": f"T2 mean gap gt_edema-minus-round11_added_fp={t2_gap:.4f}; remote/edge cases={remote_count}",
            "round13_action": "first-party CARE intensity-prior feature smoke",
        },
        {
            "route": "anatomy_lesion_consistency",
            "status": "go" if remote_count > 0 else "watch",
            "evidence": f"remote/edge activation appears in {remote_count} cases; anatomy audit written",
            "round13_action": "soft consistency feature/penalty smoke, no hard ROI",
        },
        {
            "route": "boundary_HD_objective",
            "status": "watch",
            "evidence": f"boundary/component tags={tags}",
            "round13_action": "small-weight auxiliary only after intensity/anatomy support validated",
        },
        {
            "route": "external_repo_integration",
            "status": "postpone",
            "evidence": "metadata matrix ready; no first-party high-upside smoke has been run yet",
            "round13_action": "license/compliance + one-case smoke only after route selection",
        },
    ]
    return rows


def round13_recommendation(decision_rows: list[dict[str, object]]) -> str:
    by_route = {str(row["route"]): row for row in decision_rows}
    lines = [
        "# Lane A Round12 to Round13 Recommendation",
        "",
        "## Verdict",
        "",
        "- Do not continue ordinary add-only or bidirectional refiner training.",
        "- Do not expand to fold1-4, 5-fold, validation zip, or upload.",
        "- Treat the refiner as optional baseline-preserving substrate only if deployable fallback is clean; otherwise stop it as mainline.",
        "- Round13 should prioritize a first-party high-upside mechanism smoke before any external repo training.",
        "",
        "## Recommended Round13 Order",
        "",
    ]
    intensity = by_route.get("T2_LGE_intensity_prior", {})
    anatomy = by_route.get("anatomy_lesion_consistency", {})
    if intensity.get("status") == "go":
        lines.append("1. `T2_LGE_intensity_prior_route`: build CARE-only T2/LGE support features for CenterC and failure cases.")
    if anatomy.get("status") == "go":
        lines.append("2. `anatomy_lesion_consistency_route`: combine soft lesion-anatomy consistency with intensity support, without hard deletion.")
    lines.extend(
        [
            "3. `boundary_HD_objective_route`: keep as small-weight auxiliary/watch, not primary objective.",
            "4. `missing_modality_representation_route`: metadata/one-case readiness only until compliance and teacher reliability are solved.",
            "5. `alignment_route`: keep CAA-Seg/SSA as watch unless overlays show clear sequence mismatch.",
            "",
            "Any external method must first pass license/compliance, pretrained data source, external data risk, input-output shape, label mapping, and one-case smoke.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    replays = replay_all_cases()
    write_reproducibility_gate(replays)
    baseline_rows = evaluate_predictions(replays, baseline_predictions(replays), BASELINE_MODEL)
    round10_rows = evaluate_predictions(replays, round10_predictions(replays), ROUND10_MODEL)
    round11_rows = evaluate_predictions(replays, round11_predictions(replays), ROUND11_MODEL)
    write_csv(OUT_ROOT / "round12_baseline_round10_round11_case_metrics.csv", baseline_rows + round10_rows + round11_rows)

    grid_rows, _, _ = run_fallback_grid(replays, baseline_rows)
    salvage_status, best_rule, salvage_reasons = choose_salvage_status(grid_rows)
    intensity_rows = run_intensity_audit(replays)
    anatomy_rows = run_anatomy_audit(replays)
    boundary_rows = run_boundary_audit(replays, baseline_rows, round11_rows)

    overlay_manifest: list[dict[str, object]] = []
    for replay in replays:
        if replay.case.case_id in {"Case2031", "Case3012", "Case3011", "Case3040"}:
            row = write_overlay(replay)
            if row:
                overlay_manifest.append(row)
    write_markdown_reports(
        grid_rows,
        salvage_status,
        best_rule,
        salvage_reasons,
        intensity_rows,
        anatomy_rows,
        boundary_rows,
        overlay_manifest,
    )
    print(f"Wrote Round12 diagnostics to {OUT_ROOT}")
    print(f"Salvage status: {salvage_status}")
    print(f"Best deployable rule: {best_rule.get('rule') if best_rule else 'none'}")


if __name__ == "__main__":
    main()
