#!/usr/bin/env python3
"""Lane A Round9 failure audit before baseline-preserving adaptation."""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import SimpleITK as sitk


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round09_baseline_initialized_adaptation/mpl_cache"),
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round04_fold0_short_train_eval as eval_base


OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round09_baseline_initialized_adaptation"
ROUND8_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round08_t2_edema_expert"
ROUND8_PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "laneA_t2_edema_expert_sephead_fold0_short__nnUNetPlans__3d_fullres/fold_0/validation"
)
BASELINE_PRED_DIR = eval_base.BASELINE_PRED_DIR
GT_DIR = eval_base.GT_DIR
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
DATASET_JSON = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/dataset.json"
BASELINE_CKPT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth"
)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def label_hist(arr: np.ndarray) -> dict[int, int]:
    labels, counts = np.unique(arr.astype(np.int64, copy=False), return_counts=True)
    return {int(k): int(v) for k, v in zip(labels, counts)}


def image_matches(a: sitk.Image, b: sitk.Image) -> bool:
    return (
        a.GetSize() == b.GetSize()
        and a.GetSpacing() == b.GetSpacing()
        and a.GetOrigin() == b.GetOrigin()
        and a.GetDirection() == b.GetDirection()
    )


def pred_audit_rows(pred_dir: Path, model: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    meta = eval_base.load_meta()
    for cid in eval_base.fold0_cases():
        gt_path = GT_DIR / f"{cid}.nii.gz"
        pred_path = pred_dir / f"{cid}.nii.gz"
        row: dict[str, object] = {
            "model": model,
            "case_id": cid,
            "prediction_path": str(pred_path),
            "prediction_exists": pred_path.is_file(),
            **meta.get(cid, {}),
        }
        if not pred_path.is_file():
            row["status"] = "missing_prediction"
            rows.append(row)
            continue
        gt_img = sitk.ReadImage(str(gt_path))
        pred_img = sitk.ReadImage(str(pred_path))
        gt = sitk.GetArrayFromImage(gt_img).astype(np.uint8, copy=False)
        pred = sitk.GetArrayFromImage(pred_img).astype(np.uint8, copy=False)
        hist = label_hist(pred)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        row.update(
            {
                "status": "ok",
                "geometry_matches_gt": image_matches(pred_img, gt_img),
                "pred_size": str(pred_img.GetSize()),
                "gt_size": str(gt_img.GetSize()),
                "pred_spacing": str(pred_img.GetSpacing()),
                "gt_spacing": str(gt_img.GetSpacing()),
                "labels": ",".join(str(k) for k in sorted(hist)),
                "invalid_labels": ",".join(str(k) for k in sorted(set(hist) - {0, 1, 2, 3, 4, 5})),
                "class1_voxels": hist.get(1, 0),
                "class2_voxels": hist.get(2, 0),
                "class3_voxels": hist.get(3, 0),
                "class4_voxels": hist.get(4, 0),
                "class5_voxels": hist.get(5, 0),
            }
        )
        row.update(eval_base.class_metrics(pred, gt, spacing, eval_base.EDEMA, "myops_edema"))
        row.update(eval_base.class_metrics(pred, gt, spacing, eval_base.SCAR, "myops_scar"))
        rows.append(row)
    return rows


def aggregate_basic(rows: list[dict[str, object]]) -> dict[str, object]:
    valid = [r for r in rows if r.get("status") == "ok"]
    invalid_label_cases = [r["case_id"] for r in valid if r.get("invalid_labels")]
    geometry_bad = [r["case_id"] for r in valid if not r.get("geometry_matches_gt")]
    return {
        "n_cases": len(rows),
        "n_predictions": len(valid),
        "missing": len(rows) - len(valid),
        "geometry_mismatch": len(geometry_bad),
        "invalid_label_cases": len(invalid_label_cases),
        "class4_total_voxels": sum(int(r.get("class4_voxels") or 0) for r in valid),
        "class5_total_voxels": sum(int(r.get("class5_voxels") or 0) for r in valid),
        "mean_scar_components": _mean([r.get("myops_scar_component_count") for r in valid]),
        "mean_edema_components": _mean([r.get("myops_edema_component_count") for r in valid]),
    }


def _mean(values: list[object]) -> float | None:
    vals = []
    for v in values:
        try:
            number = float(v)
        except (TypeError, ValueError):
            continue
        if not math.isnan(number) and not math.isinf(number):
            vals.append(number)
    return float(sum(vals) / len(vals)) if vals else None


def fmt(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        if math.isinf(value):
            return "inf"
        return f"{value:.4f}"
    return str(value)


def md_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    baseline_rows = pred_audit_rows(BASELINE_PRED_DIR, "baseline_nnunet501_fold0")
    round8_rows = pred_audit_rows(ROUND8_PRED_DIR, "candidate_laneA_round08_t2_edema_expert")
    all_rows = baseline_rows + round8_rows
    write_csv(OUT_ROOT / "round9_failure_audit_case_table.csv", all_rows)

    dataset_json = read_json(DATASET_JSON)
    labels = dataset_json.get("labels", {})
    fold0_cases = read_json(SPLITS_JSON)["folds"][0]["val"]
    summary_rows = [
        {"model": "baseline_nnunet501_fold0", **aggregate_basic(baseline_rows)},
        {"model": "candidate_laneA_round08_t2_edema_expert", **aggregate_basic(round8_rows)},
    ]
    baseline_geom_bad = {
        str(r["case_id"]) for r in baseline_rows if r.get("status") == "ok" and not r.get("geometry_matches_gt")
    }
    round8_geom_bad = {
        str(r["case_id"]) for r in round8_rows if r.get("status") == "ok" and not r.get("geometry_matches_gt")
    }
    round8_unique_geom_bad = sorted(round8_geom_bad - baseline_geom_bad)
    status_checks = {
        "baseline_checkpoint_exists": BASELINE_CKPT.is_file(),
        "baseline_prediction_dir_exists": BASELINE_PRED_DIR.is_dir(),
        "round8_prediction_dir_exists": ROUND8_PRED_DIR.is_dir(),
        "fold0_case_count_is_44": len(fold0_cases) == 44,
        "label_edema_is_4": labels.get("edema") == 4 or labels.get("4") == "edema",
        "label_scar_is_5": labels.get("scar") == 5 or labels.get("5") == "scar",
        "baseline_predictions_complete": aggregate_basic(baseline_rows)["n_predictions"] == 44,
        "round8_predictions_complete": aggregate_basic(round8_rows)["n_predictions"] == 44,
        "no_invalid_prediction_labels": all(not r.get("invalid_labels") for r in all_rows if r.get("status") == "ok"),
        "no_round8_unique_geometry_mismatch": len(round8_unique_geom_bad) == 0,
    }
    pass_gate = all(status_checks.values())
    obvious_bug = not pass_gate
    decision = "pass_continue_to_checkpoint_loader" if pass_gate else "fail_fix_engineering_before_training"

    lines = [
        "# Lane A Round9 Failure Audit",
        "",
        f"Decision: `{decision}`",
        "",
        "This audit checks whether Round8 collapse is explained by obvious label/export/evaluator/cache/geometry issues before any Round9 training.",
        "",
        "## Status Checks",
        "",
        md_table([{"check": k, "pass": v} for k, v in status_checks.items()], ["check", "pass"]),
        "",
        "## Prediction Summary",
        "",
        md_table(
            summary_rows,
            [
                "model",
                "n_cases",
                "n_predictions",
                "missing",
                "geometry_mismatch",
                "invalid_label_cases",
                "class4_total_voxels",
                "class5_total_voxels",
                "mean_edema_components",
                "mean_scar_components",
            ],
        ),
        "",
        "## Interpretation",
        "",
    ]
    if obvious_bug:
        lines.append("- A reproducibility/export/label/geometry check failed. Fix this before any Round9 training.")
    else:
        lines.extend(
            [
                "- Baseline and Round8 prediction files are complete for 44/44 fold0 validation cases.",
                "- Prediction labels are within compact labels `{0,1,2,3,4,5}`; geometry differences are shared with the baseline and handled by evaluator resampling.",
                "- Round8 collapse is therefore not explained by an obvious prediction-format or evaluator-label bug.",
                "- Continue to checkpoint-initialized 6-channel loader gate; do not train from scratch.",
            ]
        )
    if baseline_geom_bad or round8_geom_bad:
        lines.extend(
            [
                "",
                "Geometry note:",
                "",
                f"- Baseline geometry mismatch cases before evaluator resampling: `{len(baseline_geom_bad)}`.",
                f"- Round8 geometry mismatch cases before evaluator resampling: `{len(round8_geom_bad)}`.",
                f"- Round8-unique geometry mismatch cases: `{round8_unique_geom_bad}`.",
                "- Existing evaluator code resamples predictions to GT geometry before metric calculation; shared baseline/Round8 geometry differences are tracked as a warning, not as a Round8-specific fatal export bug.",
            ]
        )
    (OUT_ROOT / "round9_failure_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    readme = [
        "# Lane A Round9 Goal Execution Readme",
        "",
        "- Plan: `docs/plans/laneA_round09_next_baseline_initialized_edema_adaptation_execution.md`",
        "- Output root: `results/diagnostics/care_myocardium/laneA_myops/round09_baseline_initialized_adaptation/`",
        "- Current stage: `round9_failure_audit_and_baseline_reproducibility_gate`",
        f"- Current decision: `{decision}`",
        "- No training, Slurm, validation zip, upload, external repo, or weight download has been performed by this audit.",
    ]
    (OUT_ROOT / "round9_goal_execution_readme.md").write_text("\n".join(readme) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
