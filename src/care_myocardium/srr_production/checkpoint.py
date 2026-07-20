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


def restore_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.random.set_rng_state(state["torch_cpu"])
    if torch.cuda.is_available() and state.get("torch_cuda"):
        torch.cuda.set_rng_state_all(state["torch_cuda"])


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
    model.load_state_dict(payload["model_state_dict"])
    optimizer.load_state_dict(payload["optimizer_state_dict"])
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
    }

