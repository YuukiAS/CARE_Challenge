#!/usr/bin/env python3
"""CARE-DG candidate gate contract."""

from __future__ import annotations

import argparse
import json


def gate_contract() -> dict[str, object]:
    return {
        "primary_estimand": "complete80",
        "robustness_estimand": "all220",
        "exploratory_candidate_gate": {
            "scar_complete_target_dice_delta_min": -0.005,
            "pure_edema_complete_target_dice_delta_min": -0.005,
            "edema_zone_complete_target_dice_delta_min": -0.005,
            "at_least_one_pathology_dice_gain_min": 0.005,
            "hd95_relative_max": 1.05,
            "exact_hd_p95_increase_mm_max": 5.0,
            "remote_fp_relative_increase_max": 0.10,
        },
        "paper_ready_gate": {
            "complete_target_dice_gain_min": 0.005,
            "hd95_nonworse_within": 0.05,
            "remote_fp_non_increased": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(gate_contract(), indent=2, sort_keys=True))
        return 0
    raise SystemExit("CARE_DG_SELECTION_BLOCKED_UNTIL_W3_AGGREGATION_EXISTS")


if __name__ == "__main__":
    raise SystemExit(main())
