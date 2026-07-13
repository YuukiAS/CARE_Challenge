#!/usr/bin/env python3
"""Finalize M10 Wave 2 by aggregating the winning partition-race runtime."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import shlex
import subprocess
from typing import Any


PHASES = [
    "d0_control",
    "d1_spatial_br2",
    "d2_hierarchical_psip",
    "d3_full_propref",
    "hard_negative_refresh",
    "no_context_control",
    "alignment_control",
]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def sacct(job_id: str, cwd: Path) -> dict[str, str]:
    cp = run(
        ["sacct", "-j", job_id, "--parsable2", "--noheader", "--format=JobIDRaw,State,ExitCode,Elapsed,NodeList"],
        cwd,
    )
    if cp.returncode != 0 or not cp.stdout.strip():
        return {"job_id": job_id, "state": "AWAITING_SACCT", "exit_code": "UNKNOWN", "elapsed": "UNKNOWN", "node": "UNKNOWN"}
    parts = cp.stdout.strip().splitlines()[0].split("|")
    while len(parts) < 5:
        parts.append("UNKNOWN")
    return {"job_id": parts[0], "state": parts[1].split()[0], "exit_code": parts[2], "elapsed": parts[3], "node": parts[4]}


def command_record(cmd: list[str], cp: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "command": " ".join(shlex.quote(part) for part in cmd),
        "exit_code": cp.returncode,
        "stdout_tail": cp.stdout[-4000:],
        "stderr_tail": cp.stderr[-4000:],
    }


def retained_d0_metadata(submission_path: Path, cwd: Path) -> dict[str, str]:
    ledger_path = submission_path.with_name(submission_path.name.replace("_submission.json", "_job_ledger.csv"))
    d0_job_id = ""
    if ledger_path.is_file():
        with ledger_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                d0_job_id = str(row.get("upstream_d0_job_id") or "").strip()
                if d0_job_id:
                    break
    candidates = sorted(
        (
            cwd / "results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor"
        ).glob("partition_race_retry*/htzhulab/variants/m10_d0_static_matched_formal/summary.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    runtime_root = ""
    summary_path = ""
    if candidates:
        summary_path = str(candidates[0])
        runtime_root = str(candidates[0].parents[2])
    return {
        "job_id": d0_job_id,
        "runtime_root": runtime_root,
        "summary_path": summary_path,
        "source": str(ledger_path),
    }


def select_winner(submission: dict[str, Any], watcher: dict[str, Any], cwd: Path) -> tuple[str, str, dict[str, dict[str, str]]]:
    chain_states: dict[str, dict[str, str]] = {}
    complete_partitions: list[str] = []
    for partition, chain in submission["chains"].items():
        states = {phase: sacct(str(job_id), cwd) for phase, job_id in chain["jobs"].items()}
        chain_states[partition] = {phase: f"{state['state']}({state['exit_code']})" for phase, state in states.items()}
        if all(state["state"] == "COMPLETED" and state["exit_code"] == "0:0" for state in states.values()):
            complete_partitions.append(partition)
    watcher_winner = str(watcher.get("winner_partition") or "")
    if watcher_winner in complete_partitions:
        return watcher_winner, "watcher_winner_completed", chain_states
    if complete_partitions:
        return complete_partitions[0], "first_completed_chain", chain_states
    if watcher_winner:
        return watcher_winner, "watcher_winner_without_complete_chain", chain_states
    return "", "no_completed_chain", chain_states


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--watcher-state", required=True, type=Path)
    parser.add_argument("--result-path", required=True, type=Path)
    args = parser.parse_args()

    cwd = Path.cwd()
    submission = json.loads(args.submission.read_text(encoding="utf-8"))
    watcher = json.loads(args.watcher_state.read_text(encoding="utf-8")) if args.watcher_state.is_file() else {}
    winner, reason, chain_states = select_winner(submission, watcher, cwd)
    result: dict[str, Any] = {
        "winner_partition": winner,
        "winner_reason": reason,
        "chain_states": chain_states,
        "commands": [],
        "status": "NEEDS_EVIDENCE",
    }
    if not winner:
        args.result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 2

    chain = submission["chains"][winner]
    runtime_root = chain["runtime_root"]
    d0_meta = retained_d0_metadata(args.submission, cwd)
    result["retained_upstream_d0"] = d0_meta
    if not d0_meta.get("runtime_root") or not d0_meta.get("job_id"):
        result["status"] = "NEEDS_EVIDENCE"
        result["error"] = "retained upstream D0 runtime root or job id not found"
        args.result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 2

    phase_runtime_roots = {phase: runtime_root for phase in PHASES}
    phase_runtime_roots["d0_control"] = d0_meta["runtime_root"]
    phase_job_ids = {phase: str(job_id) for phase, job_id in chain["jobs"].items()}
    phase_job_ids["d0_control"] = d0_meta["job_id"]

    for phase in PHASES:
        cmd = [
            "env",
            "PYTHONPATH=.",
            "python",
            "scripts/evaluation/evaluate_srr_v3_m10_full_case.py",
            "--phase",
            phase,
            "--runtime-root",
            phase_runtime_roots[phase],
        ]
        cp = run(cmd, cwd)
        result["commands"].append(command_record(cmd, cp))
        if cp.returncode != 0:
            args.result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return cp.returncode

    for phase in PHASES:
        job_id = str(phase_job_ids[phase])
        state = sacct(job_id, cwd)
        agg_cmd = [
            "env",
            "PYTHONPATH=.",
            "python",
            "scripts/evaluation/aggregate_srr_v3_m10_myops.py",
            "--phase",
            phase,
            "--runtime-root",
            phase_runtime_roots[phase],
            "--job-id",
            f"{phase}={job_id}",
            "--job-state",
            f"{phase}={state['state']}",
            "--job-exit-code",
            f"{phase}={state['exit_code']}",
            "--job-log",
            f"{phase}=logs/{chain['log_prefixes'][phase]}_{job_id}_<timestamp>.log",
        ]
        cp = run(agg_cmd, cwd)
        result["commands"].append(command_record(agg_cmd, cp))
        if cp.returncode != 0:
            args.result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return cp.returncode

    component_cmd = [
        "env",
        "PYTHONPATH=.",
        "python",
        "-c",
        "from scripts.evaluation.aggregate_srr_v3_m10_myops import PHASES, aggregate_component_audit; "
        "raise SystemExit(0 if aggregate_component_audit(list(PHASES.values())) == 'TERMINAL_RUNTIME_EVIDENCE' else 2)",
    ]
    cp = run(component_cmd, cwd)
    result["commands"].append(command_record(component_cmd, cp))
    result["status"] = "TERMINAL_RUNTIME_EVIDENCE" if cp.returncode == 0 else "NEEDS_EVIDENCE"
    args.result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return cp.returncode


if __name__ == "__main__":
    raise SystemExit(main())
