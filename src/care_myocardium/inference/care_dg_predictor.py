"""Inference helpers for CARE-DG."""

from __future__ import annotations

import torch

from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL, CAREDG


def decode_care_dg_logits(final_logits: torch.Tensor) -> dict[str, torch.Tensor]:
    mask = final_logits.argmax(dim=1)
    scar = mask == SCAR_CHANNEL
    edema_zone = (mask == EDEMA_CHANNEL) | scar
    return {
        "mask": mask,
        "scar": scar,
        "edema_zone": edema_zone,
        "pure_edema": edema_zone & ~scar,
    }


@torch.no_grad()
def predict_care_dg(model: CAREDG, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    model.eval()
    outputs = model(
        batch["images"],
        batch["availability"],
        batch["anchor_logits"],
        uncertainty=batch.get("uncertainty"),
        myocardium_support=batch.get("myocardium_support"),
        edema_support=batch.get("edema_support"),
        distance_to_myocardium=batch.get("distance_to_myocardium"),
        t2_present=batch.get("t2_present"),
        strict_inputs=bool(batch.get("strict_inputs", False)),
        anchor_value_kind=batch.get("anchor_value_kind"),
    )
    outputs.update(decode_care_dg_logits(outputs["final_logits"]))
    return outputs
