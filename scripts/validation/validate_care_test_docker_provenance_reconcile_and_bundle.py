#!/usr/bin/env python3
"""Validate the CARE Docker provenance reconcile packet."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
TASK_KEY = "20260801_care_test_docker_provenance_reconcile_and_bundle"
RESULT_DIR = REPO / "results" / TASK_KEY
RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine")
TRANSFER = RUNTIME / "transfer"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add(errors: list[str], message: str) -> None:
    errors.append(message)


def require_file(errors: list[str], path: Path) -> bool:
    if not path.is_file():
        add(errors, f"missing file: {path}")
        return False
    return True


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def validate_labelwise(errors: list[str]) -> dict[str, Any]:
    summary_path = RESULT_DIR / "nnunet_used_channel_equivalence_summary.json"
    casewise_path = RESULT_DIR / "nnunet_labelwise_equivalence_casewise.csv"
    transition_path = RESULT_DIR / "nnunet_label_transition_counts.csv"
    for path in (summary_path, casewise_path, transition_path):
        require_file(errors, path)
    if not summary_path.is_file() or not casewise_path.is_file():
        return {}
    summary = read_json(summary_path)
    rows = csv_rows(casewise_path)
    if len(rows) != 15:
        add(errors, "labelwise casewise CSV must contain 15 cases")
    if summary.get("geometry_equal_count") != 15:
        add(errors, "W1 requires 15/15 geometry equality before later decisions")
    if summary.get("token") == "NNUNET_USED_CHANNELS_PROVENANCE_REPRODUCED":
        if summary.get("anatomy_123_multiclass_equal_count") != 15:
            add(errors, "used-channel reproduced token requires anatomy 1/2/3 multiclass 15/15")
        if summary.get("pure_edema_class4_equal_count") != 15:
            add(errors, "used-channel reproduced token requires class4 15/15")
    if summary.get("anatomy_union_equal_count") == 15 and summary.get("anatomy_123_multiclass_equal_count") != 15:
        add(errors, "anatomy union equality must not substitute for 1/2/3 multiclass equality")
    return summary


def validate_variants(errors: list[str]) -> dict[str, Any]:
    manifest_path = RESULT_DIR / "nnunet_replay_variant_manifest.json"
    casewise_path = RESULT_DIR / "nnunet_replay_variant_casewise.csv"
    decision_path = RESULT_DIR / "nnunet_replay_variant_decision.json"
    for path in (manifest_path, casewise_path, decision_path):
        require_file(errors, path)
    if not manifest_path.is_file() or not decision_path.is_file():
        return {}
    manifest = read_json(manifest_path)
    decision = read_json(decision_path)
    if len(manifest) > 3:
        add(errors, "W3 replay variant count exceeds three")
    allowed_order = ["v1_final_default_tta", "v2_best_no_tta", "v3_final_no_tta"]
    names = [row.get("variant") for row in manifest]
    if names != allowed_order[: len(names)]:
        add(errors, f"W3 variants are out of contract order: {names}")
    selected = decision.get("selected_variant")
    if selected:
        found = next((row for row in manifest if row.get("variant") == selected), None)
        if not found or found.get("decision") not in {"FULL_ARRAY_EXACT_15_OF_15", "USED_CHANNELS_1234_EXACT_15_OF_15"}:
            add(errors, "selected variant is not exact; closest-match selection is forbidden")
    if decision.get("historical_0_6691_claim_authorized") is not False:
        add(errors, "historical 0.6691 claim must remain unauthorized")
    return decision


def validate_deployable(errors: list[str]) -> dict[str, Any]:
    receipt_path = RESULT_DIR / "nnunet_deployable_source_receipt.json"
    casewise_path = RESULT_DIR / "nnunet_deployable_repeat_casewise.csv"
    split_path = RESULT_DIR / "nnunet_lineage_vs_deployment_decision.json"
    for path in (receipt_path, casewise_path, split_path):
        require_file(errors, path)
    if not receipt_path.is_file() or not casewise_path.is_file():
        return {}
    receipt = read_json(receipt_path)
    rows = csv_rows(casewise_path)
    if len(rows) != 15:
        add(errors, "deployable repeat casewise CSV must contain 15 cases")
    if receipt.get("geometry_equal_count") != 15:
        add(errors, "deployable repeat geometry equality must be 15/15")
    if receipt.get("token") == "NNUNET_DEPLOYABLE_SOURCE_REPRODUCED" and receipt.get("array_equal_count") != 15:
        add(errors, "deployable reproduced token requires two-run array equality 15/15")
    if receipt.get("token") == "NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC" and receipt.get("array_equal_count") == 15:
        add(errors, "non-deterministic token is invalid when array equality is 15/15")
    return receipt


def validate_terminal(errors: list[str], deploy: dict[str, Any]) -> str | None:
    finalizer_path = RESULT_DIR / "finalizer_state.json"
    require_file(errors, finalizer_path)
    finalizer = read_json(finalizer_path) if finalizer_path.is_file() else {}
    terminal_state = finalizer.get("terminal_state")
    if terminal_state not in {"SERVER_BUNDLE_READY", "SERVER_BUNDLE_BLOCKED"}:
        add(errors, f"invalid terminal_state: {terminal_state!r}")
    ready = TRANSFER / "SERVER_BUNDLE_READY.json"
    blocked = TRANSFER / "SERVER_BUNDLE_BLOCKED.json"
    if terminal_state == "SERVER_BUNDLE_READY":
        require_file(errors, ready)
        if deploy.get("token") != "NNUNET_DEPLOYABLE_SOURCE_REPRODUCED":
            add(errors, "ready packet requires deployable source reproduction when no historical exact variant exists")
    if terminal_state == "SERVER_BUNDLE_BLOCKED":
        if ready.exists():
            add(errors, "SERVER_BUNDLE_READY marker must not exist for blocked terminal state")
        require_file(errors, blocked)
        if finalizer.get("blocking_token") != "NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC":
            add(errors, "blocked packet must identify the current hard blocker")
    return terminal_state


def validate_git_scope(errors: list[str]) -> None:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    forbidden_suffixes = (".nii", ".nii.gz", ".pt", ".pth", ".zip", ".tar", ".tar.gz")
    for name in [line.strip() for line in proc.stdout.splitlines() if line.strip()]:
        if name.endswith(forbidden_suffixes):
            add(errors, f"forbidden binary/model/archive staged: {name}")
    for base in (RESULT_DIR, REPO / "docker" / "CARE2026_Myocardium"):
        if not base.exists():
            continue
        for pattern in ("*.nii", "*.nii.gz", "*.pt", "*.pth", "*.zip", "*.tar", "*.tar.gz"):
            for bad in base.rglob(pattern):
                add(errors, f"forbidden binary/model/archive inside tracked scope: {bad.relative_to(REPO)}")


def validate_notification(errors: list[str]) -> None:
    path = RESULT_DIR / "notification_brief.json"
    require_file(errors, path)
    if not path.is_file():
        return
    data = read_json(path)
    if data.get("final_status") not in {"complete", "blocked"}:
        add(errors, "notification_brief final_status must be complete or blocked")
    text = path.read_text(encoding="utf-8", errors="replace")
    for forbidden in ("PENDING", "RUNNING", "NEEDS_MONITOR", "JOB_SUBMITTED", "AWAITING_SACCT"):
        if forbidden in text:
            add(errors, f"notification_brief contains forbidden nonterminal token: {forbidden}")


def main() -> int:
    errors: list[str] = []
    for name in (
        "controller_context.json",
        "controller_ledger.csv",
        "historical_package_generation_trace.md",
        "historical_environment_fingerprint.json",
        "historical_asset_candidate_manifest.json",
        "fresh_mosaic_cine_15case_manifest.json",
        "fresh_mosaic_cine_15case_receipt.json",
        "source_intervention_receipt.json",
        "sentinel_manifest.json",
        "transfer_bundle_receipt.json",
        "mapper_report_final.md",
        "finalizer_state.json",
        "controller_report.md",
        "completion_check.md",
        "MANIFEST.md",
    ):
        require_file(errors, RESULT_DIR / name)
    validate_labelwise(errors)
    validate_variants(errors)
    deploy = validate_deployable(errors)
    terminal_state = validate_terminal(errors, deploy)
    validate_notification(errors)
    validate_git_scope(errors)
    report = {
        "status": "FAIL" if errors else "PASS",
        "task_key": TASK_KEY,
        "terminal_state": terminal_state,
        "blocking_token": read_json(RESULT_DIR / "finalizer_state.json").get("blocking_token")
        if (RESULT_DIR / "finalizer_state.json").is_file()
        else None,
        "errors": errors,
    }
    (RESULT_DIR / "strict_validator_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
