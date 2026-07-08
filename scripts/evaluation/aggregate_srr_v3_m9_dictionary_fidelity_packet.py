#!/usr/bin/env python3
"""Aggregate lightweight M9 SRR dictionary fidelity evidence."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


REQUIRED_OUTPUT_DIR = Path("results/20260708_srr_v3_m9_dictionary_fidelity_repair_training")
M8_ANCHOR_METRICS = Path(
    "results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_nnunet_anchor_control_metrics.csv"
)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_summary(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_float(value: object) -> float | None:
    try:
        if value in {None, ""}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def variant_dirs(runtime_roots: list[Path]) -> list[tuple[Path, Path]]:
    found: list[tuple[Path, Path]] = []
    for runtime_root in runtime_roots:
        found.extend((runtime_root, path) for path in sorted(runtime_root.glob("variants/*")) if path.is_dir())
    return found


def concat_variant_files(
    runtime_roots: list[Path],
    patterns: list[str],
    fallback_fieldnames: list[str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for runtime_root, variant_dir in variant_dirs(runtime_roots):
        for pattern in patterns:
            for path in sorted(variant_dir.glob(pattern)):
                for row in read_csv(path):
                    out = dict(row)
                    out.setdefault("candidate_id", variant_dir.name)
                    out["runtime_root"] = str(runtime_root)
                    out["source_path"] = str(path)
                    rows.append(out)
    if rows:
        return rows
    return [{name: "EVIDENCE_NOT_FOUND" for name in fallback_fieldnames}]


def dynamic_fieldnames(rows: list[dict[str, object]], preferred: list[str]) -> list[str]:
    fields: list[str] = []
    for name in preferred:
        if name not in fields:
            fields.append(name)
    for row in rows:
        for name in row:
            if name not in fields:
                fields.append(name)
    return fields


def write_dynamic_csv(path: Path, rows: list[dict[str, object]], preferred: list[str]) -> None:
    write_csv(path, rows, dynamic_fieldnames(rows, preferred))


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def summarize_pattern_rows(pattern_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    if not pattern_rows or pattern_rows[0].get("candidate_id") == "EVIDENCE_NOT_FOUND":
        fallback = [
            {
                "candidate_id": "EVIDENCE_NOT_FOUND",
                "semantic_task": "EVIDENCE_NOT_FOUND",
                "slot_group": "EVIDENCE_NOT_FOUND",
                "status": "EVIDENCE_NOT_FOUND",
            }
        ]
        return fallback, fallback, fallback

    groups: dict[tuple[str, str, str, str, str, str], list[dict[str, object]]] = {}
    for row in pattern_rows:
        key = (
            str(row.get("candidate_id", row.get("variant", ""))),
            str(row.get("semantic_task", row.get("task", ""))),
            str(row.get("slot_group", "")),
            str(row.get("slot_kind", "")),
            str(row.get("slot_modality", "")),
            str(row.get("expert_index", "")),
        )
        groups.setdefault(key, []).append(row)

    usage_rows: list[dict[str, object]] = []
    stability_rows: list[dict[str, object]] = []
    gamma_rows: list[dict[str, object]] = []
    grouped_for_gamma: dict[tuple[str, str, str, str, str], list[dict[str, object]]] = {}
    for (candidate, semantic_task, slot_group, slot_kind, slot_modality, expert_index), rows in sorted(groups.items()):
        weights = [as_float(row.get("mean_weight")) for row in rows]
        weights = [value for value in weights if value is not None]
        valid = [as_float(row.get("valid_fraction")) for row in rows]
        valid = [value for value in valid if value is not None]
        steps = {str(row.get("step", "")) for row in rows if row.get("step", "") != ""}
        cases: set[str] = set()
        for row in rows:
            for case_id in str(row.get("batch_cases", "")).split(","):
                if case_id:
                    cases.add(case_id)
        mean_weight = statistics.mean(weights) if weights else 0.0
        p95_weight = percentile(weights, 0.95)
        min_weight = min(weights) if weights else 0.0
        max_weight = max(weights) if weights else 0.0
        usage = {
            "candidate_id": candidate,
            "semantic_task": semantic_task,
            "slot_group": slot_group,
            "slot_kind": slot_kind,
            "slot_modality": slot_modality,
            "expert_index": expert_index,
            "row_count": len(rows),
            "step_count": len(steps),
            "case_count": len(cases),
            "mean_weight": mean_weight,
            "p95_weight": p95_weight,
            "min_weight": min_weight,
            "max_weight": max_weight,
            "mean_valid_fraction": statistics.mean(valid) if valid else 0.0,
        }
        usage_rows.append(usage)
        stability_rows.append(
            {
                **usage,
                "weight_range": max_weight - min_weight,
                "stability_status": "STABLE_NONZERO" if mean_weight > 0 and (max_weight - min_weight) < 0.5 else "REQUIRES_REVIEW",
            }
        )
        grouped_for_gamma.setdefault((candidate, semantic_task, slot_group, slot_kind, slot_modality), []).append(usage)

    for (candidate, semantic_task, slot_group, slot_kind, slot_modality), rows in sorted(grouped_for_gamma.items()):
        active = [row for row in rows if as_float(row.get("mean_weight")) and (as_float(row.get("mean_weight")) or 0.0) > 0.01]
        gamma_rows.append(
            {
                "candidate_id": candidate,
                "semantic_task": semantic_task,
                "slot_group": slot_group,
                "slot_kind": slot_kind,
                "slot_modality": slot_modality,
                "expert_count": len(rows),
                "active_expert_count_soft_gamma": len(active),
                "mean_active_weight": statistics.mean([float(row["mean_weight"]) for row in active]) if active else 0.0,
                "status": "RUNTIME_SUMMARY_FROM_RETRIEVAL_USAGE",
            }
        )
    return usage_rows, stability_rows, gamma_rows


def parse_context_variant(value: str) -> tuple[str, str, str]:
    if "__" not in value:
        return value, "EVIDENCE_NOT_FOUND", "EVIDENCE_NOT_FOUND"
    parts = value.split("__")
    if len(parts) >= 3:
        return "__".join(parts[:-2]), parts[-2], parts[-1]
    return value, "EVIDENCE_NOT_FOUND", "EVIDENCE_NOT_FOUND"


def anchor_lookup() -> dict[tuple[str, str], dict[str, str]]:
    rows = read_csv(M8_ANCHOR_METRICS)
    return {(row.get("case_id", ""), row.get("metric_name", "")): row for row in rows}


def same_split_help_harm(component_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    anchor = anchor_lookup()
    rows: list[dict[str, object]] = []
    for row in component_rows:
        if row.get("variant") == "EVIDENCE_NOT_FOUND":
            continue
        case_id = str(row.get("case_id", ""))
        metric_name = str(row.get("metric_name", ""))
        base = anchor.get((case_id, metric_name))
        candidate, checkpoint_name, decode_mode = parse_context_variant(str(row.get("variant", row.get("candidate_id", ""))))
        if not base:
            rows.append(
                {
                    "candidate_id": candidate,
                    "checkpoint_name": checkpoint_name,
                    "decode_mode": decode_mode,
                    "case_id": case_id,
                    "metric_name": metric_name,
                    "m9_dice": row.get("dice", "EVIDENCE_NOT_FOUND"),
                    "nnunet_dice": "EVIDENCE_NOT_FOUND",
                    "dice_delta": "EVIDENCE_NOT_FOUND",
                    "m9_hd95": row.get("hd95", "EVIDENCE_NOT_FOUND"),
                    "nnunet_hd95": "EVIDENCE_NOT_FOUND",
                    "hd95_delta": "EVIDENCE_NOT_FOUND",
                    "m9_remote_fp_count": row.get("remote_fp_count", "EVIDENCE_NOT_FOUND"),
                    "nnunet_remote_fp_count": "EVIDENCE_NOT_FOUND",
                    "remote_fp_delta": "EVIDENCE_NOT_FOUND",
                    "source_path": row.get("source_path", "EVIDENCE_NOT_FOUND"),
                }
            )
            continue
        m9_dice = as_float(row.get("dice"))
        nn_dice = as_float(base.get("dice"))
        m9_hd95 = as_float(row.get("hd95"))
        nn_hd95 = as_float(base.get("hd95"))
        m9_remote = as_float(row.get("remote_fp_count"))
        nn_remote = as_float(base.get("remote_fp_count"))
        rows.append(
            {
                "candidate_id": candidate,
                "checkpoint_name": checkpoint_name,
                "decode_mode": decode_mode,
                "case_id": case_id,
                "center": base.get("center", row.get("center", "")),
                "modality_group": base.get("modality_group", ""),
                "t2_present": base.get("t2_present", ""),
                "class_id": row.get("class_id", base.get("class_id", "")),
                "metric_name": metric_name,
                "m9_dice": row.get("dice", ""),
                "nnunet_dice": base.get("dice", ""),
                "dice_delta": "" if m9_dice is None or nn_dice is None else m9_dice - nn_dice,
                "m9_hd95": row.get("hd95", ""),
                "nnunet_hd95": base.get("hd95", ""),
                "hd95_delta": "" if m9_hd95 is None or nn_hd95 is None else m9_hd95 - nn_hd95,
                "m9_component_count": row.get("component_count", ""),
                "nnunet_component_count": base.get("component_count", ""),
                "m9_remote_fp_count": row.get("remote_fp_count", ""),
                "nnunet_remote_fp_count": base.get("remote_fp_count", ""),
                "remote_fp_delta": "" if m9_remote is None or nn_remote is None else m9_remote - nn_remote,
                "source_path": row.get("source_path", "EVIDENCE_NOT_FOUND"),
                "anchor_source": str(M8_ANCHOR_METRICS),
            }
        )
    if rows:
        return rows
    return [
        {
            "candidate_id": "EVIDENCE_NOT_FOUND",
            "checkpoint_name": "EVIDENCE_NOT_FOUND",
            "decode_mode": "EVIDENCE_NOT_FOUND",
            "case_id": "EVIDENCE_NOT_FOUND",
            "metric_name": "EVIDENCE_NOT_FOUND",
            "m9_dice": "EVIDENCE_NOT_FOUND",
            "nnunet_dice": "EVIDENCE_NOT_FOUND",
            "dice_delta": "EVIDENCE_NOT_FOUND",
        }
    ]


def select_metric_checkpoint(help_harm_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for row in help_harm_rows:
        if row.get("candidate_id") == "EVIDENCE_NOT_FOUND":
            continue
        key = (str(row.get("candidate_id", "")), str(row.get("checkpoint_name", "")), str(row.get("decode_mode", "")))
        grouped.setdefault(key, []).append(row)
    selected: list[dict[str, object]] = []
    by_candidate: dict[str, list[dict[str, object]]] = {}
    for (candidate, checkpoint, decode), rows in grouped.items():
        dice_deltas = [as_float(row.get("dice_delta")) for row in rows]
        hd_deltas = [as_float(row.get("hd95_delta")) for row in rows]
        remote_deltas = [as_float(row.get("remote_fp_delta")) for row in rows]
        dice = [value for value in dice_deltas if value is not None]
        hd = [value for value in hd_deltas if value is not None]
        remote = [value for value in remote_deltas if value is not None]
        if not dice:
            continue
        score = statistics.mean(dice) - 0.001 * statistics.mean(hd or [0.0]) - 0.002 * statistics.mean(remote or [0.0])
        by_candidate.setdefault(candidate, []).append(
            {
                "candidate_id": candidate,
                "selection_metric": "m9_metric_aligned_composite_dice_hd95_remote_fp",
                "selected_checkpoint": checkpoint,
                "decode_mode": decode,
                "status": "M9_POST_JOB_METRIC_ALIGNED_SELECTION_FROM_RUNTIME",
                "mean_dice_delta": statistics.mean(dice),
                "mean_hd95_delta": statistics.mean(hd or [0.0]),
                "mean_remote_fp_delta": statistics.mean(remote or [0.0]),
                "composite_score": score,
                "case_metric_rows": len(rows),
            }
        )
    for candidate, candidate_rows in sorted(by_candidate.items()):
        selected.append(max(candidate_rows, key=lambda row: as_float(row.get("composite_score")) or float("-inf")))
    if selected:
        return selected
    return [
        {
            "candidate_id": "EVIDENCE_NOT_FOUND",
            "selection_metric": "EVIDENCE_NOT_FOUND",
            "selected_checkpoint": "EVIDENCE_NOT_FOUND",
            "decode_mode": "EVIDENCE_NOT_FOUND",
            "status": "EVIDENCE_NOT_FOUND",
        }
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-root",
        action="append",
        default=[],
        help="Runtime root to scan; may be repeated. Defaults to runtime and runtime_* under the output directory.",
    )
    parser.add_argument("--out-dir", default=str(REQUIRED_OUTPUT_DIR))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runtime_roots = [Path(item) for item in args.runtime_root]
    if not runtime_roots:
        candidates = [out_dir / "runtime"]
        candidates.extend(sorted(out_dir.glob("runtime_*")))
        runtime_roots = []
        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                runtime_roots.append(candidate)
                seen.add(resolved)

    summary_rows: list[dict[str, object]] = []
    for runtime_root, variant_dir in variant_dirs(runtime_roots):
        for summary_path in sorted(variant_dir.glob("summary.json")):
            summary = load_summary(summary_path)
            variant = str(summary.get("variant", summary_path.parent.name))
            summary_rows.append(
                {
                    "candidate_id": variant,
                    "runtime_root": str(runtime_root),
                    "summary_path": str(summary_path),
                    "actual_optimizer_steps": summary.get("actual_optimizer_steps", "EVIDENCE_NOT_FOUND"),
                    "train_loop_seconds": summary.get("train_loop_seconds", summary.get("elapsed_seconds", "EVIDENCE_NOT_FOUND")),
                    "checkpoint_selection_mode": summary.get("checkpoint_selection_mode", "EVIDENCE_NOT_FOUND"),
                    "checkpoint_selection_status": summary.get("checkpoint_selection_status", "EVIDENCE_NOT_FOUND"),
                    "checkpoint_best": summary.get("checkpoint_best", "EVIDENCE_NOT_FOUND"),
                }
            )

    if not summary_rows:
        summary_rows.append(
            {
                "candidate_id": "EVIDENCE_NOT_FOUND",
                "runtime_root": ";".join(str(path) for path in runtime_roots),
                "summary_path": "EVIDENCE_NOT_FOUND",
                "actual_optimizer_steps": "EVIDENCE_NOT_FOUND",
                "train_loop_seconds": "EVIDENCE_NOT_FOUND",
                "checkpoint_selection_mode": "EVIDENCE_NOT_FOUND",
                "checkpoint_selection_status": "EVIDENCE_NOT_FOUND",
                "checkpoint_best": "EVIDENCE_NOT_FOUND",
            }
        )
    write_csv(
        out_dir / "m9_training_budget_ledger.csv",
        summary_rows,
        [
            "candidate_id",
            "runtime_root",
            "summary_path",
            "actual_optimizer_steps",
            "train_loop_seconds",
            "checkpoint_selection_mode",
            "checkpoint_selection_status",
            "checkpoint_best",
        ],
    )
    component_rows = concat_variant_files(
        runtime_roots,
        ["component_hd_by_case_*.csv"],
        ["candidate_id", "variant", "case_id", "metric_name", "dice", "hd95", "component_count", "remote_fp_count"],
    )
    subgroup_rows = concat_variant_files(
        runtime_roots,
        ["subgroup_metrics_*.csv"],
        ["candidate_id", "variant", "metric_name", "group", "dice_mean", "hd95_mean", "component_count_mean", "remote_fp_mean"],
    )
    proposal_rows = concat_variant_files(
        runtime_roots,
        ["proposal_pr_sweep_*.csv"],
        [
            "candidate_id",
            "variant",
            "case_id",
            "metric_name",
            "proposal_threshold",
            "proposal_recall",
            "proposal_precision",
            "lesion_wise_recall",
            "outside_myocardium_fp_ratio",
        ],
    )
    roi_rows = concat_variant_files(
        runtime_roots,
        ["roi_coverage_*.csv"],
        ["candidate_id", "variant", "case_id", "metric_name", "gt_coverage", "outside_myocardium_roi_ratio"],
    )
    train_rows = concat_variant_files(
        runtime_roots,
        ["training_log.csv"],
        ["candidate_id", "variant", "step", "stage", "loss", "elapsed_seconds"],
    )
    validation_rows = concat_variant_files(
        runtime_roots,
        ["validation_events.csv"],
        ["candidate_id", "variant", "step", "stage", "val_patch_loss", "elapsed_seconds"],
    )
    gradient_rows = concat_variant_files(
        runtime_roots,
        ["loss_component_gradient_sanity.csv"],
        ["candidate_id", "variant", "component", "grad_norm", "status"],
    )
    pattern_rows = concat_variant_files(
        runtime_roots,
        ["retrieval_usage.csv"],
        ["candidate_id", "variant", "step", "task", "expert_index", "mean_weight", "batch_cases"],
    )
    pattern_usage_rows, pattern_stability_rows, pattern_gamma_rows = summarize_pattern_rows(pattern_rows)
    prototype_rows = concat_variant_files(
        runtime_roots,
        ["prototype_update_sanity_formal.csv", "prototype_update_sanity.csv"],
        ["candidate_id", "variant", "parameter", "grad_norm", "update_norm"],
    )
    hardneg_rows = concat_variant_files(
        runtime_roots,
        ["hardneg_memory.csv"],
        ["candidate_id", "variant", "memory_source", "case_count", "component_count"],
    )
    help_harm_rows = same_split_help_harm(component_rows)
    checkpoint_rows = select_metric_checkpoint(help_harm_rows)
    if checkpoint_rows[0].get("candidate_id") == "EVIDENCE_NOT_FOUND":
        checkpoint_rows = [
            {
                "candidate_id": row["candidate_id"],
                "selection_metric": row["checkpoint_selection_mode"],
                "selected_checkpoint": row["checkpoint_best"],
                "decode_mode": "EVIDENCE_NOT_FOUND",
                "status": row["checkpoint_selection_status"],
            }
            for row in summary_rows
        ]

    write_dynamic_csv(out_dir / "m9_metric_aligned_checkpoint_selection.csv", checkpoint_rows, ["candidate_id", "selection_metric", "selected_checkpoint", "decode_mode", "status"])
    write_dynamic_csv(out_dir / "m9_training_curves.csv", train_rows, ["candidate_id", "variant", "step", "stage", "loss", "elapsed_seconds"])
    write_dynamic_csv(out_dir / "m9_validation_events.csv", validation_rows, ["candidate_id", "variant", "step", "stage", "val_patch_loss", "elapsed_seconds"])
    write_dynamic_csv(out_dir / "m9_loss_component_gradient_sanity.csv", gradient_rows, ["candidate_id", "variant", "component", "grad_norm", "status"])
    pattern_preferred = [
        "candidate_id",
        "semantic_task",
        "slot_group",
        "slot_kind",
        "slot_modality",
        "expert_index",
        "row_count",
        "step_count",
        "case_count",
        "mean_weight",
        "p95_weight",
        "min_weight",
        "max_weight",
        "mean_valid_fraction",
    ]
    write_dynamic_csv(out_dir / "m9_pattern_sip_usage_by_group.csv", pattern_usage_rows, pattern_preferred)
    write_dynamic_csv(out_dir / "m9_dictionary_slot_group_stability.csv", pattern_stability_rows, pattern_preferred + ["weight_range", "stability_status"])
    write_dynamic_csv(
        out_dir / "m9_integrativeness_gamma_soft.csv",
        pattern_gamma_rows,
        [
            "candidate_id",
            "semantic_task",
            "slot_group",
            "slot_kind",
            "slot_modality",
            "expert_count",
            "active_expert_count_soft_gamma",
            "mean_active_weight",
            "status",
        ],
    )
    write_dynamic_csv(out_dir / "m9_prototype_update_ledger.csv", prototype_rows, ["candidate_id", "variant", "parameter", "grad_norm", "update_norm"])
    write_dynamic_csv(out_dir / "m9_hard_negative_replay_ledger.csv", hardneg_rows, ["candidate_id", "variant", "memory_source", "case_count", "component_count"])
    write_dynamic_csv(out_dir / "m9_component_remote_fp_hd95_report.csv", component_rows, ["candidate_id", "variant", "case_id", "metric_name", "dice", "hd95", "component_count", "remote_fp_count"])
    write_dynamic_csv(out_dir / "m9_same_split_help_harm.csv", help_harm_rows, ["candidate_id", "checkpoint_name", "decode_mode", "case_id", "metric_name", "m9_dice", "nnunet_dice", "dice_delta", "m9_hd95", "nnunet_hd95", "hd95_delta"])
    write_dynamic_csv(out_dir / "m9_hard_subgroup_metrics.csv", subgroup_rows, ["candidate_id", "variant", "metric_name", "group", "dice_mean", "hd95_mean", "component_count_mean", "remote_fp_mean"])
    write_dynamic_csv(out_dir / "m9_proposal_refiner_recall_precision.csv", proposal_rows, ["candidate_id", "variant", "case_id", "metric_name", "proposal_threshold", "proposal_recall", "proposal_precision", "lesion_wise_recall"])
    scar_roi_rows = [row for row in roi_rows if "scar" in str(row.get("metric_name", "")).lower()] or roi_rows
    edema_roi_rows = [row for row in roi_rows if "edema" in str(row.get("metric_name", "")).lower()] or roi_rows
    write_dynamic_csv(out_dir / "m9_scar_refiner_roi_stats.csv", scar_roi_rows, ["candidate_id", "variant", "case_id", "metric_name", "gt_coverage", "outside_myocardium_roi_ratio"])
    write_dynamic_csv(out_dir / "m9_edema_refiner_roi_stats.csv", edema_roi_rows, ["candidate_id", "variant", "case_id", "metric_name", "gt_coverage", "outside_myocardium_roi_ratio"])
    write_dynamic_csv(out_dir / "m9_refiner_asymmetry_ablation.csv", roi_rows, ["candidate_id", "variant", "case_id", "metric_name", "gt_coverage", "outside_myocardium_roi_ratio"])
    write_dynamic_csv(out_dir / "m9_refiner_causal_effect.csv", component_rows, ["candidate_id", "variant", "case_id", "metric_name", "dice", "hd95", "component_count", "remote_fp_count"])
    write_dynamic_csv(out_dir / "m9_ablation_matrix.csv", checkpoint_rows, ["candidate_id", "selection_metric", "selected_checkpoint", "decode_mode", "status"])
    write_dynamic_csv(out_dir / "m9_candidate_assembly_matrix.csv", summary_rows, ["candidate_id", "runtime_root", "summary_path", "actual_optimizer_steps", "train_loop_seconds", "checkpoint_best"])
    print(f"wrote {out_dir / 'm9_training_budget_ledger.csv'}")


if __name__ == "__main__":
    main()
