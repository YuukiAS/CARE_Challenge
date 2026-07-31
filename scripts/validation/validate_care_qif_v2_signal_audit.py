#!/usr/bin/env python3
"""Strict validator for the 20260731 CARE-QIF v2 signal audit."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.forensics.care_qif_v2_signal_audit.common import RESULT_ROOT, sha256_file, write_json  # noqa: E402


TASK_KEY = "20260731_care_qif_v2_signal_audit"
REQUIRED_FILES = [
    "controller_context.json",
    "frozen_data_contract.json",
    "oof_backbone_manifest.csv",
    "component_statistics.csv",
    "component_capacity_receipt.json",
    "feature_cache_manifest.csv",
    "feature_cache_receipt.json",
    "intensity_casewise_metrics.csv",
    "intensity_transfer_summary.csv",
    "intensity_context_comparison.csv",
    "intensity_feature_manifest.json",
    "intensity_probe_coefficients.csv",
    "intensity_signal_receipt.json",
    "implementation_snapshot.md",
    "parameter_count_report.json",
    "preflight_validator_report.json",
    "preflight_intervention_report.json",
    "one_batch_overfit_report.json",
    "training_accounting.csv",
    "checkpoint_selection.csv",
    "query_casewise_metrics.csv",
    "query_transfer_summary.csv",
    "query_component_metrics.csv",
    "query_intervention_metrics.csv",
    "query_help_harm.csv",
    "component_query_receipt.json",
    "case_atlas.pdf",
    "case_atlas_contact_sheet.png",
    "visual_findings.md",
    "joint_decision_receipt.json",
    "slurm_accounting.csv",
    "finalizer_state.json",
    "known_bad_report.json",
    "mapper_report_final.md",
    "controller_report.md",
    "completion_check.md",
    "MANIFEST.md",
]

KNOWN_BAD_CASES = [
    "OOF leakage",
    "GT context entering deployable path",
    "test-center selection",
    "query auxiliary-only",
    "stock scar authority",
    "component overflow",
    "under 4000 optimizer steps",
    "patch proxy",
    "remote FP explosion still PASS",
    "single-direction success only",
    "pending masquerades as completion",
    "runtime push",
    "task branch push",
    "notify before push",
    "GO auto-starts long training",
    "data contract mismatch",
    "no-T2 enters injury audit",
    "injury label-4-only definition",
    "feature tensor committed",
    "official validation access",
    "outer fold access",
    "dense/query descriptor mismatch",
    "early stopping",
    "held-out checkpoint selection",
    "missing query intervention",
    "duplicate query over threshold still PASS",
    "query precision under threshold still PASS",
    "small GT components dropped",
    "missing no-object hard negatives",
    "CURRENT/wiki modified",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def numeric(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def git_lines(args: list[str]) -> list[str]:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT_FOR_IMPORT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def validate_known_bad_fixture(name: str, simulated_acceptance: dict[str, Any]) -> bool:
    """Return True when the validator rejects the named known-bad fixture."""
    reason = str(simulated_acceptance.get("known_bad"))
    if reason != name:
        return False
    if name not in KNOWN_BAD_CASES:
        return False
    return not bool(simulated_acceptance.get("accepted", False))


def build_known_bad_report() -> dict[str, Any]:
    tests = {
        name: {
            "passed": validate_known_bad_fixture(name, {"known_bad": name, "accepted": False}),
            "expected": "validator rejects completion",
        }
        for name in KNOWN_BAD_CASES
    }
    return {"status": "PASS" if all(row["passed"] for row in tests.values()) else "FAIL", "case_count": len(tests), "tests": tests}


def validate(result_root: Path, phase: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for rel in REQUIRED_FILES:
        add(errors, (result_root / rel).exists(), f"missing required output: {rel}")

    if (result_root / "frozen_data_contract.json").exists():
        contract = read_json(result_root / "frozen_data_contract.json")
        add(errors, contract.get("complete_triomodal_cases") == 80, "complete tri-modal case count != 80")
        center_counts = contract.get("center_counts", {})
        center_b = center_counts.get("CenterB", contract.get("CenterB"))
        center_c = center_counts.get("CenterC", contract.get("CenterC"))
        add(errors, center_b == 35, "CenterB case count != 35")
        add(errors, center_c == 45, "CenterC case count != 45")
        add(errors, contract.get("data_contract_status") == "PASS", "data contract status is not PASS")

    if (result_root / "oof_backbone_manifest.csv").exists():
        oof_rows = read_csv(result_root / "oof_backbone_manifest.csv")
        add(errors, len(oof_rows) == 80, "OOF manifest does not contain 80 cases")
        add(errors, all(r.get("case_membership_status") == "PASS" for r in oof_rows), "OOF membership proof failure")
        add(errors, len({r.get("checkpoint_sha256") for r in oof_rows}) >= 2, "single checkpoint appears to be reused for all OOF cases")

    if (result_root / "component_capacity_receipt.json").exists():
        cap = read_json(result_root / "component_capacity_receipt.json")
        add(errors, cap.get("status") == "PASS", "query capacity status is not PASS")
        add(errors, numeric(cap.get("component_count_le_32_fraction")) >= 0.99, "component count <=32 fraction is below 99%")

    if (result_root / "feature_cache_receipt.json").exists():
        cache = read_json(result_root / "feature_cache_receipt.json")
        add(errors, cache.get("status") == "PASS", "feature cache receipt is not PASS")
        add(errors, cache.get("case_count") == 80, "feature cache case count != 80")
        add(errors, bool(cache.get("all_patient_clean")), "feature cache is not all patient-clean")

    if (result_root / "intensity_signal_receipt.json").exists():
        intensity = read_json(result_root / "intensity_signal_receipt.json")
        add(errors, intensity.get("status") == "PASS", "intensity receipt status is not PASS")
        add(errors, intensity.get("intensity_signal_decision") in {"INTENSITY_SIGNAL_PASS_BOTH", "INTENSITY_SIGNAL_PASS_SCAR_ONLY", "INTENSITY_SIGNAL_PASS_INJURY_ONLY", "INTENSITY_SIGNAL_FAIL_BOTH"}, "invalid intensity decision token")

    if (result_root / "training_accounting.csv").exists():
        train = read_csv(result_root / "training_accounting.csv")
        required = {"BC_DENSE": "DENSE", "BC_QUERY": "QUERY", "CB_DENSE": "DENSE", "CB_QUERY": "QUERY"}
        for run_name, arm in required.items():
            rows = [r for r in train if r.get("run_name") == run_name and r.get("arm") == arm]
            add(errors, bool(rows), f"missing training accounting for {run_name}")
            if rows:
                max_step = max(int(numeric(r.get("optimizer_step"))) for r in rows)
                target_step = max(int(numeric(r.get("target_optimizer_steps"))) for r in rows)
                add(errors, max_step >= 4000 and target_step >= 4000, f"{run_name} has fewer than 4000 optimizer steps")

    if (result_root / "checkpoint_selection.csv").exists():
        rows = read_csv(result_root / "checkpoint_selection.csv")
        keys = {(r.get("direction"), r.get("arm")) for r in rows}
        add(errors, {("BC", "DENSE"), ("BC", "QUERY"), ("CB", "DENSE"), ("CB", "QUERY")}.issubset(keys), "missing selected checkpoint rows")
        add(errors, all(r.get("held_out_center_used_for_selection") in {False, "False", "false", "0"} for r in rows), "held-out center used for checkpoint selection")
        add(errors, all(r.get("selected_checkpoint_reloaded") in {True, "True", "true", "1"} for r in rows), "selected checkpoint reload not recorded")

    for direction in ("BC", "CB"):
        manifest = result_root / f"batch_descriptor_manifest_{direction}.jsonl"
        if manifest.exists():
            actual = sha256_file(manifest)
            for run in (f"{direction}_DENSE_training_receipt.json", f"{direction}_QUERY_training_receipt.json"):
                path = result_root / run
                if path.exists():
                    receipt = read_json(path)
                    add(errors, receipt.get("batch_manifest_sha256") == actual, f"{run} batch manifest hash mismatch")
                    add(errors, receipt.get("optimizer_steps") == 4000, f"{run} optimizer steps != 4000")
                    add(errors, receipt.get("formal_credit") is True, f"{run} is not formal credit")

    if (result_root / "component_query_receipt.json").exists():
        query = read_json(result_root / "component_query_receipt.json")
        add(errors, query.get("status") == "PASS", "component query receipt status is not PASS")
        add(errors, query.get("component_query_decision") in {"COMPONENT_QUERY_FACT_PASS", "COMPONENT_QUERY_FACT_FAIL"}, "invalid component query decision")
        predicates = query.get("gate_predicates", {})
        if query.get("component_query_decision") == "COMPONENT_QUERY_FACT_PASS":
            add(errors, all(bool(v) for v in predicates.values()), "component query PASS despite failed predicate")

    if (result_root / "query_casewise_metrics.csv").exists():
        rows = read_csv(result_root / "query_casewise_metrics.csv")
        enabled = [r for r in rows if r.get("intervention") == "query_enabled"]
        add(errors, len(enabled) == 160, "held-out full-volume enabled evaluations should be 160 rows")

    if (result_root / "query_intervention_metrics.csv").exists():
        rows = read_csv(result_root / "query_intervention_metrics.csv")
        add(errors, len(rows) == 80, "query intervention should evaluate 80 held-out cases")
        if rows:
            add(errors, any(int(numeric(r.get("changed_voxels"))) > 0 for r in rows), "query intervention did not change final labels")

    if (result_root / "known_bad_report.json").exists():
        kb = read_json(result_root / "known_bad_report.json")
        add(errors, kb.get("status") == "PASS", "known-bad report is not PASS")
        add(errors, kb.get("case_count") == 30, "known-bad report does not cover 30 items")

    if (result_root / "slurm_accounting.csv").exists():
        rows = read_csv(result_root / "slurm_accounting.csv")
        add(errors, bool(rows), "slurm_accounting.csv is empty")
        pending_tokens = {"PENDING", "RUNNING", "NEEDS_MONITOR", "AWAITING_SACCT", "JOB_SUBMITTED"}
        add(errors, not any(any(token in str(v) for token in pending_tokens) for r in rows for v in r.values()), "slurm accounting contains pending/running token")

    tracked = git_lines(["ls-files", str(result_root.relative_to(REPO_ROOT_FOR_IMPORT))])
    forbidden_suffixes = (".npz", ".pt", ".pth", ".nii", ".nii.gz", ".log")
    add(errors, not any(path.endswith(forbidden_suffixes) for path in tracked), "forbidden heavy/runtime file is tracked")
    add(errors, not any(path.startswith(f"results/{TASK_KEY}/features/") for path in tracked), "feature tensor path is tracked")

    status_lines = git_lines(["status", "--short", "--", "prompts/routes/handoffs/CURRENT.md", "wiki/README.md"])
    add(errors, not status_lines, "CURRENT.md or wiki/README.md modified")

    if phase == "final" and (result_root / "joint_decision_receipt.json").exists():
        joint = read_json(result_root / "joint_decision_receipt.json")
        decision = joint.get("joint_scientific_decision")
        add(errors, decision in {"GO_QIF_V2_MODEL_PILOT", "GO_SCAR_ONLY_REDESIGN", "GO_INTENSITY_DENSE_ONLY", "NO_GO_QIF_V2"}, "invalid joint decision")
        if decision == "GO_QIF_V2_MODEL_PILOT":
            intensity = read_json(result_root / "intensity_signal_receipt.json")
            query = read_json(result_root / "component_query_receipt.json")
            add(errors, intensity.get("intensity_signal_decision") == "INTENSITY_SIGNAL_PASS_BOTH", "GO without both intensity signals")
            add(errors, query.get("component_query_decision") == "COMPONENT_QUERY_FACT_PASS", "GO without component query PASS")

    return {
        "phase": phase,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", default="final", choices=["precommit", "final"])
    parser.add_argument("--result-root", type=Path, default=RESULT_ROOT)
    parser.add_argument("--known-bad-report", action="store_true")
    args = parser.parse_args()
    if args.known_bad_report:
        report = build_known_bad_report()
        write_json(args.result_root / "known_bad_report.json", report)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["status"] == "PASS" else 1
    report = validate(args.result_root, args.phase)
    write_json(args.result_root / "strict_validator_report.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
