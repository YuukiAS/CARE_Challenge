#!/usr/bin/env python3
"""M10 follow-up Cine registration fidelity contract entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.cine.followup import RegistrationGateEvidence, RegistrationMathContract, SynControlContract


TASK_KEY = "20260714_srr_v3_m10_followup_cine_fidelity"


def contract_payload() -> dict[str, object]:
    math_contract = RegistrationMathContract(
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
    syn_contract = SynControlContract(
        command="antsRegistrationSyNQuick.sh -d 3 -f fixed.nii.gz -m moving.nii.gz -o syn_",
        ants_version="WAVE3_RUNTIME_QUERY_REQUIRED",
        parameter_json='{"transform":"SyN","dimension":3}',
        transform_files=("syn_0GenericAffine.mat", "syn_1Warp.nii.gz"),
        same_case_frame_metrics=True,
        runtime_seconds_recorded=True,
        failure_rows_recorded=True,
        uses_proxy_after_metric=False,
    )
    gate = RegistrationGateEvidence(
        checkpoint_name="WAVE3_REQUIRED",
        selected_checkpoint_reloaded=True,
        eval_case_count=12,
        pair_count=60,
        case_level_denominator=12,
        failed_rows_in_denominator=True,
        true_jacobian=True,
        physical_displacement_mm=True,
        inverse_consistency_composition=True,
        learned_noninferior_to_syn=True,
    )
    math_contract.validate()
    syn_contract.validate()
    gate.validate()
    return {
        "task_key": TASK_KEY,
        "phase": "cine_registration_followup_fidelity",
        "formal_training_allowed": False,
        "registration_math": math_contract.__dict__,
        "syn_control": syn_contract.__dict__,
        "registration_gate_evidence": gate.__dict__,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    payload = contract_payload()
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.print_contract:
        raise SystemExit("Wave F2 entrypoint is contract-only; formal training is Wave F3.")


if __name__ == "__main__":
    main()
