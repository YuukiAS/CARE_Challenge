"""SRR-MyoPS-Lite first-party model skeleton."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from src.care_myocardium.models.pathology_heads import AnatomyPathologyHeads
from src.care_myocardium.models.srr_blocks import SRRRetrievalBlock, TaskSpecificSRRRetrievalBlock, masked_modality_fusion


class ModalityStem(nn.Module):
    """Stem that strictly closes unavailable modality features after bias/norm."""

    def __init__(self, out_channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv3d(1, out_channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(num_groups=max(1, min(8, out_channels // 4)), num_channels=out_channels),
            nn.LeakyReLU(0.01, inplace=True),
        )

    def forward(self, x: torch.Tensor, present: torch.Tensor) -> torch.Tensor:
        mask = present.view(-1, 1, 1, 1, 1).to(device=x.device, dtype=x.dtype)
        return self.net(x * mask) * mask


class SRRMyoPSLite(nn.Module):
    """Minimal trainable Result4 SRR architecture for Dataset501.

    Input channel order is Dataset501 order: LGE, T2, C0. Availability uses the
    same order and must be provided at inference, so missing modalities are
    never inferred from zero intensity.
    """

    def __init__(
        self,
        in_channels: int = 3,
        base_channels: int = 16,
        prior_strength: float = 0.5,
        router_temperatures: dict[str, float] | None = None,
        expert_dropout: float = 0.0,
        dictionary_mode: str = "standard",
    ) -> None:
        super().__init__()
        if in_channels != 3:
            raise ValueError("SRRMyoPSLite expects Dataset501 channels: LGE,T2,C0")
        self.in_channels = in_channels
        self.base_channels = int(base_channels)
        self.dictionary_mode = dictionary_mode
        self.stems = nn.ModuleList([ModalityStem(base_channels) for _ in range(3)])
        retrieval_kwargs = {
            "router_temperatures": router_temperatures,
            "expert_dropout": expert_dropout,
        }
        if dictionary_mode == "task_specific_dictionary":
            self.retrieval = TaskSpecificSRRRetrievalBlock(base_channels, shared_experts=2, private_experts=1, **retrieval_kwargs)
        else:
            block_kwargs: dict[str, object] = {}
            if dictionary_mode == "cross_modal_interaction_dictionary":
                block_kwargs["interaction_pairs"] = [(0, 1), (0, 2), (1, 2)]
            elif dictionary_mode == "anchor_guided_dictionary":
                block_kwargs["task_expert_biases"] = {
                    "anatomy": [0.7, 0.1, 0.1, 0.5],
                    "scar": [0.2, 1.0, -0.3, 0.1],
                    "edema": [0.2, -0.2, 1.0, 0.1],
                }
            elif dictionary_mode == "hierarchical_router_dictionary":
                block_kwargs["hierarchical_prior_strength"] = 0.25
            self.retrieval = SRRRetrievalBlock(base_channels, shared_experts=1, private_experts=1, **retrieval_kwargs, **block_kwargs)
        self.context_retrieval = None
        if dictionary_mode == "multiscale_dictionary":
            self.context_retrieval = SRRRetrievalBlock(base_channels, shared_experts=1, private_experts=1, **retrieval_kwargs)
        self.refine = nn.Sequential(
            nn.Conv3d(base_channels, base_channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(num_groups=max(1, min(8, base_channels // 4)), num_channels=base_channels),
            nn.LeakyReLU(0.01, inplace=True),
        )
        self.heads = AnatomyPathologyHeads(base_channels, prior_strength=prior_strength)

    def forward(self, x: torch.Tensor, availability: torch.Tensor) -> dict[str, torch.Tensor]:
        if x.ndim != 5:
            raise ValueError(f"expected x shape (B,3,D,H,W), got {tuple(x.shape)}")
        if availability.shape != (x.shape[0], 3):
            raise ValueError(f"expected availability shape (B,3), got {tuple(availability.shape)}")
        availability = availability.to(device=x.device, dtype=x.dtype).clamp(0, 1)
        features = [stem(x[:, idx : idx + 1], availability[:, idx]) for idx, stem in enumerate(self.stems)]
        fused = masked_modality_fusion(features, availability)
        routed, gates = self.retrieval(fused, availability)
        if self.context_retrieval is not None:
            pooled = F.avg_pool3d(fused, kernel_size=2, stride=2, ceil_mode=True)
            context_routed, context_gates = self.context_retrieval(pooled, availability)
            for name in routed:
                context = F.interpolate(context_routed[name], size=fused.shape[-3:], mode="trilinear", align_corners=False)
                routed[name] = 0.65 * routed[name] + 0.35 * context
                gates[f"{name}_context"] = context_gates[name]
        outputs = self.heads(
            self.refine(routed["anatomy"]),
            self.refine(routed["scar"]),
            self.refine(routed["edema"]),
        )
        outputs["gates"] = gates
        outputs["availability"] = availability
        outputs["expert_usage"] = {name: gate.mean(dim=0) for name, gate in gates.items()}
        return outputs


def build_srr_myops_lite(base_channels: int = 16) -> SRRMyoPSLite:
    return SRRMyoPSLite(base_channels=base_channels)


class ConditionalDualHeadControl(nn.Module):
    """Availability-aware late-fusion control without retrieval gates."""

    def __init__(self, in_channels: int = 3, base_channels: int = 16, prior_strength: float = 0.5) -> None:
        super().__init__()
        if in_channels != 3:
            raise ValueError("ConditionalDualHeadControl expects Dataset501 channels: LGE,T2,C0")
        self.stems = nn.ModuleList([ModalityStem(base_channels) for _ in range(3)])
        self.refine = nn.Sequential(
            nn.Conv3d(base_channels, base_channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(num_groups=max(1, min(8, base_channels // 4)), num_channels=base_channels),
            nn.LeakyReLU(0.01, inplace=True),
        )
        self.heads = AnatomyPathologyHeads(base_channels, prior_strength=prior_strength)

    def forward(self, x: torch.Tensor, availability: torch.Tensor) -> dict[str, torch.Tensor]:
        if x.ndim != 5:
            raise ValueError(f"expected x shape (B,3,D,H,W), got {tuple(x.shape)}")
        availability = availability.to(device=x.device, dtype=x.dtype).clamp(0, 1)
        features = [stem(x[:, idx : idx + 1], availability[:, idx]) for idx, stem in enumerate(self.stems)]
        fused = self.refine(masked_modality_fusion(features, availability))
        outputs = self.heads(fused, fused, fused)
        outputs["gates"] = {}
        outputs["availability"] = availability
        outputs["expert_usage"] = {}
        return outputs


def build_conditional_dualhead_control(base_channels: int = 16) -> ConditionalDualHeadControl:
    return ConditionalDualHeadControl(base_channels=base_channels)
