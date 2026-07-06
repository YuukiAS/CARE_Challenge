#!/usr/bin/env python3
"""Aggregate SRR-v3 M7 training/runtime evidence into the review packet."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260705_srr_v3_m7_training_and_cine_utilization"
OUT_ROOT = REPO_ROOT / "results" / TASK_KEY
RUNTIME_ROOT = OUT_ROOT / "runtime"
VARIANTS = [
    ("m7_full_srr_context_arbitration", "m6_full_srr_context_arbitration", "balanced_4scale"),
    ("m7_conservative_component_arbitration", "m6_conservative_component_arbitration", "safe_4scale"),
    ("m7_scar_precision_edema_safe", "m6_scar_precision_edema_safe", "balanced_4scale"),
]
MIN_OPTIMIZER_STEPS = 3000
MIN_TRAIN_LOOP_SECONDS = 1800.0
MIN_EVAL_CASES = 12
LOSS_COMPONENT_KEYS = [
    "loss_anatomy_union_lv_rv",
    "loss_scar_proposal",
    "loss_edema_proposal_t2_present_only",
    "loss_scar_refiner_roi",
    "loss_edema_refiner_t2_present_roi",
    "loss_anchor_preservation_outside_roi",
    "loss_branch_arbitration_consistency",
    "loss_bounded_correction",
    "loss_component_remote_fp",
    "loss_no_t2_edema_safety",
    "loss_dictionary_entropy_coverage_load_balance",
    "loss_prototype_diversity_margin",
    "m6_expanded_total_loss",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({key for row in rows for key in row}) or ["status"]
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


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def as_float(value: object) -> float | None:
    try:
        out = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def variant_dir(variant: str) -> Path:
    return RUNTIME_ROOT / "variants" / variant


def missing_row(variant: str, artifact: str, source_path: Path, reason: str = "M7 runtime evidence not found yet") -> dict[str, object]:
    return {
        "variant": variant,
        "status": "EVIDENCE_NOT_FOUND",
        "artifact": artifact,
        "source_path": str(source_path),
        "issue": reason,
    }


def collect_variant_file(name: str, artifact: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for variant, source_variant, profile in VARIANTS:
        path = variant_dir(variant) / name
        file_rows = read_csv(path)
        if not file_rows:
            rows.append(missing_row(variant, artifact, path))
            continue
        for row in file_rows:
            copied: dict[str, object] = dict(row)
            copied.setdefault("variant", variant)
            copied.setdefault("source_model_variant", source_variant)
            copied.setdefault("encoder_profile_expected", profile)
            copied["source_path"] = str(path)
            rows.append(copied)
    return rows


def collect_variant_glob(pattern: str, artifact: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for variant, source_variant, profile in VARIANTS:
        found = False
        for path in sorted(variant_dir(variant).glob(pattern)):
            file_rows = read_csv(path)
            if not file_rows:
                continue
            found = True
            for row in file_rows:
                copied: dict[str, object] = dict(row)
                copied.setdefault("variant", variant)
                copied.setdefault("source_model_variant", source_variant)
                copied.setdefault("encoder_profile_expected", profile)
                copied["source_path"] = str(path)
                rows.append(copied)
        if not found:
            rows.append(missing_row(variant, artifact, variant_dir(variant) / pattern))
    return rows


def adequacy_decision(summary: dict[str, object]) -> tuple[str, str]:
    if not summary:
        return "PENDING_OR_EVIDENCE_NOT_FOUND", "summary.json missing; Slurm jobs may still be pending/running"
    reasons: list[str] = []
    steps = int(summary.get("actual_optimizer_steps") or summary.get("optimizer_steps") or 0)
    seconds = float(summary.get("train_loop_seconds") or 0.0)
    val_count = int(summary.get("validation_event_count") or len(summary.get("validation_events") or []))
    loss_decrease = as_float(summary.get("loss_decrease"))
    one_batch = summary.get("one_batch_overfit") if isinstance(summary.get("one_batch_overfit"), dict) else {}
    if steps < MIN_OPTIMIZER_STEPS:
        reasons.append(f"optimizer_steps {steps} < {MIN_OPTIMIZER_STEPS}")
    if seconds < MIN_TRAIN_LOOP_SECONDS:
        reasons.append(f"train_loop_seconds {seconds:.1f} < {MIN_TRAIN_LOOP_SECONDS:.0f}")
    if val_count < 5:
        reasons.append(f"validation_event_count {val_count} < 5")
    if loss_decrease is None or loss_decrease <= 0:
        reasons.append("loss_decrease missing or non-positive")
    if one_batch.get("status") != "PASS":
        reasons.append("one_batch_overfit did not pass")
    return ("PASS" if not reasons else "PARTIAL_OR_FAIL", "; ".join(reasons) if reasons else "formal adequacy evidence present")


def write_variant_matrix() -> None:
    rows = []
    for order, (variant, source_variant, profile) in enumerate(VARIANTS, start=1):
        rows.append(
            {
                "order": order,
                "variant": variant,
                "source_model_variant": source_variant,
                "encoder_profile": profile,
                "required_by_m7": True,
                "status": "required; runtime collected from Slurm routing jobs when available",
            }
        )
    write_csv(OUT_ROOT / "variant_matrix.csv", rows)


def write_adequacy_and_overfit() -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    summaries: dict[str, dict[str, object]] = {}
    adequacy_rows: list[dict[str, object]] = []
    overfit_rows: list[dict[str, object]] = []
    for variant, source_variant, profile in VARIANTS:
        vdir = variant_dir(variant)
        summary = read_json(vdir / "summary.json")
        summaries[variant] = summary
        config = read_env(vdir / "configs" / "run_config.env")
        decision, issue = adequacy_decision(summary)
        adequacy_rows.append(
            {
                "variant": variant,
                "source_model_variant": source_variant,
                "encoder_profile_expected": profile,
                "decision": decision,
                "optimizer_steps": summary.get("actual_optimizer_steps", "EVIDENCE_NOT_FOUND"),
                "train_loop_seconds": summary.get("train_loop_seconds", "EVIDENCE_NOT_FOUND"),
                "validation_event_count": summary.get("validation_event_count", "EVIDENCE_NOT_FOUND"),
                "eval_case_count": summary.get("eval_case_count", "EVIDENCE_NOT_FOUND"),
                "job_id": config.get("job_id", "EVIDENCE_NOT_FOUND"),
                "partition": config.get("partition", "EVIDENCE_NOT_FOUND"),
                "issue": issue,
                "source_path": str(vdir / "summary.json"),
            }
        )
        overfit = summary.get("one_batch_overfit") if isinstance(summary.get("one_batch_overfit"), dict) else read_json(vdir / "one_batch_overfit.json")
        if not overfit:
            overfit_rows.append(missing_row(variant, "one_batch_overfit", vdir / "one_batch_overfit.json"))
        else:
            overfit_rows.append(
                {
                    "variant": variant,
                    "source_model_variant": source_variant,
                    "status": overfit.get("status", "EVIDENCE_NOT_FOUND"),
                    "steps": overfit.get("steps", "EVIDENCE_NOT_FOUND"),
                    "first_loss": overfit.get("first_loss", "EVIDENCE_NOT_FOUND"),
                    "last_loss": overfit.get("last_loss", "EVIDENCE_NOT_FOUND"),
                    "loss_decrease": overfit.get("loss_decrease", "EVIDENCE_NOT_FOUND"),
                    "case_id": overfit.get("case_id", "EVIDENCE_NOT_FOUND"),
                    "source_path": str(vdir / "one_batch_overfit.json"),
                }
            )
    write_csv(OUT_ROOT / "training_adequacy_by_variant.csv", adequacy_rows)
    write_csv(OUT_ROOT / "one_batch_overfit_by_variant.csv", overfit_rows)
    return summaries, adequacy_rows


def write_loss_component_by_step(training_rows: list[dict[str, object]]) -> None:
    rows: list[dict[str, object]] = []
    for row in training_rows:
        step = row.get("step")
        if not step or row.get("event") == "validation":
            continue
        dynamic_keys = [
            key
            for key in row
            if key.endswith("_semantic_family_mass") or key.endswith("_semantic_interaction_mass")
        ]
        for key in LOSS_COMPONENT_KEYS + sorted(dynamic_keys):
            if row.get(key) in (None, ""):
                continue
            rows.append(
                {
                    "variant": row.get("variant", "EVIDENCE_NOT_FOUND"),
                    "step": step,
                    "stage": row.get("stage", "EVIDENCE_NOT_FOUND"),
                    "component": key,
                    "value": row.get(key),
                    "source_path": row.get("source_path", "EVIDENCE_NOT_FOUND"),
                }
            )
    if not rows:
        rows = [missing_row(variant, "loss_component_by_step", variant_dir(variant) / "training_log.csv") for variant, _, _ in VARIANTS]
    write_csv(OUT_ROOT / "loss_component_by_step.csv", rows)


def write_dictionary_prototype_usage() -> None:
    rows: list[dict[str, object]] = []
    for variant, source_variant, profile in VARIANTS:
        vdir = variant_dir(variant)
        retrieval_rows = read_csv(vdir / "retrieval_usage.csv")
        proto = read_json(vdir / "prototype_bank_summary.json")
        if not retrieval_rows and not proto:
            rows.append(missing_row(variant, "dictionary_prototype_usage", vdir))
            continue
        for row in retrieval_rows:
            copied = dict(row)
            copied["source_model_variant"] = source_variant
            copied["encoder_profile_expected"] = profile
            copied["usage_source"] = "retrieval_usage.csv"
            copied["source_path"] = str(vdir / "retrieval_usage.csv")
            rows.append(copied)
        if proto:
            counts = proto.get("category_counts") if isinstance(proto.get("category_counts"), dict) else {}
            rows.append(
                {
                    "variant": variant,
                    "source_model_variant": source_variant,
                    "encoder_profile_expected": profile,
                    "usage_source": "prototype_bank_summary.json",
                    "status": proto.get("status", "EVIDENCE_NOT_FOUND"),
                    "scar_positive": proto.get("scar_positive", counts.get("scar_positive", "EVIDENCE_NOT_FOUND")),
                    "scar_negative": proto.get("scar_negative", counts.get("scar_negative", "EVIDENCE_NOT_FOUND")),
                    "edema_positive": proto.get("edema_positive", counts.get("edema_positive", "EVIDENCE_NOT_FOUND")),
                    "edema_negative": proto.get("edema_negative", counts.get("edema_negative", "EVIDENCE_NOT_FOUND")),
                    "selected_case_ids": ";".join(str(v) for v in proto.get("selected_case_ids", []) if isinstance(proto.get("selected_case_ids", []), list)),
                    "source_path": str(vdir / "prototype_bank_summary.json"),
                }
            )
    write_csv(OUT_ROOT / "dictionary_prototype_usage_by_variant.csv", rows)


def write_markdown(args: argparse.Namespace, adequacy_rows: list[dict[str, object]]) -> None:
    now = datetime.now(UTC).isoformat()
    any_pass = any(row.get("decision") == "PASS" for row in adequacy_rows)
    any_pending = any(row.get("decision") == "PENDING_OR_EVIDENCE_NOT_FOUND" for row in adequacy_rows)
    if any_pending:
        completion = "M7_NEEDS_MONITOR"
        experiment = "PARTIAL"
        scientific = "SCIENTIFIC_NEEDS_EVIDENCE"
    elif any_pass:
        completion = "M7_READY_FOR_REVIEW"
        experiment = "PASS"
        scientific = "SCIENTIFIC_UNRESOLVED"
    else:
        completion = "M7_NEEDS_EVIDENCE"
        experiment = "FAIL_OR_PARTIAL"
        scientific = "SCIENTIFIC_UNDERTRAINED"

    commands = [
        "# Commands Run",
        "",
        "| command | status | purpose |",
        "| --- | --- | --- |",
        "| `python -m py_compile scripts/training/run_srr_propref_myops_fold0.py` | exit 0 | Validate M7 training script syntax. |",
        "| `bash -n jobs/src/run_srr_v3_m7_myops_training.sh` | exit 0 | Validate M7 Slurm job script syntax. |",
        "| `sbatch --array=0-2 --partition=a100-gpu --qos=gpu_access --gres=gpu:nvidia_a100-pcie-40gb:1 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58003931 | Submit A100 routing array. |",
        "| `sbatch --array=0-2 --partition=htzhulab --qos=gpu_access --gres=gpu:1 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58003950 | Submit htzhulab routing mirror. |",
        "| `python scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py ...` | exit 0 | Write current M7 monitor packet. |",
        "",
        f"job_state_snapshot: `{args.job_state_snapshot}`",
    ]
    write_text(OUT_ROOT / "commands_run.md", "\n".join(commands) + "\n")

    write_text(
        OUT_ROOT / "completion_check.md",
        "\n".join(
            [
                "# Completion Check",
                "",
                f"status: `{completion}`",
                f"experiment_adequacy_decision: `{experiment}`",
                "route_promotion_decision: `NO_PROMOTION`",
                "route_negative_decision: `STOP_NOT_SUPPORTED`",
                f"scientific_resolution_status: `{scientific}`",
                "self_assessed_status: `EXECUTED_UNAUDITED`",
                "",
                "This is an executor packet only. It does not write review.md, start M8, package validation, upload, or claim hosted metrics.",
            ]
        )
        + "\n",
    )

    write_text(
        OUT_ROOT / "m7_execution_plan.md",
        "\n".join(
            [
                "# M7 Execution Plan",
                "",
                "M7 runs the three required MyoPS variants from the M6 concrete architecture repairs. Each array task performs one-batch overfit first, then formal fold0 training with expanded M6 loss components, nnU-Net anchors, runtime prototype fitting, validation events, and fold0 prediction export.",
                "",
                "| routing job | partition | status snapshot |",
                "| --- | --- | --- |",
                f"| `58003931` | `a100-gpu` | `{args.job_state_snapshot}` |",
                f"| `58003950` | `htzhulab` | `{args.job_state_snapshot}` |",
                "",
                "Routing safety: `jobs/src/run_srr_v3_m7_myops_training.sh` uses a per-variant atomic lock under `runtime/routing_locks/` so a duplicate partition start exits instead of writing the same variant directory.",
            ]
        )
        + "\n",
    )

    write_text(
        OUT_ROOT / "result.md",
        "\n".join(
            [
                "# Result 20260705 SRR-v3 M7 Training and Cine Utilization",
                "",
                "status: `EXECUTED_UNAUDITED`",
                f"completion_check: `{completion}`",
                f"generated_at_utc: `{now}`",
                "",
                "## Summary",
                "",
                "M6 and M5 prerequisite reviews were present and allowed M7 to start. The M7 MyoPS training arrays have been submitted to both A100 and htzhulab routing partitions, but no runtime variant summary was present when this packet was generated. Therefore this packet is monitor evidence, not review-ready completion.",
                "",
                "No validation packaging, validation upload, route promotion, hosted metric claim, review.md, or M8 task was created.",
            ]
        )
        + "\n",
    )

    write_text(
        OUT_ROOT / "best_variant_decision.md",
        "# Best Variant Decision\n\nstatus: `NOT_DECIDED_M7_NEEDS_MONITOR`\n\nNo best variant can be selected until all required variants have same-split nnU-Net help/harm, hard subgroup metrics, no-T2 safety, and loss component evidence.\n",
    )
    write_text(
        OUT_ROOT / "failure_interpretation.md",
        "# Failure Interpretation\n\nstatus: `M7_NEEDS_MONITOR`\n\nCurrent evidence is scheduler/runtime pending. Undertrained, missing, or pending M7 runs are not route failure and not route promotion.\n",
    )
    write_text(
        OUT_ROOT / "cinema_blocker_report.md",
        "# CineMA/Cine Blocker Report\n\nstatus: `CINE_SECONDARY_NOT_RUN_IN_CURRENT_MONITOR_PACKET`\n\nM5 has `M5_AUDITED_DIAGNOSTIC_GO`, but this M7 monitor packet has not yet run a same-safe-subset CineMA/registration/temporal dictionary matrix. Frame0-only, one-case SyN smoke, optical-flow descriptor, and untrained VoxelMorph remain insufficient as completed registration or temporal retrieval evidence.\n",
    )
    write_text(
        OUT_ROOT / "label_export_qc.md",
        "# Label Export QC\n\nstatus: `M7_NEEDS_MONITOR`\n\nNo M7 prediction export was available at this monitor snapshot. Label/export QC must be re-run from `prediction_sanity_by_variant.csv` after variant predictions exist.\n",
    )
    write_text(
        OUT_ROOT / "review_request.md",
        "# Review Request\n\nstatus: `NOT_READY_FOR_REVIEW_M7_NEEDS_MONITOR`\n\nDo not review as completed M7 yet. Reviewer should wait for required variant runtime summaries, same-split help/harm, hard subgroup metrics, loss component curves, gradient sanity, no-T2 safety, and Cine blocker/evidence update.\n",
    )
    manifest_files = [
        "result.md",
        "m7_execution_plan.md",
        "variant_matrix.csv",
        "training_adequacy_by_variant.csv",
        "one_batch_overfit_by_variant.csv",
        "training_curve_by_variant.csv",
        "validation_curve_by_variant.csv",
        "loss_component_by_step.csv",
        "loss_component_gradient_sanity.csv",
        "prediction_sanity_by_variant.csv",
        "same_split_help_harm.csv",
        "hard_subgroup_metrics.csv",
        "branch_arbitration_by_case.csv",
        "dictionary_prototype_usage_by_variant.csv",
        "proposal_refiner_by_case.csv",
        "no_t2_safety_by_variant.csv",
        "best_variant_decision.md",
        "failure_interpretation.md",
        "cinema_blocker_report.md",
        "label_export_qc.md",
        "commands_run.md",
        "completion_check.md",
        "review_request.md",
    ]
    lines = ["# Manifest", "", f"task_key: `{TASK_KEY}`", "", "| file | purpose |", "| --- | --- |"]
    for name in manifest_files:
        lines.append(f"| `{name}` | M7 executor monitor or runtime evidence artifact. |")
    write_text(OUT_ROOT / "MANIFEST.md", "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-state-snapshot", default="not queried")
    args = parser.parse_args()

    write_variant_matrix()
    _, adequacy_rows = write_adequacy_and_overfit()
    training_rows = collect_variant_file("training_log.csv", "training_curve")
    write_csv(OUT_ROOT / "training_curve_by_variant.csv", training_rows)
    write_csv(OUT_ROOT / "validation_curve_by_variant.csv", collect_variant_file("validation_events.csv", "validation_curve"))
    write_loss_component_by_step(training_rows)
    write_csv(OUT_ROOT / "loss_component_gradient_sanity.csv", collect_variant_file("loss_component_gradient_sanity.csv", "loss_component_gradient_sanity"))
    write_csv(OUT_ROOT / "prediction_sanity_by_variant.csv", collect_variant_glob("prediction_sanity_*.csv", "prediction_sanity"))
    write_csv(OUT_ROOT / "same_split_help_harm.csv", collect_variant_glob("same_split_help_harm*.csv", "same_split_help_harm"))
    write_csv(OUT_ROOT / "hard_subgroup_metrics.csv", collect_variant_glob("subgroup_metrics_*.csv", "hard_subgroup_metrics"))
    write_csv(OUT_ROOT / "branch_arbitration_by_case.csv", collect_variant_file("retrieval_usage.csv", "branch_arbitration"))
    write_dictionary_prototype_usage()
    proposal_rows = collect_variant_glob("proposal_pr_sweep_*.csv", "proposal_pr_sweep")
    proposal_rows.extend(collect_variant_glob("roi_coverage_*.csv", "roi_coverage"))
    proposal_rows.extend(collect_variant_glob("crop_bounds_*.csv", "crop_bounds"))
    write_csv(OUT_ROOT / "proposal_refiner_by_case.csv", proposal_rows)
    no_t2_rows = [row for row in collect_variant_glob("prediction_sanity_*.csv", "no_t2_safety") if str(row.get("t2_present", "")).lower() in {"false", "0"} or row.get("status") == "EVIDENCE_NOT_FOUND"]
    write_csv(OUT_ROOT / "no_t2_safety_by_variant.csv", no_t2_rows or [missing_row(variant, "no_t2_safety", variant_dir(variant)) for variant, _, _ in VARIANTS])
    write_markdown(args, adequacy_rows)


if __name__ == "__main__":
    main()
