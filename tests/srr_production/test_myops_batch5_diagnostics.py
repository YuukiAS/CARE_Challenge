from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
import torch
import yaml

from scripts.evaluation import validate_srr_batch5_packet
from scripts.srr_production import infer_myops
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS


def test_batch5_config_exposes_modes_and_paths() -> None:
    cfg = yaml.safe_load((infer_myops.REPO_ROOT / "configs/srr_production/myops_batch5.yaml").read_text(encoding="utf-8"))
    assert set(cfg["modes"]) == {
        "anchor_identity_control",
        "anchor_bounded_full",
        "srr_no_anchor_control",
        "anchor_bounded_proposal_only",
        "anchor_bounded_refiner_only",
        "production_gate_closed",
        "production_gate_open_bounded_control",
    }
    assert cfg["scope"]["training_allowed"] is False
    assert cfg["scope"]["optimizer_steps_allowed"] == 0
    for key in ("gt_dir", "split_path", "anchor_fold0_pred_dir", "inference_root", "lock_root"):
        assert cfg["paths"][key]


def test_batch5_inference_mode_alias_preserves_batch4_name() -> None:
    assert infer_myops.runtime_final_output_mode("anchor_bounded_proposal_only") == "anchor_bounded_srr_correction"
    assert infer_myops.normalized_mode("anchor_bounded_srr_correction") == "anchor_bounded_full"
    assert infer_myops.BATCH5_PRODUCTION_INTERVENTIONS["anchor_bounded_proposal_only"] == "proposal_only"
    assert infer_myops.BATCH5_PRODUCTION_INTERVENTIONS["production_gate_closed"] == "gate_closed"


def test_model_forward_exposes_batch5_intervention_argument() -> None:
    source = inspect.getsource(SRRProposeRefineMyoPS.forward)
    assert "production_intervention_mode: str = \"full\"" in source
    assert "production_intervention_mode == \"proposal_only\"" in source
    assert "production_intervention_mode == \"refiner_only\"" in source
    assert "production_intervention_mode == \"gate_open_bounded_control\"" in source
    assert "production_intervention_mode == \"gate_closed\"" in source
    assert "\"raw_scar_correction\"" in source
    assert "\"production_intervention_mode\"" in source


def test_batch5_forward_rejects_unknown_intervention() -> None:
    model = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="legacy_variant")
    x = torch.randn(1, 3, 8, 16, 16)
    availability = torch.ones(1, 3)
    with pytest.raises(ValueError, match="unknown production_intervention_mode"):
        model(x, availability, production_intervention_mode="bad_mode")


def test_batch5_validator_fails_missing_packet(tmp_path: Path) -> None:
    result_root = tmp_path / "bad_packet"
    result_root.mkdir()
    with pytest.raises(validate_srr_batch5_packet.ValidationError, match="missing required output"):
        validate_srr_batch5_packet.validate_packet(result_root)


def test_batch5_validator_fails_multiple_decisions(tmp_path: Path) -> None:
    result_root = tmp_path / "packet"
    result_root.mkdir()
    for name in validate_srr_batch5_packet.REQUIRED:
        path = result_root / name
        if path.suffix == ".json":
            path.write_text(json.dumps({}), encoding="utf-8")
        elif path.suffix == ".csv":
            path.write_text("x\n", encoding="utf-8")
        else:
            path.write_text("placeholder\n", encoding="utf-8")
    (result_root / "batch6_unique_repair_decision.md").write_text(
        "B5_OUTPUT_AUTHORITY_BOTTLENECK\nB5_REFINER_EFFECTIVENESS_BOTTLENECK\n",
        encoding="utf-8",
    )
    with pytest.raises(validate_srr_batch5_packet.ValidationError):
        validate_srr_batch5_packet.validate_packet(result_root)
