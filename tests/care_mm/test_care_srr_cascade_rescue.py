from __future__ import annotations

import ast
from pathlib import Path

import torch

from src.care_myocardium.losses.care_srr_cascade_rescue_losses import (
    care_srr_cascade_rescue_loss_terms,
    confident_anchor_preserve,
)
from src.care_myocardium.models.care_srr_cascade_rescue import (
    CARESRRCascadeRescue,
    fixed_support_map,
    soft_union_probability,
)
from src.care_myocardium.srr_production.case_prototypes import (
    build_case_prototype_record,
    select_crossfit_prototype_bank,
)


def _inputs(batch: int = 2) -> dict[str, torch.Tensor]:
    torch.manual_seed(7)
    anchor_logits = torch.randn(batch, 6, 3, 5, 4)
    source_features = torch.randn(batch, 8, 3, 5, 4)
    distance_to_union_mm = torch.linspace(0.0, 20.0, steps=batch * 3 * 5 * 4).view(batch, 1, 3, 5, 4)
    t2_present = torch.tensor([1.0, 0.0])[:batch]
    anchor_probs = torch.softmax(anchor_logits, dim=1)
    return {
        "anchor_logits": anchor_logits,
        "source_features": source_features,
        "distance_to_union_mm": distance_to_union_mm,
        "t2_present": t2_present,
        "normalized_lge": torch.randn(batch, 1, 3, 5, 4),
        "normalized_t2": torch.randn(batch, 1, 3, 5, 4),
        "teacher_anatomy_probabilities": torch.softmax(torch.randn(batch, 4, 3, 5, 4), dim=1),
        "teacher_edema_probability": torch.sigmoid(torch.randn(batch, 1, 3, 5, 4)),
        "scar_source_margin": torch.randn(batch, 1, 3, 5, 4),
        "explicit_anchor_probabilities": anchor_probs,
        "explicit_anchor_uncertainty": torch.rand(batch, 1, 3, 5, 4),
        "explicit_soft_union_probability": soft_union_probability(anchor_probs),
        "normalized_distance_to_union": (distance_to_union_mm / 15.0).clamp(0.0, 1.0),
        "prototype_scar_positive_similarity": torch.randn(batch, 1, 3, 5, 4),
        "prototype_scar_negative_similarity": torch.randn(batch, 1, 3, 5, 4),
        "prototype_edema_positive_similarity": torch.randn(batch, 1, 3, 5, 4),
        "prototype_edema_negative_similarity": torch.randn(batch, 1, 3, 5, 4),
    }


def test_import_and_zero_initialized_identity() -> None:
    model = CARESRRCascadeRescue(source_feature_channels=8)
    assert model.hidden_channels == 32
    assert model.groupnorm_groups == 8
    assert model.residual_block_count == 2
    assert torch.count_nonzero(model.scar_output_projection.weight).item() == 0
    assert torch.count_nonzero(model.scar_output_projection.bias).item() == 0
    assert torch.count_nonzero(model.edema_output_projection.weight).item() == 0
    assert torch.count_nonzero(model.edema_output_projection.bias).item() == 0

    inputs = _inputs()
    out = model(**inputs)
    assert torch.allclose(out["final_logits"], inputs["anchor_logits"], atol=0.0, rtol=0.0)


def test_anatomy_identity_and_no_t2_edema_identity_with_nonzero_deltas() -> None:
    model = CARESRRCascadeRescue(source_feature_channels=8)
    with torch.no_grad():
        model.scar_output_projection.bias.fill_(9.0)
        model.edema_output_projection.bias[1].fill_(-9.0)

    inputs = _inputs()
    out = model(**inputs)
    final_logits = out["final_logits"]
    anchor_logits = inputs["anchor_logits"]
    assert torch.equal(final_logits[:, 0:4], anchor_logits[:, 0:4])
    assert torch.equal(final_logits[1:2, 4:5], anchor_logits[1:2, 4:5])
    assert not torch.equal(final_logits[0:1, 4:5], anchor_logits[0:1, 4:5])


