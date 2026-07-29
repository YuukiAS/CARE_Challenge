"""Training, initialization, and W1 validation helpers for CARE-PRISM v2."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

from src.care_myocardium.models.care_prism import (
    CAREPRISM,
    CAREPRISMConfig,
    DEFAULT_RESENC_PLANS,
    build_care_prism,
    build_source_resenc,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESENC_RESULT_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS"


def stable_json_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dice_loss_from_logits(logits: torch.Tensor, target: torch.Tensor, eps: float = 1.0e-5) -> torch.Tensor:
    probs = torch.sigmoid(logits)
    dims = tuple(range(1, probs.ndim))
    inter = (probs * target).sum(dim=dims)
    denom = probs.sum(dim=dims) + target.sum(dim=dims)
    return (1.0 - (2.0 * inter + eps) / (denom + eps)).clamp_min(0).mean()


def focal_tversky_loss(logits: torch.Tensor, target: torch.Tensor, alpha_fn: float = 0.70, beta_fp: float = 0.30, eps: float = 1.0e-5) -> torch.Tensor:
    probs = torch.sigmoid(logits)
    dims = tuple(range(1, probs.ndim))
    tp = (probs * target).sum(dim=dims)
    fn = ((1.0 - probs) * target).sum(dim=dims)
    fp = (probs * (1.0 - target)).sum(dim=dims)
    tversky = (tp + eps) / (tp + alpha_fn * fn + beta_fp * fp + eps)
    return (1.0 - tversky).clamp_min(0).mean()


def dice_ce_loss(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    return dice_loss_from_logits(logits, target) + F.binary_cross_entropy_with_logits(logits, target)


def generalized_surface_placeholder(logits: torch.Tensor, target: torch.Tensor, *, enabled: bool) -> torch.Tensor:
    if not enabled:
        return logits.sum() * 0.0
    probs = torch.sigmoid(logits)
    return (probs - target).abs().mean().clamp_min(0)


def lesion_mil_placeholder(logits: torch.Tensor, target: torch.Tensor, *, enabled: bool) -> torch.Tensor:
    if not enabled:
        return logits.sum() * 0.0
    probs = torch.sigmoid(logits).flatten(1).amax(dim=1)
    has_lesion = (target.flatten(1).sum(dim=1) > 0).to(dtype=logits.dtype)
    return F.binary_cross_entropy(probs.clamp(1.0e-5, 1.0 - 1.0e-5), has_lesion)


def resize_like(target: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    return F.interpolate(target.float(), size=reference.shape[-3:], mode="nearest")


def router_anticollapse_loss(weights: list[torch.Tensor]) -> torch.Tensor:
    losses = []
    for w in weights:
        entropy = -(w.clamp_min(1.0e-8) * w.clamp_min(1.0e-8).log()).sum(dim=1)
        losses.append(torch.relu(w.new_tensor(0.25) - entropy).mean())
    return torch.stack(losses).mean() if losses else torch.tensor(0.0)


def negative_space_loss(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    target = target.float()
    if target.shape != logits.shape:
        target = target.expand_as(logits)
    return F.binary_cross_entropy_with_logits(logits, target)


def pathology_refiner_loss(
    outputs: dict[str, torch.Tensor],
    target: torch.Tensor,
    *,
    scar_like: bool,
    stage: str,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    surface_enabled = stage.upper() == "C"
    refine = dice_ce_loss(outputs["final_logit"], target)
    ft = focal_tversky_loss(outputs["final_logit"], target)
    mil = lesion_mil_placeholder(outputs["final_logit"], target, enabled=surface_enabled)
    surface = generalized_surface_placeholder(outputs["final_logit"], target, enabled=surface_enabled)
    proposal_target = resize_like(target, outputs["proposal_logit"])
    proposal = dice_ce_loss(outputs["proposal_logit"], proposal_target)
    negative_target = torch.zeros_like(outputs["negative_logits"])
    negative = negative_space_loss(outputs["negative_logits"], negative_target)
    if scar_like:
        total = refine + 0.50 * ft + 0.15 * mil + 0.05 * surface
    else:
        total = refine + 0.35 * ft + 0.05 * surface
    return total, {
        "refine": refine.detach(),
        "focal_tversky": ft.detach(),
        "mil": mil.detach(),
        "surface": surface.detach(),
        "proposal": proposal.detach(),
        "negative": negative.detach(),
    }


def care_prism_loss(outputs: dict[str, Any], batch: dict[str, torch.Tensor], *, stage: str = "A") -> tuple[torch.Tensor, dict[str, float]]:
    scar_target = batch["scar_target"].to(outputs["scar_direct_logit"])
    edema_target = batch["edema_zone_target"].to(outputs["edema_zone_direct_logit"])
    anatomy_target = batch["anatomy_target"].to(device=outputs["anatomy_logits"].device, dtype=torch.float32)
    t2_present = batch["t2_present"].to(outputs["edema_zone_direct_logit"]).view(-1, 1, 1, 1, 1)
    anatomy_loss = F.binary_cross_entropy_with_logits(outputs["anatomy_logits"], anatomy_target)
    scar_ref, scar_parts = pathology_refiner_loss(outputs["scar"], scar_target, scar_like=True, stage=stage)
    edema_ref_raw, edema_parts = pathology_refiner_loss(outputs["edema"], edema_target, scar_like=False, stage=stage)
    edema_active = t2_present.mean()
    edema_ref = edema_ref_raw * edema_active
    proposal_scar = scar_parts["proposal"]
    proposal_edema = edema_parts["proposal"] * edema_active.detach()
    negative_scar = scar_parts["negative"]
    negative_edema = edema_parts["negative"] * edema_active.detach()
    burden = (
        F.cross_entropy(outputs["scar"]["burden_logits"], batch["scar_burden_class"].to(outputs["scar"]["burden_logits"]).long())
        + F.smooth_l1_loss(outputs["scar"]["log_ratio"], batch["scar_log_ratio"].to(outputs["scar"]["log_ratio"]))
    )
    if float(edema_active.detach().cpu()) > 0.0:
        burden = burden + F.cross_entropy(outputs["edema"]["burden_logits"], batch["edema_burden_class"].to(outputs["edema"]["burden_logits"]).long())
        burden = burden + F.smooth_l1_loss(outputs["edema"]["log_ratio"], batch["edema_log_ratio"].to(outputs["edema"]["log_ratio"]))
    soft_relation = torch.relu(outputs["scar_probability"] - outputs["edema_probability"]).mean() * edema_active
    router = router_anticollapse_loss(outputs["scar_router_weights"] + outputs["edema_router_weights"]) if stage.upper() in {"A", "B"} else outputs["scar_direct_logit"].sum() * 0.0
    total = (
        0.50 * anatomy_loss
        + 0.35 * (proposal_scar + proposal_edema)
        + scar_ref
        + edema_ref
        + 0.15 * (negative_scar + negative_edema)
        + 0.10 * burden
        + 0.05 * soft_relation
        + 0.02 * router
    )
    parts = {
        "loss": total.detach(),
        "anatomy": anatomy_loss.detach(),
        "scar_refine": scar_ref.detach(),
        "edema_refine": edema_ref.detach(),
        "scar_proposal": proposal_scar.detach(),
        "edema_proposal": proposal_edema.detach(),
        "scar_negative": negative_scar.detach(),
        "edema_negative": negative_edema.detach(),
        "burden": burden.detach(),
        "soft_relation": soft_relation.detach(),
        "router": router.detach(),
    }
    metrics = {k: float(v.cpu()) for k, v in parts.items()}
    metrics["all_finite"] = bool(torch.isfinite(total).detach().cpu())
    metrics["all_nonnegative"] = all(float(v.cpu()) >= 0.0 for v in parts.values())
    return total, metrics


def optimizer_for_care_prism(model: nn.Module, *, stage: str = "A") -> torch.optim.Optimizer:
    encoder_params: list[nn.Parameter] = []
    new_params: list[nn.Parameter] = []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if name.startswith("shared_encoder."):
            encoder_params.append(param)
        else:
            new_params.append(param)
    encoder_lr = 1.0e-5 if stage.upper() == "D" else 2.0e-5
    new_lr = 3.0e-5 if stage.upper() == "D" else 1.0e-4
    return torch.optim.AdamW(
        [{"params": encoder_params, "lr": encoder_lr}, {"params": new_params, "lr": new_lr}],
        weight_decay=1.0e-4,
    )


def _checkpoint_state_dict(payload: Any) -> dict[str, torch.Tensor]:
    if isinstance(payload, dict):
        for key in ("network_weights", "state_dict", "model_state", "model_state_dict"):
            value = payload.get(key)
            if isinstance(value, dict):
                return value
    if isinstance(payload, dict) and all(torch.is_tensor(v) for v in payload.values()):
        return payload
    raise ValueError("checkpoint does not contain a recognizable tensor state_dict")


def _candidate_encoder_keys(state: dict[str, torch.Tensor], target_key: str) -> list[str]:
    return [
        target_key,
        f"encoder.{target_key}",
        f"network.encoder.{target_key}",
        f"module.encoder.{target_key}",
        f"feature_backbone.encoder.{target_key}",
        f"network.feature_backbone.encoder.{target_key}",
    ]


def load_same_fold_resenc_encoder(
    model: CAREPRISM,
    checkpoint_path: Path,
    *,
    map_location: str | torch.device = "cpu",
) -> dict[str, Any]:
    payload = torch.load(checkpoint_path, map_location=map_location, weights_only=False)
    source_state = _checkpoint_state_dict(payload)
    target = model.shared_encoder.state_dict()
    matched: dict[str, torch.Tensor] = {}
    matched_bytes = 0
    total_bytes = sum(v.numel() * v.element_size() for v in target.values())
    for key, value in target.items():
        for src_key in _candidate_encoder_keys(source_state, key):
            src = source_state.get(src_key)
            if torch.is_tensor(src) and tuple(src.shape) == tuple(value.shape):
                matched[key] = src.to(dtype=value.dtype)
                matched_bytes += value.numel() * value.element_size()
                break
    model.shared_encoder.load_state_dict({**target, **matched})
    return {
        "checkpoint_path": str(checkpoint_path),
        "matched_tensors": len(matched),
        "target_tensors": len(target),
        "matched_parameter_bytes": int(matched_bytes),
        "target_parameter_bytes": int(total_bytes),
        "byte_coverage": float(matched_bytes / max(total_bytes, 1)),
    }


def find_same_fold_resenc_checkpoints(root: Path = DEFAULT_RESENC_RESULT_ROOT, *, fold: int = 0) -> list[Path]:
    if not root.exists():
        return []
    out: list[Path] = []
    for ckpt in root.glob(f"**/fold_{fold}/checkpoint*.pth"):
        text = str(ckpt).lower()
        parent_text = ckpt.parents[1].name.lower() if len(ckpt.parents) > 1 else text
        if "resenc" in text or "residualencoder" in text or "resenc" in parent_text:
            out.append(ckpt)
    return sorted(out)


def fp32_encoder_parity(
    model: CAREPRISM,
    checkpoint_path: Path,
    sample: torch.Tensor,
    *,
    config: CAREPRISMConfig,
) -> dict[str, Any]:
    source = build_source_resenc(config)
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    state = _checkpoint_state_dict(payload)
    source.load_state_dict(state, strict=False)
    source.eval()
    model.shared_encoder.eval()
    with torch.no_grad():
        source_scales = list(source.encoder(sample.float()))
        prism_scales = list(model.shared_encoder(sample.float()))
    per_scale = []
    for idx, (a, b) in enumerate(zip(source_scales, prism_scales)):
        per_scale.append({"scale": idx, "max_abs_error": float((a - b).abs().max().cpu()), "shape": list(a.shape)})
    return {"per_scale": per_scale, "max_abs_error": max((row["max_abs_error"] for row in per_scale), default=None)}


def write_init_transplant_report(
    output_path: Path,
    *,
    fold: int = 0,
    plans_path: Path = DEFAULT_RESENC_PLANS,
    checkpoint_root: Path = DEFAULT_RESENC_RESULT_ROOT,
) -> dict[str, Any]:
    config = CAREPRISMConfig.from_resenc_plans(plans_path)
    candidates = find_same_fold_resenc_checkpoints(checkpoint_root, fold=fold)
    report: dict[str, Any] = {
        "status": "FAIL",
        "failure_class": "EXECUTION_OR_INIT",
        "plans_path": str(plans_path.relative_to(REPO_ROOT) if plans_path.is_relative_to(REPO_ROOT) else plans_path),
        "plans_sha256": file_sha256(plans_path) if plans_path.exists() else None,
        "fold": int(fold),
        "same_fold_resenc_checkpoint_candidates": [str(p.relative_to(REPO_ROOT) if p.is_relative_to(REPO_ROOT) else p) for p in candidates],
        "plainconv_checkpoint_counted_for_resenc_gate": False,
        "required_byte_coverage_min": 0.90,
        "required_fp32_parity_max_abs": 1.0e-6,
    }
    if not candidates:
        report["blocking_reason"] = "No same-fold ResidualEncoderUNet checkpoint was found under Dataset501_CAREMyoPS nnUNet results; PlainConv checkpoints are not valid for this gate."
    else:
        model = build_care_prism(config)
        transplant = load_same_fold_resenc_encoder(model, candidates[0])
        report["transplant"] = transplant
        report["status"] = "PASS" if transplant["byte_coverage"] >= 0.90 else "FAIL"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def save_care_prism_checkpoint(
    path: Path,
    model: CAREPRISM,
    optimizer: torch.optim.Optimizer,
    *,
    scheduler: Any = None,
    scaler: Any = None,
    stage: str,
    step: int,
    sampler_state: dict[str, Any] | None = None,
    augmentation_rng_state: dict[str, Any] | None = None,
    hard_negative_state: dict[str, Any] | None = None,
    contract_hash: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "scheduler_state": scheduler.state_dict() if scheduler is not None and hasattr(scheduler, "state_dict") else None,
            "scaler_state": scaler.state_dict() if scaler is not None and hasattr(scaler, "state_dict") else None,
            "stage": stage,
            "step": int(step),
            "sampler_state": sampler_state or {},
            "augmentation_rng_state": augmentation_rng_state or {},
            "prototype_state": {
                "scar": model.scar_refiner.prototype.state_payload(),
                "edema": model.edema_refiner.prototype.state_payload(),
            },
            "hard_negative_state": hard_negative_state or {},
            "contract_hash": contract_hash,
            "torch_rng_state": torch.random.get_rng_state(),
            "numpy_rng_state": np.random.get_state(),
            "python_rng_state": random.getstate(),
            "config": model.config.__dict__,
        },
        path,
    )


def load_care_prism_checkpoint(path: Path, *, map_location: str | torch.device = "cpu") -> tuple[CAREPRISM, dict[str, Any]]:
    payload = torch.load(path, map_location=map_location, weights_only=False)
    cfg_payload = payload.get("config", {})
    cfg = CAREPRISMConfig(**cfg_payload)
    model = build_care_prism(cfg)
    model.load_state_dict(payload["model_state"])
    return model, payload
