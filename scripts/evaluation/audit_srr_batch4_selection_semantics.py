#!/usr/bin/env python3
"""Batch5 selection-semantics and intervention aggregation for SRR MyoPS."""

from __future__ import annotations

import argparse
import csv
import json
import math
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
from src.care_myocardium.srr_production.anchor_manifest import rel, sha256_file  # noqa: E402


TASK_KEY = "20260721_srr_batch5_post_batch4_diagnostic_repair"
LABELS = {"edema": 4, "scar": 5}
STEPS = (600, 1200, 1800)
INTERVENTION_MODES = (
    "anchor_identity_control",
    "anchor_bounded_full",
    "srr_no_anchor_control",
    "anchor_bounded_proposal_only",
    "anchor_bounded_refiner_only",
    "production_gate_closed",
    "production_gate_open_bounded_control",
)
ORACLE_MODES = (
    "anchor_identity_control",
    "anchor_bounded_full",
    "anchor_bounded_proposal_only",
    "anchor_bounded_refiner_only",
    "production_gate_open_bounded_control",
)
BATCH4_VARIANT_DIR = (
    REPO_ROOT
    / "results/20260721_srr_batch4_forced_fold0_training/runtime/attempts/"
    "srr_batch4_m10d3_full4scale_fold0_seed20260721_htzhulab_59682067/variants/"
    "srr_batch4_m10d3_full4scale_fold0_seed20260721_htzhulab_59682067"
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def fold_cases(split_path: Path, fold: int) -> list[str]:
    return sorted(load_json(split_path)["folds"][fold]["val"])


def metric_row(
    *,
    case_id: str,
    mode: str,
    pathology: str,
    class_id: int,
    pred: np.ndarray,
    anchor: np.ndarray,
    gt: np.ndarray,
    spacing: tuple[float, ...],
    metadata: Any,
    tensor_lookup: dict[tuple[str, str], dict[str, str]],
) -> dict[str, Any]:
    myocardium = (gt >= 1) & (gt <= 5)
    anchor_stats = component_stats(anchor, gt, myocardium, class_id, spacing)
    pred_stats = component_stats(pred, gt, myocardium, class_id, spacing)
    gt_mask = gt == class_id
    anchor_mask = anchor == class_id
    pred_mask = pred == class_id
    anchor_error = anchor_mask != gt_mask
    pred_error = pred_mask != gt_mask
    corrected_anchor_error = anchor_error & ~pred_error
    harmful_correction = ~anchor_error & pred_error
    anchor_dice = dice_per_class(anchor, gt, class_id, skip_if_gt_empty=True)
    pred_dice = dice_per_class(pred, gt, class_id, skip_if_gt_empty=True)
    anchor_hd95 = hd95_class(anchor, gt, class_id, spacing)
    pred_hd95 = hd95_class(pred, gt, class_id, spacing)
    tensor = tensor_lookup.get((case_id, pathology), {})
    return {
        "case_id": case_id,
        "mode": mode,
        "pathology": pathology,
        "class_id": class_id,
        "center": metadata.center,
        "modality_group": metadata.modality_group,
        "t2_present": bool(metadata.t2_present),
        "gt_positive": bool(np.any(gt == class_id)),
        "anchor_dice": anchor_dice,
        "mode_dice": pred_dice,
        "dice_delta_vs_anchor": None if anchor_dice is None or pred_dice is None else float(pred_dice - anchor_dice),
        "anchor_hd95": anchor_hd95,
        "mode_hd95": pred_hd95,
        "hd95_delta_vs_anchor": None if anchor_hd95 is None or pred_hd95 is None else float(pred_hd95 - anchor_hd95),
        "changed_voxels_vs_anchor": int(np.count_nonzero((pred == class_id) != (anchor == class_id))),
        "anchor_error_voxels_vs_gt": int(np.count_nonzero(anchor_error)),
        "corrected_anchor_error_voxels": int(np.count_nonzero(corrected_anchor_error)),
        "harmful_correction_voxels": int(np.count_nonzero(harmful_correction)),
        "anchor_component_count": anchor_stats["component_count"],
        "mode_component_count": pred_stats["component_count"],
        "component_delta": int(pred_stats["component_count"]) - int(anchor_stats["component_count"]),
        "anchor_remote_fp_volume_mm3": anchor_stats["remote_fp_volume_mm3"],
        "mode_remote_fp_volume_mm3": pred_stats["remote_fp_volume_mm3"],
        "remote_fp_delta_mm3": float(pred_stats["remote_fp_volume_mm3"] - anchor_stats["remote_fp_volume_mm3"]),
        "proposal_positive_voxels": tensor.get("proposal_positive_voxels", ""),
        "proposal_component_count": "",
        "proposal_remote_fp_count": "",
        "roi_gt_coverage": "",
        "roi_outside_ratio": "",
        "refiner_residual_abs_mean": tensor.get("refiner_residual_abs_mean", ""),
        "production_gate_mean": tensor.get("production_gate_mean", ""),
        "production_gate_p50": tensor.get("production_gate_p50", ""),
        "production_gate_p95": tensor.get("production_gate_p95", ""),
        "production_gate_max": tensor.get("production_gate_max", ""),
        "raw_correction_abs_mean": tensor.get("raw_correction_abs_mean", ""),
        "raw_correction_abs_p95": tensor.get("raw_correction_abs_p95", ""),
        "raw_correction_abs_max": tensor.get("raw_correction_abs_max", ""),
        "bounded_correction_abs_mean": tensor.get("bounded_correction_abs_mean", ""),
        "bounded_correction_abs_p95": tensor.get("bounded_correction_abs_p95", ""),
        "bounded_correction_abs_max": tensor.get("bounded_correction_abs_max", ""),
    }


def aggregate_rows(rows: list[dict[str, Any]], mode: str, checkpoint: str = "step_1800") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pathology in LABELS:
        rows_p = [row for row in rows if row["mode"] == mode and row["pathology"] == pathology]
        rows_pos = [row for row in rows_p if row["gt_positive"]]
        rows_all = rows_p
        for population, subset in (("positive_gt_cases", rows_pos), ("all_case_empty_safe", rows_all)):
            out.append(
                {
                    "checkpoint": checkpoint,
                    "mode": mode,
                    "pathology": pathology,
                    "population": population,
                    "case_count": len(subset),
                    "anchor_dice_mean": mean([float(row["anchor_dice"]) for row in subset if row["anchor_dice"] is not None]),
                    "mode_dice_mean": mean([float(row["mode_dice"]) for row in subset if row["mode_dice"] is not None]),
                    "dice_delta_mean": mean([float(row["dice_delta_vs_anchor"]) for row in subset if row["dice_delta_vs_anchor"] is not None]),
                    "mode_hd95_mean": mean([float(row["mode_hd95"]) for row in subset if row["mode_hd95"] is not None]),
                    "hd95_delta_mean": mean([float(row["hd95_delta_vs_anchor"]) for row in subset if row["hd95_delta_vs_anchor"] is not None]),
                    "remote_fp_delta_mm3_mean": mean([float(row["remote_fp_delta_mm3"]) for row in subset]),
                    "component_delta_mean": mean([float(row["component_delta"]) for row in subset]),
                    "changed_voxels_mean": mean([float(row["changed_voxels_vs_anchor"]) for row in subset]),
                }
            )
    return out


def evaluate_prediction_dir(
    *,
    mode: str,
    pred_dir: Path,
    cases: list[str],
    gt_dir: Path,
    anchor_dir: Path,
    metadata: dict[str, Any],
    tensor_lookup: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_id in cases:
        gt_img, gt = read_label(gt_dir / f"{case_id}.nii.gz")
        _anchor_img, anchor = read_label(anchor_dir / f"{case_id}.nii.gz", gt_img)
        _pred_img, pred = read_label(pred_dir / f"{case_id}.nii.gz", gt_img)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        for pathology, class_id in LABELS.items():
            rows.append(
                metric_row(
                    case_id=case_id,
                    mode=mode,
                    pathology=pathology,
                    class_id=class_id,
                    pred=pred,
                    anchor=anchor,
                    gt=gt,
                    spacing=spacing,
                    metadata=metadata[case_id],
                    tensor_lookup=tensor_lookup,
                )
            )
    return rows


def tensor_lookup(inference_root: Path, mode: str) -> dict[tuple[str, str], dict[str, str]]:
    path = inference_root / f"batch3a_{mode}_tensor_checks.csv"
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_csv(path):
        out[(row.get("case_id", ""), row.get("pathology", ""))] = row
    return out


def checkpoint_reranking(
    *,
    cases: list[str],
    gt_dir: Path,
    anchor_dir: Path,
    metadata: dict[str, Any],
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_step_case_rows: dict[int, list[dict[str, Any]]] = {}
    for step in STEPS:
        pred_dir = BATCH4_VARIANT_DIR / "predictions/fold_0" / f"step_{step}" / "argmax"
        case_rows = evaluate_prediction_dir(
            mode=f"step_{step}_formal_argmax",
            pred_dir=pred_dir,
            cases=cases,
            gt_dir=gt_dir,
            anchor_dir=anchor_dir,
            metadata=metadata,
            tensor_lookup={},
        )
        by_step_case_rows[step] = case_rows
        agg = {row["pathology"]: row for row in aggregate_rows(case_rows, f"step_{step}_formal_argmax", f"step_{step}") if row["population"] == "positive_gt_cases"}
        deltas = [float(agg[p]["dice_delta_mean"]) for p in LABELS if agg[p]["dice_delta_mean"] is not None]
        hd95_deltas = [float(agg[p]["hd95_delta_mean"]) for p in LABELS if agg[p]["hd95_delta_mean"] is not None]
        remote_deltas = [float(agg[p]["remote_fp_delta_mm3_mean"]) for p in LABELS if agg[p]["remote_fp_delta_mm3_mean"] is not None]
        hd95_relative_worsening: dict[str, float] = {}
        remote_relative_worsening: dict[str, float] = {}
        hd95_gate_by_pathology: dict[str, bool] = {}
        remote_gate_by_pathology: dict[str, bool] = {}
        for pathology in LABELS:
            rows_pos_p = [row for row in case_rows if row["pathology"] == pathology and row["gt_positive"]]
            anchor_hd95_mean = mean([float(row["anchor_hd95"]) for row in rows_pos_p if row["anchor_hd95"] is not None])
            mode_hd95_mean = mean([float(row["mode_hd95"]) for row in rows_pos_p if row["mode_hd95"] is not None])
            anchor_remote_mean = mean([float(row["anchor_remote_fp_volume_mm3"]) for row in rows_pos_p])
            mode_remote_mean = mean([float(row["mode_remote_fp_volume_mm3"]) for row in rows_pos_p])
            hd95_delta = None if anchor_hd95_mean is None or mode_hd95_mean is None else mode_hd95_mean - anchor_hd95_mean
            remote_delta = None if anchor_remote_mean is None or mode_remote_mean is None else mode_remote_mean - anchor_remote_mean
            hd95_relative_worsening[pathology] = (
                0.0
                if hd95_delta is None or hd95_delta <= 0
                else float(hd95_delta / max(abs(anchor_hd95_mean or 0.0), 1e-6))
            )
            remote_relative_worsening[pathology] = (
                0.0
                if remote_delta is None or remote_delta <= 0
                else float(remote_delta / max(abs(anchor_remote_mean or 0.0), 1e-6))
            )
            hd95_gate_by_pathology[pathology] = hd95_relative_worsening[pathology] <= 0.05
            remote_gate_by_pathology[pathology] = remote_relative_worsening[pathology] <= 0.05
        harm = sum(1 for row in case_rows if row["gt_positive"] and row["dice_delta_vs_anchor"] is not None and float(row["dice_delta_vs_anchor"]) < 0)
        help_count = sum(1 for row in case_rows if row["gt_positive"] and row["dice_delta_vs_anchor"] is not None and float(row["dice_delta_vs_anchor"]) > 0)
        min_delta = min(deltas) if deltas else None
        mean_delta = mean(deltas)
        mean_hd95_delta = mean(hd95_deltas)
        mean_remote_delta = mean(remote_deltas)
        dice_gate = bool(min_delta is not None and min_delta >= -0.002)
        help_harm_gate = help_count >= harm
        hd95_gate = all(hd95_gate_by_pathology.values())
        remote_gate = all(remote_gate_by_pathology.values())
        eligible = bool(dice_gate and help_harm_gate and hd95_gate and remote_gate)
        failed_gates = [
            name
            for name, passed in (
                ("dice_delta", dice_gate),
                ("help_harm", help_harm_gate),
                ("hd95_relative_worsening", hd95_gate),
                ("remote_fp_relative_worsening", remote_gate),
            )
            if not passed
        ]
        rows.append(
            {
                "checkpoint": f"step_{step}",
                "step": step,
                "case_count": len(cases),
                "decode_rule": "outputs_logits_argmax",
                "metric_population": "positive_gt_cases",
                "edema_positive_dice_delta": agg["edema"]["dice_delta_mean"],
                "scar_positive_dice_delta": agg["scar"]["dice_delta_mean"],
                "min_scar_edema_positive_dice_delta": min_delta,
                "mean_scar_edema_positive_dice_delta": mean_delta,
                "harm_case_pathology_count": harm,
                "help_case_pathology_count": help_count,
                "mean_positive_hd95_delta": mean_hd95_delta,
                "remote_fp_delta_mean_mm3": mean_remote_delta,
                "edema_hd95_relative_worsening": hd95_relative_worsening["edema"],
                "scar_hd95_relative_worsening": hd95_relative_worsening["scar"],
                "edema_remote_fp_relative_worsening": remote_relative_worsening["edema"],
                "scar_remote_fp_relative_worsening": remote_relative_worsening["scar"],
                "hd95_relative_worsening_gate": hd95_gate,
                "remote_fp_relative_worsening_gate": remote_gate,
                "dice_delta_gate": dice_gate,
                "help_harm_gate": help_harm_gate,
                "eligible": eligible,
                "eligibility_status": "ELIGIBLE" if eligible else "B5_NO_SAFETY_ELIGIBLE_CHECKPOINT:" + ",".join(failed_gates),
            }
        )
    rows.sort(
        key=lambda row: (
            0 if row["eligible"] else 1,
            -float(row["min_scar_edema_positive_dice_delta"] or -1e9),
            -float(row["mean_scar_edema_positive_dice_delta"] or -1e9),
            int(row["harm_case_pathology_count"]),
            float(row["mean_positive_hd95_delta"] or 1e9),
            float(row["remote_fp_delta_mean_mm3"] or 1e9),
            int(row["step"]),
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["formal_argmax_rank"] = rank
    return rows


def oracle_headroom(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in case_rows:
        if row["mode"] in ORACLE_MODES:
            grouped.setdefault((row["case_id"], row["pathology"]), []).append(row)
    for (case_id, pathology), candidates in sorted(grouped.items()):
        identity = next(row for row in candidates if row["mode"] == "anchor_identity_control")
        valid = [row for row in candidates if row["mode_dice"] is not None]
        best = max(valid, key=lambda row: float(row["mode_dice"])) if valid else identity
        anchor_dice = identity["anchor_dice"]
        best_dice = best["mode_dice"]
        rows.append(
            {
                "case_id": case_id,
                "pathology": pathology,
                "anchor_dice": anchor_dice,
                "best_mode": best["mode"],
                "best_mode_dice": best_dice,
                "oracle_dice_gain": None if anchor_dice is None or best_dice is None else float(best_dice - anchor_dice),
                "anchor_error_voxels_vs_gt": int(identity["anchor_error_voxels_vs_gt"]),
                "correctable_anchor_error_voxels": int(best["corrected_anchor_error_voxels"]),
                "harmful_correction_voxels_avoided": max(
                    0,
                    max(int(row["harmful_correction_voxels"]) for row in candidates) - int(best["harmful_correction_voxels"]),
                ),
                "diagnostic_only": True,
                "deployable_candidate": False,
            }
        )
    return rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    result_root = REPO_ROOT / args.result_root
    cfg = yaml.safe_load((REPO_ROOT / args.config).read_text(encoding="utf-8"))
    paths = cfg["paths"]
    cases = fold_cases(REPO_ROOT / paths["split_path"], int(cfg["source_batch4"]["fold"]))
    gt_dir = REPO_ROOT / paths["gt_dir"]
    anchor_dir = REPO_ROOT / paths["anchor_fold0_pred_dir"]
    inference_root = result_root / "runtime/inference"
    metadata = load_myops_case_metadata(REPO_ROOT)

    rerank_rows = checkpoint_reranking(cases=cases, gt_dir=gt_dir, anchor_dir=anchor_dir, metadata=metadata, cfg=cfg)
    write_csv(result_root / "checkpoint_reranking.csv", rerank_rows)

    case_rows: list[dict[str, Any]] = []
    for mode in INTERVENTION_MODES:
        pred_dir = inference_root / mode / "predictions"
        if not pred_dir.is_dir():
            raise FileNotFoundError(f"missing Batch5 prediction directory for {mode}: {pred_dir}")
        case_rows.extend(
            evaluate_prediction_dir(
                mode=mode,
                pred_dir=pred_dir,
                cases=cases,
                gt_dir=gt_dir,
                anchor_dir=anchor_dir,
                metadata=metadata,
                tensor_lookup=tensor_lookup(inference_root, mode),
            )
        )
    write_csv(result_root / "casewise_mechanism_attribution.csv", case_rows)
    mode_rows: list[dict[str, Any]] = []
    for mode in INTERVENTION_MODES:
        mode_rows.extend(aggregate_rows(case_rows, mode))
    write_csv(result_root / "mode_intervention_metrics.csv", mode_rows)
    oracle_rows = oracle_headroom(case_rows)
    write_csv(result_root / "oracle_headroom.csv", oracle_rows)

    best = rerank_rows[0] if rerank_rows else {}
    audit = [
        "# Evaluation Semantics Audit",
        "",
        "status: COMPLETE",
        "",
        "Batch5 preserves Batch4 historical files and reranks existing step 600/1200/1800 outputs in a new namespace.",
        "",
        f"formal_decode_rule: outputs_logits_argmax",
        f"primary_population: positive_gt_cases",
        f"all_case_empty_safe_reported: true",
        f"historical_pathology_aware_role: diagnostic_only_not_checkpoint_authority",
        f"top_formal_argmax_checkpoint: {best.get('checkpoint', 'NA')}",
        "",
        "Generated files:",
        "- checkpoint_reranking.csv",
        "- mode_intervention_metrics.csv",
        "- casewise_mechanism_attribution.csv",
        "- oracle_headroom.csv",
    ]
    (result_root / "evaluation_semantics_audit.md").write_text("\n".join(audit) + "\n", encoding="utf-8")
    payload = {
        "status": "BATCH5_EVALUATION_SEMANTICS_COMPLETE",
        "case_count": len(cases),
        "reranked_checkpoints": [row["checkpoint"] for row in rerank_rows],
        "intervention_modes": list(INTERVENTION_MODES),
        "result_root": rel(result_root, REPO_ROOT),
    }
    write_json(result_root / "evaluation_semantics_audit.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch5.yaml")
    parser.add_argument("--result-root", default=f"results/{TASK_KEY}")
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
