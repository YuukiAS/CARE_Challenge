#!/usr/bin/env python3
"""Aggregate Batch7 minimal/BR2/SIP pathology decomposition runs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.aggregate_srr_batch6_formal import (  # noqa: E402
    help_harm_rows,
    mean,
    metric_rows_for_step,
    read_csv,
    rel,
    write_csv,
    write_json,
)
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402

PATHOLOGY_METRIC = {"scar": "myops_scar", "edema": "myops_edema"}
RUN_SUFFIXES = ("minimal", "br2_no_sip", "br2_sip")
FINAL_STEP = 400
EVAL_STEPS = (200, 400)


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def variant_dir(result_root: Path, attempt_label: str, pathology: str, suffix: str) -> Path:
    run_label = f"{pathology}_{suffix}__{attempt_label}"
    return result_root / "runtime/attempts" / attempt_label / "variants" / run_label


def require_variant(variant: Path, *, br2: bool) -> dict[str, Any]:
    summary_path = variant / "summary.json"
    if not summary_path.is_file():
        raise SystemExit(f"missing variant summary: {summary_path}")
    summary = load_json(summary_path)
    expected_series = 400
    if br2:
        if int(summary.get("completed_global_step", -1)) != 400:
            raise SystemExit(f"BR2 completed_global_step mismatch in {variant}: {summary.get('completed_global_step')}")
        if int(summary.get("total_optimizer_steps_in_series", -1)) != expected_series:
            raise SystemExit(f"BR2 total_optimizer_steps_in_series mismatch in {variant}")
        if int(summary.get("resume_start_global_step", -1)) != 50:
            raise SystemExit(f"BR2 resume_start_global_step mismatch in {variant}")
    else:
        if int(summary.get("actual_optimizer_steps", -1)) != expected_series:
            raise SystemExit(f"minimal actual_optimizer_steps mismatch in {variant}")
    for step in EVAL_STEPS:
        for name in (f"component_hd_by_case_step_{step}.csv", f"proposal_pr_sweep_step_{step}.csv"):
            if not (variant / name).is_file():
                raise SystemExit(f"missing eval artifact: {variant / name}")
    return summary


def add_paths_to_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(cfg)
    paths = dict(cfg.get("paths", {}))
    paths.setdefault("gt_dir", "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr")
    paths.setdefault(
        "anchor_fold0_pred_dir",
        "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation",
    )
    cfg["paths"] = paths
    return cfg


def target_case_rows(cfg: dict[str, Any], variant: Path, experiment: str, pathology: str) -> list[dict[str, Any]]:
    metric = PATHOLOGY_METRIC[pathology]
    rows: list[dict[str, Any]] = []
    for step in EVAL_STEPS:
        for row in metric_rows_for_step(cfg, variant, step, step):
            if row["pathology"] != metric:
                continue
            rows.append({**row, "experiment": experiment, "eval_step": step})
    return rows


def in_group(row: dict[str, Any], group: str) -> bool:
    if group == "all_cases":
        return True
    if group == "gt_positive_only":
        return bool(row["gt_positive"])
    if group == "complete_trimodal":
        return row["modality_group"] == "C0+LGE+T2"
    if group == "CenterB":
        return row["center"] == "CenterB"
    if group == "CenterC":
        return row["center"] == "CenterC"
    if group == "all_positive_centers":
        return bool(row["gt_positive"])
    return False


def summarize_deployment(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    groups = ("all_cases", "gt_positive_only", "complete_trimodal", "CenterB", "CenterC", "all_positive_centers")
    for experiment in sorted({row["experiment"] for row in rows}):
        exp_rows = [row for row in rows if row["experiment"] == experiment and int(row["eval_step"]) == FINAL_STEP]
        for group in groups:
            selected = [row for row in exp_rows if in_group(row, group)]
            metric_rows = [row for row in selected if row["srr_dice"] is not None and row["anchor_dice"] is not None]
            hd_rows = [row for row in selected if row["srr_hd95"] is not None and row["anchor_hd95"] is not None]
            out.append(
                {
                    "experiment": experiment,
                    "subgroup": group,
                    "case_count": len(selected),
                    "metric_case_count": len(metric_rows),
                    "anchor_dice_mean": mean([float(row["anchor_dice"]) for row in metric_rows]),
                    "srr_dice_mean": mean([float(row["srr_dice"]) for row in metric_rows]),
                    "dice_delta_mean": mean([float(row["dice_delta_vs_anchor"]) for row in metric_rows]),
                    "anchor_hd95_mean": mean([float(row["anchor_hd95"]) for row in hd_rows]),
                    "srr_hd95_mean": mean([float(row["srr_hd95"]) for row in hd_rows]),
                    "hd95_delta_mean": mean([float(row["hd95_delta_vs_anchor"]) for row in hd_rows]),
                    "remote_fp_delta_mm3_mean": mean([float(row["remote_fp_delta_mm3"]) for row in selected]),
                }
            )
        center_rows = [row for row in exp_rows if row["gt_positive"]]
        center_means = []
        for center in sorted({row["center"] for row in center_rows}):
            selected = [row for row in center_rows if row["center"] == center]
            values = [float(row["srr_dice"]) for row in selected if row["srr_dice"] is not None]
            if values:
                center_means.append((center, float(mean(values))))
        if center_means:
            center, value = min(center_means, key=lambda item: item[1])
            out.append({"experiment": experiment, "subgroup": "worst_positive_center", "case_count": "", "metric_case_count": "", "worst_center": center, "srr_dice_mean": value})
    return out


def proposal_rows(variant: Path, experiment: str, pathology: str) -> list[dict[str, Any]]:
    metric = PATHOLOGY_METRIC[pathology]
    rows: list[dict[str, Any]] = []
    for step in EVAL_STEPS:
        sweep = csv_rows(variant / f"proposal_pr_sweep_step_{step}.csv")
        selected = [row for row in sweep if row.get("metric_name") == metric and row.get("proposal_threshold") == "0.5"]
        for key in ("proposal_precision", "proposal_recall", "lesion_wise_recall"):
            values = [float(row[key]) for row in selected if row.get(key) not in {"", None}]
            rows.append({"experiment": experiment, "eval_step": step, "metric": key, "value": mean(values), "threshold": 0.5, "case_count": len(values)})
        rows.append({"experiment": experiment, "eval_step": step, "metric": "anchor_missed_recovery", "value": "PENDING_ANCHOR_ERROR_STRATIFIED_AGGREGATION", "threshold": 0.5, "case_count": len(selected)})
        rows.append({"experiment": experiment, "eval_step": step, "metric": "false_positive_suppression", "value": "PENDING_ANCHOR_ERROR_STRATIFIED_AGGREGATION", "threshold": 0.5, "case_count": len(selected)})
    return rows


def row_value(rows: list[dict[str, Any]], experiment: str, subgroup: str, key: str) -> float | None:
    for row in rows:
        if row.get("experiment") == experiment and row.get("subgroup") == subgroup and row.get(key) not in {"", None}:
            return float(row[key])
    return None


def decision_rows(pathology: str, subgroup_rows: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    minimal = f"{pathology}_minimal"
    no_sip = f"{pathology}_br2_no_sip"
    sip = f"{pathology}_br2_sip"
    min_gate = cfg["minimal_retain_gate"]
    br2_gate = cfg["br2_increment_gate"]
    sip_gate = cfg["sip_increment_gate"]
    min_delta = row_value(subgroup_rows, minimal, "gt_positive_only", "dice_delta_mean")
    min_complete = row_value(subgroup_rows, minimal, "complete_trimodal", "dice_delta_mean")
    no_sip_dice = row_value(subgroup_rows, no_sip, "gt_positive_only", "srr_dice_mean")
    minimal_dice = row_value(subgroup_rows, minimal, "gt_positive_only", "srr_dice_mean")
    sip_dice = row_value(subgroup_rows, sip, "gt_positive_only", "srr_dice_mean")
    br2_increment = None if no_sip_dice is None or minimal_dice is None else no_sip_dice - minimal_dice
    sip_increment = None if sip_dice is None or no_sip_dice is None else sip_dice - no_sip_dice
    minimal_decision = "RETAIN" if min_delta is not None and min_delta >= float(min_gate["minimum_positive_dice_delta"]) and (min_complete is None or min_complete >= 0.0) else "RETIRE"
    br2_decision = "NOT_APPLICABLE" if minimal_decision == "RETIRE" else ("RETAIN" if br2_increment is not None and br2_increment >= float(br2_gate["minimum_additional_positive_dice_over_minimal"]) else "RETIRE")
    sip_decision = "NOT_APPLICABLE" if br2_decision != "RETAIN" else ("RETAIN" if sip_increment is not None and sip_increment >= float(sip_gate["minimum_additional_positive_dice_over_no_sip"]) else "REMOVE")
    decisions = [
        {"decision_id": f"{pathology}_minimal", "decision": minimal_decision, "basis": "positive_dice_delta_and_complete_trimodal_gate"},
        {"decision_id": f"{pathology}_br2", "decision": br2_decision, "basis": "increment_over_minimal"},
        {"decision_id": f"{pathology}_sip", "decision": sip_decision, "basis": "increment_over_no_sip"},
    ]
    br2_rows = [{"pathology": pathology, "br2_increment_over_minimal": br2_increment, "decision": br2_decision}]
    sip_rows = [{"pathology": pathology, "sip_increment_over_no_sip": sip_increment, "decision": sip_decision}]
    return decisions, br2_rows, sip_rows


def aggregate_pathology(cfg: dict[str, Any], result_root: Path, pathology: str, attempt_label: str) -> dict[str, Any]:
    case_rows: list[dict[str, Any]] = []
    proposal: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    coeff_rows: list[dict[str, Any]] = []
    for suffix in RUN_SUFFIXES:
        experiment = f"{pathology}_{suffix}"
        variant = variant_dir(result_root, attempt_label, pathology, suffix)
        summary = require_variant(variant, br2=suffix.startswith("br2"))
        case_rows.extend(target_case_rows(cfg, variant, experiment, pathology))
        proposal.extend(proposal_rows(variant, experiment, pathology))
        checkpoint = variant / "checkpoints/fold_0/propref_config/checkpoint_validation_step_400.pt"
        checkpoint_rows.append(
            {
                "pathology": pathology,
                "experiment": experiment,
                "selected_step": 400,
                "checkpoint_path": rel(checkpoint),
                "checkpoint_sha256": sha256_file(checkpoint) if checkpoint.is_file() else "",
                "actual_optimizer_steps": summary.get("actual_optimizer_steps"),
                "completed_global_step": summary.get("completed_global_step"),
                "total_optimizer_steps_in_series": summary.get("total_optimizer_steps_in_series"),
                "summary_path": rel(variant / "summary.json"),
            }
        )
        coeff_rows.append({"pathology": pathology, "experiment": experiment, "source": "summary_and_br2_diagnostics", "status": "PENDING_DETAILED_BETA_EXPORT"})
    subgroup_rows = summarize_deployment(case_rows)
    help_rows = help_harm_rows(case_rows, FINAL_STEP)
    write_csv(result_root / f"{pathology}_casewise_metrics.csv", case_rows)
    write_csv(result_root / f"{pathology}_deployment_subgroup_metrics.csv", subgroup_rows)
    write_csv(result_root / f"{pathology}_proposal_mechanism_metrics.csv", proposal)
    write_csv(result_root / f"{pathology}_checkpoint_selection.csv", checkpoint_rows)
    write_csv(result_root / f"{pathology}_help_harm.csv", help_rows)
    write_csv(result_root / f"{pathology}_source_learner_coefficients.csv", coeff_rows)
    return {"pathology": pathology, "case_rows": case_rows, "subgroup_rows": subgroup_rows, "proposal_rows": proposal, "checkpoint_rows": checkpoint_rows}


def selected_sip_weights(result_root: Path) -> dict[str, str]:
    weights: dict[str, str] = {}
    for row in read_csv(result_root / "sip_weight_calibration.csv"):
        if row.get("selected") == "1" and row.get("selected_lambda") not in {"", None}:
            weights[row["pathology"]] = row["selected_lambda"]
    return weights


def update_matched_manifest(result_root: Path, completed_pathologies: set[str]) -> None:
    path = result_root / "matched_run_manifest.csv"
    rows = read_csv(path)
    sip_weights = selected_sip_weights(result_root)
    out = []
    for row in rows:
        if row.get("pathology") in completed_pathologies:
            row = {**row, "runtime_status": "TERMINAL_AGGREGATED_PASS"}
            if row.get("experiment", "").endswith("_br2_sip"):
                selected = sip_weights.get(row["pathology"])
                if selected is None:
                    raise SystemExit(f"missing selected SIP lambda for completed {row['pathology']}")
                row["sip_weight"] = selected
        out.append(row)
    write_csv(path, out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_minimal_decomposition.yaml")
    parser.add_argument("--result-root", default="results/20260722_srr_batch7_minimal_pathology_decomposition")
    parser.add_argument("--scar-attempt-label", default="")
    parser.add_argument("--edema-attempt-label", default="")
    args = parser.parse_args()
    cfg = add_paths_to_cfg(yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8")))
    result_root = repo_path(args.result_root)
    completed: set[str] = set()
    all_case_rows: list[dict[str, Any]] = []
    all_subgroup_rows: list[dict[str, Any]] = []
    all_proposal_rows: list[dict[str, Any]] = []
    all_checkpoint_rows: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    br2_rows: list[dict[str, Any]] = []
    sip_rows: list[dict[str, Any]] = []
    for pathology, attempt_label in (("scar", args.scar_attempt_label), ("edema", args.edema_attempt_label)):
        if not attempt_label:
            continue
        payload = aggregate_pathology(cfg, result_root, pathology, attempt_label)
        completed.add(pathology)
        all_case_rows.extend(payload["case_rows"])
        all_subgroup_rows.extend({**row, "pathology": pathology} for row in payload["subgroup_rows"])
        all_proposal_rows.extend({**row, "pathology": pathology} for row in payload["proposal_rows"])
        all_checkpoint_rows.extend(payload["checkpoint_rows"])
        d_rows, b_rows, s_rows = decision_rows(pathology, payload["subgroup_rows"], cfg)
        decisions.extend(d_rows)
        br2_rows.extend(b_rows)
        sip_rows.extend(s_rows)
    if not completed:
        raise SystemExit("no pathology attempt labels were provided")
    update_matched_manifest(result_root, completed)
    if all_case_rows:
        write_csv(result_root / "casewise_metrics.csv", all_case_rows)
        write_csv(result_root / "subgroup_metrics.csv", all_subgroup_rows)
        write_csv(result_root / "proposal_mechanism_metrics.csv", all_proposal_rows)
        write_csv(result_root / "help_harm.csv", help_harm_rows(all_case_rows, FINAL_STEP))
        write_csv(result_root / "checkpoint_selection.csv", all_checkpoint_rows)
    if decisions:
        write_csv(result_root / "pathology_decision_matrix.csv", decisions)
        write_csv(result_root / "br2_increment_matrix.csv", br2_rows)
        write_csv(result_root / "sip_increment_matrix.csv", sip_rows)
        write_csv(result_root / "deployment_subgroup_metrics.csv", all_subgroup_rows)
    write_json(
        result_root / "minimal_decomposition_aggregation_status.json",
        {"status": "PARTIAL" if completed != {"scar", "edema"} else "PASS", "completed_pathologies": sorted(completed)},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
