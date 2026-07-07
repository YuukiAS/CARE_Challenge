#!/usr/bin/env python3
"""Aggregate completed SRR-v3 M8 runtime outputs into lightweight evidence.

This script is intentionally fail-closed. It may be run while jobs are still
pending/running, but it will keep the packet in a non-ready state until the M8
training budget, per-variant summaries, and mandatory Cine evidence are present.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260707_srr_v3_m8_editor_grade_leaderboard_sprint"
DEFAULT_PACKET = REPO_ROOT / "results" / TASK_KEY
VARIANTS = [
    "m8_full_srr_context_arbitration_longrun",
    "m8_scar_precision_edema_safe_longrun",
    "m8_t2_centerC_edema_repair_longrun",
]
MONITOR_STATUS = "M8_NEEDS_MONITOR_NO_REVIEW"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "EVIDENCE_NOT_FOUND"


def as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: object, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def variant_dir(packet: Path, variant: str) -> Path:
    return packet / "runtime" / "variants" / variant


def summary_path(packet: Path, variant: str) -> Path:
    return variant_dir(packet, variant) / "summary.json"


def existing_summary(packet: Path, variant: str) -> dict[str, object]:
    return read_json(summary_path(packet, variant))


def concat_csv(paths: Iterable[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in paths:
        for row in read_csv(path):
            merged: dict[str, object] = {"source_path": str(path)}
            merged.update(row)
            rows.append(merged)
    return rows


def ledger_rows(packet: Path, summaries: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for idx, variant in enumerate(VARIANTS):
        summary = summaries.get(variant, {})
        run_config = read_config_env(variant_dir(packet, variant) / "configs" / "run_config.env")
        if not summary:
            rows.append(
                {
                    "run_id": f"myops_array_{idx}",
                    "variant": variant,
                    "job_id": run_config.get("job_id", "AWAITING_RUNTIME_SUMMARY"),
                    "is_training_run": "true",
                    "is_eval_only": "false",
                    "start_time": "AWAITING_RUNTIME_SUMMARY",
                    "end_time": "AWAITING_RUNTIME_SUMMARY",
                    "train_loop_seconds": "AWAITING_RUNTIME_AGGREGATION",
                    "optimizer_steps": "AWAITING_RUNTIME_AGGREGATION",
                    "validation_event_count": "AWAITING_RUNTIME_AGGREGATION",
                    "checkpoint_in": "none",
                    "checkpoint_out": str(variant_dir(packet, variant) / "checkpoints/fold_0/propref_config"),
                    "included_in_8h_budget": "false_until_completed_and_aggregated",
                    "exclusion_reason": f"{MONITOR_STATUS}: summary.json missing or job still running/pending",
                }
            )
            continue
        seconds = as_float(summary.get("train_loop_seconds"))
        steps = as_int(summary.get("actual_optimizer_steps"))
        val_count = as_int(summary.get("validation_event_count"))
        include = seconds > 0 and steps > 0 and val_count > 0
        rows.append(
            {
                "run_id": f"myops_array_{idx}",
                "variant": variant,
                "job_id": run_config.get("job_id", "EVIDENCE_NOT_FOUND"),
                "is_training_run": "true",
                "is_eval_only": "false",
                "start_time": "SEE_SLURM_ACCOUNTING",
                "end_time": "SEE_SLURM_ACCOUNTING",
                "train_loop_seconds": seconds,
                "optimizer_steps": steps,
                "validation_event_count": val_count,
                "checkpoint_in": "none",
                "checkpoint_out": summary.get("checkpoint_best", "EVIDENCE_NOT_FOUND"),
                "included_in_8h_budget": str(include).lower(),
                "exclusion_reason": "" if include else "completed summary lacks train seconds/steps/validation events",
            }
        )
    return rows


def read_config_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def total_included_seconds(rows: list[dict[str, object]]) -> float:
    total = 0.0
    for row in rows:
        if str(row.get("included_in_8h_budget", "")).lower() == "true":
            total += as_float(row.get("train_loop_seconds"))
    return total


def derive_status(packet: Path, summaries: dict[str, dict[str, object]], ledger: list[dict[str, object]]) -> tuple[str, list[str]]:
    issues: list[str] = []
    missing = [variant for variant in VARIANTS if not summaries.get(variant)]
    if missing:
        issues.append(f"missing_runtime_summary={','.join(missing)}")
        return MONITOR_STATUS, issues
    total_seconds = total_included_seconds(ledger)
    if total_seconds < 28800.0:
        issues.append(f"included_train_loop_seconds={total_seconds:.1f}<28800")
        return "M8_NEEDS_EVIDENCE_UNDERTRAINED", issues
    if not any(as_float(row.get("train_loop_seconds")) >= 7200.0 or as_int(row.get("optimizer_steps")) >= 6000 for row in ledger):
        issues.append("no_primary_candidate_meets_long_candidate_gate")
        return "M8_NEEDS_EVIDENCE_UNDERTRAINED", issues
    for row in ledger:
        if as_float(row.get("train_loop_seconds")) < 900.0 or as_int(row.get("validation_event_count")) < 3:
            issues.append(f"formal_run_too_small={row.get('variant')}")
    if issues:
        return "M8_NEEDS_EVIDENCE_UNDERTRAINED", issues
    cine_matrix = packet / "m8_registration_same_subset_matrix.csv"
    if not cine_matrix.is_file() or not read_csv(cine_matrix):
        issues.append("cine_mature_registration_evidence_missing")
        return "M8_NEEDS_EVIDENCE_CINE_REGISTRATION", issues
    contribution = read_csv(packet / "m8_srr_contribution_by_case.csv")
    if not contribution or any(row.get("anchor_delta_rate") in {"", "EVIDENCE_NOT_FOUND", "EVIDENCE_NOT_EXPORTED_PER_CASE"} for row in contribution[:20]):
        issues.append("per_case_contribution_anchor_delta_missing")
        return "M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE", issues
    temporal = read_csv(packet / "m8_temporal_dictionary_evidence.csv")
    if temporal and any("USABLE" in str(row).upper() for row in read_csv(cine_matrix)) and not any(row.get("status") not in {"", MONITOR_STATUS} for row in temporal):
        issues.append("usable_registration_without_temporal_dictionary")
        return "M8_NEEDS_EVIDENCE_CINE_REGISTRATION", issues
    return "M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE", ["ready gate intentionally requires final reviewer-grade metric/contribution audit"]


def summarize_training_curves(packet: Path) -> None:
    write_csv(
        packet / "m8_training_curves.csv",
        concat_csv(variant_dir(packet, variant) / "training_log.csv" for variant in VARIANTS),
    )
    write_csv(
        packet / "m8_validation_events.csv",
        concat_csv(variant_dir(packet, variant) / "validation_events.csv" for variant in VARIANTS),
    )
    write_csv(
        packet / "m8_loss_component_gradient_sanity.csv",
        concat_csv(variant_dir(packet, variant) / "loss_component_gradient_sanity.csv" for variant in VARIANTS),
    )
    loss_rows = []
    for row in concat_csv(variant_dir(packet, variant) / "training_log.csv" for variant in VARIANTS):
        if row.get("event") == "validation":
            continue
        loss_rows.append(row)
    write_csv(packet / "m8_loss_component_by_step.csv", loss_rows)
    arbitration_fields = {
        "variant",
        "step",
        "stage",
        "baseline_gate_mean",
        "baseline_residual_abs_mean",
        "branch_correction_open_rate",
        "proposal_weight_mean",
        "refiner_weight_mean",
        "final_logit_delta_roi_abs_mean",
        "source_path",
    }
    write_csv(
        packet / "m8_arbitration_opening_diagnostics.csv",
        [{key: row.get(key, "") for key in arbitration_fields} for row in loss_rows],
    )


def summarize_batch_and_memory(packet: Path) -> None:
    rows = []
    for row in concat_csv(variant_dir(packet, variant) / "batch_composition.csv" for variant in VARIANTS):
        rows.append(
            {
                "step": row.get("step", ""),
                "variant": row.get("variant", row.get("source_path", "")),
                "case_id": row.get("case_id", ""),
                "center": row.get("center", ""),
                "modality_group": row.get("modality_group", ""),
                "t2_present": row.get("t2_present", ""),
                "c0_present": row.get("c0_present", ""),
                "scar_gt_positive": row.get("scar_gt_positive", ""),
                "edema_gt_positive": row.get("edema_gt_positive", ""),
                "no_t2_safety_case": str(row.get("t2_present", "")).lower() == "false",
                "remote_fp_positive": row.get("anchor_remote_fp_scar", "") or row.get("anchor_remote_fp_edema", ""),
                "small_lesion": "",
                "large_lesion": "",
                "selected_reason": row.get("split_role", ""),
                "loss_terms_active": row.get("stage", ""),
                "source_path": row.get("source_path", ""),
            }
        )
    write_csv(packet / "m8_batch_composition.csv", rows)
    write_csv(packet / "m8_hard_negative_memory_summary.csv", concat_csv(variant_dir(packet, variant) / "hardneg_memory.csv" for variant in VARIANTS))


def summarize_prototypes(packet: Path) -> None:
    summaries = {variant: read_json(variant_dir(packet, variant) / "prototype_bank_summary.json") for variant in VARIANTS}
    write_text(packet / "m8_prototype_bank_summary.json", json.dumps({"variants": summaries}, indent=2, sort_keys=True) + "\n")
    write_csv(
        packet / "m8_prototype_margin_by_case.csv",
        concat_csv(variant_dir(packet, variant) / "prototype_update_sanity_formal.csv" for variant in VARIANTS)
        or concat_csv(variant_dir(packet, variant) / "prototype_update_sanity.csv" for variant in VARIANTS),
    )


def summarize_eval_outputs(packet: Path) -> None:
    component_rows = concat_csv(variant_dir(packet, variant) / "component_hd_by_case_checkpoint_best.csv" for variant in VARIANTS)
    subgroup_rows = concat_csv(variant_dir(packet, variant) / "subgroup_metrics_checkpoint_best.csv" for variant in VARIANTS)
    proposal_rows = concat_csv(variant_dir(packet, variant) / "proposal_pr_sweep_checkpoint_best.csv" for variant in VARIANTS)
    roi_rows = concat_csv(variant_dir(packet, variant) / "roi_coverage_checkpoint_best.csv" for variant in VARIANTS)
    sanity_rows = concat_csv(variant_dir(packet, variant) / "prediction_sanity_checkpoint_best.csv" for variant in VARIANTS)
    write_csv(packet / "m8_same_split_help_harm.csv", component_rows)
    write_csv(packet / "m8_hard_subgroup_metrics.csv", subgroup_rows)
    write_csv(packet / "m8_component_remote_fp_hd95_report.csv", component_rows)
    write_csv(packet / "m8_proposal_refiner_recall_precision.csv", proposal_rows + roi_rows)
    contribution_rows = []
    for row in component_rows:
        contribution_rows.append(
            {
                "variant": row.get("variant", ""),
                "checkpoint": "checkpoint_best",
                "decode_mode": str(row.get("variant", "")).split("__")[-1] if "__" in str(row.get("variant", "")) else "",
                "case_id": row.get("case_id", ""),
                "center": row.get("center", ""),
                "modality_group": row.get("modality_group", ""),
                "t2_present": row.get("t2_present", ""),
                "class_name": row.get("metric_name", ""),
                "anchor_delta_rate": "EVIDENCE_NOT_EXPORTED_PER_CASE",
                "final_delta_rate": "EVIDENCE_NOT_EXPORTED_PER_CASE",
                "correction_gate_open_rate": "EVIDENCE_NOT_EXPORTED_PER_CASE",
                "srr_weight_mean": "EVIDENCE_NOT_EXPORTED_PER_CASE",
                "proposal_weight_mean": "EVIDENCE_NOT_EXPORTED_PER_CASE",
                "refiner_weight_mean": "EVIDENCE_NOT_EXPORTED_PER_CASE",
                "fallback_weight_mean": "EVIDENCE_NOT_EXPORTED_PER_CASE",
                "final_logit_delta_abs_mean": "EVIDENCE_NOT_EXPORTED_PER_CASE",
                "roi_delta_abs_mean": "",
                "proposal_recall_proxy": "",
                "proposal_precision_proxy": "",
                "refiner_delta_magnitude": "",
                "no_t2_edema_voxels": next((s.get("no_t2_edema_voxels", "") for s in sanity_rows if s.get("case_id") == row.get("case_id")), ""),
                "dice_delta": "EVIDENCE_NOT_COMPUTED_VS_ANCHOR",
                "hd95_delta": "EVIDENCE_NOT_COMPUTED_VS_ANCHOR",
                "remote_fp_delta": "EVIDENCE_NOT_COMPUTED_VS_ANCHOR",
                "component_count_delta": "EVIDENCE_NOT_COMPUTED_VS_ANCHOR",
                "source_prediction_path": "runtime prediction directories",
            }
        )
    write_csv(packet / "m8_srr_contribution_by_case.csv", contribution_rows)


def write_decision_docs(packet: Path, status: str, issues: list[str], summaries: dict[str, dict[str, object]], ledger: list[dict[str, object]]) -> None:
    now = datetime.now(UTC).isoformat()
    total_seconds = total_included_seconds(ledger)
    issue_text = "\n".join(f"- `{issue}`" for issue in issues) or "- none"
    write_text(
        packet / "result.md",
        "\n".join(
            [
                "# M8 Executor Result",
                "",
                f"status: `{status}`",
                "",
                f"updated_at_utc: `{now}`",
                f"git_head: `{git_head()}`",
                f"included_myops_train_loop_seconds: `{total_seconds:.3f}`",
                "",
                "This packet was aggregated from local runtime evidence where available. It does not claim validation packaging/upload, hosted metrics, challenge readiness, scientific stop, fold expansion, or M9.",
                "",
                "## Blocking Issues",
                issue_text,
                "",
                "## Runtime Summary Status",
                *[
                    f"- `{variant}`: {'summary.json present' if summaries.get(variant) else 'summary.json missing'}"
                    for variant in VARIANTS
                ],
            ]
        )
        + "\n",
    )
    write_text(
        packet / "completion_check.md",
        f"# M8 Completion Check\n\nstatus: `{status}`\n\nincluded_myops_train_loop_seconds: `{total_seconds:.3f}`\n\nblocking_issues:\n{issue_text}\n",
    )
    review_text = (
        "# M8 Review Request\n\n"
        "status: `NO_REVIEW_REQUESTED_MONITOR_ONLY`\n\n"
        "Do not review this as a normal ready packet until completion_check.md has a reviewer-ready state and contains no pending/running/awaiting-runtime evidence.\n"
    )
    if status not in {MONITOR_STATUS}:
        review_text = (
            "# M8 Review Request\n\n"
            "status: `DO_NOT_REVIEW_UNTIL_BLOCKERS_RESOLVED`\n\n"
            "The packet has post-job aggregation where available, but the blocking issues in completion_check.md still prevent normal review.\n"
        )
    write_text(packet / "review_request.md", review_text)


def write_manifest(packet: Path) -> None:
    files = sorted(path.name for path in packet.iterdir() if path.is_file())
    lines = [
        "# M8 Manifest",
        "",
        f"task_key: `{TASK_KEY}`",
        f"updated_at_utc: `{datetime.now(UTC).isoformat()}`",
        "",
        "## Files",
        *[f"- `{name}`" for name in files],
        "",
        "## Excluded",
        "- `runtime/` checkpoints, NIfTI predictions, and large logs are intentionally not tracked.",
    ]
    write_text(packet / "MANIFEST.md", "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    args = parser.parse_args()
    packet = Path(args.packet)
    if not packet.is_absolute():
        packet = REPO_ROOT / packet
    summaries = {variant: existing_summary(packet, variant) for variant in VARIANTS}
    ledger = ledger_rows(packet, summaries)
    write_csv(
        packet / "m8_training_budget_ledger.csv",
        ledger,
        [
            "run_id",
            "variant",
            "job_id",
            "is_training_run",
            "is_eval_only",
            "start_time",
            "end_time",
            "train_loop_seconds",
            "optimizer_steps",
            "validation_event_count",
            "checkpoint_in",
            "checkpoint_out",
            "included_in_8h_budget",
            "exclusion_reason",
        ],
    )
    summarize_training_curves(packet)
    summarize_batch_and_memory(packet)
    summarize_prototypes(packet)
    summarize_eval_outputs(packet)
    status, issues = derive_status(packet, summaries, ledger)
    write_decision_docs(packet, status, issues, summaries, ledger)
    write_manifest(packet)
    print(json.dumps({"packet": str(packet), "status": status, "issues": issues}, indent=2))


if __name__ == "__main__":
    main()
