#!/usr/bin/env python3
"""M10 follow-up Cine temporal fidelity contract entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.cine.followup import TemporalLaunchContract
from src.care_myocardium.cine.temporal_dictionary import TEMPORAL_SLOT_NAMES


TASK_KEY = "20260714_srr_v3_m10_followup_cine_fidelity"


def contract_payload() -> dict[str, object]:
    temporal = TemporalLaunchContract(
        registration_gate_passed=True,
        registration_checkpoint_reloaded=True,
        valid_non_reference_frames=4,
        slot_names=TEMPORAL_SLOT_NAMES,
        includes_velocity=True,
        includes_jacobian=True,
        includes_residual=True,
        includes_uncertainty=True,
        writes_temporal_output_without_registration=False,
    )
    temporal.validate()
    return {
        "task_key": TASK_KEY,
        "phase": "cine_temporal_followup_fidelity",
        "formal_training_allowed": False,
        "temporal_launch": temporal.__dict__,
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
