#!/usr/bin/env python3
"""Validate the lightweight Route B controller packet."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULT_ROOT = REPO_ROOT / "results" / "route_B"
ALLOWED_CONTROLLER_TOKENS = {
    "ROUTE_B_READY_FOR_REVIEW",
    "ROUTE_B_NEEDS_EVIDENCE",
    "ROUTE_B_NEEDS_REVISION",
    "ROUTE_B_NEEDS_MONITOR",
    "ROUTE_B_IMPLEMENTATION_NEEDS_REVISION",
    "ROUTE_B_SCIENTIFIC_UNDERTRAINED",
}
FORBIDDEN_TOKENS = {
    "ROUTE_PROMOTED",
    "VALIDATION_UPLOAD_APPROVED",
    "HOSTED_METRIC_CLAIM",
    "M11_AUTHORIZED",
    "FINAL_SCIENTIFIC_CONCLUSION",
    "CROSS_ROUTE_MERGE_APPROVED",
}
REQUIRED_FILES = [
    "controller_context.json",
    "controller_ledger.csv",
    "controller_bootstrap_snapshot.md",
    "implementation_gap_inventory.md",
    "implementation_snapshot.md",
    "architecture_component_trace.csv",
    "architecture_delta_final.md",
    "mapper_report_draft.md",
    "mapper_report_final.md",
    "implementation_gate.md",
    "implementation_gate.json",
    "gradient_and_intervention_report.csv",
    "save_reload_export_report.json",
    "implementation_freeze_receipt.json",
    "cine_registration_temporal_report.csv",
    "finalizer_state.json",
    "validator_implementation_report.json",
    "validator_packet_report.json",
    "result.md",
    "commands_run.md",
    "controller_report.md",
    "completion_check.md",
    "review_request.md",
    "MANIFEST.md",
]
HEAVY_SUFFIXES = (".nii", ".nii.gz", ".pth", ".pt", ".ckpt", ".zip")


def git(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False).stdout


def evaluate(result_root: Path = RESULT_ROOT) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    missing = [name for name in REQUIRED_FILES if not (result_root / name).exists()]
    errors.extend(f"missing_required_file:{name}" for name in missing)
    text_corpus = ""
    for path in result_root.glob("*"):
        if path.is_file() and path.suffix in {".md", ".json", ".csv"}:
            text_corpus += path.read_text(encoding="utf-8", errors="replace") + "\n"
    for token in FORBIDDEN_TOKENS:
        if token in text_corpus:
            errors.append(f"forbidden_token_present:{token}")
    completion = (result_root / "completion_check.md").read_text(encoding="utf-8", errors="replace") if (result_root / "completion_check.md").exists() else ""
    allowed_present = [token for token in ALLOWED_CONTROLLER_TOKENS if token in completion]
    if len(allowed_present) != 1:
        errors.append(f"completion_check_must_contain_exactly_one_allowed_token:{allowed_present}")
    if "review.md" in {path.name for path in result_root.glob("*")}:
        errors.append("review_md_written_by_controller")
    if "ROUTE_B_READY_FOR_REVIEW" in allowed_present:
        gate = json.loads((result_root / "implementation_gate.json").read_text(encoding="utf-8"))
        if gate.get("gate_passed") is not True:
            errors.append("ready_for_review_without_gate_passed")
    if any(term in completion for term in ("JOB_SUBMITTED", "PENDING_MONITOR", "RUNNING", "AWAITING_SACCT")):
        if "ROUTE_B_READY_FOR_REVIEW" in allowed_present:
            errors.append("ready_token_with_monitor_state")
        warnings.append("monitor_language_present")
    staged = git(["diff", "--cached", "--name-only"]).splitlines()
    heavy_staged = [path for path in staged if path.startswith("results/route_B/") and path.endswith(HEAVY_SUFFIXES)]
    errors.extend(f"heavy_runtime_artifact_staged:{path}" for path in heavy_staged)
    return {
        "status": "PASS" if not errors else "FAIL",
        "allowed_completion_tokens_found": allowed_present,
        "missing_required_files": missing,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", type=Path)
    args = parser.parse_args()
    report = evaluate()
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
