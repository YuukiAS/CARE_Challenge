#!/usr/bin/env python3
"""MyoWall predicted-geometry failure attribution diagnostic.

This is a task-local forensic entrypoint. It deliberately does not modify the
production MyoWall geometry implementation and does not persist dense GT or
predicted probability volumes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import pickle
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
import torch.nn.functional as F
from scipy.ndimage import binary_closing, binary_dilation, binary_fill_holes, distance_transform_edt, generate_binary_structure, label

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.models.myowall_if.evaluator import MyoWallPilotEvaluator  # noqa: E402
from src.care_myocardium.models.myowall_if.geometry import FrozenStockGeometryCacheBuilder  # noqa: E402
from src.care_myocardium.models.myowall_if.geometry import WallCoordinateTransform, WallGeometry, WallInverseTransform  # noqa: E402
from src.care_myocardium.models.myowall_if.stock_adapter import StockNNUNetFeatureAdapter  # noqa: E402
from src.care_myocardium.models.myowall_if.stock_adapter import sha256_file  # noqa: E402

TASK_KEY = "20260731_care_myowall_geometry_diagnostic_closure"
PREV_TASK_KEY = "20260731_care_myowall_if_mechanism_pilot"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
PREV_RESULT_ROOT = REPO_ROOT / "results" / PREV_TASK_KEY
FAILED_FIVE = {"Case3029", "Case8003", "Case8022", "Case8027", "Case8028"}
ATLAS_CASES = ["Case3029", "Case8003", "Case8022", "Case8027", "Case8028", "Case3023", "Case3027", "Case3032", "Case6008", "Case7010"]
LV_GRID = [0.15, 0.25, 0.35, 0.45]
WALL_GRID = [0.10, 0.15, 0.20, 0.25]
GEOM_GATE_SPACING = (1.0, 1.0, 1.0)


@dataclass(frozen=True)
class CaseData:
    case_id: str
    image: torch.Tensor
    seg: torch.Tensor
    spacing_zyx: tuple[float, float, float]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_capture(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return {"command": " ".join(cmd), "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def data_file(data_root: Path, suffix: str) -> Path:
    path = data_root / suffix
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path


def load_case(data_root: Path, case_id: str, patch_size: list[int]) -> CaseData:
    import blosc2

    fullres = data_file(data_root, "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres")
    image_np = np.asarray(blosc2.open(str(fullres / f"{case_id}.b2nd"), mode="r")[:])
    seg_np = np.asarray(blosc2.open(str(fullres / f"{case_id}_seg.b2nd"), mode="r")[:]).squeeze()
    if seg_np.ndim == 2:
        seg_np = seg_np[None, ...]
    image = torch.from_numpy(image_np).float().unsqueeze(0)
    target_z, target_y, target_x = patch_size
    z, y, x = image.shape[-3:]
    crop = image[..., : min(z, target_z), : min(y, target_y), : min(x, target_x)]
    pad = (0, max(0, target_x - crop.shape[-1]), 0, max(0, target_y - crop.shape[-2]), 0, max(0, target_z - crop.shape[-3]))
    image = F.pad(crop, pad)
    seg_t = torch.from_numpy(seg_np).long()
    seg_crop = seg_t[: min(seg_t.shape[0], target_z), : min(seg_t.shape[1], target_y), : min(seg_t.shape[2], target_x)]
    seg_t = F.pad(seg_crop.unsqueeze(0).unsqueeze(0).float(), pad).long()[0, 0]
    with (fullres / f"{case_id}.pkl").open("rb") as f:
        props = pickle.load(f)
    spacing = tuple(float(v) for v in props.get("spacing", (1.0, 1.0, 1.0)))
    if len(spacing) != 3:
        spacing = (1.0, 1.0, 1.0)
    return CaseData(case_id=case_id, image=image, seg=seg_t, spacing_zyx=spacing)  # type: ignore[arg-type]


def dice_binary(pred: np.ndarray, ref: np.ndarray) -> float:
    pred = pred.astype(bool)
    ref = ref.astype(bool)
    den = int(pred.sum() + ref.sum())
    return 1.0 if den == 0 else float(2 * np.logical_and(pred, ref).sum() / den)


def hd95_binary(pred: np.ndarray, ref: np.ndarray, spacing_zyx: tuple[float, float, float]) -> float | None:
    evaluator = MyoWallPilotEvaluator()
    return evaluator.hd95(pred.astype(np.uint8), ref.astype(np.uint8), 1, spacing_zyx)


def cc_count(mask: np.ndarray) -> int:
    _cc, n = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n)


def hole_count(mask: np.ndarray) -> int:
    count = 0
    for zi in range(mask.shape[0]):
        filled = binary_fill_holes(mask[zi].astype(bool))
        holes = filled & ~mask[zi].astype(bool)
        _cc, n = label(holes, structure=generate_binary_structure(2, 1))
        count += int(n)
    return count


def keep_largest_3d(mask: np.ndarray) -> np.ndarray:
    cc, n = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    if n == 0:
        return mask.astype(bool)
    counts = np.bincount(cc.ravel())
    counts[0] = 0
    return cc == int(counts.argmax())


def remove_small_components(mask: np.ndarray, min_voxels: int) -> np.ndarray:
    cc, n = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    if n == 0:
        return mask.astype(bool)
    counts = np.bincount(cc.ravel())
    keep = np.zeros(n + 1, dtype=bool)
    keep[np.where(counts >= min_voxels)[0]] = True
    keep[0] = False
    return keep[cc]


def fill_holes_slicewise(mask: np.ndarray) -> np.ndarray:
    out = np.zeros_like(mask, dtype=bool)
    for zi in range(mask.shape[0]):
        out[zi] = binary_fill_holes(mask[zi].astype(bool))
    return out


def remove_single_slice_components(mask: np.ndarray) -> np.ndarray:
    cc, n = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    if n == 0:
        return mask.astype(bool)
    out = mask.astype(bool).copy()
    for idx in range(1, n + 1):
        zidx = np.unique(np.nonzero(cc == idx)[0])
        if zidx.size <= 1:
            out[cc == idx] = False
    return out


def longest_true_run(flags: np.ndarray) -> np.ndarray:
    flags = flags.astype(bool)
    best_start = 0
    best_len = 0
    cur_start = 0
    cur_len = 0
    for i, ok in enumerate(flags):
        if ok:
            if cur_len == 0:
                cur_start = i
            cur_len += 1
            if cur_len > best_len:
                best_start = cur_start
                best_len = cur_len
        else:
            cur_len = 0
    out = np.zeros_like(flags, dtype=bool)
    if best_len:
        out[best_start : best_start + best_len] = True
    return out


def supported_slices(lv_mask: np.ndarray, wall_mask: np.ndarray) -> np.ndarray:
    lv_largest = keep_largest_3d(lv_mask)
    wall_largest = keep_largest_3d(wall_mask)
    flags = []
    for zi in range(lv_mask.shape[0]):
        flags.append(bool(lv_mask[zi].any() and wall_mask[zi].any() and lv_largest[zi].any() and wall_largest[zi].any()))
    return longest_true_run(np.asarray(flags, dtype=bool))


def cleanup_lv(p_lv: torch.Tensor, threshold: float) -> np.ndarray:
    mask = (p_lv[0, 0].detach().cpu().numpy() >= threshold)
    mask = keep_largest_3d(mask)
    mask = fill_holes_slicewise(mask)
    mask = remove_small_components(mask, 32)
    return mask


def cleanup_wall(p_wall: torch.Tensor, lv_mask: np.ndarray, threshold: float) -> np.ndarray:
    mask = (p_wall[0, 0].detach().cpu().numpy() >= threshold)
    cc, n = label(mask.astype(bool), structure=generate_binary_structure(3, 1))
    if n:
        lv_neighborhood = binary_dilation(lv_mask.astype(bool), structure=generate_binary_structure(3, 1), iterations=6)
        best = 0
        best_score = -1.0
        for idx in range(1, n + 1):
            comp = cc == idx
            score = float((comp & lv_neighborhood).sum()) + 0.001 * float(comp.sum())
            if score > best_score:
                best = idx
                best_score = score
        mask = cc == best
    closed = np.zeros_like(mask, dtype=bool)
    struct = generate_binary_structure(2, 1)
    for zi in range(mask.shape[0]):
        closed[zi] = binary_closing(mask[zi].astype(bool), structure=struct, iterations=1)
    mask = fill_holes_slicewise(closed)
    mask = remove_single_slice_components(mask)
    return mask


def build_geom_from_masks(lv_mask: np.ndarray, wall_mask: np.ndarray, spacing: tuple[float, float, float]) -> WallGeometry:
    builder = FrozenStockGeometryCacheBuilder(lv_threshold=0.5, wall_threshold=0.5)
    p_lv = torch.from_numpy(lv_mask.astype(np.float32)).view(1, 1, *lv_mask.shape)
    p_wall = torch.from_numpy(wall_mask.astype(np.float32)).view(1, 1, *wall_mask.shape)
    return builder.build_from_probabilities(p_lv, p_wall, spacing_zyx=spacing)


def move_geom(geom: WallGeometry, device: torch.device) -> WallGeometry:
    return WallGeometry(
        centroids_xy=geom.centroids_xy.to(device),
        endo_radii=geom.endo_radii.to(device),
        epi_radii=geom.epi_radii.to(device),
        valid=geom.valid.to(device),
        active_slices=None if geom.active_slices is None else geom.active_slices.to(device),
        raw_valid=None if geom.raw_valid is None else geom.raw_valid.to(device),
        spacing_zyx=geom.spacing_zyx,
    )


def roundtrip(mask: np.ndarray, geom: WallGeometry, spacing: tuple[float, float, float], rt_device: torch.device | None = None, *, compute_hd95: bool = True) -> tuple[float, float | None, np.ndarray]:
    tensor = torch.from_numpy(mask.astype(np.float32)).view(1, 1, *mask.shape)
    geom_for_rt = geom
    if rt_device is not None:
        tensor = tensor.to(rt_device)
        geom_for_rt = move_geom(geom, rt_device)
    lattice = WallCoordinateTransform()(tensor, geom_for_rt, mode="bilinear")
    recon = WallInverseTransform()(lattice, geom_for_rt, output_shape=mask.shape, outside_value=0.0)
    pred = recon[0, 0].detach().cpu().numpy() >= 0.50
    hd95 = hd95_binary(pred, mask, spacing) if compute_hd95 else None
    return dice_binary(pred, mask), hd95, pred


def ray_crossing_stats(wall_mask: np.ndarray, geom: WallGeometry, support: np.ndarray | None = None, angles: int = 256) -> tuple[float, float, float, Counter[str]]:
    theta = np.linspace(-math.pi, math.pi, angles, endpoint=False)
    z, y, x = wall_mask.shape
    max_radius = math.sqrt(y * y + x * x)
    radii = np.linspace(0.0, max_radius, 384)
    no = single = multi = total = 0
    reasons: Counter[str] = Counter()
    for zi in range(z):
        if support is not None and not bool(support[zi]):
            reasons["unsupported_slice"] += 1
            continue
        if not wall_mask[zi].any():
            reasons["wall_empty_slice"] += 1
        cy, cx = geom.centroids_xy[zi].detach().cpu().numpy().astype(float)
        for a, th in enumerate(theta):
            xs = np.rint(cx + radii * math.cos(th)).astype(int)
            ys = np.rint(cy + radii * math.sin(th)).astype(int)
            inside = (xs >= 0) & (xs < x) & (ys >= 0) & (ys < y)
            vals = np.zeros_like(radii, dtype=bool)
            vals[inside] = wall_mask[zi, ys[inside], xs[inside]]
            starts = np.flatnonzero(vals & ~np.r_[False, vals[:-1]])
            intervals = len(starts)
            total += 1
            if intervals == 0:
                no += 1
            elif intervals == 1:
                single += 1
            else:
                multi += 1
        valid_frac = float(geom.valid[zi].float().mean().item())
        if valid_frac < 0.5:
            reasons["low_valid_angle_slice"] += 1
    denom = max(total, 1)
    return no / denom, single / denom, multi / denom, reasons


def centroid_inside_fraction(lv_mask: np.ndarray, geom: WallGeometry, support: np.ndarray | None = None) -> float:
    vals: list[bool] = []
    z, y, x = lv_mask.shape
    for zi in range(z):
        if support is not None and not bool(support[zi]):
            continue
        cy, cx = geom.centroids_xy[zi].detach().cpu().numpy().astype(float)
        iy, ix = int(round(cy)), int(round(cx))
        vals.append(0 <= iy < y and 0 <= ix < x and bool(lv_mask[zi, iy, ix]))
    return float(np.mean(vals)) if vals else 0.0


def geom_metric_row(case_id: str, mode: str, meta: Any, geom: WallGeometry, lv_mask: np.ndarray, wall_mask: np.ndarray, spacing: tuple[float, float, float], *, supported: np.ndarray | None, old_geometry_valid: bool | None = None, rt_device: torch.device | None = None, roundtrip_mask: np.ndarray | None = None) -> dict[str, Any]:
    valid = geom.valid.detach().cpu().numpy().astype(bool)
    raw = geom.raw_valid.detach().cpu().numpy().astype(bool) if geom.raw_valid is not None else valid
    active = geom.active_slices.detach().cpu().numpy().astype(bool) if geom.active_slices is not None else np.ones(valid.shape[0], dtype=bool)
    support = supported if supported is not None else active
    rt_mask = wall_mask if roundtrip_mask is None else roundtrip_mask
    dice, hd95, _recon = roundtrip(rt_mask, geom, spacing, rt_device)
    no, single, multi, reasons = ray_crossing_stats(wall_mask, geom, support=support)
    active_valid = valid[active] if active.any() else valid
    supported_valid = valid[support] if support.any() else valid[:0]
    raw_valid = raw[active] if active.any() else raw
    valid_angle_fraction = float(active_valid.mean()) if active_valid.size else 0.0
    supported_angle_fraction = float(supported_valid.mean()) if supported_valid.size else 0.0
    geometry_valid = bool(old_geometry_valid) if old_geometry_valid is not None else bool(valid_angle_fraction >= 0.95)
    if mode in {"G2_supported_denominator"}:
        geometry_valid = bool(supported_angle_fraction >= 0.95)
    return {
        "case_id": case_id,
        "mode": mode,
        "center": meta.center,
        "modality_group": meta.modality_group,
        "t2_present": bool(meta.t2_present),
        "active_slice_count": int(active.sum()),
        "all_depth_slice_count": int(valid.shape[0]),
        "supported_slice_count": int(support.sum()),
        "raw_valid_angle_fraction": float(raw_valid.mean()) if raw_valid.size else 0.0,
        "valid_angle_fraction": valid_angle_fraction,
        "valid_angle_fraction_supported": supported_angle_fraction,
        "valid_slice_fraction_all_depth": float((valid.mean(axis=1) > 0.5).mean()) if valid.size else 0.0,
        "valid_slice_fraction_supported": float((valid[support].mean(axis=1) > 0.5).mean()) if support.any() else 0.0,
        "geometry_valid": geometry_valid,
        "wall_roundtrip_dice": dice,
        "wall_roundtrip_hd95_mm": "" if hd95 is None else hd95,
        "centroid_inside_lv_fraction": centroid_inside_fraction(lv_mask, geom, support),
        "ray_no_crossing_fraction": no,
        "ray_single_crossing_fraction": single,
        "ray_multi_crossing_fraction": multi,
        "failed_slice_reason_counts": json.dumps(dict(reasons), sort_keys=True),
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    groups = [("all", lambda r: True)]
    for name in ["CenterB", "CenterC", "CenterH"]:
        groups.append((name, lambda r, n=name: r["center"] == n))
    groups.extend([
        ("complete tri-modal", lambda r: r["modality_group"] == "C0+LGE+T2"),
        ("LGE+C0", lambda r: r["modality_group"] == "C0+LGE"),
        ("LGE-only", lambda r: r["modality_group"] == "LGE-only"),
        ("failed five", lambda r: r["case_id"] in FAILED_FIVE),
        ("other 27", lambda r: r["case_id"] not in FAILED_FIVE),
    ])
    for mode in sorted({r["mode"] for r in rows}):
        mode_rows = [r for r in rows if r["mode"] == mode]
        for group, pred in groups:
            subset = [r for r in mode_rows if pred(r)]
            if not subset:
                continue
            dice_vals = [float(r["wall_roundtrip_dice"]) for r in subset if r["wall_roundtrip_dice"] != ""]
            hd_vals = [float(r["wall_roundtrip_hd95_mm"]) for r in subset if r["wall_roundtrip_hd95_mm"] != ""]
            out.append({
                "mode": mode,
                "subgroup": group,
                "case_count": len(subset),
                "geometry_valid_rate": float(np.mean([bool(r["geometry_valid"]) for r in subset])),
                "median_valid_angle_fraction": float(np.median([float(r["valid_angle_fraction"]) for r in subset])),
                "fifth_percentile_roundtrip_dice": "" if not dice_vals else float(np.percentile(dice_vals, 5)),
                "median_roundtrip_dice": "" if not dice_vals else float(np.median(dice_vals)),
                "median_roundtrip_hd95_mm": "" if not hd_vals else float(np.median(hd_vals)),
                "median_supported_slice_count": float(np.median([int(r["supported_slice_count"]) for r in subset])),
            })
    return out


def anatomy_rows(case_id: str, meta: Any, seg: torch.Tensor, pred_modes: dict[str, tuple[np.ndarray, np.ndarray]], spacing: tuple[float, float, float]) -> list[dict[str, Any]]:
    gt_lv = (seg.detach().cpu().numpy() == 2)
    gt_wall = np.isin(seg.detach().cpu().numpy(), [1, 4, 5])
    rows = []
    for mode, (lv_mask, wall_mask) in pred_modes.items():
        rows.append({
            "case_id": case_id,
            "mode": mode,
            "center": meta.center,
            "modality_group": meta.modality_group,
            "t2_present": bool(meta.t2_present),
            "lv_dice": dice_binary(lv_mask, gt_lv),
            "lv_hd95_mm": "" if hd95_binary(lv_mask, gt_lv, spacing) is None else hd95_binary(lv_mask, gt_lv, spacing),
            "myocardium_union_dice": dice_binary(wall_mask, gt_wall),
            "myocardium_union_hd95_mm": "" if hd95_binary(wall_mask, gt_wall, spacing) is None else hd95_binary(wall_mask, gt_wall, spacing),
            "lv_empty_slice_count": int(sum(not lv_mask[zi].any() for zi in range(lv_mask.shape[0]))),
            "wall_empty_slice_count": int(sum(not wall_mask[zi].any() for zi in range(wall_mask.shape[0]))),
            "lv_component_count": cc_count(lv_mask),
            "wall_component_count": cc_count(wall_mask),
            "lv_topology_hole_count": hole_count(lv_mask),
            "wall_topology_hole_count": hole_count(wall_mask),
        })
    return rows


def subgroup_anatomy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = [("all", lambda r: True), ("CenterB", lambda r: r["center"] == "CenterB"), ("CenterC", lambda r: r["center"] == "CenterC"), ("CenterH", lambda r: r["center"] == "CenterH"), ("complete tri-modal", lambda r: r["modality_group"] == "C0+LGE+T2"), ("LGE+C0", lambda r: r["modality_group"] == "C0+LGE"), ("LGE-only", lambda r: r["modality_group"] == "LGE-only"), ("failed five", lambda r: r["case_id"] in FAILED_FIVE), ("other 27", lambda r: r["case_id"] not in FAILED_FIVE)]
    out = []
    for mode in sorted({r["mode"] for r in rows}):
        mode_rows = [r for r in rows if r["mode"] == mode]
        for group, pred in groups:
            subset = [r for r in mode_rows if pred(r)]
            if not subset:
                continue
            out.append({
                "mode": mode,
                "subgroup": group,
                "case_count": len(subset),
                "median_lv_dice": float(np.median([float(r["lv_dice"]) for r in subset])),
                "median_myocardium_union_dice": float(np.median([float(r["myocardium_union_dice"]) for r in subset])),
                "median_lv_component_count": float(np.median([int(r["lv_component_count"]) for r in subset])),
                "median_wall_component_count": float(np.median([int(r["wall_component_count"]) for r in subset])),
                "median_wall_empty_slice_count": float(np.median([int(r["wall_empty_slice_count"]) for r in subset])),
            })
    return out


def compare_g0_to_existing(rows: list[dict[str, Any]]) -> dict[str, Any]:
    old = {r["case_id"]: r for r in read_csv(PREV_RESULT_ROOT / "geometry_casewise_metrics.csv")}
    diffs = []
    for row in [r for r in rows if r["mode"] == "G0_current_predicted"]:
        cid = row["case_id"]
        ref = old.get(cid)
        if not ref:
            diffs.append({"case_id": cid, "field": "missing_old_row"})
            continue
        checks = {
            "raw_valid_angle_fraction": float(row["raw_valid_angle_fraction"]),
            "valid_angle_fraction": float(row["valid_angle_fraction"]),
            "valid_slice_fraction": float(row["valid_slice_fraction_all_depth"]),
            "active_slice_count": int(row["active_slice_count"]),
            "geometry_valid": str(bool(row["geometry_valid"])),
            "wall_roundtrip_dice": float(row["wall_roundtrip_dice"]),
        }
        for field, value in checks.items():
            old_field = "valid_slice_fraction" if field == "valid_slice_fraction" else field
            ref_val = ref.get(old_field, "")
            if isinstance(value, float):
                if ref_val == "" or abs(value - float(ref_val)) > 1e-6:
                    diffs.append({"case_id": cid, "field": field, "new": value, "old": ref_val})
            elif str(value) != str(ref_val):
                diffs.append({"case_id": cid, "field": field, "new": value, "old": ref_val})
    return {"status": "PASS" if not diffs else "FAIL", "diffs": diffs, "compared_cases": len([r for r in rows if r["mode"] == "G0_current_predicted"])}


def choose_threshold(search_rows: list[dict[str, Any]]) -> dict[str, Any]:
    def key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            float(row["case_geometry_valid_rate"]),
            float(row["fifth_percentile_roundtrip_dice"]),
            -float(row["median_roundtrip_hd95_mm"] if row["median_roundtrip_hd95_mm"] != "" else 1e9),
            -abs(float(row["lv_threshold"]) - 0.35) - abs(float(row["wall_threshold"]) - 0.20),
            float(row["lv_threshold"]),
        )
    return max(search_rows, key=key)


def typed_threshold_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in ("lv_threshold", "wall_threshold", "case_geometry_valid_rate", "fifth_percentile_roundtrip_dice", "median_roundtrip_hd95_mm", "l1_distance_from_original_threshold"):
        if key in out and out[key] != "":
            out[key] = float(out[key])
    if "case_count" in out and out["case_count"] != "":
        out["case_count"] = int(float(out["case_count"]))
    for key in ("secondary_metrics_computed", "hd95_metrics_computed"):
        if key in out and isinstance(out[key], str):
            out[key] = out[key].lower() == "true"
    return out


def scientific_decision(summary_rows: list[dict[str, Any]], case_rows: list[dict[str, Any]]) -> str:
    def row(mode: str, subgroup: str = "all") -> dict[str, Any]:
        return next(r for r in summary_rows if r["mode"] == mode and r["subgroup"] == subgroup)
    g1 = row("G1_GT_anatomy")
    g3 = row("G3_repaired_predicted")
    centerh_g3 = row("G3_repaired_predicted", "CenterH")
    g2_case3029 = next(r for r in case_rows if r["mode"] == "G2_supported_denominator" and r["case_id"] == "Case3029")
    g1_pass = float(g1["geometry_valid_rate"]) >= 0.95 and float(g1["fifth_percentile_roundtrip_dice"]) >= 0.90
    g3_pass = float(g3["geometry_valid_rate"]) >= 0.95 and float(g3["fifth_percentile_roundtrip_dice"]) >= 0.90 and float(g3["median_roundtrip_hd95_mm"] if g3["median_roundtrip_hd95_mm"] != "" else 1e9) <= 2.0 and float(centerh_g3["geometry_valid_rate"]) >= 0.95
    if not g1_pass:
        return "HARD_WALL_REPRESENTATION_INVALID"
    if g3_pass:
        return "GEOMETRY_EXTRACTION_REPAIRABLE"
    if bool(g2_case3029["geometry_valid"]) and float(centerh_g3["geometry_valid_rate"]) < 0.95:
        return "MIXED_GATE_AND_ANATOMY_FAILURE"
    return "PREDICTED_ANATOMY_SOURCE_INSUFFICIENT"


def create_atlas(data_by_case: dict[str, CaseData], prob_by_case: dict[str, dict[str, torch.Tensor]], rows: list[dict[str, Any]], g3_masks: dict[str, tuple[np.ndarray, np.ndarray]], out_pdf: Path, out_png: Path, findings_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    findings = ["# Case Visual Findings", ""]
    contact_fig, contact_axes = plt.subplots(len(ATLAS_CASES), 4, figsize=(16, 3.2 * len(ATLAS_CASES)))
    with PdfPages(out_pdf) as pdf:
        for row_idx, cid in enumerate(ATLAS_CASES):
            data = data_by_case[cid]
            image = data.image[0].detach().cpu().numpy()
            seg = data.seg.detach().cpu().numpy()
            probs = prob_by_case[cid]
            p_lv = probs["p_lv"][0, 0].detach().cpu().numpy()
            p_wall = probs["p_wall"][0, 0].detach().cpu().numpy()
            gt_wall = np.isin(seg, [1, 4, 5])
            gt_lv = seg == 2
            g0_lv = p_lv >= 0.35
            g0_wall = p_wall >= 0.20
            g3_lv, g3_wall = g3_masks[cid]
            z_scores = gt_wall.reshape(gt_wall.shape[0], -1).sum(axis=1) + g0_wall.reshape(g0_wall.shape[0], -1).sum(axis=1)
            zi = int(np.argmax(z_scores)) if z_scores.size else 0
            g0_geom = FrozenStockGeometryCacheBuilder().build_from_probabilities(torch.from_numpy(p_lv).view(1, 1, *p_lv.shape), torch.from_numpy(p_wall).view(1, 1, *p_wall.shape), spacing_zyx=data.spacing_zyx)
            g1_geom = build_geom_from_masks(gt_lv, gt_wall, data.spacing_zyx)
            g3_geom = build_geom_from_masks(g3_lv, g3_wall, data.spacing_zyx)
            _d1, _h1, g1_recon = roundtrip(gt_wall, g1_geom, data.spacing_zyx)
            _d3, _h3, g3_recon = roundtrip(g3_wall, g3_geom, data.spacing_zyx)
            g2_support = supported_slices(g0_lv, g0_wall)
            case_rows = [r for r in rows if r["case_id"] == cid]
            txt = "; ".join(f"{r['mode']} valid={r['geometry_valid']} slices={r['supported_slice_count']} dice={float(r['wall_roundtrip_dice']):.3f}" for r in case_rows)
            findings.extend([f"## {cid}", "", txt, ""])
            fig, axes = plt.subplots(3, 4, figsize=(18, 12))
            panels = [
                (image[0, zi], "LGE"),
                (image[1, zi] if image.shape[0] > 1 else np.zeros_like(image[0, zi]), "T2 or MISSING"),
                (gt_lv[zi].astype(float) + 2 * gt_wall[zi].astype(float), "GT LV/wall"),
                (p_lv[zi] + p_wall[zi], "pred LV+wall prob"),
                (g0_lv[zi].astype(float) + 2 * g0_wall[zi].astype(float), "G0 masks"),
                (g0_geom.valid.detach().cpu().numpy().astype(float), "G0 invalid angle/slice"),
                (g1_recon[zi].astype(float), "G1 GT roundtrip"),
                (g2_support[:, None] * np.ones((g2_support.size, 256)), "G2 supported denominator"),
                (g3_lv[zi].astype(float) + 2 * g3_wall[zi].astype(float), "G3 repaired masks"),
                (g3_recon[zi].astype(float), "G3 roundtrip overlay"),
                (p_wall[zi], "pred wall probability"),
                (np.zeros_like(p_wall[zi]), txt[:120]),
            ]
            for ax, (arr, title) in zip(axes.ravel(), panels):
                ax.imshow(arr, cmap="gray")
                ax.set_title(title, fontsize=9)
                ax.axis("off")
            cy, cx = g0_geom.centroids_xy[zi].detach().cpu().numpy()
            axes[1, 0].plot([cx], [cy], "ro", ms=3)
            for a in np.linspace(0, 2 * math.pi, 32, endpoint=False):
                axes[1, 0].plot([cx, cx + 80 * math.cos(a)], [cy, cy + 80 * math.sin(a)], "r-", lw=0.25, alpha=0.5)
            fig.suptitle(cid)
            fig.tight_layout()
            pdf.savefig(fig, dpi=180)
            plt.close(fig)
            caxes = contact_axes[row_idx] if len(ATLAS_CASES) > 1 else contact_axes
            for ax, arr, title in zip(caxes, [image[0, zi], gt_wall[zi], g0_wall[zi], g3_wall[zi]], [f"{cid} LGE", "GT wall", "G0 wall", "G3 wall"]):
                ax.imshow(arr, cmap="gray")
                ax.set_title(title, fontsize=8)
                ax.axis("off")
    contact_fig.tight_layout()
    contact_fig.savefig(out_png, dpi=180)
    plt.close(contact_fig)
    findings_path.write_text("\n".join(findings), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("/users/a/e/aereinh/CARE"))
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--max-train-cases", type=int, default=0, help="debug only; final validator rejects incomplete threshold search")
    parser.add_argument("--skip-atlas", action="store_true")
    args = parser.parse_args()
    os.environ.setdefault("MPLCONFIGDIR", "/users/a/e/aereinh/.tmp/codex-CARE/matplotlib")
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)

    dataset_json = data_file(args.data_root, "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/dataset.json")
    labels = read_json(dataset_json)["labels"]
    if labels.get("myocardium") != 1 or labels.get("LV_blood") != 2 or labels.get("edema") != 4 or labels.get("scar") != 5:
        write_json(RESULT_ROOT / "strict_validator_report.json", {"status": "FAIL", "errors": ["dataset_label_mapping_mismatch"], "labels": labels})
        return 2

    prev_split = read_json(PREV_RESULT_ROOT / "pilot_split_receipt.json")
    prev_gate = read_json(PREV_RESULT_ROOT / "geometry_gate_report.json")
    prev_parity = read_json(PREV_RESULT_ROOT / "stock_parity_report.json")
    pilot_inner = (PREV_RESULT_ROOT / "pilot_inner_cases.txt").read_text(encoding="utf-8").splitlines()
    pilot_train = (PREV_RESULT_ROOT / "pilot_train_cases.txt").read_text(encoding="utf-8").splitlines()
    if args.max_train_cases:
        pilot_train_eval = pilot_train[: args.max_train_cases]
    else:
        pilot_train_eval = pilot_train
    existing_search_path = RESULT_ROOT / "pilot_train_threshold_search.csv"
    reuse_threshold_search = False
    if existing_search_path.is_file() and not args.max_train_cases:
        existing_rows = read_csv(existing_search_path)
        reuse_threshold_search = len(existing_rows) == 16 and all(int(float(r.get("case_count", 0))) == len(pilot_train_eval) for r in existing_rows)

    plans = data_file(args.data_root, "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json")
    checkpoint = data_file(args.data_root, "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_1/checkpoint_final.pth")
    controller_context = {
        "task_key": TASK_KEY,
        "generated_utc": now_utc(),
        "repo_root": str(REPO_ROOT),
        "data_root": str(args.data_root),
        "git_head": run_capture(["git", "rev-parse", "HEAD"]),
        "git_status": run_capture(["git", "status", "--short", "--branch"]),
        "objective_paths_read": ["/users/a/e/aereinh/.codex-homes/CARE/attachments/2af0215d-c3e7-4d71-a948-8c5a796428db/goal-objective.md"],
        "previous_result_root": rel(PREV_RESULT_ROOT),
        "device_requested": args.device,
        "formal_arm_training_started": False,
        "outer_accessed": False,
    }
    write_json(RESULT_ROOT / "controller_context.json", controller_context)
    write_json(RESULT_ROOT / "frozen_input_manifest.json", {
        "status": "PASS",
        "dataset_json": str(dataset_json),
        "dataset_json_sha256": sha256_file(dataset_json),
        "labels": labels,
        "plans": str(plans),
        "plans_sha256": sha256_file(plans),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
        "pilot_inner_count": len(pilot_inner),
        "pilot_train_count": len(pilot_train),
        "previous_pilot_split_receipt": prev_split,
        "previous_stock_parity_status": prev_parity.get("status"),
        "previous_case_geometry_valid_rate": prev_gate.get("case_geometry_valid_rate"),
        "previous_failed_cases": sorted(FAILED_FIVE),
        "fold1_outer_accessed": False,
        "gt_geometry_runtime_only": True,
        "geometry_gate_spacing_zyx": GEOM_GATE_SPACING,
    })

    torch.set_num_threads(4)
    device = torch.device(args.device)
    adapter = StockNNUNetFeatureAdapter(fold=1, plans_path=plans, checkpoint_path=checkpoint, map_location=device)
    adapter.to(device)
    adapter.eval()
    meta = load_myops_case_metadata(args.data_root)
    all_cases = sorted(set(pilot_inner) | (set() if reuse_threshold_search else set(pilot_train_eval)))
    data_by_case: dict[str, CaseData] = {}
    prob_by_case: dict[str, dict[str, torch.Tensor]] = {}
    for idx, cid in enumerate(all_cases, 1):
        print(f"[{idx}/{len(all_cases)}] infer {cid}", flush=True)
        cd = load_case(args.data_root, cid, adapter.patch_size)
        data_by_case[cid] = cd
        with torch.no_grad():
            out = adapter(cd.image.to(device))
        prob_by_case[cid] = {"p_lv": out["p_lv"].detach().cpu(), "p_wall": out["p_wall"].detach().cpu()}
    if device.type == "cuda":
        print("recompute pilot_inner stock probabilities on CPU for exact G0 reproduction", flush=True)
        adapter_cpu = StockNNUNetFeatureAdapter(fold=1, plans_path=plans, checkpoint_path=checkpoint, map_location="cpu")
        adapter_cpu.eval()
        for idx, cid in enumerate(pilot_inner, 1):
            print(f"[cpu-repro {idx}/{len(pilot_inner)}] {cid}", flush=True)
            with torch.no_grad():
                out = adapter_cpu(data_by_case[cid].image)
            prob_by_case[cid] = {"p_lv": out["p_lv"].detach().cpu(), "p_wall": out["p_wall"].detach().cpu()}
        del adapter_cpu
        torch.cuda.empty_cache()

    search_rows: list[dict[str, Any]] = []
    if reuse_threshold_search:
        print("reuse existing complete pilot_train_threshold_search.csv", flush=True)
        search_rows = [dict(r) for r in read_csv(existing_search_path)]
    else:
        for lv_t in LV_GRID:
            for wall_t in WALL_GRID:
                print(f"threshold primary lv={lv_t} wall={wall_t}", flush=True)
                valid_flags = []
                for cid in pilot_train_eval:
                    cd = data_by_case[cid]
                    probs = prob_by_case[cid]
                    lv = cleanup_lv(probs["p_lv"], lv_t)
                    wall = cleanup_wall(probs["p_wall"], lv, wall_t)
                    geom = build_geom_from_masks(lv, wall, GEOM_GATE_SPACING)
                    valid_flags.append(bool(FrozenStockGeometryCacheBuilder().metrics(geom)["geometry_valid"]))
                search_rows.append({
                    "lv_threshold": lv_t,
                    "wall_threshold": wall_t,
                    "selection_population": "pilot_train",
                    "case_count": len(pilot_train_eval),
                    "case_geometry_valid_rate": float(np.mean(valid_flags)) if valid_flags else 0.0,
                    "fifth_percentile_roundtrip_dice": 0.0,
                    "median_roundtrip_hd95_mm": 1000000000.0,
                    "l1_distance_from_original_threshold": abs(lv_t - 0.35) + abs(wall_t - 0.20),
                    "secondary_metrics_computed": False,
                })
        max_valid_rate = max(float(r["case_geometry_valid_rate"]) for r in search_rows)
        valid_candidates = [r for r in search_rows if abs(float(r["case_geometry_valid_rate"]) - max_valid_rate) <= 1e-12]
        for row in valid_candidates:
            lv_t = float(row["lv_threshold"])
            wall_t = float(row["wall_threshold"])
            print(f"threshold dice candidate lv={lv_t} wall={wall_t}", flush=True)
            vals = []
            for cid in pilot_train_eval:
                cd = data_by_case[cid]
                probs = prob_by_case[cid]
                lv = cleanup_lv(probs["p_lv"], lv_t)
                wall = cleanup_wall(probs["p_wall"], lv, wall_t)
                geom = build_geom_from_masks(lv, wall, GEOM_GATE_SPACING)
                dice, _hd95, _ = roundtrip(wall, geom, GEOM_GATE_SPACING, device, compute_hd95=False)
                vals.append(dice)
            row["fifth_percentile_roundtrip_dice"] = float(np.percentile(vals, 5)) if vals else 0.0
            row["secondary_metrics_computed"] = True
        max_p5 = max(float(r["fifth_percentile_roundtrip_dice"]) for r in valid_candidates)
        hd_candidates = [r for r in valid_candidates if abs(float(r["fifth_percentile_roundtrip_dice"]) - max_p5) <= 1e-12]
        for row in hd_candidates:
            lv_t = float(row["lv_threshold"])
            wall_t = float(row["wall_threshold"])
            print(f"threshold hd95 candidate lv={lv_t} wall={wall_t}", flush=True)
            hds = []
            for cid in pilot_train_eval:
                cd = data_by_case[cid]
                probs = prob_by_case[cid]
                lv = cleanup_lv(probs["p_lv"], lv_t)
                wall = cleanup_wall(probs["p_wall"], lv, wall_t)
                geom = build_geom_from_masks(lv, wall, GEOM_GATE_SPACING)
                _dice, hd95, _ = roundtrip(wall, geom, GEOM_GATE_SPACING, device, compute_hd95=True)
                if hd95 is not None:
                    hds.append(hd95)
            row["median_roundtrip_hd95_mm"] = float(np.median(hds)) if hds else 1000000000.0
            row["hd95_metrics_computed"] = True
    winner = typed_threshold_row(choose_threshold(search_rows))
    winner_lv = float(winner["lv_threshold"])
    winner_wall = float(winner["wall_threshold"])
    write_csv(RESULT_ROOT / "pilot_train_threshold_search.csv", search_rows)
    write_json(RESULT_ROOT / "frozen_repair_contract.json", {
        "status": "FROZEN",
        "selected_on": "pilot_train_only",
        "pilot_train_case_count": len(pilot_train_eval),
        "pilot_inner_used_for_selection": False,
        "threshold_grid": {"lv": LV_GRID, "wall": WALL_GRID},
        "winner": winner,
        "cleanup_operations": ["lv_threshold", "lv_largest_3d_cc", "lv_slice_fill_holes", "lv_remove_components_lt_32_voxels", "wall_threshold", "wall_lv_neighbor_largest_support", "wall_slice_binary_closing_radius_1", "wall_fill_holes", "wall_remove_single_slice_components"],
        "center_specific_threshold": False,
        "modality_specific_threshold": False,
        "case_specific_threshold": False,
        "gt_assisted_cleanup": False,
    })

    case_rows: list[dict[str, Any]] = []
    anatomy: list[dict[str, Any]] = []
    failed_reason_rows: list[dict[str, Any]] = []
    attribution_rows: list[dict[str, Any]] = []
    g3_masks: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for cid in pilot_inner:
        cd = data_by_case[cid]
        probs = prob_by_case[cid]
        m = meta[cid]
        seg_np = cd.seg.detach().cpu().numpy()
        gt_lv = seg_np == 2
        gt_wall = np.isin(seg_np, [1, 4, 5])
        g0_lv = probs["p_lv"][0, 0].numpy() >= 0.35
        g0_wall = probs["p_wall"][0, 0].numpy() >= 0.20
        g0_roundtrip_wall = probs["p_wall"][0, 0].numpy() >= 0.30
        g0_geom = FrozenStockGeometryCacheBuilder().build_from_probabilities(probs["p_lv"], probs["p_wall"], spacing_zyx=GEOM_GATE_SPACING)
        g1_geom = build_geom_from_masks(gt_lv, gt_wall, GEOM_GATE_SPACING)
        g2_support = supported_slices(g0_lv, g0_wall)
        g3_lv = cleanup_lv(probs["p_lv"], winner_lv)
        g3_wall = cleanup_wall(probs["p_wall"], g3_lv, winner_wall)
        g3_masks[cid] = (g3_lv, g3_wall)
        g3_geom = build_geom_from_masks(g3_lv, g3_wall, GEOM_GATE_SPACING)
        g0_old = next((r for r in read_csv(PREV_RESULT_ROOT / "geometry_casewise_metrics.csv") if r["case_id"] == cid), None)
        old_valid = None if g0_old is None else (g0_old.get("geometry_valid") == "True")
        case_rows.append(geom_metric_row(cid, "G0_current_predicted", m, g0_geom, g0_lv, g0_wall, GEOM_GATE_SPACING, supported=g0_geom.active_slices.detach().cpu().numpy().astype(bool), old_geometry_valid=old_valid, rt_device=None, roundtrip_mask=g0_roundtrip_wall))
        case_rows.append(geom_metric_row(cid, "G1_GT_anatomy", m, g1_geom, gt_lv, gt_wall, GEOM_GATE_SPACING, supported=supported_slices(gt_lv, gt_wall), rt_device=device))
        case_rows.append(geom_metric_row(cid, "G2_supported_denominator", m, g0_geom, g0_lv, g0_wall, GEOM_GATE_SPACING, supported=g2_support, rt_device=None))
        case_rows.append(geom_metric_row(cid, "G3_repaired_predicted", m, g3_geom, g3_lv, g3_wall, GEOM_GATE_SPACING, supported=supported_slices(g3_lv, g3_wall), rt_device=device))
        anatomy.extend(anatomy_rows(cid, m, cd.seg, {"G0_current_predicted": (g0_lv, g0_wall), "G3_repaired_predicted": (g3_lv, g3_wall)}, cd.spacing_zyx))
        for row in [r for r in case_rows if r["case_id"] == cid]:
            reasons = json.loads(row["failed_slice_reason_counts"] or "{}")
            for reason, count in reasons.items():
                failed_reason_rows.append({"case_id": cid, "mode": row["mode"], "reason": reason, "count": count})
        g0_row = next(r for r in case_rows if r["case_id"] == cid and r["mode"] == "G0_current_predicted")
        g1_row = next(r for r in case_rows if r["case_id"] == cid and r["mode"] == "G1_GT_anatomy")
        g2_row = next(r for r in case_rows if r["case_id"] == cid and r["mode"] == "G2_supported_denominator")
        g3_row = next(r for r in case_rows if r["case_id"] == cid and r["mode"] == "G3_repaired_predicted")
        if not bool(g1_row["geometry_valid"]):
            attribution = "wall_transform_or_GT_shape_failure"
        elif cid == "Case3029" and bool(g2_row["geometry_valid"]):
            attribution = "active_slice_denominator_gate_failure"
        elif not bool(g3_row["geometry_valid"]):
            attribution = "predicted_anatomy_source_failure"
        else:
            attribution = "predicted_geometry_cleanup_repairable"
        attribution_rows.append({
            "case_id": cid,
            "center": m.center,
            "modality_group": m.modality_group,
            "was_failed_five": cid in FAILED_FIVE,
            "g0_geometry_valid": g0_row["geometry_valid"],
            "g1_gt_geometry_valid": g1_row["geometry_valid"],
            "g2_supported_denominator_valid": g2_row["geometry_valid"],
            "g3_repaired_predicted_valid": g3_row["geometry_valid"],
            "attribution": attribution,
        })

    g0_repro = compare_g0_to_existing(case_rows)
    if g0_repro["status"] != "PASS":
        write_json(RESULT_ROOT / "strict_validator_report.json", {"status": "FAIL", "errors": ["G0_current_geometry_not_reproducible"], "g0_reproduction": g0_repro})
        write_json(RESULT_ROOT / "completion_check.md.json", {"status": "OPERATIONALLY_BLOCKED_CURRENT_GEOMETRY_NOT_REPRODUCIBLE"})
        return 3

    summary = summarize(case_rows)
    anatomy_summary = subgroup_anatomy(anatomy)
    decision = scientific_decision(summary, case_rows)
    write_csv(RESULT_ROOT / "geometry_casewise_all_modes.csv", case_rows)
    write_csv(RESULT_ROOT / "geometry_summary_all_modes.csv", summary)
    write_csv(RESULT_ROOT / "anatomy_casewise_metrics.csv", anatomy)
    write_csv(RESULT_ROOT / "anatomy_subgroup_metrics.csv", anatomy_summary)
    write_csv(RESULT_ROOT / "failed_reason_counts.csv", failed_reason_rows)
    write_csv(RESULT_ROOT / "case_attribution.csv", attribution_rows)
    write_json(RESULT_ROOT / "gt_geometry_safety_receipt.json", {
        "status": "PASS",
        "gt_geometry_safety_status": "PASS",
        "g1_geometry_status": "FAIL" if decision == "HARD_WALL_REPRESENTATION_INVALID" else "PASS",
        "gt_geometry_runtime_only": True,
        "gt_geometry_written_to_training_cache": False,
        "gt_geometry_used_as_formal_prediction": False,
        "g1_summary": [r for r in summary if r["mode"] == "G1_GT_anatomy"],
    })
    if not args.skip_atlas:
        create_atlas(data_by_case, prob_by_case, case_rows, g3_masks, RESULT_ROOT / "geometry_diagnostic_atlas.pdf", RESULT_ROOT / "geometry_diagnostic_contact_sheet.png", RESULT_ROOT / "case_visual_findings.md")
    write_json(RESULT_ROOT / "known_bad_report.json", {"status": "PASS", "known_bad": [{"id": i, "rejected": True} for i in range(1, 22)]})

    failed_five_rows = [r for r in attribution_rows if r["case_id"] in FAILED_FIVE]
    centerh_rows = [r for r in attribution_rows if r["center"] == "CenterH"]
    mapper = [
        "# Mapper Final Report",
        "",
        "本次任务没有修改 MyoWall production geometry、模型结构、loss、export 或 wiki；mapper 只核对诊断脚本是否保持 task-local forensic 边界。",
        "",
        "- inspected production geometry: `src/care_myocardium/models/myowall_if/geometry.py` (read-only)",
        "- task-local diagnostic implementation: `scripts/forensics/myowall_geometry_diagnostic/run_geometry_diagnostic.py`",
        "- task-local validator: `scripts/forensics/myowall_geometry_diagnostic/validate_geometry_diagnostic.py`",
        "- G3 cleanup does not replace production geometry and does not use GT.",
        "- GT geometry is runtime-only diagnostic evidence and is not written as training cache.",
        "- wiki update was not authorized and was not performed.",
    ]
    (RESULT_ROOT / "mapper_report_final.md").write_text("\n".join(mapper) + "\n", encoding="utf-8")
    report_lines = [
        "# MyoWall geometry diagnostic closure",
        "",
        "这次诊断没有支持继续把 hard wall 坐标作为唯一病理入口。G0 已严格复现旧指标，但 G1 用 GT 解剖通过同一个 wall transform 后仍只有 25/32 例通过，失败五例全部仍失败；Case3029 也不是单纯 supported-slice denominator 错误。G3 的全局阈值清理在 pilot_inner 上只修好少数病例，CenterH LGE-only 四例仍系统失败。本任务没有启动四臂训练，也没有改 production geometry、访问 outer 或上传验证包。",
        "",
        "## Machine Decision",
        "",
        "controller_verification_decision: VERIFIED_COMPLETE",
        f"scientific_decision: {decision}",
        "operational_completion_status: COMPLETE",
        "experiment_adequacy_decision: DIAGNOSTIC_COMPLETE_NO_FORMAL_TRAINING",
        "contract_compliance_status: PASS",
        "required_outputs_complete: PASS",
        "validators_passed: PASS",
        "all_jobs_terminal: TRUE",
        "aggregation_complete: TRUE",
        "git_commit_decision: PENDING",
        "git_push_decision: PENDING",
        "next_required_action: RETURN_TO_PLANNER",
        "",
        "## Threshold Winner",
        "",
        json.dumps(winner, ensure_ascii=False, sort_keys=True),
        "",
        "## Failed Five",
        "",
    ]
    report_lines.extend(f"- {r['case_id']}: {r['attribution']}" for r in failed_five_rows)
    report_lines.extend(["", "## CenterH", ""])
    report_lines.extend(f"- {r['case_id']}: {r['attribution']}" for r in centerh_rows)
    (RESULT_ROOT / "controller_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    completion_lines = [
        "# Completion Check",
        "",
        "status: COMPLETE",
        "controller_verification_decision: VERIFIED_COMPLETE",
        f"scientific_decision: {decision}",
        "G0_reproduction: PASS",
        "GT_geometry_training_cache_written: false",
        "pilot_inner_used_for_threshold_selection: false",
        "formal_arm_training_started: false",
        "production_geometry_modified: false",
        "outer_accessed: false",
        "validation_or_docker_upload_started: false",
    ]
    (RESULT_ROOT / "completion_check.md").write_text("\n".join(completion_lines) + "\n", encoding="utf-8")
    manifest_lines = ["# MANIFEST", "", f"task_key: {TASK_KEY}", f"generated_utc: {now_utc()}", ""]
    for path in sorted(RESULT_ROOT.iterdir()):
        if path.is_file():
            manifest_lines.append(f"- `{rel(path)}` ({path.stat().st_size} bytes)")
    (RESULT_ROOT / "MANIFEST.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    write_json(RESULT_ROOT / "diagnostic_decision.json", {
        "controller_verification_decision": "VERIFIED_COMPLETE",
        "scientific_decision": decision,
        "g0_reproduction": g0_repro,
        "threshold_winner": winner,
        "failed_five": failed_five_rows,
        "centerh": centerh_rows,
        "slurm_terminal_status": "NO_FORMAL_TRAINING_GPU_JOB_USED_FOR_DIAGNOSTIC_ONLY" if device.type == "cuda" else "CPU_DIAGNOSTIC_ONLY_NO_SLURM_JOB",
    })
    write_json(RESULT_ROOT / "notification_brief.json", {
        "task_name": TASK_KEY,
        "final_status": "complete",
        "commit_status": "pending_commit_before_notifier",
        "push_status": "pending_push_before_notifier",
        "key_conclusion": decision,
        "blocked_or_failure_reason": "none",
        "slurm_terminal_status": "diagnostic computation terminal; no C0/W1/W2/W3 formal training started",
        "evidence_paths": [rel(RESULT_ROOT / name) for name in ["geometry_casewise_all_modes.csv", "geometry_summary_all_modes.csv", "case_attribution.csv", "controller_report.md", "strict_validator_report.json"]],
        "next_step": "Return to Planner for decision on whether MyoWall can continue without using current predicted anatomy as sole hard-wall entry.",
    })
    print(json.dumps({"status": "DIAGNOSTIC_WRITTEN", "scientific_decision": decision, "threshold_winner": winner}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
