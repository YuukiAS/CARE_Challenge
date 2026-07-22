from __future__ import annotations

import csv
import shutil
from types import SimpleNamespace

import numpy as np
import torch
import torch.nn.functional as F
import yaml

from scripts.evaluation.validate_srr_batch7_minimal_decomposition_packet import (
    REPO_ROOT,
    validate_packet,
)
from scripts.training.run_srr_propref_myops_fold0 import (
    AnchoredCaseData,
    advance_batch7_sampler_rng,
    apply_batch7_decomposition_schedule,
    batch_from_source_balanced_case,
    build_source_balanced_center_sequence,
    source_balanced_case_pools,
    source_balanced_count_summary,
    validate_batch7_training_source,
)
from src.care_myocardium.losses.srr_losses import (
    br2_center_deviation_shrinkage_loss,
    br2_selective_integration_penalty,
    br2_source_l1_sparsity_loss,
)
from src.care_myocardium.models.srr_propref import (
    BR2_CENTER_ORDER,
    BR2_CENTER_TO_PATTERN,
    BR2_REPRESENTER_SPECS,
    LightweightCenterHierarchicalBR2,
    ProposalDictionary,
    SRRProposeRefineMyoPS,
)
from scripts.evaluation.prepare_srr_batch7_minimal_decomposition_packet import validate_resolved_loss_rows


BATCH7_CONFIG_PATH = REPO_ROOT / "configs/srr_production/myops_batch7_minimal_decomposition.yaml"
BATCH7_RESULT_ROOT = REPO_ROOT / "results/20260722_srr_batch7_minimal_pathology_decomposition"


def _batch7_cfg() -> dict:
    return yaml.safe_load(BATCH7_CONFIG_PATH.read_text(encoding="utf-8"))


def _copy_batch7_packet(tmp_path):
    packet = tmp_path / "packet"
    shutil.copytree(BATCH7_RESULT_ROOT, packet)
    return packet


def _fake_anchored_case(
    case_id: str,
    *,
    center: str,
    t2_present: bool,
    c0_present: bool,
    scar: bool = False,
    edema: bool = False,
) -> AnchoredCaseData:
    shape = (5, 5, 5)
    image = np.zeros((3, *shape), dtype=np.float32)
    label = np.zeros(shape, dtype=np.int64)
    if scar:
        label[2, 2, 2] = 5
    if edema:
        label[1, 1, 1] = 4
    anchor = np.zeros((6, *shape), dtype=np.float32)
    anchor[0] = 1.0
    target_class = 5 if scar else 4
    anchor[:, 0, 0, 0] = 0.0
    anchor[target_class, 0, 0, 0] = 1.0
    components = np.zeros((2, *shape), dtype=np.float32)
    availability = np.asarray([1.0, float(t2_present), float(c0_present)], dtype=np.float32)
    metadata = SimpleNamespace(
        center=center,
        t2_present=t2_present,
        modality_group="lge_t2_c0" if t2_present and c0_present else "lge_c0" if c0_present else "lge_only",
    )
    return AnchoredCaseData(
        case_id=case_id,
        image=image,
        label_arr=label,
        label_img=None,
        availability=availability,
        metadata=metadata,
        anchor_probabilities=anchor,
        component_features=components,
        anchor_source="unit_test",
        anchor_fold=0,
        raw_anchor_probabilities=anchor,
        raw_component_features=components,
    )


def test_center_deviation_is_zero_sum_within_availability_pattern() -> None:
    block = LightweightCenterHierarchicalBR2(4)
    with torch.no_grad():
        block.center_deviation_raw.copy_(torch.arange(7 * 7, dtype=torch.float32).view(7, 7) / 10.0)

    deviation = block.center_deviation_zero_sum()

    for pattern in {"lge_only", "lge_c0", "lge_t2_c0"}:
        rows = [idx for idx, center in enumerate(BR2_CENTER_ORDER) if BR2_CENTER_TO_PATTERN[center] == pattern]
        assert torch.allclose(deviation[rows].sum(dim=0), torch.zeros(7), atol=1e-6)


