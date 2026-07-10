#!/usr/bin/env python3
"""Finalize a CARE milestone/controller packet after Slurm jobs reach terminal state."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any


MONITOR_STATES = {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING", "AWAITING_SACCT"}
SUCCESS_STATES = {"COMPLETED"}
FAILED_STATES = {"FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY", "PREEMPTED", "BOOT_FAIL"}


def run(cmd: str | list[str], cwd: Path, shell: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, shell=shell, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def acquire_lock(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)


def read_fixture(path: Path) -> dict[str, dict[str, str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    jobs: dict[str, dict[str, str]] = {}
    for job_id, value in raw.get("jobs", raw).items():
        jobs[str(job_id)] = {str(k): str(v) for k, v in value.items()}
    return jobs


def sacct_job(job_id: str, repo_root: Path) -> dict[str, str]:
    fields = "JobIDRaw,State,ExitCode,Elapsed,NodeList"
    cp = run(["sacct", "-j", job_id, "--parsable2", "--noheader", f"--format={fields}"], repo_root)
    if cp.returncode != 0 or not cp.stdout.strip():
        return {
            "job_id": job_id,
            "state": "AWAITING_SACCT",
            "exit_code": "UNKNOWN",
            "elapsed": "UNKNOWN",
            "node": "UNKNOWN",
            "sacct_error": (cp.stderr or cp.stdout).strip(),
        }
    first = cp.stdout.strip().splitlines()[0].split("|")
    while len(first) < 5:
        first.append("UNKNOWN")
    return {
        "job_id": job_id,
        "state": first[1].split()[0],
        "exit_code": first[2],
        "elapsed": first[3],
        "node": first[4],
    }


def load_job_states(job_ids: list[str], repo_root: Path, fixture: Path | None) -> dict[str, dict[str, str]]:
    fixture_jobs = read_fixture(fixture) if fixture else {}
    jobs: dict[str, dict[str, str]] = {}
    for job_id in job_ids:
        jobs[job_id] = fixture_jobs.get(job_id) or sacct_job(job_id, repo_root)
        jobs[job_id].setdefault("job_id", job_id)
        jobs[job_id]["state"] = jobs[job_id].get("state", "UNKNOWN").split()[0].upper()
    return jobs


def write_state(result_dir: Path, state: dict[str, Any]) -> None:
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "finalizer_state.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def command_record(command: str, cp: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "command": command,
        "exit_code": cp.returncode,
        "stdout_tail": cp.stdout[-4000:],
        "stderr_tail": cp.stderr[-4000:],
    }


def maybe_commit(repo_root: Path, files: list[str], message: str) -> tuple[str | None, list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    if any(Path(path).name == "review.md" for path in files):
        raise RuntimeError("finalizer must not stage or commit review.md")
    for file_path in files:
        cp = run(["git", "add", "-f", file_path], repo_root)
        records.append(command_record("git add -f " + shlex.quote(file_path), cp))
        if cp.returncode != 0:
            return None, records
    cp = run(["git", "commit", "-m", message], repo_root)
    records.append(command_record("git commit -m " + shlex.quote(message), cp))
    if cp.returncode != 0:
        return None, records
    head = run(["git", "rev-parse", "HEAD"], repo_root)
    records.append(command_record("git rev-parse HEAD", head))
    return head.stdout.strip() if head.returncode == 0 else None, records


def final_state_from_jobs(jobs: dict[str, dict[str, str]], pending_checks: int) -> str:
    states = {job.get("state", "UNKNOWN").upper() for job in jobs.values()}
    if states & MONITOR_STATES:
        return "NEEDS_MONITOR"
    if states <= SUCCESS_STATES:
        return "JOBS_COMPLETED"
    if states & FAILED_STATES:
        return "RUNTIME_FAILURE"
    if "PENDING" in states and pending_checks < 12:
        return "NEEDS_MONITOR"
    return "NEEDS_EVIDENCE"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-key", required=True)
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--required-job-id", action="append", default=[])
    parser.add_argument("--runtime-output-path", action="append", default=[])
    parser.add_argument("--log-path", action="append", default=[])
    parser.add_argument("--aggregation-command", default="")
    parser.add_argument("--validator-command", action="append", default=[])
    parser.add_argument("--mapper-final-command", default="")
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--sacct-fixture", type=Path)
    parser.add_argument("--pending-check-count", type=int, default=0)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--commit-message", default="Finalize CARE milestone packet")
    parser.add_argument("--tracked-file", action="append", default=[])
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    result_dir = args.result_dir
    lock_path = args.lock_path or result_dir / ".finalizer.lock"
    git_head_before = run(["git", "rev-parse", "HEAD"], repo_root).stdout.strip()
    state: dict[str, Any] = {
        "task_key": args.task_key,
        "required_job_ids": args.required_job_id,
        "job_states": {},
        "exit_codes": {},
        "elapsed": {},
        "log_paths": args.log_path,
        "runtime_output_paths": args.runtime_output_path,
        "aggregation_command": args.aggregation_command,
        "aggregation_exit_code": None,
        "validator_commands": args.validator_command,
        "validator_exit_codes": [],
        "mapper_final_status": "not_requested" if not args.mapper_final_command else "pending",
        "lock_path": str(lock_path),
        "git_head_before": git_head_before,
        "git_commit_after": None,
        "final_state": "INITIALIZING",
        "records": [],
    }

    try:
        lock_fd = acquire_lock(lock_path)
    except FileExistsError:
        state["final_state"] = "NEEDS_MONITOR"
        state["lock_error"] = "lock already exists; another finalizer or manual resume may be active"
        write_state(result_dir, state)
        return 2

    try:
        os.write(lock_fd, str(os.getpid()).encode("utf-8"))
        jobs = load_job_states(args.required_job_id, repo_root, args.sacct_fixture)
        state["job_states"] = {jid: job.get("state") for jid, job in jobs.items()}
        state["exit_codes"] = {jid: job.get("exit_code", job.get("ExitCode", "UNKNOWN")) for jid, job in jobs.items()}
        state["elapsed"] = {jid: job.get("elapsed", "UNKNOWN") for jid, job in jobs.items()}
        state["nodes"] = {jid: job.get("node", "UNKNOWN") for jid, job in jobs.items()}

        job_state = final_state_from_jobs(jobs, args.pending_check_count)
        if job_state == "NEEDS_MONITOR":
            state["final_state"] = "NEEDS_MONITOR"
            write_state(result_dir, state)
            return 0
        if job_state == "RUNTIME_FAILURE":
            state["final_state"] = "RUNTIME_FAILURE"
            write_state(result_dir, state)
            return 1

        missing_outputs = [path for path in args.runtime_output_path if not (repo_root / path).exists()]
        if missing_outputs:
            state["final_state"] = "NEEDS_EVIDENCE"
            state["missing_runtime_outputs"] = missing_outputs
            write_state(result_dir, state)
            return 1

        if args.aggregation_command:
            cp = run(args.aggregation_command, repo_root, shell=True)
            state["aggregation_exit_code"] = cp.returncode
            state["records"].append(command_record(args.aggregation_command, cp))
            if cp.returncode != 0:
                state["final_state"] = "NEEDS_EVIDENCE"
                write_state(result_dir, state)
                return 1

        for command in args.validator_command:
            cp = run(command, repo_root, shell=True)
            state["validator_exit_codes"].append(cp.returncode)
            state["records"].append(command_record(command, cp))
            if cp.returncode != 0:
                state["final_state"] = "NEEDS_REVISION"
                write_state(result_dir, state)
                return 1

        if args.mapper_final_command:
            cp = run(args.mapper_final_command, repo_root, shell=True)
            state["records"].append(command_record(args.mapper_final_command, cp))
            state["mapper_final_status"] = "complete" if cp.returncode == 0 else "failed"
            if cp.returncode != 0:
                state["final_state"] = "NEEDS_REVISION"
                write_state(result_dir, state)
                return 1

        diff_check = run(["git", "diff", "--check"], repo_root)
        state["records"].append(command_record("git diff --check", diff_check))
        if diff_check.returncode != 0:
            state["final_state"] = "NEEDS_REVISION"
            write_state(result_dir, state)
            return 1

        if args.commit:
            commit_after, commit_records = maybe_commit(repo_root, args.tracked_file, args.commit_message)
            state["records"].extend(commit_records)
            state["git_commit_after"] = commit_after
            if not commit_after:
                state["final_state"] = "NEEDS_EVIDENCE"
                write_state(result_dir, state)
                return 1

        state["final_state"] = "PACKET_COMMITTED_FOR_REVIEW" if args.commit else "READY_FOR_LOCAL_PACKET_COMMIT"
        write_state(result_dir, state)
        return 0
    finally:
        os.close(lock_fd)


if __name__ == "__main__":
    raise SystemExit(main())
