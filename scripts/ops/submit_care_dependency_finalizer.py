#!/usr/bin/env python3
"""Submit a CARE accounting/finalizer job with Slurm afterany dependencies.

This helper is finalizer-only. It must not be used as a training-chain
submission helper; use submit_care_training_chain.py for training stages that
require afterok dependencies.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
from datetime import datetime, timezone

from care_milestone_finalizer import DEFAULT_ACCOUNTING_RETRY_SECONDS


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def parse_job_id(stdout: str) -> str | None:
    for token in stdout.replace(";", " ").split():
        if token.isdigit():
            return token
    return None


def quote_items(items: list[str]) -> list[str]:
    return [shlex.quote(item) for item in items]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-key", required=True)
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--required-job-id", action="append", required=True)
    parser.add_argument("--effective-training-job-id", action="append", default=[])
    parser.add_argument("--failed-attempt-job-id", action="append", default=[])
    parser.add_argument("--runtime-output-path", action="append", default=[])
    parser.add_argument("--log-path", action="append", default=[])
    parser.add_argument("--aggregation-command", default="")
    parser.add_argument("--validator-command", action="append", default=[])
    parser.add_argument("--mapper-final-command", default="")
    parser.add_argument("--stage", choices=("accounting", "commit", "all"), default="accounting")
    parser.add_argument("--awaiting-sacct-retry-seconds", type=int, default=DEFAULT_ACCOUNTING_RETRY_SECONDS)
    parser.add_argument("--awaiting-sacct-retry-interval", type=int, default=30)
    parser.add_argument("--accounting-exhaustion-backend", choices=("tmux_watcher", "resubmit_finalizer"), default="tmux_watcher")
    parser.add_argument("--recover-stale-lock", action="store_true")
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--receipt-path", type=Path)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--commit-message", default="Finalize CARE milestone packet")
    parser.add_argument("--tracked-file", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    result_dir = args.result_dir
    result_dir.mkdir(parents=True, exist_ok=True)
    lock_path = args.lock_path or result_dir / ".finalizer.lock"
    receipt_path = args.receipt_path or result_dir / "dependency_finalizer_submission.json"
    log_path = result_dir / "care_milestone_finalizer_%j.log"
    dependency = "afterany:" + ":".join(args.required_job_id)

    script = repo_root / "jobs" / "src" / "care_milestone_finalizer.sh"
    finalizer_args = [
        "--task-key",
        args.task_key,
        "--result-dir",
        str(result_dir),
        "--lock-path",
        str(lock_path),
        "--stage",
        args.stage,
        "--awaiting-sacct-retry-seconds",
        str(args.awaiting_sacct_retry_seconds),
        "--awaiting-sacct-retry-interval",
        str(args.awaiting_sacct_retry_interval),
        "--accounting-exhaustion-backend",
        args.accounting_exhaustion_backend,
    ]
    if args.recover_stale_lock:
        finalizer_args.append("--recover-stale-lock")
    for job_id in args.required_job_id:
        finalizer_args.extend(["--required-job-id", job_id])
    for path in args.runtime_output_path:
        finalizer_args.extend(["--runtime-output-path", path])
    for path in args.log_path:
        finalizer_args.extend(["--log-path", path])
    if args.aggregation_command:
        finalizer_args.extend(["--aggregation-command", args.aggregation_command])
    for command in args.validator_command:
        finalizer_args.extend(["--validator-command", command])
    if args.mapper_final_command:
        finalizer_args.extend(["--mapper-final-command", args.mapper_final_command])
    if args.commit:
        finalizer_args.append("--commit")
    finalizer_args.extend(["--commit-message", args.commit_message])
    for path in args.tracked_file:
        finalizer_args.extend(["--tracked-file", path])

    command = [
        "sbatch",
        f"--dependency={dependency}",
        "--parsable",
        "--output",
        str(log_path),
        str(script),
        *finalizer_args,
    ]

    receipt = {
        "task_key": args.task_key,
        "finalizer_only": True,
        "result_dir": str(result_dir),
        "required_job_ids": args.required_job_id,
        "all_attempt_job_ids": args.required_job_id,
        "effective_training_job_ids": args.effective_training_job_id,
        "failed_attempt_job_ids": args.failed_attempt_job_id,
        "dependency": dependency,
        "dependency_type": "afterany",
        "command": " ".join(quote_items(command)),
        "log_path": str(log_path),
        "lock_path": str(lock_path),
        "accounting_exhaustion_backend": args.accounting_exhaustion_backend,
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
        "finalizer_job_id": None,
        "submit_exit_code": None,
        "submit_stdout": "",
        "submit_stderr": "",
        "dry_run": args.dry_run,
    }

    if args.dry_run:
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(receipt["command"])
        return 0

    cp = run(command, repo_root)
    receipt["submit_exit_code"] = cp.returncode
    receipt["submit_stdout"] = cp.stdout
    receipt["submit_stderr"] = cp.stderr
    receipt["finalizer_job_id"] = parse_job_id(cp.stdout)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if cp.returncode != 0 or not receipt["finalizer_job_id"]:
        print(cp.stderr or cp.stdout, file=sys.stderr)
        return 1
    print(receipt["finalizer_job_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
