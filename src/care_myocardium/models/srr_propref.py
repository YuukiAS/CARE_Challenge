"""SRR proposal-refinement model for CARE MyoPS fold0 hardmode tasks."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from src.care_myocardium.anchors.myops_decode import canonical_t2_present
from src.care_myocardium.models.pathology_heads import AnatomyPathologyHeads
from src.care_myocardium.models.proposal_prototypes import deterministic_axis_prototypes
from src.care_myocardium.models.srr_blocks import gate_diagnostics
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
            nn.Conv3d(channels + 11, channels, kernel_size=3, padding=1, bias=False),
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
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        proposal = torch.sigmoid(proposal_logits)
        anatomy = torch.sigmoid(anatomy_prior)
        k = _odd_kernel(self.roi_kernel, tuple(int(v) for v in proposal.shape[-3:]))
        proposal_context = F.avg_pool3d(proposal, kernel_size=k, stride=1, padding=k // 2)
        anatomy_context = F.avg_pool3d(anatomy, kernel_size=k, stride=1, padding=k // 2)
        uncertainty = self._uncertainty(evidence_logits)
        if self.pathology == "scar":
            roi = (
                0.55 * proposal
                + 0.15 * proposal_context
                + 0.10 * anchor_evidence
                + 0.08 * component_evidence
                + 0.07 * anatomy_context
                + 0.05 * uncertainty
            )
        else:
            roi = (
                0.45 * proposal
                + 0.20 * proposal_context
                + 0.10 * anchor_evidence
                + 0.08 * component_evidence
                + 0.12 * anatomy_context
                + 0.05 * uncertainty
            )
        distance_support = anatomy_context.clamp(0.0, 1.0)
        roi = roi.clamp(0.0, 1.0) * (0.25 + 0.75 * distance_support)
        return roi.clamp(0.0, 1.0), uncertainty, distance_support

    @staticmethod
    def _crop(tensor: torch.Tensor, batch_idx: int, starts: tuple[int, int, int], ends: tuple[int, int, int]) -> torch.Tensor:
        z0, y0, x0 = starts
        z1, y1, x1 = ends
        return tensor[batch_idx : batch_idx + 1, :, z0:z1, y0:y1, x0:x1]

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
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if image.shape[1] <= self.modality_index:
            raise ValueError(f"image has {image.shape[1]} channels, cannot read modality index {self.modality_index}")
        roi, uncertainty, distance_support = self.soft_roi(
            proposal_logits,
            anatomy_prior,
            anchor_evidence,
            component_evidence,
            evidence_logits,
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
                crop_seed = torch.ones_like(roi_b, dtype=torch.bool)
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
        self.scar_refine = CropSoftROIRefinementHead(
            base_channels,
            pathology="scar",
            modality_index=0,
            roi_kernel=scar_kernel,
            crop_margin=1 if variant == "srr_propref_scar_precision" else 2,
            min_crop_shape=(3, 4, 4),
            residual_scale=scar_scale,
            roi_threshold=0.22 if variant == "srr_propref_scar_precision" else 0.18,
            containment_penalty=0.45 if variant == "srr_propref_scar_precision" else 0.30,
        )
        self.edema_refine = CropSoftROIRefinementHead(
            base_channels,
            pathology="edema",
            modality_index=1,
            roi_kernel=edema_kernel,
            crop_margin=3,
            min_crop_shape=(5, 8, 8),
            residual_scale=0.65,
            roi_threshold=0.12,
            containment_penalty=0.18,
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
    ) -> dict[str, torch.Tensor]:
        if x.shape[1] != 3:
            raise ValueError(f"SRRProposeRefineMyoPS expects 3 channels, got {x.shape[1]}")
        availability = availability.to(device=x.device, dtype=x.dtype).clamp(0, 1)
        features, gates, gate_metadata, gate_valid_masks = self._evidence_features(x, availability, anchor_features)
        evidence = self.evidence_heads(features["anatomy"], features["scar"], features["edema"])
        anatomy_prior = evidence["union_prior_logits"]
        scar_dict = self.scar_dictionary(
            features["scar"],
            evidence["scar_logits"],
            anatomy_prior,
            anchor_features=anchor_features,
            component_features=component_features,
            availability=availability,
        )
        edema_dict = self.edema_dictionary(
            features["edema"],
            evidence["edema_logits"],
            anatomy_prior,
            anchor_features=anchor_features,
            component_features=component_features,
            availability=availability,
        )
        scar_logits, scar_residual, scar_roi, scar_crop_mask, scar_crop_bounds, scar_roi_stats = self.scar_refine(
            x,
            features["scar"],
            evidence["scar_logits"],
            scar_dict["proposal_logits"],
            anatomy_prior,
            availability,
            anchor_evidence=scar_dict["anchor_evidence"],
            component_evidence=scar_dict["component_evidence"],
            pos_similarity=scar_dict["pos_similarity"],
            neg_similarity=scar_dict["neg_similarity"],
        )
        edema_logits, edema_residual, edema_roi, edema_crop_mask, edema_crop_bounds, edema_roi_stats = self.edema_refine(
            x,
            features["edema"],
            evidence["edema_logits"],
            edema_dict["proposal_logits"],
            anatomy_prior,
            availability,
            anchor_evidence=edema_dict["anchor_evidence"],
            component_evidence=edema_dict["component_evidence"],
            pos_similarity=edema_dict["pos_similarity"],
            neg_similarity=edema_dict["neg_similarity"],
        )
        t2_present = canonical_t2_present(availability).to(device=edema_logits.device)
        no_t2_mask = (~t2_present).view(-1, 1, 1, 1, 1)
        edema_logits = torch.where(no_t2_mask, torch.full_like(edema_logits, -20.0), edema_logits)
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
            "scar_anchor_evidence": scar_dict["anchor_evidence"],
            "edema_anchor_evidence": edema_dict["anchor_evidence"],
            "scar_component_evidence": scar_dict["component_evidence"],
            "edema_component_evidence": edema_dict["component_evidence"],
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
            "proposal_math": "positive_similarity - negative_similarity + nnU-Net/component evidence + anatomy/distance prior",
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
        return outputs
