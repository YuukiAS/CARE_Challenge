#!/usr/bin/env python3
"""Lane B Round2 topology diagnostics for existing CineMyoPS predictions.

This script is deterministic and diagnostic-only. It does not train, run
inference, submit Slurm jobs, create validation zips, upload, or download
weights. Candidate postprocess variants are evaluated in memory and summarized
under results/diagnostics/phase0_phase1/laneB_cine/round2/.
"""

from __future__ import annotations

import argparse
import csv
import math
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneB_cine/round2"
FAILURE_REGISTRY = REPO_ROOT / "results/diagnostics/phase0_phase1/failure_registry"

DEFAULT_SOURCE_DIR = REPO_ROOT / "results/predictions/CineMyoPS_R6_pathology_direct/fold_0"
DEFAULT_GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS/labelsTr"
DEFAULT_LABELS_DIR = DEFAULT_GT_DIR
DEFAULT_SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_CineMyoPS.json"

COMPACT_TO_RAW = {0: 0, 1: 200, 2: 500, 3: 2221}
LEGAL_RAW_LABELS = {0, 200, 500, 2221}
SCAR = 3
MYOCARDIUM = 1
LV = 2


@dataclass(frozen=True)
class Component:
    component_id: int
    voxels: int
    mask: np.ndarray
    bbox_min: np.ndarray
    bbox_max: np.ndarray
    bbox_gap_mm: float | None
    center_distance_mm: float | None
    anatomy_overlap_ratio: float
    z_span: int


@dataclass(frozen=True)
class Thresholds:
    train_scar_volume_p95: float
    train_scar_volume_p99: float
    train_scar_anatomy_ratio_p95: float
    train_component_volume_p10: float
    train_bbox_gap_p95: float
    train_center_distance_p95: float
    fold0_pred_component_volume_p10: float
    fold0_pred_scar_volume_p95: float
    small_component_volume_threshold: float


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"No rows to write for {path}")
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


def read_array(path: Path) -> tuple[sitk.Image, np.ndarray]:
    image = sitk.ReadImage(str(path))
    return image, sitk.GetArrayFromImage(image).astype(np.uint8, copy=False)


def resample_array_to_reference(path: Path, reference: sitk.Image) -> np.ndarray:
    image = sitk.ReadImage(str(path))
    if image.GetSize() != reference.GetSize() or image.GetSpacing() != reference.GetSpacing() or image.GetDirection() != reference.GetDirection():
        image = sitk.Resample(image, reference, sitk.Transform(), sitk.sitkNearestNeighbor, 0, image.GetPixelID())
    return sitk.GetArrayFromImage(image).astype(np.uint8, copy=False)


def spacing_zyx(image: sitk.Image) -> tuple[float, ...]:
    return tuple(float(v) for v in image.GetSpacing()[::-1])


def load_fold_ids(splits_json: Path, fold: int, key: str) -> list[str]:
    data = read_json(splits_json)
    return sorted(data["folds"][fold][key])


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


def center_distance_mm(a: tuple[np.ndarray, np.ndarray] | None, b: tuple[np.ndarray, np.ndarray] | None, spacing: tuple[float, ...]) -> float | None:
    if a is None or b is None:
        return None
    ca = (a[0].astype(np.float64) + a[1].astype(np.float64)) / 2.0
    cb = (b[0].astype(np.float64) + b[1].astype(np.float64)) / 2.0
    return float(np.linalg.norm((ca - cb) * np.asarray(spacing, dtype=np.float64)))


def component_count(mask: np.ndarray) -> int:
    _, n_comp = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_comp)


