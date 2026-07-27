#!/usr/bin/env python3
"""Validate Gate A-R3 evidence status consistency."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260727_care_dg_dual_pathology_validation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    strict = load_json(RESULT_ROOT / "strict_validator_report.json")
    summary = load_json(RESULT_ROOT / "gate_a_summary.json")
    unit = (RESULT_ROOT / "unit_test_report.md").read_text(encoding="utf-8")
    known = load_json(RESULT_ROOT / "known_bad_report.json")
    impl = load_json(RESULT_ROOT / "implementation_contract.json")

    if strict.get("status") != "PASS":
        failures.append("strict_validator_not_PASS")
    if strict.get("failures") not in ([], None):
        failures.append("strict_validator_failures_nonempty")
    if "strict validator: `PASS`" not in unit:
        failures.append("unit_test_report_does_not_record_strict_PASS")
    if "DEFERRED" in unit or "`FAIL`" in unit:
        failures.append("unit_test_report_contains_FAIL_or_DEFERRED")
    if summary.get("strict_validator_status") != "PASS":
        failures.append("gate_a_summary_strict_not_PASS")
    if summary.get("gate_revision") != "A-R3":
        failures.append("gate_a_summary_not_R3")
    if summary.get("approval_token_required") != "APPROVE_GATE_A_R3":
        failures.append("gate_a_summary_wrong_approval_token")
    if str(summary).find("DEFERRED") >= 0 or str(summary).find("FAIL") >= 0:
        failures.append("gate_a_summary_contains_FAIL_or_DEFERRED")
    if known.get("status") != "PASS":
        failures.append("known_bad_not_PASS")
    if impl.get("status") != "GATE_A_REPAIRED_IMPLEMENTATION_PASS" or impl.get("gate_revision") != "A-R3":
        failures.append("implementation_contract_not_gate_A_R3_PASS")
    if summary.get("resolved_training_contract_sha256") != load_json(RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/resolved_training_contract.json").get("resolved_training_contract_sha256"):
        failures.append("resolved_contract_sha_mismatch")

    report = {
        "checked_at_utc": now_utc(),
        "status": "PASS" if not failures else "NEEDS_REPAIR",
        "failures": failures,
        "checked_files": [
            "results/20260727_care_dg_dual_pathology_validation/strict_validator_report.json",
            "results/20260727_care_dg_dual_pathology_validation/unit_test_report.md",
            "results/20260727_care_dg_dual_pathology_validation/gate_a_summary.json",
            "results/20260727_care_dg_dual_pathology_validation/known_bad_report.json",
            "results/20260727_care_dg_dual_pathology_validation/implementation_contract.json",
        ],
    }
    write_json(RESULT_ROOT / "gate_a_consistency_validator_report.json", report)
    summary["consistency_validator_status"] = report["status"]
    summary["consistency_validator_checked_at_utc"] = report["checked_at_utc"]
    write_json(RESULT_ROOT / "gate_a_summary.json", summary)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
