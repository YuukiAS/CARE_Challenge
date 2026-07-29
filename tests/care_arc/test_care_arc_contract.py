from __future__ import annotations

import torch

from src.care_myocardium.models.care_arc import build_care_arc, trainable_parameter_count
from src.care_myocardium.training.care_arc_trainer import care_arc_loss


def test_care_arc_parameter_count_and_single_encoder() -> None:
    model = build_care_arc()
    assert 20_000_000 <= trainable_parameter_count(model) <= 45_000_000
    assert model.shared_encoder_count == 1


def test_external_context_does_not_change_pathology_outputs() -> None:
    torch.manual_seed(1)
    model = build_care_arc().eval()
    images = torch.randn(1, 3, 2, 64, 64)
    availability = torch.tensor([[1.0, 1.0, 1.0]])
    with torch.no_grad():
        out_a = model(images, availability, external_nnunet_context={"prob": torch.randn(1, 6, 2, 64, 64)})
        out_b = model(images, availability, external_nnunet_context={"prob": torch.randn(1, 6, 2, 64, 64) * 11.0})
    assert torch.equal(out_a["scar_direct_logit"], out_b["scar_direct_logit"])
    assert torch.equal(out_a["edema_zone_direct_logit"], out_b["edema_zone_direct_logit"])


def test_no_t2_edema_outputs_and_branch_gradients_are_zero() -> None:
    torch.manual_seed(2)
    model = build_care_arc()
    images = torch.randn(1, 3, 2, 64, 64)
    availability = torch.tensor([[1.0, 0.0, 1.0]])
    out = model(images, availability)
    assert float(out["edema_zone_direct_logit"].abs().max()) == 0.0
    assert float(out["edema"]["coarse_extent_logit"].abs().max()) == 0.0
    batch = {
        "scar_target": torch.zeros(1, 1, 2, 64, 64),
        "edema_zone_target": torch.ones(1, 1, 2, 64, 64),
        "myocardium_target": torch.ones(1, 1, 2, 64, 64),
        "spacing_zyx": torch.ones(1, 3),
        "t2_present": torch.zeros(1, 1),
        "anatomy_target": torch.zeros(1, 2, 64, 64, dtype=torch.long),
    }
    loss, metrics = care_arc_loss(out, batch)
    assert metrics["edema_active"] == 0.0
    loss.backward()
    grads = [p.grad for p in model.edema_decoder.parameters() if p.grad is not None]
    assert grads
    assert all(float(g.abs().max()) == 0.0 for g in grads)


def test_burden_film_changes_direct_logits() -> None:
    torch.manual_seed(3)
    model = build_care_arc().eval()
    images = torch.randn(1, 3, 2, 64, 64)
    availability = torch.tensor([[1.0, 1.0, 1.0]])
    with torch.no_grad():
        out = model(images, availability)
        pre = model.scar_decoder.direct_head(out["scar"]["pre_film_features"])
    assert float((pre - out["scar_direct_logit"]).abs().max()) > 0.0


def test_missing_modality_gate_weights_are_exact_zero() -> None:
    torch.manual_seed(4)
    model = build_care_arc().eval()
    images = torch.randn(1, 3, 2, 64, 64)
    availability = torch.tensor([[1.0, 0.0, 1.0]])
    with torch.no_grad():
        out = model(images, availability)
    for weights in out["scar_gate_weights"]:
        assert float(weights[:, 1].abs().max()) == 0.0
        assert torch.allclose(weights.sum(dim=1), torch.ones(1), atol=1e-6)
