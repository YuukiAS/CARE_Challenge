from __future__ import annotations

import torch

from src.care_myocardium.cine.cinema_adapter import CineMAAdapter, dice_ce_loss
from src.care_myocardium.cine.registration_model import RegistrationUNet, local_ncc_loss, smoothness_loss, warp
from src.care_myocardium.cine.temporal_dictionary import TEMPORAL_SLOT_NAMES, TemporalSlotDictionary, temporal_load_loss
from src.care_myocardium.cine.temporal_model import CineTemporalModel


def test_cinema_adapter_has_gradient_to_adapter_and_head() -> None:
    model = CineMAAdapter()
    image = torch.randn(2, 1, 8, 16, 16)
    prior = torch.randn(2, 1, 8, 16, 16)
    target = torch.randint(0, 4, (2, 8, 16, 16))
    loss = dice_ce_loss(model(image, prior), target)
    loss.backward()
    assert model.adapter[0].weight.grad is not None
    assert float(model.adapter[0].weight.grad.abs().sum()) > 0
    assert float(model.head.weight.grad.abs().sum()) > 0


def test_registration_model_predicts_warpable_velocity() -> None:
    model = RegistrationUNet(channels=(4, 8, 16, 32))
    fixed = torch.randn(1, 1, 8, 16, 16)
    moving = torch.randn(1, 1, 8, 16, 16)
    velocity = model(fixed, moving)
    warped = warp(moving, velocity)
    loss = local_ncc_loss(fixed, warped) + 0.05 * smoothness_loss(velocity)
    loss.backward()
    assert velocity.shape == (1, 3, 8, 16, 16)
    assert model.velocity.weight.grad is not None
    assert torch.isfinite(warped).all()


def test_temporal_dictionary_uses_exact_eight_slots_and_qc_mask() -> None:
    assert len(TEMPORAL_SLOT_NAMES) == 8
    model = TemporalSlotDictionary(in_channels=5, hidden_channels=8, slot_count=8)
    z = torch.randn(1, 4, 5, 8, 16, 16)
    valid = torch.tensor([[True, True, False, True]])
    temporal, beta = model(z, valid_frame_mask=valid)
    loss = temporal.square().mean() + temporal_load_loss(beta)
    loss.backward()
    assert temporal.shape == (1, 8, 8, 16, 16)
    assert beta.shape == (1, 4, 8, 8, 16, 16)
    assert float(beta[:, 2].max()) < 1e-3


def test_cine_temporal_model_changes_final_logits_from_temporal_evidence() -> None:
    model = CineTemporalModel(hidden_channels=8)
    ed_image = torch.randn(1, 1, 8, 16, 16)
    ed_prior = torch.randn(1, 1, 8, 16, 16)
    z1 = torch.randn(1, 4, 5, 8, 16, 16)
    z2 = z1.clone()
    z2[:, 1] = z2[:, 1] + 1.0
    valid = torch.ones(1, 4, dtype=torch.bool)
    logits1, _ = model(ed_image, ed_prior, z1, valid_frame_mask=valid)
    logits2, _ = model(ed_image, ed_prior, z2, valid_frame_mask=valid)
    assert logits1.shape == (1, 4, 8, 16, 16)
    assert float((logits1 - logits2).abs().mean()) > 1e-5
