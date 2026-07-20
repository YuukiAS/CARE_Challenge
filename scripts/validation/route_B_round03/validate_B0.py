#!/usr/bin/env python3
"""Strict B0 validator for Route B Round03 assets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED = [
    "source_probe.json",
    "manifest_freeze_receipt.json",
    "sampler_contract.json",
    "validator_fixture_index.json",
    "partition_static_matrix.json",
    "completion.json",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(result_dir: Path) -> dict:
    errors: list[str] = []
    for name in REQUIRED:
        if not (result_dir / name).is_file():
            errors.append(f"missing:{name}")
    if errors:
        return {"status": "FAIL", "errors": errors}

    source = load(result_dir / "source_probe.json")
    freeze = load(result_dir / "manifest_freeze_receipt.json")
    sampler = load(result_dir / "sampler_contract.json")
    fixtures = load(result_dir / "validator_fixture_index.json")
    matrix = load(result_dir / "partition_static_matrix.json")
    completion = load(result_dir / "completion.json")

    if source.get("canonical_modality_order") != ["LGE", "T2", "C0"]:
        errors.append("canonical_modality_order_not_LGE_T2_C0")
    if source.get("legacy_order_rejected") != ["LGE", "C0", "T2"]:
        errors.append("legacy_order_not_recorded_as_rejected")
    if not all(source.get("source_blobs", {}).values()):
        errors.append("missing_source_blob")
    if freeze.get("primary_case_count") != 44:
        errors.append("primary_case_count_not_44")
    if int(freeze.get("t2_edema_positive_count", 0)) < 8:
        errors.append("fewer_than_eight_t2_edema_positive")
    centers = freeze.get("center_counts", {})
    if centers.get("CenterB", 0) <= 0 or centers.get("CenterC", 0) <= 0:
        errors.append("missing_centerB_or_centerC")
    if freeze.get("cine_case_count") != 12:
        errors.append("cine_case_count_not_12")
    if set(freeze.get("cine_center_counts", {}).values()) != {6}:
        errors.append("cine_center_balance_not_6_each")
    for key in ("primary_sha256", "edema_sha256", "sampler_sha256", "cine_sha256"):
        if len(str(freeze.get(key, ""))) != 64:
            errors.append(f"bad_sha:{key}")
    if sampler.get("draw_cycle") != ["E", "E", "S", "R"]:
        errors.append("sampler_cycle_not_EESR")
    if sampler.get("philox_seed") != 26071821:
        errors.append("sampler_seed_mismatch")
    if int(fixtures.get("fixture_count", 0)) < 10:
        errors.append("fixture_index_too_small")
    race = matrix.get("race_rules", {})
    for key in (
        "scientific_hashes_identical",
        "isolated_output_log_checkpoint_cache_roots",
        "atomic_winner_lock_required",
        "pending_loser_cancellation_required",
        "retry_lineage_required",
        "all_attempt_finalizer_coverage_required",
        "v100_semantic_downscaling_forbidden",
    ):
        if race.get(key) is not True:
            errors.append(f"race_rule_missing:{key}")
    if completion.get("completion_token") != "ROUTE_B_ROUND03_B0_READY_FOR_CONTROLLER_MERGE":
        errors.append("completion_token_not_ready")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "t2_edema_positive_count": freeze.get("t2_edema_positive_count"),
        "cine_case_count": freeze.get("cine_case_count"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()
    report = validate(args.result_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and report["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
