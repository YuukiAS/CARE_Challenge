#!/usr/bin/env python3
"""Gate B-R1 old-run checkpoint diagnostics on train-side inner12 only."""

from __future__ import annotations

import argparse
import csv
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
import torch

from scripts.evaluation.evaluate_care_dpr import (
    aupr,
    auroc,
    candidate_utility_target,
    component_recall_precision_np,
    dice_np,
)
from scripts.evaluation.evaluate_care_dpr_gate_b import proposal_mechanisms, sha256_file
from scripts.training.run_care_dpr import stable_json_sha256
from src.care_myocardium.data.care_dpr_dataset import (
    CaseCache,
    deterministic_inner_split,
    distance_to_reliable_gt,
    load_splits,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_dpr_predictor import THRESHOLD_CANDIDATES, run_two_pass_full_volume_dpr
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.training.care_dpr_trainer import load_care_dpr_checkpoint

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
FORMAL_RUNTIME = RESULT_ROOT / "runtime" / "formal_fold0"
OUT_ROOT = FORMAL_RUNTIME / "gate_b_r1_old_run_diagnostic"
CHECKPOINT_STEPS = (500, 1000, 1500, 2000, 2500, 3000, 3500, 4000)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: set[str] = set(); fieldnames = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key); fieldnames.append(key)
        fieldnames = fieldnames or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def score_dist(values: list[float]) -> dict[str, Any]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return {"count": 0, "min": "NA", "p05": "NA", "p25": "NA", "median": "NA", "p75": "NA", "p95": "NA", "max": "NA", "mean": "NA"}
    return {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "p05": float(np.quantile(arr, 0.05)),
        "p25": float(np.quantile(arr, 0.25)),
        "median": float(np.median(arr)),
        "p75": float(np.quantile(arr, 0.75)),
        "p95": float(np.quantile(arr, 0.95)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
    }


def evaluate_checkpoint(checkpoint: Path, *, cases: list[str], case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, device: torch.device) -> dict[str, Any]:
    model, step, extra = load_care_dpr_checkpoint(checkpoint)
    model.to(device).eval()
    candidate_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    score_rows: dict[str, list[tuple[np.ndarray, np.ndarray]]] = defaultdict(list)
    component_values: dict[str, list[tuple[float, float]]] = defaultdict(list)
    roi_rows: list[dict[str, float]] = []
    no_outer_cases = []
    for idx, case_id in enumerate(cases):
        meta = metadata[case_id]
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
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
        pred = run_two_pass_full_volume_dpr(model, batch_np, patch_shape=(8, 128, 128), overlap=0.5, utility_threshold=0.5, device=device)
        pass1 = pred["pass1"]
        mech = proposal_mechanisms(pass1, rec, t2_present=bool(meta.t2_present))
        for name, (scores, labels, mask) in mech["scores"].items():
            m = mask.astype(bool)
            if np.any(m):
                score_rows[name].append((scores[m].reshape(-1).astype(np.float32), labels[m].reshape(-1).astype(np.uint8)))
        for pathology, pair in mech["components"].items():
            if pathology == "edema_zone" and not bool(meta.t2_present):
                continue
            component_values[pathology].append(pair)
        roi_rows.append(mech["roi"])
        labels = rec["labels"]
        gt_maps = {
            "scar": labels == SCAR_CHANNEL,
            "edema_zone": (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL),
        }
        dist_maps = {
            "scar": distance_to_reliable_gt(rec, pathology="scar", t2_present=bool(meta.t2_present))[0],
            "edema_zone": distance_to_reliable_gt(rec, pathology="edema_zone", t2_present=bool(meta.t2_present))[0],
        }
        by_case_counts = defaultdict(int)
        by_case_accept = defaultdict(int)
        for item_idx, item in enumerate(pred.get("candidate_evidence", [])):
            pathology = str(item["pathology"])
            ctype = str(item["candidate_type"])
            roi_mask = item["roi_mask"].astype(bool)
            gt_c = gt_maps[pathology] & roi_mask
            refined_c = item["refined_local_mask"].astype(bool) & roi_mask
            accept, utility, reason = candidate_utility_target(item["anchor_local_mask"], item["refined_local_mask"], gt_maps[pathology], dist_maps[pathology], ctype, roi_mask)
            row = {
                "checkpoint_step": int(step),
                "checkpoint": str(checkpoint.relative_to(REPO_ROOT)),
                "case_id": case_id,
                "candidate_index": item_idx,
                "pathology": pathology,
                "candidate_type": ctype,
                "utility_score": float(item["utility_score"]),
                "utility_regression": float(item["utility_regression"]),
                "accept_target": int(accept),
                "utility_target": float(utility),
                "target_reason": reason,
                "candidate_level_refiner_dice": dice_np(refined_c, gt_c, roi_mask),
                "roi_voxels": int(roi_mask.sum()),
                "gt_voxels_in_candidate_roi": int(gt_c.sum()),
                "refined_voxels_in_candidate_roi": int(refined_c.sum()),
                "source": "old_formal_inner12_exact_two_pass_full_volume_candidate",
            }
            candidate_rows.append(row)
            by_case_counts[f"{pathology}_{ctype}"] += 1
            if item.get("accepted"):
                by_case_accept[pathology] += 1
        case_rows.append({
            "checkpoint_step": int(step),
            "case_id": case_id,
            "candidate_count": len(pred.get("candidate_evidence", [])),
            "runtime_accepted_at_0_5": sum(1 for item in pred.get("candidate_evidence", []) if item.get("accepted")),
            "two_pass_full_volume_candidate_pipeline": bool(pred.get("two_pass_full_volume_candidate_pipeline")),
            "component_utility_calls": int(pred.get("component_utility_calls", 0)),
            **{f"count_{k}": int(v) for k, v in by_case_counts.items()},
            **{f"accepted_{k}_at_0_5": int(v) for k, v in by_case_accept.items()},
        })
        no_outer_cases.append(case_id)
        print(json.dumps({"checkpoint_step": int(step), "case": case_id, "index": idx + 1, "total": len(cases), "candidates": len(pred.get("candidate_evidence", []))}), flush=True)
    metrics: dict[str, Any] = {}
    for short, (aupr_key, prev_key) in {
        "scar_p": ("scar_p_coarse_auprc", "scar_p_coarse_positive_prevalence"),
        "scar_qfn": ("scar_q_fn_auprc", "scar_q_fn_positive_prevalence"),
        "scar_qfp": ("scar_q_fp_auprc", "scar_q_fp_positive_prevalence"),
        "edema_p": ("edema_p_coarse_auprc", "edema_p_coarse_positive_prevalence"),
        "edema_qfn": ("edema_q_fn_auprc", "edema_q_fn_positive_prevalence"),
        "edema_qfp": ("edema_q_fp_auprc", "edema_q_fp_positive_prevalence"),
    }.items():
        labels_np = np.concatenate([l for _, l in score_rows.get(short, [])]) if score_rows.get(short) else np.asarray([], dtype=np.uint8)
        scores_np = np.concatenate([s for s, _ in score_rows.get(short, [])]) if score_rows.get(short) else np.asarray([], dtype=np.float32)
        metrics[aupr_key] = aupr(scores_np, labels_np)
        metrics[prev_key] = float(labels_np.mean()) if labels_np.size else 0.0
    for pathology in ("scar", "edema_zone"):
        vals = component_values.get(pathology, [])
        metrics[f"{pathology}_p_coarse_component_recall"] = float(np.mean([v[0] for v in vals])) if vals else 0.0
        metrics[f"{pathology}_p_coarse_component_precision"] = float(np.mean([v[1] for v in vals])) if vals else 0.0
    for key in ["scar_coverage", "edema_coverage", "scar_support_volume_ratio", "edema_support_volume_ratio", "scar_predicted_refiner_dice", "edema_predicted_refiner_dice"]:
        metrics[key] = float(np.mean([r[key] for r in roi_rows])) if roi_rows else 0.0
    by_pathology = defaultdict(list)
    for row in candidate_rows:
        by_pathology[row["pathology"]].append(row)
    threshold_rows: list[dict[str, Any]] = []
    per_pathology_summary: dict[str, Any] = {}
    for pathology in ("scar", "edema_zone"):
        rows = by_pathology[pathology]
        scores = np.asarray([r["utility_score"] for r in rows], dtype=np.float64)
        targets = np.asarray([r["accept_target"] for r in rows], dtype=np.uint8)
        utilities = np.asarray([r["utility_target"] for r in rows], dtype=np.float64)
        per_pathology_summary[pathology] = {
            "candidate_count": len(rows),
            "score_distribution": score_dist(scores.tolist()),
            "add_fn_count": sum(1 for r in rows if r["candidate_type"] == "ADD_FN"),
            "revise_fp_count": sum(1 for r in rows if r["candidate_type"] == "REVISE_FP"),
            "accept_target_positive_count": int(targets.sum()) if targets.size else 0,
            "accept_target_negative_count": int(targets.size - targets.sum()) if targets.size else 0,
            "utility_auroc": auroc(scores, targets) if targets.size else 0.5,
            "utility_auprc": aupr(scores, targets) if targets.size else 0.0,
            "signed_total_utility": float(utilities.sum()) if utilities.size else 0.0,
            "candidate_level_refiner_dice_mean": float(np.mean([r["candidate_level_refiner_dice"] for r in rows])) if rows else 0.0,
        }
        for threshold in THRESHOLD_CANDIDATES:
            accepted = scores >= float(threshold)
            accepted_utils = utilities[accepted]
            threshold_rows.append({
                "checkpoint_step": int(step),
                "pathology": pathology,
                "threshold": float(threshold),
                "accepted": int(accepted.sum()),
                "rejected": int((~accepted).sum()),
                "positive_accepted_utility": float(accepted_utils[accepted_utils > 0].sum()) if accepted_utils.size else 0.0,
                "negative_accepted_utility": float(accepted_utils[accepted_utils < 0].sum()) if accepted_utils.size else 0.0,
                "signed_net_utility": float(accepted_utils.sum()) if accepted_utils.size else 0.0,
                "harmful_accepted_candidate_count": int((accepted_utils < 0).sum()) if accepted_utils.size else 0,
            })
    return {
        "checkpoint_step": int(step),
        "checkpoint": str(checkpoint.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(checkpoint),
        "case_rows": case_rows,
        "candidate_rows": candidate_rows,
        "threshold_rows": threshold_rows,
        "metrics": metrics,
        "per_pathology_summary": per_pathology_summary,
        "inner12_cases_sha256": stable_json_sha256(no_outer_cases),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--cache-cases", type=int, default=16)
    args = parser.parse_args()
    metadata = load_myops_case_metadata(REPO_ROOT)
    splits = load_splits()
    fold = next(row for row in splits if int(row["fold"]) == 0)
    split = deterministic_inner_split(sorted(fold["train"]), 0, metadata)
    inner_cases = list(split["complete_inner_select_cases"])
    outer_val = set(fold["val"])
    if set(inner_cases) & outer_val:
        raise RuntimeError("OLD_RUN_DIAGNOSTIC_WOULD_USE_OUTER_FOLD0")
    case_to_fold = {case_id: int(row["fold"]) for row in splits for case_id in row["val"]}
    device = torch.device(args.device if torch.cuda.is_available() and args.device == "cuda" else "cpu")
    cache = CaseCache(max_cases=int(args.cache_cases))
    all_rows: list[dict[str, Any]] = []
    threshold_all: list[dict[str, Any]] = []
    case_all: list[dict[str, Any]] = []
    summary_by_ckpt: list[dict[str, Any]] = []
    checkpoint_payloads = []
    for step in CHECKPOINT_STEPS:
        checkpoint = FORMAL_RUNTIME / "checkpoints" / f"checkpoint_step{step:05d}.pt"
        result = evaluate_checkpoint(checkpoint, cases=inner_cases, case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device)
        all_rows.extend(result.pop("candidate_rows"))
        threshold_all.extend(result.pop("threshold_rows"))
        case_all.extend(result.pop("case_rows"))
        flat = {"checkpoint_step": result["checkpoint_step"], "checkpoint": result["checkpoint"], "checkpoint_sha256": result["checkpoint_sha256"]}
        for pathology, vals in result["per_pathology_summary"].items():
            for key, value in vals.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        flat[f"{pathology}_{key}_{sub_key}"] = sub_value
                else:
                    flat[f"{pathology}_{key}"] = value
        for key, value in result["metrics"].items():
            flat[key] = value
        summary_by_ckpt.append(flat)
        checkpoint_payloads.append(result)
    report = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_B_R1_OLD_RUN_DIAGNOSTIC",
        "status": "PASS",
        "created_at_utc": now_utc(),
        "diagnostic_scope": "old formal run only; zero scientific final output credit; train-side complete inner12 only",
        "outer_fold0_read": False,
        "fold_expansion_authorized": False,
        "checkpoint_steps": list(CHECKPOINT_STEPS),
        "inner12_cases": inner_cases,
        "inner12_cases_sha256": stable_json_sha256(inner_cases),
        "checkpoint_summaries": summary_by_ckpt,
        "outputs": {
            "summary_csv": str((OUT_ROOT / "old_checkpoint_diagnostic_summary.csv").relative_to(REPO_ROOT)),
            "threshold_csv": str((OUT_ROOT / "old_checkpoint_thresholds.csv").relative_to(REPO_ROOT)),
            "candidate_csv": str((OUT_ROOT / "old_checkpoint_candidate_rows.csv").relative_to(REPO_ROOT)),
            "case_csv": str((OUT_ROOT / "old_checkpoint_case_rows.csv").relative_to(REPO_ROOT)),
        },
    }
    write_csv(OUT_ROOT / "old_checkpoint_candidate_rows.csv", all_rows)
    write_csv(OUT_ROOT / "old_checkpoint_thresholds.csv", threshold_all)
    write_csv(OUT_ROOT / "old_checkpoint_case_rows.csv", case_all)
    write_csv(OUT_ROOT / "old_checkpoint_diagnostic_summary.csv", summary_by_ckpt)
    write_json(OUT_ROOT / "old_checkpoint_diagnostic_report.json", report)
    write_json(RESULT_ROOT / "gate_b_r1_old_run_diagnostic_report.json", {**report, "evidence_root": str(OUT_ROOT.relative_to(REPO_ROOT))})
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
