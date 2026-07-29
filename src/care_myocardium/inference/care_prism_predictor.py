"""Inference helpers for CARE-PRISM v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch


@dataclass(frozen=True)
class CAREPRISMDecodeConfig:
    scar_threshold: float = 0.50
    edema_threshold: float = 0.50


def decode_care_prism_outputs(
    outputs: dict[str, Any],
    availability: torch.Tensor,
    config: CAREPRISMDecodeConfig | None = None,
) -> dict[str, Any]:
    cfg = config or CAREPRISMDecodeConfig()
    scar_prob = outputs["scar_probability"].detach().cpu().numpy()[0, 0].astype(np.float32)
    t2_present = bool(float(availability.detach().cpu().flatten()[1]) > 0.5)
    if t2_present:
        edema_prob = outputs["edema_probability"].detach().cpu().numpy()[0, 0].astype(np.float32)
        edema_zone = edema_prob >= float(cfg.edema_threshold)
    else:
        edema_prob = np.zeros_like(scar_prob, dtype=np.float32)
        edema_zone = np.zeros_like(scar_prob, dtype=bool)
    scar = scar_prob >= float(cfg.scar_threshold)
    pure_edema = edema_zone & ~scar
    compact = np.zeros_like(scar, dtype=np.uint8)
    compact[pure_edema] = 4
    compact[scar] = 5
    return {
        "compact_pathology": compact,
        "scar_mask": scar.astype(np.uint8),
        "edema_zone_mask": edema_zone.astype(np.uint8),
        "pure_edema_mask": pure_edema.astype(np.uint8),
        "scar_probability": scar_prob,
        "edema_probability": edema_prob,
        "no_t2_edema_exact_zero": (not t2_present and float(edema_prob.max()) == 0.0 and int(edema_zone.sum()) == 0),
    }


def predict_with_tta(model: torch.nn.Module, images: torch.Tensor, availability: torch.Tensor) -> dict[str, Any]:
    probs: dict[str, list[torch.Tensor]] = {"scar": [], "edema": []}
    aux: dict[str, Any] | None = None
    for dims in ((), (-1,), (-2,), (-1, -2)):
        x = torch.flip(images, dims=dims) if dims else images
        out = model(x, availability)
        scar = out["scar_probability"]
        edema = out["edema_probability"]
        if dims:
            scar = torch.flip(scar, dims=dims)
            edema = torch.flip(edema, dims=dims)
        probs["scar"].append(scar)
        probs["edema"].append(edema)
        if aux is None:
            aux = out
    assert aux is not None
    aux["scar_probability"] = torch.stack(probs["scar"]).mean(dim=0)
    aux["edema_probability"] = torch.stack(probs["edema"]).mean(dim=0) * availability[:, 1:2].view(-1, 1, 1, 1, 1).to(images)
    return aux
