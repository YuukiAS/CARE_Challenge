#!/usr/bin/env python3
"""Aggregate M10 Wave 3 Cine runtime artifacts into lightweight packets."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXECUTOR_RESULT_DIR = REPO_ROOT / "results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_cine_temporal_executor"


@dataclass(frozen=True)
class CinePhase:
    phase: str
    design: str
    variant_dir_name: str
    result_dir: Path
    min_steps: int
    min_seconds: int
    min_validation_events: int
    min_eval_cases: int


PHASES = {
    "cinema_adapter": CinePhase(
        "cinema_adapter",
        "CineMA CARE adapter",
        "m10_cinema_adapter",
        REPO_ROOT / "results/20260711_srr_v3_m10_cinema_adapter",
        10000,
        3600,
        8,
        12,
    ),
    "cine_registration": CinePhase(
        "cine_registration",
        "learned diffeomorphic Cine registration",
        "m10_cine_registration",
        REPO_ROOT / "results/20260711_srr_v3_m10_cine_registration",
        25000,
        7200,
        10,
        12,
    ),
    "cine_temporal": CinePhase(
        "cine_temporal",
        "registration-gated learned temporal dictionary",
        "m10_cine_learned_temporal",
        REPO_ROOT / "results/20260711_srr_v3_m10_cine_learned_temporal",
        20000,
        7200,
        10,
        12,
    ),
}


def read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def phase_runtime_dir(phase: CinePhase, runtime_root: Path) -> Path:
    return runtime_root / "variants" / phase.variant_dir_name


def summarize_loss(rows: list[dict[str, str]]) -> dict[str, object]:
    losses: list[float] = []
    for row in rows:
        if row.get("event") == "validation":
            continue
        try:
            losses.append(float(row.get("loss", "")))
        except ValueError:
            pass
    if not losses:
        return {"status": "EVIDENCE_NOT_FOUND", "first_loss": "EVIDENCE_NOT_FOUND", "last_loss": "EVIDENCE_NOT_FOUND", "loss_decrease": "EVIDENCE_NOT_FOUND"}
    return {
        "status": "PASS" if losses[-1] <= losses[0] else "REQUIRES_REVIEW",
        "first_loss": losses[0],
        "last_loss": losses[-1],
        "loss_decrease": losses[0] - losses[-1],
    }


def phase_status(phase: CinePhase, summary: dict[str, object], validation_rows: list[dict[str, str]], job_id: str) -> str:
    if not summary:
        return "NEEDS_MONITOR" if job_id else "EVIDENCE_NOT_FOUND"
    if summary.get("status") == "REGISTRATION_GATE_FAILED_BLOCKS_TEMPORAL":
        return "REGISTRATION_GATE_FAILED_BLOCKS_TEMPORAL"
    if int(summary.get("actual_optimizer_steps") or 0) < phase.min_steps:
        return "UNDERTRAINED"
    if float(summary.get("train_loop_seconds") or 0.0) < phase.min_seconds:
        return "UNDERTRAINED"
    if len(validation_rows) < phase.min_validation_events:
        return "NEEDS_EVIDENCE"
    if int(summary.get("eval_cases") or 0) < phase.min_eval_cases:
        return "NEEDS_EVIDENCE"
    return "TERMINAL_RUNTIME_EVIDENCE"


def aggregate_phase(
    phase: CinePhase,
    runtime_root: Path,
    job_id: str = "",
    job_state: str = "",
    job_exit_code: str = "",
    job_log: str = "",
    partition: str = "",
) -> str:
    result_dir = phase.result_dir
    result_dir.mkdir(parents=True, exist_ok=True)
    rdir = phase_runtime_dir(phase, runtime_root)
    summary_path = rdir / "summary.json"
    summary = read_json(summary_path)
    train_rows = read_csv(rdir / "training_log.csv")
    validation_rows = read_csv(rdir / "validation_events.csv")
    status = phase_status(phase, summary, validation_rows, job_id)
    write_csv(
        result_dir / "training_budget_ledger.csv",
        [
            {
                "phase": phase.phase,
                "design": phase.design,
                "runtime_summary": str(summary_path),
                "slurm_job_id": job_id or "EVIDENCE_NOT_FOUND",
                "slurm_state": job_state or "EVIDENCE_NOT_FOUND",
                "slurm_exit_code": job_exit_code or "EVIDENCE_NOT_FOUND",
                "slurm_log_path": job_log or "EVIDENCE_NOT_FOUND",
                "partition": partition or "EVIDENCE_NOT_FOUND",
                "status": status,
                "actual_optimizer_steps": summary.get("actual_optimizer_steps", "EVIDENCE_NOT_FOUND"),
                "required_optimizer_steps": phase.min_steps,
                "train_loop_seconds": summary.get("train_loop_seconds", "EVIDENCE_NOT_FOUND"),
                "required_train_loop_seconds": phase.min_seconds,
                "validation_event_count": len(validation_rows),
                "required_validation_events": phase.min_validation_events,
                "eval_cases": summary.get("eval_cases", "EVIDENCE_NOT_FOUND"),
                "required_eval_cases": phase.min_eval_cases,
                "stop_reason": summary.get("stop_reason", "EVIDENCE_NOT_FOUND"),
            }
        ],
    )
    write_csv(result_dir / "loss_stability.csv", [{"phase": phase.phase, "status": status, **summarize_loss(train_rows)}])
    write_csv(result_dir / "validation_events.csv", [dict(row) for row in validation_rows] or [{"phase": phase.phase, "status": "EVIDENCE_NOT_FOUND"}])
    write_csv(
        result_dir / "checkpoint_selection.csv",
        [
            {
                "phase": phase.phase,
                "status": status,
                "checkpoint_best": summary.get("checkpoint_best", "EVIDENCE_NOT_FOUND"),
                "checkpoint_final": summary.get("checkpoint_final", "EVIDENCE_NOT_FOUND"),
                "best_step": summary.get("best_step", "EVIDENCE_NOT_FOUND"),
                "checkpoint_selection_mode": summary.get("checkpoint_selection_mode", "EVIDENCE_NOT_FOUND"),
                "checkpoint_selection_status": summary.get("checkpoint_selection_status", "EVIDENCE_NOT_FOUND"),
            }
        ],
    )
    write_csv(result_dir / "case_metrics.csv", [dict(row) for row in read_csv(rdir / "component_hd_by_case_checkpoint_best.csv")] or [{"phase": phase.phase, "status": "EVIDENCE_NOT_FOUND"}])
    write_csv(result_dir / "hard_subgroup_metrics.csv", [dict(row) for row in read_csv(rdir / "subgroup_metrics_checkpoint_best.csv")] or [{"phase": phase.phase, "status": "EVIDENCE_NOT_FOUND"}])
    extra_files = []
    for name in ("asset_provenance.json", "registration_gate.json", "temporal_slot_usage.csv"):
        if (rdir / name).is_file():
            extra_files.append(str(rdir / name))
    write_json(
        result_dir / "runtime_manifest.json",
        {
            "phase": phase.phase,
            "design": phase.design,
            "status": status,
            "runtime_variant_dir": str(rdir),
            "summary_path": str(summary_path),
            "slurm_job_id": job_id or "EVIDENCE_NOT_FOUND",
            "slurm_state": job_state or "EVIDENCE_NOT_FOUND",
            "slurm_exit_code": job_exit_code or "EVIDENCE_NOT_FOUND",
            "slurm_log_path": job_log or "EVIDENCE_NOT_FOUND",
            "partition": partition or "EVIDENCE_NOT_FOUND",
            "runtime_files_checked": [
                str(summary_path),
                str(rdir / "training_log.csv"),
                str(rdir / "validation_events.csv"),
                str(rdir / "component_hd_by_case_checkpoint_best.csv"),
                str(rdir / "subgroup_metrics_checkpoint_best.csv"),
                *extra_files,
            ],
        },
    )
    (result_dir / "prediction_sanity.md").write_text(
        "\n".join(
            [
                f"# Prediction Sanity - {phase.phase}",
                "",
                f"Status: `{status}`",
                f"Runtime summary: `{summary_path}`",
                f"Prediction dirs: `{summary.get('prediction_dirs', 'EVIDENCE_NOT_FOUND')}`",
                "",
                "No hosted metrics, validation packaging, validation upload, route promotion, or scientific stop is claimed.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (result_dir / "result.md").write_text(
        "\n".join(
            [
                f"# M10 Cine Phase Result - {phase.phase}",
                "",
                f"Design: `{phase.design}`",
                f"Status: `{status}`",
                "",
                "This phase packet is runtime-derived when the summary exists. Missing runtime artifacts remain evidence gaps.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (result_dir / "commands_run.md").write_text(
        "\n".join(
            [
                f"# Commands Run - {phase.phase}",
                "",
                f"- job_id: `{job_id or 'EVIDENCE_NOT_FOUND'}`",
                f"- state: `{job_state or 'EVIDENCE_NOT_FOUND'}`",
                f"- exit_code: `{job_exit_code or 'EVIDENCE_NOT_FOUND'}`",
                f"- log_path: `{job_log or 'EVIDENCE_NOT_FOUND'}`",
                f"- partition: `{partition or 'EVIDENCE_NOT_FOUND'}`",
                f"- aggregation_command: `python scripts/evaluation/aggregate_cine_m10_packet.py --phase {phase.phase}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (result_dir / "MANIFEST.md").write_text(
        "\n".join(
            [
                f"# MANIFEST - {phase.phase}",
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


def write_executor_packet(statuses: dict[str, str], runtime_root: Path) -> str:
    EXECUTOR_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    if all(value == "TERMINAL_RUNTIME_EVIDENCE" for value in statuses.values()):
        token = "READY_FOR_CONTROLLER_MERGE"
    elif any(value == "NEEDS_MONITOR" for value in statuses.values()):
        token = "NEEDS_MONITOR"
    else:
        token = "NEEDS_EVIDENCE"
    lines = [
        "# M10 Cine Temporal Executor Result",
        "",
        f"completion_token: `{token}`",
        f"runtime_root: `{runtime_root}`",
        "",
        "| Phase | Status |",
        "| --- | --- |",
    ]
    for phase, status in statuses.items():
        lines.append(f"| `{phase}` | `{status}` |")
    lines.extend(
        [
            "",
            "No review, push, validation packaging/upload, hosted metric claim, route promotion, route-negative decision, or M11 start is performed here.",
        ]
    )
    (EXECUTOR_RESULT_DIR / "result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (EXECUTOR_RESULT_DIR / "completion_check.md").write_text(
        "\n".join(["# Completion Check", "", f"decision: `{token}`", "", "Wave 3 remains controller-owned and requires independent review after final packet commit."]) + "\n",
        encoding="utf-8",
    )
    write_json(EXECUTOR_RESULT_DIR / "runtime_manifest.json", {"status": token, "phase_statuses": statuses, "runtime_root": str(runtime_root)})
    (EXECUTOR_RESULT_DIR / "commands_run.md").write_text(
        "\n".join(["# Commands Run", "", f"- aggregation_command: `python scripts/evaluation/aggregate_cine_m10_packet.py --phase all --runtime-root {runtime_root}`"]) + "\n",
        encoding="utf-8",
    )
    (EXECUTOR_RESULT_DIR / "MANIFEST.md").write_text(
        "\n".join(["# MANIFEST", "", "- result.md", "- completion_check.md", "- runtime_manifest.json", "- commands_run.md"]) + "\n",
        encoding="utf-8",
    )
    return token


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=[*PHASES.keys(), "all"], default="all")
    parser.add_argument("--runtime-root", default="results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_cine_temporal_executor")
    parser.add_argument("--job-id", default="")
    parser.add_argument("--job-state", default="")
    parser.add_argument("--job-exit-code", default="")
    parser.add_argument("--job-log", default="")
    parser.add_argument("--partition", default="")
    args = parser.parse_args()
    runtime_root = Path(args.runtime_root)
    if not runtime_root.is_absolute():
        runtime_root = REPO_ROOT / runtime_root
    selected = PHASES if args.phase == "all" else {args.phase: PHASES[args.phase]}
    statuses = {
        key: aggregate_phase(phase, runtime_root, job_id=args.job_id, job_state=args.job_state, job_exit_code=args.job_exit_code, job_log=args.job_log, partition=args.partition)
        for key, phase in selected.items()
    }
    if args.phase == "all":
        token = write_executor_packet(statuses, runtime_root)
        print(json.dumps({"executor_token": token, "phase_statuses": statuses}, indent=2, sort_keys=True))
    else:
        print(json.dumps({"phase_statuses": statuses}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