def components_for(arr: np.ndarray, spacing: tuple[float, ...], anatomy_roi: np.ndarray) -> list[Component]:
    scar = arr == SCAR
    cc, n_comp = label(scar, structure=generate_binary_structure(scar.ndim, 1))
    anatomy_bbox = bbox(anatomy_roi)
    rows: list[Component] = []
    dilated_anatomy = binary_dilation(anatomy_roi, structure=generate_binary_structure(anatomy_roi.ndim, 1), iterations=1)
    for component_id in range(1, n_comp + 1):
        mask = cc == component_id
        comp_bbox = bbox(mask)
        if comp_bbox is None:
            continue
        voxels = int(mask.sum())
        overlap = float(np.logical_and(mask, dilated_anatomy).sum() / max(1, voxels))
        rows.append(
            Component(
                component_id=component_id,
                voxels=voxels,
                mask=mask,
                bbox_min=comp_bbox[0],
                bbox_max=comp_bbox[1],
                bbox_gap_mm=bbox_gap_mm(comp_bbox, anatomy_bbox, spacing),
                center_distance_mm=center_distance_mm(comp_bbox, anatomy_bbox, spacing),
                anatomy_overlap_ratio=overlap,
                z_span=int(comp_bbox[1][0] - comp_bbox[0][0] + 1),
            )
        )
    rows.sort(key=lambda item: item.voxels, reverse=True)
    return rows


def dice(pred: np.ndarray, gt: np.ndarray, class_id: int) -> float:
    p = pred == class_id
    g = gt == class_id
    denom = float(p.sum() + g.sum())
    if denom < 1e-8:
        return 1.0
    return float(2.0 * np.logical_and(p, g).sum(dtype=np.float64) / denom)


def surface_distances(pred_bin: np.ndarray, gt_bin: np.ndarray, spacing: tuple[float, ...]) -> np.ndarray:
    p = pred_bin.astype(bool)
    g = gt_bin.astype(bool)
    if not p.any() and not g.any():
        return np.array([0.0], dtype=np.float64)
    if not p.any() or not g.any():
        return np.array([np.inf], dtype=np.float64)
    struct = generate_binary_structure(p.ndim, 1)
    surf_p = p & ~binary_erosion(p, structure=struct)
    surf_g = g & ~binary_erosion(g, structure=struct)
    dt_g = distance_transform_edt(~surf_g, sampling=spacing)
    dt_p = distance_transform_edt(~surf_p, sampling=spacing)
    return np.concatenate([dt_g[surf_p].ravel(), dt_p[surf_g].ravel()]).astype(np.float64, copy=False)


def hd(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing: tuple[float, ...]) -> float | None:
    distances = surface_distances(pred == class_id, gt == class_id, spacing)
    if np.isinf(distances).any():
        return None
    return float(np.max(distances))


def hd95(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing: tuple[float, ...]) -> float | None:
    distances = surface_distances(pred == class_id, gt == class_id, spacing)
    if np.isinf(distances).any():
        return None
    return float(np.percentile(distances, 95))


def finite(values: list[float | None]) -> list[float]:
    return [float(v) for v in values if isinstance(v, (int, float)) and not math.isnan(float(v))]


def pct(values: list[float], q: float, default: float = 0.0) -> float:
    vals = finite(values)
    if not vals:
        return default
    return float(np.percentile(np.asarray(vals, dtype=np.float64), q))


def anatomy_mask(arr: np.ndarray) -> np.ndarray:
    return np.isin(arr, (MYOCARDIUM, LV))


