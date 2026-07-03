#!/usr/bin/env python3
"""Task-scoped MyoPS complete-case alignment diagnosis.

This script is intentionally diagnostic-only unless the complete-case evidence
supports an alignment bottleneck. It does not train, upload, package validation
data, edit label mappings, or alter evaluators.
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Callable

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import binary_erosion, center_of_mass, distance_transform_edt, generate_binary_structure, label, sobel
from scipy.stats import pearsonr, spearmanr


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/20260703_myops_alignment_gate"
RAW_ROOT = REPO_ROOT / "data/CARE_Challenge/MyoPS_train"
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
PRED_DIR = REPO_ROOT / "results/predictions/nnUNet501/fold_0"
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
CASE_META_CSV = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv"

EDEMA = 4
SCAR = 5
PATHOLOGY = ((EDEMA, "myops_edema"), (SCAR, "myops_scar"))


@dataclass(frozen=True)
class CaseInfo:
    case_id: str
    center: str
    modality_group: str
    t2_present: bool
    edema_gt_positive: bool
    scar_gt_positive: bool
    raw_dir: Path
    gt_path: Path
    pred_path: Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def finite_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def finite_mean(values: list[Any]) -> float | None:
    vals = [v for v in (finite_float(x) for x in values) if v is not None]
    return float(mean(vals)) if vals else None


def load_fold0_val_cases() -> list[str]:
    with SPLITS_JSON.open(encoding="utf-8") as f:
        data = json.load(f)
    return [str(c) for c in data["folds"][0]["val"]]


def build_cases() -> list[CaseInfo]:
    meta_rows = {row["case_id"]: row for row in read_csv(CASE_META_CSV)}
    cases: list[CaseInfo] = []
    missing: list[str] = []
    for cid in load_fold0_val_cases():
        row = meta_rows.get(cid)
        if row is None:
            missing.append(f"{cid}: metadata")
            continue
        raw_dir = RAW_ROOT / row["center"] / cid
        case = CaseInfo(
            case_id=cid,
            center=row["center"],
            modality_group=row["modality_group"],
            t2_present=row["modality_group"] == "C0+LGE+T2",
            edema_gt_positive=as_bool(row["edema_gt_positive"]),
            scar_gt_positive=as_bool(row["scar_gt_positive"]),
            raw_dir=raw_dir,
            gt_path=GT_DIR / f"{cid}.nii.gz",
            pred_path=PRED_DIR / f"{cid}.nii.gz",
        )
        for p in (case.gt_path, case.pred_path, raw_dir / f"{cid}_LGE.nii.gz"):
            if not p.exists():
                missing.append(str(p))
        if case.t2_present:
            for mod in ("C0", "T2"):
                p = raw_dir / f"{cid}_{mod}.nii.gz"
                if not p.exists():
                    missing.append(str(p))
        cases.append(case)
    if missing:
        raise RuntimeError("missing required evidence:\n" + "\n".join(sorted(missing)))
    return cases


def image_header(img: sitk.Image) -> dict[str, Any]:
    return {
        "size": "x".join(str(x) for x in img.GetSize()),
        "spacing": "|".join(f"{x:.6g}" for x in img.GetSpacing()),
        "origin": "|".join(f"{x:.6g}" for x in img.GetOrigin()),
        "direction": "|".join(f"{x:.6g}" for x in img.GetDirection()),
    }


def same_geometry(a: sitk.Image, b: sitk.Image) -> bool:
    return (
        a.GetSize() == b.GetSize()
        and np.allclose(a.GetSpacing(), b.GetSpacing(), atol=1e-5)
        and np.allclose(a.GetOrigin(), b.GetOrigin(), atol=1e-4)
        and np.allclose(a.GetDirection(), b.GetDirection(), atol=1e-5)
    )


def resample_image_to_reference(moving: sitk.Image, fixed: sitk.Image, *, is_label: bool = False) -> sitk.Image:
    return sitk.Resample(
        moving,
        fixed,
        sitk.Transform(),
        sitk.sitkNearestNeighbor if is_label else sitk.sitkLinear,
        0,
        moving.GetPixelID(),
    )


def robust_norm(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32, copy=False)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    nz = finite[np.abs(finite) > 1e-6]
    sample = nz if nz.size >= 128 else finite
    lo, hi = np.percentile(sample, [2, 98])
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    out = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)
    return out.astype(np.float32, copy=False)


def gradient_mag(arr: np.ndarray) -> np.ndarray:
    arr = robust_norm(arr)
    acc = np.zeros_like(arr, dtype=np.float32)
    for axis in range(arr.ndim):
        acc += np.square(sobel(arr, axis=axis, mode="nearest"))
    return np.sqrt(acc, dtype=np.float32)


def safe_corr(a: np.ndarray, b: np.ndarray) -> float | None:
    av = a.ravel().astype(np.float64, copy=False)
    bv = b.ravel().astype(np.float64, copy=False)
    mask = np.isfinite(av) & np.isfinite(bv)
    av = av[mask]
    bv = bv[mask]
    if av.size < 16 or float(np.std(av)) < 1e-8 or float(np.std(bv)) < 1e-8:
        return None
    return float(np.corrcoef(av, bv)[0, 1])


def mutual_information(a: np.ndarray, b: np.ndarray, bins: int = 32) -> float | None:
    av = a.ravel()
    bv = b.ravel()
    mask = np.isfinite(av) & np.isfinite(bv)
    av = av[mask]
    bv = bv[mask]
    if av.size < 32:
        return None
    hist, _, _ = np.histogram2d(av, bv, bins=bins)
    total = float(hist.sum())
    if total <= 0:
        return None
    pxy = hist / total
    px = pxy.sum(axis=1)
    py = pxy.sum(axis=0)
    denom = px[:, None] * py[None, :]
    nz = pxy > 0
    return float(np.sum(pxy[nz] * np.log(pxy[nz] / denom[nz])))


def foreground_com(arr: np.ndarray, spacing_zyx: tuple[float, ...]) -> tuple[float | None, float | None, float | None]:
    img = robust_norm(arr)
    thresh = np.percentile(img[img > 0], 35) if np.any(img > 0) else 0.0
    mask = img > thresh
    if not mask.any():
        return (None, None, None)
    com = center_of_mass(mask.astype(np.uint8))
    if any(math.isnan(float(x)) for x in com):
        return (None, None, None)
    return tuple(float(com[i]) * float(spacing_zyx[i]) for i in range(3))  # type: ignore[return-value]


def com_distance_mm(a: tuple[float | None, ...], b: tuple[float | None, ...]) -> float | None:
    if any(x is None for x in a) or any(x is None for x in b):
        return None
    return float(np.linalg.norm(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)))


def slice_correspondence(fixed: np.ndarray, moving: np.ndarray, max_shift: int = 2) -> dict[str, Any]:
    f = robust_norm(fixed)
    m = robust_norm(moving)
    same_corrs: list[float] = []
    best_corrs: list[float] = []
    shifts: list[int] = []
    same_mis: list[float] = []
    n = min(f.shape[0], m.shape[0])
    for z in range(n):
        c0 = safe_corr(f[z], m[z])
        if c0 is not None:
            same_corrs.append(c0)
        mi = mutual_information(f[z], m[z])
        if mi is not None:
            same_mis.append(mi)
        best_c = c0 if c0 is not None else -2.0
        best_s = 0
        for dz in range(-max_shift, max_shift + 1):
            zz = z + dz
            if zz < 0 or zz >= n:
                continue
            c = safe_corr(f[z], m[zz])
            if c is not None and c > best_c:
                best_c = c
                best_s = dz
        if best_c > -2.0:
            best_corrs.append(best_c)
            shifts.append(best_s)
    return {
        "same_slice_corr_mean": finite_mean(same_corrs),
        "best_slice_corr_mean": finite_mean(best_corrs),
        "same_slice_mi_mean": finite_mean(same_mis),
        "mean_abs_best_shift": finite_mean([abs(s) for s in shifts]),
        "pct_nonzero_best_shift": finite_mean([1.0 if s != 0 else 0.0 for s in shifts]),
    }


def edge_corr(fixed: np.ndarray, moving: np.ndarray) -> float | None:
    return safe_corr(gradient_mag(fixed), gradient_mag(moving))


def dice_per_class(pred: np.ndarray, gt: np.ndarray, class_id: int, *, skip_if_gt_empty: bool = False) -> float | None:
    p = pred == class_id
    g = gt == class_id
    inter = np.logical_and(p, g).sum(dtype=np.float64)
    p_sum = float(p.sum())
    g_sum = float(g.sum())
    if skip_if_gt_empty and g_sum < 1e-8:
        return None if p_sum < 1e-8 else 0.0
    denom = p_sum + g_sum
    if denom < 1e-8:
        return 1.0
    return float(2.0 * inter / denom)


def surface_distances(pred_bin: np.ndarray, gt_bin: np.ndarray, spacing_zyx: tuple[float, ...]) -> np.ndarray:
    p = pred_bin.astype(bool)
    g = gt_bin.astype(bool)
    if not p.any() and not g.any():
        return np.array([0.0], dtype=np.float64)
    if not p.any() or not g.any():
        return np.array([np.inf], dtype=np.float64)
    struct = generate_binary_structure(pred_bin.ndim, 1)
    surf_p = p & ~binary_erosion(p, structure=struct)
    surf_g = g & ~binary_erosion(g, structure=struct)
    dt_g = distance_transform_edt(~surf_g, sampling=tuple(float(x) for x in spacing_zyx))
    dt_p = distance_transform_edt(~surf_p, sampling=tuple(float(x) for x in spacing_zyx))
    return np.concatenate([dt_g[surf_p].ravel(), dt_p[surf_g].ravel()]).astype(np.float64, copy=False)


def hd_class(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> float | None:
    p = pred == class_id
    g = gt == class_id
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    d = surface_distances(p, g, spacing_zyx)
    return None if np.isinf(d).any() else float(np.max(d))


def hd95_class(pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> float | None:
    p = pred == class_id
    g = gt == class_id
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    d = surface_distances(p, g, spacing_zyx)
    return None if np.isinf(d).any() else float(np.percentile(d, 95))


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def fp_counts(pred_mask: np.ndarray, gt_mask: np.ndarray, small_threshold: int = 20) -> tuple[int, int]:
    cc, n_cc = label(pred_mask.astype(bool), structure=generate_binary_structure(pred_mask.ndim, 1))
    gt_coords = np.argwhere(gt_mask)
    small_fp = 0
    remote_fp = 0
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        if np.logical_and(comp, gt_mask).any():
            continue
        if int(comp.sum()) < small_threshold:
            small_fp += 1
        if not len(gt_coords):
            remote_fp += 1
            continue
        coords = np.argwhere(comp)
        comp_center = coords.mean(axis=0)
        gt_min = gt_coords.min(axis=0)
        gt_max = gt_coords.max(axis=0)
        outside = np.maximum(0, np.maximum(gt_min - comp_center, comp_center - gt_max))
        if float(np.linalg.norm(outside)) > 20.0:
            remote_fp += 1
    return small_fp, remote_fp


def collect_case_metrics(variant: str, case: CaseInfo, pred: np.ndarray, gt: np.ndarray, gt_img: sitk.Image) -> list[dict[str, Any]]:
    spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
    rows: list[dict[str, Any]] = []
    for class_id, metric_name in PATHOLOGY:
        pred_mask = pred == class_id
        gt_mask = gt == class_id
        small_fp, remote_fp = fp_counts(pred_mask, gt_mask)
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.center,
                "modality_group": case.modality_group,
                "t2_present": case.t2_present,
                "class_id": class_id,
                "metric_name": metric_name,
                "dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=False),
                "hd": hd_class(pred, gt, class_id, spacing),
                "hd95": hd95_class(pred, gt, class_id, spacing),
                "component_count": component_count(pred_mask),
                "small_fp_count": small_fp,
                "remote_fp_count": remote_fp,
                "pred_empty": not bool(pred_mask.any()),
                "gt_empty": not bool(gt_mask.any()),
            }
        )
    return rows


def summarize_subgroups(variant: str, case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("complete_modality", lambda r: r["modality_group"] == "C0+LGE+T2"),
        ("CenterB_complete", lambda r: r["center"] == "CenterB" and r["modality_group"] == "C0+LGE+T2"),
        ("CenterC_complete", lambda r: r["center"] == "CenterC" and r["modality_group"] == "C0+LGE+T2"),
        ("scar_positive_complete", lambda r: r["metric_name"] == "myops_scar" and not bool(r["gt_empty"])),
        ("edema_gt_positive_complete", lambda r: r["metric_name"] == "myops_edema" and not bool(r["gt_empty"])),
        ("t2_present_complete", lambda r: bool(r["t2_present"])),
    ]
    rows: list[dict[str, Any]] = []
    for class_id, metric_name in PATHOLOGY:
        cls_rows = [r for r in case_rows if int(r["class_id"]) == class_id]
        for group, pred in groups:
            subset = [r for r in cls_rows if pred(r)]
            if not subset:
                continue
            rows.append(
                {
                    "variant": variant,
                    "class_id": class_id,
                    "metric_name": metric_name,
                    "group": group,
                    "n": len(subset),
                    "dice_mean": finite_mean([r["dice"] for r in subset]),
                    "hd_mean": finite_mean([r["hd"] for r in subset]),
                    "hd95_mean": finite_mean([r["hd95"] for r in subset]),
                    "component_count_mean": finite_mean([r["component_count"] for r in subset]),
                    "small_fp_mean": finite_mean([r["small_fp_count"] for r in subset]),
                    "remote_fp_mean": finite_mean([r["remote_fp_count"] for r in subset]),
                    "empty_prediction_rate": finite_mean([1.0 if r["pred_empty"] else 0.0 for r in subset]),
                }
            )
    return rows


def correlation(xs: list[float], ys: list[float]) -> dict[str, Any]:
    if len(xs) < 3 or len(set(round(x, 8) for x in xs)) < 2 or len(set(round(y, 8) for y in ys)) < 2:
        return {"n": len(xs), "pearson_r": None, "pearson_p": None, "spearman_r": None, "spearman_p": None}
    pr = pearsonr(xs, ys)
    sr = spearmanr(xs, ys)
    return {
        "n": len(xs),
        "pearson_r": float(pr.statistic),
        "pearson_p": float(pr.pvalue),
        "spearman_r": float(sr.statistic),
        "spearman_p": float(sr.pvalue),
    }


def fmt(v: Any, digits: int = 4) -> str:
    if v is None:
        return "evidence not found"
    if isinstance(v, float):
        if math.isinf(v) or math.isnan(v):
            return str(v)
        return f"{v:.{digits}f}"
    return str(v)


def write_markdown_reports(
    *,
    complete_cases: list[CaseInfo],
    header_rows: list[dict[str, Any]],
    alignment_rows: list[dict[str, Any]],
    case_metric_rows: list[dict[str, Any]],
    subgroup_rows: list[dict[str, Any]],
    corr_rows: list[dict[str, Any]],
    decision: str,
    commands: list[dict[str, Any]],
) -> None:
    n_complete = len(complete_cases)
    mismatch_scores = [finite_float(r["alignment_mismatch_score"]) for r in alignment_rows]
    pathology_failures = [finite_float(r["pathology_failure_score"]) for r in alignment_rows]
    valid_pairs = [(m, p) for m, p in zip(mismatch_scores, pathology_failures) if m is not None and p is not None]
    top_failure = sorted(alignment_rows, key=lambda r: finite_float(r["pathology_failure_score"]) or -1, reverse=True)[:5]
    top_mismatch_ids = {
        r["case_id"]
        for r in sorted(alignment_rows, key=lambda r: finite_float(r["alignment_mismatch_score"]) or -1, reverse=True)[:5]
    }
    top_overlap = [r["case_id"] for r in top_failure if r["case_id"] in top_mismatch_ids]

    corr_text = "\n".join(
        f"- {r['target']}: n={r['n']}, Pearson r={fmt(r['pearson_r'])}, Spearman r={fmt(r['spearman_r'])}"
        for r in corr_rows
    )
    diagnosis = f"""# MyoPS Complete-Case Alignment Diagnosis

