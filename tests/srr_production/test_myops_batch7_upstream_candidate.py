from __future__ import annotations

import torch

from src.care_myocardium.models.srr_dictionary_memory import deterministic_memory_shard
from src.care_myocardium.models.srr_propref import (
    DifferentiableSoftROIRefinementHead,
    PathologySourceArbiter,
    SRRProposeRefineMyoPS,
)


def _anchor(batch: int, shape: tuple[int, int, int]) -> dict[str, torch.Tensor]:
    logits = torch.zeros((batch, 6, *shape), dtype=torch.float32)
    logits[:, 1] = 2.0
    return {"logits": logits, "probabilities": torch.softmax(logits, dim=1)}


def _component(batch: int, shape: tuple[int, int, int]) -> dict[str, torch.Tensor]:
    zero = torch.zeros((batch, 1, *shape), dtype=torch.float32)
    return {"scar_component": zero, "edema_component": zero}


def _seed_memory(model: SRRProposeRefineMyoPS) -> None:
    channels = model.feature_channels
    for idx in range(8):
        case_id = f"Proto{idx:04d}"
        features = torch.randn(6, channels)
        model.cross_fitted_memory.update("scar", "positive", "positive_scar", features + 1.0, case_id=case_id, t2_present=True)
        model.cross_fitted_memory.update("scar", "negative", "normal_myocardium", features - 1.0, case_id=case_id, t2_present=True)
        model.cross_fitted_memory.update("edema", "positive", "positive_edema", features + 0.5, case_id=case_id, t2_present=True)
        model.cross_fitted_memory.update("edema", "negative", "normal_myocardium", features - 0.5, case_id=case_id, t2_present=True)
    assert {deterministic_memory_shard(f"Proto{idx:04d}") for idx in range(8)}


def test_batch7_uses_differentiable_refiner_and_source_arbiter() -> None:
    model = SRRProposeRefineMyoPS(
        variant="m10_d3_hierarchical_memory_propref",
        encoder_profile="safe_4scale",
        base_channels=4,
        final_output_mode="anchor_bounded_srr_correction",
    )
    assert isinstance(model.scar_refine, DifferentiableSoftROIRefinementHead)
    assert isinstance(model.edema_refine, DifferentiableSoftROIRefinementHead)
    assert isinstance(model.scar_source_arbiter, PathologySourceArbiter)
    assert isinstance(model.edema_source_arbiter, PathologySourceArbiter)


def test_batch7_forward_source_weights_and_no_t2_zero_chain() -> None:
    torch.manual_seed(7)
    model = SRRProposeRefineMyoPS(
        variant="m10_d3_hierarchical_memory_propref",
        encoder_profile="safe_4scale",
        base_channels=4,
        final_output_mode="anchor_bounded_srr_correction",
    )
    _seed_memory(model)
    model.eval()
    x = torch.randn(2, 3, 8, 16, 16)
    availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
    anchor = _anchor(2, (8, 16, 16))
    component = _component(2, (8, 16, 16))
    with torch.no_grad():
        out = model(
            x,
            availability,
            anchor_features=anchor,
            component_features=component,
            memory_query_policy="validation_inference_all_train_shards",
            case_ids=["Case2002", "Case1002"],
        )
    scar_sum = out["scar_proposal_source_weight"] + out["scar_refiner_source_weight"]
    edema_sum = out["edema_proposal_source_weight"] + out["edema_refiner_source_weight"]
    assert torch.allclose(scar_sum, torch.ones_like(scar_sum), atol=1e-6)
    assert torch.allclose(edema_sum, torch.ones_like(edema_sum), atol=1e-6)
    assert float(out["edema_soft_roi"][1].abs().max()) == 0.0
    assert float(out["edema_refinement_residual"][1].abs().max()) == 0.0
    assert float(out["bounded_edema_correction"][1].abs().max()) == 0.0
    assert float(out["scar_discovery_logits"].abs().max()) > 0.0
    assert "m10_prototype_maps" in out
