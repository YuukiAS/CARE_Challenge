"""Training helpers for CARE-ASE."""

from __future__ import annotations

from dataclasses import asdict
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

from src.care_myocardium.models.care_ase import CAREASE, CAREASEConfig


CHECKPOINT_SCHEMA_VERSION = 1


def dice_loss_softmax(logits: torch.Tensor, target: torch.Tensor, *, classes: tuple[int, ...], eps: float = 1.0e-5) -> torch.Tensor:
    probs = torch.softmax(logits, dim=1)
    valid_mask = (target >= 0).to(probs)
    losses = []
    for cls in classes:
        p = probs[:, cls] * valid_mask
        g = (target == int(cls)).to(p) * valid_mask
        valid = (p.sum(dim=(1, 2, 3)) + g.sum(dim=(1, 2, 3))) > 0
        if bool(valid.any()):
            inter = (p[valid] * g[valid]).sum(dim=(1, 2, 3))
            denom = p[valid].sum(dim=(1, 2, 3)) + g[valid].sum(dim=(1, 2, 3))
            losses.append(1.0 - ((2.0 * inter + eps) / (denom + eps)).mean())
    if losses:
        return torch.stack(losses).mean()
    return logits.sum() * 0.0


def binary_dice_bce(logit: torch.Tensor, target: torch.Tensor, valid_mask: torch.Tensor | None = None) -> torch.Tensor:
    target = target.to(logit)
    mask = torch.ones_like(target) if valid_mask is None else valid_mask.to(logit)
    prob = torch.sigmoid(logit)
    dims = tuple(range(1, prob.ndim))
    inter = (prob * target * mask).sum(dim=dims)
    denom = (prob * mask).sum(dim=dims) + (target * mask).sum(dim=dims)
    dice = (1.0 - (2.0 * inter + 1.0e-5) / (denom + 1.0e-5)).mean()
    bce = F.binary_cross_entropy_with_logits(logit, target, reduction="none")
    return dice + ((bce * mask).sum() / mask.sum().clamp_min(1.0))