def test_correction_bound_and_fixed_support_formula() -> None:
    model = CARESRRCascadeRescue(source_feature_channels=8)
    with torch.no_grad():
        model.scar_output_projection.bias.fill_(100.0)
        model.edema_output_projection.bias[1].fill_(100.0)

    inputs = _inputs()
    out = model(**inputs)
    assert out["scar_correction"].abs().max().item() <= 2.0
    assert out["edema_correction"].abs().max().item() <= 2.0

    probs = torch.softmax(inputs["anchor_logits"], dim=1)
    union = soft_union_probability(probs)
    expected_scar = fixed_support_map(
        distance_to_union_mm=inputs["distance_to_union_mm"],
        soft_union=union,
        max_distance_mm=10.0,
        sigma_mm=5.0,
    )
    expected_edema = fixed_support_map(
        distance_to_union_mm=inputs["distance_to_union_mm"],
        soft_union=union,
        max_distance_mm=15.0,
        sigma_mm=7.5,
    )
    assert torch.allclose(out["scar_support"], expected_scar)
    assert torch.allclose(out["edema_support"], expected_edema)


def test_explicit_inputs_are_wired_into_head_deltas() -> None:
    model = CARESRRCascadeRescue(source_feature_channels=8)
    with torch.no_grad():
        model.scar_output_projection.weight.fill_(0.03)
        model.edema_output_projection.weight[1].fill_(0.03)

    for key in (
        "normalized_lge",
        "normalized_t2",
        "teacher_anatomy_probabilities",
        "teacher_edema_probability",
        "scar_source_margin",
        "explicit_anchor_probabilities",
        "explicit_anchor_uncertainty",
        "explicit_soft_union_probability",
        "normalized_distance_to_union",
        "prototype_scar_positive_similarity",
        "prototype_scar_negative_similarity",
        "prototype_edema_positive_similarity",
        "prototype_edema_negative_similarity",
    ):
        inputs = _inputs()
        base = model(**inputs)
        changed_inputs = {name: value.clone() if torch.is_tensor(value) else value for name, value in inputs.items()}
        changed_inputs[key] = changed_inputs[key] + torch.randn_like(changed_inputs[key]) * 0.25
        changed = model(**changed_inputs)
        scar_diff = (changed["scar_delta"] - base["scar_delta"]).abs().max().item()
        edema_diff = (changed["edema_delta"] - base["edema_delta"]).abs().max().item()
        assert max(scar_diff, edema_diff) > 0.0, key
        assert torch.equal(changed["final_logits"][:, 0:4], changed_inputs["anchor_logits"][:, 0:4])


def test_resolved_loss_terms_are_final_logit_or_zone_aux_and_backprop_to_heads() -> None:
    model = CARESRRCascadeRescue(source_feature_channels=8)
    with torch.no_grad():
        model.scar_output_projection.bias.fill_(0.5)
        model.edema_output_projection.bias[1].fill_(-0.5)
        model.edema_output_projection.bias[0].fill_(0.25)

    inputs = _inputs()
    anchor = inputs["anchor_logits"].clone()
    anchor[:] = -4.0
    anchor[:, 0] = 1.0
    anchor[0, 5, 0, 0, 0] = 8.0
    anchor[0, 4, 0, 0, 1] = 8.0
    anchor[0, 0, 0, 0, 2] = 8.0
    anchor[0, 5, 0, 0, 3] = 8.0
    anchor[0, 4, 0, 1, 1] = 8.0
    inputs["anchor_logits"] = anchor
    inputs["distance_to_union_mm"] = torch.zeros_like(inputs["distance_to_union_mm"])
    labels = torch.zeros(2, 3, 5, 4, dtype=torch.long)
    labels[0, 0, 0, 0] = 5
    labels[0, 0, 0, 1] = 4
    labels[0, 0, 0, 2] = 5
    labels[0, 0, 0, 3] = 0
    labels[0, 0, 1, 0] = 4
    labels[0, 0, 1, 1] = 0
    distance_union = torch.full((2, 1, 3, 5, 4), 12.0)
    distance_surface = torch.full((2, 1, 3, 5, 4), 6.0)

    outputs = model(**inputs)
    terms = care_srr_cascade_rescue_loss_terms(
        outputs,
        labels,
        distance_to_gt_union_mm=distance_union,
        distance_to_gt_pathology_surface_mm=distance_surface,
    )
    nonzero_terms = {name: value for name, value in terms.items() if value.detach().abs().item() > 0.0}
    assert set(nonzero_terms) == set(terms)
    assert all(torch.isfinite(value) for value in terms.values())
    loss = sum(terms.values())
    loss.backward()
    assert model.scar_output_projection.bias.grad is not None
    assert model.scar_output_projection.bias.grad.abs().sum().item() > 0.0
    assert model.edema_output_projection.bias.grad is not None
    assert model.edema_output_projection.bias.grad.abs().sum().item() > 0.0
    assert "scar_delta" not in care_srr_cascade_rescue_loss_terms.__code__.co_names
    assert "edema_delta" not in care_srr_cascade_rescue_loss_terms.__code__.co_names


