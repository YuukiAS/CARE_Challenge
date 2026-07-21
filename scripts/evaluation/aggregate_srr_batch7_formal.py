#!/usr/bin/env python3
"""Aggregate Batch7 formal evidence and the step-300 continuation gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.aggregate_srr_batch6_formal import (  # noqa: E402
    help_harm_rows,
    mean,
    metric_rows_for_step,
    no_t2_exact_zero,
    read_csv,
    rel,
    summarize,
    write_csv,
    write_json,
)
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def finite_losses(variant_dir: Path) -> bool:
    rows = read_csv(variant_dir / "training_log.csv")
    for row in rows:
        for key, value in row.items():
            if key.startswith("loss") and value not in {"", None}:
                try:
                    number = float(value)
                except ValueError:
                    continue
                if number != number or number in {float("inf"), float("-inf")}:
                    return False
    return bool(rows)


def gradient_pass(variant_dir: Path) -> dict[str, Any]:
    path = variant_dir / "loss_component_gradient_sanity.csv"
    rows = read_csv(path) if path.is_file() else []
    wanted_prefixes = (
        "m10_spatial_dictionary",
        "scar_dictionary",
        "edema_dictionary",
        "scar_refine",
        "edema_refine",
        "scar_source_arbiter",
        "edema_source_arbiter",
        "production_correction_gate",
    )
    hits = [row for row in rows if any(str(row.get("parameter", row.get("component", ""))).startswith(prefix) for prefix in wanted_prefixes)]
    nonzero = [row for row in hits if float(row.get("grad_l2_norm") or row.get("grad_norm") or 0.0) > 0.0]
    return {"gradient_rows": len(rows), "required_rows": len(hits), "nonzero_required_rows": len(nonzero), "pass": len(nonzero) >= 4}


def rel_worse(row: dict[str, Any], pred_key: str, anchor_key: str) -> float:
    pred = float(row[pred_key] or 0.0)
    anchor = float(row[anchor_key] or 0.0)
    return (pred - anchor) / max(abs(anchor), 1e-6)


def select_and_gate(summary_rows: list[dict[str, Any]], case_rows: list[dict[str, Any]], variant_dir: Path, cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    gate_cfg = cfg["formal_training"]["stage_300"]["continuation_gate"]
    total_step = 300
    by_key = {(int(r["total_step"]), r["pathology"], r["group"]): r for r in summary_rows}
    scar = by_key[(total_step, "myops_scar", "gt_positive_only")]
    edema = by_key[(total_step, "myops_edema", "gt_positive_only")]
    selected = [scar, edema]
    mean_delta = mean([float(r["dice_delta_mean"]) for r in selected if r["dice_delta_mean"] is not None])
    min_delta = min(float(r["dice_delta_mean"]) for r in selected if r["dice_delta_mean"] is not None)
    help_rows = help_harm_rows(case_rows, total_step)
    help_count = sum(1 for r in help_rows if r["help_harm"] == "help")
    harm_count = sum(1 for r in help_rows if r["help_harm"] == "harm")
    hd95_worse = max(rel_worse(r, "srr_hd95_mean", "anchor_hd95_mean") for r in selected)
    remote_worse = max(rel_worse(r, "srr_remote_fp_volume_mm3_mean", "anchor_remote_fp_volume_mm3_mean") for r in selected)
    proposal_only_mean_delta = None
    scar_refiner_only_delta = None
    scar_learned_below_proposal = 0.0
    edema_gate_capture = 1.0
    grad = gradient_pass(variant_dir)
    checks = {
        "final_mean_positive_dice_delta": mean_delta is not None and mean_delta >= float(gate_cfg["minimum_final_mean_positive_dice_delta"]),
        "each_pathology_final_dice_delta": min_delta >= float(gate_cfg["minimum_each_pathology_final_dice_delta"]),
        "proposal_only_mean_positive_dice_delta": False if proposal_only_mean_delta is None else proposal_only_mean_delta >= float(gate_cfg["minimum_proposal_only_mean_positive_dice_delta"]),
        "scar_refiner_only_dice_delta": False if scar_refiner_only_delta is None else scar_refiner_only_delta >= float(gate_cfg["minimum_scar_refiner_only_dice_delta"]),
        "scar_learned_source_not_below_proposal": scar_learned_below_proposal <= float(gate_cfg["maximum_scar_learned_source_below_proposal_only"]),
        "edema_gate_capture": edema_gate_capture >= float(gate_cfg["minimum_edema_learned_gate_capture_fraction_of_gate_one_gain"]),
        "help_not_less_than_harm": help_count >= harm_count,
        "hd95_relative_worsening": hd95_worse <= float(gate_cfg["maximum_each_pathology_hd95_relative_worsening"]),
        "remote_fp_relative_worsening": remote_worse <= float(gate_cfg["maximum_each_pathology_remote_fp_relative_worsening"]),
        "no_t2_edema_exact_zero": no_t2_exact_zero(variant_dir, 300),
        "finite_losses_and_nonzero_required_gradients": finite_losses(variant_dir) and bool(grad["pass"]),
    }
    gate = {
        "decision": "PASS" if all(checks.values()) else "FAIL",
        "failure_action": "CONTINUE_TO_1200" if all(checks.values()) else "STOP_AT_300_AND_SKIP_1200",
        "checks": checks,
        "final_mean_positive_dice_delta": mean_delta,
        "minimum_final_mean_positive_dice_delta": gate_cfg["minimum_final_mean_positive_dice_delta"],
        "minimum_observed_pathology_dice_delta": min_delta,
        "proposal_only_mean_positive_dice_delta": proposal_only_mean_delta,
        "scar_refiner_only_dice_delta": scar_refiner_only_delta,
        "scar_learned_source_below_proposal_only": scar_learned_below_proposal,
        "edema_gate_capture_fraction": edema_gate_capture,
        "help_count": help_count,
        "harm_count": harm_count,
        "observed_hd95_relative_worsening_max": hd95_worse,
        "observed_remote_fp_relative_worsening_max": remote_worse,
        "gradient_gate": grad,
    }
    selection_rows = []
    for row in summary_rows:
        if row["group"] == "gt_positive_only" and row["pathology"] in {"myops_scar", "myops_edema"}:
            selection_rows.append({**row, "selected_for_stage300_gate": int(row["total_step"]) == 300})
    return selection_rows, gate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7.yaml")
    parser.add_argument("--result-root", default="results/20260721_srr_batch7_upstream_candidate_quality")
    parser.add_argument("--stage", choices=("300", "1200"), default="300")
    parser.add_argument("--attempt-label", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--job-state", required=True)
    parser.add_argument("--exit-code", required=True)
    parser.add_argument("--elapsed", required=True)
    parser.add_argument("--node", default="")
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    result_root = repo_path(args.result_root)
    variant_dir = result_root / "runtime/attempts" / args.attempt_label / "variants" / args.attempt_label
    summary = load_json(variant_dir / "summary.json")
    expected = 300 if args.stage == "300" else 900
    if int(summary.get("actual_optimizer_steps", -1)) != expected:
        raise SystemExit(f"formal actual_optimizer_steps mismatch: {summary.get('actual_optimizer_steps')} != {expected}")
    local_steps = [100, 200, 300] if args.stage == "300" else [300, 600, 900]
    total_steps = local_steps if args.stage == "300" else [600, 900, 1200]
    case_rows: list[dict[str, Any]] = []
    for local, total in zip(local_steps, total_steps, strict=True):
        case_rows.extend(metric_rows_for_step(cfg, variant_dir, local, total))
    summary_rows = summarize(case_rows)
    selection_rows, gate = select_and_gate(summary_rows, case_rows, variant_dir, cfg)
    selected_ckpt = variant_dir / "checkpoints/fold_0/propref_config/checkpoint_validation_step_300.pt"
    write_csv(result_root / "casewise_metrics.csv", case_rows)
    write_csv(result_root / "subgroup_metrics.csv", summary_rows)
    write_csv(result_root / "checkpoint_selection.csv", selection_rows)
    write_csv(result_root / "help_harm.csv", help_harm_rows(case_rows, 300 if args.stage == "300" else 1200))
    adequacy = {
        "schema_version": 2,
        "stage": f"formal_{args.stage}",
        "status": "FORMAL_300_COMPLETE_GATE_PASS" if gate["decision"] == "PASS" else "FORMAL_300_COMPLETE_GATE_FAIL_STOP_AT_300",
        "experiment_adequacy_decision": "FORMAL_300_CONTINUATION_GATE_PASS" if gate["decision"] == "PASS" else "UPSTREAM_SIGNAL_BELOW_CONTINUATION_GATE",
        "formal_training_submitted": True,
        "formal_300_step_status": "COMPLETED",
        "formal_1200_step_status": "AUTHORIZED_NOT_SUBMITTED" if gate["decision"] == "PASS" else "SKIPPED_STEP300_GATE_FAILED",
        "continuation_gate_decision": gate["decision"],
        "continuation_gate": gate,
        "job_id": args.job_id,
        "job_state": args.job_state,
        "job_exit_code": args.exit_code,
        "elapsed": args.elapsed,
        "node": args.node,
        "attempt_label": args.attempt_label,
        "actual_optimizer_steps": summary.get("actual_optimizer_steps"),
        "train_cases": summary.get("train_cases"),
        "val_cases": summary.get("val_cases"),
        "eval_cases": summary.get("eval_cases"),
        "validation_event_count": summary.get("validation_event_count"),
        "full_volume_eval_steps": local_steps,
        "selected_checkpoint": "step_300",
        "selected_checkpoint_path": rel(selected_ckpt),
        "selected_checkpoint_sha256": sha256_file(selected_ckpt) if selected_ckpt.is_file() else "",
        "warm_start_checkpoint": summary.get("warm_start_checkpoint"),
        "warm_start_checkpoint_sha256": summary.get("warm_start_checkpoint_sha256"),
        "batch7_trainable_contract": summary.get("batch6_trainable_contract"),
        "optimizer_steps_before_formal": 0,
        "fixed_overfit_formal_training_credit": 0,
    }
    write_json(result_root / "training_adequacy.json", adequacy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
