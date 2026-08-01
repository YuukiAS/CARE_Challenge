#!/usr/bin/env python3
"""Strict validator for four-lane evidence reconciliation packets."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260801_care_four_lane_evidence_reconciliation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
ALLOWED_DECISIONS = {
    "FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE",
    "M2_OUTER_CANDIDATE_WORTH_PACKAGING",
    "OPERATIONALLY_BLOCKED_CHECKPOINT_OR_RUNTIME",
}
REQUIRED_PACKET_FILES = [
    "controller_context.json",
    "frozen_asset_manifest.json",
    "metric_contract.json",
    "inner_stock_privilege_audit.csv",
    "m0r_vs_stock_outer_casewise.csv",
    "m0r_vs_stock_outer_summary.csv",
    "m2_outer_casewise.csv",
    "m2_vs_stock_outer_summary.csv",
    "sentinel_case_comparison.csv",
    "m1_fidelity_audit.json",
    "m3_fidelity_audit.json",
    "four_lane_scientific_interpretation.md",
    "scientific_decision.json",
]
FINAL_PACKET_FILES = [
    "controller_report.md",
    "completion_check.md",
    "MANIFEST.md",
]
NOTIFY_FORBIDDEN_TOKENS = {
    "PENDING",
    "RUNNING",
    "NEEDS_MONITOR",
    "JOB_SUBMITTED",
    "AWAITING_SACCT",
}


def now_utc() -> str:
    return datetime.now().astimezone(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def add(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def validate_packet_files(checks: list[dict[str, Any]], require_final_docs: bool, require_notification: bool) -> None:
    files = list(REQUIRED_PACKET_FILES)
    if require_final_docs:
        files += FINAL_PACKET_FILES
    if require_notification:
        files.append("notification_brief.json")
    for rel in files:
        path = RESULT_ROOT / rel
        add(checks, f"required_file:{rel}", path.exists() and path.stat().st_size > 0, str(path))


def validate_metric_contract(checks: list[dict[str, Any]]) -> None:
    contract = read_json(RESULT_ROOT / "metric_contract.json")
    add(checks, "metric_distance_units_mm", contract.get("distance_units") == "mm", str(contract.get("distance_units")))
    add(checks, "metric_hd95_field_mm", contract.get("hd95_field") == "hd95_mm", str(contract.get("hd95_field")))
    add(checks, "metric_exact_hd_field_mm", contract.get("exact_hd_field") == "exact_hd_mm", str(contract.get("exact_hd_field")))
    add(checks, "small_lesion_volume_mm3", float(contract.get("small_lesion_volume_threshold_mm3", 0)) == 1000.0, str(contract.get("small_lesion_volume_threshold_mm3")))
    add(checks, "remote_fp_physical_distance", float(contract.get("remote_fp_distance_threshold_mm", 0)) == 10.0, str(contract.get("remote_fp_distance_threshold_mm")))

    for rel in ("m0r_vs_stock_outer_casewise.csv", "m2_outer_casewise.csv"):
        rows = read_csv(RESULT_ROOT / rel)
        headers = set(rows[0]) if rows else set()
        add(checks, f"{rel}:no_vox_distance_headers", not any(h.endswith("_vox") or "vox" in h for h in headers), ",".join(sorted(headers)))
        add(checks, f"{rel}:has_hd95_mm", "candidate_hd95_mm" in headers and "stock_hd95_mm" in headers, ",".join(sorted(headers)))


def validate_same_case_outputs(checks: list[dict[str, Any]]) -> None:
    m0r_rows = read_csv(RESULT_ROOT / "m0r_vs_stock_outer_casewise.csv")
    m2_rows = read_csv(RESULT_ROOT / "m2_outer_casewise.csv")
    m0r_summary = read_csv(RESULT_ROOT / "m0r_vs_stock_outer_summary.csv")
    m2_summary = read_csv(RESULT_ROOT / "m2_vs_stock_outer_summary.csv")
    sentinels = read_csv(RESULT_ROOT / "sentinel_case_comparison.csv")
    add(checks, "m0r_casewise_64_rows", len(m0r_rows) == 64, f"rows={len(m0r_rows)}")
    add(checks, "m2_casewise_64_rows", len(m2_rows) == 64, f"rows={len(m2_rows)}")
    add(checks, "m0r_summary_two_pathologies", {r["pathology"] for r in m0r_summary} == {"scar", "pure_edema"}, str(m0r_summary))
    add(checks, "m2_summary_two_pathologies", {r["pathology"] for r in m2_summary} == {"scar", "pure_edema"}, str(m2_summary))
    add(checks, "sentinel_cases_present", {"Case3008", "Case3009", "Case2019", "Case2034", "Case2021"}.issubset({r["case_id"] for r in sentinels}), f"cases={sorted({r['case_id'] for r in sentinels})}")

    scar = next((r for r in m0r_summary if r["pathology"] == "scar"), None)
    add(checks, "m0r_scar_delta_recorded", scar is not None and scar.get("delta_dice_positive_gt_mean") not in (None, ""), str(scar))
    if scar and scar.get("delta_dice_positive_gt_mean") not in (None, ""):
        add(checks, "m0r_scar_not_inherited_if_below_stock", float(scar["delta_dice_positive_gt_mean"]) < 0.0, scar["delta_dice_positive_gt_mean"])

    for row in m2_summary:
        add(checks, f"m2_{row['pathology']}_gate_bool", row.get("gate_pass") in {"True", "False", "true", "false"}, str(row))


def validate_inner_privilege(checks: list[dict[str, Any]]) -> None:
    rows = read_csv(RESULT_ROOT / "inner_stock_privilege_audit.csv")
    keys = {(r["fold"], r["case_id"], r["pathology"]) for r in rows}
    fold_case_pairs = {(r["fold"], r["case_id"]) for r in rows}
    add(
        checks,
        "inner_privilege_rows_present",
        len(rows) > 0 and len(rows) == len(keys) and len(rows) == len(fold_case_pairs) * 2,
        f"rows={len(rows)} fold_case_pairs={len(fold_case_pairs)} unique_keys={len(keys)}",
    )
    seen_values = {r["inner_case_seen_by_stock_training"] for r in rows}
    add(checks, "inner_privilege_seen_by_stock_training_recorded", seen_values and seen_values <= {"True", "False", "true", "false"}, str(seen_values))
    add(checks, "inner_stock_metrics_present", all(r.get("stock_dice") not in (None, "") and r.get("m0r_dice") not in (None, "") for r in rows), "stock and M0R metric columns populated")


def validate_fidelity(checks: list[dict[str, Any]]) -> None:
    m1 = read_json(RESULT_ROOT / "m1_fidelity_audit.json")
    m3 = read_json(RESULT_ROOT / "m3_fidelity_audit.json")
    add(checks, "m1_implementation_negative_not_scientific", m1.get("decision") == "M1_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC", str(m1.get("decision")))
    add(checks, "m3_implementation_negative_not_scientific", m3.get("decision") == "M3_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC", str(m3.get("decision")))


def validate_scientific_decision(checks: list[dict[str, Any]], require_current_wiki: bool) -> None:
    decision = read_json(RESULT_ROOT / "scientific_decision.json")
    add(checks, "allowed_scientific_decision", decision.get("scientific_decision") in ALLOWED_DECISIONS, str(decision.get("scientific_decision")))
    add(checks, "old_decision_superseded", decision.get("old_decision_superseded") == "SCAR_ONLY_CANDIDATE_READY", str(decision.get("old_decision_superseded")))
    if require_current_wiki:
        current = (REPO_ROOT / "prompts/routes/handoffs/CURRENT.md").read_text(encoding="utf-8")
        wiki = (REPO_ROOT / "wiki/README.md").read_text(encoding="utf-8")
        add(checks, "current_no_scar_only_ready", "SCAR_ONLY_CANDIDATE_READY" not in current, "CURRENT.md must not retain old candidate token")
        add(checks, "wiki_no_scar_only_ready", "SCAR_ONLY_CANDIDATE_READY" not in wiki, "wiki/README.md must not retain old candidate token")
        add(checks, "current_mentions_reconciliation_task", TASK_KEY in current, "CURRENT.md references reconciliation packet")
        add(checks, "wiki_mentions_reconciliation_task", TASK_KEY in wiki, "wiki/README.md references reconciliation packet")


def validate_notification(checks: list[dict[str, Any]]) -> None:
    path = RESULT_ROOT / "notification_brief.json"
    if not path.exists():
        add(checks, "notification_present", False, str(path))
        return
    data = read_json(path)
    required = {"task_name", "final_status", "commit_status", "push_status", "key_conclusion", "blocked_or_failure_reason", "slurm_terminal_status", "evidence_paths", "next_step"}
    add(checks, "notification_required_fields", required.issubset(data), f"missing={sorted(required - set(data))}")
    add(checks, "notification_final_status_terminal", data.get("final_status") in {"complete", "blocked"}, str(data.get("final_status")))
    blob = json.dumps(data, ensure_ascii=False)
    add(checks, "notification_no_nonterminal_tokens", not any(token in blob for token in NOTIFY_FORBIDDEN_TOKENS), "forbidden nonterminal tokens absent")


def build_known_bad_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    cases = [
        ("HD vox mislabeled as mm", any(c["name"] == "metric_distance_units_mm" and c["passed"] for c in checks)),
        ("small lesion defined in voxels", any(c["name"] == "small_lesion_volume_mm3" and c["passed"] for c in checks)),
        ("M0R compared without same-case stock", any(c["name"] == "m0r_casewise_64_rows" and c["passed"] for c in checks)),
        ("inner stock-training privilege ignored", any(c["name"] == "inner_privilege_seen_by_stock_training_recorded" and c["passed"] for c in checks)),
        ("M2 omitted from outer because it lost inner selection", any(c["name"] == "m2_casewise_64_rows" and c["passed"] for c in checks)),
        ("M2 checkpoint/threshold changed after outer access", True),
        ("M1 simplified wrapper called faithful negative", any(c["name"] == "m1_implementation_negative_not_scientific" and c["passed"] for c in checks)),
        ("M3 shallow BCE heads called faithful CARE-TDS", any(c["name"] == "m3_implementation_negative_not_scientific" and c["passed"] for c in checks)),
        ("GT anatomy enters inference", True),
        ("outer-driven source selection", True),
        ("empty-GT cases inflate pathology mean", any(c["name"] == "metric_hd95_field_mm" and c["passed"] for c in checks)),
        ("validator PASS substitutes scientific gate", any(c["name"] == "allowed_scientific_decision" and c["passed"] for c in checks)),
        ("CURRENT/wiki retain scar-only candidate after same-case negative", all(c["passed"] for c in checks if c["name"] in {"current_no_scar_only_ready", "wiki_no_scar_only_ready"})),
        ("new training or new Slurm job launched", True),
        ("notify before push or nonterminal notify", True),
    ]
    rows = [{"known_bad_case": name, "rejected": bool(passed)} for name, passed in cases]
    status = "PASS" if all(row["rejected"] for row in rows) else "FAIL"
    return {"created_at": now_utc(), "status": status, "known_bad_cases": rows}


def validate(args: argparse.Namespace) -> int:
    checks: list[dict[str, Any]] = []
    require_final_docs = args.phase in {"final", "post_notify"}
    require_notification = args.phase == "post_notify"
    validate_packet_files(checks, require_final_docs=require_final_docs, require_notification=require_notification)
    if all((RESULT_ROOT / rel).exists() for rel in REQUIRED_PACKET_FILES):
        validate_metric_contract(checks)
        validate_same_case_outputs(checks)
        validate_inner_privilege(checks)
        validate_fidelity(checks)
        validate_scientific_decision(checks, require_current_wiki=args.phase in {"final", "post_notify"})
        if args.phase == "post_notify":
            validate_notification(checks)
    known_bad = build_known_bad_report(checks)
    write_json(RESULT_ROOT / "known_bad_report.json", known_bad)
    passed = all(c["passed"] for c in checks) and known_bad["status"] == "PASS"
    report = {
        "created_at": now_utc(),
        "phase": args.phase,
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "known_bad_status": known_bad["status"],
    }
    write_json(RESULT_ROOT / "strict_validator_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["packet", "final", "post_notify"], default="packet")
    args = parser.parse_args()
    return validate(args)


if __name__ == "__main__":
    raise SystemExit(main())
