from __future__ import annotations

from pathlib import Path

import pytest

from src.care_myocardium.cine.followup import (
    AdapterControlContract,
    CineMAProvenance,
    RegistrationGateEvidence,
    RegistrationMathContract,
    SynControlContract,
    TemporalLaunchContract,
    build_freeze_receipt,
)
from src.care_myocardium.cine.followup.contracts import ContractError


def valid_provenance() -> CineMAProvenance:
    return CineMAProvenance(
        source_url="https://example.org/cinema",
        repository="https://example.org/cinema.git",
        model_identifier="cinema-acdc-seed0",
        source_commit_or_tag="v1.0.0",
        license="Apache-2.0",
        weight_filename="cinema.pt",
        weight_sha256="a" * 64,
        architecture_identifier="CineMA-multiclass-logits-features-uncertainty",
        preprocessing="zscore-resample-canonical",
        label_map={"background": 0, "myocardium": 1, "lv": 2, "rv": 3},
        orientation="RAS",
        spacing=(1.5, 1.5, 2.0),
        time_axis_convention="B,T,C,H,W,D",
        case_frame_count=96,
        output_channels=4,
        feature_channels=16,
        uncertainty_channels=1,
    )


def valid_adapter() -> AdapterControlContract:
    return AdapterControlContract(
        uses_verified_pretrained_path=True,
        trainable_adapter="final_two_blocks",
        trainable_parameter_count=1024,
        random_init_parameter_count=1000,
        capacity_tolerance=0.05,
        scheduled_checkpoints=10,
        eval_case_count=12,
        selected_checkpoint_name="checkpoint_validation_step_10000",
        selected_checkpoint_reloaded=True,
        random_init_control_present=True,
        prior_channels=4,
        feature_channels=16,
        uncertainty_channels=1,
        missing_non_reference_policy="record_frame_failure",
        fallback_to_frame0=False,
        binarizes_prior=False,
    )


def valid_registration_math() -> RegistrationMathContract:
    return RegistrationMathContract(
        input_rank=6,
        input_layout="B,T,1,H,W,D",
        reference_frame="ED",
        es_selection_rule="minimum_selected_checkpoint_lv_volume",
        selected_frame_count=8,
        velocity_model="stationary_velocity_field",
        unet_channels=(16, 32, 64, 128),
        integration_method="scaling_and_squaring",
        scaling_and_squaring_steps=7,
        predicts_both_directions=True,
        unit_conversion="normalized_grid_to_voxel_and_physical_mm",
        uses_direct_velocity_as_displacement=False,
        objective_terms={
            "lncc_9x9x9": 1.00,
            "multiclass_dice": 1.00,
            "grad_v": 0.05,
            "negative_jacobian": 0.10,
            "inverse_consistency": 0.10,
        },
    )


def test_valid_followup_contracts_pass() -> None:
    valid_provenance().validate()
    valid_adapter().validate()
    valid_registration_math().validate()
    SynControlContract(
        command="antsRegistrationSyNQuick.sh -d 3 -f fixed.nii.gz -m moving.nii.gz -o out_",
        ants_version="2.5.4",
        parameter_json='{"transform":"SyN"}',
        transform_files=("out_1Warp.nii.gz", "out_0GenericAffine.mat"),
        same_case_frame_metrics=True,
        runtime_seconds_recorded=True,
        failure_rows_recorded=True,
        uses_proxy_after_metric=False,
    ).validate()
    RegistrationGateEvidence(
        checkpoint_name="checkpoint_validation_step_10000",
        selected_checkpoint_reloaded=True,
        eval_case_count=12,
        pair_count=60,
        case_level_denominator=12,
        failed_rows_in_denominator=True,
        true_jacobian=True,
        physical_displacement_mm=True,
        inverse_consistency_composition=True,
        learned_noninferior_to_syn=True,
    ).validate()
    TemporalLaunchContract(
        registration_gate_passed=True,
        registration_checkpoint_reloaded=True,
        valid_non_reference_frames=4,
        slot_names=(
            "ed_anatomy_anchor",
            "early_systolic_contraction",
            "late_systolic_contraction",
            "early_diastolic_relaxation",
            "late_diastolic_relaxation",
            "motion_magnitude",
            "registered_texture_residual",
            "registration_uncertainty_safety",
        ),
        includes_velocity=True,
        includes_jacobian=True,
        includes_residual=True,
        includes_uncertainty=True,
        writes_temporal_output_without_registration=False,
    ).validate()


