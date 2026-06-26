"""Selective representation retrieval blocks for CARE MyoPS."""

from __future__ import annotations

import torch
from torch import nn


def _conv_block(channels: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv3d(channels, channels, kernel_size=3, padding=1, bias=False),
        nn.GroupNorm(num_groups=max(1, min(8, channels // 4)), num_channels=channels),
        nn.LeakyReLU(0.01, inplace=True),
        nn.Conv3d(channels, channels, kernel_size=3, padding=1, bias=False),
        nn.GroupNorm(num_groups=max(1, min(8, channels // 4)), num_channels=channels),
        nn.LeakyReLU(0.01, inplace=True),
    )


class ExpertBank(nn.Module):
    """Shared and modality-private expert bank at one feature scale."""

    def __init__(
        self,
        channels: int,
        shared_experts: int = 1,
        private_experts: int = 1,
        modalities: int = 3,
        interaction_pairs: list[tuple[int, ...]] | None = None,
    ) -> None:
        super().__init__()
        self.channels = int(channels)
        self.shared_experts = int(shared_experts)
        self.private_experts = int(private_experts)
        self.modalities = int(modalities)
        self.interaction_pairs = list(interaction_pairs or [])
        self.shared = nn.ModuleList([_conv_block(channels) for _ in range(shared_experts)])
        self.private = nn.ModuleList([_conv_block(channels) for _ in range(private_experts * modalities)])
        self.interaction = nn.ModuleList([_conv_block(channels) for _ in self.interaction_pairs])

    @property
    def n_experts(self) -> int:
        return self.shared_experts + self.private_experts * self.modalities + len(self.interaction_pairs)

    def availability_mask(self, availability: torch.Tensor) -> torch.Tensor:
        """Return valid expert mask with unavailable modality-private experts off."""

        batch = availability.shape[0]
        shared = torch.ones((batch, self.shared_experts), device=availability.device, dtype=availability.dtype)
        private_masks = []
        for modality_idx in range(self.modalities):
            for _ in range(self.private_experts):
                private_masks.append(availability[:, modality_idx : modality_idx + 1])
        interaction_masks = []
        for pair in self.interaction_pairs:
            pair_mask = torch.ones((batch, 1), device=availability.device, dtype=availability.dtype)
            for modality_idx in pair:
                pair_mask = pair_mask * availability[:, modality_idx : modality_idx + 1]
            interaction_masks.append(pair_mask)
        return torch.cat([shared, *private_masks, *interaction_masks], dim=1)

    def forward(self, fused: torch.Tensor) -> list[torch.Tensor]:
        return [expert(fused) for expert in [*self.shared, *self.private, *self.interaction]]


class RetrievalRouter(nn.Module):
    """Availability plus feature-summary router with strict invalid-expert mask."""

    def __init__(
        self,
        channels: int,
        n_experts: int,
        modalities: int = 3,
        temperature: float = 1.0,
        expert_dropout: float = 0.0,
        expert_bias: list[float] | None = None,
        hierarchical_prior_strength: float = 0.0,
    ) -> None:
        super().__init__()
        self.temperature = float(temperature)
        self.expert_dropout = float(expert_dropout)
        self.hierarchical_prior_strength = float(hierarchical_prior_strength)
        self.net = nn.Sequential(
            nn.Linear(channels + modalities, max(16, channels // 2)),
            nn.LeakyReLU(0.01, inplace=True),
            nn.Linear(max(16, channels // 2), n_experts),
        )
        if expert_bias is None:
            bias = torch.zeros(n_experts, dtype=torch.float32)
        else:
            bias = torch.zeros(n_experts, dtype=torch.float32)
            values = torch.as_tensor(expert_bias, dtype=torch.float32)
            bias[: min(n_experts, values.numel())] = values[:n_experts]
        self.register_buffer("expert_bias", bias)

    def forward(self, fused: torch.Tensor, availability: torch.Tensor, valid_experts: torch.Tensor) -> torch.Tensor:
        summary = fused.mean(dim=(2, 3, 4))
        logits = self.net(torch.cat([summary, availability], dim=1)) + self.expert_bias.to(dtype=fused.dtype, device=fused.device)
        valid = valid_experts
        if self.training and self.expert_dropout > 0:
            keep = (torch.rand_like(valid) >= self.expert_dropout).to(dtype=valid.dtype)
            dropped_valid = valid * keep
            empty = dropped_valid.sum(dim=1, keepdim=True) <= 0
            valid = torch.where(empty, valid, dropped_valid)
        temperature = max(self.temperature, 1e-3)
        masked_logits = (logits / temperature).masked_fill(valid <= 0, torch.finfo(logits.dtype).min)
        weights = torch.softmax(masked_logits, dim=1)
        weights = weights * valid
        weights = weights / weights.sum(dim=1, keepdim=True).clamp_min(1e-6)
        if self.hierarchical_prior_strength > 0:
            prior = valid / valid.sum(dim=1, keepdim=True).clamp_min(1e-6)
            strength = min(max(self.hierarchical_prior_strength, 0.0), 0.95)
            weights = (1.0 - strength) * weights + strength * prior
            weights = weights * valid
            weights = weights / weights.sum(dim=1, keepdim=True).clamp_min(1e-6)
        return weights


class SRRRetrievalBlock(nn.Module):
    """One-scale shared/private feature retrieval for anatomy, scar, and edema."""

    def __init__(
        self,
        channels: int,
        shared_experts: int = 1,
        private_experts: int = 1,
        router_temperatures: dict[str, float] | None = None,
        expert_dropout: float = 0.0,
        interaction_pairs: list[tuple[int, ...]] | None = None,
        task_expert_biases: dict[str, list[float]] | None = None,
        hierarchical_prior_strength: float = 0.0,
    ) -> None:
        super().__init__()
        temps = router_temperatures or {}
        biases = task_expert_biases or {}
        self.bank = ExpertBank(channels, shared_experts=shared_experts, private_experts=private_experts, interaction_pairs=interaction_pairs)
        self.routers = nn.ModuleDict(
            {
                "anatomy": RetrievalRouter(
                    channels,
                    self.bank.n_experts,
                    temperature=temps.get("anatomy", 1.0),
                    expert_dropout=expert_dropout,
                    expert_bias=biases.get("anatomy"),
                    hierarchical_prior_strength=hierarchical_prior_strength,
                ),
                "scar": RetrievalRouter(
                    channels,
                    self.bank.n_experts,
                    temperature=temps.get("scar", 1.0),
                    expert_dropout=expert_dropout,
                    expert_bias=biases.get("scar"),
                    hierarchical_prior_strength=hierarchical_prior_strength,
                ),
                "edema": RetrievalRouter(
                    channels,
                    self.bank.n_experts,
                    temperature=temps.get("edema", 1.0),
                    expert_dropout=expert_dropout,
                    expert_bias=biases.get("edema"),
                    hierarchical_prior_strength=hierarchical_prior_strength,
                ),
            }
        )

    def forward(self, fused: torch.Tensor, availability: torch.Tensor) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        valid = self.bank.availability_mask(availability)
        expert_outputs = torch.stack(self.bank(fused), dim=1)
        routed: dict[str, torch.Tensor] = {}
        gates: dict[str, torch.Tensor] = {}
        for name, router in self.routers.items():
            gate = router(fused, availability, valid)
            gates[name] = gate
            shape = (gate.shape[0], gate.shape[1], 1, 1, 1, 1)
            routed[name] = torch.sum(gate.view(shape) * expert_outputs, dim=1)
        return routed, gates


class TaskSpecificSRRRetrievalBlock(nn.Module):
    """Separate lightweight dictionary banks for anatomy, scar, and edema."""

    def __init__(
        self,
        channels: int,
        shared_experts: int = 1,
        private_experts: int = 1,
        router_temperatures: dict[str, float] | None = None,
        expert_dropout: float = 0.0,
    ) -> None:
        super().__init__()
        temps = router_temperatures or {}
        self.banks = nn.ModuleDict({name: ExpertBank(channels, shared_experts, private_experts) for name in ("anatomy", "scar", "edema")})
        self.routers = nn.ModuleDict(
            {
                name: RetrievalRouter(
                    channels,
                    self.banks[name].n_experts,
                    temperature=temps.get(name, 1.0),
                    expert_dropout=expert_dropout,
                )
                for name in ("anatomy", "scar", "edema")
            }
        )

    def forward(self, fused: torch.Tensor, availability: torch.Tensor) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        routed: dict[str, torch.Tensor] = {}
        gates: dict[str, torch.Tensor] = {}
        for name, bank in self.banks.items():
            valid = bank.availability_mask(availability)
            expert_outputs = torch.stack(bank(fused), dim=1)
            gate = self.routers[name](fused, availability, valid)
            gates[name] = gate
            shape = (gate.shape[0], gate.shape[1], 1, 1, 1, 1)
            routed[name] = torch.sum(gate.view(shape) * expert_outputs, dim=1)
        return routed, gates


def masked_modality_fusion(features: list[torch.Tensor], availability: torch.Tensor) -> torch.Tensor:
    """Fuse modality features while making unavailable inputs mathematically inert."""

    weighted = []
    for idx, feat in enumerate(features):
        mask = availability[:, idx].view(-1, 1, 1, 1, 1).to(dtype=feat.dtype, device=feat.device)
        weighted.append(feat * mask)
    denom = availability.sum(dim=1).clamp_min(1.0).view(-1, 1, 1, 1, 1).to(features[0].dtype)
    return torch.stack(weighted, dim=0).sum(dim=0) / denom
