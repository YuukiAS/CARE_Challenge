#!/usr/bin/env python3
"""Aggregate Batch7 repair stagewise training outputs and gates."""

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


def stage_cfg(cfg: dict[str, Any], stage: str) -> dict[str, Any]:
    mapping = {
        "proposal": "proposal_stage",
        "scar_refiner": "scar_refiner_stage",
        "edema_refiner": "edema_refiner_stage",
        "source_arbiter": "source_arbiter_stage",
        "production_gate": "production_gate_stage",
    }
    return dict(cfg["stagewise_training"][mapping[stage]])


def find_variant_dir(result_root: Path, stage: str, attempt_label: str) -> Path:
    return result_root / "runtime/stages" / stage / "attempts" / attempt_label / "variants" / attempt_label


def rel_worse(row: dict[str, Any], pred_key: str, anchor_key: str) -> float:
    pred = float(row[pred_key] or 0.0)
    anchor = float(row[anchor_key] or 0.0)
    return (pred - anchor) / max(abs(anchor), 1e-6)


def positive_summary(summary_rows: list[dict[str, Any]], step: int) -> dict[str, dict[str, Any]]:
    return {
        str(row["pathology"]): row
        for row in summary_rows
        if int(row["total_step"]) == step and row["group"] == "gt_positive_only" and row["pathology"] in {"myops_scar", "myops_edema"}
    }


def proposal_gate(cfg: dict[str, Any], variant_dir: Path, case_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]], step: int) -> dict[str, Any]:
    gate_cfg = stage_cfg(cfg, "proposal")["continuation_gate"]
    by_path = positive_summary(summary_rows, step)
    scar = by_path["myops_scar"]
    edema = by_path["myops_edema"]
    scar_delta = float(scar["dice_delta_mean"])
    edema_delta = float(edema["dice_delta_mean"])
    mean_delta = (scar_delta + edema_delta) / 2.0
    help_rows = help_harm_rows(case_rows, step)
    help_count = sum(1 for row in help_rows if row["help_harm"] == "help")
    harm_count = sum(1 for row in help_rows if row["help_harm"] == "harm")
    hd95_worse = max(rel_worse(row, "srr_hd95_mean", "anchor_hd95_mean") for row in (scar, edema))
    remote_worse = max(rel_worse(row, "srr_remote_fp_volume_mm3_mean", "anchor_remote_fp_volume_mm3_mean") for row in (scar, edema))
    checks = {
        "minimum_mean_positive_dice_delta": mean_delta >= float(gate_cfg["minimum_mean_positive_dice_delta"]),
        "minimum_scar_positive_dice_delta": scar_delta >= float(gate_cfg["minimum_scar_positive_dice_delta"]),
        "minimum_edema_positive_dice_delta": edema_delta >= float(gate_cfg["minimum_edema_positive_dice_delta"]),
        "help_not_less_than_harm": help_count >= harm_count,
        "hd95_relative_worsening": hd95_worse <= float(gate_cfg["maximum_each_pathology_hd95_relative_worsening"]),
        "remote_fp_relative_worsening": remote_worse <= float(gate_cfg["maximum_each_pathology_remote_fp_relative_worsening"]),
        "no_t2_edema_exact_zero": no_t2_exact_zero(variant_dir, step),
    }
    decision = "PASS" if all(checks.values()) else "FAIL"
    return {
        "continuation_gate_decision": decision,
        "failure_action": stage_cfg(cfg, "proposal")["failure_action"] if decision == "FAIL" else "CONTINUE_TO_REFINERS",
        "checks": checks,
        "mean_positive_dice_delta": mean_delta,
        "scar_positive_dice_delta": scar_delta,
        "edema_positive_dice_delta": edema_delta,
        "help_count": help_count,
        "harm_count": harm_count,
        "observed_hd95_relative_worsening_max": hd95_worse,
        "observed_remote_fp_relative_worsening_max": remote_worse,
    }