def test_edema_no_t2_effective_beta_is_exact_zero() -> None:
    block = LightweightCenterHierarchicalBR2(4)
    with torch.no_grad():
        block.beta_pattern.fill_(0.25)
        block.center_deviation_raw.fill_(0.10)
    availability = torch.tensor([[1.0, 0.0, 0.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0]])

    beta = block.beta_for_batch(
        availability,
        center_ids=["CenterA", "CenterE", "CenterB"],
        use_center_beta=True,
        pathology="edema",
    )

    assert float(beta["effective_beta"][:2].detach().abs().max()) == 0.0
    assert float(beta["availability_mask"][:2].detach().abs().max()) == 0.0
    assert float(beta["effective_beta"][2].detach().abs().max()) > 0.0


def test_representer_modules_have_distinct_parameter_storage() -> None:
    block = LightweightCenterHierarchicalBR2(4)
    pointers = []
    for name, _modalities in BR2_REPRESENTER_SPECS:
        params = list(block.representers[name].parameters())
        assert params
        pointers.append(params[-1].data_ptr())

    assert len(set(pointers)) == len(BR2_REPRESENTER_SPECS)


def test_representer_pre_beta_rms_one_missing_zero_and_initial_delta_zero() -> None:
    block = LightweightCenterHierarchicalBR2(4)
    base = torch.randn((2, 4, 3, 4, 4), dtype=torch.float32)
    per_modality = [torch.randn_like(base) for _ in range(3)]
    availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 0.0]], dtype=torch.float32)

    out, diag = block(
        base,
        per_modality,
        availability,
        pathology="scar",
        center_ids=["CenterB", "CenterA"],
        use_center_beta=True,
    )

    available = diag["availability_mask"] > 0.5
    missing = ~available
    assert torch.allclose(diag["representer_pre_beta_rms"][available], torch.ones_like(diag["representer_pre_beta_rms"][available]), atol=1e-5)
    assert float(diag["representer_contribution_rms"][missing].detach().abs().max()) == 0.0
    assert float((out - base).detach().abs().max()) <= 1e-6
    assert float(diag["br2_delta_rms"].detach().abs().max()) <= 1e-6


def _br2_proposal_gradient_summary(block: LightweightCenterHierarchicalBR2) -> dict[str, float]:
    torch.manual_seed(20260722)
    dictionary = ProposalDictionary(4, pathology="scar", no_proto=True)
    base = torch.randn((1, 4, 3, 4, 4), dtype=torch.float32)
    per_modality = [torch.randn_like(base) for _ in range(3)]
    availability = torch.tensor([[1.0, 1.0, 1.0]], dtype=torch.float32)
    br2_feature, diag = block(
        base,
        per_modality,
        availability,
        pathology="scar",
        center_ids=["CenterB"],
        use_center_beta=True,
    )
    proposal = dictionary(
        br2_feature,
        torch.zeros((1, 1, 3, 4, 4), dtype=torch.float32),
        torch.zeros((1, 1, 3, 4, 4), dtype=torch.float32),
        availability=availability,
    )["proposal_logits"]
    loss = F.binary_cross_entropy_with_logits(proposal, torch.ones_like(proposal))
    block.zero_grad(set_to_none=True)
    dictionary.zero_grad(set_to_none=True)
    loss.backward()
    representer_grad = 0.0
    for _name, representer in block.representers.items():
        for param in representer.adapter.parameters():
            if param.grad is not None:
                representer_grad += float(param.grad.detach().abs().sum())
    return {
        "initial_delta_max_abs": float((br2_feature - base).detach().abs().max()),
        "initial_delta_rms": float(diag["br2_delta_rms"].detach().abs().max()),
        "beta_pattern_grad_l1": float(block.beta_pattern.grad.detach().abs().sum()) if block.beta_pattern.grad is not None else 0.0,
        "center_deviation_grad_l1": float(block.center_deviation_raw.grad.detach().abs().sum()) if block.center_deviation_raw.grad is not None else 0.0,
        "projection_weight_grad_l1": float(block.pathology_projection.weight.grad.detach().abs().sum()) if block.pathology_projection.weight.grad is not None else 0.0,
        "representer_adapter_grad_l1": representer_grad,
    }


