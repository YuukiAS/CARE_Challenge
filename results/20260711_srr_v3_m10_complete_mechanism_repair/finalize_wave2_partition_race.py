#!/usr/bin/env python3
"""Finalize M10 Wave 2 by aggregating the winning partition-race runtime."""

from __future__ import annotations

import argparse
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
    for phase in PHASES:
        cmd = [
            "env",
            "PYTHONPATH=.",
            "python",
            "scripts/evaluation/evaluate_srr_v3_m10_full_case.py",
            "--phase",
            phase,
            "--runtime-root",
            runtime_root,
        ]
        cp = run(cmd, cwd)
        result["commands"].append(command_record(cmd, cp))
        if cp.returncode != 0:
            args.result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return cp.returncode

    agg_cmd = ["env", "PYTHONPATH=.", "python", "scripts/evaluation/aggregate_srr_v3_m10_myops.py", "--all", "--runtime-root", runtime_root]
    for phase in PHASES:
        job_id = str(chain["jobs"][phase])
        state = sacct(job_id, cwd)
        agg_cmd.extend(["--job-id", f"{phase}={job_id}"])
        agg_cmd.extend(["--job-state", f"{phase}={state['state']}"])
        agg_cmd.extend(["--job-exit-code", f"{phase}={state['exit_code']}"])
        agg_cmd.extend(["--job-log", f"{phase}=logs/{chain['log_prefixes'][phase]}_{job_id}_<timestamp>.log"])
    cp = run(agg_cmd, cwd)
    result["commands"].append(command_record(agg_cmd, cp))
    result["status"] = "TERMINAL_RUNTIME_EVIDENCE" if cp.returncode == 0 else "NEEDS_EVIDENCE"
    args.result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return cp.returncode


if __name__ == "__main__":
    raise SystemExit(main())
