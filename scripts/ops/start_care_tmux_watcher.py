#!/usr/bin/env python3
"""Start or run a state-aware CARE finalizer watcher."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any


SUCCESS_FINALIZER_STATES = {
    "READY_FOR_MAPPER_FINAL",
    "PACKET_COMMITTED_FOR_REVIEW",
    "READY_FOR_LOCAL_PACKET_COMMIT",
}
CONTINUE_FINALIZER_STATES = {
    "NEEDS_MONITOR",
    "AWAITING_SACCT_RETRY_EXHAUSTED",
    "INITIALIZING",
}
FAIL_FINALIZER_STATES = {
    "RUNTIME_FAILURE",
    "NEEDS_EVIDENCE",
    "NEEDS_REVISION",
    "NEEDS_MAPPER_FINAL",
    "NEEDS_VALIDATOR",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str] | str, cwd: Path, shell: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, shell=shell, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def read_state(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"final_state": "INITIALIZING", "job_states": {}}


def append_ledger(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.is_file()
    fields = ["timestamp", "iteration", "finalizer_exit_code", "finalizer_state", "job_states", "next_action"]
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fields})


def next_action_for_state(final_state: str) -> tuple[str, int | None]:
    if final_state in SUCCESS_FINALIZER_STATES:
        return "STOP_SUCCESS", 0
    if final_state in CONTINUE_FINALIZER_STATES:
        return "CONTINUE_POLLING", None
    if final_state in FAIL_FINALIZER_STATES:
        return "STOP_FAILURE", 1
    return "STOP_FAILURE_UNKNOWN_STATE", 1


def run_watcher_loop(
    *,
    repo_root: Path,
    result_dir: Path,
    finalizer_command: str,
    ledger_path: Path,
    receipt_path: Path,
    poll_interval: int,
    max_iterations: int,
    receipt: dict[str, Any],
) -> int:
    result_dir.mkdir(parents=True, exist_ok=True)
    state_path = result_dir / "finalizer_state.json"
    iteration = 0
    while True:
        iteration += 1
        cp = run(finalizer_command, repo_root, shell=True)
        state = read_state(state_path)
        final_state = str(state.get("final_state", "INITIALIZING"))
        action, exit_code = next_action_for_state(final_state)
        append_ledger(
            ledger_path,
            {
                "timestamp": utc_now(),
                "iteration": iteration,
                "finalizer_exit_code": cp.returncode,
                "finalizer_state": final_state,
                "job_states": json.dumps(state.get("job_states", {}), sort_keys=True),
                "next_action": action,
            },
        )
        receipt.update(
            {
                "watcher_final_status": action,
                "watcher_stop_reason": final_state,
                "finalizer_exit_code": cp.returncode,
                "finalizer_stdout_tail": cp.stdout[-2000:],
                "finalizer_stderr_tail": cp.stderr[-2000:],
                "iterations": iteration,
                "finished_at": utc_now() if exit_code is not None else None,
            }
        )
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if exit_code is not None:
            return exit_code
        if max_iterations and iteration >= max_iterations:
            receipt.update(
                {
                    "watcher_final_status": "STOP_FAILURE_MAX_ITERATIONS",
                    "watcher_stop_reason": f"max_iterations={max_iterations}",
                    "finished_at": utc_now(),
                }
            )
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return 1
        time.sleep(max(1, poll_interval))


def build_foreground_command(args: argparse.Namespace, repo_root: Path, receipt_path: Path, ledger_path: Path) -> str:
    parts = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--task-key",
        args.task_key,
        "--result-dir",
        str(args.result_dir),
        "--poll-interval",
        str(args.poll_interval),
        "--finalizer-command",
        args.finalizer_command,
        "--receipt-path",
        str(receipt_path),
        "--ledger-path",
        str(ledger_path),
        "--foreground",
    ]
    if args.max_iterations:
        parts.extend(["--max-iterations", str(args.max_iterations)])
    for job_id in args.required_job_id:
        parts.extend(["--required-job-id", job_id])
    if args.lock_path:
        parts.extend(["--lock-path", str(args.lock_path)])
    if args.log_path:
        parts.extend(["--log-path", str(args.log_path)])
    return "cd " + shlex.quote(str(repo_root)) + "; " + " ".join(shlex.quote(part) for part in parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-key", required=True)
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--required-job-id", action="append", default=[])
    parser.add_argument("--poll-interval", type=int, default=300)
    parser.add_argument("--max-iterations", type=int, default=0)
    parser.add_argument("--session-name", default="")
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--log-path", type=Path)
    parser.add_argument("--ledger-path", type=Path)
    parser.add_argument("--finalizer-command", required=True)
    parser.add_argument("--receipt-path", type=Path)
    parser.add_argument("--foreground", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    result_dir = args.result_dir
    result_dir.mkdir(parents=True, exist_ok=True)
    session = args.session_name or f"care_{args.task_key}_watcher"
    lock_path = args.lock_path or result_dir / ".tmux_watcher.lock"
    log_path = args.log_path or result_dir / "tmux_watcher.log"
    receipt_path = args.receipt_path or result_dir / "tmux_watcher_receipt.json"
    ledger_path = args.ledger_path or result_dir / "tmux_watcher_iteration_ledger.csv"
    receipt: dict[str, Any] = {
        "task_key": args.task_key,
        "session_name": session,
        "pid": None,
        "command": "",
        "watcher_shell_command": "",
        "finalizer_command": args.finalizer_command,
        "ledger_path": str(ledger_path),
        "log_path": str(log_path),
        "lock_path": str(lock_path),
        "result_dir": str(result_dir),
        "required_job_ids": args.required_job_id,
        "poll_interval": args.poll_interval,
        "max_iterations": args.max_iterations,
        "started_at": utc_now(),
        "dry_run": args.dry_run,
        "foreground": args.foreground,
    }
    if args.foreground:
        return run_watcher_loop(
            repo_root=repo_root,
            result_dir=result_dir,
            finalizer_command=args.finalizer_command,
            ledger_path=ledger_path,
            receipt_path=receipt_path,
            poll_interval=args.poll_interval,
            max_iterations=args.max_iterations,
            receipt=receipt,
        )
    shell_command = build_foreground_command(args, repo_root, receipt_path, ledger_path)
    tmux_cmd = ["tmux", "new-session", "-d", "-s", session, shell_command]
    receipt["command"] = " ".join(shlex.quote(part) for part in tmux_cmd)
    receipt["watcher_shell_command"] = shell_command
    if args.dry_run:
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(receipt["command"])
        return 0
    cp = run(tmux_cmd, repo_root)
    if cp.returncode != 0:
        print(cp.stderr or cp.stdout, file=sys.stderr)
        receipt["start_exit_code"] = cp.returncode
        receipt["stderr"] = cp.stderr
        receipt["watcher_final_status"] = "START_FAILED"
        receipt["watcher_stop_reason"] = cp.stderr or cp.stdout
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 1
    pid = run(["tmux", "display-message", "-p", "-t", session, "#{pane_pid}"], repo_root)
    receipt["pid"] = pid.stdout.strip() if pid.returncode == 0 else None
    receipt["start_exit_code"] = 0
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
