"""Frozen full nnU-Net adapter for the CARE-MyoWall-IF pilot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import torch
from torch import nn

from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_source_nnunet


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PLANS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json"
DEFAULT_STOCK_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checkpoint_state_dict(payload: Any) -> dict[str, torch.Tensor]:
    if isinstance(payload, dict):
        for key in ("network_weights", "state_dict", "model_state_dict", "model_state"):
            obj = payload.get(key)
            if isinstance(obj, dict):
                return {str(k).removeprefix("module."): v for k, v in obj.items() if torch.is_tensor(v)}
    if isinstance(payload, dict):
        return {str(k).removeprefix("module."): v for k, v in payload.items() if torch.is_tensor(v)}
    raise TypeError("unsupported checkpoint payload")


class StockNNUNetFeatureAdapter(nn.Module):
    """Loads the complete same-fold stock nnU-Net and exposes frozen logits/F0."""

    input_channel_order = ("LGE", "T2", "C0")
    pathology_logits_used_for_final_output = False

    def __init__(
        self,
        *,
        fold: int = 1,
        plans_path: Path | str = DEFAULT_PLANS,
        checkpoint_path: Path | str | None = None,
        configuration: str = "3d_fullres",
        map_location: str | torch.device = "cpu",
    ) -> None:
        super().__init__()
        self.fold = int(fold)
        self.plans_path = Path(plans_path)
        self.configuration = str(configuration)
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path is not None else DEFAULT_STOCK_ROOT / f"fold_{self.fold}" / "checkpoint_final.pth"
        self.config = CAREPRISMConfig.from_nnunet_plans(self.plans_path, configuration=self.configuration)
        self.network = build_source_nnunet(self.config)
        payload = torch.load(self.checkpoint_path, map_location=map_location, weights_only=False)
        state = checkpoint_state_dict(payload)
        missing, unexpected = self.network.load_state_dict(state, strict=False)
        self.load_missing_keys = list(missing)
        self.load_unexpected_keys = list(unexpected)
        self.parameter_byte_coverage = self._byte_coverage(state, self.network.state_dict())
        for p in self.network.parameters():
            p.requires_grad_(False)
        self.network.eval()
        self._hook_feature: torch.Tensor | None = None
        self._hook_handle = self.network.decoder.stages[-1].register_forward_hook(self._capture_hook)

    @property
    def patch_size(self) -> list[int]:
        plans = json.loads(self.plans_path.read_text(encoding="utf-8"))
        return [int(v) for v in plans["configurations"][self.configuration]["patch_size"]]

    @property
    def stock_parameter_count(self) -> int:
        return int(sum(p.numel() for p in self.network.parameters()))

    @staticmethod
    def _byte_coverage(source: dict[str, torch.Tensor], target: dict[str, torch.Tensor]) -> float:
        matched = 0
        total = 0
        for key, value in target.items():
            total += int(value.numel() * value.element_size())
            src = source.get(key)
            if torch.is_tensor(src) and tuple(src.shape) == tuple(value.shape):
                matched += int(value.numel() * value.element_size())
        return float(matched / max(total, 1))

    def _capture_hook(self, _module: nn.Module, _inputs: tuple[Any, ...], output: Any) -> None:
        if not torch.is_tensor(output):
            raise RuntimeError("network.decoder.stages[-1] did not return a tensor")
        self._hook_feature = output.detach()

    def forward(self, images: torch.Tensor) -> dict[str, torch.Tensor]:
        if images.ndim != 5 or images.shape[1] != 3:
            raise ValueError("stock nnU-Net input must be [B,3,Z,Y,X] ordered as [LGE,T2,C0]")
        self._hook_feature = None
        with torch.no_grad():
            logits = self.network(images.float())
        if self._hook_feature is None:
            raise RuntimeError("decoder.stages[-1] hook did not fire")
        probs = torch.softmax(logits, dim=1)
        anatomy = {
            "p_lv": probs[:, 2:3],
            "p_wall": probs[:, 1:2] + probs[:, 4:5] + probs[:, 5:6],
            "p_rv": probs[:, 3:4],
        }
        return {"logits": logits, "f0": self._hook_feature, **anatomy}

    def parity_report(self, sample: torch.Tensor) -> dict[str, Any]:
        source = build_source_nnunet(self.config)
        payload = torch.load(self.checkpoint_path, map_location=sample.device, weights_only=False)
        missing, unexpected = source.load_state_dict(checkpoint_state_dict(payload), strict=False)
        source.eval()
        with torch.no_grad():
            reference = source(sample.float())
            current = self.forward(sample.float())["logits"]
        diff = (reference - current).abs()
        argmax_changed = int((reference.argmax(1) != current.argmax(1)).sum().item())
        return {
            "status": "PASS" if float(diff.max().item()) <= 1.0e-6 and argmax_changed == 0 and self.parameter_byte_coverage >= 0.99 else "FAIL",
            "checkpoint_path": str(self.checkpoint_path.relative_to(REPO_ROOT) if self.checkpoint_path.is_relative_to(REPO_ROOT) else self.checkpoint_path),
            "checkpoint_sha256": sha256_file(self.checkpoint_path),
            "plans_path": str(self.plans_path.relative_to(REPO_ROOT) if self.plans_path.is_relative_to(REPO_ROOT) else self.plans_path),
            "plans_sha256": sha256_file(self.plans_path),
            "network_class": self.config.network_class_name,
            "patch_size": self.patch_size,
            "parameter_byte_coverage": self.parameter_byte_coverage,
            "missing_keys": self.load_missing_keys,
            "unexpected_keys": self.load_unexpected_keys,
            "reference_missing_keys": list(missing),
            "reference_unexpected_keys": list(unexpected),
            "fp32_stock_logit_parity_max_abs_error": float(diff.max().item()),
            "argmax_changed_voxels": argmax_changed,
            "f0_shape": list(self._hook_feature.shape) if self._hook_feature is not None else None,
        }
