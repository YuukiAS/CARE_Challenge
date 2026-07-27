#!/usr/bin/env python3
"""CARE-DG local inference entrypoint placeholder."""

from __future__ import annotations

import argparse
import json


def contract() -> dict[str, object]:
    return {
        "method": "CARE-DG",
        "anchor": "frozen 5-fold nnU-Net ensemble",
        "correction_model": "all-data CARE-DG deployment checkpoint",
        "determinism_required": "two independent hash-identical runs",
        "validation_upload": False,
        "docker_upload": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--validation-infer", action="store_true")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(contract(), indent=2, sort_keys=True))
        return 0
    if args.validation_infer:
        raise SystemExit("CARE_DG_VALIDATION_INFERENCE_BLOCKED_UNTIL_W4_DEPLOYMENT_CONTRACT_PASS")
    parser.error("expected --print-contract or --validation-infer")


if __name__ == "__main__":
    raise SystemExit(main())
