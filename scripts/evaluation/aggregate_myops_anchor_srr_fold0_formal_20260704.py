#!/usr/bin/env python3
"""Aggregate formal MyoPS anchored SRR fold0 task artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/20260704_myops_anchor_srr_fold0_formal"
TASK_PATH = "prompts/tasks/20260704_myops_anchor_srr_fold0_formal.md"
VARIANT_MAP = {
    "anchored_srr_v25_full": "srr_propref_shared_dual_dict",
    "anchored_scar_precision_edema_safe": "srr_propref_scar_precision",
    "anchored_conservative_cascade_no_proto_or_frozen_proto": "srr_propref_no_proto_cascade",
}
MIN_OPTIMIZER_STEPS = 1500
MIN_TRAIN_LOOP_SECONDS = 1800.0
NNUNET_SCAR = 0.5602
NNUNET_EDEMA_GT_POS = 0.3944


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({key for row in rows for key in row}) or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def finite_float(value: object) -> float | None:
    try:
        val = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if val != val or val in (float("inf"), float("-inf")):
        return None
    return val


def add_names(formal_variant: str, alias: str, row: dict[str, object], source_path: Path) -> dict[str, object]:
    out = dict(row)
    out.setdefault("formal_variant", formal_variant)
    out.setdefault("script_alias", alias)
    out.setdefault("source_path", str(source_path))
    return out


def missing_row(formal_variant: str, alias: str, source_path: Path, fields: list[str]) -> dict[str, object]:
    row = {field: "evidence not found" for field in fields}
    row.update(
        {
            "formal_variant": formal_variant,
            "script_alias": alias,
            "source_path": str(source_path),
            "not_run_reason": "formal variant evidence not found",
        }
    )
    return row


def concat_variant_files(patterns: list[str], missing_fields: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for formal_variant, alias in VARIANT_MAP.items():
        found = False
        for pattern in patterns:
            glob_path = OUT_ROOT / "variants" / alias / pattern
            for file_path in sorted(glob_path.parent.glob(glob_path.name)):
                file_rows = read_csv(file_path)
                if file_rows:
                    found = True
                    rows.extend(add_names(formal_variant, alias, row, file_path) for row in file_rows)
        if not found:
            rows.append(missing_row(formal_variant, alias, OUT_ROOT / "variants" / alias, missing_fields))
    return rows


def load_summary(alias: str) -> dict[str, object]:
    path = OUT_ROOT / "variants" / alias / "summary.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def load_stage0_summary(alias: str) -> dict[str, object]:
    path = OUT_ROOT / "stage0_local" / "variants" / alias / "one_batch_overfit.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def load_formal_overfit(alias: str) -> dict[str, object]:
    path = OUT_ROOT / "variants" / alias / "one_batch_overfit.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def load_run_config(alias: str) -> dict[str, str]:
    path = OUT_ROOT / "variants" / alias / "configs" / "run_config.env"
    config: dict[str, str] = {}
    if not path.is_file():
        return config
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        config[key] = value
    return config


def prediction_count(path_text: object) -> int:
    path = Path(str(path_text))
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_dir():
        return 0
    return len(list(path.glob("*.nii.gz")))


def formal_adequacy(summary: dict[str, object]) -> tuple[str, list[str]]:
    if not summary:
        return "EVIDENCE_NOT_FOUND", ["summary.json evidence not found"]
    reasons: list[str] = []
    if int(summary.get("actual_optimizer_steps") or 0) < MIN_OPTIMIZER_STEPS:
        reasons.append("actual_optimizer_steps below formal minimum")
    if float(summary.get("train_loop_seconds") or 0.0) < MIN_TRAIN_LOOP_SECONDS:
        reasons.append("train_loop_seconds below formal minimum")
    if int(summary.get("validation_event_count") or 0) < 3:
        reasons.append("validation events incomplete")
    if summary.get("loss_decrease") is None or float(summary.get("loss_decrease") or 0.0) <= 0:
        reasons.append("loss decrease not demonstrated")
    overfit = summary.get("one_batch_overfit") if isinstance(summary.get("one_batch_overfit"), dict) else {}
    if overfit.get("status") != "PASS":
        reasons.append("formal one-batch overfit did not pass")
    pred_dirs = summary.get("prediction_dirs") if isinstance(summary.get("prediction_dirs"), list) else []
    if not any(prediction_count(path) for path in pred_dirs):
        reasons.append("prediction export evidence not found")
    return ("PASS" if not reasons else "FAIL", reasons)


def select_status(summaries: dict[str, dict[str, object]], job_id: str) -> tuple[str, str, str, str]:
    statuses = [formal_adequacy(summary)[0] for summary in summaries.values()]
    if any(status == "EVIDENCE_NOT_FOUND" for status in statuses):
        if job_id and job_id != "none":
            return "PENDING_OR_RUNNING", "NO_PROMOTION", "STOP_NOT_SUPPORTED", "NEEDS_MONITOR"
        return "EVIDENCE_NOT_FOUND", "NO_PROMOTION", "STOP_NOT_SUPPORTED", "NEEDS_EVIDENCE"
    if any(status != "PASS" for status in statuses):
        return "FAIL", "NO_PROMOTION", "STOP_NOT_SUPPORTED", "SCIENTIFIC_UNDERTRAINED"
    return "PASS", "NO_PROMOTION", "STOP_NOT_SUPPORTED", "SCIENTIFIC_UNRESOLVED"


def write_job_status(
    job_id: str,
    job_state: str,
    stage0: dict[str, dict[str, object]],
    formal_overfit: dict[str, dict[str, object]],
    summaries: dict[str, dict[str, object]],
    configs: dict[str, dict[str, str]],
) -> None:
    log_glob = f"logs/MyoPSAnchorSRRF0_*_{job_id}_*.log" if job_id and job_id != "none" else "logs/MyoPSAnchorSRRF0_*_<job_id>_*.log"
    lines = [
        "# Job Status",
        "",
        f"job_id: `{job_id or 'none'}`",
        f"job_state_snapshot: `{job_state or 'not queried'}`",
        f"log_path_glob: `{log_glob}`",
        "partition_policy: `htzhulab default; 7:30:00 per array task; qos gpu_access`",
        "",
        "| formal_variant | script_alias | slurm_task_job_id | log_file | pre_submit_stage0 | formal_stage0 | formal_summary | optimizer_steps | validation_events |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | ---: |",
    ]
    for formal_variant, alias in VARIANT_MAP.items():
        summary = summaries.get(alias, {})
        config = configs.get(alias, {})
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | {} | {} |".format(
                formal_variant,
                alias,
                config.get("job_id", "evidence not found"),
                config.get("log_file", "evidence not found"),
                stage0.get(alias, {}).get("status", "evidence not found"),
                formal_overfit.get(alias, {}).get("status", "evidence not found"),
                "present" if summary else "not yet written",
                summary.get("actual_optimizer_steps", "evidence not found"),
                summary.get("validation_event_count", "evidence not found"),
            )
        )
    write_text(OUT_ROOT / "job_status.md", "\n".join(lines) + "\n")


def write_one_batch(
    stage0: dict[str, dict[str, object]],
    formal_overfit: dict[str, dict[str, object]],
    summaries: dict[str, dict[str, object]],
) -> None:
    lines = [
        "# One-Batch Overfit",
        "",
        "| formal_variant | script_alias | pre_submit_stage0 | formal_stage0 | steps | first_loss | last_loss | loss_decrease | case_id |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for formal_variant, alias in VARIANT_MAP.items():
        formal = summaries.get(alias, {}).get("one_batch_overfit") if isinstance(summaries.get(alias, {}).get("one_batch_overfit"), dict) else formal_overfit.get(alias, {})
        pre = stage0.get(alias, {})
        source = formal if formal else pre
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | {} | {} | {} | {} | `{}` |".format(
                formal_variant,
                alias,
                pre.get("status", "evidence not found"),
                formal.get("status", "evidence not found"),
                source.get("steps", "evidence not found"),
                source.get("first_loss", "evidence not found"),
                source.get("last_loss", "evidence not found"),
                source.get("loss_decrease", "evidence not found"),
                source.get("case_id", "evidence not found"),
            )
        )
    lines.append("\nPre-submit Stage 0 used a bounded CPU sanity config. Formal jobs rerun Stage 0 with the formal GPU config before optimizer training.")
    write_text(OUT_ROOT / "one_batch_overfit.md", "\n".join(lines) + "\n")


def write_experiment_adequacy(summaries: dict[str, dict[str, object]]) -> None:
    lines = [
        "# Experiment Adequacy Report",
        "",
        f"minimum_optimizer_steps: {MIN_OPTIMIZER_STEPS}",
        f"minimum_train_loop_seconds: {MIN_TRAIN_LOOP_SECONDS:.0f}",
        "",
        "| formal_variant | script_alias | decision | optimizer_steps | train_loop_seconds | validation_events | loss_decrease | missing_or_failed_evidence |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for formal_variant, alias in VARIANT_MAP.items():
        summary = summaries.get(alias, {})
        decision, reasons = formal_adequacy(summary)
        lines.append(
            "| `{}` | `{}` | `{}` | {} | {} | {} | {} | {} |".format(
                formal_variant,
                alias,
                decision,
                summary.get("actual_optimizer_steps", "evidence not found"),
                summary.get("train_loop_seconds", "evidence not found"),
                summary.get("validation_event_count", "evidence not found"),
                summary.get("loss_decrease", "evidence not found"),
                "; ".join(reasons) if reasons else "none",
            )
        )
    lines.append("\nPending/running jobs are not formal evidence complete. Budget exhaustion while curves still move remains `SCIENTIFIC_UNDERTRAINED` or `NEEDS_MONITOR`, not route failure.")
    write_text(OUT_ROOT / "experiment_adequacy_report.md", "\n".join(lines) + "\n")


def write_checkpoint_policy(summaries: dict[str, dict[str, object]]) -> None:
    lines = [
        "# Checkpoint Policy",
        "",
        "| formal_variant | script_alias | best_step | final_step | validation_events | checkpoint_best | checkpoint_final |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for formal_variant, alias in VARIANT_MAP.items():
        summary = summaries.get(alias, {})
        lines.append(
            "| `{}` | `{}` | {} | {} | {} | `{}` | `{}` |".format(
                formal_variant,
                alias,
                summary.get("best_step", "evidence not found"),
                summary.get("actual_optimizer_steps", "evidence not found"),
                summary.get("validation_event_count", "evidence not found"),
                summary.get("checkpoint_best", "evidence not found"),
                summary.get("checkpoint_final", "evidence not found"),
            )
        )
    lines.append("\nFormal best checkpoint selection is validation-loss based after warmup eligibility. Final checkpoint is retained for comparison.")
    write_text(OUT_ROOT / "checkpoint_policy.md", "\n".join(lines) + "\n")


def write_prediction_sanity(rows: list[dict[str, object]]) -> None:
    valid = [r for r in rows if r.get("compact_label_values") != "evidence not found"]
    lines = [
        "# Prediction Sanity",
        "",
        "| formal_variant | script_alias | checkpoint | decode | mean_foreground_rate | mean_pathology_rate | empty_prediction_rate | compact_labels |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    groups: dict[tuple[str, str, str, str], list[dict[str, object]]] = {}
    for row in valid:
        key = (str(row.get("formal_variant")), str(row.get("script_alias")), str(row.get("checkpoint_name")), str(row.get("decode_mode")))
        groups.setdefault(key, []).append(row)
    if not groups:
        lines.append("| evidence not found | evidence not found | evidence not found | evidence not found |  |  |  | evidence not found |")
    for key, subset in sorted(groups.items()):
        formal_variant, alias, checkpoint, decode = key
        fg = [finite_float(r.get("foreground_rate")) for r in subset]
        path = [finite_float(r.get("pathology_rate")) for r in subset]
        empty = [1.0 if str(r.get("empty_prediction")).lower() == "true" else 0.0 for r in subset]
        labels = sorted({str(r.get("compact_label_values")) for r in subset})
        fg_vals = [v for v in fg if v is not None]
        path_vals = [v for v in path if v is not None]
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | {:.6f} | {:.6f} | {:.6f} | `{}` |".format(
                formal_variant,
                alias,
                checkpoint,
                decode,
                sum(fg_vals) / max(1, len(fg_vals)),
                sum(path_vals) / max(1, len(path_vals)),
                sum(empty) / max(1, len(empty)),
                ";".join(labels),
            )
        )
    lines.append("\nRaw-label validation export and upload-ready packaging were not generated by this task.")
    write_text(OUT_ROOT / "prediction_sanity.md", "\n".join(lines) + "\n")


def write_metrics_summary(subgroups: list[dict[str, object]]) -> None:
    lines = [
        "# Metrics Summary",
        "",
        f"same_split_nnunet_scar_all_case_dice: {NNUNET_SCAR:.4f}",
        f"same_split_nnunet_edema_gt_positive_dice: {NNUNET_EDEMA_GT_POS:.4f}",
        "",
        "| formal_variant | script_alias | metric | group | dice_mean | hd95_mean | component_count_mean | remote_fp_mean |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    found = False
    for row in subgroups:
        if row.get("metric_name") == "evidence not found":
            continue
        if row.get("group") not in {"all_cases", "gt_positive_only", "t2_present", "CenterB", "CenterC", "LGE-only", "no_T2_empty_GT"}:
            continue
        found = True
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | {} | {} | {} | {} |".format(
                row.get("formal_variant", ""),
                row.get("script_alias", ""),
                row.get("metric_name", ""),
                row.get("group", ""),
                row.get("dice_mean", ""),
                row.get("hd95_mean", ""),
                row.get("component_count_mean", ""),
                row.get("remote_fp_mean", ""),
            )
        )
    if not found:
        lines.append("| evidence not found | evidence not found | evidence not found | evidence not found |  |  |  |  |")
    write_text(OUT_ROOT / "metrics_summary.md", "\n".join(lines) + "\n")


def write_no_t2_decode_sanity(pred_rows: list[dict[str, object]]) -> None:
    rows = []
    for row in pred_rows:
        if row.get("t2_present") in ("False", "false", False, "0", 0):
            rows.append(
                {
                    "formal_variant": row.get("formal_variant", ""),
                    "script_alias": row.get("script_alias", ""),
                    "case_id": row.get("case_id", ""),
                    "checkpoint_name": row.get("checkpoint_name", ""),
                    "decode_mode": row.get("decode_mode", ""),
                    "no_t2_edema_voxels": row.get("no_t2_edema_voxels", ""),
                    "compact_label_values": row.get("compact_label_values", ""),
                    "source_path": row.get("source_path", ""),
                }
            )
    if not rows:
        rows = [
            {
                "formal_variant": "evidence not found",
                "script_alias": "evidence not found",
                "case_id": "evidence not found",
                "checkpoint_name": "evidence not found",
                "decode_mode": "evidence not found",
                "no_t2_edema_voxels": "evidence not found",
                "compact_label_values": "evidence not found",
                "source_path": str(OUT_ROOT / "prediction_sanity.csv"),
            }
        ]
    write_csv(OUT_ROOT / "no_t2_decode_sanity.csv", rows)


def write_label_export_qc(pred_rows: list[dict[str, object]]) -> None:
    lines = ["# Label Export QC", "", "| formal_variant | script_alias | compact_labels | raw_label_export | validation_package |", "| --- | --- | --- | --- | --- |"]
    for formal_variant, alias in VARIANT_MAP.items():
        labels = sorted({str(row.get("compact_label_values")) for row in pred_rows if row.get("script_alias") == alias and row.get("compact_label_values")})
        lines.append(f"| `{formal_variant}` | `{alias}` | `{';'.join(labels) if labels else 'evidence not found'}` | not generated; not authorized | not generated; not authorized |")
    write_text(OUT_ROOT / "label_export_qc.md", "\n".join(lines) + "\n")


def write_loss_stage_status(summaries: dict[str, dict[str, object]]) -> None:
    lines = ["# Loss Stage Status", "", "| formal_variant | script_alias | stop_reason | stage_step_counts | first_train_loss | last_train_loss | loss_decrease |", "| --- | --- | --- | --- | ---: | ---: | ---: |"]
    for formal_variant, alias in VARIANT_MAP.items():
        summary = summaries.get(alias, {})
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | {} | {} | {} |".format(
                formal_variant,
                alias,
                summary.get("stop_reason", "evidence not found"),
                summary.get("stage_step_counts", "evidence not found"),
                summary.get("first_train_loss", "evidence not found"),
                summary.get("last_train_loss", "evidence not found"),
                summary.get("loss_decrease", "evidence not found"),
            )
        )
    write_text(OUT_ROOT / "loss_stage_status.md", "\n".join(lines) + "\n")


def write_failure_interpretation(experiment_decision: str, scientific_status: str) -> None:
    lines = [
        "# Failure Interpretation",
        "",
        f"experiment_adequacy_decision: {experiment_decision}",
        "route_promotion_decision: NO_PROMOTION",
        "route_negative_decision: STOP_NOT_SUPPORTED",
        f"scientific_resolution_status: {scientific_status}",
        "",
        "This executor does not claim route promotion or `STOP_NO_SIGNAL`. Pending, running, missing, or undertrained formal evidence requires monitoring, revision, or audit.",
    ]
    write_text(OUT_ROOT / "failure_interpretation.md", "\n".join(lines) + "\n")


def write_manifest() -> None:
    files = [
        "result.md",
        "MANIFEST.md",
        "job_status.md",
        "experiment_adequacy_report.md",
        "one_batch_overfit.md",
        "checkpoint_policy.md",
        "training_curves.csv",
        "validation_curve.csv",
        "prediction_sanity.md",
        "dictionary_stats.csv",
        "gate_usage_by_pattern.csv",
        "proposal_pr_sweep.csv",
        "metrics_summary.md",
        "subgroup_metrics.csv",
        "component_hd_by_case.csv",
        "no_t2_decode_sanity.csv",
        "label_export_qc.md",
        "loss_stage_status.md",
        "failure_interpretation.md",
        "command_transcript.md",
    ]
    lines = [
        "# MANIFEST: 20260704_myops_anchor_srr_fold0_formal",
        "",
        f"- Task: `{TASK_PATH}`",
        "- Result: `results/20260704_myops_anchor_srr_fold0_formal/result.md`",
        "- Review: `results/20260704_myops_anchor_srr_fold0_formal/review.md` (not written by executor)",
        "",
        "| artifact | purpose |",
        "| --- | --- |",
    ]
    for file in files:
        lines.append(f"| `{file}` | formal fold0 executor evidence or pending-status placeholder |")
    lines.append("| `variants/<script_alias>/` | per-variant formal checkpoints, logs, predictions, and metrics when Slurm tasks complete |")
    lines.append("| `stage0_local/` | bounded pre-submit one-batch/loss-gradient sanity outputs |")
    write_text(OUT_ROOT / "MANIFEST.md", "\n".join(lines) + "\n")


def write_result(
    experiment_decision: str,
    promotion_decision: str,
    negative_decision: str,
    scientific_status: str,
    job_id: str,
    stage0: dict[str, dict[str, object]],
    formal_overfit: dict[str, dict[str, object]],
    summaries: dict[str, dict[str, object]],
    configs: dict[str, dict[str, str]],
    commands: list[str],
) -> None:
    self_status = "NEEDS_MONITOR" if scientific_status == "NEEDS_MONITOR" else ("EXECUTED_UNAUDITED" if experiment_decision == "PASS" else scientific_status)
    lines = [
        "# Result 20260704 MyoPS Anchor SRR Fold0 Formal",
        "",
        f"experiment_adequacy_decision: {experiment_decision}",
        f"route_promotion_decision: {promotion_decision}",
        f"route_negative_decision: {negative_decision}",
        f"scientific_resolution_status: {scientific_status}",
        f"self_assessed_status: {self_status}",
        "role: executor",
        "review_required: true",
        "",
        "## Execution Summary",
        "",
        "Verified the LOCKED contract and Phase 1-5 PASS_PREFLIGHT prerequisites. Ran bounded pre-submit Stage 0 sanity for all three required aliases, then used the CARE htzhulab GPU policy for the formal fold0 Slurm array.",
        "",
        "No validation package, external upload, network access, fold expansion, git commit, or git push was performed.",
        "",
        "## Variant Mapping",
        "",
        "| formal_variant | script_alias | pre_submit_stage0 | formal_stage0 | formal_summary | adequacy |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for formal_variant, alias in VARIANT_MAP.items():
        adequacy, _ = formal_adequacy(summaries.get(alias, {}))
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` |".format(
                formal_variant,
                alias,
                stage0.get(alias, {}).get("status", "evidence not found"),
                formal_overfit.get(alias, {}).get("status", "evidence not found"),
                "present" if summaries.get(alias) else "evidence not found",
                adequacy,
            )
        )
    lines.extend(
        [
            "",
            "## Job",
            "",
            f"- job_id: `{job_id or 'none'}`",
            f"- log_path_glob: `logs/MyoPSAnchorSRRF0_*_{job_id or '<job_id>'}_*.log`",
            f"- formal_status: `{'COMPLETE' if experiment_decision != 'PENDING_OR_RUNNING' else 'PENDING_OR_RUNNING'}`",
            "",
            "Per-variant log files:",
        ]
    )
    for formal_variant, alias in VARIANT_MAP.items():
        lines.append(f"- `{formal_variant}` / `{alias}`: `{configs.get(alias, {}).get('log_file', 'evidence not found')}`")
    lines.extend(
        [
            "",
            "## Commands Run",
            "",
        ]
    )
    lines.extend(f"- `{cmd}`" for cmd in commands)
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- Required result artifacts were written under `results/20260704_myops_anchor_srr_fold0_formal/`.",
            "- Per-variant formal evidence is under `variants/<script_alias>/`: checkpoints, prediction exports, logs, summaries, and metric CSVs.",
            "",
            "## Boundary",
            "",
            "This executor does not authorize route promotion, route-negative stop, validation packaging/upload, fold expansion, commit, or push. Separate read-only audit remains required.",
        ]
    )
    write_text(OUT_ROOT / "result.md", "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", default="none")
    parser.add_argument("--job-state", default="")
    parser.add_argument("--command", action="append", default=[])
    args = parser.parse_args()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    summaries = {alias: load_summary(alias) for alias in VARIANT_MAP.values()}
    stage0 = {alias: load_stage0_summary(alias) for alias in VARIANT_MAP.values()}
    formal_overfit = {alias: load_formal_overfit(alias) for alias in VARIANT_MAP.values()}
    configs = {alias: load_run_config(alias) for alias in VARIANT_MAP.values()}

    component = concat_variant_files(["component_hd_by_case_*.csv"], ["variant", "case_id", "metric_name", "dice", "hd", "hd95", "component_count", "remote_fp_count"])
    subgroup = concat_variant_files(["subgroup_metrics_*.csv"], ["variant", "metric_name", "group", "dice_mean", "hd95_mean", "component_count_mean", "remote_fp_mean"])
    proposal = concat_variant_files(["proposal_pr_sweep_*.csv"], ["variant", "case_id", "metric_name", "proposal_threshold", "proposal_recall", "proposal_precision", "lesion_wise_recall", "outside_myocardium_fp_ratio"])
    pred_sanity = concat_variant_files(["prediction_sanity_*.csv"], ["variant", "checkpoint_name", "decode_mode", "compact_label_values", "foreground_rate", "pathology_rate", "empty_prediction", "no_t2_edema_voxels"])
    training = concat_variant_files(["training_log.csv"], ["variant", "step", "stage", "loss", "elapsed_seconds"])
    validation = concat_variant_files(["validation_events.csv"], ["variant", "step", "stage", "val_patch_loss", "elapsed_seconds"])
    gate_usage = concat_variant_files(["retrieval_usage.csv"], ["variant", "step", "task", "expert_index", "mean_weight", "batch_cases"])
    dictionary = concat_variant_files(["hardneg_memory.csv", "prototype_update_sanity_formal.csv"], ["variant", "memory_source", "class_id", "safety_type", "replay_safe_components", "parameter", "grad_norm", "update_norm"])

    write_csv(OUT_ROOT / "component_hd_by_case.csv", component)
    write_csv(OUT_ROOT / "subgroup_metrics.csv", subgroup)
    write_csv(OUT_ROOT / "proposal_pr_sweep.csv", proposal)
    write_csv(OUT_ROOT / "training_curves.csv", training)
    write_csv(OUT_ROOT / "validation_curve.csv", validation)
    write_csv(OUT_ROOT / "gate_usage_by_pattern.csv", gate_usage)
    write_csv(OUT_ROOT / "dictionary_stats.csv", dictionary)
    write_no_t2_decode_sanity(pred_sanity)
    write_job_status(args.job_id, args.job_state, stage0, formal_overfit, summaries, configs)
    write_one_batch(stage0, formal_overfit, summaries)
    write_experiment_adequacy(summaries)
    write_checkpoint_policy(summaries)
    write_prediction_sanity(pred_sanity)
    write_metrics_summary(subgroup)
    write_label_export_qc(pred_sanity)
    write_loss_stage_status(summaries)
    experiment_decision, promotion_decision, negative_decision, scientific_status = select_status(summaries, args.job_id)
    write_failure_interpretation(experiment_decision, scientific_status)
    write_manifest()
    commands = args.command or ["evidence not recorded"]
    write_result(experiment_decision, promotion_decision, negative_decision, scientific_status, args.job_id, stage0, formal_overfit, summaries, configs, commands)
    write_text(
        OUT_ROOT / "command_transcript.md",
        "\n".join(
            [
                "# Command Transcript",
                "",
                f"- aggregate_time_utc: `{datetime.now(UTC).isoformat()}`",
                f"- aggregate_command: `{' '.join(['scripts/evaluation/aggregate_myops_anchor_srr_fold0_formal_20260704.py', *commands])}`",
                "- aggregate_exit_status: `0`",
                "- network_used: `false`",
            ]
        )
        + "\n",
    )
    print(f"wrote {OUT_ROOT}")


if __name__ == "__main__":
    main()
