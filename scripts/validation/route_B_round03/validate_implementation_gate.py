#!/usr/bin/env python3
"""Validate Route B Round03 B2 implementation-gate output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = [
    "implementation_gate.json",
    "gradient_intervention_report.csv",
    "save_reload_report.json",
    "cinema_real_frame_smoke.json",
    "official_cinema_source_report.json",
    "registration_temporal_smoke.json",
    "known_bad_selftest_report.md",
    "completion.json",
]

CINEMA_WEIGHT_SHA256 = "c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()
    errors = [f"missing:{name}" for name in REQUIRED if not (args.result_dir / name).is_file()]
    gate = {}
    if not errors:
        gate = json.loads((args.result_dir / "implementation_gate.json").read_text(encoding="utf-8"))
        cinema = json.loads((args.result_dir / "cinema_real_frame_smoke.json").read_text(encoding="utf-8"))
        official = json.loads((args.result_dir / "official_cinema_source_report.json").read_text(encoding="utf-8"))
        token = gate.get("completion_token")
        if token == "ROUTE_B_ROUND03_B2_IMPLEMENTATION_GATE_PASSED" and gate.get("status") != "PASS":
            errors.append("pass_token_without_pass_status")
        if token == "ROUTE_B_ROUND03_B2_EXTERNAL_RESOURCE_BLOCKER" and not gate.get("external_errors"):
            errors.append("external_blocker_without_external_errors")
        if token == "ROUTE_B_ROUND03_B2_IMPLEMENTATION_NEEDS_REVISION" and not gate.get("semantic_errors"):
            errors.append("needs_revision_without_semantic_errors")
        if gate.get("formal_training_submitted") is True:
            errors.append("formal_training_submitted_before_gate")
        if gate.get("monitor_state") is True or gate.get("submitted_only_state") is True:
            errors.append("monitor_or_submitted_state_in_b2")
        if official.get("status") != "PASS":
            errors.append("official_cinema_probe_not_pass")
        if official.get("observed_weight_sha256") != CINEMA_WEIGHT_SHA256:
            errors.append("official_cinema_weight_sha_mismatch")
        if official.get("missing_keys") or official.get("unexpected_keys"):
            errors.append("official_cinema_load_state_not_exact")
        if official.get("official_logits_shape") != [1, 4, 192, 192, 16]:
            errors.append("official_cinema_logits_shape_bad")
        if official.get("official_logits_finite") is not True:
            errors.append("official_cinema_logits_not_finite")
        if cinema.get("route_local_decoder_feature_shape", [None, None])[1] != 32:
            errors.append("route_local_cinema_decoder_feature_shape_bad")
        if cinema.get("route_local_projected_feature_shape", [None, None])[1] != 16:
            errors.append("route_local_cinema_projected_feature_shape_bad")
        if cinema.get("route_local_entropy_shape", [None, None])[1] != 1:
            errors.append("route_local_cinema_entropy_shape_bad")
    status = "PASS" if not errors and gate.get("status") == "PASS" else "FAIL"
    report = {"status": status, "errors": errors, "completion_token": gate.get("completion_token")}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and status != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