def test_br2_initial_proposal_loss_reaches_zero_initialized_projection() -> None:
    summary = _br2_proposal_gradient_summary(LightweightCenterHierarchicalBR2(4))

    assert summary["initial_delta_max_abs"] <= 1e-6
    assert summary["initial_delta_rms"] <= 1e-6
    assert summary["projection_weight_grad_l1"] > 0.0
    assert summary["beta_pattern_grad_l1"] == 0.0
    assert summary["center_deviation_grad_l1"] == 0.0
    assert summary["representer_adapter_grad_l1"] == 0.0


def test_known_bad_double_zero_br2_init_blocks_beta_and_representer_gradients() -> None:
    block = LightweightCenterHierarchicalBR2(4)
    with torch.no_grad():
        block.beta_pattern.zero_()
        block.center_deviation_raw.zero_()
        block.pathology_projection.weight.zero_()
        block.pathology_projection.bias.zero_()

    summary = _br2_proposal_gradient_summary(block)

    assert summary["initial_delta_max_abs"] == 0.0
    assert summary["beta_pattern_grad_l1"] == 0.0
    assert summary["center_deviation_grad_l1"] == 0.0
    assert summary["representer_adapter_grad_l1"] == 0.0


def test_br2_staged_gradient_chain_preserves_zero_projection_init() -> None:
    torch.manual_seed(7)
    block = LightweightCenterHierarchicalBR2(4)
    assert float(block.pathology_projection.weight.detach().abs().max()) == 0.0
    assert float(block.pathology_projection.bias.detach().abs().max()) == 0.0
    assert float(block.beta_pattern.detach().abs().max()) > 0.0

    base = torch.zeros((1, 4, 3, 3, 3), dtype=torch.float32)
    per_modality = [torch.randn_like(base) for _ in range(3)]
    availability = torch.tensor([[1.0, 1.0, 1.0]], dtype=torch.float32)

    out, diag = block(
        base,
        per_modality,
        availability,
        pathology="scar",
        center_ids=["CenterB"],
        use_center_beta=True,
    )
    assert torch.allclose(out, base, atol=1e-6)
    assert float(diag["br2_delta_rms"].detach().abs().max()) == 0.0

    loss = (out - torch.ones_like(out)).square().mean()
    block.zero_grad(set_to_none=True)
    loss.backward()
    projection_grad = block.pathology_projection.weight.grad.detach().abs().max()
    assert float(projection_grad) > 0.0

    with torch.no_grad():
        block.pathology_projection.weight.add_(-1.0e-2 * block.pathology_projection.weight.grad)

    block.zero_grad(set_to_none=True)
    out_after_projection_step, _diag = block(
        base,
        per_modality,
        availability,
        pathology="scar",
        center_ids=["CenterB"],
        use_center_beta=True,
    )
    staged_loss = (out_after_projection_step - torch.ones_like(out_after_projection_step)).square().mean()
    staged_loss.backward()

    beta_grad = block.beta_pattern.grad.detach().abs().max()
    representer_grad = max(
        float(param.grad.detach().abs().max())
        for param in block.representers.parameters()
        if param.grad is not None
    )
    assert float(beta_grad) > 0.0
    assert representer_grad > 0.0


