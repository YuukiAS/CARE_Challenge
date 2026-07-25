#!/usr/bin/env python3
"""Evaluate MoSAIC fold0 fair-comparison predictions under one protocol."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
MOSAIC_CODE = REPO_ROOT / "code/MoSAIC"
if str(MOSAIC_CODE) not in sys.path:
    sys.path.insert(0, str(MOSAIC_CODE))

from mosaic_fair_protocol import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_RESULT_ROOT,
    OFFICIAL_TO_COMPACT,
    classify_spatial_layout,
    geometry_matches,
    geometry_signature,
    label_mapping_audit_rows,
    load_fold_val_cases,
    load_yaml,
    protocol_receipt,
    remap_labels,
    write_csv,
    write_json,
)
from scripts.evaluation.evaluate_predictions import dice_per_class, hd_class  # noqa: E402


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit-cases", type=int, default=None)
    ap.add_argument("--nnunet-pred-dir", type=Path, default=None)
    ap.add_argument("--native-mosaic-pred-dir", type=Path, default=None)
    ap.add_argument("--hybrid-pred-dir", type=Path, default=None)
    ap.add_argument("--care-candidate-pred-dir", type=Path, default=None)
    return ap.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def model_specs(config: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    override = {
        "nnunet_fold0": args.nnunet_pred_dir,
        "native_mosaic": args.native_mosaic_pred_dir,
        "nnunet_anatomy_prior_mosaic_experts": args.hybrid_pred_dir,
        "care_candidate": args.care_candidate_pred_dir,
    }
    specs = []
    for spec in config["evaluation"]["allowed_models"]:
        pred_dir = override.get(spec["model_id"]) or (REPO_ROOT / spec["prediction_dir"])
        specs.append({**spec, "prediction_dir_resolved": pred_dir})
    return specs


def load_label_array(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    return img, sitk.GetArrayFromImage(img).astype(np.int32, copy=False)


def resample_label_to_reference(img: sitk.Image, reference: sitk.Image) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(img)


def evaluate_predictions(config: dict[str, Any], cases: list[str], specs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    gt_dir = REPO_ROOT / config["dataset"]["raw_label_dir"]
    casewise: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    label_rows = label_mapping_audit_rows()
    class_map = {"pure_edema": 4, "scar": 5}

    for spec in specs:
        model_id = spec["model_id"]
        pred_dir = Path(spec["prediction_dir_resolved"])
        pred_dir_exists = pred_dir.is_dir()
        for case_id in cases:
            gt_path = gt_dir / f"{case_id}.nii.gz"
            pred_path = pred_dir / f"{case_id}.nii.gz"
            if not gt_path.is_file():
                geometry_rows.append({"model_id": model_id, "case_id": case_id, "status": "MISSING_GT", "prediction_dir": str(pred_dir)})
                continue
            gt_img, gt = load_label_array(gt_path)
            if not pred_dir_exists or not pred_path.is_file():
                geometry_rows.append({"model_id": model_id, "case_id": case_id, "status": "MISSING_PRED", "prediction_dir": str(pred_dir)})
                continue
            pred_img_raw, pred_raw = load_label_array(pred_path)
            pred_sig = geometry_signature(pred_img_raw)
            gt_sig = geometry_signature(gt_img)
            raw_layout = classify_spatial_layout(tuple(pred_raw.shape), tuple(gt.shape))
            raw_geometry_match = geometry_matches(pred_sig, gt_sig) and raw_layout == "ZHW"
            pred_img = pred_img_raw if raw_geometry_match else resample_label_to_reference(pred_img_raw, gt_img)
            pred = sitk.GetArrayFromImage(pred_img).astype(np.int32, copy=False)
            if spec.get("label_space") == "official":
                pred = remap_labels(pred, OFFICIAL_TO_COMPACT)
            geometry_rows.append(
                {
                    "model_id": model_id,
                    "case_id": case_id,
                    "status": "PASS" if geometry_matches(geometry_signature(pred_img), gt_sig) else "FAIL",
                    "raw_geometry_status": "PASS" if raw_geometry_match else "FAIL_STANDARDIZED_AFTER_AUDIT",
                    "layout": raw_layout,
                    "prediction_dir": str(pred_dir),
                    "size_xyz_match": int(pred_sig["size_xyz"] == gt_sig["size_xyz"]),
                    "spacing_origin_direction_match": int(geometry_matches(pred_sig, gt_sig)),
                }
            )
            spacing = tuple(float(v) for v in gt_img.GetSpacing()[::-1])
            for pathology, class_id in class_map.items():
                gt_positive = bool(np.any(gt == class_id))
                pred_positive = bool(np.any(pred == class_id))
                casewise.append(
                    {
                        "model_id": model_id,
                        "role": spec.get("role", ""),
                        "case_id": case_id,
                        "pathology": pathology,
                        "compact_class": class_id,
                        "official_label": 1220 if class_id == 4 else 2221,
                        "gt_positive": int(gt_positive),
                        "prediction_positive": int(pred_positive),
                        "dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=True),
                        "exact_hd": hd_class(pred, gt, class_id, spacing),
                    }
                )
    return casewise, geometry_rows, label_rows


def mean(values: list[Any]) -> float | None:
    vals: list[float] = []
    for value in values:
        if value in (None, "", "None", "nan"):
            continue
        val = float(value)
        if np.isfinite(val):
            vals.append(val)
    return float(np.mean(vals)) if vals else None


def summarize(casewise: list[dict[str, Any]], specs: list[dict[str, Any]], cases: list[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in casewise:
        grouped[(row["model_id"], row["pathology"])].append(row)
    rows: list[dict[str, Any]] = []
    for spec in specs:
        for pathology in ("pure_edema", "scar"):
            group = grouped.get((spec["model_id"], pathology), [])
            rows.append(
                {
                    "model_id": spec["model_id"],
                    "role": spec.get("role", ""),
                    "pathology": pathology,
                    "population": "positive_gt",
                    "case_count_expected": len(cases),
                    "case_count_evaluated": len({row["case_id"] for row in group}),
                    "gt_positive_cases": sum(int(row["gt_positive"]) for row in group),
                    "mean_dice": mean([row["dice"] for row in group if int(row["gt_positive"]) == 1]),
                    "mean_exact_hd": mean([row["exact_hd"] for row in group if int(row["gt_positive"]) == 1]),
                    "status": "PASS" if len({row["case_id"] for row in group}) == len(cases) else "MISSING_PREDICTIONS",
                }
            )
    return rows


def write_result_md(path: Path, receipt: dict[str, Any], metrics: list[dict[str, Any]]) -> None:
    status = receipt["status"]
    complete = status == "VERIFIED_EVALUATION_COMPLETE"
    if complete:
        first = "MoSAIC fold0 公平复现已经形成完整评价闭环，可以和 nnU-Net 及 CARE 候选在同一口径下比较；下一步仍需由 Planner 决定是否进入机制筛查或训练。"
    elif status == "NEEDS_PREDICTIONS":
        first = "MoSAIC 源码、权重路径和启动前检查已经就绪，但 native MoSAIC 的 fold0 预测还没有生成；当前可以开始正式 GPU inference，不能训练、不能上传，也不能把 MoSAIC 当成已完成 baseline。"
    else:
        first = "MoSAIC 权重已经登记，但 native MoSAIC 复现还没有闭环；当前只能确认协议、通道、label 和几何审计框架，不能训练、不能上传，也不能把 MoSAIC 当成已完成 baseline。"
    lines = [
        first,
        "",
        f"machine_status: {receipt['status']}",
        f"reason: {receipt['reason']}",
        f"case_count: {receipt['val_count']}",
        "",
        "| model_id | pathology | evaluated | gt_positive | mean_dice | mean_exact_hd | status |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in metrics:
        values = {k: "" if v is None else v for k, v in row.items()}
        lines.append(
            "| {model_id} | {pathology} | {case_count_evaluated} | {gt_positive_cases} | {mean_dice} | {mean_exact_hd} | {status} |".format(**values)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    config = load_yaml(args.config)
    split_path = REPO_ROOT / config["dataset"]["split_path"]
    cases = load_fold_val_cases(split_path, int(config["dataset"]["fold"]))
    if args.limit_cases is not None:
        cases = cases[: args.limit_cases]
    specs = model_specs(config, args)

    if args.dry_run:
        casewise: list[dict[str, Any]] = []
        geometry_rows = [
            {
                "model_id": spec["model_id"],
                "case_id": case_id,
                "status": "DRY_RUN_NOT_EVALUATED",
                "prediction_dir": str(spec["prediction_dir_resolved"]),
            }
            for spec in specs
            for case_id in cases
        ]
        label_rows = label_mapping_audit_rows()
        metrics = summarize(casewise, specs, cases)
        inference_receipt_path = args.result_root / "mosaic_inference_receipt.json"
        inference_status = None
        if inference_receipt_path.is_file():
            inference_status = json.loads(inference_receipt_path.read_text(encoding="utf-8")).get("status")
        if inference_status == "READY_TO_START_INFERENCE":
            status = "NEEDS_PREDICTIONS"
            reason = "native MoSAIC source, entrypoint, and weights are ready; predictions have not been generated"
        else:
            status = "NEEDS_MOSAIC_SOURCE"
            reason = "dry run only; native MoSAIC source/predictions not yet available"
    else:
        casewise, geometry_rows, label_rows = evaluate_predictions(config, cases, specs)
        metrics = summarize(casewise, specs, cases)
        all_models_complete = all(row["status"] == "PASS" for row in metrics)
        all_geometry_pass = bool(geometry_rows) and all(row.get("status") == "PASS" for row in geometry_rows)
        status = "VERIFIED_EVALUATION_COMPLETE" if all_models_complete and all_geometry_pass else "NEEDS_EVIDENCE"
        reason = "all declared model predictions evaluated" if status == "VERIFIED_EVALUATION_COMPLETE" else "one or more declared models lack predictions or geometry audit pass"

    receipt = protocol_receipt(config, result_status=status, reason=reason)
    receipt.update(
        {
            "config_path": str(args.config.relative_to(REPO_ROOT)) if args.config.is_absolute() else str(args.config),
            "result_root": str(args.result_root.relative_to(REPO_ROOT)) if args.result_root.is_absolute() else str(args.result_root),
            "dry_run": bool(args.dry_run),
            "evaluated_case_count": len(cases),
            "declared_models": [spec["model_id"] for spec in specs],
        }
    )
    write_json(args.result_root / "protocol_receipt.json", receipt)
    write_csv(args.result_root / "label_mapping_audit.csv", label_rows)
    write_csv(args.result_root / "geometry_audit.csv", geometry_rows)
    write_csv(args.result_root / "casewise_metrics.csv", casewise)
    write_csv(args.result_root / "metrics.csv", metrics)
    write_result_md(args.result_root / "result.md", receipt, metrics)
    return 0 if args.dry_run or status == "VERIFIED_EVALUATION_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