def test_confident_anchor_preserve_includes_correct_background_voxel() -> None:
    anchor_logits = torch.full((1, 6, 1, 1, 1), -8.0)
    anchor_logits[:, 0] = 8.0
    final_logits = anchor_logits.clone().detach().requires_grad_(True)
    final_logits.data[:, 5] = -4.0
    labels = torch.zeros(1, 1, 1, 1, dtype=torch.long)

    loss = confident_anchor_preserve(final_logits, anchor_logits, labels, class_index=5)
    assert loss.detach().item() > 0.0
    loss.backward()
    assert final_logits.grad is not None
    assert final_logits.grad[:, 5].abs().sum().item() > 0.0


def _prototype_masks() -> dict[str, torch.Tensor]:
    mask = torch.zeros(3, 5, 4, dtype=torch.bool)
    mask.reshape(-1)[:40] = True
    alt = torch.zeros(3, 5, 4, dtype=torch.bool)
    alt.reshape(-1)[20:60] = True
    return {
        "scar_positive": mask,
        "scar_negative": alt,
        "edema_positive": mask,
        "edema_negative": alt,
    }


def test_case_level_prototypes_crossfit_cap_no_t2_and_fail_closed() -> None:
    features = torch.arange(4 * 3 * 5 * 4, dtype=torch.float32).view(4, 3, 5, 4)
    records = [
        build_case_prototype_record(
            case_id=f"case{i:03d}",
            shard=i % 4,
            t2_present=(i != 0),
            features=features + float(i),
            masks=_prototype_masks(),
            cap=16,
            min_voxels=8,
        )
        for i in range(12)
    ]
    assert records[0].edema_negative.numel() == 0
    assert records[1].provenance["scar_positive_accepted"] == 16
    bank, provenance = select_crossfit_prototype_bank(
        records,
        query_case_id="case005",
        query_shard=1,
        pathology="scar",
        minimum_positive=4,
        minimum_negative=4,
    )
    assert bank["positive"].shape[0] >= 4
    assert provenance["excluded_query_case"] is True
    assert provenance["excluded_query_shard"] is True
    try:
        select_crossfit_prototype_bank(
            records[:2],
            query_case_id="case001",
            query_shard=1,
            pathology="edema",
            minimum_positive=4,
            minimum_negative=4,
        )
    except ValueError as exc:
        assert "fail-closed insufficient prototype bank" in str(exc)
    else:
        raise AssertionError("insufficient bank did not fail closed")


def test_no_legacy_imports_in_new_model_file() -> None:
    path = Path("src/care_myocardium/models/care_srr_cascade_rescue.py")
    tree = ast.parse(path.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden = {
        "SRRProposeRefineMyoPS",
        "ProposalDictionary",
        "M10TwoPassSpatialDictionary",
        "legacy_BR2",
        "legacy_SIP",
        "PathologySourceArbiter",
        "BranchArbitrationGate",
        "production_correction_gate",
    }
    assert not forbidden.intersection(imported)
    text = path.read_text()
    assert all(token not in text for token in forbidden)
