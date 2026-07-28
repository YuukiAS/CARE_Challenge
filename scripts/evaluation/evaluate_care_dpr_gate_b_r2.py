#!/usr/bin/env python3
"""Evaluate CARE-DPR Gate B-R2 with fast inner-only threshold replay."""

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
import SimpleITK as sitk
import torch

from scripts.evaluation.care_dpr_gate_b_science import PATHOLOGIES, scientific_gate_from_casewise
from scripts.evaluation.evaluate_care_dg import LABEL_ROOT, finite_mean, metric_rows_for_case, summarize
from scripts.evaluation.evaluate_care_dpr_gate_b import RESULT_ROOT, anchor_rows_for_cases, collect_candidate_targets, evaluate_population, sha256_file, stable_json_sha256, write_csv, write_json
from scripts.training.run_care_dpr import source_hashes
from scripts.training.run_care_dpr_gate_b_r2 import PROPOSAL_THRESHOLD_CANDIDATES, UTILITY_THRESHOLD_CANDIDATES
from src.care_myocardium.data.care_dpr_dataset import CaseCache, deterministic_inner_split, load_splits
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_dpr_predictor import run_two_pass_full_volume_dpr
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.training.care_dpr_trainer import load_care_dpr_checkpoint

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
MODEL_NAME = "A2_care_dpr_gate_b_r2_selected"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def checkpoint_paths(runtime_root: Path) -> list[Path]:
    return [p for p in sorted((runtime_root / "checkpoints").glob("checkpoint_step*.pt")) if p.name != "checkpoint_last.pt"]


def threshold_grid() -> list[dict[str, float]]:
    return [
        {"scar_utility_threshold": float(su), "edema_utility_threshold": float(eu)}
        for su in UTILITY_THRESHOLD_CANDIDATES
        for eu in UTILITY_THRESHOLD_CANDIDATES
    ]


def proposal_grid() -> list[dict[str, float]]:
    return [
        {"scar_proposal_threshold": float(sp), "edema_proposal_threshold": float(ep)}
        for sp in PROPOSAL_THRESHOLD_CANDIDATES["scar"]
        for ep in PROPOSAL_THRESHOLD_CANDIDATES["edema_zone"]
    ]


def case_batch_np(rec: dict[str, np.ndarray], t2_present: bool) -> dict[str, np.ndarray]:
    return {
        "images": rec["images"],
        "availability": rec["availability"],
        "anchor_logits": rec["anchor_logits"],
        "anchor_mask": rec["anchor_mask"],
        "uncertainty": rec["uncertainty"],
        "myocardium_support": rec["myocardium_support"],
        "edema_support": rec["edema_support"],
        "distance_to_myocardium": rec["distance_to_myocardium"],
        "t2_present": bool(t2_present),
    }


def compose_from_evidence(anchor_mask: np.ndarray, evidence: list[dict[str, Any]], *, scar_utility_threshold: float, edema_utility_threshold: float) -> np.ndarray:
    final_by_pathology = {
        "edema_zone": ((anchor_mask == SCAR_CHANNEL) | (anchor_mask == EDEMA_CHANNEL)).copy(),
        "scar": (anchor_mask == SCAR_CHANNEL).copy(),
    }
    for pathology in ("edema_zone", "scar"):
        result = final_by_pathology[pathology]
        threshold = edema_utility_threshold if pathology == "edema_zone" else scar_utility_threshold
        for item in [x for x in evidence if x["pathology"] == pathology]:
            anchor_local = item["anchor_local_mask"].astype(bool)
            refined = item["refined_local_mask"].astype(bool)
            seed = item["seed_mask"].astype(bool)
            accepted = float(item.get("predicted_signed_utility", item.get("utility_regression", 0.0))) >= float(threshold)
            if item["candidate_type"] == "ADD_FN":
                if accepted:
                    result[refined] = True
            elif accepted:
                region = anchor_local | refined | seed
                result[region] = refined[region]
            else:
                result[anchor_local] = True
        final_by_pathology[pathology] = result
    final = anchor_mask.copy()
    final[(anchor_mask == EDEMA_CHANNEL) | (anchor_mask == SCAR_CHANNEL)] = 0
    edema = final_by_pathology["edema_zone"]
    scar = final_by_pathology["scar"]
    final[edema & ~scar] = EDEMA_CHANNEL
    final[scar] = SCAR_CHANNEL
    return final.astype(np.uint8, copy=False)


def signed_counts(candidate_rows: list[dict[str, Any]], evidence: list[dict[str, Any]], pathology: str, threshold: float) -> dict[str, Any]:
    sub_rows = [r for r in candidate_rows if r.get("pathology") == pathology]
    sub_ev = [e for e in evidence if e.get("pathology") == pathology]
    accepted_mask = [float(e.get("predicted_signed_utility", e.get("utility_regression", 0.0))) >= float(threshold) for e in sub_ev]
    signed = 0.0
    for row, accepted in zip(sub_rows, accepted_mask):
        if accepted:
            signed += float(row.get("utility_target", 0.0))
    return {
        "candidate_count": len(sub_rows),
        "accepted": int(sum(accepted_mask)),
        "rejected": int(len(sub_rows) - sum(accepted_mask)),
        "signed_net_utility": float(signed),
        "add_count": sum(1 for r in sub_rows if r.get("candidate_type") == "ADD_FN"),
        "revise_count": sum(1 for r in sub_rows if r.get("candidate_type") == "REVISE_FP"),
    }