def test_br2_losses_use_full_center_table_not_batch_proxy() -> None:
    logits = torch.zeros((1, 6, 2, 2, 2), dtype=torch.float32)
    outputs = {
        "logits": logits,
        "scar_br2_effective_beta": torch.tensor([[0.2, -0.05]], dtype=torch.float32),
        "scar_br2_availability_mask": torch.ones((1, 2), dtype=torch.float32),
        "scar_br2_all_center_beta": torch.tensor(
            [
                [0.2, -0.05],
                [-0.2, 0.0],
                [0.2, 0.0],
                [0.0, 0.0],
                [0.0, 0.0],
                [0.0, 0.0],
                [0.0, 0.0],
            ],
            dtype=torch.float32,
        ),
        "scar_br2_source_eligibility_mask": torch.tensor(
            [
                [1.0, 1.0],
                [1.0, 1.0],
                [1.0, 1.0],
                [0.0, 0.0],
                [0.0, 0.0],
                [0.0, 0.0],
                [0.0, 0.0],
            ],
            dtype=torch.float32,
        ),
        "scar_br2_all_center_deviation": torch.ones((7, 2), dtype=torch.float32) * 0.5,
    }

    assert torch.isclose(br2_source_l1_sparsity_loss(outputs, "scar"), torch.tensor(0.10833333))
    assert torch.isclose(br2_center_deviation_shrinkage_loss(outputs, "scar"), torch.tensor(0.25))
    sip, metrics = br2_selective_integration_penalty(outputs, "scar", tau=0.10)
    assert torch.isclose(sip, torch.tensor(1.0))
    assert float(metrics["scar_br2_sip_terms"]) == 2.0


def test_edema_sip_source_set_excludes_no_t2_centers() -> None:
    block = LightweightCenterHierarchicalBR2(4)
    with torch.no_grad():
        block.beta_pattern.fill_(0.2)
    availability = torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32)
    beta = block.beta_for_batch(availability, center_ids=["CenterA"], use_center_beta=True, pathology="edema")
    outputs = {"logits": torch.zeros((1, 6, 1, 1, 1)), **{f"edema_br2_{k}": v for k, v in beta.items()}}

    assert int(beta["source_eligibility_mask"].sum().detach().cpu().item()) == 14
    assert float(beta["source_eligibility_mask"][[0, 3, 4, 5, 6]].sum().detach().cpu()) == 0.0
    sip, metrics = br2_selective_integration_penalty(outputs, "edema", tau=0.10)
    assert float(sip.detach().cpu()) == 0.0
    assert float(metrics["edema_br2_sip_terms"]) == 7.0


def test_missing_br2_outputs_make_losses_exact_zero() -> None:
    outputs = {"logits": torch.ones((1, 6, 1, 1, 1), dtype=torch.float32)}

    assert float(br2_source_l1_sparsity_loss(outputs, "scar")) == 0.0
    assert float(br2_center_deviation_shrinkage_loss(outputs, "scar")) == 0.0
    sip, _metrics = br2_selective_integration_penalty(outputs, "scar")
    assert float(sip) == 0.0


def test_known_bad_no_t2_edema_loss_nonzero_rejected() -> None:
    rows = [
        {
            "experiment": "edema_minimal",
            "loss_name": "loss_no_t2_edema_safety",
            "resolved_weight": 0.5,
        }
    ]

    try:
        validate_resolved_loss_rows(rows)
    except ValueError as exc:
        assert "loss_no_t2_edema_safety=0.5" in str(exc)
    else:
        raise AssertionError("nonzero no-T2 edema safety loss must be rejected")


def test_known_bad_availability_pattern_training_source_rejected() -> None:
    try:
        validate_batch7_training_source("availability_pattern")
    except ValueError as exc:
        assert "metadata.center" in str(exc)
        assert "availability-pattern source is forbidden" in str(exc)
    else:
        raise AssertionError("availability-pattern must not be accepted as Batch7 training source")


def test_source_balanced_edema_pools_exclude_no_t2_centers() -> None:
    cases = [
        _fake_anchored_case("A001", center="CenterA", t2_present=False, c0_present=False, edema=True),
        _fake_anchored_case("E001", center="CenterE", t2_present=False, c0_present=True, edema=True),
        _fake_anchored_case("B001", center="CenterB", t2_present=True, c0_present=True, edema=True),
        _fake_anchored_case("C001", center="CenterC", t2_present=True, c0_present=True, edema=True),
    ]

    pools = source_balanced_case_pools(cases, "edema")

    assert sorted(pools) == ["CenterB", "CenterC"]


