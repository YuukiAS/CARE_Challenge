#!/usr/bin/env python3
"""Fail-closed validator for the SRR-v3 M7 continued/follow-up packet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


READY_TOKENS = {"M7_CONTINUED_READY_FOR_REVIEW", "M7_FOLLOWUP2_READY_FOR_REVIEW"}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def fail(checks: list[dict[str, object]], gate: str, reason: str) -> None:
    checks.append({"gate": gate, "ok": False, "reason": reason})


def pass_gate(checks: list[dict[str, object]], gate: str, reason: str) -> None:
    checks.append({"gate": gate, "ok": True, "reason": reason})


def validate(packet: Path) -> tuple[bool, list[dict[str, object]]]:
    checks: list[dict[str, object]] = []
    if not packet.is_dir():
        fail(checks, "packet_exists", f"packet directory not found: {packet}")
        return False, checks
    pass_gate(checks, "packet_exists", str(packet))

    grad_path = packet / "loss_component_gradient_sanity.csv"
    grad_rows = read_csv(grad_path)
    if not grad_rows:
        fail(checks, "loss_gradient_sanity", f"missing or empty {grad_path.name}")
    elif all(str(r.get("status", "")).startswith("BACKWARD_FAILED") for r in grad_rows):
        fail(checks, "loss_gradient_sanity", "all gradient sanity rows are BACKWARD_FAILED")
    else:
        pass_gate(checks, "loss_gradient_sanity", "not all rows are BACKWARD_FAILED")

    loss_graph = text(packet / "loss_graph_training_validity_report.md")
    if "original" not in loss_graph.lower() or "graph" not in loss_graph.lower():
        fail(checks, "loss_graph_training_validity_report", "missing original training graph validity statement")
    else:
        pass_gate(checks, "loss_graph_training_validity_report", "report exists with graph/original statement")

    case_rows = read_csv(packet / "m7_case_pool_audit.csv")
    selected = [r for r in case_rows if str(r.get("selected_for_formal_val", "")).lower() == "true"]
    if not selected:
        fail(checks, "hard_subgroup_coverage", "no selected formal-val rows")
    else:
        centers = {r.get("center", "") for r in selected}
        modality_groups = {r.get("modality_group", "") for r in selected}
        t2_values = {str(r.get("t2_present", "")).lower() for r in selected}
        if centers <= {"CenterA"} and modality_groups <= {"LGE-only"} and t2_values <= {"false", "0", ""}:
            fail(checks, "hard_subgroup_coverage", "selected formal-val rows are all CenterA/LGE-only/no-T2")
        else:
            pass_gate(checks, "hard_subgroup_coverage", "selected formal-val rows include broader subgroup evidence")

    best_rows = read_csv(packet / "best_variant_decision_table.csv")
    mixed = [
        r
        for r in best_rows
        if str(r.get("split_role", "formal_val")) != "formal_val"
        or str(r.get("eligible_for_best_variant_decision", "true")).lower() != "true"
    ]
    if mixed:
        fail(checks, "formal_diagnostic_boundary", "diagnostic rows are mixed into formal best-variant decision")
    else:
        pass_gate(checks, "formal_diagnostic_boundary", "best-variant rows remain formal-val eligible only")

    cine_report = packet / "cine_registration_repair_report.md"
    cine_followup2_report = packet / "cine_registration_followup2_report.md"
    if not cine_report.is_file() and not cine_followup2_report.is_file():
        fail(checks, "cine_registration_attempt", "no M7 continued/follow-up Cine registration attempt report")
    else:
        pass_gate(checks, "cine_registration_attempt", "Cine registration attempt report exists")

    reg_rows = read_csv(packet / "registration_same_subset_matrix.csv")
    usable_rows = [r for r in reg_rows if str(r.get("usable_for_temporal_dictionary", "")).lower() == "true"]
    bad_usable = [
        r
        for r in reg_rows
        if str(r.get("usable_for_temporal_dictionary", "")).lower() == "true"
        and (
            "frame0" in str(r.get("method", "")).lower()
            or "untrained" in str(r.get("method", "")).lower()
            or "one_case" in str(r.get("failure_reason", "")).lower()
        )
    ]
    if bad_usable:
        fail(checks, "registration_usability", "frame0/one-case/untrained row marked usable")
    else:
        pass_gate(checks, "registration_usability", "no frame0/one-case/untrained row is usable")

    temporal_rows = read_csv(packet / "temporal_dictionary_evidence.csv")
    temporal_ready = any("READY" in str(r.get("status", "")) or str(r.get("temporal_dictionary_attempted", "")).lower() == "true" for r in temporal_rows)
    if temporal_ready and not usable_rows:
        fail(checks, "temporal_dictionary_gate", "temporal dictionary marked ready without usable non-reference registration")
    else:
        pass_gate(checks, "temporal_dictionary_gate", "temporal dictionary readiness is gated by usable registration")

    completion = text(packet / "completion_check.md")
    ready = any(token in completion for token in READY_TOKENS)
    unresolved = any(not bool(row["ok"]) for row in checks)
    if ready and unresolved:
        fail(checks, "completion_ready_gate", "completion_check claims ready while blocker gates are unresolved")
    else:
        pass_gate(checks, "completion_ready_gate", "completion status is compatible with validator result")

    return not any(not bool(row["ok"]) for row in checks), checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()
    ok, checks = validate(Path(args.packet))
    payload = {"ok": ok, "checks": checks}
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
