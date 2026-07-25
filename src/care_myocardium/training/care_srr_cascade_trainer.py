"""Formal trainer runtime for CARE-SRR-Cascade."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
from torch.cuda.amp import GradScaler

from src.care_myocardium.data.care_srr_cascade_runtime import ScheduleRow
from src.care_myocardium.losses.care_srr_cascade_rescue_losses import care_srr_cascade_rescue_loss_terms
from src.care_myocardium.models.care_srr_cascade_rescue import CARESRRCascadeRescue


CHECKPOINT_SCHEMA_VERSION = 1


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(payload: Any) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def capture_rng_states() -> dict[str, Any]:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.random.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def restore_rng_states(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.random.set_rng_state(state["torch_cpu"].cpu() if isinstance(state["torch_cpu"], torch.Tensor) else torch.as_tensor(state["torch_cpu"], dtype=torch.uint8))
    if torch.cuda.is_available() and state.get("torch_cuda"):
        torch.cuda.set_rng_state_all([s.cpu() if isinstance(s, torch.Tensor) else torch.as_tensor(s, dtype=torch.uint8) for s in state["torch_cuda"]])


@dataclass
class FormalRuntimeConfig:
    logical_run_id: str
    pathology: str
    variant: str
    seed: int
    optimizer_steps: int = 6250
    gradient_accumulation: int = 2
    validation_steps: tuple[int, ...] = (1250, 2500, 3750, 5000, 6250)
    initial_lr: float = 1e-4
    weight_decay: float = 1e-4
    minimum_lr: float = 1e-6
    grad_clip_norm: float = 12.0


def trainable_parameters_for_pathology(model: CARESRRCascadeRescue, pathology: str) -> list[torch.nn.Parameter]:
    if pathology == "scar":
        return [p for p in model.scar_branch.parameters() if p.requires_grad]
    if pathology == "edema":
        return [p for p in model.edema_branch.parameters() if p.requires_grad]
    raise ValueError("pathology must be scar or edema")


class CARESRRCascadeFormalTrainer:
    def __init__(
        self,
        *,
        model: CARESRRCascadeRescue,
        config: FormalRuntimeConfig,
        device: torch.device | str = "cpu",
        use_amp: bool = False,
    ) -> None:
        self.model = model.to(device)
        self.config = config
        self.device = torch.device(device)
        self.use_amp = bool(use_amp and self.device.type == "cuda")
        self.optimizer = torch.optim.AdamW(
            trainable_parameters_for_pathology(self.model, config.pathology),
            lr=float(config.initial_lr),
            weight_decay=float(config.weight_decay),
        )
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=max(1, int(config.optimizer_steps)),
            eta_min=float(config.minimum_lr),
        )
        self.scaler = GradScaler(enabled=self.use_amp)
        self.optimizer_step = 0
        self.microbatch_cursor = 0
        self.validation_events: list[dict[str, Any]] = []

    def _move_batch(self, batch: dict[str, Any]) -> dict[str, Any]:
        moved: dict[str, Any] = {}
        for key, value in batch.items():
            moved[key] = value.to(self.device) if torch.is_tensor(value) else value
        return moved

    def loss_for_batch(self, batch: dict[str, Any]) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        batch = self._move_batch(batch)
        outputs = self.model(
            anchor_logits=batch["anchor_logits"],
            source_features=batch["source_features"],
            distance_to_union_mm=batch["distance_to_union_mm"],
            t2_present=batch["t2_present"],
            normalized_lge=batch.get("normalized_lge"),
            normalized_t2=batch.get("normalized_t2"),
            teacher_anatomy_probabilities=batch.get("teacher_anatomy_probabilities"),
            teacher_edema_probability=batch.get("teacher_edema_probability"),
            scar_source_margin=batch.get("scar_source_margin"),
            explicit_anchor_probabilities=batch.get("explicit_anchor_probabilities"),
            explicit_anchor_uncertainty=batch.get("explicit_anchor_uncertainty"),
            explicit_soft_union_probability=batch.get("explicit_soft_union_probability"),
            normalized_distance_to_union=batch.get("normalized_distance_to_union"),
            prototype_scar_positive_similarity=batch.get("prototype_scar_positive_similarity"),
            prototype_scar_negative_similarity=batch.get("prototype_scar_negative_similarity"),
            prototype_edema_positive_similarity=batch.get("prototype_edema_positive_similarity"),
            prototype_edema_negative_similarity=batch.get("prototype_edema_negative_similarity"),
            active_pathology=self.config.pathology,
        )
        terms = care_srr_cascade_rescue_loss_terms(
            outputs,
            batch["labels"],
            distance_to_gt_union_mm=batch["distance_to_gt_union_mm"],
            distance_to_gt_pathology_surface_mm=batch["distance_to_gt_pathology_surface_mm"],
            active_pathology=self.config.pathology,
        )
        total = sum(terms.values())
        if not torch.isfinite(total):
            raise FloatingPointError(f"nonfinite loss at optimizer_step={self.optimizer_step}")
        return total, terms

    def train_microbatches(self, batches: Iterable[dict[str, Any]], *, max_optimizer_steps: int | None = None) -> dict[str, Any]:
        self.model.train()
        max_steps = int(max_optimizer_steps or self.config.optimizer_steps)
        losses: list[float] = []
        self.optimizer.zero_grad(set_to_none=True)
        for batch in batches:
            loss, _ = self.loss_for_batch(batch)
            (loss / int(self.config.gradient_accumulation)).backward()
            losses.append(float(loss.detach().cpu()))
            self.microbatch_cursor += 1
            if self.microbatch_cursor % int(self.config.gradient_accumulation) == 0:
                torch.nn.utils.clip_grad_norm_(trainable_parameters_for_pathology(self.model, self.config.pathology), float(self.config.grad_clip_norm))
                self.optimizer.step()
                self.scheduler.step()
                self.optimizer.zero_grad(set_to_none=True)
                self.optimizer_step += 1
                if self.optimizer_step in set(self.config.validation_steps):
                    self.validation_events.append({"optimizer_step": self.optimizer_step, "event": "CALIBRATION_VALIDATION_DUE"})
                if self.optimizer_step >= max_steps:
                    break
        return {
            "optimizer_step": self.optimizer_step,
            "microbatch_cursor": self.microbatch_cursor,
            "loss_count": len(losses),
            "last_loss": losses[-1] if losses else None,
            "validation_events": list(self.validation_events),
        }

    def checkpoint_payload(
        self,
        *,
        schedule_sha256: str,
        initial_state_sha256: str,
        code_sha256: str,
        config_sha256: str,
        source_cache_sha256: str,
        anchor_cache_sha256: str,
        prototype_cache_sha256: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "model_state": self.model.state_dict(),
            "optimizer_state": self.optimizer.state_dict(),
            "scheduler_state": self.scheduler.state_dict(),
            "scaler_state": self.scaler.state_dict(),
            "optimizer_step": int(self.optimizer_step),
            "microbatch_cursor": int(self.microbatch_cursor),
            "schedule_sha256": str(schedule_sha256),
            "initial_state_sha256": str(initial_state_sha256),
            "code_sha256": str(code_sha256),
            "config_sha256": str(config_sha256),
            "source_cache_sha256": str(source_cache_sha256),
            "anchor_cache_sha256": str(anchor_cache_sha256),
            "prototype_cache_sha256": str(prototype_cache_sha256),
            "RNG_states": capture_rng_states(),
            "logical_run_id": self.config.logical_run_id,
            "pathology": self.config.pathology,
            "variant": self.config.variant,
        }

    def save_checkpoint(self, path: Path, **hashes: str) -> dict[str, Any]:
        payload = self.checkpoint_payload(**hashes)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        torch.save(payload, tmp)
        tmp.replace(path)
        return {"path": str(path), "sha256": sha256_bytes(path.read_bytes()), "optimizer_step": self.optimizer_step}

    def load_checkpoint(self, path: Path, *, expected: dict[str, str]) -> dict[str, Any]:
        payload = torch.load(path, map_location=self.device, weights_only=False)
        if int(payload.get("schema_version", 0)) != CHECKPOINT_SCHEMA_VERSION:
            raise ValueError("unsupported checkpoint schema")
        for key, value in expected.items():
            if str(payload.get(key)) != str(value):
                raise ValueError(f"resume hash mismatch for {key}: {payload.get(key)} != {value}")
        self.model.load_state_dict(payload["model_state"])
        self.optimizer.load_state_dict(payload["optimizer_state"])
        self.scheduler.load_state_dict(payload["scheduler_state"])
        self.scaler.load_state_dict(payload["scaler_state"])
        self.optimizer_step = int(payload["optimizer_step"])
        self.microbatch_cursor = int(payload["microbatch_cursor"])
        restore_rng_states(payload["RNG_states"])
        return payload


def checkpoint_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "required_fields": [
            "model_state",
            "optimizer_state",
            "scheduler_state",
            "scaler_state",
            "optimizer_step",
            "microbatch_cursor",
            "schedule_sha256",
            "initial_state_sha256",
            "code_sha256",
            "config_sha256",
            "source_cache_sha256",
            "anchor_cache_sha256",
            "prototype_cache_sha256",
            "RNG_states",
        ],
        "resume_requires_same_hashes": True,
        "partial_attempt_formal_credit": 0,
    }