def test_source_balanced_sampler_records_center_case_patch_and_passes_count_gate() -> None:
    cases = [
        _fake_anchored_case("A001", center="CenterA", t2_present=False, c0_present=False, scar=True),
        _fake_anchored_case("B001", center="CenterB", t2_present=True, c0_present=True, scar=True),
        _fake_anchored_case("E001", center="CenterE", t2_present=False, c0_present=True, scar=True),
    ]
    pools = source_balanced_case_pools(cases, "scar")
    center_sequence = build_source_balanced_center_sequence(sorted(pools), steps=30, rng=np.random.default_rng(7))
    rows = []
    for step in range(1, 31):
        *_batch, manifest = batch_from_source_balanced_case(
            pools=pools,
            step=step,
            patch_shape=(3, 3, 3),
            rng=np.random.default_rng(1000 + step),
            pathology="scar",
            oversample_foreground=1.0,
            center_sequence=center_sequence,
        )
        rows.append(manifest)

    summary = source_balanced_count_summary(rows, max_deviation_fraction=0.15)

    assert summary["status"] == "PASS"
    assert summary["max_deviation_fraction"] == 0.0
    assert set(summary["center_counts"].values()) == {10}
    assert rows[0]["training_source"] == "metadata.center"
    assert rows[0]["availability_is_observation_set_not_source"] is True
    assert rows[0]["patch_source"] in {"lesion", "anchor_error"}
    assert isinstance(rows[0]["selected_case_id"], str)
    assert rows[0]["anchor_error_voxel_count"] > 0
    assert {"patch_center_z", "patch_center_y", "patch_center_x"}.issubset(rows[0])


def test_source_balanced_count_gate_rejects_availability_pattern_manifest_proxy() -> None:
    rows = [
        {
            "step": 1,
            "selected_center": "lge_only",
            "training_source": "availability_pattern",
            "availability_is_observation_set_not_source": False,
        }
    ]

    summary = source_balanced_count_summary(rows, max_deviation_fraction=0.15)

    assert summary["status"] == "FAIL"
    assert summary["bad_training_source_rows"]



def _trainable_parameter_names(model: torch.nn.Module) -> set[str]:
    return {name for name, param in model.named_parameters() if param.requires_grad}


def test_batch7_decomposition_schedule_authorizes_only_target_blocks_by_phase() -> None:
    model = SRRProposeRefineMyoPS(
        base_channels=4,
        variant="m10_d3_hierarchical_memory_propref",
        encoder_profile="tiny_3scale",
        final_output_mode="anchor_bounded_srr_correction",
        enable_batch7_decomposition_br2=True,
    )

    warmup = apply_batch7_decomposition_schedule(model, pathology="scar", step=1, br2_enabled=True)
    names = _trainable_parameter_names(model)
    assert warmup["phase"] == "warmup_coefficients_and_target_heads_representers_frozen"
    assert any(name.startswith("scar_lightweight_br2.beta_pattern") for name in names)
    assert any(name.startswith("scar_dictionary.") for name in names)
    assert not any(name.startswith("scar_lightweight_br2.representers.") for name in names)
    assert not any(name.startswith("edema_dictionary.") for name in names)

    coeff = apply_batch7_decomposition_schedule(model, pathology="scar", step=51, br2_enabled=True)
    names = _trainable_parameter_names(model)
    assert coeff["phase"] == "alternate_coefficients"
    assert names == {"scar_lightweight_br2.beta_pattern", "scar_lightweight_br2.center_deviation_raw"}

    representer = apply_batch7_decomposition_schedule(model, pathology="scar", step=52, br2_enabled=True)
    names = _trainable_parameter_names(model)
    assert representer["phase"] == "alternate_representers_and_target_heads"
    assert any(name.startswith("scar_lightweight_br2.representers.") for name in names)
    assert any(name.startswith("scar_lightweight_br2.pathology_projection.") for name in names)
    assert any(name.startswith("scar_dictionary.") for name in names)
    assert not any(name.startswith("scar_lightweight_br2.beta_pattern") for name in names)

    calibration = apply_batch7_decomposition_schedule(model, pathology="scar", step=351, br2_enabled=True)
    names = _trainable_parameter_names(model)
    assert calibration["phase"] == "calibration_coefficients_and_target_heads_representers_frozen"
    assert any(name.startswith("scar_lightweight_br2.center_deviation_raw") for name in names)
    assert not any(name.startswith("scar_lightweight_br2.representers.") for name in names)


