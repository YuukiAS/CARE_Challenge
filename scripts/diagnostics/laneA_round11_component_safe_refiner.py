#!/usr/bin/env python3
"""Lane A Round11 component-safe refiner audit and offline fusion grid.

This script is intentionally diagnostic-only. It replays the Round10 edema-only
refiner on fold0 validation cases, audits component failures, and evaluates
offline fusion rules without training a new model.
"""

from __future__ import annotations

import argparse
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
    str(REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round11_component_safe_refiner/mpl_cache"),
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round04_fold0_short_train_eval as base_eval
from scripts.diagnostics import laneA_round10_refiner_eval as r10_eval
from src.care_myocardium.refiner.laneA_round10_dataset import RefinerCase, build_cases, load_case_features, write_csv
from src.care_myocardium.refiner.laneA_round10_model import (
    ConservativeEdemaResidualRefiner,
    assert_scar_unchanged,
    refined_edema_logit,
)


OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round11_component_safe_refiner"
OVERLAY_ROOT = OUT_ROOT / "failure_overlays"
R10_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round10_edema_refiner"
R10_CKPT = R10_ROOT / "checkpoints/laneA_r10_edema_residual_refiner_fold0_very_short.pt"
R10_PRED_DIR = R10_ROOT / "predictions/laneA_r10_edema_residual_refiner_fold0_very_short/validation"
BASELINE_MODEL = "baseline_nnunet501_fold0"
ROUND10_MODEL = "candidate_laneA_round10_edema_refiner"
EDEMA = 4
SCAR = 5
SUBSETS = [
    "all_case",
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
class CaseReplay:
    case: RefinerCase
    gt_img: sitk.Image
    gt: np.ndarray
    baseline: np.ndarray
    round10: np.ndarray
    baseline_edema_prob: np.ndarray
    refined_edema_prob: np.ndarray
    delta: np.ndarray
    anatomy_support_prob: np.ndarray
    t2_image: np.ndarray
    spacing: tuple[float, float, float]


@dataclass(frozen=True)
class FusionRule:
    name: str
    description: str
    apply: Callable[[CaseReplay], np.ndarray]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
    out = []
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


def delta(candidate: object, baseline: object, *, lower_is_better: bool = False) -> float | None:
    if candidate is None or baseline is None:
        return None
    try:
        c = float(candidate)
        b = float(baseline)
    except (TypeError, ValueError):
        return None
    if math.isnan(c) or math.isnan(b) or math.isinf(c) or math.isinf(b):
        return None
    return b - c if lower_is_better else c - b


def md_table(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col)) for col in columns) + " |")
    return lines


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def component_sizes(mask: np.ndarray) -> list[int]:
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return [int((cc == idx).sum()) for idx in range(1, n_cc + 1)]


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


def remove_small_components(mask: np.ndarray, min_size: int) -> np.ndarray:
    if min_size <= 1:
        return mask
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    out = np.zeros_like(mask, dtype=bool)
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if int(comp.sum()) >= min_size:
            out |= comp
    return out


def keep_components_near_support(mask: np.ndarray, support: np.ndarray, spacing: tuple[float, float, float], max_dist_mm: float) -> np.ndarray:
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    out = np.zeros_like(mask, dtype=bool)
    if not support.any():
        return out
    dist = distance_transform_edt(~support.astype(bool), sampling=spacing)
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if comp.any() and float(dist[comp].min()) <= max_dist_mm:
            out |= comp
    return out


