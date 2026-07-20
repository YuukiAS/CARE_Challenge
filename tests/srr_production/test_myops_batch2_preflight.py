from __future__ import annotations

from pathlib import Path

import torch

from scripts.training.run_srr_propref_myops_fold0 import (
    anchor_dict_from_tensor,
    component_dict_from_tensor,
    safety_context_dicts_from_raw,
)
from src.care_myocardium.models.srr_dictionary_memory import deterministic_memory_shard
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS
from src.care_myocardium.srr_production.checkpoint import load_srr_checkpoint, save_srr_checkpoint


def test_memory_query_policy_training_vs_inference_shards() -> None:
    model = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="srr_no_anchor_control")
    features = torch.randn(1, model.feature_channels, 2, 4, 4)
    for shard in range(4):
        model.cross_fitted_memory.positive_counts[0, shard, 0] = 1
        model.cross_fitted_memory.negative_counts[0, shard, 0] = 1
        model.cross_fitted_memory.positive_mu[0, shard, 0].normal_()
        model.cross_fitted_memory.negative_mu[0, shard, 0].normal_()
    case_id = "Case1002"
    query_shard = deterministic_memory_shard(case_id)
    train_query = model.cross_fitted_memory.query(
        features,
        pathology="scar",
        case_id=case_id,
        require_ready=True,
        query_policy="training_crossfit_exclude_query_shard",
    )
    infer_query = model.cross_fitted_memory.query(
        features,
        pathology="scar",
        case_id=case_id,
        require_ready=True,
        query_policy="validation_inference_all_train_shards",
    )
    assert int(train_query["query_shard"]) == query_shard
    assert query_shard not in {int(v) for v in train_query["source_shards"].tolist()}
    assert {int(v) for v in infer_query["source_shards"].tolist()} == {0, 1, 2, 3}


def test_raw_anchor_and_safety_context_are_separate_in_forward() -> None:
    model = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="srr_no_anchor_control")
    x = torch.randn(1, 3, 2, 8, 8)
    availability = torch.tensor([[1.0, 0.0, 1.0]])
    raw_anchor = torch.zeros(1, 6, 2, 8, 8)
    raw_anchor[:, 0] = 0.9
    raw_anchor[:, 4] = 0.8
    raw_anchor[:, 5] = 0.1
    raw_anchor = raw_anchor / raw_anchor.sum(dim=1, keepdim=True).clamp_min(1e-6)
    raw_component = torch.zeros(1, 2, 2, 8, 8)
    raw_component[:, 1] = 1.0
    anchor = anchor_dict_from_tensor(raw_anchor)
    component = component_dict_from_tensor(raw_component)
    safety_anchor, safety_component = safety_context_dicts_from_raw(anchor, component, availability)

    assert float(anchor["probabilities"][:, 4].max()) > 0.0
    assert float(safety_anchor["probabilities"][:, 4].max()) == 0.0
    assert float(safety_component["edema_component"].max()) == 0.0

    with torch.no_grad():
        out = model(
            x,
            availability,
            anchor_features=anchor,
            component_features=component,
            safety_anchor_features=safety_anchor,
            safety_component_features=safety_component,
            case_ids=["Case1002"],
            anchor_identity_control=True,
        )
    assert bool(out["raw_anchor_used_for_final_baseline"].item())
    assert bool(out["safety_context_used_for_srr_evidence"].item())
    assert float(out["edema_candidate_probability"].max()) == 0.0
    assert float(out["bounded_edema_correction"].abs().max()) == 0.0


def test_schema_v2_checkpoint_loads_model_memory_and_optimizer(tmp_path: Path) -> None:
    model = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="anchor_bounded_srr_correction")
    with torch.no_grad():
        model.cross_fitted_memory.positive_counts[0, 0, 0] = 1
        model.cross_fitted_memory.negative_counts[0, 0, 0] = 1
        model.cross_fitted_memory.positive_mu[0, 0, 0].fill_(0.25)
        model.cross_fitted_memory.negative_mu[0, 0, 0].fill_(-0.25)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    ckpt = tmp_path / "srr_schema_v2.pth"
    save_srr_checkpoint(
        path=ckpt,
        model=model,
        optimizer=optimizer,
        scheduler=None,
        amp_scaler=None,
        global_step=0,
        epoch=0,
        final_output_mode="anchor_bounded_srr_correction",
        architecture_config={"class_name": "SRRProposeRefineMyoPS", "base_channels": 2},
        oof_anchor_manifest_hash="anchor-hash",
        prototype_memory_provenance={"source": "unit_frozen_fold0_train_memory"},
        split_hash="split-hash",
        source_commit="unit",
        best_metric_state={"status": "ZERO_STEP_DIAGNOSTIC_NO_TRAINING"},
    )
    reloaded = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="anchor_bounded_srr_correction")
    opt_reloaded = torch.optim.AdamW(reloaded.parameters(), lr=9e-3)
    payload = load_srr_checkpoint(
        path=ckpt,
        model=reloaded,
        optimizer=opt_reloaded,
        scheduler=None,
        amp_scaler=None,
        restore_rng=False,
    )
    assert payload["schema_version"] == 2
    assert int(payload["global_step"]) == 0
    assert int(reloaded.cross_fitted_memory.positive_counts[0, 0, 0]) == 1
    assert float(reloaded.cross_fitted_memory.positive_mu[0, 0, 0, 0]) == 0.25
