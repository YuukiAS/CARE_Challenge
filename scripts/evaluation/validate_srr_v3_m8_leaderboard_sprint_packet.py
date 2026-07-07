#!/usr/bin/env python3
"""Fail-closed validator for SRR-v3 M8 leaderboard sprint packets."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


READY_STATE = "M8_READY_FOR_REVIEW"
MONITOR_TOKENS = {
    "PENDING_MONITOR",
    "NEEDS_MONITOR",
    "JOB_SUBMITTED",
    "PENDING_PRIORITY",
    "RUNNING",
    "AWAITING_SACCT",
    "AWAITING_RUNTIME_AGGREGATION",
    "AWAITING COMPLETED",
    "AWAITING COMPLETED M8 RUNTIME AGGREGATION",
}
ALLOWED_STATES = {
    READY_STATE,
    "M8_NEEDS_MONITOR_NO_REVIEW",
    "M8_RESOURCE_BLOCKED",
    "M8_NEEDS_REVISION_TRAINING_UNDERRUN",
    "M8_NEEDS_REVISION_ARCHITECTURE_GAP",
    "M8_NEEDS_EVIDENCE_UNDERTRAINED",
    "M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE",
    "M8_NEEDS_EVIDENCE_CINE_REGISTRATION",
    "M8_NEEDS_REVISION",
    "M8_BLOCKED_BY_M7",
}

REQUIRED_READY_FILES = [
    "result.md",
    "completion_check.md",
    "review_request.md",
    "MANIFEST.md",
    "commands_run.md",
    "m8_training_budget_ledger.csv",
    "m8_variant_config_contract.json",
    "m8_variant_matrix.csv",
    "m8_architecture_gap_closure_table.csv",
    "m8_batch_composition.csv",
    "m8_srr_contribution_by_case.csv",
    "m8_same_split_help_harm.csv",
    "m8_registration_same_subset_matrix.csv",
    "m8_registration_method_selection.md",
    "m8_temporal_dictionary_evidence.csv",
    "m8_label_export_dry_run_qc.md",
    "m8_official_label_mapping_qc.csv",
    "m8_formal_case_manifest.csv",
    "m8_candidate_assembly_matrix.csv",
    "m8_nnunet_anchor_control_metrics.csv",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def completion_state(packet: Path) -> str:
    text = read_text(packet / "completion_check.md")
    match = re.search(r"status:\s*`?([A-Z0-9_]+)`?", text)
    return match.group(1) if match else "EVIDENCE_NOT_FOUND"


def numeric(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_usable_registration(row: dict[str, str]) -> bool:
    text = " ".join(str(value).upper() for value in row.values())
    if "NOT_USABLE" in text or "REFERENCE_CONTROL" in text:
        return False
    return "USABLE" in text or str(row.get("failure_reason", "")).strip() == ""


def has_unnegated_claim(text: str, phrase: str) -> bool:
    start = 0
    while True:
        idx = text.find(phrase, start)
        if idx < 0:
            return False
        context = text[max(0, idx - 140):idx]
        if not any(marker in context for marker in ("not ", "no ", "without ", "does not ", "do not ", "not authorized", "not created", "not run")):
            return True
        start = idx + len(phrase)


def validate(packet: Path) -> list[str]:
    errors: list[str] = []
    state = completion_state(packet)
    if state not in ALLOWED_STATES:
        errors.append(f"completion_check.md has invalid or missing status: {state}")

    all_text = "\n".join(
        read_text(path)
        for path in packet.glob("*.md")
        if path.name not in {"commands_run.md", "m8_strict_validator_report.md", "m8_validator_unit_test_report.md"}
    )
    forbidden_claims = [
        "validation upload",
        "hosted metric claim",
        "challenge-ready",
        "leaderboard-ready",
        "M9",
    ]
    if state == READY_STATE:
        all_text_upper = all_text.upper()
        for token in MONITOR_TOKENS:
            if token in all_text_upper:
                errors.append(f"ready packet contains monitor token {token}")
        commands_text = read_text(packet / "commands_run.md").upper()
        if any(token in commands_text for token in MONITOR_TOKENS) and "FINAL_M8_READY_AGGREGATION" not in commands_text:
            errors.append("ready packet commands_run.md contains historical monitor tokens without final completed aggregation marker")
        for file_name in REQUIRED_READY_FILES:
            if not (packet / file_name).is_file():
                errors.append(f"ready packet missing required file {file_name}")
        ledger = read_csv(packet / "m8_training_budget_ledger.csv")
        included_seconds = 0.0
        for row in ledger:
            if str(row.get("included_in_8h_budget", "")).lower() in {"true", "1", "yes"}:
                value = numeric(row.get("train_loop_seconds", ""))
                if value is not None:
                    included_seconds += value
        if included_seconds < 28800.0:
            errors.append(f"ready packet has included train_loop_seconds {included_seconds:.1f} < 28800")
        try:
            contract = json.loads((packet / "m8_variant_config_contract.json").read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"variant config contract unreadable: {type(exc).__name__}")
            contract = {}
        if "run_srr_propref_myops_fold0.py" not in str(contract.get("code_path", "")) or "--variant-config-contract" not in str(contract.get("code_path", "")):
            errors.append("variant config contract is not tied to the training code reader")
        variants = contract.get("variants") if isinstance(contract, dict) else {}
        if not isinstance(variants, dict) or len(variants) < 3:
            errors.append("variant config contract does not define three M8 variants")
        elif len({json.dumps(value, sort_keys=True) for value in variants.values()}) == 1:
            errors.append("variant config variants only differ by name")
        contribution = read_csv(packet / "m8_srr_contribution_by_case.csv")
        if not contribution:
            errors.append("m8_srr_contribution_by_case.csv has no rows")
        for row in contribution[:20]:
            if row.get("anchor_delta_rate") in {"", None, "EVIDENCE_NOT_EXPORTED_PER_CASE", "EVIDENCE_NOT_FOUND"}:
                errors.append("m8_srr_contribution_by_case.csv lacks real per-case anchor_delta_rate")
                break
        if any(numeric(row.get("no_t2_edema_voxels", "")) and numeric(row.get("no_t2_edema_voxels", "")) > 0 for row in contribution):
            errors.append("ready packet contains no-T2 edema voxel safety violation")
        architecture = read_csv(packet / "m8_architecture_gap_closure_table.csv")
        bad_status = [row.get("closure_status", "") for row in architecture if row.get("closure_status") in {"CLOSED", "NEEDS_REVISION", "NEEDS_EVIDENCE"}]
        if bad_status:
            errors.append("architecture closure table contains bare/blocked closure statuses")
        formal = read_csv(packet / "m8_formal_case_manifest.csv")
        if not formal or not any(str(row.get("t2_present", "")).lower() == "true" for row in formal):
            errors.append("ready packet lacks broad formal evidence with T2-present cases")
        if not formal or not ({"CenterB", "CenterC"} & {str(row.get("center", "")) for row in formal}):
            errors.append("ready packet lacks broad formal evidence with CenterB/CenterC cases")
        if not formal or not any(str(row.get("modality_group", "")).lower() != "lge-only" for row in formal):
            errors.append("ready packet lacks broad formal evidence with multimodal cases")
        candidates = read_csv(packet / "m8_candidate_assembly_matrix.csv")
        if not candidates or any(row.get("decision") in {"BLOCKS_READY_REVIEW", "EVIDENCE_NOT_FOUND"} for row in candidates):
            errors.append("ready packet lacks complete local candidate assembly")
        anchor_control = read_csv(packet / "m8_nnunet_anchor_control_metrics.csv")
        anchor_metrics = {row.get("metric_name", "") for row in anchor_control}
        if not {"myops_scar", "myops_edema"}.issubset(anchor_metrics):
            errors.append("ready packet lacks same-split nnU-Net anchor control metrics")
        trained_candidate_keys = {
            (row.get("candidate_id", ""), row.get("metric_name", ""))
            for row in candidates
            if row.get("candidate_type") == "trained_srr_variant_decode"
            and row.get("same_split_nnunet_control_status") == "COMPARED_AGAINST_SAME_SPLIT_NNUNET_CONTROL"
        }
        trained_candidate_ids = {key[0] for key in trained_candidate_keys}
        if len(trained_candidate_ids) < 6 or any((candidate_id, metric) not in trained_candidate_keys for candidate_id in trained_candidate_ids for metric in ("myops_scar", "myops_edema")):
            errors.append("ready packet does not compare every local SRR candidate against nnU-Net for scar and edema")
        required_candidate_fields = [
            "dice_delta_vs_nnunet",
            "hd95_delta_vs_nnunet",
            "component_count_delta_vs_nnunet",
            "remote_fp_delta_vs_nnunet",
            "no_t2_edema_voxels",
            "label_export_status",
        ]
        for row in candidates:
            if row.get("candidate_type") != "trained_srr_variant_decode":
                continue
            if any(row.get(field, "") in {"", "EVIDENCE_NOT_FOUND"} for field in required_candidate_fields):
                errors.append("ready packet candidate assembly lacks required comparison fields")
                break
        label_qc = read_csv(packet / "m8_official_label_mapping_qc.csv")
        if any(row.get("observed_status") == "FAIL" for row in label_qc):
            errors.append("official label/export QC contains a failing row")
        cine_matrix = read_csv(packet / "m8_registration_same_subset_matrix.csv")
        cine_cases = {row.get("case_id", "") for row in cine_matrix if row.get("case_id")}
        cine_methods = {
            row.get("method", "")
            for row in cine_matrix
            if row.get("method") and "identity" not in row.get("method", "").lower()
        }
        if len(cine_cases) < 12:
            errors.append("ready packet Cine registration covers fewer than 12 cases")
        if len(cine_methods) < 2:
            errors.append("ready packet lacks at least two mature non-reference Cine registration families")
        if "selected" not in read_text(packet / "m8_registration_method_selection.md").lower():
            errors.append("ready packet lacks quantitative best-registration selection text")
        usable_registration = any(is_usable_registration(row) for row in cine_matrix)
        temporal = read_csv(packet / "m8_temporal_dictionary_evidence.csv")
        temporal_attempted = any(str(row.get("temporal_dictionary_attempted", "")).lower() == "true" or str(row.get("status", "")).upper().startswith("TEMPORAL_DICTIONARY_EXECUTED") for row in temporal)
        if usable_registration and not temporal_attempted:
            errors.append("usable Cine registration exists but temporal dictionary was not executed")
        if not usable_registration and state == READY_STATE:
            errors.append("ready packet has no usable non-reference Cine registration")
    else:
        if READY_STATE in all_text:
            errors.append(f"non-ready packet text contains {READY_STATE}")

    lower_text = all_text.lower()
    if "upload_ready/" in lower_text or "care-myocardium-organagent.zip" in lower_text:
        errors.append("packet references upload package path or zip")
    for phrase in forbidden_claims:
        if has_unnegated_claim(lower_text, phrase):
            errors.append(f"packet may contain forbidden claim: {phrase}")
    return errors


def write_reports(packet: Path, errors: list[str]) -> None:
    state = completion_state(packet)
    now = datetime.now(UTC).isoformat()
    rows = [{"status": state, "error_count": str(len(errors)), "error": error} for error in errors]
    if not rows:
        rows = [{"status": state, "error_count": "0", "error": ""}]
    write_csv(packet / "m8_strict_validator_report.csv", rows, ["status", "error_count", "error"])
    result = "pass" if not errors else "fail"
    error_text = "\n".join(f"- `{error}`" for error in errors) or "- none"
    (packet / "m8_strict_validator_report.md").write_text(
        "\n".join(
            [
                "# M8 Strict Validator Report",
                "",
                f"status: `{state}`",
                f"updated_at_utc: `{now}`",
                "",
                "Command:",
                "",
                "```bash",
                "PYTHONPATH=. python scripts/evaluation/validate_srr_v3_m8_leaderboard_sprint_packet.py --packet results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint",
                "```",
                "",
                f"Result: `{result}`, `error_count={len(errors)}`.",
                "",
                "Interpretation: this validates the current packet state only. A non-ready status is not M8 completion.",
                "",
                "## Errors",
                error_text,
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def make_ready_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_READY_FILES + ["result.md", "completion_check.md"]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".csv":
            path.write_text("status,value\nPASS,1\n", encoding="utf-8")
        else:
            path.write_text(f"# {name}\n\nstatus: `{READY_STATE}`\n", encoding="utf-8")
    (root / "completion_check.md").write_text(f"# Completion\n\nstatus: `{READY_STATE}`\n", encoding="utf-8")
    (root / "commands_run.md").write_text("# Commands\n\n- Aggregation completed.\n", encoding="utf-8")
    write_csv(
        root / "m8_training_budget_ledger.csv",
        [{"run_id": "run0", "included_in_8h_budget": "true", "train_loop_seconds": "28800", "optimizer_steps": "6000", "validation_event_count": "3"}],
        ["run_id", "included_in_8h_budget", "train_loop_seconds", "optimizer_steps", "validation_event_count"],
    )
    variants = {
        "v0": {"encoder_profile": "a", "dictionary_slot_counts": {"shared": 4}},
        "v1": {"encoder_profile": "b", "dictionary_slot_counts": {"shared": 6}},
        "v2": {"encoder_profile": "c", "dictionary_slot_counts": {"shared": 8}},
    }
    (root / "m8_variant_config_contract.json").write_text(
        json.dumps({"code_path": "scripts/training/run_srr_propref_myops_fold0.py --variant-config-contract", "variants": variants}),
        encoding="utf-8",
    )
    write_csv(
        root / "m8_srr_contribution_by_case.csv",
        [{"case_id": "Case1", "anchor_delta_rate": "0.01", "no_t2_edema_voxels": "0"}],
        ["case_id", "anchor_delta_rate", "no_t2_edema_voxels"],
    )
    write_csv(
        root / "m8_architecture_gap_closure_table.csv",
        [{"route_component": "x", "closure_status": "CLOSED_WITH_RUNTIME_EVIDENCE"}],
        ["route_component", "closure_status"],
    )
    write_csv(
        root / "m8_formal_case_manifest.csv",
        [
            {"case_id": "Case1", "center": "CenterB", "modality_group": "LGE+T2", "t2_present": "true"},
            {"case_id": "Case2", "center": "CenterC", "modality_group": "C0+LGE+T2", "t2_present": "true"},
        ],
        ["case_id", "center", "modality_group", "t2_present"],
    )
    write_csv(
        root / "m8_nnunet_anchor_control_metrics.csv",
        [
            {"candidate_id": "A_nnunet_anchor_control", "metric_name": "myops_scar", "dice": "0.5"},
            {"candidate_id": "A_nnunet_anchor_control", "metric_name": "myops_edema", "dice": "0.6"},
        ],
        ["candidate_id", "metric_name", "dice"],
    )
    candidate_rows = []
    for candidate_idx in range(6):
        for metric in ("myops_scar", "myops_edema"):
            candidate_rows.append(
                {
                    "candidate_id": f"candidate_{candidate_idx}",
                    "candidate_type": "trained_srr_variant_decode",
                    "metric_name": metric,
                    "decision": "SELECTABLE_FOR_REVIEW",
                    "same_split_nnunet_control_status": "COMPARED_AGAINST_SAME_SPLIT_NNUNET_CONTROL",
                    "dice_delta_vs_nnunet": "0.01",
                    "hd95_delta_vs_nnunet": "-0.1",
                    "component_count_delta_vs_nnunet": "0",
                    "remote_fp_delta_vs_nnunet": "0",
                    "no_t2_edema_voxels": "0",
                    "label_export_status": "PASS_NO_INVALID_COMPACT_LABELS",
                }
            )
    write_csv(
        root / "m8_candidate_assembly_matrix.csv",
        candidate_rows,
        [
            "candidate_id",
            "candidate_type",
            "metric_name",
            "decision",
            "same_split_nnunet_control_status",
            "dice_delta_vs_nnunet",
            "hd95_delta_vs_nnunet",
            "component_count_delta_vs_nnunet",
            "remote_fp_delta_vs_nnunet",
            "no_t2_edema_voxels",
            "label_export_status",
        ],
    )
    write_csv(
        root / "m8_official_label_mapping_qc.csv",
        [{"check": "no_t2_edema_voxels", "observed_status": "PASS"}],
        ["check", "observed_status"],
    )
    cine_rows = []
    for idx in range(12):
        case_id = f"Case{idx:04d}"
        cine_rows.append({"method": "SimpleITK_Demons", "case_id": case_id, "failure_reason": "", "m7_continued_decision": "USABLE_FOR_TEMPORAL_DICTIONARY"})
        cine_rows.append({"method": "ANTsPy_SyNOnly", "case_id": case_id, "failure_reason": "", "m7_continued_decision": "USABLE_FOR_TEMPORAL_DICTIONARY"})
    write_csv(root / "m8_registration_same_subset_matrix.csv", cine_rows, ["method", "case_id", "failure_reason", "m7_continued_decision"])
    (root / "m8_registration_method_selection.md").write_text("# Method Selection\n\nselected method: `SimpleITK_Demons`\n", encoding="utf-8")
    write_csv(
        root / "m8_temporal_dictionary_evidence.csv",
        [{"status": "TEMPORAL_DICTIONARY_EXECUTED", "temporal_dictionary_attempted": "true"}],
        ["status", "temporal_dictionary_attempted"],
    )


def mutate_fixture(name: str, path: Path) -> None:
    if name == "total_training_budget_under_8h":
        write_csv(path / "m8_training_budget_ledger.csv", [{"run_id": "run0", "included_in_8h_budget": "true", "train_loop_seconds": "1000"}], ["run_id", "included_in_8h_budget", "train_loop_seconds"])
    elif name == "missing_training_budget_ledger":
        (path / "m8_training_budget_ledger.csv").unlink()
    elif name == "pending_monitor_packet_marked_ready":
        (path / "commands_run.md").write_text("# Commands\n\nPENDING_PRIORITY RUNNING AWAITING_RUNTIME_AGGREGATION\n", encoding="utf-8")
    elif name == "completed_job_not_reaggregated":
        (path / "commands_run.md").write_text("# Commands\n\nsbatch submitted; PENDING_PRIORITY only.\n", encoding="utf-8")
    elif name == "config_contract_not_read_by_code":
        contract = json.loads((path / "m8_variant_config_contract.json").read_text(encoding="utf-8"))
        contract["code_path"] = "EVIDENCE_NOT_FOUND"
        (path / "m8_variant_config_contract.json").write_text(json.dumps(contract), encoding="utf-8")
    elif name == "variants_only_renamed":
        contract = json.loads((path / "m8_variant_config_contract.json").read_text(encoding="utf-8"))
        contract["variants"] = {key: {"encoder_profile": "same", "dictionary_slot_counts": {"shared": 4}} for key in contract["variants"]}
        (path / "m8_variant_config_contract.json").write_text(json.dumps(contract), encoding="utf-8")
    elif name == "missing_per_case_anchor_delta":
        write_csv(path / "m8_srr_contribution_by_case.csv", [{"case_id": "Case1", "anchor_delta_rate": "EVIDENCE_NOT_EXPORTED_PER_CASE"}], ["case_id", "anchor_delta_rate"])
    elif name == "easy_only_formal_evaluation":
        write_csv(
            path / "m8_formal_case_manifest.csv",
            [{"case_id": "Case2", "center": "CenterA", "modality_group": "LGE-only", "t2_present": "false"}],
            ["case_id", "center", "modality_group", "t2_present"],
        )
    elif name == "no_t2_safety_violation":
        write_csv(path / "m8_srr_contribution_by_case.csv", [{"case_id": "Case1", "anchor_delta_rate": "0.01", "no_t2_edema_voxels": "3"}], ["case_id", "anchor_delta_rate", "no_t2_edema_voxels"])
    elif name == "missing_local_candidate_assembly":
        (path / "m8_candidate_assembly_matrix.csv").unlink()
    elif name == "cine_three_case_smoke":
        rows = [{"method": "SimpleITK_Demons", "case_id": f"Case{idx:04d}", "failure_reason": "", "m7_continued_decision": "USABLE"} for idx in range(3)]
        write_csv(path / "m8_registration_same_subset_matrix.csv", rows, ["method", "case_id", "failure_reason", "m7_continued_decision"])
    elif name == "no_best_registration_selection":
        (path / "m8_registration_method_selection.md").write_text("# Method Selection\n\nEVIDENCE_NOT_FOUND\n", encoding="utf-8")
    elif name == "usable_registration_without_temporal_dictionary":
        write_csv(path / "m8_temporal_dictionary_evidence.csv", [{"status": "TEMPORAL_DICTIONARY_BLOCKED", "temporal_dictionary_attempted": "false"}], ["status", "temporal_dictionary_attempted"])
    elif name == "missing_label_export_qc":
        (path / "m8_official_label_mapping_qc.csv").unlink()
    elif name == "placeholder_final_proof":
        (path / "result.md").write_text(f"# Result\n\nstatus: `{READY_STATE}`\n\nAwaiting completed M8 runtime aggregation.\n", encoding="utf-8")
    elif name == "unauthorized_upload_claim":
        (path / "result.md").write_text(f"# Result\n\nstatus: `{READY_STATE}`\n\nCreated upload_ready/CARE-Myocardium-OrganAgent.zip\n", encoding="utf-8")
    else:
        raise ValueError(name)


def validator_reason(errors: list[str]) -> str:
    return "; ".join(errors[:2]) if errors else ""


def run_self_tests(packet: Path) -> list[dict[str, str]]:
    cases = [
        "total_training_budget_under_8h",
        "missing_training_budget_ledger",
        "pending_monitor_packet_marked_ready",
        "completed_job_not_reaggregated",
        "config_contract_not_read_by_code",
        "variants_only_renamed",
        "missing_per_case_anchor_delta",
        "easy_only_formal_evaluation",
        "no_t2_safety_violation",
        "missing_local_candidate_assembly",
        "cine_three_case_smoke",
        "no_best_registration_selection",
        "usable_registration_without_temporal_dictionary",
        "missing_label_export_qc",
        "placeholder_final_proof",
        "unauthorized_upload_claim",
    ]
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="m8_validator_selftest_") as tmp:
        base = Path(tmp) / "good"
        make_ready_fixture(base)
        good_errors = validate(base)
        rows.append(
            {
                "fixture": "good_ready_fixture",
                "expected": "PASS",
                "actual": "PASS" if not good_errors else "FAIL",
                "failure_reason": validator_reason(good_errors),
            }
        )
        for case in cases:
            fixture = Path(tmp) / case
            shutil.copytree(base, fixture)
            mutate_fixture(case, fixture)
            errors = validate(fixture)
            rows.append(
                {
                    "fixture": case,
                    "expected": "FAIL_CLOSED",
                    "actual": "FAIL_CLOSED" if errors else "FAIL_OPEN",
                    "failure_reason": validator_reason(errors),
                }
            )
    write_csv(packet / "m8_validator_unit_test_report.csv", rows, ["fixture", "expected", "actual", "failure_reason"])
    all_ok = all((row["expected"] == "PASS" and row["actual"] == "PASS") or (row["expected"] == "FAIL_CLOSED" and row["actual"] == "FAIL_CLOSED") for row in rows)
    lines = [
        "# M8 Validator Unit Test Report",
        "",
        f"status: `{'PASS_FAIL_CLOSED' if all_ok else 'FAIL_OPEN'}`",
        "",
        "Temporary known-bad fixtures were generated outside the repo and are not committed. Summary rows are in `m8_validator_unit_test_report.csv`.",
        "",
        "| fixture | expected | actual | failure_reason |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(f"| {row['fixture']} | {row['expected']} | {row['actual']} | {row['failure_reason']} |" for row in rows)
    (packet / "m8_validator_unit_test_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    packet = Path(args.packet)
    if not packet.is_absolute():
        packet = Path.cwd() / packet
    if args.self_test:
        rows = run_self_tests(packet)
        failed = [row for row in rows if row["actual"] not in {"PASS", "FAIL_CLOSED"}]
        print(json.dumps({"packet": str(packet), "self_test_rows": len(rows), "failed": failed}, indent=2))
        if failed:
            sys.exit(1)
        return
    errors = validate(packet)
    write_reports(packet, errors)
    print(json.dumps({"packet": str(packet), "error_count": len(errors), "errors": errors}, indent=2))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