def train_thresholds(labels_dir: Path, splits_json: Path, fold: int, source_dir: Path, case_ids: list[str]) -> Thresholds:
    train_ids = load_fold_ids(splits_json, fold, "train")
    train_scar_volumes: list[float] = []
    train_component_volumes: list[float] = []
    train_ratios: list[float] = []
    train_bbox_gaps: list[float] = []
    train_center_distances: list[float] = []
    for cid in train_ids:
        path = labels_dir / f"{cid}.nii.gz"
        if not path.is_file():
            continue
        image, arr = read_array(path)
        spacing = spacing_zyx(image)
        scar = arr == SCAR
        anatomy = anatomy_mask(arr)
        scar_volume = int(scar.sum())
        if scar_volume <= 0:
            continue
        train_scar_volumes.append(float(scar_volume))
        train_ratios.append(float(scar_volume / max(1, int(anatomy.sum()))))
        train_bbox_gaps.append(float(bbox_gap_mm(bbox(scar), bbox(anatomy), spacing) or 0.0))
        train_center_distances.append(float(center_distance_mm(bbox(scar), bbox(anatomy), spacing) or 0.0))
        for comp in components_for(arr, spacing, anatomy):
            train_component_volumes.append(float(comp.voxels))

    fold0_pred_component_volumes: list[float] = []
    fold0_pred_scar_volumes: list[float] = []
    for cid in case_ids:
        path = source_dir / f"{cid}.nii.gz"
        if not path.is_file():
            continue
        image, arr = read_array(path)
        spacing = spacing_zyx(image)
        fold0_pred_scar_volumes.append(float((arr == SCAR).sum()))
        for comp in components_for(arr, spacing, anatomy_mask(arr)):
            fold0_pred_component_volumes.append(float(comp.voxels))

    train_component_p10 = pct(train_component_volumes, 10, default=1.0)
    fold0_component_p10 = pct(fold0_pred_component_volumes, 10, default=train_component_p10)
    return Thresholds(
        train_scar_volume_p95=pct(train_scar_volumes, 95, default=0.0),
        train_scar_volume_p99=pct(train_scar_volumes, 99, default=0.0),
        train_scar_anatomy_ratio_p95=pct(train_ratios, 95, default=0.0),
        train_component_volume_p10=train_component_p10,
        train_bbox_gap_p95=pct(train_bbox_gaps, 95, default=0.0),
        train_center_distance_p95=pct(train_center_distances, 95, default=0.0),
        fold0_pred_component_volume_p10=fold0_component_p10,
        fold0_pred_scar_volume_p95=pct(fold0_pred_scar_volumes, 95, default=0.0),
        small_component_volume_threshold=float(min(train_component_p10, fold0_component_p10)),
    )


def keep_mask_for_variant(variant: str, arr: np.ndarray, comps: list[Component], thresholds: Thresholds, component_actions: list[dict[str, object]], cid: str) -> tuple[np.ndarray, bool, str]:
    scar = arr == SCAR
    if not comps:
        return scar, False, "no_scar_components"
    keep = np.zeros(scar.shape, dtype=bool)
    total_scar = int(scar.sum())
    largest_id = comps[0].component_id

    def remote(comp: Component) -> bool:
        bbox_outlier = (comp.bbox_gap_mm or 0.0) > thresholds.train_bbox_gap_p95
        center_outlier = (comp.center_distance_mm or 0.0) > thresholds.train_center_distance_p95
        return bool(bbox_outlier or center_outlier)

    for comp in comps:
        is_largest = comp.component_id == largest_id
        small = comp.voxels < thresholds.small_component_volume_threshold
        volume_outlier = total_scar > thresholds.train_scar_volume_p95
        low_anatomy_overlap = comp.anatomy_overlap_ratio <= 0.0
        keep_component = True
        reason = "kept"

        if variant in {"pathology_direct", "baseline"}:
            keep_component = True
            reason = "baseline"
        elif variant == "topology_lcc":
            keep_component = is_largest
            reason = "largest_component" if keep_component else "topology_lcc_removed"
        elif variant == "component_size_guard":
            keep_component = is_largest or not (small and (remote(comp) or low_anatomy_overlap))
            reason = "kept_largest_or_size_supported" if keep_component else "small_remote_component"
        elif variant == "myocardium_overlap_guard":
            keep_component = is_largest or comp.anatomy_overlap_ratio > 0.0 or not remote(comp)
            reason = "kept_anatomy_or_distance_supported" if keep_component else "low_overlap_with_anatomy_roi"
        elif variant == "bbox_distance_guard":
            keep_component = is_largest or not remote(comp)
            reason = "kept_largest_or_distance_supported" if keep_component else "bbox_or_center_distance_outlier"
        elif variant == "volume_guard":
            keep_component = is_largest or not (volume_outlier and small)
            reason = "kept_largest_or_volume_supported" if keep_component else "volume_outlier_small_component"
        elif variant == "combined_topology_guard":
            keep_component = is_largest or (
                (not small)
                and (comp.anatomy_overlap_ratio > 0.0 or not remote(comp))
                and total_scar <= thresholds.train_scar_volume_p99
            )
            reason = "kept_combined_plausibility" if keep_component else "combined_small_or_remote_or_volume_outlier"
        else:
            raise ValueError(f"Unknown variant: {variant}")

        component_actions.append(
            {
                "case_id": cid,
                "variant": variant,
                "component_id": comp.component_id,
                "voxels": comp.voxels,
                "anatomy_overlap_ratio": comp.anatomy_overlap_ratio,
                "bbox_gap_mm": comp.bbox_gap_mm,
                "center_distance_mm": comp.center_distance_mm,
                "z_span": comp.z_span,
                "kept": keep_component,
                "action_reason": reason,
                "small_threshold": thresholds.small_component_volume_threshold,
                "bbox_gap_threshold_p95": thresholds.train_bbox_gap_p95,
                "center_distance_threshold_p95": thresholds.train_center_distance_p95,
                "train_scar_volume_p95": thresholds.train_scar_volume_p95,
                "train_scar_volume_p99": thresholds.train_scar_volume_p99,
            }
        )
        if keep_component:
            keep |= comp.mask

    fallback = bool(scar.any() and not keep.any())
    if fallback:
        return scar, True, "fallback_original_would_delete_all_pathology"
    return keep, False, "ok"


