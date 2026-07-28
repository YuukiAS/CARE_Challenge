#!/usr/bin/env python3
"""Cross-file consistency validator for CARE-DPR Gate A-R1 evidence."""

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


def check(result_root: Path) -> dict[str, Any]:
    mechanism = load_json(result_root / "runtime/preflight/mechanism_report.json")
    strict = load_json(result_root / "strict_validator_report.json")
    implementation = load_json(result_root / "implementation_validator_report.json")
    receipt = load_json(result_root / "runtime/preflight/preflight_receipt.json")
    sampler = load_json(result_root / "runtime/preflight/sampler_audit_stage_preflight.json")
    old_gate = load_json(result_root / "checkpoint_notifications/dpr_gate_a.json")
    old_send = load_json(result_root / "checkpoint_notifications/dpr_gate_a_send_receipt.json")
    sent = load_json(result_root / "checkpoint_notifications/sent_gates.json")
    impl_contract = load_json(result_root / "implementation_contract.json")

    sent_entries = sent.get("sent_gates") if isinstance(sent.get("sent_gates"), list) else sent.get("gates", [])
    old_sent_superseded = True
    if isinstance(sent_entries, list):
        old_entries = [e for e in sent_entries if "APPROVE_DPR_GATE_A" in json.dumps(e, ensure_ascii=False)]
        old_sent_superseded = all(e.get("status") == "SUPERSEDED_BY_DPR_GATE_A_R1" or e.get("formal_fold0_authorized") is False for e in old_entries)

    checks = {
        "old_gate_superseded": old_gate.get("status") == "SUPERSEDED_BY_DPR_GATE_A_R1" and old_gate.get("scientific_credit") == 0 and old_gate.get("formal_fold0_authorized") is False,
        "old_send_receipt_superseded": old_send.get("status") == "SUPERSEDED_BY_DPR_GATE_A_R1" and old_send.get("scientific_credit") == 0 and old_send.get("formal_fold0_authorized") is False,
        "sent_gate_entries_superseded": old_sent_superseded,
        "mechanism_passes_r1_thresholds": mechanism.get("status") == "PASS" and (mechanism.get("r1_thresholds") or {}).get("status") == "PASS",
        "strict_validator_pass": strict.get("status") == "PASS",
        "implementation_validator_pass": implementation.get("status") == "PASS",
        "preflight_receipt_zero_credit": receipt.get("status") == "PASS" and receipt.get("formal_training_credit") == 0,
        "sampler_audit_pass": sampler.get("status") == "PASS" and all(float(v) == 1.0 for v in (sampler.get("slot_hit_rates") or {}).values()),
        "formal_fold0_guard_new_token_only": impl_contract.get("formal_fold0_guard") == "APPROVE_DPR_GATE_A_R1 required; APPROVE_DPR_GATE_A superseded",
        "teacher_inner_outer_forbidden": mechanism.get("teacher_roi_inner_outer_inference") is False and mechanism.get("outer_fold0_used") is False,
        "no_t2_exact_zero": (mechanism.get("no_t2_exact_zero") or {}).get("status") == "PASS",
        "checkpoint_resume_exact": (mechanism.get("checkpoint_resume_exact") or {}).get("status") == "PASS",
    }
    failures = [name for name, ok in checks.items() if not ok]
    report = {
        "task_key": TASK_KEY,
        "status": "PASS" if not failures else "FAIL",
        "checked_at_utc": now_utc(),
        "checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()},
        "failures": failures,
        "formal_fold0_authorized": False,
        "valid_approval_token": "APPROVE_DPR_GATE_A_R1",
        "superseded_approval_token": "APPROVE_DPR_GATE_A",
    }
    write_json(result_root / "gate_a_r1_consistency_validator_report.json", report)
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
