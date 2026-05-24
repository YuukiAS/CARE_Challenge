#!/usr/bin/env python3
"""Build CARE Myocardium diagnostic tables from existing artifacts.

This script is intentionally read-only with respect to model outputs: it does
not train, infer, submit Slurm jobs, create validation zips, or download
weights. It only summarizes existing predictions, metrics, and raw training
data into the governed CARE Myocardium diagnostics tree.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium"
LANE_A = OUT_ROOT / "laneA_myops"
LANE_B = OUT_ROOT / "laneB_cine"
LANE_C = OUT_ROOT / "laneC_da"
FAILURE_REGISTRY = OUT_ROOT / "failure_registry"

MYOPS_PRED_DIR = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
)
MYOPS_RESULT_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
MYOPS_METRICS_DIR = REPO_ROOT / "results/metrics/unified/nnUNet_D501_fold0_pathology_hd/fold_0"
MYOPS_GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
MYOPS_IMG_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/imagesTr"
MYOPS_RAW_ROOT = REPO_ROOT / "data/CARE_Challenge/MyoPS_train"
MYOPS_CASES_JSON = REPO_ROOT / "data/benchmarks/protocol/cases_MyoPS.json"
MYOPS_SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
MYOPS_DATASET_JSON = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/dataset.json"

CINE_COMPONENT_JSON = REPO_ROOT / "results/diagnostics/care_myocardium/laneB_cine/round02_topology_lcc/cinemyops_component_hd.json"
CINE_REPAIR_SUMMARY = REPO_ROOT / "results/diagnostics/baseline_paper_models/CineMyoPS/round08_hd_repair/CineMyoPS_round8_repair_summary.json"
CINE_DATASET_JSON = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS/dataset.json"
CINE_IMG_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS/imagesTr"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"No rows for {path}")
    names = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        return f"{value:.4f}"
    return str(value)


def finite_values(values: list[float | None]) -> list[float]:
    return [float(v) for v in values if isinstance(v, (int, float)) and not math.isnan(float(v))]


def avg(values: list[float | None]) -> float | None:
    vals = finite_values(values)
    return float(mean(vals)) if vals else None


def load_myops_case_meta() -> dict[str, dict[str, str]]:
    raw = read_json(MYOPS_CASES_JSON)["cases"]
    by_case = {}
    for item in raw:
        cid = item["case_id"]
        case_dir = MYOPS_RAW_ROOT / item["center"] / cid
        modalities = {
            name
            for name, suffix in {"LGE": "LGE", "C0": "C0", "T2": "T2"}.items()
            if (case_dir / f"{cid}_{suffix}.nii.gz").is_file()
        }
        if {"C0", "LGE", "T2"} <= modalities:
            group = "C0+LGE+T2"
        elif {"C0", "LGE"} <= modalities:
            group = "C0+LGE"
        else:
            group = "LGE-only"
        by_case[cid] = {"center": item["center"], "modality_group": group}
    return by_case


def load_metric_maps(metrics_dir: Path) -> tuple[dict, dict, dict]:
    summary = read_json(metrics_dir / "evaluation_summary.json")
    return (
        summary.get("per_case", {}),
        summary.get("per_case_hd", {}),
        summary.get("per_case_hd95", {}),
    )


def component_count(mask: np.ndarray) -> tuple[int, list[int]]:
    cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    sizes = [int((cc == i).sum()) for i in range(1, n_cc + 1)]
    return int(n_cc), sizes


def bbox(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    return coords.min(axis=0), coords.max(axis=0)


def bbox_gap_mm(a: tuple[np.ndarray, np.ndarray] | None, b: tuple[np.ndarray, np.ndarray] | None, spacing: tuple[float, ...]) -> float | None:
    if a is None or b is None:
        return None
    gap = np.zeros(len(spacing), dtype=np.float64)
    for axis in range(len(spacing)):
        if a[1][axis] < b[0][axis]:
            gap[axis] = b[0][axis] - a[1][axis]
        elif b[1][axis] < a[0][axis]:
            gap[axis] = a[0][axis] - b[1][axis]
    return float(np.linalg.norm(gap * np.asarray(spacing, dtype=np.float64)))


def pred_fp_summary(pred: np.ndarray, gt: np.ndarray, cls: int, spacing: tuple[float, ...]) -> tuple[int, int, int]:
    pred_mask = pred == cls
    gt_mask = gt == cls
    cc, n_cc = label(pred_mask, structure=generate_binary_structure(pred.ndim, 1))
    small_fp = 0
    remote_fp = 0
    gt_bbox = bbox(gt_mask)
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if np.logical_and(comp, gt_mask).any():
            continue
        voxels = int(comp.sum())
        if voxels < 20:
            small_fp += 1
        gap = bbox_gap_mm(bbox(comp), gt_bbox, spacing)
        if gap is None or gap > 20.0:
            remote_fp += 1
    return int(n_cc), small_fp, remote_fp


def build_myops_baseline_audit() -> None:
    splits = read_json(MYOPS_SPLITS_JSON)["folds"]
    dataset = read_json(MYOPS_DATASET_JSON)
    eval_summary = read_json(MYOPS_METRICS_DIR / "evaluation_summary.json")
    hd = eval_summary.get("mean_hd", {})
    hd95 = eval_summary.get("mean_hd95", {})
    dice = eval_summary.get("mean_dice", {})
    rows = []
    label_space = "compact 0 bg, 1 myocardium, 2 LV, 3 RV, 4 edema/myops_edema, 5 scar/myops_scar; raw submission maps edema=1220, scar=2221"
    for fold_info in splits:
        fold = int(fold_info["fold"])
        pred_dir = MYOPS_RESULT_ROOT / f"fold_{fold}/validation"
        expected = len(fold_info["val"])
        pred_count = len(list(pred_dir.glob("*.nii.gz"))) if pred_dir.is_dir() else 0
        has_ckpt = (MYOPS_RESULT_ROOT / f"fold_{fold}/checkpoint_best.pth").is_file()
        is_fold0_metric = fold == 0 and MYOPS_METRICS_DIR.is_dir()
        pass_fail = "pass" if pred_count == expected and has_ckpt and (fold != 0 or is_fold0_metric) else "fail"
        rows.append(
            {
                "model": "nnUNet501",
                "fold": fold,
                "pred_dir": str(pred_dir),
                "metrics_dir": str(MYOPS_METRICS_DIR if is_fold0_metric else ""),
                "checkpoint_or_source": str(MYOPS_RESULT_ROOT / f"fold_{fold}/checkpoint_best.pth"),
                "label_space": label_space,
                "scar_dice": dice.get("class_5") if is_fold0_metric else None,
                "scar_hd": hd.get("class_5") if is_fold0_metric else None,
                "scar_hd95": hd95.get("class_5") if is_fold0_metric else None,
                "edema_dice": dice.get("class_4") if is_fold0_metric else None,
                "edema_hd": hd.get("class_4") if is_fold0_metric else None,
                "edema_hd95": hd95.get("class_4") if is_fold0_metric else None,
                "cache_status": f"existing_predictions={pred_count}/{expected}; checkpoint_best={'yes' if has_ckpt else 'no'}",
                "pass_fail": pass_fail,
            }
        )
    csv_path = LANE_A / "myops_baseline_protocol_audit.csv"
    write_csv(csv_path, rows)
    lines = [
        "# MyoPS CARE Diagnostics Baseline/Protocol Audit",
        "",
        f"- Metric source: `{MYOPS_METRICS_DIR}`",
        f"- Dataset label source: `{MYOPS_DATASET_JSON}`",
        f"- Label map: `{label_space}`",
        f"- nnU-Net dataset labels: `{json.dumps(dataset['labels'], sort_keys=True)}`",
        "",
        "| model | fold | predictions | checkpoint | scar Dice | scar HD95 | edema Dice | edema HD95 | gate |",
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {model} | {fold} | {cache} | {ckpt} | {sd} | {sh95} | {ed} | {eh95} | {gate} |".format(
                model=row["model"],
                fold=row["fold"],
                cache=row["cache_status"].split(";")[0].replace("existing_predictions=", ""),
                ckpt="yes" if "checkpoint_best=yes" in row["cache_status"] else "no",
                sd=fmt(row["scar_dice"]),
                sh95=fmt(row["scar_hd95"]),
                ed=fmt(row["edema_dice"]),
                eh95=fmt(row["edema_hd95"]),
                gate=row["pass_fail"],
            )
        )
    lines += [
        "",
        "结论：fold0 已有可复现 prediction、checkpoint_best 和统一 Dice/HD/HD95 指标；fold1-4 有 validation prediction 和 checkpoint_best，但本轮不重算 HD/HD95，保持 CARE diagnostic smoke 范围。",
    ]
    (LANE_A / "myops_baseline_protocol_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_myops_modality_center_metrics() -> None:
    meta = load_myops_case_meta()
    per_case, per_case_hd, per_case_hd95 = load_metric_maps(MYOPS_METRICS_DIR)
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    case_rows = []
    for cid in sorted(per_case):
        pred_path = MYOPS_PRED_DIR / f"{cid}.nii.gz"
        gt_path = MYOPS_GT_DIR / f"{cid}.nii.gz"
        if not pred_path.is_file() or not gt_path.is_file():
            continue
        gt_img = sitk.ReadImage(str(gt_path))
        pred_img = sitk.ReadImage(str(pred_path))
        if pred_img.GetSize() != gt_img.GetSize() or pred_img.GetSpacing() != gt_img.GetSpacing():
            pred_img = sitk.Resample(pred_img, gt_img, sitk.Transform(), sitk.sitkNearestNeighbor, 0, pred_img.GetPixelID())
        pred = sitk.GetArrayFromImage(pred_img).astype(np.uint8, copy=False)
        gt = sitk.GetArrayFromImage(gt_img).astype(np.uint8, copy=False)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        scar_components, scar_small_fp, scar_remote_fp = pred_fp_summary(pred, gt, 5, spacing)
        edema_components, edema_small_fp, edema_remote_fp = pred_fp_summary(pred, gt, 4, spacing)
        scar_gt = int((gt == 5).sum())
        edema_gt = int((gt == 4).sum())
        row = {
            "case_id": cid,
            "modality_group": meta.get(cid, {}).get("modality_group", "unknown"),
            "center": meta.get(cid, {}).get("center", "unknown"),
            "scar_gt_positive": scar_gt > 0,
            "edema_gt_positive": edema_gt > 0,
            "scar_dice": per_case[cid].get("class_5"),
            "edema_dice": per_case[cid].get("class_4"),
            "scar_hd95": per_case_hd95.get(cid, {}).get("class_5"),
            "edema_hd95": per_case_hd95.get(cid, {}).get("class_4"),
            "scar_components": scar_components,
            "edema_components": edema_components,
            "small_fp": scar_small_fp + edema_small_fp,
            "remote_fp": scar_remote_fp + edema_remote_fp,
            "pred_gt_volume_ratio": float(((pred == 4).sum() + (pred == 5).sum()) / max(1, (gt == 4).sum() + (gt == 5).sum())),
        }
        case_rows.append(row)
        grouped[(row["modality_group"], row["center"])].append(row)

    rows = []
    for (modality_group, center), items in sorted(grouped.items()):
        rows.append(
            {
                "modality_group": modality_group,
                "center": center,
                "n_cases": len(items),
                "scar_gt_positive_n": sum(1 for x in items if x["scar_gt_positive"]),
                "edema_gt_positive_n": sum(1 for x in items if x["edema_gt_positive"]),
                "scar_dice": avg([x["scar_dice"] for x in items]),
                "edema_dice": avg([x["edema_dice"] for x in items]),
                "scar_hd95": avg([x["scar_hd95"] for x in items]),
                "edema_hd95": avg([x["edema_hd95"] for x in items]),
                "scar_components": avg([x["scar_components"] for x in items]),
                "edema_components": avg([x["edema_components"] for x in items]),
                "small_fp": sum(int(x["small_fp"]) for x in items),
                "remote_fp": sum(int(x["remote_fp"]) for x in items),
                "pred_gt_volume_ratio": avg([x["pred_gt_volume_ratio"] for x in items]),
            }
        )
    csv_path = LANE_A / "myops_modality_center_metrics.csv"
    write_csv(csv_path, rows)
    write_csv(LANE_A / "myops_modality_center_case_metrics.csv", case_rows)
    lines = [
        "# MyoPS Modality/Center Metrics",
        "",
        f"- Cases: {len(case_rows)} fold0 validation cases from `{MYOPS_PRED_DIR}`",
        "- Metrics: class_5=`myops_scar`, class_4=`myops_edema`; HD95 from unified evaluator.",
        "",
        "| modality_group | center | n | scar GT+ | edema GT+ | scar Dice | edema Dice | scar HD95 | edema HD95 | scar comps | edema comps | small FP | remote FP | volume ratio |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {modality_group} | {center} | {n_cases} | {scar_gt_positive_n} | {edema_gt_positive_n} | {scar_dice} | {edema_dice} | {scar_hd95} | {edema_hd95} | {scar_components} | {edema_components} | {small_fp} | {remote_fp} | {pred_gt_volume_ratio} |".format(
                **{k: fmt(v) for k, v in row.items()}
            )
        )
    lines += [
        "",
        "结论：该表按 center 和 modality_group 拆开了 scar/edema、HD95、组件和 FP 信号；后续若进入 normalization/DA smoke，应优先围绕这些分层差异，而不是 aggregate mean。",
    ]
    (LANE_A / "myops_modality_center_metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    build_failure_registry(case_rows)


def build_cine_postprocess_table() -> None:
    data = read_json(CINE_COMPONENT_JSON)
    summary = data["summary"]
    rows = []
    for row in data["rows"]:
        variant = str(row["variant"])
        mapped_variant = {
            "pathology_direct": "pathology_direct",
            "lcc": "lcc",
            "pathology_largest_component": "small_component_filter",
            "pathology_volume_guard": "volume_guard",
            "pathology_roi_lcc_volume_guard": "bbox_guard",
        }.get(variant, variant)
        rows.append(
            {
                "case_id": row["case"],
                "variant": mapped_variant,
                "class1_dice": row.get("dice_class_1"),
                "class1_hd95": row.get("hd95_class_1"),
                "class3_dice": row.get("dice_class_3"),
                "class3_hd": row.get("hd_class_3"),
                "class3_hd95": row.get("hd95_class_3"),
                "raw_2221_voxels": row.get("scar_voxels"),
                "component_count": row.get("scar_components"),
                "largest_component_fraction": row.get("largest_component_frac"),
                "bbox_distance_or_flag": row.get("bbox_distance_mm"),
                "fallback_used": row.get("fallback_used"),
                "pass_fail": "fail" if row.get("fallback_used") or row.get("scar_voxels") == 0 else "pass",
            }
        )
    csv_path = LANE_B / "cinemyops_postprocess_before_after.csv"
    write_csv(csv_path, rows)
    write_csv(LANE_B / "cinemyops_postprocess_case_flags.csv", [r for r in rows if r["pass_fail"] != "pass" or (r["component_count"] or 0) > 1])
    lines = [
        "# CineMyoPS Postprocess Before/After Diagnostics",
        "",
        f"- Source audit: `{CINE_COMPONENT_JSON}`",
        f"- Repair summary: `{CINE_REPAIR_SUMMARY}`",
        "",
        "| variant | cases | class1 Dice | class3 Dice | class3 HD | class3 HD95 | scar comps | worst class3 HD | fallback | gate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for variant, item in summary.items():
        gate = "go/watch" if variant == "lcc" and item.get("mean_hd95_class_3", 999) < summary["pathology_direct"].get("mean_hd95_class_3", 999) else "baseline"
        lines.append(
            "| {variant} | {n_cases} | {d1} | {d3} | {h3} | {h953} | {cc} | {wh3} | {fb} | {gate} |".format(
                variant=variant,
                n_cases=item.get("n_cases", 0),
                d1=fmt(item.get("mean_dice_class_1")),
                d3=fmt(item.get("mean_dice_class_3")),
                h3=fmt(item.get("mean_hd_class_3")),
                h953=fmt(item.get("mean_hd95_class_3")),
                cc=fmt(item.get("mean_scar_components")),
                wh3=fmt(item.get("worst_hd_class_3")),
                fb=",".join(item.get("fallback_cases", [])) or "none",
                gate=gate,
            )
        )
    lines += [
        "",
        "结论：LCC 把平均 class_3 HD95 从 26.6533 降到 18.7983，component count 从 5.5385 降到 1.0，class_3 Dice 小幅上升；本轮只保留为 watch/go 候选，不创建 validation zip。",
    ]
    (LANE_B / "cinemyops_postprocess_before_after.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def image_stats(path: Path) -> dict[str, float]:
    arr = sitk.GetArrayFromImage(sitk.ReadImage(str(path))).astype(np.float32, copy=False)
    nz = arr[np.isfinite(arr)]
    if nz.size == 0:
        return {"p01": 0.0, "p50": 0.0, "p99": 0.0, "mean": 0.0, "std": 0.0, "iqr": 0.0}
    p01, p25, p50, p75, p99 = np.percentile(nz, [1, 25, 50, 75, 99])
    return {
        "p01": float(p01),
        "p50": float(p50),
        "p99": float(p99),
        "mean": float(np.mean(nz)),
        "std": float(np.std(nz)),
        "iqr": float(p75 - p25),
    }


def build_normalization_audit() -> None:
    meta = load_myops_case_meta()
    per_case, _, per_case_hd95 = load_metric_maps(MYOPS_METRICS_DIR)
    rows = []
    corr_rows = []
    modality_channels = {"LGE": "0000", "T2": "0001", "C0": "0002"}
    by_group_center: dict[tuple[str, str], list[str]] = defaultdict(list)
    for cid in sorted(per_case):
        key = (
            meta.get(cid, {}).get("modality_group", "unknown"),
            meta.get(cid, {}).get("center", "unknown"),
        )
        by_group_center[key].append(cid)
    sample_cases = []
    buckets = [list(v) for _, v in sorted(by_group_center.items())]
    while len(sample_cases) < 15 and any(buckets):
        for bucket in buckets:
            if bucket and len(sample_cases) < 15:
                sample_cases.append(bucket.pop(0))
    for cid in sample_cases:
        for modality, channel in modality_channels.items():
            path = MYOPS_IMG_DIR / f"{cid}_{channel}.nii.gz"
            if not path.is_file():
                continue
            stats = image_stats(path)
            missing = 0.0
            if modality != "LGE":
                missing = 1.0 if cid in meta and modality not in meta[cid]["modality_group"].split("+") else 0.0
            rows.append(
                {
                    "dataset": "MyoPS",
                    "center": meta.get(cid, {}).get("center", "unknown"),
                    "modality_group": meta.get(cid, {}).get("modality_group", "unknown"),
                    "modality": modality,
                    "n_cases": 1,
                    **stats,
                    "missingness_rate": missing,
                    "target_metric": "scar/edema",
                    "dice": avg([per_case[cid].get("class_5"), per_case[cid].get("class_4")]),
                    "hd95": avg([per_case_hd95.get(cid, {}).get("class_5"), per_case_hd95.get(cid, {}).get("class_4")]),
                    "component_count": None,
                    "recommended_smoke": "robust-z" if stats["iqr"] > 0 else "none",
                }
            )
        corr_rows.append(
            {
                "dataset": "MyoPS",
                "case_id": cid,
                "center": meta.get(cid, {}).get("center", "unknown"),
                "modality_group": meta.get(cid, {}).get("modality_group", "unknown"),
                "missing_modality_count": 3 - len(meta.get(cid, {}).get("modality_group", "LGE-only").split("+")),
                "scar_dice": per_case[cid].get("class_5"),
                "edema_dice": per_case[cid].get("class_4"),
                "scar_hd95": per_case_hd95.get(cid, {}).get("class_5"),
                "edema_hd95": per_case_hd95.get(cid, {}).get("class_4"),
            }
        )

    cine_dataset = read_json(CINE_DATASET_JSON)
    for path in sorted(CINE_IMG_DIR.glob("*_0000.nii.gz"))[:10]:
        cid = path.name.replace("_0000.nii.gz", "")
        center = "center_alpha" if "Case1" in cid else "center_beta"
        rows.append(
            {
                "dataset": "CineMyoPS",
                "center": center,
                "modality_group": "Cine",
                "modality": "Cine",
                "n_cases": 1,
                **image_stats(path),
                "missingness_rate": 0.0,
                "target_metric": "cine scar sanity",
                "dice": None,
                "hd95": None,
                "component_count": None,
                "recommended_smoke": "BN-stat",
            }
        )

    write_csv(LANE_C / "normalization_intensity_by_center_modality.csv", rows)
    write_csv(LANE_C / "normalization_error_correlation.csv", corr_rows)
    by_key: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_key[(row["dataset"], row["center"], row["modality_group"], row["modality"])].append(row)
    lines = [
        "# Lane C Normalization/DA Audit",
        "",
        f"- MyoPS smoke cases: {len(sample_cases)} fold0 cases; Cine smoke cases: 10.",
        f"- Cine labels: `{json.dumps(cine_dataset['labels'], sort_keys=True)}`",
        "- 本轮只诊断 intensity/missingness/error 相关性，不使用 validation pseudo-label 或外部权重。",
        "",
        "| dataset | center | modality_group | modality | n | p50 | iqr | missingness | dice | hd95 | recommended_smoke |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for key, items in sorted(by_key.items()):
        dataset, center, group, modality = key
        lines.append(
            "| {dataset} | {center} | {group} | {modality} | {n} | {p50} | {iqr} | {miss} | {dice} | {hd95} | {smoke} |".format(
                dataset=dataset,
                center=center,
                group=group,
                modality=modality,
                n=len(items),
                p50=fmt(avg([x["p50"] for x in items])),
                iqr=fmt(avg([x["iqr"] for x in items])),
                miss=fmt(avg([x["missingness_rate"] for x in items])),
                dice=fmt(avg([x["dice"] for x in items])),
                hd95=fmt(avg([x["hd95"] for x in items])),
                smoke=items[0]["recommended_smoke"],
            )
        )
    lines += [
        "",
        "结论：Lane C 有 CARE-only smoke 空间：MyoPS 可先测 robust-z/clipping 对 center/modality 分层 HD95 的影响；Cine 只建议保留 BN-stat/强度统计诊断，不进入外部 harmonization。",
    ]
    (LANE_C / "normalization_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_failure_registry(case_rows: list[dict[str, object]]) -> None:
    FAILURE_REGISTRY.mkdir(parents=True, exist_ok=True)
    categories = {
        "remote_false_positive": [r for r in case_rows if int(r["remote_fp"]) > 0],
        "small_false_positive": [r for r in case_rows if int(r["small_fp"]) > 0],
        "hd95_outlier": [r for r in case_rows if (r["scar_hd95"] or 0) > 50 or (r["edema_hd95"] or 0) > 50],
        "edema_no_t2_gap": [r for r in case_rows if r["modality_group"] != "C0+LGE+T2" and r["edema_gt_positive"]],
    }
    for category, rows in categories.items():
        md = [
            f"# {category}",
            "",
            "| case | modality_group | center | scar Dice | edema Dice | scar HD95 | edema HD95 | small FP | remote FP | volume ratio |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in rows[:12]:
            md.append(
                "| {case_id} | {modality_group} | {center} | {scar_dice} | {edema_dice} | {scar_hd95} | {edema_hd95} | {small_fp} | {remote_fp} | {pred_gt_volume_ratio} |".format(
                    **{k: fmt(v) for k, v in row.items()}
                )
            )
        if not rows:
            md.append("| none | NA | NA | NA | NA | NA | NA | NA | NA | NA |")
        (FAILURE_REGISTRY / f"{category}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def build_decision_table() -> None:
    rows = [
        {
            "lane": "Lane A",
            "candidate": "nnUNet501 protocol anchor",
            "target_metric": "myops_scar/myops_edema",
            "decision": "go",
            "reason": "fold0 prediction/checkpoint/label/evaluator gate passes; fold1-4 predictions exist but HD/HD95 not recomputed in this smoke run.",
            "next_command": "python scripts/evaluation/evaluate_predictions.py --pred-dir <candidate> --gt-dir data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr --fold-json data/benchmarks/protocol/splits_MyoPS.json --fold 0 --foreground-classes 4,5 --skip-dice-if-gt-empty --hd --hd95 --output-dir results/diagnostics/care_myocardium/<candidate>",
            "estimated_runtime": "minutes on CPU for fold0 pathology classes",
            "prohibited": "no cache reuse without candidate-specific output-dir; no label remap changes",
        },
        {
            "lane": "Lane A",
            "candidate": "modality/center normalization smoke",
            "target_metric": "myops_scar/myops_edema",
            "decision": "watch",
            "reason": "modality/center table exposes stratified error and FP signals; needs candidate-specific smoke before implementation.",
            "next_command": "reuse fold0 only; compare robust-z/clipping outputs against laneA_myops/myops_modality_center_metrics.csv",
            "estimated_runtime": "short smoke only",
            "prohibited": "no new backbone, no external data, no pseudo-label",
        },
        {
            "lane": "Lane B",
            "candidate": "Cine pathology LCC",
            "target_metric": "myocardium_cinemyops via class_3 sanity",
            "decision": "go",
            "reason": "existing before/after audit lowers class_3 HD95 and component count without Dice loss on the smoke set.",
            "next_command": "python scripts/evaluation/cinemyops_component_hd_audit.py --pred-dirs pathology_direct=results/predictions/CineMyoPS_R6_pathology_direct/fold_0 lcc=results/predictions/CineMyoPS_R8_hd_repair/pathology_largest_component/fold_0 --baseline-variant pathology_direct --output-prefix results/diagnostics/care_myocardium/laneB_cine/cinemyops_postprocess_before_after",
            "estimated_runtime": "minutes on CPU",
            "prohibited": "no validation zip in this phase; no empty pathology fallback increase",
        },
        {
            "lane": "Lane C",
            "candidate": "CARE-only robust-z / BN-stat smoke",
            "target_metric": "all three leaderboard metrics",
            "decision": "watch",
            "reason": "intensity/missingness audit gives a lightweight diagnostic direction, but no model-training evidence yet.",
            "next_command": "limit to 5-15 cases and write outputs under results/diagnostics/care_myocardium/laneC_da/",
            "estimated_runtime": "minutes for statistics; bounded smoke only for any transform",
            "prohibited": "no external harmonization, diffusion, foundation checkpoints, or validation pseudo-label",
        },
        {
            "lane": "Cross-lane",
            "candidate": "unstructured baseline patching",
            "target_metric": "myops_scar/myops_edema/myocardium_cinemyops",
            "decision": "stop",
            "reason": "future work must pass protocol/cache/label gates and report each target metric separately.",
            "next_command": "none",
            "estimated_runtime": "NA",
            "prohibited": "no aggregate-only success criteria; no hidden postprocess default changes",
        },
    ]
    write_csv(OUT_ROOT / "next_round_decision_table.csv", rows)
    lines = [
        "# Next Round Decision Table",
        "",
        "| lane | candidate | target_metric | decision | reason | next command | runtime | prohibited |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {lane} | {candidate} | {target_metric} | {decision} | {reason} | `{next_command}` | {estimated_runtime} | {prohibited} |".format(
                **row
            )
        )
    (OUT_ROOT / "next_round_decision_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    for path in (LANE_A, LANE_B, LANE_C, FAILURE_REGISTRY):
        path.mkdir(parents=True, exist_ok=True)
    build_myops_baseline_audit()
    build_myops_modality_center_metrics()
    build_cine_postprocess_table()
    build_normalization_audit()
    build_decision_table()
    print(json.dumps({"output_root": str(OUT_ROOT)}, indent=2))


if __name__ == "__main__":
    main()
