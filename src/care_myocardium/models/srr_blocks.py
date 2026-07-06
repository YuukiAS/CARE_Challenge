"""Selective representation retrieval blocks for CARE MyoPS."""

from __future__ import annotations

from collections.abc import Mapping

import torch
from torch import nn


MODALITY_NAMES = ("LGE", "T2", "C0")
TASK_NAMES = ("anatomy", "scar", "edema")


def _conv_block(channels: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv3d(channels, channels, kernel_size=3, padding=1, bias=False),
        nn.GroupNorm(num_groups=max(1, min(8, channels // 4)), num_channels=channels),
        nn.LeakyReLU(0.01, inplace=True),
        nn.Conv3d(channels, channels, kernel_size=3, padding=1, bias=False),
        nn.GroupNorm(num_groups=max(1, min(8, channels // 4)), num_channels=channels),
        nn.LeakyReLU(0.01, inplace=True),
    )


def _as_slot_count(value: int | Mapping[str, int], modality: str) -> int:
    if isinstance(value, Mapping):
        return int(value.get(modality, value.get(modality.lower(), 0)))
    return int(value)


def _as_interaction_slot_count(value: int | Mapping[str, int], pair_name: str) -> int:
    if isinstance(value, Mapping):
        return int(value.get(pair_name, value.get(pair_name.replace("_", "-"), 0)))
    return int(value)


def dictionary_slot_config(name: str, *, use_interactions: bool = True) -> dict[str, object]:
    """Return audited SRR-v3 dictionary slot configuration.

    The M6 contract requires named pair-specific dictionary configs rather than
    reusing the old uniform ``interaction_slots`` default.  The returned values
    are consumed by ``ScaleRetrieval`` and exported through slot metadata.
    """

    if name == "dict_full_interaction":
        return {
            "shared_slots": 8,
            "private_slots": {"LGE": 4, "T2": 4, "C0": 4},
            "interaction_slots": {"lge_t2": 4, "lge_c0": 4, "t2_c0": 4} if use_interactions else {},
            "interaction_pairs": [(0, 1), (0, 2), (1, 2)] if use_interactions else [],
            "router_top_k": 8,
        }
    if name == "dict_conservative_private_shared":
        return {
            "shared_slots": 6,
            "private_slots": {"LGE": 4, "T2": 4, "C0": 2},
            "interaction_slots": {"lge_t2": 2} if use_interactions else {},
            "interaction_pairs": [(0, 1)] if use_interactions else [],
            "router_top_k": 5,
        }
    if name == "dict_scar_precision_edema_safe":
        return {
            "shared_slots": 6,
            "private_slots": {"LGE": 6, "T2": 5, "C0": 2},
            "interaction_slots": {"lge_t2": 3, "lge_c0": 3, "t2_c0": 2} if use_interactions else {},
            "interaction_pairs": [(0, 1), (0, 2), (1, 2)] if use_interactions else [],
            "router_top_k": 6,
        }
    if name == "legacy_interaction_slots":
        return {
            "shared_slots": 4,
            "private_slots": {"LGE": 2, "T2": 2, "C0": 2},
            "interaction_slots": {"lge_t2": 2, "lge_c0": 2, "t2_c0": 2} if use_interactions else {},
            "interaction_pairs": [(0, 1), (0, 2), (1, 2)] if use_interactions else [],
            "router_top_k": 4,
        }
    raise ValueError(f"unknown dictionary_config: {name!r}")


def _fuse_feature_list(features: list[torch.Tensor], availability: torch.Tensor, indices: tuple[int, ...] | None = None) -> torch.Tensor:
    if indices is None:
        indices = tuple(range(len(features)))
    weighted = []
    denom_terms = []
    for idx in indices:
        feat = features[idx]
        mask = availability[:, idx].view(-1, 1, 1, 1, 1).to(dtype=feat.dtype, device=feat.device)
        weighted.append(feat * mask)
        denom_terms.append(mask)
    denom = torch.stack(denom_terms, dim=0).sum(dim=0).clamp_min(1.0)
    return torch.stack(weighted, dim=0).sum(dim=0) / denom


def masked_modality_fusion(features: list[torch.Tensor], availability: torch.Tensor) -> torch.Tensor:
    """Fuse modality features while making unavailable inputs mathematically inert."""

    return _fuse_feature_list(features, availability)


def anchor_summary_from_tensor(
    anchor_features: torch.Tensor | Mapping[str, torch.Tensor] | None,
    *,
    batch_size: int,
    dtype: torch.dtype,
    device: torch.device,
) -> torch.Tensor:
    """Return fixed-size pooled nnU-Net anchor evidence for router conditioning.

    The Phase 1 inventory found nnU-Net probability arrays rather than separate
    logits. This helper accepts probability/logit tensors when a caller wires
    them in and returns five compact features: anatomy probability, edema
    probability, scar probability, mean confidence, and anchor-present flag.
    """

    if anchor_features is None:
        return torch.zeros((batch_size, 5), dtype=dtype, device=device)
    if isinstance(anchor_features, Mapping):
        for key in ("probabilities", "probs", "logits", "anchor", "features"):
            value = anchor_features.get(key)
            if isinstance(value, torch.Tensor):
                return anchor_summary_from_tensor(value, batch_size=batch_size, dtype=dtype, device=device)
        return torch.zeros((batch_size, 5), dtype=dtype, device=device)

    anchor = anchor_features.to(device=device, dtype=dtype)
    if anchor.shape[0] != batch_size:
        raise ValueError(f"anchor batch {anchor.shape[0]} does not match image batch {batch_size}")
    if anchor.ndim >= 3 and anchor.shape[1] >= 2:
        if bool((anchor.detach().min() < 0).item()) or bool((anchor.detach().max() > 1.0).item()):
            probs = torch.softmax(anchor, dim=1)
        else:
            probs = anchor.clamp(0, 1)
        flat = probs.flatten(2)
        anatomy = flat[:, 1 : min(4, flat.shape[1])].sum(dim=1).mean(dim=1, keepdim=True) if flat.shape[1] > 1 else flat.mean(dim=(1, 2), keepdim=True)
        edema = flat[:, 4].mean(dim=1, keepdim=True) if flat.shape[1] > 4 else torch.zeros((batch_size, 1), dtype=dtype, device=device)
        scar = flat[:, 5].mean(dim=1, keepdim=True) if flat.shape[1] > 5 else torch.zeros((batch_size, 1), dtype=dtype, device=device)
        confidence = flat.max(dim=1).values.mean(dim=1, keepdim=True)
    else:
        flat = anchor.reshape(batch_size, -1)
        anatomy = flat.mean(dim=1, keepdim=True)
        edema = flat.std(dim=1, keepdim=True, unbiased=False)
        scar = flat.abs().amax(dim=1, keepdim=True)
        confidence = (flat.abs() > 0).to(dtype=dtype).mean(dim=1, keepdim=True)
    present = (anchor.reshape(batch_size, -1).abs().sum(dim=1, keepdim=True) > 0).to(dtype=dtype)
    return torch.cat([anatomy, edema, scar, confidence, present], dim=1)


class GroupedExpertBank(nn.Module):
    """Multi-slot shared/private/interaction representer bank at one scale."""

    def __init__(
        self,
        channels: int,
        *,
        shared_slots: int = 4,
        private_slots: int | Mapping[str, int] = 2,
        interaction_slots: int | Mapping[str, int] = 2,
        modality_names: tuple[str, ...] = MODALITY_NAMES,
        interaction_pairs: list[tuple[int, ...]] | None = None,
    ) -> None:
        super().__init__()
        self.channels = int(channels)
        self.modality_names = tuple(modality_names)
        if interaction_pairs is None:
            interaction_pairs = [(0, 1), (0, 2), (1, 2)]
        self.interaction_pairs = [tuple(pair) for pair in interaction_pairs]
        self.slot_specs: list[dict[str, object]] = []
        modules = []

        for slot in range(int(shared_slots)):
            self.slot_specs.append({"index": len(self.slot_specs), "group": "shared", "kind": "shared", "slot": slot})
            modules.append(_conv_block(channels))
        for modality_idx, modality in enumerate(self.modality_names):
            for slot in range(_as_slot_count(private_slots, modality)):
                group = f"{modality.lower()}_private"
                self.slot_specs.append(
                    {
                        "index": len(self.slot_specs),
                        "group": group,
                        "kind": "private",
                        "modality": modality,
                        "modality_index": modality_idx,
                        "slot": slot,
                    }
                )
                modules.append(_conv_block(channels))
        for pair in self.interaction_pairs:
            pair_name = "_".join(self.modality_names[idx].lower() for idx in pair)
            for slot in range(_as_interaction_slot_count(interaction_slots, pair_name)):
                self.slot_specs.append(
                    {
                        "index": len(self.slot_specs),
                        "group": f"interaction_{pair_name}",
                        "kind": "interaction",
                        "modalities": tuple(self.modality_names[idx] for idx in pair),
                        "modality_indices": pair,
                        "slot": slot,
                    }
                )
                modules.append(_conv_block(channels))
        if not modules:
            raise ValueError("GroupedExpertBank needs at least one representer slot")
        self.experts = nn.ModuleList(modules)

    @property
    def n_experts(self) -> int:
        return len(self.slot_specs)

    @property
    def slot_metadata(self) -> list[dict[str, object]]:
        return [dict(spec) for spec in self.slot_specs]

    @property
    def slot_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for spec in self.slot_specs:
            group = str(spec["group"])
            counts[group] = counts.get(group, 0) + 1
        return counts

    def availability_mask(self, availability: torch.Tensor) -> torch.Tensor:
        masks = []
        for spec in self.slot_specs:
            kind = str(spec["kind"])
            if kind == "shared":
                masks.append(torch.ones((availability.shape[0], 1), dtype=availability.dtype, device=availability.device))
            elif kind == "private":
                idx = int(spec["modality_index"])
                masks.append(availability[:, idx : idx + 1])
            else:
                pair_mask = torch.ones((availability.shape[0], 1), dtype=availability.dtype, device=availability.device)
                for idx in spec["modality_indices"]:  # type: ignore[index]
                    pair_mask = pair_mask * availability[:, int(idx) : int(idx) + 1]
                masks.append(pair_mask)
        return torch.cat(masks, dim=1)

    def forward(
        self,
        modality_features: list[torch.Tensor],
        availability: torch.Tensor,
    ) -> torch.Tensor:
        fused = _fuse_feature_list(modality_features, availability)
        outputs = []
        for expert, spec in zip(self.experts, self.slot_specs):
            kind = str(spec["kind"])
            if kind == "shared":
                slot_input = fused
            elif kind == "private":
                slot_input = modality_features[int(spec["modality_index"])]
            else:
                slot_input = _fuse_feature_list(modality_features, availability, tuple(int(i) for i in spec["modality_indices"]))  # type: ignore[arg-type,index]
            outputs.append(expert(slot_input))
        return torch.stack(outputs, dim=1)


class RetrievalRouter(nn.Module):
    """Feature, availability, and anchor-conditioned router with invalid-slot mask."""

    def __init__(
        self,
        channels: int,
        n_experts: int,
        modalities: int = 3,
        *,
        anchor_summary_dim: int = 5,
        temperature: float = 1.0,
        top_k: int | None = 4,
        expert_dropout: float = 0.0,
        expert_bias: list[float] | torch.Tensor | None = None,
        hierarchical_prior_strength: float = 0.03,
    ) -> None:
        super().__init__()
        self.temperature = float(temperature)
        self.top_k = None if top_k is None else int(top_k)
        self.expert_dropout = float(expert_dropout)
        self.hierarchical_prior_strength = float(hierarchical_prior_strength)
        input_dim = int(channels) + int(modalities) + int(anchor_summary_dim)
        hidden = max(16, channels // 2)
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.LeakyReLU(0.01, inplace=True),
            nn.Linear(hidden, n_experts),
        )
        if expert_bias is None:
            bias = torch.zeros(n_experts, dtype=torch.float32)
        else:
            bias = torch.zeros(n_experts, dtype=torch.float32)
            values = torch.as_tensor(expert_bias, dtype=torch.float32)
            bias[: min(n_experts, values.numel())] = values[:n_experts]
        self.register_buffer("expert_bias", bias)

    def forward(
        self,
        fused: torch.Tensor,
        availability: torch.Tensor,
        valid_experts: torch.Tensor,
        anchor_summary: torch.Tensor | None = None,
    ) -> torch.Tensor:
        summary = fused.mean(dim=(2, 3, 4))
        if anchor_summary is None:
            anchor_summary = torch.zeros((fused.shape[0], 5), dtype=fused.dtype, device=fused.device)
        query = torch.cat([summary, availability.to(dtype=fused.dtype, device=fused.device), anchor_summary.to(dtype=fused.dtype, device=fused.device)], dim=1)
        logits = self.net(query) + self.expert_bias.to(dtype=fused.dtype, device=fused.device)
        valid = valid_experts.to(dtype=fused.dtype, device=fused.device)
        if self.training and self.expert_dropout > 0:
            keep = (torch.rand_like(valid) >= self.expert_dropout).to(dtype=valid.dtype)
            dropped_valid = valid * keep
            empty = dropped_valid.sum(dim=1, keepdim=True) <= 0
            valid = torch.where(empty, valid, dropped_valid)
        masked_logits = (logits / max(self.temperature, 1e-3)).masked_fill(valid <= 0, torch.finfo(logits.dtype).min)
        weights = torch.softmax(masked_logits, dim=1) * valid
        if self.top_k is not None and self.top_k > 0 and self.top_k < weights.shape[1]:
            _, indices = torch.topk(weights, k=self.top_k, dim=1)
            keep = torch.zeros_like(weights).scatter(1, indices, 1.0) * valid
            weights = weights * keep
        weights = weights / weights.sum(dim=1, keepdim=True).clamp_min(1e-6)
        if self.hierarchical_prior_strength > 0:
            prior = valid / valid.sum(dim=1, keepdim=True).clamp_min(1e-6)
            strength = min(max(self.hierarchical_prior_strength, 0.0), 0.95)
            weights = (1.0 - strength) * weights + strength * prior
            weights = weights * valid
            weights = weights / weights.sum(dim=1, keepdim=True).clamp_min(1e-6)
        return weights


def task_slot_biases(slot_specs: list[dict[str, object]]) -> dict[str, list[float]]:
    biases = {task: [] for task in TASK_NAMES}
    for spec in slot_specs:
        group = str(spec["group"])
        kind = str(spec["kind"])
        has_lge = "lge" in group
        has_t2 = "t2" in group
        has_c0 = "c0" in group
        biases["anatomy"].append(0.45 if kind == "shared" else (0.20 if has_c0 else 0.05))
        biases["scar"].append(0.85 if "lge_private" == group else (0.35 if has_lge else (-0.15 if has_t2 and not has_lge else 0.0)))
        biases["edema"].append(0.85 if "t2_private" == group else (0.35 if has_t2 else (-0.10 if has_lge and not has_t2 else 0.0)))
    return biases


class MultiSlotSRRRetrievalBlock(nn.Module):
    """One-scale multi-slot SRR dictionary for anatomy, scar, and edema."""

    def __init__(
        self,
        channels: int,
        *,
        shared_slots: int = 4,
        private_slots: int | Mapping[str, int] = 2,
        interaction_slots: int | Mapping[str, int] = 2,
        router_temperatures: dict[str, float] | None = None,
        router_top_k: int | None = 4,
        expert_dropout: float = 0.0,
        interaction_pairs: list[tuple[int, ...]] | None = None,
        task_expert_biases: dict[str, list[float]] | None = None,
        hierarchical_prior_strength: float = 0.03,
    ) -> None:
        super().__init__()
        temps = router_temperatures or {}
        self.bank = GroupedExpertBank(
            channels,
            shared_slots=shared_slots,
            private_slots=private_slots,
            interaction_slots=interaction_slots,
            interaction_pairs=interaction_pairs,
        )
        default_biases = task_slot_biases(self.bank.slot_specs)
        if task_expert_biases:
            default_biases.update(task_expert_biases)
        self.routers = nn.ModuleDict(
            {
                task: RetrievalRouter(
                    channels,
                    self.bank.n_experts,
                    temperature=temps.get(task, 1.0),
                    top_k=router_top_k,
                    expert_dropout=expert_dropout,
                    expert_bias=default_biases.get(task),
                    hierarchical_prior_strength=hierarchical_prior_strength,
                )
                for task in TASK_NAMES
            }
        )
        self.last_valid_mask: torch.Tensor | None = None

    @property
    def n_experts(self) -> int:
        return self.bank.n_experts

    @property
    def slot_metadata(self) -> list[dict[str, object]]:
        return self.bank.slot_metadata

    @property
    def slot_counts(self) -> dict[str, int]:
        return self.bank.slot_counts

    def forward(
        self,
        modality_features: list[torch.Tensor],
        availability: torch.Tensor,
        anchor_features: torch.Tensor | Mapping[str, torch.Tensor] | None = None,
    ) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        if len(modality_features) != len(MODALITY_NAMES):
            raise ValueError(f"expected {len(MODALITY_NAMES)} modality feature tensors, got {len(modality_features)}")
        availability = availability.to(device=modality_features[0].device, dtype=modality_features[0].dtype).clamp(0, 1)
        fused = _fuse_feature_list(modality_features, availability)
        anchor_summary = anchor_summary_from_tensor(
            anchor_features,
            batch_size=fused.shape[0],
            dtype=fused.dtype,
            device=fused.device,
        )
        valid = self.bank.availability_mask(availability)
        self.last_valid_mask = valid.detach()
        expert_outputs = self.bank(modality_features, availability)
        routed: dict[str, torch.Tensor] = {}
        gates: dict[str, torch.Tensor] = {}
        for name, router in self.routers.items():
            gate = router(fused, availability, valid, anchor_summary)
            gates[name] = gate
            shape = (gate.shape[0], gate.shape[1], 1, 1, 1, 1)
            routed[name] = torch.sum(gate.view(shape) * expert_outputs, dim=1)
        return routed, gates


class SRRRetrievalBlock(nn.Module):
    """Backward-compatible one-scale dictionary block for fused Lite features."""

    def __init__(
        self,
        channels: int,
        shared_experts: int = 4,
        private_experts: int = 2,
        router_temperatures: dict[str, float] | None = None,
        router_top_k: int | None = 4,
        expert_dropout: float = 0.0,
        interaction_pairs: list[tuple[int, ...]] | None = None,
        task_expert_biases: dict[str, list[float]] | None = None,
        hierarchical_prior_strength: float = 0.03,
    ) -> None:
        super().__init__()
        self.block = MultiSlotSRRRetrievalBlock(
            channels,
            shared_slots=shared_experts,
            private_slots=private_experts,
            interaction_slots=2 if interaction_pairs else 0,
            router_temperatures=router_temperatures,
            router_top_k=router_top_k,
            expert_dropout=expert_dropout,
            interaction_pairs=interaction_pairs or [],
            task_expert_biases=task_expert_biases,
            hierarchical_prior_strength=hierarchical_prior_strength,
        )

    @property
    def n_experts(self) -> int:
        return self.block.n_experts

    @property
    def slot_metadata(self) -> list[dict[str, object]]:
        return self.block.slot_metadata

    @property
    def slot_counts(self) -> dict[str, int]:
        return self.block.slot_counts

    @property
    def last_valid_mask(self) -> torch.Tensor | None:
        return self.block.last_valid_mask

    def forward(
        self,
        fused: torch.Tensor,
        availability: torch.Tensor,
        anchor_features: torch.Tensor | Mapping[str, torch.Tensor] | None = None,
    ) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        modality_features = [fused, fused, fused]
        return self.block(modality_features, availability, anchor_features)


class TaskSpecificSRRRetrievalBlock(nn.Module):
    """Separate task banks for anatomy, scar, and edema, each multi-slot."""

    def __init__(
        self,
        channels: int,
        shared_experts: int = 4,
        private_experts: int = 2,
        router_temperatures: dict[str, float] | None = None,
        router_top_k: int | None = 4,
        expert_dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.blocks = nn.ModuleDict(
            {
                name: MultiSlotSRRRetrievalBlock(
                    channels,
                    shared_slots=shared_experts,
                    private_slots=private_experts,
                    interaction_slots=0,
                    router_temperatures=router_temperatures,
                    router_top_k=router_top_k,
                    expert_dropout=expert_dropout,
                )
                for name in TASK_NAMES
            }
        )

    @property
    def slot_metadata(self) -> list[dict[str, object]]:
        return next(iter(self.blocks.values())).slot_metadata

    @property
    def slot_counts(self) -> dict[str, int]:
        return next(iter(self.blocks.values())).slot_counts

    @property
    def last_valid_mask(self) -> torch.Tensor | None:
        first = next(iter(self.blocks.values()))
        return first.last_valid_mask

    def forward(
        self,
        fused: torch.Tensor,
        availability: torch.Tensor,
        anchor_features: torch.Tensor | Mapping[str, torch.Tensor] | None = None,
    ) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        routed: dict[str, torch.Tensor] = {}
        gates: dict[str, torch.Tensor] = {}
        modality_features = [fused, fused, fused]
        for name, block in self.blocks.items():
            task_routed, task_gates = block(modality_features, availability, anchor_features)
            routed[name] = task_routed[name]
            gates[name] = task_gates[name]
        return routed, gates


def gate_diagnostics(
    gates: dict[str, torch.Tensor],
    metadata: dict[str, list[dict[str, object]]],
    valid_masks: dict[str, torch.Tensor] | None = None,
    *,
    eps: float = 1e-6,
    inactive_threshold: float = 1e-4,
    collapse_threshold: float = 0.95,
) -> dict[str, dict[str, object]]:
    """Summarize slot usage, entropy, inactive slots, and collapse warnings."""

    out: dict[str, dict[str, object]] = {}
    valid_masks = valid_masks or {}
    for name, gate in gates.items():
        usage = gate.detach().mean(dim=0)
        entropy = -(gate.detach() * torch.log(gate.detach().clamp_min(eps))).sum(dim=1)
        valid = valid_masks.get(name)
        active_valid = valid.detach().mean(dim=0) > 0 if valid is not None else torch.ones_like(usage, dtype=torch.bool)
        inactive = [int(i) for i, value in enumerate(usage) if bool(active_valid[i]) and float(value) < inactive_threshold]
        max_weight = gate.detach().max(dim=1).values
        group_usage: dict[str, float] = {}
        for idx, spec in enumerate(metadata[name]):
            group = str(spec["group"])
            group_usage[group] = group_usage.get(group, 0.0) + float(usage[idx])
        out[name] = {
            "entropy_mean": float(entropy.mean()),
            "entropy_min": float(entropy.min()),
            "max_weight_mean": float(max_weight.mean()),
            "inactive_slots": inactive,
            "inactive_slot_count": len(inactive),
            "collapse_warning": bool((max_weight > collapse_threshold).any().item()),
            "group_usage": group_usage,
        }
    return out
