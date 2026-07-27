from __future__ import annotations

from pathlib import Path

import torch

from src.care_myocardium.data.care_dg_dataset import validate_care_dg_batch
from src.care_myocardium.models.care_dg import build_care_dg
from src.care_myocardium.training.care_dg_trainer import (
    care_dg_loss,
    load_care_dg_checkpoint,
    make_error_targets,
    save_care_dg_checkpoint,
)


def _batch(batch: int = 2, t2: tuple[float, ...] = (1.0, 1.0)) -> dict[str, torch.Tensor]:
    torch.manual_seed(7)
    images = torch.randn(batch, 3, 4, 16, 16)
    anchor = torch.randn(batch, 6, 4, 16, 16)
    labels = anchor.argmax(dim=1)
    labels[:, 1:2, 5:8, 5:8] = 5
    labels[:, 2:3, 8:11, 8:11] = 4
    availability = torch.tensor([[1.0, float(t2[i]), 1.0] for i in range(batch)])
    return {
        "images": images,
        "anchor_logits": anchor,
        "availability": availability,
        "labels": labels,
        "anchor_mask": anchor.argmax(dim=1),
        "t2_present": availability[:, 1],
        "myocardium_support": torch.ones(batch, 1, 4, 16, 16),
        "edema_support": torch.ones(batch, 1, 4, 16, 16),
    }


def test_forward_shapes_and_nonconstant_gates() -> None:
    batch = _batch()
    validate_care_dg_batch(batch)
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    out = model(batch["images"], batch["availability"], batch["anchor_logits"])
    assert out["final_logits"].shape == batch["anchor_logits"].shape
    assert out["scar_q_fn"].std() > 0
    assert out["edema_q_fp"].std() > 0


def test_zero_correction_exact_anchor_identity() -> None:
    batch = _batch()
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    out = model(batch["images"], batch["availability"], batch["anchor_logits"], force_zero_correction=True)
    torch.testing.assert_close(out["final_logits"], batch["anchor_logits"])


def test_competitive_intervention_changes_argmax() -> None:
    batch = _batch(batch=1, t2=(1.0,))
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4, "scar_margin_cap": 8.0})
    with torch.no_grad():
        model.scar_decoder.head.bias[0] = 12.0
        model.scar_decoder.head.bias[1] = -12.0
        model.scar_decoder.head.bias[2] = 12.0
        model.scar_decoder.head.bias[3] = -12.0
    out = model(batch["images"], batch["availability"], batch["anchor_logits"])
    assert torch.count_nonzero(out["final_mask"] != batch["anchor_mask"]) > 0


def test_no_t2_edema_decoder_gradient_zero() -> None:
    batch = _batch(batch=1, t2=(0.0,))
    batch["labels"].fill_(0)
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    out = model(batch["images"], batch["availability"], batch["anchor_logits"])
    loss, _ = care_dg_loss(out, batch["labels"], batch["anchor_mask"], t2_present=batch["t2_present"])
    loss.backward()
    for param in model.edema_decoder.parameters():
        if param.grad is not None:
            assert torch.count_nonzero(param.grad) == 0


def test_error_target_construction() -> None:
    labels = torch.tensor([[[[5, 0], [0, 0]]]])
    anchor = torch.tensor([[[[0, 5], [0, 0]]]])
    target = make_error_targets(labels, anchor, 5)
    assert target["fn"][0, 0, 0, 0, 0] == 1
    assert target["fp"][0, 0, 0, 0, 1] == 1


def test_checkpoint_reload_exact(tmp_path: Path) -> None:
    batch = _batch(batch=1, t2=(1.0,))
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    before = model(batch["images"], batch["availability"], batch["anchor_logits"])["final_logits"]
    ckpt = tmp_path / "care_dg.pt"
    save_care_dg_checkpoint(ckpt, model, opt, step=3)
    loaded, step, _ = load_care_dg_checkpoint(ckpt)
    after = loaded(batch["images"], batch["availability"], batch["anchor_logits"])["final_logits"]
    assert step == 3
    torch.testing.assert_close(before, after)


def test_aligned_crop_preserves_image_label_error_map_coordinates() -> None:
    from src.care_myocardium.data.care_dg_dataset import aligned_spatial_crop

    batch = _batch(batch=1, t2=(1.0,))
    batch["fn_error_map"] = torch.zeros(1, 1, 4, 16, 16)
    batch["images"].zero_()
    batch["labels"].zero_()
    batch["anchor_mask"].zero_()
    batch["images"][0, 0, 2, 9, 10] = 5.0
    batch["labels"][0, 2, 9, 10] = 5
    batch["anchor_mask"][0, 2, 9, 10] = 0
    batch["fn_error_map"][0, 0, 2, 9, 10] = 1.0
    cropped = aligned_spatial_crop(batch, (1, 5, 6), (2, 8, 8))
    assert cropped["images"][0, 0, 1, 4, 4] == 5.0
    assert cropped["labels"][0, 1, 4, 4] == 5
    assert cropped["fn_error_map"][0, 0, 1, 4, 4] == 1.0
