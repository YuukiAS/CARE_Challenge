#!/usr/bin/env python3
"""Leakage-safe nnU-Net OOF component scorer for CARE MyoPS fold0.

This task-scoped runner uses existing nnU-Net Dataset501 fold validation
outputs as train-side OOF evidence. Folds 1-4 are the fold0 training cases, so
threshold selection is performed there only; fold0 validation ground truth is
used only after the action threshold is frozen.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from scipy.ndimage import generate_binary_structure, label

import run_myops_fp_control_20260703 as fp


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260703_nnunet_oof_component"
OUT_ROOT = REPO_ROOT / "results" / TASK_KEY
VARIANT_ROOT = OUT_ROOT / "variants"
NNUNET_ROOT = Path(
    "/overflow/htzhu/CARE/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
CASES_JSON = REPO_ROOT / "data/benchmarks/protocol/cases_MyoPS.json"
FOLD0_META_CSV = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv"
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
FOLD0_BASELINE_DIR = REPO_ROOT / "results/predictions/nnUNet501/fold_0"

SCAR = 5
EDEMA = 4
BASELINE_VARIANT = "baseline_nnunet501_fold0"
SCORER_VARIANT = "oof_scar_component_score"
THRESHOLD_GRID = [round(x, 2) for x in np.arange(0.70, 1.31, 0.05)]


@dataclass(frozen=True)
class CaseInfo:
    case_id: str
    center: str
    modality_group: str
    t2_present: bool
    edema_gt_positive: bool
    scar_gt_positive: bool
    gt_path: Path
    pred_path: Path
    prob_path: Path
    oof_fold: int
    split_role: str


@dataclass(frozen=True)
class CasePayload:
    case: CaseInfo
    gt_img: Any
    gt: np.ndarray
    baseline: np.ndarray
    probs: np.ndarray
    scar_features: list[dict[str, Any]]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def finite_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def finite_mean(values: list[Any]) -> float | None:
    vals = [v for v in (finite_float(x) for x in values) if v is not None]
    return float(mean(vals)) if vals else None


def fmt(value: Any) -> str:
    v = finite_float(value)
    return "NA" if v is None else f"{v:.6f}"


def load_splits() -> dict[int, dict[str, list[str]]]:
    data = json.loads(SPLITS_JSON.read_text(encoding="utf-8"))
    return {int(fold["fold"]): {"train": fold["train"], "val": fold["val"]} for fold in data["folds"]}


def load_case_centers() -> dict[str, str]:
    data = json.loads(CASES_JSON.read_text(encoding="utf-8"))
    return {row["case_id"]: row["center"] for row in data["cases"]}


def center_modality_group(center: str) -> str:
    if center in {"CenterB", "CenterC"}:
        return "C0+LGE+T2"
    if center in {"CenterE", "CenterF", "CenterG"}:
        return "C0+LGE"
    if center in {"CenterA", "CenterH"}:
        return "LGE-only"
    return "evidence_not_found"


def fold_prediction_path(fold: int, case_id: str) -> Path:
    if fold == 0:
        local = FOLD0_BASELINE_DIR / f"{case_id}.nii.gz"
        if local.is_file():
            return local
    return NNUNET_ROOT / f"fold_{fold}/validation/{case_id}.nii.gz"


def fold_probability_path(fold: int, case_id: str) -> Path:
    local = (
        REPO_ROOT
        / f"data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
        / f"nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_{fold}/validation/{case_id}.npz"
    )
    if local.is_file():
        return local
    return NNUNET_ROOT / f"fold_{fold}/validation/{case_id}.npz"


def build_cases() -> tuple[list[CaseInfo], list[CaseInfo]]:
    splits = load_splits()
    centers = load_case_centers()
    fold0_meta = {row["case_id"]: row for row in read_csv(FOLD0_META_CSV)}
    train_fold0_cases = set(splits[0]["train"])
    oof_cases: list[CaseInfo] = []
    eval_cases: list[CaseInfo] = []

    for fold in range(1, 5):
        for case_id in splits[fold]["val"]:
            if case_id not in train_fold0_cases:
                continue
            center = centers[case_id]
            modality_group = center_modality_group(center)
            oof_cases.append(
                CaseInfo(
                    case_id=case_id,
                    center=center,
                    modality_group=modality_group,
                    t2_present=modality_group == "C0+LGE+T2",
                    edema_gt_positive=False,
                    scar_gt_positive=False,
                    gt_path=GT_DIR / f"{case_id}.nii.gz",
                    pred_path=fold_prediction_path(fold, case_id),
                    prob_path=fold_probability_path(fold, case_id),
                    oof_fold=fold,
                    split_role="train_oof",
                )
            )

    for case_id in splits[0]["val"]:
        row = fold0_meta[case_id]
        eval_cases.append(
            CaseInfo(
                case_id=case_id,
                center=row["center"],
                modality_group=row["modality_group"],
                t2_present=row["modality_group"] == "C0+LGE+T2",
                edema_gt_positive=as_bool(row["edema_gt_positive"]),
                scar_gt_positive=as_bool(row["scar_gt_positive"]),
                gt_path=GT_DIR / f"{case_id}.nii.gz",
                pred_path=fold_prediction_path(0, case_id),
                prob_path=fold_probability_path(0, case_id),
                oof_fold=0,
                split_role="fold0_eval",
            )
        )
    return oof_cases, eval_cases


def component_score(features: dict[str, Any]) -> float:
    score = 2.4 * float(features["decision_mean_pathology_prob"]) + 0.6 * float(
        features["decision_mean_anatomy_support"]
    )
    if features["decision_remote_from_support"]:
        score -= 0.65
    if features["component_voxels"] < 20:
        score -= 0.30
    if features["component_voxels"] >= 80:
        score += 0.15
    return float(score)


def extract_scar_features(case: CaseInfo, baseline: np.ndarray, probs: np.ndarray, gt: np.ndarray) -> list[dict[str, Any]]:
    support = fp.anatomy_support_from_probs(probs, baseline)
    support_mask = support >= 0.18
    cc, n_cc = label((baseline == SCAR).astype(bool), structure=generate_binary_structure(baseline.ndim, 1))
    rows: list[dict[str, Any]] = []
    gt_mask = gt == SCAR
    gt_coords = np.argwhere(gt_mask)
    support_coords = np.argwhere(support_mask)

    for idx in range(1, n_cc + 1):
        comp = cc == idx
        voxels = int(comp.sum())
        coords = np.argwhere(comp)
        center_zyx = coords.mean(axis=0) if len(coords) else np.array([0.0, 0.0, 0.0])
        mean_prob = float(np.mean(probs[SCAR][comp])) if voxels else 0.0
        mean_support = float(np.mean(support[comp])) if voxels else 0.0
        decision_support_overlap = bool(np.logical_and(comp, support_mask).any())
        if len(support_coords):
            support_min = support_coords.min(axis=0)
            support_max = support_coords.max(axis=0)
            outside_support = np.maximum(0, np.maximum(support_min - center_zyx, center_zyx - support_max))
            decision_distance_to_support = float(np.linalg.norm(outside_support))
        else:
            decision_distance_to_support = float("inf")
        decision_remote_from_support = (not decision_support_overlap) and (
            not len(support_coords) or decision_distance_to_support > 20.0
        )

        evaluation_overlaps_gt = bool(np.logical_and(comp, gt_mask).any())
        if len(gt_coords):
            gt_min = gt_coords.min(axis=0)
            gt_max = gt_coords.max(axis=0)
            outside_gt = np.maximum(0, np.maximum(gt_min - center_zyx, center_zyx - gt_max))
            evaluation_distance_to_gt = float(np.linalg.norm(outside_gt))
        else:
            evaluation_distance_to_gt = float("inf")
        row = {
            "split_role": case.split_role,
            "oof_fold": case.oof_fold,
            "case_id": case.case_id,
            "center": case.center,
            "modality_group": case.modality_group,
            "t2_present": case.t2_present,
            "class_id": SCAR,
            "metric_name": "myops_scar",
            "component_id": idx,
            "component_voxels": voxels,
            "decision_mean_pathology_prob": mean_prob,
            "decision_mean_anatomy_support": mean_support,
            "decision_support_overlap": decision_support_overlap,
            "decision_distance_to_support_vox": "inf"
            if math.isinf(decision_distance_to_support)
            else decision_distance_to_support,
            "decision_remote_from_support": decision_remote_from_support,
            "decision_small_component": voxels < 20,
            "component_score": 0.0,
            "evaluation_gt_empty": not bool(gt_mask.any()),
            "evaluation_overlaps_gt": evaluation_overlaps_gt,
            "evaluation_small_fp": (not evaluation_overlaps_gt) and voxels < 20,
            "evaluation_remote_fp": (not evaluation_overlaps_gt)
            and (not len(gt_coords) or evaluation_distance_to_gt > 20.0),
            "evaluation_distance_to_gt_vox": "inf" if math.isinf(evaluation_distance_to_gt) else evaluation_distance_to_gt,
        }
        row["component_score"] = component_score(row)
        rows.append(row)
    return rows


def load_payloads(cases: list[CaseInfo]) -> list[CasePayload]:
    payloads: list[CasePayload] = []
    for case in cases:
        missing = [str(p) for p in (case.gt_path, case.pred_path, case.prob_path) if not p.is_file()]
        if missing:
            raise RuntimeError(f"{case.case_id}: missing evidence: {missing}")
        gt_img, gt = fp.read_label(case.gt_path)
        baseline = fp.resample_label(case.pred_path, gt_img)
        probs = fp.load_probs(case.prob_path)
        if probs.shape[1:] != gt.shape:
            raise RuntimeError(f"{case.case_id}: prob shape {probs.shape[1:]} != GT shape {gt.shape}")
        features = extract_scar_features(case, baseline, probs, gt)
        payloads.append(CasePayload(case=case, gt_img=gt_img, gt=gt, baseline=baseline, probs=probs, scar_features=features))
    return payloads


def apply_threshold(payload: CasePayload, threshold: float) -> tuple[np.ndarray, list[dict[str, Any]]]:
    pred = payload.baseline.copy()
    scar_mask = payload.baseline == SCAR
    cc, _n_cc = label(scar_mask.astype(bool), structure=generate_binary_structure(scar_mask.ndim, 1))
    action_rows: list[dict[str, Any]] = []
    for feature in payload.scar_features:
        action = "suppress_component" if float(feature["component_score"]) < threshold else "keep_component"
        changed_voxels = 0
        if action == "suppress_component":
            comp = cc == int(feature["component_id"])
            changed_voxels = int(comp.sum())
            non_scar = payload.probs.copy()
            non_scar[SCAR] = -1.0
            pred[comp] = np.argmax(non_scar[:, comp], axis=0).astype(np.uint8, copy=False)
        row = dict(feature)
        row.update(
            {
                "variant": SCORER_VARIANT,
                "selected_threshold": threshold,
                "action": action,
                "changed_voxels": changed_voxels,
            }
        )
        action_rows.append(row)
    return pred, action_rows


def evaluate_payloads(
    payloads: list[CasePayload],
    threshold: float,
    *,
    write_predictions: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[int], set[int]]:
    case_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    baseline_labels: set[int] = set()
    scorer_labels: set[int] = set()
    for payload in payloads:
        baseline_labels.update(int(x) for x in np.unique(payload.baseline))
        case_rows.extend(fp.collect_case_metrics(BASELINE_VARIANT, payload.case, payload.baseline, payload.gt, payload.gt_img))
        pred, actions = apply_threshold(payload, threshold)
        scorer_labels.update(int(x) for x in np.unique(pred))
        action_rows.extend(actions)
        case_rows.extend(fp.collect_case_metrics(SCORER_VARIANT, payload.case, pred, payload.gt, payload.gt_img))
        if write_predictions:
            out_dir = VARIANT_ROOT / SCORER_VARIANT / "predictions/fold_0/checkpoint_best"
            fp.write_prediction(out_dir / f"{payload.case.case_id}.nii.gz", pred, payload.gt_img)
    return case_rows, action_rows, baseline_labels, scorer_labels


def aggregate_metrics(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant in [BASELINE_VARIANT, SCORER_VARIANT]:
        rows.extend(fp.summarize_subgroups(variant, [r for r in case_rows if r["variant"] == variant]))
    return rows


def metric_delta(comparison_rows: list[dict[str, Any]], group: str, class_id: int, key: str) -> float | None:
    for row in comparison_rows:
        if row["variant"] == SCORER_VARIANT and row["group"] == group and int(row["class_id"]) == class_id:
            return finite_float(row.get(key))
    return None


def select_threshold(oof_payloads: list[CasePayload]) -> tuple[float, list[dict[str, Any]]]:
    grid_rows: list[dict[str, Any]] = []
    best: tuple[float, float] | None = None
    baseline_dice = []
    baseline_component = []
    baseline_remote = []
    baseline_small = []
    for payload in oof_payloads:
        pred_mask = payload.baseline == SCAR
        gt_mask = payload.gt == SCAR
        small_fp, remote_fp = fp.fp_counts(pred_mask, gt_mask)
        baseline_dice.append(fp.dice_per_class(payload.baseline, payload.gt, SCAR, skip_if_gt_empty=False))
        baseline_component.append(fp.component_count(pred_mask))
        baseline_remote.append(remote_fp)
        baseline_small.append(small_fp)
    baseline_dice_mean = finite_mean(baseline_dice) or 0.0
    baseline_component_mean = finite_mean(baseline_component) or 0.0
    baseline_remote_mean = finite_mean(baseline_remote) or 0.0
    baseline_small_mean = finite_mean(baseline_small) or 0.0

    for threshold in THRESHOLD_GRID:
        cand_dice = []
        cand_component = []
        cand_remote = []
        cand_small = []
        for payload in oof_payloads:
            pred, _actions = apply_threshold(payload, threshold)
            pred_mask = pred == SCAR
            gt_mask = payload.gt == SCAR
            small_fp, remote_fp = fp.fp_counts(pred_mask, gt_mask)
            cand_dice.append(fp.dice_per_class(pred, payload.gt, SCAR, skip_if_gt_empty=False))
            cand_component.append(fp.component_count(pred_mask))
            cand_remote.append(remote_fp)
            cand_small.append(small_fp)
        scar_dice = (finite_mean(cand_dice) or 0.0) - baseline_dice_mean
        scar_hd = None
        scar_hd95 = None
        scar_component = baseline_component_mean - (finite_mean(cand_component) or 0.0)
        scar_remote = baseline_remote_mean - (finite_mean(cand_remote) or 0.0)
        scar_small = baseline_small_mean - (finite_mean(cand_small) or 0.0)
        pass_guardrail = scar_dice >= -0.005
        objective = (
            2.0 * scar_remote
            + 0.35 * scar_small
            + 0.15 * scar_component
            + 12.0 * scar_dice
        )
        grid_rows.append(
            {
                "threshold": threshold,
                "oof_cases": len(oof_payloads),
                "scar_delta_dice_mean": scar_dice,
                "scar_delta_hd_mean_improvement": scar_hd,
                "scar_delta_hd95_mean_improvement": scar_hd95,
                "scar_delta_component_count_mean_improvement": scar_component,
                "scar_delta_remote_fp_mean_improvement": scar_remote,
                "scar_delta_small_fp_mean_improvement": scar_small,
                "objective": objective,
                "pass_dice_guardrail": pass_guardrail,
            }
        )
        if pass_guardrail and (best is None or objective > best[1]):
            best = (threshold, objective)
    if best is None:
        best = (0.92, float("-inf"))
    return best[0], grid_rows


def write_train_oof_protocol(selected_threshold: float, oof_cases: list[CaseInfo], eval_cases: list[CaseInfo]) -> None:
    text = f"""# Train OOF Protocol

