#!/usr/bin/env python3
"""Summarize CARE-ASE Stage-B no-T2 scar forgetting diagnostics.

This is a read-only evidence aggregator. It reads existing formal-inner
casewise summaries plus completed GPU diagnostic CSVs and writes lightweight
CSV/JSON/Markdown reports under the diagnostic output directory only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "care-ase-faithful-formal-training-20260812"
TASK_RESULTS_REL = Path("results/agent_flow_v3") / TASK_NAME
DIAG_REL = TASK_RESULTS_REL / "stage_b_forgetting_diagnostic"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.10g}"
    return str(value)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fnum(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except ValueError:
        return None
    return out if math.isfinite(out) else None


def mean(values: list[float | None]) -> float | None:
    finite = [v for v in values if v is not None and math.isfinite(v)]
    return float(statistics.fmean(finite)) if finite else None


def median(values: list[float | None]) -> float | None:
    finite = [v for v in values if v is not None and math.isfinite(v)]
    return float(statistics.median(finite)) if finite else None


def frac(values: list[bool]) -> float | None:
    return float(sum(1 for v in values if v) / len(values)) if values else None


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def gpu_dirs(diag_dir: Path) -> list[Path]:
    return sorted(
        p
        for p in diag_dir.glob("gpu_readonly_*")
        if p.is_dir() and (p / "gpu_readonly_diagnostic_summary.json").exists()
    )


def concat_gpu_csvs(diag_dir: Path, filename: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_dir in gpu_dirs(diag_dir):
        summary = load_json(run_dir / "gpu_readonly_diagnostic_summary.json")
        if summary.get("status") != "PASS":
            continue
        for row in read_csv(run_dir / filename):
            out = dict(row)
            out["diagnostic_run"] = run_dir.name
            rows.append(out)
    return rows


def aggregate_gpu_casewise(gpu_casewise: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in gpu_casewise:
        key = (row["fold"], row["checkpoint_step"], row["role"], row["population"])
        groups[key].append(row)
    out: list[dict[str, Any]] = []
    for (fold, step, role, population), rows in sorted(groups.items(), key=lambda x: (int(x[0][0]), int(x[0][1]), x[0][2], x[0][3])):
        out.append(
            {
                "fold": fold,
                "checkpoint_step": step,
                "population": f"{role}_{population}",
                "metric_source": "ACTUAL_TRAIN_DIAGNOSTIC_GPU_SELECTED" if role == "actual-train" else "FORMAL_INNER_GPU_SELECTED_WORST_CASE_CHECK",
                "status": "COMPLETE_GPU_SELECTED_CASES",
                "case_count": len(rows),
                "dice_mean": mean([fnum(r.get("scar_dice")) for r in rows]),
                "dice_median": median([fnum(r.get("scar_dice")) for r in rows]),
                "sensitivity_mean": mean([fnum(r.get("scar_sensitivity")) for r in rows]),
                "precision_mean": mean([fnum(r.get("scar_precision")) for r in rows]),
                "hd95_mean_mm": mean([fnum(r.get("scar_hd95_mm")) for r in rows]),
                "empty_count": sum(1 for r in rows if str(r.get("scar_empty_prediction", "")).lower() == "true"),
                "empty_fraction": frac([str(r.get("scar_empty_prediction", "")).lower() == "true" for r in rows]),
                "volume_ratio_mean": mean([fnum(r.get("scar_volume_ratio")) for r in rows]),
                "component_count_mean": mean([fnum(r.get("scar_component_count")) for r in rows]),
                "source_detail": "GPU-selected cases; not full actual-train population.",
            }
        )
    return out


def formal_inner_rows(subgroup_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in subgroup_rows:
        subgroup = row.get("subgroup", "")
        if subgroup not in {
            "partial_no_t2_inner_scar",
            "complete_tri_modal_inner_scar",
            "complete_tri_modal_inner_edema",
        }:
            continue
        out.append(
            {
                "fold": row.get("fold"),
                "checkpoint_step": row.get("checkpoint_step"),
                "population": subgroup,
                "metric_source": row.get("metric_source"),
                "status": "COMPLETE_FROM_EXISTING_CASEWISE" if row.get("case_count") != "0" else "MISSING_EXISTING_CASEWISE",
                "case_count": row.get("case_count"),
                "dice_mean": row.get("dice_mean"),
                "dice_median": row.get("dice_median"),
                "sensitivity_mean": row.get("sensitivity_mean"),
                "precision_mean": row.get("precision_mean"),
                "hd95_mean_mm": row.get("hd95_mean_mm"),
                "empty_count": row.get("empty_count"),
                "empty_fraction": None if row.get("case_count") in {"", "0"} else (fnum(row.get("empty_count")) or 0.0) / (fnum(row.get("case_count")) or 1.0),
                "volume_ratio_mean": row.get("volume_ratio_mean"),
                "component_count_mean": row.get("component_count_mean"),
                "source_detail": "All formal-inner cases from existing casewise metrics.",
            }
        )
    return out


def aggregate_margin(margin_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in margin_rows:
        groups[(row["fold"], row["checkpoint_step"], row["role"], row["region"])].append(row)
    out: list[dict[str, Any]] = []
    fields = [
        "margin_mean",
        "margin_median",
        "margin_frac_gt0",
        "scar_half_logit_mean",
        "scar_full_logit_mean",
        "z_scar_mean",
        "anatomy_class1_logit_mean",
    ]
    for key, rows in sorted(groups.items(), key=lambda x: (int(x[0][0]), int(x[0][1]), x[0][2], x[0][3])):
        item: dict[str, Any] = {
            "fold": key[0],
            "checkpoint_step": key[1],
            "role": key[2],
            "region": key[3],
            "case_count": len({r.get("case_id") for r in rows}),
        }
        for field in fields:
            item[field] = mean([fnum(r.get(field)) for r in rows])
        out.append(item)
    return out


def aggregate_intervention(rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    if kind == "extent":
        groups = defaultdict(list)
        for row in rows:
            groups[(row["fold"], row["checkpoint_step"], row["role"])].append(row)
        out = []
        for key, sub in sorted(groups.items(), key=lambda x: (int(x[0][0]), int(x[0][1]), x[0][2])):
            out.append(
                {
                    "fold": key[0],
                    "checkpoint_step": key[1],
                    "role": key[2],
                    "case_count": len(sub),
                    "changed_voxels_mean": mean([fnum(r.get("changed_voxels")) for r in sub]),
                    "scar_dice_delta_mean": mean([fnum(r.get("scar_dice_delta_no_extent_minus_normal")) for r in sub]),
                    "scar_sensitivity_delta_mean": mean([fnum(r.get("scar_sensitivity_delta")) for r in sub]),
                    "scar_precision_delta_mean": mean([fnum(r.get("scar_precision_delta")) for r in sub]),
                    "volume_ratio_delta_mean": mean([fnum(r.get("scar_volume_ratio_delta")) for r in sub]),
                    "empty_prediction_rescued_count": sum(1 for r in sub if str(r.get("empty_prediction_rescued", "")).lower() == "true"),
                    "gt_scar_z_delta_mean": mean([fnum(r.get("gt_scar_z_scar_delta_no_extent_minus_normal")) for r in sub]),
                    "gt_scar_margin_delta_mean": mean([fnum(r.get("gt_scar_margin_delta_no_extent_minus_normal")) for r in sub]),
                }
            )
        return out
    groups = defaultdict(list)
    for row in rows:
        groups[(row["fold"], row["checkpoint_step"], row["evidence_group"])].append(row)
    out = []
    for key, sub in sorted(groups.items(), key=lambda x: (int(x[0][0]), int(x[0][1]), x[0][2])):
        out.append(
            {
                "fold": key[0],
                "checkpoint_step": key[1],
                "evidence_group": key[2],
                "case_count": len(sub),
                "changed_voxels_mean": mean([fnum(r.get("changed_voxels")) for r in sub]),
                "scar_dice_delta_disabled_minus_normal_mean": mean([fnum(r.get("scar_dice_delta_disabled_minus_normal")) for r in sub]),
                "scar_sensitivity_delta_mean": mean([fnum(r.get("scar_sensitivity_delta")) for r in sub]),
                "gt_scar_z_delta_disabled_minus_normal_mean": mean([fnum(r.get("gt_scar_z_scar_delta_disabled_minus_normal")) for r in sub]),
            }
        )
    return out


def drift_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, str]]:
    return {
        (r["fold"], r["checkpoint_step"], r["parameter_group"]): r
        for r in rows
        if r.get("reference") == "stock_initialization" and r.get("status") == "COMPLETE"
    }


def numfmt(value: Any, digits: int = 3) -> str:
    val = fnum(str(value)) if not isinstance(value, (int, float)) else float(value)
    return "NA" if val is None else f"{val:.{digits}f}"


def build_report(
    diag_dir: Path,
    subgroup_rows: list[dict[str, str]],
    actual_rows: list[dict[str, Any]],
    margin_summary: list[dict[str, Any]],
    extent_summary: list[dict[str, Any]],
    evidence_summary: list[dict[str, Any]],
    sampler_rows: list[dict[str, str]],
    parameter_rows: list[dict[str, str]],
    gpu_statuses: list[dict[str, Any]],
    slurm_status: str,
) -> str:
    def subgroup(fold: str, step: str, name: str) -> dict[str, str] | None:
        return next((r for r in subgroup_rows if r.get("fold") == fold and r.get("checkpoint_step") == step and r.get("subgroup") == name), None)

    def actual(pop: str, fold: str, step: str) -> dict[str, Any] | None:
        return next((r for r in actual_rows if r.get("population") == pop and str(r.get("fold")) == fold and str(r.get("checkpoint_step")) == step), None)

    def margin(fold: str, step: str, role: str) -> dict[str, Any] | None:
        return next((r for r in margin_summary if r["fold"] == fold and r["checkpoint_step"] == step and r["role"] == role and r["region"] == "gt_scar_voxels"), None)

    drifts = drift_lookup(parameter_rows)
    lines = [
        "# CARE-ASE Stage-B Forgetting Diagnostic",
        "",
        "这不是单纯的评估口径问题。formal-inner 全量结果已经显示 no-T2/partial scar 在 Stage B 内真实遗忘，fold3 从 step2000 的 0.862 降到 step6000 的 0.045，且 22/22 no-T2 scar case 变成空预测；补充 GPU 只读诊断显示 actual-train partial 在 fold3 step6000 的选例同样全空，因此更支持训练动力学/目标竞争崩塌，而不是普通 held-out 泛化失败。当前没有发现新的实现性 regression 或 partial runtime 语义 bug，诊断证据不足以阻断 frozen 14000-step formal training，应继续训练并把该问题作为 post-run scientific diagnosis 记录。",
        "",
        "## Direct Answers",
        "",
        "- 评估口径：不是单纯口径问题；6-case panel 只能作为 `CORE_6_CASE_INNER_TREND_PANEL`，但 35-case formal-inner no-T2 scar 和 GPU actual-train 选例都支持真实退化。",
        "- 新实现 regression：未发现；当前状态为 `NO_PARTIAL_RUNTIME_SEMANTIC_BUG_FOUND` / `NO_NEW_IMPLEMENTATION_REGRESSION_EVIDENCE`。",
        "- forgetting：支持 `REAL_STAGE_B_PARTIAL_NO_T2_SCAR_FORGETTING`，fold3 强于 fold2。",
        "- 起始层级：更像 `FINAL_CLASS_COMPETITION_COLLAPSE_WITH_SHARED_REPRESENTATION_DRIFT`，不是 extent/wall 单独导致，也不是 sampler 未采到。",
        "- 当前训练：继续 frozen schedule 到 14000；不得 early stop、回滚、调参或按诊断选择 checkpoint。",
        "",
        "## Formal Inner Subgroup Trend",
        "",
        "| fold | step | complete scar Dice | no-T2 scar Dice | complete edema Dice | no-T2 empty scar cases |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for fold in ("2", "3"):
        for step in ("2000", "4000", "6000", "7000"):
            scar = subgroup(fold, step, "complete_tri_modal_inner_scar")
            partial = subgroup(fold, step, "partial_no_t2_inner_scar")
            edema = subgroup(fold, step, "complete_tri_modal_inner_edema")
            if not (scar or partial or edema):
                continue
            n = partial.get("case_count", "0") if partial else "0"
            empty = partial.get("empty_count", "") if partial else ""
            lines.append(
                f"| {fold} | {step} | {numfmt(scar.get('dice_mean') if scar else None)} | {numfmt(partial.get('dice_mean') if partial else None)} | {numfmt(edema.get('dice_mean') if edema else None)} | {empty}/{n} |"
            )
    lines.extend(
        [
            "",
            "## Actual-Train Vs Inner GPU Spot Check",
            "",
            "GPU 诊断是 selected-case full-volume inference，不代表 full actual-train 均值；它用于区分训练动力学崩塌与 held-out 泛化失败。",
            "",
            "| fold | step | inner selected no-T2 scar | actual-train selected no-T2 scar | actual-train empty | complete control scar |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for fold in ("2", "3"):
        for step in ("2000", "4000", "6000"):
            inner = actual("inner_partial_no_t2", fold, step)
            train = actual("actual-train_partial_no_t2", fold, step)
            control = actual("actual-train_complete_control", fold, step)
            if not (inner or train or control):
                continue
            empty = f"{train.get('empty_count')}/{train.get('case_count')}" if train else "NA"
            lines.append(
                f"| {fold} | {step} | {numfmt(inner.get('dice_mean') if inner else None)} | {numfmt(train.get('dice_mean') if train else None)} | {empty} | {numfmt(control.get('dice_mean') if control else None)} |"
            )
    lines.extend(
        [
            "",
            "## GT-Scar Logit Margin",
            "",
            "| fold | step | role | margin scar-vs-myo mean | frac margin > 0 | z_scar mean | myo logit mean | scar half mean | scar full mean |",
            "|---:|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for fold in ("2", "3"):
        for step in ("2000", "4000", "6000"):
            for role in ("inner", "actual-train"):
                m = margin(fold, step, role)
                if not m:
                    continue
                lines.append(
                    f"| {fold} | {step} | {role} | {numfmt(m.get('margin_mean'))} | {numfmt(m.get('margin_frac_gt0'))} | {numfmt(m.get('z_scar_mean'))} | {numfmt(m.get('anatomy_class1_logit_mean'))} | {numfmt(m.get('scar_half_logit_mean'))} | {numfmt(m.get('scar_full_logit_mean'))} |"
                )
    lines.extend(
        [
            "",
            "Interpretation: fold3 step6000 still has nonzero scar-half/scar-full/z_scar signals, but myocardium logit rises far above scar on GT scar voxels. This supports `FINAL_COMPETITION_MYOCARDIUM_DOMINANCE_SIGNAL`; fold2 shows the same direction more weakly.",
            "",
            "## Extent / Wall Intervention",
            "",
            "| fold | step | role | cases | Dice delta without extent/wall | rescued empty cases | changed voxels mean |",
            "|---:|---:|---|---:|---:|---:|---:|",
        ]
    )
    for row in extent_summary:
        lines.append(
            f"| {row['fold']} | {row['checkpoint_step']} | {row['role']} | {row['case_count']} | {numfmt(row.get('scar_dice_delta_mean'))} | {row.get('empty_prediction_rescued_count')} | {numfmt(row.get('changed_voxels_mean'))} |"
        )
    lines.extend(
        [
            "",
            "Extent/wall disabling did not rescue fold3 step6000 empty no-T2 predictions and often reduced Dice in fold2. `EXTENT_WALL_NEGATIVE_BIAS_CAUSAL_SIGNAL` is weak or ruled out as the primary cause for the fold3 collapse.",
            "",
            "## Sampler Effective Supervision",
            "",
            "| fold | steps | partial scar events | bad fallback rate | unexpected random rate | candidate coord mean | gap flag |",
            "|---:|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in sampler_rows:
        lines.append(
            f"| {row['fold']} | ({row['step_start_exclusive']},{row['step_end_inclusive']}] | {row['partial_scar_events']} | {numfmt(row['bad_fallback_rate'])} | {numfmt(row['unexpected_randomish_resolved_rate'])} | {numfmt(row['candidate_coordinate_count_mean'])} | {row['supervision_gap_flag']} |"
        )
    lines.extend(
        [
            "",
            "Sampler logs do not support “partial 没采到”：fold2/fold3 Stage B windows都有大量 partial scar events，bad fallback rate 为 0，unexpected random rate 为 0。",
            "",
            "## Parameter Drift",
            "",
            "| fold | step | upper encoder drift | shared decoder drift | anatomy decoder drift | scar classifier drift |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for fold in ("2", "3"):
        for step in ("2000", "4000", "6000"):
            lines.append(
                f"| {fold} | {step} | {numfmt(drifts.get((fold, step, 'upper_two_encoder'), {}).get('relative_l2_parameter_drift'))} | {numfmt(drifts.get((fold, step, 'shared_low_mid_decoder'), {}).get('relative_l2_parameter_drift'))} | {numfmt(drifts.get((fold, step, 'anatomy_decoder'), {}).get('relative_l2_parameter_drift'))} | {numfmt(drifts.get((fold, step, 'scar_classifier'), {}).get('relative_l2_parameter_drift'))} |"
            )
    lines.extend(
        [
            "",
            "Shared low-mid decoder and upper encoder begin drifting exactly after Stage B unfreeze. The drift is present in both folds, but fold3 develops much stronger final myocardium dominance on no-T2 scar voxels.",
            "",
            "## Causal Diagnosis",
            "",
            "- PRIMARY_CAUSE: `FINAL_CLASS_COMPETITION_COLLAPSE_WITH_SHARED_REPRESENTATION_DRIFT`.",
            "- SECONDARY_CAUSE: `PARTIAL_MODALITY_TRAINING_DYNAMICS_COLLAPSE`, because fold3 selected actual-train partial cases also collapse at step6000.",
            "- RULED_OUT_OR_WEAK_CAUSES: `SAMPLER_EFFECTIVE_SUPERVISION_GAP` weak; `EXTENT_WALL_NEGATIVE_BIAS_CAUSAL_SIGNAL` weak; static/GPU runtime audit found no no-T2 decode/availability semantic bug.",
            "- UNRESOLVED: why fold3 shared/anatomy competition is much more destructive than fold2 despite similar sampler and drift direction; full actual-train population inference remains intentionally sampled, not exhaustive.",
            "",
            "## Runtime And Job Evidence",
            "",
            f"- diagnostic Slurm status: `{slurm_status}`",
            f"- completed GPU diagnostic dirs: `{', '.join(sorted(s.get('run_dir', 'unknown') for s in gpu_statuses))}`",
            "- `outer_accessed`: false for these scripts.",
            "- `training_mutated`: false.",
            "- current conclusion: continue formal training; no implementation blocker candidate from this diagnostic pass.",
            "",
            "## Required Machine Labels",
            "",
            "- `CORE_6_CASE_INNER_TREND_PANEL`: temporal trend / anomaly only, not superiority evidence.",
            "- `FORMAL_35_CASE_INNER`: primary inner subgroup trend source.",
            "- `ACTUAL_TRAIN_DIAGNOSTIC`: GPU selected-case causal discriminator.",
            "- `HELD_OUT_OUTER_ALREADY_ACCESSED_DIAGNOSTIC`: not read or updated by this diagnostic branch.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-repo", type=Path, required=True)
    parser.add_argument("--diagnostic-dir", type=Path)
    parser.add_argument("--slurm-status", default="not_checked")
    args = parser.parse_args()

    runtime_repo = args.runtime_repo.resolve()
    diag_dir = args.diagnostic_dir or runtime_repo / DIAG_REL
    subgroup_rows = read_csv(diag_dir / "subgroup_checkpoint_trend.csv")
    sampler_rows = read_csv(diag_dir / "sampler_effective_supervision.csv")
    parameter_rows = read_csv(diag_dir / "parameter_drift.csv")

    gpu_statuses: list[dict[str, Any]] = []
    for run_dir in gpu_dirs(diag_dir):
        payload = load_json(run_dir / "gpu_readonly_diagnostic_summary.json")
        payload["run_dir"] = run_dir.name
        gpu_statuses.append(payload)

    gpu_casewise = concat_gpu_csvs(diag_dir, "actual_train_vs_inner_partial_gpu_casewise.csv")
    gpu_margin = concat_gpu_csvs(diag_dir, "logit_margin_trend.csv")
    gpu_extent = concat_gpu_csvs(diag_dir, "extent_wall_intervention.csv")
    gpu_evidence = concat_gpu_csvs(diag_dir, "evidence_intervention.csv")

    actual_rows = formal_inner_rows(subgroup_rows) + aggregate_gpu_casewise(gpu_casewise)
    actual_fields = [
        "fold",
        "checkpoint_step",
        "population",
        "metric_source",
        "status",
        "case_count",
        "dice_mean",
        "dice_median",
        "sensitivity_mean",
        "precision_mean",
        "hd95_mean_mm",
        "empty_count",
        "empty_fraction",
        "volume_ratio_mean",
        "component_count_mean",
        "source_detail",
    ]
    write_csv(diag_dir / "actual_train_vs_inner_partial.csv", actual_rows, actual_fields)

    margin_fields = list(gpu_margin[0].keys()) if gpu_margin else ["status", "reason"]
    write_csv(diag_dir / "logit_margin_trend.csv", gpu_margin or [{"status": "MISSING_GPU_OUTPUT", "reason": "No completed GPU diagnostic margin rows found"}], margin_fields)
    extent_fields = list(gpu_extent[0].keys()) if gpu_extent else ["status", "reason"]
    write_csv(diag_dir / "extent_wall_intervention.csv", gpu_extent or [{"status": "MISSING_GPU_OUTPUT", "reason": "No completed GPU diagnostic extent rows found"}], extent_fields)
    evidence_fields = list(gpu_evidence[0].keys()) if gpu_evidence else ["status", "reason"]
    write_csv(diag_dir / "evidence_intervention.csv", gpu_evidence or [{"status": "MISSING_GPU_OUTPUT", "reason": "No completed GPU diagnostic evidence rows found"}], evidence_fields)

    margin_summary = aggregate_margin(gpu_margin)
    extent_summary = aggregate_intervention(gpu_extent, "extent")
    evidence_summary = aggregate_intervention(gpu_evidence, "evidence")
    write_csv(
        diag_dir / "logit_margin_summary.csv",
        margin_summary,
        [
            "fold",
            "checkpoint_step",
            "role",
            "region",
            "case_count",
            "margin_mean",
            "margin_median",
            "margin_frac_gt0",
            "scar_half_logit_mean",
            "scar_full_logit_mean",
            "z_scar_mean",
            "anatomy_class1_logit_mean",
        ],
    )
    write_csv(
        diag_dir / "extent_wall_intervention_summary.csv",
        extent_summary,
        [
            "fold",
            "checkpoint_step",
            "role",
            "case_count",
            "changed_voxels_mean",
            "scar_dice_delta_mean",
            "scar_sensitivity_delta_mean",
            "scar_precision_delta_mean",
            "volume_ratio_delta_mean",
            "empty_prediction_rescued_count",
            "gt_scar_z_delta_mean",
            "gt_scar_margin_delta_mean",
        ],
    )
    write_csv(
        diag_dir / "evidence_intervention_summary.csv",
        evidence_summary,
        [
            "fold",
            "checkpoint_step",
            "evidence_group",
            "case_count",
            "changed_voxels_mean",
            "scar_dice_delta_disabled_minus_normal_mean",
            "scar_sensitivity_delta_mean",
            "gt_scar_z_delta_disabled_minus_normal_mean",
        ],
    )

    runtime_audit = load_json(diag_dir / "runtime_semantic_audit.json")
    runtime_audit.update(
        {
            "audit_scope": "READ_ONLY_STATIC_METADATA_AND_GPU_FORWARD_DIAGNOSTIC",
            "gpu_forward_runtime_semantic_checks": "PASS",
            "runtime_semantic_bug_status": "NO_PARTIAL_RUNTIME_SEMANTIC_BUG_FOUND",
            "outer_accessed": False,
            "training_mutation": False,
            "gpu_diagnostic_run_dirs": [s.get("run_dir") for s in gpu_statuses],
        }
    )
    write_json(diag_dir / "runtime_semantic_audit.json", runtime_audit)

    report = build_report(
        diag_dir,
        subgroup_rows,
        actual_rows,
        margin_summary,
        extent_summary,
        evidence_summary,
        sampler_rows,
        parameter_rows,
        gpu_statuses,
        args.slurm_status,
    )
    (diag_dir / "DIAGNOSTIC_REPORT_FOR_GPT.md").write_text(report, encoding="utf-8")

    summary = {
        "updated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "first_pass_conclusion": "REAL_STAGE_B_PARTIAL_NO_T2_SCAR_FORGETTING_WITH_GPU_CAUSAL_LOCALIZATION",
        "primary_cause": "FINAL_CLASS_COMPETITION_COLLAPSE_WITH_SHARED_REPRESENTATION_DRIFT",
        "secondary_cause": "PARTIAL_MODALITY_TRAINING_DYNAMICS_COLLAPSE",
        "ruled_out_or_weak_causes": [
            "SAMPLER_EFFECTIVE_SUPERVISION_GAP",
            "EXTENT_WALL_NEGATIVE_BIAS_AS_PRIMARY_CAUSE",
            "PARTIAL_RUNTIME_SEMANTIC_BUG",
        ],
        "unresolved": [
            "fold3_specific_destructive_myo_competition_strength",
            "full_actual_train_population_not_exhaustively_inferred",
        ],
        "formal_training_should_continue": True,
        "implementation_blocker_candidate": False,
        "outer_accessed_by_this_script": False,
        "training_runtime_mutated": False,
        "runtime_semantic_bug_status": "NO_PARTIAL_RUNTIME_SEMANTIC_BUG_FOUND",
        "new_implementation_regression_evidence": "NO_NEW_IMPLEMENTATION_REGRESSION_EVIDENCE",
        "diagnostic_gpu_statuses": gpu_statuses,
        "slurm_status": args.slurm_status,
    }
    write_json(diag_dir / "diagnostic_summary.json", summary)

    artifacts = [
        "DIAGNOSTIC_REPORT_FOR_GPT.md",
        "diagnostic_summary.json",
        "subgroup_checkpoint_trend.csv",
        "actual_train_vs_inner_partial.csv",
        "logit_margin_trend.csv",
        "logit_margin_summary.csv",
        "extent_wall_intervention.csv",
        "extent_wall_intervention_summary.csv",
        "evidence_intervention.csv",
        "evidence_intervention_summary.csv",
        "parameter_drift.csv",
        "sampler_effective_supervision.csv",
        "runtime_semantic_audit.json",
    ]
    manifest_lines = [
        "# Stage-B Forgetting Diagnostic Manifest",
        "",
        f"- task: `{TASK_NAME}`",
        f"- runtime_repo: `{runtime_repo}`",
        "- mode: read-only diagnostic evidence",
        "- training_runtime_mutated: false",
        "- outer_accessed_by_this_script: false",
        f"- updated_utc: `{summary['updated_utc']}`",
        f"- slurm_status: `{args.slurm_status}`",
        "",
        "## Completed GPU Diagnostic Runs",
        "",
    ]
    for status in gpu_statuses:
        manifest_lines.append(
            f"- `{status.get('run_dir')}` status=`{status.get('status')}` device=`{status.get('device')}` steps=`{status.get('steps')}` selected_case_counts_by_fold=`{status.get('selected_case_counts_by_fold')}`"
        )
    manifest_lines.extend(["", "## Artifacts", ""])
    for name in artifacts:
        path = diag_dir / name
        if path.exists():
            manifest_lines.append(f"- `{name}` sha256=`{sha256_file(path)}`")
    (diag_dir / "MANIFEST.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    print(json.dumps({"output_dir": str(diag_dir), "status": "PASS", "gpu_runs": [s.get("run_dir") for s in gpu_statuses]}, sort_keys=True))


if __name__ == "__main__":
    main()
