"""Lane A Round9 checkpoint-initialization helpers.

Round9 preserves the nnU-Net501 fold0 representation while expanding the input
stem from the original image channels to image + modality-presence channels.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any

import torch
from torch import nn


def load_checkpoint_state(checkpoint_path: str | Path) -> OrderedDict[str, torch.Tensor]:
    """Load an nnU-Net checkpoint network state dict on CPU."""

    checkpoint = torch.load(Path(checkpoint_path), map_location="cpu", weights_only=False)
    if not isinstance(checkpoint, dict):
        raise TypeError(f"Expected checkpoint dict at {checkpoint_path}, got {type(checkpoint)!r}")
    state = checkpoint.get("network_weights") or checkpoint.get("state_dict")
    if state is None:
        state = checkpoint
    if not isinstance(state, OrderedDict):
        state = OrderedDict(state)
    return state


def _is_expandable_input_weight(source: torch.Tensor, target: torch.Tensor) -> bool:
    return (
        source.ndim >= 3
        and target.ndim == source.ndim
        and source.shape[0] == target.shape[0]
        and source.shape[1] < target.shape[1]
        and source.shape[2:] == target.shape[2:]
    )


def adapt_checkpoint_to_model(
    source_state: dict[str, torch.Tensor],
    model: nn.Module,
    *,
    modality_init: float = 0.0,
) -> tuple[OrderedDict[str, torch.Tensor], list[dict[str, Any]]]:
    """Return a model-compatible state dict and an audit report.

    Compatible tensors are copied directly. Input-stem tensors whose channel
    dimension expands from 3 to 6 are copied for the original channels and the
    added modality-presence channels are initialized to ``modality_init``.
    """

    model_state = model.state_dict()
    adapted: OrderedDict[str, torch.Tensor] = OrderedDict()
    report: list[dict[str, Any]] = []
    source_keys = set(source_state)
    model_keys = set(model_state)

    for key, target in model_state.items():
        source = source_state.get(key)
        if source is None:
            adapted[key] = target
            report.append(
                {
                    "key": key,
                    "checkpoint_shape": "",
                    "model_shape": tuple(target.shape),
                    "status": "missing",
                    "notes": "kept model initialization",
                }
            )
            continue
        if tuple(source.shape) == tuple(target.shape):
            adapted[key] = source.detach().clone().to(dtype=target.dtype)
            report.append(
                {
                    "key": key,
                    "checkpoint_shape": tuple(source.shape),
                    "model_shape": tuple(target.shape),
                    "status": "loaded",
                    "notes": "",
                }
            )
            continue
        if _is_expandable_input_weight(source, target):
            expanded = target.detach().clone()
            expanded.zero_()
            if modality_init:
                expanded.fill_(float(modality_init))
            expanded[:, : source.shape[1], ...] = source.detach().clone().to(dtype=target.dtype)
            adapted[key] = expanded
            report.append(
                {
                    "key": key,
                    "checkpoint_shape": tuple(source.shape),
                    "model_shape": tuple(target.shape),
                    "status": "expanded_first_conv",
                    "notes": f"copied first {source.shape[1]} channels; initialized added channels to {modality_init}",
                }
            )
            continue
        adapted[key] = target
        report.append(
            {
                "key": key,
                "checkpoint_shape": tuple(source.shape),
                "model_shape": tuple(target.shape),
                "status": "shape_mismatch",
                "notes": "kept model initialization",
            }
        )

    for key in sorted(source_keys - model_keys):
        source = source_state[key]
        report.append(
            {
                "key": key,
                "checkpoint_shape": tuple(source.shape),
                "model_shape": "",
                "status": "unexpected",
                "notes": "checkpoint key not present in model",
            }
        )
    return adapted, report


def load_adapted_checkpoint(
    model: nn.Module,
    checkpoint_path: str | Path,
    *,
    modality_init: float = 0.0,
) -> list[dict[str, Any]]:
    """Adapt and load a 3-channel nnU-Net checkpoint into a 6-channel model."""

    source_state = load_checkpoint_state(checkpoint_path)
    adapted, report = adapt_checkpoint_to_model(source_state, model, modality_init=modality_init)
    incompatible = model.load_state_dict(adapted, strict=False)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        report.append(
            {
                "key": "__load_state_dict__",
                "checkpoint_shape": "",
                "model_shape": "",
                "status": "load_state_dict_incompatible",
                "notes": f"missing={list(incompatible.missing_keys)} unexpected={list(incompatible.unexpected_keys)}",
            }
        )
    return report
