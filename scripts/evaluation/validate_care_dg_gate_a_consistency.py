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
    preflight_label = str(summary.get("active_preflight_runtime_label") or "gate_a_r3_preflight")
    preflight_contract = RESULT_ROOT / "runtime" / preflight_label / "fold0/resolved_training_contract.json"
    if summary.get("resolved_training_contract_sha256") != load_json(preflight_contract).get("resolved_training_contract_sha256"):
        failures.append("resolved_contract_sha_mismatch")

    gate_b_summary_path = RESULT_ROOT / "gate_b_summary.json"
    gate_b_validator_path = RESULT_ROOT / "runtime/repaired_formal_scar_priority/fold0/gate_b_evaluation/gate_b_validator_report.json"
    gate_b_r1_summary_path = RESULT_ROOT / "gate_b_r1_summary.json"
    gate_b_r1_validator_path = RESULT_ROOT / "runtime/repaired_formal_scar_priority/fold0/gate_b_r1_evaluation/gate_b_r1_validator_report.json"
    gate_b_r2_summary_path = RESULT_ROOT / "gate_b_r2_summary.json"
    gate_b_r2_validator_path = RESULT_ROOT / "gate_b_r2_validator_report.json"
    gate_b_failures: list[str] = []
    gate_b_summary = load_json(gate_b_summary_path) if gate_b_summary_path.exists() else None
    gate_b_validator = load_json(gate_b_validator_path) if gate_b_validator_path.exists() else None
    if gate_b_summary is not None or gate_b_validator is not None:
        if gate_b_summary is None:
            gate_b_failures.append("gate_b_summary_missing")
        elif gate_b_summary.get("status") not in {"PASS", "GATE_B_OVERACTIVE_FRAGMENTED_CORRECTION_DIAGNOSTIC"}:
            gate_b_failures.append("gate_b_summary_status_bad")
        elif gate_b_summary.get("status") == "GATE_B_OVERACTIVE_FRAGMENTED_CORRECTION_DIAGNOSTIC" and gate_b_summary.get("scientific_expansion_authorized") is not False:
            gate_b_failures.append("gate_b_diagnostic_scientific_expansion_not_false")
        if gate_b_validator is None:
            gate_b_failures.append("gate_b_validator_missing")
        elif gate_b_validator.get("status") != "PASS" or gate_b_validator.get("failures") not in ([], None):
            gate_b_failures.append("gate_b_validator_not_PASS")
        if strict.get("status") != "PASS" or strict.get("failures") not in ([], None):
            gate_b_failures.append("strict_validator_not_PASS_for_gate_b")
        if gate_b_summary is not None:
            if gate_b_summary.get("outer_heldout_cases") != 44:
                gate_b_failures.append("gate_b_outer44_count_bad")
            if gate_b_summary.get("complete_trimodal_heldout_cases") != 16:
                gate_b_failures.append("gate_b_complete16_count_bad")
            if gate_b_summary.get("post_scar_decision_overwritten_voxels") != 0:
                gate_b_failures.append("gate_b_post_scar_overwrite_nonzero")
            if gate_b_summary.get("no_t2_edema_delta_exact_zero") is not True:
                gate_b_failures.append("gate_b_no_t2_not_exact_zero")

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
    gate_b_report = {
        "checked_at_utc": report["checked_at_utc"],
        "status": "PASS" if not gate_b_failures else "NEEDS_REPAIR",
        "failures": gate_b_failures,
        "checked_files": [
            "results/20260727_care_dg_dual_pathology_validation/gate_b_summary.json",
            "results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/gate_b_evaluation/gate_b_validator_report.json",
            "results/20260727_care_dg_dual_pathology_validation/gate_b_r1_summary.json",
            "results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/gate_b_r1_evaluation/gate_b_r1_validator_report.json",
            "results/20260727_care_dg_dual_pathology_validation/gate_b_r2_summary.json",
            "results/20260727_care_dg_dual_pathology_validation/gate_b_r2_validator_report.json",
            "results/20260727_care_dg_dual_pathology_validation/strict_validator_report.json",
        ],
    }
    if gate_b_r1_summary_path.exists() or gate_b_r1_validator_path.exists():
        if not gate_b_r1_summary_path.exists():
            gate_b_failures.append("gate_b_r1_summary_missing")
        if not gate_b_r1_validator_path.exists():
            gate_b_failures.append("gate_b_r1_validator_missing")
        if gate_b_r1_summary_path.exists() and gate_b_r1_validator_path.exists():
            r1_summary = load_json(gate_b_r1_summary_path)
            r1_validator = load_json(gate_b_r1_validator_path)
            if r1_validator.get("status") != "PASS" or r1_validator.get("failures") not in ([], None):
                gate_b_failures.append("gate_b_r1_validator_not_PASS")
            if (r1_summary.get("scientific_gate") or {}).get("scientific_expansion_authorized") != r1_validator.get("scientific_expansion_authorized"):
                gate_b_failures.append("gate_b_r1_scientific_authorization_mismatch")
    if gate_b_r2_summary_path.exists() or gate_b_r2_validator_path.exists():
        if not gate_b_r2_summary_path.exists():
            gate_b_failures.append("gate_b_r2_summary_missing")
        if not gate_b_r2_validator_path.exists():
            gate_b_failures.append("gate_b_r2_validator_missing")
        if gate_b_r2_summary_path.exists() and gate_b_r2_validator_path.exists():
            r2_summary = load_json(gate_b_r2_summary_path)
            r2_validator = load_json(gate_b_r2_validator_path)
            if r2_validator.get("status") != "PASS" or r2_validator.get("failures") not in ([], None):
                gate_b_failures.append("gate_b_r2_validator_not_PASS")
            if r2_summary.get("scientific_expansion_authorized") is not False:
                gate_b_failures.append("gate_b_r2_scientific_expansion_not_false")
            if r2_validator.get("eligible_count") != 0:
                gate_b_failures.append("gate_b_r2_eligible_count_not_zero")
            if r2_validator.get("outer_val_used") is not False:
                gate_b_failures.append("gate_b_r2_outer_val_used")
    gate_b_report["status"] = "PASS" if not gate_b_failures else "NEEDS_REPAIR"
    gate_b_report["failures"] = gate_b_failures
    write_json(RESULT_ROOT / "gate_a_consistency_validator_report.json", report)
    write_json(RESULT_ROOT / "gate_b_consistency_validator_report.json", gate_b_report)
    summary["consistency_validator_status"] = report["status"]
    summary["consistency_validator_checked_at_utc"] = report["checked_at_utc"]
    write_json(RESULT_ROOT / "gate_a_summary.json", summary)
    if gate_b_summary is not None:
        gate_b_summary["strict_validator_status"] = strict.get("status")
        gate_b_summary["consistency_validator_status"] = gate_b_report["status"]
        gate_b_summary["consistency_validator_checked_at_utc"] = gate_b_report["checked_at_utc"]
        write_json(gate_b_summary_path, gate_b_summary)
    print(json.dumps({"gate_a": report, "gate_b": gate_b_report}, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" and gate_b_report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
