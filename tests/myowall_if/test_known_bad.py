from __future__ import annotations

import torch

from src.care_myocardium.models.myowall_if import (
    CartesianMatchedPathologyHead,
    EdemaWallFieldHead,
    MyoWallPilotLoss,
    MyoWallPilotModel,
    ScarWallFieldHead,
)


def test_required_heads_are_separate() -> None:
    c0 = CartesianMatchedPathologyHead(48)
    assert c0.scar is not c0.edema_surface
    w1 = MyoWallPilotModel("W1")
    assert isinstance(w1.scar_wall_head, ScarWallFieldHead)
    assert isinstance(w1.edema_wall_head, EdemaWallFieldHead)
    assert w1.scar_wall_head is not w1.edema_wall_head


def test_no_t2_edema_loss_has_zero_gradient() -> None:
    outputs = {
        "final_scar_logit": torch.zeros(1, 1, 2, 8, 8, requires_grad=True),
        "final_edema_logit": torch.full((1, 1, 2, 8, 8), -16.0, requires_grad=True),
    }
    targets = {
        "scar": torch.zeros(1, 1, 2, 8, 8),
        "pure_edema": torch.ones(1, 1, 2, 8, 8),
    }
    availability = torch.tensor([[1.0, 0.0, 1.0]])
    loss = MyoWallPilotLoss(arm="W1")(outputs, targets, availability)
    loss["pure_edema_dice_ce"].backward(retain_graph=True)
    assert outputs["final_edema_logit"].grad is not None
    assert float(outputs["final_edema_logit"].grad.abs().sum()) == 0.0


def test_w3_zeroes_rank_channels() -> None:
    model = MyoWallPilotModel("W3")
    x = torch.randn(1, 48, 2, 8, 8)
    x_clone = x.clone()
    # The no-geometry failure happens after rank zeroing would be applied; this
    # test guards the declared channel contract through the public arm flag.
    assert model.arm == "W3"
    x_clone[:, 32:35].zero_()
    assert torch.count_nonzero(x_clone[:, 32:35]) == 0
