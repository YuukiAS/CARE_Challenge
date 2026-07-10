#!/usr/bin/env python3
"""Prepare isolated worktrees and receipts for one CARE executor wave."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from typing import Any

from validate_executor_plan import load_yaml, validate_plan, as_list


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_record(cmd: list[str], cp: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "command": " ".join(cmd),
        "exit_code": cp.returncode,
        "stdout_tail": cp.stdout[-2000:],
        "stderr_tail": cp.stderr[-2000:],
    }


def selected_wave(plan: dict[str, Any], wave: int) -> list[dict[str, Any]]:
    return [item for item in plan.get("executors", []) if int(item.get("wave", 1)) == wave]


def dependency_errors(plan: dict[str, Any], wave: int, repo_root: Path) -> list[str]:
    executors = plan.get("executors", [])
    waves = {str(item.get("id")): int(item.get("wave", 1)) for item in executors}
    errors: list[str] = []
    for item in selected_wave(plan, wave):
        eid = str(item.get("id"))
        for dep in as_list(item.get("depends_on")):
            if waves.get(dep, wave) >= wave:
                errors.append(f"{eid}: dependency {dep} is not completed in an earlier wave")
                continue
            dep_wave = waves.get(dep)
            receipt_path = repo_root / "results" / "executor_wave_receipts" / f"wave_{dep_wave}_merge_receipt.json"
            try:
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                errors.append(f"{eid}: dependency {dep} has no successful merge receipt: {receipt_path}")
                continue
            if receipt.get("merge_state") != "MERGED" or dep not in receipt.get("merged_executors", []):
                errors.append(f"{eid}: dependency {dep} is not recorded as merged in {receipt_path}")
    return errors


def prepare_paths(repo_root: Path, entry: dict[str, Any]) -> None:
    for field in ("result_dir", "runtime_output_root", "lock_path", "log_path", "prompt_path"):
        path = repo_root / str(entry.get(field, ""))
        if field in {"lock_path", "log_path", "prompt_path"}:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--wave", required=True, type=int)
    parser.add_argument("--receipt-path", type=Path)
    parser.add_argument("--allow-subagent-launch", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    plan = load_yaml(args.plan)
    errors = validate_plan(plan)
    errors.extend(dependency_errors(plan, args.wave, repo_root))
    entries = selected_wave(plan, args.wave)
    if not entries:
        errors.append(f"wave {args.wave}: no executors")
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    receipt_path = args.receipt_path or repo_root / "results" / "executor_wave_receipts" / f"wave_{args.wave}_launch_receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "plan_path": str(args.plan),
        "wave": args.wave,
        "created_at": utc_now(),
        "subagent_launch_supported": args.allow_subagent_launch,
        "controller_action": "LAUNCH_EXECUTORS" if args.allow_subagent_launch else "NEEDS_SUBAGENT_LAUNCH",
        "executors": [],
        "records": [],
        "dry_run": args.dry_run,
    }
    for entry in entries:
        prepare_paths(repo_root, entry)
        branch = str(entry.get("branch_name"))
        worktree = Path(str(entry.get("worktree_path")))
        executor_receipt = {
            "id": entry.get("id"),
            "lane": entry.get("lane"),
            "prompt_path": entry.get("prompt_path"),
            "branch_name": branch,
            "worktree_path": str(worktree),
            "result_dir": entry.get("result_dir"),
            "runtime_output_root": entry.get("runtime_output_root"),
            "log_path": entry.get("log_path"),
            "lock_path": entry.get("lock_path"),
            "slurm_job_namespace": entry.get("slurm_job_namespace"),
            "merge_order": entry.get("merge_order"),
        }
        receipt["executors"].append(executor_receipt)
        if not args.dry_run:
            cp = run(["git", "worktree", "add", "-B", branch, str(worktree), "HEAD"], repo_root)
            receipt["records"].append(command_record(["git", "worktree", "add", "-B", branch, str(worktree), "HEAD"], cp))
            if cp.returncode != 0:
                receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                print(cp.stderr or cp.stdout, file=sys.stderr)
                return 1
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(receipt["controller_action"])
    return 0 if args.allow_subagent_launch or args.dry_run else 2


if __name__ == "__main__":
    raise SystemExit(main())
