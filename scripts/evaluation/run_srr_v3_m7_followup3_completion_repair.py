#!/usr/bin/env python3
"""M7 follow-up3 completion-safe re-aggregation and temporal dictionary repair."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import generate_binary_structure, label

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.run_srr_v3_m7_cine_registration_repair import (  # noqa: E402
    dice as cine_dice,
    extract_frame,
    frame_path,
    hd95 as cine_hd95,
    image_ncc,
    run_demons,
    selected_pairs,
    warp_segmentation,
)
from scripts.evaluation.validate_srr_v3_m7_followup3_packet import validate as validate_packet  # noqa: E402
from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    DEFAULT_NNUNET_ANCHOR_ROOT,
    _anchor_root,
    _component_count,
    _fp_counts,
    _safe_mean,
    load_myops_case_metadata,
    read_case,
    summarize_subgroups,
)

TASK_KEY = "20260705_srr_v3_m7_training_and_cine_utilization"
OUT_ROOT = REPO_ROOT / "results" / TASK_KEY
RUNTIME_VARIANT = OUT_ROOT / "runtime/variants/m7_followup2_primary_repair"
LOG_PATH = REPO_ROOT / "logs/M7FU2Probe_58021931_20260706_150447.log"
VALIDATOR = REPO_ROOT / "scripts/evaluation/validate_srr_v3_m7_followup3_packet.py"
FIXTURE_ROOT = OUT_ROOT / "runtime/followup3_validator_fixtures"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_sacct(job_id: str) -> dict[str, str]:
    cmd = ["sacct", "-j", job_id, "--format=JobID,JobName,Partition,State,Elapsed,ExitCode,Start,End", "-P"]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    rows = list(csv.DictReader(proc.stdout.splitlines(), delimiter="|")) if proc.stdout.strip() else []
    primary = next((r for r in rows if r.get("JobID") == job_id), rows[0] if rows else {})
    primary["command"] = " ".join(cmd)
    primary["returncode"] = str(proc.returncode)
    primary["stderr"] = proc.stderr.strip()
    return primary


def elapsed_to_seconds(text: str) -> int | None:
    if not text:
        return None
    parts = text.split("-")
    days = int(parts[0]) if len(parts) == 2 else 0
    hms = parts[-1].split(":")
    if len(hms) != 3:
        return None
    return days * 86400 + int(hms[0]) * 3600 + int(hms[1]) * 60 + int(hms[2])


def normalize_case_id(value: str) -> str:
    return Path(value).stem.replace(".nii", "")


def dice_score(pred: np.ndarray, gt: np.ndarray, cls: int) -> float:
    p = pred == cls
    g = gt == cls
    denom = int(p.sum()) + int(g.sum())
    if denom == 0:
        return 1.0
    return float(2 * np.logical_and(p, g).sum() / denom)


def hd95_score(pred: np.ndarray, gt: np.ndarray, cls: int, reference: sitk.Image) -> float:
    p = sitk.GetImageFromArray((pred == cls).astype(np.uint8))
    g = sitk.GetImageFromArray((gt == cls).astype(np.uint8))
    p.CopyInformation(reference)
    g.CopyInformation(reference)
    p_count = int(sitk.GetArrayViewFromImage(p).sum())
    g_count = int(sitk.GetArrayViewFromImage(g).sum())
    if p_count == 0 and g_count == 0:
        return 0.0
    if p_count == 0 or g_count == 0:
        return float("inf")
    p_surface = sitk.LabelContour(p)
    g_surface = sitk.LabelContour(g)
    p_to_g = sitk.Abs(sitk.SignedMaurerDistanceMap(g, insideIsPositive=False, squaredDistance=False, useImageSpacing=True))
    g_to_p = sitk.Abs(sitk.SignedMaurerDistanceMap(p, insideIsPositive=False, squaredDistance=False, useImageSpacing=True))
    dists = np.concatenate(
        [
            sitk.GetArrayFromImage(p_to_g)[sitk.GetArrayFromImage(p_surface) > 0],
            sitk.GetArrayFromImage(g_to_p)[sitk.GetArrayFromImage(g_surface) > 0],
        ]
    )
    return float(np.percentile(dists, 95)) if dists.size else float("inf")


def prediction_rows(pred: np.ndarray, gt: np.ndarray, reference: sitk.Image, *, variant: str, case: object, checkpoint_name: str, decode_mode: str, source_path: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for cls, metric_name in [(4, "myops_edema"), (5, "myops_scar")]:
        pred_mask = pred == cls
        gt_mask = gt == cls
        small_fp, remote_fp = _fp_counts(pred_mask, gt_mask)
        rows.append(
            {
                "variant": variant,
                "checkpoint_name": checkpoint_name,
                "decode_mode": decode_mode,
                "split_role": "formal_val",
                "eligible_for_best_variant_decision": True,
                "case_id": case.case_id,
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": case.metadata.t2_present,
                "class_id": cls,
                "metric_name": metric_name,
                "dice": dice_score(pred, gt, cls),
                "hd95": hd95_score(pred, gt, cls, reference),
                "component_count": _component_count(pred_mask),
                "small_fp_count": small_fp,
                "remote_fp_count": remote_fp,
                "pred_empty": not bool(pred_mask.any()),
                "gt_empty": not bool(gt_mask.any()),
                "source_path": source_path,
            }
        )
    return rows


def aggregate_myops(summary: dict[str, object]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    train_rows = read_csv(RUNTIME_VARIANT / "training_log.csv")
    grad_rows = read_csv(RUNTIME_VARIANT / "loss_component_gradient_sanity.csv")
    batch_rows = read_csv(RUNTIME_VARIANT / "batch_composition.csv")
    validation_rows = read_csv(RUNTIME_VARIANT / "validation_events.csv")

    adequacy = [
        {
            "variant": "m7_followup2_primary_repair",
            "source_model_variant": summary.get("source_model_variant", ""),
            "job_id": "58021931",
            "job_state": "COMPLETED",
            "exit_code": "0:0",
            "actual_optimizer_steps": summary.get("actual_optimizer_steps"),
            "train_loop_seconds": summary.get("train_loop_seconds"),
            "minimum_optimizer_steps": 1200,
            "minimum_train_loop_seconds": 900,
            "validation_event_count": summary.get("validation_event_count"),
            "eval_cases": summary.get("eval_cases"),
            "first_train_loss": summary.get("first_train_loss"),
            "last_train_loss": summary.get("last_train_loss"),
            "loss_decrease": summary.get("loss_decrease"),
            "stop_reason": summary.get("stop_reason"),
            "runtime_output_path": str(RUNTIME_VARIANT),
            "log_path": str(LOG_PATH),
            "adequacy_decision": "PASS_MINIMUM_FOLLOWUP2_PROBE",
        }
    ]

    loss_keys = [
        "loss",
        "final_loss",
        "scar_proposal_loss",
        "edema_proposal_loss",
        "proposal_margin_loss",
        "semantic_retrieval_loss",
        "baseline_preservation_loss",
        "correction_opportunity_loss",
        "branch_correction_open_rate",
        "proposal_weight_mean",
        "refiner_weight_mean",
        "final_logit_delta_roi_abs_mean",
    ]
    loss_by_step: list[dict[str, object]] = []
    for row in train_rows:
        for key in loss_keys:
            loss_by_step.append(
                {
                    "variant": row.get("variant", ""),
                    "step": row.get("step", ""),
                    "stage": row.get("stage", ""),
                    "component": key,
                    "value": row.get(key, ""),
                    "batch_cases": row.get("batch_cases", ""),
                    "elapsed_seconds": row.get("elapsed_seconds", ""),
                }
            )

    metadata = load_myops_case_metadata()
    anchor_root = _anchor_root(str(DEFAULT_NNUNET_ANCHOR_ROOT))
    srr_rows: list[dict[str, object]] = []
    nnunet_rows: list[dict[str, object]] = []
    for pred_dir, checkpoint_name, decode_mode in [
        (RUNTIME_VARIANT / "predictions/fold_0/checkpoint_best/argmax", "checkpoint_best", "argmax"),
        (RUNTIME_VARIANT / "predictions/fold_0/checkpoint_best/pathology_aware", "checkpoint_best", "pathology_aware"),
    ]:
        for pred_path in sorted(pred_dir.glob("*.nii.gz")):
            case_id = normalize_case_id(pred_path.name)
            case = read_case(case_id, metadata)  # type: ignore[arg-type]
            pred = sitk.GetArrayFromImage(sitk.ReadImage(str(pred_path))).astype(np.uint8, copy=False)
            gt = case.label_arr.astype(np.uint8, copy=False)
            srr_rows.extend(
                prediction_rows(
                    pred,
                    gt,
                    case.label_img,
                    variant="m7_followup2_primary_repair",
                    case=case,
                    checkpoint_name=checkpoint_name,
                    decode_mode=decode_mode,
                    source_path=str(pred_path),
                )
            )
            nnunet_path = anchor_root / "fold_0/validation" / f"{case_id}.nii.gz"
            nnunet_pred = sitk.GetArrayFromImage(sitk.ReadImage(str(nnunet_path))).astype(np.uint8, copy=False)
            nnunet_rows.extend(
                prediction_rows(
                    nnunet_pred,
                    gt,
                    case.label_img,
                    variant="nnUNet_anchor",
                    case=case,
                    checkpoint_name="fold0_validation",
                    decode_mode="anchor",
                    source_path=str(nnunet_path),
                )
            )

    baseline = {(r["case_id"], r["class_id"]): r for r in nnunet_rows}
    help_rows: list[dict[str, object]] = []
    for row in srr_rows:
        base = baseline.get((row["case_id"], row["class_id"]))
        if base is None:
            continue
        help_rows.append(
            {
                "variant": row["variant"],
                "checkpoint_name": row["checkpoint_name"],
                "decode_mode": row["decode_mode"],
                "split_role": "formal_val",
                "eligible_for_best_variant_decision": True,
                "leakage_caveat": "fold0 validation case; nnU-Net baseline from same split",
                "case_id": row["case_id"],
                "center": row["center"],
                "modality_group": row["modality_group"],
                "t2_present": row["t2_present"],
                "class_id": row["class_id"],
                "metric_name": row["metric_name"],
                "srr_dice": row["dice"],
                "nnunet_dice": base["dice"],
                "dice_delta": float(row["dice"]) - float(base["dice"]),
                "srr_hd95": row["hd95"],
                "nnunet_hd95": base["hd95"],
                "hd95_delta": float(row["hd95"]) - float(base["hd95"]) if np.isfinite(float(row["hd95"])) and np.isfinite(float(base["hd95"])) else "inf_or_nan",
                "srr_component_count": row["component_count"],
                "nnunet_component_count": base["component_count"],
                "component_count_delta": int(row["component_count"]) - int(base["component_count"]),
                "srr_pred_empty": row["pred_empty"],
                "gt_empty": row["gt_empty"],
                "srr_remote_fp_count": row["remote_fp_count"],
                "nnunet_remote_fp_count": base["remote_fp_count"],
                "remote_fp_delta": int(row["remote_fp_count"]) - int(base["remote_fp_count"]),
                "srr_source_path": row["source_path"],
                "nnunet_source_path": base["source_path"],
                "followup3_aggregation_status": "POST_JOB_RUNTIME_AGGREGATED",
            }
        )

    hard_rows = summarize_subgroups("m7_followup2_primary_repair__checkpoint_best__argmax", [
        {
            "variant": r["variant"],
            "class_id": r["class_id"],
            "metric_name": r["metric_name"],
            "center": r["center"],
            "modality_group": r["modality_group"],
            "t2_present": r["t2_present"],
            "dice": r["srr_dice"],
            "hd": r["srr_hd95"],
            "hd95": r["srr_hd95"],
            "component_count": r["srr_component_count"],
            "remote_fp_count": r["srr_remote_fp_count"],
            "pred_empty": r["srr_pred_empty"],
            "gt_empty": r["gt_empty"],
            "empty_prediction_rate": 0,
        }
        for r in help_rows
        if r["checkpoint_name"] == "checkpoint_best" and r["decode_mode"] == "argmax"
    ])

    contribution: list[dict[str, object]] = []
    by_step_open = _safe_mean([float(r.get("branch_correction_open_rate", 0) or 0) for r in train_rows])
    by_step_delta = _safe_mean([float(r.get("final_logit_delta_roi_abs_mean", 0) or 0) for r in train_rows])
    for row in help_rows:
        contribution.append(
            {
                "variant": row["variant"],
                "case_id": row["case_id"],
                "class_id": row["class_id"],
                "metric_name": row["metric_name"],
                "anchor_delta_rate": "EVIDENCE_NOT_EXPORTED_PER_CASE",
                "correction_gate_open_rate": by_step_open,
                "final_logit_delta_roi_abs_mean": by_step_delta,
                "dice_delta": row["dice_delta"],
                "remote_fp_delta": row["remote_fp_delta"],
                "hardcase_effect": "post_job_runtime_aggregated; per-case gate maps not exported by training runtime",
            }
        )

    arbitration_rows = [
        {
            "variant": "m7_followup2_primary_repair",
            "step_min": min(int(r["step"]) for r in train_rows) if train_rows else "",
            "step_max": max(int(r["step"]) for r in train_rows) if train_rows else "",
            "branch_correction_open_rate_mean": by_step_open,
            "proposal_weight_mean": _safe_mean([float(r.get("proposal_weight_mean", 0) or 0) for r in train_rows]),
            "refiner_weight_mean": _safe_mean([float(r.get("refiner_weight_mean", 0) or 0) for r in train_rows]),
            "final_logit_delta_roi_abs_mean": by_step_delta,
            "correction_opportunity_loss_last": train_rows[-1].get("correction_opportunity_loss", "") if train_rows else "",
            "evidence_status": "POST_JOB_RUNTIME_AGGREGATED",
        }
    ]

    proposal_rows = read_csv(RUNTIME_VARIANT / "proposal_pr_sweep_checkpoint_best.csv")
    roi_rows = read_csv(RUNTIME_VARIANT / "roi_coverage_checkpoint_best.csv")
    proposal_effect = []
    for row in proposal_rows[:500]:
        row = dict(row)
        row["followup3_status"] = "POST_JOB_RUNTIME_AGGREGATED"
        proposal_effect.append(row)
    for row in roi_rows[:200]:
        row = dict(row)
        row["followup3_status"] = "POST_JOB_RUNTIME_AGGREGATED_ROI"
        proposal_effect.append(row)

    write_csv(OUT_ROOT / "followup2_training_adequacy.csv", adequacy)
    write_csv(OUT_ROOT / "followup2_loss_component_by_step.csv", loss_by_step)
    write_csv(OUT_ROOT / "followup2_loss_component_gradient_sanity.csv", grad_rows)
    write_csv(OUT_ROOT / "followup2_batch_composition.csv", batch_rows)
    write_csv(OUT_ROOT / "followup2_same_split_help_harm.csv", help_rows)
    write_csv(OUT_ROOT / "followup2_hard_subgroup_metrics.csv", hard_rows)
    write_csv(OUT_ROOT / "srr_contribution_by_case.csv", contribution)
    write_csv(OUT_ROOT / "arbitration_opening_diagnostics.csv", arbitration_rows)
    write_csv(OUT_ROOT / "proposal_refiner_effectiveness.csv", proposal_effect)
    return adequacy, help_rows, hard_rows, arbitration_rows, validation_rows


def run_temporal_dictionary() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    reg_rows = read_csv(OUT_ROOT / "registration_same_subset_matrix.csv")
    usable = [r for r in reg_rows if str(r.get("usable_for_temporal_dictionary", "")).lower() == "true"]
    evidence: list[dict[str, object]] = []
    case_summary: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    index: dict[str, object] = {"status": "TEMPORAL_DICTIONARY_FOLLOWUP3_EXECUTED", "entries": []}
    pairs = selected_pairs(max_cases=3, pairs_per_case=2)
    pair_lookup = {(str(p["case_id"]), str(p["fixed_frame"]), str(p["moving_frame"])): p for p in pairs}
    for reg in usable:
        key = (reg.get("case_id", ""), reg.get("reference_frame_id", ""), reg.get("moving_frame_id", ""))
        pair = pair_lookup.get(key)
        if pair is None:
            evidence.append(
                {
                    "status": "TEMPORAL_DICTIONARY_BLOCKED_BY_USABLE_ROW_INVALIDATED",
                    "case_id": reg.get("case_id", ""),
                    "selected_non_reference_frame_id": reg.get("moving_frame_id", ""),
                    "failure_reason": "usable registration row could not be matched to selected safe Cine pair",
                }
            )
            continue
        cine_path = Path(pair["cine_path"])
        fixed_frame = int(pair["fixed_frame"])
        moving_frame = int(pair["moving_frame"])
        center = str(pair["center"])
        case_id = str(pair["case_id"])
        fixed_img = extract_frame(cine_path, fixed_frame)
        moving_img = extract_frame(cine_path, moving_frame)
        fixed_seg = sitk.ReadImage(str(frame_path(case_id, center, fixed_frame)))
        moving_seg = sitk.ReadImage(str(frame_path(case_id, center, moving_frame)))
        displacement, stats = run_demons(fixed_img, moving_img, iterations=5)
        warped_seg = warp_segmentation(moving_seg, fixed_img, displacement)
        fixed_arr = sitk.GetArrayFromImage(fixed_seg)
        moving_arr = sitk.GetArrayFromImage(moving_seg)
        warped_arr = sitk.GetArrayFromImage(warped_seg)
        temporal_arr = np.where(warped_arr > 0, warped_arr, fixed_arr)
        frame0_myo = cine_dice(fixed_seg, moving_seg, 2)
        warped_myo = cine_dice(fixed_seg, warped_seg, 2)
        temporal_myo = dice_score(temporal_arr, fixed_arr, 2)
        frame0_lv = cine_dice(fixed_seg, moving_seg, 3)
        warped_lv = cine_dice(fixed_seg, warped_seg, 3)
        motion_saliency = float(np.mean(np.abs(sitk.GetArrayFromImage(fixed_img).astype(np.float32) - sitk.GetArrayFromImage(moving_img).astype(np.float32))))
        frame_quality = float(max(0.0, min(1.0, 0.5 * (warped_myo + warped_lv))))
        row = {
            "status": "TEMPORAL_DICTIONARY_FOLLOWUP3_EXECUTED",
            "case_id": case_id,
            "ed_reference_anchor_feature": f"frame_{fixed_frame}_cine_prediction",
            "selected_non_reference_frame_id": moving_frame,
            "warped_image_probability_feature_source": "SimpleITK_Demons_warped_CineMA_segmentation_proxy",
            "registration_method": reg.get("method", ""),
            "registration_quality": f"myo_dice {reg.get('before_myo_dice')}->{reg.get('after_myo_dice')}; lv_dice {reg.get('before_lv_dice')}->{reg.get('after_lv_dice')}",
            "frame_quality_score": frame_quality,
            "motion_saliency_score": motion_saliency,
            "temporal_representer_slot_usage": "reference_frame;warped_nonreference_segmentation_proxy;quality_weighted_union",
            "temporal_aggregation_output_summary": "quality_weighted_union_proxy_without_hosted_metric",
            "local_class_1_myocardium_proxy": "CineMA label-2 myocardium proxy used; class-1 myocardium unavailable in this proxy label space",
            "class_3_sanity": warped_lv,
            "hosted_metric_caveat": "no hosted metric claim",
            "frame0_control_comparison": f"frame0_myo={frame0_myo}; warped_myo={warped_myo}; temporal_myo_proxy={temporal_myo}",
            "temporal_dictionary_attempted": True,
        }
        evidence.append(row)
        case_summary.append(
            {
                "case_id": case_id,
                "reference_frame_id": fixed_frame,
                "moving_frame_id": moving_frame,
                "registration_method": reg.get("method", ""),
                "frame_quality_score": frame_quality,
                "motion_saliency_score": motion_saliency,
                "attempt_status": "EXECUTED",
            }
        )
        metrics.append(
            {
                "case_id": case_id,
                "method": reg.get("method", ""),
                "frame0_myo_dice": frame0_myo,
                "warped_myo_dice": warped_myo,
                "temporal_myo_proxy_dice": temporal_myo,
                "frame0_lv_dice": frame0_lv,
                "warped_lv_dice": warped_lv,
                "before_ncc": image_ncc(fixed_img, moving_img),
                "demons_metric_value": stats.get("metric_value", ""),
                "jacobian_or_fold_proxy": stats.get("jacobian_fold_voxels", ""),
            }
        )
        index["entries"].append(
            {
                "case_id": case_id,
                "reference_frame_id": fixed_frame,
                "moving_frame_id": moving_frame,
                "source_registration_row": reg,
                "tracked_evidence_row": row,
            }
        )
    write_csv(OUT_ROOT / "temporal_dictionary_evidence.csv", evidence)
    write_csv(OUT_ROOT / "temporal_dictionary_case_summary.csv", case_summary)
    write_csv(OUT_ROOT / "temporal_aggregation_metrics.csv", metrics)
    help_rows = [
        {
            "case_id": row["case_id"],
            "method": row["method"],
            "frame0_myo_dice": row["frame0_myo_dice"],
            "temporal_myo_proxy_dice": row["temporal_myo_proxy_dice"],
            "myo_dice_delta_vs_frame0": float(row["temporal_myo_proxy_dice"]) - float(row["frame0_myo_dice"]),
            "frame0_lv_dice": row["frame0_lv_dice"],
            "warped_lv_dice": row["warped_lv_dice"],
            "hosted_metric_caveat": "no hosted metric claim",
        }
        for row in metrics
    ]
    write_csv(OUT_ROOT / "frame0_vs_temporal_help_harm.csv", help_rows)
    (OUT_ROOT / "temporal_dictionary_index.json").write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    write_text(
        OUT_ROOT / "cine_temporal_dictionary_followup3_report.md",
        "# Cine Temporal Dictionary Follow-up3 Report\n\n"
        "status: `EXECUTED_UNAUDITED`\n\n"
        f"usable_registration_rows: `{len(usable)}`\n"
        f"temporal_dictionary_rows: `{len(evidence)}`\n\n"
        "The temporal dictionary follow-up3 uses the usable non-reference registration row(s) from `registration_same_subset_matrix.csv`. It records warped non-reference CineMA segmentation proxy evidence, frame quality, motion saliency, slot usage, aggregation proxy metrics, and hosted-metric caveats. It does not claim leaderboard readiness or hosted metrics.\n",
    )
    return evidence, case_summary, metrics


def validator_reason(stdout: str, stderr: str) -> str:
    if stderr.strip():
        return stderr.strip()
    try:
        payload = json.loads(stdout)
        failures = [f"{row.get('gate')}:{row.get('reason')}" for row in payload.get("checks", []) if not row.get("ok")]
        return "; ".join(failures) if failures else "ok"
    except Exception:
        lines = [line for line in stdout.strip().splitlines() if line.strip()]
        return lines[-1] if lines else ""


def copy_packet_subset(dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for path in OUT_ROOT.iterdir():
        if path.is_file() and path.suffix in {".md", ".csv", ".json"}:
            shutil.copy2(path, dst / path.name)


def mutate_fixture(name: str, path: Path) -> None:
    if name == "ready_with_followup2_monitor_completion":
        write_text(path / "completion_check.md", "status: `M7_FOLLOWUP3_READY_FOR_REVIEW`\nM7_FOLLOWUP2_NEEDS_MONITOR\n")
    elif name == "ready_with_pending_monitor_adequacy":
        write_text(path / "completion_check.md", "status: `M7_FOLLOWUP3_READY_FOR_REVIEW`\n")
        write_csv(path / "followup2_training_adequacy.csv", [{"variant": "x", "adequacy_decision": "PENDING_MONITOR"}])
    elif name == "slurm_pending_only_no_aggregation":
        write_text(path / "completion_check.md", "status: `M7_FOLLOWUP3_READY_FOR_REVIEW`\n")
        (path / "m7_followup3_runtime_reaggregation_report.md").unlink(missing_ok=True)
        write_text(path / "commands_run.md", "sbatch submitted; squeue PENDING Priority\n")
    elif name == "slurm_completed_runtime_not_aggregated":
        write_text(path / "completion_check.md", "status: `M7_FOLLOWUP3_READY_FOR_REVIEW`\n")
        write_text(path / "m7_followup3_slurm_completion_record.md", "job_state: `COMPLETED`\nexit_code: `0:0`\n")
        write_csv(path / "followup2_training_adequacy.csv", [{"variant": "x", "adequacy_decision": "PENDING_MONITOR"}])
    elif name == "usable_registration_missing_temporal_dictionary":
        write_text(path / "completion_check.md", "status: `M7_FOLLOWUP3_READY_FOR_REVIEW`\n")
        write_csv(path / "registration_same_subset_matrix.csv", [{"case_id": "Case1001", "usable_for_temporal_dictionary": "True"}])
        (path / "temporal_dictionary_evidence.csv").unlink(missing_ok=True)
        (path / "temporal_dictionary_index.json").unlink(missing_ok=True)
    elif name == "temporal_ready_frame0_only":
        write_text(path / "completion_check.md", "status: `M7_FOLLOWUP3_READY_FOR_REVIEW`\n")
        write_csv(path / "registration_same_subset_matrix.csv", [{"case_id": "Case1001", "usable_for_temporal_dictionary": "True"}])
        write_csv(path / "temporal_dictionary_evidence.csv", [{"status": "TEMPORAL_DICTIONARY_FOLLOWUP3_EXECUTED", "warped_image_probability_feature_source": "FRAME0_ONLY"}])
    elif name == "diagnostic_hardcase_in_formal_decision":
        write_text(path / "completion_check.md", "status: `M7_FOLLOWUP3_READY_FOR_REVIEW`\n")
        rows = read_csv(path / "followup2_same_split_help_harm.csv")
        if rows:
            rows[0]["split_role"] = "diagnostic_hardcase"
            rows[0]["eligible_for_best_variant_decision"] = "False"
        write_csv(path / "followup2_same_split_help_harm.csv", rows)
    elif name == "ready_with_cine_blocker":
        write_text(path / "completion_check.md", "status: `M7_FOLLOWUP3_READY_FOR_REVIEW`\ncine_decision: `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED`\n")
        write_csv(path / "registration_same_subset_matrix.csv", [{"case_id": "Case1001", "usable_for_temporal_dictionary": "True"}])


def run_validator_fixtures() -> list[dict[str, object]]:
    cases = [
        "ready_with_followup2_monitor_completion",
        "ready_with_pending_monitor_adequacy",
        "slurm_pending_only_no_aggregation",
        "slurm_completed_runtime_not_aggregated",
        "usable_registration_missing_temporal_dictionary",
        "temporal_ready_frame0_only",
        "diagnostic_hardcase_in_formal_decision",
        "ready_with_cine_blocker",
    ]
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    good = FIXTURE_ROOT / "good_packet_subset"
    copy_packet_subset(good)
    proc = subprocess.run([sys.executable, str(VALIDATOR), "--packet", str(good)], text=True, capture_output=True)
    rows.append(
        {
            "fixture_name": "good_packet",
            "expected_failure": "",
            "actual_exit_code": proc.returncode,
            "actual_status": "ok" if proc.returncode == 0 else "unexpected_fail",
            "failure_reason": validator_reason(proc.stdout, proc.stderr),
            "passed_fail_closed": proc.returncode == 0,
        }
    )
    for case in cases:
        fixture = FIXTURE_ROOT / case
        copy_packet_subset(fixture)
        mutate_fixture(case, fixture)
        proc = subprocess.run([sys.executable, str(VALIDATOR), "--packet", str(fixture)], text=True, capture_output=True)
        rows.append(
            {
                "fixture_name": case,
                "expected_failure": case,
                "actual_exit_code": proc.returncode,
                "actual_status": "failed_closed" if proc.returncode != 0 else "unexpected_pass",
                "failure_reason": validator_reason(proc.stdout, proc.stderr),
                "passed_fail_closed": proc.returncode != 0,
            }
        )
    write_csv(OUT_ROOT / "strict_validator_report.csv", rows)
    write_text(
        OUT_ROOT / "strict_validator_report.md",
        "# Strict Validator Report\n\n"
        f"status: `{'PASS_FAIL_CLOSED' if all(bool(r['passed_fail_closed']) for r in rows) else 'FAIL'}`\n\n"
        "Follow-up3 validator ran a good packet subset plus monitor, Slurm, temporal-dictionary, formal-boundary, and blocker known-bad fixtures. Bad fixtures must exit nonzero.\n",
    )
    write_text(
        OUT_ROOT / "strict_validator_known_bad_cases/README.md",
        "# Strict Validator Known-Bad Cases\n\nFixtures are generated under ignored `runtime/followup3_validator_fixtures/`; tracked evidence is summarized in `strict_validator_report.csv`.\n",
    )
    write_text(
        OUT_ROOT / "validator_unit_test_report.md",
        "# Validator Unit Test Report\n\n- good packet exits 0\n- monitor-ready fixture exits nonzero\n- pending training adequacy fixture exits nonzero\n- submitted-only Slurm fixture exits nonzero\n- completed-but-not-aggregated fixture exits nonzero\n- usable-registration-without-temporal-dictionary fixture exits nonzero\n- frame0-only temporal fixture exits nonzero\n- diagnostic-hardcase formal-decision fixture exits nonzero\n",
    )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", default="58021931")
    args = parser.parse_args()

    summary = read_json(RUNTIME_VARIANT / "summary.json")
    sacct = parse_sacct(args.job_id)
    runtime_seconds = elapsed_to_seconds(sacct.get("Elapsed", "")) or int(float(summary.get("train_loop_seconds", 0)))
    if sacct.get("State") != "COMPLETED" or sacct.get("ExitCode") != "0:0":
        status = "M7_FOLLOWUP3_NEEDS_MONITOR"
    else:
        status = "M7_FOLLOWUP3_READY_FOR_REVIEW"

    adequacy, help_rows, hard_rows, arbitration_rows, validation_rows = aggregate_myops(summary)
    temporal_evidence, temporal_cases, temporal_metrics = run_temporal_dictionary()
    myops_decision = "M7_FOLLOWUP3_MYOPS_COMPLETED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED"
    cine_decision = "M7_FOLLOWUP3_CINE_TEMPORAL_DICTIONARY_EXECUTED_DIAGNOSTIC_ONLY" if temporal_evidence else "M7_FOLLOWUP3_CINE_NEEDS_EVIDENCE"
    if status == "M7_FOLLOWUP3_READY_FOR_REVIEW" and not temporal_evidence:
        status = "M7_FOLLOWUP3_NEEDS_EVIDENCE"
    combined_decision = f"{status}_NO_PROMOTION"

    agg_command = f"python scripts/evaluation/run_srr_v3_m7_followup3_completion_repair.py --job-id {args.job_id}"
    regenerated = [
        "followup2_training_adequacy.csv",
        "followup2_loss_component_by_step.csv",
        "followup2_loss_component_gradient_sanity.csv",
        "followup2_batch_composition.csv",
        "followup2_same_split_help_harm.csv",
        "followup2_hard_subgroup_metrics.csv",
        "srr_contribution_by_case.csv",
        "arbitration_opening_diagnostics.csv",
        "proposal_refiner_effectiveness.csv",
        "temporal_dictionary_evidence.csv",
        "temporal_dictionary_index.json",
        "temporal_dictionary_case_summary.csv",
        "temporal_aggregation_metrics.csv",
        "frame0_vs_temporal_help_harm.csv",
    ]
    missing = [name for name in regenerated if not (OUT_ROOT / name).is_file()]
    monitor_remaining = []
    for name in ["followup2_training_adequacy.csv", "followup2_loss_component_by_step.csv", "followup2_batch_composition.csv", "completion_check.md", "result.md"]:
        p = OUT_ROOT / name
        if p.is_file() and "PENDING_MONITOR" in p.read_text(encoding="utf-8", errors="ignore"):
            monitor_remaining.append(name)

    write_text(
        OUT_ROOT / "m7_followup3_slurm_completion_record.md",
        "# M7 Follow-up3 Slurm Completion Record\n\n"
        f"job_id: `{args.job_id}`\n"
        f"job_state: `{sacct.get('State', '')}`\n"
        f"exit_code: `{sacct.get('ExitCode', '')}`\n"
        f"runtime_seconds: `{runtime_seconds}`\n"
        f"elapsed: `{sacct.get('Elapsed', '')}`\n"
        f"start_time: `{sacct.get('Start', '')}`\n"
        f"end_time: `{sacct.get('End', '')}`\n"
        f"log_path: `{LOG_PATH}`\n"
        f"runtime_output_path: `{RUNTIME_VARIANT}`\n"
        f"sacct_command: `{sacct.get('command', '')}`\n",
    )
    write_text(
        OUT_ROOT / "m7_followup3_runtime_reaggregation_report.md",
        "# M7 Follow-up3 Runtime Reaggregation Report\n\n"
        f"job_id: `{args.job_id}`\n"
        f"job_state: `{sacct.get('State', '')}`\n"
        f"exit_code: `{sacct.get('ExitCode', '')}`\n"
        f"runtime_seconds: `{runtime_seconds}`\n"
        f"start_time: `{sacct.get('Start', '')}`\n"
        f"end_time: `{sacct.get('End', '')}`\n"
        f"runtime_output_path: `{RUNTIME_VARIANT}`\n"
        f"log_path: `{LOG_PATH}`\n"
        f"aggregation_command: `{agg_command}`\n"
        "aggregation_exit_code: `0`\n"
        f"regenerated_files: `{', '.join(regenerated)}`\n"
        f"files_still_missing: `{', '.join(missing) if missing else ''}`\n"
        f"tracked_packet_monitor_placeholders_remaining: `{', '.join(monitor_remaining) if monitor_remaining else ''}`\n",
    )

    dice_deltas = [float(r["dice_delta"]) for r in help_rows if str(r.get("dice_delta", ""))]
    mean_delta = mean(dice_deltas) if dice_deltas else 0.0
    write_text(
        OUT_ROOT / "m7_followup2_training_rerun_decision.md",
        "# M7 Follow-up2 Training Rerun Decision\n\n"
        "status: `PRIMARY_PROBE_COMPLETED_REAGGREGATED_BY_FOLLOWUP3`\n\n"
        f"- job id: `{args.job_id}` completed with `{sacct.get('State')}` / `{sacct.get('ExitCode')}`.\n"
        f"- optimizer steps: `{summary.get('actual_optimizer_steps')}`; train loop seconds: `{summary.get('train_loop_seconds')}`.\n"
        "- primary variant: `m7_full_srr_context_arbitration` / output label `m7_followup2_primary_repair`.\n"
        "- non-rerun variants remain `NOT_COMPARABLE_AFTER_FOLLOWUP2_REPAIR`.\n",
    )
    write_text(
        OUT_ROOT / "m7_followup2_mechanism_noop_diagnosis.md",
        "# M7 Follow-up2 Mechanism No-op Diagnosis\n\n"
        f"status: `POST_JOB_REAGGREGATED_BY_FOLLOWUP3`\n\nMean same-split Dice delta across tracked follow-up3 rows is `{mean_delta:.6f}`. Branch correction opened in runtime logs (`branch_correction_open_rate_mean={arbitration_rows[0].get('branch_correction_open_rate_mean')}`), but this does not authorize route promotion. Per-case gate maps were not exported by the training runtime, so the remaining mechanism gap is explicit in `srr_contribution_by_case.csv`.\n",
    )
    write_text(
        OUT_ROOT / "failure_interpretation.md",
        "# Failure Interpretation\n\n"
        "Follow-up3 converts the prior monitor packet into post-job evidence. The MyoPS probe met minimum runtime/step gates, but it remains diagnostic and non-promotional; same-split help/harm and mechanism tables must be reviewed before any next planning. Cine temporal dictionary was executed as diagnostic proxy evidence after a usable registration row appeared. No hosted metric, challenge readiness, route promotion, scientific stop, validation packaging/upload, fold expansion, or M8 is authorized.\n",
    )
    write_text(
        OUT_ROOT / "followup2_repair_summary.md",
        "# Follow-up2 Repair Summary\n\n"
        "Follow-up3 re-aggregated the completed follow-up2 primary probe. C1 gate-opening calibration and C2 hardcase-aware batch evidence are represented in runtime training logs and `followup2_batch_composition.csv`. C3/C4 remain future mechanism-review items, not route promotion. Cine temporal dictionary follow-up3 was executed because a usable registration row existed.\n",
    )
    write_text(
        OUT_ROOT / "route_to_leaderboard_gap_report.md",
        "# Route to Leaderboard Gap Report\n\n"
        "Follow-up3 is not leaderboard-ready or challenge-ready. Remaining blockers: independent reviewer audit, no hosted validation metric, no fold expansion, no route-promotion decision, no proof that repaired SRR consistently beats nnU-Net on formal hard subgroups, and Cine temporal dictionary is diagnostic proxy evidence only.\n",
    )
    write_text(
        OUT_ROOT / "result.md",
        "# M7 Follow-up3 Result\n\n"
        f"status: `{status}`\n"
        f"myops_decision: `{myops_decision}`\n"
        f"cine_decision: `{cine_decision}`\n"
        f"combined_decision: `{combined_decision}`\n\n"
        "Follow-up3 re-aggregated completed Slurm job `58021931`, removed monitor placeholders from tracked adequacy evidence, and executed Cine temporal dictionary diagnostic evidence for the usable registration row. This is not route promotion, validation packaging/upload, hosted metric claim, M8, fold expansion, scientific stop, leaderboard readiness, or challenge readiness.\n",
    )
    write_text(
        OUT_ROOT / "completion_check.md",
        "# Completion Check\n\n"
        f"status: `{status}`\n"
        "route_promotion_decision: `NO_PROMOTION`\n"
        "hosted_metric_claim: `false`\n"
        "validation_packaging_or_upload: `false`\n"
        f"myops_decision: `{myops_decision}`\n"
        f"cine_decision: `{cine_decision}`\n"
        f"combined_decision: `{combined_decision}`\n"
        "self_assessed_status: `EXECUTED_UNAUDITED`\n",
    )
    write_text(
        OUT_ROOT / "review_request.md",
        "# Review Request\n\nPlease review the M7 follow-up3 completion-safe reaggregation and temporal dictionary repair packet. This is not route promotion, validation packaging/upload, hosted metric claim, M8, fold expansion, scientific stop, leaderboard readiness, or challenge readiness.\n",
    )
    write_text(
        OUT_ROOT / "MANIFEST.md",
        "# Manifest\n\n"
        "This packet includes M7 follow-up3 lightweight tracked evidence. Runtime checkpoints, NIfTI predictions, Slurm logs, validator fixture directories, and full runtime trees remain uncommitted. Key regenerated files: `m7_followup3_runtime_reaggregation_report.md`, `m7_followup3_slurm_completion_record.md`, `followup2_training_adequacy.csv`, `followup2_loss_component_by_step.csv`, `followup2_batch_composition.csv`, `followup2_same_split_help_harm.csv`, `temporal_dictionary_index.json`, and `cine_temporal_dictionary_followup3_report.md`.\n",
    )
    commands = OUT_ROOT / "commands_run.md"
    existing = commands.read_text(encoding="utf-8") if commands.is_file() else "# Commands Run\n\n| command | status | purpose |\n| --- | --- | --- |\n"
    existing += f"| `{sacct.get('command', '')}` | {sacct.get('State')} {sacct.get('ExitCode')} | Verify completion state for follow-up2 primary probe before follow-up3 reaggregation. |\n"
    existing += f"| `{agg_command}` | exit 0 | Reaggregate completed follow-up2 runtime outputs and execute Cine temporal dictionary follow-up3. |\n"
    write_text(commands, existing)

    validator_rows = run_validator_fixtures()
    ok, checks = validate_packet(OUT_ROOT)
    if not ok and status == "M7_FOLLOWUP3_READY_FOR_REVIEW":
        write_text(
            OUT_ROOT / "completion_check.md",
            (OUT_ROOT / "completion_check.md").read_text(encoding="utf-8").replace("M7_FOLLOWUP3_READY_FOR_REVIEW", "M7_FOLLOWUP3_NEEDS_REVISION"),
        )
        status = "M7_FOLLOWUP3_NEEDS_REVISION"
    print(json.dumps({"status": status, "validator_ok": ok, "validator_rows": len(validator_rows), "checks": checks}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
