#!/usr/bin/env python3
"""Strict Route B Round04 B0 binding and manifest validator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


READY_TOKEN = "ROUTE_B_ROUND04_B0_READY_FOR_CONTROLLER_MERGE"
REQUIRED_FILES = [
    "source_fingerprint_audit.json",
    "round03_inheritance_matrix.json",
    "label_target_audit.json",
    "manifest_freeze_receipt.json",
    "same_split_baseline_receipt.json",
    "planning_snapshot_gate_receipt.json",
    "validator_fixture_index.json",
    "completion.json",
]
EXPECTED_FAILURE_KEYS = [
    "STALE_PLANNING_BINDING",
    "PLANNING_SOURCE_UNREADABLE",
    "PLANNING_SNAPSHOT_INCOMPLETE",
    "PLANNING_SNAPSHOT_HASH_MISMATCH",
    "CURRENT_REREVIEW_MISSING_OR_NOT_READY",
    "CURRENT_HANDOFF_MISSING",
    "CURRENT_COORDINATOR_RECEIPT_MISSING_OR_STALE",
    "DISALLOWED_MAIN_DESCENDANT_PATH",
    "ROUTE_EVIDENCE_REF_MISMATCH",
    "MANIFEST_HASH_MISMATCH",
    "ANATOMY_TARGET_LABEL_ROUNDTRIP_FAILED",
    "SAME_SPLIT_BASELINE_MISSING",
    "VALIDATOR_MATRIX_INCOMPLETE",
]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(errors: list[dict[str, str]], key: str, detail: str) -> None:
    errors.append({"key": key, "detail": detail})


def validate(result_dir: Path, require_token: str) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    payloads: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_FILES:
        path = result_dir / name
        if not path.is_file():
            add(errors, "PLANNING_SNAPSHOT_INCOMPLETE", f"missing {name}")
            continue
        try:
            payloads[name] = load(path)
        except Exception as exc:  # noqa: BLE001
            add(errors, "PLANNING_SNAPSHOT_INCOMPLETE", f"unreadable {name}: {exc}")
    if errors:
        return {"status": "FAIL", "errors": errors, "failure_keys": sorted({e["key"] for e in errors})}

    source = payloads["source_fingerprint_audit.json"]
    inherit = payloads["round03_inheritance_matrix.json"]
    labels = payloads["label_target_audit.json"]
    freeze = payloads["manifest_freeze_receipt.json"]
    baseline = payloads["same_split_baseline_receipt.json"]
    snapshot = payloads["planning_snapshot_gate_receipt.json"]
    fixtures = payloads["validator_fixture_index.json"]
    completion = payloads["completion.json"]

    if source.get("status") != "PASS":
        add(errors, "STALE_PLANNING_BINDING", "source fingerprint did not pass")
    if source.get("git_head") != source.get("origin_route_B"):
        add(errors, "STALE_PLANNING_BINDING", "route_B HEAD does not match origin/route_B")
    if source.get("origin_route_B") != source.get("expected_route_B"):
        add(errors, "ROUTE_EVIDENCE_REF_MISMATCH", "route_B evidence ref mismatch")
    source_sha = source.get("source_sha256", {})
    missing_blobs = [
        path
        for path, blob in source.get("source_blobs", {}).items()
        if not blob and "route_B_round04" not in path
    ]
    if missing_blobs:
        add(errors, "PLANNING_SOURCE_UNREADABLE", ",".join(missing_blobs))
    missing_new_sha = [
        path
        for path in source.get("source_blobs", {})
        if "route_B_round04" in path and len(str(source_sha.get(path, ""))) != 64
    ]
    if missing_new_sha:
        add(errors, "PLANNING_SOURCE_UNREADABLE", ",".join(missing_new_sha))

    for field in ("materialization_receipt_status", "manifest_status", "hash_audit_status", "descendant_diff_audit_status"):
        if snapshot.get(field) != "PASS":
            key = {
                "materialization_receipt_status": "PLANNING_SNAPSHOT_INCOMPLETE",
                "manifest_status": "CURRENT_HANDOFF_MISSING",
                "hash_audit_status": "PLANNING_SNAPSHOT_HASH_MISMATCH",
                "descendant_diff_audit_status": "DISALLOWED_MAIN_DESCENDANT_PATH",
            }[field]
            add(errors, key, f"{field}={snapshot.get(field)}")
    if snapshot.get("critic_token") != "ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER":
        add(errors, "CURRENT_REREVIEW_MISSING_OR_NOT_READY", "critic ready token missing")
    if snapshot.get("read_only_files") is not True:
        add(errors, "PLANNING_SNAPSHOT_INCOMPLETE", "snapshot files are writable")

    if freeze.get("status") != "PASS":
        add(errors, "MANIFEST_HASH_MISMATCH", "manifest freeze did not pass")
    if freeze.get("primary_case_count") != 44 or freeze.get("t2_edema_positive_count") != 16:
        add(errors, "MANIFEST_HASH_MISMATCH", "top-level MyoPS manifest counts changed")
    if freeze.get("cine_case_count") != 12:
        add(errors, "MANIFEST_HASH_MISMATCH", "top-level Cine manifest count changed")
    copied = freeze.get("copied_round04_manifests", {})
    expected_counts = {
        "myops_fold0_primary_44.json": 44,
        "myops_t2_edema_positive.json": 16,
        "cine_train12.json": 12,
    }
    for name, count in expected_counts.items():
        row = copied.get(name, {})
        if row.get("case_count") != count or len(str(row.get("sha256", ""))) != 64:
            add(errors, "MANIFEST_HASH_MISMATCH", f"{name} count/hash mismatch")
    centers = freeze.get("center_counts", {})
    if centers.get("CenterB", 0) <= 0 or centers.get("CenterC", 0) <= 0:
        add(errors, "MANIFEST_HASH_MISMATCH", "CenterB/CenterC missing")

    if labels.get("roundtrip_pass") is not True:
        add(errors, "ANATOMY_TARGET_LABEL_ROUNDTRIP_FAILED", "label roundtrip failed")
    if labels.get("anatomy_targets_compact") != {"union": [1, 4, 5], "lv": [2], "rv": [3]}:
        add(errors, "ANATOMY_TARGET_LABEL_ROUNDTRIP_FAILED", "anatomy compact targets changed")

    if baseline.get("status") != "PASS" or baseline.get("case_count") != 44:
        add(errors, "SAME_SPLIT_BASELINE_MISSING", "same split baseline missing")
    if baseline.get("round03_help_harm_status") != "PASS" or baseline.get("round03_safety_status") != "PASS":
        add(errors, "SAME_SPLIT_BASELINE_MISSING", "round03 baseline receipts not pass")

    if inherit.get("b3_only_adequate_negative") is not True or inherit.get("b3_cannot_stop_full_route") is not True:
        add(errors, "STALE_PLANNING_BINDING", "round03 inheritance semantics changed")
    if inherit.get("b4_b5_b6_training_credit") != 0 or inherit.get("b7_b8_b9_training_credit") != 0:
        add(errors, "STALE_PLANNING_BINDING", "round03 evidence credited to round04")

    if int(fixtures.get("fixture_count", 0)) < len(EXPECTED_FAILURE_KEYS):
        add(errors, "VALIDATOR_MATRIX_INCOMPLETE", "fixture count too small")
    listed = set(fixtures.get("fixtures", []))
    missing_fixture_keys = [key for key in EXPECTED_FAILURE_KEYS if key not in listed]
    if missing_fixture_keys:
        add(errors, "VALIDATOR_MATRIX_INCOMPLETE", ",".join(missing_fixture_keys))

    if completion.get("completion_token") != require_token or require_token != READY_TOKEN:
        add(errors, "CURRENT_COORDINATOR_RECEIPT_MISSING_OR_STALE", "completion token mismatch")
    if completion.get("status") != "PASS":
        add(errors, "CURRENT_COORDINATOR_RECEIPT_MISSING_OR_STALE", "completion status not pass")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "failure_keys": sorted({e["key"] for e in errors}),
        "required_token": require_token,
        "completion_token": completion.get("completion_token"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--require-token", default=READY_TOKEN)
    args = parser.parse_args()
    report = validate(args.input, args.require_token)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and report["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
