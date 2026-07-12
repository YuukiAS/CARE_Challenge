#!/usr/bin/env python3
"""Finalize a CARE milestone/controller packet after Slurm jobs reach terminal state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
from typing import Any


MONITOR_STATES = {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING", "AWAITING_SACCT"}
SUCCESS_STATES = {"COMPLETED"}
FAILED_STATES = {"FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY", "PREEMPTED", "BOOT_FAIL"}
TERMINAL_STATES = SUCCESS_STATES | FAILED_STATES
DEFAULT_ACCOUNTING_RETRY_SECONDS = 3600
ACCOUNTING_EXHAUSTION_BACKENDS = {"tmux_watcher", "resubmit_finalizer"}
RETRYABLE_FAILURE_CLASSES = {"STARTUP_ENVIRONMENT_FAILURE", "STARTUP_WRAPPER_FAILURE", "PREEMPTED_RETRYABLE", "NODE_FAILURE_RETRYABLE"}


def run(cmd: str | list[str], cwd: Path, shell: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, shell=shell, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_lock(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def lock_is_stale(path: Path, ttl_seconds: int) -> tuple[bool, str]:
    data = read_lock(path)
    pid = int(data.get("pid", -1)) if str(data.get("pid", "")).lstrip("-").isdigit() else -1
    host = str(data.get("host", ""))
    started = float(data.get("started_epoch", 0.0) or 0.0)
    age = time.time() - started if started else 10**9
    if host == socket.gethostname() and pid_is_running(pid):
        return False, "active local process still owns lock"
    if host != socket.gethostname() and age < ttl_seconds:
        return False, "foreign-host lock is younger than stale ttl"
    if pid > 0 and not pid_is_running(pid):
        return True, "pid is not running"
    if age >= ttl_seconds:
        return True, "lock exceeded stale ttl"
    return False, "lock is not stale"


def acquire_lock(path: Path, task_key: str, ttl_seconds: int, recover_stale: bool) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "started_epoch": time.time(),
        "task_key": task_key,
    }
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        stale, reason = lock_is_stale(path, ttl_seconds)
        if recover_stale and stale:
            path.unlink()
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            payload["recovered_stale_lock_reason"] = reason
        else:
            raise FileExistsError(reason)
    os.write(fd, json.dumps(payload, sort_keys=True).encode("utf-8"))
    os.fsync(fd)
    return fd


def read_fixture(path: Path) -> dict[str, dict[str, str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    jobs: dict[str, dict[str, str]] = {}
    for job_id, value in raw.get("jobs", raw).items():
        jobs[str(job_id)] = value
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


def load_job_states(job_ids: list[str], repo_root: Path, fixture: Path | None, fixture_poll: int = 0) -> dict[str, dict[str, str]]:
    fixture_jobs = read_fixture(fixture) if fixture else {}
    jobs: dict[str, dict[str, str]] = {}
    for job_id in job_ids:
        fixture_value = fixture_jobs.get(job_id)
        if isinstance(fixture_value, dict) and "polls" in fixture_value:
            polls = fixture_value.get("polls", [])
            fixture_value = polls[min(fixture_poll, len(polls) - 1)] if polls else {}
        jobs[job_id] = fixture_value or sacct_job(job_id, repo_root)
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


def build_finalizer_retry_command(args: argparse.Namespace, retry_seconds: int | None = None) -> str:
    parts = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--task-key",
        args.task_key,
        "--result-dir",
        str(args.result_dir),
        "--stage",
        args.stage,
        "--awaiting-sacct-retry-seconds",
        str(DEFAULT_ACCOUNTING_RETRY_SECONDS if retry_seconds is None else retry_seconds),
        "--awaiting-sacct-retry-interval",
        str(args.awaiting_sacct_retry_interval),
        "--accounting-exhaustion-backend",
        args.accounting_exhaustion_backend,
        "--recover-stale-lock",
    ]
    lock_path = args.lock_path or args.result_dir / ".finalizer.lock"
    parts.extend(["--lock-path", str(lock_path)])
    for job_id in args.required_job_id:
        parts.extend(["--required-job-id", job_id])
    for path in args.runtime_output_path:
        parts.extend(["--runtime-output-path", path])
    for path in args.log_path:
        parts.extend(["--log-path", path])
    if args.aggregation_command:
        parts.extend(["--aggregation-command", args.aggregation_command])
    for command in args.validator_command:
        parts.extend(["--validator-command", command])
    if args.mapper_final_command:
        parts.extend(["--mapper-final-command", args.mapper_final_command])
    if args.mapper_final_required:
        parts.append("--mapper-final-required")
    if args.validator_required:
        parts.append("--validator-required")
    if args.commit:
        parts.append("--commit")
    parts.extend(["--commit-message", args.commit_message])
    for path in args.tracked_file:
        parts.extend(["--tracked-file", path])
    return " ".join(shlex.quote(part) for part in parts)


def launch_accounting_continuation(
    args: argparse.Namespace,
    repo_root: Path,
    result_dir: Path,
    state: dict[str, Any],
    lock_path: Path,
) -> None:
    backend = args.accounting_exhaustion_backend
    receipt_path = args.accounting_continuation_receipt_path or result_dir / "accounting_continuation_receipt.json"
    if backend == "tmux_watcher":
        session_name = args.accounting_retry_session_name or f"care_{args.task_key}_accounting_retry"
        finalizer_command = build_finalizer_retry_command(args, retry_seconds=DEFAULT_ACCOUNTING_RETRY_SECONDS)
        command = [
            sys.executable,
            "scripts/ops/start_care_tmux_watcher.py",
            "--task-key",
            args.task_key,
            "--result-dir",
            str(result_dir),
            "--session-name",
            session_name,
            "--lock-path",
            str(lock_path),
            "--log-path",
            str(result_dir / "accounting_retry_watcher.log"),
            "--receipt-path",
            str(receipt_path),
            "--finalizer-command",
            finalizer_command,
            "--poll-interval",
            str(args.accounting_continuation_poll_interval),
        ]
        cp = run(command, repo_root)
        state["retry_backend"] = "tmux_watcher"
        state["next_retry_job_id_or_tmux_session"] = session_name if cp.returncode == 0 else None
        state["accounting_continuation_receipt_path"] = str(receipt_path)
        state["accounting_continuation_launch"] = command_record(" ".join(shlex.quote(part) for part in command), cp)
        return
    if backend == "resubmit_finalizer":
        submit_script = repo_root / "scripts" / "ops" / "submit_care_dependency_finalizer.py"
        command = [
            sys.executable,
            str(submit_script),
            "--task-key",
            args.task_key,
            "--result-dir",
            str(result_dir),
            "--stage",
            args.stage,
            "--awaiting-sacct-retry-seconds",
            str(DEFAULT_ACCOUNTING_RETRY_SECONDS),
            "--awaiting-sacct-retry-interval",
            str(args.awaiting_sacct_retry_interval),
            "--accounting-exhaustion-backend",
            backend,
            "--receipt-path",
            str(receipt_path),
        ]
        for job_id in args.required_job_id:
            command.extend(["--required-job-id", job_id])
        for path in args.runtime_output_path:
            command.extend(["--runtime-output-path", path])
        for path in args.log_path:
            command.extend(["--log-path", path])
        if args.aggregation_command:
            command.extend(["--aggregation-command", args.aggregation_command])
        for validator in args.validator_command:
            command.extend(["--validator-command", validator])
        if args.mapper_final_command:
            command.extend(["--mapper-final-command", args.mapper_final_command])
        if args.commit:
            command.append("--commit")
        command.extend(["--commit-message", args.commit_message])
        for path in args.tracked_file:
            command.extend(["--tracked-file", path])
        cp = run(command, repo_root)
        state["retry_backend"] = "resubmit_finalizer"
        stdout_tokens = cp.stdout.replace(";", " ").split()
        job_id = next((token for token in stdout_tokens if token.isdigit()), None)
        state["next_retry_job_id_or_tmux_session"] = job_id
        state["accounting_continuation_receipt_path"] = str(receipt_path)
        state["accounting_continuation_launch"] = command_record(" ".join(shlex.quote(part) for part in command), cp)
        return
    raise ValueError(f"unsupported accounting exhaustion backend: {backend}")


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


def read_text_tail(path: Path, limit: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError:
        return ""


def classify_runtime_failure(jobs: dict[str, dict[str, str]], log_paths: list[str], repo_root: Path, override: str = "") -> tuple[str, bool, str]:
    if override:
        return override, override in RETRYABLE_FAILURE_CLASSES, "explicit finalizer failure class override"
    states = {job.get("state", "UNKNOWN").upper() for job in jobs.values()}
    logs = "\n".join(read_text_tail(repo_root / path) for path in log_paths)
    if "ModuleNotFoundError" in logs or "No module named" in logs:
        return "STARTUP_ENVIRONMENT_FAILURE", True, "missing import/module in job log"
    if "command not found" in logs or "No such file or directory" in logs:
        return "STARTUP_WRAPPER_FAILURE", True, "wrapper or command startup failure in job log"
    if "PREEMPTED" in states:
        return "PREEMPTED_RETRYABLE", True, "Slurm preemption is retryable with matching fingerprints"
    if states & {"NODE_FAIL", "BOOT_FAIL"}:
        return "NODE_FAILURE_RETRYABLE", True, "node or boot failure is retryable with matching fingerprints"
    if "OUT_OF_MEMORY" in states:
        return "OUT_OF_MEMORY_NEEDS_REVISION", False, "OOM requires implementation/budget revision"
    if "FAILED" in states:
        return "UNKNOWN_RUNTIME_FAILURE", False, "failed job without recognized retryable startup signature"
    return "MODEL_OR_DATA_FAILURE_NEEDS_REVISION", False, "terminal runtime failure requires task-local revision"


def wait_for_accounting(
    job_ids: list[str],
    repo_root: Path,
    fixture: Path | None,
    retry_seconds: int,
    retry_interval: int,
) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]], bool]:
    attempts: list[dict[str, Any]] = []
    deadline = time.time() + max(0, retry_seconds)
    poll = 0
    while True:
        jobs = load_job_states(job_ids, repo_root, fixture, fixture_poll=poll)
        states = {job.get("state", "UNKNOWN") for job in jobs.values()}
        attempts.append({"poll": poll, "states": sorted(states)})
        if "AWAITING_SACCT" not in states:
            return jobs, attempts, False
        if retry_seconds <= 0 or time.time() >= deadline:
            return jobs, attempts, True
        time.sleep(max(1, retry_interval))
        poll += 1


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
    parser.add_argument("--stage", choices=("accounting", "commit", "all"), default="all")
    parser.add_argument("--lock-ttl-seconds", type=int, default=3600)
    parser.add_argument("--recover-stale-lock", action="store_true")
    parser.add_argument("--awaiting-sacct-retry-seconds", type=int, default=DEFAULT_ACCOUNTING_RETRY_SECONDS)
    parser.add_argument("--awaiting-sacct-retry-interval", type=int, default=30)
    parser.add_argument("--accounting-exhaustion-backend", choices=sorted(ACCOUNTING_EXHAUSTION_BACKENDS), default="tmux_watcher")
    parser.add_argument("--accounting-continuation-poll-interval", type=int, default=300)
    parser.add_argument("--accounting-continuation-receipt-path", type=Path)
    parser.add_argument("--accounting-retry-session-name", default="")
    parser.add_argument("--mapper-final-required", action="store_true")
    parser.add_argument("--validator-required", action="store_true")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--commit-message", default="Finalize CARE milestone packet")
    parser.add_argument("--tracked-file", action="append", default=[])
    parser.add_argument("--failure-class", default="")
    parser.add_argument("--attempt-number", type=int, default=1)
    parser.add_argument("--supersedes-job-id", action="append", default=[])
    parser.add_argument("--replacement-job-id", action="append", default=[])
    parser.add_argument("--training-credit-policy", default="zero_for_failed_startup")
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
        "git_commit_decision": "COMMIT_LOCAL_PACKET" if args.commit else "SKIP_COMMIT",
        "precommit_head": git_head_before,
        "tracked_paths": args.tracked_file,
        "manifest_sha256": sha256_path(result_dir / "MANIFEST.md"),
        "final_state": "INITIALIZING",
        "records": [],
        "stage": args.stage,
        "awaiting_sacct_retry_seconds": args.awaiting_sacct_retry_seconds,
        "awaiting_sacct_retry_interval": args.awaiting_sacct_retry_interval,
        "awaiting_sacct_attempts": [],
        "retryable": False,
        "retry_count": 0,
        "retry_backend": args.accounting_exhaustion_backend,
        "next_retry_job_id_or_tmux_session": None,
        "accounting_wait_seconds": 0,
        "accounting_continuation_receipt_path": None,
        "accounting_continuation_launch": None,
        "failure_class": None,
        "retry_reason": None,
        "suggested_next_state": None,
        "attempt_number": args.attempt_number,
        "supersedes_job_ids": args.supersedes_job_id,
        "replacement_job_ids": args.replacement_job_id,
        "job_attempt_lineage": [],
        "training_credit_policy": args.training_credit_policy,
        "lock_released": False,
    }

    try:
        lock_fd = acquire_lock(lock_path, args.task_key, args.lock_ttl_seconds, args.recover_stale_lock)
    except FileExistsError as exc:
        state["final_state"] = "NEEDS_MONITOR"
        state["lock_error"] = f"lock already exists; {exc}"
        write_state(result_dir, state)
        return 2

    try:
        jobs, attempts, exhausted = wait_for_accounting(
            args.required_job_id,
            repo_root,
            args.sacct_fixture,
            args.awaiting_sacct_retry_seconds,
            args.awaiting_sacct_retry_interval,
        )
        state["awaiting_sacct_attempts"] = attempts
        state["retry_count"] = max(0, len(attempts) - 1)
        state["accounting_wait_seconds"] = min(
            args.awaiting_sacct_retry_seconds,
            max(0, len(attempts) - 1) * max(1, args.awaiting_sacct_retry_interval),
        )
        state["job_states"] = {jid: job.get("state") for jid, job in jobs.items()}
        state["exit_codes"] = {jid: job.get("exit_code", job.get("ExitCode", "UNKNOWN")) for jid, job in jobs.items()}
        state["elapsed"] = {jid: job.get("elapsed", "UNKNOWN") for jid, job in jobs.items()}
        state["nodes"] = {jid: job.get("node", "UNKNOWN") for jid, job in jobs.items()}

        job_state = final_state_from_jobs(jobs, args.pending_check_count)
        if exhausted and "AWAITING_SACCT" in set(state["job_states"].values()):
            state["final_state"] = "AWAITING_SACCT_RETRY_EXHAUSTED"
            state["retryable"] = True
            launch_accounting_continuation(args, repo_root, result_dir, state, lock_path)
            if not state.get("next_retry_job_id_or_tmux_session"):
                state["final_state"] = "NEEDS_MONITOR"
                state["continuation_error"] = "accounting retry continuation did not return a session or job id"
            write_state(result_dir, state)
            return 0
        if job_state == "NEEDS_MONITOR":
            state["final_state"] = "NEEDS_MONITOR"
            state["retryable"] = True
            write_state(result_dir, state)
            return 0
        if job_state == "RUNTIME_FAILURE":
            failure_class, retryable, retry_reason = classify_runtime_failure(jobs, args.log_path, repo_root, args.failure_class)
            state["failure_class"] = failure_class
            state["retryable"] = retryable
            state["retry_reason"] = retry_reason
            state["job_attempt_lineage"] = [
                {
                    "attempt_number": args.attempt_number,
                    "job_id": jid,
                    "state": job.get("state"),
                    "exit_code": job.get("exit_code", job.get("ExitCode", "UNKNOWN")),
                    "training_credit": "zero" if failure_class.startswith("STARTUP_") else "verified_completed_steps_only",
                }
                for jid, job in jobs.items()
            ]
            if retryable:
                state["final_state"] = "OPERATIONAL_RETRY_REQUIRED"
                state["suggested_next_state"] = "HAND_BACK_TO_CONTROLLER_FOR_SAME_SCOPE_RETRY"
                write_state(result_dir, state)
                return 0
            state["final_state"] = "RUNTIME_FAILURE"
            state["suggested_next_state"] = "NEEDS_REVISION" if failure_class.endswith("NEEDS_REVISION") else "NEEDS_EVIDENCE"
            write_state(result_dir, state)
            return 1

        missing_outputs = [path for path in args.runtime_output_path if not (repo_root / path).exists()]
        if missing_outputs:
            state["final_state"] = "NEEDS_EVIDENCE"
            state["missing_runtime_outputs"] = missing_outputs
            write_state(result_dir, state)
            return 1

        if args.stage in {"accounting", "all"} and args.aggregation_command:
            cp = run(args.aggregation_command, repo_root, shell=True)
            state["aggregation_exit_code"] = cp.returncode
            state["records"].append(command_record(args.aggregation_command, cp))
            if cp.returncode != 0:
                state["final_state"] = "NEEDS_EVIDENCE"
                write_state(result_dir, state)
                return 1

        if args.stage == "accounting":
            state["final_state"] = "READY_FOR_MAPPER_FINAL"
            write_state(result_dir, state)
            return 0

        if args.mapper_final_required and not args.mapper_final_command and state.get("mapper_final_status") != "complete":
            state["final_state"] = "NEEDS_MAPPER_FINAL"
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

        if args.validator_required and not args.validator_command:
            state["final_state"] = "NEEDS_VALIDATOR"
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

        diff_check = run(["git", "diff", "--check"], repo_root)
        state["records"].append(command_record("git diff --check", diff_check))
        if diff_check.returncode != 0:
            state["final_state"] = "NEEDS_REVISION"
            write_state(result_dir, state)
            return 1

        if args.commit:
            commit_after, commit_records = maybe_commit(repo_root, args.tracked_file, args.commit_message)
            state["records"].extend(commit_records)
            state["local_packet_commit"] = commit_after
            if not commit_after:
                state["final_state"] = "NEEDS_EVIDENCE"
                write_state(result_dir, state)
                return 1

        state["final_state"] = "PACKET_COMMITTED_FOR_REVIEW" if args.commit else "READY_FOR_LOCAL_PACKET_COMMIT"
        write_state(result_dir, state)
        return 0
    finally:
        os.close(lock_fd)
        try:
            lock_path.unlink()
            state["lock_released"] = True
            write_state(result_dir, state)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
