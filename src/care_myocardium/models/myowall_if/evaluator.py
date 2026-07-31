"""Pilot evaluator helpers for final-label scar and pure-edema metrics."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt, generate_binary_structure, label


class MyoWallPilotEvaluator:
    """Computes case-wise metrics required by the MyoWall-IF pilot."""

    def dice(self, pred: np.ndarray, gt: np.ndarray, class_id: int, *, skip_if_gt_empty: bool = True) -> float | None:
        pm = pred == class_id
        gm = gt == class_id
        if skip_if_gt_empty and not gm.any():
            return None
        den = int(pm.sum() + gm.sum())
        return 1.0 if den == 0 else float(2 * np.logical_and(pm, gm).sum() / den)

    def surface_distances(self, mask: np.ndarray, ref: np.ndarray, spacing_zyx: tuple[float, float, float]) -> np.ndarray:
        if not mask.any() or not ref.any():
            return np.array([], dtype=np.float64)
        struct = generate_binary_structure(mask.ndim, 1)
        surf_m = mask & ~binary_erosion(mask, structure=struct)
        surf_r = ref & ~binary_erosion(ref, structure=struct)
        return distance_transform_edt(~surf_r, sampling=spacing_zyx)[surf_m]

    def hd95(self, pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, float, float]) -> float | None:
        pm = pred == class_id
        gm = gt == class_id
        if not pm.any() or not gm.any():
            return None
        d = np.concatenate([self.surface_distances(pm, gm, spacing_zyx), self.surface_distances(gm, pm, spacing_zyx)])
        return float(np.percentile(d, 95)) if d.size else None

    def exact_hd(self, pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, float, float]) -> float | None:
        pm = pred == class_id
        gm = gt == class_id
        if not pm.any() or not gm.any():
            return None
        d = np.concatenate([self.surface_distances(pm, gm, spacing_zyx), self.surface_distances(gm, pm, spacing_zyx)])
        return float(d.max()) if d.size else None

    def component_metrics(self, pred: np.ndarray, gt: np.ndarray, class_id: int, spacing_zyx: tuple[float, float, float]) -> dict[str, Any]:
        pm = pred == class_id
        gm = gt == class_id
        cc, n_cc = label(pm, structure=generate_binary_structure(pm.ndim, 1))
        fp = pm & ~gm
        fp_cc, n_fp = label(fp, structure=generate_binary_structure(fp.ndim, 1))
        myocardium = (gt == 1) | (gt == 4) | (gt == 5)
        if myocardium.any():
            dist = distance_transform_edt(~myocardium.astype(bool), sampling=spacing_zyx)
            remote = fp & (dist > 10.0)
        else:
            remote = fp
        spacing_volume = float(np.prod(spacing_zyx))
        return {
            "component_count": int(n_cc),
            "fp_component_count": int(n_fp),
            "remote_fp_volume_mm3": float(remote.sum() * spacing_volume),
            "pred_volume_mm3": float(pm.sum() * spacing_volume),
            "gt_volume_mm3": float(gm.sum() * spacing_volume),
        }
