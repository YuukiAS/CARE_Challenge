#!/usr/bin/env python3
"""CARE-DPR Gate B-R1 evaluator with inner-only checkpoint and threshold selection."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch

from scripts.evaluation.evaluate_care_dg import PATHOLOGIES, finite_mean, summarize
from scripts.evaluation.evaluate_care_dpr import THRESHOLD_CANDIDATES, aupr, auroc
from scripts.evaluation.care_dpr_gate_b_science import scientific_gate_from_casewise
from scripts.evaluation.evaluate_care_dpr_gate_b import (
    RESULT_ROOT,
    RUNTIME_ROOT,
    anchor_rows_for_cases,
    evaluate_population,
    sha256_file,
    stable_json_sha256,
    write_csv,
    write_json,
)
from scripts.training.run_care_dpr import source_hashes
from src.care_myocardium.data.care_dpr_dataset import CaseCache, deterministic_inner_split, load_splits
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.training.care_dpr_trainer import load_care_dpr_checkpoint

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
MODEL_NAME = "A2_care_dpr_gate_b_r1_selected"
ANCHOR_NAME = "A0_nnunet_anchor"
REGRESSION_MIN_CANDIDATES = (0.50, 0.75, 0.90, 0.95, 0.99)
HELP_HARM_DICE_DELTA_THRESHOLD = 0.005


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def regression_candidates(value: float | None) -> tuple[float | None, ...]:
    if value is None or float(value) < 0.0:
        return REGRESSION_MIN_CANDIDATES
    return (float(value),)


def choose_pathology_threshold(rows: list[dict[str, Any]], pathology: str, *, utility_regression_min_candidates: tuple[float | None, ...]) -> dict[str, Any]:
    subset = [r for r in rows if r.get("pathology") == pathology]
    scores = np.asarray([r["utility_score"] for r in subset], dtype=np.float64)
    utilities = np.asarray([r["utility_target"] for r in subset], dtype=np.float64)
    regressions = np.asarray([r.get("utility_regression", 0.0) for r in subset], dtype=np.float64)
    out = []
    for regression_min in utility_regression_min_candidates:
        for threshold in THRESHOLD_CANDIDATES:
            accepted = scores >= float(threshold)
            if regression_min is not None:
                accepted = accepted & (regressions >= float(regression_min))
            signed = float(utilities[accepted].sum()) if utilities.size else 0.0
            row = {
                "pathology": pathology,
                "threshold": float(threshold),
                "accepted": int(accepted.sum()),
                "rejected": int((~accepted).sum()),
                "signed_net_utility": signed,
                "positive_accepted_utility": float(np.clip(utilities[accepted], 0, None).sum()) if utilities.size else 0.0,
                "negative_accepted_utility": float(np.clip(utilities[accepted], None, 0).sum()) if utilities.size else 0.0,
                "harmful_accepted_candidate_count": int((utilities[accepted] < 0).sum()) if utilities.size else 0,
                "utility_regression_min": regression_min,
                "selection_uses_accept_logit_and_signed_regression_gate": regression_min is not None,
                "eligible": bool(accepted.any() and (~accepted).any() and signed > 0.0),
            }
            out.append(row)
    eligible = [r for r in out if r["eligible"]]
    selected = max(eligible, key=lambda r: (float(r.get("utility_regression_min") or -1.0), float(r["threshold"]), float(r["signed_net_utility"]))) if eligible else (max(out, key=lambda r: (float(r["signed_net_utility"]), float(r.get("utility_regression_min") or -1.0), float(r["threshold"]))) if out else {"threshold": 0.5, "accepted": 0, "rejected": 0, "signed_net_utility": 0.0, "eligible": False, "utility_regression_min": None})
    labels = np.asarray([r["accept_target"] for r in subset], dtype=np.uint8)
    return {
        "pathology": pathology,
        "status": "PASS" if bool(selected.get("eligible")) else "FAIL",
        "selected_threshold": float(selected["threshold"]),
        "selected": selected,
        "threshold_rows": out,
        "candidate_count": len(subset),
        "accept_target_positive_count": int(labels.sum()) if labels.size else 0,
        "accept_target_negative_count": int(labels.size - labels.sum()) if labels.size else 0,
        "utility_auroc": auroc(scores, labels) if labels.size else 0.5,
        "utility_auprc": aupr(scores, labels) if labels.size else 0.0,
        "positive_prevalence": float(labels.mean()) if labels.size else 0.0,
        "utility_regression_min_candidates": list(utility_regression_min_candidates),
        "selected_utility_regression_min": selected.get("utility_regression_min"),
    }


def delta_rows(casewise: list[dict[str, Any]], population: str, model_name: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by = {(r["population"], r["model"], r["pathology"], r["case_id"]): r for r in casewise}
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for pathology in PATHOLOGIES:
        deltas = []
        hd_ratios = []
        remote_ratios = []
        component_ratios = []
        for key, pred in by.items():
            pop, model, path, case_id = key
            if pop != population or model != model_name or path != pathology:
                continue
            anchor = by.get((population, ANCHOR_NAME, pathology, case_id))
            if not anchor:
                continue
            dice_delta = float(pred["dice"]) - float(anchor["dice"])
            hd_anchor = float(anchor["hd95_mm"])
            hd_pred = float(pred["hd95_mm"])
            remote_anchor = float(anchor["remote_fp_volume_mm3"])
            remote_pred = float(pred["remote_fp_volume_mm3"])
            comp_anchor = float(anchor["component_count"])
            comp_pred = float(pred["component_count"])
            help_harm = "help" if dice_delta >= HELP_HARM_DICE_DELTA_THRESHOLD else "harm" if dice_delta <= -HELP_HARM_DICE_DELTA_THRESHOLD else "neutral"
            rows.append({"population": population, "case_id": case_id, "pathology": pathology, "anchor_dice": anchor["dice"], "dpr_dice": pred["dice"], "dice_delta": dice_delta, "help_harm": help_harm, "help_harm_dice_delta_threshold": HELP_HARM_DICE_DELTA_THRESHOLD})
            deltas.append(dice_delta)
            hd_ratios.append(hd_pred / max(hd_anchor, 1e-6) if math.isfinite(hd_pred) and math.isfinite(hd_anchor) else math.inf)
            remote_ratios.append(remote_pred / max(remote_anchor, 1e-6))
            component_ratios.append(comp_pred / max(comp_anchor, 1.0))
        summary[pathology] = {
            "dice_delta_mean": finite_mean(deltas),
            "hd95_ratio_mean": finite_mean(hd_ratios),
            "remote_fp_ratio_mean": finite_mean(remote_ratios),
            "component_count_ratio_mean": finite_mean(component_ratios),
            "improves_by_ge_0.005": finite_mean(deltas) >= 0.005,
            "not_below_anchor_by_more_than_0.005": finite_mean(deltas) >= -0.005,
            "no_new_infinite_exact_hd": not any(math.isinf(x) for x in hd_ratios),
            "remote_fp_le_1.10x_anchor": finite_mean(remote_ratios) <= 1.10,
            "no_component_count_explosion": finite_mean(component_ratios) <= 10.0,
        }
    return rows, summary


def checkpoint_paths(runtime_root: Path) -> list[Path]:
    return [runtime_root / "checkpoints" / f"checkpoint_step{step:05d}.pt" for step in range(500, 4001, 500)]


def run_gate_b_r1(args: argparse.Namespace) -> dict[str, Any]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    splits = load_splits()
    fold = next(row for row in splits if int(row["fold"]) == int(args.fold))
    outer_val = sorted(fold["val"])
    complete_val = [case_id for case_id in outer_val if metadata[case_id].modality_group == "C0+LGE+T2"]
    split_payload = deterministic_inner_split(sorted(fold["train"]), int(args.fold), metadata)
    inner_cases = list(split_payload["complete_inner_select_cases"])
    case_to_fold = {case_id: int(row["fold"]) for row in splits for case_id in row["val"]}
    result_root = Path(args.result_root)
    runtime_root = Path(args.runtime_root) if args.runtime_root else result_root / "runtime" / args.runtime_name
    receipt = read_json(runtime_root / "fold_training_receipt.json")
    if receipt.get("status") != "PASS" or int(receipt.get("actual_optimizer_steps", -1)) != 4000:
        raise RuntimeError("CARE_DPR_GATE_B_R1_FORMAL_RECEIPT_NOT_PASS_4000")
    device = torch.device(args.device if args.device else ("cuda" if torch.cuda.is_available() and not args.cpu else "cpu"))
    cache = CaseCache(max_cases=int(args.cache_cases))
    out_root = runtime_root / "gate_b_r1_evaluation"
    out_root.mkdir(parents=True, exist_ok=True)
    selection_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    inner_candidate_rows: list[dict[str, Any]] = []
    inner_casewise_all: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    for ckpt in checkpoint_paths(runtime_root):
        if not ckpt.is_file():
            raise FileNotFoundError(ckpt)
        model, step, _ = load_care_dpr_checkpoint(ckpt)
        model.to(device).eval()
        probe = evaluate_population(model=model, cases=inner_cases, population="fold0_train_side_complete_inner12", case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device, utility_threshold=0.5, model_name=f"checkpoint_step{step:05d}_probe")
        cand_rows = probe["candidate_rows"]
        for r in cand_rows:
            r["checkpoint_step"] = int(step)
            r["checkpoint"] = str(ckpt.relative_to(REPO_ROOT))
        inner_candidate_rows.extend(cand_rows)
        scar_sel = choose_pathology_threshold(cand_rows, "scar", utility_regression_min_candidates=regression_candidates(args.scar_utility_regression_min))
        edema_sel = choose_pathology_threshold(cand_rows, "edema_zone", utility_regression_min_candidates=regression_candidates(args.edema_utility_regression_min))
        threshold_rows.extend([{**r, "checkpoint_step": int(step)} for r in scar_sel["threshold_rows"] + edema_sel["threshold_rows"]])
        selected_eval = evaluate_population(
            model=model,
            cases=inner_cases,
            population="fold0_train_side_complete_inner12",
            case_to_fold=case_to_fold,
            metadata=metadata,
            cache=cache,
            device=device,
            utility_threshold=0.5,
            scar_utility_threshold=float(scar_sel["selected_threshold"]),
            edema_utility_threshold=float(edema_sel["selected_threshold"]),
            model_name=f"checkpoint_step{step:05d}_inner_selected",
            scar_utility_regression_min=scar_sel["selected"].get("utility_regression_min"),
            edema_utility_regression_min=edema_sel["selected"].get("utility_regression_min"),
        )
        inner_casewise = []
        inner_casewise.extend(anchor_rows_for_cases(inner_cases, "fold0_train_side_complete_inner12", case_to_fold, metadata, cache))
        inner_casewise.extend(selected_eval["casewise"])
        inner_deltas, inner_delta_summary = delta_rows(inner_casewise, "fold0_train_side_complete_inner12", f"checkpoint_step{step:05d}_inner_selected")
        inner_casewise_all.extend(inner_casewise)
        dice_values = [inner_delta_summary[p]["dice_delta_mean"] for p in PATHOLOGIES]
        hd_values = [inner_delta_summary[p]["hd95_ratio_mean"] for p in PATHOLOGIES]
        remote_values = [inner_delta_summary[p]["remote_fp_ratio_mean"] for p in PATHOLOGIES]
        eligibility = all(inner_delta_summary[p]["not_below_anchor_by_more_than_0.005"] for p in PATHOLOGIES) and all(inner_delta_summary[p]["no_new_infinite_exact_hd"] for p in PATHOLOGIES) and all(inner_delta_summary[p]["remote_fp_le_1.10x_anchor"] for p in PATHOLOGIES) and all(inner_delta_summary[p]["no_component_count_explosion"] for p in PATHOLOGIES) and scar_sel["status"] == "PASS" and edema_sel["status"] == "PASS"
        row = {
            "checkpoint_step": int(step),
            "checkpoint": str(ckpt.relative_to(REPO_ROOT)),
            "checkpoint_sha256": sha256_file(ckpt),
            "scar_utility_threshold": float(scar_sel["selected_threshold"]),
            "edema_utility_threshold": float(edema_sel["selected_threshold"]),
            "scar_signed_net_utility": float(scar_sel["selected"].get("signed_net_utility", 0.0)),
            "edema_signed_net_utility": float(edema_sel["selected"].get("signed_net_utility", 0.0)),
            "scar_accepted": int(scar_sel["selected"].get("accepted", 0)),
            "scar_rejected": int(scar_sel["selected"].get("rejected", 0)),
            "edema_accepted": int(edema_sel["selected"].get("accepted", 0)),
            "edema_rejected": int(edema_sel["selected"].get("rejected", 0)),
            "avg_dice_delta": finite_mean(dice_values),
            "avg_hd95_ratio": finite_mean(hd_values),
            "avg_remote_fp_ratio": finite_mean(remote_values),
            "eligible": bool(eligibility),
            "eligibility_summary": inner_delta_summary,
            "outer_fold0_used": False,
            "scar_utility_regression_min": scar_sel["selected"].get("utility_regression_min"),
            "edema_utility_regression_min": edema_sel["selected"].get("utility_regression_min"),
            "selection_uses_accept_logit_and_signed_regression_gate": True,
        }
        selection_rows.append(row)
        write_csv(out_root / "gate_b_r1_checkpoint_selection_rows.csv", selection_rows)
        write_csv(out_root / "gate_b_r1_threshold_rows.csv", threshold_rows)
        write_csv(out_root / "gate_b_r1_inner_candidate_rows.csv", inner_candidate_rows)
        write_csv(out_root / "gate_b_r1_inner_casewise_metrics.csv", inner_casewise_all)
        write_json(out_root / "gate_b_r1_checkpoint_threshold_selection.json", {"status": "IN_PROGRESS", "rows": selection_rows, "threshold_rows": threshold_rows, "outer_fold0_used": False})
        if eligibility:
            eligible.append(row)
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    if not eligible:
        failure = {
            "task_key": TASK_KEY,
            "gate": "DPR_GATE_B_R1",
            "generated_at_utc": now_utc(),
            "status": "GATE_B_R1_REPAIR_REQUIRED",
            "failure": "CARE_DPR_GATE_B_R1_NO_ELIGIBLE_CHECKPOINT_INNER_ONLY",
            "selection_rule": "inner12_all_8_checkpoints_independent_scar_edema_thresholds_with_candidate_signed_regression_gate",
            "scar_utility_regression_min_candidates": list(regression_candidates(args.scar_utility_regression_min)),
            "edema_utility_regression_min_candidates": list(regression_candidates(args.edema_utility_regression_min)),
            "outer_fold0_used_for_checkpoint_or_threshold_selection": False,
            "fold_expansion_authorized": False,
            "scientific_final_output_credit": 0,
            "rows": selection_rows,
            "threshold_rows": threshold_rows,
        }
        write_json(out_root / "gate_b_r1_checkpoint_threshold_selection.json", {"status": "FAIL", "rows": selection_rows, "threshold_rows": threshold_rows, "outer_fold0_used": False})
        write_json(out_root / "gate_b_r1_summary.json", failure)
        write_json(result_root / "gate_b_r1_summary.json", {**failure, "evidence_root": str(out_root.relative_to(REPO_ROOT))})
        raise RuntimeError("CARE_DPR_GATE_B_R1_NO_ELIGIBLE_CHECKPOINT_INNER_ONLY")
    selected = max(eligible, key=lambda r: (float(r["avg_dice_delta"]), -float(r["avg_hd95_ratio"]), -float(r["avg_remote_fp_ratio"]), -int(r["checkpoint_step"])))
    checkpoint = REPO_ROOT / selected["checkpoint"]
    model, step, _ = load_care_dpr_checkpoint(checkpoint)
    model.to(device).eval()
    casewise: list[dict[str, Any]] = []
    casewise.extend(anchor_rows_for_cases(outer_val, "fold0_outer44", case_to_fold, metadata, cache))
    casewise.extend(anchor_rows_for_cases(complete_val, "fold0_complete_trimodal16", case_to_fold, metadata, cache))
    outer_eval = evaluate_population(model=model, cases=outer_val, population="fold0_outer44", case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device, utility_threshold=0.5, scar_utility_threshold=float(selected["scar_utility_threshold"]), edema_utility_threshold=float(selected["edema_utility_threshold"]), model_name=MODEL_NAME, scar_utility_regression_min=selected.get("scar_utility_regression_min"), edema_utility_regression_min=selected.get("edema_utility_regression_min"))
    complete_eval = evaluate_population(model=model, cases=complete_val, population="fold0_complete_trimodal16", case_to_fold=case_to_fold, metadata=metadata, cache=cache, device=device, utility_threshold=0.5, scar_utility_threshold=float(selected["scar_utility_threshold"]), edema_utility_threshold=float(selected["edema_utility_threshold"]), model_name=MODEL_NAME, scar_utility_regression_min=selected.get("scar_utility_regression_min"), edema_utility_regression_min=selected.get("edema_utility_regression_min"))
    casewise.extend(outer_eval["casewise"]); casewise.extend(complete_eval["casewise"])
    summary = summarize(casewise)
    no_t2_rows = outer_eval["no_t2"] + complete_eval["no_t2"]
    gate, help_harm = scientific_gate_from_casewise(
        casewise,
        no_t2_rows,
        population="fold0_complete_trimodal16",
        model_name=MODEL_NAME,
    )
    failures = list(gate["failures"])
    if selected["scar_accepted"] <= 0 or selected["scar_rejected"] <= 0 or selected["edema_accepted"] <= 0 or selected["edema_rejected"] <= 0:
        failures.append("selected_threshold_lacks_nonzero_accept_reject")
    if selected["scar_signed_net_utility"] <= 0 or selected["edema_signed_net_utility"] <= 0:
        failures.append("selected_signed_net_utility_not_positive")
    gate["failures"] = failures
    gate["status"] = "PASS" if not failures else "FAIL"
    gate["scientific_final_output_credit"] = 0 if failures else 1
    notification = {
        "subject": "[CARE-DPR][B-R1/2] Fold0候选级重建与仲裁修复完成，等待下一轮决策",
        "state": "AWAITING_HUMAN_ACCEPTANCE_DPR_GATE_B_R1",
        "approval_token": "APPROVE_DPR_GATE_B_R1",
        "fold_expansion_authorized": False,
        "all_data_fit_authorized": False,
        "validation_upload_authorized": False,
    }
    mechanism = outer_eval["mechanisms"]
    gate_summary = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_B_R1",
        "generated_at_utc": now_utc(),
        "status": "GATE_B_R1_OPERATIONAL_PASS" if gate["status"] == "PASS" else "GATE_B_R1_REPAIR_REQUIRED",
        "scientific_gate": gate,
        "selected_checkpoint": selected,
        "checkpoint_step": int(step),
        "checkpoint_sha256": sha256_file(checkpoint),
        "selection_rule": "inner12_all_8_checkpoints_independent_scar_edema_thresholds_with_candidate_signed_regression_gate",
        "scar_utility_regression_min": selected.get("scar_utility_regression_min"),
        "edema_utility_regression_min": selected.get("edema_utility_regression_min"),
        "outer_fold0_used_for_checkpoint_or_threshold_selection": False,
        "teacher_roi_inner_outer_inference": False,
        "predicted_roi_only_for_inner_outer_inference": True,
        "outer_heldout_cases": len(outer_val),
        "complete_trimodal_heldout_cases": len(complete_val),
        "outer44_case_ids_sha256": stable_json_sha256(outer_val),
        "complete16_case_ids_sha256": stable_json_sha256(complete_val),
        "train_side_inner12_case_ids_sha256": stable_json_sha256(inner_cases),
        "two_pass_full_volume_inference_contract": {
            "status": "PASS" if all(row["two_pass_full_volume_candidate_pipeline"] and not row["pass1_aggregates_patch_final_labels"] and not row["pass1_runs_component_decision"] and row["pass2_refines_each_candidate"] for row in outer_eval["activation"] + complete_eval["activation"]) else "FAIL",
            "scar_utility_threshold": float(selected["scar_utility_threshold"]),
            "edema_utility_threshold": float(selected["edema_utility_threshold"]),
            "scar_utility_regression_min": selected.get("scar_utility_regression_min"),
            "edema_utility_regression_min": selected.get("edema_utility_regression_min"),
            "acceptance_rule": "accept_logit_probability_threshold_and_clipped_utility_regression_min",
            "overlap": 0.5,
            "gaussian_blending": True,
            "patch_final_label_averaging": False,
            "patch_local_component_decision": False,
        },
        "mechanism_report": mechanism,
        "no_t2_exact_zero": {"status": "PASS" if all(r.get("status") == "PASS" for r in no_t2_rows) else "FAIL", "rows": no_t2_rows},
        "source_hashes": {**source_hashes(), "scripts/evaluation/evaluate_care_dpr_gate_b_r1.py": sha256_file(REPO_ROOT / "scripts/evaluation/evaluate_care_dpr_gate_b_r1.py")},
        "outputs": {
            "casewise": str((out_root / "gate_b_r1_casewise_metrics.csv").relative_to(REPO_ROOT)),
            "summary": str((out_root / "gate_b_r1_model_summary.csv").relative_to(REPO_ROOT)),
            "selection": str((out_root / "gate_b_r1_checkpoint_threshold_selection.json").relative_to(REPO_ROOT)),
            "candidate_rows": str((out_root / "gate_b_r1_outer_candidate_rows.csv").relative_to(REPO_ROOT)),
            "help_harm": str((out_root / "gate_b_r1_help_harm.csv").relative_to(REPO_ROOT)),
        },
        "notification": notification,
    }
    write_csv(out_root / "gate_b_r1_checkpoint_selection_rows.csv", selection_rows)
    write_csv(out_root / "gate_b_r1_threshold_rows.csv", threshold_rows)
    write_csv(out_root / "gate_b_r1_inner_candidate_rows.csv", inner_candidate_rows)
    write_csv(out_root / "gate_b_r1_inner_casewise_metrics.csv", inner_casewise_all)
    write_csv(out_root / "gate_b_r1_casewise_metrics.csv", casewise)
    write_csv(out_root / "gate_b_r1_model_summary.csv", summary)
    write_csv(out_root / "gate_b_r1_complete16_summary.csv", [r for r in summary if r["population"] == "fold0_complete_trimodal16"])
    write_csv(out_root / "gate_b_r1_outer44_summary.csv", [r for r in summary if r["population"] == "fold0_outer44"])
    write_csv(out_root / "gate_b_r1_help_harm.csv", help_harm)
    write_csv(out_root / "gate_b_r1_outer_candidate_rows.csv", outer_eval["candidate_rows"])
    write_csv(out_root / "gate_b_r1_activation_audit.csv", outer_eval["activation"] + complete_eval["activation"])
    write_csv(out_root / "gate_b_r1_no_t2_safety_audit.csv", no_t2_rows)
    write_json(out_root / "gate_b_r1_checkpoint_threshold_selection.json", {"status": "PASS", "selected": selected, "rows": selection_rows, "threshold_rows": threshold_rows, "outer_fold0_used": False})
    write_json(out_root / "gate_b_r1_mechanism_report.json", mechanism)
    write_json(out_root / "gate_b_r1_scientific_gate.json", gate)
    write_json(out_root / "gate_b_r1_summary.json", gate_summary)
    write_json(result_root / "gate_b_r1_summary.json", {**gate_summary, "evidence_root": str(out_root.relative_to(REPO_ROOT))})
    write_json(result_root / "checkpoint_notifications/dpr_gate_b_r1.json", {**notification, "gate_summary": gate_summary})
    return gate_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--cache-cases", type=int, default=16)
    parser.add_argument("--result-root", default=str(RESULT_ROOT))
    parser.add_argument("--runtime-name", default="formal_fold0")
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--device", default="")
    parser.add_argument("--scar-utility-regression-min", type=float, default=-1.0)
    parser.add_argument("--edema-utility-regression-min", type=float, default=-1.0)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    result = run_gate_b_r1(args)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["two_pass_full_volume_inference_contract"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