def test_binary_or_frame0_cinema_fallback_fails_closed() -> None:
    with pytest.raises(ContractError, match="multiclass"):
        bad = valid_provenance()
        CineMAProvenance(**{**bad.__dict__, "output_channels": 2}).validate()

    with pytest.raises(ContractError, match="frame0 fallback"):
        bad_adapter = valid_adapter()
        AdapterControlContract(**{**bad_adapter.__dict__, "fallback_to_frame0": True}).validate()

    with pytest.raises(ContractError, match="binarized prior"):
        bad_adapter = valid_adapter()
        AdapterControlContract(**{**bad_adapter.__dict__, "binarizes_prior": True}).validate()


def test_missing_random_init_or_checkpoint_reload_fails_closed() -> None:
    with pytest.raises(ContractError, match="random initialization"):
        bad = valid_adapter()
        AdapterControlContract(**{**bad.__dict__, "random_init_control_present": False}).validate()

    with pytest.raises(ContractError, match="reloaded"):
        bad = valid_adapter()
        AdapterControlContract(**{**bad.__dict__, "selected_checkpoint_reloaded": False}).validate()


def test_registration_shortcuts_fail_closed() -> None:
    with pytest.raises(ContractError, match="direct velocity"):
        bad = valid_registration_math()
        RegistrationMathContract(**{**bad.__dict__, "uses_direct_velocity_as_displacement": True}).validate()

    with pytest.raises(ContractError, match="seven"):
        bad = valid_registration_math()
        RegistrationMathContract(**{**bad.__dict__, "scaling_and_squaring_steps": 1}).validate()

    with pytest.raises(ContractError, match="case-level denominator"):
        RegistrationGateEvidence(
            checkpoint_name="checkpoint_validation_step_10000",
            selected_checkpoint_reloaded=True,
            eval_case_count=12,
            pair_count=60,
            case_level_denominator=1,
            failed_rows_in_denominator=True,
            true_jacobian=True,
            physical_displacement_mm=True,
            inverse_consistency_composition=True,
            learned_noninferior_to_syn=True,
        ).validate()


def test_proxy_syn_and_temporal_without_registration_fail_closed() -> None:
    with pytest.raises(ContractError, match="proxy"):
        SynControlContract(
            command="antsRegistrationSyNQuick.sh -d 3 -f fixed.nii.gz -m moving.nii.gz -o out_",
            ants_version="2.5.4",
            parameter_json='{"transform":"SyN"}',
            transform_files=("out_1Warp.nii.gz",),
            same_case_frame_metrics=True,
            runtime_seconds_recorded=True,
            failure_rows_recorded=True,
            uses_proxy_after_metric=True,
        ).validate()

    with pytest.raises(ContractError, match="passed registration gate"):
        TemporalLaunchContract(
            registration_gate_passed=False,
            registration_checkpoint_reloaded=True,
            valid_non_reference_frames=4,
            slot_names=(
                "ed_anatomy_anchor",
                "early_systolic_contraction",
                "late_systolic_contraction",
                "early_diastolic_relaxation",
                "late_diastolic_relaxation",
                "motion_magnitude",
                "registered_texture_residual",
                "registration_uncertainty_safety",
            ),
            includes_velocity=True,
            includes_jacobian=True,
            includes_residual=True,
            includes_uncertainty=True,
            writes_temporal_output_without_registration=False,
        ).validate()


def test_freeze_receipt_hashes_exact_files(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("alpha\n", encoding="utf-8")
    b.write_text("beta\n", encoding="utf-8")
    receipt = build_freeze_receipt([b, a], task_key="m10-test")
    assert receipt["status"] == "FROZEN_FOR_WAVE_F3"
    assert len(receipt["files"]) == 2
    assert len(str(receipt["freeze_hash"])) == 64