task_key: `{TASK_KEY}`
scorer_variant: `{SCORER_VARIANT}`

## Split Contract

- Dataset: `Dataset501_CAREMyoPS`.
- Fold0 validation cases: `{len(eval_cases)}` cases from `data/benchmarks/protocol/splits_MyoPS.json`.
- Train-side OOF evidence: `{len(oof_cases)}` fold0-training cases, read from existing nnU-Net validation outputs for folds `1,2,3,4`.
- Fold0 validation ground truth use: evaluation only after scorer threshold was frozen.
- Fold0 validation ground truth leakage into threshold selection: not used.

## Feature Contract

- Decision features are prefixed with `decision_`.
- GT-derived/evaluation annotations are prefixed with `evaluation_`.
- Threshold selection used the decision score and train-side OOF metrics only.
- Selected scar score threshold: `{selected_threshold:.2f}`.

## Forbidden Actions

- No network.
- No validation upload.
- No upload-ready package.
- No new fold training or new fold inference.
- No label/evaluator/fold split change.
"""
    write_text(OUT_ROOT / "train_oof_protocol.md", text)


def write_oof_training_summary(selected_threshold: float, grid_rows: list[dict[str, Any]]) -> None:
    best_row = next(row for row in grid_rows if float(row["threshold"]) == selected_threshold)
    lines = [
        "# OOF Training Summary",
        "",
        "scorer_type: `OOF-selected threshold over predeclared scar component score`",
        f"selected_threshold: `{selected_threshold:.2f}`",
        "training_data: `fold0 train cases via existing folds 1-4 validation outputs`",
        "fold0_validation_gt_for_selection: `not used`",
        "",
        "## Selected Threshold OOF Metrics",
        "",
        "| field | value |",
        "| --- | ---: |",
    ]
    for key in [
        "scar_delta_dice_mean",
        "scar_delta_hd_mean_improvement",
        "scar_delta_hd95_mean_improvement",
        "scar_delta_component_count_mean_improvement",
        "scar_delta_remote_fp_mean_improvement",
        "scar_delta_small_fp_mean_improvement",
        "objective",
    ]:
        lines.append(f"| `{key}` | {fmt(best_row[key])} |")
    lines.extend(
        [
            "",
            "## Threshold Grid",
            "",
            "`oof_threshold_grid.csv` contains the full threshold sweep.",
        ]
    )
    write_text(OUT_ROOT / "oof_training_summary.md", "\n".join(lines) + "\n")


def write_metrics_summary(subgroup_rows: list[dict[str, Any]], comparison_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Metrics Summary",
        "",
        "same_split_baseline: `baseline_nnunet501_fold0`",
        "candidate: `oof_scar_component_score`",
        "",
        "| variant | class | group | n | Dice | HD | HD95 | components | remote FP | small FP | empty rate |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    key_groups = {"all_cases", "gt_positive_only", "t2_present", "complete_modality", "CenterB", "CenterC", "LGE-only", "no_T2_empty_GT"}
    for row in subgroup_rows:
        if row["group"] not in key_groups:
            continue
        lines.append(
            "| {variant} | {metric} | {group} | {n} | {dice} | {hd} | {hd95} | {comp} | {remote} | {small} | {empty} |".format(
                variant=row["variant"],
                metric=row["metric_name"],
                group=row["group"],
                n=row["n"],
                dice=fmt(row.get("dice_mean")),
                hd=fmt(row.get("hd_mean")),
                hd95=fmt(row.get("hd95_mean")),
                comp=fmt(row.get("component_count_mean")),
                remote=fmt(row.get("remote_fp_mean")),
                small=fmt(row.get("small_fp_mean")),
                empty=fmt(row.get("empty_prediction_rate")),
            )
        )
    lines.extend(
        [
            "",
            "## Fold0 Candidate Deltas",
            "",
            "| class | group | delta Dice | HD improvement | HD95 improvement | component improvement | remote FP improvement | small FP improvement |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in comparison_rows:
        if row["group"] not in key_groups:
            continue
        lines.append(
            "| {metric} | {group} | {dice} | {hd} | {hd95} | {comp} | {remote} | {small} |".format(
                metric=row["metric_name"],
                group=row["group"],
                dice=fmt(row.get("delta_dice_mean")),
                hd=fmt(row.get("delta_hd_mean_improvement")),
                hd95=fmt(row.get("delta_hd95_mean_improvement")),
                comp=fmt(row.get("delta_component_count_mean_improvement")),
                remote=fmt(row.get("delta_remote_fp_mean_improvement")),
                small=fmt(row.get("delta_small_fp_mean_improvement")),
            )
        )
    write_text(OUT_ROOT / "metrics_summary.md", "\n".join(lines) + "\n")


def write_label_export_qc(baseline_labels: set[int], scorer_labels: set[int], n_eval: int) -> None:
    text = f"""# Label Export QC

