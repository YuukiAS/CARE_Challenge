#!/usr/bin/env python3
"""Cross-file consistency validator for CARE-DPR Gate A-R2 evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
DEFAULT_RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _sent_entries(sent: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(sent.get("sent_gates"), list):
        return list(sent["sent_gates"])
    if isinstance(sent.get("gates"), list):
        return list(sent["gates"])
    return [v for v in sent.values() if isinstance(v, dict)]


def check(result_root: Path) -> dict[str, Any]:
    runtime = result_root / "runtime/preflight"
    mechanism = load_json(runtime / "mechanism_report.json")
    strict = load_json(result_root / "strict_validator_report.json")
    implementation = load_json(result_root / "implementation_validator_report.json")
    receipt = load_json(runtime / "preflight_receipt.json")
    sampler = load_json(runtime / "sampler_audit_stage_preflight.json")
    optimizer_cases = load_json(runtime / "preflight_optimizer_cases.json")
    diagnostic_cases = load_json(runtime / "gate_a_r2_diagnostic_cases.json")
    r1_gate = load_json(result_root / "checkpoint_notifications/dpr_gate_a_r1.json")
    r1_send = load_json(result_root / "checkpoint_notifications/dpr_gate_a_r1_send_receipt.json")
    r2_gate = load_json(result_root / "checkpoint_notifications/dpr_gate_a_r2.json")
    r2_send = load_json(result_root / "checkpoint_notifications/dpr_gate_a_r2_send_receipt.json")
    sent = load_json(result_root / "checkpoint_notifications/sent_gates.json")
    impl_contract = load_json(result_root / "implementation_contract.json")
    entries = _sent_entries(sent)
    r1_entries = [e for e in entries if "APPROVE_DPR_GATE_A_R1" in json.dumps(e, ensure_ascii=False)]
    diagnostic_overlap = set(optimizer_cases.get("case_ids", [])) & set(diagnostic_cases.get("case_ids", []))
    utility = mechanism.get("utility_metrics") or {}
    two_pass = mechanism.get("two_pass_full_volume_candidate_pipeline") or {}
    checks = {
        "r1_gate_superseded": r1_gate.get("status") == "SUPERSEDED_BY_DPR_GATE_A_R2" and r1_gate.get("scientific_credit") == 0 and r1_gate.get("formal_fold0_authorized") is False,
        "r1_send_receipt_superseded": r1_send.get("status") == "SUPERSEDED_BY_DPR_GATE_A_R2" and r1_send.get("scientific_credit") == 0 and r1_send.get("formal_fold0_authorized") is False,
        "sent_r1_entries_superseded": all(e.get("status") == "SUPERSEDED_BY_DPR_GATE_A_R2" or e.get("formal_fold0_authorized") is False for e in r1_entries),
        "mechanism_passes_r2_thresholds": mechanism.get("status") == "PASS" and (mechanism.get("r2_thresholds") or {}).get("status") == "PASS",
        "strict_validator_pass": strict.get("status") == "PASS",
        "implementation_validator_pass": implementation.get("status") == "PASS",
        "preflight_receipt_zero_credit": receipt.get("status") == "PASS" and receipt.get("formal_training_credit") == 0,
        "diagnostic_cases_disjoint": bool(diagnostic_cases.get("case_ids")) and bool(optimizer_cases.get("case_ids")) and not diagnostic_overlap,
        "diagnostic_outer_fold0_not_used": diagnostic_cases.get("outer_fold0_used") is False and optimizer_cases.get("outer_fold0_used") is False and mechanism.get("outer_fold0_used") is False,
        "two_pass_real_candidate_pipeline": two_pass.get("status") == "PASS" and int(two_pass.get("component_utility_call_count", 0)) == int(utility.get("true_candidate_total_count", -1)),
        "real_candidate_utility_not_synthetic": utility.get("primary_metric_source") == "model_real_full_volume_candidates_only" and utility.get("synthetic_utility_variants_used_for_primary_gate") is False,
        "sampler_audit_pass": sampler.get("status") == "PASS",
        "no_t2_exact_zero": (mechanism.get("no_t2_exact_zero") or {}).get("status") == "PASS",
        "checkpoint_resume_exact": (mechanism.get("checkpoint_resume_exact") or {}).get("status") == "PASS",
        "formal_fold0_guard_r2_only": impl_contract.get("formal_fold0_guard") == "APPROVE_DPR_GATE_A_R2 required; APPROVE_DPR_GATE_A and APPROVE_DPR_GATE_A_R1 superseded",
        "r2_notification_prepared_or_sent": r2_gate.get("approval_token") in {"APPROVE_DPR_GATE_A_R2", None} and (not r2_send or r2_send.get("approval_token") == "APPROVE_DPR_GATE_A_R2"),
        "formal_fold0_authorized_false": r2_gate.get("formal_fold0_authorized", False) is False and r2_send.get("formal_fold0_authorized", False) is False,
    }
    failures = [name for name, ok in checks.items() if not ok]
    report = {
        "task_key": TASK_KEY,
        "gate": "DPR_GATE_A_R2",
        "status": "PASS" if not failures else "FAIL",
        "checked_at_utc": now_utc(),
        "checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()},
        "failures": failures,
        "formal_fold0_authorized": False,
        "valid_approval_token": "APPROVE_DPR_GATE_A_R2",
        "superseded_approval_tokens": ["APPROVE_DPR_GATE_A", "APPROVE_DPR_GATE_A_R1"],
    }
    write_json(result_root / "gate_a_r2_consistency_validator_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", default=str(DEFAULT_RESULT_ROOT))
    args = parser.parse_args()
    report = check(Path(args.result_root))
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
