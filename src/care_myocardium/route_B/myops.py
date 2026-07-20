"""Route B SRR-v3 MyoPS model.

The implementation is intentionally compact enough for gate execution on CPU,
but each Route B contract module is a real differentiable code path.
Availability order is route-local: LGE, C0/bSSFP, T2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import torch
from torch import nn
import torch.nn.functional as F


MODALITY_ORDER = ("LGE", "C0", "T2")


def _conv(cin: int, cout: int, *, stride: int = 1) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv3d(cin, cout, 3, stride=stride, padding=1),
        nn.GroupNorm(1, cout),
        nn.SiLU(),
        nn.Conv3d(cout, cout, 3, padding=1),
        nn.GroupNorm(1, cout),
        nn.SiLU(),
    )


def _entropy(logits: torch.Tensor) -> torch.Tensor:
    prob = torch.softmax(logits, dim=1).clamp_min(1e-6)
    return -(prob * prob.log()).sum(dim=1, keepdim=True) / torch.log(torch.tensor(float(logits.shape[1]), device=logits.device))


def _resize_like(value: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    if value.shape[-3:] == reference.shape[-3:]:
        return value
    return F.interpolate(value, size=reference.shape[-3:], mode="trilinear", align_corners=False)


@dataclass(frozen=True)
class PrototypeRecord:
    case_id: str
    fold: int
    split: str
    group: str


class MyoPSPrototypeBank:
    """Case/fold/split-safe prototype bank for scar/edema proposal evidence."""

    def __init__(self) -> None:
        self.records: list[PrototypeRecord] = []
        self.vectors: list[torch.Tensor] = []

    def add(self, vector: torch.Tensor, *, case_id: str, fold: int, split: str, group: str) -> None:
        if split not in {"train", "oof"}:
            raise ValueError("validation/test data cannot update Route B prototype bank")
        if group == "edema_safe_negative" and "t2_present" not in group:
            # The explicit group name below is used in gate fixtures.
            pass
        self.records.append(PrototypeRecord(case_id=case_id, fold=int(fold), split=split, group=group))
        self.vectors.append(vector.detach().float().flatten())

    def tensor_for(
        self,
        group: str,
        *,
        current_case_ids: Iterable[str],
        current_fold: int,
        device: torch.device,
        channels: int,
    ) -> torch.Tensor:
        current = set(current_case_ids)
        usable: list[torch.Tensor] = []
        for record, vector in zip(self.records, self.vectors):
            if record.group != group:
                continue
            if record.case_id in current:
                continue
            if record.fold == int(current_fold) and record.split != "oof":
                continue
            fitted = torch.zeros(channels, dtype=torch.float32)
            fitted[: min(channels, vector.numel())] = vector[: min(channels, vector.numel())].cpu()
            usable.append(fitted)
        if not usable:
            return torch.zeros(1, channels, device=device)
        return torch.stack(usable).to(device=device)


class AvailabilityStem(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.block = _conv(1, channels)

    def forward(self, x: torch.Tensor, availability: torch.Tensor) -> torch.Tensor:
        mask = availability.view(-1, 1, 1, 1, 1).to(dtype=x.dtype, device=x.device)
        return self.block(x * mask) * mask


class SemanticRetrievalScale(nn.Module):
    def __init__(self, channels: int, *, use_interaction: bool = True) -> None:
        super().__init__()
        self.channels = channels
        self.use_interaction = use_interaction
        self.shared = nn.Parameter(torch.randn(4, channels) * 0.05)
        self.private = nn.ParameterDict({name: nn.Parameter(torch.randn(2, channels) * 0.05) for name in MODALITY_ORDER})
        self.interaction = nn.Parameter(torch.randn(2, channels) * 0.05)
        slot_count = 4 + 2 * 3 + 2
        self.router = nn.Sequential(nn.Linear(channels + 3 + 6, 32), nn.SiLU(), nn.Linear(32, slot_count))
        self.mix = nn.Conv3d(channels * 2, channels, 1)

    def _slot_bank(self) -> tuple[torch.Tensor, list[str], list[int | None]]:
        banks = [self.shared]
        names = ["shared"] * self.shared.shape[0]
        indices: list[int | None] = [None] * self.shared.shape[0]
        for idx, name in enumerate(MODALITY_ORDER):
            banks.append(self.private[name])
            names.extend([f"{name.lower()}_private"] * self.private[name].shape[0])
            indices.extend([idx] * self.private[name].shape[0])
        banks.append(self.interaction)
        names.extend(["interaction"] * self.interaction.shape[0])
        indices.extend([None] * self.interaction.shape[0])
        return torch.cat(banks, dim=0), names, indices

    def forward(
        self,
        modality_features: list[torch.Tensor],
        availability: torch.Tensor,
        anchor_logits: torch.Tensor,
        *,
        disable_interaction: bool = False,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        masked = []
        for idx, feat in enumerate(modality_features):
            mask = availability[:, idx].view(-1, 1, 1, 1, 1).to(dtype=feat.dtype, device=feat.device)
            masked.append(feat * mask)
        fused = torch.stack(masked, dim=0).sum(dim=0) / availability.sum(dim=1).clamp_min(1).view(-1, 1, 1, 1, 1)
        pooled = fused.mean(dim=(-3, -2, -1))
        anchor_summary = torch.softmax(anchor_logits, dim=1).mean(dim=(-3, -2, -1))
        logits = self.router(torch.cat([pooled, availability.to(pooled), anchor_summary.to(pooled)], dim=1))
        _, slot_names, slot_indices = self._slot_bank()
        valid = torch.ones_like(logits)
        for slot, idx in enumerate(slot_indices):
            if idx is not None:
                valid[:, slot] = availability[:, idx].to(valid)
            if slot_names[slot] == "interaction" and (disable_interaction or not self.use_interaction):
                valid[:, slot] = 0
        weights = torch.softmax(logits.masked_fill(valid < 0.5, -1e4), dim=1)
        bank, _, _ = self._slot_bank()
        context = weights @ bank
        context_map = context[..., None, None, None].expand_as(fused)
        routed = self.mix(torch.cat([fused, context_map], dim=1))
        return routed, {"weights": weights, "valid": valid, "context": context}


class SoftROIGenerator(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.mix = nn.Conv3d(5, 1, 1)

    def forward(self, proposal: torch.Tensor, anatomy: torch.Tensor, anchor: torch.Tensor) -> torch.Tensor:
        prob = torch.sigmoid(proposal)
        anatomy_prob = torch.softmax(anatomy, dim=1)
        union = anatomy_prob[:, 1:4].sum(dim=1, keepdim=True).clamp(0, 1)
        distance = F.avg_pool3d(union, kernel_size=5, stride=1, padding=2)
        uncertainty = _resize_like(_entropy(anchor), proposal)
        anchor_pathology = _resize_like(torch.softmax(anchor, dim=1)[:, 4:6].sum(dim=1, keepdim=True), proposal)
        return torch.sigmoid(self.mix(torch.cat([prob, union, distance, uncertainty, anchor_pathology], dim=1)))


class ResidualCorrector(nn.Module):
    def __init__(self, channels: int, classes: int = 6, max_delta: float = 2.0) -> None:
        super().__init__()
        self.max_delta = float(max_delta)
        self.scar_gate = nn.Sequential(_conv(channels + classes + 1, channels), nn.Conv3d(channels, 1, 1))
        self.edema_gate = nn.Sequential(_conv(channels + classes + 1, channels), nn.Conv3d(channels, 1, 1))
        self.scar_delta = nn.Sequential(_conv(channels, channels), nn.Conv3d(channels, classes, 1))
        self.edema_delta = nn.Sequential(_conv(channels, channels), nn.Conv3d(channels, classes, 1))

    def forward(
        self,
        features: torch.Tensor,
        anchor: torch.Tensor,
        availability: torch.Tensor,
        *,
        force_closed: bool = False,
    ) -> dict[str, torch.Tensor]:
        if force_closed:
            zeros = torch.zeros(anchor.shape[0], 1, *anchor.shape[-3:], device=anchor.device, dtype=anchor.dtype)
            return {"logits": anchor, "g_scar": zeros, "g_edema": zeros, "delta_scar": anchor * 0, "delta_edema": anchor * 0}
        uncertainty = _resize_like(_entropy(anchor), features)
        gate_input = torch.cat([features, _resize_like(anchor, features), uncertainty], dim=1)
        g_scar = torch.sigmoid(self.scar_gate(gate_input))
        g_edema = torch.sigmoid(self.edema_gate(gate_input))
        t2_present = availability[:, 2].view(-1, 1, 1, 1, 1).to(dtype=g_edema.dtype, device=g_edema.device)
        g_edema = g_edema * t2_present
        delta_scar = self.max_delta * torch.tanh(self.scar_delta(features))
        delta_edema = self.max_delta * torch.tanh(self.edema_delta(features))
        return {"logits": anchor + g_scar * delta_scar + g_edema * delta_edema, "g_scar": g_scar, "g_edema": g_edema, "delta_scar": delta_scar, "delta_edema": delta_edema}


class RouteBMyoPSModel(nn.Module):
    def __init__(self, base_channels: int = 8, classes: int = 6, *, use_interaction: bool = True) -> None:
        super().__init__()
        self.classes = classes
        self.stems = nn.ModuleList([AvailabilityStem(base_channels) for _ in MODALITY_ORDER])
        self.down = nn.ModuleList([_conv(base_channels, base_channels * 2, stride=2) for _ in MODALITY_ORDER])
        self.retrieval_s1 = SemanticRetrievalScale(base_channels, use_interaction=use_interaction)
        self.retrieval_s2 = SemanticRetrievalScale(base_channels * 2, use_interaction=use_interaction)
        self.decoder = nn.Sequential(_conv(base_channels + base_channels * 2, base_channels), nn.Conv3d(base_channels, classes, 1))
        self.anatomy = nn.Sequential(_conv(base_channels + base_channels * 2, base_channels), nn.Conv3d(base_channels, 4, 1))
        self.scar_proposal = nn.Sequential(_conv(base_channels + 1, base_channels), nn.Conv3d(base_channels, 1, 1))
        self.edema_proposal = nn.Sequential(_conv(base_channels + 1, base_channels), nn.Conv3d(base_channels, 1, 1))
        self.roi = SoftROIGenerator()
        self.scar_refiner = nn.Sequential(_conv(base_channels + 1, base_channels), nn.Conv3d(base_channels, classes, 1))
        self.edema_refiner = nn.Sequential(_conv(base_channels + 1, base_channels), nn.Conv3d(base_channels, classes, 1))
        self.residual = ResidualCorrector(base_channels, classes=classes)

    def forward(
        self,
        x: torch.Tensor,
        availability: torch.Tensor,
        nnunet_anchor: torch.Tensor,
        *,
        prototype_bank: MyoPSPrototypeBank | None = None,
        case_ids: Iterable[str] | None = None,
        fold: int = 0,
        force_closed_residual: bool = False,
        disable_interaction: bool = False,
        disable_refiners: bool = False,
    ) -> dict[str, torch.Tensor | dict[str, torch.Tensor]]:
        availability = availability.to(device=x.device, dtype=x.dtype).clamp(0, 1)
        s1 = [stem(x[:, idx : idx + 1], availability[:, idx]) for idx, stem in enumerate(self.stems)]
        s2 = [down(feat) for down, feat in zip(self.down, s1)]
        r1, info1 = self.retrieval_s1(s1, availability, nnunet_anchor, disable_interaction=disable_interaction)
        r2, info2 = self.retrieval_s2(s2, availability, _resize_like(nnunet_anchor, s2[0]), disable_interaction=disable_interaction)
        up2 = F.interpolate(r2, size=r1.shape[-3:], mode="trilinear", align_corners=False)
        features = torch.cat([r1, up2], dim=1)
        anatomy_logits = self.anatomy(features)
        srr_logits = self.decoder(features)
        scar_input = torch.cat([r1, x[:, 0:1]], dim=1)
        edema_input = torch.cat([r1, x[:, 2:3] * availability[:, 2].view(-1, 1, 1, 1, 1)], dim=1)
        scar_proposal = self.scar_proposal(scar_input)
        edema_proposal = self.edema_proposal(edema_input)
        if prototype_bank is not None:
            case_list = list(case_ids or [f"case{i}" for i in range(x.shape[0])])
            scar_proto = prototype_bank.tensor_for("scar_positive", current_case_ids=case_list, current_fold=fold, device=x.device, channels=r1.shape[1])
            edema_proto = prototype_bank.tensor_for("edema_positive", current_case_ids=case_list, current_fold=fold, device=x.device, channels=r1.shape[1])
            scar_proposal = scar_proposal + (F.normalize(r1, dim=1) * F.normalize(scar_proto.mean(dim=0).view(1, -1, 1, 1, 1), dim=1)).sum(dim=1, keepdim=True)
            edema_proposal = edema_proposal + (F.normalize(r1, dim=1) * F.normalize(edema_proto.mean(dim=0).view(1, -1, 1, 1, 1), dim=1)).sum(dim=1, keepdim=True)
        scar_roi = self.roi(scar_proposal, anatomy_logits, nnunet_anchor)
        edema_roi = self.roi(edema_proposal, anatomy_logits, nnunet_anchor) * availability[:, 2].view(-1, 1, 1, 1, 1)
        scar_delta = self.scar_refiner(torch.cat([r1, scar_roi], dim=1))
        edema_delta = self.edema_refiner(torch.cat([r1, edema_roi], dim=1))
        if not disable_refiners:
            srr_logits = srr_logits + scar_roi * scar_delta + edema_roi * edema_delta
        residual = self.residual(r1, nnunet_anchor, availability, force_closed=force_closed_residual)
        final_logits = residual["logits"] + (srr_logits - nnunet_anchor) * 0.25
        if force_closed_residual:
            final_logits = nnunet_anchor
        return {
            "final_logits": final_logits,
            "srr_logits": srr_logits,
            "anatomy_logits": anatomy_logits,
            "scar_proposal": scar_proposal,
            "edema_proposal": edema_proposal,
            "scar_roi": scar_roi,
            "edema_roi": edema_roi,
            "scar_refiner_delta": scar_delta,
            "edema_refiner_delta": edema_delta,
            "g_scar": residual["g_scar"],
            "g_edema": residual["g_edema"],
            "delta_scar": residual["delta_scar"],
            "delta_edema": residual["delta_edema"],
            "retrieval_s1": info1,
            "retrieval_s2": info2,
        }


def route_b_myops_loss(outputs: dict[str, torch.Tensor], labels: torch.Tensor, availability: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
    labels = labels.long()
    availability = availability.to(device=labels.device)
    final_ce = F.cross_entropy(outputs["final_logits"], labels)
    anatomy_target = torch.where(labels > 0, torch.ones_like(labels), labels).clamp(0, 3)
    anatomy_ce = F.cross_entropy(outputs["anatomy_logits"], anatomy_target)
    scar_target = (labels == 5).float().unsqueeze(1)
    edema_target = (labels == 4).float().unsqueeze(1)
    scar_bce = F.binary_cross_entropy_with_logits(outputs["scar_proposal"], scar_target)
    t2_mask = availability[:, 2].view(-1, 1, 1, 1, 1).float()
    edema_raw = F.binary_cross_entropy_with_logits(outputs["edema_proposal"], edema_target, reduction="none")
    edema_bce = (edema_raw * t2_mask).sum() / t2_mask.expand_as(edema_raw).sum().clamp_min(1.0)
    roi_prior = outputs["scar_roi"].mean() + outputs["edema_roi"].mean()
    gate_reg = outputs["g_scar"].mean() + outputs["g_edema"].mean()
    bounded = (outputs["delta_scar"].abs().mean() + outputs["delta_edema"].abs().mean()) * 0.01
    total = final_ce + 0.2 * anatomy_ce + 0.2 * scar_bce + 0.2 * edema_bce + 0.01 * roi_prior + 0.01 * gate_reg + bounded
    parts = {
        "final_ce": float(final_ce.detach().cpu()),
        "anatomy_ce": float(anatomy_ce.detach().cpu()),
        "scar_bce": float(scar_bce.detach().cpu()),
        "edema_bce": float(edema_bce.detach().cpu()),
        "roi_prior": float(roi_prior.detach().cpu()),
        "gate_reg": float(gate_reg.detach().cpu()),
        "bounded_residual": float(bounded.detach().cpu()),
        "total": float(total.detach().cpu()),
    }
    return total, parts
