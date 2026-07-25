"""Clean CARE SRR cascade rescue model for bounded pathology correction."""

from __future__ import annotations

import math

import torch
from torch import nn
from torch.nn import functional as F


ANATOMY_CHANNELS = (0, 1, 2, 3)
EDEMA_CHANNEL = 4
SCAR_CHANNEL = 5


def _check_anchor(anchor_logits: torch.Tensor) -> None:
    if anchor_logits.ndim != 5:
        raise ValueError(f"anchor_logits must be [B, 6, D, H, W], got ndim={anchor_logits.ndim}")
    if anchor_logits.shape[1] != 6:
        raise ValueError(f"anchor_logits must have six channels, got {anchor_logits.shape[1]}")


def _expand_binary_case_mask(mask: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    values = mask.to(device=reference.device, dtype=reference.dtype)
    if values.ndim == 1:
        values = values.view(-1, 1, 1, 1, 1)
    elif values.ndim == 2:
        values = values.view(values.shape[0], values.shape[1], 1, 1, 1)
    while values.ndim < reference.ndim:
        values = values.unsqueeze(-1)
    if values.shape[1] != 1:
        raise ValueError("t2_present must expand to one channel")
    return values.expand(reference.shape[0], 1, *reference.shape[2:])


def _single_channel(value: torch.Tensor | None, reference: torch.Tensor, *, fill: float = 0.0) -> torch.Tensor:
    if value is None:
        return reference.new_full((reference.shape[0], 1, *reference.shape[2:]), float(fill))
    if value.shape[0] != reference.shape[0] or value.shape[2:] != reference.shape[2:]:
        raise ValueError(f"spatial shape mismatch: expected batch/spatial {reference.shape[0], reference.shape[2:]}")
    if value.shape[1] != 1:
        raise ValueError(f"expected a single-channel tensor, got {value.shape[1]} channels")
    return value.to(device=reference.device, dtype=reference.dtype)


def _six_channels(value: torch.Tensor | None, reference: torch.Tensor, *, name: str) -> torch.Tensor:
    if value is None:
        return anchor_probabilities(reference)
    if value.shape != reference.shape:
        raise ValueError(f"{name} must share anchor [B, 6, D, H, W] shape")
    return value.to(device=reference.device, dtype=reference.dtype)


def _four_channels(value: torch.Tensor | None, reference: torch.Tensor, *, name: str) -> torch.Tensor:
    if value is None:
        return reference.new_zeros((reference.shape[0], 4, *reference.shape[2:]))
    if value.shape[0] != reference.shape[0] or value.shape[1] != 4 or value.shape[2:] != reference.shape[2:]:
        raise ValueError(f"{name} must be [B, 4, D, H, W] on the anchor grid")
    return value.to(device=reference.device, dtype=reference.dtype)


def anchor_probabilities(anchor_logits: torch.Tensor, epsilon: float = 1e-6) -> torch.Tensor:
    _check_anchor(anchor_logits)
    raw = torch.softmax(anchor_logits, dim=1).clamp(float(epsilon), 1.0)
    return raw / raw.sum(dim=1, keepdim=True).clamp_min(float(epsilon))


def anchor_uncertainty(anchor_probs: torch.Tensor) -> torch.Tensor:
    clipped = anchor_probs.clamp_min(1e-6)
    entropy = -(clipped * clipped.log()).sum(dim=1, keepdim=True)
    return entropy / math.log(float(anchor_probs.shape[1]))


def soft_union_probability(anchor_probs: torch.Tensor) -> torch.Tensor:
    union = anchor_probs[:, 1:2] + anchor_probs[:, EDEMA_CHANNEL : EDEMA_CHANNEL + 1] + anchor_probs[:, SCAR_CHANNEL : SCAR_CHANNEL + 1]
    return union.clamp(0.0, 1.0)


def fixed_support_map(
    *,
    distance_to_union_mm: torch.Tensor,
    soft_union: torch.Tensor,
    max_distance_mm: float,
    sigma_mm: float,
) -> torch.Tensor:
    distance = distance_to_union_mm.to(device=soft_union.device, dtype=soft_union.dtype).clamp_min(0.0)
    radial = torch.exp(-0.5 * (distance / float(sigma_mm)).square())
    inside = (distance <= float(max_distance_mm)).to(dtype=soft_union.dtype)
    return inside * torch.maximum(soft_union, radial)


class _ResidualBlock(nn.Module):
    def __init__(self, channels: int, groups: int) -> None:
        super().__init__()
        self.conv1 = nn.Conv3d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.norm1 = nn.GroupNorm(groups, channels)
        self.conv2 = nn.Conv3d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.norm2 = nn.GroupNorm(groups, channels)
        self.activation = nn.SiLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.activation(self.norm1(self.conv1(x)))
        x = self.norm2(self.conv2(x))
        return self.activation(x + residual)


class _PathologyBranch(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, hidden_channels: int, groups: int, residual_blocks: int) -> None:
        super().__init__()
        self.input_projection = nn.Sequential(
            nn.Conv3d(in_channels, hidden_channels, kernel_size=1, bias=False),
            nn.GroupNorm(groups, hidden_channels),
            nn.SiLU(inplace=True),
        )
        self.residual_blocks = nn.Sequential(*[_ResidualBlock(hidden_channels, groups) for _ in range(int(residual_blocks))])
        self.output_projection = nn.Conv3d(hidden_channels, out_channels, kernel_size=1)
        nn.init.zeros_(self.output_projection.weight)
        nn.init.zeros_(self.output_projection.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.output_projection(self.residual_blocks(self.input_projection(x)))


class CARESRRCascadeRescue(nn.Module):
    """Composes bounded pathology corrections onto frozen six-class anchor logits."""

    pathology_channels = {"edema": EDEMA_CHANNEL, "scar": SCAR_CHANNEL}
    anatomy_channels = ANATOMY_CHANNELS
    correction_bound_logit = 2.0
    hidden_channels = 32
    groupnorm_groups = 8
    residual_block_count = 2
    explicit_feature_keys = (
        "source_features",
        "normalized_lge",
        "normalized_t2",
        "anchor_probabilities",
        "teacher_anatomy_probabilities",
        "teacher_edema_probability",
        "scar_source_margin",
        "anchor_uncertainty",
        "soft_union_probability",
        "normalized_distance_to_union",
        "prototype_scar_positive_similarity",
        "prototype_scar_negative_similarity",
        "prototype_edema_positive_similarity",
        "prototype_edema_negative_similarity",
    )

    def __init__(self, source_feature_channels: int = 32) -> None:
        super().__init__()
        self.source_feature_channels = int(source_feature_channels)
        if self.source_feature_channels <= 0:
            raise ValueError("source_feature_channels must be positive")

        scar_in_channels = self.source_feature_channels + 17
        edema_in_channels = self.source_feature_channels + 18
        self.scar_branch = _PathologyBranch(
            scar_in_channels,
            1,
            self.hidden_channels,
            self.groupnorm_groups,
            self.residual_block_count,
        )
        self.edema_branch = _PathologyBranch(
            edema_in_channels,
            2,
            self.hidden_channels,
            self.groupnorm_groups,
            self.residual_block_count,
        )

    @property
    def scar_output_projection(self) -> nn.Conv3d:
        return self.scar_branch.output_projection

    @property
    def edema_output_projection(self) -> nn.Conv3d:
        return self.edema_branch.output_projection

    def forward(
        self,
        *,
        anchor_logits: torch.Tensor,
        source_features: torch.Tensor,
        distance_to_union_mm: torch.Tensor,
        t2_present: torch.Tensor,
        normalized_lge: torch.Tensor | None = None,
        normalized_t2: torch.Tensor | None = None,
        teacher_anatomy_logits: torch.Tensor | None = None,
        teacher_anatomy_probabilities: torch.Tensor | None = None,
        teacher_edema_logit: torch.Tensor | None = None,
        teacher_edema_probability: torch.Tensor | None = None,
        scar_source_margin: torch.Tensor | None = None,
        explicit_anchor_probabilities: torch.Tensor | None = None,
        explicit_anchor_uncertainty: torch.Tensor | None = None,
        explicit_soft_union_probability: torch.Tensor | None = None,
        normalized_distance_to_union: torch.Tensor | None = None,
        prototype_scar_positive_similarity: torch.Tensor | None = None,
        prototype_scar_negative_similarity: torch.Tensor | None = None,
        prototype_edema_positive_similarity: torch.Tensor | None = None,
        prototype_edema_negative_similarity: torch.Tensor | None = None,
        active_pathology: str = "both",
    ) -> dict[str, torch.Tensor]:
        if active_pathology not in {"scar", "edema", "both"}:
            raise ValueError("active_pathology must be one of scar, edema, both")
        _check_anchor(anchor_logits)
        if source_features.ndim != 5:
            raise ValueError("source_features must be [B, C, D, H, W]")
        if source_features.shape[1] != self.source_feature_channels:
            raise ValueError(
                f"source_features channel mismatch: expected {self.source_feature_channels}, got {source_features.shape[1]}"
            )
        if source_features.shape[0] != anchor_logits.shape[0] or source_features.shape[2:] != anchor_logits.shape[2:]:
            raise ValueError("source_features must share anchor batch and spatial shape")

        dist = _single_channel(distance_to_union_mm, anchor_logits)
        t2_mask = _expand_binary_case_mask(t2_present, anchor_logits)
        probs = _six_channels(explicit_anchor_probabilities, anchor_logits, name="explicit_anchor_probabilities")
        uncertainty = _single_channel(explicit_anchor_uncertainty, anchor_logits) if explicit_anchor_uncertainty is not None else anchor_uncertainty(probs)
        union = _single_channel(explicit_soft_union_probability, anchor_logits) if explicit_soft_union_probability is not None else soft_union_probability(probs)
        norm_dist = _single_channel(normalized_distance_to_union, anchor_logits) if normalized_distance_to_union is not None else (dist / 15.0).clamp(0.0, 1.0)
        if teacher_anatomy_probabilities is None and teacher_anatomy_logits is not None:
            teacher_anatomy_probabilities = torch.softmax(teacher_anatomy_logits, dim=1)
        teacher_anatomy = _four_channels(
            teacher_anatomy_probabilities,
            anchor_logits,
            name="teacher_anatomy_probabilities",
        )
        if teacher_edema_probability is None and teacher_edema_logit is not None:
            teacher_edema_probability = torch.sigmoid(teacher_edema_logit)
        teacher_edema = _single_channel(teacher_edema_probability, anchor_logits)
        scar_support = fixed_support_map(
            distance_to_union_mm=dist,
            soft_union=union,
            max_distance_mm=10.0,
            sigma_mm=5.0,
        )
        edema_support = fixed_support_map(
            distance_to_union_mm=dist,
            soft_union=union,
            max_distance_mm=15.0,
            sigma_mm=7.5,
        )

        source = source_features.to(device=anchor_logits.device, dtype=anchor_logits.dtype)
        normalized_lge_1 = _single_channel(normalized_lge, anchor_logits)
        normalized_t2_1 = _single_channel(normalized_t2, anchor_logits)
        scar_positive = _single_channel(prototype_scar_positive_similarity, anchor_logits)
        scar_negative = _single_channel(prototype_scar_negative_similarity, anchor_logits)
        edema_positive = _single_channel(prototype_edema_positive_similarity, anchor_logits)
        edema_negative = _single_channel(prototype_edema_negative_similarity, anchor_logits)
        scar_features = torch.cat(
            [
                source,
                normalized_lge_1,
                probs,
                teacher_anatomy,
                _single_channel(scar_source_margin, anchor_logits),
                uncertainty,
                union,
                norm_dist,
                scar_positive,
                scar_negative,
            ],
            dim=1,
        )
        edema_features = torch.cat(
            [
                source,
                normalized_t2_1,
                normalized_lge_1,
                probs,
                teacher_edema,
                teacher_anatomy,
                uncertainty,
                union,
                norm_dist,
                edema_positive,
                edema_negative,
            ],
            dim=1,
        )
        zero_pathology = anchor_logits.new_zeros((anchor_logits.shape[0], 1, *anchor_logits.shape[2:]))
        if active_pathology in {"scar", "both"}:
            scar_delta = self.scar_branch(scar_features)
        else:
            scar_delta = zero_pathology
        if active_pathology in {"edema", "both"}:
            edema_outputs = self.edema_branch(edema_features)
            edema_zone_aux_logit = edema_outputs[:, 0:1]
            edema_delta = edema_outputs[:, 1:2]
        else:
            edema_zone_aux_logit = zero_pathology
            edema_delta = zero_pathology

        scar_correction = scar_support * self.correction_bound_logit * torch.tanh(scar_delta)
        edema_correction = t2_mask * edema_support * self.correction_bound_logit * torch.tanh(edema_delta)

        final_logits = anchor_logits.clone()
        final_logits[:, 0:4] = anchor_logits[:, 0:4]
        if active_pathology in {"edema", "both"}:
            final_logits[:, EDEMA_CHANNEL : EDEMA_CHANNEL + 1] = (
                anchor_logits[:, EDEMA_CHANNEL : EDEMA_CHANNEL + 1] + edema_correction
            )
        else:
            final_logits[:, EDEMA_CHANNEL : EDEMA_CHANNEL + 1] = anchor_logits[:, EDEMA_CHANNEL : EDEMA_CHANNEL + 1]
        if active_pathology in {"scar", "both"}:
            final_logits[:, SCAR_CHANNEL : SCAR_CHANNEL + 1] = (
                anchor_logits[:, SCAR_CHANNEL : SCAR_CHANNEL + 1] + scar_correction
            )
        else:
            final_logits[:, SCAR_CHANNEL : SCAR_CHANNEL + 1] = anchor_logits[:, SCAR_CHANNEL : SCAR_CHANNEL + 1]

        return {
            "logits": final_logits,
            "final_logits": final_logits,
            "anchor_logits": anchor_logits,
            "anchor_probabilities": probs,
            "anchor_uncertainty": uncertainty,
            "soft_union_probability": union,
            "normalized_distance_to_union": norm_dist,
            "teacher_anatomy_probabilities": teacher_anatomy,
            "teacher_edema_probability": teacher_edema,
            "scar_support": scar_support,
            "edema_support": edema_support,
            "scar_delta": scar_delta,
            "edema_delta": edema_delta,
            "scar_correction": scar_correction,
            "edema_correction": edema_correction,
            "edema_zone_aux_logit": edema_zone_aux_logit,
            "t2_present_mask": t2_mask,
            "active_pathology": active_pathology,
        }
