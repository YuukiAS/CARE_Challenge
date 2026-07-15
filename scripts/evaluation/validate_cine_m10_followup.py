#!/usr/bin/env python3
"""Validate M10 follow-up Cine F2 implementation-fidelity packet."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "results/20260714_srr_v3_m10_followup_cine_fidelity"
REQUIRED = [
    "result.md",
    "cine_fidelity_gap_closure.csv",
    "cinema_provenance_contract.json",
    "cinema_adapter_control_contract.json",
    "registration_math_contract.md",
    "syn_control_contract.md",
    "temporal_dictionary_contract.md",
    "unit_test_report.md",
    "known_bad_selftest_report.md",
    "freeze_receipt.json",
    "commands_run.md",
    "executor_completion.md",
    "MANIFEST.md",
]


def main() -> None:
    findings: list[str] = []
    for name in REQUIRED:
        if not (OUT_DIR / name).is_file():
            findings.append(f"missing required file: {name}")
    if (OUT_DIR / "freeze_receipt.json").is_file():
        receipt = json.loads((OUT_DIR / "freeze_receipt.json").read_text(encoding="utf-8"))
        if receipt.get("status") != "FROZEN_FOR_WAVE_F3":
            findings.append("freeze receipt status is not FROZEN_FOR_WAVE_F3")
        if len(str(receipt.get("freeze_hash", ""))) != 64:
            findings.append("freeze_hash missing or invalid length")
        if int(receipt.get("unit_test_exit_code", 1)) != 0:
            findings.append("unit tests did not pass")
    for job_name in (
        "run_srr_v3_m10_followup_cine_adapter.sh",
        "run_srr_v3_m10_followup_cine_random_init.sh",
        "run_srr_v3_m10_followup_cine_registration.sh",
        "run_srr_v3_m10_followup_cine_temporal.sh",
    ):
        job_path = REPO_ROOT / "jobs/src" / job_name
        if job_path.is_file():
            text = job_path.read_text(encoding="utf-8")
            executable_lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
                and not line.strip().startswith("#")
                and not line.strip().startswith(("set ", "CARE_ROOT=", "cd ", "source ", "export ", "mkdir ", "TS=", "LOG_FILE=", "exec "))
            ]
            if executable_lines and executable_lines[-1].endswith("--print-contract"):
                findings.append(f"formal job entrypoint is contract-only and cannot run Wave F3 runtime: {job_name}")
    token = (OUT_DIR / "executor_completion.md").read_text(encoding="utf-8").strip() if (OUT_DIR / "executor_completion.md").is_file() else ""
    if token != "M10_FOLLOWUP_CINE_FIDELITY_READY_FOR_CONTROLLER_MERGE":
        findings.append(f"unexpected completion token: {token}")
    report = "# M10 Follow-up Cine F2 Validator\n\n"
    if findings:
        report += "Status: `FAIL`\n\n" + "\n".join(f"- {item}" for item in findings) + "\n"
        (OUT_DIR / "validator_report.md").write_text(report, encoding="utf-8")
        (OUT_DIR / "executor_completion.md").write_text("M10_FOLLOWUP_CINE_FIDELITY_NEEDS_REVISION\n", encoding="utf-8")
        raise SystemExit(1)
    report += "Status: `PASS`\n\nNo validator findings.\n"
    (OUT_DIR / "validator_report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
