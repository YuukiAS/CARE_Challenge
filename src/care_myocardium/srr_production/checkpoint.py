"""Shared checkpoint schema and true resume helpers for SRR production paths."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.care_myocardium.srr_production.anchor_manifest import sha256_file


CHECKPOINT_SCHEMA_VERSION = 2


def capture_rng_state() -> dict[str, Any]:
    state: dict[str, Any] = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.random.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }
    return state


def _rng_byte_tensor_on_cpu(value: Any, *, name: str) -> torch.ByteTensor:
    if isinstance(value, torch.Tensor):
        tensor = value.detach().to(device="cpu")
    else:
        tensor = torch.as_tensor(value, dtype=torch.uint8, device="cpu")
    if tensor.dtype != torch.uint8:
        raise TypeError(f"{name} RNG state must be torch.uint8, got {tensor.dtype}")
    return tensor.contiguous()


def restore_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.random.set_rng_state(_rng_byte_tensor_on_cpu(state["torch_cpu"], name="torch_cpu"))
    if torch.cuda.is_available() and state.get("torch_cuda"):
        torch.cuda.set_rng_state_all(
            [
                _rng_byte_tensor_on_cpu(cuda_state, name=f"torch_cuda[{index}]")
                for index, cuda_state in enumerate(state["torch_cuda"])
            ]
        )


def save_srr_checkpoint(
    *,
    path: Path,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    amp_scaler: Any,
    global_step: int,
    epoch: int,
    final_output_mode: str,
    architecture_config: dict[str, Any],
    oof_anchor_manifest_hash: str,
    prototype_memory_provenance: dict[str, Any],
    split_hash: str,
    source_commit: str,
    best_metric_state: dict[str, Any],
    loss_weight_contract: dict[str, float] | None = None,
) -> None:
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": None if scheduler is None else scheduler.state_dict(),
        "amp_scaler_state_dict": None if amp_scaler is None else amp_scaler.state_dict(),
        "global_step": int(global_step),
        "epoch": int(epoch),
        "production_final_output_mode": str(final_output_mode),
        "architecture_config": dict(architecture_config),
        "oof_anchor_manifest_hash": str(oof_anchor_manifest_hash),
        "prototype_memory_provenance": prototype_memory_provenance,
        "split_hash": str(split_hash),
        "source_commit": str(source_commit),
        "rng_state": capture_rng_state(),
        "best_metric_state": dict(best_metric_state),
        "loss_weight_contract": dict(loss_weight_contract or {}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    torch.save(payload, tmp)
    tmp.replace(path)


def load_srr_checkpoint(
    *,
    path: Path,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    amp_scaler: Any,
    map_location: torch.device | str = "cpu",
    restore_rng: bool = True,
    restore_optimizer: bool = True,
    strict_model_state: bool = True,
) -> dict[str, Any]:
    payload = torch.load(path, map_location=map_location, weights_only=False)
    if int(payload.get("schema_version", 0)) != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(f"unsupported SRR checkpoint schema_version: {payload.get('schema_version')}")
    required = (
        "model_state_dict",
        "optimizer_state_dict",
        "global_step",
        "epoch",
        "production_final_output_mode",
        "oof_anchor_manifest_hash",
        "prototype_memory_provenance",
        "rng_state",
        "best_metric_state",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"SRR checkpoint missing required fields: {missing}")
    state = dict(payload["model_state_dict"])
    model_state = model.state_dict()
    migration: dict[str, Any] = {"applied": False}
    key = "production_correction_gate.weight"
    if key in state and key in model_state and tuple(state[key].shape) != tuple(model_state[key].shape):
        source = state[key]
        target = model_state[key].clone()
        if tuple(source.shape[:1] + source.shape[2:]) != tuple(target.shape[:1] + target.shape[2:]) or source.shape[1] != 4 or target.shape[1] != 13:
            raise ValueError(f"unsupported production gate checkpoint migration: {tuple(source.shape)} -> {tuple(target.shape)}")
        target.zero_()
        target[:, :4].copy_(source)
        state[key] = target
        migration = {
            "applied": True,
            "key": key,
            "source_shape": list(source.shape),
            "target_shape": list(target.shape),
            "copied_input_channels": [0, 1, 2, 3],
            "zero_initialized_input_channels": [4, 5, 6, 7, 8, 9, 10, 11, 12],
            "non_gate_parameters_loaded_strict": True,
        }
    missing_keys: list[str] = []
    unexpected_keys: list[str] = []
    if strict_model_state:
        model.load_state_dict(state)
    else:
        load_result = model.load_state_dict(state, strict=False)
        missing_keys = list(load_result.missing_keys)
        unexpected_keys = list(load_result.unexpected_keys)
    if migration["applied"]:
        payload["optimizer_state_dict_migration"] = "skipped_optimizer_state_due_to_production_gate_input_shape_migration"
    elif restore_optimizer:
        optimizer.load_state_dict(payload["optimizer_state_dict"])
    else:
        payload["optimizer_state_dict_migration"] = "skipped_optimizer_state_by_warm_start_finetune_contract"
    payload["production_gate_migration"] = migration
    payload["model_state_load"] = {
        "strict_model_state": bool(strict_model_state),
        "missing_keys": missing_keys,
        "unexpected_keys": unexpected_keys,
    }
    if scheduler is not None:
        scheduler_state = payload.get("scheduler_state_dict")
        if scheduler_state is None:
            raise ValueError("checkpoint lacks scheduler_state_dict but scheduler restore was requested")
        scheduler.load_state_dict(scheduler_state)
    if amp_scaler is not None:
        scaler_state = payload.get("amp_scaler_state_dict")
        if scaler_state is None:
            raise ValueError("checkpoint lacks amp_scaler_state_dict but scaler restore was requested")
        amp_scaler.load_state_dict(scaler_state)
    if restore_rng:
        restore_rng_state(payload["rng_state"])
    return payload


def checkpoint_receipt(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "checkpoint_path": str(path),
        "checkpoint_sha256": sha256_file(path),
        "schema_version": int(payload["schema_version"]),
        "global_step": int(payload["global_step"]),
        "epoch": int(payload["epoch"]),
        "optimizer_restored": "optimizer_state_dict" in payload,
        "scheduler_state": "disabled_by_config" if payload.get("scheduler_state_dict") is None else "restored",
        "amp_scaler_state": "disabled_by_config" if payload.get("amp_scaler_state_dict") is None else "restored",
        "prototype_memory_state_restored": "prototype_memory_provenance" in payload,
        "rng_state_restored": "rng_state" in payload,
        "best_metric_state_restored": "best_metric_state" in payload,
        "oof_anchor_manifest_hash": payload["oof_anchor_manifest_hash"],
        "split_hash": payload["split_hash"],
        "production_gate_migration": payload.get("production_gate_migration", {"applied": False}),
        "loss_weight_contract": payload.get("loss_weight_contract", {}),
    }
