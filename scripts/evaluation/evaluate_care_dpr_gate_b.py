#!/usr/bin/env python3
"""Formal CARE-DPR Gate B fold0 evaluator.

This evaluator uses the Gate A-R2 two-pass DPR inference contract:
Pass 1 aggregates full-volume shared features and proposal maps; Pass 2 builds
whole-volume candidates and calls the pathology-specific local refiner and
component utility MLP once per candidate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import SimpleITK as sitk
import torch
from scipy import ndimage as ndi

from scripts.evaluation.evaluate_care_dg import (
    LABEL_ROOT,
    PATHOLOGIES,
    case_mask,
    finite_mean,
    metric_rows_for_case,
    summarize,
    transition_rows,
)
from scripts.evaluation.evaluate_care_dpr import (
    aupr,
    auroc,
    candidate_utility_target,
    component_recall_precision_np,
    dice_np,
)
from scripts.training.run_care_dpr import source_hashes, stable_json_sha256
from src.care_myocardium.data.care_dpr_dataset import (
    CaseCache,
    deterministic_inner_split,
    distance_to_reliable_gt,
    load_splits,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_dpr_predictor import (
    THRESHOLD_CANDIDATES,
    run_two_pass_full_volume_dpr,
)
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.training.care_dpr_trainer import load_care_dpr_checkpoint

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
RUNTIME_ROOT = RESULT_ROOT / "runtime" / "formal_fold0"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: set[str] = set()
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
        fieldnames = fieldnames or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    h = hashlib.sha256()
    h.update(str(arr.shape).encode())
    h.update(str(arr.dtype).encode())
    h.update(np.ascontiguousarray(arr).tobytes())
    return h.hexdigest()


def anchor_rows_for_cases(cases: list[str], population: str, case_to_fold: dict[str, int], metadata: Any, cache: CaseCache) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_id in cases:
        meta = metadata[case_id]
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        ref = sitk.ReadImage(str(LABEL_ROOT / f"{case_id}.nii.gz"))
        spacing = tuple(float(v) for v in ref.GetSpacing()[::-1])
        anchor = rec["anchor_mask"].astype(np.uint8, copy=False)
        gt = rec["labels"].astype(np.uint8, copy=False)
        rows.extend(metric_rows_for_case(case_id, population, "A0_nnunet_anchor", anchor, anchor, gt, meta, spacing))
    return rows


def proposal_mechanisms(pass1: dict[str, np.ndarray], rec: dict[str, np.ndarray], *, t2_present: bool) -> dict[str, Any]:
    labels = rec["labels"]
    anchor = rec["anchor_mask"]
    scar_gt = labels == SCAR_CHANNEL
    edema_gt = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
    scar_anchor = anchor == SCAR_CHANNEL
    edema_anchor = (anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)
    support = rec["myocardium_support"][0] > 0.1
    edema_support = (rec["edema_support"][0] > 0.1) & bool(t2_present)
    scar_fn = scar_gt & ~scar_anchor
    scar_fp = ~scar_gt & scar_anchor
    edema_fn = edema_gt & ~edema_anchor
    edema_fp = ~edema_gt & edema_anchor
    return {
        "scores": {
            "scar_p": (pass1["scar_p_coarse"], scar_gt, support),
            "scar_qfn": (pass1["scar_q_fn"], scar_fn, support),
            "scar_qfp": (pass1["scar_q_fp"] * scar_anchor.astype(np.float32), scar_fp, support),
            "edema_p": (pass1["edema_p_coarse"], edema_gt, edema_support),
            "edema_qfn": (pass1["edema_q_fn"], edema_fn, edema_support),
            "edema_qfp": (pass1["edema_q_fp"] * edema_anchor.astype(np.float32), edema_fp, edema_support),
        },
        "components": {
            "scar": component_recall_precision_np(pass1["scar_p_coarse"] >= 0.30, scar_gt, support),
            "edema_zone": component_recall_precision_np(pass1["edema_p_coarse"] >= 0.30, edema_gt, edema_support) if t2_present else (0.0, 1.0),
        },
        "roi": {
            "scar_coverage": float((((pass1["scar_p_coarse"] >= 0.5) | (pass1["scar_q_fn"] >= 0.5) | (pass1["scar_q_fp"] >= 0.5) | scar_anchor) & scar_gt).sum() / max(int(scar_gt.sum()), 1)),
            "edema_coverage": float((((pass1["edema_p_coarse"] >= 0.5) | (pass1["edema_q_fn"] >= 0.5) | (pass1["edema_q_fp"] >= 0.5) | edema_anchor) & edema_gt & edema_support).sum() / max(int((edema_gt & edema_support).sum()), 1)) if t2_present else 0.0,
            "scar_support_volume_ratio": float(((pass1["scar_p_coarse"] >= 0.5) | (pass1["scar_q_fn"] >= 0.5) | (pass1["scar_q_fp"] >= 0.5) | scar_anchor).sum() / max(int(support.sum()), 1)),
            "edema_support_volume_ratio": float((((pass1["edema_p_coarse"] >= 0.5) | (pass1["edema_q_fn"] >= 0.5) | (pass1["edema_q_fp"] >= 0.5) | edema_anchor) & edema_support).sum() / max(int(edema_support.sum()), 1)) if t2_present else 0.0,
            "scar_predicted_refiner_dice": dice_np(pass1["scar_p_refined"] >= 0.5, scar_gt, (pass1["scar_p_coarse"] >= 0.5) | (pass1["scar_q_fn"] >= 0.5) | (pass1["scar_q_fp"] >= 0.5) | scar_anchor),
            "edema_predicted_refiner_dice": dice_np(pass1["edema_p_refined"] >= 0.5, edema_gt, ((pass1["edema_p_coarse"] >= 0.5) | (pass1["edema_q_fn"] >= 0.5) | (pass1["edema_q_fp"] >= 0.5) | edema_anchor) & edema_support) if t2_present else 0.0,
            "scar_teacher_refiner_dice": dice_np(scar_gt, scar_gt, scar_gt | scar_anchor),
            "edema_teacher_refiner_dice": dice_np(edema_gt, edema_gt, (edema_gt | edema_anchor) & edema_support) if t2_present else 0.0,
        },
    }


def collect_candidate_targets(pred: dict[str, Any], rec: dict[str, np.ndarray], *, case_id: str, t2_present: bool, population: str) -> list[dict[str, Any]]:
    labels = rec["labels"]
    gt_maps = {
        "scar": labels == SCAR_CHANNEL,
        "edema_zone": (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL),
    }
    dist_maps = {
        "scar": distance_to_reliable_gt(rec, pathology="scar", t2_present=t2_present)[0],
        "edema_zone": distance_to_reliable_gt(rec, pathology="edema_zone", t2_present=t2_present)[0],
    }
    rows: list[dict[str, Any]] = []
    for item in pred.get("candidate_evidence", []):
        pathology = str(item["pathology"])
        accept, utility, reason = candidate_utility_target(
            item["anchor_local_mask"],
            item["refined_local_mask"],
            gt_maps[pathology],
            dist_maps[pathology],
            str(item["candidate_type"]),
        )
        rows.append({
            "case_id": case_id,
            "population": population,
            "pathology": pathology,
            "candidate_type": item["candidate_type"],
            "utility_score": float(item["utility_score"]),
            "utility_regression": float(item["utility_regression"]),
            "accepted_at_runtime_threshold": bool(item["accepted"]),
            "accept_target": int(accept),
            "utility_target": float(utility),
            "target_reason": reason,
            "source": "model_real_full_volume_candidate",
        })
    return rows


def summarize_mechanisms(score_rows: dict[str, list[tuple[np.ndarray, np.ndarray]]], component_values: dict[str, list[tuple[float, float]]], roi_rows: list[dict[str, float]], candidate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    key_map = {
        "scar_p": ("scar_p_coarse_auprc", "scar_p_coarse_positive_prevalence"),
        "scar_qfn": ("scar_q_fn_auprc", "scar_q_fn_positive_prevalence"),
        "scar_qfp": ("scar_q_fp_auprc", "scar_q_fp_positive_prevalence"),
        "edema_p": ("edema_p_coarse_auprc", "edema_p_coarse_positive_prevalence"),
        "edema_qfn": ("edema_q_fn_auprc", "edema_q_fn_positive_prevalence"),
        "edema_qfp": ("edema_q_fp_auprc", "edema_q_fp_positive_prevalence"),
    }
    proposal: dict[str, Any] = {}
    for short, (aupr_key, prev_key) in key_map.items():
        scores = np.concatenate([s for s, _ in score_rows.get(short, [])]) if score_rows.get(short) else np.asarray([], dtype=np.float32)
        labels = np.concatenate([l for _, l in score_rows.get(short, [])]) if score_rows.get(short) else np.asarray([], dtype=np.uint8)
        proposal[aupr_key] = aupr(scores, labels)
        proposal[prev_key] = float(labels.mean()) if labels.size else 0.0
    for pathology in ("scar", "edema_zone"):
        vals = component_values.get(pathology, [])
        proposal[f"{pathology}_p_coarse_component_recall"] = float(np.mean([v[0] for v in vals])) if vals else 0.0
        proposal[f"{pathology}_p_coarse_component_precision"] = float(np.mean([v[1] for v in vals])) if vals else 0.0
    scores = np.asarray([r["utility_score"] for r in candidate_rows], dtype=np.float64)
    labels = np.asarray([r["accept_target"] for r in candidate_rows], dtype=np.float64)
    utilities = np.asarray([r["utility_target"] for r in candidate_rows], dtype=np.float64)
    threshold_rows = []
    for threshold in THRESHOLD_CANDIDATES:
        accepted = scores >= float(threshold)
        threshold_rows.append({
            "threshold": float(threshold),
            "accepted": int(accepted.sum()),
            "rejected": int((~accepted).sum()),
            "realized_gain": float(np.clip(utilities[accepted], 0, None).sum()) if utilities.size else 0.0,
            "has_nonzero_accepted_and_rejected": bool(accepted.any() and (~accepted).any()),
        })
    counts = defaultdict(int)
    for row in candidate_rows:
        counts[f"{row['pathology']}_{row['candidate_type']}"] += 1
    return {
        "proposal_metrics": proposal,
        "roi_metrics": {
            key: float(np.mean([r[key] for r in roi_rows])) if roi_rows else 0.0
            for key in [
                "scar_coverage",
                "edema_coverage",
                "scar_support_volume_ratio",
                "edema_support_volume_ratio",
                "scar_predicted_refiner_dice",
                "edema_predicted_refiner_dice",
                "scar_teacher_refiner_dice",
                "edema_teacher_refiner_dice",
            ]
        },
        "utility_metrics": {
            "component_descriptor_fields": [
                "pooled_aggregated_shared_full_resolution_feature",
                "pooled_p_coarse",
                "pooled_q_fn",
                "pooled_q_fp",
                "pooled_p_refined",
                "anchor_margin",
                "uncertainty",
                "distance_to_support",
                "voxel_volume",
                "surface_compactness",
                "bounding_box_size",
                "candidate_type",
                "component_truncation_flag",
            ],
            "primary_metric_source": "model_real_full_volume_candidates_only",
            "synthetic_utility_variants_used_for_primary_gate": False,
            "true_candidate_total_count": len(candidate_rows),
            "candidate_counts": dict(counts),
            "accept_target_positive_count": int(labels.sum()) if labels.size else 0,
            "accept_target_negative_count": int(labels.size - labels.sum()) if labels.size else 0,
            "positive_prevalence": float(labels.mean()) if labels.size else 0.0,
            "component_utility_auroc": auroc(scores, labels) if labels.size else 0.5,
            "component_utility_auprc": aupr(scores, labels) if labels.size else 0.0,
            "threshold_candidates": threshold_rows,
            "oracle_gain": float(np.clip(utilities, 0, None).sum()) if utilities.size else 0.0,
            "realized_gain": max((row["realized_gain"] for row in threshold_rows), default=0.0),
        },
    }


def choose_threshold(inner_candidate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = np.asarray([r["utility_score"] for r in inner_candidate_rows], dtype=np.float64)
    utilities = np.asarray([r["utility_target"] for r in inner_candidate_rows], dtype=np.float64)
    rows = []
    for threshold in THRESHOLD_CANDIDATES:
        accepted = scores >= float(threshold)
        rows.append({
            "threshold": float(threshold),
            "accepted": int(accepted.sum()),
            "rejected": int((~accepted).sum()),
            "realized_gain": float(np.clip(utilities[accepted], 0, None).sum()) if utilities.size else 0.0,
            "has_nonzero_accepted_and_rejected": bool(accepted.any() and (~accepted).any()),
        })
    eligible = [r for r in rows if r["has_nonzero_accepted_and_rejected"]]
    selected = max(eligible or rows, key=lambda r: (float(r["realized_gain"]), -abs(float(r["threshold"]) - 0.5)))
    return {
        "status": "PASS" if inner_candidate_rows else "FAIL",
        "checkpoint_selection_rule": "formal_terminal_step04000_only_fixed_by_training_contract",
        "outer_fold0_used_for_checkpoint_or_threshold_selection": False,
        "selected_utility_threshold": float(selected["threshold"]),
        "threshold_rows": rows,
        "inner_real_candidate_count": len(inner_candidate_rows),
    }


def evaluate_population(
    *,
    model: torch.nn.Module,
    cases: list[str],
    population: str,
    case_to_fold: dict[str, int],
    metadata: Any,
    cache: CaseCache,
    device: torch.device,
    utility_threshold: float,
    model_name: str,
) -> dict[str, Any]:
    casewise: list[dict[str, Any]] = []
    activation: list[dict[str, Any]] = []
    transition: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    prediction_hashes: list[dict[str, Any]] = []
    score_rows: dict[str, list[tuple[np.ndarray, np.ndarray]]] = defaultdict(list)
    component_values: dict[str, list[tuple[float, float]]] = defaultdict(list)
    roi_rows: list[dict[str, float]] = []
    no_t2_rows: list[dict[str, Any]] = []
    for idx, case_id in enumerate(cases):
        meta = metadata[case_id]
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        ref = sitk.ReadImage(str(LABEL_ROOT / f"{case_id}.nii.gz"))
        spacing = tuple(float(v) for v in ref.GetSpacing()[::-1])
        gt = rec["labels"].astype(np.uint8, copy=False)
        anchor = rec["anchor_mask"].astype(np.uint8, copy=False)
        batch_np = {
            "images": rec["images"],
            "availability": rec["availability"],
            "anchor_logits": rec["anchor_logits"],
            "anchor_mask": rec["anchor_mask"],
            "uncertainty": rec["uncertainty"],
            "myocardium_support": rec["myocardium_support"],
            "edema_support": rec["edema_support"],
            "distance_to_myocardium": rec["distance_to_myocardium"],
            "t2_present": bool(meta.t2_present),
        }
        pred = run_two_pass_full_volume_dpr(
            model,
            batch_np,
            patch_shape=(8, 128, 128),
            overlap=0.5,
            proposal_threshold=0.5,
            refined_threshold=0.5,
            utility_threshold=utility_threshold,
            device=device,
        )
        final = pred["final_mask"].astype(np.uint8, copy=False)
        casewise.extend(metric_rows_for_case(case_id, population, model_name, final, anchor, gt, meta, spacing))
        transition.extend(transition_rows(case_id, anchor, anchor, final))
        cand_rows = collect_candidate_targets(pred, rec, case_id=case_id, t2_present=bool(meta.t2_present), population=population)
        candidate_rows.extend(cand_rows)
        mech = proposal_mechanisms(pred["pass1"], rec, t2_present=bool(meta.t2_present))
        for name, (scores, labels, mask) in mech["scores"].items():
            m = mask.astype(bool)
            if np.any(m):
                score_rows[name].append((scores[m].reshape(-1).astype(np.float32), labels[m].reshape(-1).astype(np.uint8)))
        for pathology, pair in mech["components"].items():
            if pathology == "edema_zone" and not bool(meta.t2_present):
                continue
            component_values[pathology].append(pair)
        roi_rows.append(mech["roi"])
        activation.append({
            "case_id": case_id,
            "population": population,
            "model": model_name,
            "t2_present": bool(meta.t2_present),
            "two_pass_full_volume_candidate_pipeline": bool(pred.get("two_pass_full_volume_candidate_pipeline")),
            "pass1_aggregates_patch_final_labels": bool(pred.get("pass1_aggregates_patch_final_labels")),
            "pass1_runs_component_decision": bool(pred.get("pass1_runs_component_decision")),
            "pass2_refines_each_candidate": bool(pred.get("pass2_refines_each_candidate")),
            "component_utility_calls": int(pred.get("component_utility_calls", 0)),
            "candidate_count": len(pred.get("candidate_evidence", [])),
            "accepted_candidates": sum(1 for r in pred.get("candidate_evidence", []) if r.get("accepted")),
            "rejected_candidates": sum(1 for r in pred.get("candidate_evidence", []) if not r.get("accepted")),
            "changed_voxels_vs_anchor": int(np.count_nonzero(final != anchor)),
            "scar_changed_voxels_vs_anchor": int(np.count_nonzero(case_mask(final, "scar") != case_mask(anchor, "scar"))),
            "edema_zone_changed_voxels_vs_anchor": int(np.count_nonzero(case_mask(final, "edema_zone") != case_mask(anchor, "edema_zone"))),
            "prediction_sha256": sha256_array(final),
        })
        if not bool(meta.t2_present):
            no_t2_rows.append({
                "case_id": case_id,
                "edema_candidate_count": sum(1 for r in pred.get("candidate_evidence", []) if r["pathology"] == "edema_zone"),
                "edema_p_refined_voxels": int(np.count_nonzero(pred["pass1"]["edema_p_refined"] > 0)),
                "pure_edema_changed_voxels_vs_anchor": int(np.count_nonzero(case_mask(final, "pure_edema") != case_mask(anchor, "pure_edema"))),
                "status": "PASS" if sum(1 for r in pred.get("candidate_evidence", []) if r["pathology"] == "edema_zone") == 0 and int(np.count_nonzero(pred["pass1"]["edema_p_refined"] > 0)) == 0 and int(np.count_nonzero(case_mask(final, "pure_edema") != case_mask(anchor, "pure_edema"))) == 0 else "FAIL",
            })
        prediction_hashes.append({"case_id": case_id, "population": population, "prediction_sha256": sha256_array(final)})
        print(json.dumps({"case": case_id, "index": idx + 1, "total": len(cases), "population": population, "candidates": activation[-1]["candidate_count"], "accepted": activation[-1]["accepted_candidates"], "changed_voxels": activation[-1]["changed_voxels_vs_anchor"]}), flush=True)
    return {
        "casewise": casewise,
        "activation": activation,
        "transition": transition,
        "candidate_rows": candidate_rows,
        "prediction_hashes": prediction_hashes,
        "mechanisms": summarize_mechanisms(score_rows, component_values, roi_rows, candidate_rows),
        "no_t2": no_t2_rows,
    }


def scientific_gate(summary_rows: list[dict[str, Any]], help_harm: list[dict[str, Any]], no_t2_rows: list[dict[str, Any]], mechanism_report: dict[str, Any]) -> dict[str, Any]:
    by = {(r["population"], r["model"], r["pathology"]): r for r in summary_rows}
    population = "fold0_complete_trimodal16"
    failures: list[str] = []
    pathology_checks = []
    improvements = 0

    def metric_float(value: Any, fallback: float) -> float:
        try:
            out = float(value)
        except (TypeError, ValueError):
            return fallback
        return out if math.isfinite(out) else fallback

    for pathology in PATHOLOGIES:
        anchor = by.get((population, "A0_nnunet_anchor", pathology))
        dpr = by.get((population, "A2_care_dpr_gate_b_selected", pathology))
        if not anchor or not dpr:
            failures.append(f"missing_summary:{pathology}")
            continue
        dice_delta = metric_float(dpr["dice_mean"], 0.0) - metric_float(anchor["dice_mean"], 0.0)
        hd95_ok = metric_float(dpr["hd95_mean_mm"], 1e6) <= 1.05 * max(metric_float(anchor["hd95_mean_mm"], 1e6), 1e-6)
        remote_ok = metric_float(dpr["remote_fp_volume_mean_mm3"], 1e6) <= 1.10 * max(metric_float(anchor["remote_fp_volume_mean_mm3"], 0.0), 1e-6)
        comp_ok = metric_float(dpr["component_count_mean"], 1e6) <= 10.0 * max(metric_float(anchor["component_count_mean"], 1.0), 1.0)
        if dice_delta < -0.005:
            failures.append(f"{pathology}_dice_below_anchor_by_more_than_0.005:{dice_delta:.6f}")
        if dice_delta > 0.005:
            improvements += 1
        if not hd95_ok:
            failures.append(f"{pathology}_hd95_gt_1.05x_anchor")
        if not remote_ok:
            failures.append(f"{pathology}_remote_fp_gt_1.10x_anchor")
        if not comp_ok:
            failures.append(f"{pathology}_component_count_order_of_magnitude_explosion")
        pathology_checks.append({"pathology": pathology, "dice_delta": dice_delta, "hd95_ok": hd95_ok, "remote_fp_ok": remote_ok, "component_count_ok": comp_ok})
    if improvements < 1:
        failures.append("no_pathology_improves_by_more_than_0.005")
    complete_hh = [r for r in help_harm if r["population"] == population]
    help_count = sum(1 for r in complete_hh if r["help_harm"] == "help")
    harm_count = sum(1 for r in complete_hh if r["help_harm"] == "harm")
    if help_count < harm_count - 1:
        failures.append(f"help_lt_harm_minus_1:{help_count}<{harm_count}-1")
    utility = mechanism_report.get("utility_metrics", {})
    if int(utility.get("true_candidate_total_count", 0)) <= 0:
        failures.append("no_real_candidates")
    if int(utility.get("accept_target_positive_count", 0)) <= 0 or int(utility.get("accept_target_negative_count", 0)) <= 0:
        failures.append("utility_targets_not_both_classes")
    if not any(bool(row.get("has_nonzero_accepted_and_rejected")) for row in utility.get("threshold_candidates", [])):
        failures.append("no_threshold_with_nonzero_accept_reject")
    if not all(row.get("status") == "PASS" for row in no_t2_rows):
        failures.append("no_t2_exact_zero_fail")
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "scientific_expansion_authorized": False,
        "formal_gate_b_scientific_checks": pathology_checks,
        "help_count": help_count,
        "harm_count": harm_count,
        "help_ge_harm_minus_1": help_count >= harm_count - 1,
    }


def run_gate_b(args: argparse.Namespace) -> dict[str, Any]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    splits = load_splits()
    fold = next(row for row in splits if int(row["fold"]) == int(args.fold))
    outer_val = sorted(fold["val"])
    complete_val = [case_id for case_id in outer_val if metadata[case_id].modality_group == "C0+LGE+T2"]
    if len(outer_val) != 44:
        raise RuntimeError(f"Gate B expected outer44, got {len(outer_val)}")
    if len(complete_val) != 16:
        raise RuntimeError(f"Gate B expected complete16, got {len(complete_val)}")
    split_payload = deterministic_inner_split(sorted(fold["train"]), int(args.fold), metadata)
    inner_cases = list(split_payload["complete_inner_select_cases"])
    case_to_fold = {case_id: int(row["fold"]) for row in splits for case_id in row["val"]}
    checkpoint = RUNTIME_ROOT / "checkpoints" / args.checkpoint
    receipt_path = RUNTIME_ROOT / "fold_training_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS" or int(receipt.get("actual_optimizer_steps", -1)) != 4000:
        raise RuntimeError("CARE_DPR_FORMAL_FOLD0_RECEIPT_NOT_PASS_4000")
    device = torch.device(args.device if args.device else ("cuda" if torch.cuda.is_available() and not args.cpu else "cpu"))
    model, step, extra = load_care_dpr_checkpoint(checkpoint)
    if int(step) != 4000:
        raise RuntimeError(f"CARE_DPR_GATE_B_EXPECTS_STEP04000:{step}")
    model.to(device).eval()
    out_root = RUNTIME_ROOT / "gate_b_evaluation"
    cache = CaseCache(max_cases=int(args.cache_cases))

    inner_eval = evaluate_population(
        model=model,
        cases=inner_cases,
        population="fold0_train_side_complete_inner12",
        case_to_fold=case_to_fold,
        metadata=metadata,
        cache=cache,
        device=device,
        utility_threshold=0.5,
        model_name="A2_care_dpr_inner_threshold_probe",
    )
    selection = choose_threshold(inner_eval["candidate_rows"])
    selected_threshold = float(selection["selected_utility_threshold"])

    casewise: list[dict[str, Any]] = []
    casewise.extend(anchor_rows_for_cases(outer_val, "fold0_outer44", case_to_fold, metadata, cache))
    casewise.extend(anchor_rows_for_cases(complete_val, "fold0_complete_trimodal16", case_to_fold, metadata, cache))
    outer_eval = evaluate_population(
        model=model,
        cases=outer_val,
        population="fold0_outer44",
        case_to_fold=case_to_fold,
        metadata=metadata,
        cache=cache,
        device=device,
        utility_threshold=selected_threshold,
        model_name="A2_care_dpr_gate_b_selected",
    )
    casewise.extend(outer_eval["casewise"])
    complete_eval = evaluate_population(
        model=model,
        cases=complete_val,
        population="fold0_complete_trimodal16",
        case_to_fold=case_to_fold,
        metadata=metadata,
        cache=cache,
        device=device,
        utility_threshold=selected_threshold,
        model_name="A2_care_dpr_gate_b_selected",
    )
    casewise.extend(complete_eval["casewise"])

    summary = summarize(casewise)
    anchor_by_key = {(r["population"], r["pathology"], r["case_id"]): r for r in casewise if r["model"] == "A0_nnunet_anchor"}
    help_harm: list[dict[str, Any]] = []
    for row in casewise:
        if row["model"] != "A2_care_dpr_gate_b_selected":
            continue
        anchor_row = anchor_by_key[(row["population"], row["pathology"], row["case_id"])]
        delta = float(row["dice"]) - float(anchor_row["dice"])
        help_harm.append({
            "case_id": row["case_id"],
            "population": row["population"],
            "pathology": row["pathology"],
            "anchor_dice": anchor_row["dice"],
            "care_dpr_dice": row["dice"],
            "dice_delta": delta,
            "help_harm": "help" if delta > 1e-6 else ("harm" if delta < -1e-6 else "neutral"),
            "changed_components": row["new_component_count_vs_anchor"],
            "farthest_new_component_distance_mm": row["farthest_new_component_distance_mm"],
        })

    outer_mechanism = outer_eval["mechanisms"]
    no_t2_rows = outer_eval["no_t2"] + complete_eval["no_t2"]
    gate = scientific_gate(summary, help_harm, no_t2_rows, outer_mechanism)
    exact_tail = sorted([r for r in casewise if r["model"] == "A2_care_dpr_gate_b_selected"], key=lambda r: math.inf if math.isinf(float(r["exact_hd_mm"])) else float(r["exact_hd_mm"]), reverse=True)[:50]
    remote_rows = [r for r in casewise if r["model"] == "A2_care_dpr_gate_b_selected" and float(r["remote_fp_volume_mm3"]) > 0]
    component_rows = [r for r in casewise if r["model"] == "A2_care_dpr_gate_b_selected"]
    notification = {
        "subject": "[CARE-DPR][B/2] Fold0双病理结果完成，等待下一轮决策",
        "state": "AWAITING_HUMAN_ACCEPTANCE_DPR_GATE_B",
        "approval_token": "APPROVE_DPR_GATE_B",
        "formal_fold0_authorized_next": False,
        "fold_expansion_authorized": False,
        "all_data_fit_authorized": False,
        "validation_upload_authorized": False,
    }
    gate_summary = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_B",
        "generated_at_utc": now_utc(),
        "status": "GATE_B_OPERATIONAL_PASS" if gate["status"] == "PASS" else "GATE_B_SCIENTIFIC_REVIEW_REQUIRED",
        "scientific_gate": gate,
        "fold": int(args.fold),
        "checkpoint": str(checkpoint.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(checkpoint),
        "checkpoint_step": int(step),
        "resolved_training_contract_hash": receipt.get("resolved_training_contract_hash"),
        "selection": selection,
        "outer_fold0_used_for_checkpoint_or_threshold_selection": False,
        "teacher_roi_inner_outer_inference": False,
        "predicted_roi_only_for_inner_outer_inference": True,
        "preflight_credit": 0,
        "formal_training_credit": int(receipt.get("formal_training_credit", 0)),
        "outer_heldout_cases": len(outer_val),
        "complete_trimodal_heldout_cases": len(complete_val),
        "outer44_case_ids_sha256": stable_json_sha256(outer_val),
        "complete16_case_ids_sha256": stable_json_sha256(complete_val),
        "train_side_inner12_case_ids_sha256": stable_json_sha256(inner_cases),
        "two_pass_full_volume_inference_contract": {
            "status": "PASS" if all(row["two_pass_full_volume_candidate_pipeline"] and not row["pass1_aggregates_patch_final_labels"] and not row["pass1_runs_component_decision"] and row["pass2_refines_each_candidate"] for row in outer_eval["activation"] + complete_eval["activation"]) else "FAIL",
            "overlap": 0.5,
            "gaussian_blending": True,
            "pass1_aggregates": ["shared_full_resolution_feature", "p_coarse", "q_fn", "q_fp"],
            "pass2_per_candidate_refinement": True,
            "patch_final_label_averaging": False,
            "patch_local_component_decision": False,
        },
        "mechanism_report": outer_mechanism,
        "no_t2_exact_zero": {
            "status": "PASS" if all(row["status"] == "PASS" for row in no_t2_rows) else "FAIL",
            "rows": no_t2_rows,
        },
        "checkpoint_reload_exact": receipt.get("checkpoint_reload", {}),
        "sampler_audit": {
            "stage_a1": json.loads((RUNTIME_ROOT / "sampler_audit_stage_a1.json").read_text(encoding="utf-8")),
            "stage_a2": json.loads((RUNTIME_ROOT / "sampler_audit_stage_a2.json").read_text(encoding="utf-8")),
            "stage_b": json.loads((RUNTIME_ROOT / "sampler_audit_stage_b.json").read_text(encoding="utf-8")),
        },
        "source_hashes": {
            **source_hashes(),
            "scripts/evaluation/evaluate_care_dpr_gate_b.py": sha256_file(REPO_ROOT / "scripts/evaluation/evaluate_care_dpr_gate_b.py"),
        },
        "outputs": {
            "casewise": str((out_root / "gate_b_casewise_metrics.csv").relative_to(REPO_ROOT)),
            "summary": str((out_root / "gate_b_model_summary.csv").relative_to(REPO_ROOT)),
            "complete16_summary": str((out_root / "gate_b_complete16_summary.csv").relative_to(REPO_ROOT)),
            "outer44_summary": str((out_root / "gate_b_outer44_summary.csv").relative_to(REPO_ROOT)),
            "help_harm": str((out_root / "gate_b_help_harm.csv").relative_to(REPO_ROOT)),
            "mechanism": str((out_root / "gate_b_mechanism_report.json").relative_to(REPO_ROOT)),
            "selection": str((out_root / "gate_b_checkpoint_threshold_selection.json").relative_to(REPO_ROOT)),
        },
        "notification": notification,
    }
    out_root.mkdir(parents=True, exist_ok=True)
    write_csv(out_root / "gate_b_inner_candidate_rows.csv", inner_eval["candidate_rows"])
    write_csv(out_root / "gate_b_outer_candidate_rows.csv", outer_eval["candidate_rows"])
    write_csv(out_root / "gate_b_casewise_metrics.csv", casewise)
    write_csv(out_root / "gate_b_model_summary.csv", summary)
    write_csv(out_root / "gate_b_complete16_summary.csv", [r for r in summary if r["population"] == "fold0_complete_trimodal16"])
    write_csv(out_root / "gate_b_outer44_summary.csv", [r for r in summary if r["population"] == "fold0_outer44"])
    write_csv(out_root / "gate_b_help_harm.csv", help_harm)
    write_csv(out_root / "gate_b_exact_hd_tail_audit.csv", exact_tail)
    write_csv(out_root / "gate_b_remote_fp_audit.csv", remote_rows)
    write_csv(out_root / "gate_b_component_audit.csv", component_rows)
    write_csv(out_root / "gate_b_activation_audit.csv", outer_eval["activation"] + complete_eval["activation"])
    write_csv(out_root / "gate_b_transition_matrix.csv", outer_eval["transition"] + complete_eval["transition"])
    write_csv(out_root / "gate_b_no_t2_safety_audit.csv", no_t2_rows)
    write_csv(out_root / "gate_b_prediction_hashes.csv", outer_eval["prediction_hashes"] + complete_eval["prediction_hashes"])
    write_json(out_root / "gate_b_checkpoint_threshold_selection.json", selection)
    write_json(out_root / "gate_b_mechanism_report.json", outer_mechanism)
    write_json(out_root / "gate_b_scientific_gate.json", gate)
    write_json(out_root / "gate_b_summary.json", gate_summary)
    write_json(RESULT_ROOT / "gate_b_summary.json", {**gate_summary, "evidence_root": str(out_root.relative_to(REPO_ROOT))})
    write_json(RESULT_ROOT / "checkpoint_notifications/dpr_gate_b.json", {**notification, "gate_summary": gate_summary})
    return gate_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--checkpoint", default="checkpoint_step04000.pt")
    parser.add_argument("--cache-cases", type=int, default=16)
    parser.add_argument("--device", default="")
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    result = run_gate_b(args)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["two_pass_full_volume_inference_contract"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