def collect_proposal_evidence(model: torch.nn.Module, cases: list[str], *, population: str, case_to_fold: dict[str, int], metadata: Any, cache: CaseCache, device: torch.device, scar_proposal_threshold: float, edema_proposal_threshold: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, case_id in enumerate(cases):
        meta = metadata[case_id]
        rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
        batch_np = case_batch_np(rec, bool(meta.t2_present))
        pred = run_two_pass_full_volume_dpr(
            model,
            batch_np,
            patch_shape=(8, 128, 128),
            overlap=0.5,
            scar_proposal_threshold=scar_proposal_threshold,
            edema_proposal_threshold=edema_proposal_threshold,
            scar_utility_threshold=999.0,
            edema_utility_threshold=999.0,
            device=device,
        )
        candidate_rows = collect_candidate_targets(pred, rec, case_id=case_id, t2_present=bool(meta.t2_present), population=population)
        rows.append({"case_id": case_id, "record": rec, "metadata": meta, "candidate_rows": candidate_rows, "candidate_evidence": pred["candidate_evidence"], "no_t2": pred.get("candidate_evidence", []), "proposal_activation": pred})
        print(json.dumps({"case": case_id, "index": idx + 1, "total": len(cases), "population": population, "proposal_thresholds": [scar_proposal_threshold, edema_proposal_threshold], "candidates": len(pred["candidate_evidence"])}), flush=True)
    return rows


def replay_metrics(case_items: list[dict[str, Any]], *, population: str, model_name: str, scar_utility_threshold: float, edema_utility_threshold: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    casewise: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    no_t2_rows: list[dict[str, Any]] = []
    for item in case_items:
        case_id = item["case_id"]
        rec = item["record"]
        meta = item["metadata"]
        ref = sitk.ReadImage(str(LABEL_ROOT / f"{case_id}.nii.gz"))
        spacing = tuple(float(v) for v in ref.GetSpacing()[::-1])
        anchor = rec["anchor_mask"].astype(np.uint8, copy=False)
        final = compose_from_evidence(anchor, item["candidate_evidence"], scar_utility_threshold=scar_utility_threshold, edema_utility_threshold=edema_utility_threshold)
        casewise.extend(metric_rows_for_case(case_id, population, model_name, final, anchor, rec["labels"].astype(np.uint8, copy=False), meta, spacing))
        for row in item["candidate_rows"]:
            threshold = edema_utility_threshold if row.get("pathology") == "edema_zone" else scar_utility_threshold
            score = float(row.get("predicted_signed_utility", row.get("utility_regression", row.get("utility_score", 0.0))))
            candidate_rows.append({**row, "accepted_at_runtime_threshold": score >= threshold, "runtime_utility_threshold": threshold})
        if not bool(meta.t2_present):
            edema_count = sum(1 for e in item["candidate_evidence"] if e["pathology"] == "edema_zone")
            no_t2_rows.append({"case_id": case_id, "edema_candidate_count": edema_count, "edema_p_refined_voxels": 0, "pure_edema_changed_voxels_vs_anchor": 0, "status": "PASS" if edema_count == 0 else "FAIL"})
    return casewise, candidate_rows, no_t2_rows


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
    paths = checkpoint_paths(runtime_root)
    if args.max_checkpoints:
        paths = paths[-int(args.max_checkpoints):]
    if not paths:
        raise FileNotFoundError(runtime_root / "checkpoints")
    prop_rows = proposal_grid()
    if args.max_proposal_grid:
        prop_rows = prop_rows[: int(args.max_proposal_grid)]
    selection_rows: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    inner_candidate_rows_all: list[dict[str, Any]] = []
    for ckpt in paths:
        model, step, _ = load_care_dpr_checkpoint(ckpt)
        model.to(device).eval()
        for prop in prop_rows:
            prop_items = collect_proposal_evidence(model, inner_cases, population="fold_train_inner12", case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device, **prop)
            anchor_rows = anchor_rows_for_cases(inner_cases, "fold_train_inner12", case_to_fold, metadata, cache)
            for util in threshold_grid():
                model_name = f"checkpoint_step{step:05d}_inner_r2"
                pred_rows, cand_rows, no_t2 = replay_metrics(prop_items, population="fold_train_inner12", model_name=model_name, **util)
                casewise = anchor_rows + pred_rows
                gate, _ = scientific_gate_from_casewise(casewise, no_t2, population="fold_train_inner12", model_name=model_name)
                scar_counts = signed_counts(cand_rows, [e for item in prop_items for e in item["candidate_evidence"]], "scar", util["scar_utility_threshold"])
                edema_counts = signed_counts(cand_rows, [e for item in prop_items for e in item["candidate_evidence"]], "edema_zone", util["edema_utility_threshold"])
                row = {
                    "checkpoint": str(ckpt.relative_to(REPO_ROOT)),
                    "checkpoint_step": int(step),
                    "checkpoint_sha256": sha256_file(ckpt),
                    **prop,
                    **util,
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
                }
                row["eligible"] = bool(row["scar_accepted"] > 0 and row["scar_rejected"] > 0 and row["edema_accepted"] > 0 and row["edema_rejected"] > 0 and row["scar_signed_net_utility"] > 0 and row["edema_signed_net_utility"] > 0 and row["all_dice_delta_ge_minus_0.005"] and row["at_least_one_inner_improves_ge_0.005"] and row["safety_gate_pass"])
                selection_rows.append(row)
                if row["eligible"]:
                    eligible.append(row)
                for cr in cand_rows:
                    inner_candidate_rows_all.append({**cr, "checkpoint_step": int(step), **prop, **util})
            write_csv(out_root / "gate_b_r2_inner_selection_rows.csv", selection_rows)
            write_csv(out_root / "gate_b_r2_inner_candidate_rows.csv", inner_candidate_rows_all)
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    if not eligible:
        result = {"task_key": TASK_KEY, "gate": "DPR_GATE_B_R2", "status": "GATE_B_R2_REPAIR_REQUIRED_NO_INNER_ELIGIBLE_CHECKPOINT_THRESHOLD", "fold": int(args.fold), "development_evidence_only": int(args.fold) == 0, "clean_scientific_gate": False, "outer_fold_used_for_selection": False, "fold_expansion_authorized": False, "scientific_final_output_credit": 0, "selection_rows": selection_rows}
        write_json(out_root / "gate_b_r2_summary.json", result)
        write_json(result_root / "gate_b_r2_summary.json", {**result, "evidence_root": str(out_root.relative_to(REPO_ROOT))})
        return result
    selected = max(eligible, key=lambda r: (float(r["avg_inner_dice_delta"]), float(r["scar_signed_net_utility"]) + float(r["edema_signed_net_utility"]), int(r["checkpoint_step"])))
    checkpoint = REPO_ROOT / selected["checkpoint"]
    model, step, _ = load_care_dpr_checkpoint(checkpoint)
    model.to(device).eval()
    eval_kwargs = {k: float(selected[k]) for k in ["scar_proposal_threshold", "edema_proposal_threshold", "scar_utility_threshold", "edema_utility_threshold"]}
    casewise = anchor_rows_for_cases(outer_val, f"fold{args.fold}_outer", case_to_fold, metadata, cache)
    casewise += anchor_rows_for_cases(complete_val, f"fold{args.fold}_complete_trimodal", case_to_fold, metadata, cache)
    outer_eval = evaluate_population(model=model, cases=outer_val, population=f"fold{args.fold}_outer", case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device, utility_threshold=0.0, model_name=MODEL_NAME, **eval_kwargs)
    complete_eval = evaluate_population(model=model, cases=complete_val, population=f"fold{args.fold}_complete_trimodal", case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device, utility_threshold=0.0, model_name=MODEL_NAME, **eval_kwargs)
    casewise += outer_eval["casewise"] + complete_eval["casewise"]
    summary = summarize(casewise)
    gate, help_harm = scientific_gate_from_casewise(casewise, outer_eval["no_t2"] + complete_eval["no_t2"], population=f"fold{args.fold}_complete_trimodal", model_name=MODEL_NAME)
    status = "GATE_B_R2_CLEAN_EVALUATION_PASS" if gate["status"] == "PASS" and int(args.fold) != 0 else "GATE_B_R2_DEVELOPMENT_EVIDENCE_RECORDED" if int(args.fold) == 0 else "GATE_B_R2_CLEAN_EVALUATION_FAIL"
    result = {"task_key": TASK_KEY, "gate": "DPR_GATE_B_R2", "status": status, "fold": int(args.fold), "development_evidence_only": int(args.fold) == 0, "clean_scientific_gate": int(args.fold) != 0, "selected": selected, "outer_fold_used_for_selection": False, "scientific_gate": gate, "fold_expansion_authorized": False, "validation_upload_authorized": False, "final_arbitration_score": "predicted_signed_utility", "accept_probability_threshold_used": False, "utility_regression_min_used": False, "inner12_case_ids_sha256": stable_json_sha256(inner_cases), "outer_case_ids_sha256": stable_json_sha256(outer_val), "complete_case_ids_sha256": stable_json_sha256(complete_val), "source_hashes": {**source_hashes(), "scripts/evaluation/evaluate_care_dpr_gate_b_r2.py": sha256_file(REPO_ROOT / "scripts/evaluation/evaluate_care_dpr_gate_b_r2.py")}}
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
    parser.add_argument("--max-proposal-grid", type=int, default=0)
    parser.add_argument("--device", default="")
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if not str(result["status"]).endswith("REQUIRED_NO_INNER_ELIGIBLE_CHECKPOINT_THRESHOLD") else 1


if __name__ == "__main__":
    raise SystemExit(main())
