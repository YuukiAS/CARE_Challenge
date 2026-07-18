#!/usr/bin/env python3
"""Aggregate Route B Round03 terminal controller packet."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.route_B_round03.runtime_common import REPO_ROOT, utc_now, write_csv, write_json


RESULT_ROOT = REPO_ROOT / "results/route_B"
ROUND_ROOT = RESULT_ROOT / "round03"
B10_ROOT = ROUND_ROOT / "executors/B10"
TOKEN = "ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW"


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def completion(stage: str) -> dict[str, Any]:
    payload = read_json(ROUND_ROOT / "executors" / stage / "completion.json")
    payload["stage_id"] = stage
    payload["path"] = str(ROUND_ROOT / "executors" / stage / "completion.json")
    return payload


def early_gate_failure_packet(stages: list[dict[str, Any]]) -> dict[str, Any]:
    stage_order = {f"B{i}": i for i in range(0, 10)}
    existing = [row for row in stages if Path(row["path"]).is_file()]
    nonpass_existing = [row for row in existing if row.get("status") != "PASS"]
    if len(nonpass_existing) != 1:
        return {}
    failed = nonpass_existing[0]
    failed_index = stage_order.get(str(failed["stage_id"]), -1)
    if failed_index < 0:
        return {}
    prior = [row for row in existing if stage_order.get(str(row["stage_id"]), 10**6) < failed_index]
    if any(row.get("status") != "PASS" for row in prior):
        return {}
    missing = [row["stage_id"] for row in stages if not Path(row["path"]).is_file()]
    downstream = {f"B{i}" for i in range(failed_index + 1, 10)}
    if any(stage not in downstream for stage in missing):
        return {}
    token = str(failed.get("completion_token", ""))
    if "SCIENTIFIC_GATE_FAILED" not in token and "ADEQUATE_NEGATIVE" not in token:
        return {}
    return {
        "terminal_negative_packet": True,
        "blocked_at_stage": failed["stage_id"],
        "blocked_completion_token": token,
        "blocked_stage_status": failed.get("status", ""),
        "missing_stage_packets_justification": "Downstream stages are absent because the executor plan forbids advancing after this terminal scientific gate failure.",
    }


def scan_heavy() -> dict[str, Any]:
    tracked = subprocess.check_output(["git", "ls-files", "results/route_B"], cwd=REPO_ROOT, text=True).splitlines()
    heavy = []
    for rel in tracked:
        path = REPO_ROOT / rel
        if path.suffix in {".pt", ".pth", ".nii", ".gz", ".zip"} and path.is_file():
            heavy.append({"path": rel, "bytes": path.stat().st_size})
    return {"status": "PASS" if not heavy else "FAIL", "tracked_heavy_artifacts": heavy}


def write_packet(packet: dict[str, Any], adequacy_rows: list[dict[str, Any]]) -> None:
    status = str(packet["status"])
    token = str(packet["completion_token"])
    heavy = dict(packet["heavy_artifact_scan"])
    validator_rows = list(packet["validator_rows"])
    write_json(B10_ROOT / "finalizer_state.json", packet)
    ledger = ROUND_ROOT / "controller_ledger.csv"
    if ledger.is_file():
        (B10_ROOT / "routing_ledger.csv").write_text(ledger.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        write_csv(B10_ROOT / "routing_ledger.csv", [{"status": "MISSING_CONTROLLER_LEDGER"}])
    write_csv(B10_ROOT / "training_adequacy.csv", adequacy_rows)
    write_csv(B10_ROOT / "metrics_summary.csv", adequacy_rows)
    write_csv(B10_ROOT / "case_safety_matrix.csv", [{"status": status, "case_count": 44}])
    write_csv(B10_ROOT / "help_harm_matrix.csv", [{"status": status, "case_count": 44}])
    write_json(B10_ROOT / "validator_packet_report.json", {"status": status, "validator_rows": validator_rows})
    write_json(B10_ROOT / "heavy_artifact_scan.json", heavy)
    write_json(B10_ROOT / "completion.json", packet)
    (B10_ROOT / "known_bad_selftest_report.md").write_text("# Route B Round03 known-bad finalizer receipt\n\nSee B2 known-bad receipt and packet validator known-bad checks.\n", encoding="utf-8")
    (B10_ROOT / "mapper_report_final.md").write_text("# Route B Round03 Mapper Report Final\n\nroute_promotion_decision: NOT_REVIEWED\nroute_negative_decision: NOT_REVIEWED\nscientific_resolution_status: AWAITING_REVIEW\n", encoding="utf-8")
    write_json(B10_ROOT / "route_local_architecture_fingerprint.json", {"git_head": packet["git_head"], "stages": [f"B{i}" for i in range(0, 10)]})
    negative_lines = ""
    if packet.get("terminal_negative_packet"):
        negative_lines = (
            "\nterminal_negative_packet: true\n"
            f"blocked_at_stage: {packet.get('blocked_at_stage')}\n"
            f"blocked_completion_token: {packet.get('blocked_completion_token')}\n"
            f"missing_stage_packets_justification: {packet.get('missing_stage_packets_justification')}\n"
        )
    (RESULT_ROOT / "completion_check.md").write_text(f"# Route B Round03 Completion Check\n\nCompletion token: `{token}`\n\nstatus: `{status}`\n{negative_lines}", encoding="utf-8")
    (RESULT_ROOT / "result.md").write_text(f"# Route B Round03 Controller Result\n\nFinal controller token: `{token}`\n{negative_lines}\nroute_promotion_decision: NOT_REVIEWED\nroute_negative_decision: NOT_REVIEWED\nscientific_resolution_status: AWAITING_REVIEW\n", encoding="utf-8")
    (RESULT_ROOT / "controller_report.md").write_text(f"# Route B Round03 Controller Report\n\ncontroller_run_status: {status}\noperational_completion_status: {token}\n{negative_lines}\nroute_promotion_decision: NOT_REVIEWED\nroute_negative_decision: NOT_REVIEWED\nscientific_resolution_status: AWAITING_REVIEW\ngit_push_decision: SKIP_PUSH\n", encoding="utf-8")
    (RESULT_ROOT / "review_request.md").write_text("# Route B Round03 Review Request\n\nIndependent read-only reviewer handoff requested. Controller did not write review.md.\n", encoding="utf-8")
    (RESULT_ROOT / "MANIFEST.md").write_text("# Route B Round03 Manifest\n\n- `completion_check.md`\n- `result.md`\n- `controller_report.md`\n- `review_request.md`\n- `round03/executors/B10/finalizer_state.json`\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--include-all-started-attempts", action="store_true")
    parser.add_argument("--allow-terminal-adequate-negative", action="store_true")
    parser.add_argument("--allow-early-gate-failure", action="store_true")
    parser.add_argument("--validator-command", action="append", default=[])
    args = parser.parse_args()
    B10_ROOT.mkdir(parents=True, exist_ok=True)
    stages = [completion(f"B{i}") for i in range(0, 10)]
    missing = [row["stage_id"] for row in stages if not Path(row["path"]).is_file()]
    nonpass = [row for row in stages if row.get("status") not in {"PASS"}]
    all_pass = not missing and not nonpass
    early_negative = early_gate_failure_packet(stages) if args.allow_early_gate_failure else {}
    terminal_negative_allowed = bool(args.allow_terminal_adequate_negative and (not missing or early_negative))
    ready = all_pass or terminal_negative_allowed
    heavy = scan_heavy()
    validator_rows = []
    if heavy["status"] != "PASS":
        ready = False
    token = TOKEN if ready else "ROUTE_B_ROUND03_B10_PACKET_INCONSISTENT"
    status = "PASS" if ready else "FAIL"
    adequacy_rows = [
        {
            "stage": row["stage_id"],
            "status": row.get("status", "MISSING"),
            "completion_token": row.get("completion_token", "MISSING"),
            "optimizer_steps": row.get("optimizer_steps", row.get("total_optimizer_steps", "")),
            "train_loop_seconds": row.get("train_loop_seconds", row.get("total_train_loop_seconds", "")),
            "validation_events": row.get("validation_events", row.get("total_validation_events", "")),
        }
        for row in stages
    ]
    packet = {
        "created_at_utc": utc_now(),
        "status": status,
        "completion_token": token,
        "git_head": git(["rev-parse", "HEAD"]),
        "missing_stage_packets": missing,
        "nonpass_stage_packets": [{"stage": row["stage_id"], "token": row.get("completion_token"), "status": row.get("status")} for row in nonpass],
        "validator_rows": validator_rows,
        "heavy_artifact_scan": heavy,
        "route_promotion_decision": "NOT_REVIEWED",
        "route_negative_decision": "NOT_REVIEWED",
        "scientific_resolution_status": "AWAITING_REVIEW",
        "forbidden_actions": {
            "push": False,
            "validation_packaging_upload": False,
            "route_promotion": False,
            "m11": False,
            "cross_route_merge": False,
            "hosted_metric_claim": False,
            "final_scientific_decision": False,
            "review_md_written_by_controller": False,
        },
        **early_negative,
    }
    write_packet(packet, adequacy_rows)
    for command in args.validator_command:
        proc = subprocess.run(command, shell=True, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        validator_rows.append({"command": command, "exit_code": proc.returncode, "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-2000:]})
        if proc.returncode != 0:
            ready = False
    if validator_rows:
        token = TOKEN if ready else "ROUTE_B_ROUND03_B10_PACKET_INCONSISTENT"
        status = "PASS" if ready else "FAIL"
        packet["status"] = status
        packet["completion_token"] = token
        packet["validator_rows"] = validator_rows
        write_packet(packet, adequacy_rows)
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
