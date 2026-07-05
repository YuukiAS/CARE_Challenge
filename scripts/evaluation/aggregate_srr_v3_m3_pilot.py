#!/usr/bin/env python3
"""Aggregate SRR-v3 M3 minimum-effective pilot evidence."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import collect_case_metrics, read_case  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402


TASK_KEY = "20260705_srr_v3_m3_myops_min_effective_pilot_training"
TASK_PATH = f"prompts/tasks/{TASK_KEY}.md"
DEFAULT_OUT_ROOT = REPO_ROOT / "results" / TASK_KEY
DEFAULT_ANCHOR_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
MIN_OPTIMIZER_STEPS = 1200
MIN_TRAIN_LOOP_SECONDS = 1800.0
MIN_EVAL_CASES = 12


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def finite_float(value: object) -> float | None:
    try:
        val = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not np.isfinite(val):
        return None
    return val


def safe_mean(values: list[float | None]) -> float | None:
    vals = [value for value in values if value is not None]
    return float(mean(vals)) if vals else None


def compact_list(values: object) -> str:
    if isinstance(values, list):
        return ";".join(str(value) for value in values)
    return str(values)


def baseline_rows(eval_case_ids: list[str], anchor_root: Path) -> list[dict[str, object]]:
    metadata = load_myops_case_metadata()
    rows: list[dict[str, object]] = []
    for case_id in eval_case_ids:
        pred_path = anchor_root / "fold_0" / "validation" / f"{case_id}.nii.gz"
        if not pred_path.is_file():
            rows.append(
                {
                    "variant": "nnunet_fold0_anchor",
                    "case_id": case_id,
                    "metric_name": "evidence_not_found",
                    "source_path": str(pred_path),
                }
            )
            continue
        case = read_case(case_id, metadata)
        pred = sitk.GetArrayFromImage(sitk.ReadImage(str(pred_path))).astype(np.uint8, copy=False)
        for row in collect_case_metrics("nnunet_fold0_anchor", case, pred):
            row = dict(row)
            row["source_path"] = str(pred_path)
            rows.append(row)
    return rows


def copy_training_curves(variant_dir: Path, output_dir: Path) -> list[dict[str, str]]:
    rows = read_csv(variant_dir / "training_log.csv")
    write_csv(output_dir / "training_curves.csv", rows)
    return rows


def copy_validation_events(variant_dir: Path, output_dir: Path) -> list[dict[str, str]]:
    rows = read_csv(variant_dir / "validation_events.csv")
    write_csv(output_dir / "validation_events.csv", rows)
    return rows


def copy_prediction_sanity(variant_dir: Path, output_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(variant_dir.glob("prediction_sanity_*.csv")):
        for row in read_csv(path):
            copied = dict(row)
            copied["source_path"] = str(path)
            rows.append(copied)
    write_csv(output_dir / "prediction_sanity.csv", rows)
    return rows


def write_gate_residual_stats(
    training_rows: list[dict[str, str]],
    output_dir: Path,
    variant_dir: Path,
    eval_case_ids: list[str],
    anchor_root: Path,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    numeric_train = [row for row in training_rows if row.get("baseline_gate_mean") not in (None, "")]
    for key in ("baseline_gate_mean", "baseline_residual_abs_mean", "baseline_preserve_gate_mean"):
        values = [finite_float(row.get(key)) for row in numeric_train]
        rows.append(
            {
                "stat_scope": "training_log",
                "stat_name": key,
                "count": sum(value is not None for value in values),
                "mean": safe_mean(values),
                "min": min([value for value in values if value is not None], default=None),
                "max": max([value for value in values if value is not None], default=None),
                "source_path": str(variant_dir / "training_log.csv"),
            }
        )
    gate_values = [finite_float(row.get("baseline_gate_mean")) for row in numeric_train]
    open_values = [value for value in gate_values if value is not None and value > 0.01]
    rows.append(
        {
            "stat_scope": "training_log",
            "stat_name": "gate_open_rate_mean_gt_0.01",
            "count": len(gate_values),
            "mean": None if not gate_values else len(open_values) / max(1, len([v for v in gate_values if v is not None])),
            "min": None,
            "max": None,
            "source_path": str(variant_dir / "training_log.csv"),
        }
    )

    pred_dir = variant_dir / "predictions/fold_0/checkpoint_best/pathology_aware"
    metadata = load_myops_case_metadata()
    for case_id in eval_case_ids:
        srr_path = pred_dir / f"{case_id}.nii.gz"
        nn_path = anchor_root / "fold_0" / "validation" / f"{case_id}.nii.gz"
        if not srr_path.is_file() or not nn_path.is_file():
            rows.append(
                {
                    "stat_scope": "decode_delta",
                    "stat_name": f"{case_id}:missing_prediction",
                    "count": None,
                    "mean": None,
                    "min": None,
                    "max": None,
                    "source_path": f"{srr_path};{nn_path}",
                }
            )
            continue
        srr = sitk.GetArrayFromImage(sitk.ReadImage(str(srr_path))).astype(np.uint8, copy=False)
        nn = sitk.GetArrayFromImage(sitk.ReadImage(str(nn_path))).astype(np.uint8, copy=False)
        case = read_case(case_id, metadata)
        for cls, metric_name in ((5, "myops_scar"), (4, "myops_edema")):
            changed = int(np.logical_xor(srr == cls, nn == cls).sum())
            rows.append(
                {
                    "stat_scope": "decode_delta",
                    "stat_name": f"{case_id}:{metric_name}:changed_voxels_vs_nnunet",
                    "count": changed,
                    "mean": changed / max(1, int(case.label_arr.size)),
                    "min": None,
                    "max": None,
                    "source_path": f"{srr_path};{nn_path}",
                }
            )
    write_csv(output_dir / "gate_residual_stats.csv", rows)
    return rows


def write_same_split_help_harm(
    output_dir: Path,
    variant_dir: Path,
    eval_case_ids: list[str],
    variant: str,
    anchor_root: Path,
) -> list[dict[str, object]]:
    srr_rows = [
        row
        for row in read_csv(variant_dir / "component_hd_by_case_checkpoint_best.csv")
        if str(row.get("variant", "")).endswith("__checkpoint_best__pathology_aware")
    ]
    baseline = baseline_rows(eval_case_ids, anchor_root)
    by_key = {(row.get("case_id"), row.get("metric_name")): row for row in baseline}
    rows: list[dict[str, object]] = []
    for row in srr_rows:
        key = (row.get("case_id"), row.get("metric_name"))
        base = by_key.get(key, {})
        dice = finite_float(row.get("dice"))
        base_dice = finite_float(base.get("dice"))
        hd95 = finite_float(row.get("hd95"))
        base_hd95 = finite_float(base.get("hd95"))
        remote = finite_float(row.get("remote_fp_count"))
        base_remote = finite_float(base.get("remote_fp_count"))
        component = finite_float(row.get("component_count"))
        base_component = finite_float(base.get("component_count"))
        rows.append(
            {
                "variant": variant,
                "checkpoint_name": "checkpoint_best",
                "decode_mode": "pathology_aware",
                "case_id": row.get("case_id"),
                "center": row.get("center"),
                "modality_group": row.get("modality_group"),
                "t2_present": row.get("t2_present"),
                "class_id": row.get("class_id"),
                "metric_name": row.get("metric_name"),
                "srr_dice": dice,
                "nnunet_dice": base_dice,
                "dice_delta": None if dice is None or base_dice is None else dice - base_dice,
                "srr_hd95": hd95,
                "nnunet_hd95": base_hd95,
                "hd95_delta": None if hd95 is None or base_hd95 is None else hd95 - base_hd95,
                "srr_component_count": component,
                "nnunet_component_count": base_component,
                "component_count_delta": None if component is None or base_component is None else component - base_component,
                "srr_remote_fp_count": remote,
                "nnunet_remote_fp_count": base_remote,
                "remote_fp_delta": None if remote is None or base_remote is None else remote - base_remote,
                "srr_source_path": str(variant_dir / "component_hd_by_case_checkpoint_best.csv"),
                "nnunet_source_path": base.get("source_path", "evidence_not_found"),
            }
        )
    write_csv(output_dir / "same_split_help_harm.csv", rows)
    return rows


def write_hard_subgroup_metrics(output_dir: Path, help_harm_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups = {
        "all_cases": lambda row: True,
        "gt_positive_only": lambda row: finite_float(row.get("nnunet_dice")) not in (None, 1.0),
        "t2_present": lambda row: str(row.get("t2_present")).lower() == "true",
        "no_t2": lambda row: str(row.get("t2_present")).lower() != "true",
        "CenterC": lambda row: row.get("center") == "CenterC",
        "remote_fp_baseline_positive": lambda row: (finite_float(row.get("nnunet_remote_fp_count")) or 0.0) > 0.0,
    }
    rows: list[dict[str, object]] = []
    for metric_name in sorted({str(row.get("metric_name")) for row in help_harm_rows}):
        metric_rows = [row for row in help_harm_rows if row.get("metric_name") == metric_name]
        for group, predicate in groups.items():
            subset = [row for row in metric_rows if predicate(row)]
            if not subset:
                continue
            rows.append(
                {
                    "metric_name": metric_name,
                    "group": group,
                    "case_count": len({str(row.get("case_id")) for row in subset}),
                    "srr_dice_mean": safe_mean([finite_float(row.get("srr_dice")) for row in subset]),
                    "nnunet_dice_mean": safe_mean([finite_float(row.get("nnunet_dice")) for row in subset]),
                    "dice_delta_mean": safe_mean([finite_float(row.get("dice_delta")) for row in subset]),
                    "hd95_delta_mean": safe_mean([finite_float(row.get("hd95_delta")) for row in subset]),
                    "component_count_delta_mean": safe_mean([finite_float(row.get("component_count_delta")) for row in subset]),
                    "remote_fp_delta_mean": safe_mean([finite_float(row.get("remote_fp_delta")) for row in subset]),
                }
            )
    write_csv(output_dir / "hard_subgroup_metrics.csv", rows)
    return rows


def adequacy(summary: dict[str, object], pred_rows: list[dict[str, object]], help_harm_rows: list[dict[str, object]], proto: dict[str, object]) -> tuple[str, list[str]]:
    issues: list[str] = []
    if int(summary.get("actual_optimizer_steps") or 0) < MIN_OPTIMIZER_STEPS:
        issues.append("actual_optimizer_steps below 1200")
    if float(summary.get("train_loop_seconds") or 0.0) < MIN_TRAIN_LOOP_SECONDS:
        issues.append("train_loop_seconds below 1800")
    if int(summary.get("eval_cases") or 0) < MIN_EVAL_CASES:
        issues.append("eval_cases below 12")
    overfit = summary.get("one_batch_overfit") if isinstance(summary.get("one_batch_overfit"), dict) else {}
    if overfit.get("status") != "PASS":
        issues.append("one_batch_overfit did not pass")
    if summary.get("loss_decrease") is None or float(summary.get("loss_decrease") or 0.0) <= 0:
        issues.append("loss decrease not demonstrated")
    if not pred_rows:
        issues.append("prediction_sanity rows missing")
    no_t2_bad = [
        row for row in pred_rows if str(row.get("t2_present")).lower() != "true" and int(float(row.get("no_t2_edema_voxels") or 0)) > 0
    ]
    if no_t2_bad:
        issues.append("no-T2 prediction sanity has edema voxels")
    counts = proto.get("counts") if isinstance(proto.get("counts"), dict) else {}
    cats = proto.get("category_counts") if isinstance(proto.get("category_counts"), dict) else {}
    if int(counts.get("edema_positive") or 0) <= 0 or int(counts.get("edema_negative") or 0) <= 0:
        issues.append("prototype bank lacks edema positive/negative coverage")
    if int(cats.get("t2_present_edema_positive") or cats.get("t2_present_edema_positive_voxels") or 0) <= 0:
        issues.append("prototype bank lacks T2-present edema-positive voxels")
    if not help_harm_rows:
        issues.append("same-split nnU-Net help/harm missing")
    checkpoint_best = Path(str(summary.get("checkpoint_best", "")))
    checkpoint_final = Path(str(summary.get("checkpoint_final", "")))
    if not checkpoint_best.is_file() or not checkpoint_final.is_file():
        issues.append("checkpoint provenance paths missing")
    return ("PASS" if not issues else "FAIL", issues)


def write_reports(
    output_dir: Path,
    variant_dir: Path,
    variant: str,
    summary: dict[str, object],
    adequacy_decision: str,
    issues: list[str],
    command: str,
) -> None:
    train_ids = summary.get("train_case_ids", [])
    eval_ids = summary.get("eval_case_ids", [])
    write_text(
        output_dir / "pilot_training_config.md",
        "\n".join(
            [
                "# Pilot Training Config",
                "",
                f"task: `{TASK_PATH}`",
                f"variant: `{variant}`",
                f"model_variant: `{summary.get('model_variant')}`",
                f"fold: `{summary.get('fold')}`",
                f"device: `{summary.get('device')}`",
                f"encoder_profile: `{summary.get('encoder_profile')}`",
                f"encoder_scale_channels: `{summary.get('encoder_scale_channels')}`",
                "base_channels: `8` from training command; full scale channels are recorded above",
                f"patch_shape: derived from training command and summary; eval cases `{compact_list(eval_ids)}`",
                f"train_case_selection: `{summary.get('train_case_selection')}`",
                f"train_case_ids: `{compact_list(train_ids)}`",
                f"eval_case_selection: `{summary.get('eval_case_selection')}`",
                f"eval_case_ids: `{compact_list(eval_ids)}`",
                f"checkpoint_best: `{summary.get('checkpoint_best')}`",
                f"checkpoint_final: `{summary.get('checkpoint_final')}`",
                f"command: `{command}`",
                "",
                "Scope: controlled fold0 pilot subset, not full fold training, not route promotion, not validation packaging/upload.",
            ]
        )
        + "\n",
    )
    write_text(
        output_dir / "adequacy_check.md",
        "\n".join(
            [
                "# Adequacy Check",
                "",
                f"decision: `{adequacy_decision}`",
                "",
                "| requirement | value | status |",
                "| --- | ---: | --- |",
                f"| optimizer_steps >= {MIN_OPTIMIZER_STEPS} | {summary.get('actual_optimizer_steps')} | {'PASS' if int(summary.get('actual_optimizer_steps') or 0) >= MIN_OPTIMIZER_STEPS else 'FAIL'} |",
                f"| train_loop_seconds >= {MIN_TRAIN_LOOP_SECONDS:.0f} | {summary.get('train_loop_seconds')} | {'PASS' if float(summary.get('train_loop_seconds') or 0.0) >= MIN_TRAIN_LOOP_SECONDS else 'FAIL'} |",
                f"| eval_cases >= {MIN_EVAL_CASES} | {summary.get('eval_cases')} | {'PASS' if int(summary.get('eval_cases') or 0) >= MIN_EVAL_CASES else 'FAIL'} |",
                f"| one_batch_overfit | {(summary.get('one_batch_overfit') or {}).get('status') if isinstance(summary.get('one_batch_overfit'), dict) else 'evidence_not_found'} | {'PASS' if isinstance(summary.get('one_batch_overfit'), dict) and summary.get('one_batch_overfit', {}).get('status') == 'PASS' else 'FAIL'} |",
                f"| loss_decrease > 0 | {summary.get('loss_decrease')} | {'PASS' if summary.get('loss_decrease') is not None and float(summary.get('loss_decrease') or 0.0) > 0 else 'FAIL'} |",
                f"| same_split_help_harm | see `same_split_help_harm.csv` | {'PASS' if adequacy_decision == 'PASS' or 'same-split nnU-Net help/harm missing' not in issues else 'FAIL'} |",
                "",
                "issues: " + ("none" if not issues else "; ".join(issues)),
            ]
        )
        + "\n",
    )
    completion_state = "M3_READY_FOR_REVIEW" if adequacy_decision == "PASS" else "M3_NEEDS_EVIDENCE"
    write_text(
        output_dir / "completion_check.md",
        "\n".join(
            [
                "# Completion Check",
                "",
                f"`{completion_state}`",
                "",
                f"adequacy_decision: `{adequacy_decision}`",
                "review_status: `EXECUTED_UNAUDITED`",
                "M4 remains blocked until a separate read-only reviewer writes `M3_AUDITED_GO`.",
                "",
                "This executor did not write `review.md`, did not approve itself, did not package validation, did not upload, and did not start M4.",
            ]
        )
        + "\n",
    )
    write_text(
        output_dir / "review_request.md",
        "\n".join(
            [
                "# Review Request",
                "",
                "Please audit this M3 executor packet as a separate read-only review. `review.md` is intentionally absent at executor stop.",
                "",
                "Reviewer should verify minimum-effective training budget, one-batch overfit, loss decrease, prediction sanity including no-T2 edema safety, prototype T2-present coverage, gate/residual stats, same-split nnU-Net help/harm, hard subgroup metrics, and cache/provenance isolation.",
                "",
                "M4 remains blocked until a separate read-only reviewer writes `M3_AUDITED_GO`.",
            ]
        )
        + "\n",
    )
    write_text(
        output_dir / "result.md",
        "\n".join(
            [
                "# SRR-v3 M3 MyoPS Minimum-Effective Pilot Training Result",
                "",
                "status: `EXECUTED_UNAUDITED`",
                f"completion_state: `{'M3_READY_FOR_REVIEW' if adequacy_decision == 'PASS' else 'M3_NEEDS_EVIDENCE'}`",
                f"adequacy_decision: `{adequacy_decision}`",
                "",
                "## Summary",
                "",
                "Executed one controlled fold0 SRR-v3 pilot variant and aggregated the required M3 evidence. This is not full fold training, not challenge readiness, not route promotion, and not validation packaging/upload.",
                "",
                f"- optimizer_steps: `{summary.get('actual_optimizer_steps')}`",
                f"- train_loop_seconds: `{summary.get('train_loop_seconds')}`",
                f"- eval_cases: `{summary.get('eval_cases')}`",
                f"- validation_events: `{summary.get('validation_event_count')}`",
                f"- loss_decrease: `{summary.get('loss_decrease')}`",
                f"- checkpoint_best: `{summary.get('checkpoint_best')}`",
                "",
                "## Evidence",
                "",
                "- `training_curves.csv` and `validation_events.csv` summarize the pilot training loop.",
                "- `prediction_sanity.csv` records compact-label and no-T2 edema checks.",
                "- `gate_residual_stats.csv` records gate/residual means and decode deltas versus nnU-Net.",
                "- `prototype_bank_summary.json` records T2-present edema prototype coverage.",
                "- `same_split_help_harm.csv` and `hard_subgroup_metrics.csv` compare against same-split nnU-Net anchors.",
                "",
                "## Issues",
                "",
                "none" if not issues else "\n".join(f"- {issue}" for issue in issues),
            ]
        )
        + "\n",
    )


def write_manifest(output_dir: Path, variant_dir: Path, variant: str) -> None:
    files = [
        "result.md",
        "pilot_training_config.md",
        "training_curves.csv",
        "validation_events.csv",
        "prediction_sanity.csv",
        "gate_residual_stats.csv",
        "prototype_bank_summary.json",
        "same_split_help_harm.csv",
        "hard_subgroup_metrics.csv",
        "adequacy_check.md",
        "completion_check.md",
        "review_request.md",
        "MANIFEST.md",
        "commands_run.md",
        "slurm_status.md",
    ]
    lines = [
        "# MANIFEST",
        "",
        f"task: `{TASK_PATH}`",
        f"result_dir: `{output_dir}`",
        f"variant_dir: `{variant_dir}`",
        f"variant: `{variant}`",
        "",
        "| artifact | purpose |",
        "| --- | --- |",
    ]
    for file in files:
        lines.append(f"| `{file}` | M3 executor evidence packet |")
    lines.extend(
        [
            "",
            "Nested variant outputs contain checkpoints, prediction NIfTI files, logs, and runtime artifacts. They are intentionally not part of the committed lightweight review packet.",
        ]
    )
    write_text(output_dir / "MANIFEST.md", "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--variant", default="srr_v3_m3_shared_dual_dict_pilot")
    parser.add_argument("--anchor-root", type=Path, default=DEFAULT_ANCHOR_ROOT)
    parser.add_argument("--training-command", default="")
    args = parser.parse_args()

    output_dir = args.out_root if args.out_root.is_absolute() else REPO_ROOT / args.out_root
    variant_dir = output_dir / "variants" / args.variant
    summary = read_json(variant_dir / "summary.json")
    if not summary:
        raise FileNotFoundError(f"missing pilot summary: {variant_dir / 'summary.json'}")
    output_dir.mkdir(parents=True, exist_ok=True)
    eval_case_ids = [str(item) for item in summary.get("eval_case_ids", [])] if isinstance(summary.get("eval_case_ids"), list) else []
    training_rows = copy_training_curves(variant_dir, output_dir)
    copy_validation_events(variant_dir, output_dir)
    pred_rows = copy_prediction_sanity(variant_dir, output_dir)
    write_gate_residual_stats(training_rows, output_dir, variant_dir, eval_case_ids, args.anchor_root)
    help_harm_rows = write_same_split_help_harm(output_dir, variant_dir, eval_case_ids, args.variant, args.anchor_root)
    write_hard_subgroup_metrics(output_dir, help_harm_rows)
    proto = read_json(variant_dir / "prototype_bank_summary.json")
    (output_dir / "prototype_bank_summary.json").write_text(json.dumps(proto, indent=2, sort_keys=True), encoding="utf-8")
    decision, issues = adequacy(summary, pred_rows, help_harm_rows, proto)
    write_reports(output_dir, variant_dir, args.variant, summary, decision, issues, args.training_command)
    write_manifest(output_dir, variant_dir, args.variant)
    write_text(
        output_dir / "commands_run.md",
        "\n".join(
            [
                "# Commands Run",
                "",
                f"- training_command: `{args.training_command}`",
                f"- aggregate_command: `{' '.join(sys.argv)}`",
                f"- aggregate_time_utc: `{datetime.now(UTC).isoformat()}`",
                "- network_used: `false`",
            ]
        )
        + "\n",
    )
    print(json.dumps({"output_dir": str(output_dir), "adequacy_decision": decision, "issues": issues}, indent=2))
    if decision != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
