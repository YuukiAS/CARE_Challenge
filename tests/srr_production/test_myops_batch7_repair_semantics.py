from __future__ import annotations

import torch
import pytest

from src.care_myocardium.models.srr_dictionary_memory import M10CrossFittedPrototypeMemory
from src.care_myocardium.models.srr_propref import ProposalDictionary, SRRProposeRefineMyoPS
from scripts.srr_production.infer_myops import load_memory_asset_fail_closed


def _seed_memory(memory: M10CrossFittedPrototypeMemory) -> None:
    for idx in range(8):
        case_id = f"Case{idx:04d}"
        features = torch.randn(4, memory.channels)
        memory.update("scar", "positive", "scar_positive", features + 1.0, case_id=case_id, t2_present=True)
        memory.update("scar", "negative", "normal_myocardium", features - 1.0, case_id=case_id, t2_present=True)


def test_repair_memory_query_policy_field_is_truthful() -> None:
    torch.manual_seed(7)
    memory = M10CrossFittedPrototypeMemory(6)
    _seed_memory(memory)
    features = torch.randn(1, 6, 3, 4, 4)
    validation = memory.query(
        features,
        pathology="scar",
        case_id="Case9999",
        require_ready=True,
        query_policy="validation_inference_all_train_shards",
    )
    training = memory.query(
        features,
        pathology="scar",
        case_id="Case9999",
        require_ready=True,
        query_policy="training_crossfit_exclude_query_shard",
    )
    assert bool(validation["production_crossfit_exclusive"].item()) is False
    assert bool(training["production_crossfit_exclusive"].item()) is True
    assert bool(validation["formal_real_memory_exclusive"].item()) is True


def test_proposal_dictionary_can_use_real_memory_exclusive_without_crossfit_claim() -> None:
    torch.manual_seed(8)
    dictionary = ProposalDictionary(6, pathology="scar")
    features = torch.randn(1, 6, 3, 4, 4)
    evidence = torch.randn(1, 1, 3, 4, 4)
    anatomy = torch.randn(1, 1, 3, 4, 4)
    memory_query = {
        "positive_similarity": torch.full((1, 1, 3, 4, 4), 0.5),
        "negative_similarity": torch.full((1, 1, 3, 4, 4), 0.25),
        "production_crossfit_exclusive": torch.tensor(False),
        "formal_real_memory_exclusive": torch.tensor(True),
    }
    out = dictionary(features, evidence, anatomy, memory_query=memory_query)
    assert torch.allclose(out["pos_similarity"], memory_query["positive_similarity"])
    assert torch.allclose(out["neg_similarity"], memory_query["negative_similarity"])


def test_semantic_memory_asset_missing_required_state_fails_closed(tmp_path) -> None:
    model = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="anchor_bounded_srr_correction")
    state = {
        key: value.detach().clone()
        for key, value in model.state_dict().items()
        if key.startswith("cross_fitted_memory.")
    }
    state.pop("cross_fitted_memory.positive_mu")
    asset_path = tmp_path / "missing_required_memory.pt"
    torch.save({"model_memory_state": state}, asset_path)

    with pytest.raises(ValueError, match="missing_required"):
        load_memory_asset_fail_closed(model, asset_path, torch.device("cpu"))


def test_semantic_memory_asset_invalid_state_fails_closed(tmp_path) -> None:
    model = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="anchor_bounded_srr_correction")
    state = {
        key: value.detach().clone()
        for key, value in model.state_dict().items()
        if key.startswith("cross_fitted_memory.")
    }
    state["not_memory_state"] = torch.tensor(1.0)
    state["cross_fitted_memory.negative_counts"] = "not-a-tensor"
    asset_path = tmp_path / "invalid_memory.pt"
    torch.save({"model_memory_state": state}, asset_path)

    with pytest.raises(ValueError, match="invalid_keys"):
        load_memory_asset_fail_closed(model, asset_path, torch.device("cpu"))
