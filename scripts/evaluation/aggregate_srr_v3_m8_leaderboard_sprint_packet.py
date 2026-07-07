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
    contribution = read_csv(packet / "m8_srr_contribution_by_case.csv")
    if not contribution or any(row.get("anchor_delta_rate") in {"", "EVIDENCE_NOT_FOUND", "EVIDENCE_NOT_EXPORTED_PER_CASE"} for row in contribution[:20]):
        issues.append("per_case_contribution_anchor_delta_missing")
        return "M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE", issues
    temporal = read_csv(packet / "m8_temporal_dictionary_evidence.csv")
    if temporal and any("USABLE" in str(row).upper() for row in read_csv(cine_matrix)) and not any(row.get("status") not in {"", MONITOR_STATUS} for row in temporal):
        issues.append("usable_registration_without_temporal_dictionary")
        return "M8_NEEDS_EVIDENCE_CINE_REGISTRATION", issues
    return "M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE", ["ready gate intentionally requires final reviewer-grade metric/contribution audit"]


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
                "This M8 packet is not leaderboard-ready. It is an executor evidence packet with completed training-budget aggregation and remaining reviewer-grade evidence gates.",
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
                "Next action: reviewer or follow-up executor must audit the final metric/contribution evidence and the Cine registration-blocked state before any normal review, route promotion, validation packaging, upload, or next milestone.",
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
    write_decision_docs(packet, status, issues, summaries, ledger)
    write_manifest(packet)
    print(json.dumps({"packet": str(packet), "status": status, "issues": issues}, indent=2))


if __name__ == "__main__":
    main()