def test_resume_replay_preserves_source_balanced_step_51_case_and_patch() -> None:
    cases = [
        _fake_anchored_case("A001", center="CenterA", t2_present=False, c0_present=False, scar=True),
        _fake_anchored_case("B001", center="CenterB", t2_present=True, c0_present=True, scar=True),
        _fake_anchored_case("E001", center="CenterE", t2_present=False, c0_present=True, scar=True),
    ]
    pools = source_balanced_case_pools(cases, "scar")
    center_sequence = build_source_balanced_center_sequence(sorted(pools), steps=400, rng=np.random.default_rng(20260722))
    full_rng = np.random.default_rng(77)
    replay_rng = np.random.default_rng(77)
    full_rows = []
    for step in range(1, 52):
        *_batch, manifest = batch_from_source_balanced_case(
            pools=pools,
            step=step,
            patch_shape=(3, 3, 3),
            rng=full_rng,
            pathology="scar",
            oversample_foreground=1.0,
            center_sequence=center_sequence,
        )
        full_rows.append(manifest)
    replay_rows = advance_batch7_sampler_rng(
        pools=pools,
        through_step=50,
        patch_shape=(3, 3, 3),
        rng=replay_rng,
        pathology="scar",
        oversample_foreground=1.0,
        center_sequence=center_sequence,
    )
    *_batch, resumed_manifest = batch_from_source_balanced_case(
        pools=pools,
        step=51,
        patch_shape=(3, 3, 3),
        rng=replay_rng,
        pathology="scar",
        oversample_foreground=1.0,
        center_sequence=center_sequence,
    )

    assert len(replay_rows) == 50
    assert replay_rows[-1]["resume_skip_replay"] is True
    assert resumed_manifest["selected_case_id"] == full_rows[-1]["selected_case_id"]
    assert resumed_manifest["selected_center"] == full_rows[-1]["selected_center"]
    assert resumed_manifest["patch_source"] == full_rows[-1]["patch_source"]
    assert resumed_manifest["patch_center_z"] == full_rows[-1]["patch_center_z"]
    assert resumed_manifest["patch_center_y"] == full_rows[-1]["patch_center_y"]
    assert resumed_manifest["patch_center_x"] == full_rows[-1]["patch_center_x"]


def test_minimal_decomposition_validator_accepts_static_preflight_packet() -> None:
    errors = validate_packet(BATCH7_RESULT_ROOT, _batch7_cfg(), final=False)

    assert errors == []


def test_minimal_decomposition_validator_rejects_static_packet_as_final_completion() -> None:
    errors = validate_packet(BATCH7_RESULT_ROOT, _batch7_cfg(), final=True)

    assert any(error.startswith("missing_or_empty:scar_casewise_metrics.csv") for error in errors)
    assert not any(error == "known_bad_packet_not_rejected" for error in errors)


def test_minimal_decomposition_validator_rejects_known_bad_source_and_loss(tmp_path) -> None:
    packet = _copy_batch7_packet(tmp_path)
    inventory_path = packet / "center_modality_inventory.csv"
    rows = list(csv.DictReader(inventory_path.open(newline="", encoding="utf-8")))
    rows[0]["source_semantics"] = "availability_pattern"
    with inventory_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    loss_path = packet / "resolved_stage_loss_weights.csv"
    loss_rows = list(csv.DictReader(loss_path.open(newline="", encoding="utf-8")))
    loss_rows[0]["loss_name"] = "loss_pattern_sip_integrativeness"
    loss_rows[0]["resolved_weight"] = "0.1"
    with loss_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(loss_rows[0]))
        writer.writeheader()
        writer.writerows(loss_rows)

    errors = validate_packet(packet, _batch7_cfg(), final=False)

    assert any(error.startswith("center_source_not_metadata_center") for error in errors)
    assert any(error.startswith("legacy_sip_or_dictionary_nonzero") for error in errors)
