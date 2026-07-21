from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import torch

from scripts.srr_production import infer_myops
from scripts.training import run_srr_propref_myops_fold0 as train_myops
from src.care_myocardium.losses.srr_losses import (
    final_pathology_loss_from_logits,
    production_gate_repair_preserve_loss,
    srr_m6_expanded_total_loss,
)
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS
from src.care_myocardium.srr_production.checkpoint import load_srr_checkpoint, save_srr_checkpoint


def _anchor(batch: int = 1, shape: tuple[int, int, int] = (4, 8, 8)) -> dict[str, torch.Tensor]:
    logits = torch.randn(batch, 6, *shape)
    return {"probabilities": torch.softmax(logits, dim=1)}


def _tiny_forward(mode: str = "full", *, t2: bool = True) -> dict[str, torch.Tensor]:
    torch.manual_seed(20260721)
    model = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="legacy_variant")
    x = torch.randn(1, 3, 4, 8, 8)
    availability = torch.tensor([[1.0, 1.0 if t2 else 0.0, 1.0]])
    return model(
        x,
        availability,
        anchor_features=_anchor(shape=(4, 8, 8)),
        production_intervention_mode=mode,
    )


def test_batch6_inference_mode_aliases_are_supported() -> None:
    assert infer_myops.BATCH5_PRODUCTION_INTERVENTIONS["full_gate_one"] == "gate_open_bounded_control"
    assert infer_myops.BATCH5_PRODUCTION_INTERVENTIONS["proposal_only_gate_one"] == "proposal_only_gate_one"
    assert infer_myops.normalized_mode("refiner_only_gate_one") == "anchor_bounded_refiner_only"


def test_batch6_production_gate_has_fixed_13_channel_contract() -> None:
    outputs = _tiny_forward()
    assert tuple(outputs["production_correction_gate_input"].shape[1:2]) == (13,)
    assert tuple(outputs["production_correction_gate_logits"].shape[1:2]) == (2,)
    assert len(outputs["production_correction_gate_input_channel_names"]) == 13
    assert outputs["production_correction_gate_input_channel_names"][4] == "anchor_scar_probability"
    assert outputs["production_correction_gate_input_channel_names"][12] == "anatomy_union_support"


def test_batch6_pure_interventions_do_not_consume_cross_component_inputs() -> None:
    proposal = _tiny_forward("proposal_only_gate_one")
    refiner = _tiny_forward("refiner_only_gate_one")
    assert proposal["production_correction_gate_component_sources"] == {"proposal_consumed": True, "refiner_consumed": False}
    assert refiner["production_correction_gate_component_sources"] == {"proposal_consumed": False, "refiner_consumed": True}
    assert torch.count_nonzero(proposal["production_correction_gate_input"][:, 2:4]).item() == 0
    assert torch.count_nonzero(refiner["production_correction_gate_input"][:, 0:2]).item() == 0
    assert torch.allclose(proposal["production_correction_gate"], torch.ones_like(proposal["production_correction_gate"]))
    assert torch.allclose(refiner["production_correction_gate"], torch.ones_like(refiner["production_correction_gate"]))


def test_final_pathology_loss_consumes_deployed_outputs_logits() -> None:
    logits = torch.randn(1, 6, 3, 4, 4, requires_grad=True)
    labels = torch.zeros(1, 3, 4, 4, dtype=torch.long)
    labels[:, :, 1:3, 1:3] = 5
    availability = torch.ones(1, 3)
    scar_loss, edema_loss = final_pathology_loss_from_logits(logits, labels, availability)
    (scar_loss + edema_loss).backward()
    assert logits.grad is not None
    assert float(logits.grad.abs().sum()) > 0.0


def test_no_t2_edema_final_and_gate_supervision_are_masked() -> None:
    outputs = _tiny_forward(t2=False)
    labels = torch.zeros(1, 4, 8, 8, dtype=torch.long)
    availability = torch.tensor([[1.0, 0.0, 1.0]])
    _scar_loss, edema_loss = final_pathology_loss_from_logits(outputs["logits"], labels, availability)
    assert float(edema_loss.detach()) == pytest.approx(0.0)
    gate_loss, _metrics = production_gate_repair_preserve_loss(outputs, labels, availability)
    changed = dict(outputs)
    changed["production_correction_gate_logits"] = outputs["production_correction_gate_logits"].clone()
    changed["production_correction_gate_logits"][:, 1] += 10.0
    changed_gate_loss, _changed_metrics = production_gate_repair_preserve_loss(changed, labels, availability)
    assert float(changed_gate_loss.detach()) == pytest.approx(float(gate_loss.detach()))


