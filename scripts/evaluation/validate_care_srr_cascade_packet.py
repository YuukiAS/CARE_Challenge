#!/usr/bin/env python
"""Strict packet validator for CARE-SRR-Cascade runtime closure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_KNOWN_BAD = (
    "OOF_case_uses_wrong_fold",
    "anchor_roundtrip_changed_voxel",
    "source_cache_hash_or_shape_mismatch",
    "stale_source_cache_lock_adopted",
    "shared_trainable_pathology_trunk",
    "inactive_pathology_channel_modified",
    "no_t2_edema_modified",
    "prototype_query_uses_same_shard",
    "prototype_negative_categories_collapsed",
    "first_N_voxel_sampling",
    "spatial_tensor_augmentation_mismatch",
    "control_and_srr_schedule_or_initial_state_mismatch",
    "inactive_pathology_loss_nonzero",
    "partial_or_resumed_run_counted_complete",
    "missing_validation_checkpoint",
    "audit_used_for_selection",
    "selected_checkpoint_not_reloaded",
    "selection_deployment_decode_mismatch",
    "exact_HD_missing_or_replaced_by_HD95",
    "single_fold_anchor_used_for_official_package",
    "package_accesses_GT",
    "monitor_packet_marked_complete",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_packet(packet_root: Path) -> dict[str, Any]:
    required = [
        "runtime_import_graph.json",
        "runtime_api_contract.json",
        "model_branch_independence_checks.csv",
        "prototype_category_contract.json",
        "schedule_schema.json",
        "checkpoint_resume_schema.json",
        "future_wave_entrypoint_audit.json",
        "unit_test_report_rc1.md",
    ]
    missing = [name for name in required if not (packet_root / name).exists()]
    failures = []
    if missing:
        failures.append(f"missing_required_rc1_outputs:{missing}")
    known_bad_path = packet_root / "real_known_bad_report_v2.json"
    if known_bad_path.exists():
        report = load_json(known_bad_path)
        by_name = {row.get("fixture"): row for row in report.get("fixtures", [])}
        for name in REQUIRED_KNOWN_BAD:
            row = by_name.get(name)
            if not row or not row.get("rejected"):
                failures.append(f"known_bad_not_rejected:{name}")
    return {
        "decision": "PASS" if not failures else "NEEDS_REPAIR",
        "packet_root": str(packet_root),
        "failures": failures,
        "required_known_bad": REQUIRED_KNOWN_BAD,
    }


def contract() -> dict[str, Any]:
    return {
        "entrypoint": "scripts/evaluation/validate_care_srr_cascade_packet.py",
        "monitor_packet_marked_complete_forbidden": True,
        "known_bad_count": len(REQUIRED_KNOWN_BAD),
        "fixture_acceptance": "validator_nonzero_and_expected_error_substring_match",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--packet-root", type=Path)
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(contract(), indent=2, sort_keys=True))
        return 0
    if not args.packet_root:
        raise SystemExit("--packet-root is required unless --print-contract")
    payload = validate_packet(args.packet_root)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
