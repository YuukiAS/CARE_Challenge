"""Training losses and checkpoint helpers for CARE-DG."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import random
import numpy as np
import torch
import torch.nn.functional as F

from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL, CAREDG, CAREDGConfig

ANATOMY_CHANNELS = (0, 1, 2, 3)


def _squeeze_labels(x: torch.Tensor) -> torch.Tensor:
    return x[:, 0] if x.ndim == 5 else x


def make_error_targets(labels: torch.Tensor, anchor_mask: torch.Tensor, channel: int) -> dict[str, torch.Tensor]:
    labels = _squeeze_labels(labels)
    anchor_mask = _squeeze_labels(anchor_mask)
    gt = labels == int(channel)
    pred = anchor_mask == int(channel)
    return {
        "fn": (gt & ~pred).float().unsqueeze(1),
        "fp": (~gt & pred).float().unsqueeze(1),
        "gt": gt.float().unsqueeze(1),
        "anchor_pred": pred.float().unsqueeze(1),
    }


def make_edema_zone_targets(labels: torch.Tensor, anchor_mask: torch.Tensor) -> dict[str, torch.Tensor]:
    labels = _squeeze_labels(labels)
    anchor_mask = _squeeze_labels(anchor_mask)
    gt = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
    pred = (anchor_mask == SCAR_CHANNEL) | (anchor_mask == EDEMA_CHANNEL)
    return {
        "fn": (gt & ~pred).float().unsqueeze(1),
        "fp": (~gt & pred).float().unsqueeze(1),
        "gt": gt.float().unsqueeze(1),
        "anchor_pred": pred.float().unsqueeze(1),
    }


def _case_mask(mask: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    if mask.ndim == 1:
        mask = mask[:, None, None, None, None]
    elif mask.ndim == 2:
        mask = mask[:, :1, None, None, None]
    return mask.to(device=reference.device, dtype=reference.dtype).expand(-1, 1, *reference.shape[-3:])


def masked_mean(value: torch.Tensor, mask: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    mask = mask.to(device=value.device, dtype=value.dtype)
    return (value * mask).sum() / mask.sum().clamp_min(eps)


def binary_dice_loss(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor | None = None, eps: float = 1e-5) -> torch.Tensor:
    prob = torch.sigmoid(logits)
    if mask is None:
        mask = torch.ones_like(prob)
    mask = mask.to(device=prob.device, dtype=prob.dtype)
    dims = tuple(range(2, prob.ndim))
    inter = (prob * target * mask).sum(dim=dims)
    denom = (prob * mask).sum(dim=dims) + (target * mask).sum(dim=dims)
    active = mask.sum(dim=dims) > 0
    loss = 1.0 - (2.0 * inter + eps) / (denom + eps)
    if active.any():
        return loss[active].mean()
    return (prob * mask).sum() * 0.0


def masked_bce_with_logits(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    loss = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    return masked_mean(loss, mask)


def focal_bce(prob: torch.Tensor, target: torch.Tensor, mask: torch.Tensor | None = None, gamma: float = 2.0, eps: float = 1e-4) -> torch.Tensor:
    prob32 = prob.float().clamp(float(eps), 1.0 - float(eps))
    target32 = target.float()
    pt = torch.where(target32 > 0.5, prob32, 1.0 - prob32).clamp(float(eps), 1.0)
    bce = -(target32 * prob32.log() + (1.0 - target32) * (1.0 - prob32).clamp(float(eps), 1.0).log())
    loss = (1.0 - pt).pow(gamma) * bce
    if mask is None:
        return loss.mean()
    return masked_mean(loss, mask)


def scar_margin(logits: torch.Tensor) -> torch.Tensor:
    competitor = torch.cat([logits[:, :SCAR_CHANNEL], logits[:, SCAR_CHANNEL + 1 :]], dim=1).amax(dim=1, keepdim=True)
    return logits[:, SCAR_CHANNEL : SCAR_CHANNEL + 1] - competitor


def edema_zone_margin(logits: torch.Tensor) -> torch.Tensor:
    zone = torch.maximum(logits[:, SCAR_CHANNEL : SCAR_CHANNEL + 1], logits[:, EDEMA_CHANNEL : EDEMA_CHANNEL + 1])
    anatomy = logits[:, list(ANATOMY_CHANNELS)].amax(dim=1, keepdim=True)
    return zone - anatomy


def margin_improvement_loss(
    final_margin: torch.Tensor,
    anchor_margin: torch.Tensor,
    targets: dict[str, torch.Tensor],
    active_mask: torch.Tensor,
    margin: float,
) -> torch.Tensor:
    fn = targets["fn"] * active_mask
    fp = targets["fp"] * active_mask
    fn_loss = F.relu(float(margin) - (final_margin - anchor_margin))
    fp_loss = F.relu(float(margin) - (anchor_margin - final_margin))
    return masked_mean(fn_loss, fn) + masked_mean(fp_loss, fp)


def care_dg_loss(
    outputs: dict[str, torch.Tensor],
    labels: torch.Tensor,
    anchor_mask: torch.Tensor,
    *,
    t2_present: torch.Tensor,
    scar_reliable: torch.Tensor | None = None,
    edema_reliable: torch.Tensor | None = None,
    margin: float = 1.0,
) -> tuple[torch.Tensor, dict[str, float]]:
    labels = _squeeze_labels(labels)
    anchor_mask = _squeeze_labels(anchor_mask)
    final_logits = outputs["final_logits"]
    anchor_logits = outputs["anchor_logits"].detach()
    if scar_reliable is None:
        scar_reliable = torch.ones_like(t2_present)
    if edema_reliable is None:
        edema_reliable = t2_present
    scar_mask = _case_mask(scar_reliable, final_logits)
    edema_mask = _case_mask(edema_reliable, final_logits)

    scar_targets = make_error_targets(labels, anchor_mask, SCAR_CHANNEL)
    edema_targets = make_edema_zone_targets(labels, anchor_mask)

    scar_final_margin = scar_margin(final_logits)
    scar_anchor_margin = scar_margin(anchor_logits)
    edema_final_margin = edema_zone_margin(final_logits)
    edema_anchor_margin = edema_zone_margin(anchor_logits)

    scar_seg = binary_dice_loss(scar_final_margin, scar_targets["gt"], scar_mask) + masked_bce_with_logits(
        scar_final_margin, scar_targets["gt"], scar_mask
    )
    edema_seg = binary_dice_loss(edema_final_margin, edema_targets["gt"], edema_mask) + masked_bce_with_logits(
        edema_final_margin, edema_targets["gt"], edema_mask
    )
    scar_gate = focal_bce(outputs["scar_q_fn"], scar_targets["fn"], scar_mask) + focal_bce(outputs["scar_q_fp"], scar_targets["fp"], scar_mask)
    edema_gate = focal_bce(outputs["edema_q_fn"], edema_targets["fn"], edema_mask) + focal_bce(outputs["edema_q_fp"], edema_targets["fp"], edema_mask)

    scar_margin_loss = margin_improvement_loss(scar_final_margin, scar_anchor_margin, scar_targets, scar_mask, margin)
    edema_margin_loss = margin_improvement_loss(edema_final_margin, edema_anchor_margin, edema_targets, edema_mask, margin)
    correct = ((labels == anchor_mask).float().unsqueeze(1)).detach()
    identity = masked_mean(outputs["scar_delta"].abs() + outputs["edema_delta"].abs(), correct)
    remote = masked_mean(outputs["scar_delta_raw"].abs(), (1.0 - outputs["scar_support"]) * scar_mask) + masked_mean(
        outputs["edema_delta_raw"].abs(), (1.0 - outputs["edema_support"]) * edema_mask
    )

    total = scar_seg + edema_seg + 0.5 * (scar_gate + edema_gate) + 0.25 * (scar_margin_loss + edema_margin_loss) + 0.10 * identity + 0.10 * remote
    metrics = {
        "loss": float(total.detach().cpu()),
        "scar_seg": float(scar_seg.detach().cpu()),
        "edema_seg": float(edema_seg.detach().cpu()),
        "scar_gate": float(scar_gate.detach().cpu()),
        "edema_gate": float(edema_gate.detach().cpu()),
        "scar_margin": float(scar_margin_loss.detach().cpu()),
        "edema_margin": float(edema_margin_loss.detach().cpu()),
        "identity": float(identity.detach().cpu()),
        "remote": float(remote.detach().cpu()),
    }
    return total, metrics


def _rng_payload(local_rng: random.Random | None = None) -> dict[str, Any]:
    return {
        "python_random_state": random.getstate(),
        "local_random_state": local_rng.getstate() if local_rng is not None else None,
        "numpy_random_state": np.random.get_state(),
        "torch_cpu_rng_state": torch.get_rng_state(),
        "torch_cuda_rng_states": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def _restore_rng_payload(payload: dict[str, Any], local_rng: random.Random | None = None) -> None:
    if payload.get("python_random_state") is not None:
        random.setstate(payload["python_random_state"])
    if payload.get("local_random_state") is not None and local_rng is not None:
        local_rng.setstate(payload["local_random_state"])
    if payload.get("numpy_random_state") is not None:
        np.random.set_state(payload["numpy_random_state"])
    if payload.get("torch_cpu_rng_state") is not None:
        torch.set_rng_state(payload["torch_cpu_rng_state"])
    cuda_states = payload.get("torch_cuda_rng_states") or []
    if cuda_states and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(cuda_states)


def _validate_hash_contract(extra: dict[str, Any], expected_hash_contract: dict[str, Any] | None) -> None:
    if expected_hash_contract is None:
        return
    actual = dict(extra.get("hash_contract") or {})
    for key, expected in expected_hash_contract.items():
        if actual.get(key) != expected:
            raise ValueError(f"CARE_DG_CHECKPOINT_HASH_CONTRACT_MISMATCH:{key}")


def save_care_dg_checkpoint(
    path: Path,
    model: CAREDG,
    optimizer: torch.optim.Optimizer,
    step: int,
    extra: dict[str, Any] | None = None,
    *,
    scaler: Any | None = None,
    local_rng: random.Random | None = None,
    stage: str | None = None,
    local_step: int | None = None,
    total_step: int | None = None,
    fixed_inner_plan_hash: str | None = None,
    hash_contract: dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    runtime_state = {
        **_rng_payload(local_rng),
        "amp_grad_scaler_state": scaler.state_dict() if scaler is not None else None,
        "stage": stage,
        "local_step": local_step,
        "total_step": int(total_step if total_step is not None else step),
        "fixed_inner_evaluation_plan_sha256": fixed_inner_plan_hash,
    }
    merged_extra = dict(extra or {})
    if hash_contract is not None:
        merged_extra["hash_contract"] = hash_contract
    torch.save(
        {
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "step": int(step),
            "config": model.config.__dict__,
            "extra": merged_extra,
            "runtime_state": runtime_state,
        },
        path,
    )


def load_care_dg_checkpoint(
    path: Path,
    model: CAREDG | None = None,
    optimizer: torch.optim.Optimizer | None = None,
    *,
    scaler: Any | None = None,
    local_rng: random.Random | None = None,
    restore_rng: bool = False,
    expected_hash_contract: dict[str, Any] | None = None,
) -> tuple[CAREDG, int, dict[str, Any]]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    extra = dict(payload.get("extra", {}))
    _validate_hash_contract(extra, expected_hash_contract)
    if model is None:
        model = CAREDG(CAREDGConfig(**payload["config"]))
    model.load_state_dict(payload["model_state"])
    if optimizer is not None and "optimizer_state" in payload:
        optimizer.load_state_dict(payload["optimizer_state"])
    runtime_state = dict(payload.get("runtime_state") or {})
    if scaler is not None and runtime_state.get("amp_grad_scaler_state") is not None:
        scaler.load_state_dict(runtime_state["amp_grad_scaler_state"])
    if restore_rng:
        _restore_rng_payload(runtime_state, local_rng)
    extra["runtime_state"] = runtime_state
    return model, int(payload.get("step", 0)), extra