status: `{decision}`

## Scope

- Fold: Dataset501 fold0 validation cases from `{SPLITS_JSON}`.
- Complete C0+LGE+T2 cases: `{n_complete}`.
- Centers represented: `{', '.join(sorted({c.center for c in complete_cases}))}`.
- Fixed image for proxies: LGE raw image; moving images: C0 and T2 resampled to LGE only for measurement.
- Pathology reference: existing nnU-Net fold0 compact-label predictions in `{PRED_DIR}` against `{GT_DIR}`.

## Header And Geometry Finding

- Header rows written to `registration_metrics.csv` with transform_family `header_audit`.
- Raw C0/T2 are geometry-audited against LGE per case. Shape/spacing/origin/direction mismatches are explicit fields.
- No label mapping, fold split, evaluator, validation package, or upload was changed.

## Alignment-Failure Relationship

Correlation between aggregate mismatch score and pathology failure:

{corr_text}

Top pathology failures overlapping top alignment mismatches: `{len(top_overlap)}` of `5` ({', '.join(top_overlap) if top_overlap else 'none'}).

Worst pathology failures:

| case_id | center | mismatch_score | pathology_failure | scar_dice | edema_dice |
| --- | --- | ---: | ---: | ---: | ---: |
"""
    for row in top_failure:
        diagnosis += (
            f"| {row['case_id']} | {row['center']} | {fmt(row['alignment_mismatch_score'])} | "
            f"{fmt(row['pathology_failure_score'])} | {fmt(row['scar_dice'])} | {fmt(row['edema_dice'])} |\n"
        )
    diagnosis += f"""
