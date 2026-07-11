"""M10 spatial SRR dictionary blocks.

These blocks are intentionally independent from the older global
``ScaleRetrieval`` path.  They provide the wave-1 contract surface for M10:
exact 16-slot per-scale banks, deterministic invalid-slot closure, and
two-pass lesion-conditioned spatial retrieval.
"""

from __future__ import annotations

from collections.abc import Mapping

import torch
import torch.nn.functional as F
from torch import nn

from src.care_myocardium.models.srr_blocks import MODALITY_NAMES, slot_validity_mask


M10_SLOT_SPECS: tuple[dict[str, object], ...] = (
    *({"group": "shared", "kind": "shared", "slot": idx} for idx in range(4)),
    *(
        {"group": "lge_private", "kind": "private", "modality": "LGE", "modality_index": 0, "slot": idx}
        for idx in range(2)
    ),
    *(
        {"group": "t2_private", "kind": "private", "modality": "T2", "modality_index": 1, "slot": idx}
        for idx in range(2)
    ),
    *(
        {"group": "c0_private", "kind": "private", "modality": "C0", "modality_index": 2, "slot": idx}
        for idx in range(2)
    ),
    *(
        {
            "group": "interaction_lge_t2",
            "kind": "interaction",
            "modalities": ("LGE", "T2"),
            "modality_indices": (0, 1),
            "slot": idx,
        }
        for idx in range(2)
    ),
    *(
        {
            "group": "interaction_lge_c0",
            "kind": "interaction",
            "modalities": ("LGE", "C0"),
            "modality_indices": (0, 2),
            "slot": idx,
        }
        for idx in range(2)
    ),
    *(
        {
            "group": "interaction_t2_c0",
            "kind": "interaction",
            "modalities": ("T2", "C0"),
            "modality_indices": (1, 2),
            "slot": idx,
        }
        for idx in range(2)
    ),
)

for _idx, _spec in enumerate(M10_SLOT_SPECS):
    _spec["index"] = _idx


def m10_slot_metadata() -> list[dict[str, object]]:
    return [dict(spec) for spec in M10_SLOT_SPECS]