def load_round10_model(device: torch.device) -> ConservativeEdemaResidualRefiner:
    ckpt = torch.load(R10_CKPT, map_location=device)
    args = ckpt.get("args", {})
    model = ConservativeEdemaResidualRefiner(
        in_channels=13,
        hidden_channels=int(args.get("hidden_channels", 16)),
        delta_max=float(args.get("delta_max", 1.0)),
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model


def replay_case(case: RefinerCase, model: ConservativeEdemaResidualRefiner, device: torch.device) -> CaseReplay:
    features, _, baseline, gt_img = load_case_features(case)
    gt = sitk.GetArrayFromImage(sitk.ReadImage(str(case.gt_path))).astype(np.uint8, copy=False)
    round10 = base_eval.read_pred(R10_PRED_DIR / f"{case.case_id}.nii.gz", gt_img)
    x = torch.from_numpy(features[None]).float().to(device)
    base_prob = torch.from_numpy(features[4][None, None]).float().to(device)
    with torch.no_grad():
        delta_tensor = model(x)
        prob_tensor = torch.sigmoid(refined_edema_logit(base_prob, delta_tensor))
    delta_arr = delta_tensor[0, 0].detach().cpu().numpy().astype(np.float32, copy=False)
    prob_arr = prob_tensor[0, 0].detach().cpu().numpy().astype(np.float32, copy=False)
    spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
    return CaseReplay(
        case=case,
        gt_img=gt_img,
        gt=gt,
        baseline=baseline.astype(np.uint8, copy=False),
        round10=round10.astype(np.uint8, copy=False),
        baseline_edema_prob=features[4].astype(np.float32, copy=False),
        refined_edema_prob=prob_arr,
        delta=delta_arr,
        anatomy_support_prob=features[-1].astype(np.float32, copy=False),
        t2_image=features[8].astype(np.float32, copy=False),
        spacing=spacing,
    )


def replay_all_cases() -> list[CaseReplay]:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(2)
    model = load_round10_model(device)
    val_cases = [c for c in build_cases() if c.fold0_split == "val"]
    return [replay_case(case, model, device) for case in val_cases]


def class_row(replay: CaseReplay, pred: np.ndarray, model: str) -> dict[str, object]:
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


def subset_filter(name: str):
    if name == "all_case":
        return lambda r: True
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


def aggregate(rows: list[dict[str, object]], subset: str, model: str) -> dict[str, object]:
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


def compare_to_baseline(subset_rows: list[dict[str, object]], candidate_model: str) -> list[dict[str, object]]:
    by_key = {(r["model"], r["subset"]): r for r in subset_rows}
    out: list[dict[str, object]] = []
    for subset in SUBSETS:
        b = by_key[(BASELINE_MODEL, subset)]
        c = by_key[(candidate_model, subset)]
        out.append(
            {
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
                "delta_edema_remote_fp_improvement": delta(
                    c["myops_edema_remote_fp"], b["myops_edema_remote_fp"], lower_is_better=True
                ),
                "baseline_scar_dice": b["myops_scar_dice"],
                "candidate_scar_dice": c["myops_scar_dice"],
                "delta_scar_dice": delta(c["myops_scar_dice"], b["myops_scar_dice"]),
                "baseline_scar_hd95": b["myops_scar_hd95"],
                "candidate_scar_hd95": c["myops_scar_hd95"],
                "delta_scar_hd95_improvement": delta(c["myops_scar_hd95"], b["myops_scar_hd95"], lower_is_better=True),
            }
        )
    return out


def evaluate_model_rows(replays: list[CaseReplay], predictions: dict[str, np.ndarray], model: str) -> list[dict[str, object]]:
    return [class_row(replay, predictions[replay.case.case_id], model) for replay in replays]


def scar_guardrail_rows(replays: list[CaseReplay], predictions: dict[str, np.ndarray]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for replay in replays:
        pred = predictions[replay.case.case_id]
        rows.append(
            {
                "case_id": replay.case.case_id,
                "scar_changed_voxels": int(np.logical_xor(replay.baseline == SCAR, pred == SCAR).sum()),
                "non_edema_changed_voxels": int(((replay.baseline != pred) & (replay.baseline != EDEMA) & (pred != EDEMA)).sum()),
                "changed_voxels_total": int((replay.baseline != pred).sum()),
            }
        )
    return rows


def failure_flags(
    baseline_rows: list[dict[str, object]],
    candidate_rows: list[dict[str, object]],
    scar_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_baseline = {str(row["case_id"]): row for row in baseline_rows}
    by_candidate = {str(row["case_id"]): row for row in candidate_rows}
    by_scar = {str(row["case_id"]): row for row in scar_rows}
    out: list[dict[str, object]] = []
    for cid in sorted(by_candidate):
        b = by_baseline[cid]
        c = by_candidate[cid]
        flags: list[str] = []
        ed_dice_delta = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
        ed_hd95_delta = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
        comp_delta = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
        remote_delta = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
        if ed_dice_delta is not None and ed_dice_delta > 0.005 and ed_hd95_delta is not None and ed_hd95_delta < -0.5:
            flags.append("edema_dice_up_hd95_worse")
        if comp_delta is not None and comp_delta < -0.5:
            flags.append("edema_component_worse")
        if remote_delta is not None and remote_delta < 0:
            flags.append("edema_remote_fp_worse")
        if c.get("t2_present") is False and c.get("edema_gt_positive") is False:
            if float(c.get("myops_edema_component_count") or 0) > float(b.get("myops_edema_component_count") or 0):
                flags.append("no_t2_empty_gt_new_edema_fp")
        scar = by_scar[cid]
        if int(scar.get("scar_changed_voxels") or 0) != 0:
            flags.append("scar_changed")
        out.append(
            {
                "case_id": cid,
                "center": c.get("center"),
                "modality_group": c.get("modality_group"),
                "t2_present": c.get("t2_present"),
                "edema_gt_positive": c.get("edema_gt_positive"),
                "delta_edema_dice": ed_dice_delta,
                "delta_edema_hd95_improvement": ed_hd95_delta,
                "delta_edema_component_count_improvement": comp_delta,
                "delta_edema_remote_fp_improvement": remote_delta,
                "flags": ";".join(flags),
            }
        )
    return out


def audit_replay(replay: CaseReplay) -> dict[str, object]:
    baseline_edema = replay.baseline == EDEMA
    round10_edema = replay.round10 == EDEMA
    gt_edema = replay.gt == EDEMA
    added = round10_edema & ~baseline_edema
    removed = baseline_edema & ~round10_edema
    hard_anatomy = np.isin(replay.baseline, [1, 2, 3])
    dilated_baseline_edema = binary_dilation(baseline_edema, structure=generate_binary_structure(3, 1), iterations=2)
    added_outside_near_baseline = int((added & ~dilated_baseline_edema).sum())
    added_outside_anatomy_prob = int((added & (replay.anatomy_support_prob < 0.05)).sum())
    added_low_baseline_prob = int((added & (replay.baseline_edema_prob < 0.05)).sum())
    added_low_t2 = int((added & (replay.t2_image < 0.25)).sum()) if replay.case.t2_present else 0
    baseline_metrics = base_eval.class_metrics(replay.baseline, replay.gt, replay.spacing, EDEMA, "baseline_edema")
    r10_metrics = base_eval.class_metrics(replay.round10, replay.gt, replay.spacing, EDEMA, "round10_edema")
    comp_delta = delta(r10_metrics["round10_edema_component_count"], baseline_metrics["baseline_edema_component_count"], lower_is_better=True)
    remote_delta = delta(r10_metrics["round10_edema_remote_fp"], baseline_metrics["baseline_edema_remote_fp"], lower_is_better=True)
    hd95_delta = delta(r10_metrics["round10_edema_hd95"], baseline_metrics["baseline_edema_hd95"], lower_is_better=True)
    dice_delta = delta(r10_metrics["round10_edema_dice"], baseline_metrics["baseline_edema_dice"])
    reason = "no_component_worse"
    if comp_delta is not None and comp_delta < -0.5:
        if added_outside_near_baseline > 0:
            reason = "residual_remote_addition"
        elif added_low_baseline_prob > 0:
            reason = "baseline_probability_low_support"
        elif added_outside_anatomy_prob > 0:
            reason = "outside_anatomy_support"
        elif added_low_t2 > 0:
            reason = "low_t2_support"
        elif int(added.sum()) > 0:
            reason = "component_split_from_edge_add"
        else:
            reason = "unclear_needs_overlay_review"
    elif hd95_delta is not None and hd95_delta < 0:
        reason = "hd95_worse_without_component_worse"
    return {
        "case_id": replay.case.case_id,
        "center": replay.case.center,
        "modality_group": replay.case.modality_group,
        "t2_present": replay.case.t2_present,
        "edema_gt_positive": replay.case.edema_gt_positive,
        "baseline_edema_voxels": int(baseline_edema.sum()),
        "round10_edema_voxels": int(round10_edema.sum()),
        "gt_edema_voxels": int(gt_edema.sum()),
        "added_voxels": int(added.sum()),
        "removed_voxels": int(removed.sum()),
        "baseline_component_count": baseline_metrics["baseline_edema_component_count"],
        "round10_component_count": r10_metrics["round10_edema_component_count"],
        "delta_component_count_improvement": comp_delta,
        "baseline_remote_fp": baseline_metrics["baseline_edema_remote_fp"],
        "round10_remote_fp": r10_metrics["round10_edema_remote_fp"],
        "delta_remote_fp_improvement": remote_delta,
        "delta_dice": dice_delta,
        "delta_hd95_improvement": hd95_delta,
        "added_component_count": component_count(added),
        "added_component_sizes": ";".join(map(str, sorted(component_sizes(added), reverse=True)[:8])),
        "added_mean_distance_to_baseline_edema_mm": mean_dist_to_support(added, baseline_edema, replay.spacing),
        "added_max_distance_to_baseline_edema_mm": max_dist_to_support(added, baseline_edema, replay.spacing),
        "added_mean_distance_to_hard_anatomy_mm": mean_dist_to_support(added, hard_anatomy, replay.spacing),
        "added_max_distance_to_hard_anatomy_mm": max_dist_to_support(added, hard_anatomy, replay.spacing),
        "added_baseline_prob_mean": float(replay.baseline_edema_prob[added].mean()) if added.any() else None,
        "added_baseline_prob_min": float(replay.baseline_edema_prob[added].min()) if added.any() else None,
        "added_residual_mean": float(replay.delta[added].mean()) if added.any() else None,
        "added_residual_min": float(replay.delta[added].min()) if added.any() else None,
        "added_refined_prob_mean": float(replay.refined_edema_prob[added].mean()) if added.any() else None,
        "added_t2_mean": float(replay.t2_image[added].mean()) if added.any() and replay.case.t2_present else None,
        "added_outside_2dil_baseline_edema_voxels": added_outside_near_baseline,
        "added_low_baseline_prob_voxels": added_low_baseline_prob,
        "added_outside_anatomy_prob_voxels": added_outside_anatomy_prob,
        "added_low_t2_voxels": added_low_t2,
        "failure_reason_tag": reason,
    }


def write_overlay(replay: CaseReplay, audit_row: dict[str, object]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    OVERLAY_ROOT.mkdir(parents=True, exist_ok=True)
    edema_union = (replay.gt == EDEMA) | (replay.baseline == EDEMA) | (replay.round10 == EDEMA)
    coords = np.argwhere(edema_union)
    if coords.size == 0:
        return
    z = int(np.median(coords[:, 0]))
    t2 = replay.t2_image[z]
    base = replay.baseline[z] == EDEMA
    r10 = replay.round10[z] == EDEMA
    gt = replay.gt[z] == EDEMA
    added = r10 & ~base
    fig, axes = plt.subplots(1, 4, figsize=(14, 4), constrained_layout=True)
    panels = [
        ("T2 + GT", gt, "Greens"),
        ("baseline edema", base, "Blues"),
        ("Round10 edema", r10, "Reds"),
        ("added voxels", added, "magma"),
    ]
    for ax, (title, mask, cmap) in zip(axes, panels):
        ax.imshow(t2, cmap="gray")
        ax.imshow(np.ma.masked_where(~mask, mask), cmap=cmap, alpha=0.45)
        ax.set_title(title)
        ax.axis("off")
    fig.suptitle(f"{replay.case.case_id} z={z} reason={audit_row['failure_reason_tag']}")
    fig.savefig(OVERLAY_ROOT / f"{replay.case.case_id}_round11_failure_overlay.png", dpi=150)
    plt.close(fig)


def current_round10_predictions(replays: list[CaseReplay]) -> dict[str, np.ndarray]:
    return {r.case.case_id: r.round10.copy() for r in replays}


def baseline_predictions(replays: list[CaseReplay]) -> dict[str, np.ndarray]:
    return {r.case.case_id: r.baseline.copy() for r in replays}


def add_only_prediction(
    replay: CaseReplay,
    *,
    prob_threshold: float = 0.5,
    residual_threshold: float | None = None,
    baseline_prob_min: float | None = None,
    anatomy_prob_min: float | None = None,
    t2_present_only: bool = False,
    min_new_component_size: int = 1,
    near_baseline_edema_mm: float | None = None,
) -> np.ndarray:
    pred = replay.baseline.copy()
    if t2_present_only and not replay.case.t2_present:
        return pred
    add = (replay.refined_edema_prob >= prob_threshold) & (pred != SCAR)
    if residual_threshold is not None:
        add &= replay.delta >= residual_threshold
    if baseline_prob_min is not None:
        add &= replay.baseline_edema_prob >= baseline_prob_min
    if anatomy_prob_min is not None:
        add &= replay.anatomy_support_prob >= anatomy_prob_min
    new_add = add & (replay.baseline != EDEMA)
    if min_new_component_size > 1:
        new_add = remove_small_components(new_add, min_new_component_size)
    if near_baseline_edema_mm is not None:
        new_add = keep_components_near_support(new_add, replay.baseline == EDEMA, replay.spacing, near_baseline_edema_mm)
    final_add = (add & (replay.baseline == EDEMA)) | new_add
    pred[final_add] = EDEMA
    return pred


def add_remove_prediction(
    replay: CaseReplay,
    *,
    add_threshold: float,
    remove_threshold: float,
    anatomy_prob_min: float | None = None,
    near_baseline_edema_mm: float | None = None,
) -> np.ndarray:
    pred = replay.baseline.copy()
    add = (replay.refined_edema_prob >= add_threshold) & (pred != SCAR)
    if anatomy_prob_min is not None:
        add &= replay.anatomy_support_prob >= anatomy_prob_min
    if near_baseline_edema_mm is not None:
        new_add = add & (replay.baseline != EDEMA)
        new_add = keep_components_near_support(new_add, replay.baseline == EDEMA, replay.spacing, near_baseline_edema_mm)
        add = (add & (replay.baseline == EDEMA)) | new_add
    remove = (replay.baseline == EDEMA) & (replay.refined_edema_prob < remove_threshold) & (pred != SCAR)
    pred[remove] = 0
    pred[add] = EDEMA
    return pred


def fallback_if_component_worse(replay: CaseReplay, candidate: np.ndarray) -> np.ndarray:
    cand_count = component_count(candidate == EDEMA)
    base_count = component_count(replay.baseline == EDEMA)
    if cand_count > base_count:
        return replay.baseline.copy()
    return candidate


def fallback_if_component_or_remote_worse(replay: CaseReplay, candidate: np.ndarray) -> np.ndarray:
    cand_metrics = base_eval.class_metrics(candidate, replay.gt, replay.spacing, EDEMA, "cand")
    base_metrics = base_eval.class_metrics(replay.baseline, replay.gt, replay.spacing, EDEMA, "base")
    if float(cand_metrics["cand_component_count"] or 0) > float(base_metrics["base_component_count"] or 0):
        return replay.baseline.copy()
    if float(cand_metrics["cand_remote_fp"] or 0) > float(base_metrics["base_remote_fp"] or 0):
        return replay.baseline.copy()
    return candidate


def build_rules() -> list[FusionRule]:
    return [
        FusionRule("r10_add_only_baseline", "Original Round10 add-only fusion at probability 0.5", lambda r: r.round10.copy()),
        FusionRule(
            "residual_thresholded_add_delta_ge_0p10",
            "Add only where refined prob >= 0.5 and residual logit >= 0.10",
            lambda r: add_only_prediction(r, residual_threshold=0.10),
        ),
        FusionRule(
            "residual_thresholded_add_delta_ge_0p25",
            "Add only where refined prob >= 0.5 and residual logit >= 0.25",
            lambda r: add_only_prediction(r, residual_threshold=0.25),
        ),
        FusionRule(
            "baseline_prob_supported_add_ge_0p05",
            "Require baseline edema probability >= 0.05 for new additions",
            lambda r: add_only_prediction(r, baseline_prob_min=0.05),
        ),
        FusionRule(
            "baseline_prob_supported_add_ge_0p10",
            "Require baseline edema probability >= 0.10 for new additions",
            lambda r: add_only_prediction(r, baseline_prob_min=0.10),
        ),
        FusionRule(
            "anatomy_supported_add_ge_0p05",
            "Require baseline anatomy support probability >= 0.05",
            lambda r: add_only_prediction(r, anatomy_prob_min=0.05),
        ),
        FusionRule(
            "t2_present_only_add",
            "Disable all additions in no-T2 cases",
            lambda r: add_only_prediction(r, t2_present_only=True),
        ),
        FusionRule(
            "component_safe_add_near_baseline_2mm",
            "Allow new add components only within 2 mm of baseline edema",
            lambda r: add_only_prediction(r, near_baseline_edema_mm=2.0),
        ),
        FusionRule(
            "component_safe_add_min5_near_baseline_2mm",
            "Require new add components >=5 voxels and within 2 mm of baseline edema",
            lambda r: add_only_prediction(r, min_new_component_size=5, near_baseline_edema_mm=2.0),
        ),
        FusionRule(
            "fallback_if_component_worse",
            "Use Round10 fusion, but revert a case to baseline if edema component count increases",
            lambda r: fallback_if_component_worse(r, r.round10.copy()),
        ),
        FusionRule(
            "fallback_if_component_or_remote_worse",
            "Use Round10 fusion, but revert if component count or remote FP increases on fold0 diagnostic GT",
            lambda r: fallback_if_component_or_remote_worse(r, r.round10.copy()),
        ),
        FusionRule(
            "add_remove_prob_band_0p52_0p45",
            "Bounded bidirectional offline probe: add >=0.52, remove baseline edema <0.45",
            lambda r: add_remove_prediction(r, add_threshold=0.52, remove_threshold=0.45),
        ),
        FusionRule(
            "add_remove_prob_band_0p55_0p40_near2mm",
            "Stricter offline bidirectional probe with near-baseline add support",
            lambda r: add_remove_prediction(r, add_threshold=0.55, remove_threshold=0.40, near_baseline_edema_mm=2.0),
        ),
    ]


def rule_predictions(replays: list[CaseReplay], rule: FusionRule) -> dict[str, np.ndarray]:
    predictions = {}
    for replay in replays:
        pred = rule.apply(replay).astype(np.uint8, copy=False)
        if int(np.logical_xor(replay.baseline == SCAR, pred == SCAR).sum()) != 0:
            raise RuntimeError(f"{rule.name} changed scar in {replay.case.case_id}")
        predictions[replay.case.case_id] = pred
    return predictions


def summarize_rule(
    replays: list[CaseReplay],
    baseline_rows: list[dict[str, object]],
    rule: FusionRule,
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    predictions = rule_predictions(replays, rule)
    cand_rows = evaluate_model_rows(replays, predictions, f"rule:{rule.name}")
    scar_rows = scar_guardrail_rows(replays, predictions)
    subset_rows: list[dict[str, object]] = []
    for model, rows in [(BASELINE_MODEL, baseline_rows), (f"rule:{rule.name}", cand_rows)]:
        for subset in SUBSETS:
            subset_rows.append(aggregate(rows, subset, model))
    comparison = compare_to_baseline(subset_rows, f"rule:{rule.name}")
    flags = failure_flags(baseline_rows, cand_rows, scar_rows)
    by_subset = {r["subset"]: r for r in comparison}
    hard_flags = [r for r in flags if r.get("flags")]
    changed_cases = sum(1 for replay in replays if np.any(predictions[replay.case.case_id] != replay.baseline))
    row = {
        "rule": rule.name,
        "description": rule.description,
        "changed_cases": changed_cases,
        "hard_flag_count": len(hard_flags),
        "flagged_cases": ";".join(f"{r['case_id']}:{r['flags']}" for r in hard_flags[:10]),
        "all_case_delta_edema_dice": by_subset["all_case"]["delta_edema_dice"],
        "all_case_delta_edema_hd95_improvement": by_subset["all_case"]["delta_edema_hd95_improvement"],
        "t2_gtpos_delta_edema_dice": by_subset["t2_present_gt_positive"]["delta_edema_dice"],
        "t2_gtpos_delta_edema_hd95_improvement": by_subset["t2_present_gt_positive"]["delta_edema_hd95_improvement"],
        "t2_gtpos_delta_component_improvement": by_subset["t2_present_gt_positive"]["delta_edema_component_count_improvement"],
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
    return row, comparison, cand_rows, flags


def choose_best_rule(grid_rows: list[dict[str, object]]) -> dict[str, object] | None:
    eligible = []
    for row in grid_rows:
        if int(row["hard_flag_count"]) != 0:
            continue
        scar_ok = abs(float(row["delta_scar_dice_all"] or 0.0)) < 1e-8 and abs(float(row["delta_scar_hd95_improvement_all"] or 0.0)) < 1e-8
        no_t2_ok = float(row["no_t2_empty_delta_component_improvement"] or 0.0) >= 0.0
        t2_dice = float(row["t2_gtpos_delta_edema_dice"] or 0.0)
        t2_hd95 = float(row["t2_gtpos_delta_edema_hd95_improvement"] or 0.0)
        center_c_hd95 = float(row["centerC_delta_edema_hd95_improvement"] or 0.0)
        center_c_comp = float(row["centerC_delta_component_improvement"] or 0.0)
        if scar_ok and no_t2_ok and t2_dice >= 0.0 and t2_hd95 >= -0.05 and center_c_hd95 >= -0.05 and center_c_comp >= 0.0:
            score = t2_dice + 0.001 * t2_hd95 + 0.001 * center_c_comp
            eligible.append((score, row))
    if not eligible:
        return None
    return sorted(eligible, key=lambda x: x[0], reverse=True)[0][1]


def write_repro_gate(replays: list[CaseReplay]) -> None:
    r10_metrics = read_csv(R10_ROOT / "round10_fold0_very_short_metrics.csv")
    r10_flags = read_csv(R10_ROOT / "case_level_failure_flags.csv")
    r10_flagged = sorted(row["case_id"] for row in r10_flags if row.get("flags"))
    current_flags = []
    baseline_rows = [class_row(r, r.baseline, BASELINE_MODEL) for r in replays]
    r10_rows = [class_row(r, r.round10, ROUND10_MODEL) for r in replays]
    scar_rows = scar_guardrail_rows(replays, current_round10_predictions(replays))
    for row in failure_flags(baseline_rows, r10_rows, scar_rows):
        if row.get("flags"):
            current_flags.append(str(row["case_id"]))
    rows = [
        {
            "check": "round10_checkpoint_exists",
            "status": R10_CKPT.is_file(),
            "detail": str(R10_CKPT),
        },
        {
            "check": "round10_predictions_44_of_44",
            "status": len(list(R10_PRED_DIR.glob("*.nii.gz"))) == 44,
            "detail": str(R10_PRED_DIR),
        },
        {
            "check": "fold0_validation_replayed",
            "status": len(replays) == 44,
            "detail": len(replays),
        },
        {
            "check": "round10_failure_cases_reproduced",
            "status": current_flags == r10_flagged == ["Case2031", "Case3012"],
            "detail": f"recorded={r10_flagged}; replayed={current_flags}; metric_rows={len(r10_metrics)}",
        },
    ]
    write_csv(OUT_ROOT / "round11_round10_repro_gate.csv", rows)


def run_audit(replays: list[CaseReplay]) -> list[dict[str, object]]:
    rows = [audit_replay(replay) for replay in replays]
    write_csv(OUT_ROOT / "round11_failure_audit.csv", rows)
    focus = [row for row in rows if row["case_id"] in {"Case2031", "Case3012"} or float(row.get("delta_component_count_improvement") or 0) < 0]
    write_csv(OUT_ROOT / "case2031_case3012_component_audit.csv", [row for row in rows if row["case_id"] in {"Case2031", "Case3012"}])
    write_csv(
        OUT_ROOT / "residual_magnitude_summary.csv",
        [
            {
                "case_id": r.case.case_id,
                "center": r.case.center,
                "modality_group": r.case.modality_group,
                "t2_present": r.case.t2_present,
                "edema_gt_positive": r.case.edema_gt_positive,
                "delta_abs_mean": float(np.abs(r.delta).mean()),
                "delta_abs_max": float(np.abs(r.delta).max()),
                "delta_clip_fraction": float((np.abs(r.delta) >= 1.0 - 1e-6).mean()),
                "changed_voxels": int((r.round10 != r.baseline).sum()),
                "scar_changed_voxels": int(np.logical_xor(r.baseline == SCAR, r.round10 == SCAR).sum()),
                "baseline_edema_voxels": int((r.baseline == EDEMA).sum()),
                "round10_edema_voxels": int((r.round10 == EDEMA).sum()),
            }
            for r in replays
        ],
    )
    for replay in replays:
        if replay.case.case_id in {"Case2031", "Case3012"}:
            row = next(item for item in rows if item["case_id"] == replay.case.case_id)
            write_overlay(replay, row)
    lines = [
        "# Lane A Round11 Failure Audit",
        "",
        "Scope: replay Round10 checkpoint on fold0 validation; no training, no Slurm, no validation zip.",
        "",
        "## Focus Cases",
        "",
        *md_table(
            focus,
            [
                "case_id",
                "center",
                "added_voxels",
                "baseline_component_count",
                "round10_component_count",
                "delta_component_count_improvement",
                "delta_dice",
                "delta_hd95_improvement",
                "failure_reason_tag",
            ],
        ),
    ]
    (OUT_ROOT / "round11_failure_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def run_grid(replays: list[CaseReplay]) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    baseline_rows = evaluate_model_rows(replays, baseline_predictions(replays), BASELINE_MODEL)
    grid_rows: list[dict[str, object]] = []
    comparisons_by_rule: dict[str, list[dict[str, object]]] = {}
    candidate_rows_by_rule: dict[str, list[dict[str, object]]] = {}
    flags_by_rule: dict[str, list[dict[str, object]]] = {}
    for rule in build_rules():
        row, comparison, cand_rows, flags = summarize_rule(replays, baseline_rows, rule)
        grid_rows.append(row)
        comparisons_by_rule[rule.name] = comparison
        candidate_rows_by_rule[rule.name] = cand_rows
        flags_by_rule[rule.name] = flags
    write_csv(OUT_ROOT / "round11_offline_fusion_grid.csv", grid_rows)
    best = choose_best_rule(grid_rows)
    best_rule = str(best["rule"]) if best else "none"
    if best:
        write_csv(OUT_ROOT / "baseline_vs_refiner_by_subset.csv", comparisons_by_rule[best_rule])
        write_csv(OUT_ROOT / "case_level_failure_flags.csv", flags_by_rule[best_rule])
        best_rows = candidate_rows_by_rule[best_rule]
        write_csv(OUT_ROOT / "no_t2_empty_gt_fp_table.csv", [r for r in best_rows if r.get("t2_present") is False and r.get("edema_gt_positive") is False])
        write_csv(OUT_ROOT / "centerB_centerC_edema_table.csv", [r for r in best_rows if r.get("center") in {"CenterB", "CenterC"}])
        write_csv(OUT_ROOT / "scar_unchanged_guardrail_table.csv", scar_guardrail_rows(replays, rule_predictions(replays, next(r for r in build_rules() if r.name == best_rule))))
    component_rows = [
        {
            "rule": row["rule"],
            "hard_flag_count": row["hard_flag_count"],
            "flagged_cases": row["flagged_cases"],
            "t2_gtpos_delta_component_improvement": row["t2_gtpos_delta_component_improvement"],
            "centerC_delta_component_improvement": row["centerC_delta_component_improvement"],
            "centerC_delta_remote_fp_improvement": row["centerC_delta_remote_fp_improvement"],
            "no_t2_empty_delta_component_improvement": row["no_t2_empty_delta_component_improvement"],
        }
        for row in grid_rows
    ]
    write_csv(OUT_ROOT / "component_safety_summary.csv", component_rows)
    lines = [
        "# Lane A Round11 Offline Fusion Grid",
        "",
        f"Best eligible rule: `{best_rule}`",
        "",
        "Rules are diagnostic-only and use existing Round10 residuals; no new model was trained.",
        "",
        "## Grid Summary",
        "",
        *md_table(
            grid_rows,
            [
                "rule",
                "hard_flag_count",
                "t2_gtpos_delta_edema_dice",
                "t2_gtpos_delta_edema_hd95_improvement",
                "centerC_delta_edema_dice",
                "centerC_delta_edema_hd95_improvement",
                "centerC_delta_component_improvement",
                "flagged_cases",
            ],
        ),
    ]
    (OUT_ROOT / "round11_offline_fusion_grid.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return grid_rows, best


def write_readme_and_decision(audit_rows: list[dict[str, object]], grid_rows: list[dict[str, object]], best: dict[str, object] | None) -> None:
    if best:
        decision = "go_fusion_calibrated_refiner"
        reasons = [
            f"Offline rule `{best['rule']}` removes hard component flags without training.",
            "class_5 scar remains unchanged by construction.",
            "no-T2 empty-GT edema component count does not increase.",
            "Do not train bidirectional refiner in this run unless user explicitly asks for the next stage.",
        ]
    else:
        decision = "watch_bidirectional_refiner_needed"
        reasons = [
            "No offline fusion rule passed the clean component/HD95/scar/no-T2 gate.",
            "Proceed to bidirectional refiner architecture gate only after reviewing failure audit.",
        ]
    failure_focus = [row for row in audit_rows if row["case_id"] in {"Case2031", "Case3012"}]
    commands = [
        "./envs/env_CARE/bin/python scripts/diagnostics/laneA_round11_component_safe_refiner.py --mode audit-grid",
        "# No training command has been run in Round11 so far.",
    ]
    (OUT_ROOT / "round11_train_commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")
    (OUT_ROOT / "round11_train_config.yaml").write_text(
        "\n".join(
            [
                "round: 11",
                "stage_completed: offline_fusion_grid",
                "trainable_bidirectional_refiner: not_started",
                "baseline: nnUNet501 fold0 validation probabilities/predictions",
                "round10_checkpoint: results/diagnostics/care_myocardium/laneA_myops/round10_edema_refiner/checkpoints/laneA_r10_edema_residual_refiner_fold0_very_short.pt",
                "class_4_edema_only: true",
                "class_5_scar_immutable: true",
                f"decision_after_offline_grid: {decision}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    for empty_name in [
        "round11_unit_gradient_smoke.csv",
        "round11_tiny_overfit_metrics.csv",
        "round11_fold0_very_short_metrics.csv",
        "round11_fold0_short_train_metrics.csv",
        "round11_fold0_longer_train_metrics.csv",
    ]:
        path = OUT_ROOT / empty_name
        if not path.exists():
            path.write_text("status,reason\nnot_run,offline_fusion_grid_stage_completed_before_training\n", encoding="utf-8")
    readme_lines = [
        "# Lane A Round11 Goal Execution README",
        "",
        "Executed stages:",
        "- `round11_reproducibility_and_round10_result_gate`",
        "- `case_level_failure_audit_and_overlay`",
        "- `offline_fusion_and_threshold_grid`",
        "",
        "Not executed yet:",
        "- bidirectional refiner architecture gate",
        "- tiny-overfit",
        "- fold0 very-short/short/longer training",
        "- validation zip or upload",
        "",
        f"Current decision: `{decision}`",
        "",
        "Focus audit:",
        *md_table(
            failure_focus,
            [
                "case_id",
                "center",
                "added_voxels",
                "baseline_component_count",
                "round10_component_count",
                "delta_component_count_improvement",
                "failure_reason_tag",
            ],
        ),
    ]
    (OUT_ROOT / "round11_goal_execution_readme.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")
    decision_lines = [
        "# Lane A Round11 Decision Table",
        "",
        f"Decision: `{decision}`",
        "",
        "Reasons:",
        *[f"- {reason}" for reason in reasons],
        "",
        "## Best Offline Rule",
        "",
        *(md_table([best], list(best.keys())) if best else ["No eligible offline fusion rule passed."]),
        "",
        "No validation zip was created. No upload was performed. No fold1-4 or 5-fold training was run.",
    ]
    (OUT_ROOT / "round11_decision_table.md").write_text("\n".join(decision_lines) + "\n", encoding="utf-8")
    next_lines = [
        "# Lane A Round11 Next Actions",
        "",
        f"Current decision: `{decision}`",
        "",
    ]
    if best:
        next_lines.extend(
            [
                "Recommended next action:",
                f"- Treat `{best['rule']}` as the fusion-calibrated refiner candidate and inspect overlays/CSV before adding any new training.",
                "- If accepted, create a small export script for this exact fusion rule and rerun evaluation/export QA; do not train bidirectional refiner yet.",
            ]
        )
    else:
        next_lines.extend(
            [
                "Recommended next action:",
                "- Implement the bidirectional add/remove refiner architecture gate, then run unit/gradient and tiny-overfit gates only.",
            ]
        )
    (OUT_ROOT / "round11_next_actions.md").write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["audit-grid"], default="audit-grid")
    args = parser.parse_args()
    if args.mode != "audit-grid":
        raise ValueError(args.mode)
    replays = replay_all_cases()
    write_repro_gate(replays)
    audit_rows = run_audit(replays)
    grid_rows, best = run_grid(replays)
    write_readme_and_decision(audit_rows, grid_rows, best)
    print(f"Wrote Round11 audit/grid outputs to {OUT_ROOT}")
    print(f"Decision: {'go_fusion_calibrated_refiner' if best else 'watch_bidirectional_refiner_needed'}")


if __name__ == "__main__":
    main()
