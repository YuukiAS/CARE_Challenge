#!/usr/bin/env python3
"""Aggregate M10 wave 2 MyoPS phase artifacts into reviewable files."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Iterable

from scripts.training.run_srr_v3_m10_complete_repair import PHASES, REPO_ROOT, PhaseSpec


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(value: object) -> float | None:
    try:
        if value in {None, ""}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def variant_dir(spec: PhaseSpec, runtime_root: Path | None = None) -> Path:
    root = runtime_root or (REPO_ROOT / spec.result_dir / "runtime")
    if not root.is_absolute():
        root = REPO_ROOT / root
    return root / "variants" / spec.run_label


def summarize_loss(rows: list[dict[str, str]]) -> dict[str, object]:
    losses = [as_float(row.get("loss")) for row in rows if row.get("event") != "validation"]
    losses = [value for value in losses if value is not None]
    if not losses:
        return {
            "first_loss": "EVIDENCE_NOT_FOUND",
            "last_loss": "EVIDENCE_NOT_FOUND",
            "median_first_window": "EVIDENCE_NOT_FOUND",
            "median_last_window": "EVIDENCE_NOT_FOUND",
            "loss_decrease": "EVIDENCE_NOT_FOUND",
            "last_five_cv": "EVIDENCE_NOT_FOUND",
            "status": "EVIDENCE_NOT_FOUND",
        }
    first_window = losses[: min(10, len(losses))]
    last_window = losses[-min(10, len(losses)) :]
    last_five = losses[-min(5, len(losses)) :]
    mean_last = statistics.mean(last_five)
    cv = 0.0 if mean_last == 0 else statistics.pstdev(last_five) / abs(mean_last)
    first_med = statistics.median(first_window)
    last_med = statistics.median(last_window)
    decrease = first_med - last_med
    status = "PASS" if decrease > 0 and cv <= 0.15 else "REQUIRES_REVIEW"
    return {
        "first_loss": losses[0],
        "last_loss": losses[-1],
        "median_first_window": first_med,
        "median_last_window": last_med,
        "loss_decrease": decrease,
        "last_five_cv": cv,
        "status": status,
    }


def phase_status(
    spec: PhaseSpec,
    summary: dict[str, object],
    train_rows: list[dict[str, str]],
    validation_rows: list[dict[str, str]],
    job_id: str = "",
    job_state: str = "",
) -> str:
    normalized_job_state = job_state.upper()
    if not summary and any(token in normalized_job_state for token in ("FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL")):
        return "STARTUP_FAILED_NEEDS_EVIDENCE"
    if not summary:
        if job_id:
            return "NEEDS_MONITOR"
        return "EVIDENCE_NOT_FOUND"
    steps = int(summary.get("actual_optimizer_steps") or 0)
    seconds = float(summary.get("train_loop_seconds") or 0.0)
    eval_cases = int(summary.get("eval_cases") or 0)
    validation_count = len(validation_rows)
    if steps < spec.min_steps or seconds < spec.min_train_loop_seconds:
        return "UNDERTRAINED"
    if validation_count < spec.min_validation_events or eval_cases < spec.min_eval_cases:
        return "NEEDS_EVIDENCE"
    loss_status = summarize_loss(train_rows).get("status")
    if loss_status not in {"PASS", "REQUIRES_REVIEW"}:
        return "NEEDS_EVIDENCE"
    return "TERMINAL_RUNTIME_EVIDENCE"


def aggregate_phase(
    spec: PhaseSpec,
    runtime_root: Path | None = None,
    job_id: str = "",
    job_state: str = "",
    job_exit_code: str = "",
    job_log: str = "",
) -> str:
    result_dir = REPO_ROOT / spec.result_dir
    result_dir.mkdir(parents=True, exist_ok=True)
    vdir = variant_dir(spec, runtime_root)
    summary_path = vdir / "summary.json"
    summary = load_json(summary_path)
    train_rows = read_csv(vdir / "training_log.csv")
    validation_rows = read_csv(vdir / "validation_events.csv")
    status = phase_status(spec, summary, train_rows, validation_rows, job_id=job_id, job_state=job_state)

    budget_row = {
        "phase": spec.phase,
        "design": spec.design,
        "variant": spec.variant,
        "runtime_summary": str(summary_path),
        "slurm_job_id": job_id or "EVIDENCE_NOT_FOUND",
        "slurm_state": job_state or "EVIDENCE_NOT_FOUND",
        "slurm_exit_code": job_exit_code or "EVIDENCE_NOT_FOUND",
        "slurm_log_path": job_log or "EVIDENCE_NOT_FOUND",
        "status": status,
        "actual_optimizer_steps": summary.get("actual_optimizer_steps", "EVIDENCE_NOT_FOUND"),
        "required_optimizer_steps": spec.min_steps,
        "train_loop_seconds": summary.get("train_loop_seconds", "EVIDENCE_NOT_FOUND"),
        "required_train_loop_seconds": spec.min_train_loop_seconds,
        "validation_event_count": len(validation_rows),
        "required_validation_events": spec.min_validation_events,
        "eval_cases": summary.get("eval_cases", "EVIDENCE_NOT_FOUND"),
        "required_eval_cases": spec.min_eval_cases,
        "stop_reason": summary.get("stop_reason", "EVIDENCE_NOT_FOUND"),
    }
    write_csv(result_dir / "training_budget_ledger.csv", [budget_row])
    loss_row = {"phase": spec.phase, "status": status, **summarize_loss(train_rows)}
    write_csv(result_dir / "loss_stability.csv", [loss_row])

    if validation_rows:
        write_csv(result_dir / "validation_events.csv", [dict(row) for row in validation_rows])
    else:
        write_csv(result_dir / "validation_events.csv", [{"phase": spec.phase, "status": "EVIDENCE_NOT_FOUND"}])

    checkpoint_row = {
        "phase": spec.phase,
        "status": status,
        "checkpoint_best": summary.get("checkpoint_best", "EVIDENCE_NOT_FOUND"),
        "checkpoint_final": summary.get("checkpoint_final", "EVIDENCE_NOT_FOUND"),
        "best_step": summary.get("best_step", "EVIDENCE_NOT_FOUND"),
        "checkpoint_selection_mode": summary.get("checkpoint_selection_mode", "EVIDENCE_NOT_FOUND"),
        "checkpoint_selection_status": summary.get("checkpoint_selection_status", "EVIDENCE_NOT_FOUND"),
    }
    write_csv(result_dir / "checkpoint_selection.csv", [checkpoint_row])

    case_rows = read_csv(vdir / "component_hd_by_case_checkpoint_best.csv")
    write_csv(result_dir / "case_metrics.csv", [dict(row) for row in case_rows] or [{"phase": spec.phase, "status": "EVIDENCE_NOT_FOUND"}])
    subgroup_rows = read_csv(vdir / "subgroup_metrics_checkpoint_best.csv")
    write_csv(result_dir / "hard_subgroup_metrics.csv", [dict(row) for row in subgroup_rows] or [{"phase": spec.phase, "status": "EVIDENCE_NOT_FOUND"}])

    prediction_lines = [
        f"# Prediction Sanity - {spec.phase}",
        "",
        f"Status: `{status}`",
        f"Runtime summary: `{summary_path}`",
        f"Prediction dirs: `{summary.get('prediction_dirs', 'EVIDENCE_NOT_FOUND')}`",
        "",
        "No hosted metrics, validation packaging, validation upload, route promotion, or scientific stop is claimed.",
    ]
    (result_dir / "prediction_sanity.md").write_text("\n".join(prediction_lines) + "\n", encoding="utf-8")
    runtime_manifest = {
        "phase": spec.phase,
        "design": spec.design,
        "variant": spec.variant,
        "status": status,
        "result_dir": str(result_dir),
        "runtime_variant_dir": str(vdir),
        "slurm_job_id": job_id or "EVIDENCE_NOT_FOUND",
        "slurm_state": job_state or "EVIDENCE_NOT_FOUND",
        "slurm_exit_code": job_exit_code or "EVIDENCE_NOT_FOUND",
        "slurm_log_path": job_log or "EVIDENCE_NOT_FOUND",
        "summary_path": str(summary_path),
        "runtime_files_checked": [
            str(vdir / "summary.json"),
            str(vdir / "training_log.csv"),
            str(vdir / "validation_events.csv"),
            str(vdir / "component_hd_by_case_checkpoint_best.csv"),
            str(vdir / "subgroup_metrics_checkpoint_best.csv"),
        ],
    }
    (result_dir / "runtime_manifest.json").write_text(json.dumps(runtime_manifest, indent=2, sort_keys=True), encoding="utf-8")

    result_lines = [
        f"# M10 MyoPS Phase Result - {spec.phase}",
        "",
        f"Design: `{spec.design}`",
        f"Variant: `{spec.variant}`",
        f"Status: `{status}`",
        "",
        "This phase packet is runtime-derived when the summary exists. Missing runtime artifacts remain evidence gaps.",
    ]
    (result_dir / "result.md").write_text("\n".join(result_lines) + "\n", encoding="utf-8")
    command_lines = [
        f"# Commands Run - {spec.phase}",
        "",
        "## Slurm",
        "",
        f"- job_id: `{job_id or 'EVIDENCE_NOT_FOUND'}`",
        f"- state: `{job_state or 'EVIDENCE_NOT_FOUND'}`",
        f"- exit_code: `{job_exit_code or 'EVIDENCE_NOT_FOUND'}`",
        f"- log_path: `{job_log or 'EVIDENCE_NOT_FOUND'}`",
        "- partition: `htzhulab`",
        f"- job_script: `jobs/src/{job_script_for_phase(spec.phase)}`",
        f"- state_at_packet_write: `{status}`",
        "",
        "## Aggregation",
        "",
        f"- command: `python scripts/evaluation/aggregate_srr_v3_m10_myops.py --phase {spec.phase}`",
        f"- runtime_summary_checked: `{summary_path}`",
    ]
    (result_dir / "commands_run.md").write_text("\n".join(command_lines) + "\n", encoding="utf-8")
    (result_dir / "MANIFEST.md").write_text(
        "\n".join(
            [
                f"# MANIFEST - {spec.phase}",
                "",
                "- result.md",
                "- training_budget_ledger.csv",
                "- loss_stability.csv",
                "- validation_events.csv",
                "- checkpoint_selection.csv",
                "- case_metrics.csv",
                "- hard_subgroup_metrics.csv",
                "- prediction_sanity.md",
                "- runtime_manifest.json",
                "- commands_run.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return status


def job_script_for_phase(phase: str) -> str:
    return {
        "d0_control": "run_srr_v3_m10_myops_d0_control.sh",
        "d1_spatial_br2": "run_srr_v3_m10_myops_d1_spatial_br2.sh",
        "d2_hierarchical_psip": "run_srr_v3_m10_myops_d2_hierarchical_psip.sh",
        "d3_full_propref": "run_srr_v3_m10_myops_d3_full_propref.sh",
        "hard_negative_refresh": "run_srr_v3_m10_hard_negative_refresh.sh",
        "no_context_control": "run_srr_v3_m10_no_context_control.sh",
        "alignment_control": "run_srr_v3_m10_alignment_control.sh",
    }.get(phase, "EVIDENCE_NOT_FOUND")


def aggregate_component_audit(phases: Iterable[PhaseSpec]) -> str:
    result_dir = REPO_ROOT / "results/20260711_srr_v3_m10_component_causal_audit"
    result_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    statuses = []
    for spec in phases:
        manifest = load_json(REPO_ROOT / spec.result_dir / "runtime_manifest.json")
        status = str(manifest.get("status", "EVIDENCE_NOT_FOUND"))
        statuses.append(status)
        rows.append(
            {
                "phase": spec.phase,
                "design": spec.design,
                "variant": spec.variant,
                "source_runtime_manifest": str(REPO_ROOT / spec.result_dir / "runtime_manifest.json"),
                "component_call_count": "EVIDENCE_NOT_FOUND" if status != "TERMINAL_RUNTIME_EVIDENCE" else "SEE_RUNTIME_TABLES",
                "gradient_norm": "EVIDENCE_NOT_FOUND" if status != "TERMINAL_RUNTIME_EVIDENCE" else "SEE_LOSS_COMPONENT_GRADIENT_SANITY",
                "final_output_effect": "EVIDENCE_NOT_FOUND" if status != "TERMINAL_RUNTIME_EVIDENCE" else "SEE_CASE_METRICS_AND_INTERVENTIONS",
                "classification": "UNDERTRAINED_OR_MISSING" if status != "TERMINAL_RUNTIME_EVIDENCE" else "OUTPUT_EFFECT_REQUIRES_REVIEW",
            }
        )
    write_csv(result_dir / "component_causal_interventions.csv", rows)
    overall = "TERMINAL_RUNTIME_EVIDENCE" if all(status == "TERMINAL_RUNTIME_EVIDENCE" for status in statuses) else "NEEDS_MONITOR_OR_EVIDENCE"
    (result_dir / "runtime_manifest.json").write_text(json.dumps({"status": overall, "phase_count": len(rows)}, indent=2, sort_keys=True), encoding="utf-8")
    (result_dir / "result.md").write_text(
        f"# M10 Component Causal Audit\n\nStatus: `{overall}`\n\nThis audit aggregates phase runtime evidence only and does not replace intervention jobs or review.\n",
        encoding="utf-8",
    )
    (result_dir / "commands_run.md").write_text("# Commands Run\n\nGenerated by `scripts/evaluation/aggregate_srr_v3_m10_myops.py --all`.\n", encoding="utf-8")
    (result_dir / "MANIFEST.md").write_text("# MANIFEST\n\n- result.md\n- component_causal_interventions.csv\n- runtime_manifest.json\n- commands_run.md\n", encoding="utf-8")
    return overall


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=sorted(PHASES))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--job-id", action="append", default=[], help="Repeatable phase=job_id monitor receipt.")
    parser.add_argument("--job-state", action="append", default=[], help="Repeatable phase=SlurmState receipt.")
    parser.add_argument("--job-exit-code", action="append", default=[], help="Repeatable phase=ExitCode receipt.")
    parser.add_argument("--job-log", action="append", default=[], help="Repeatable phase=log_path receipt.")
    args = parser.parse_args()
    if not args.all and not args.phase:
        parser.error("use --phase or --all")
    runtime_root = Path(args.runtime_root) if args.runtime_root else None
    if runtime_root is not None and not runtime_root.is_absolute():
        runtime_root = REPO_ROOT / runtime_root
    job_ids: dict[str, str] = {}
    for item in args.job_id:
        if "=" not in item:
            parser.error("--job-id expects phase=job_id")
        phase, job_id = item.split("=", 1)
        job_ids[phase.strip()] = job_id.strip()
    job_states: dict[str, str] = {}
    for item in args.job_state:
        if "=" not in item:
            parser.error("--job-state expects phase=state")
        phase, state = item.split("=", 1)
        job_states[phase.strip()] = state.strip()
    job_exit_codes: dict[str, str] = {}
    for item in args.job_exit_code:
        if "=" not in item:
            parser.error("--job-exit-code expects phase=exit_code")
        phase, exit_code = item.split("=", 1)
        job_exit_codes[phase.strip()] = exit_code.strip()
    job_logs: dict[str, str] = {}
    for item in args.job_log:
        if "=" not in item:
            parser.error("--job-log expects phase=log_path")
        phase, log_path = item.split("=", 1)
        job_logs[phase.strip()] = log_path.strip()
    selected = list(PHASES.values()) if args.all else [PHASES[str(args.phase)]]
    statuses = [
        aggregate_phase(
            spec,
            runtime_root,
            job_id=job_ids.get(spec.phase, ""),
            job_state=job_states.get(spec.phase, ""),
            job_exit_code=job_exit_codes.get(spec.phase, ""),
            job_log=job_logs.get(spec.phase, ""),
        )
        for spec in selected
    ]
    if args.all:
        statuses.append(aggregate_component_audit(selected))
    if any(status in {"EVIDENCE_NOT_FOUND", "NEEDS_EVIDENCE", "UNDERTRAINED", "NEEDS_MONITOR", "NEEDS_MONITOR_OR_EVIDENCE", "STARTUP_FAILED_NEEDS_EVIDENCE"} for status in statuses):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
