"""CARE-DPR dual-pathology proposal-refine-arbitrate model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from torch import nn
import torch.nn.functional as F

from src.care_myocardium.models.care_dg import (
    ANATOMY_CHANNELS,
    EDEMA_CHANNEL,
    SCAR_CHANNEL,
    Encoder3D,
    ResidualBlock3D,
    Stem3D,
    _as_case_mask,
    _availability_map,
    _ensure_map,
    apply_competitive_correction,
)


@dataclass(frozen=True)
class CAREDPRConfig:
    image_channels: int = 3
    anchor_channels: int = 6
    stem_channels: int = 8
    context_channels: int = 16
    encoder_channels: tuple[int, int, int] = (32, 64, 96)
    branch_channels: int = 32
    scar_margin_cap: float = 4.0
    edema_margin_cap: float = 4.0
    utility_accept_threshold: float = 0.5
    scar_roi_context_zyx: tuple[int, int, int] = (8, 96, 96)
    edema_roi_context_zyx: tuple[int, int, int] = (8, 128, 128)


class DPRBranch(nn.Module):
    """One pathology branch with direct lesion, error proposal, refiner, and utility heads."""

    def __init__(self, channels: tuple[int, int, int], branch_channels: int) -> None:
        super().__init__()
        c0, c1, c2 = channels
        self.up1 = nn.Sequential(
            nn.Conv3d(c2 + c1, 64, 3, padding=1, bias=False),
            nn.InstanceNorm3d(64, affine=True),
            nn.SiLU(inplace=True),
            ResidualBlock3D(64, level=1),
        )
        self.up0 = nn.Sequential(
            nn.Conv3d(64 + c0, branch_channels, (1, 3, 3), padding=(0, 1, 1), bias=False),
            nn.InstanceNorm3d(branch_channels, affine=True),
            nn.SiLU(inplace=True),
            ResidualBlock3D(branch_channels, level=0),
        )
        # Output order is contract-sensitive: p_coarse, q_fn, q_fp.
        self.proposal_head = nn.Conv3d(branch_channels, 3, 1)
        self.refiner_head = nn.Sequential(
            nn.Conv3d(branch_channels + 7, branch_channels, (1, 3, 3), padding=(0, 1, 1), bias=False),
            nn.InstanceNorm3d(branch_channels, affine=True),
            nn.SiLU(inplace=True),
            nn.Conv3d(branch_channels, 1, 1),
        )
        self.utility_head = nn.Sequential(
            nn.Conv3d(branch_channels + 7, branch_channels, (1, 3, 3), padding=(0, 1, 1), bias=False),
            nn.InstanceNorm3d(branch_channels, affine=True),
            nn.SiLU(inplace=True),
            nn.Conv3d(branch_channels, 2, 1),
        )

    def forward(self, scales: tuple[torch.Tensor, torch.Tensor, torch.Tensor], branch_context: torch.Tensor) -> dict[str, torch.Tensor]:
        s0, s1, s2 = scales
        u1 = F.interpolate(s2, size=s1.shape[-3:], mode="trilinear", align_corners=False)
        u1 = self.up1(torch.cat([u1, s1], dim=1))
        u0 = F.interpolate(u1, size=s0.shape[-3:], mode="trilinear", align_corners=False)
        feat = self.up0(torch.cat([u0, s0], dim=1))
        proposal_raw = self.proposal_head(feat)
        p_coarse_logit = proposal_raw[:, 0:1]
        q_fn_logit = proposal_raw[:, 1:2]
        q_fp_logit = proposal_raw[:, 2:3]
        head_input = torch.cat([feat, branch_context], dim=1)
        refined_logit = self.refiner_head(head_input)
        utility_raw = self.utility_head(head_input)
        utility_accept_logit = utility_raw[:, 0:1]
        utility_regression_logit = utility_raw[:, 1:2]
        return {
            "feature": feat,
            "p_coarse_logit": p_coarse_logit,
            "q_fn_logit": q_fn_logit,
            "q_fp_logit": q_fp_logit,
            "p_coarse": torch.sigmoid(p_coarse_logit),
            "q_fn": torch.sigmoid(q_fn_logit),
            "q_fp": torch.sigmoid(q_fp_logit),
            "refined_logit": refined_logit,
            "p_refined": torch.sigmoid(refined_logit),
            "utility_accept_logit": utility_accept_logit,
            "utility_regression": torch.tanh(utility_regression_logit),
            "utility_accept_prob": torch.sigmoid(utility_accept_logit),
        }


def pathology_margin(anchor_logits: torch.Tensor, channel: int) -> torch.Tensor:
    competitor = torch.cat([anchor_logits[:, :channel], anchor_logits[:, channel + 1 :]], dim=1).amax(dim=1, keepdim=True)
    return anchor_logits[:, channel : channel + 1] - competitor


def edema_zone_margin(anchor_logits: torch.Tensor) -> torch.Tensor:
    zone = torch.maximum(anchor_logits[:, SCAR_CHANNEL : SCAR_CHANNEL + 1], anchor_logits[:, EDEMA_CHANNEL : EDEMA_CHANNEL + 1])
    anatomy = anchor_logits[:, list(ANATOMY_CHANNELS)].amax(dim=1, keepdim=True)
    return zone - anatomy


def soft_union(*maps: torch.Tensor) -> torch.Tensor:
    out = torch.zeros_like(maps[0])
    for m in maps:
        out = torch.maximum(out, m.clamp(0.0, 1.0))
    return out


def _branch_context(uncertainty: torch.Tensor, support: torch.Tensor, distance: torch.Tensor, p_coarse: torch.Tensor, q_fn: torch.Tensor, q_fp: torch.Tensor, pathology_margin_map: torch.Tensor) -> torch.Tensor:
    return torch.cat([uncertainty, support, distance, p_coarse, q_fn, q_fp, pathology_margin_map], dim=1)


def _training_roi(predicted_roi: torch.Tensor, teacher_roi: torch.Tensor | None, teacher_roi_fraction: float, *, allow_teacher_roi: bool) -> torch.Tensor:
    frac = float(teacher_roi_fraction)
    if frac <= 0.0:
        return predicted_roi
    if not allow_teacher_roi:
        raise ValueError("CARE_DPR_TEACHER_ROI_FORBIDDEN_IN_EVAL_OR_INFERENCE")
    if teacher_roi is None:
        raise ValueError("CARE_DPR_TEACHER_ROI_REQUIRED_FOR_TEACHER_FORCING")
    return torch.maximum(predicted_roi * (1.0 - frac), teacher_roi.to(predicted_roi).clamp(0.0, 1.0) * frac)


def _delta_from_refiner(refined_logit: torch.Tensor, anchor_margin: torch.Tensor, p_coarse: torch.Tensor, q_fn: torch.Tensor, q_fp: torch.Tensor, utility_accept: torch.Tensor, roi: torch.Tensor, margin_cap: float, hard_accept: bool, threshold: float) -> torch.Tensor:
    accept = (utility_accept >= float(threshold)).to(utility_accept.dtype) if hard_accept else utility_accept
    desired_delta = torch.clamp(refined_logit - anchor_margin, -float(margin_cap), float(margin_cap))
    proposal_gate = soft_union(p_coarse, q_fn, q_fp)
    return desired_delta * proposal_gate * accept * roi


class CAREDPR(nn.Module):
    """One shared encoder with independent scar and edema-zone DPR branches."""

    def __init__(self, config: CAREDPRConfig | None = None) -> None:
        super().__init__()
        self.config = config or CAREDPRConfig()
        c = self.config
        self.lge_stem = Stem3D(1, c.stem_channels)
        self.t2_stem = Stem3D(1, c.stem_channels)
        self.c0_stem = Stem3D(1, c.stem_channels)
        self.anchor_context = Stem3D(c.anchor_channels + 2, c.context_channels)
        encoder_in = c.stem_channels * 3 + c.context_channels + 3
        self.encoder = Encoder3D(encoder_in, c.encoder_channels)
        self.scar_branch = DPRBranch(c.encoder_channels, c.branch_channels)
        self.edema_branch = DPRBranch(c.encoder_channels, c.branch_channels)

    def forward(
        self,
        images: torch.Tensor,
        availability: torch.Tensor,
        anchor_logits: torch.Tensor,
        *,
        uncertainty: torch.Tensor | None = None,
        myocardium_support: torch.Tensor | None = None,
        edema_support: torch.Tensor | None = None,
        distance_to_myocardium: torch.Tensor | None = None,
        t2_present: torch.Tensor | None = None,
        scar_teacher_roi: torch.Tensor | None = None,
        edema_teacher_roi: torch.Tensor | None = None,
        teacher_roi_fraction: float = 0.0,
        allow_teacher_roi: bool = False,
        strict_inputs: bool = False,
        anchor_value_kind: str | None = None,
        hard_component_accept: bool = False,
        force_anchor_fallback: bool = False,
    ) -> dict[str, torch.Tensor]:
        if images.ndim != 5 or images.shape[1] != 3:
            raise ValueError("images must be [B,3,D,H,W] in LGE,T2,C0 order")
        if anchor_logits.ndim != 5 or anchor_logits.shape[1] != 6:
            raise ValueError("anchor_logits must be [B,6,D,H,W]")
        if images.shape[0] != anchor_logits.shape[0] or images.shape[-3:] != anchor_logits.shape[-3:]:
            raise ValueError("images and anchor_logits must share batch and spatial shape")
        if strict_inputs and anchor_value_kind not in {"logits", "log_probabilities"}:
            raise ValueError("formal CARE-DPR mode requires anchor_value_kind='logits' or 'log_probabilities'")

        avail = _availability_map(availability, anchor_logits)
        unc = _ensure_map(uncertainty, anchor_logits, 0.0, name="uncertainty", strict=strict_inputs)
        dist = _ensure_map(distance_to_myocardium, anchor_logits, 0.0, name="distance_to_myocardium", strict=strict_inputs)
        scar_support = _ensure_map(myocardium_support, anchor_logits, 1.0, name="myocardium_support", strict=strict_inputs).clamp(0.0, 1.0)
        edema_zone_support = _ensure_map(edema_support, anchor_logits, 1.0, name="edema_support", strict=strict_inputs).clamp(0.0, 1.0)
        if t2_present is None:
            t2_present = availability[:, 1] if availability.ndim == 2 else availability[:, 1].flatten(1).amax(dim=1)
        t2_mask = _as_case_mask(t2_present, anchor_logits)

        stemmed = torch.cat([
            self.lge_stem(images[:, 0:1] * avail[:, 0:1]),
            self.t2_stem(images[:, 1:2] * avail[:, 1:2]),
            self.c0_stem(images[:, 2:3] * avail[:, 2:3]),
        ], dim=1)
        context = self.anchor_context(torch.cat([anchor_logits, unc, dist], dim=1))
        scales = self.encoder(torch.cat([stemmed, context, avail], dim=1))

        scar_anchor_prob = torch.softmax(anchor_logits, dim=1)[:, SCAR_CHANNEL : SCAR_CHANNEL + 1]
        edema_anchor_prob = torch.softmax(anchor_logits, dim=1)[:, [SCAR_CHANNEL, EDEMA_CHANNEL]].amax(dim=1, keepdim=True)
        scar_anchor_margin = pathology_margin(anchor_logits, SCAR_CHANNEL)
        edema_anchor_margin = edema_zone_margin(anchor_logits)

        blank = torch.zeros(anchor_logits.shape[0], 3, *anchor_logits.shape[-3:], device=anchor_logits.device, dtype=anchor_logits.dtype)
        scar0 = self.scar_branch(scales, torch.cat([unc, scar_support, dist, blank[:, 0:1], blank[:, 1:2], blank[:, 2:3], scar_anchor_margin], dim=1))
        edema0 = self.edema_branch(scales, torch.cat([unc, edema_zone_support, dist, blank[:, 0:1], blank[:, 1:2], blank[:, 2:3], edema_anchor_margin], dim=1))

        scar_predicted_roi = scar_support * soft_union(scar_anchor_prob, scar0["p_coarse"], scar0["q_fn"], scar0["q_fp"] * scar_anchor_prob, unc)
        edema_predicted_roi = edema_zone_support * t2_mask * soft_union(edema_anchor_prob, edema0["p_coarse"], edema0["q_fn"], edema0["q_fp"] * edema_anchor_prob, unc)
        scar_train_roi = _training_roi(scar_predicted_roi, scar_teacher_roi, teacher_roi_fraction, allow_teacher_roi=allow_teacher_roi)
        edema_train_roi = _training_roi(edema_predicted_roi, edema_teacher_roi, teacher_roi_fraction, allow_teacher_roi=allow_teacher_roi) * t2_mask

        scar = self.scar_branch(scales, _branch_context(unc, scar_train_roi, dist, scar0["p_coarse"], scar0["q_fn"], scar0["q_fp"], scar_anchor_margin))
        edema = self.edema_branch(scales, _branch_context(unc, edema_train_roi, dist, edema0["p_coarse"], edema0["q_fn"], edema0["q_fp"], edema_anchor_margin))

        scar_delta = _delta_from_refiner(scar["refined_logit"], scar_anchor_margin, scar0["p_coarse"], scar0["q_fn"], scar0["q_fp"], scar["utility_accept_prob"], scar_train_roi, self.config.scar_margin_cap, hard_component_accept, self.config.utility_accept_threshold)
        edema_delta = _delta_from_refiner(edema["refined_logit"], edema_anchor_margin, edema0["p_coarse"], edema0["q_fn"], edema0["q_fp"], edema["utility_accept_prob"], edema_train_roi, self.config.edema_margin_cap, hard_component_accept, self.config.utility_accept_threshold) * t2_mask
        if force_anchor_fallback:
            scar_delta = scar_delta * 0.0
            edema_delta = edema_delta * 0.0

        after_edema = apply_competitive_correction(anchor_logits, edema_delta, torch.ones_like(edema_delta), EDEMA_CHANNEL, self.config.edema_margin_cap, competitor_channels=ANATOMY_CHANNELS)
        final_logits = apply_competitive_correction(after_edema, scar_delta, torch.ones_like(scar_delta), SCAR_CHANNEL, self.config.scar_margin_cap, competitor_channels=tuple(c for c in range(anchor_logits.shape[1]) if c != SCAR_CHANNEL))
        final_mask = final_logits.argmax(dim=1)
        scar_mask = final_mask == SCAR_CHANNEL
        edema_zone_mask = (final_mask == EDEMA_CHANNEL) | scar_mask
        pure_edema_mask = edema_zone_mask & ~scar_mask

        def z(v: torch.Tensor) -> torch.Tensor:
            return v * t2_mask

        edema_p_coarse_logit = z(edema0["p_coarse_logit"])
        edema_q_fn_logit = z(edema0["q_fn_logit"])
        edema_q_fp_logit = z(edema0["q_fp_logit"])
        edema_refined_logit = z(edema["refined_logit"])
        edema_utility_accept_logit = z(edema["utility_accept_logit"])
        edema_utility_regression = torch.tanh(z(torch.atanh(edema["utility_regression"].clamp(-0.999, 0.999)))) * t2_mask
        edema_p_coarse = torch.sigmoid(edema_p_coarse_logit) * t2_mask
        edema_q_fn = torch.sigmoid(edema_q_fn_logit) * t2_mask
        edema_q_fp = torch.sigmoid(edema_q_fp_logit) * t2_mask
        edema_p_refined = torch.sigmoid(edema_refined_logit) * t2_mask
        edema_utility_accept_prob = torch.sigmoid(edema_utility_accept_logit) * t2_mask

        return {
            "anchor_logits": anchor_logits,
            "shared_feature": scales[0],
            "after_edema_logits": after_edema,
            "final_logits": final_logits,
            "final_logits_after_scar_priority": final_logits,
            "final_mask": final_mask,
            "scar_mask": scar_mask,
            "edema_zone_mask": edema_zone_mask,
            "pure_edema_mask": pure_edema_mask,
            "scar_delta": scar_delta,
            "edema_delta": edema_delta,
            "scar_predicted_roi": scar_predicted_roi,
            "edema_predicted_roi": edema_predicted_roi,
            "scar_training_roi": scar_train_roi,
            "edema_training_roi": edema_train_roi,
            "teacher_roi_fraction": torch.as_tensor(float(teacher_roi_fraction), device=anchor_logits.device),
            "scar_support": scar_support,
            "edema_support": edema_zone_support,
            "t2_mask": t2_mask,
            "scar_anchor_margin": scar_anchor_margin,
            "edema_anchor_margin": edema_anchor_margin,
            "scar_p_coarse": scar0["p_coarse"],
            "scar_p_coarse_logit": scar0["p_coarse_logit"],
            "scar_q_fn": scar0["q_fn"],
            "scar_q_fp": scar0["q_fp"],
            "scar_q_fn_logit": scar0["q_fn_logit"],
            "scar_q_fp_logit": scar0["q_fp_logit"],
            "scar_p_refined": scar["p_refined"],
            "scar_refined_logit": scar["refined_logit"],
            "scar_utility_accept_logit": scar["utility_accept_logit"],
            "scar_utility_accept_prob": scar["utility_accept_prob"],
            "scar_utility_regression": scar["utility_regression"],
            "edema_p_coarse": edema_p_coarse,
            "edema_p_coarse_logit": edema_p_coarse_logit,
            "edema_q_fn": edema_q_fn,
            "edema_q_fp": edema_q_fp,
            "edema_q_fn_logit": edema_q_fn_logit,
            "edema_q_fp_logit": edema_q_fp_logit,
            "edema_p_refined": edema_p_refined,
            "edema_refined_logit": edema_refined_logit,
            "edema_utility_accept_logit": edema_utility_accept_logit,
            "edema_utility_accept_prob": edema_utility_accept_prob,
            "edema_utility_regression": edema_utility_regression,
        }


def build_care_dpr(config: dict[str, Any] | CAREDPRConfig | None = None) -> CAREDPR:
    if isinstance(config, CAREDPRConfig):
        cfg = config
    else:
        cfg = CAREDPRConfig(**(config or {}))
    return CAREDPR(cfg)
