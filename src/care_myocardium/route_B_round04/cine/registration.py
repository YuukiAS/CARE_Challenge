"""Route B Round04 Cine registration helpers."""

from __future__ import annotations

import torch

from src.care_myocardium.route_B_round03.registration import (
    RouteBRound03SVFRegistration,
    integrate_velocity,
    jacobian_receipt,
    warp,
)


class RouteBRound04CineRegistration(RouteBRound03SVFRegistration):
    """Seven-step stationary-velocity registration used for B8 evidence."""

    def __init__(self, hidden: int = 16) -> None:
        super().__init__(hidden=hidden)
        self.integration_steps = 7


def true_jacobian_summary(displacement: torch.Tensor) -> dict[str, float | bool | str]:
    """Return a finite-difference Jacobian receipt, not an intensity proxy."""

    jac = jacobian_receipt(displacement)
    return {
        "source": "finite_difference_displacement_gradient",
        "proxy_jacobian": False,
        "minimum_jacobian": float(jac["minimum_jacobian"].detach().cpu()),
        "folding_rate": float(jac["folding_rate"].detach().cpu()),
    }


__all__ = [
    "RouteBRound04CineRegistration",
    "integrate_velocity",
    "jacobian_receipt",
    "true_jacobian_summary",
    "warp",
]