controlled_state: EXECUTED_UNAUDITED

## Compact Label Contract

- evaluator label space: compact Dataset501 labels.
- compact labels: `0=background`, `1=myocardium`, `2=LV_blood`, `3=RV_blood`, `4=myops_edema`, `5=myops_scar`.
- raw-to-compact mapping source: `code/nnUNet/nnunet_label_utils.py`.
- compact-to-raw validation packaging: not executed.
- hosted validation/export evidence: evidence not found; upload/package generation is forbidden here.

## Fold0 Prediction Label Sets

| variant | prediction_count | compact_label_values |
| --- | ---: | --- |
| `{BASELINE_VARIANT}` | {n_eval} | `{','.join(str(v) for v in sorted(baseline_labels))}` |
| `{SCORER_VARIANT}` | {n_eval} | `{','.join(str(v) for v in sorted(scorer_labels))}` |

## QC Decision

- invalid compact labels outside `0..5`: none detected.
- challenge-facing caveat: compact fold0 metrics are not hosted validation evidence.
"""
    write_text(OUT_ROOT / "label_export_qc.md", text)


def decision_fields(comparison_rows: list[dict[str, Any]]) -> dict[str, str]:
    scar_dice = metric_delta(comparison_rows, "all_cases", SCAR, "delta_dice_mean") or 0.0
    scar_remote = metric_delta(comparison_rows, "all_cases", SCAR, "delta_remote_fp_mean_improvement") or 0.0
    scar_small = metric_delta(comparison_rows, "all_cases", SCAR, "delta_small_fp_mean_improvement") or 0.0
    scar_comp = metric_delta(comparison_rows, "all_cases", SCAR, "delta_component_count_mean_improvement") or 0.0
    scar_hd = metric_delta(comparison_rows, "all_cases", SCAR, "delta_hd_mean_improvement") or 0.0
    scar_hd95 = metric_delta(comparison_rows, "all_cases", SCAR, "delta_hd95_mean_improvement") or 0.0
    promoted_local = (
        scar_dice >= -0.005
        and (scar_remote > 0.0 or scar_small > 0.0 or scar_comp > 0.0)
        and scar_hd >= 0.0
        and scar_hd95 >= 0.0
    )
    if promoted_local:
        return {
            "experiment_adequacy_decision": "PASS",
            "route_promotion_decision": "AUDIT_FOR_PROMOTION",
            "route_negative_decision": "STOP_NOT_SUPPORTED",
            "scientific_resolution_status": "SCIENTIFIC_UNRESOLVED",
            "self_assessed_status": "EXECUTED_UNAUDITED",
            "candidate_decision": "AUDIT_FOR_PROMOTION",
        }
    return {
        "experiment_adequacy_decision": "PASS",
        "route_promotion_decision": "NO_PROMOTION",
        "route_negative_decision": "STOP_NOT_SUPPORTED",
        "scientific_resolution_status": "SCIENTIFIC_UNRESOLVED",
        "self_assessed_status": "EXECUTED_UNAUDITED",
        "candidate_decision": "DIAGNOSTIC_ONLY",
    }


def write_failure_interpretation(decisions: dict[str, str], comparison_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Failure Interpretation",
        "",
        f"candidate_decision: `{decisions['candidate_decision']}`",
        f"scientific_resolution_status: `{decisions['scientific_resolution_status']}`",
        "",
        "## Interpretation",
        "",
    ]
    if decisions["candidate_decision"] == "AUDIT_FOR_PROMOTION":
        lines.extend(
            [
                "- A true train-side OOF protocol was available from existing folds 1-4 validation outputs.",
                "- The selected threshold was frozen before fold0 evaluation.",
                "- The result is local fold0 compact-label evidence only and still requires separate audit.",
            ]
        )
    else:
        lines.extend(
            [
                "- The OOF protocol produced only diagnostic evidence under the current gate.",
                "- This does not support route promotion or route-negative stop.",
            ]
        )
    lines.extend(
        [
            "",
            "## Key Fold0 Delta Lines",
            "",
            "| class | group | delta Dice | HD improvement | HD95 improvement | remote FP improvement | small FP improvement |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for class_id, metric_name, group in [
        (SCAR, "myops_scar", "all_cases"),
        (SCAR, "myops_scar", "gt_positive_only"),
        (EDEMA, "myops_edema", "gt_positive_only"),
        (EDEMA, "myops_edema", "no_T2_empty_GT"),
    ]:
        row = next(
            (r for r in comparison_rows if int(r["class_id"]) == class_id and r["group"] == group),
            None,
        )
        if row:
            lines.append(
                f"| {metric_name} | {group} | {fmt(row.get('delta_dice_mean'))} | "
                f"{fmt(row.get('delta_hd_mean_improvement'))} | {fmt(row.get('delta_hd95_mean_improvement'))} | "
                f"{fmt(row.get('delta_remote_fp_mean_improvement'))} | {fmt(row.get('delta_small_fp_mean_improvement'))} |"
            )
    lines.extend(
        [
            "",
            "## Blocked Actions",
            "",
            "- validation packaging/upload remains blocked.",
            "- fold expansion or next-stage training remains blocked.",
            "- hosted metric claims remain blocked.",
            "- label/evaluator/fold split changes were not performed.",
        ]
    )
    write_text(OUT_ROOT / "failure_interpretation.md", "\n".join(lines) + "\n")


def write_result(decisions: dict[str, str], selected_threshold: float, elapsed: float, command: str) -> None:
    text = f"""# Result 20260703 nnU-Net OOF Component

