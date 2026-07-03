"""SRR proposal-refinement model for CARE MyoPS fold0 hardmode tasks."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from src.care_myocardium.models.pathology_heads import AnatomyPathologyHeads
from src.care_myocardium.models.srr_v2_unet import ModalityEncoder, ScaleRetrieval, TaskDecoder


def _groups(channels: int) -> int:
    return max(1, min(8, channels // 4))


class ProposalDictionary(nn.Module):
    """Pathology-specific positive and negative prototype proposal scorer."""

    def __init__(
        self,
        channels: int,
        *,
        pathology: str,
        n_positive: int = 6,
        n_negative: int = 6,
        no_proto: bool = False,
    ) -> None:
        super().__init__()
        self.pathology = pathology
        self.no_proto = bool(no_proto)
        self.embedding = nn.Conv3d(channels, channels, kernel_size=1, bias=False)
        self.conv_score = nn.Conv3d(channels, 1, kernel_size=1)
        if not self.no_proto:
            self.positive = nn.Parameter(torch.randn(n_positive, channels) * 0.02)
            self.negative = nn.Parameter(torch.randn(n_negative, channels) * 0.02)
            self.memory_types = (
                "outside_myocardium",
                "normal_myocardium",
                "blood_pool",
                "lge_bright_artifact",
                "t2_texture_noise",
                "remote_fp_island",
            )
            self.negative_memory = nn.ParameterDict(
                {name: nn.Parameter(torch.randn(2, channels) * 0.02) for name in self.memory_types}
            )

    @staticmethod
    def _max_similarity(embedding: torch.Tensor, prototypes: torch.Tensor) -> torch.Tensor:
        emb = F.normalize(embedding, dim=1)
        proto = F.normalize(prototypes, dim=1)
        sim = torch.einsum("bcdhw,kc->bkdhw", emb, proto)
        return sim.max(dim=1, keepdim=True).values

    def forward(self, features: torch.Tensor, evidence_logits: torch.Tensor, anatomy_prior: torch.Tensor) -> dict[str, torch.Tensor]:
        emb = self.embedding(features)
        conv = self.conv_score(features)
        if self.no_proto:
            proposal = conv + 0.35 * evidence_logits + 0.20 * torch.tanh(anatomy_prior)
            zero = proposal * 0.0
            return {
                "proposal_logits": proposal,
                "pos_similarity": zero,
                "neg_similarity": zero,
                "memory_negative_similarity": zero,
            }
        pos_sim = self._max_similarity(emb, self.positive)
        neg_proto = self._max_similarity(emb, self.negative)
        memory_bank = torch.cat([param for param in self.negative_memory.values()], dim=0)
        neg_memory = self._max_similarity(emb, memory_bank)
        neg_sim = torch.maximum(neg_proto, neg_memory)
        proposal = conv + 2.5 * (pos_sim - neg_sim) + 0.45 * evidence_logits + 0.20 * torch.tanh(anatomy_prior)
        return {
            "proposal_logits": proposal,
            "pos_similarity": pos_sim,
            "neg_similarity": neg_sim,
            "memory_negative_similarity": neg_memory,
        }


class SoftROIRefinementHead(nn.Module):
    """Refines pathology logits under a soft, differentiable ROI mask."""

    def __init__(self, channels: int, *, roi_kernel: int, residual_scale: float) -> None:
        super().__init__()
        self.roi_kernel = int(roi_kernel)
        self.residual_scale = float(residual_scale)
        self.refine = nn.Sequential(
            nn.Conv3d(channels + 3, channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(_groups(channels), channels),
            nn.LeakyReLU(0.01, inplace=True),
            nn.Conv3d(channels, channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(_groups(channels), channels),
            nn.LeakyReLU(0.01, inplace=True),
            nn.Conv3d(channels, 1, kernel_size=1),
        )

    def soft_roi(self, proposal_logits: torch.Tensor, anatomy_prior: torch.Tensor) -> torch.Tensor:
        proposal = torch.sigmoid(proposal_logits)
        anatomy = torch.sigmoid(anatomy_prior)
        k = max(1, min(self.roi_kernel, *(int(s) for s in proposal.shape[-3:])))
        if k % 2 == 0:
            k = max(1, k - 1)
        proposal_context = F.avg_pool3d(proposal, kernel_size=k, stride=1, padding=k // 2)
        anatomy_context = F.avg_pool3d(anatomy, kernel_size=k, stride=1, padding=k // 2)
        return torch.clamp(0.70 * proposal + 0.20 * proposal_context + 0.10 * anatomy_context, 0.0, 1.0)

    def forward(
        self,
        features: torch.Tensor,
        evidence_logits: torch.Tensor,
        proposal_logits: torch.Tensor,
        anatomy_prior: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        roi = self.soft_roi(proposal_logits, anatomy_prior)
        x = torch.cat([features, evidence_logits, proposal_logits, roi], dim=1)
        residual = self.refine(x)
        final = evidence_logits + self.residual_scale * roi * residual
        return final, residual, roi


class SRRProposeRefineMyoPS(nn.Module):
    """SRR evidence trunk with pathology dictionaries and soft ROI refinement.

    Inputs use Dataset501 channel order LGE, T2, C0. Availability uses the same
    order. The proposal dictionaries emit candidate maps; final pathology logits
    are produced only after the refinement heads consume image features,
    evidence logits, proposal logits, and soft ROI masks.
    """

    def __init__(
        self,
        *,
        base_channels: int = 10,
        variant: str = "srr_propref_shared_dual_dict",
        use_interactions: bool = True,
    ) -> None:
        super().__init__()
        if variant not in {
            "srr_propref_shared_dual_dict",
            "srr_propref_scar_precision",
            "srr_propref_no_proto_cascade",
        }:
            raise ValueError(f"unknown PropRef variant: {variant}")
        self.variant = variant
        self.base_channels = int(base_channels)
        self.encoders = nn.ModuleList([ModalityEncoder(base_channels) for _ in range(3)])
        self.retrieval = nn.ModuleList(
            [
                ScaleRetrieval(base_channels, use_interactions=use_interactions),
                ScaleRetrieval(base_channels * 2, use_interactions=use_interactions),
                ScaleRetrieval(base_channels * 4, use_interactions=use_interactions),
            ]
        )
        self.decoders = nn.ModuleDict({task: TaskDecoder(base_channels) for task in ("anatomy", "scar", "edema")})
        self.evidence_heads = AnatomyPathologyHeads(base_channels, prior_strength=0.35)
        no_proto = variant == "srr_propref_no_proto_cascade"
        scar_neg = 10 if variant == "srr_propref_scar_precision" else 6
        edema_pos = 8 if variant == "srr_propref_shared_dual_dict" else 4
        self.scar_dictionary = ProposalDictionary(
            base_channels,
            pathology="scar",
            n_positive=6,
            n_negative=scar_neg,
            no_proto=no_proto,
        )
        self.edema_dictionary = ProposalDictionary(
            base_channels,
            pathology="edema",
            n_positive=edema_pos,
            n_negative=6,
            no_proto=no_proto,
        )
        scar_kernel = 3 if variant == "srr_propref_scar_precision" else 5
        scar_scale = 0.85 if variant == "srr_propref_scar_precision" else 0.70
        edema_kernel = 9 if variant != "srr_propref_scar_precision" else 7
        self.scar_refine = SoftROIRefinementHead(base_channels, roi_kernel=scar_kernel, residual_scale=scar_scale)
        self.edema_refine = SoftROIRefinementHead(base_channels, roi_kernel=edema_kernel, residual_scale=0.65)

    def _evidence_features(self, x: torch.Tensor, availability: torch.Tensor) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        per_modality = [encoder(x[:, idx : idx + 1], availability[:, idx]) for idx, encoder in enumerate(self.encoders)]
        routed_by_task = {task: [] for task in ("anatomy", "scar", "edema")}
        gates: dict[str, torch.Tensor] = {}
        for scale, retrieval in enumerate(self.retrieval):
            routed, scale_gates = retrieval([features[scale] for features in per_modality], availability)
            for task in routed_by_task:
                routed_by_task[task].append(routed[task])
                gates[f"{task}_scale{scale}"] = scale_gates[task]
        return {
            "anatomy": self.decoders["anatomy"](routed_by_task["anatomy"]),
            "scar": self.decoders["scar"](routed_by_task["scar"]),
            "edema": self.decoders["edema"](routed_by_task["edema"]),
        }, gates

    def forward(self, x: torch.Tensor, availability: torch.Tensor) -> dict[str, torch.Tensor]:
        if x.shape[1] != 3:
            raise ValueError(f"SRRProposeRefineMyoPS expects 3 channels, got {x.shape[1]}")
        availability = availability.to(device=x.device, dtype=x.dtype).clamp(0, 1)
        features, gates = self._evidence_features(x, availability)
        evidence = self.evidence_heads(features["anatomy"], features["scar"], features["edema"])
        anatomy_prior = evidence["union_prior_logits"]
        scar_dict = self.scar_dictionary(features["scar"], evidence["scar_logits"], anatomy_prior)
        edema_dict = self.edema_dictionary(features["edema"], evidence["edema_logits"], anatomy_prior)
        scar_logits, scar_residual, scar_roi = self.scar_refine(
            features["scar"], evidence["scar_logits"], scar_dict["proposal_logits"], anatomy_prior
        )
        edema_logits, edema_residual, edema_roi = self.edema_refine(
            features["edema"], evidence["edema_logits"], edema_dict["proposal_logits"], anatomy_prior
        )
        outputs = {
            "logits": torch.cat([evidence["anatomy_logits"], edema_logits, scar_logits], dim=1),
            "anatomy_logits": evidence["anatomy_logits"],
            "scar_logits": scar_logits,
            "edema_logits": edema_logits,
            "union_prior_logits": anatomy_prior,
            "scar_evidence_logits": evidence["scar_logits"],
            "edema_evidence_logits": evidence["edema_logits"],
            "scar_proposal_logits": scar_dict["proposal_logits"],
            "edema_proposal_logits": edema_dict["proposal_logits"],
            "scar_pos_similarity": scar_dict["pos_similarity"],
            "scar_neg_similarity": scar_dict["neg_similarity"],
            "edema_pos_similarity": edema_dict["pos_similarity"],
            "edema_neg_similarity": edema_dict["neg_similarity"],
            "scar_memory_negative_similarity": scar_dict["memory_negative_similarity"],
            "edema_memory_negative_similarity": edema_dict["memory_negative_similarity"],
            "scar_refinement_residual": scar_residual,
            "edema_refinement_residual": edema_residual,
            "scar_soft_roi": scar_roi,
            "edema_soft_roi": edema_roi,
            "gates": gates,
            "availability": availability,
            "expert_usage": {name: gate.mean(dim=0) for name, gate in gates.items()},
        }
        return outputs
