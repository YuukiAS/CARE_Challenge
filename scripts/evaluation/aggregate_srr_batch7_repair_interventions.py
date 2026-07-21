#!/usr/bin/env python3
"""Aggregate Batch7 repair interventions from independent prediction roots."""

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

from scripts.evaluation.aggregate_srr_batch6_formal import mean, read_label, rel, summarize, write_csv  # noqa: E402
from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class  # noqa: E402
from scripts.srr_production.evaluate_myops_fair import component_stats  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402

LABELS = {"myops_edema": 4, "myops_scar": 5}


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def split_val_cases(cfg: dict[str, Any]) -> list[str]:
    payload = json.loads(repo_path(cfg["paths"]["split_path"]).read_text(encoding="utf-8"))
    return list(payload["folds"][int(cfg["training_data"]["fold"])]["val"])


def mode_prediction_manifest(intervention_root: Path, mode: str) -> dict[str, Any]:
    manifest_path = intervention_root / mode / "prediction_manifest.json"
    if not manifest_path.is_file():
        fallback = intervention_root / f"batch3a_{mode}_inference_contract.json"
        if not fallback.is_file():
            raise FileNotFoundError(f"missing prediction manifest for {mode}")
        return json.loads(fallback.read_text(encoding="utf-8"))
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def metric_rows_for_mode(cfg: dict[str, Any], mode: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    result_root = repo_path(cfg["paths"]["result_root"])
    intervention_root = repo_path(cfg["paths"]["intervention_root"])
    pred_dir = intervention_root / mode / "predictions"
    gt_dir = repo_path(cfg["paths"]["gt_dir"])
    anchor_dir = repo_path(cfg["paths"]["anchor_root"]) / "fold_0/validation"
    geometry_csv = intervention_root / f"batch3a_{mode}_geometry_roundtrip.csv"
    geometry = {row["case_id"]: row for row in read_csv(geometry_csv)} if geometry_csv.is_file() else {}
    rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    for case_id in split_val_cases(cfg):
        meta = metadata[case_id]
        gt_img, gt = read_label(gt_dir / f"{case_id}.nii.gz")
        _anchor_img, anchor = read_label(anchor_dir / f"{case_id}.nii.gz", gt_img)
        pred_path = pred_dir / f"{case_id}.nii.gz"
        _pred_img, pred = read_label(pred_path, gt_img)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        myo = (gt >= 1) & (gt <= 5)
        geom = geometry.get(case_id, {})
        manifest_rows.append(
            {
                "mode": mode,
                "case_id": case_id,
                "prediction_path": rel(pred_path),
                "prediction_sha256": sha256_file(pred_path),
                "prediction_root": rel(pred_dir),
                "command_manifest": rel(intervention_root / mode / "commands.json"),
                "model_forward_count": int(float(geom.get("model_forward_count", 1) or 1)),
                "checkpoint_actual_load_count": int(float(geom.get("checkpoint_actual_load_count", 1) or 1)),
                "output_sha256_from_inference": geom.get("output_sha256", ""),
            }
        )
        for pathology, cls in LABELS.items():
            gt_positive = bool(np.any(gt == cls))
            anchor_dice = dice_per_class(anchor, gt, cls, skip_if_gt_empty=False)
            pred_dice = dice_per_class(pred, gt, cls, skip_if_gt_empty=False)
            anchor_hd95 = hd95_class(anchor, gt, cls, spacing)
            pred_hd95 = hd95_class(pred, gt, cls, spacing)
            anchor_comp = component_stats(anchor, gt, myo, cls, spacing)
            pred_comp = component_stats(pred, gt, myo, cls, spacing)
            rows.append(
                {
                    "stage": "batch7_repair_intervention",
                    "mode": mode,
                    "total_step": 0,
                    "case_id": case_id,
                    "center": meta.center,
                    "modality_group": meta.modality_group,
                    "t2_present": bool(meta.t2_present),
                    "pathology": pathology,
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
                    "prediction_path": rel(pred_path),
                }
            )
    return rows, manifest_rows


def summary_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for mode in sorted({str(row["mode"]) for row in case_rows}):
        rows = [{**row, "total_step": 0} for row in case_rows if row["mode"] == mode]
        for row in summarize(rows):
            out.append({"mode": mode, **row})
    return out


def component_metric_rows(summary: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_mode = {(row["mode"], row["pathology"], row["group"]): row for row in summary}
    proposal_refiner: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for pathology in LABELS:
        prop = by_mode.get(("proposal_only_gate_one", pathology, "gt_positive_only"))
        refiner = by_mode.get(("refiner_only_gate_one", pathology, "gt_positive_only"))
        learned = by_mode.get(("learned_source_gate_one", pathology, "gt_positive_only"))
        full = by_mode.get(("production_gate_one", pathology, "gt_positive_only"))
        proposal_delta = None if prop is None else prop.get("dice_delta_mean")
        refiner_delta = None if refiner is None else refiner.get("dice_delta_mean")
        learned_delta = None if learned is None else learned.get("dice_delta_mean")
        full_delta = None if full is None else full.get("dice_delta_mean")
        proposal_refiner.append(
            {
                "pathology": pathology,
                "proposal_only_dice_delta": proposal_delta,
                "refiner_only_dice_delta": refiner_delta,
                "refiner_minus_proposal_dice_delta": None
                if proposal_delta in {"", None} or refiner_delta in {"", None}
                else float(refiner_delta) - float(proposal_delta),
                "source": "independent_prediction_roots",
            }
        )
        source_rows.append(
            {
                "pathology": pathology,
                "learned_source_dice_delta": learned_delta,
                "production_gate_one_dice_delta": full_delta,
                "learned_source_minus_proposal_dice_delta": None
                if proposal_delta in {"", None} or learned_delta in {"", None}
                else float(learned_delta) - float(proposal_delta),
                "source": "independent_prediction_roots",
            }
        )
    return proposal_refiner, source_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_repair.yaml")
    parser.add_argument("--result-root", default="")
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    if args.result_root:
        cfg["paths"]["result_root"] = args.result_root
        cfg["paths"]["runtime_root"] = str(Path(args.result_root) / "runtime")
        cfg["paths"]["intervention_root"] = str(Path(args.result_root) / "runtime/interventions")
    result_root = repo_path(cfg["paths"]["result_root"])
    intervention_root = repo_path(cfg["paths"]["intervention_root"])
    modes = [str(mode) for mode in cfg["intervention_execution"]["modes"]]
    case_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    manifests = []
    for mode in modes:
        manifests.append(mode_prediction_manifest(intervention_root, mode))
        rows, pred_rows = metric_rows_for_mode(cfg, mode)
        case_rows.extend(rows)
        prediction_rows.extend(pred_rows)
    summary = summary_rows(case_rows)
    proposal_refiner, source_rows = component_metric_rows(summary)
    write_csv(result_root / "intervention_casewise_metrics.csv", case_rows)
    write_csv(result_root / "intervention_summary.csv", summary)
    write_csv(result_root / "intervention_prediction_manifest.csv", prediction_rows)
    write_csv(result_root / "proposal_refiner_metrics.csv", proposal_refiner)
    write_csv(result_root / "source_arbiter_metrics.csv", source_rows)
    write_json(result_root / "intervention_aggregation.json", {"status": "PASS", "mode_count": len(modes), "case_metric_rows": len(case_rows), "prediction_manifest_rows": len(prediction_rows), "mode_manifests": manifests})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
