"""SRR-v2 U-Net style model for CARE MyoPS rescue experiments."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from src.care_myocardium.models.pathology_heads import AnatomyPathologyHeads
from src.care_myocardium.models.srr_blocks import MultiSlotSRRRetrievalBlock, gate_diagnostics
from src.care_myocardium.models.srr_myops import PathologyProposalHead


def _groups(channels: int) -> int:
    return max(1, min(8, channels // 4))


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, 3, padding=1, bias=False),
            nn.GroupNorm(_groups(out_channels), out_channels),
            nn.LeakyReLU(0.01, inplace=True),
            nn.Conv3d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.GroupNorm(_groups(out_channels), out_channels),
            nn.LeakyReLU(0.01, inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ModalityEncoder(nn.Module):
    """Three-scale modality-private encoder with strict missing-modality closure."""

    def __init__(self, base_channels: int) -> None:
        super().__init__()
        self.stage0 = ConvBlock(1, base_channels)
        self.stage1 = ConvBlock(base_channels, base_channels * 2)
        self.stage2 = ConvBlock(base_channels * 2, base_channels * 4)

    @staticmethod
    def _safe_pool(x: torch.Tensor) -> torch.Tensor:
        kernel = tuple(1 if size < 2 else 2 for size in x.shape[-3:])
        if kernel == (1, 1, 1):
            return x
        return F.avg_pool3d(x, kernel_size=kernel, stride=kernel, ceil_mode=True)

    def forward(self, x: torch.Tensor, present: torch.Tensor) -> list[torch.Tensor]:
        mask = present.view(-1, 1, 1, 1, 1).to(device=x.device, dtype=x.dtype)
        x = x * mask
        f0 = self.stage0(x) * mask
        f1 = self.stage1(self._safe_pool(f0)) * mask
        f2 = self.stage2(self._safe_pool(f1)) * mask
        return [f0, f1, f2]



class StrongModalityEncoder(nn.Module):
    """Four-scale modality-private encoder with strict missing-modality closure."""

    def __init__(self, base_channels: int) -> None:
        super().__init__()
        self.stage0 = ConvBlock(1, base_channels)
        self.stage1 = ConvBlock(base_channels, base_channels * 2)
        self.stage2 = ConvBlock(base_channels * 2, base_channels * 4)
        self.stage3 = ConvBlock(base_channels * 4, base_channels * 8)

    @staticmethod
    def _safe_pool(x: torch.Tensor) -> torch.Tensor:
        return ModalityEncoder._safe_pool(x)

    def forward(self, x: torch.Tensor, present: torch.Tensor) -> list[torch.Tensor]:
        mask = present.view(-1, 1, 1, 1, 1).to(device=x.device, dtype=x.dtype)
        x = x * mask
        f0 = self.stage0(x) * mask
        f1 = self.stage1(self._safe_pool(f0)) * mask
        f2 = self.stage2(self._safe_pool(f1)) * mask
        f3 = self.stage3(self._safe_pool(f2)) * mask
        return [f0, f1, f2, f3]


class ProfileModalityEncoder(nn.Module):
    """Four-scale encoder with explicit audited channel profiles."""

    def __init__(self, scale_channels: list[int] | tuple[int, int, int, int]) -> None:
        super().__init__()
        if len(scale_channels) != 4:
            raise ValueError("ProfileModalityEncoder requires exactly four channel scales")
        c0, c1, c2, c3 = [int(v) for v in scale_channels]
        self.scale_channels = [c0, c1, c2, c3]
        self.stage0 = ConvBlock(1, c0)
        self.stage1 = ConvBlock(c0, c1)
        self.stage2 = ConvBlock(c1, c2)
        self.stage3 = ConvBlock(c2, c3)

    @staticmethod
    def _safe_pool(x: torch.Tensor) -> torch.Tensor:
        return ModalityEncoder._safe_pool(x)

    def forward(self, x: torch.Tensor, present: torch.Tensor) -> list[torch.Tensor]:
        mask = present.view(-1, 1, 1, 1, 1).to(device=x.device, dtype=x.dtype)
        x = x * mask
        f0 = self.stage0(x) * mask
        f1 = self.stage1(self._safe_pool(f0)) * mask
        f2 = self.stage2(self._safe_pool(f1)) * mask
        f3 = self.stage3(self._safe_pool(f2)) * mask
        return [f0, f1, f2, f3]


def encoder_profile_scale_channels(base_channels: int, encoder_profile: str) -> list[int]:
    base = int(base_channels)
    if encoder_profile == "tiny_3scale":
        return [base, base * 2, base * 4]
    if encoder_profile == "strong_4scale":
        return [base, base * 2, base * 4, base * 8]
    if encoder_profile == "balanced_4scale":
        return [16, 32, 64, 128]
    if encoder_profile == "full_4scale":
        return [32, 64, 128, 256]
    if encoder_profile == "safe_4scale":
        return [12, 24, 48, 96]
    raise ValueError(f"unknown encoder_profile: {encoder_profile!r}")


def build_modality_encoder(base_channels: int, encoder_profile: str) -> nn.Module:
    if encoder_profile == "tiny_3scale":
        return ModalityEncoder(base_channels)
    if encoder_profile == "strong_4scale":
        return StrongModalityEncoder(base_channels)
    if encoder_profile in {"balanced_4scale", "full_4scale", "safe_4scale"}:
        return ProfileModalityEncoder(encoder_profile_scale_channels(base_channels, encoder_profile))
    raise ValueError(f"unknown encoder_profile: {encoder_profile!r}")


class ScaleRetrieval(nn.Module):
    """Per-scale multi-slot shared/private/interaction retrieval bank.

    The class name remains for existing callers, but the old implementation
    with one shared block plus one block per modality is no longer used.
    """

    def __init__(
        self,
        channels: int,
        modalities: int = 3,
        use_interactions: bool = True,
        shared_slots: int = 4,
        private_slots: int = 2,
        interaction_slots: int = 2,
        dictionary_config: str = "legacy_interaction_slots",
        router_top_k: int | None = 4,
    ) -> None:
        super().__init__()
        if modalities != 3:
            raise ValueError("ScaleRetrieval is locked to Dataset501 modalities LGE,T2,C0")
        if dictionary_config != "legacy_interaction_slots":
            from src.care_myocardium.models.srr_blocks import dictionary_slot_config

            cfg = dictionary_slot_config(dictionary_config, use_interactions=use_interactions)
            shared_slots = int(cfg["shared_slots"])
            private_slots = cfg["private_slots"]  # type: ignore[assignment]
            interaction_slots = cfg["interaction_slots"]  # type: ignore[assignment]
            interaction_pairs = cfg["interaction_pairs"]  # type: ignore[assignment]
            router_top_k = cfg.get("router_top_k", router_top_k)  # type: ignore[assignment]
            self.dictionary_config = str(dictionary_config)
        else:
            interaction_pairs = [(0, 1), (0, 2), (1, 2)] if use_interactions else []
            self.dictionary_config = "legacy_interaction_slots"
        self.block = MultiSlotSRRRetrievalBlock(
            channels,
            shared_slots=shared_slots,
            private_slots=private_slots,
            interaction_slots=interaction_slots if use_interactions else 0,
            interaction_pairs=interaction_pairs,
            router_top_k=router_top_k,
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
        modality_features: list[torch.Tensor],
        availability: torch.Tensor,
        anchor_features: torch.Tensor | dict[str, torch.Tensor] | None = None,
    ) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        return self.block(modality_features, availability, anchor_features)


class FlexibleTaskDecoder(nn.Module):
    """Decoder for 3- or 4-scale SRR feature pyramids."""

    def __init__(self, scale_channels: list[int] | tuple[int, ...]) -> None:
        super().__init__()
        if len(scale_channels) < 3:
            raise ValueError("FlexibleTaskDecoder requires at least three scales")
        self.scale_channels = [int(ch) for ch in scale_channels]
        self.ups = nn.ModuleList()
        self.decoders = nn.ModuleList()
        current = self.scale_channels[-1]
        for skip_channels in reversed(self.scale_channels[:-1]):
            self.ups.append(nn.ConvTranspose3d(current, skip_channels, 2, stride=2))
            self.decoders.append(ConvBlock(skip_channels * 2, skip_channels))
            current = skip_channels

    def forward(self, routed: list[torch.Tensor]) -> torch.Tensor:
        if len(routed) != len(self.scale_channels):
            raise ValueError(f"decoder expected {len(self.scale_channels)} scales, got {len(routed)}")
        x = routed[-1]
        skips = list(reversed(routed[:-1]))
        for up, dec, skip in zip(self.ups, self.decoders, skips):
            x = up(x)
            if x.shape[-3:] != skip.shape[-3:]:
                x = F.interpolate(x, size=skip.shape[-3:], mode="trilinear", align_corners=False)
            x = dec(torch.cat([x, skip], dim=1))
        return x


class TaskDecoder(FlexibleTaskDecoder):
    def __init__(self, base_channels: int) -> None:
        super().__init__([base_channels, base_channels * 2, base_channels * 4])


class SRRV2MyoPSUNet(nn.Module):
    """Isolated multi-scale SRR-v2 route.

    Input channel order remains LGE, T2, C0. Availability order remains the
    same. Private retrieval experts operate on modality-specific features at
    each scale, not on an already averaged fused feature.
    """

    def __init__(
        self,
        base_channels: int = 12,
        proposal_mode: str = "none",
        use_interactions: bool = True,
        proposal_final_mix_weight: float = 0.50,
    ) -> None:
        super().__init__()
        self.base_channels = int(base_channels)
        self.proposal_mode = proposal_mode
        self.encoders = nn.ModuleList([ModalityEncoder(base_channels) for _ in range(3)])
        self.retrieval = nn.ModuleList(
            [
                ScaleRetrieval(base_channels, use_interactions=use_interactions),
                ScaleRetrieval(base_channels * 2, use_interactions=use_interactions),
                ScaleRetrieval(base_channels * 4, use_interactions=use_interactions),
            ]
        )
        self.decoders = nn.ModuleDict({task: TaskDecoder(base_channels) for task in ("anatomy", "scar", "edema")})
        self.heads = AnatomyPathologyHeads(base_channels, prior_strength=0.45)
        self.proposal_head = (
            PathologyProposalHead(base_channels, mode=proposal_mode, final_mix_weight=proposal_final_mix_weight)
            if proposal_mode != "none"
            else None
        )

    def forward(
        self,
        x: torch.Tensor,
        availability: torch.Tensor,
        anchor_features: torch.Tensor | dict[str, torch.Tensor] | None = None,
        component_features: torch.Tensor | dict[str, torch.Tensor] | None = None,
    ) -> dict[str, torch.Tensor]:
        if x.shape[1] != 3:
            raise ValueError(f"SRRV2MyoPSUNet expects 3 image channels, got {x.shape[1]}")
        availability = availability.to(device=x.device, dtype=x.dtype).clamp(0, 1)
        per_modality = [encoder(x[:, idx : idx + 1], availability[:, idx]) for idx, encoder in enumerate(self.encoders)]
        routed_by_task = {task: [] for task in ("anatomy", "scar", "edema")}
        gates: dict[str, torch.Tensor] = {}
        for scale, retrieval in enumerate(self.retrieval):
            routed, scale_gates = retrieval([features[scale] for features in per_modality], availability, anchor_features)
            for task in routed_by_task:
                routed_by_task[task].append(routed[task])
                gates[f"{task}_scale{scale}"] = scale_gates[task]
        gate_metadata = {
            f"{task}_scale{scale}": self.retrieval[scale].slot_metadata
            for scale in range(len(self.retrieval))
            for task in routed_by_task
        }
        gate_valid_masks = {
            f"{task}_scale{scale}": self.retrieval[scale].last_valid_mask
            for scale in range(len(self.retrieval))
            for task in routed_by_task
            if self.retrieval[scale].last_valid_mask is not None
        }
        anatomy_features = self.decoders["anatomy"](routed_by_task["anatomy"])
        scar_features = self.decoders["scar"](routed_by_task["scar"])
        edema_features = self.decoders["edema"](routed_by_task["edema"])
        outputs = self.heads(anatomy_features, scar_features, edema_features)
        if self.proposal_head is not None:
            self.proposal_head(
                outputs,
                scar_features,
                edema_features,
                availability,
                anchor_features=anchor_features,
                component_features=component_features,
            )
        outputs["gates"] = gates
        outputs["availability"] = availability
        outputs["expert_usage"] = {name: gate.mean(dim=0) for name, gate in gates.items()}
        outputs["dictionary_slot_counts"] = {f"scale{idx}": block.slot_counts for idx, block in enumerate(self.retrieval)}
        outputs["dictionary_slot_metadata"] = gate_metadata
        outputs["gate_valid_masks"] = gate_valid_masks
        outputs["dictionary_diagnostics"] = gate_diagnostics(gates, gate_metadata, gate_valid_masks)
        return outputs