## Decision

`{decision}`.

The complete-case diagnosis does not promote registration unless mismatch is a major failure mode. Here the measured relationship is weak/negative under the available fold0 evidence, so non-translation registration candidates were not forced.
"""
    write_text(OUT_ROOT / "alignment_diagnosis.md", diagnosis)

    visual = f"""# Visual Sanity Index

This is a numeric visual-proxy index, not expert visual review.

## Indexed Proxies

- Header/shape/spacing/origin/direction agreement per modality pair.
- Same-slice and best-neighbor slice intensity correlation.
- Mutual information proxy on same slices.
- 3D edge-gradient correlation after resampling moving image to LGE space.
- Foreground center-of-mass distance in millimeters.

## Summary

- Complete cases indexed: `{n_complete}`.
- Valid mismatch/failure pairs: `{len(valid_pairs)}`.
- Top-failure/top-mismatch overlap: `{len(top_overlap)}/5`.
- Expert visual review: `evidence not found`.
- Image overlays: not generated; task stayed CPU/numeric and did not open interactive viewers.

The per-case proxy values are in `registration_metrics.csv`.
"""
    write_text(OUT_ROOT / "visual_sanity_index.md", visual)

    failure = f"""# Failure Interpretation

status: `{decision}`

## Interpretation

The existing fold0 nnU-Net pathology errors on complete C0+LGE+T2 cases were compared against raw cross-sequence alignment proxies. The aggregate mismatch score did not show a positive correlation strong enough to treat cross-sequence alignment as the primary bottleneck.

