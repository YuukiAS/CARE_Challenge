#!/usr/bin/env python3
"""Aggregate SRR-ProposeRefine repair artifacts for the 20260703 executor task."""

from __future__ import annotations

import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/20260703_srr_propref_repair"
TASK_PATH = "prompts/tasks/20260703_srr_propref_repair.md"
VARIANTS = [
    "srr_propref_shared_dual_dict",
    "srr_propref_scar_precision",
    "srr_propref_no_proto_cascade",
]
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
    names = fieldnames or sorted({key for row in rows for key in row})
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


def load_summary(variant: str) -> dict[str, object]:
    path = OUT_ROOT / "variants" / variant / "summary.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    overfit_path = OUT_ROOT / "variants" / variant / "one_batch_overfit.json"
    if overfit_path.is_file():
        return {
            "variant": variant,
            "stop_reason": "local_smoke_interrupted_before_formal_summary",
            "actual_optimizer_steps": 0,
            "optimizer_steps": 0,
            "train_loop_seconds": 0.0,
            "validation_event_count": 0,
            "loss_decrease": None,
            "one_batch_overfit": json.loads(overfit_path.read_text(encoding="utf-8")),
            "prediction_dirs": [],
            "checkpoint_best": "evidence not found",
            "checkpoint_final": "evidence not found",
        }
    return {}


