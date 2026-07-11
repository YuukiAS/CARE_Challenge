"""SRR proposal-refinement model for CARE MyoPS fold0 hardmode tasks."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from src.care_myocardium.anchors.myops_decode import canonical_t2_present
from src.care_myocardium.models.pathology_heads import AnatomyPathologyHeads
from src.care_myocardium.models.proposal_prototypes import deterministic_axis_prototypes
from src.care_myocardium.models.srr_blocks import gate_diagnostics
from src.care_myocardium.models.srr_spatial_dictionary import M10TwoPassSpatialDictionary
from src.care_myocardium.models.srr_v2_unet import FlexibleTaskDecoder, ScaleRetrieval, build_modality_encoder, encoder_profile_scale_channels


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
        self.prototype_source = "no_proto_variant" if self.no_proto else "deterministic_axis_bootstrap_pending_train_or_oof_fit"
        if not self.no_proto:
            self.memory_types = (
                "outside_myocardium",
                "normal_myocardium",
                "blood_pool",
                "lge_bright_artifact",
                "t2_texture_noise",
                "remote_fp_island",
            )
            self.register_buffer("positive", deterministic_axis_prototypes(n_positive, channels, offset=0))
            self.register_buffer("negative", deterministic_axis_prototypes(n_negative, channels, offset=1))
            for idx, name in enumerate(self.memory_types):
                self.register_buffer(f"negative_memory_{name}", deterministic_axis_prototypes(2, channels, offset=idx + 2))

    def load_prototype_bank(self, *, positive: torch.Tensor, negative: torch.Tensor, source: str) -> None:
        if self.no_proto:
            return
        self.positive.copy_(self._resize_bank(positive, self.positive))
        self.negative.copy_(self._resize_bank(negative, self.negative))
        self.prototype_source = str(source)

    @staticmethod
    def _resize_bank(bank: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        value = bank.detach().to(device=target.device, dtype=target.dtype)
        if value.ndim != 2 or value.shape[1] != target.shape[1]:
            raise ValueError(f"prototype bank must have shape (K,{target.shape[1]}), got {tuple(value.shape)}")
        if value.shape[0] >= target.shape[0]:
            value = value[: target.shape[0]]
        else:
            value = torch.cat([value, value[-1:].repeat(target.shape[0] - value.shape[0], 1)], dim=0)
        return F.normalize(value, dim=1)

    @staticmethod
    def _max_similarity(embedding: torch.Tensor, prototypes: torch.Tensor) -> torch.Tensor:
        emb = F.normalize(embedding, dim=1)
        proto = F.normalize(prototypes, dim=1)
        sim = torch.einsum("bcdhw,kc->bkdhw", emb, proto)
        return sim.max(dim=1, keepdim=True).values

    @staticmethod
    def _evidence_map(
        evidence: torch.Tensor | dict[str, torch.Tensor] | None,
        keys: tuple[str, ...],
        channel: int,
        reference: torch.Tensor,
    ) -> torch.Tensor:
        if evidence is None:
            return torch.zeros_like(reference)
        value: torch.Tensor | None = None
        if isinstance(evidence, dict):
            for key in keys:
                candidate = evidence.get(key)
                if isinstance(candidate, torch.Tensor):
                    value = candidate
                    break
            if value is None:
                for key in ("probabilities", "probs", "logits", "anchor", "features"):
                    candidate = evidence.get(key)
                    if isinstance(candidate, torch.Tensor):
                        value = candidate
                        break
        elif isinstance(evidence, torch.Tensor):
            value = evidence
        if value is None or value.ndim != 5:
            return torch.zeros_like(reference)
        value = value.to(device=reference.device, dtype=reference.dtype)
        if value.shape[1] == 1:
            out = value
        elif value.shape[1] > channel:
            out = value[:, channel : channel + 1]
        else:
            return torch.zeros_like(reference)
        if out.shape[-3:] != reference.shape[-3:]:
            out = F.interpolate(out, size=reference.shape[-3:], mode="trilinear", align_corners=False)
        if bool((out.detach().min() < 0).item()) or bool((out.detach().max() > 1).item()):
            out = torch.sigmoid(out)
        return out.clamp(0, 1)

    def _negative_memory_bank(self) -> torch.Tensor:
        return torch.cat([getattr(self, f"negative_memory_{name}") for name in self.memory_types], dim=0)

    def forward(
        self,
        features: torch.Tensor,
        evidence_logits: torch.Tensor,
        anatomy_prior: torch.Tensor,
        *,
        anchor_features: torch.Tensor | dict[str, torch.Tensor] | None = None,
        component_features: torch.Tensor | dict[str, torch.Tensor] | None = None,
        availability: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        emb = self.embedding(features)
        conv = self.conv_score(features)
        channel = 5 if self.pathology == "scar" else 4
        anchor_map = self._evidence_map(anchor_features, (self.pathology, f"{self.pathology}_prob", f"{self.pathology}_probability"), channel, conv)
        component_map = self._evidence_map(component_features, (f"{self.pathology}_component", f"{self.pathology}_components", self.pathology), 0, conv)
        if self.no_proto:
            proposal = conv + 0.35 * evidence_logits + 0.25 * torch.logit(anchor_map.clamp(1e-4, 1.0 - 1e-4)) + 0.20 * torch.tanh(anatomy_prior)
            zero = proposal * 0.0
            return {
                "proposal_logits": proposal,
                "pos_similarity": zero,
                "neg_similarity": zero,
                "memory_negative_similarity": zero,
                "anchor_evidence": anchor_map,
                "component_evidence": component_map,
                "proposal_formula_terms": {
                    "w_pos_s_pos": zero,
                    "w_neg_s_neg": zero,
                    "w_anatomy_A": 0.20 * torch.tanh(anatomy_prior),
                    "w_context_C": 0.25 * torch.logit(anchor_map.clamp(1e-4, 1.0 - 1e-4)),
                    "w_uncertainty_U": zero,
                    "learned_residual_r": conv + 0.35 * evidence_logits,
                },
            }
        pos_sim = self._max_similarity(emb, self.positive)
        neg_proto = self._max_similarity(emb, self.negative)
        memory_bank = self._negative_memory_bank()
        neg_memory = self._max_similarity(emb, memory_bank)
        neg_sim = torch.maximum(neg_proto, neg_memory)
        proposal = (
            conv
            + 2.5 * (pos_sim - neg_sim)
            + 0.45 * evidence_logits
            + 0.35 * torch.logit(anchor_map.clamp(1e-4, 1.0 - 1e-4))
            + 0.30 * torch.logit(component_map.clamp(1e-4, 1.0 - 1e-4))
            + 0.20 * torch.tanh(anatomy_prior)
        )
        if self.pathology == "edema" and availability is not None:
            t2_present = availability[:, 1].view(-1, 1, 1, 1, 1).to(dtype=torch.bool, device=proposal.device)
            proposal = torch.where(t2_present, proposal, torch.full_like(proposal, -20.0))
        return {
            "proposal_logits": proposal,
            "pos_similarity": pos_sim,
            "neg_similarity": neg_sim,
            "memory_negative_similarity": neg_memory,
            "anchor_evidence": anchor_map,
            "component_evidence": component_map,
            "proposal_formula_terms": {
                "w_pos_s_pos": 2.5 * pos_sim,
                "w_neg_s_neg": -2.5 * neg_sim,
                "w_anatomy_A": 0.20 * torch.tanh(anatomy_prior),
                "w_context_C": 0.35 * torch.logit(anchor_map.clamp(1e-4, 1.0 - 1e-4)) + 0.30 * torch.logit(component_map.clamp(1e-4, 1.0 - 1e-4)),
                "w_uncertainty_U": torch.zeros_like(proposal),
                "learned_residual_r": conv + 0.45 * evidence_logits,
            },
        }


def _odd_kernel(requested: int, spatial: tuple[int, int, int]) -> int:
    k = max(1, min(int(requested), *(int(s) for s in spatial)))
    if k % 2 == 0:
        k = max(1, k - 1)
    return k


def _bounded_box(
    mask: torch.Tensor,
    *,
    margin: int,
    min_shape: tuple[int, int, int],
    spatial_shape: tuple[int, int, int],
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    coords = torch.nonzero(mask.detach().to(dtype=torch.bool), as_tuple=False)
    if coords.numel() == 0:
        return (0, 0, 0), spatial_shape
    starts_t = coords.min(dim=0).values.to(dtype=torch.long) - int(margin)
    ends_t = coords.max(dim=0).values.to(dtype=torch.long) + int(margin) + 1
    starts = [max(0, int(v)) for v in starts_t.tolist()]
    ends = [min(int(spatial_shape[idx]), int(v)) for idx, v in enumerate(ends_t.tolist())]
    for idx, min_size in enumerate(min_shape):
        size = ends[idx] - starts[idx]
        if size >= min_size or min_size >= spatial_shape[idx]:
            starts[idx] = max(0, min(starts[idx], spatial_shape[idx] - min_size))
            ends[idx] = min(spatial_shape[idx], max(ends[idx], starts[idx] + min_size))
            continue
        missing = int(min_size) - size
        before = missing // 2
        after = missing - before
        starts[idx] = max(0, starts[idx] - before)
        ends[idx] = min(spatial_shape[idx], ends[idx] + after)
        if ends[idx] - starts[idx] < min_size:
            starts[idx] = max(0, ends[idx] - int(min_size))
            ends[idx] = min(spatial_shape[idx], starts[idx] + int(min_size))
    return tuple(starts), tuple(ends)  # type: ignore[return-value]


def _safe_logit(prob: torch.Tensor) -> torch.Tensor:
    return torch.logit(prob.clamp(1e-4, 1.0 - 1e-4))


M6_VARIANT_CONFIGS: dict[str, dict[str, object]] = {
    "m6_full_srr_context_arbitration": {
        "default_encoder_profile": "balanced_4scale",
        "dictionary_config": "dict_full_interaction",
        "scar_negative": 8,
        "edema_positive": 6,
        "scar_kernel": 5,
        "edema_kernel": 9,
        "scar_scale": 0.75,
        "edema_scale": 0.65,
        "arbitration_mode": "full_context",
    },
    "m6_conservative_component_arbitration": {
        "default_encoder_profile": "safe_4scale",
        "dictionary_config": "dict_conservative_private_shared",
        "scar_negative": 10,
        "edema_positive": 6,
        "scar_kernel": 3,
        "edema_kernel": 7,
        "scar_scale": 0.55,
        "edema_scale": 0.45,
        "arbitration_mode": "conservative_component",
    },
    "m6_scar_precision_edema_safe": {
        "default_encoder_profile": "balanced_4scale",
        "dictionary_config": "dict_scar_precision_edema_safe",
        "scar_negative": 12,
        "edema_positive": 8,
        "scar_kernel": 3,
        "edema_kernel": 9,
        "scar_scale": 0.70,
        "edema_scale": 0.50,
        "arbitration_mode": "scar_precision_edema_safe",
    },
    "m9_srr_main_true_br2_pattern_sip": {
        "default_encoder_profile": "balanced_4scale",
        "dictionary_config": "dict_full_interaction",
        "scar_negative": 12,
        "edema_positive": 10,
        "scar_kernel": 3,
        "edema_kernel": 11,
        "scar_scale": 0.70,
        "edema_scale": 0.60,
        "scar_crop_margin": 1,
        "edema_crop_margin": 4,
        "arbitration_mode": "m9_srr_main_control_only",
        "m9_final_output_mode": "SRR_MAIN_NOT_ANCHOR_RESIDUAL",
    },
    "m9_srr_main_lesion_proposal_memory": {
        "default_encoder_profile": "balanced_4scale",
        "dictionary_config": "dict_scar_precision_edema_safe",
        "scar_negative": 14,
        "edema_positive": 10,
        "scar_kernel": 3,
        "edema_kernel": 9,
        "scar_scale": 0.75,
        "edema_scale": 0.58,
        "scar_crop_margin": 1,
        "edema_crop_margin": 4,
        "arbitration_mode": "m9_srr_main_control_only",
        "m9_final_output_mode": "SRR_MAIN_NOT_ANCHOR_RESIDUAL",
    },
    "m9_srr_main_t2_edema_recall_focus": {
        "default_encoder_profile": "balanced_4scale",
        "dictionary_config": "dict_full_interaction",
        "scar_negative": 10,
        "edema_positive": 12,
        "scar_kernel": 5,
        "edema_kernel": 11,
        "scar_scale": 0.65,
        "edema_scale": 0.70,
        "scar_crop_margin": 2,
        "edema_crop_margin": 5,
        "arbitration_mode": "m9_srr_main_control_only",
        "m9_final_output_mode": "SRR_MAIN_NOT_ANCHOR_RESIDUAL",
    },
    "m10_d0_static_matched_propref": {
        "default_encoder_profile": "full_4scale",
        "dictionary_config": "srr_v3_m10_16slot",
        "scar_negative": 12,
        "edema_positive": 8,
        "scar_kernel": 3,
        "edema_kernel": 9,
        "scar_scale": 2.0,
        "edema_scale": 1.5,
        "arbitration_mode": "m10_srr_proposal_refinement",
        "m10_design": "D0_STATIC_MATCHED_PROPREF",
        "m10_final_output_mode": "SRR_PROPOSAL_REFINEMENT",
    },
    "m10_d1_spatial_br2_propref": {
        "default_encoder_profile": "full_4scale",
        "dictionary_config": "srr_v3_m10_16slot",
        "scar_negative": 12,
        "edema_positive": 8,
        "scar_kernel": 3,
        "edema_kernel": 9,
        "scar_scale": 2.0,
        "edema_scale": 1.5,
        "arbitration_mode": "m10_srr_proposal_refinement",
        "m10_design": "D1_SPATIAL_BR2_PROPREF",
        "m10_final_output_mode": "SRR_PROPOSAL_REFINEMENT",
        "m10_spatial_dictionary": True,
    },
    "m10_d2_hierarchical_psip_propref": {
        "default_encoder_profile": "full_4scale",
        "dictionary_config": "srr_v3_m10_16slot",
        "scar_negative": 12,
        "edema_positive": 8,
        "scar_kernel": 3,
        "edema_kernel": 9,
        "scar_scale": 2.0,
        "edema_scale": 1.5,
        "arbitration_mode": "m10_srr_proposal_refinement",
        "m10_design": "D2_HIERARCHICAL_BR2_PSIP_PROPREF",
        "m10_final_output_mode": "SRR_PROPOSAL_REFINEMENT",
        "m10_spatial_dictionary": True,
        "m10_pattern_sip": True,
    },
    "m10_d3_hierarchical_memory_propref": {
        "default_encoder_profile": "full_4scale",
        "dictionary_config": "srr_v3_m10_16slot",
        "scar_negative": 12,
        "edema_positive": 8,
        "scar_kernel": 3,
        "edema_kernel": 9,
        "scar_scale": 2.0,
        "edema_scale": 1.5,
        "arbitration_mode": "m10_srr_proposal_refinement",
        "m10_design": "D3_HIERARCHICAL_BR2_MEMORY_PROPREF",
        "m10_final_output_mode": "SRR_PROPOSAL_REFINEMENT",
        "m10_spatial_dictionary": True,
        "m10_pattern_sip": True,
        "m10_memory": True,
    },
}


class AnatomyDistanceROIPrior(nn.Module):
    """Build P_union/P_LV/P_RV distance and uncertainty maps for soft ROI gates."""

    def __init__(self, *, distance_steps: int = 6, empty_threshold: float = 0.05) -> None:
        super().__init__()
        self.distance_steps = int(distance_steps)
        self.empty_threshold = float(empty_threshold)

    @staticmethod
    def _anchor_tensor(anchor_features: torch.Tensor | dict[str, torch.Tensor] | None) -> torch.Tensor | None:
        if anchor_features is None:
            return None
        if isinstance(anchor_features, dict):
            for key in ("probabilities", "probs", "logits", "anchor", "features"):
                value = anchor_features.get(key)
                if isinstance(value, torch.Tensor):
                    return value
            return None
        return anchor_features

    @staticmethod
    def _class_probs(value: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
        value = value.to(device=reference.device, dtype=reference.dtype)
        if value.shape[-3:] != reference.shape[-3:]:
            value = F.interpolate(value, size=reference.shape[-3:], mode="trilinear", align_corners=False)
        if bool((value.detach().min() >= 0).item()) and bool((value.detach().max() <= 1).item()):
            denom = value.sum(dim=1, keepdim=True).clamp_min(1e-6)
            return (value / denom).clamp(0.0, 1.0)
        return torch.softmax(value, dim=1)

    def _soft_distance(self, support: torch.Tensor) -> torch.Tensor:
        support = support.clamp(0.0, 1.0)
        dilated = support
        accum = torch.zeros_like(support)
        for _ in range(max(1, self.distance_steps)):
            accum = accum + (1.0 - dilated)
            dilated = F.max_pool3d(dilated, kernel_size=3, stride=1, padding=1)
        return (accum / float(max(1, self.distance_steps))).clamp(0.0, 1.0)

    def forward(
        self,
        anatomy_logits: torch.Tensor,
        anchor_features: torch.Tensor | dict[str, torch.Tensor] | None,
        availability: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        probs = torch.softmax(anatomy_logits, dim=1)
        p_union = probs[:, 1:4].sum(dim=1, keepdim=True).clamp(0.0, 1.0)
        p_lv = probs[:, 2:3].clamp(0.0, 1.0)
        p_rv = probs[:, 3:4].clamp(0.0, 1.0)
        union_distance = self._soft_distance(p_union)
        lv_distance = self._soft_distance(p_lv)
        rv_distance = self._soft_distance(p_rv)
        union_proximity = (1.0 - union_distance).clamp(0.0, 1.0)
        lv_proximity = (1.0 - lv_distance).clamp(0.0, 1.0)
        rv_proximity = (1.0 - rv_distance).clamp(0.0, 1.0)
        anatomy_uncertainty = (1.0 - probs.max(dim=1, keepdim=True).values).clamp(0.0, 1.0)

        anchor = self._anchor_tensor(anchor_features)
        if anchor is not None and anchor.ndim == 5 and anchor.shape[1] >= 4:
            anchor_probs = self._class_probs(anchor, anatomy_logits)
            anchor_uncertainty = (1.0 - anchor_probs.max(dim=1, keepdim=True).values).clamp(0.0, 1.0)
        else:
            anchor_uncertainty = torch.zeros_like(anatomy_uncertainty)
        uncertainty = torch.maximum(anatomy_uncertainty, anchor_uncertainty)
        confidence = (1.0 - uncertainty).clamp(0.0, 1.0)

        empty_union = (p_union.amax(dim=(2, 3, 4), keepdim=True) < self.empty_threshold).to(dtype=anatomy_logits.dtype)
        scar_base = 0.55 * p_union + 0.25 * union_proximity + 0.12 * lv_proximity + 0.03 * rv_proximity
        edema_base = 0.48 * p_union + 0.34 * union_proximity + 0.06 * lv_proximity + 0.06 * rv_proximity
        scar_gate = (scar_base * (0.70 + 0.30 * confidence)).clamp(0.0, 1.0)
        edema_gate = (edema_base * (0.62 + 0.38 * confidence)).clamp(0.0, 1.0)
        scar_gate = torch.where(empty_union.bool(), torch.zeros_like(scar_gate), scar_gate)
        edema_gate = torch.where(empty_union.bool(), torch.zeros_like(edema_gate), edema_gate)

        t2_present = canonical_t2_present(availability).to(device=anatomy_logits.device)
        no_t2 = (~t2_present).view(-1, 1, 1, 1, 1)
        edema_gate = torch.where(no_t2, torch.zeros_like(edema_gate), edema_gate)

        return {
            "p_union": p_union,
            "p_lv": p_lv,
            "p_rv": p_rv,
            "union_distance": union_distance,
            "lv_distance": lv_distance,
            "rv_distance": rv_distance,
            "union_proximity": union_proximity,
            "lv_proximity": lv_proximity,
            "rv_proximity": rv_proximity,
            "anatomy_uncertainty": anatomy_uncertainty,
            "anchor_uncertainty": anchor_uncertainty,
            "uncertainty": uncertainty,
            "scar_soft_gate": scar_gate,
            "edema_soft_gate": edema_gate,
            "scar_soft_gate_logits": _safe_logit(scar_gate),
            "edema_soft_gate_logits": torch.where(no_t2, torch.full_like(edema_gate, -20.0), _safe_logit(edema_gate)),
            "empty_union_fallback": empty_union.expand_as(p_union),
        }


class CropSoftROIRefinementHead(nn.Module):
    """Refine pathology logits by cropping a local soft ROI and pasting back.

    The residual branch never sees the full volume at once. It consumes the
    task features, the original lesion-relevant modality crop, proposal and
    dictionary maps, anchor/component evidence, anatomy support, uncertainty,
    and a soft ROI mask inside a bounded crop.
    """

    def __init__(
        self,
        channels: int,
        *,
        pathology: str,
        modality_index: int,
        roi_kernel: int,
        crop_margin: int,
        min_crop_shape: tuple[int, int, int],
        residual_scale: float,
        roi_threshold: float,
        containment_penalty: float,
    ) -> None:
        super().__init__()
        if pathology not in {"scar", "edema"}:
            raise ValueError(f"unknown pathology {pathology!r}")
        self.pathology = pathology
        self.modality_index = int(modality_index)
        self.roi_kernel = int(roi_kernel)
        self.crop_margin = int(crop_margin)
        self.min_crop_shape = tuple(int(v) for v in min_crop_shape)
        self.residual_scale = float(residual_scale)
        self.roi_threshold = float(roi_threshold)
        self.containment_penalty = float(containment_penalty)
        self.refine = nn.Sequential(
            nn.Conv3d(channels + 18, channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(_groups(channels), channels),
            nn.LeakyReLU(0.01, inplace=True),
            nn.Conv3d(channels, channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(_groups(channels), channels),
            nn.LeakyReLU(0.01, inplace=True),
            nn.Conv3d(channels, 1, kernel_size=1),
        )

    @staticmethod
    def _uncertainty(logits: torch.Tensor) -> torch.Tensor:
        prob = torch.sigmoid(logits)
        return (1.0 - torch.abs(2.0 * prob - 1.0)).clamp(0.0, 1.0)

    def soft_roi(
        self,
        proposal_logits: torch.Tensor,
        anatomy_prior: torch.Tensor,
        anchor_evidence: torch.Tensor,
        component_evidence: torch.Tensor,
        evidence_logits: torch.Tensor,
        anatomy_context: dict[str, torch.Tensor] | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        proposal = torch.sigmoid(proposal_logits)
        anatomy = torch.sigmoid(anatomy_prior)
        k = _odd_kernel(self.roi_kernel, tuple(int(v) for v in proposal.shape[-3:]))
        proposal_context = F.avg_pool3d(proposal, kernel_size=k, stride=1, padding=k // 2)
        anatomy_neighborhood = F.avg_pool3d(anatomy, kernel_size=k, stride=1, padding=k // 2)
        uncertainty = self._uncertainty(evidence_logits)
        if anatomy_context is None:
            anatomy_gate = anatomy_neighborhood.clamp(0.0, 1.0)
            distance_support = anatomy_neighborhood.clamp(0.0, 1.0)
        else:
            gate_key = "scar_soft_gate" if self.pathology == "scar" else "edema_soft_gate"
            anatomy_gate = anatomy_context[gate_key].to(device=proposal.device, dtype=proposal.dtype)
            distance_support = anatomy_context["union_proximity"].to(device=proposal.device, dtype=proposal.dtype)
            uncertainty = torch.maximum(
                uncertainty,
                anatomy_context["uncertainty"].to(device=proposal.device, dtype=proposal.dtype),
            )
        if self.pathology == "scar":
            roi = (
                0.55 * proposal
                + 0.15 * proposal_context
                + 0.10 * anchor_evidence
                + 0.08 * component_evidence
                + 0.07 * anatomy_gate
                + 0.05 * uncertainty
            )
            gate_floor = 0.08
        else:
            roi = (
                0.45 * proposal
                + 0.20 * proposal_context
                + 0.10 * anchor_evidence
                + 0.08 * component_evidence
                + 0.12 * anatomy_gate
                + 0.05 * uncertainty
            )
            gate_floor = 0.12
        distance_support = distance_support.clamp(0.0, 1.0)
        soft_gate = (gate_floor + (1.0 - gate_floor) * anatomy_gate.clamp(0.0, 1.0)).clamp(0.0, 1.0)
        roi = roi.clamp(0.0, 1.0) * soft_gate * (0.25 + 0.75 * distance_support)
        return roi.clamp(0.0, 1.0), uncertainty, distance_support

    @staticmethod
    def _crop(tensor: torch.Tensor, batch_idx: int, starts: tuple[int, int, int], ends: tuple[int, int, int]) -> torch.Tensor:
        z0, y0, x0 = starts
        z1, y1, x1 = ends
        return tensor[batch_idx : batch_idx + 1, :, z0:z1, y0:y1, x0:x1]

    @staticmethod
    def _center_seed(spatial_shape: tuple[int, int, int], device: torch.device) -> torch.Tensor:
        depth, height, width = spatial_shape
        seed = torch.zeros(spatial_shape, dtype=torch.bool, device=device)
        seed[int(depth) // 2, int(height) // 2, int(width) // 2] = True
        return seed

    def forward(
        self,
        image: torch.Tensor,
        features: torch.Tensor,
        evidence_logits: torch.Tensor,
        proposal_logits: torch.Tensor,
        anatomy_prior: torch.Tensor,
        availability: torch.Tensor,
        *,
        anchor_evidence: torch.Tensor,
        component_evidence: torch.Tensor,
        pos_similarity: torch.Tensor,
        neg_similarity: torch.Tensor,
        anatomy_context: dict[str, torch.Tensor] | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if image.shape[1] <= self.modality_index:
            raise ValueError(f"image has {image.shape[1]} channels, cannot read modality index {self.modality_index}")
        roi, uncertainty, distance_support = self.soft_roi(
            proposal_logits,
            anatomy_prior,
            anchor_evidence,
            component_evidence,
            evidence_logits,
            anatomy_context=anatomy_context,
        )
        batch, _, depth, height, width = evidence_logits.shape
        spatial_shape = (int(depth), int(height), int(width))
        final = evidence_logits - self.containment_penalty * (1.0 - distance_support) * (1.0 - roi)
        residual_full = torch.zeros_like(evidence_logits)
        crop_mask_full = torch.zeros_like(evidence_logits)
        bounds = torch.zeros((batch, 6), dtype=torch.long, device=evidence_logits.device)
        stats = torch.zeros((batch, 8), dtype=evidence_logits.dtype, device=evidence_logits.device)
        t2_present = canonical_t2_present(availability).to(device=evidence_logits.device)
        for bidx in range(batch):
            if self.pathology == "edema" and not bool(t2_present[bidx].item()):
                final[bidx : bidx + 1] = torch.full_like(final[bidx : bidx + 1], -20.0)
                stats[bidx, 7] = 3.0  # no-T2 blocked.
                continue
            roi_b = roi[bidx, 0]
            proposal_seed = torch.sigmoid(proposal_logits[bidx, 0]) >= self.roi_threshold
            roi_seed = roi_b >= self.roi_threshold
            source_code = 0.0
            crop_seed = roi_seed | proposal_seed
            if not bool(crop_seed.any().item()):
                anatomy_seed = torch.sigmoid(anatomy_prior[bidx, 0]) >= 0.35
                crop_seed = anatomy_seed
                source_code = 1.0
            if not bool(crop_seed.any().item()):
                crop_seed = self._center_seed(spatial_shape, roi_b.device)
                source_code = 2.0
            starts, ends = _bounded_box(
                crop_seed,
                margin=self.crop_margin,
                min_shape=self.min_crop_shape,
                spatial_shape=spatial_shape,
            )
            z0, y0, x0 = starts
            z1, y1, x1 = ends
            bounds[bidx] = torch.tensor([z0, z1, y0, y1, x0, x1], dtype=torch.long, device=evidence_logits.device)
            crop_mask_full[bidx : bidx + 1, :, z0:z1, y0:y1, x0:x1] = 1.0
            modality = self._crop(image[:, self.modality_index : self.modality_index + 1], bidx, starts, ends)
            present = availability[bidx, self.modality_index].to(device=image.device, dtype=image.dtype).view(1, 1, 1, 1, 1)
            modality = modality * present
            crop_inputs = torch.cat(
                [
                    self._crop(features, bidx, starts, ends),
                    modality,
                    self._crop(evidence_logits, bidx, starts, ends),
                    self._crop(proposal_logits, bidx, starts, ends),
                    self._crop(anatomy_prior, bidx, starts, ends),
                    self._crop(anchor_evidence, bidx, starts, ends),
                    self._crop(component_evidence, bidx, starts, ends),
                    self._crop(pos_similarity, bidx, starts, ends),
                    self._crop(neg_similarity, bidx, starts, ends),
                    self._crop(uncertainty, bidx, starts, ends),
                    self._crop(distance_support, bidx, starts, ends),
                    self._crop(roi, bidx, starts, ends),
                    self._crop(
                        anatomy_context["p_union"] if anatomy_context is not None else torch.sigmoid(anatomy_prior),
                        bidx,
                        starts,
                        ends,
                    ),
                    self._crop(
                        anatomy_context["p_lv"] if anatomy_context is not None else torch.zeros_like(anatomy_prior),
                        bidx,
                        starts,
                        ends,
                    ),
                    self._crop(
                        anatomy_context["p_rv"] if anatomy_context is not None else torch.zeros_like(anatomy_prior),
                        bidx,
                        starts,
                        ends,
                    ),
                    self._crop(
                        anatomy_context["union_distance"] if anatomy_context is not None else 1.0 - distance_support,
                        bidx,
                        starts,
                        ends,
                    ),
                    self._crop(
                        anatomy_context["lv_distance"] if anatomy_context is not None else torch.ones_like(anatomy_prior),
                        bidx,
                        starts,
                        ends,
                    ),
                    self._crop(
                        anatomy_context["rv_distance"] if anatomy_context is not None else torch.ones_like(anatomy_prior),
                        bidx,
                        starts,
                        ends,
                    ),
                    self._crop(
                        anatomy_context["scar_soft_gate" if self.pathology == "scar" else "edema_soft_gate"]
                        if anatomy_context is not None
                        else distance_support,
                        bidx,
                        starts,
                        ends,
                    ),
                ],
                dim=1,
            )
            residual = self.refine(crop_inputs)
            roi_crop = self._crop(roi, bidx, starts, ends)
            evidence_crop = self._crop(evidence_logits, bidx, starts, ends)
            final_crop = evidence_crop + self.residual_scale * roi_crop * residual
            final[bidx : bidx + 1, :, z0:z1, y0:y1, x0:x1] = final_crop
            residual_full[bidx : bidx + 1, :, z0:z1, y0:y1, x0:x1] = residual
            crop_voxels = float((z1 - z0) * (y1 - y0) * (x1 - x0))
            total_voxels = float(max(1, depth * height * width))
            stats[bidx, 0] = roi_b.mean()
            stats[bidx, 1] = roi_b.max()
            stats[bidx, 2] = (roi_b >= self.roi_threshold).to(dtype=evidence_logits.dtype).mean()
            stats[bidx, 3] = crop_voxels / total_voxels
            stats[bidx, 4] = (torch.sigmoid(final[bidx, 0]) >= 0.5).to(dtype=evidence_logits.dtype).mean()
            stats[bidx, 5] = residual.abs().mean()
            stats[bidx, 6] = 1.0 if crop_voxels >= total_voxels else 0.0
            stats[bidx, 7] = source_code
        return final, residual_full, roi, crop_mask_full, bounds, stats


SoftROIRefinementHead = CropSoftROIRefinementHead



class BaselinePreservingResidualGate(nn.Module):
    """Bounded SRR correction around same-case nnU-Net anchor logits."""

    def __init__(self, num_classes: int = 6, max_delta: float = 4.0, init_gate_bias: float = -4.0) -> None:
        super().__init__()
        self.num_classes = int(num_classes)
        self.max_delta = float(max_delta)
        self.gate = nn.Conv3d(self.num_classes * 2 + 4, self.num_classes, kernel_size=1)
        nn.init.zeros_(self.gate.weight)
        nn.init.constant_(self.gate.bias, float(init_gate_bias))

    @staticmethod
    def _anchor_tensor(anchor_features: torch.Tensor | dict[str, torch.Tensor] | None) -> torch.Tensor | None:
        if anchor_features is None:
            return None
        if isinstance(anchor_features, dict):
            for key in ("logits", "probabilities", "probs", "anchor", "features"):
                value = anchor_features.get(key)
                if isinstance(value, torch.Tensor):
                    return value
            return None
        return anchor_features

    @staticmethod
    def _as_logits(anchor: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
        value = anchor.to(device=reference.device, dtype=reference.dtype)
        if value.shape[1] != reference.shape[1]:
            raise ValueError(f"nnU-Net anchor class count {value.shape[1]} does not match SRR logits {reference.shape[1]}")
        if value.shape[-3:] != reference.shape[-3:]:
            value = F.interpolate(value, size=reference.shape[-3:], mode="trilinear", align_corners=False)
        if bool((value.detach().min() >= 0).item()) and bool((value.detach().max() <= 1).item()):
            value = torch.logit(value.clamp(1e-4, 1.0 - 1e-4))
        return value

    def forward(
        self,
        srr_logits: torch.Tensor,
        anchor_features: torch.Tensor | dict[str, torch.Tensor] | None,
        availability: torch.Tensor,
        *,
        force_closed: bool = False,
    ) -> dict[str, torch.Tensor | str]:
        anchor = self._anchor_tensor(anchor_features)
        if anchor is None:
            zero = torch.zeros_like(srr_logits)
            return {
                "final_logits": srr_logits,
                "anchor_logits": zero,
                "gate": zero,
                "bounded_delta": zero,
                "residual_magnitude": zero[:, :1],
                "gate_status": "anchor_missing_passthrough",
            }
        anchor_logits = self._as_logits(anchor, srr_logits)
        probs = torch.softmax(anchor_logits, dim=1)
        uncertainty = (1.0 - probs.max(dim=1, keepdim=True).values).clamp(0.0, 1.0)
        availability_maps = availability.to(device=srr_logits.device, dtype=srr_logits.dtype).view(-1, 3, 1, 1, 1)
        availability_maps = availability_maps.expand(-1, -1, *srr_logits.shape[-3:])
        gate_input = torch.cat([srr_logits, anchor_logits, uncertainty, availability_maps], dim=1)
        gate = torch.sigmoid(self.gate(gate_input))
        if force_closed:
            gate = torch.zeros_like(gate)
        bounded_delta = self.max_delta * torch.tanh(srr_logits - anchor_logits)
        final = anchor_logits + gate * bounded_delta
        t2_present = canonical_t2_present(availability).to(device=final.device)
        no_t2_mask = (~t2_present).view(-1, 1, 1, 1, 1)
        final[:, 4:5] = torch.where(no_t2_mask, torch.full_like(final[:, 4:5], -20.0), final[:, 4:5])
        return {
            "final_logits": final,
            "anchor_logits": anchor_logits,
            "gate": gate,
            "bounded_delta": bounded_delta,
            "residual_magnitude": (gate * bounded_delta).abs().mean(dim=1, keepdim=True),
            "gate_status": "baseline_preserving_residual",
        }


class SegmentationContextInterface(nn.Module):
    """Expose nnU-Net anchor context as SRR evidence instead of a silent bypass."""

    @staticmethod
    def _anchor_tensor(anchor_features: torch.Tensor | dict[str, torch.Tensor] | None) -> torch.Tensor | None:
        return BaselinePreservingResidualGate._anchor_tensor(anchor_features)

    @staticmethod
    def _class_probs(anchor: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
        value = anchor.to(device=reference.device, dtype=reference.dtype)
        if value.shape[-3:] != reference.shape[-3:]:
            value = F.interpolate(value, size=reference.shape[-3:], mode="trilinear", align_corners=False)
        if bool((value.detach().min() >= 0).item()) and bool((value.detach().max() <= 1).item()):
            denom = value.sum(dim=1, keepdim=True).clamp_min(1e-6)
            return (value / denom).clamp(0.0, 1.0)
        return torch.softmax(value, dim=1)

    @staticmethod
    def _component_tensor(
        component_features: torch.Tensor | dict[str, torch.Tensor] | None,
        key: str,
        channel: int,
        reference: torch.Tensor,
    ) -> torch.Tensor:
        value: torch.Tensor | None = None
        if isinstance(component_features, dict):
            candidate = component_features.get(key)
            if isinstance(candidate, torch.Tensor):
                value = candidate
        elif isinstance(component_features, torch.Tensor):
            value = component_features[:, channel : channel + 1] if component_features.shape[1] > channel else None
        if value is None:
            return torch.zeros_like(reference[:, :1])
        value = value.to(device=reference.device, dtype=reference.dtype)
        if value.shape[-3:] != reference.shape[-3:]:
            value = F.interpolate(value, size=reference.shape[-3:], mode="nearest")
        return value[:, :1].clamp(0.0, 1.0)

    def forward(
        self,
        reference_logits: torch.Tensor,
        anchor_features: torch.Tensor | dict[str, torch.Tensor] | None,
        component_features: torch.Tensor | dict[str, torch.Tensor] | None,
        anatomy_context: dict[str, torch.Tensor],
    ) -> dict[str, torch.Tensor | str]:
        anchor = self._anchor_tensor(anchor_features)
        if anchor is None:
            probs = torch.softmax(reference_logits.detach(), dim=1)
            source_status = "anchor_missing_reference_softmax"
        else:
            probs = self._class_probs(anchor, reference_logits)
            source_status = "nnunet_anchor_context"
        hard = probs.argmax(dim=1, keepdim=True).to(dtype=reference_logits.dtype)
        sorted_probs = probs.sort(dim=1, descending=True).values
        margin = (sorted_probs[:, 0:1] - sorted_probs[:, 1:2]).clamp(0.0, 1.0)
        entropy = -(probs * torch.log(probs.clamp_min(1e-6))).sum(dim=1, keepdim=True)
        entropy = entropy / reference_logits.new_tensor(float(max(2, probs.shape[1]))).log()
        confidence = probs.max(dim=1, keepdim=True).values
        scar_component = self._component_tensor(component_features, "scar_component", 0, reference_logits)
        edema_component = self._component_tensor(component_features, "edema_component", 1, reference_logits)
        p_union = anatomy_context["p_union"].to(device=reference_logits.device, dtype=reference_logits.dtype)
        union_distance = anatomy_context["union_distance"].to(device=reference_logits.device, dtype=reference_logits.dtype)
        scar_size = scar_component.flatten(2).mean(dim=2).view(-1, 1, 1, 1, 1).expand_as(scar_component)
        edema_size = edema_component.flatten(2).mean(dim=2).view(-1, 1, 1, 1, 1).expand_as(edema_component)
        remote_scar = ((scar_component > 0.5) & (union_distance > 0.65)).to(dtype=reference_logits.dtype)
        remote_edema = ((edema_component > 0.5) & (union_distance > 0.65)).to(dtype=reference_logits.dtype)
        return {
            "anchor_probabilities": probs,
            "anchor_hard_prediction": hard,
            "anchor_entropy": entropy,
            "anchor_margin": margin,
            "anchor_confidence": confidence,
            "scar_component_mask": scar_component,
            "edema_component_mask": edema_component,
            "scar_component_size": scar_size,
            "edema_component_size": edema_size,
            "component_distance_to_union": union_distance,
            "scar_remote_component_flag": remote_scar,
            "edema_remote_component_flag": remote_edema,
            "anatomy_union_support": p_union,
            "segmentation_context_status": source_status,
        }


class BranchArbitrationGate(nn.Module):
    """Explicit branch arbitration with exact segmentation fallback."""

    def __init__(self, *, mode: str = "full_context", max_delta: float = 4.0) -> None:
        super().__init__()
        self.mode = str(mode)
        self.max_delta = float(max_delta)
        init_bias = -2.0 if self.mode == "conservative_component" else -1.2
        self.context_gate = nn.Conv3d(10, 4, kernel_size=1)
        nn.init.zeros_(self.context_gate.weight)
        nn.init.constant_(self.context_gate.bias, float(init_bias))

    def forward(
        self,
        srr_logits: torch.Tensor,
        anchor_logits: torch.Tensor,
        availability: torch.Tensor,
        *,
        segmentation_context: dict[str, torch.Tensor | str],
        scar_proposal_logits: torch.Tensor,
        edema_proposal_logits: torch.Tensor,
        scar_roi: torch.Tensor,
        edema_roi: torch.Tensor,
        force_segmentation_fallback: bool = False,
        fallback_reason_override: str | None = None,
    ) -> dict[str, torch.Tensor | str]:
        anchor_conf = segmentation_context["anchor_confidence"]  # type: ignore[assignment]
        anchor_entropy = segmentation_context["anchor_entropy"]  # type: ignore[assignment]
        scar_component = segmentation_context["scar_component_mask"]  # type: ignore[assignment]
        edema_component = segmentation_context["edema_component_mask"]  # type: ignore[assignment]
        union_support = segmentation_context["anatomy_union_support"]  # type: ignore[assignment]
        if not isinstance(anchor_conf, torch.Tensor) or not isinstance(anchor_entropy, torch.Tensor):
            raise TypeError("segmentation context tensors missing")
        context = torch.cat(
            [
                anchor_conf,
                anchor_entropy,
                scar_component if isinstance(scar_component, torch.Tensor) else torch.zeros_like(anchor_conf),
                edema_component if isinstance(edema_component, torch.Tensor) else torch.zeros_like(anchor_conf),
                union_support if isinstance(union_support, torch.Tensor) else torch.zeros_like(anchor_conf),
                torch.sigmoid(scar_proposal_logits),
                torch.sigmoid(edema_proposal_logits),
                scar_roi,
                edema_roi,
                (1.0 - anchor_conf).clamp(0.0, 1.0),
            ],
            dim=1,
        )
        weights = torch.sigmoid(self.context_gate(context))
        uncertainty = (1.0 - anchor_conf).clamp(0.0, 1.0)
        proposal_support = torch.maximum(torch.sigmoid(scar_proposal_logits), torch.sigmoid(edema_proposal_logits))
        if self.mode == "conservative_component":
            open_signal = (uncertainty * proposal_support).clamp(0.0, 1.0)
            weights = weights * open_signal
        elif self.mode == "scar_precision_edema_safe":
            weights = weights * (0.35 + 0.65 * proposal_support)
        else:
            weights = weights * (0.20 + 0.80 * torch.maximum(uncertainty, proposal_support))
        segmentation_weight = (1.0 - weights[:, 0:1]).clamp(0.0, 1.0)
        srr_weight = weights[:, 0:1]
        proposal_weight = weights[:, 1:2]
        refiner_weight = weights[:, 2:3]
        fallback_weight = weights[:, 3:4]
        if force_segmentation_fallback:
            srr_weight = torch.zeros_like(srr_weight)
            proposal_weight = torch.zeros_like(proposal_weight)
            refiner_weight = torch.zeros_like(refiner_weight)
            fallback_weight = torch.ones_like(fallback_weight)
            segmentation_weight = torch.ones_like(segmentation_weight)
        bounded_delta = self.max_delta * torch.tanh(srr_logits - anchor_logits)
        proposal_delta = torch.zeros_like(bounded_delta)
        proposal_delta[:, 4:5] = self.max_delta * torch.tanh(edema_proposal_logits - anchor_logits[:, 4:5])
        proposal_delta[:, 5:6] = self.max_delta * torch.tanh(scar_proposal_logits - anchor_logits[:, 5:6])
        refiner_delta = torch.zeros_like(bounded_delta)
        refiner_delta[:, 4:6] = bounded_delta[:, 4:6]
        correction_mask = ((srr_weight + proposal_weight + refiner_weight) > 1e-4).to(dtype=srr_logits.dtype)
        branch_delta = (
            srr_weight * bounded_delta
            + proposal_weight * proposal_delta
            + refiner_weight * refiner_delta
        ).clamp(min=-self.max_delta, max=self.max_delta)
        final = anchor_logits + branch_delta
        t2_present = canonical_t2_present(availability).to(device=final.device)
        no_t2_mask = (~t2_present).view(-1, 1, 1, 1, 1)
        final[:, 4:5] = torch.where(no_t2_mask, torch.full_like(final[:, 4:5], -20.0), final[:, 4:5])
        return {
            "final_logits": final,
            "segmentation_weight": segmentation_weight,
            "srr_retrieval_weight": srr_weight,
            "proposal_weight": proposal_weight,
            "refiner_weight": refiner_weight,
            "fallback_weight": fallback_weight,
            "bounded_delta": bounded_delta,
            "proposal_delta": proposal_delta,
            "refiner_delta": refiner_delta,
            "branch_delta": branch_delta,
            "correction_mask": correction_mask,
            "anchor_confidence": anchor_conf,
            "srr_confidence": proposal_support,
            "fallback_reason": fallback_reason_override or ("explicit_segmentation_fallback" if force_segmentation_fallback else "evidence_arbitration"),
            "chosen_source": "segmentation_branch" if force_segmentation_fallback else f"srr_v3_{self.mode}",
        }


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
        encoder_profile: str = "tiny_3scale",
        disable_local_refinement: bool = False,
        disable_anatomy_roi_prior: bool = False,
    ) -> None:
        super().__init__()
        if variant not in {
            "srr_propref_shared_dual_dict",
            "srr_propref_scar_precision",
            "srr_propref_no_proto_cascade",
            *M6_VARIANT_CONFIGS.keys(),
        }:
            raise ValueError(f"unknown PropRef variant: {variant}")
        self.variant = variant
        self.base_channels = int(base_channels)
        self.m6_config = M6_VARIANT_CONFIGS.get(variant, {})
        self.m9_srr_main_output = str(self.m6_config.get("m9_final_output_mode", "")) == "SRR_MAIN_NOT_ANCHOR_RESIDUAL"
        self.m10_final_output = str(self.m6_config.get("m10_final_output_mode", "")) == "SRR_PROPOSAL_REFINEMENT"
        self.m10_design = str(self.m6_config.get("m10_design", ""))
        if self.m6_config and str(encoder_profile) in {"tiny_3scale", ""}:
            encoder_profile = str(self.m6_config["default_encoder_profile"])
        self.encoder_profile = str(encoder_profile)
        self.disable_local_refinement = bool(disable_local_refinement)
        self.disable_anatomy_roi_prior = bool(disable_anatomy_roi_prior)
        self.encoder_scale_channels = encoder_profile_scale_channels(base_channels, self.encoder_profile)
        self.feature_channels = int(self.encoder_scale_channels[0])
        self.dictionary_config = str(self.m6_config.get("dictionary_config", "legacy_interaction_slots"))
        self.encoders = nn.ModuleList([build_modality_encoder(base_channels, self.encoder_profile) for _ in range(3)])
        self.retrieval = nn.ModuleList(
            [
                ScaleRetrieval(
                    channels,
                    use_interactions=use_interactions,
                    dictionary_config=self.dictionary_config,
                )
                for channels in self.encoder_scale_channels
            ]
        )
        self.decoders = nn.ModuleDict({task: FlexibleTaskDecoder(self.encoder_scale_channels) for task in ("anatomy", "scar", "edema")})
        self.evidence_heads = AnatomyPathologyHeads(self.feature_channels, prior_strength=0.35)
        self.anatomy_roi_prior = AnatomyDistanceROIPrior(distance_steps=6)
        no_proto = variant == "srr_propref_no_proto_cascade"
        scar_neg = int(self.m6_config.get("scar_negative", 10 if variant == "srr_propref_scar_precision" else 6))
        edema_pos = int(self.m6_config.get("edema_positive", 8 if variant == "srr_propref_shared_dual_dict" else 4))
        self.scar_dictionary = ProposalDictionary(
            self.feature_channels,
            pathology="scar",
            n_positive=6,
            n_negative=scar_neg,
            no_proto=no_proto,
        )
        self.edema_dictionary = ProposalDictionary(
            self.feature_channels,
            pathology="edema",
            n_positive=edema_pos,
            n_negative=6,
            no_proto=no_proto,
        )
        scar_kernel = int(self.m6_config.get("scar_kernel", 3 if variant == "srr_propref_scar_precision" else 5))
        scar_scale = float(self.m6_config.get("scar_scale", 0.85 if variant == "srr_propref_scar_precision" else 0.70))
        edema_kernel = int(self.m6_config.get("edema_kernel", 9 if variant != "srr_propref_scar_precision" else 7))
        edema_scale = float(self.m6_config.get("edema_scale", 0.65))
        self.scar_refine = CropSoftROIRefinementHead(
            self.feature_channels,
            pathology="scar",
            modality_index=0,
            roi_kernel=scar_kernel,
            crop_margin=int(
                self.m6_config.get(
                    "scar_crop_margin",
                    1 if variant in {"srr_propref_scar_precision", "m6_scar_precision_edema_safe", "m6_conservative_component_arbitration"} else 2,
                )
            ),
            min_crop_shape=(3, 4, 4),
            residual_scale=scar_scale,
            roi_threshold=0.22 if variant in {"srr_propref_scar_precision", "m6_scar_precision_edema_safe"} else 0.18,
            containment_penalty=0.45 if variant in {"srr_propref_scar_precision", "m6_scar_precision_edema_safe"} else 0.30,
        )
        self.edema_refine = CropSoftROIRefinementHead(
            self.feature_channels,
            pathology="edema",
            modality_index=1,
            roi_kernel=edema_kernel,
            crop_margin=int(self.m6_config.get("edema_crop_margin", 3)),
            min_crop_shape=(5, 8, 8),
            residual_scale=edema_scale,
            roi_threshold=0.12,
            containment_penalty=0.18,
        )
        self.baseline_gate = BaselinePreservingResidualGate(num_classes=6)
        self.segmentation_context_interface = SegmentationContextInterface()
        self.branch_arbitration = BranchArbitrationGate(mode=str(self.m6_config.get("arbitration_mode", "legacy_baseline")))
        self.m10_spatial_dictionary = (
            M10TwoPassSpatialDictionary(
                self.feature_channels,
                enable_pattern_sip=bool(self.m6_config.get("m10_pattern_sip", False)),
                enable_memory=bool(self.m6_config.get("m10_memory", False)),
            )
            if bool(self.m6_config.get("m10_spatial_dictionary", False))
            else None
        )

    @staticmethod
    def _neutral_anatomy_context(anatomy_logits: torch.Tensor, availability: torch.Tensor) -> dict[str, torch.Tensor]:
        zero = anatomy_logits[:, :1] * 0.0
        one = zero + 1.0
        t2_present = canonical_t2_present(availability).to(device=anatomy_logits.device)
        no_t2 = (~t2_present).view(-1, 1, 1, 1, 1)
        edema_gate = torch.where(no_t2, zero, one)
        return {
            "p_union": one,
            "p_lv": zero,
            "p_rv": zero,
            "union_distance": zero,
            "lv_distance": one,
            "rv_distance": one,
            "union_proximity": one,
            "lv_proximity": zero,
            "rv_proximity": zero,
            "anatomy_uncertainty": zero,
            "anchor_uncertainty": zero,
            "uncertainty": zero,
            "scar_soft_gate": one,
            "edema_soft_gate": edema_gate,
            "scar_soft_gate_logits": _safe_logit(one),
            "edema_soft_gate_logits": torch.where(no_t2, torch.full_like(zero, -20.0), _safe_logit(one)),
            "empty_union_fallback": zero,
        }

    @staticmethod
    def _bypass_refinement(
        refiner: CropSoftROIRefinementHead,
        *,
        proposal_logits: torch.Tensor,
        anatomy_prior: torch.Tensor,
        availability: torch.Tensor,
        anchor_evidence: torch.Tensor,
        component_evidence: torch.Tensor,
        evidence_logits: torch.Tensor,
        anatomy_context: dict[str, torch.Tensor] | None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        roi, _uncertainty, _distance_support = refiner.soft_roi(
            proposal_logits,
            anatomy_prior,
            anchor_evidence,
            component_evidence,
            evidence_logits,
            anatomy_context=anatomy_context,
        )
        final = proposal_logits
        residual = torch.zeros_like(proposal_logits)
        crop_mask = torch.zeros_like(proposal_logits)
        batch = int(proposal_logits.shape[0])
        bounds = torch.zeros((batch, 6), dtype=torch.long, device=proposal_logits.device)
        stats = torch.zeros((batch, 8), dtype=proposal_logits.dtype, device=proposal_logits.device)
        stats[:, 0] = roi.flatten(1).mean(dim=1)
        stats[:, 1] = roi.flatten(1).amax(dim=1)
        stats[:, 2] = (roi >= refiner.roi_threshold).to(dtype=proposal_logits.dtype).flatten(1).mean(dim=1)
        stats[:, 4] = (torch.sigmoid(final) >= 0.5).to(dtype=proposal_logits.dtype).flatten(1).mean(dim=1)
        stats[:, 7] = 4.0
        if refiner.pathology == "edema":
            t2_present = canonical_t2_present(availability).to(device=proposal_logits.device)
            no_t2 = (~t2_present).view(-1, 1, 1, 1, 1)
            final = torch.where(no_t2, torch.full_like(final, -20.0), final)
            stats[:, 7] = torch.where(no_t2.flatten(), torch.full_like(stats[:, 7], 3.0), stats[:, 7])
        return final, residual, roi, crop_mask, bounds, stats

    @staticmethod
    def _iter_context_tensors(context: torch.Tensor | dict[str, torch.Tensor] | None) -> list[tuple[str, torch.Tensor]]:
        if context is None:
            return []
        if isinstance(context, torch.Tensor):
            return [("tensor", context)]
        return [(str(key), value) for key, value in context.items() if isinstance(value, torch.Tensor)]

    def _validate_context_shapes(
        self,
        x: torch.Tensor,
        anchor_features: torch.Tensor | dict[str, torch.Tensor] | None,
        component_features: torch.Tensor | dict[str, torch.Tensor] | None,
    ) -> None:
        expected_batch = int(x.shape[0])
        expected_spatial = tuple(int(v) for v in x.shape[-3:])
        for source_name, context in (("anchor_features", anchor_features), ("component_features", component_features)):
            for key, value in self._iter_context_tensors(context):
                if value.ndim != 5:
                    continue
                if int(value.shape[0]) != expected_batch:
                    raise ValueError(
                        f"{source_name}.{key} batch {value.shape[0]} does not match image batch {expected_batch}"
                    )
                if tuple(int(v) for v in value.shape[-3:]) != expected_spatial:
                    raise ValueError(
                        f"{source_name}.{key} spatial shape {tuple(value.shape[-3:])} does not match image spatial shape {expected_spatial}"
                    )

    def _evidence_features(
        self,
        x: torch.Tensor,
        availability: torch.Tensor,
        anchor_features: torch.Tensor | dict[str, torch.Tensor] | None = None,
    ) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor], dict[str, list[dict[str, object]]], dict[str, torch.Tensor]]:
        per_modality = [encoder(x[:, idx : idx + 1], availability[:, idx]) for idx, encoder in enumerate(self.encoders)]
        routed_by_task = {task: [] for task in ("anatomy", "scar", "edema")}
        gates: dict[str, torch.Tensor] = {}
        gate_metadata: dict[str, list[dict[str, object]]] = {}
        gate_valid_masks: dict[str, torch.Tensor] = {}
        for scale, retrieval in enumerate(self.retrieval):
            routed, scale_gates = retrieval([features[scale] for features in per_modality], availability, anchor_features)
            for task in routed_by_task:
                routed_by_task[task].append(routed[task])
                gates[f"{task}_scale{scale}"] = scale_gates[task]
                gate_metadata[f"{task}_scale{scale}"] = retrieval.slot_metadata
                if retrieval.last_valid_mask is not None:
                    gate_valid_masks[f"{task}_scale{scale}"] = retrieval.last_valid_mask
        return {
            "anatomy": self.decoders["anatomy"](routed_by_task["anatomy"]),
            "scar": self.decoders["scar"](routed_by_task["scar"]),
            "edema": self.decoders["edema"](routed_by_task["edema"]),
        }, gates, gate_metadata, gate_valid_masks

    def forward(
        self,
        x: torch.Tensor,
        availability: torch.Tensor,
        anchor_features: torch.Tensor | dict[str, torch.Tensor] | None = None,
        component_features: torch.Tensor | dict[str, torch.Tensor] | None = None,
        *,
        force_segmentation_fallback: bool = False,
        force_closed_gate: bool = False,
        disable_srr_evidence: bool = False,
    ) -> dict[str, torch.Tensor]:
        if x.shape[1] != 3:
            raise ValueError(f"SRRProposeRefineMyoPS expects 3 channels, got {x.shape[1]}")
        self._validate_context_shapes(x, anchor_features, component_features)
        availability = availability.to(device=x.device, dtype=x.dtype).clamp(0, 1)
        features, gates, gate_metadata, gate_valid_masks = self._evidence_features(x, availability, anchor_features)
        evidence = self.evidence_heads(features["anatomy"], features["scar"], features["edema"])
        anatomy_prior = evidence["union_prior_logits"]
        if self.disable_anatomy_roi_prior:
            anatomy_context = self._neutral_anatomy_context(evidence["anatomy_logits"], availability)
        else:
            anatomy_context = self.anatomy_roi_prior(evidence["anatomy_logits"], anchor_features, availability)
        segmentation_context = self.segmentation_context_interface(
            evidence["anatomy_logits"],
            anchor_features,
            component_features,
            anatomy_context,
        )
        m10_spatial: dict[str, object] | None = None
        if self.m10_spatial_dictionary is not None:
            m10_spatial = self.m10_spatial_dictionary(
                [features["anatomy"], features["scar"], features["edema"]],
                availability,
                anatomy_context=anatomy_context,
                initial_evidence={"scar": evidence["scar_logits"], "edema": evidence["edema_logits"]},
            )
            features["scar"] = features["scar"] + m10_spatial["scar_retrieved"]  # type: ignore[operator]
            features["edema"] = features["edema"] + m10_spatial["edema_retrieved"]  # type: ignore[operator]
            spatial_gates = m10_spatial["gates"]  # type: ignore[assignment]
            spatial_metadata = {
                name: m10_spatial["slot_metadata"]  # type: ignore[index]
                for name in spatial_gates  # type: ignore[union-attr]
            }
            spatial_valid = {
                name: m10_spatial["valid_mask"]  # type: ignore[index]
                for name in spatial_gates  # type: ignore[union-attr]
            }
            gates = {**gates, **spatial_gates}  # type: ignore[arg-type]
            gate_metadata = {**gate_metadata, **spatial_metadata}  # type: ignore[arg-type]
            gate_valid_masks = {**gate_valid_masks, **spatial_valid}  # type: ignore[arg-type]
        scar_anatomy_prior = anatomy_context["scar_soft_gate_logits"]
        edema_anatomy_prior = anatomy_context["edema_soft_gate_logits"]
        scar_dict = self.scar_dictionary(
            features["scar"],
            evidence["scar_logits"],
            scar_anatomy_prior,
            anchor_features=anchor_features,
            component_features=component_features,
            availability=availability,
        )
        edema_dict = self.edema_dictionary(
            features["edema"],
            evidence["edema_logits"],
            edema_anatomy_prior,
            anchor_features=anchor_features,
            component_features=component_features,
            availability=availability,
        )
        if self.disable_local_refinement:
            scar_logits, scar_residual, scar_roi, scar_crop_mask, scar_crop_bounds, scar_roi_stats = self._bypass_refinement(
                self.scar_refine,
                proposal_logits=scar_dict["proposal_logits"],
                anatomy_prior=scar_anatomy_prior,
                availability=availability,
                anchor_evidence=scar_dict["anchor_evidence"],
                component_evidence=scar_dict["component_evidence"],
                evidence_logits=evidence["scar_logits"],
                anatomy_context=anatomy_context,
            )
            edema_logits, edema_residual, edema_roi, edema_crop_mask, edema_crop_bounds, edema_roi_stats = self._bypass_refinement(
                self.edema_refine,
                proposal_logits=edema_dict["proposal_logits"],
                anatomy_prior=edema_anatomy_prior,
                availability=availability,
                anchor_evidence=edema_dict["anchor_evidence"],
                component_evidence=edema_dict["component_evidence"],
                evidence_logits=evidence["edema_logits"],
                anatomy_context=anatomy_context,
            )
        else:
            scar_logits, scar_residual, scar_roi, scar_crop_mask, scar_crop_bounds, scar_roi_stats = self.scar_refine(
                x,
                features["scar"],
                evidence["scar_logits"],
                scar_dict["proposal_logits"],
                scar_anatomy_prior,
                availability,
                anchor_evidence=scar_dict["anchor_evidence"],
                component_evidence=scar_dict["component_evidence"],
                pos_similarity=scar_dict["pos_similarity"],
                neg_similarity=scar_dict["neg_similarity"],
                anatomy_context=anatomy_context,
            )
            edema_logits, edema_residual, edema_roi, edema_crop_mask, edema_crop_bounds, edema_roi_stats = self.edema_refine(
                x,
                features["edema"],
                evidence["edema_logits"],
                edema_dict["proposal_logits"],
                edema_anatomy_prior,
                availability,
                anchor_evidence=edema_dict["anchor_evidence"],
                component_evidence=edema_dict["component_evidence"],
                pos_similarity=edema_dict["pos_similarity"],
                neg_similarity=edema_dict["neg_similarity"],
                anatomy_context=anatomy_context,
            )
        t2_present = canonical_t2_present(availability).to(device=edema_logits.device)
        no_t2_mask = (~t2_present).view(-1, 1, 1, 1, 1)
        edema_logits = torch.where(no_t2_mask, torch.full_like(edema_logits, -20.0), edema_logits)
        if disable_srr_evidence:
            scar_dict["proposal_logits"] = torch.full_like(scar_dict["proposal_logits"], -20.0)
            edema_dict["proposal_logits"] = torch.full_like(edema_dict["proposal_logits"], -20.0)
            scar_logits = torch.full_like(scar_logits, -20.0)
            edema_logits = torch.full_like(edema_logits, -20.0)
            scar_roi = torch.zeros_like(scar_roi)
            edema_roi = torch.zeros_like(edema_roi)
        srr_logits = torch.cat([evidence["anatomy_logits"], edema_logits, scar_logits], dim=1)
        baseline_blend = self.baseline_gate(srr_logits, anchor_features, availability, force_closed=force_closed_gate)
        fallback_reason_override = None
        if disable_srr_evidence:
            fallback_reason_override = "low_quality_srr_evidence_empty"
        elif force_closed_gate:
            fallback_reason_override = "closed_gate_identity"
        elif force_segmentation_fallback:
            fallback_reason_override = "explicit_segmentation_fallback"
        arbitration = self.branch_arbitration(
            srr_logits,
            baseline_blend["anchor_logits"],
            availability,
            segmentation_context=segmentation_context,
            scar_proposal_logits=scar_dict["proposal_logits"],
            edema_proposal_logits=edema_dict["proposal_logits"],
            scar_roi=scar_roi,
            edema_roi=edema_roi,
            force_segmentation_fallback=bool(force_segmentation_fallback or force_closed_gate or disable_srr_evidence),
            fallback_reason_override=fallback_reason_override,
        )
        proposal_logits = torch.cat([evidence["anatomy_logits"], edema_dict["proposal_logits"], scar_dict["proposal_logits"]], dim=1)
        refiner_logits = srr_logits
        use_arbitration = self.variant in M6_VARIANT_CONFIGS and not self.m9_srr_main_output
        if self.m9_srr_main_output or self.m10_final_output:
            final_logits = srr_logits
            branch_arbitration_status = (
                "m10_srr_proposal_refinement_no_anchor_identity"
                if self.m10_final_output
                else "m9_srr_main_output_anchor_control_only"
            )
        else:
            final_logits = arbitration["final_logits"] if use_arbitration else baseline_blend["final_logits"]
            branch_arbitration_status = "enabled_explicit_arbitration" if use_arbitration else "legacy_baseline_gate_only"
        final_labels = final_logits.argmax(dim=1)
        srr_labels = srr_logits.argmax(dim=1)
        anchor_labels = baseline_blend["anchor_logits"].argmax(dim=1)
        final_delta_vs_srr = (final_labels != srr_labels).to(dtype=final_logits.dtype).flatten(1).mean(dim=1)
        final_delta_vs_anchor = (final_labels != anchor_labels).to(dtype=final_logits.dtype).flatten(1).mean(dim=1)
        q_struct = torch.softmax(evidence["anatomy_logits"], dim=1)
        p_scar = torch.sigmoid(scar_logits)
        q_edema = canonical_t2_present(availability).to(device=final_logits.device, dtype=final_logits.dtype).view(-1, 1, 1, 1, 1)
        p_edema = q_edema * (1.0 - p_scar).clamp_min(0.0) * torch.sigmoid(edema_logits)
        residual_anatomy = (1.0 - p_scar - p_edema).clamp_min(0.0)
        m10_final_probabilities = torch.cat([residual_anatomy * q_struct, p_edema, p_scar], dim=1)
        outputs = {
            "logits": final_logits,
            "branch_arbitration_status": branch_arbitration_status,
            "branch_chosen_source": arbitration["chosen_source"],
            "branch_fallback_reason": arbitration["fallback_reason"],
            "segmentation_weight": arbitration["segmentation_weight"],
            "srr_retrieval_weight": arbitration["srr_retrieval_weight"],
            "proposal_weight": arbitration["proposal_weight"],
            "refiner_weight": arbitration["refiner_weight"],
            "branch_fallback_weight": arbitration["fallback_weight"],
            "branch_correction_mask": arbitration["correction_mask"],
            "branch_anchor_confidence": arbitration["anchor_confidence"],
            "branch_srr_confidence": arbitration["srr_confidence"],
            "srr_logits_pre_anchor": srr_logits,
            "m9_final_output_mode": "SRR_MAIN_NOT_ANCHOR_RESIDUAL" if self.m9_srr_main_output else "ANCHOR_RESIDUAL_OR_LEGACY_CONTROL",
            "m10_design": self.m10_design,
            "final_output_base": "SRR_PROPOSAL_REFINEMENT" if self.m10_final_output else "ANCHOR_RESIDUAL_OR_LEGACY_CONTROL",
            "m10_final_probabilities": m10_final_probabilities,
            "m10_no_t2_edema_probability_max": p_edema[q_edema.expand_as(p_edema) <= 0].max() if bool((q_edema <= 0).any()) else p_edema.new_tensor(0.0),
            "nnunet_role": (
                "CONTEXT_TEACHER_SAFETY_CONTROL_ONLY"
                if self.m9_srr_main_output or self.m10_final_output
                else "ANCHOR_RESIDUAL_CONTROL_OR_LEGACY_CONTEXT"
            ),
            "srr_main_logits": srr_logits,
            "proposal_logits": proposal_logits,
            "refiner_logits": refiner_logits,
            "anatomy_context_logits": evidence["anatomy_logits"],
            "final_label_delta_vs_srr_without_dictionary": final_delta_vs_srr,
            "final_label_delta_vs_anchor_control": final_delta_vs_anchor,
            "nnunet_anchor_logits": baseline_blend["anchor_logits"],
            "baseline_residual_gate": baseline_blend["gate"],
            "bounded_delta_srr": baseline_blend["bounded_delta"],
            "arbitration_bounded_delta": arbitration["bounded_delta"],
            "arbitration_proposal_delta": arbitration["proposal_delta"],
            "arbitration_refiner_delta": arbitration["refiner_delta"],
            "arbitration_branch_delta": arbitration["branch_delta"],
            "baseline_residual_magnitude": baseline_blend["residual_magnitude"],
            "baseline_gate_status": baseline_blend["gate_status"],
            "encoder_profile": self.encoder_profile,
            "encoder_scale_channels": tuple(self.encoder_scale_channels),
            "dictionary_config": self.dictionary_config,
            "local_refinement_status": "disabled_bypass_to_proposal_logits" if self.disable_local_refinement else "enabled_crop_soft_roi",
            "anatomy_roi_prior_status": "disabled_neutral_context" if self.disable_anatomy_roi_prior else "enabled_distance_soft_gates",
            "segmentation_context_status": segmentation_context["segmentation_context_status"],
            "anchor_probabilities": segmentation_context["anchor_probabilities"],
            "anchor_hard_prediction": segmentation_context["anchor_hard_prediction"],
            "anchor_entropy": segmentation_context["anchor_entropy"],
            "anchor_margin": segmentation_context["anchor_margin"],
            "anchor_confidence": segmentation_context["anchor_confidence"],
            "scar_component_mask": segmentation_context["scar_component_mask"],
            "edema_component_mask": segmentation_context["edema_component_mask"],
            "scar_component_size": segmentation_context["scar_component_size"],
            "edema_component_size": segmentation_context["edema_component_size"],
            "component_distance_to_union": segmentation_context["component_distance_to_union"],
            "scar_remote_component_flag": segmentation_context["scar_remote_component_flag"],
            "edema_remote_component_flag": segmentation_context["edema_remote_component_flag"],
            "anatomy_union_support": segmentation_context["anatomy_union_support"],
            "anatomy_logits": evidence["anatomy_logits"],
            "scar_logits": scar_logits,
            "edema_logits": edema_logits,
            "union_prior_logits": anatomy_prior,
            "p_union": anatomy_context["p_union"],
            "p_lv": anatomy_context["p_lv"],
            "p_rv": anatomy_context["p_rv"],
            "union_distance": anatomy_context["union_distance"],
            "lv_distance": anatomy_context["lv_distance"],
            "rv_distance": anatomy_context["rv_distance"],
            "union_proximity": anatomy_context["union_proximity"],
            "anatomy_uncertainty": anatomy_context["anatomy_uncertainty"],
            "anchor_anatomy_uncertainty": anatomy_context["anchor_uncertainty"],
            "scar_anatomy_soft_gate": anatomy_context["scar_soft_gate"],
            "edema_anatomy_soft_gate": anatomy_context["edema_soft_gate"],
            "empty_union_fallback": anatomy_context["empty_union_fallback"],
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
            "scar_anchor_evidence": scar_dict["anchor_evidence"],
            "edema_anchor_evidence": edema_dict["anchor_evidence"],
            "scar_component_evidence": scar_dict["component_evidence"],
            "edema_component_evidence": edema_dict["component_evidence"],
            "scar_proposal_formula_terms": scar_dict["proposal_formula_terms"],
            "edema_proposal_formula_terms": edema_dict["proposal_formula_terms"],
            "scar_refinement_residual": scar_residual,
            "edema_refinement_residual": edema_residual,
            "scar_soft_roi": scar_roi,
            "edema_soft_roi": edema_roi,
            "scar_crop_region_mask": scar_crop_mask,
            "edema_crop_region_mask": edema_crop_mask,
            "scar_crop_bounds_zyx": scar_crop_bounds,
            "edema_crop_bounds_zyx": edema_crop_bounds,
            "scar_roi_stats": scar_roi_stats,
            "edema_roi_stats": edema_roi_stats,
            "no_t2_inference_policy": "block_edema",
            "proposal_math": (
                "positive_similarity - negative_similarity + nnU-Net/component evidence + neutral anatomy ROI context"
                if self.disable_anatomy_roi_prior
                else "positive_similarity - negative_similarity + nnU-Net/component evidence + P_union/P_LV/P_RV distance/uncertainty soft ROI prior"
            ),
            "prototype_source": {
                "scar": self.scar_dictionary.prototype_source,
                "edema": self.edema_dictionary.prototype_source,
            },
            "gates": gates,
            "availability": availability,
            "expert_usage": {name: gate.mean(dim=0) for name, gate in gates.items()},
            "dictionary_slot_counts": {f"scale{idx}": block.slot_counts for idx, block in enumerate(self.retrieval)},
            "dictionary_slot_metadata": gate_metadata,
            "gate_valid_masks": gate_valid_masks,
            "dictionary_diagnostics": gate_diagnostics(gates, gate_metadata, gate_valid_masks),
        }
        if m10_spatial is not None:
            outputs["m10_spatial_dictionary_status"] = "enabled_two_pass_spatial"
            outputs["m10_spatial_pattern_sip_status"] = m10_spatial["pattern_sip_status"]  # type: ignore[index]
            outputs["m10_spatial_memory_status"] = m10_spatial["memory_status"]  # type: ignore[index]
            outputs["m10_scar_initial_proposal"] = m10_spatial["scar_initial_proposal"]  # type: ignore[index]
            outputs["m10_edema_initial_proposal"] = m10_spatial["edema_initial_proposal"]  # type: ignore[index]
        else:
            outputs["m10_spatial_dictionary_status"] = "disabled_for_static_or_legacy_design"
        return outputs
