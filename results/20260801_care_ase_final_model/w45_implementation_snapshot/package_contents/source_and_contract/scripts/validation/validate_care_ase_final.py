#!/usr/bin/env python
"""Fail-closed final validator for CARE-ASE terminal packet."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


RESULT_DIR = REPO_ROOT / "results/20260801_care_ase_final_model"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_output(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.stdout.strip()


def add(checks: list[dict[str, Any]], name: str, ok: bool, evidence: Any) -> None:
    checks.append({"name": name, "status": "PASS" if ok else "FAIL", "evidence": evidence})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=RESULT_DIR)
    parser.add_argument("--require-git-clean", action="store_true")
    parser.add_argument("--require-remote-sha", action="store_true")
    args = parser.parse_args()
    result_dir = args.result_dir.resolve()
    checks: list[dict[str, Any]] = []

    contract = result_dir / "contract_coverage.json"
    preflight = result_dir / "w2_preflight_receipt.json"
    split_authority = result_dir / "split_authority_receipt.json"
    add(checks, "w1_contract_coverage_pass", contract.exists() and read_json(contract).get("status") == "PASS" and read_json(contract).get("remaining_gap_count") == 0, str(contract.relative_to(REPO_ROOT)) if contract.exists() else "missing")
    add(checks, "w2_preflight_pass", preflight.exists() and read_json(preflight).get("status") == "PASS", str(preflight.relative_to(REPO_ROOT)) if preflight.exists() else "missing")
    add(checks, "split_authority_pass", split_authority.exists() and read_json(split_authority).get("status") == "PASS", str(split_authority.relative_to(REPO_ROOT)) if split_authority.exists() else "missing")

    for fold in (2, 3):
        runtime = result_dir / "runtime" / f"fold_{fold}"
        terminal = runtime / "training_terminal_receipt.json"
        start_receipt = runtime / "training_start_receipt.json"
        checkpoint = runtime / "checkpoint_step14000.pt"
        evaluation = result_dir / "outer_eval" / f"fold_{fold}" / "evaluation_receipt.json"
        add(checks, f"fold{fold}_checkpoint_step14000_exists", checkpoint.exists(), str(checkpoint.relative_to(REPO_ROOT)) if checkpoint.exists() else "missing")
        add(checks, f"fold{fold}_training_terminal_pass", terminal.exists() and read_json(terminal).get("status") == "PASS" and read_json(terminal).get("global_optimizer_step") == 14000, str(terminal.relative_to(REPO_ROOT)) if terminal.exists() else "missing")
        add(checks, f"fold{fold}_training_inner_excluded", start_receipt.exists() and read_json(start_receipt).get("inner_excluded") is True, str(start_receipt.relative_to(REPO_ROOT)) if start_receipt.exists() else "missing")
        add(checks, f"fold{fold}_outer_eval_pass", evaluation.exists() and read_json(evaluation).get("status") == "PASS" and read_json(evaluation).get("global_optimizer_step") == 14000, str(evaluation.relative_to(REPO_ROOT)) if evaluation.exists() else "missing")

    mapper = result_dir / "mapper_final_receipt.json"
    controller = result_dir / "controller_report.md"
    freeze = result_dir / "checkpoint_freeze_receipt.json"
    reload_receipt = result_dir / "full_reload_parity_receipt.json"
    outer_audit = result_dir / "outer_access_audit_receipt.json"
    w45_snapshot = result_dir / "w45_implementation_snapshot" / "w45_implementation_snapshot_receipt.json"
    w45_push = result_dir / "w45_implementation_snapshot" / "w45_implementation_snapshot_push_receipt.json"
    w5 = result_dir / "w5_aggregation_receipt.json"
    add(checks, "w4_checkpoint_freeze_pass", freeze.exists() and read_json(freeze).get("status") == "PASS", str(freeze.relative_to(REPO_ROOT)) if freeze.exists() else "missing")
    add(checks, "w4_full_reload_parity_pass", reload_receipt.exists() and read_json(reload_receipt).get("status") == "PASS", str(reload_receipt.relative_to(REPO_ROOT)) if reload_receipt.exists() else "missing")
    add(checks, "w4_outer_access_before_freeze_zero", outer_audit.exists() and read_json(outer_audit).get("outer_access_count_before_freeze") == 0, str(outer_audit.relative_to(REPO_ROOT)) if outer_audit.exists() else "missing")
    add(checks, "w45_implementation_snapshot_pass", w45_snapshot.exists() and read_json(w45_snapshot).get("status") == "PASS", str(w45_snapshot.relative_to(REPO_ROOT)) if w45_snapshot.exists() else "missing")
    add(checks, "w45_implementation_snapshot_push_pass", w45_push.exists() and read_json(w45_push).get("status") == "PASS" and bool(read_json(w45_push).get("implementation_snapshot_commit_sha")), str(w45_push.relative_to(REPO_ROOT)) if w45_push.exists() else "missing")
    add(checks, "w5_aggregation_pass", w5.exists() and read_json(w5).get("status") == "PASS", str(w5.relative_to(REPO_ROOT)) if w5.exists() else "missing")
    add(checks, "mapper_final_receipt_exists", mapper.exists(), str(mapper.relative_to(REPO_ROOT)) if mapper.exists() else "missing")
    add(checks, "controller_report_exists", controller.exists(), str(controller.relative_to(REPO_ROOT)) if controller.exists() else "missing")

    if args.require_git_clean:
        status = git_output(["status", "--short"])
        add(checks, "git_status_clean_or_only_known_untracked_absent", status == "", status)
    if args.require_remote_sha:
        local = git_output(["rev-parse", "HEAD"])
        remote = git_output(["rev-parse", "origin/main"])
        add(checks, "local_remote_sha_equal", bool(local) and local == remote, {"HEAD": local, "origin/main": remote})

    receipt = {
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "checks": checks,
        "controller_verification_decision_if_used_now": "VERIFIED_COMPLETE" if all(row["status"] == "PASS" for row in checks) else "NEEDS_REPAIR",
    }
    out = result_dir / "final_validator_receipt.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True, default=str))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