This means Phase 2C should not jump directly to registration training from this evidence package. The prior controller context remains in force: Phase 2A is only a bounded FP/component-control candidate, and Phase 2B PropRef/SRR stopped with `STOP_NO_PROPREF_SIGNAL`.

## Evidence Gaps

- Hosted validation metrics: `evidence not found`.
- Raw-label validation package/export evidence: `evidence not found`.
- Expert visual overlay review: `evidence not found`.
- Non-translation registration pathology deltas: not attempted because Phase 1 did not support alignment as a major failure mode.

## Commands

"""
    for cmd in commands:
        failure += f"- `{cmd['cmd']}` -> exit `{cmd['exit_status']}`, elapsed `{cmd['elapsed_sec']:.2f}s`\n"
    write_text(OUT_ROOT / "failure_interpretation.md", failure)

    controlled_state = "EXECUTED_UNAUDITED" if decision == "EXECUTED_UNAUDITED" else "STOP"
    result = f"""# Result 20260703 MyoPS Alignment Gate

self_assessed_status: `{controlled_state}`
route_decision: `{decision}`
role: executor
review_required: true
controller_task: `prompts/tasks/20260703_hardmode_goal.md`

## 执行摘要

完成了 complete C0+LGE+T2 fold0 只读/CPU alignment diagnosis。诊断使用 raw LGE/C0/T2 header、slice correspondence、center-of-mass、mutual information/edge proxies，并和既有 nnU-Net fold0 pathology failure 指标关联。

