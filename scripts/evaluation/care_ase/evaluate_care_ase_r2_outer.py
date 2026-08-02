#!/usr/bin/env python
"""CARE-ASE R2 one-time outer evaluator.

This entrypoint is deliberately fail-closed before W4.5. It exists during G1 so
the implementation has a fixed evaluator/decode path, but it refuses to touch
fold1/fold4 outer data unless the pre-outer snapshot push receipt is present.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits, pure_edema_metric_population, scar_metric_population


RESULT_ROOT = REPO_ROOT / "results/20260803_care_ase_r2_full_fidelity_execution"
W45_PUSH_RECEIPT = RESULT_ROOT / "preouter_snapshot_push_receipt.json"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def assert_w45_permit() -> dict[str, Any]:
    if not W45_PUSH_RECEIPT.is_file():
        raise RuntimeError("W5 outer evaluation forbidden before W4.5 snapshot push receipt")
    receipt = json.loads(W45_PUSH_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS" or not receipt.get("push_verified", False):
        raise RuntimeError("W4.5 snapshot push receipt is not PASS/push_verified")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--allow-after-w45", action="store_true")
    args = parser.parse_args()

    if not args.allow_after_w45:
        raise RuntimeError("outer evaluator requires explicit --allow-after-w45")
    permit = assert_w45_permit()
    out = (args.output_dir or RESULT_ROOT / "outer_once" / f"fold_{args.fold}").resolve()
    out.mkdir(parents=True, exist_ok=True)

    # The heavy full-volume sliding-window inference loop is wired here after
    # W4.5. G1 only validates that fixed decode/population semantics are the
    # actual imported functions and that this entrypoint is fail-closed pre-W4.5.
    synthetic_logits = torch.zeros(1, 6, 1, 1, 1)
    synthetic_availability = torch.tensor([[1.0, 0.0, 1.0]])
    decoded = decode_care_ase_r2_logits(synthetic_logits, synthetic_availability)
    if int(decoded.item()) == 4:
        raise RuntimeError("no-T2 fixed decode allowed class4")

    write_json(
        out / "outer_once_evaluator_receipt.json",
        {
            "status": "WIRED_WAITING_FOR_W5_RUNTIME",
            "fold": int(args.fold),
            "checkpoint": str(args.checkpoint),
            "w45_permit": permit,
            "decode": "fixed_argmax_t2_present_0_1_2_3_4_5_no_t2_0_1_2_3_5",
            "scar_population_function": scar_metric_population.__name__,
            "pure_edema_population_function": pure_edema_metric_population.__name__,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
