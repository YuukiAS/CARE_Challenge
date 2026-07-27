"""Training losses and checkpoint helpers for CARE-DG."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL, CAREDG, CAREDGConfig


def make_error_targets(labels: torch.Tensor, anchor_mask: torch.Tensor, channel: int) -> dict[str, torch.Tensor]:
    if labels.ndim == 5:
        labels = labels[:, 0]
    if anchor_mask.ndim == 5:
        anchor_mask = anchor_mask[:, 0]
    gt = labels == int(channel)
    pred = anchor_mask == int(channel)
    return {
        "fn": (gt & ~pred).float().unsqueeze(1),
        "fp": (~gt & pred).float().unsqueeze(1),
        "gt": gt.float().unsqueeze(1),
        "anchor_pred": pred.float().unsqueeze(1),
    }


def binary_dice_loss(logits: torch.Tensor, target: torch.Tensor, eps: float = 1e-5) -> torch.Tensor:
    prob = torch.sigmoid(logits)
    dims = tuple(range(2, prob.ndim))
    inter = (prob * target).sum(dim=dims)
    denom = prob.sum(dim=dims) + target.sum(dim=dims)
    return (1.0 - (2.0 * inter + eps) / (denom + eps)).mean()


def focal_bce(prob: torch.Tensor, target: torch.Tensor, gamma: float = 2.0, eps: float = 1e-4) -> torch.Tensor:
    prob32 = prob.float().clamp(float(eps), 1.0 - float(eps))
    target32 = target.float()
    pt = torch.where(target32 > 0.5, prob32, 1.0 - prob32).clamp(float(eps), 1.0)
    bce = -(target32 * prob32.log() + (1.0 - target32) * (1.0 - prob32).clamp(float(eps), 1.0).log())
    return ((1.0 - pt).pow(gamma) * bce).mean()


def care_dg_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    anchor_mask: torch.Tensor,
    *,
    t2_present: torch.Tensor,
    margin: float = 1.0,
) -> tuple[torch.Tensor, dict[str, float]]:
    if labels.ndim == 5:
        labels = labels[:, 0]
    if anchor_mask.ndim == 5:
        anchor_mask = anchor_mask[:, 0]
    final_logits = outputs["final_logits"]
    ce = F.cross_entropy(final_logits, labels.long())
    scar_targets = make_error_targets(labels, anchor_mask, SCAR_CHANNEL)
    edema_targets = make_error_targets(labels, anchor_mask, EDEMA_CHANNEL)
    t2 = t2_present.to(final_logits.device, final_logits.dtype).view(-1, 1, 1, 1, 1)

    scar_final_binary = final_logits[:, SCAR_CHANNEL : SCAR_CHANNEL + 1] - final_logits[:, :SCAR_CHANNEL].amax(dim=1, keepdim=True)
    edema_final_binary = final_logits[:, EDEMA_CHANNEL : EDEMA_CHANNEL + 1] - torch.cat(
        [final_logits[:, :EDEMA_CHANNEL], final_logits[:, EDEMA_CHANNEL + 1 :]], dim=1
    ).amax(dim=1, keepdim=True)

    scar_seg = binary_dice_loss(scar_final_binary, scar_targets["gt"])
    edema_seg = binary_dice_loss(edema_final_binary, edema_targets["gt"]) * t2.mean().clamp(0.0, 1.0)
    scar_gate = focal_bce(outputs["scar_q_fn"], scar_targets["fn"]) + focal_bce(outputs["scar_q_fp"], scar_targets["fp"])
    edema_gate = (focal_bce(outputs["edema_q_fn"], edema_targets["fn"]) + focal_bce(outputs["edema_q_fp"], edema_targets["fp"])) * t2.mean().clamp(0.0, 1.0)

    anchor_logits = outputs["anchor_logits"].detach()
    scar_anchor_margin = anchor_logits[:, SCAR_CHANNEL : SCAR_CHANNEL + 1] - anchor_logits[:, :SCAR_CHANNEL].amax(dim=1, keepdim=True)
    edema_anchor_margin = anchor_logits[:, EDEMA_CHANNEL : EDEMA_CHANNEL + 1] - torch.cat(
        [anchor_logits[:, :EDEMA_CHANNEL], anchor_logits[:, EDEMA_CHANNEL + 1 :]], dim=1
    ).amax(dim=1, keepdim=True)
    scar_error = (scar_targets["fn"] + scar_targets["fp"]).clamp(0, 1)
    edema_error = (edema_targets["fn"] + edema_targets["fp"]).clamp(0, 1) * t2
    scar_margin = (F.relu(margin - (scar_final_binary - scar_anchor_margin)) * scar_error).mean()
    edema_margin = (F.relu(margin - (edema_final_binary - edema_anchor_margin)) * edema_error).mean()
    correct = ((labels == anchor_mask).float().unsqueeze(1)).detach()
    identity = ((outputs["scar_delta"].abs() + outputs["edema_delta"].abs()) * correct).mean()
    remote = (
        outputs["scar_delta"].abs() * (1.0 - outputs["scar_support"])
        + outputs["edema_delta"].abs() * (1.0 - outputs["edema_support"])
    ).mean()
    total = ce + scar_seg + edema_seg + 0.5 * (scar_gate + edema_gate) + 0.25 * (scar_margin + edema_margin) + 0.10 * identity + 0.10 * remote
    metrics = {
        "loss": float(total.detach().cpu()),
        "ce": float(ce.detach().cpu()),
        "scar_seg": float(scar_seg.detach().cpu()),
        "edema_seg": float(edema_seg.detach().cpu()),
        "scar_gate": float(scar_gate.detach().cpu()),
        "edema_gate": float(edema_gate.detach().cpu()),
        "identity": float(identity.detach().cpu()),
        "remote": float(remote.detach().cpu()),
    }
    return total, metrics


def save_care_dg_checkpoint(path: Path, model: CAREDG, optimizer: torch.optim.Optimizer, step: int, extra: dict[str, Any] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "step": int(step),
            "config": model.config.__dict__,
            "extra": extra or {},
        },
        path,
    )


def load_care_dg_checkpoint(path: Path, model: CAREDG | None = None, optimizer: torch.optim.Optimizer | None = None) -> tuple[CAREDG, int, dict[str, Any]]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if model is None:
        model = CAREDG(CAREDGConfig(**payload["config"]))
    model.load_state_dict(payload["model_state"])
    if optimizer is not None and "optimizer_state" in payload:
        optimizer.load_state_dict(payload["optimizer_state"])
    return model, int(payload.get("step", 0)), dict(payload.get("extra", {}))