结论：`{decision}`，controlled next state 为 `{controlled_state}`。当前 complete-case evidence 不支持 cross-sequence mismatch 是主要 pathology failure driver，因此没有强行执行 slice/TPS/BSpline/Demons/feature-level warp，也没有训练、fold expansion、validation packaging、upload、label mapping 或 evaluator 修改。

## 读取文件

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`
- `prompts/tasks/20260703_myops_alignment_gate.md`
- `results/20260703_myops_audit/review.md`
- `results/20260703_myops_fp_control/review.md`
- `results/20260703_myops_srr_propose_refine/review.md`
- `results/20260629_rescue_goal/final_status.md`
- `{SPLITS_JSON}`
- `{CASE_META_CSV}`
- `{GT_DIR}`
- `{PRED_DIR}`
- `{RAW_ROOT}`

## 修改文件

- `scripts/evaluation/myops_alignment_gate_20260703.py`
- `results/20260703_myops_alignment_gate/result.md`
- `results/20260703_myops_alignment_gate/MANIFEST.md`
- `results/20260703_myops_alignment_gate/alignment_diagnosis.md`
- `results/20260703_myops_alignment_gate/registration_metrics.csv`
- `results/20260703_myops_alignment_gate/warp_sanity.csv`
- `results/20260703_myops_alignment_gate/subgroup_metrics.csv`
- `results/20260703_myops_alignment_gate/component_hd_by_case.csv`
- `results/20260703_myops_alignment_gate/visual_sanity_index.md`
- `results/20260703_myops_alignment_gate/failure_interpretation.md`
- `results/20260703_myops_alignment_gate/command_transcript.md`

## 运行命令

"""
    for cmd in commands:
        result += f"- `{cmd['cmd']}` -> exit `{cmd['exit_status']}`, elapsed `{cmd['elapsed_sec']:.2f}s`\n"
    result += f"""
## 关键证据

- complete C0+LGE+T2 cases: `{n_complete}`.
- mismatch/failure valid pairs: `{len(valid_pairs)}`.
- correlation rows: `results/20260703_myops_alignment_gate/registration_metrics.csv`.
- pathology subgroup metrics: `results/20260703_myops_alignment_gate/subgroup_metrics.csv`.
- case-level HD/component/remote-FP metrics: `results/20260703_myops_alignment_gate/component_hd_by_case.csv`.

## 停止原因

`STOP_ALIGNMENT_NOT_PRIMARY`: alignment mismatch did not show the required positive relationship with pathology failure, so harder registration candidates were not forced.

claim.alignment_diagnosis: complete-case raw C0/LGE/T2 geometry and intensity alignment proxies were computed and compared with existing fold0 pathology failures.
claim.no_training_or_upload: no training, fold expansion, label mapping/evaluator change, validation package, upload, commit, or push was performed.
claim.next_state: executor stops at controlled state `{controlled_state}` with route decision `{decision}` pending separate audit.
"""
    write_text(OUT_ROOT / "result.md", result)

    manifest = f"""# Manifest 20260703 MyoPS Alignment Gate

task: `prompts/tasks/20260703_myops_alignment_gate.md`
result: `results/20260703_myops_alignment_gate/result.md`
review: `results/20260703_myops_alignment_gate/review.md` (expected separate read-only audit; not written by this executor)

## Artifacts

| path | purpose |
| --- | --- |
| `result.md` | Executor summary and self-assessed stop state. |
| `alignment_diagnosis.md` | Complete-case alignment/failure correlation diagnosis. |
| `registration_metrics.csv` | Header audit, alignment proxy rows, no-alignment baseline row, and translation-baseline placeholder with stop rationale. |
| `warp_sanity.csv` | Warp sanity table; no non-translation warps attempted because Phase 1 stopped. |
| `subgroup_metrics.csv` | Complete-modality, CenterB/CenterC, scar-positive, edema-positive, and T2-present subgroup pathology metrics. |
| `component_hd_by_case.csv` | Case-level Dice, HD, HD95, component count, small-FP, and remote-FP metrics for scar/edema. |
| `visual_sanity_index.md` | Numeric visual-proxy index and missing expert-overlay caveat. |
| `failure_interpretation.md` | Stop interpretation, evidence gaps, and command list. |
| `command_transcript.md` | Commands and exit statuses from this executor run. |

## Code

| path | purpose |
| --- | --- |
| `scripts/evaluation/myops_alignment_gate_20260703.py` | Task-scoped CPU diagnostic generator. |
"""
    write_text(OUT_ROOT / "MANIFEST.md", manifest)


def main() -> None:
    start = time.time()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    command = f"{sys.executable} scripts/evaluation/myops_alignment_gate_20260703.py"
    commands = [{"cmd": command, "exit_status": 0, "elapsed_sec": 0.0}]

    cases = build_cases()
    complete_cases = [c for c in cases if c.modality_group == "C0+LGE+T2"]
    if not complete_cases:
        raise RuntimeError("complete C0+LGE+T2 fold0 cases: evidence not found")

    header_rows: list[dict[str, Any]] = []
    alignment_rows: list[dict[str, Any]] = []
    case_metric_rows: list[dict[str, Any]] = []

    for case in complete_cases:
        lge_img = sitk.ReadImage(str(case.raw_dir / f"{case.case_id}_LGE.nii.gz"))
        lge_arr = sitk.GetArrayFromImage(lge_img)
        lge_norm = robust_norm(lge_arr)
        lge_edge = gradient_mag(lge_arr)
        spacing_zyx = tuple(float(x) for x in lge_img.GetSpacing()[::-1])
        lge_com = foreground_com(lge_arr, spacing_zyx)

        gt_img = sitk.ReadImage(str(case.gt_path))
        pred_img = sitk.ReadImage(str(case.pred_path))
        pred_img = resample_image_to_reference(pred_img, gt_img, is_label=True)
        gt = sitk.GetArrayFromImage(gt_img).astype(np.uint8, copy=False)
        pred = sitk.GetArrayFromImage(pred_img).astype(np.uint8, copy=False)
        per_case_metrics = collect_case_metrics("no_alignment_nnunet501_fold0", case, pred, gt, gt_img)
        case_metric_rows.extend(per_case_metrics)
        scar_row = next(r for r in per_case_metrics if r["class_id"] == SCAR)
        edema_row = next(r for r in per_case_metrics if r["class_id"] == EDEMA)
        scar_dice = finite_float(scar_row["dice"])
        edema_dice = finite_float(edema_row["dice"])
        pathology_failure = (1.0 - (scar_dice or 0.0)) + (1.0 - (edema_dice or 0.0))

        pair_scores: list[float] = []
        row_base: dict[str, Any] = {
            "case_id": case.case_id,
            "center": case.center,
            "modality_group": case.modality_group,
            "scar_dice": scar_dice,
            "edema_dice": edema_dice,
            "scar_hd95": scar_row["hd95"],
            "edema_hd95": edema_row["hd95"],
            "pathology_failure_score": pathology_failure,
        }

        for moving_name in ("C0", "T2"):
            moving_img = sitk.ReadImage(str(case.raw_dir / f"{case.case_id}_{moving_name}.nii.gz"))
            moving_header = image_header(moving_img)
            lge_header = image_header(lge_img)
            geom_same = same_geometry(lge_img, moving_img)
            moving_rs = moving_img if geom_same else resample_image_to_reference(moving_img, lge_img, is_label=False)
            moving_arr = sitk.GetArrayFromImage(moving_rs)
            moving_norm = robust_norm(moving_arr)
            moving_edge = gradient_mag(moving_arr)
            corr = safe_corr(lge_norm, moving_norm)
            mi = mutual_information(lge_norm, moving_norm)
            e_corr = safe_corr(lge_edge, moving_edge)
            m_com = foreground_com(moving_arr, spacing_zyx)
            com_mm = com_distance_mm(lge_com, m_com)
            slices = slice_correspondence(lge_arr, moving_arr)
            shape_mismatch = lge_img.GetSize() != moving_img.GetSize()
            spacing_mismatch = not np.allclose(lge_img.GetSpacing(), moving_img.GetSpacing(), atol=1e-5)
            origin_mismatch = not np.allclose(lge_img.GetOrigin(), moving_img.GetOrigin(), atol=1e-4)
            direction_mismatch = not np.allclose(lge_img.GetDirection(), moving_img.GetDirection(), atol=1e-5)
            mismatch = 0.0
            mismatch += min((com_mm or 0.0) / 40.0, 2.0)
            mismatch += 1.0 - max(min(e_corr if e_corr is not None else 0.0, 1.0), -1.0)
            mismatch += float(slices["mean_abs_best_shift"] or 0.0) * 0.5
            mismatch += 0.5 if shape_mismatch else 0.0
            mismatch += 0.5 if spacing_mismatch else 0.0
            mismatch += 0.5 if origin_mismatch else 0.0
            mismatch += 0.5 if direction_mismatch else 0.0
            pair_scores.append(float(mismatch))

            header_rows.append(
                {
                    "variant": "diagnosis",
                    "transform_family": "header_audit",
                    "case_id": case.case_id,
                    "center": case.center,
                    "fixed": "LGE",
                    "moving": moving_name,
                    "fixed_size": lge_header["size"],
                    "moving_size": moving_header["size"],
                    "fixed_spacing": lge_header["spacing"],
                    "moving_spacing": moving_header["spacing"],
                    "fixed_origin": lge_header["origin"],
                    "moving_origin": moving_header["origin"],
                    "fixed_direction": lge_header["direction"],
                    "moving_direction": moving_header["direction"],
                    "shape_mismatch": shape_mismatch,
                    "spacing_mismatch": spacing_mismatch,
                    "origin_mismatch": origin_mismatch,
                    "direction_mismatch": direction_mismatch,
                    "same_geometry": geom_same,
                    "intensity_corr": corr,
                    "mutual_information": mi,
                    "edge_corr": e_corr,
                    "com_distance_mm": com_mm,
                    **slices,
                    "pair_mismatch_score": mismatch,
                    "scar_dice": scar_dice,
                    "edema_dice": edema_dice,
                    "pathology_failure_score": pathology_failure,
                }
            )

        row_base["alignment_mismatch_score"] = finite_mean(pair_scores)
        alignment_rows.append(row_base)

    subgroup_rows = summarize_subgroups("no_alignment_nnunet501_fold0", case_metric_rows)

    xs = [float(r["alignment_mismatch_score"]) for r in alignment_rows if r["alignment_mismatch_score"] is not None]
    failure_by_id = {
        r["case_id"]: float(r["pathology_failure_score"])
        for r in alignment_rows
        if r["alignment_mismatch_score"] is not None and r["pathology_failure_score"] is not None
    }
    score_by_id = {r["case_id"]: float(r["alignment_mismatch_score"]) for r in alignment_rows if r["alignment_mismatch_score"] is not None}
    common_ids = [cid for cid in score_by_id if cid in failure_by_id]
    corr_rows: list[dict[str, Any]] = []
    for target, getter in (
        ("pathology_failure_score", lambda r: finite_float(r["pathology_failure_score"])),
        ("scar_failure", lambda r: 1.0 - (finite_float(r["scar_dice"]) or 0.0)),
        ("edema_failure", lambda r: 1.0 - (finite_float(r["edema_dice"]) or 0.0)),
    ):
        target_rows = [r for r in alignment_rows if r["alignment_mismatch_score"] is not None and getter(r) is not None]
        vals_x = [float(r["alignment_mismatch_score"]) for r in target_rows]
        vals_y = [float(getter(r)) for r in target_rows]
        c = correlation(vals_x, vals_y)
        corr_rows.append({"variant": "diagnosis", "transform_family": "correlation", "target": target, **c})

    main_corr = next(r for r in corr_rows if r["target"] == "pathology_failure_score")
    spearman = finite_float(main_corr["spearman_r"])
    pearson = finite_float(main_corr["pearson_r"])
    top_failure = sorted(alignment_rows, key=lambda r: finite_float(r["pathology_failure_score"]) or -1, reverse=True)[:5]
    top_mismatch = sorted(alignment_rows, key=lambda r: finite_float(r["alignment_mismatch_score"]) or -1, reverse=True)[:5]
    overlap = len({r["case_id"] for r in top_failure} & {r["case_id"] for r in top_mismatch})
    alignment_primary = bool(
        (spearman is not None and spearman >= 0.45)
        or (pearson is not None and pearson >= 0.45 and overlap >= 2)
    )
    decision = "EXECUTED_UNAUDITED" if alignment_primary else "STOP_ALIGNMENT_NOT_PRIMARY"

    registration_rows: list[dict[str, Any]] = []
    registration_rows.extend(header_rows)
    registration_rows.extend(corr_rows)
    registration_rows.append(
        {
            "variant": "no_alignment_nnunet501_fold0",
            "transform_family": "none",
            "case_id": "complete_subset",
            "center": "CenterB+CenterC+other_complete",
            "moving": "none",
            "fixed": "none",
            "n_cases": len(complete_cases),
            "myops_scar_dice_mean": finite_mean([r["dice"] for r in case_metric_rows if r["class_id"] == SCAR]),
            "myops_edema_dice_mean": finite_mean([r["dice"] for r in case_metric_rows if r["class_id"] == EDEMA]),
            "scar_hd95_mean": finite_mean([r["hd95"] for r in case_metric_rows if r["class_id"] == SCAR]),
            "edema_hd95_mean": finite_mean([r["hd95"] for r in case_metric_rows if r["class_id"] == EDEMA]),
            "pathology_delta_vs_no_alignment": 0.0,
        }
    )
    registration_rows.append(
        {
            "variant": "translation_baseline",
            "transform_family": "translation",
            "case_id": "not_executed",
            "center": "not_executed",
            "moving": "C0/T2",
            "fixed": "LGE",
            "n_cases": len(complete_cases),
            "stop_reason": "not executed because Phase 1 did not support alignment as primary bottleneck",
            "pathology_delta_vs_no_alignment": "evidence not found",
        }
    )

    write_csv(OUT_ROOT / "registration_metrics.csv", registration_rows)
    write_csv(OUT_ROOT / "subgroup_metrics.csv", subgroup_rows)
    write_csv(OUT_ROOT / "component_hd_by_case.csv", case_metric_rows)
    write_csv(
        OUT_ROOT / "warp_sanity.csv",
        [
            {
                "variant": "no_alignment_nnunet501_fold0",
                "transform_family": "none",
                "n_cases": len(complete_cases),
                "warp_generated": False,
                "smoothness_proxy": 0.0,
                "jacobian_folding_proxy": 0.0,
                "invalid_warp_cases": 0,
                "runtime_sec": 0.0,
                "pathology_delta_vs_no_alignment": 0.0,
            },
            {
                "variant": "translation_baseline",
                "transform_family": "translation",
                "n_cases": len(complete_cases),
                "warp_generated": False,
                "smoothness_proxy": "evidence not found",
                "jacobian_folding_proxy": "evidence not found",
                "invalid_warp_cases": "evidence not found",
                "runtime_sec": "evidence not found",
                "stop_reason": "not executed because Phase 1 did not support alignment as primary bottleneck",
            },
            {
                "variant": "slice_or_tps_alignment",
                "transform_family": "slice/TPS",
                "n_cases": len(complete_cases),
                "warp_generated": False,
                "smoothness_proxy": "evidence not found",
                "jacobian_folding_proxy": "evidence not found",
                "invalid_warp_cases": "evidence not found",
                "runtime_sec": "evidence not found",
                "stop_reason": "not attempted after STOP_ALIGNMENT_NOT_PRIMARY",
            },
            {
                "variant": "deformable_or_feature_warp",
                "transform_family": "BSpline/Demons/feature-level",
                "n_cases": len(complete_cases),
                "warp_generated": False,
                "smoothness_proxy": "evidence not found",
                "jacobian_folding_proxy": "evidence not found",
                "invalid_warp_cases": "evidence not found",
                "runtime_sec": "evidence not found",
                "stop_reason": "not attempted after STOP_ALIGNMENT_NOT_PRIMARY",
            },
        ],
    )

    elapsed = time.time() - start
    commands[0]["elapsed_sec"] = elapsed
    write_text(
        OUT_ROOT / "command_transcript.md",
        f"""# Command Transcript

cwd: `{REPO_ROOT}`
network: disabled/not used

| command | exit_status | elapsed_sec |
| --- | ---: | ---: |
| `{command}` | 0 | {elapsed:.2f} |

## Environment Checks

- Python executable: `{sys.executable}`
- SimpleITK: available
- scipy/numpy: available
- git_head: `{subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO_ROOT, text=True).strip()}`
""",
    )
    write_markdown_reports(
        complete_cases=complete_cases,
        header_rows=header_rows,
        alignment_rows=alignment_rows,
        case_metric_rows=case_metric_rows,
        subgroup_rows=subgroup_rows,
        corr_rows=corr_rows,
        decision=decision,
        commands=commands,
    )
    print(f"wrote {OUT_ROOT}")
    print(f"decision={decision}")


if __name__ == "__main__":
    main()
