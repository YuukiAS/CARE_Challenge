"""Training helpers for CARE-ARC."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
from scipy import ndimage as ndi
from torch import nn
import torch.nn.functional as F

from src.care_myocardium.models.care_arc import CAREARC, CAREARCConfig, build_care_arc


def stable_json_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def dice_loss_from_logits(logits: torch.Tensor, target: torch.Tensor, eps: float = 1.0e-5) -> torch.Tensor:
    probs = torch.sigmoid(logits)
    dims = tuple(range(1, probs.ndim))
    inter = (probs * target).sum(dim=dims)
    denom = probs.sum(dim=dims) + target.sum(dim=dims)
    return (1.0 - (2.0 * inter + eps) / (denom + eps)).mean()


def focal_bce_from_logits(logits: torch.Tensor, target: torch.Tensor, gamma: float = 2.0) -> torch.Tensor:
    bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    probs = torch.sigmoid(logits)
    pt = torch.where(target > 0.5, probs, 1.0 - probs)
    return ((1.0 - pt).pow(gamma) * bce).mean()


def focal_tversky_loss(logits: torch.Tensor, target: torch.Tensor, alpha_fn: float = 0.70, beta_fp: float = 0.30, eps: float = 1.0e-5) -> torch.Tensor:
    probs = torch.sigmoid(logits)
    dims = tuple(range(1, probs.ndim))
    tp = (probs * target).sum(dim=dims)
    fn = ((1.0 - probs) * target).sum(dim=dims)
    fp = (probs * (1.0 - target)).sum(dim=dims)
    tversky = (tp + eps) / (tp + alpha_fn * fn + beta_fp * fp + eps)
    return (1.0 - tversky).mean()


def direct_reconstruction_loss(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    return dice_loss_from_logits(logits, target) + 0.5 * focal_bce_from_logits(logits, target) + 0.5 * focal_tversky_loss(logits, target)


def resize_target(target: torch.Tensor, size: tuple[int, int, int]) -> torch.Tensor:
    return F.interpolate(target.float(), size=size, mode="nearest")


def case_presence_target(target: torch.Tensor) -> torch.Tensor:
    return (target.flatten(1).sum(dim=1, keepdim=True) > 0).to(dtype=target.dtype)


def log_burden_target(target: torch.Tensor, myocardium: torch.Tensor, spacing_zyx: torch.Tensor) -> torch.Tensor:
    voxel_mm3 = spacing_zyx.prod(dim=1, keepdim=True).to(device=target.device, dtype=target.dtype)
    lesion = target.flatten(1).sum(dim=1, keepdim=True) * voxel_mm3
    myo = myocardium.flatten(1).sum(dim=1, keepdim=True).clamp_min(0.0) * voxel_mm3
    return torch.log((lesion + 1.0) / (myo + 1.0))


def prediction_log_burden(logits: torch.Tensor, myocardium: torch.Tensor, spacing_zyx: torch.Tensor) -> torch.Tensor:
    voxel_mm3 = spacing_zyx.prod(dim=1, keepdim=True).to(device=logits.device, dtype=logits.dtype)
    lesion = torch.sigmoid(logits).flatten(1).sum(dim=1, keepdim=True) * voxel_mm3
    myo = myocardium.flatten(1).sum(dim=1, keepdim=True).clamp_min(0.0) * voxel_mm3
    return torch.log((lesion + 1.0) / (myo + 1.0))


def sdf_target_from_mask(mask: torch.Tensor, spacing_zyx: torch.Tensor) -> torch.Tensor:
    masks = mask.detach().cpu().numpy() > 0.5
    spacing_np = spacing_zyx.detach().cpu().numpy()
    out = np.zeros_like(masks, dtype=np.float32)
    for b in range(masks.shape[0]):
        m = masks[b, 0]
        if m.any():
            inside = ndi.distance_transform_edt(m, sampling=spacing_np[b])
            outside = ndi.distance_transform_edt(~m, sampling=spacing_np[b])
            sdf = inside - outside
        else:
            sdf = -ndi.distance_transform_edt(np.ones_like(m, dtype=bool), sampling=spacing_np[b])
        out[b, 0] = np.clip(sdf, -15.0, 15.0) / 15.0
    return torch.from_numpy(out).to(device=mask.device, dtype=mask.dtype)


def sdf_nll(mean: torch.Tensor, logvar: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    logvar = logvar.clamp(-5.0, 3.0)
    return (0.5 * torch.exp(-logvar) * (mean - target).pow(2) + 0.5 * logvar).mean()


def _pathology_loss(
    outputs: dict[str, torch.Tensor],
    target: torch.Tensor,
    myocardium: torch.Tensor,
    spacing_zyx: torch.Tensor,
    active_mask: torch.Tensor,
    prefix: str,
    sdf_target: torch.Tensor | None = None,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    active = active_mask.view(-1, 1).to(device=target.device, dtype=target.dtype)
    if float(active.sum().detach().cpu()) == 0.0:
        zero = outputs["direct_full_logit"].sum() * 0.0
        return zero, {
            f"{prefix}_active": zero.detach(),
            f"{prefix}_direct": zero.detach(),
            f"{prefix}_coarse": zero.detach(),
            f"{prefix}_presence": zero.detach(),
            f"{prefix}_burden_head": zero.detach(),
            f"{prefix}_burden_consistency": zero.detach(),
            f"{prefix}_sdf": zero.detach(),
        }
    direct = direct_reconstruction_loss(outputs["direct_full_logit"], target)
    coarse_target = resize_target(target, outputs["coarse_extent_logit"].shape[-3:])
    coarse = dice_loss_from_logits(outputs["coarse_extent_logit"], coarse_target) + F.binary_cross_entropy_with_logits(outputs["coarse_extent_logit"], coarse_target)
    presence_target = case_presence_target(target)
    presence = F.binary_cross_entropy_with_logits(outputs["presence_logit"], presence_target, reduction="none")
    presence = (presence * active).sum() / active.sum().clamp_min(1.0)
    burden_target = log_burden_target(target, myocardium, spacing_zyx)
    burden_head = F.smooth_l1_loss(outputs["log_burden_pred"], burden_target, reduction="none")
    burden_head = (burden_head * active).sum() / active.sum().clamp_min(1.0)
    burden_consistency = (prediction_log_burden(outputs["direct_full_logit"], myocardium, spacing_zyx) - outputs["log_burden_pred"].detach()).abs()
    burden_consistency = (burden_consistency * active).sum() / active.sum().clamp_min(1.0)
    if sdf_target is None:
        sdf_target = sdf_target_from_mask(target, spacing_zyx)
    else:
        sdf_target = sdf_target.to(device=target.device, dtype=target.dtype)
    sdf = sdf_nll(outputs["sdf_mean"], outputs["sdf_logvar"], sdf_target)
    total = direct + 0.30 * coarse + 0.15 * presence + 0.10 * burden_head + 0.05 * burden_consistency + 0.15 * sdf
    return total, {
        f"{prefix}_active": total.detach(),
        f"{prefix}_direct": direct.detach(),
        f"{prefix}_coarse": coarse.detach(),
        f"{prefix}_presence": presence.detach(),
        f"{prefix}_burden_head": burden_head.detach(),
        f"{prefix}_burden_consistency": burden_consistency.detach(),
        f"{prefix}_sdf": sdf.detach(),
    }


def care_arc_loss(model_outputs: dict[str, Any], batch: dict[str, Any]) -> tuple[torch.Tensor, dict[str, float]]:
    scar_target = batch["scar_target"].to(model_outputs["scar_direct_logit"])
    edema_target = batch["edema_zone_target"].to(model_outputs["edema_zone_direct_logit"])
    myocardium = batch["myocardium_target"].to(model_outputs["scar_direct_logit"])
    spacing = batch["spacing_zyx"].to(model_outputs["scar_direct_logit"])
    t2_present = batch["t2_present"].to(model_outputs["scar_direct_logit"]).view(-1, 1)
    anatomy_target = batch["anatomy_target"].to(device=model_outputs["anatomy_logits"].device, dtype=torch.long)
    anatomy = F.cross_entropy(model_outputs["anatomy_logits"], anatomy_target)
    scar_loss, scar_metrics = _pathology_loss(
        model_outputs["scar"],
        scar_target,
        myocardium,
        spacing,
        torch.ones_like(t2_present),
        "scar",
        batch.get("scar_sdf_target"),
    )
    edema_loss, edema_metrics = _pathology_loss(
        model_outputs["edema"],
        edema_target,
        myocardium,
        spacing,
        t2_present,
        "edema",
        batch.get("edema_sdf_target"),
    )
    inclusiveness = torch.relu(torch.sigmoid(model_outputs["scar_direct_logit"]) - torch.sigmoid(model_outputs["edema_zone_direct_logit"])).mean()
    align = (
        model_outputs["alignment"]["t2_offset"].pow(2).mean()
        + model_outputs["alignment"]["c0_offset"].pow(2).mean()
    )
    total = scar_loss + edema_loss + 0.30 * anatomy + 0.10 * inclusiveness * t2_present.mean() + 0.01 * align
    metrics = {"loss": float(total.detach().cpu()), "anatomy": float(anatomy.detach().cpu())}
    metrics.update({k: float(v.cpu()) for k, v in scar_metrics.items()})
    metrics.update({k: float(v.cpu()) for k, v in edema_metrics.items()})
    metrics["alignment"] = float(align.detach().cpu())
    return total, metrics


def optimizer_for_care_arc(model: nn.Module, *, stage: str = "A") -> torch.optim.Optimizer:
    if stage == "B":
        lr = 2.0e-5
        return torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1.0e-4)
    encoder_params: list[torch.nn.Parameter] = []
    care_params: list[torch.nn.Parameter] = []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if name.startswith("encoder."):
            encoder_params.append(param)
        else:
            care_params.append(param)
    return torch.optim.AdamW(
        [
            {"params": encoder_params, "lr": 2.0e-5},
            {"params": care_params, "lr": 1.0e-4},
        ],
        weight_decay=1.0e-4,
    )


def save_care_arc_checkpoint(
    path: Path,
    model: CAREARC,
    optimizer: torch.optim.Optimizer,
    *,
    step: int,
    config: CAREARCConfig,
    contract_hash: str,
    sampler_state: dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "step": int(step),
            "config": config.__dict__,
            "contract_hash": contract_hash,
            "torch_rng_state": torch.random.get_rng_state(),
            "numpy_rng_state": np.random.get_state(),
            "python_rng_state": random.getstate(),
            "sampler_state": sampler_state or {},
        },
        path,
    )


def load_care_arc_checkpoint(path: Path, *, map_location: str | torch.device = "cpu") -> tuple[CAREARC, dict[str, Any]]:
    payload = torch.load(path, map_location=map_location, weights_only=False)
    config = CAREARCConfig(**payload.get("config", {}))
    model = build_care_arc(config)
    model.load_state_dict(payload["model_state"])
    return model, payload


def restore_rng_from_checkpoint(payload: dict[str, Any]) -> None:
    if "torch_rng_state" in payload:
        torch.random.set_rng_state(payload["torch_rng_state"])
    if "numpy_rng_state" in payload:
        np.random.set_state(payload["numpy_rng_state"])
    if "python_rng_state" in payload:
        random.setstate(payload["python_rng_state"])
