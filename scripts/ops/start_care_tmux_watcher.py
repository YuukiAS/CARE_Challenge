#!/usr/bin/env python3
"""Start a namespace-local tmux watcher for CARE finalizer fallback."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import shlex
import subprocess
import sys


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-key", required=True)
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--required-job-id", action="append", default=[])
    parser.add_argument("--poll-interval", type=int, default=300)
    parser.add_argument("--session-name", default="")
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--log-path", type=Path)
    parser.add_argument("--finalizer-command", required=True)
    parser.add_argument("--receipt-path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    result_dir = args.result_dir
    result_dir.mkdir(parents=True, exist_ok=True)
    session = args.session_name or f"care_{args.task_key}_watcher"
    lock_path = args.lock_path or result_dir / ".tmux_watcher.lock"
    log_path = args.log_path or result_dir / "tmux_watcher.log"
    receipt_path = args.receipt_path or result_dir / "tmux_watcher_receipt.json"
    shell_command = (
        f"cd {shlex.quote(str(repo_root))}; "
        f"while true; do {args.finalizer_command}; code=$?; "
        f"if [ $code -eq 0 ]; then break; fi; "
        f"sleep {int(args.poll_interval)}; done"
    )
    tmux_cmd = ["tmux", "new-session", "-d", "-s", session, shell_command]
    receipt = {
        "task_key": args.task_key,
        "session_name": session,
        "pid": None,
        "command": " ".join(shlex.quote(part) for part in tmux_cmd),
        "watcher_shell_command": shell_command,
        "log_path": str(log_path),
        "lock_path": str(lock_path),
        "result_dir": str(result_dir),
        "required_job_ids": args.required_job_id,
        "poll_interval": args.poll_interval,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(receipt["command"])
        return 0
    cp = run(tmux_cmd, repo_root)
    if cp.returncode != 0:
        print(cp.stderr or cp.stdout, file=sys.stderr)
        receipt["start_exit_code"] = cp.returncode
        receipt["stderr"] = cp.stderr
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
