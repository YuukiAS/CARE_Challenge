"""SRR-v2 U-Net style model for CARE MyoPS rescue experiments."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from src.care_myocardium.models.pathology_heads import AnatomyPathologyHeads
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


class ScaleRetrieval(nn.Module):
    """Shared/private/interaction retrieval at one U-Net scale."""

    def __init__(self, channels: int, modalities: int = 3, use_interactions: bool = True) -> None:
        super().__init__()
        self.modalities = modalities
        self.use_interactions = use_interactions
        self.shared = ConvBlock(channels, channels)
        self.private = nn.ModuleList([ConvBlock(channels, channels) for _ in range(modalities)])
        self.interaction_pairs = [(0, 1), (0, 2), (1, 2)] if use_interactions else []
        self.interaction = nn.ModuleList([ConvBlock(channels, channels) for _ in self.interaction_pairs])
        self.n_experts = 1 + modalities + len(self.interaction_pairs)
        hidden = max(16, channels // 2)
        self.routers = nn.ModuleDict(
            {
                task: nn.Sequential(
                    nn.Linear(channels + modalities, hidden),
                    nn.LeakyReLU(0.01, inplace=True),
                    nn.Linear(hidden, self.n_experts),
                )
                for task in ("anatomy", "scar", "edema")
            }
        )

    def _valid_mask(self, availability: torch.Tensor) -> torch.Tensor:
        shared = torch.ones((availability.shape[0], 1), dtype=availability.dtype, device=availability.device)
        masks = [availability[:, idx : idx + 1] for idx in range(self.modalities)]
        for pair in self.interaction_pairs:
            pair_mask = torch.ones_like(shared)
            for idx in pair:
                pair_mask = pair_mask * availability[:, idx : idx + 1]
            masks.append(pair_mask)
        return torch.cat([shared, *masks], dim=1)

    @staticmethod
    def _fuse(features: list[torch.Tensor], availability: torch.Tensor) -> torch.Tensor:
        weighted = []
        for idx, feat in enumerate(features):
            mask = availability[:, idx].view(-1, 1, 1, 1, 1).to(dtype=feat.dtype, device=feat.device)
            weighted.append(feat * mask)
        denom = availability.sum(dim=1).clamp_min(1.0).view(-1, 1, 1, 1, 1).to(dtype=features[0].dtype, device=features[0].device)
        return torch.stack(weighted, dim=0).sum(dim=0) / denom

    def forward(self, modality_features: list[torch.Tensor], availability: torch.Tensor) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        fused = self._fuse(modality_features, availability)
        experts = [self.shared(fused)]
        experts.extend(block(feat) for block, feat in zip(self.private, modality_features))
        for block, pair in zip(self.interaction, self.interaction_pairs):
            pair_features = [modality_features[idx] for idx in pair]
            pair_av = availability[:, list(pair)]
            experts.append(block(self._fuse(pair_features, pair_av)))
        expert_outputs = torch.stack(experts, dim=1)
        valid = self._valid_mask(availability)
        query = torch.cat([fused.mean(dim=(2, 3, 4)), availability], dim=1)
        routed: dict[str, torch.Tensor] = {}
        gates: dict[str, torch.Tensor] = {}
        for task, router in self.routers.items():
            logits = router(query).masked_fill(valid <= 0, torch.finfo(query.dtype).min)
            gate = torch.softmax(logits, dim=1) * valid
            gate = gate / gate.sum(dim=1, keepdim=True).clamp_min(1e-6)
            gates[task] = gate
            routed[task] = (gate.view(gate.shape[0], gate.shape[1], 1, 1, 1, 1) * expert_outputs).sum(dim=1)
        return routed, gates


class TaskDecoder(nn.Module):
    def __init__(self, base_channels: int) -> None:
        super().__init__()
        self.up1 = nn.ConvTranspose3d(base_channels * 4, base_channels * 2, 2, stride=2)
        self.dec1 = ConvBlock(base_channels * 4, base_channels * 2)
        self.up0 = nn.ConvTranspose3d(base_channels * 2, base_channels, 2, stride=2)
        self.dec0 = ConvBlock(base_channels * 2, base_channels)

    def forward(self, routed: list[torch.Tensor]) -> torch.Tensor:
        f0, f1, f2 = routed
        x = self.up1(f2)
        x = F.interpolate(x, size=f1.shape[-3:], mode="trilinear", align_corners=False) if x.shape[-3:] != f1.shape[-3:] else x
        x = self.dec1(torch.cat([x, f1], dim=1))
        x = self.up0(x)
        x = F.interpolate(x, size=f0.shape[-3:], mode="trilinear", align_corners=False) if x.shape[-3:] != f0.shape[-3:] else x
        return self.dec0(torch.cat([x, f0], dim=1))


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

    def forward(self, x: torch.Tensor, availability: torch.Tensor) -> dict[str, torch.Tensor]:
        if x.shape[1] != 3:
            raise ValueError(f"SRRV2MyoPSUNet expects 3 image channels, got {x.shape[1]}")
        availability = availability.to(device=x.device, dtype=x.dtype).clamp(0, 1)
        per_modality = [encoder(x[:, idx : idx + 1], availability[:, idx]) for idx, encoder in enumerate(self.encoders)]
        routed_by_task = {task: [] for task in ("anatomy", "scar", "edema")}
        gates: dict[str, torch.Tensor] = {}
        for scale, retrieval in enumerate(self.retrieval):
            routed, scale_gates = retrieval([features[scale] for features in per_modality], availability)
            for task in routed_by_task:
                routed_by_task[task].append(routed[task])
                gates[f"{task}_scale{scale}"] = scale_gates[task]
        anatomy_features = self.decoders["anatomy"](routed_by_task["anatomy"])
        scar_features = self.decoders["scar"](routed_by_task["scar"])
        edema_features = self.decoders["edema"](routed_by_task["edema"])
        outputs = self.heads(anatomy_features, scar_features, edema_features)
        if self.proposal_head is not None:
            self.proposal_head(outputs, scar_features, edema_features, availability)
        outputs["gates"] = gates
        outputs["availability"] = availability
        outputs["expert_usage"] = {name: gate.mean(dim=0) for name, gate in gates.items()}
        return outputs
