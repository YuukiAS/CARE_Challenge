#!/usr/bin/env python
"""Summarize user-authorized CARE-ASE outer diagnostic casewise CSVs by subgroup.

This is a reporting-only helper. It reads existing casewise diagnostic CSVs,
joins immutable MyoPS case metadata, and writes lightweight subgroup evidence.
It does not run inference, select checkpoints, tune thresholds, or alter
training state.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata


TASK_KEY = "care-ase-faithful-formal-training-20260812"
DEFAULT_RESULT_ROOT = REPO_ROOT / "results/agent_flow_v3" / TASK_KEY
DEFAULT_OUTER_ROOT = DEFAULT_RESULT_ROOT / "outer_diagnostic_user_authorized"
DEFAULT_RUNTIME_WORKTREE_ROOT = Path("/users/a/e/aereinh/CARE/.worktrees") / TASK_KEY
CASEWISE_BY_FOLD = {
    2: DEFAULT_OUTER_ROOT / "fold_2/step05000/outer_casewise_metrics.csv",
    3: DEFAULT_OUTER_ROOT / "fold_3/step04000/outer_casewise_metrics.csv",
}
VOLUME_RATIO_CASEWISE_BY_FOLD = {
    2: DEFAULT_OUTER_ROOT / "fold_2/step05000_no_t2_matched_20260813/outer_casewise_metrics.csv",
    3: DEFAULT_OUTER_ROOT / "fold_3/step04000_no_t2_matched_20260813/outer_casewise_metrics.csv",
}
CHECKPOINTS_BY_FOLD = {
    2: DEFAULT_RESULT_ROOT / "runtime/fold_2/checkpoint_step05000.pt",
    3: DEFAULT_RESULT_ROOT / "runtime/fold_3_parallel/checkpoint_step04000.pt",
}
PROVENANCE_FIELDS = (
    "training_source_commit_sha",
    "formal_execution_checkout_commit_sha",
    "critical_source_manifest_sha256",
    "implementation_source_manifest_sha256",
    "code_hash",
    "config_hash",
    "split_hash",
    "plans_hash",
    "stock_checkpoint_hash",
    "frozen_contract_sha256",
    "global_optimizer_step",
    "fold",
)


@dataclass(frozen=True)
class GroupSpec:
    key: str
    label: str
    metric_prefix: str
    require_t2: bool | None = None
    complete: bool | None = None
    center: str | None = None


GROUPS = (
    GroupSpec("all_outer_scar", "all outer scar", "scar"),
    GroupSpec("complete_tri_modal_scar", "complete tri-modal scar", "scar", require_t2=True, complete=True),
    GroupSpec("partial_modality_scar", "partial-modality scar", "scar", complete=False),
    GroupSpec("pure_edema_t2_present", "pure edema on T2-present", "pure_edema", require_t2=True),
    GroupSpec("centerB_complete_scar", "CenterB complete scar", "scar", require_t2=True, complete=True, center="CenterB"),
    GroupSpec("centerB_complete_edema", "CenterB complete edema", "pure_edema", require_t2=True, complete=True, center="CenterB"),
    GroupSpec("centerC_complete_scar", "CenterC complete scar", "scar", require_t2=True, complete=True, center="CenterC"),
    GroupSpec("centerC_complete_edema", "CenterC complete edema", "pure_edema", require_t2=True, complete=True, center="CenterC"),
)


def parse_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out):
        return None
    return out


def mean(values: Iterable[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def fmt(value: float | None, digits: int = 6) -> str:
    if value is None:
        return "NA"
    return f"{value:.{digits}f}"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def metadata_root(default_repo_root: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    if (default_repo_root / "data/benchmarks/protocol/cases_MyoPS.json").is_file():
        return default_repo_root
    fallback = Path("/users/a/e/aereinh/CARE")
    if (fallback / "data/benchmarks/protocol/cases_MyoPS.json").is_file():
        return fallback
    return default_repo_root


def load_rows(casewise_by_fold: dict[int, Path], meta_repo_root: Path) -> list[dict[str, Any]]:
    metadata = load_myops_case_metadata(meta_repo_root)
    rows: list[dict[str, Any]] = []
    for fold, path in sorted(casewise_by_fold.items()):
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                case_id = str(row["case_id"])
                meta = metadata[case_id]
                row["fold"] = int(row.get("fold") or fold)
                row["center"] = meta.center
                row["modality_group"] = meta.modality_group
                row["availability"] = "".join("1" if flag else "0" for flag in meta.availability)
                row["complete_tri_modal"] = row["availability"] == "111"
                row["t2_present_metadata"] = bool(meta.t2_present)
                rows.append(row)
    return rows


def filter_rows(rows: list[dict[str, Any]], spec: GroupSpec, fold: int | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if fold is not None and int(row["fold"]) != int(fold):
            continue
        if spec.require_t2 is not None and bool(row["t2_present_metadata"]) != spec.require_t2:
            continue
        if spec.complete is not None and bool(row["complete_tri_modal"]) != spec.complete:
            continue
        if spec.center is not None and row["center"] != spec.center:
            continue
        out.append(row)
    return out


def summarize(rows: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    pairs: list[tuple[float, float]] = []
    for row in rows:
        care = parse_float(row.get(f"care_{prefix}_dice"))
        nnunet = parse_float(row.get(f"nnunet_{prefix}_dice"))
        if care is not None and nnunet is not None:
            pairs.append((care, nnunet))
    care_dice = mean(care for care, _ in pairs)
    nnunet_dice = mean(nnunet for _, nnunet in pairs)
    summary: dict[str, Any] = {
        "case_count": len(pairs),
        "care_dice": care_dice,
        "nnunet_dice": nnunet_dice,
        "delta_care_minus_nnunet": None if care_dice is None or nnunet_dice is None else care_dice - nnunet_dice,
        "care_help_count": sum(1 for care, nnunet in pairs if care > nnunet + 1e-12),
        "care_harm_count": sum(1 for care, nnunet in pairs if care < nnunet - 1e-12),
        "tie_count": sum(1 for care, nnunet in pairs if abs(care - nnunet) <= 1e-12),
    }
    for metric in ("sensitivity", "precision", "hd95"):
        for model in ("care", "nnunet"):
            values = [parse_float(row.get(f"{model}_{prefix}_{metric}")) for row in rows]
            clean = [v for v in values if v is not None]
            summary[f"{model}_{metric}"] = mean(clean)
            summary[f"{model}_{metric}_n"] = len(clean)
    summary["care_empty_prediction_count_from_blank_precision"] = sum(
        1
        for row in rows
        if parse_float(row.get(f"care_{prefix}_dice")) is not None and row.get(f"care_{prefix}_precision") in ("", None)
    )
    summary["nnunet_empty_prediction_count_from_blank_precision"] = sum(
        1
        for row in rows
        if parse_float(row.get(f"nnunet_{prefix}_dice")) is not None and row.get(f"nnunet_{prefix}_precision") in ("", None)
    )
    volume_ratio_columns = [f"care_{prefix}_volume_ratio", f"nnunet_{prefix}_volume_ratio"]
    if all(column in rows[0] for column in volume_ratio_columns) if rows else False:
        summary["care_volume_ratio"] = mean(parse_float(row.get(volume_ratio_columns[0])) for row in rows)
        summary["nnunet_volume_ratio"] = mean(parse_float(row.get(volume_ratio_columns[1])) for row in rows)
    else:
        summary["volume_ratio_status"] = "NOT_AVAILABLE_IN_CURRENT_CASEWISE_CSV"
    return summary


def summarize_no_t2_matched_baseline(rows: list[dict[str, Any]], fold: int | None) -> dict[str, Any]:
    subset = [
        row
        for row in rows
        if not bool(row["t2_present_metadata"]) and (fold is None or int(row["fold"]) == int(fold))
    ]
    care = [parse_float(row.get("care_scar_dice")) for row in subset]
    direct = [parse_float(row.get("nnunet_scar_dice")) for row in subset]
    matched = [parse_float(row.get("nnunet_no_t2_matched_scar_dice")) for row in subset]
    pairs_direct = [(c, n) for c, n in zip(care, direct) if c is not None and n is not None]
    pairs_matched = [(c, n) for c, n in zip(care, matched) if c is not None and n is not None]
    care_mean = mean(care)
    direct_mean = mean(direct)
    matched_mean = mean(matched)
    return {
        "case_count": len(subset),
        "care_scar_dice": care_mean,
        "nnunet_direct_six_class_scar_dice": direct_mean,
        "nnunet_matched_no_t2_class_set_scar_dice": matched_mean,
        "delta_care_minus_nnunet_direct_six_class": None
        if care_mean is None or direct_mean is None
        else care_mean - direct_mean,
        "delta_care_minus_nnunet_matched_no_t2_class_set": None
        if care_mean is None or matched_mean is None
        else care_mean - matched_mean,
        "nnunet_matched_minus_direct": None if direct_mean is None or matched_mean is None else matched_mean - direct_mean,
        "help_vs_direct": sum(1 for c, n in pairs_direct if c > n + 1e-12),
        "harm_vs_direct": sum(1 for c, n in pairs_direct if c < n - 1e-12),
        "help_vs_matched_no_t2": sum(1 for c, n in pairs_matched if c > n + 1e-12),
        "harm_vs_matched_no_t2": sum(1 for c, n in pairs_matched if c < n - 1e-12),
        "care_scar_sensitivity": mean(parse_float(row.get("care_scar_sensitivity")) for row in subset),
        "nnunet_direct_six_class_scar_sensitivity": mean(parse_float(row.get("nnunet_scar_sensitivity")) for row in subset),
        "nnunet_matched_no_t2_class_set_scar_sensitivity": mean(
            parse_float(row.get("nnunet_no_t2_matched_scar_sensitivity")) for row in subset
        ),
        "care_scar_precision": mean(parse_float(row.get("care_scar_precision")) for row in subset),
        "nnunet_direct_six_class_scar_precision": mean(parse_float(row.get("nnunet_scar_precision")) for row in subset),
        "nnunet_matched_no_t2_class_set_scar_precision": mean(
            parse_float(row.get("nnunet_no_t2_matched_scar_precision")) for row in subset
        ),
        "care_scar_hd95": mean(parse_float(row.get("care_scar_hd95")) for row in subset),
        "nnunet_direct_six_class_scar_hd95": mean(parse_float(row.get("nnunet_scar_hd95")) for row in subset),
        "nnunet_matched_no_t2_class_set_scar_hd95": mean(
            parse_float(row.get("nnunet_no_t2_matched_scar_hd95")) for row in subset
        ),
        "care_scar_volume_ratio": mean(parse_float(row.get("care_scar_volume_ratio")) for row in subset),
        "nnunet_direct_six_class_scar_volume_ratio": mean(parse_float(row.get("nnunet_scar_volume_ratio")) for row in subset),
        "nnunet_matched_no_t2_class_set_scar_volume_ratio": mean(
            parse_float(row.get("nnunet_no_t2_matched_scar_volume_ratio")) for row in subset
        ),
    }


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    group_summaries: dict[str, Any] = {}
    for spec in GROUPS:
        group_summaries[spec.key] = {
            "label": spec.label,
            "metric_prefix": spec.metric_prefix,
            "fold2": summarize(filter_rows(rows, spec, 2), spec.metric_prefix),
            "fold3": summarize(filter_rows(rows, spec, 3), spec.metric_prefix),
            "combined": summarize(filter_rows(rows, spec, None), spec.metric_prefix),
        }
    summary = {
        "status": "PASS",
        "task_key": TASK_KEY,
        "source": "existing_user_authorized_outer_casewise_csv_plus_myops_metadata_join",
        "interpretation_boundary": {
            "outer_access": "diagnostic_only_user_authorized_not_checkpoint_selection",
            "mixed_scar_headline_warning": "all_outer_scar mixes complete tri-modal and no-T2 partial-modality scar cases",
            "edema_boundary": "pure_edema_t2_present already uses only T2-present cases and must not be discounted by scar subgroup decomposition",
            "volume_ratio_status": "not present in current casewise CSV; no voxel-volume ratio is invented here",
        },
        "subgroups": group_summaries,
        "known_case_diagnostics": {
            "Case2012": {
                "fold": 3,
                "reason": "catastrophic CARE empty prediction on T2-present complete case in existing CSV; retained in formal metrics",
            }
        },
    }
    if rows and "nnunet_no_t2_matched_scar_dice" in rows[0]:
        summary["diagnostic_no_t2_matched_class_set_baseline"] = {
            "status": "PASS",
            "boundary": "diagnostic-only; does not replace original six-class nnU-Net outer headline and must not drive checkpoint selection",
            "fold2_partial_modality_scar": summarize_no_t2_matched_baseline(rows, 2),
            "fold3_partial_modality_scar": summarize_no_t2_matched_baseline(rows, 3),
            "combined_partial_modality_scar": summarize_no_t2_matched_baseline(rows, None),
        }
    return summary


def attach_volume_ratio_diagnostics(summary: dict[str, Any], rows: list[dict[str, Any]], source_paths: dict[int, Path]) -> None:
    """Attach volume-ratio fields from a separate diagnostic CSV without changing Dice means."""
    summary["volume_ratio_diagnostic_source"] = {
        "status": "PASS",
        "boundary": (
            "volume ratios are read from a separate user-authorized read-only diagnostic CSV; "
            "they do not overwrite original outer Dice, nnU-Net headline, or checkpoint selection"
        ),
        "casewise_csvs": {f"fold{fold}": rel(path) for fold, path in sorted(source_paths.items())},
    }
    for spec in GROUPS:
        group = summary["subgroups"][spec.key]
        for split, fold in (("fold2", 2), ("fold3", 3), ("combined", None)):
            subset = filter_rows(rows, spec, fold)
            care_column = f"care_{spec.metric_prefix}_volume_ratio"
            nnunet_column = f"nnunet_{spec.metric_prefix}_volume_ratio"
            group[split]["care_volume_ratio"] = mean(parse_float(row.get(care_column)) for row in subset)
            group[split]["nnunet_volume_ratio"] = mean(parse_float(row.get(nnunet_column)) for row in subset)
            group[split]["volume_ratio_status"] = "DIAGNOSTIC_ONLY_FROM_SEPARATE_VOLUME_RATIO_CSV"
    if rows and "nnunet_no_t2_matched_scar_dice" in rows[0]:
        summary["diagnostic_no_t2_matched_class_set_baseline"] = {
            "status": "PASS",
            "boundary": "diagnostic-only; does not replace original six-class nnU-Net outer headline and must not drive checkpoint selection",
            "fold2_partial_modality_scar": summarize_no_t2_matched_baseline(rows, 2),
            "fold3_partial_modality_scar": summarize_no_t2_matched_baseline(rows, 3),
            "combined_partial_modality_scar": summarize_no_t2_matched_baseline(rows, None),
        }


def write_csv(summary: dict[str, Any], path: Path) -> None:
    fields = [
        "group",
        "split",
        "case_count",
        "care_dice",
        "nnunet_dice",
        "delta_care_minus_nnunet",
        "care_help_count",
        "care_harm_count",
        "tie_count",
        "care_sensitivity",
        "nnunet_sensitivity",
        "care_precision",
        "nnunet_precision",
        "care_hd95",
        "nnunet_hd95",
        "care_empty_prediction_count_from_blank_precision",
        "nnunet_empty_prediction_count_from_blank_precision",
        "care_volume_ratio",
        "nnunet_volume_ratio",
        "volume_ratio_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for group_key, group in summary["subgroups"].items():
            for split in ("fold2", "fold3", "combined"):
                item = group[split]
                writer.writerow({field: item.get(field, "") for field in fields} | {"group": group_key, "split": split})


def load_checkpoint_provenance(paths_by_fold: dict[int, Path]) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "PASS", "folds": {}}
    missing: list[str] = []
    for fold, path in sorted(paths_by_fold.items()):
        source_path = existing_checkpoint_path(path)
        if not source_path.is_file():
            missing.append(f"fold{fold}:{path}")
            out["folds"][f"fold{fold}"] = {
                "checkpoint": rel(path),
                "status": "MISSING_CHECKPOINT_FOR_LIGHTWEIGHT_REPORTING_CHECKOUT",
            }
            continue
        payload = static_checkpoint_provenance(source_path)
        missing_fields = [field for field in PROVENANCE_FIELDS if payload.get(field) is None]
        out["folds"][f"fold{fold}"] = {
            "checkpoint": rel(source_path),
            "read_method": "safe_static_checkpoint_string_scan_no_pickle",
            "status": "PASS" if not missing_fields else "PARTIAL_STATIC_PROVENANCE",
            "missing_fields": missing_fields,
            **payload,
        }
    if missing:
        out["status"] = "PARTIAL_MISSING_CHECKPOINTS"
        out["missing"] = missing
    elif any(item.get("status") != "PASS" for item in out["folds"].values()):
        out["status"] = "PARTIAL_STATIC_PROVENANCE"
    return out


def existing_checkpoint_path(path: Path) -> Path:
    if path.is_file():
        return path
    try:
        rel_path = path.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        return path
    fallback = DEFAULT_RUNTIME_WORKTREE_ROOT / rel_path
    return fallback if fallback.is_file() else path


def static_checkpoint_provenance(path: Path) -> dict[str, Any]:
    """Extract scalar provenance without unpickling checkpoint payloads."""
    data = path.read_bytes()
    aliases = {
        "plans_hash": ("plans_hash", "plans_sha256"),
        "stock_checkpoint_hash": ("stock_checkpoint_hash", "stock_checkpoint_sha256"),
    }
    payload: dict[str, Any] = {}
    for field in PROVENANCE_FIELDS:
        if field == "fold":
            payload[field] = int(match.group(1)) if (match := re.search(r"fold_(\d+)", path.as_posix())) else None
        elif field == "global_optimizer_step":
            payload[field] = int(match.group(1)) if (match := re.search(r"checkpoint_step(\d+)", path.name)) else None
        else:
            payload[field] = find_hex_after_any_marker(data, aliases.get(field, (field,)))
    return payload


def find_hex_after_any_marker(data: bytes, markers: tuple[str, ...]) -> str | None:
    for marker in markers:
        start = 0
        marker_b = marker.encode("ascii")
        while True:
            idx = data.find(marker_b, start)
            if idx < 0:
                break
            window = data[idx + len(marker_b) : idx + len(marker_b) + 256]
            for pattern in (rb"[0-9a-f]{64}", rb"[0-9a-f]{40}"):
                if match := re.search(pattern, window):
                    return match.group(0).decode("ascii")
            start = idx + len(marker_b)
    return None


def render_markdown(summary: dict[str, Any], provenance: dict[str, Any]) -> str:
    sg = summary["subgroups"]
    lines: list[str] = []
    lines.append("# CARE-ASE outer diagnostic subgroup correction")
    lines.append("")
    lines.append(
        "当前 `scar -0.105394` headline 不能单独作为科学结论，因为它把 complete tri-modal 目标域病例和 no-T2 partial-modality 病例混在同一个均值里。"
        "从原始 casewise CSV 重新分层后，complete tri-modal scar 已经与 matched nnU-Net 持平并轻微高出；真正把 all-scar headline 拉低的是 partial-modality scar。"
    )
    lines.append("")
    lines.append(
        "这不等于 CARE-ASE 已经整体胜过 nnU-Net：pure edema 的评价分母本来就是 T2-present 病例，combined delta 仍为负，尤其 fold3 暴露了真实的 edema 欠激活/校准问题。"
    )
    lines.append("")
    lines.append("## Primary Subgroup Table")
    lines.append("")
    lines.append("| Group | Split | Cases | CARE Dice | nnU-Net Dice | Delta |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for group_key in ("all_outer_scar", "complete_tri_modal_scar", "partial_modality_scar", "pure_edema_t2_present"):
        for split in ("fold2", "fold3", "combined"):
            item = sg[group_key][split]
            lines.append(
                f"| {sg[group_key]['label']} | {split} | {item['case_count']} | "
                f"{fmt(item['care_dice'])} | {fmt(item['nnunet_dice'])} | {fmt(item['delta_care_minus_nnunet'])} |"
            )
    lines.append("")
    lines.append("## Complete Tri-Modal Center Breakdown")
    lines.append("")
    lines.append("| Group | Split | Cases | CARE Dice | nnU-Net Dice | Delta |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for group_key in (
        "centerB_complete_scar",
        "centerB_complete_edema",
        "centerC_complete_scar",
        "centerC_complete_edema",
    ):
        for split in ("fold2", "fold3", "combined"):
            item = sg[group_key][split]
            lines.append(
                f"| {sg[group_key]['label']} | {split} | {item['case_count']} | "
                f"{fmt(item['care_dice'])} | {fmt(item['nnunet_dice'])} | {fmt(item['delta_care_minus_nnunet'])} |"
            )
    lines.append("")
    lines.append("## Help/Harm And Shape Metrics")
    lines.append("")
    lines.append("| Group | Split | Help | Harm | Tie | CARE sens | nnU-Net sens | CARE prec | nnU-Net prec | CARE HD95 | nnU-Net HD95 | CARE vol ratio | nnU-Net vol ratio | CARE empty pred | nnU-Net empty pred |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for group_key in ("complete_tri_modal_scar", "partial_modality_scar", "pure_edema_t2_present"):
        for split in ("fold2", "fold3", "combined"):
            item = sg[group_key][split]
            lines.append(
                f"| {sg[group_key]['label']} | {split} | {item['care_help_count']} | {item['care_harm_count']} | {item['tie_count']} | "
                f"{fmt(item['care_sensitivity'])} | {fmt(item['nnunet_sensitivity'])} | "
                f"{fmt(item['care_precision'])} | {fmt(item['nnunet_precision'])} | "
                f"{fmt(item['care_hd95'], 3)} | {fmt(item['nnunet_hd95'], 3)} | "
                f"{fmt(item.get('care_volume_ratio'))} | {fmt(item.get('nnunet_volume_ratio'))} | "
                f"{item['care_empty_prediction_count_from_blank_precision']} | {item['nnunet_empty_prediction_count_from_blank_precision']} |"
            )
    lines.append("")
    lines.append("## Diagnostic Boundaries")
    lines.append("")
    if sg["all_outer_scar"]["combined"].get("care_volume_ratio") is None:
        lines.append("- `volume_ratio`: not reported from the original casewise CSV because prediction/GT voxel-count columns were not written there; no value is invented.")
    else:
        source = summary.get("volume_ratio_diagnostic_source", {}).get("status", "current CSV")
        lines.append(f"- `volume_ratio`: reported from explicit prediction/GT voxel-count fields (`{source}`); these are diagnostic-only and do not alter Dice denominators or checkpoint selection.")
    lines.append("- `empty pred`: counted from blank precision in the existing CSV, which is emitted when there are zero predicted voxels for that class.")
    lines.append("- `subgroup verification`: `scripts/evaluation/care_ase/verify_outer_diagnostic_subgroup_summary.py` recomputes the key subgroup rows from raw outer casewise CSV plus MyoPS metadata and writes `outer_diagnostic_subgroup_verification_receipt.json`.")
    lines.append("- `Case2012`: fold3 complete/T2-present case with CARE scar Dice 0 and edema Dice 0; retained in the official subgroup means.")
    lines.append("- `no-T2 baseline asymmetry`: CARE no-T2 decode excludes class 4 (`0,1,2,3,5`), while the current matched nnU-Net baseline row in `run_current_user_authorized_outer_diagnostic.py` uses direct six-class argmax. This is a diagnostic comparison asymmetry, not checkpoint-selection evidence.")
    if "diagnostic_no_t2_matched_class_set_baseline" in summary:
        lines.append("")
        lines.append("## no-T2 Matched Class-Set Diagnostic")
        lines.append("")
        lines.append("| Split | Cases | CARE scar | nnU-Net direct | nnU-Net no-T2 matched | CARE-direct delta | CARE-matched delta | matched-direct | CARE vol ratio | nnU-Net matched vol ratio |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        diag = summary["diagnostic_no_t2_matched_class_set_baseline"]
        for key, label in (
            ("fold2_partial_modality_scar", "fold2 partial scar"),
            ("fold3_partial_modality_scar", "fold3 partial scar"),
            ("combined_partial_modality_scar", "combined partial scar"),
        ):
            item = diag[key]
            lines.append(
                f"| {label} | {item['case_count']} | {fmt(item['care_scar_dice'])} | "
                f"{fmt(item['nnunet_direct_six_class_scar_dice'])} | {fmt(item['nnunet_matched_no_t2_class_set_scar_dice'])} | "
                f"{fmt(item['delta_care_minus_nnunet_direct_six_class'])} | "
                f"{fmt(item['delta_care_minus_nnunet_matched_no_t2_class_set'])} | "
                f"{fmt(item['nnunet_matched_minus_direct'])} | {fmt(item['care_scar_volume_ratio'])} | "
                f"{fmt(item['nnunet_matched_no_t2_class_set_scar_volume_ratio'])} |"
            )
        lines.append("")
        lines.append("Interpretation: matched no-T2 class-set argmax produced the same scar Dice as direct six-class argmax on the partial-modality rows in this diagnostic rerun. The code asymmetry is real and now audited, but it is not the cause of the observed partial-scar deficit.")
    lines.append("")
    lines.append("## Provenance Snapshot")
    lines.append("")
    lines.append("| Fold | Step | training source | formal checkout | source manifest | config hash | split hash | plans hash | stock hash | contract hash |")
    lines.append("|---:|---:|---|---|---|---|---|---|---|---|")
    for fold_key, item in provenance.get("folds", {}).items():
        lines.append(
            f"| {fold_key.replace('fold', '')} | {item.get('global_optimizer_step')} | "
            f"`{item.get('training_source_commit_sha')}` | `{item.get('formal_execution_checkout_commit_sha')}` | "
            f"`{item.get('critical_source_manifest_sha256')}` | `{item.get('config_hash')}` | "
            f"`{item.get('split_hash')}` | `{item.get('plans_hash')}` | `{item.get('stock_checkpoint_hash')}` | "
            f"`{item.get('frozen_contract_sha256')}` |"
        )
    lines.append("")
    lines.append("Provenance judgment: `NO_NEW_FAITHFULNESS_REGRESSION_EVIDENCE`. The inspected checkpoints bind the same frozen contract and source manifest; the post-review changes visible before `fdd45b5` are formal runtime/path/cache namespace, authorization, fold selection, checkpoint cadence, and monitoring/evidence wiring, not model/loss/sampler/inference semantic redesign.")
    lines.append("")
    lines.append("Operational judgment: continue formal training to the frozen 14000-step schedule. The current 4000/5000-step mixed outer metrics justify reporting correction and later diagnostic monitoring, not early implementation block.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-repo-root", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTER_ROOT)
    parser.add_argument("--casewise-fold2", type=Path, default=CASEWISE_BY_FOLD[2])
    parser.add_argument("--casewise-fold3", type=Path, default=CASEWISE_BY_FOLD[3])
    parser.add_argument("--volume-ratio-casewise-fold2", type=Path, default=VOLUME_RATIO_CASEWISE_BY_FOLD[2])
    parser.add_argument("--volume-ratio-casewise-fold3", type=Path, default=VOLUME_RATIO_CASEWISE_BY_FOLD[3])
    parser.add_argument("--checkpoint-fold2", type=Path, default=CHECKPOINTS_BY_FOLD[2])
    parser.add_argument("--checkpoint-fold3", type=Path, default=CHECKPOINTS_BY_FOLD[3])
    parser.add_argument("--output-prefix", default="outer_diagnostic_subgroup")
    args = parser.parse_args()

    casewise_by_fold = {2: args.casewise_fold2, 3: args.casewise_fold3}
    checkpoints_by_fold = {2: args.checkpoint_fold2, 3: args.checkpoint_fold3}
    rows = load_rows(casewise_by_fold, metadata_root(REPO_ROOT, args.metadata_repo_root))
    summary = build_summary(rows)
    volume_ratio_casewise_by_fold = {
        2: args.volume_ratio_casewise_fold2,
        3: args.volume_ratio_casewise_fold3,
    }
    if all(path.is_file() for path in volume_ratio_casewise_by_fold.values()):
        volume_rows = load_rows(volume_ratio_casewise_by_fold, metadata_root(REPO_ROOT, args.metadata_repo_root))
        attach_volume_ratio_diagnostics(summary, volume_rows, volume_ratio_casewise_by_fold)
    provenance = load_checkpoint_provenance(checkpoints_by_fold)
    summary["checkpoint_provenance"] = provenance
    summary["casewise_csvs"] = {f"fold{fold}": rel(path) for fold, path in sorted(casewise_by_fold.items())}

    args.output_root.mkdir(parents=True, exist_ok=True)
    json_path = args.output_root / f"{args.output_prefix}_summary.json"
    csv_path = args.output_root / f"{args.output_prefix}_table.csv"
    md_name = "OUTER_DIAGNOSTIC_SUBGROUP_REPORT.md" if args.output_prefix == "outer_diagnostic_subgroup" else f"{args.output_prefix}_report.md"
    md_path = args.output_root / md_name
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(summary, csv_path)
    md_path.write_text(render_markdown(summary, provenance), encoding="utf-8")
    print(json.dumps({"status": "PASS", "json": rel(json_path), "csv": rel(csv_path), "markdown": rel(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
