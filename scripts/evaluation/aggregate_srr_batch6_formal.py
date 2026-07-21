#!/usr/bin/env python3
"""Aggregate Batch6 formal calibration evidence and continuation gate."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class  # noqa: E402
from scripts.srr_production.evaluate_myops_fair import component_stats  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402

LABELS = {"myops_edema": 4, "myops_scar": 5}
GROUPS = ("all_cases", "gt_positive_only", "CenterB", "CenterC", "LGE-only", "t2_present")


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def split_val_cases() -> list[str]:
    payload = load_json(REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json")
    return list(payload["folds"][0]["val"])


def read_label(path: Path, reference: sitk.Image | None = None) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    if reference is not None:
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(reference)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        img = resampler.Execute(img)
    return img, sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def metric_rows_for_step(cfg: dict[str, Any], variant_dir: Path, local_step: int, total_step: int) -> list[dict[str, Any]]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    pred_dir = variant_dir / "predictions/fold_0" / f"step_{local_step}" / "argmax"
    gt_dir = repo_path(cfg["paths"]["gt_dir"])
    anchor_dir = repo_path(cfg["paths"]["anchor_fold0_pred_dir"])
    rows: list[dict[str, Any]] = []
    for case_id in split_val_cases():
        meta = metadata[case_id]
        gt_img, gt = read_label(gt_dir / f"{case_id}.nii.gz")
        _anchor_img, anchor = read_label(anchor_dir / f"{case_id}.nii.gz", gt_img)
        _pred_img, pred = read_label(pred_dir / f"{case_id}.nii.gz", gt_img)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        myo = (gt >= 1) & (gt <= 5)
        for metric_name, cls in LABELS.items():
            gt_positive = bool(np.any(gt == cls))
            anchor_dice = dice_per_class(anchor, gt, cls, skip_if_gt_empty=False)
            pred_dice = dice_per_class(pred, gt, cls, skip_if_gt_empty=False)
            anchor_hd95 = hd95_class(anchor, gt, cls, spacing)
            pred_hd95 = hd95_class(pred, gt, cls, spacing)
            anchor_comp = component_stats(anchor, gt, myo, cls, spacing)
            pred_comp = component_stats(pred, gt, myo, cls, spacing)
            rows.append(
                {
                    "stage": f"formal_{total_step}",
                    "local_step": local_step,
                    "total_step": total_step,
                    "case_id": case_id,
                    "center": meta.center,
                    "modality_group": meta.modality_group,
                    "t2_present": bool(meta.t2_present),
                    "pathology": metric_name,
                    "class_id": cls,
                    "gt_positive": gt_positive,
                    "anchor_dice": anchor_dice,
                    "srr_dice": pred_dice,
                    "dice_delta_vs_anchor": None if anchor_dice is None or pred_dice is None else float(pred_dice - anchor_dice),
                    "anchor_hd95": anchor_hd95,
                    "srr_hd95": pred_hd95,
                    "hd95_delta_vs_anchor": None if anchor_hd95 is None or pred_hd95 is None else float(pred_hd95 - anchor_hd95),
                    "anchor_component_count": anchor_comp["component_count"],
                    "srr_component_count": pred_comp["component_count"],
                    "component_delta": float(pred_comp["component_count"] - anchor_comp["component_count"]),
                    "anchor_remote_fp_volume_mm3": anchor_comp["remote_fp_volume_mm3"],
                    "srr_remote_fp_volume_mm3": pred_comp["remote_fp_volume_mm3"],
                    "remote_fp_delta_mm3": float(pred_comp["remote_fp_volume_mm3"] - anchor_comp["remote_fp_volume_mm3"]),
                    "changed_voxels_vs_anchor": int(np.count_nonzero((pred == cls) != (anchor == cls))),
                    "prediction_path": rel(pred_dir / f"{case_id}.nii.gz"),
                }
            )
    return rows


def in_group(row: dict[str, Any], group: str) -> bool:
    if group == "all_cases":
        return True
    if group == "gt_positive_only":
        return bool(row["gt_positive"])
    if group == "CenterB":
        return row["center"] == "CenterB"
    if group == "CenterC":
        return row["center"] == "CenterC"
    if group == "LGE-only":
        return row["modality_group"] == "LGE-only"
    if group == "t2_present":
        return bool(row["t2_present"])
    return False


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    steps = sorted({int(row["total_step"]) for row in rows})
    for step in steps:
        step_rows = [row for row in rows if int(row["total_step"]) == step]
        for pathology in LABELS:
            path_rows = [row for row in step_rows if row["pathology"] == pathology]
            for group in GROUPS:
                selected = [row for row in path_rows if in_group(row, group)]
                dice_rows = [row for row in selected if row["srr_dice"] is not None and row["anchor_dice"] is not None]
                hd_rows = [row for row in selected if row["srr_hd95"] is not None and row["anchor_hd95"] is not None]
                out.append(
                    {
                        "total_step": step,
                        "pathology": pathology,
                        "group": group,
                        "case_count": len(selected),
                        "metric_case_count": len(dice_rows),
                        "anchor_dice_mean": mean([float(row["anchor_dice"]) for row in dice_rows]),
                        "srr_dice_mean": mean([float(row["srr_dice"]) for row in dice_rows]),
                        "dice_delta_mean": mean([float(row["dice_delta_vs_anchor"]) for row in dice_rows]),
                        "anchor_hd95_mean": mean([float(row["anchor_hd95"]) for row in hd_rows]),
                        "srr_hd95_mean": mean([float(row["srr_hd95"]) for row in hd_rows]),
                        "hd95_delta_mean": mean([float(row["hd95_delta_vs_anchor"]) for row in hd_rows]),
                        "anchor_remote_fp_volume_mm3_mean": mean([float(row["anchor_remote_fp_volume_mm3"]) for row in selected]),
                        "srr_remote_fp_volume_mm3_mean": mean([float(row["srr_remote_fp_volume_mm3"]) for row in selected]),
                        "remote_fp_delta_mm3_mean": mean([float(row["remote_fp_delta_mm3"]) for row in selected]),
                        "changed_voxels_vs_anchor_mean": mean([float(row["changed_voxels_vs_anchor"]) for row in selected]),
                    }
                )
    return out


def help_harm_rows(case_rows: list[dict[str, Any]], selected_total_step: int) -> list[dict[str, Any]]:
    rows = []
    for row in case_rows:
        if int(row["total_step"]) != selected_total_step or not row["gt_positive"] or row["dice_delta_vs_anchor"] is None:
            continue
        delta = float(row["dice_delta_vs_anchor"])
        rows.append({**row, "help_harm": "help" if delta > 0 else ("harm" if delta < 0 else "neutral")})
    return rows


def no_t2_exact_zero(variant_dir: Path, local_step: int) -> bool:
    path = variant_dir / f"prediction_sanity_step_{local_step}.csv"
    if not path.is_file():
        return False
    rows = read_csv(path)
    no_t2_rows = [row for row in rows if row.get("decode_mode") == "argmax" and row.get("t2_present") == "False"]
    return bool(no_t2_rows) and all(int(float(row.get("no_t2_edema_voxels", "1") or 1)) == 0 for row in no_t2_rows)


def gradient_gate(variant_dir: Path) -> dict[str, Any]:
    path = variant_dir / "loss_component_gradient_sanity.csv"
    rows = read_csv(path) if path.is_file() else []
    wanted = {
        "loss_final_scar_pathology",
        "loss_final_scar_anchor_error_pathology",
        "loss_final_edema_t2_present_pathology",
        "loss_final_edema_anchor_error_pathology",
        "loss_production_gate_repair_preserve",
    }
    hits = [row for row in rows if row.get("component") in wanted]
    nonzero = [row for row in hits if float(row.get("grad_l2_norm") or 0.0) > 0.0]
    return {
        "gradient_rows": len(rows),
        "required_rows": len(hits),
        "nonzero_required_rows": len(nonzero),
        "pass": len(nonzero) >= 3,
    }


def finite_training_losses(variant_dir: Path) -> bool:
    rows = read_csv(variant_dir / "training_log.csv")
    numeric_keys = ["loss", "loss_final_scar_pathology", "loss_final_edema_t2_present_pathology", "loss_production_gate_repair_preserve"]
    for row in rows:
        for key in numeric_keys:
            if key in row and row[key] != "":
                value = float(row[key])
                if not math.isfinite(value):
                    return False
    return bool(rows)


def select_step_and_gate(summary_rows: list[dict[str, Any]], case_rows: list[dict[str, Any]], variant_dir: Path, local_step: int, total_step: int, cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    gate_cfg = cfg["formal_training"]["stage_300"]["continuation_gate"]
    by_key = {(int(r["total_step"]), r["pathology"], r["group"]): r for r in summary_rows}
    scar = by_key[(total_step, "myops_scar", "gt_positive_only")]
    edema = by_key[(total_step, "myops_edema", "gt_positive_only")]
    selected_positive = [scar, edema]
    mean_delta = mean([float(r["dice_delta_mean"]) for r in selected_positive if r["dice_delta_mean"] is not None])
    min_delta = min(float(r["dice_delta_mean"]) for r in selected_positive if r["dice_delta_mean"] is not None)
    help_rows = help_harm_rows(case_rows, total_step)
    help_count = sum(1 for r in help_rows if r["help_harm"] == "help")
    harm_count = sum(1 for r in help_rows if r["help_harm"] == "harm")
    def rel_worse(row: dict[str, Any], pred_key: str, anchor_key: str) -> float:
        pred = float(row[pred_key] or 0.0)
        anchor = float(row[anchor_key] or 0.0)
        return (pred - anchor) / max(abs(anchor), 1e-6)
    hd95_worse = max(rel_worse(r, "srr_hd95_mean", "anchor_hd95_mean") for r in selected_positive)
    remote_worse = max(rel_worse(r, "srr_remote_fp_volume_mm3_mean", "anchor_remote_fp_volume_mm3_mean") for r in selected_positive)
    grad = gradient_gate(variant_dir)
    gate = {
        "minimum_mean_scar_edema_positive_dice_delta": gate_cfg["minimum_mean_scar_edema_positive_dice_delta"],
        "mean_scar_edema_positive_dice_delta": mean_delta,
        "minimum_each_pathology_dice_delta": gate_cfg["minimum_each_pathology_dice_delta"],
        "minimum_observed_pathology_dice_delta": min_delta,
        "help_count": help_count,
        "harm_count": harm_count,
        "help_not_less_than_harm": help_count >= harm_count,
        "maximum_each_pathology_hd95_relative_worsening": gate_cfg["maximum_each_pathology_hd95_relative_worsening"],
        "observed_hd95_relative_worsening_max": hd95_worse,
        "maximum_each_pathology_remote_fp_relative_worsening": gate_cfg["maximum_each_pathology_remote_fp_relative_worsening"],
        "observed_remote_fp_relative_worsening_max": remote_worse,
        "no_t2_edema_exact_zero": no_t2_exact_zero(variant_dir, local_step),
        "finite_losses": finite_training_losses(variant_dir),
        "gradient_gate": grad,
    }
    checks = {
        "mean_delta": mean_delta is not None and mean_delta >= float(gate_cfg["minimum_mean_scar_edema_positive_dice_delta"]),
        "each_delta": min_delta >= float(gate_cfg["minimum_each_pathology_dice_delta"]),
        "help_harm": help_count >= harm_count,
        "hd95": hd95_worse <= float(gate_cfg["maximum_each_pathology_hd95_relative_worsening"]),
        "remote_fp": remote_worse <= float(gate_cfg["maximum_each_pathology_remote_fp_relative_worsening"]),
        "no_t2": bool(gate["no_t2_edema_exact_zero"]),
        "finite_and_grad": bool(gate["finite_losses"]) and bool(grad["pass"]),
    }
    gate["checks"] = checks
    gate["decision"] = "PASS" if all(checks.values()) else "FAIL"
    selection_rows = []
    for row in summary_rows:
        if row["group"] == "gt_positive_only" and row["pathology"] in LABELS:
            selection_rows.append({**row, "selected_for_stage300_gate": int(row["total_step"]) == total_step})
    return selection_rows, gate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch6.yaml")
    parser.add_argument("--result-root", default="results/20260721_srr_batch6_final_objective_alignment")
    parser.add_argument("--stage", choices=("300",), default="300")
    parser.add_argument("--attempt-label", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--job-state", required=True)
    parser.add_argument("--exit-code", required=True)
    parser.add_argument("--elapsed", required=True)
    parser.add_argument("--node", default="")
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    result_root = repo_path(args.result_root)
    variant_dir = result_root / "runtime/attempts" / args.attempt_label / "variants" / args.attempt_label
    summary = load_json(variant_dir / "summary.json")
    if int(summary.get("actual_optimizer_steps", -1)) != 300:
        raise SystemExit(f"formal 300 actual_optimizer_steps mismatch: {summary.get('actual_optimizer_steps')}")
    local_steps = [100, 200, 300]
    case_rows: list[dict[str, Any]] = []
    for step in local_steps:
        case_rows.extend(metric_rows_for_step(cfg, variant_dir, step, step))
    summary_rows = summarize(case_rows)
    selection_rows, gate = select_step_and_gate(summary_rows, case_rows, variant_dir, 300, 300, cfg)
    selected_ckpt = variant_dir / "checkpoints/fold_0/propref_config/checkpoint_validation_step_300.pt"
    write_csv(result_root / "casewise_metrics.csv", case_rows)
    write_csv(result_root / "subgroup_metrics.csv", summary_rows)
    write_csv(result_root / "checkpoint_selection.csv", selection_rows)
    write_csv(result_root / "help_harm.csv", help_harm_rows(case_rows, 300))
    adequacy = {
        "schema_version": 2,
        "stage": "formal_300",
        "status": "FORMAL_300_COMPLETE_GATE_PASS" if gate["decision"] == "PASS" else "FORMAL_300_COMPLETE_GATE_FAIL_STOP_AT_300",
        "experiment_adequacy_decision": "FORMAL_300_CONTINUATION_GATE_PASS" if gate["decision"] == "PASS" else "MECHANISM_REPAIRED_BUT_NOT_USEFUL_STOP_AT_300",
        "formal_training_submitted": True,
        "formal_300_step_status": "COMPLETED",
        "formal_900_step_status": "AUTHORIZED_NOT_SUBMITTED" if gate["decision"] == "PASS" else "SKIPPED_STEP300_GATE_FAILED",
        "continuation_gate_decision": gate["decision"],
        "continuation_gate": gate,
        "job_id": args.job_id,
        "job_state": args.job_state,
        "job_exit_code": args.exit_code,
        "elapsed": args.elapsed,
        "node": args.node,
        "attempt_label": args.attempt_label,
        "actual_optimizer_steps": summary.get("actual_optimizer_steps"),
        "optimizer_steps": summary.get("optimizer_steps"),
        "train_cases": summary.get("train_cases"),
        "val_cases": summary.get("val_cases"),
        "eval_cases": summary.get("eval_cases"),
        "validation_event_count": summary.get("validation_event_count"),
        "full_volume_eval_steps": local_steps,
        "selected_checkpoint": "step_300",
        "selected_checkpoint_path": rel(selected_ckpt),
        "selected_checkpoint_sha256": sha256_file(selected_ckpt),
        "warm_start_checkpoint": summary.get("warm_start_checkpoint"),
        "warm_start_checkpoint_sha256": summary.get("warm_start_checkpoint_sha256"),
        "batch6_trainable_contract": summary.get("batch6_trainable_contract"),
        "production_gate_migration": summary.get("production_gate_migration"),
        "optimizer_steps_before_formal": 0,
        "fixed_overfit_formal_training_credit": 0,
    }
    write_json(result_root / "training_adequacy.json", adequacy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