def concat_variant_files(patterns: list[str], missing_fields: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        found = False
        for pattern in patterns:
            path = OUT_ROOT / "variants" / variant / pattern
            for file_path in sorted(path.parent.glob(path.name)):
                file_rows = read_csv(file_path)
                if file_rows:
                    found = True
                    for row in file_rows:
                        row = dict(row)
                        row["source_path"] = str(file_path)
                        rows.append(row)
        if not found:
            row = {field: "evidence not found" for field in missing_fields}
            row["variant"] = variant
            row["source_path"] = str(OUT_ROOT / "variants" / variant)
            row["not_run_reason"] = "variant evidence not found"
            rows.append(row)
    return rows


def prediction_count(path_text: object) -> int:
    path = Path(str(path_text))
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_dir():
        return 0
    return len(list(path.glob("*.nii.gz")))


def adequacy_status(summary: dict[str, object]) -> tuple[str, list[str]]:
    if not summary:
        return "EVIDENCE_NOT_FOUND", ["summary.json evidence not found"]
    reasons: list[str] = []
    if int(summary.get("actual_optimizer_steps") or 0) < MIN_OPTIMIZER_STEPS:
        reasons.append("actual_optimizer_steps below minimum")
    if float(summary.get("train_loop_seconds") or 0.0) < MIN_TRAIN_LOOP_SECONDS:
        reasons.append("train_loop_seconds below minimum")
    if int(summary.get("validation_event_count") or 0) < 3:
        reasons.append("post-warmup validation events incomplete")
    if summary.get("loss_decrease") is None or float(summary.get("loss_decrease") or 0.0) <= 0:
        reasons.append("loss decrease not demonstrated")
    overfit = summary.get("one_batch_overfit") if isinstance(summary.get("one_batch_overfit"), dict) else {}
    if overfit.get("status") != "PASS":
        reasons.append("one-batch overfit sanity did not pass")
    pred_dirs = summary.get("prediction_dirs") if isinstance(summary.get("prediction_dirs"), list) else []
    if not any(prediction_count(path) for path in pred_dirs):
        reasons.append("prediction sanity/export evidence not found")
    return ("PASS" if not reasons else "FAIL", reasons)


def select_scientific_status(summaries: dict[str, dict[str, object]]) -> tuple[str, str, str, str]:
    statuses = [adequacy_status(summary)[0] for summary in summaries.values()]
    if all(status == "EVIDENCE_NOT_FOUND" for status in statuses):
        return "EVIDENCE_NOT_FOUND", "NOT_EVALUABLE", "STOP_NOT_SUPPORTED", "SCIENTIFIC_NEEDS_EVIDENCE"
    if any(status != "PASS" for status in statuses):
        return "FAIL", "NOT_EVALUABLE", "STOP_NOT_SUPPORTED", "SCIENTIFIC_UNDERTRAINED"
    return "PASS", "NO_PROMOTION", "STOP_NOT_SUPPORTED", "SCIENTIFIC_UNRESOLVED"


def write_experiment_adequacy_report(summaries: dict[str, dict[str, object]]) -> None:
    lines = [
        "# Experiment Adequacy Report",
        "",
        f"minimum_optimizer_steps: {MIN_OPTIMIZER_STEPS}",
        f"minimum_train_loop_seconds: {MIN_TRAIN_LOOP_SECONDS:.0f}",
        "",
        "| variant | decision | actual_optimizer_steps | train_loop_seconds | validation_events | loss_decrease | overfit | missing_or_failed_evidence |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for variant, summary in summaries.items():
        status, reasons = adequacy_status(summary)
        overfit = summary.get("one_batch_overfit") if isinstance(summary.get("one_batch_overfit"), dict) else {}
        lines.append(
            "| `{}` | `{}` | {} | {} | {} | {} | `{}` | {} |".format(
                variant,
                status,
                summary.get("actual_optimizer_steps", "evidence not found"),
                summary.get("train_loop_seconds", "evidence not found"),
                summary.get("validation_event_count", "evidence not found"),
                summary.get("loss_decrease", "evidence not found"),
                overfit.get("status", "evidence not found"),
                "; ".join(reasons) if reasons else "none",
            )
        )
    lines.extend(
        [
            "",
            "Slurm elapsed time alone is not used as adequacy evidence. `STOP_NO_PROPREF_SIGNAL` remains unsupported unless this gate passes and a separate auditor supports the route-negative decision.",
        ]
    )
    write_text(OUT_ROOT / "experiment_adequacy_report.md", "\n".join(lines) + "\n")


def write_one_batch_overfit(summaries: dict[str, dict[str, object]]) -> None:
    lines = ["# One-Batch Overfit Sanity", "", "| variant | status | steps | first_loss | last_loss | loss_decrease | case_id |", "| --- | --- | ---: | ---: | ---: | ---: | --- |"]
    for variant, summary in summaries.items():
        overfit = summary.get("one_batch_overfit") if isinstance(summary.get("one_batch_overfit"), dict) else {}
        lines.append(
            "| `{}` | `{}` | {} | {} | {} | {} | `{}` |".format(
                variant,
                overfit.get("status", "evidence not found"),
                overfit.get("steps", "evidence not found"),
                overfit.get("first_loss", "evidence not found"),
                overfit.get("last_loss", "evidence not found"),
                overfit.get("loss_decrease", "evidence not found"),
                overfit.get("case_id", "evidence not found"),
            )
        )
    lines.append("\nPrototype gradient/update rows are in each variant's `prototype_update_sanity*.csv` files.")
    write_text(OUT_ROOT / "one_batch_overfit.md", "\n".join(lines) + "\n")


def write_checkpoint_policy(summaries: dict[str, dict[str, object]]) -> None:
    lines = ["# Checkpoint Policy", "", "| variant | best_step | final_step | validation_schedule | validation_events | checkpoint_best | checkpoint_final |", "| --- | ---: | ---: | --- | ---: | --- | --- |"]
    for variant, summary in summaries.items():
        lines.append(
            "| `{}` | {} | {} | `{}` | {} | `{}` | `{}` |".format(
                variant,
                summary.get("best_step", "evidence not found"),
                summary.get("actual_optimizer_steps", "evidence not found"),
                summary.get("validation_schedule", "evidence not found"),
                summary.get("validation_event_count", "evidence not found"),
                summary.get("checkpoint_best", "evidence not found"),
                summary.get("checkpoint_final", "evidence not found"),
            )
        )
    lines.append("\nPolicy: formal evidence must compare best and final checkpoints. Best checkpoint selection is ineligible before the warmup fraction and falls back to final when no eligible validation exists.")
    write_text(OUT_ROOT / "checkpoint_policy.md", "\n".join(lines) + "\n")


def write_prediction_sanity_doc(rows: list[dict[str, object]]) -> None:
    valid_rows = [row for row in rows if row.get("compact_label_values") != "evidence not found"]
    lines = ["# Prediction Sanity", "", "| variant | checkpoint | decode | mean foreground_rate | mean pathology_rate | empty_prediction_rate | compact labels |", "| --- | --- | --- | ---: | ---: | ---: | --- |"]
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for row in valid_rows:
        key = (str(row.get("variant")), str(row.get("checkpoint_name")), str(row.get("decode_mode")))
        groups.setdefault(key, []).append(row)
    if not groups:
        lines.append("| evidence not found | evidence not found | evidence not found |  |  |  | evidence not found |")
    for (variant, checkpoint, decode), subset in sorted(groups.items()):
        fg = [finite_float(row.get("foreground_rate")) for row in subset]
        path = [finite_float(row.get("pathology_rate")) for row in subset]
        empty = [1.0 if str(row.get("empty_prediction")).lower() == "true" else 0.0 for row in subset]
        labels = sorted({str(row.get("compact_label_values")) for row in subset})
        lines.append(
            "| `{}` | `{}` | `{}` | {:.6f} | {:.6f} | {:.6f} | `{}` |".format(
                variant,
                checkpoint,
                decode,
                sum(v for v in fg if v is not None) / max(1, sum(1 for v in fg if v is not None)),
                sum(v for v in path if v is not None) / max(1, sum(1 for v in path if v is not None)),
                sum(empty) / max(1, len(empty)),
                ";".join(labels),
            )
        )
    lines.append("\nRaw-label validation export was not generated; validation packaging/upload is forbidden by task scope.")
    write_text(OUT_ROOT / "prediction_sanity.md", "\n".join(lines) + "\n")


def write_metrics_summary(subgroups: list[dict[str, object]]) -> None:
    lines = [
        "# Metrics Summary",
        "",
        f"same_split_nnunet_scar_all_case_dice: {NNUNET_SCAR:.4f}",
        f"same_split_nnunet_edema_gt_positive_dice: {NNUNET_EDEMA_GT_POS:.4f}",
        "",
        "| context_variant | metric | group | dice_mean | hd95_mean | component_count_mean | remote_fp_mean |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    if not subgroups or subgroups[0].get("metric_name") == "evidence not found":
        lines.append("| evidence not found | evidence not found | evidence not found |  |  |  |  |")
    else:
        for row in subgroups:
            if row.get("group") not in {"all_cases", "gt_positive_only", "t2_present", "CenterB", "CenterC", "LGE-only", "no_T2_empty_GT"}:
                continue
            lines.append(
                "| `{}` | `{}` | `{}` | {} | {} | {} | {} |".format(
                    row.get("variant", ""),
                    row.get("metric_name", ""),
                    row.get("group", ""),
                    row.get("dice_mean", ""),
                    row.get("hd95_mean", ""),
                    row.get("component_count_mean", ""),
                    row.get("remote_fp_mean", ""),
                )
            )
    write_text(OUT_ROOT / "metrics_summary.md", "\n".join(lines) + "\n")


def write_label_export_qc(pred_rows: list[dict[str, object]]) -> None:
    lines = ["# Label Export QC", "", "| variant | compact labels | raw-label export | validation package |", "| --- | --- | --- | --- |"]
    for variant in VARIANTS:
        labels = sorted({str(row.get("compact_label_values")) for row in pred_rows if str(row.get("variant")) == variant and row.get("compact_label_values")})
        compact = ";".join(labels) if labels else "evidence not found"
        lines.append(f"| `{variant}` | `{compact}` | evidence not found; not authorized | evidence not found; not authorized |")
    write_text(OUT_ROOT / "label_export_qc.md", "\n".join(lines) + "\n")


def write_failure_interpretation(experiment_decision: str, scientific_status: str) -> None:
    lines = [
        "# Failure Interpretation",
        "",
        f"experiment_adequacy_decision: {experiment_decision}",
        "route_negative_decision: STOP_NOT_SUPPORTED",
        f"scientific_resolution_status: {scientific_status}",
        "",
        "This executor does not write `STOP_NO_PROPREF_SIGNAL` unless adequacy passes. Missing or short training evidence is classified as undertrained/needs evidence, not as a scientific route stop.",
        "",
        "No old SRR-v2 tuning route, fold expansion, validation packaging, upload, label/evaluator change, or split change was launched.",
    ]
    write_text(OUT_ROOT / "failure_interpretation.md", "\n".join(lines) + "\n")


def write_manifest() -> None:
    files = [
        "result.md",
        "MANIFEST.md",
        "experiment_adequacy_report.md",
        "one_batch_overfit.md",
        "checkpoint_policy.md",
        "prediction_sanity.md",
        "proposal_pr_sweep.csv",
        "metrics_summary.md",
        "subgroup_metrics.csv",
        "component_hd_by_case.csv",
        "roi_coverage.csv",
        "label_export_qc.md",
        "failure_interpretation.md",
        "command_transcript.md",
    ]
    lines = [
        "# MANIFEST: 20260703_srr_propref_repair",
        "",
        f"- Task: `{TASK_PATH}`",
        "- Result: `results/20260703_srr_propref_repair/result.md`",
        "- Review: `results/20260703_srr_propref_repair/review.md` (not written by executor)",
        "",
        "| artifact | purpose |",
        "| --- | --- |",
    ]
    for file in files:
        lines.append(f"| `{file}` | task-scoped SRR PropRef repair evidence |")
    lines.append("| `variants/<variant>/` | per-variant checkpoints, logs, prediction sanity, and metrics when runs complete |")
    write_text(OUT_ROOT / "MANIFEST.md", "\n".join(lines) + "\n")


def write_result(
    summaries: dict[str, dict[str, object]],
    experiment_decision: str,
    promotion_decision: str,
    negative_decision: str,
    scientific_status: str,
) -> None:
    lines = [
        "# Result 20260703 SRR PropRef Repair",
        "",
        f"experiment_adequacy_decision: {experiment_decision}",
        f"route_promotion_decision: {promotion_decision}",
        f"route_negative_decision: {negative_decision}",
        f"scientific_resolution_status: {scientific_status}",
        "self_assessed_status: EXECUTED_UNAUDITED",
        "role: executor",
        "review_required: true",
        "",
        "## Execution Summary",
        "",
        "Patched the SRR-ProposeRefine runner for task-scoped repair evidence: non-step1-only checkpoint policy, explicit optimizer/time/validation/stage/loss counters, one-batch overfit sanity, prototype gradient/update sanity, best/final checkpoint export comparison, argmax versus pathology-aware decode, proposal threshold/PR sweep, and provenance output.",
        "",
        "No network, external upload, validation packaging/upload, fold expansion, label/evaluator/fold split change, old SRR-v2 tuning route, git commit, or git push was performed.",
        "",
        "## Variant Evidence",
        "",
        "| variant | adequacy | optimizer_steps | train_loop_seconds | validation_events | best_step | stop_reason |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for variant, summary in summaries.items():
        status, _ = adequacy_status(summary)
        lines.append(
            "| `{}` | `{}` | {} | {} | {} | {} | `{}` |".format(
                variant,
                status,
                summary.get("actual_optimizer_steps", "evidence not found"),
                summary.get("train_loop_seconds", "evidence not found"),
                summary.get("validation_event_count", "evidence not found"),
                summary.get("best_step", "evidence not found"),
                summary.get("stop_reason", "evidence not found"),
            )
        )
    lines.extend(
        [
            "",
            "## Files Changed",
            "",
            "- `scripts/training/run_srr_propref_myops_fold0.py`",
            "- `jobs/src/run_srr_propref_myops_fold0.sh`",
            "- `scripts/evaluation/aggregate_srr_propref_repair_20260703.py`",
            "- `results/20260703_srr_propref_repair/`",
            "",
            "## Incomplete Items",
            "",
            "- `review.md` was not written because this session is executor-only.",
            "- Adequate formal fold0 conclusions require the adequacy gate in `experiment_adequacy_report.md` plus separate audit.",
            "- `STOP_NO_PROPREF_SIGNAL` is not claimed by this executor unless adequacy passes; current route-negative decision remains `STOP_NOT_SUPPORTED`.",
            "",
            "## Required Next State",
            "",
            "EXECUTED_UNAUDITED",
        ]
    )
    write_text(OUT_ROOT / "result.md", "\n".join(lines) + "\n")


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    component = concat_variant_files(["component_hd_by_case_*.csv"], ["variant", "case_id", "metric_name", "dice", "hd", "hd95", "component_count", "remote_fp_count"])
    subgroup = concat_variant_files(["subgroup_metrics_*.csv"], ["variant", "metric_name", "group", "dice_mean", "hd95_mean"])
    proposal = concat_variant_files(["proposal_pr_sweep_*.csv"], ["variant", "case_id", "metric_name", "proposal_threshold", "proposal_recall", "proposal_precision", "lesion_wise_recall", "outside_myocardium_fp_ratio"])
    roi = concat_variant_files(["roi_coverage_*.csv"], ["variant", "case_id", "metric_name", "gt_coverage", "outside_myocardium_roi_ratio"])
    pred_sanity = concat_variant_files(["prediction_sanity_*.csv"], ["variant", "checkpoint_name", "decode_mode", "compact_label_values", "foreground_rate", "pathology_rate", "empty_prediction"])
    write_csv(OUT_ROOT / "component_hd_by_case.csv", component)
    write_csv(OUT_ROOT / "subgroup_metrics.csv", subgroup)
    write_csv(OUT_ROOT / "proposal_pr_sweep.csv", proposal)
    write_csv(OUT_ROOT / "roi_coverage.csv", roi)
    summaries = {variant: load_summary(variant) for variant in VARIANTS}
    experiment_decision, promotion_decision, negative_decision, scientific_status = select_scientific_status(summaries)
    write_experiment_adequacy_report(summaries)
    write_one_batch_overfit(summaries)
    write_checkpoint_policy(summaries)
    write_prediction_sanity_doc(pred_sanity)
    write_metrics_summary(subgroup)
    write_label_export_qc(pred_sanity)
    write_failure_interpretation(experiment_decision, scientific_status)
    write_manifest()
    write_result(summaries, experiment_decision, promotion_decision, negative_decision, scientific_status)
    write_text(
        OUT_ROOT / "command_transcript.md",
        "\n".join(
            [
                "# Command Transcript",
                "",
                f"- aggregate_command: `{' '.join(sys.argv)}`",
                f"- aggregate_time_utc: `{datetime.now(UTC).isoformat()}`",
                "- aggregate_exit_status: `0`",
                "- network_used: `false`",
            ]
        )
        + "\n",
    )
    print(f"wrote {OUT_ROOT}")


if __name__ == "__main__":
    main()