def _five_class_logits_and_target(logits: torch.Tensor, target: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    five = torch.cat([logits[:, :4], logits[:, 5:6]], dim=1)
    mapped = target.clone()
    mapped = torch.where(mapped == 5, torch.full_like(mapped, 4), mapped)
    mapped = torch.where(mapped == 4, torch.zeros_like(mapped), mapped)
    return five, mapped


def care_ase_loss(outputs: dict[str, Any], batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, dict[str, float]]:
    logits = outputs["final_logits"]
    target = batch["seg"].to(device=logits.device, dtype=torch.long)
    availability = batch["availability"].to(logits)
    t2_present = availability[:, 1] > 0.5
    losses: list[torch.Tensor] = []
    metrics: dict[str, torch.Tensor] = {}
    if bool(t2_present.any()):
        idx = t2_present
        ce6 = F.cross_entropy(logits[idx], target[idx], ignore_index=-1)
        dice6 = dice_loss_softmax(logits[idx], target[idx], classes=(1, 2, 3, 4, 5))
        metrics["six_class_ce"] = ce6
        metrics["six_class_dice"] = dice6
        losses.append(ce6 + dice6)
    if bool((~t2_present).any()):
        idx = ~t2_present
        five_logits, five_target = _five_class_logits_and_target(logits[idx], target[idx])
        ce5 = F.cross_entropy(five_logits, five_target, ignore_index=-1)
        dice5 = dice_loss_softmax(five_logits, five_target, classes=(1, 2, 3, 4))
        metrics["five_class_ce_without_class4"] = ce5
        metrics["five_class_dice_without_class4"] = dice5
        losses.append(ce5 + dice5)
    anatomy_target = target.clone()
    anatomy_target = torch.where((anatomy_target == 4) | (anatomy_target == 5), torch.ones_like(anatomy_target), anatomy_target)
    anatomy_ce = F.cross_entropy(outputs["anatomy_logits_0_3"], anatomy_target.clamp(-1, 3), ignore_index=-1)
    valid_binary = (target >= 0).unsqueeze(1).to(logits)
    scar_loss = binary_dice_bce(outputs["z_scar"], (target == 5).unsqueeze(1), valid_binary)
    edema_loss_raw = binary_dice_bce(outputs["z_pure_edema"], (target == 4).unsqueeze(1), valid_binary)
    edema_active = availability[:, 1].view(-1, 1, 1, 1, 1)
    edema_loss = edema_loss_raw * edema_active.mean()
    total = torch.stack(losses).mean() + 0.25 * anatomy_ce + 0.35 * scar_loss + 0.35 * edema_loss
    metrics.update(
        {
            "loss": total,
            "anatomy_ce": anatomy_ce,
            "scar_binary": scar_loss,
            "edema_binary_t2_gated": edema_loss,
            "all_finite": torch.isfinite(total).to(total),
            "all_nonnegative": (total >= 0).to(total),
        }
    )
    return total, {k: float(v.detach().cpu()) for k, v in metrics.items()}


def set_stage_trainability(model: CAREASE, *, global_step: int) -> str:
    step = int(global_step)
    stage = "A" if step < model.config.stage_a_steps else "B" if step < model.config.stage_a_steps + model.config.stage_b_steps else "C"
    for name, param in model.named_parameters():
        trainable = True
        if stage == "A" and (name.startswith("encoder.") or name.startswith("low_mid_") or name.startswith("anatomy_decoder.")):
            trainable = False
        if stage == "B" and name.startswith("encoder."):
            trainable = False
        param.requires_grad_(trainable)
    return stage


def optimizer_parameter_groups(model: CAREASE) -> list[dict[str, Any]]:
    groups: dict[str, list[nn.Parameter]] = {
        "encoder": [],
        "shared_decoder": [],
        "anatomy_decoder": [],
        "scar_branch": [],
        "edema_branch": [],
        "component_heads": [],
        "modality_adapters": [],
    }
    seen: set[int] = set()

    def add(group: str, modules: list[nn.Module]) -> None:
        for module in modules:
            for param in module.parameters():
                ident = id(param)
                if ident in seen or not param.requires_grad:
                    continue
                seen.add(ident)
                groups[group].append(param)

    add("encoder", [model.encoder])
    add("shared_decoder", [*model.low_mid_transpconvs, *model.low_mid_stages])
    add(
        "anatomy_decoder",
        [
            model.anatomy_decoder.transpconvs[4],
            model.anatomy_decoder.transpconvs[5],
            model.anatomy_decoder.stages[4],
            model.anatomy_decoder.stages[5],
            model.anatomy_decoder.seg_layers[5],
        ],
    )
    add("scar_branch", [model.scar_branch])
    add("edema_branch", [model.edema_branch])
    add("component_heads", [model.component_heads])
    add(
        "modality_adapters",
        [model.scar_lge_adapter, model.scar_c0_adapter, model.edema_t2_adapter, model.edema_c0_adapter],
    )
    lr = {
        "encoder": 1.0e-5,
        "shared_decoder": 2.0e-5,
        "anatomy_decoder": 1.0e-5,
        "scar_branch": 5.0e-5,
        "edema_branch": 5.0e-5,
        "component_heads": 1.0e-4,
        "modality_adapters": 8.0e-5,
    }
    return [{"name": name, "params": params, "lr": lr[name], "weight_decay": 1.0e-4} for name, params in groups.items() if params]


def build_optimizer(model: CAREASE) -> torch.optim.Optimizer:
    return torch.optim.AdamW(optimizer_parameter_groups(model))


def capture_rng_state() -> dict[str, Any]:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.random.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def restore_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.random.set_rng_state(state["torch_cpu"].cpu() if torch.is_tensor(state["torch_cpu"]) else torch.as_tensor(state["torch_cpu"], dtype=torch.uint8))
    if torch.cuda.is_available() and state.get("torch_cuda"):
        torch.cuda.set_rng_state_all([s.cpu() if torch.is_tensor(s) else torch.as_tensor(s, dtype=torch.uint8) for s in state["torch_cuda"]])


def save_care_ase_checkpoint(
    path: Path,
    *,
    model: CAREASE,
    optimizer: torch.optim.Optimizer,
    global_step: int,
    microbatch_cursor: int,
    stage_id: str,
    next_batch_hash: str,
    loss_history_tail: list[dict[str, Any]],
) -> None:
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "global_optimizer_step": int(global_step),
        "microbatch_cursor": int(microbatch_cursor),
        "stage_id": str(stage_id),
        "stage_step": int(global_step),
        "extent_wall_ramp_value": CAREASE.extent_wall_ramp(global_step),
        "next_batch_hash": str(next_batch_hash),
        "rng_state": capture_rng_state(),
        "config": asdict(model.config),
        "loss_history_tail": loss_history_tail[-20:],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    torch.save(payload, tmp)
    tmp.replace(path)


def load_care_ase_checkpoint(
    path: Path,
    *,
    map_location: str | torch.device = "cpu",
    restore_rng: bool = True,
) -> tuple[CAREASE, dict[str, Any]]:
    payload = torch.load(path, map_location=map_location, weights_only=False)
    if int(payload.get("schema_version", 0)) != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(f"unsupported CARE-ASE checkpoint schema_version: {payload.get('schema_version')}")
    model = CAREASE(CAREASEConfig(**payload["config"]), map_location=map_location)
    model.load_state_dict(payload["model_state_dict"])
    if restore_rng:
        restore_rng_state(payload["rng_state"])
    return model, payload


def checkpoint_receipt(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "checkpoint_path": str(path),
        "schema_version": int(payload["schema_version"]),
        "global_optimizer_step": int(payload["global_optimizer_step"]),
        "microbatch_cursor": int(payload["microbatch_cursor"]),
        "stage_id": payload["stage_id"],
        "extent_wall_ramp_value": float(payload["extent_wall_ramp_value"]),
        "next_batch_hash": payload["next_batch_hash"],
        "has_optimizer_state": "optimizer_state_dict" in payload,
        "has_rng_state": "rng_state" in payload,
        "fixed_terminal_step14000": int(payload["global_optimizer_step"]) == 14000,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
