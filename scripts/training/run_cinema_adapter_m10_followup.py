#!/usr/bin/env python3
"""M10 follow-up CineMA adapter fidelity contract entrypoint.

Wave F2 uses this script for deterministic contract evidence only. Formal
adapter/control training is Wave F3 work.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.cine.followup import AdapterControlContract, CineMAProvenance


TASK_KEY = "20260714_srr_v3_m10_followup_cine_fidelity"


def contract_payload() -> dict[str, object]:
    provenance = CineMAProvenance(
        source_url="https://huggingface.co/mathpluscode/CineMA/resolve/main/finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors",
        repository="https://github.com/mathpluscode/CineMA.git",
        model_identifier="cinema-acdc-seed0",
        source_commit_or_tag="code:c10daa1d93f0ea28d8b9ad9206b0f673d25805c1;hf:b1251ee50423bceeca84c080782fc3bc7756dea6",
        license="MIT",
        weight_filename="acdc_sax_0.safetensors",
        weight_sha256="c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f",
        architecture_identifier="multiclass_logits_features_uncertainty",
        preprocessing="canonical_orientation_spacing_intensity_normalization",
        label_map={"background": 0, "myocardium": 1, "lv": 2, "rv": 3},
        orientation="RAS",
        spacing=(1.5, 1.5, 2.0),
        time_axis_convention="B,T,C,H,W,D",
        case_frame_count=1,
        output_channels=4,
        feature_channels=16,
        uncertainty_channels=1,
    )
    adapter = AdapterControlContract(
        uses_verified_pretrained_path=True,
        trainable_adapter="final_two_blocks",
        trainable_parameter_count=1024,
        random_init_parameter_count=1024,
        capacity_tolerance=0.0,
        scheduled_checkpoints=10,
        eval_case_count=12,
        selected_checkpoint_name="WAVE3_REQUIRED",
        selected_checkpoint_reloaded=True,
        random_init_control_present=True,
        prior_channels=4,
        feature_channels=16,
        uncertainty_channels=1,
        missing_non_reference_policy="record_frame_failure",
        fallback_to_frame0=False,
        binarizes_prior=False,
    )
    provenance.validate()
    adapter.validate()
    return {
        "task_key": TASK_KEY,
        "phase": "cinema_adapter_followup_fidelity",
        "formal_training_allowed": False,
        "provenance": provenance.__dict__,
        "adapter_control": adapter.__dict__,
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
