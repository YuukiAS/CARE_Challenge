from __future__ import annotations

import torch

from src.care_myocardium.losses.care_mm_losses import (
    ReliableMaskBatch,
    compute_care_mm_loss,
)
from src.care_myocardium.models.care_mm_reliable_distill import (
    CAREMMReliableDistillResEnc,
    ResEncMConfig,
    final_margin_logits,
)


def small_model() -> CAREMMReliableDistillResEnc:
    return CAREMMReliableDistillResEnc(
        ResEncMConfig(
            feature_channels=8,
            n_stages=3,
            features_per_stage=(8, 16, 32),
            kernel_sizes=((3, 3, 3), (3, 3, 3), (3, 3, 3)),
            strides=((1, 1, 1), (1, 2, 2), (2, 2, 2)),
            n_blocks_per_stage=(1, 1, 1),
            n_conv_per_stage_decoder=(1, 1),
        )
    )


def test_availability_masks_missing_stem_exactly_zero() -> None:
    model = small_model()
    x = torch.randn(2, 3, 8, 16, 16)
    availability = torch.tensor([[1, 0, 1], [1, 1, 0]], dtype=torch.float32)
    out = model(x, availability)
    assert out["stem_t2"][0].abs().max().item() == 0.0
    assert out["stem_c0"][1].abs().max().item() == 0.0
    assert out["six_class_logits"].shape == (2, 6, 8, 16, 16)


def test_no_t2_edema_logit_forced_to_contract_value() -> None:
    model = small_model()
    x = torch.randn(1, 3, 8, 16, 16)
    out = model(x, torch.tensor([[1, 0, 1]], dtype=torch.float32))
    assert torch.all(out["six_class_logits"][:, 4] == -20.0)


def test_pathology_margins_are_final_logit_one_vs_rest() -> None:
    six = torch.randn(1, 6, 2, 2, 2)
    margins = final_margin_logits(six)
    expected_scar = six[:, 5:6] - torch.logsumexp(six[:, 0:5], dim=1, keepdim=True)
    expected_edema = six[:, 4:5] - torch.logsumexp(torch.cat([six[:, 0:4], six[:, 5:6]], dim=1), dim=1, keepdim=True)
    assert torch.allclose(margins["scar"], expected_scar)
    assert torch.allclose(margins["edema"], expected_edema)


def test_nonzero_losses_enter_total_and_backward() -> None:
    model = small_model()
    x = torch.randn(2, 3, 8, 16, 16)
    availability = torch.tensor([[1, 1, 1], [1, 0, 0]], dtype=torch.float32)
    seg = torch.zeros(2, 8, 16, 16, dtype=torch.long)
    seg[0, :, 4:8, 4:8] = 4
    seg[0, :, 8:12, 8:12] = 5
    seg[1, :, 5:10, 5:10] = 5
    out = model(x, availability)
    masks = ReliableMaskBatch(
        anatomy=torch.tensor([True, True]),
        scar=torch.tensor([True, True]),
        edema=torch.tensor([True, False]),
        final_six_class=torch.tensor([True, False]),
        natural_complete_trimodal=torch.tensor([True, False]),
    )
    weights = {
        "loss_anatomy_ce_dice": 1.0,
        "loss_scar_final_margin_bce_dice": 1.0,
        "loss_edema_final_margin_bce_dice_reliable_only": 1.0,
        "loss_final_six_class_reliable": 0.5,
    }
    loss, terms = compute_care_mm_loss(out, seg, masks, weights)
    assert terms["loss_edema_final_margin_bce_dice_reliable_only"].requires_grad
    loss.backward()
    grad_sum = sum(float(p.grad.abs().sum()) for p in model.parameters() if p.grad is not None)
    assert grad_sum > 0
