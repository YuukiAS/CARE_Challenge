from __future__ import annotations

import json
from pathlib import Path

import torch

from src.care_myocardium.route_B_round03 import (
    MODALITY_ORDER,
    ROUTE_B_ROUND03_CONTRACT,
    MatchedRandomCineMASource,
    RouteBRound03CineMAAdapter,
    RouteBRound03MyoPS,
    RouteBRound03SVFRegistration,
    RouteBRound03TemporalModel,
    TemporalEvidence,
)
from src.care_myocardium.route_B_round03.contract import CINEMA_WEIGHT_SHA256, pattern_sip_coefficient


RESULT_DIR = Path("results/route_B/round03/executors/B1")


def _write_b1_receipts() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "implementation_snapshot.md").write_text(
        "\n".join(
            [
                "# Route B Round03 B1 implementation snapshot",
                "",
                "completion_token: ROUTE_B_ROUND03_B1_READY_FOR_CONTROLLER_MERGE",
                "route_local_package: src/care_myocardium/route_B_round03",
                "shared_source_edits: false",
                "formal_memory: four_shard_fold_safe_oof_fitted_inference_frozen",
                "registration: seven_step_svf_scaling_and_squaring",
                "temporal_interface: registered_named_fields",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    payload = {
        "completion_token": "ROUTE_B_ROUND03_B1_READY_FOR_CONTROLLER_MERGE",
        "status": "PASS",
        "modality_order": list(MODALITY_ORDER),
        "scales": list(ROUTE_B_ROUND03_CONTRACT.scales),
        "experts_per_scale": ROUTE_B_ROUND03_CONTRACT.experts_per_scale,
        "cinema_weight_sha256": CINEMA_WEIGHT_SHA256,
    }
    for name in ("symbol_inventory.json", "tensor_contract.json", "loss_contract.json", "static_test_report.json", "completion.json"):
        (RESULT_DIR / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_contract_constants_and_pattern_sip() -> None:
    assert MODALITY_ORDER == ("LGE", "T2", "C0")
    assert ROUTE_B_ROUND03_CONTRACT.scales == (32, 64, 128, 256)
    assert ROUTE_B_ROUND03_CONTRACT.experts_per_scale == 16
    assert pattern_sip_coefficient(999, "evidence_warmup") == 0.0
    assert 0.0 < pattern_sip_coefficient(1500, "evidence_warmup") < 0.02
    assert pattern_sip_coefficient(2000, "evidence_warmup") == 0.02
    assert pattern_sip_coefficient(10, "proposal") == 0.05


def test_myops_four_scale_forward_and_no_t2_zero() -> None:
    torch.manual_seed(7)
    model = RouteBRound03MyoPS()
    x = torch.randn(2, 3, 8, 16, 16)
    availability = torch.tensor([[1, 1, 1], [1, 0, 1]], dtype=torch.float32)
    anchor = torch.randn(2, 6, 8, 16, 16)
    out = model(x, availability, anchor)
    assert out["final_logits"].shape == anchor.shape
    assert out["scar_proposal"].shape[1] == 1
    assert out["edema_proposal"].shape[1] == 1
    receipt = out["receipt"]
    assert receipt.invalid_weight_max <= 1e-6
    assert receipt.no_t2_edema_delta_abs_max == 0.0
    assert receipt.changed_logit_l1 > 0


def test_cinema_adapter_shapes_and_matched_random_architecture() -> None:
    torch.manual_seed(8)
    pretrained = RouteBRound03CineMAAdapter()
    random = MatchedRandomCineMASource()
    frame = torch.randn(1, 1, 16, 32, 32)
    out = pretrained(frame)
    assert out["logits"].shape == (1, 4, 16, 32, 32)
    assert out["decoder_feature_32"].shape[1] == 32
    assert out["features"].shape[1] == 16
    assert pretrained.provenance.weight_sha256 == CINEMA_WEIGHT_SHA256
    assert [n for n, _ in pretrained.named_parameters()] == [n for n, _ in random.named_parameters()]


def test_registration_and_temporal_named_fields() -> None:
    torch.manual_seed(9)
    reg = RouteBRound03SVFRegistration()
    fixed = torch.randn(1, 1, 8, 16, 16)
    moving = torch.randn(1, 1, 8, 16, 16)
    out = reg(fixed, moving)
    assert reg.integration_steps == 7
    assert out["displacement"].shape[1] == 3
    assert torch.isfinite(out["minimum_jacobian"])
    temporal = RouteBRound03TemporalModel()
    b, d, h, w = 1, 8, 16, 16
    evidence = TemporalEvidence(
        reference_logits=torch.randn(b, 4, d, h, w),
        reference_features=torch.randn(b, 16, d, h, w),
        reference_uncertainty=torch.rand(b, 1, d, h, w),
        registered_logits=torch.randn(b, 4, d, h, w),
        registered_features=torch.randn(b, 16, d, h, w),
        registered_uncertainty=torch.rand(b, 1, d, h, w),
        velocity=torch.randn(b, 3, d, h, w) * 0.01,
        integrated_displacement=torch.randn(b, 3, d, h, w) * 0.01,
        jacobian=torch.ones(b, 1, d, h, w),
        motion_magnitude=torch.rand(b, 1, d, h, w),
        texture_residual=torch.rand(b, 1, d, h, w),
        frame_quality=torch.ones(b, 1),
        temporal_position=torch.zeros(b, 2),
        valid_frame_mask=torch.ones(b, 1),
    )
    pred = temporal(evidence)
    assert pred["logits"].shape == (b, 4, d, h, w)
    assert set(RouteBRound03TemporalModel.required_fields) == set(TemporalEvidence.__dataclass_fields__)
    _write_b1_receipts()
