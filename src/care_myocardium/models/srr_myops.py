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
        proposal_mode: str = "none",
    ) -> None:
        super().__init__()
        if in_channels != 3:
            raise ValueError("SRRMyoPSLite expects Dataset501 channels: LGE,T2,C0")
        self.in_channels = in_channels
        self.base_channels = int(base_channels)
        self.dictionary_mode = dictionary_mode
        self.proposal_mode = proposal_mode
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
        self.proposal_head = (
            PathologyProposalHead(base_channels, mode=proposal_mode)
            if proposal_mode != "none"
            else None
        )

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
        anatomy_features = self.refine(routed["anatomy"])
        scar_features = self.refine(routed["scar"])
        edema_features = self.refine(routed["edema"])
        outputs = self.heads(anatomy_features, scar_features, edema_features)
        if self.proposal_head is not None:
            self.proposal_head(outputs, scar_features, edema_features, availability)
        outputs["gates"] = gates
        outputs["availability"] = availability
        outputs["expert_usage"] = {name: gate.mean(dim=0) for name, gate in gates.items()}
        return outputs


def build_srr_myops_lite(base_channels: int = 16) -> SRRMyoPSLite:
    return SRRMyoPSLite(base_channels=base_channels)


class PathologyProposalHead(nn.Module):
    """Prototype proposal head for scar/edema candidate generation.

    The head keeps the original SRR evidence logits, but replaces the final
    pathology logits with a soft proposal score that combines positive-vs-
    negative prototype similarity, anatomy neighborhood confidence, and an
    optional uncertainty gate. It never hard-deletes anatomy-outside voxels.
    """

    def __init__(self, channels: int, mode: str, n_prototypes: int = 4) -> None:
        super().__init__()
        self.mode = mode
        self.temperature = 0.20
        self.evidence_weight = 0.55
        self.anatomy_weight = 0.25
        self.distance_weight = 0.05
        self.uncertainty_weight = 0.0
        if mode == "proposal_anatomy_distance":
            self.anatomy_weight = 0.38
            self.distance_weight = 0.35
        elif mode == "proposal_uncertainty_gate":
            self.anatomy_weight = 0.30
            self.distance_weight = 0.20
            self.uncertainty_weight = 0.45
        self.scar_embed = nn.Conv3d(channels, channels, kernel_size=1, bias=False)
        self.edema_embed = nn.Conv3d(channels, channels, kernel_size=1, bias=False)
        self.scar_pos = nn.Parameter(torch.randn(n_prototypes, channels) * 0.02)
        self.scar_neg = nn.Parameter(torch.randn(n_prototypes, channels) * 0.02)
        self.edema_pos = nn.Parameter(torch.randn(n_prototypes, channels) * 0.02)
        self.edema_neg = nn.Parameter(torch.randn(n_prototypes, channels) * 0.02)

    @staticmethod
    def _similarity(emb: torch.Tensor, prototypes: torch.Tensor) -> torch.Tensor:
        emb_n = F.normalize(emb, dim=1)
        proto_n = F.normalize(prototypes, dim=1)
        sims = torch.einsum("bcdhw,kc->bkdhw", emb_n, proto_n)
        return sims.max(dim=1, keepdim=True).values

    @staticmethod
    def _local_anatomy_confidence(union_prior_logits: torch.Tensor) -> torch.Tensor:
        union = torch.sigmoid(union_prior_logits)
        kernel = []
        padding = []
        for dim in union.shape[-3:]:
            k = min(7, int(dim))
            if k % 2 == 0:
                k = max(1, k - 1)
            kernel.append(k)
            padding.append(k // 2)
        return F.avg_pool3d(union, kernel_size=tuple(kernel), stride=1, padding=tuple(padding))

    @staticmethod
    def _uncertainty(logits: torch.Tensor) -> torch.Tensor:
        prob = torch.sigmoid(logits)
        return (1.0 - torch.abs(2.0 * prob - 1.0)).clamp(0.0, 1.0)

    def _proposal_logit(
        self,
        evidence_logits: torch.Tensor,
        pos_sim: torch.Tensor,
        neg_sim: torch.Tensor,
        union_prior_logits: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        local_anatomy = self._local_anatomy_confidence(union_prior_logits)
        remote_penalty = (1.0 - local_anatomy).clamp(0.0, 1.0)
        uncertainty = self._uncertainty(evidence_logits)
        logit = (
            (pos_sim - neg_sim) / self.temperature
            + self.evidence_weight * evidence_logits
            + self.anatomy_weight * torch.tanh(union_prior_logits)
            - self.distance_weight * remote_penalty
        )
        if self.uncertainty_weight > 0:
            logit = logit - self.uncertainty_weight * uncertainty
        return logit, uncertainty

    def forward(
        self,
        outputs: dict[str, torch.Tensor],
        scar_features: torch.Tensor,
        edema_features: torch.Tensor,
        availability: torch.Tensor,
    ) -> None:
        scar_emb = self.scar_embed(scar_features)
        edema_emb = self.edema_embed(edema_features)
        scar_pos = self._similarity(scar_emb, self.scar_pos)
        scar_neg = self._similarity(scar_emb, self.scar_neg)
        edema_pos = self._similarity(edema_emb, self.edema_pos)
        edema_neg = self._similarity(edema_emb, self.edema_neg)

        original_scar = outputs["scar_logits"]
        original_edema = outputs["edema_logits"]
        scar_proposal, scar_uncertainty = self._proposal_logit(
            original_scar, scar_pos, scar_neg, outputs["union_prior_logits"]
        )
        edema_proposal, edema_uncertainty = self._proposal_logit(
            original_edema, edema_pos, edema_neg, outputs["union_prior_logits"]
        )

        outputs["scar_evidence_logits"] = original_scar
        outputs["edema_evidence_logits"] = original_edema
        outputs["scar_proposal_logits"] = scar_proposal
        outputs["edema_proposal_logits"] = edema_proposal
        outputs["scar_pos_similarity"] = scar_pos
        outputs["scar_neg_similarity"] = scar_neg
        outputs["edema_pos_similarity"] = edema_pos
        outputs["edema_neg_similarity"] = edema_neg
        outputs["scar_uncertainty"] = scar_uncertainty
        outputs["edema_uncertainty"] = edema_uncertainty
        outputs["local_anatomy_confidence"] = self._local_anatomy_confidence(outputs["union_prior_logits"])
        outputs["proposal_mode"] = self.mode

        outputs["scar_logits"] = 0.40 * original_scar + 0.60 * scar_proposal
        outputs["edema_logits"] = 0.40 * original_edema + 0.60 * edema_proposal
        outputs["logits"] = torch.cat(
            [outputs["anatomy_logits"], outputs["edema_logits"], outputs["scar_logits"]],
            dim=1,
        )


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
