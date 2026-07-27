#!/usr/bin/env python3
"""CARE-DG evaluator entrypoint."""

from __future__ import annotations

import argparse
import json


def contract() -> dict[str, object]:
    return {
        "required_metrics": [
            "Dice", "leaderboard_HD", "HD95", "exact_HD", "precision", "recall",
            "remote_FP", "component_count", "volume_ratio", "help_harm",
        ],
        "populations": ["complete80_primary", "all220_robustness"],
        "pathologies": ["scar", "edema_zone", "pure_edema"],
        "parity_required_before_training": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(contract(), indent=2, sort_keys=True))
        return 0
    raise SystemExit("CARE_DG_EVALUATION_BLOCKED_UNTIL_OOF_PREDICTIONS_EXIST")


if __name__ == "__main__":
    raise SystemExit(main())