def refiner_acceptance(cfg: dict[str, Any], result_root: Path, stage: str, summary_rows: list[dict[str, Any]], step: int) -> dict[str, Any]:
    pathology = "myops_scar" if stage == "scar_refiner" else "myops_edema"
    proposal_path = result_root / "proposal_stage_adequacy.json"
    proposal = load_json(proposal_path)
    proposal_delta = float(proposal["pathology_positive_dice_delta"][pathology])
    row = positive_summary(summary_rows, step)[pathology]
    observed = float(row["dice_delta_mean"])
    minimum = float(stage_cfg(cfg, stage)["acceptance_gate"]["minimum_dice_gain_over_proposal"])
    accepted = observed >= proposal_delta + minimum
    return {
        "acceptance_decision": "PASS" if accepted else "FAIL",
        "formal_source": "refiner" if accepted else "proposal_only",
        "pathology": pathology,
        "proposal_positive_dice_delta": proposal_delta,
        "refiner_positive_dice_delta": observed,
        "refiner_minus_proposal": observed - proposal_delta,
        "minimum_dice_gain_over_proposal": minimum,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_repair.yaml")
    parser.add_argument("--stage", choices=("proposal", "scar_refiner", "edema_refiner", "source_arbiter", "production_gate"), required=True)
    parser.add_argument("--attempt-label", required=True)
    parser.add_argument("--job-id", default="local")
    parser.add_argument("--job-state", default="COMPLETED")
    parser.add_argument("--exit-code", default="0:0")
    parser.add_argument("--elapsed", default="")
    parser.add_argument("--node", default="")
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    cfg["paths"].setdefault("anchor_fold0_pred_dir", str(Path(cfg["paths"]["anchor_root"]) / "fold_0/validation"))
    result_root = repo_path(cfg["paths"]["result_root"])
    variant_dir = find_variant_dir(result_root, args.stage, args.attempt_label)
    summary = load_json(variant_dir / "summary.json")
    expected_steps = int(stage_cfg(cfg, args.stage)["optimizer_steps"])
    if int(summary.get("actual_optimizer_steps", -1)) != expected_steps:
        raise SystemExit(f"{args.stage} optimizer steps mismatch: {summary.get('actual_optimizer_steps')} != {expected_steps}")
    local_steps = [int(step) for step in stage_cfg(cfg, args.stage)["full_volume_eval_steps"]]
    case_rows: list[dict[str, Any]] = []
    for step in local_steps:
        case_rows.extend(metric_rows_for_step(cfg, variant_dir, step, step))
    summary_rows = summarize(case_rows)
    write_csv(result_root / f"{args.stage}_stage_casewise.csv", case_rows)
    write_csv(result_root / f"{args.stage}_stage_subgroups.csv", summary_rows)
    write_csv(result_root / f"{args.stage}_stage_help_harm.csv", help_harm_rows(case_rows, local_steps[-1]))
    ckpt = variant_dir / f"checkpoints/fold_0/propref_config/checkpoint_validation_step_{local_steps[-1]}.pt"
    adequacy: dict[str, Any] = {
        "schema_version": 1,
        "stage": args.stage,
        "status": "COMPLETE",
        "attempt_label": args.attempt_label,
        "job_id": args.job_id,
        "job_state": args.job_state,
        "job_exit_code": args.exit_code,
        "elapsed": args.elapsed,
        "node": args.node,
        "actual_optimizer_steps": summary.get("actual_optimizer_steps"),
        "validation_event_count": summary.get("validation_event_count"),
        "full_volume_eval_steps": local_steps,
        "selected_checkpoint_path": rel(ckpt),
        "selected_checkpoint_sha256": sha256_file(ckpt) if ckpt.is_file() else "",
        "pathology_positive_dice_delta": {key: float(row["dice_delta_mean"]) for key, row in positive_summary(summary_rows, local_steps[-1]).items()},
    }
    if args.stage == "proposal":
        adequacy.update(proposal_gate(cfg, variant_dir, case_rows, summary_rows, local_steps[-1]))
        write_csv(result_root / "proposal_stage_checkpoint_selection.csv", summary_rows)
        write_csv(result_root / "proposal_stage_casewise.csv", case_rows)
        write_csv(result_root / "proposal_stage_help_harm.csv", help_harm_rows(case_rows, local_steps[-1]))
        write_csv(result_root / "proposal_stage_subgroups.csv", summary_rows)
        write_json(result_root / "proposal_stage_adequacy.json", adequacy)
    elif args.stage in {"scar_refiner", "edema_refiner"}:
        adequacy.update(refiner_acceptance(cfg, result_root, args.stage, summary_rows, local_steps[-1]))
        write_json(result_root / f"{args.stage}_stage_adequacy.json", adequacy)
        rows = []
        for name in ("scar_refiner", "edema_refiner"):
            path = result_root / f"{name}_stage_adequacy.json"
            if path.is_file():
                rows.append(load_json(path))
        write_csv(result_root / "refiner_acceptance.csv", rows)
    else:
        write_json(result_root / f"{args.stage}_stage_adequacy.json", adequacy)
        write_json(result_root / "training_stage_adequacy.json", adequacy)
    attempts_path = result_root / "slurm_attempts.csv"
    attempts = read_csv(attempts_path) if attempts_path.is_file() else []
    attempts.append(
        {
            "stage": args.stage,
            "attempt_label": args.attempt_label,
            "job_id": args.job_id,
            "job_state": args.job_state,
            "exit_code": args.exit_code,
            "elapsed": args.elapsed,
            "node": args.node,
            "variant_dir": rel(variant_dir),
        }
    )
    write_csv(attempts_path, attempts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