def apply_variant_with_spacing(variant: str, arr: np.ndarray, spacing: tuple[float, ...], thresholds: Thresholds, component_actions: list[dict[str, object]], cid: str) -> tuple[np.ndarray, bool, str]:
    out = arr.copy()
    scar = arr == SCAR
    comps = components_for(arr, spacing, anatomy_mask(arr))
    keep, fallback, action_reason = keep_mask_for_variant(variant, arr, comps, thresholds, component_actions, cid)
    if not fallback:
        out[np.logical_and(scar, ~keep)] = 0
    return out, fallback, action_reason


def evaluate_variant(cid: str, variant: str, before: np.ndarray, after: np.ndarray, gt: np.ndarray, spacing: tuple[float, ...], fallback: bool, action_reason: str) -> dict[str, object]:
    scar = after == SCAR
    anatomy = anatomy_mask(after)
    comps = components_for(after, spacing, anatomy)
    largest = comps[0].voxels if comps else 0
    total = int(scar.sum())
    before_components = component_count(before == SCAR)
    after_components = component_count(scar)
    removed = np.logical_and(before == SCAR, after != SCAR)
    return {
        "case_id": cid,
        "variant": variant,
        "class_1_dice": dice(after, gt, MYOCARDIUM),
        "class_1_hd": hd(after, gt, MYOCARDIUM, spacing),
        "class_1_hd95": hd95(after, gt, MYOCARDIUM, spacing),
        "class_3_dice": dice(after, gt, SCAR),
        "class_3_hd": hd(after, gt, SCAR, spacing),
        "class_3_hd95": hd95(after, gt, SCAR, spacing),
        "before_component_count": before_components,
        "after_component_count": after_components,
        "removed_components": max(0, before_components - after_components),
        "removed_voxels": int(removed.sum()),
        "scar_voxels": total,
        "anatomy_voxels": int(anatomy.sum()),
        "scar_anatomy_ratio": float(total / max(1, int(anatomy.sum()))),
        "largest_component_fraction": float(largest / total) if total else 0.0,
        "bbox_gap_mm": bbox_gap_mm(bbox(scar), bbox(anatomy), spacing),
        "center_distance_mm": center_distance_mm(bbox(scar), bbox(anatomy), spacing),
        "fallback_used": fallback,
        "action_reason": action_reason,
        "pass_fail": "fail_empty_pathology" if total == 0 else "pass",
    }


def raw_label_arr(compact: np.ndarray) -> np.ndarray:
    raw = np.zeros_like(compact, dtype=np.uint16)
    for src, dst in COMPACT_TO_RAW.items():
        raw[compact == src] = dst
    return raw


