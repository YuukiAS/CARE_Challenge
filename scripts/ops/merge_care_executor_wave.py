#!/usr/bin/env python3
"""Merge completed CARE executor branches for one wave in merge_order."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from typing import Any

from validate_executor_plan import load_yaml, validate_plan


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record(cmd: list[str], cp: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "command": " ".join(cmd),
        "exit_code": cp.returncode,
        "stdout_tail": cp.stdout[-2000:],
        "stderr_tail": cp.stderr[-2000:],
    }


def wave_entries(plan: dict[str, Any], wave: int) -> list[dict[str, Any]]:
    return sorted(
        [item for item in plan.get("executors", []) if int(item.get("wave", 1)) == wave],
        key=lambda item: int(item.get("merge_order", 0)),
    )


def result_packet_exists(repo_root: Path, entry: dict[str, Any]) -> bool:
    result_dir = repo_root / str(entry.get("result_dir"))
    return (result_dir / "completion_check.md").is_file() or (result_dir / "result.md").is_file()


def branch_clean(repo_root: Path, entry: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    worktree = Path(str(entry.get("worktree_path", "")))
    cwd = worktree if worktree.is_dir() else repo_root
    cp = run(["git", "status", "--short"], cwd)
    return cp.returncode == 0 and not cp.stdout.strip(), record(["git", "status", "--short"], cp)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--wave", required=True, type=int)
    parser.add_argument("--receipt-path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    plan = load_yaml(args.plan)
    errors = validate_plan(plan)
    entries = wave_entries(plan, args.wave)
    if not entries:
        errors.append(f"wave {args.wave}: no executors")
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    receipt_path = args.receipt_path or repo_root / "results" / "executor_wave_receipts" / f"wave_{args.wave}_merge_receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "plan_path": str(args.plan),
        "wave": args.wave,
        "created_at": utc_now(),
        "merge_state": "INITIALIZING",
        "records": [],
        "merged_executors": [],
        "dry_run": args.dry_run,
    }

    for entry in entries:
        eid = str(entry.get("id"))
        branch = str(entry.get("branch_name"))
        blocking = bool(entry.get("blocking", True))
        if blocking and not result_packet_exists(repo_root, entry):
            receipt["merge_state"] = "NEEDS_EVIDENCE"
            receipt["failure_reason"] = f"{eid}: required result packet missing"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(receipt["failure_reason"], file=sys.stderr)
            return 1
        clean, clean_record = branch_clean(repo_root, entry)
        receipt["records"].append(clean_record)
        if not clean:
            receipt["merge_state"] = "NEEDS_REVISION_EXECUTOR_BRANCH_DIRTY"
            receipt["failure_reason"] = f"{eid}: executor branch is not clean"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(receipt["failure_reason"], file=sys.stderr)
            return 1
        if args.dry_run:
            receipt["merged_executors"].append(eid)
            continue
        cp = run(["git", "merge", "--no-ff", "--no-commit", branch], repo_root)
        receipt["records"].append(record(["git", "merge", "--no-ff", "--no-commit", branch], cp))
        if cp.returncode != 0:
            run(["git", "merge", "--abort"], repo_root)
            receipt["merge_state"] = "NEEDS_REVISION_PARALLEL_MERGE_CONFLICT"
            receipt["failure_reason"] = f"{eid}: merge conflict or merge failure"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(receipt["failure_reason"], file=sys.stderr)
            return 1
        cp = run(["git", "commit", "-m", f"Merge executor {eid}"], repo_root)
        receipt["records"].append(record(["git", "commit", "-m", f"Merge executor {eid}"], cp))
        if cp.returncode != 0:
            receipt["merge_state"] = "NEEDS_REVISION_PARALLEL_MERGE_CONFLICT"
            receipt["failure_reason"] = f"{eid}: merge commit failed"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(cp.stderr or cp.stdout, file=sys.stderr)
            return 1
        receipt["merged_executors"].append(eid)
    receipt["merge_state"] = "MERGED" if not args.dry_run else "DRY_RUN_READY"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(receipt["merge_state"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
