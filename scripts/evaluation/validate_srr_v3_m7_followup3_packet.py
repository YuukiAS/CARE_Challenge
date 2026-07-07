#!/usr/bin/env python3
"""Fail-closed validator for the SRR-v3 M7 follow-up3 packet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


READY = "M7_FOLLOWUP3_READY_FOR_REVIEW"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def add(checks: list[dict[str, object]], gate: str, ok: bool, reason: str) -> None:
    checks.append({"gate": gate, "ok": bool(ok), "reason": reason})


def validate(packet: Path) -> tuple[bool, list[dict[str, object]]]:
    checks: list[dict[str, object]] = []
    add(checks, "packet_exists", packet.is_dir(), str(packet))
    completion = text(packet / "completion_check.md")
    ready = READY in completion

    monitor_text = "\n".join(
        [
            completion,
            text(packet / "result.md"),
            text(packet / "review_request.md"),
            text(packet / "commands_run.md"),
        ]
    )
    monitor_tokens = [
        "M7_FOLLOWUP2_NEEDS_MONITOR",
        "M7_FOLLOWUP3_NEEDS_MONITOR",
        "PENDING_MONITOR",
        "PENDING_PRIORITY",
        "JOB_SUBMITTED",
        "RUNNING",
        "AWAITING_SACCT",
        "TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED",
    ]
    add(checks, "no_ready_monitor_tokens", not (ready and any(tok in monitor_text for tok in monitor_tokens)), "ready packet must not contain monitor-only tokens")

    adequacy = read_csv(packet / "followup2_training_adequacy.csv")
    adequacy_text = json.dumps(adequacy)
    pass_adequacy = bool(adequacy) and "PENDING_MONITOR" not in adequacy_text and any(str(r.get("adequacy_decision", "")).startswith("PASS") for r in adequacy)
    add(checks, "training_adequacy_aggregated", (not ready) or pass_adequacy, "followup2 training adequacy must be post-job aggregation")

    reagg = text(packet / "m7_followup3_runtime_reaggregation_report.md")
    slurm = text(packet / "m7_followup3_slurm_completion_record.md")
    add(
        checks,
        "slurm_completion_record",
        (not ready) or ("job_state: `COMPLETED`" in slurm and "exit_code: `0:0`" in slurm and "aggregation_exit_code: `0`" in reagg),
        "ready packet requires completed Slurm and aggregation records",
    )

    reg_rows = read_csv(packet / "registration_same_subset_matrix.csv")
    usable = [r for r in reg_rows if str(r.get("usable_for_temporal_dictionary", "")).lower() == "true" or r.get("m7_continued_decision") == "USABLE_NONREFERENCE_REGISTRATION_ROW"]
    temporal_rows = read_csv(packet / "temporal_dictionary_evidence.csv")
    temporal_text = json.dumps(temporal_rows)
    temporal_index = packet / "temporal_dictionary_index.json"
    temporal_executed = bool(temporal_rows) and temporal_index.is_file() and "TEMPORAL_DICTIONARY_FOLLOWUP3_EXECUTED" in temporal_text
    add(checks, "temporal_dictionary_executed_if_usable", (not ready) or (not usable) or temporal_executed, "usable registration requires temporal dictionary execution")
    no_frame0_only = "FRAME0_ONLY" not in temporal_text and "NO_WARP_ONLY" not in temporal_text and "DESCRIPTOR_ONLY" not in temporal_text
    add(checks, "temporal_dictionary_not_frame0_only", (not ready) or (not usable) or no_frame0_only, "temporal dictionary must not be frame0/no-warp/descriptor only")

    best_rows = read_csv(packet / "followup2_same_split_help_harm.csv")
    mixed = [
        r
        for r in best_rows
        if str(r.get("split_role", "formal_val")) != "formal_val"
        or str(r.get("eligible_for_best_variant_decision", "true")).lower() != "true"
    ]
    add(checks, "formal_diagnostic_boundary", (not ready) or not mixed, "diagnostic rows must not drive formal best-variant decision")

    blocker_text = "\n".join([completion, text(packet / "route_to_leaderboard_gap_report.md")])
    forbidden = [
        "route_promotion_decision: `PROMOTE",
        "hosted_metric_claim: `true`",
        "validation_packaging_or_upload: `true`",
        "status: `LEADERBOARD_READY`",
        "status: `CHALLENGE_READY`",
        "leaderboard_readiness: `true`",
        "challenge_readiness: `true`",
    ]
    add(checks, "no_promotion_claims", not any(tok in blocker_text for tok in forbidden), "follow-up3 cannot claim route promotion or challenge readiness")

    return not any(not bool(c["ok"]) for c in checks), checks


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
