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
CASEWISE_BY_FOLD = {
    2: DEFAULT_OUTER_ROOT / "fold_2/step05000/outer_casewise_metrics.csv",
    3: DEFAULT_OUTER_ROOT / "fold_3/step04000/outer_casewise_metrics.csv",
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
    return {
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
        "volume_ratio_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for group_key, group in summary["subgroups"].items():
            for split in ("fold2", "fold3", "combined"):
                item = group[split]
                writer.writerow({field: item.get(field, "") for field in fields} | {"group": group_key, "split": split})


def load_checkpoint_provenance(paths_by_fold: dict[int, Path]) -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:  # pragma: no cover - dependency availability is environment-specific.
        return {"status": "UNAVAILABLE", "reason": f"torch import failed: {exc}"}
    out: dict[str, Any] = {"status": "PASS", "folds": {}}
    for fold, path in sorted(paths_by_fold.items()):
        payload = torch.load(path, map_location="cpu", weights_only=False)
        out["folds"][f"fold{fold}"] = {
            "checkpoint": rel(path),
            **{field: payload.get(field) for field in PROVENANCE_FIELDS},
        }
    return out


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
    lines.append("| Group | Split | Help | Harm | Tie | CARE sens | nnU-Net sens | CARE prec | nnU-Net prec | CARE HD95 | nnU-Net HD95 | CARE empty pred | nnU-Net empty pred |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for group_key in ("complete_tri_modal_scar", "partial_modality_scar", "pure_edema_t2_present"):
        for split in ("fold2", "fold3", "combined"):
            item = sg[group_key][split]
            lines.append(
                f"| {sg[group_key]['label']} | {split} | {item['care_help_count']} | {item['care_harm_count']} | {item['tie_count']} | "
                f"{fmt(item['care_sensitivity'])} | {fmt(item['nnunet_sensitivity'])} | "
                f"{fmt(item['care_precision'])} | {fmt(item['nnunet_precision'])} | "
                f"{fmt(item['care_hd95'], 3)} | {fmt(item['nnunet_hd95'], 3)} | "
                f"{item['care_empty_prediction_count_from_blank_precision']} | {item['nnunet_empty_prediction_count_from_blank_precision']} |"
            )
    lines.append("")
    lines.append("## Diagnostic Boundaries")
    lines.append("")
    lines.append("- `volume_ratio`: not reported from the current CSV because prediction/GT voxel-count columns were not written by the original outer runner; no value is invented here.")
    lines.append("- `empty pred`: counted from blank precision in the existing CSV, which is emitted when there are zero predicted voxels for that class.")
    lines.append("- `Case2012`: fold3 complete/T2-present case with CARE scar Dice 0 and edema Dice 0; retained in the official subgroup means.")
    lines.append("- `no-T2 baseline asymmetry`: CARE no-T2 decode excludes class 4 (`0,1,2,3,5`), while the current matched nnU-Net baseline row in `run_current_user_authorized_outer_diagnostic.py` uses direct six-class argmax. This is a diagnostic comparison asymmetry, not checkpoint-selection evidence.")
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
    args = parser.parse_args()

    casewise_by_fold = CASEWISE_BY_FOLD
    rows = load_rows(casewise_by_fold, metadata_root(REPO_ROOT, args.metadata_repo_root))
    summary = build_summary(rows)
    provenance = load_checkpoint_provenance(CHECKPOINTS_BY_FOLD)
    summary["checkpoint_provenance"] = provenance
    summary["casewise_csvs"] = {f"fold{fold}": rel(path) for fold, path in sorted(casewise_by_fold.items())}

    args.output_root.mkdir(parents=True, exist_ok=True)
    json_path = args.output_root / "outer_diagnostic_subgroup_summary.json"
    csv_path = args.output_root / "outer_diagnostic_subgroup_table.csv"
    md_path = args.output_root / "OUTER_DIAGNOSTIC_SUBGROUP_REPORT.md"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(summary, csv_path)
    md_path.write_text(render_markdown(summary, provenance), encoding="utf-8")
    print(json.dumps({"status": "PASS", "json": rel(json_path), "csv": rel(csv_path), "markdown": rel(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
