#!/usr/bin/env python3
"""Evaluate CARE-DPR Gate B-R2 with inner-only checkpoint/threshold selection."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch

from scripts.evaluation.care_dpr_gate_b_science import PATHOLOGIES, scientific_gate_from_casewise
from scripts.evaluation.evaluate_care_dg import finite_mean, summarize
from scripts.evaluation.evaluate_care_dpr_gate_b import RESULT_ROOT, anchor_rows_for_cases, evaluate_population, sha256_file, stable_json_sha256, write_csv, write_json
from scripts.training.run_care_dpr import source_hashes
from scripts.training.run_care_dpr_gate_b_r2 import PROPOSAL_THRESHOLD_CANDIDATES, UTILITY_THRESHOLD_CANDIDATES
from src.care_myocardium.data.care_dpr_dataset import CaseCache, deterministic_inner_split, load_splits
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.training.care_dpr_trainer import load_care_dpr_checkpoint

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
MODEL_NAME = "A2_care_dpr_gate_b_r2_selected"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def checkpoint_paths(runtime_root: Path) -> list[Path]:
    paths = sorted((runtime_root / "checkpoints").glob("checkpoint_step*.pt"))
    return [p for p in paths if p.name != "checkpoint_last.pt"]


def signed_counts(rows: list[dict[str, Any]], pathology: str) -> dict[str, Any]:
    sub = [r for r in rows if r.get("pathology") == pathology]
    accepted = [r for r in sub if bool(r.get("accepted_at_runtime_threshold"))]
    return {
        "candidate_count": len(sub),
        "accepted": len(accepted),
        "rejected": len(sub) - len(accepted),
        "signed_net_utility": float(sum(float(r.get("utility_target", 0.0)) for r in accepted)),
        "add_count": sum(1 for r in sub if r.get("candidate_type") == "ADD_FN"),
        "revise_count": sum(1 for r in sub if r.get("candidate_type") == "REVISE_FP"),
    }


def threshold_grid(max_grid: int = 0) -> list[dict[str, float]]:
    rows = []
    for scar_p in PROPOSAL_THRESHOLD_CANDIDATES["scar"]:
        for edema_p in PROPOSAL_THRESHOLD_CANDIDATES["edema_zone"]:
            for scar_u in UTILITY_THRESHOLD_CANDIDATES:
                for edema_u in UTILITY_THRESHOLD_CANDIDATES:
                    rows.append({"scar_proposal_threshold": float(scar_p), "edema_proposal_threshold": float(edema_p), "scar_utility_threshold": float(scar_u), "edema_utility_threshold": float(edema_u)})
    return rows[: int(max_grid)] if max_grid else rows


def evaluate_combo(model: torch.nn.Module, cases: list[str], *, population: str, case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, device: torch.device, combo: dict[str, float], model_name: str) -> dict[str, Any]:
    return evaluate_population(
        model=model,
        cases=cases,
        population=population,
        case_to_fold=case_to_fold,
        metadata=metadata,
        cache=cache,
        device=device,
        utility_threshold=0.0,
        model_name=model_name,
        proposal_threshold=0.5,
        scar_proposal_threshold=combo["scar_proposal_threshold"],
        edema_proposal_threshold=combo["edema_proposal_threshold"],
        scar_utility_threshold=combo["scar_utility_threshold"],
        edema_utility_threshold=combo["edema_utility_threshold"],
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    result_root = Path(args.result_root)
    runtime_root = Path(args.runtime_root) if args.runtime_root else result_root / "runtime" / args.runtime_name
    out_root = runtime_root / "gate_b_r2_evaluation"
    out_root.mkdir(parents=True, exist_ok=True)
    metadata = load_myops_case_metadata(REPO_ROOT)
    splits = load_splits()
    fold = next(row for row in splits if int(row["fold"]) == int(args.fold))
    outer_val = sorted(fold["val"])
    complete_val = [c for c in outer_val if metadata[c].modality_group == "C0+LGE+T2"]
    split_payload = deterministic_inner_split(sorted(fold["train"]), int(args.fold), metadata)
    inner_cases = list(split_payload["complete_inner_select_cases"])
    case_to_fold = {case_id: int(row["fold"]) for row in splits for case_id in row["val"]}
    cache = CaseCache(max_cases=int(args.cache_cases))
    device = torch.device(args.device if args.device else ("cuda" if torch.cuda.is_available() and not args.cpu else "cpu"))
    selection_rows: list[dict[str, Any]] = []
    candidate_rows_all: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    paths = checkpoint_paths(runtime_root)
    if args.max_checkpoints:
        paths = paths[-int(args.max_checkpoints):]
    if not paths:
        raise FileNotFoundError(runtime_root / "checkpoints")
    for ckpt in paths:
        model, step, _ = load_care_dpr_checkpoint(ckpt)
        model.to(device).eval()
        for combo in threshold_grid(args.max_grid):
            model_name = f"checkpoint_step{step:05d}_inner_r2"
            inner_eval = evaluate_combo(model, inner_cases, population="fold_train_inner12", case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device, combo=combo, model_name=model_name)
            casewise = anchor_rows_for_cases(inner_cases, "fold_train_inner12", case_to_fold, metadata, cache) + inner_eval["casewise"]
            summary = summarize(casewise)
            gate, help_harm = scientific_gate_from_casewise(casewise, inner_eval["no_t2"], population="fold_train_inner12", model_name=model_name)
            scar_counts = signed_counts(inner_eval["candidate_rows"], "scar")
            edema_counts = signed_counts(inner_eval["candidate_rows"], "edema_zone")
            row = {
                "checkpoint": str(ckpt.relative_to(REPO_ROOT)),
                "checkpoint_step": int(step),
                "checkpoint_sha256": sha256_file(ckpt),
                **combo,
                "scar_accepted": scar_counts["accepted"],
                "scar_rejected": scar_counts["rejected"],
                "scar_signed_net_utility": scar_counts["signed_net_utility"],
                "edema_accepted": edema_counts["accepted"],
                "edema_rejected": edema_counts["rejected"],
                "edema_signed_net_utility": edema_counts["signed_net_utility"],
                "scar_add_count": scar_counts["add_count"],
                "scar_revise_count": scar_counts["revise_count"],
                "edema_add_count": edema_counts["add_count"],
                "edema_revise_count": edema_counts["revise_count"],
                "scientific_gate_status": gate["status"],
                "scientific_failures": json.dumps(gate["failures"], ensure_ascii=False),
                "at_least_one_inner_improves_ge_0.005": gate["contract_checks"]["at_least_one_pathology_dice_delta_ge_plus_0.005"],
                "all_dice_delta_ge_minus_0.005": gate["contract_checks"]["per_pathology_dice_delta_ge_minus_0.005"],
                "safety_gate_pass": all(v for k, v in gate["contract_checks"].items() if k != "at_least_one_pathology_dice_delta_ge_plus_0.005"),
                "avg_inner_dice_delta": finite_mean([gate["complete16_delta_summary"][p]["dice_delta_mean"] for p in PATHOLOGIES]),
                "eligible": False,
            }
            row["eligible"] = bool(
                scar_counts["accepted"] > 0 and scar_counts["rejected"] > 0 and edema_counts["accepted"] > 0 and edema_counts["rejected"] > 0
                and scar_counts["signed_net_utility"] > 0 and edema_counts["signed_net_utility"] > 0
                and row["all_dice_delta_ge_minus_0.005"] and row["at_least_one_inner_improves_ge_0.005"] and row["safety_gate_pass"]
            )
            selection_rows.append(row)
            for cand in inner_eval["candidate_rows"]:
                candidate_rows_all.append({**cand, "checkpoint_step": int(step), **combo})
            write_csv(out_root / "gate_b_r2_inner_selection_rows.csv", selection_rows)
            write_csv(out_root / "gate_b_r2_inner_candidate_rows.csv", candidate_rows_all)
            if row["eligible"]:
                eligible.append(row)
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    if not eligible:
        result = {
            "task_key": TASK_KEY,
            "gate": "DPR_GATE_B_R2",
            "status": "GATE_B_R2_REPAIR_REQUIRED_NO_INNER_ELIGIBLE_CHECKPOINT_THRESHOLD",
            "fold": int(args.fold),
            "development_evidence_only": int(args.fold) == 0,
            "clean_scientific_gate": False,
            "outer_fold_used_for_selection": False,
            "selection_rows": selection_rows,
            "fold_expansion_authorized": False,
            "scientific_final_output_credit": 0,
        }
        write_json(out_root / "gate_b_r2_summary.json", result)
        write_json(result_root / "gate_b_r2_summary.json", {**result, "evidence_root": str(out_root.relative_to(REPO_ROOT))})
        return result
    selected = max(eligible, key=lambda r: (float(r["avg_inner_dice_delta"]), float(r["scar_signed_net_utility"]) + float(r["edema_signed_net_utility"]), int(r["checkpoint_step"])))
    checkpoint = REPO_ROOT / selected["checkpoint"]
    model, step, _ = load_care_dpr_checkpoint(checkpoint)
    model.to(device).eval()
    combo = {k: float(selected[k]) for k in ["scar_proposal_threshold", "edema_proposal_threshold", "scar_utility_threshold", "edema_utility_threshold"]}
    casewise = anchor_rows_for_cases(outer_val, f"fold{args.fold}_outer", case_to_fold, metadata, cache)
    casewise += anchor_rows_for_cases(complete_val, f"fold{args.fold}_complete_trimodal", case_to_fold, metadata, cache)
    outer_eval = evaluate_combo(model, outer_val, population=f"fold{args.fold}_outer", case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device, combo=combo, model_name=MODEL_NAME)
    complete_eval = evaluate_combo(model, complete_val, population=f"fold{args.fold}_complete_trimodal", case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device, combo=combo, model_name=MODEL_NAME)
    casewise += outer_eval["casewise"] + complete_eval["casewise"]
    summary = summarize(casewise)
    gate, help_harm = scientific_gate_from_casewise(casewise, outer_eval["no_t2"] + complete_eval["no_t2"], population=f"fold{args.fold}_complete_trimodal", model_name=MODEL_NAME)
    status = "GATE_B_R2_CLEAN_EVALUATION_PASS" if gate["status"] == "PASS" and int(args.fold) != 0 else "GATE_B_R2_DEVELOPMENT_EVIDENCE_RECORDED" if int(args.fold) == 0 else "GATE_B_R2_CLEAN_EVALUATION_FAIL"
    result = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_B_R2",
        "status": status,
        "fold": int(args.fold),
        "development_evidence_only": int(args.fold) == 0,
        "clean_scientific_gate": int(args.fold) != 0,
        "selected": selected,
        "outer_fold_used_for_selection": False,
        "scientific_gate": gate,
        "fold_expansion_authorized": False,
        "validation_upload_authorized": False,
        "final_arbitration_score": "predicted_signed_utility",
        "accept_probability_threshold_used": False,
        "utility_regression_min_used": False,
        "inner12_case_ids_sha256": stable_json_sha256(inner_cases),
        "outer_case_ids_sha256": stable_json_sha256(outer_val),
        "complete_case_ids_sha256": stable_json_sha256(complete_val),
        "source_hashes": {**source_hashes(), "scripts/evaluation/evaluate_care_dpr_gate_b_r2.py": sha256_file(REPO_ROOT / "scripts/evaluation/evaluate_care_dpr_gate_b_r2.py")},
    }
    write_csv(out_root / "gate_b_r2_casewise_metrics.csv", casewise)
    write_csv(out_root / "gate_b_r2_model_summary.csv", summary)
    write_csv(out_root / "gate_b_r2_help_harm.csv", help_harm)
    write_csv(out_root / "gate_b_r2_outer_candidate_rows.csv", outer_eval["candidate_rows"])
    write_csv(out_root / "gate_b_r2_activation_audit.csv", outer_eval["activation"] + complete_eval["activation"])
    write_csv(out_root / "gate_b_r2_no_t2_safety_audit.csv", outer_eval["no_t2"] + complete_eval["no_t2"])
    write_json(out_root / "gate_b_r2_scientific_gate.json", gate)
    write_json(out_root / "gate_b_r2_summary.json", result)
    write_json(result_root / "gate_b_r2_summary.json", {**result, "evidence_root": str(out_root.relative_to(REPO_ROOT))})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--result-root", default=str(RESULT_ROOT))
    parser.add_argument("--runtime-name", default="formal_fold0_r2")
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--cache-cases", type=int, default=16)
    parser.add_argument("--max-checkpoints", type=int, default=0)
    parser.add_argument("--max-grid", type=int, default=0)
    parser.add_argument("--device", default="")
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if not str(result["status"]).endswith("REQUIRED_NO_INNER_ELIGIBLE_CHECKPOINT_THRESHOLD") else 1


if __name__ == "__main__":
    raise SystemExit(main())
