"""Inference and decode utilities for CARE-ARC."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from scipy import ndimage as ndi


@dataclass(frozen=True)
class CAREARCDecodeConfig:
    scar_threshold: float = 0.40
    edema_threshold: float = 0.35
    scar_min_component_mm3: float = 25.0
    edema_min_component_mm3: float = 50.0
    presence_rescue_threshold: float = 0.70
    bridge_distance_mm: float = 3.0
    tta_flips: tuple[tuple[int, ...], ...] = ((), (-1,), (-2,), (-1, -2))


def _remove_small_components(mask: np.ndarray, spacing_zyx: tuple[float, float, float], min_volume_mm3: float) -> np.ndarray:
    if min_volume_mm3 <= 0 or not mask.any():
        return mask.astype(bool, copy=False)
    labeled, n = ndi.label(mask)
    if n == 0:
        return mask.astype(bool, copy=False)
    voxel = float(np.prod(spacing_zyx))
    keep = np.zeros_like(mask, dtype=bool)
    for idx in range(1, n + 1):
        comp = labeled == idx
        if float(comp.sum()) * voxel >= float(min_volume_mm3):
            keep |= comp
    return keep


def _bridge(mask: np.ndarray, spacing_zyx: tuple[float, float, float], distance_mm: float) -> np.ndarray:
    if distance_mm <= 0 or not mask.any():
        return mask.astype(bool, copy=False)
    radius = [max(1, int(round(float(distance_mm) / max(s, 1.0e-6)))) for s in spacing_zyx]
    structure = np.ones(tuple(2 * r + 1 for r in radius), dtype=bool)
    return ndi.binary_closing(mask, structure=structure)


def decode_care_arc_outputs(
    outputs: dict[str, Any],
    availability: torch.Tensor,
    spacing_zyx: tuple[float, float, float],
    config: CAREARCDecodeConfig | None = None,
) -> dict[str, Any]:
    cfg = config or CAREARCDecodeConfig()
    scar_prob = torch.sigmoid(outputs["scar_direct_logit"]).detach().cpu().numpy()[0, 0]
    edema_prob = torch.sigmoid(outputs["edema_zone_direct_logit"]).detach().cpu().numpy()[0, 0]
    scar_presence = float(torch.sigmoid(outputs["scar"]["presence_logit"]).detach().cpu().flatten()[0])
    edema_presence = float(torch.sigmoid(outputs["edema"]["presence_logit"]).detach().cpu().flatten()[0])
    t2_present = bool(float(availability.detach().cpu().flatten()[1]) > 0.5)
    scar = scar_prob >= float(cfg.scar_threshold)
    edema = edema_prob >= float(cfg.edema_threshold) if t2_present else np.zeros_like(scar, dtype=bool)
    if scar_presence >= cfg.presence_rescue_threshold and not scar.any():
        lower = max(0.01, float(cfg.scar_threshold) - 0.05)
        scar = scar_prob >= lower
    if t2_present and edema_presence >= cfg.presence_rescue_threshold and not edema.any():
        lower = max(0.01, float(cfg.edema_threshold) - 0.05)
        coarse = torch.sigmoid(outputs["edema"]["coarse_extent_logit"]).detach().cpu().numpy()[0, 0]
        coarse = ndi.zoom(coarse, [edema_prob.shape[i] / coarse.shape[i] for i in range(3)], order=1)
        edema = (edema_prob >= lower) & (coarse >= lower)
    scar = _bridge(scar, spacing_zyx, cfg.bridge_distance_mm)
    edema = _bridge(edema, spacing_zyx, cfg.bridge_distance_mm) if t2_present else edema
    scar = _remove_small_components(scar, spacing_zyx, cfg.scar_min_component_mm3)
    edema = _remove_small_components(edema, spacing_zyx, cfg.edema_min_component_mm3) if t2_present else edema
    edema = edema & ~scar
    compact = np.zeros_like(scar, dtype=np.uint8)
    compact[edema] = 4
    compact[scar] = 5
    return {
        "compact_pathology": compact,
        "scar_mask": scar.astype(np.uint8),
        "edema_zone_mask": (edema | scar).astype(np.uint8),
        "pure_edema_mask": edema.astype(np.uint8),
        "scar_probability": scar_prob.astype(np.float32),
        "edema_zone_probability": edema_prob.astype(np.float32),
        "scar_presence_probability": scar_presence,
        "edema_presence_probability": edema_presence if t2_present else 0.0,
        "no_t2_edema_exact_zero": (not t2_present and int(edema.sum()) == 0),
    }


def predict_with_tta(model: torch.nn.Module, images: torch.Tensor, availability: torch.Tensor, *, alignment_mode: str = "enabled") -> dict[str, Any]:
    probs: dict[str, list[torch.Tensor]] = {"scar": [], "edema": []}
    aux = None
    for dims in CAREARCDecodeConfig().tta_flips:
        x = torch.flip(images, dims=dims) if dims else images
        out = model(x, availability, alignment_mode=alignment_mode)
        scar = out["scar_direct_logit"]
        edema = out["edema_zone_direct_logit"]
        if dims:
            scar = torch.flip(scar, dims=dims)
            edema = torch.flip(edema, dims=dims)
        probs["scar"].append(torch.sigmoid(scar))
        probs["edema"].append(torch.sigmoid(edema))
        if aux is None:
            aux = out
    assert aux is not None
    aux["scar_direct_logit"] = torch.logit(torch.stack(probs["scar"]).mean(dim=0).clamp(1.0e-5, 1.0 - 1.0e-5))
    aux["edema_zone_direct_logit"] = torch.logit(torch.stack(probs["edema"]).mean(dim=0).clamp(1.0e-5, 1.0 - 1.0e-5))
    aux["scar"]["direct_full_logit"] = aux["scar_direct_logit"]
    aux["edema"]["direct_full_logit"] = aux["edema_zone_direct_logit"]
    return aux
