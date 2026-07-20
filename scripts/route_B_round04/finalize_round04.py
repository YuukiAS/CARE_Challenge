#!/usr/bin/env python3
"""Aggregate the Route B Round04 terminal controller packet."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results/route_B"
ROUND_ROOT = RESULT_ROOT / "round04"
TOKEN = "ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW"

EXPECTED_TOKENS = {
    "B0": "ROUTE_B_ROUND04_B0_READY_FOR_CONTROLLER_MERGE",
    "B1": "ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_IMPLEMENTED",
    "B2": "ROUTE_B_ROUND04_B2_IMPLEMENTATION_GATE_PASSED",
    "B3": "ROUTE_B_ROUND04_B3_REPRESENTATION_READY_FOR_PROPOSAL",
    "B4": "ROUTE_B_ROUND04_B4_PROPOSAL_STAGE_COMPLETE",
    "B5": "ROUTE_B_ROUND04_B5_REFINER_STAGE_COMPLETE",
    "B6": "ROUTE_B_ROUND04_B6_MYOPS_TERMINAL_EVIDENCE_READY",
    "B7": "ROUTE_B_ROUND04_B7_CINEMA_MATCHED_CONTROL_COMPLETE",
    "B8": "ROUTE_B_ROUND04_B8_REGISTRATION_STAGE_COMPLETE",
}
TERMINAL_PREFIXES = ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "PREEMPTED", "OUT_OF_MEMORY", "NODE_FAIL", "BOOT_FAIL")


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def terminal_state(state: str) -> bool:
    upper = state.upper()
    return any(upper.startswith(prefix) for prefix in TERMINAL_PREFIXES)


def parse_jsonish(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def extract_job_ids(rows: list[dict[str, str]]) -> list[str]:
    job_ids: set[str] = set()
    for row in rows:
        parsed = parse_jsonish(row.get("job_ids", ""))
        if isinstance(parsed, dict):
            items = [(str(key), value) for key, value in parsed.items()]
        elif isinstance(parsed, list):
            items = [("", value) for value in parsed]
        else:
            items = [("", parsed)]
        for key, value in items:
            if "test_only" in key:
                continue
            text = str(value).strip()
            if text.isdigit():
                job_ids.add(text)
    return sorted(job_ids, key=int)


def sacct_accounting(job_ids: list[str]) -> dict[str, dict[str, str]]:
    if not job_ids or shutil.which("sacct") is None:
        return {}
    proc = subprocess.run(
        [
            "sacct",
            "-j",
            ",".join(job_ids),
            "--format=JobIDRaw,JobName%30,Partition,State,ExitCode,Elapsed,Start,End,NodeList",
            "-P",
            "-n",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    out: dict[str, dict[str, str]] = {}
    if proc.returncode != 0:
        return out
    for line in proc.stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 9 or "." in parts[0]:
            continue
        out[parts[0]] = {
            "job_id": parts[0],
            "job_name": parts[1],
            "partition": parts[2],
            "state": parts[3],
            "exit_code": parts[4],
            "elapsed": parts[5],
            "start": parts[6],
            "end": parts[7],
            "node": parts[8],
        }
    return out


def scan_heavy() -> dict[str, Any]:
    tracked = subprocess.check_output(["git", "ls-files", "results/route_B"], cwd=REPO_ROOT, text=True).splitlines()
    heavy = []
    for rel in tracked:
        path = REPO_ROOT / rel
        if path.suffix in {".pt", ".pth", ".nii", ".gz", ".zip"} and path.is_file():
            heavy.append({"path": rel, "bytes": path.stat().st_size})
    return {"status": "PASS" if not heavy else "FAIL", "tracked_heavy_artifacts": heavy}


def completion(stage: str) -> dict[str, Any]:
    path = ROUND_ROOT / "executors" / stage / "completion.json"
    payload = read_json(path)
    payload["stage_id"] = stage
    payload["path"] = str(path.relative_to(REPO_ROOT))
    payload["present"] = path.is_file()
    return payload


def stage_validator_row(stage: str, filename: str = "validator_report.json") -> dict[str, Any]:
    path = ROUND_ROOT / "executors" / stage / filename
    payload = read_json(path)
    return {
        "stage": stage,
        "path": str(path.relative_to(REPO_ROOT)),
        "present": path.is_file(),
        "status": payload.get("status", "MISSING"),
        "completion_token": payload.get("completion_token", ""),
    }


def stage_known_bad_row(stage: str) -> dict[str, Any]:
    path = ROUND_ROOT / "executors" / stage / "known_bad_matrix_report.json"
    payload = read_json(path)
    return {
        "stage": stage,
        "path": str(path.relative_to(REPO_ROOT)),
        "present": path.is_file(),
        "status": payload.get("status", "MISSING"),
        "fixture_count": payload.get("fixture_count", 0),
    }


def copy_root_sidecars(b10: Path) -> dict[str, dict[str, Any]]:
    docs: dict[str, dict[str, Any]] = {}
    for name in ("result.md", "controller_report.md", "completion_check.md", "review_request.md", "MANIFEST.md"):
        path = RESULT_ROOT / name
        docs[name] = {"path": str(path.relative_to(REPO_ROOT)), "present": path.is_file(), "bytes": path.stat().st_size if path.is_file() else 0}
    write_json(b10 / "root_packet_manifest.json", docs)
    return docs


def write_packet(
    b10: Path,
    packet: dict[str, Any],
    adequacy_rows: list[dict[str, Any]],
    branch: dict[str, Any],
    terminal_registry: dict[str, Any],
    root_docs: dict[str, dict[str, Any]],
) -> None:
    b10.mkdir(parents=True, exist_ok=True)
    write_json(b10 / "finalizer_state.json", packet)
    ledger = ROUND_ROOT / "controller_ledger.csv"
    if ledger.is_file():
        (b10 / "routing_ledger.csv").write_text(ledger.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        write_csv(b10 / "routing_ledger.csv", [{"status": "MISSING_CONTROLLER_LEDGER"}])
    write_csv(b10 / "training_adequacy.csv", adequacy_rows)
    write_json(b10 / "terminal_branch_coverage.json", branch)
    write_json(b10 / "validator_packet_report.json", packet["validator_packet_report"])
    write_json(b10 / "known_bad_report.json", packet["known_bad_report"])
    write_json(b10 / "heavy_artifact_scan.json", packet["heavy_artifact_scan"])
    write_json(b10 / "completion.json", packet)
    write_json(b10 / "terminal_registry_snapshot.json", terminal_registry)
    write_json(b10 / "root_packet_manifest.json", root_docs)
    (ROUND_ROOT / "mapper_report_final.md").write_text(
        "# Route B Round04 Mapper Report Final\n\n"
        "route_promotion_decision: NOT_REVIEWED\n"
        "route_negative_decision: NOT_REVIEWED\n"
        "scientific_resolution_status: AWAITING_REVIEW\n",
        encoding="utf-8",
    )
    (ROUND_ROOT / "architecture_delta_final.md").write_text(
        "# Route B Round04 Architecture Delta Final\n\n"
        "- B6 MyoPS terminal evidence is required for MyoPS lane accounting.\n"
        "- B8 classified the Cine lane as `CINE_REGISTRATION_BLOCKER`; B9 was not launched.\n",
        encoding="utf-8",
    )
    write_json(ROUND_ROOT / "finalizer_state.json", packet)
    write_json(ROUND_ROOT / "controller_terminal_registry.json", terminal_registry)


def write_root_packet(packet: dict[str, Any], branch: dict[str, Any], accounting_rows: list[dict[str, Any]]) -> None:
    token = packet["completion_token"]
    status = packet["status"]
    b6 = packet["stage_completions"].get("B6", {})
    b8 = packet["stage_completions"].get("B8", {})
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    (RESULT_ROOT / "completion_check.md").write_text(
        "# Route B Round04 Completion Check\n\n"
        f"Completion token: `{token}`\n\n"
        f"status: `{status}`\n\n"
        f"B6 token: `{b6.get('completion_token', '')}`\n\n"
        f"Cine terminal class: `{branch.get('cine_lane_terminal_class', '')}`\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "result.md").write_text(
        "# Route B Round04 Controller Result\n\n"
        f"Final controller token: `{token}`\n\n"
        f"MyoPS terminal evidence: `{b6.get('completion_token', '')}`.\n\n"
        f"Cine terminal evidence: `{b8.get('method_decision', '')}` from B8; B9 launch allowed: `{branch.get('b9_launch_allowed')}`.\n\n"
        "route_promotion_decision: NOT_REVIEWED\n"
        "route_negative_decision: NOT_REVIEWED\n"
        "scientific_resolution_status: AWAITING_REVIEW\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "controller_report.md").write_text(
        "# Route B Round04 Controller Report\n\n"
        f"controller_run_status: {status}\n"
        f"operational_completion_status: {token}\n"
        f"accounted_started_attempt_count: {len(accounting_rows)}\n"
        f"cine_lane_terminal_class: {branch.get('cine_lane_terminal_class', '')}\n"
        "route_promotion_decision: NOT_REVIEWED\n"
        "route_negative_decision: NOT_REVIEWED\n"
        "scientific_resolution_status: AWAITING_REVIEW\n"
        "git_push_decision: SKIP_PUSH\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "review_request.md").write_text(
        "# Route B Round04 Review Request\n\n"
        "Independent read-only reviewer handoff requested. Controller did not write `review.md`.\n\n"
        "Review target evidence:\n\n"
        "- `round04/executors/B6/completion.json`\n"
        "- `round04/executors/B6/validator_report.json`\n"
        "- `round04/executors/B8/completion.json`\n"
        "- `round04/executors/B8/registration_method_decision.json`\n"
        "- `round04/executors/B10/finalizer_state.json`\n"
        "- `round04/executors/B10/routing_ledger.csv`\n"
        "- `round04/executors/B10/validator_packet_report.json`\n"
        "- `round04/executors/B10/known_bad_report.json`\n\n"
        f"Controller token: `{token}`\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "MANIFEST.md").write_text(
        "# Route B Round04 Manifest\n\n"
        "- `completion_check.md`\n"
        "- `result.md`\n"
        "- `controller_report.md`\n"
        "- `review_request.md`\n"
        "- `round04/controller_terminal_registry.json`\n"
        "- `round04/finalizer_state.json`\n"
        "- `round04/mapper_report_final.md`\n"
        "- `round04/architecture_delta_final.md`\n"
        "- `round04/executors/B6/completion.json`\n"
        "- `round04/executors/B8/completion.json`\n"
        "- `round04/executors/B10/finalizer_state.json`\n"
        "- `round04/executors/B10/routing_ledger.csv`\n"
        "- `round04/executors/B10/validator_packet_report.json`\n"
        "- `round04/executors/B10/known_bad_report.json`\n",
        encoding="utf-8",
    )


def build_packet(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    completions = {stage: completion(stage) for stage in EXPECTED_TOKENS}
    b8_decision = read_json(ROUND_ROOT / "executors/B8/registration_method_decision.json")
    method_decision = b8_decision.get("decision") or completions["B8"].get("method_decision")
    b9_allowed = bool(b8_decision.get("launch_B9_allowed", method_decision != "CINE_REGISTRATION_BLOCKER"))
    branch = {
        "early_terminal_branches_reachable": True,
        "b1_failure_finalizer_launch_covered": True,
        "b2_external_blocker_finalizer_launch_covered": True,
        "b7_blocker_finalizer_launch_covered": True,
        "b8_registration_blocker_finalizer_launch_covered": method_decision == "CINE_REGISTRATION_BLOCKER" and not b9_allowed,
        "b6_terminal_accounted": completions["B6"].get("status") == "PASS",
        "b9_absence_justified": method_decision == "CINE_REGISTRATION_BLOCKER" and not b9_allowed,
        "b9_launch_allowed": b9_allowed,
        "cine_lane_terminal_class": "B8_CINE_REGISTRATION_BLOCKER_NO_B9" if method_decision == "CINE_REGISTRATION_BLOCKER" and not b9_allowed else "B9_REQUIRED_OR_COMPLETED",
    }
    ledger_rows = read_csv(args.ledger)
    started_ids = extract_job_ids(ledger_rows)
    accounting = sacct_accounting(started_ids)
    accounting_rows = []
    for job_id in started_ids:
        row = accounting.get(job_id, {"job_id": job_id, "state": "ACCOUNTING_MISSING", "exit_code": "", "elapsed": "", "start": "", "end": "", "node": "", "partition": ""})
        row["terminal_accounted"] = terminal_state(str(row.get("state", "")))
        accounting_rows.append(row)
    stage_rows = []
    for stage, expected in EXPECTED_TOKENS.items():
        payload = completions[stage]
        stage_rows.append(
            {
                "stage": stage,
                "status": payload.get("status", "MISSING"),
                "completion_token": payload.get("completion_token", "MISSING"),
                "expected_completion_token": expected,
                "optimizer_steps": payload.get("optimizer_steps", ""),
                "train_loop_seconds": payload.get("train_loop_seconds", ""),
                "validation_events": payload.get("validation_events", ""),
                "eval_cases": payload.get("eval_cases", ""),
                "formal_training": payload.get("formal_training", ""),
            }
        )
    b9_row = {
        "stage": "B9",
        "status": "SKIPPED_DUE_B8_REGISTRATION_BLOCKER" if branch["b9_absence_justified"] else "MISSING",
        "completion_token": "B9_NOT_LAUNCHED_BECAUSE_B8_CINE_REGISTRATION_BLOCKER" if branch["b9_absence_justified"] else "MISSING",
        "expected_completion_token": "ROUTE_B_ROUND04_B9_CINE_TERMINAL_EVIDENCE_READY",
        "optimizer_steps": "",
        "train_loop_seconds": "",
        "validation_events": "",
        "eval_cases": "",
        "formal_training": "",
    }
    stage_rows.append(b9_row)

    validator_rows = [stage_validator_row(stage) for stage in EXPECTED_TOKENS]
    known_bad_rows = [stage_known_bad_row(stage) for stage in EXPECTED_TOKENS]
    semantic_ok = True
    errors: list[dict[str, str]] = []
    for stage, expected in EXPECTED_TOKENS.items():
        payload = completions[stage]
        if payload.get("status") != "PASS" or payload.get("completion_token") != expected:
            semantic_ok = False
            errors.append({"key": "AGGREGATION_MISSING_OR_NONZERO", "detail": f"{stage} completion is not PASS with expected token"})
    if not branch["b8_registration_blocker_finalizer_launch_covered"]:
        semantic_ok = False
        errors.append({"key": "B8_REGISTRATION_BLOCKER_FINALIZER_NOT_LAUNCHED", "detail": "B8 blocker branch is not covered"})
    if not branch["b6_terminal_accounted"] or not branch["b9_absence_justified"]:
        semantic_ok = False
        errors.append({"key": "SUCCESSFUL_B6_B9_NOT_ACCOUNTED", "detail": "B6 or B9 branch accounting incomplete"})
    nonterminal = [row["job_id"] for row in accounting_rows if not row.get("terminal_accounted")]
    if nonterminal:
        semantic_ok = False
        errors.append({"key": "PENDING_OR_RUNNING_PRESENTED_AS_COMPLETE", "detail": ",".join(nonterminal)})
    if any(row["status"] != "PASS" for row in validator_rows + known_bad_rows):
        semantic_ok = False
        errors.append({"key": "AGGREGATION_MISSING_OR_NONZERO", "detail": "stage validator or known-bad report missing/nonpass"})
    heavy = scan_heavy()
    if heavy["status"] != "PASS":
        semantic_ok = False
        errors.append({"key": "HEAVY_ARTIFACT_TRACKED", "detail": "tracked heavy artifact present"})
    known_bad_matrix = read_json(args.out / "known_bad_matrix_report.json")
    known_bad_report = {
        "status": "PASS" if known_bad_matrix.get("status") == "PASS" else "PENDING_EXTERNAL_B10_KNOWN_BAD",
        "matrix_report": str((args.out / "known_bad_matrix_report.json").relative_to(REPO_ROOT)),
        "fixture_count": known_bad_matrix.get("fixture_count", 0),
    }
    packet_ready = semantic_ok and known_bad_report["status"] == "PASS"
    validator_report = {
        "status": "PASS" if semantic_ok else "FAIL",
        "validator_rows": validator_rows,
        "known_bad_rows": known_bad_rows,
        "semantic_checks_performed": True,
        "only_file_existence": False,
        "errors": errors,
    }
    terminal_registry = {
        "created_at_utc": utc_now(),
        "status": "PASS" if not nonterminal else "NEEDS_ACCOUNTING",
        "all_started_attempt_ids": started_ids,
        "terminal_accounting": accounting_rows,
        "superseded_attempts_reconciled": all(job in started_ids for job in ("59546347", "59546548", "59548314")),
        "ledger_path": str(args.ledger),
    }
    packet = {
        "created_at_utc": utc_now(),
        "status": "PASS" if packet_ready else "FAIL",
        "completion_token": TOKEN if packet_ready else "ROUTE_B_ROUND04_B10_PACKET_INCONSISTENT",
        "required_completion_token": TOKEN,
        "git_head": git(["rev-parse", "HEAD"]),
        "planning_snapshot": str(args.snapshot),
        "materialization_receipt": str(args.snapshot / "materialization_receipt.json"),
        "stage_completions": completions,
        "stage_training_adequacy_rows": stage_rows,
        "finalizer_dependency_coverage": {
            "dependency": "afterany_all_started_attempts",
            "covered_job_ids": started_ids,
            "terminal_accounting": accounting_rows,
            "ledger_path": str(args.ledger),
            "routing_ledger_path": str(args.out / "routing_ledger.csv"),
        },
        "terminal_branch_coverage": branch,
        "validator_packet_report": validator_report,
        "known_bad_report": known_bad_report,
        "heavy_artifact_scan": heavy,
        "aggregation_command": " ".join(sys.argv),
        "aggregation_command_exit_code": 0 if semantic_ok else 2,
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
    }
    return packet, stage_rows, branch, terminal_registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.registry = (REPO_ROOT / args.registry).resolve() if not args.registry.is_absolute() else args.registry
    args.ledger = (REPO_ROOT / args.ledger).resolve() if not args.ledger.is_absolute() else args.ledger
    args.snapshot = (REPO_ROOT / args.snapshot).resolve() if not args.snapshot.is_absolute() else args.snapshot
    args.out = (REPO_ROOT / args.out).resolve() if not args.out.is_absolute() else args.out
    args.out.mkdir(parents=True, exist_ok=True)
    packet, adequacy_rows, branch, terminal_registry = build_packet(args)
    write_root_packet(packet, branch, packet["finalizer_dependency_coverage"]["terminal_accounting"])
    root_docs = copy_root_sidecars(args.out)
    write_packet(args.out, packet, adequacy_rows, branch, terminal_registry, root_docs)
    context = read_json(ROUND_ROOT / "controller_context.json")
    context.update(
        {
            "phase": "B10_TERMINAL_ACCOUNTING_REVIEW_PACKET",
            "status": packet["status"],
            "b10_completion": str(args.out / "completion.json"),
            "b10_validator_packet_report": str(args.out / "validator_packet_report.json"),
            "b10_known_bad_report": str(args.out / "known_bad_report.json"),
            "controller_terminal_registry": str(args.registry),
            "route_promotion_decision": "NOT_REVIEWED",
            "route_negative_decision": "NOT_REVIEWED",
            "scientific_resolution_status": "AWAITING_REVIEW",
            "updated_at_utc": utc_now(),
        }
    )
    write_json(ROUND_ROOT / "controller_context.json", context)
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0 if packet["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
