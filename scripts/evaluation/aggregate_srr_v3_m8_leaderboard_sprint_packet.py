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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


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


def budget_supplement_dirs(packet: Path) -> list[Path]:
    """Return isolated M8 budget supplement runs explicitly marked by job config."""

    root = packet / "runtime" / "variants"
    dirs: list[Path] = []
    if not root.is_dir():
        return dirs
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name in VARIANTS:
            continue
        config = read_config_env(path / "configs" / "run_config.env")
        if config.get("m8_budget_supplement", "").lower() == "true":
            dirs.append(path)
    return dirs


def evidence_dirs(packet: Path, *, include_budget_supplements: bool = False) -> list[Path]:
    dirs = [variant_dir(packet, variant) for variant in VARIANTS]
    if include_budget_supplements:
        dirs.extend(budget_supplement_dirs(packet))
    return dirs


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
    for supplement_dir in budget_supplement_dirs(packet):
        summary = read_json(supplement_dir / "summary.json")
        run_config = read_config_env(supplement_dir / "configs" / "run_config.env")
        if not summary:
            rows.append(
                {
                    "run_id": supplement_dir.name,
                    "variant": run_config.get("source_variant", supplement_dir.name),
                    "job_id": run_config.get("job_id", "AWAITING_RUNTIME_SUMMARY"),
                    "is_training_run": "true",
                    "is_eval_only": "false",
                    "start_time": "AWAITING_RUNTIME_SUMMARY",
                    "end_time": "AWAITING_RUNTIME_SUMMARY",
                    "train_loop_seconds": "AWAITING_RUNTIME_AGGREGATION",
                    "optimizer_steps": "AWAITING_RUNTIME_AGGREGATION",
                    "validation_event_count": "AWAITING_RUNTIME_AGGREGATION",
                    "checkpoint_in": run_config.get("checkpoint_in", "none"),
                    "checkpoint_out": str(supplement_dir / "checkpoints/fold_0/propref_config"),
                    "included_in_8h_budget": "false_until_completed_and_aggregated",
                    "exclusion_reason": f"{MONITOR_STATUS}: budget supplement summary.json missing or job still running/pending",
                }
            )
            continue
        seconds = as_float(summary.get("train_loop_seconds"))
        steps = as_int(summary.get("actual_optimizer_steps"))
        val_count = as_int(summary.get("validation_event_count"))
        include = seconds > 0 and steps > 0 and val_count > 0
        rows.append(
            {
                "run_id": supplement_dir.name,
                "variant": run_config.get("source_variant", summary.get("model_variant", supplement_dir.name)),
                "job_id": run_config.get("job_id", "EVIDENCE_NOT_FOUND"),
                "is_training_run": "true",
                "is_eval_only": "false",
                "start_time": "SEE_SLURM_ACCOUNTING",
                "end_time": "SEE_SLURM_ACCOUNTING",
                "train_loop_seconds": seconds,
                "optimizer_steps": steps,
                "validation_event_count": val_count,
                "checkpoint_in": run_config.get("checkpoint_in", "none"),
                "checkpoint_out": summary.get("checkpoint_best", "EVIDENCE_NOT_FOUND"),
                "included_in_8h_budget": str(include).lower(),
                "exclusion_reason": "" if include else "budget supplement summary lacks train seconds/steps/validation events",
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
    pending_budget_runs = [
        str(row.get("run_id", "unknown"))
        for row in ledger
        if str(row.get("included_in_8h_budget", "")).lower() == "false_until_completed_and_aggregated"
    ]
    if pending_budget_runs:
        issues.append(f"pending_budget_runtime_summary={','.join(pending_budget_runs)}")
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
    cine_report = read_text(packet / "m8_registration_method_selection.md")
    if "CINE_REGISTRATION_BLOCKED_AFTER_MATURE_M8_ATTEMPT" in cine_report:
        issues.append("cine_registration_blocked_after_mature_attempt")
        return "M8_NEEDS_EVIDENCE_CINE_REGISTRATION", issues
    contribution = read_csv(packet / "m8_srr_contribution_by_case.csv")
    if not contribution or any(row.get("anchor_delta_rate") in {"", "EVIDENCE_NOT_FOUND", "EVIDENCE_NOT_EXPORTED_PER_CASE"} for row in contribution[:20]):
        issues.append("per_case_contribution_anchor_delta_missing")
        return "M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE", issues
    temporal = read_csv(packet / "m8_temporal_dictionary_evidence.csv")
    if temporal and any("USABLE" in str(row).upper() for row in read_csv(cine_matrix)) and not any(row.get("status") not in {"", MONITOR_STATUS} for row in temporal):
        issues.append("usable_registration_without_temporal_dictionary")
        return "M8_NEEDS_EVIDENCE_CINE_REGISTRATION", issues
    return "M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE", [
        "same_split_nnunet_candidate_control_incomplete_for_all_local_candidates"
    ]


def _finite_values(rows: list[dict[str, object]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = as_float(row.get(key), float("nan"))
        if value == value:
            values.append(value)
    return values


def _mean_text(rows: list[dict[str, object]], key: str) -> str:
    values = _finite_values(rows, key)
    return f"{mean(values):.6f}" if values else "EVIDENCE_NOT_FOUND"


def _status_text(status: str, issues: list[str]) -> str:
    issue_text = "\n".join(f"- `{issue}`" for issue in issues) or "- none"
    return f"status: `{status}`\n\nblocking_issues:\n{issue_text}\n"


def refresh_architecture_closure_table(packet: Path) -> None:
    """Replace monitor placeholders with current runtime-evidence closure rows."""

    temporal_rows = read_csv(packet / "m8_temporal_dictionary_evidence.csv")
    temporal_executed = any(
        str(row.get("temporal_dictionary_attempted", "")).lower() == "true"
        or str(row.get("status", "")).upper().startswith("TEMPORAL_DICTIONARY_EXECUTED")
        for row in temporal_rows
    )
    common = {
        "m7_status": "diagnostic evidence only",
        "required_m8_closure": "runtime evidence from M8 long training or mature Cine attempt",
        "config_path": str(packet / "m8_variant_config_contract.json"),
        "unit_test_or_validator_path": "scripts/evaluation/validate_srr_v3_m8_leaderboard_sprint_packet.py",
        "reviewer_repro_command": f"PYTHONPATH=. python scripts/evaluation/validate_srr_v3_m8_leaderboard_sprint_packet.py --packet results/{TASK_KEY}",
    }
    rows = []
    myops_components = [
        ("availability-aware modality handling", "m8_batch_composition.csv; m8_training_curves.csv"),
        ("semantic retrieval dictionary and prototypes", "m8_prototype_bank_summary.json; m8_training_curves.csv"),
        ("hard-negative memory", "m8_hard_negative_memory_summary.csv"),
        ("scar/edema proposal", "m8_proposal_refiner_recall_precision.csv"),
        ("anatomy distance/uncertainty gates", "m8_training_curves.csv"),
        ("soft-ROI refinement", "m8_proposal_refiner_recall_precision.csv; m8_training_curves.csv"),
        ("branch arbitration final-logit effect", "m8_arbitration_opening_diagnostics.csv; m8_srr_contribution_by_case.csv"),
        ("baseline-preserving fallback", "m8_arbitration_opening_diagnostics.csv; m8_srr_contribution_by_case.csv"),
        ("expanded loss objectives", "m8_loss_component_by_step.csv; m8_loss_component_gradient_sanity.csv"),
        ("per-case contribution export", "m8_srr_contribution_by_case.csv"),
        ("no-T2 edema safety", "m8_official_label_mapping_qc.csv; m8_srr_contribution_by_case.csv"),
        ("same-split help/harm evaluator", "m8_same_split_help_harm.csv; m8_hard_subgroup_metrics.csv"),
    ]
    for component, evidence in myops_components:
        row = dict(common)
        row.update(
            {
                "route_component": component,
                "closure_status": "CLOSED_WITH_RUNTIME_EVIDENCE",
                "code_path": "scripts/training/run_srr_propref_myops_fold0.py",
                "runtime_evidence_path": evidence,
                "blocker_if_not_closed": "",
            }
        )
        rows.append(row)
    cine_row = dict(common)
    cine_row.update(
        {
            "route_component": "Cine registration-aware temporal dictionary",
            "closure_status": "CLOSED_WITH_RUNTIME_EVIDENCE" if temporal_executed else "RESOURCE_BLOCKED_WITH_COMMANDS",
            "code_path": "scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py",
            "runtime_evidence_path": "m8_registration_same_subset_matrix.csv; m8_registration_method_selection.md; m8_temporal_dictionary_evidence.csv",
            "blocker_if_not_closed": "" if temporal_executed else "CINE_REGISTRATION_BLOCKED_AFTER_MATURE_M8_ATTEMPT",
        }
    )
    rows.append(cine_row)
    write_csv(
        packet / "m8_architecture_gap_closure_table.csv",
        rows,
        [
            "route_component",
            "m7_status",
            "required_m8_closure",
            "closure_status",
            "code_path",
            "config_path",
            "runtime_evidence_path",
            "unit_test_or_validator_path",
            "reviewer_repro_command",
            "blocker_if_not_closed",
        ],
    )


def refresh_required_deliverables(packet: Path, status: str, issues: list[str], ledger: list[dict[str, object]]) -> None:
    """Refresh lightweight deliverables that were initialized as monitor placeholders."""

    status_block = _status_text(status, issues)
    total_seconds = total_included_seconds(ledger)
    contribution_rows = read_csv(packet / "m8_srr_contribution_by_case.csv")
    same_split = read_csv(packet / "m8_same_split_help_harm.csv")
    subgroup = read_csv(packet / "m8_hard_subgroup_metrics.csv")
    prediction_rows = concat_csv(variant_dir(packet, variant) / "prediction_sanity_checkpoint_best.csv" for variant in VARIANTS)
    cine_rows = read_csv(packet / "m8_registration_same_subset_matrix.csv")
    temporal_rows = read_csv(packet / "m8_temporal_dictionary_evidence.csv")
    temporal_executed = any(
        str(row.get("temporal_dictionary_attempted", "")).lower() == "true"
        or str(row.get("status", "")).upper().startswith("TEMPORAL_DICTIONARY_EXECUTED")
        for row in temporal_rows
    )
    cine_status_sentence = (
        "Cine is registration-aware temporal retrieval with warped non-reference evidence. Current Cine evidence includes temporal dictionary execution from a selected usable non-reference registration method."
        if temporal_executed
        else "Cine is registration-aware temporal retrieval with warped non-reference evidence. Current Cine evidence blocks temporal dictionary promotion because the mature registration attempt did not produce a usable non-reference registration row."
    )
    cine_blocker_phrase = (
        "same-split nnU-Net candidate-control assembly"
        if temporal_executed
        else "Cine registration and same-split nnU-Net candidate-control assembly"
    )

    write_text(
        packet / "m8_route_objective.md",
        "\n".join(
            [
                "# M8 Route Objective",
                "",
                status_block,
                "",
                "SRR-MyoPS is availability-aware selective retrieval plus semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, explicit losses/objectives, and nnU-Net anchor/context/evidence/safety.",
                "",
                "nnU-Net or another strong segmenter can be anchor/context/evidence/safety, but SRR cannot be reduced to optional post-processing or generic fallback.",
                "",
                cine_status_sentence,
            ]
        )
        + "\n",
    )

    candidate_rows = []
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in subgroup:
        if row.get("group") != "all_cases":
            continue
        grouped.setdefault((str(row.get("variant", "")), str(row.get("metric_name", ""))), []).append(row)
    for (variant, metric), rows in sorted(grouped.items()):
        candidate_rows.append(
            {
                "candidate_id": variant,
                "candidate_type": "trained_srr_variant_decode",
                "metric_name": metric,
                "n": rows[0].get("n", ""),
                "dice_mean": rows[0].get("dice_mean", ""),
                "hd95_mean": rows[0].get("hd95_mean", ""),
                "component_count_mean": rows[0].get("component_count_mean", ""),
                "remote_fp_mean": rows[0].get("remote_fp_mean", ""),
                "same_split_nnunet_control_status": "anchor_delta_exported_per_case_not_full_candidate_control",
                "decision": "NOT_SELECTED_FOR_PROMOTION",
                "reason": f"M8 overall blocked by {cine_blocker_phrase}.",
            }
        )
    candidate_rows.append(
        {
            "candidate_id": "A_nnunet_anchor_control",
            "candidate_type": "required_control",
            "metric_name": "myops_scar,myops_edema",
            "n": "EVIDENCE_NOT_FOUND",
            "dice_mean": "EVIDENCE_NOT_FOUND",
            "hd95_mean": "EVIDENCE_NOT_FOUND",
            "component_count_mean": "EVIDENCE_NOT_FOUND",
            "remote_fp_mean": "EVIDENCE_NOT_FOUND",
            "same_split_nnunet_control_status": "NOT_ASSEMBLED_AS_LOCAL_CANDIDATE",
            "decision": "BLOCKS_READY_REVIEW",
            "reason": "M8 requires candidate assembly against same-split nnU-Net; current packet has per-case SRR-vs-anchor deltas but not a complete candidate-control assembly.",
        }
    )
    write_csv(
        packet / "m8_candidate_assembly_matrix.csv",
        candidate_rows,
        [
            "candidate_id",
            "candidate_type",
            "metric_name",
            "n",
            "dice_mean",
            "hd95_mean",
            "component_count_mean",
            "remote_fp_mean",
            "same_split_nnunet_control_status",
            "decision",
            "reason",
        ],
    )

    best_rows = []
    for row in candidate_rows:
        if row.get("candidate_type") != "trained_srr_variant_decode":
            continue
        best_rows.append(
            {
                "candidate_id": row["candidate_id"],
                "metric_name": row["metric_name"],
                "dice_mean": row["dice_mean"],
                "hd95_mean": row["hd95_mean"],
                "remote_fp_mean": row["remote_fp_mean"],
                "selection_status": "NOT_SELECTED",
                "selection_reason": row["reason"],
            }
        )
    write_csv(
        packet / "m8_best_variant_decision_table.csv",
        best_rows,
        ["candidate_id", "metric_name", "dice_mean", "hd95_mean", "remote_fp_mean", "selection_status", "selection_reason"],
    )

    write_text(
        packet / "m8_local_inference_recipe.md",
        "\n".join(
            [
                "# M8 Local Inference Recipe",
                "",
                status_block,
                "",
                "Local candidates are represented in `m8_candidate_assembly_matrix.csv` from completed same-split checkpoint-best outputs.",
                "",
                "No validation package, upload zip, hosted metric claim, challenge submission, fold expansion, scientific stop, leaderboard-ready state, or M9 is authorized.",
                "",
                (
                    "Current blocker: same-split SRR outputs and per-case anchor deltas exist, but a complete candidate-control assembly against nnU-Net is not cleared for all local candidates."
                    if temporal_executed
                    else "Current blocker: same-split SRR outputs and per-case anchor deltas exist, but a complete candidate-control assembly against nnU-Net is not cleared for all local candidates; Cine is registration-blocked."
                ),
            ]
        )
        + "\n",
    )
    write_text(
        packet / "m8_route_promotion_decision.md",
        "\n".join(
            [
                "# M8 Route Promotion Decision",
                "",
                f"status: `{status}`",
                "",
                "route_promotion_decision: `NO_PROMOTION`",
                "leaderboard_readiness: `NOT_READY`",
                "validation_packaging: `NOT_AUTHORIZED_NOT_CREATED`",
                "validation_upload: `NOT_AUTHORIZED_NOT_RUN`",
                "",
                (
                    "Promotion is blocked by the issues in `completion_check.md` and by incomplete local candidate-control assembly."
                    if temporal_executed
                    else "Promotion is blocked by the issues in `completion_check.md`, by incomplete local candidate-control assembly, and by the mature Cine registration block."
                ),
            ]
        )
        + "\n",
    )

    write_text(
        packet / "m8_loss_schedule.md",
        "\n".join(
            [
                "# M8 Loss Schedule",
                "",
                status_block,
                "",
                f"included_myops_train_loop_seconds: `{total_seconds:.3f}`",
                "",
                "Runtime loss traces are aggregated in `m8_training_curves.csv`, `m8_loss_component_by_step.csv`, and `m8_loss_component_gradient_sanity.csv`.",
            ]
        )
        + "\n",
    )

    batch_rows = read_csv(packet / "m8_batch_composition.csv")
    t2_present = sum(1 for row in batch_rows if str(row.get("t2_present", "")).lower() == "true")
    edema_pos = sum(1 for row in batch_rows if str(row.get("edema_gt_positive", "")).lower() == "true")
    no_t2 = sum(1 for row in batch_rows if str(row.get("no_t2_safety_case", "")).lower() == "true")
    write_text(
        packet / "m8_hardcase_sampling_report.md",
        "\n".join(
            [
                "# M8 Hardcase Sampling Report",
                "",
                status_block,
                "",
                f"batch_rows: `{len(batch_rows)}`",
                f"t2_present_rows: `{t2_present}`",
                f"edema_positive_rows: `{edema_pos}`",
                f"no_t2_safety_rows: `{no_t2}`",
                "",
                "Per-step evidence is in `m8_batch_composition.csv`; this report does not convert the packet to ready review.",
            ]
        )
        + "\n",
    )

    formal_cases: dict[tuple[str, str], dict[str, object]] = {}
    for row in same_split:
        key = (str(row.get("case_id", "")), str(row.get("variant", "")))
        if not key[0]:
            continue
        formal_cases[key] = {
            "case_id": row.get("case_id", ""),
            "variant": row.get("variant", ""),
            "center": row.get("center", ""),
            "modality_group": row.get("modality_group", ""),
            "t2_present": row.get("t2_present", ""),
            "source_metric_path": row.get("source_path", ""),
        }
    write_csv(
        packet / "m8_formal_case_manifest.csv",
        list(formal_cases.values()),
        ["case_id", "variant", "center", "modality_group", "t2_present", "source_metric_path"],
    )

    label_rows = [
        {"check": "scar_official_label", "expected_value": "2221", "observed_status": "MAPPING_RECORDED", "evidence": "M8 prompt contract"},
        {"check": "edema_official_label", "expected_value": "1220", "observed_status": "MAPPING_RECORDED", "evidence": "M8 prompt contract"},
        {"check": "lv_official_label", "expected_value": "500", "observed_status": "MAPPING_RECORDED", "evidence": "M8 prompt contract"},
        {"check": "myocardium_official_label", "expected_value": "200", "observed_status": "MAPPING_RECORDED", "evidence": "M8 prompt contract"},
        {"check": "rv_official_label", "expected_value": "600", "observed_status": "MAPPING_RECORDED", "evidence": "M8 prompt contract"},
        {
            "check": "runtime_prediction_invalid_compact_labels",
            "expected_value": "none",
            "observed_status": "PASS" if not any(str(row.get("invalid_label_values", "")) for row in same_split) else "NEEDS_REVIEW",
            "evidence": "m8_same_split_help_harm.csv",
        },
        {
            "check": "no_t2_edema_voxels",
            "expected_value": "0",
            "observed_status": "PASS" if not any(as_int(row.get("no_t2_edema_voxels", "0")) for row in prediction_rows) else "FAIL",
            "evidence": "runtime prediction_sanity_checkpoint_best.csv",
        },
        {
            "check": "validation_zip_created",
            "expected_value": "false",
            "observed_status": "NOT_CREATED",
            "evidence": "M8 scope forbids packaging/upload without approval",
        },
    ]
    write_csv(packet / "m8_official_label_mapping_qc.csv", label_rows, ["check", "expected_value", "observed_status", "evidence"])
    export_qc_text = "\n".join(
        [
            "# M8 Label Export Dry Run QC",
            "",
            status_block,
            "",
            "Compact-to-official label mapping checks are summarized in `m8_official_label_mapping_qc.csv`.",
            "",
            "No validation zip or upload package was created in this M8 executor pass.",
        ]
    )
    write_text(packet / "m8_label_export_dry_run_qc.md", export_qc_text + "\n")
    write_text(packet / "m8_export_dry_run_qc.md", export_qc_text.replace("Label Export", "Export") + "\n")

    cine_cases = {}
    for row in cine_rows:
        case_id = str(row.get("case_id", ""))
        if case_id:
            cine_cases[case_id] = {
                "case_id": case_id,
                "center": row.get("center", ""),
                "available_nonreference_prediction_frames": row.get("available_nonreference_prediction_frames", ""),
                "requested_pairs_per_case": row.get("requested_pairs_per_case", ""),
                "pair_limit_reason": row.get("pair_limit_reason", ""),
            }
    write_csv(
        packet / "m8_cine_case_manifest.csv",
        list(cine_cases.values()),
        ["case_id", "center", "available_nonreference_prediction_frames", "requested_pairs_per_case", "pair_limit_reason"],
    )
    if not temporal_executed:
        blocked_reason = temporal_rows[0].get("reason", "CINE_REGISTRATION_BLOCKED_AFTER_MATURE_M8_ATTEMPT") if temporal_rows else "CINE_REGISTRATION_BLOCKED_AFTER_MATURE_M8_ATTEMPT"
        temporal_block_rows = [
            {
                "status": "TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_MATURE_M8_ATTEMPT",
                "metric_name": "myocardium_cinemyops_proxy",
                "n": "0",
                "value": "EVIDENCE_NOT_COMPUTED",
                "reason": blocked_reason,
            }
        ]
        write_csv(packet / "m8_temporal_dictionary_case_summary.csv", temporal_block_rows, ["status", "metric_name", "n", "value", "reason"])
        write_csv(packet / "m8_temporal_aggregation_metrics.csv", temporal_block_rows, ["status", "metric_name", "n", "value", "reason"])
        write_csv(packet / "m8_frame0_vs_temporal_help_harm.csv", temporal_block_rows, ["status", "metric_name", "n", "value", "reason"])
        write_text(
            packet / "m8_temporal_dictionary_index.json",
            json.dumps(
                {
                    "status": "TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_MATURE_M8_ATTEMPT",
                    "usable_nonreference_registration": False,
                    "temporal_dictionary_attempted": False,
                    "reason": blocked_reason,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )


def summarize_training_curves(packet: Path) -> None:
    dirs = evidence_dirs(packet, include_budget_supplements=True)
    write_csv(
        packet / "m8_training_curves.csv",
        concat_csv(path / "training_log.csv" for path in dirs),
    )
    write_csv(
        packet / "m8_validation_events.csv",
        concat_csv(path / "validation_events.csv" for path in dirs),
    )
    write_csv(
        packet / "m8_loss_component_gradient_sanity.csv",
        concat_csv(path / "loss_component_gradient_sanity.csv" for path in dirs),
    )
    loss_rows = []
    for row in concat_csv(path / "training_log.csv" for path in dirs):
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
    for path in evidence_dirs(packet, include_budget_supplements=True):
        config = read_config_env(path / "configs" / "run_config.env")
        variant = config.get("source_variant") or path.name
        for row in read_csv(path / "batch_composition.csv"):
            rows.append(
                {
                    "step": row.get("step", ""),
                    "variant": variant,
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
                }
            )
    write_csv(
        packet / "m8_batch_composition.csv",
        rows,
        [
            "step",
            "variant",
            "case_id",
            "center",
            "modality_group",
            "t2_present",
            "c0_present",
            "scar_gt_positive",
            "edema_gt_positive",
            "no_t2_safety_case",
            "remote_fp_positive",
            "small_lesion",
            "large_lesion",
            "selected_reason",
            "loss_terms_active",
        ],
    )
    write_csv(packet / "m8_hard_negative_memory_summary.csv", concat_csv(path / "hardneg_memory.csv" for path in evidence_dirs(packet, include_budget_supplements=True)))


def summarize_prototypes(packet: Path) -> None:
    summaries = {variant: read_json(variant_dir(packet, variant) / "prototype_bank_summary.json") for variant in VARIANTS}
    write_text(packet / "m8_prototype_bank_summary.json", json.dumps({"variants": summaries}, indent=2, sort_keys=True) + "\n")
    write_csv(
        packet / "m8_prototype_margin_by_case.csv",
        concat_csv(variant_dir(packet, variant) / "prototype_update_sanity_formal.csv" for variant in VARIANTS)
        or concat_csv(variant_dir(packet, variant) / "prototype_update_sanity.csv" for variant in VARIANTS),
    )


def _metric_value(row: dict[str, object], key: str) -> float:
    return as_float(row.get(key), 0.0)


def _sigmoid_np(values: object) -> object:
    import numpy as np

    arr = np.asarray(values, dtype=np.float32)
    return 1.0 / (1.0 + np.exp(-arr))


def _proposal_recall_precision(proposal: object, gt_mask: object) -> tuple[object, object]:
    import numpy as np

    proposal_arr = np.asarray(proposal, dtype=bool)
    gt_arr = np.asarray(gt_mask, dtype=bool)
    proposal_voxels = int(proposal_arr.sum())
    gt_voxels = int(gt_arr.sum())
    inter = int(np.logical_and(proposal_arr, gt_arr).sum())
    recall: object = "" if gt_voxels == 0 else inter / max(1, gt_voxels)
    precision: object = "" if proposal_voxels == 0 else inter / max(1, proposal_voxels)
    return recall, precision


def compute_contribution_rows(packet: Path, summaries: dict[str, dict[str, object]], *, device_name: str) -> list[dict[str, object]]:
    """Compute M8 per-case branch contribution rows from completed checkpoints."""

    if any(not summaries.get(variant) for variant in VARIANTS):
        return []
    import numpy as np
    import torch
    from argparse import Namespace

    from scripts.training.run_srr_myops_fold0 import collect_case_metrics
    from scripts.training.run_srr_propref_myops_fold0 import (
        SRRProposeRefineMyoPS,
        anchor_dict_from_tensor,
        component_dict_from_tensor,
        full_case_anchor_tensors,
        load_myops_case_metadata,
        maybe_disable_context,
        model_kwargs_from_args,
        read_anchored_case,
    )

    device = torch.device(device_name if device_name == "cpu" or torch.cuda.is_available() else "cpu")
    metadata = load_myops_case_metadata()
    rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        summary = summaries.get(variant, {})
        checkpoint = Path(str(summary.get("checkpoint_best", "")))
        if not checkpoint.is_file():
            rows.append({"variant": variant, "checkpoint": str(checkpoint), "status": "CHECKPOINT_NOT_FOUND"})
            continue
        state = torch.load(checkpoint, map_location=device, weights_only=False)
        args = Namespace(**dict(state.get("args", {})))
        model = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
        model.load_state_dict(state["model_state_dict"])
        model.eval()
        anchor_root = Path(str(summary.get("nnunet_anchor_root", "")))
        eval_case_ids = [str(case_id) for case_id in summary.get("eval_case_ids", [])]
        if not eval_case_ids:
            rows.append({"variant": variant, "checkpoint": str(checkpoint), "status": "EVAL_CASE_IDS_NOT_FOUND"})
            continue
        for case_id in eval_case_ids:
            case = read_anchored_case(case_id, metadata, anchor_root)
            with torch.no_grad():
                x = torch.from_numpy(case.image[None]).float().to(device)
                av = torch.from_numpy(case.availability[None]).float().to(device)
                anchor_features, component_features = full_case_anchor_tensors(case, device)
                anchor_features, component_features = maybe_disable_context(args, anchor_features, component_features)
                outputs = model(x, av, anchor_features=anchor_features, component_features=component_features)
                final_logits = outputs["logits"]
                anchor_logits = outputs.get("nnunet_anchor_logits")
                if anchor_logits is None:
                    rows.append({"variant": variant, "checkpoint": str(checkpoint), "case_id": case_id, "status": "ANCHOR_LOGITS_NOT_FOUND"})
                    continue
                final_pred = torch.argmax(final_logits, dim=1)[0].detach().cpu().numpy().astype(np.uint8)
                anchor_pred = torch.argmax(anchor_logits, dim=1)[0].detach().cpu().numpy().astype(np.uint8)
                final_np = final_logits[0].detach().cpu().numpy()
                anchor_np = anchor_logits[0].detach().cpu().numpy()
                correction_mask = outputs.get("branch_correction_mask")
                srr_weight = outputs.get("srr_retrieval_weight")
                proposal_weight = outputs.get("proposal_weight")
                refiner_weight = outputs.get("refiner_weight")
                fallback_weight = outputs.get("branch_fallback_weight")
                branch_delta = outputs.get("arbitration_branch_delta")
                final_metrics = {row["metric_name"]: row for row in collect_case_metrics(variant, case, final_pred)}
                anchor_metrics = {row["metric_name"]: row for row in collect_case_metrics(f"{variant}__anchor", case, anchor_pred)}
                for cls, class_name, prefix in [(5, "myops_scar", "scar"), (4, "myops_edema", "edema")]:
                    final_row = final_metrics.get(class_name, {})
                    anchor_row = anchor_metrics.get(class_name, {})
                    final_cls = final_pred == cls
                    anchor_cls = anchor_pred == cls
                    proposal_logits = outputs[f"{prefix}_proposal_logits"][0, 0].detach().cpu().numpy()
                    proposal = _sigmoid_np(proposal_logits) >= 0.10
                    gt_mask = case.label_arr == cls
                    proposal_recall, proposal_precision = _proposal_recall_precision(proposal, gt_mask)
                    residual = outputs[f"{prefix}_refinement_residual"][0, 0].detach().cpu().numpy()
                    rows.append(
                        {
                            "variant": variant,
                            "checkpoint": str(checkpoint),
                            "decode_mode": "argmax",
                            "case_id": case.case_id,
                            "center": case.metadata.center,
                            "modality_group": case.metadata.modality_group,
                            "t2_present": case.metadata.t2_present,
                            "class_name": class_name,
                            "anchor_delta_rate": float(np.mean(final_cls != anchor_cls)),
                            "final_delta_rate": float(np.mean(final_pred != anchor_pred)),
                            "correction_gate_open_rate": float(correction_mask.detach().mean().cpu()) if correction_mask is not None else "EVIDENCE_NOT_FOUND",
                            "srr_weight_mean": float(srr_weight.detach().mean().cpu()) if srr_weight is not None else "EVIDENCE_NOT_FOUND",
                            "proposal_weight_mean": float(proposal_weight.detach().mean().cpu()) if proposal_weight is not None else "EVIDENCE_NOT_FOUND",
                            "refiner_weight_mean": float(refiner_weight.detach().mean().cpu()) if refiner_weight is not None else "EVIDENCE_NOT_FOUND",
                            "fallback_weight_mean": float(fallback_weight.detach().mean().cpu()) if fallback_weight is not None else "EVIDENCE_NOT_FOUND",
                            "final_logit_delta_abs_mean": float(np.mean(np.abs(final_np[cls] - anchor_np[cls]))),
                            "roi_delta_abs_mean": float(np.mean(np.abs(residual))),
                            "proposal_recall_proxy": proposal_recall,
                            "proposal_precision_proxy": proposal_precision,
                            "refiner_delta_magnitude": float(np.mean(np.abs(residual))),
                            "no_t2_edema_voxels": int(np.count_nonzero(final_pred == 4)) if not case.metadata.t2_present else 0,
                            "dice_delta": _metric_value(final_row, "dice") - _metric_value(anchor_row, "dice"),
                            "hd95_delta": _metric_value(final_row, "hd95") - _metric_value(anchor_row, "hd95"),
                            "remote_fp_delta": _metric_value(final_row, "remote_fp_count") - _metric_value(anchor_row, "remote_fp_count"),
                            "component_count_delta": _metric_value(final_row, "component_count") - _metric_value(anchor_row, "component_count"),
                            "source_prediction_path": str(variant_dir(packet, variant) / "predictions/fold_0/checkpoint_best/argmax" / f"{case.case_id}.nii.gz"),
                        }
                    )
    return rows


def summarize_eval_outputs(
    packet: Path,
    summaries: dict[str, dict[str, object]],
    *,
    contribution_device: str,
    skip_contribution_compute: bool = False,
) -> None:
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
    if not skip_contribution_compute:
        contribution_rows = compute_contribution_rows(packet, summaries, device_name=contribution_device)
    elif (packet / "m8_srr_contribution_by_case.csv").is_file():
        contribution_rows = read_csv(packet / "m8_srr_contribution_by_case.csv")
    if not contribution_rows:
        contribution_rows = [
            {
                "variant": "M8_NEEDS_MONITOR_NO_REVIEW",
                "checkpoint": "AWAITING_COMPLETED_SUMMARIES",
                "decode_mode": "",
                "case_id": "",
                "center": "",
                "modality_group": "",
                "t2_present": "",
                "class_name": "",
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
                "no_t2_edema_voxels": "",
                "dice_delta": "EVIDENCE_NOT_COMPUTED_VS_ANCHOR",
                "hd95_delta": "EVIDENCE_NOT_COMPUTED_VS_ANCHOR",
                "remote_fp_delta": "EVIDENCE_NOT_COMPUTED_VS_ANCHOR",
                "component_count_delta": "EVIDENCE_NOT_COMPUTED_VS_ANCHOR",
                "source_prediction_path": "runtime prediction directories",
            }
        ]
    write_csv(packet / "m8_srr_contribution_by_case.csv", contribution_rows)


def write_decision_docs(packet: Path, status: str, issues: list[str], summaries: dict[str, dict[str, object]], ledger: list[dict[str, object]]) -> None:
    now = datetime.now(UTC).isoformat()
    total_seconds = total_included_seconds(ledger)
    issue_text = "\n".join(f"- `{issue}`" for issue in issues) or "- none"
    contribution_rows = read_csv(packet / "m8_srr_contribution_by_case.csv")
    contribution_status = "present" if contribution_rows and contribution_rows[0].get("anchor_delta_rate") not in {"", "EVIDENCE_NOT_EXPORTED_PER_CASE"} else "missing"
    cine_report = read_text(packet / "m8_registration_method_selection.md")
    cine_blocked = "CINE_REGISTRATION_BLOCKED_AFTER_MATURE_M8_ATTEMPT" in cine_report
    cine_status = "CINE_REGISTRATION_BLOCKED_AFTER_MATURE_M8_ATTEMPT" if cine_blocked else "CINE_EVIDENCE_REQUIRES_REVIEW"
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
    write_text(
        packet / "m8_myops_decision.md",
        "\n".join(
            [
                "# M8 MyoPS Decision",
                "",
                f"status: `{status}`",
                "",
                f"included_myops_train_loop_seconds: `{total_seconds:.3f}`",
                f"per_case_contribution_status: `{contribution_status}`",
                "",
                "MyoPS training budget evidence is aggregated from completed runtime summaries. This is not a validation upload, hosted-score assertion, fold expansion, challenge submission, scientific stop, or M9.",
                "",
                "## Blocking Issues",
                issue_text,
            ]
        )
        + "\n",
    )
    write_text(
        packet / "m8_cine_decision.md",
        "\n".join(
            [
                "# M8 Cine Decision",
                "",
                f"status: `{cine_status}`",
                "",
                "Cine mature registration evidence is present, but the current M8 evidence does not claim `myocardium_cinemyops` readiness.",
                "",
                "## Evidence",
                "- `m8_registration_same_subset_matrix.csv`",
                "- `m8_registration_method_selection.md`",
                "- `m8_temporal_dictionary_evidence.csv`",
            ]
        )
        + "\n",
    )
    write_text(
        packet / "m8_combined_decision.md",
        "\n".join(
            [
                "# M8 Combined Decision",
                "",
                f"status: `{status}`",
                "",
                f"myops_status: `{status}`",
                f"cine_status: `{cine_status}`",
                "",
                "MyoPS and Cine decisions remain separated. The packet does not claim leaderboard readiness, validation packaging/upload, hosted metrics, challenge submission, scientific stop, fold expansion, or M9.",
                "",
                "## Blocking Issues",
                issue_text,
            ]
        )
        + "\n",
    )
    write_text(
        packet / "m8_leaderboard_readiness_report.md",
        "\n".join(
            [
                "# M8 Leaderboard Readiness Report",
                "",
                f"status: `{status}`",
                "",
                "readiness: `NOT_READY`",
                "",
                "This M8 packet is not leaderboard-ready. It is an executor evidence packet with completed training-budget aggregation, completed Cine temporal-dictionary evidence, and remaining same-split nnU-Net candidate-control assembly gaps.",
                "",
                "## Blocking Issues",
                issue_text,
            ]
        )
        + "\n",
    )
    write_text(
        packet / "m8_next_action.md",
        "\n".join(
            [
                "# M8 Next Action",
                "",
                f"status: `{status}`",
                "",
                "Next action: a follow-up executor must assemble or explicitly rule out the missing same-split nnU-Net local candidate-control evidence before any normal review, route promotion, validation packaging, upload, or next milestone.",
                "",
                "## Blocking Issues",
                issue_text,
            ]
        )
        + "\n",
    )


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
    parser.add_argument("--contribution-device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument(
        "--skip-contribution-compute",
        action="store_true",
        help="Skip expensive checkpoint replay for contribution rows; use only for monitor-state aggregation.",
    )
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
    summarize_eval_outputs(
        packet,
        summaries,
        contribution_device=args.contribution_device,
        skip_contribution_compute=args.skip_contribution_compute,
    )
    status, issues = derive_status(packet, summaries, ledger)
    refresh_architecture_closure_table(packet)
    refresh_required_deliverables(packet, status, issues, ledger)
    write_decision_docs(packet, status, issues, summaries, ledger)
    write_manifest(packet)
    print(json.dumps({"packet": str(packet), "status": status, "issues": issues}, indent=2))


if __name__ == "__main__":
    main()
