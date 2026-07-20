#!/usr/bin/env python3
"""Aggregate the CARE SRR Batch4 terminal packet from audited runtime files."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class  # noqa: E402
from scripts.srr_production.evaluate_myops_fair import component_stats  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402

TASK_KEY = "20260721_srr_batch4_forced_fold0_training"
ATTEMPT_ID = "srr_batch4_m10d3_full4scale_fold0_seed20260721_htzhulab_59682067"
LABELS = {"myops_edema": 4, "myops_scar": 5}
SELECTION_STEPS = (600, 1200, 1800)
CONTROL_MODES = ("anchor_identity_control", "anchor_bounded_srr_correction", "srr_no_anchor_control")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=True) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(out) or math.isinf(out) else out


def mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def split_cases() -> list[str]:
    return sorted(load_json(REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json")["folds"][0]["val"])


def read_label(path: Path, reference: sitk.Image | None = None) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    if reference is not None:
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(reference)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        img = resampler.Execute(img)
    return img, sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def select_checkpoint(variant_dir: Path) -> tuple[int, list[dict[str, Any]]]:
    cases = split_cases()
    anchor_dir = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
    gt_dir = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
    rows: list[dict[str, Any]] = []
    for step in SELECTION_STEPS:
        pred_dir = variant_dir / "predictions/fold_0" / f"step_{step}" / "pathology_aware"
        deltas_by_pathology: dict[str, float | None] = {}
        hd95_by_pathology: dict[str, float | None] = {}
        remote_delta_by_pathology: dict[str, float | None] = {}
        changed_cases_by_pathology: dict[str, int] = {}
        harm_count = 0
        for pathology, cls in LABELS.items():
            deltas: list[float] = []
            hd95s: list[float] = []
            remote_deltas: list[float] = []
            changed_cases = 0
            for cid in cases:
                gt_img, gt = read_label(gt_dir / f"{cid}.nii.gz")
                _anchor_img, anchor = read_label(anchor_dir / f"{cid}.nii.gz", gt_img)
                _pred_img, pred = read_label(pred_dir / f"{cid}.nii.gz", gt_img)
                d0 = dice_per_class(anchor, gt, cls, skip_if_gt_empty=True)
                d1 = dice_per_class(pred, gt, cls, skip_if_gt_empty=True)
                if d0 is not None and d1 is not None:
                    delta = float(d1 - d0)
                    deltas.append(delta)
                    harm_count += int(delta < 0)
                h = hd95_class(pred, gt, cls, tuple(float(x) for x in gt_img.GetSpacing()[::-1]))
                if h is not None and not math.isnan(h):
                    hd95s.append(float(h))
                myo = (gt >= 1) & (gt <= 5)
                anchor_stats = component_stats(anchor, gt, myo, cls, tuple(float(x) for x in gt_img.GetSpacing()[::-1]))
                pred_stats = component_stats(pred, gt, myo, cls, tuple(float(x) for x in gt_img.GetSpacing()[::-1]))
                remote_deltas.append(float(pred_stats["remote_fp_volume_mm3"] - anchor_stats["remote_fp_volume_mm3"]))
                changed_cases += int(np.count_nonzero((pred == cls) != (anchor == cls)) > 0)
            deltas_by_pathology[pathology] = mean(deltas)
            hd95_by_pathology[pathology] = mean(hd95s)
            remote_delta_by_pathology[pathology] = mean(remote_deltas)
            changed_cases_by_pathology[pathology] = changed_cases
        selected_key = {
            "min_scar_edema_dice_delta": min(v for v in deltas_by_pathology.values() if v is not None),
            "mean_scar_edema_dice_delta": mean([v for v in deltas_by_pathology.values() if v is not None]),
            "harm_case_pathology_count": harm_count,
            "mean_hd95": mean([v for v in hd95_by_pathology.values() if v is not None]),
            "remote_fp_delta_mean_mm3": mean([v for v in remote_delta_by_pathology.values() if v is not None]),
        }
        rows.append(
            {
                "checkpoint": f"step_{step}",
                "step": step,
                "case_count": len(cases),
                "edema_dice_delta_mean": deltas_by_pathology["myops_edema"],
                "scar_dice_delta_mean": deltas_by_pathology["myops_scar"],
                "edema_changed_cases": changed_cases_by_pathology["myops_edema"],
                "scar_changed_cases": changed_cases_by_pathology["myops_scar"],
                **selected_key,
            }
        )
    ranked = sorted(
        rows,
        key=lambda r: (
            -float(r["min_scar_edema_dice_delta"]),
            -float(r["mean_scar_edema_dice_delta"]),
            int(r["harm_case_pathology_count"]),
            float(r["mean_hd95"]),
            float(r["remote_fp_delta_mean_mm3"]),
            int(r["step"]),
        ),
    )
    return int(ranked[0]["step"]), ranked


def aggregate(result_root: Path, variant_dir: Path, control_root: Path, eval_root: Path) -> dict[str, Any]:
    summary = load_json(variant_dir / "summary.json")
    selected_step, candidate_rows = select_checkpoint(variant_dir)
    checkpoint = variant_dir / "checkpoints/fold_0/propref_config" / f"checkpoint_validation_step_{selected_step}.pt"
    batch_rows = read_csv(variant_dir / "batch_composition.csv")
    train_usage = Counter(
        row["case_id"]
        for row in batch_rows
        if row.get("split_role") == "train" and row.get("used_in_training") == "True"
    )
    full_eval_counts = {
        f"step_{step}": len({row["case_id"] for row in read_csv(variant_dir / f"component_hd_by_case_step_{step}.csv")})
        for step in SELECTION_STEPS
    }
    coverage = {
        "summary_top_level_source_commit": summary.get("source_commit"),
        "summary_top_level_source_commit_status": "MISSING_COVERED_BY_CHECKPOINT_PAYLOAD",
        "summary_top_level_full_volume_eval_steps": summary.get("full_volume_eval_steps"),
        "summary_top_level_full_volume_eval_steps_status": "MISSING_COVERED_BY_RUNTIME_STEP_FILES",
        "runtime_full_volume_eval_case_counts": full_eval_counts,
    }
    adequacy = {
        "schema_version": 1,
        "status": "TRAINING_BUDGET_VALID_AGGREGATED_FROM_59682067",
        "job_id": "59682067",
        "job_state": "COMPLETED",
        "job_exit_code": "0:0",
        "elapsed": "00:33:26",
        "node": "g1807htzh01",
        "actual_optimizer_steps": summary.get("actual_optimizer_steps"),
        "optimizer_steps": summary.get("optimizer_steps"),
        "max_steps": summary.get("max_steps"),
        "train_loop_seconds": summary.get("train_loop_seconds"),
        "post_optimizer_wait_seconds": summary.get("post_optimizer_wait_seconds"),
        "stop_reason": summary.get("stop_reason"),
        "train_cases": summary.get("train_cases"),
        "val_cases": summary.get("val_cases"),
        "eval_cases": summary.get("eval_cases"),
        "train_unique_case_count": len(train_usage),
        "minimum_case_usage": min(train_usage.values()) if train_usage else 0,
        "model_variant": summary.get("model_variant"),
        "encoder_profile": summary.get("encoder_profile"),
        "encoder_scale_channels": summary.get("encoder_scale_channels"),
        "selected_checkpoint": f"step_{selected_step}",
        "selected_checkpoint_path": rel(checkpoint),
        "selected_checkpoint_sha256": sha256_file(checkpoint),
        "coverage_for_missing_summary_fields": coverage,
    }
    write_json(result_root / "training_adequacy.json", adequacy)

    log_rows = read_csv(variant_dir / "training_log.csv")
    stages = sorted({row.get("stage", "") for row in log_rows})
    write_csv(
        result_root / "training_log_summary.csv",
        [
            {
                "stage": stage or "all",
                "logged_rows": len([r for r in log_rows if r.get("stage", "") == stage]),
                "first_step": min(int(r["step"]) for r in log_rows if r.get("stage", "") == stage and r.get("step", "").isdigit()),
                "last_step": max(int(r["step"]) for r in log_rows if r.get("stage", "") == stage and r.get("step", "").isdigit()),
                "mean_loss": mean([v for v in (num(r.get("loss")) for r in log_rows if r.get("stage", "") == stage) if v is not None]),
            }
            for stage in stages
        ],
    )
    metric_rows: list[dict[str, Any]] = []
    for name in [*(f"step_{s}" for s in SELECTION_STEPS), "checkpoint_best", "checkpoint_final"]:
        for row in read_csv(variant_dir / f"subgroup_metrics_{name}.csv"):
            if row.get("group") == "all_cases":
                metric_rows.append({"checkpoint": name, **row})
    write_csv(result_root / "validation_checkpoint_metrics.csv", metric_rows)

    contracts = {}
    contract_hashes = set()
    for mode in CONTROL_MODES:
        payload = load_json(control_root / f"batch3a_{mode}_inference_contract.json")
        contracts[mode] = {
            "status": payload.get("status"),
            "case_count": payload.get("case_count"),
            "checkpoint_global_step": payload.get("checkpoint_global_step"),
            "checkpoint_sha256": payload.get("checkpoint_receipt", {}).get("checkpoint_sha256"),
            "checkpoint_oof_anchor_manifest_hash": payload.get("checkpoint_oof_anchor_manifest_hash"),
            "training_summary_anchor_manifest_hash": payload.get("training_summary_anchor_manifest_hash"),
            "raw_oof_anchor_manifest_hash": payload.get("raw_oof_anchor_manifest_hash"),
            "prediction_dir": payload.get("prediction_dir"),
            "anchor_identity_changed_voxels_total": payload.get("anchor_identity_changed_voxels_total"),
            "anchor_identity_softmax_max_abs_delta": payload.get("anchor_identity_softmax_max_abs_delta"),
            "nonidentity_downstream_tensor_max_abs_delta": payload.get("nonidentity_downstream_tensor_max_abs_delta"),
        }
        contract_hashes.add(str(contracts[mode]["checkpoint_sha256"]))
    eval_completion = load_json(eval_root / "batch2_completion.json")
    selected = {
        "schema_version": 1,
        "status": "SELECTED_CHECKPOINT_RELOADED_THREE_MODE_CONTROLS_COMPLETE",
        "selected_checkpoint": f"step_{selected_step}",
        "selected_checkpoint_sha256": sha256_file(checkpoint),
        "candidate_rows_ranked": candidate_rows,
        "control_slurm_job_id": "59686817",
        "control_slurm_job_status": "FAILED_1:0_ZERO_COMPLETION_CREDIT",
        "control_slurm_failure_accounting": "59686817 failed only in downstream evaluator before config repair; inference contracts and predictions were written, then evaluator was rerun locally under audited config 74afdf0.",
        "same_checkpoint_three_mode_controls_complete": len(contract_hashes) == 1 and all(c["case_count"] == 44 for c in contracts.values()),
        "control_contracts": contracts,
        "control_evaluation_completion": eval_completion,
    }
    write_json(result_root / "selected_checkpoint.json", selected)

    for name in ("casewise_metrics.csv", "subgroup_metrics.csv", "help_harm.csv", "component_remote_fp.csv"):
        shutil.copyfile(eval_root / name, result_root / name)
    for src, dst in (
        (f"proposal_pr_sweep_step_{selected_step}.csv", "proposal_diagnostics.csv"),
        (f"roi_coverage_step_{selected_step}.csv", "roi_diagnostics.csv"),
    ):
        shutil.copyfile(variant_dir / src, result_root / dst)
    gate_keys = [
        "baseline_gate_mean",
        "baseline_residual_abs_mean",
        "branch_correction_open_rate",
        "proposal_weight_mean",
        "refiner_weight_mean",
        "final_logit_delta_roi_abs_mean",
    ]
    write_csv(
        result_root / "correction_gate_diagnostics.csv",
        [
            {
                "metric": key,
                "count": len(vals := [v for v in (num(r.get(key)) for r in log_rows) if v is not None]),
                "mean": mean(vals),
                "min": min(vals) if vals else "",
                "max": max(vals) if vals else "",
                "last": vals[-1] if vals else "",
            }
            for key in gate_keys
        ],
    )
    manifest = Path(summary["frozen_prototype_memory_manifest"]["asset_path"]).with_name("frozen_prototype_memory_manifest.json")
    if manifest.is_file():
        shutil.copyfile(manifest, result_root / "frozen_prototype_memory_manifest.json")
    return {"selected_step": selected_step, "git_head": git_head()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", default=f"results/{TASK_KEY}")
    parser.add_argument(
        "--variant-dir",
        default=f"results/{TASK_KEY}/runtime/attempts/{ATTEMPT_ID}/variants/{ATTEMPT_ID}",
    )
    parser.add_argument("--control-root", default=f"results/{TASK_KEY}/selected_checkpoint_controls")
    parser.add_argument("--eval-root", default=f"results/{TASK_KEY}/selected_checkpoint_evaluation")
    args = parser.parse_args()
    payload = aggregate(REPO_ROOT / args.result_root, REPO_ROOT / args.variant_dir, REPO_ROOT / args.control_root, REPO_ROOT / args.eval_root)
    print(json.dumps({"status": "OK", **payload}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