def raw_qc_row(cid: str, variant: str, compact: np.ndarray, fallback: bool, action_reason: str, spacing: tuple[float, ...]) -> dict[str, object]:
    raw = raw_label_arr(compact)
    labels = {int(v): int(c) for v, c in zip(*np.unique(raw, return_counts=True))}
    scar = raw == 2221
    anatomy = np.isin(raw, (200, 500))
    comps = components_for(np.where(raw == 2221, SCAR, np.where(raw == 200, MYOCARDIUM, np.where(raw == 500, LV, 0))).astype(np.uint8), spacing, anatomy)
    largest = comps[0].voxels if comps else 0
    total = int(scar.sum())
    present_labels = set(labels)
    return {
        "case_id": cid,
        "variant": variant,
        "raw_labels": json.dumps(labels, sort_keys=True),
        "legal_raw_label_subset": present_labels <= LEGAL_RAW_LABELS,
        "pathology_non_empty": total > 0,
        "raw_2221_voxels": total,
        "raw_2221_components": len(comps),
        "largest_raw_2221_fraction": float(largest / total) if total else 0.0,
        "raw_2221_bbox_gap_mm": bbox_gap_mm(bbox(scar), bbox(anatomy), spacing),
        "raw_2221_center_distance_mm": center_distance_mm(bbox(scar), bbox(anatomy), spacing),
        "raw_scar_anatomy_ratio": float(total / max(1, int(anatomy.sum()))),
        "fallback_used": fallback,
        "action_reason": action_reason,
    }


def summarize(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["variant"])].append(row)
    summary: dict[str, dict[str, object]] = {}
    for variant, items in grouped.items():
        item: dict[str, object] = {"cases": len(items)}
        for key in (
            "class_1_dice",
            "class_1_hd95",
            "class_3_dice",
            "class_3_hd",
            "class_3_hd95",
            "after_component_count",
            "removed_voxels",
            "scar_voxels",
            "largest_component_fraction",
        ):
            vals = finite([r.get(key) for r in items])
            if vals:
                item[f"mean_{key}"] = float(mean(vals))
                item[f"median_{key}"] = float(median(vals))
        hd_vals = finite([r.get("class_3_hd") for r in items])
        if hd_vals:
            item["worst_class_3_hd"] = float(max(hd_vals))
        item["fallback_cases"] = [r["case_id"] for r in items if r.get("fallback_used")]
        item["empty_pathology_cases"] = [r["case_id"] for r in items if r.get("scar_voxels") == 0]
        summary[variant] = item
    return summary


