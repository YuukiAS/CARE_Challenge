#!/usr/bin/env python3
"""Fail-closed validator for the CARE rootless Docker unblock packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
TASK_KEY = "20260801_care_test_docker_rootless_unblock"
RESULT_DIR = REPO / "results" / TASK_KEY

ALLOWED_FINAL_STATES = {
    "TEST_DOCKERS_READY_FOR_USER_EMAIL_SUBMISSION",
    "DOCKERS_READY_WITH_GPU_RUNTIME_REQUEST",
    "ROOTLESS_DOCKER_PREREQUISITE_BLOCKED",
    "NNUNET_PROVENANCE_REPLAY_MISMATCH",
    "DOCKER_DEPENDENCY_LOCK_BLOCKED",
    "DOCKER_RUNTIME_OR_EQUIVALENCE_BLOCKED",
}

FORBIDDEN_READY_WORDS = {
    "PENDING",
    "RUNNING",
    "NEEDS_MONITOR",
    "JOB_SUBMITTED",
    "AWAITING_SACCT",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_blocked_prereq(errors: list[str]) -> None:
    prereq_path = RESULT_DIR / "rootless_prerequisite_audit.json"
    storage_path = RESULT_DIR / "rootless_storage_receipt.json"
    install_path = RESULT_DIR / "rootless_install_receipt.json"
    for path in (prereq_path, storage_path, install_path):
        if not path.is_file():
            fail(errors, f"missing required rootless evidence: {path.relative_to(REPO)}")
    if errors:
        return

    prereq = read_json(prereq_path)
    hard = prereq.get("hard_requirements", {})
    required_keys = {
        "arch_x86_64_or_amd64",
        "unprivileged_user_namespace_works",
        "newuidmap_exists",
        "newgidmap_exists",
        "subuid_at_least_65536",
        "subgid_at_least_65536",
        "writable_local_docker_data_root",
    }
    missing = sorted(required_keys.difference(hard))
    if missing:
        fail(errors, f"rootless hard requirement keys missing: {missing}")
    if prereq.get("rootless_prerequisite_decision") != "FAIL":
        fail(errors, "blocked prerequisite packet must record rootless_prerequisite_decision=FAIL")
    if hard.get("subuid_at_least_65536") is not False:
        fail(errors, "blocked prerequisite packet must prove subuid_at_least_65536=false")
    if hard.get("subgid_at_least_65536") is not False:
        fail(errors, "blocked prerequisite packet must prove subgid_at_least_65536=false")
    if prereq.get("subuid_total") != 0:
        fail(errors, "expected current-user subuid_total=0 for this blocked evidence")
    if prereq.get("subgid_total") != 0:
        fail(errors, "expected current-user subgid_total=0 for this blocked evidence")

    storage = read_json(storage_path)
    if storage.get("decision") != "PASS":
        fail(errors, "storage receipt should identify the local writable Docker data root separately")
    if storage.get("selected_docker_data_root") != "/tmp/aereinh/care-rootless-docker-data":
        fail(errors, "unexpected selected Docker data root")

    install = read_json(install_path)
    if install.get("download_returncode") != 0:
        fail(errors, "official rootless Docker installer was not downloaded successfully")
    if not install.get("script_exists"):
        fail(errors, "official rootless Docker installer script is missing")
    if not install.get("script_sha256"):
        fail(errors, "official rootless Docker installer SHA256 is missing")
    if install.get("install_executed") is not False:
        fail(errors, "install must not be marked executed after hard prerequisite failure")
    skip_reason = install.get("install_skip_reason", "")
    if "subuid" not in skip_reason or "subgid" not in skip_reason:
        fail(errors, "install skip reason must name the subordinate uid/gid blocker")


def validate_common(errors: list[str]) -> dict[str, Any] | None:
    finalizer_path = RESULT_DIR / "finalizer_state.json"
    if not finalizer_path.is_file():
        fail(errors, "missing finalizer_state.json")
        return None
    finalizer = read_json(finalizer_path)
    state = finalizer.get("terminal_state")
    if state not in ALLOWED_FINAL_STATES:
        fail(errors, f"terminal_state is not allowed: {state!r}")
    if finalizer.get("docker_upload_authorized") is not False:
        fail(errors, "docker_upload_authorized must be false")
    if finalizer.get("organizer_email_send_authorized") is not False:
        fail(errors, "organizer_email_send_authorized must be false")
    if finalizer.get("new_training_authorized") is not False:
        fail(errors, "new_training_authorized must be false")
    return finalizer


def validate_ready(errors: list[str]) -> None:
    required = [
        "fresh_nnunet_15case_manifest.json",
        "fresh_nnunet_vs_historical_casewise.csv",
        "fresh_nnunet_provenance_receipt.json",
        "fresh_mosaic_myops_15case_manifest.json",
        "fresh_mosaic_cine_15case_manifest.json",
        "mosaic_frozen_replay_receipt.json",
        "docker_build_receipt.json",
        "docker_export_manifest.json",
        "docker_prediction_equivalence.csv",
        "docker_output_geometry_audit.csv",
        "myops_source_intervention.csv",
        "submission_email_draft_myops.md",
        "submission_email_draft_cinemyops.md",
    ]
    for name in required:
        if not (RESULT_DIR / name).is_file():
            fail(errors, f"ready packet missing {name}")


def validate(paths_only: bool = False) -> int:
    errors: list[str] = []
    finalizer = validate_common(errors)
    terminal_state = finalizer.get("terminal_state") if finalizer else None
    if terminal_state == "ROOTLESS_DOCKER_PREREQUISITE_BLOCKED":
        validate_blocked_prereq(errors)
    elif terminal_state in {
        "TEST_DOCKERS_READY_FOR_USER_EMAIL_SUBMISSION",
        "DOCKERS_READY_WITH_GPU_RUNTIME_REQUEST",
    }:
        validate_ready(errors)

    for name in ("completion_check.md", "controller_report.md", "MANIFEST.md", "notification_brief.json"):
        path = RESULT_DIR / name
        if not path.is_file():
            fail(errors, f"missing terminal packet file: {name}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if name == "notification_brief.json":
            try:
                brief = json.loads(text)
            except json.JSONDecodeError as exc:
                fail(errors, f"notification_brief.json is invalid JSON: {exc}")
                continue
            if brief.get("final_status") not in {"complete", "blocked"}:
                fail(errors, "notification_brief.json final_status must be complete or blocked")
            for forbidden in FORBIDDEN_READY_WORDS:
                if forbidden in text:
                    fail(errors, f"notification_brief.json contains forbidden nonterminal token {forbidden}")

    report = {
        "status": "FAIL" if errors else "PASS",
        "task_key": TASK_KEY,
        "terminal_state": terminal_state,
        "errors": errors,
    }
    out_path = RESULT_DIR / "strict_validator_report.json"
    if not paths_only:
        out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paths-only", action="store_true")
    args = parser.parse_args()
    return validate(paths_only=args.paths_only)


if __name__ == "__main__":
    sys.exit(main())