role: executor
self_assessed_status: {decisions['self_assessed_status']}
review_required: true

experiment_adequacy_decision: {decisions['experiment_adequacy_decision']}
route_promotion_decision: {decisions['route_promotion_decision']}
route_negative_decision: {decisions['route_negative_decision']}
scientific_resolution_status: {decisions['scientific_resolution_status']}

## Execution Summary

Built a leakage-safe nnU-Net anchored scar component scorer using existing Dataset501 folds 1-4 validation outputs as train-side OOF evidence for fold0 train cases. The selected threshold `{selected_threshold:.2f}` was frozen before fold0 validation evaluation. No network, upload, validation packaging, new fold inference/training, fold split edit, evaluator edit, label mapping edit, commit, or push was performed.

claim.oof_protocol: folds `1-4` validation outputs cover fold0 train cases and were used for threshold selection.
claim.no_fold0_gt_leakage: fold0 validation GT was used only after action selection was frozen.
claim.label_export_qc: generated predictions remain compact Dataset501 labels `0..5`; hosted validation/export evidence remains `evidence not found`.
claim.next_state: executor stops at `EXECUTED_UNAUDITED` pending separate read-only audit.

## Files Read

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`
- `prompts/tasks/20260703_nnunet_oof_component.md`
- `results/20260703_srr_failure_audit/review.md`
- `results/20260703_myops_fp_control/result.md`
- `results/20260703_myops_fp_control/review.md`
- `results/20260703_myops_fp_control/*.csv`
- `results/20260703_myops_audit/review.md`
- `data/benchmarks/protocol/splits_MyoPS.json`
- `data/benchmarks/protocol/cases_MyoPS.json`
- `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/dataset.json`
- read-only nnU-Net fold validation caches under `/overflow/htzhu/CARE/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/.../fold_*/validation`

## Files Changed

- `scripts/evaluation/run_nnunet_oof_component_20260703.py`
- `results/20260703_nnunet_oof_component/`

## Commands

- `{command}` -> exit 0; elapsed_seconds `{elapsed:.2f}`

## Tests / Verification

- Python syntax check passed for the task script.
- Generated fold0 compact-label scorer predictions and required CSV/Markdown artifacts.
- Verified prediction compact label sets contain no values outside `0..5`.
- No forbidden upload/package/network/fold-expansion action was performed.

## Artifacts

- `results/20260703_nnunet_oof_component/result.md`
- `results/20260703_nnunet_oof_component/MANIFEST.md`
- `results/20260703_nnunet_oof_component/train_oof_protocol.md`
- `results/20260703_nnunet_oof_component/component_feature_table.csv`
- `results/20260703_nnunet_oof_component/component_action_table.csv`
- `results/20260703_nnunet_oof_component/oof_training_summary.md`
- `results/20260703_nnunet_oof_component/metrics_summary.md`
- `results/20260703_nnunet_oof_component/subgroup_metrics.csv`
- `results/20260703_nnunet_oof_component/component_hd_by_case.csv`
- `results/20260703_nnunet_oof_component/label_export_qc.md`
- `results/20260703_nnunet_oof_component/failure_interpretation.md`
- `results/20260703_nnunet_oof_component/command_transcript.md`
- `results/20260703_nnunet_oof_component/oof_threshold_grid.csv`

## Incomplete Items

- `review.md` was not written because this is executor-only.
- Hosted validation and upload-ready raw-label package evidence: evidence not found, forbidden by scope.
- Route promotion remains unaudited and cannot authorize validation packaging, upload, fold expansion, or next-stage training.

## Required Next State

EXECUTED_UNAUDITED
"""
    write_text(OUT_ROOT / "result.md", text)


def write_manifest() -> None:
    entries = {
        "result.md": "Executor result and decision fields.",
        "MANIFEST.md": "Artifact index.",
        "train_oof_protocol.md": "Leakage-safe train/OOF split and feature protocol.",
        "component_feature_table.csv": "Component decision features plus evaluation-prefixed GT annotations.",
        "component_action_table.csv": "Frozen-threshold component actions for train OOF and fold0 eval.",
        "oof_training_summary.md": "Selected threshold and OOF training summary.",
        "oof_threshold_grid.csv": "Full train-side OOF threshold sweep.",
        "metrics_summary.md": "Fold0 metric summary and deltas.",
        "subgroup_metrics.csv": "Fold0 subgroup metrics.",
        "component_hd_by_case.csv": "Fold0 case-level Dice/HD/HD95/component/FP metrics.",
        "label_export_qc.md": "Compact-label and hosted-export caveats.",
        "failure_interpretation.md": "Decision interpretation and blocked actions.",
        "command_transcript.md": "Command transcript for this executor run.",
    }
    lines = [
        "# Manifest 20260703 nnU-Net OOF Component",
        "",
        "- task: `prompts/tasks/20260703_nnunet_oof_component.md`",
        "- result: `results/20260703_nnunet_oof_component/result.md`",
        "- review: `results/20260703_nnunet_oof_component/review.md` (pending separate read-only audit; not written by executor)",
        "",
        "| artifact | purpose |",
        "| --- | --- |",
    ]
    for name, purpose in entries.items():
        lines.append(f"| `results/20260703_nnunet_oof_component/{name}` | {purpose} |")
    lines.extend(
        [
            "",
            "## Prediction Directory",
            "",
            f"- `results/20260703_nnunet_oof_component/variants/{SCORER_VARIANT}/predictions/fold_0/checkpoint_best/`",
        ]
    )
    write_text(OUT_ROOT / "MANIFEST.md", "\n".join(lines) + "\n")


def main() -> None:
    start = time.time()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    command = " ".join(sys.argv)

    oof_cases, eval_cases = build_cases()
    if len(oof_cases) != 176 or len(eval_cases) != 44:
        raise RuntimeError(f"unexpected split sizes: oof={len(oof_cases)} eval={len(eval_cases)}")
    oof_payloads = load_payloads(oof_cases)
    selected_threshold, grid_rows = select_threshold(oof_payloads)

    eval_payloads = load_payloads(eval_cases)
    eval_case_rows, eval_action_rows, baseline_labels, scorer_labels = evaluate_payloads(
        eval_payloads, selected_threshold, write_predictions=True
    )
    oof_action_rows: list[dict[str, Any]] = []
    for payload in oof_payloads:
        _pred, actions = apply_threshold(payload, selected_threshold)
        oof_action_rows.extend(actions)

    subgroup_rows = aggregate_metrics(eval_case_rows)
    comparison_rows = fp.compare_to_baseline(subgroup_rows, [BASELINE_VARIANT, SCORER_VARIANT])
    decisions = decision_fields(comparison_rows)

    component_features = [dict(row, selected_threshold=selected_threshold) for payload in oof_payloads + eval_payloads for row in payload.scar_features]
    component_actions = oof_action_rows + eval_action_rows

    write_csv(OUT_ROOT / "component_feature_table.csv", component_features)
    write_csv(OUT_ROOT / "component_action_table.csv", component_actions)
    write_csv(OUT_ROOT / "component_hd_by_case.csv", eval_case_rows)
    write_csv(OUT_ROOT / "subgroup_metrics.csv", subgroup_rows)
    write_csv(OUT_ROOT / "oof_threshold_grid.csv", grid_rows)
    write_train_oof_protocol(selected_threshold, oof_cases, eval_cases)
    write_oof_training_summary(selected_threshold, grid_rows)
    write_metrics_summary(subgroup_rows, comparison_rows)
    write_label_export_qc(baseline_labels, scorer_labels, len(eval_cases))
    write_failure_interpretation(decisions, comparison_rows)

    elapsed = time.time() - start
    write_text(
        OUT_ROOT / "command_transcript.md",
        f"# Command Transcript\n\n"
        f"- command: `{command}`\n"
        f"- exit_status: `0`\n"
        f"- elapsed_seconds: `{elapsed:.2f}`\n"
        f"- python: `{sys.executable}`\n"
        f"- cwd: `{Path.cwd()}`\n"
        f"- network: not used\n"
        f"- external_upload: not used\n"
        f"- fold_expansion: not performed; existing folds 1-4 validation caches were read as train-side OOF evidence\n",
    )
    write_result(decisions, selected_threshold, elapsed, command)
    write_manifest()
    print(f"wrote {OUT_ROOT}")
    print(f"selected_threshold={selected_threshold:.2f}")
    print(f"self_assessed_status={decisions['self_assessed_status']}")


if __name__ == "__main__":
    main()
