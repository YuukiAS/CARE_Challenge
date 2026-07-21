#!/usr/bin/env python3
"""Aggregate Batch6 final six-mode intervention predictions."""

from __future__ import annotations

import argparse
import csv
import json
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

MODES = (
    "anchor_identity_control",
    "full_learned_gate",
    "full_gate_one",
    "full_gate_zero",
    "proposal_only_gate_one",
    "refiner_only_gate_one",
)
LABELS = {"myops_edema": 4, "myops_scar": 5}


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def read_label(path: Path, reference: sitk.Image | None = None) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    if reference is not None:
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(reference)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        img = resampler.Execute(img)
    return img, sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch6.yaml")
    parser.add_argument("--result-root", default="results/20260721_srr_batch6_final_objective_alignment")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--job-state", required=True)
    parser.add_argument("--exit-code", required=True)
    parser.add_argument("--elapsed", required=True)
    parser.add_argument("--node", default="")
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    result_root = repo_path(args.result_root)
    out_root = result_root / "final_interventions/step300"
    val_cases = sorted(read_json(REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json")["folds"][0]["val"])
    metadata = load_myops_case_metadata(REPO_ROOT)
    gt_dir = repo_path(cfg["paths"]["gt_dir"])
    anchor_dir = repo_path(cfg["paths"]["anchor_fold0_pred_dir"])
    rows: list[dict[str, Any]] = []
    for mode in MODES:
        contract = read_json(out_root / f"batch3a_{mode}_inference_contract.json")
        pred_dir = out_root / mode / "predictions"
        for metric_name, cls in LABELS.items():
            all_deltas: list[float] = []
            pos_deltas: list[float] = []
            hd_deltas: list[float] = []
            remote_deltas: list[float] = []
            changed: list[float] = []
            for case_id in val_cases:
                meta = metadata[case_id]
                gt_img, gt = read_label(gt_dir / f"{case_id}.nii.gz")
                _anchor_img, anchor = read_label(anchor_dir / f"{case_id}.nii.gz", gt_img)
                _pred_img, pred = read_label(pred_dir / f"{case_id}.nii.gz", gt_img)
                spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
                myo = (gt >= 1) & (gt <= 5)
                anchor_dice = dice_per_class(anchor, gt, cls, skip_if_gt_empty=False)
                pred_dice = dice_per_class(pred, gt, cls, skip_if_gt_empty=False)
                if anchor_dice is not None and pred_dice is not None:
                    delta = float(pred_dice - anchor_dice)
                    all_deltas.append(delta)
                    if np.any(gt == cls):
                        pos_deltas.append(delta)
                anchor_hd = hd95_class(anchor, gt, cls, spacing)
                pred_hd = hd95_class(pred, gt, cls, spacing)
                if anchor_hd is not None and pred_hd is not None:
                    hd_deltas.append(float(pred_hd - anchor_hd))
                anchor_comp = component_stats(anchor, gt, myo, cls, spacing)
                pred_comp = component_stats(pred, gt, myo, cls, spacing)
                remote_deltas.append(float(pred_comp["remote_fp_volume_mm3"] - anchor_comp["remote_fp_volume_mm3"]))
                changed.append(float(np.count_nonzero((pred == cls) != (anchor == cls))))
            rows.append(
                {
                    "mode": mode,
                    "pathology": metric_name,
                    "population": "positive_gt_cases",
                    "case_count": len(pos_deltas),
                    "mean_dice_delta_vs_anchor": mean(pos_deltas),
                    "mean_hd95_delta_vs_anchor": mean(hd_deltas),
                    "mean_remote_fp_delta_mm3": mean(remote_deltas),
                    "mean_changed_voxels_vs_anchor": mean(changed),
                    "checkpoint_global_step": contract.get("checkpoint_global_step"),
                    "checkpoint_sha256": contract.get("checkpoint_receipt", {}).get("checkpoint_sha256"),
                    "slurm_job_id": args.job_id,
                    "slurm_state": args.job_state,
                    "slurm_exit_code": args.exit_code,
                    "slurm_elapsed": args.elapsed,
                    "slurm_node": args.node,
                }
            )
            rows.append(
                {
                    "mode": mode,
                    "pathology": metric_name,
                    "population": "all_case_empty_safe",
                    "case_count": len(all_deltas),
                    "mean_dice_delta_vs_anchor": mean(all_deltas),
                    "mean_hd95_delta_vs_anchor": mean(hd_deltas),
                    "mean_remote_fp_delta_mm3": mean(remote_deltas),
                    "mean_changed_voxels_vs_anchor": mean(changed),
                    "checkpoint_global_step": contract.get("checkpoint_global_step"),
                    "checkpoint_sha256": contract.get("checkpoint_receipt", {}).get("checkpoint_sha256"),
                    "slurm_job_id": args.job_id,
                    "slurm_state": args.job_state,
                    "slurm_exit_code": args.exit_code,
                    "slurm_elapsed": args.elapsed,
                    "slurm_node": args.node,
                }
            )
    write_csv(result_root / "final_mechanism_interventions.csv", rows)
    print(json.dumps({"status": "BATCH6_FINAL_INTERVENTIONS_AGGREGATED", "rows": len(rows), "modes": list(MODES)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
