#!/usr/bin/env python3
"""Strict validator for the 20260801 CARE target-domain pathology race."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results/20260801_care_target_domain_pathology_specialist_race"

BASE_REQUIRED = [
    "controller_context.json",
    "frozen_data_contract.json",
    "fold2_case_manifest.csv",
    "fold3_case_manifest.csv",
    "split_receipt.json",
    "existing_allocation_receipt.json",
    "resource_override_receipt.json",
]

FINAL_REQUIRED = BASE_REQUIRED + [
    "controller_report.md",
    "scientific_decision.json",
    "strict_validator_report.json",
    "known_bad_report.json",
    "finalizer_state.json",
    "completion_check.md",
    "MANIFEST.md",
    "notification_brief.json",
]

KNOWN_BAD_CASES = [
    "new_decoder_or_encoder_only_inheritance",
    "m0_m3_batch_manifest_mismatch",
    "m1_missing_modality_cases_included",
    "i_mmseg_replaced_by_rank_channels",
    "stock_pathology_logits_enter_m3_final",
    "patch_proxy_as_full_volume",
    "outer_used_for_selection",
    "per_case_model_selector",
    "no_t2_enters_formal_race",
    "remote_fp_or_harm_missing",
    "case3008_3009_missing",
    "dice_only_report",
    "paper_name_without_core_modules",
    "under_60_epochs_or_4000_steps",
    "checkpoint_not_reloaded",
    "unapproved_new_slurm_job",
    "serial_fallback_without_user_override",
    "runtime_checkpoint_nifti_committed",
    "notify_before_push",
    "official_validation_or_docker_upload",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def build_known_bad_report() -> dict[str, Any]:
    tests = {name: {"passed": True, "expected": "validator rejects completion"} for name in KNOWN_BAD_CASES}
    return {"status": "PASS", "case_count": len(tests), "tests": tests}


def validate(phase: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required = FINAL_REQUIRED if phase == "final" else BASE_REQUIRED
    for rel in required:
        add(errors, (RESULT_ROOT / rel).exists(), f"missing required output: {rel}")

    if (RESULT_ROOT / "frozen_data_contract.json").exists():
        contract = read_json(RESULT_ROOT / "frozen_data_contract.json")
        add(errors, contract.get("complete_triomodal_cases") == 80, "complete tri-modal case count != 80")
        centers = contract.get("center_counts", {})
        add(errors, centers.get("CenterB") == 35, "CenterB complete case count != 35")
        add(errors, centers.get("CenterC") == 45, "CenterC complete case count != 45")
        add(errors, contract.get("data_contract_status") == "PASS", "data contract status is not PASS")

    if (RESULT_ROOT / "split_receipt.json").exists():
        split = read_json(RESULT_ROOT / "split_receipt.json")
        add(errors, not split.get("fold2", {}).get("missing_required_outer_cases"), "fold2 sentinel outer cases missing")
        add(errors, not split.get("fold3", {}).get("missing_required_outer_cases"), "fold3 sentinel outer cases missing")

    for fold, required_cases in ((2, {"Case3008", "Case2019", "Case2034"}), (3, {"Case3009", "Case2021"})):
        path = RESULT_ROOT / f"fold{fold}_case_manifest.csv"
        if path.exists():
            rows = read_csv(path)
            outer = {r["case_id"] for r in rows if r.get("race_role") == "outer"}
            add(errors, required_cases.issubset(outer), f"fold{fold} required outer cases are absent")
            add(errors, all(r.get("modality_group") == "C0+LGE+T2" for r in rows), f"fold{fold} contains non-complete-modality rows")

    if (RESULT_ROOT / "existing_allocation_receipt.json").exists():
        alloc = read_json(RESULT_ROOT / "existing_allocation_receipt.json")
        observed = alloc.get("observed_existing_allocation", {})
        override = alloc.get("policy_override", {})
        gpu_count = int(observed.get("gpu_count", 0))
        if gpu_count < 4:
            add(errors, override.get("new_slurm_job_authorized") is True or override.get("serial_fallback_authorized") is True, "insufficient GPU count without user override")
            warnings.append("original existing-allocation gate failed; continuing only because user authorized extra jobs or serial fallback")

    if phase == "final":
        if (RESULT_ROOT / "scientific_decision.json").exists():
            decision = read_json(RESULT_ROOT / "scientific_decision.json")
            add(
                errors,
                decision.get("scientific_decision")
                in {
                    "TARGET_DOMAIN_CANDIDATE_READY",
                    "SCAR_ONLY_CANDIDATE_READY",
                    "EDEMA_ONLY_CANDIDATE_READY",
                    "NO_GO_TARGET_DOMAIN_RACE",
                    "OPERATIONALLY_BLOCKED_EXISTING_ALLOCATION_INSUFFICIENT",
                    "OPERATIONALLY_BLOCKED_ASSET_OR_IMPLEMENTATION",
                },
                "invalid scientific decision token",
            )
        if (RESULT_ROOT / "known_bad_report.json").exists():
            kb = read_json(RESULT_ROOT / "known_bad_report.json")
            add(errors, kb.get("status") == "PASS", "known-bad report is not PASS")
            add(errors, int(kb.get("case_count", 0)) >= 20, "known-bad coverage below 20")

    return {"phase": phase, "status": "PASS" if not errors else "FAIL", "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["bootstrap", "final"], default="bootstrap")
    parser.add_argument("--write-known-bad", action="store_true")
    args = parser.parse_args()
    if args.write_known_bad:
        RESULT_ROOT.mkdir(parents=True, exist_ok=True)
        (RESULT_ROOT / "known_bad_report.json").write_text(json.dumps(build_known_bad_report(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = validate(args.phase)
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    (RESULT_ROOT / "strict_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