def write_lcc_before_after(rows: list[dict[str, object]]) -> None:
    lcc_rows = [r for r in rows if r["variant"] in {"pathology_direct", "topology_lcc"}]
    write_csv(OUT_ROOT / "topology_lcc_before_after.csv", lcc_rows)
    summary = summarize(lcc_rows)
    lines = [
        "# Lane B Round2 topology_lcc before/after",
        "",
        "| variant | cases | class_1 Dice | class_3 Dice | class_3 HD | class_3 HD95 | scar comps | removed voxels | fallback | gate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for variant in ("pathology_direct", "topology_lcc"):
        item = summary[variant]
        fallback_cases = item.get("fallback_cases", [])
        gate = "baseline" if variant == "pathology_direct" else ("go/watch" if not fallback_cases else "fail_fallback")
        lines.append(
            "| {variant} | {cases} | {d1} | {d3} | {hd3} | {hd953} | {cc} | {rv} | {fallback} | {gate} |".format(
                variant=variant,
                cases=item["cases"],
                d1=fmt(item.get("mean_class_1_dice")),
                d3=fmt(item.get("mean_class_3_dice")),
                hd3=fmt(item.get("mean_class_3_hd")),
                hd953=fmt(item.get("mean_class_3_hd95")),
                cc=fmt(item.get("mean_after_component_count")),
                rv=fmt(item.get("mean_removed_voxels")),
                fallback=",".join(fallback_cases) if fallback_cases else "none",
                gate=gate,
            )
        )
    lines += [
        "",
        "结论：`topology_lcc` 是 formalized LCC；其价值是降低 class_3/raw 2221 topology 和 HD95 风险，不是 class_1 proxy 调参。",
    ]
    (OUT_ROOT / "topology_lcc_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_guard_grid(rows: list[dict[str, object]], component_actions: list[dict[str, object]], thresholds: Thresholds) -> None:
    write_csv(OUT_ROOT / "topology_guard_grid.csv", rows)
    write_csv(OUT_ROOT / "topology_component_actions.csv", component_actions)
    summary = summarize(rows)
    lines = [
        "# Lane B Round2 topology guard grid",
        "",
        "Thresholds are derived from CARE train/fold0 distributions, not handwritten constants.",
        "",
        "| threshold | value |",
        "| --- | ---: |",
        f"| train_scar_volume_p95 | {thresholds.train_scar_volume_p95:.4f} |",
        f"| train_scar_volume_p99 | {thresholds.train_scar_volume_p99:.4f} |",
        f"| train_scar_anatomy_ratio_p95 | {thresholds.train_scar_anatomy_ratio_p95:.6f} |",
        f"| train_component_volume_p10 | {thresholds.train_component_volume_p10:.4f} |",
        f"| fold0_pred_component_volume_p10 | {thresholds.fold0_pred_component_volume_p10:.4f} |",
        f"| small_component_volume_threshold | {thresholds.small_component_volume_threshold:.4f} |",
        f"| train_bbox_gap_p95 | {thresholds.train_bbox_gap_p95:.4f} |",
        f"| train_center_distance_p95 | {thresholds.train_center_distance_p95:.4f} |",
        "",
        "| variant | cases | class_3 Dice | class_3 HD95 | scar comps | removed voxels | fallback | gate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    baseline_hd95 = summary["pathology_direct"].get("mean_class_3_hd95")
    lcc_hd95 = summary["topology_lcc"].get("mean_class_3_hd95")
    for variant, item in summary.items():
        fallback_cases = item.get("fallback_cases", [])
        hd95_value = item.get("mean_class_3_hd95")
        gate = "baseline" if variant == "pathology_direct" else "watch"
        if variant != "pathology_direct" and isinstance(hd95_value, float) and isinstance(baseline_hd95, float):
            gate = "pass_vs_baseline" if hd95_value <= baseline_hd95 else "fail_hd95"
        if variant not in {"pathology_direct", "topology_lcc"} and isinstance(hd95_value, float) and isinstance(lcc_hd95, float) and hd95_value > lcc_hd95:
            gate = "keep_lcc_default"
        if fallback_cases:
            gate = "fail_fallback"
        lines.append(
            "| {variant} | {cases} | {d3} | {hd953} | {cc} | {rv} | {fallback} | {gate} |".format(
                variant=variant,
                cases=item["cases"],
                d3=fmt(item.get("mean_class_3_dice")),
                hd953=fmt(item.get("mean_class_3_hd95")),
                cc=fmt(item.get("mean_after_component_count")),
                rv=fmt(item.get("mean_removed_voxels")),
                fallback=",".join(fallback_cases) if fallback_cases else "none",
                gate=gate,
            )
        )
    lines += [
        "",
        "Decision rule: a complex guard is not promoted unless it beats plain `topology_lcc` on class_3 HD95/component behavior without fallback or scar deletion risk.",
        "Per-component keep/remove evidence is in `topology_component_actions.csv`.",
    ]
    (OUT_ROOT / "topology_guard_grid.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_ROOT / "topology_thresholds.json").write_text(json.dumps(thresholds.__dict__, indent=2), encoding="utf-8")


def write_raw_qc(rows: list[dict[str, object]]) -> None:
    write_csv(OUT_ROOT / "raw_label_topology_qc.csv", rows)


def write_failure_registry() -> None:
    FAILURE_REGISTRY.mkdir(parents=True, exist_ok=True)
    entries = {
        "cine_remote_pathology_island.md": (
            "# cine_remote_pathology_island\n\n"
            "Definition: class_3/raw `2221` component far from anatomy bbox or GT.\n\n"
            "Required evidence: component size, bbox gap, center distance, class_3 HD/HD95 contribution.\n"
        ),
        "cine_fragmented_pathology.md": (
            "# cine_fragmented_pathology\n\n"
            "Definition: more than one class_3 component with low largest-component fraction.\n\n"
            "Required evidence: component count, largest fraction, removed components, before/after HD95.\n"
        ),
        "cine_volume_outlier.md": (
            "# cine_volume_outlier\n\n"
            "Definition: scar volume above train p95/p99 or scar/anatomy ratio outlier.\n\n"
            "Required evidence: raw `2221` voxels, train percentile, scar/anatomy ratio.\n"
        ),
        "cine_anatomy_guard_risk.md": (
            "# cine_anatomy_guard_risk\n\n"
            "Definition: component outside anatomy ROI but plausible by GT or adjacent anatomy.\n\n"
            "Required evidence: anatomy overlap, bbox distance, Dice delta after deletion, fallback flag.\n"
        ),
        "cine_empty_repair_risk.md": (
            "# cine_empty_repair_risk\n\n"
            "Definition: repair deletes all pathology or would trigger fallback.\n\n"
            "Required evidence: fallback flag, raw label histogram, before/after class_3 Dice.\n"
        ),
        "hosted_local_metric_mismatch.md": (
            "# hosted_local_metric_mismatch\n\n"
            "Definition: local class_1 remains stable while class_3/raw topology changes materially.\n\n"
            "Required evidence: class_1 vs class_3 metrics and raw topology QA.\n"
        ),
    }
    for name, text in entries.items():
        path = FAILURE_REGISTRY / name
        if not path.exists():
            path.write_text(text, encoding="utf-8")


def main() -> None:
    global OUT_ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--gt-dir", type=Path, default=DEFAULT_GT_DIR)
    parser.add_argument("--labels-dir", type=Path, default=DEFAULT_LABELS_DIR)
    parser.add_argument("--splits-json", type=Path, default=DEFAULT_SPLITS_JSON)
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--output-root", type=Path, default=OUT_ROOT)
    args = parser.parse_args()

    OUT_ROOT = args.output_root
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    case_ids = load_fold_ids(args.splits_json, args.fold, "val")
    thresholds = train_thresholds(args.labels_dir, args.splits_json, args.fold, args.source_dir, case_ids)
    variants = [
        "pathology_direct",
        "topology_lcc",
        "component_size_guard",
        "myocardium_overlap_guard",
        "bbox_distance_guard",
        "volume_guard",
        "combined_topology_guard",
    ]

    metric_rows: list[dict[str, object]] = []
    raw_rows: list[dict[str, object]] = []
    component_actions: list[dict[str, object]] = []

    for cid in case_ids:
        pred_path = args.source_dir / f"{cid}.nii.gz"
        gt_path = args.gt_dir / f"{cid}.nii.gz"
        if not pred_path.is_file() or not gt_path.is_file():
            continue
        pred_img, pred = read_array(pred_path)
        gt = resample_array_to_reference(gt_path, pred_img)
        spacing = spacing_zyx(pred_img)
        for variant in variants:
            after, fallback, action_reason = apply_variant_with_spacing(variant, pred, spacing, thresholds, component_actions, cid)
            metric_rows.append(evaluate_variant(cid, variant, pred, after, gt, spacing, fallback, action_reason))
            raw_rows.append(raw_qc_row(cid, variant, after, fallback, action_reason, spacing))

    write_lcc_before_after(metric_rows)
    write_guard_grid(metric_rows, component_actions, thresholds)
    write_raw_qc(raw_rows)
    write_failure_registry()
    print(
        json.dumps(
            {
                "cases": len({row["case_id"] for row in metric_rows}),
                "variants": variants,
                "output_root": str(OUT_ROOT),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
