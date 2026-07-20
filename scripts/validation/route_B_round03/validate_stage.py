#!/usr/bin/env python3
"""Validate Route B Round03 B3-B5 staged MyoPS receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.route_B_round03.runtime_common import expected_frozen_sampler_counts  # noqa: E402


TOKENS = {
    "evidence_warmup": "ROUTE_B_ROUND03_B3_EVIDENCE_WARMUP_PASSED",
    "proposal": "ROUTE_B_ROUND03_B4_PROPOSAL_GATE_PASSED",
    "refiner": "ROUTE_B_ROUND03_B5_REFINER_GATE_PASSED",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(TOKENS))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    completion = args.result_dir / "completion.json"
    for name in ("completion.json", "training_adequacy.csv", "metrics_summary.csv"):
        if not (args.result_dir / name).is_file():
            errors.append(f"missing:{name}")
    payload = {}
    if completion.is_file():
        payload = json.loads(completion.read_text(encoding="utf-8"))
        if payload.get("stage") != args.stage:
            errors.append("stage_mismatch")
        if payload.get("completion_token") != TOKENS[args.stage]:
            errors.append("completion_token_not_pass")
        if payload.get("status") != "PASS":
            errors.append("status_not_pass")
        checks = payload.get("gate_checks", {})
        for key, value in checks.items():
            if value is not True:
                errors.append(f"gate_check_failed:{key}")
        if payload.get("optimizer_steps", 0) < payload.get("required_optimizer_steps", 10**12):
            errors.append("optimizer_steps_under_required")
        if payload.get("train_loop_seconds", 0.0) < payload.get("required_train_loop_seconds", 10**12):
            errors.append("train_loop_seconds_under_required")
        if payload.get("validation_events", 0) < payload.get("required_validation_events", 10**12):
            errors.append("validation_events_under_required")
        if args.stage == "evidence_warmup":
            for name in ("sampler_counts.csv", "sampler_sequence_prefix.csv", "sampler_sequence_receipt.json"):
                if not (args.result_dir / name).is_file():
                    errors.append(f"missing_sampler_evidence:{name}")
            counts = payload.get("sampler_counts", {})
            expected = payload.get("expected_sampler_counts") or expected_frozen_sampler_counts(int(payload.get("optimizer_steps", 0)))
            if counts != expected:
                errors.append("frozen_sampler_counts_mismatch")
            contract = payload.get("sampler_contract", {})
            if contract.get("draw_cycle") != ["E", "E", "S", "R"]:
                errors.append("frozen_sampler_bad_draw_cycle")
            if contract.get("philox_seed") != 26071821:
                errors.append("frozen_sampler_bad_seed")
            if contract.get("rng") != "numpy.random.Philox":
                errors.append("frozen_sampler_bad_rng")
            if contract.get("with_replacement") is not True:
                errors.append("frozen_sampler_not_with_replacement")
            if int(contract.get("cycle_mismatch_count", -1)) != 0:
                errors.append("frozen_sampler_sequence_mismatch")
            if not contract.get("trace_sha256"):
                errors.append("frozen_sampler_missing_trace_sha256")
    status = "PASS" if not errors else "FAIL"
    print(json.dumps({"status": status, "errors": errors, "completion_token": payload.get("completion_token")}, indent=2, sort_keys=True))
    return 1 if args.strict and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
