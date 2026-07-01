"""Lane A Round10 edema-only residual refiner.

The module is intentionally small and baseline-preserving: it predicts only a
class_4 edema residual, and fusion copies every non-edema baseline label unless
the edema residual wins a conservative threshold. Class_5 scar is never changed.
"""

from __future__ import annotations

import torch
from torch import nn


EDEMA_CLASS = 4
SCAR_CLASS = 5


class ConservativeEdemaResidualRefiner(nn.Module):
    """Small 3D residual module for class_4 edema correction."""

    def __init__(self, in_channels: int, hidden_channels: int = 16, delta_max: float = 1.0) -> None:
        super().__init__()
        self.delta_max = float(delta_max)
        self.net = nn.Sequential(
            nn.Conv3d(in_channels, hidden_channels, kernel_size=3, padding=1),
            nn.InstanceNorm3d(hidden_channels, affine=True),
            nn.LeakyReLU(inplace=True),
            nn.Conv3d(hidden_channels, hidden_channels, kernel_size=3, padding=1),
            nn.InstanceNorm3d(hidden_channels, affine=True),
            nn.LeakyReLU(inplace=True),
            nn.Conv3d(hidden_channels, 1, kernel_size=1),
        )
        final = self.net[-1]
        if isinstance(final, nn.Conv3d):
            nn.init.zeros_(final.weight)
            nn.init.zeros_(final.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        delta = self.net(x)
        return torch.clamp(delta, min=-self.delta_max, max=self.delta_max)


class ConservativePathologyResidualRefiner(nn.Module):
    """Small 3D residual module for edema and scar correction.

    Channel 0 predicts an edema logit residual; channel 1 predicts a scar logit
    residual. Fusion remains conservative and class-protected in helper
    functions below.
    """

    def __init__(self, in_channels: int, hidden_channels: int = 16, delta_max: float = 1.0) -> None:
        super().__init__()
        self.delta_max = float(delta_max)
        self.net = nn.Sequential(
            nn.Conv3d(in_channels, hidden_channels, kernel_size=3, padding=1),
            nn.InstanceNorm3d(hidden_channels, affine=True),
            nn.LeakyReLU(inplace=True),
            nn.Conv3d(hidden_channels, hidden_channels, kernel_size=3, padding=1),
            nn.InstanceNorm3d(hidden_channels, affine=True),
            nn.LeakyReLU(inplace=True),
            nn.Conv3d(hidden_channels, 2, kernel_size=1),
        )
        final = self.net[-1]
        if isinstance(final, nn.Conv3d):
            nn.init.zeros_(final.weight)
            nn.init.zeros_(final.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        delta = self.net(x)
        return torch.clamp(delta, min=-self.delta_max, max=self.delta_max)


def prob_to_logit(prob: torch.Tensor, eps: float = 1e-4) -> torch.Tensor:
    """Convert probability to finite logit."""

    p = torch.clamp(prob, eps, 1.0 - eps)
    return torch.log(p / (1.0 - p))


def refined_edema_logit(baseline_edema_prob: torch.Tensor, delta_logit: torch.Tensor) -> torch.Tensor:
    """Return baseline edema logit plus predicted residual."""

    if baseline_edema_prob.ndim == delta_logit.ndim - 1:
        baseline_edema_prob = baseline_edema_prob[:, None]
    return prob_to_logit(baseline_edema_prob) + delta_logit


def refined_pathology_logits(baseline_probs: torch.Tensor, delta_logits: torch.Tensor) -> torch.Tensor:
    """Return edema/scar baseline logits plus residual logits."""

    if baseline_probs.ndim == delta_logits.ndim - 1:
        baseline_probs = baseline_probs[:, None]
    if baseline_probs.shape[1] != 2 or delta_logits.shape[1] != 2:
        raise ValueError(f"expected 2 pathology channels, got baseline={tuple(baseline_probs.shape)} delta={tuple(delta_logits.shape)}")
    return prob_to_logit(baseline_probs) + delta_logits


def fuse_edema_only_from_prob(
    baseline_seg: torch.Tensor,
    baseline_edema_prob: torch.Tensor,
    delta_logit: torch.Tensor,
    threshold: float = 0.5,
) -> torch.Tensor:
    """Fuse a class_4-only residual into a compact-label segmentation.

    Class_5 scar is protected by construction. Other baseline labels may only
    change to class_4 edema when the refined edema probability crosses the
    threshold.
    """

    logits = refined_edema_logit(baseline_edema_prob, delta_logit)
    if logits.ndim == baseline_seg.ndim + 1:
        edema_prob = torch.sigmoid(logits[:, 0])
    elif logits.ndim == baseline_seg.ndim:
        edema_prob = torch.sigmoid(logits)
    else:
        raise ValueError(f"shape mismatch: baseline={tuple(baseline_seg.shape)} logits={tuple(logits.shape)}")
    refined = baseline_seg.clone()
    edema_mask = (edema_prob >= threshold) & (baseline_seg != SCAR_CLASS)
    refined[edema_mask] = EDEMA_CLASS
    return refined


def fuse_pathology_from_probs(
    baseline_seg: torch.Tensor,
    baseline_pathology_probs: torch.Tensor,
    delta_logits: torch.Tensor,
    edema_threshold: float = 0.5,
    scar_threshold: float = 0.6,
) -> torch.Tensor:
    """Fuse conservative edema/scar residuals into compact-label segmentation."""

    logits = refined_pathology_logits(baseline_pathology_probs, delta_logits)
    edema_prob = torch.sigmoid(logits[:, 0])
    scar_prob = torch.sigmoid(logits[:, 1])
    refined = baseline_seg.clone()
    edema_mask = (edema_prob >= edema_threshold) & (baseline_seg != SCAR_CLASS)
    scar_mask = scar_prob >= scar_threshold
    refined[edema_mask] = EDEMA_CLASS
    refined[scar_mask] = SCAR_CLASS
    return refined


def assert_scar_unchanged(baseline_seg: torch.Tensor, refined_seg: torch.Tensor) -> int:
    """Return changed scar voxels and raise if shapes are incompatible."""

    if baseline_seg.shape != refined_seg.shape:
        raise ValueError(f"shape mismatch: baseline={tuple(baseline_seg.shape)} refined={tuple(refined_seg.shape)}")
    changed = ((baseline_seg == SCAR_CLASS) != (refined_seg == SCAR_CLASS)).sum()
    return int(changed.detach().cpu())