def test_batch6_canonical_weights_override_legacy_aliases() -> None:
    args = argparse.Namespace(
        variant_config_record={
            "variant_config": {
                "loss_weights": {"baseline_preservation": 0.75, "loss_correction_opportunity": 0.9},
                "canonical_loss_weights": {
                    "loss_anchor_preservation_outside_roi": 0.05,
                    "loss_correction_opportunity": 0.0,
                    "loss_final_scar_pathology": 1.0,
                },
            }
        },
        canonical_loss_weights={},
        loss_weight_json="",
        loss_weight=[],
        baseline_preservation_weight=0.6,
        scar_weight=None,
        edema_weight=None,
        proposal_weight=None,
        margin_weight=None,
        component_proposal_weight=None,
        semantic_retrieval_weight=None,
        semantic_integrative_weight=None,
        roi_weight=None,
        roi_remote_weight=None,
    )
    weights = train_myops.collect_expanded_loss_weights(args)
    assert weights["loss_anchor_preservation_outside_roi"] == pytest.approx(0.05)
    assert weights["loss_correction_opportunity"] == pytest.approx(0.0)
    assert weights["loss_final_scar_pathology"] == pytest.approx(1.0)


def test_batch6_checkpoint_migration_copies_old_gate_channels_and_zeroes_new(tmp_path: Path) -> None:
    torch.manual_seed(20260721)
    model = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="anchor_bounded_srr_correction")
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    ckpt = tmp_path / "checkpoint.pt"
    save_srr_checkpoint(
        path=ckpt,
        model=model,
        optimizer=optimizer,
        scheduler=None,
        amp_scaler=None,
        global_step=1800,
        epoch=0,
        final_output_mode="anchor_bounded_srr_correction",
        architecture_config={"variant": "unit"},
        oof_anchor_manifest_hash="anchor",
        prototype_memory_provenance={"source": "unit"},
        split_hash="split",
        source_commit="commit",
        best_metric_state={"role": "unit"},
        loss_weight_contract={"loss_final_scar_pathology": 1.0},
    )
    payload = torch.load(ckpt, map_location="cpu", weights_only=False)
    old_weight = payload["model_state_dict"]["production_correction_gate.weight"][:, :4].clone()
    payload["model_state_dict"]["production_correction_gate.weight"] = old_weight.clone()
    torch.save(payload, ckpt)

    reloaded = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="anchor_bounded_srr_correction")
    reloaded_opt = torch.optim.AdamW(reloaded.parameters(), lr=1e-4)
    loaded = load_srr_checkpoint(
        path=ckpt,
        model=reloaded,
        optimizer=reloaded_opt,
        scheduler=None,
        amp_scaler=None,
        restore_rng=False,
    )
    migrated = reloaded.state_dict()["production_correction_gate.weight"]
    assert loaded["production_gate_migration"]["applied"] is True
    assert torch.allclose(migrated[:, :4], old_weight)
    assert torch.count_nonzero(migrated[:, 4:]).item() == 0


def test_batch6_expanded_loss_exposes_new_components() -> None:
    outputs = _tiny_forward()
    labels = torch.zeros(1, 4, 8, 8, dtype=torch.long)
    labels[:, :, 2:4, 2:4] = 5
    availability = torch.ones(1, 3)
    weights = {
        "loss_final_scar_pathology": 1.0,
        "loss_final_edema_t2_present_pathology": 1.0,
        "loss_production_gate_repair_preserve": 0.2,
        "loss_correction_opportunity": 0.0,
        "loss_branch_arbitration_consistency": 0.0,
        "loss_bounded_correction": 0.0,
        "loss_refiner_final_label_effect": 0.0,
    }
    _total, metrics = srr_m6_expanded_total_loss(outputs, labels, availability, weights=weights, detach_metrics=False)
    for key in (
        "loss_final_scar_pathology",
        "loss_final_edema_t2_present_pathology",
        "loss_production_gate_repair_preserve",
        "repair_mask_voxels",
        "preserve_mask_voxels",
    ):
        assert key in metrics
