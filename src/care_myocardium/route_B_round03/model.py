"""Route-local four-scale SRR-v3 MyoPS model for Round03 gates."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

import torch
from torch import nn
import torch.nn.functional as F

from .contract import EXPERTS_PER_SCALE, MODALITY_ORDER, SCALES, assert_modality_order


def _groups(channels: int) -> int:
    return max(1, min(8, channels // 4))


def _conv_norm_act(channels: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv3d(channels, channels, 3, padding=1, bias=False),
        nn.GroupNorm(_groups(channels), channels),
        nn.SiLU(),
        nn.Conv3d(channels, channels, 3, padding=1, bias=False),
        nn.GroupNorm(_groups(channels), channels),
    )


class ResidualExpert(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.body = _conv_norm_act(channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.silu(x + self.body(x))


class ExpertScale(nn.Module):
    """Sixteen valid-mask-aware shared/private/interaction experts."""

    family_names = (
        ("shared",) * 4
        + ("LGE_private",) * 2
        + ("T2_private",) * 2
        + ("C0_private",) * 2
        + ("LGE_T2_interaction",) * 2
        + ("LGE_C0_interaction",) * 2
        + ("T2_C0_interaction",) * 2
    )

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.channels = int(channels)
        self.experts = nn.ModuleList([ResidualExpert(channels) for _ in range(EXPERTS_PER_SCALE)])
        self.pair_project = nn.ModuleDict(
            {
                "LGE_T2": nn.Conv3d(channels * 2, channels, 1, bias=False),
                "LGE_C0": nn.Conv3d(channels * 2, channels, 1, bias=False),
                "T2_C0": nn.Conv3d(channels * 2, channels, 1, bias=False),
            }
        )
        query_channels = channels + 16 + 8
        self.router = nn.Sequential(
            nn.Conv3d(query_channels, max(8, channels // 2), 1),
            nn.GroupNorm(1, max(8, channels // 2)),
            nn.SiLU(),
            nn.Conv3d(max(8, channels // 2), EXPERTS_PER_SCALE, 1),
        )

    @staticmethod
    def _availability_embedding(availability: torch.Tensor, spatial: tuple[int, int, int]) -> torch.Tensor:
        b = availability.shape[0]
        values = torch.zeros(b, 16, *spatial, device=availability.device, dtype=availability.dtype)
        values[:, :3] = availability[:, :, None, None, None]
        values[:, 3:6] = 1.0 - availability[:, :, None, None, None]
        values[:, 6:7] = availability[:, 0:1, None, None, None] * availability[:, 1:2, None, None, None]
        values[:, 7:8] = availability[:, 0:1, None, None, None] * availability[:, 2:3, None, None, None]
        values[:, 8:9] = availability[:, 1:2, None, None, None] * availability[:, 2:3, None, None, None]
        values[:, 9:10] = availability.sum(dim=1, keepdim=True)[:, :, None, None, None] / 3.0
        return values

    @staticmethod
    def _valid_mask(availability: torch.Tensor) -> torch.Tensor:
        lge, t2, c0 = availability[:, 0], availability[:, 1], availability[:, 2]
        masks = [
            torch.ones_like(lge) for _ in range(4)
        ] + [
            lge,
            lge,
            t2,
            t2,
            c0,
            c0,
            lge * t2,
            lge * t2,
            lge * c0,
            lge * c0,
            t2 * c0,
            t2 * c0,
        ]
        return torch.stack(masks, dim=1)

    def forward(
        self,
        modality_features: dict[str, torch.Tensor],
        availability: torch.Tensor,
        anchor_context: torch.Tensor,
        proposal_context: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        lge = modality_features["LGE"] * availability[:, 0, None, None, None, None]
        t2 = modality_features["T2"] * availability[:, 1, None, None, None, None]
        c0 = modality_features["C0"] * availability[:, 2, None, None, None, None]
        inputs = [lge, lge, lge, lge, lge, lge, t2, t2, c0, c0]
        inputs.extend([self.pair_project["LGE_T2"](torch.cat([lge, t2], dim=1))] * 2)
        inputs.extend([self.pair_project["LGE_C0"](torch.cat([lge, c0], dim=1))] * 2)
        inputs.extend([self.pair_project["T2_C0"](torch.cat([t2, c0], dim=1))] * 2)
        expert_out = torch.stack([expert(x) for expert, x in zip(self.experts, inputs)], dim=1)
        fused = (lge + t2 + c0) / availability.sum(dim=1).clamp_min(1.0)[:, None, None, None, None]
        spatial = fused.shape[-3:]
        proposal = torch.zeros(anchor_context.shape[0], 2, *spatial, device=fused.device, dtype=fused.dtype)
        if proposal_context is not None:
            proposal = F.interpolate(proposal_context, size=spatial, mode="trilinear", align_corners=False)
        anchor = F.interpolate(anchor_context, size=spatial, mode="trilinear", align_corners=False)
        query = torch.cat([fused, self._availability_embedding(availability, spatial), anchor[:, :4], anchor[:, 4:6], proposal], dim=1)
        logits = self.router(query)
        valid = self._valid_mask(availability).to(dtype=fused.dtype, device=fused.device)
        weights = torch.softmax(logits.masked_fill(valid[:, :, None, None, None] < 0.5, -1.0e4), dim=1)
        invalid_weight_max = (weights * (1.0 - valid[:, :, None, None, None])).abs().max()
        routed = (weights[:, :, None] * expert_out).sum(dim=1)
        return routed, {"weights": weights, "valid": valid, "invalid_weight_max": invalid_weight_max}


class OfflinePrototypeBank(nn.Module):
    """Frozen OOF prototype bank with no bootstrap or EMA formal path."""

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.source = "four_shard_fold_safe_oof_fitted_inference_frozen"
        self.register_buffer("scar_positive", self._init_bank(8, channels, "scar_positive"))
        self.register_buffer("scar_negative", self._init_bank(12, channels, "scar_negative"))
        self.register_buffer("edema_positive", self._init_bank(8, channels, "edema_positive"))
        self.register_buffer("edema_safe_negative", self._init_bank(12, channels, "edema_safe_negative_t2_present_only"))

    @staticmethod
    def _init_bank(count: int, channels: int, key: str) -> torch.Tensor:
        seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)
        gen = torch.Generator().manual_seed(seed)
        return F.normalize(torch.randn(count, channels, generator=gen), dim=1)

    @staticmethod
    def similarity(features: torch.Tensor, bank: torch.Tensor) -> torch.Tensor:
        emb = F.normalize(features, dim=1)
        proto = F.normalize(bank, dim=1)
        return torch.einsum("bcdhw,kc->bkdhw", emb, proto).max(dim=1, keepdim=True).values


@dataclass
class MyoPSForwardReceipt:
    invalid_weight_max: float
    no_t2_edema_delta_abs_max: float
    changed_logit_l1: float


class RouteBRound03MyoPS(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.modality_order = MODALITY_ORDER
        self.scales = SCALES
        self.stems = nn.ModuleDict({mod: nn.Conv3d(1, SCALES[0], 3, padding=1) for mod in MODALITY_ORDER})
        self.down = nn.ModuleList([nn.Conv3d(SCALES[i], SCALES[i + 1], 3, stride=2, padding=1) for i in range(3)])
        self.expert_scales = nn.ModuleList([ExpertScale(channels) for channels in SCALES])
        self.prototype_bank = OfflinePrototypeBank(SCALES[0])
        self.anatomy_head = nn.Conv3d(sum(SCALES), 4, 1)
        self.scar_proposal = nn.Conv3d(SCALES[0] + 4, 1, 3, padding=2, dilation=2)
        self.edema_proposal = nn.Conv3d(SCALES[0] + 5, 1, 3, padding=3, dilation=3)
        self.scar_refiner = nn.Sequential(ResidualExpert(SCALES[0]), nn.Conv3d(SCALES[0], 1, 1))
        self.edema_refiner = nn.Sequential(ResidualExpert(SCALES[0]), nn.Conv3d(SCALES[0], 1, 1))
        self.gate = nn.Sequential(nn.Conv3d(12, 16, 1), nn.GroupNorm(4, 16), nn.SiLU(), nn.Conv3d(16, 1, 1), nn.Sigmoid())

    def forward(self, x: torch.Tensor, availability: torch.Tensor, anchor_logits: torch.Tensor) -> dict[str, torch.Tensor | MyoPSForwardReceipt]:
        assert_modality_order(self.modality_order)
        availability = availability.to(device=x.device, dtype=x.dtype).clamp(0, 1)
        current = {mod: self.stems[mod](x[:, idx : idx + 1] * availability[:, idx, None, None, None, None]) for idx, mod in enumerate(MODALITY_ORDER)}
        routed_scales = []
        receipts = []
        proposal_context = None
        for level, scale in enumerate(self.expert_scales):
            routed, receipt = scale(current, availability, anchor_logits, proposal_context)
            routed_scales.append(routed)
            receipts.append(receipt)
            if level < len(self.down):
                current = {mod: self.down[level](feat) for mod, feat in current.items()}
        up = [F.interpolate(feat, size=routed_scales[0].shape[-3:], mode="trilinear", align_corners=False) for feat in routed_scales]
        fused = torch.cat(up, dim=1)
        anatomy = self.anatomy_head(fused)
        base = routed_scales[0]
        anchor_prob = torch.softmax(anchor_logits, dim=1)
        anchor_context = F.interpolate(anchor_prob[:, :4], size=base.shape[-3:], mode="trilinear", align_corners=False)
        pos_scar = self.prototype_bank.similarity(base, self.prototype_bank.scar_positive)
        neg_scar = self.prototype_bank.similarity(base, self.prototype_bank.scar_negative)
        pos_edema = self.prototype_bank.similarity(base, self.prototype_bank.edema_positive)
        neg_edema = self.prototype_bank.similarity(base, self.prototype_bank.edema_safe_negative)
        scar_prop = self.scar_proposal(torch.cat([base, anchor_context], dim=1)) + pos_scar - neg_scar
        t2 = availability[:, 1, None, None, None, None]
        edema_prop = self.edema_proposal(torch.cat([base, anchor_context, t2.expand(-1, 1, *base.shape[-3:])], dim=1)) + pos_edema - neg_edema
        scar_roi = torch.sigmoid((torch.sigmoid(scar_prop) - 0.55) / 0.10)
        edema_roi = torch.sigmoid((torch.sigmoid(edema_prop) - 0.35) / 0.12) * t2
        scar_delta = 4.0 * torch.tanh(self.scar_refiner(base))
        edema_delta = 4.0 * torch.tanh(self.edema_refiner(base)) * t2
        gate_input = torch.cat([base[:, :4], anchor_context, scar_roi, edema_roi, pos_scar, pos_edema], dim=1)
        gate = self.gate(gate_input)
        final = anchor_logits.clone()
        final[:, 5:6] = final[:, 5:6] + scar_roi * gate * scar_delta
        final[:, 4:5] = final[:, 4:5] + edema_roi * gate * edema_delta
        no_t2_delta = (edema_roi * gate * edema_delta * (1.0 - t2)).abs().max()
        changed = (final - anchor_logits).abs().mean()
        receipt = MyoPSForwardReceipt(
            invalid_weight_max=float(torch.stack([r["invalid_weight_max"] for r in receipts]).max().detach().cpu()),
            no_t2_edema_delta_abs_max=float(no_t2_delta.detach().cpu()),
            changed_logit_l1=float(changed.detach().cpu()),
        )
        return {
            "anatomy_logits": anatomy,
            "scar_proposal": scar_prop,
            "edema_proposal": edema_prop,
            "scar_roi": scar_roi,
            "edema_roi": edema_roi,
            "final_logits": final,
            "receipt": receipt,
        }
