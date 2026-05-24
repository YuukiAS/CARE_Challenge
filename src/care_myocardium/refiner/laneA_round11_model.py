"""Lane A Round11 component-safe bidirectional edema refiner."""

from __future__ import annotations

import torch
from torch import nn

from src.care_myocardium.refiner.laneA_round10_model import EDEMA_CLASS, SCAR_CLASS, prob_to_logit


class BidirectionalEdemaResidualRefiner(nn.Module):
    """Small add/remove residual module for class_4 edema only.

    The final convolution is zero-initialized, so the initial refined edema
    logit exactly matches the baseline edema logit. Fusion protects class_5
    scar and limits additions/removals to explicit support masks.
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
        return torch.clamp(self.net(x), min=-self.delta_max, max=self.delta_max)


def split_add_remove_delta(delta: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    if delta.shape[1] != 2:
        raise ValueError(f"expected two residual channels, got {tuple(delta.shape)}")
    return delta[:, 0:1], delta[:, 1:2]


def bidirectional_edema_logit(baseline_edema_prob: torch.Tensor, delta: torch.Tensor) -> torch.Tensor:
    if baseline_edema_prob.ndim == delta.ndim - 1:
        baseline_edema_prob = baseline_edema_prob[:, None]
    add_delta, remove_delta = split_add_remove_delta(delta)
    return prob_to_logit(baseline_edema_prob) + add_delta - remove_delta


def fuse_component_safe_bidirectional(
    baseline_seg: torch.Tensor,
    baseline_edema_prob: torch.Tensor,
    delta: torch.Tensor,
    anatomy_support: torch.Tensor,
    *,
    t2_present: bool | torch.Tensor,
    threshold: float = 0.5,
    add_prob_threshold: float = 0.5,
    remove_prob_threshold: float = 0.45,
    baseline_prob_min_for_add: float = 0.05,
    anatomy_min_for_add: float = 0.05,
) -> torch.Tensor:
    """Fuse a bidirectional class_4-only residual into baseline labels.

    Additions are disabled for no-T2 cases. Removals are only allowed from
    baseline class_4 edema voxels. Scar voxels are immutable.
    """

    if baseline_edema_prob.ndim == baseline_seg.ndim:
        baseline_edema_prob = baseline_edema_prob[:, None]
    if anatomy_support.ndim == baseline_seg.ndim:
        anatomy_support = anatomy_support[:, None]
    logits = bidirectional_edema_logit(baseline_edema_prob, delta)
    edema_prob = torch.sigmoid(logits[:, 0])
    baseline_edema_prob_3d = baseline_edema_prob[:, 0]
    anatomy_support_3d = anatomy_support[:, 0]

    if isinstance(t2_present, torch.Tensor):
        t2_gate = t2_present.to(dtype=torch.bool, device=baseline_seg.device)
        while t2_gate.ndim < baseline_seg.ndim:
            t2_gate = t2_gate[..., None]
    else:
        t2_gate = torch.as_tensor(t2_present, dtype=torch.bool, device=baseline_seg.device)

    refined = baseline_seg.clone()
    scar_mask = baseline_seg == SCAR_CLASS
    baseline_edema = baseline_seg == EDEMA_CLASS
    add_mask = (
        (edema_prob >= add_prob_threshold)
        & (~baseline_edema)
        & (~scar_mask)
        & (baseline_edema_prob_3d >= baseline_prob_min_for_add)
        & (anatomy_support_3d >= anatomy_min_for_add)
        & t2_gate
    )
    remove_mask = baseline_edema & (~scar_mask) & (edema_prob < remove_prob_threshold)
    refined[add_mask] = EDEMA_CLASS
    refined[remove_mask] = 0
    return refined


def assert_scar_unchanged(baseline_seg: torch.Tensor, refined_seg: torch.Tensor) -> int:
    if baseline_seg.shape != refined_seg.shape:
        raise ValueError(f"shape mismatch: baseline={tuple(baseline_seg.shape)} refined={tuple(refined_seg.shape)}")
    changed = ((baseline_seg == SCAR_CLASS) != (refined_seg == SCAR_CLASS)).sum()
    return int(changed.detach().cpu())