class _ResidualExpert3d(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        groups = max(1, min(8, channels // 4))
        self.norm1 = nn.GroupNorm(groups, channels)
        self.dw1 = nn.Conv3d(channels, channels, kernel_size=3, padding=1, groups=channels, bias=False)
        self.pw1 = nn.Conv3d(channels, channels, kernel_size=1, bias=False)
        self.norm2 = nn.GroupNorm(groups, channels)
        self.dw2 = nn.Conv3d(channels, channels, kernel_size=3, padding=1, groups=channels, bias=False)
        self.pw2 = nn.Conv3d(channels, channels, kernel_size=1, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.pw1(self.dw1(F.silu(self.norm1(x))))
        x = self.pw2(self.dw2(F.silu(self.norm2(x))))
        return x + residual


class M10SlotBank(nn.Module):
    """Exact M10 16-slot bank with deterministic invalid-slot zeroing."""

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.channels = int(channels)
        self.shared_project = nn.Conv3d(self.channels * 2, self.channels, kernel_size=1, bias=False)
        self.interaction_projectors = nn.ModuleDict(
            {
                "interaction_lge_t2": nn.Conv3d(self.channels * 4, self.channels, kernel_size=1, bias=False),
                "interaction_lge_c0": nn.Conv3d(self.channels * 4, self.channels, kernel_size=1, bias=False),
                "interaction_t2_c0": nn.Conv3d(self.channels * 4, self.channels, kernel_size=1, bias=False),
            }
        )
        self.experts = nn.ModuleList([_ResidualExpert3d(self.channels) for _ in M10_SLOT_SPECS])

    @property
    def slot_metadata(self) -> list[dict[str, object]]:
        return m10_slot_metadata()

    @staticmethod
    def _masked_stats(features: list[torch.Tensor], availability: torch.Tensor) -> torch.Tensor:
        masks = [availability[:, idx].view(-1, 1, 1, 1, 1).to(device=features[idx].device, dtype=features[idx].dtype) for idx in range(3)]
        stacked = torch.stack([features[idx] * masks[idx] for idx in range(3)], dim=0)
        denom = torch.stack(masks, dim=0).sum(dim=0).clamp_min(1.0)
        mean = stacked.sum(dim=0) / denom
        variance = torch.stack([((features[idx] - mean) * masks[idx]).square() for idx in range(3)], dim=0).sum(dim=0) / denom
        return torch.cat([mean, variance], dim=1)

    def forward(self, features: list[torch.Tensor], availability: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if len(features) != 3:
            raise ValueError(f"M10SlotBank expects {len(MODALITY_NAMES)} modality features, got {len(features)}")
        availability = availability.to(device=features[0].device, dtype=features[0].dtype).clamp(0, 1)
        valid = slot_validity_mask(availability, self.slot_metadata)
        shared = self.shared_project(self._masked_stats(features, availability))
        outputs = []
        for expert, spec in zip(self.experts, M10_SLOT_SPECS):
            kind = str(spec["kind"])
            if kind == "shared":
                slot_input = shared
            elif kind == "private":
                idx = int(spec["modality_index"])
                slot_input = features[idx]
            else:
                i, j = (int(v) for v in spec["modality_indices"])  # type: ignore[index]
                fi = features[i]
                fj = features[j]
                slot_input = self.interaction_projectors[str(spec["group"])](
                    torch.cat([fi, fj, (fi - fj).abs(), fi * fj], dim=1)
                )
            slot_valid = valid[:, int(spec["index"])].view(-1, 1, 1, 1, 1)
            outputs.append(expert(slot_input * slot_valid) * slot_valid)
        return torch.stack(outputs, dim=1), valid


class M10SpatialRouter(nn.Module):
    """Voxelwise router with availability embedding and invalid-slot closure."""

    def __init__(self, channels: int, *, context_channels: int = 0, top_k: int | None = None) -> None:
        super().__init__()
        self.channels = int(channels)
        self.context_channels = int(context_channels)
        self.top_k = None if top_k is None else int(top_k)
        self.availability_embed = nn.Linear(3, 16)
        self.router = nn.Sequential(
            nn.Conv3d(self.channels + 16 + self.context_channels, self.channels, kernel_size=1, bias=False),
            nn.GroupNorm(max(1, min(8, self.channels // 4)), self.channels),
            nn.SiLU(inplace=True),
            nn.Conv3d(self.channels, len(M10_SLOT_SPECS), kernel_size=1),
        )

    def forward(
        self,
        base: torch.Tensor,
        availability: torch.Tensor,
        valid: torch.Tensor,
        context: torch.Tensor | None = None,
    ) -> torch.Tensor:
        availability = availability.to(device=base.device, dtype=base.dtype).clamp(0, 1)
        valid = valid.to(device=base.device, dtype=base.dtype)
        emb = self.availability_embed(availability).to(dtype=base.dtype)
        emb_map = emb.view(emb.shape[0], emb.shape[1], 1, 1, 1).expand(-1, -1, *base.shape[-3:])
        parts = [base, emb_map]
        if self.context_channels:
            if context is None:
                context = base.new_zeros((base.shape[0], self.context_channels, *base.shape[-3:]))
            parts.append(context.to(device=base.device, dtype=base.dtype))
        logits = self.router(torch.cat(parts, dim=1))
        valid_map = valid.view(valid.shape[0], valid.shape[1], 1, 1, 1)
        masked_logits = logits.masked_fill(valid_map <= 0, torch.finfo(logits.dtype).min)
        weights = torch.softmax(masked_logits, dim=1) * valid_map
        if self.top_k is not None and 0 < self.top_k < weights.shape[1]:
            _, indices = torch.topk(weights, k=self.top_k, dim=1)
            keep = torch.zeros_like(weights).scatter_(1, indices, 1.0) * valid_map
            weights = weights * keep
        return weights / weights.sum(dim=1, keepdim=True).clamp_min(1e-6)


def _weighted_sum(weights: torch.Tensor, experts: torch.Tensor) -> torch.Tensor:
    return torch.sum(weights.unsqueeze(2) * experts, dim=1)


class M10TwoPassSpatialDictionary(nn.Module):
    """D1-D3 spatial dictionary with optional Pattern-SIP/memory hooks."""

    def __init__(
        self,
        channels: int,
        *,
        top_k_first: int | None = 4,
        top_k_second: int | None = 2,
        enable_pattern_sip: bool = False,
        enable_memory: bool = False,
    ) -> None:
        super().__init__()
        self.channels = int(channels)
        self.enable_pattern_sip = bool(enable_pattern_sip)
        self.enable_memory = bool(enable_memory)
        self.bank = M10SlotBank(channels)
        self.anatomy_router = M10SpatialRouter(channels, context_channels=4, top_k=top_k_first)
        self.scar_router0 = M10SpatialRouter(channels, context_channels=8, top_k=top_k_first)
        self.edema_router0 = M10SpatialRouter(channels, context_channels=8, top_k=top_k_first)
        self.scar_router1 = M10SpatialRouter(channels, context_channels=9, top_k=top_k_second)
        self.edema_router1 = M10SpatialRouter(channels, context_channels=9, top_k=top_k_second)
        self.scar_proposal0 = nn.Conv3d(channels, 1, kernel_size=1)
        self.edema_proposal0 = nn.Conv3d(channels, 1, kernel_size=1)

    @property
    def slot_metadata(self) -> list[dict[str, object]]:
        return self.bank.slot_metadata

    @staticmethod
    def _ctx(anatomy_context: Mapping[str, torch.Tensor] | None, reference: torch.Tensor) -> torch.Tensor:
        if anatomy_context is None:
            return reference.new_zeros((reference.shape[0], 4, *reference.shape[-3:]))
        keys = ("p_union", "p_lv", "p_rv", "union_distance")
        maps = []
        for key in keys:
            value = anatomy_context.get(key)
            if isinstance(value, torch.Tensor):
                value = value.to(device=reference.device, dtype=reference.dtype)
                if value.shape[-3:] != reference.shape[-3:]:
                    value = F.interpolate(value, size=reference.shape[-3:], mode="trilinear", align_corners=False)
                maps.append(value[:, :1])
            else:
                maps.append(torch.zeros_like(reference[:, :1]))
        return torch.cat(maps, dim=1)

    @staticmethod
    def _resize_map(value: torch.Tensor | None, reference: torch.Tensor) -> torch.Tensor:
        if value is None:
            return torch.zeros_like(reference[:, :1])
        out = value.to(device=reference.device, dtype=reference.dtype)
        if out.shape[-3:] != reference.shape[-3:]:
            out = F.interpolate(out, size=reference.shape[-3:], mode="trilinear", align_corners=False)
        return out[:, :1]

    def forward(
        self,
        features: list[torch.Tensor],
        availability: torch.Tensor,
        *,
        anatomy_context: Mapping[str, torch.Tensor] | None = None,
        initial_evidence: Mapping[str, torch.Tensor] | None = None,
        prototype_maps: Mapping[str, torch.Tensor] | None = None,
    ) -> dict[str, torch.Tensor | dict[str, torch.Tensor] | list[dict[str, object]] | str]:
        experts, valid = self.bank(features, availability)
        base = features[0]
        anatomy_ctx = self._ctx(anatomy_context, base)
        anatomy_gate = self.anatomy_router(base, availability, valid, anatomy_ctx)
        anatomy_retrieved = _weighted_sum(anatomy_gate, experts)

        scar_ev = self._resize_map(None if initial_evidence is None else initial_evidence.get("scar"), base)
        edema_ev = self._resize_map(None if initial_evidence is None else initial_evidence.get("edema"), base)
        scar_proto_pos = self._resize_map(None if prototype_maps is None else prototype_maps.get("scar_pos"), base)
        scar_proto_neg = self._resize_map(None if prototype_maps is None else prototype_maps.get("scar_neg"), base)
        edema_proto_pos = self._resize_map(None if prototype_maps is None else prototype_maps.get("edema_pos"), base)
        edema_proto_neg = self._resize_map(None if prototype_maps is None else prototype_maps.get("edema_neg"), base)

        scar_ctx0 = torch.cat([anatomy_ctx, scar_ev, scar_proto_pos, scar_proto_neg, (scar_proto_pos - scar_proto_neg).abs()], dim=1)
        edema_ctx0 = torch.cat([anatomy_ctx, edema_ev, edema_proto_pos, edema_proto_neg, (edema_proto_pos - edema_proto_neg).abs()], dim=1)
        scar_gate0 = self.scar_router0(base, availability, valid, scar_ctx0)
        edema_gate0 = self.edema_router0(base, availability, valid, edema_ctx0)
        scar_r0 = _weighted_sum(scar_gate0, experts)
        edema_r0 = _weighted_sum(edema_gate0, experts)
        scar_p0 = torch.sigmoid(self.scar_proposal0(scar_r0))
        edema_p0 = torch.sigmoid(self.edema_proposal0(edema_r0))

        scar_ctx1 = torch.cat([anatomy_ctx, scar_r0.mean(dim=1, keepdim=True), scar_p0, scar_ev, scar_proto_pos, scar_proto_neg], dim=1)
        edema_ctx1 = torch.cat([anatomy_ctx, edema_r0.mean(dim=1, keepdim=True), edema_p0, edema_ev, edema_proto_pos, edema_proto_neg], dim=1)
        scar_gate1 = self.scar_router1(base, availability, valid, scar_ctx1)
        edema_gate1 = self.edema_router1(base, availability, valid, edema_ctx1)
        no_t2 = (availability[:, 1] <= 0).view(-1, 1, 1, 1, 1).to(device=base.device)
        edema_gate1 = torch.where(no_t2, torch.zeros_like(edema_gate1), edema_gate1)
        edema_gate1 = edema_gate1 / edema_gate1.sum(dim=1, keepdim=True).clamp_min(1e-6)
        return {
            "slot_metadata": self.slot_metadata,
            "valid_mask": valid,
            "expert_outputs": experts,
            "anatomy_retrieved": anatomy_retrieved,
            "scar_retrieved": _weighted_sum(scar_gate1, experts),
            "edema_retrieved": _weighted_sum(edema_gate1, experts),
            "scar_initial_proposal": scar_p0,
            "edema_initial_proposal": torch.where(no_t2, torch.zeros_like(edema_p0), edema_p0),
            "gates": {
                "m10_anatomy_spatial": anatomy_gate,
                "m10_scar_pass0": scar_gate0,
                "m10_edema_pass0": edema_gate0,
                "m10_scar_pass1": scar_gate1,
                "m10_edema_pass1": edema_gate1,
            },
            "pattern_sip_status": "independent_enabled" if self.enable_pattern_sip else "disabled_by_design",
            "memory_status": "cross_fitted_memory_enabled" if self.enable_memory else "disabled_by_design",
        }
