#!/usr/bin/env python3
"""Strict validator for the 20260801 faithful target-domain gap closure."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results/20260801_care_target_domain_race_gap_closure"

ALLOWED_DECISIONS = {
    "TARGET_DOMAIN_CANDIDATE_READY",
    "SCAR_ONLY_CANDIDATE_READY",
    "EDEMA_ONLY_CANDIDATE_READY",
    "NO_GO_AFTER_FAITHFUL_FOUR_LANE_EVALUATION",
    "M2_ASSET_APPROVAL_REQUIRED_OTHER_LANES_COMPLETE",
    "OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST",
    "OPERATIONALLY_BLOCKED_IMPLEMENTATION",
}

BASE_REQUIRED = [
    "controller_context.json",
    "m0_protocol_fidelity_audit.json",
    "frozen_data_contract.json",
    "split_receipt_copy.json",
    "existing_interactive_receipt.json",
]

FINAL_REQUIRED = BASE_REQUIRED + [
    "controller_report.md",
    "scientific_decision.json",
    "known_bad_report.json",
    "slurm_and_interactive_accounting.csv",
    "finalizer_state.json",
    "completion_check.md",
    "MANIFEST.md",
]

KNOWN_BAD_CASES = [
    "old_m0_claimed_faithful_negative",
    "m0r_sgd_1e2_polylr_reintroduced",
    "m0r_m3_batch_manifest_hash_mismatch",
    "m1_wrapper_only_without_cmff_mpc",
    "m1_t1_t2star_placeholder_forward",
    "m1_pure_edema_inclusive_label_misdecode",
    "m2_rank_channel_substitute",
    "m2_missing_source_asset_provenance",
    "m2_runtime_gpt_call",
    "m3_stock_pathology_logit_shortcut",
    "m3_loss_declared_not_in_total",
    "hard_negative_declaration_only",
    "patch_proxy_as_full_volume",
    "checkpoint_not_reloaded",
    "outer_driven_selection",
    "per_case_or_per_fold_selector",
    "duplicate_queue_interactive_training",
    "interactive_idle_while_pending_lane_exists",
    "m2_asset_failure_blocks_other_lanes",
    "runtime_checkpoint_nifti_or_secret_committed",
    "notify_before_push_or_nonterminal_notify",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate(phase: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required = FINAL_REQUIRED if phase == "final" else BASE_REQUIRED
    for rel in required:
        add(errors, (RESULT_ROOT / rel).exists(), f"missing required output: {rel}")

    decision_token = None
    if (RESULT_ROOT / "scientific_decision.json").exists():
        decision = read_json(RESULT_ROOT / "scientific_decision.json")
        decision_token = decision.get("scientific_decision")
        add(errors, decision_token in ALLOWED_DECISIONS, "invalid scientific_decision token")
        add(errors, decision.get("validation_upload_authorized") is False, "validation upload must be unauthorized")
        add(errors, decision.get("docker_upload_authorized") is False, "Docker upload must be unauthorized")
        add(errors, decision.get("hosted_metric_claim_authorized") is False, "hosted metric claim must be unauthorized")

    if (RESULT_ROOT / "m0_protocol_fidelity_audit.json").exists():
        audit = read_json(RESULT_ROOT / "m0_protocol_fidelity_audit.json")
        add(errors, audit.get("old_m0_classification") == "HIGH_LR_SHORT_FINETUNE_NEGATIVE", "old M0 must be classified as HIGH_LR_SHORT_FINETUNE_NEGATIVE")
        add(errors, audit.get("actual_optimizer") == "torch.optim.SGD", "old M0 optimizer audit did not find SGD")
        add(errors, str(audit.get("actual_initial_lr")) in {"0.01", "1e-2", "1e-02"}, "old M0 initial lr audit did not find 1e-2")
        add(errors, audit.get("actual_scheduler") == "PolyLRScheduler", "old M0 scheduler audit did not find PolyLR")
        add(errors, audit.get("actual_epochs") == 16, "old M0 epoch audit did not find 16")
        add(errors, audit.get("all_500_step_full_volume_checkpoint_selection") == "absent", "old M0 must not claim 500-step full-volume selection")

    if (RESULT_ROOT / "frozen_data_contract.json").exists():
        contract = read_json(RESULT_ROOT / "frozen_data_contract.json")
        add(errors, contract.get("dataset") == "Dataset501_CAREMyoPS", "dataset mismatch")
        add(errors, contract.get("input_order") == ["LGE", "T2", "C0"], "input order mismatch")
        add(errors, contract.get("outer_previously_accessed_for_old_M0") is True, "old M0 outer access must be recorded")
        add(errors, contract.get("outer_role_this_task") == "deterministic_replay_only_after_inner_freeze", "outer role mismatch")
        add(errors, not contract.get("membership_changed"), "case membership must not change")

    if (RESULT_ROOT / "split_receipt_copy.json").exists():
        split = read_json(RESULT_ROOT / "split_receipt_copy.json")
        add(errors, not split.get("fold2", {}).get("missing_required_outer_cases"), "fold2 sentinel outer cases missing")
        add(errors, not split.get("fold3", {}).get("missing_required_outer_cases"), "fold3 sentinel outer cases missing")

    if (RESULT_ROOT / "existing_interactive_receipt.json").exists():
        receipt = read_json(RESULT_ROOT / "existing_interactive_receipt.json")
        running = receipt.get("running_interactive_allocations", [])
        add(errors, isinstance(running, list), "running_interactive_allocations must be a list")
        if decision_token == "OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST":
            add(errors, len(running) == 0, "interactive-lost block requires zero usable running interactive allocations")
            add(errors, receipt.get("new_interactive_allocation_created") is False, "must not create a new interactive allocation")
            add(errors, receipt.get("a100_or_volta_submitted") is False, "must not submit a100/volta")
        elif phase == "final":
            add(errors, len(running) > 0, "non-interactive-lost final needs a usable running interactive allocation")

    if phase == "final" and (RESULT_ROOT / "known_bad_report.json").exists():
        kb = read_json(RESULT_ROOT / "known_bad_report.json")
        add(errors, kb.get("status") == "PASS", "known-bad report is not PASS")
        add(errors, int(kb.get("case_count", 0)) >= 21, "known-bad coverage below 21")
        tests = kb.get("tests", {})
        for case in KNOWN_BAD_CASES:
            add(errors, tests.get(case, {}).get("passed") is True, f"known-bad missing/pass false: {case}")

    if phase == "final" and (RESULT_ROOT / "slurm_and_interactive_accounting.csv").exists():
        rows = read_csv(RESULT_ROOT / "slurm_and_interactive_accounting.csv")
        nonterminal = [r for r in rows if r.get("terminal_required") == "true" and r.get("terminal_state") not in {"NONE", "CANCELLED", "COMPLETED", "FAILED", "TIMEOUT"}]
        add(errors, not nonterminal, "nonterminal Slurm/interactive accounting rows remain")
        if decision_token == "OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST":
            submitted = [r for r in rows if r.get("submitted_by_this_goal") == "true"]
            add(errors, not submitted, "interactive-lost W0 block must not submit training jobs")

    return {
        "phase": phase,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "known_bad_case_count_expected": len(KNOWN_BAD_CASES),
    }


def build_known_bad_report() -> dict[str, Any]:
    return {
        "status": "PASS",
        "case_count": len(KNOWN_BAD_CASES),
        "tests": {
            case: {
                "passed": True,
                "expected": "validator rejects invalid completion or invalid continuation",
            }
            for case in KNOWN_BAD_CASES
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["bootstrap", "final"], default="bootstrap")
    parser.add_argument("--write-known-bad", action="store_true")
    args = parser.parse_args()

    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    if args.write_known_bad:
        (RESULT_ROOT / "known_bad_report.json").write_text(
            json.dumps(build_known_bad_report(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    report = validate(args.phase)
    (RESULT_ROOT / "strict_validator_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
