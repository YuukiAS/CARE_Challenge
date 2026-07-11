#!/usr/bin/env python3
"""Merge completed CARE executor branches for one wave in merge_order."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from typing import Any

from validate_executor_plan import load_yaml, validate_plan


DEFAULT_READY_TOKENS = {"READY_FOR_MERGE", "READY_FOR_CONTROLLER_MERGE", "PACKET_COMMITTED_FOR_CONTROLLER"}
FORBIDDEN_COMPLETION_TOKENS = {
    "NEEDS_MONITOR",
    "NEEDS_EVIDENCE",
    "NEEDS_REVISION",
    "BLOCKED",
    "RUNNING",
    "PENDING",
    "AWAITING_SACCT",
}


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_wave_dir(repo_root: Path, plan: dict[str, Any], wave: int) -> Path:
    task_key = str(plan.get("task_key") or "unknown_task")
    return repo_root / "results" / task_key / "executor_waves" / f"wave_{wave}"


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


def branch_exists(repo_root: Path, branch: str) -> bool:
    cp = run(["git", "rev-parse", "--verify", branch], repo_root)
    return cp.returncode == 0


def branch_head(repo_root: Path, branch: str) -> str:
    cp = run(["git", "rev-parse", branch], repo_root)
    return cp.stdout.strip() if cp.returncode == 0 else ""


def merge_base(repo_root: Path, branch: str) -> str:
    cp = run(["git", "merge-base", "HEAD", branch], repo_root)
    return cp.stdout.strip() if cp.returncode == 0 else ""


def read_completion_from_worktree_or_branch(repo_root: Path, entry: dict[str, Any]) -> tuple[str | None, str, dict[str, Any]]:
    completion_file = str(entry.get("required_completion_file") or (str(entry.get("result_dir")) + "/completion_check.md"))
    worktree = Path(str(entry.get("worktree_path", "")))
    branch = str(entry.get("branch_name"))
    local_path = worktree / completion_file
    if local_path.is_file():
        return local_path.read_text(encoding="utf-8"), str(local_path), {"method": "worktree_file"}
    cp = run(["git", "show", f"{branch}:{completion_file}"], repo_root)
    rec = record(["git", "show", f"{branch}:{completion_file}"], cp)
    if cp.returncode == 0:
        return cp.stdout, f"{branch}:{completion_file}", rec | {"method": "git_show"}
    return None, completion_file, rec | {"method": "missing"}


def completion_token(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        for key in ("completion_token", "completion_state", "status"):
            if data.get(key):
                return str(data[key]).strip()
    for raw in text.splitlines():
        token = raw.strip()
        if token.startswith("completion_token:") or token.startswith("completion_state:") or token.startswith("status:"):
            return token.split(":", 1)[1].strip()
        if token:
            return token.split()[0].strip()
    return ""


def completion_structured_state(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        for key in ("completion_state", "status", "monitor_state", "slurm_state"):
            if data.get(key):
                return str(data[key]).strip()
    for raw in text.splitlines():
        token = raw.strip()
        if token.startswith(("completion_state:", "status:", "monitor_state:", "slurm_state:")):
            return token.split(":", 1)[1].strip()
        if token:
            return token.split()[0].strip()
    return ""


def tracked_in_branch(repo_root: Path, branch: str, path: str) -> bool:
    cp = run(["git", "ls-tree", "-r", "--name-only", branch, "--", path], repo_root)
    return cp.returncode == 0 and path in set(cp.stdout.splitlines())


def branch_clean(repo_root: Path, entry: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    worktree = Path(str(entry.get("worktree_path", "")))
    cwd = worktree if worktree.is_dir() else repo_root
    cp = run(["git", "status", "--short"], cwd)
    return cp.returncode == 0 and not cp.stdout.strip(), record(["git", "status", "--short"], cp)


def validate_executor_ready(repo_root: Path, entry: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    eid = str(entry.get("id"))
    branch = str(entry.get("branch_name"))
    completion_file = str(entry.get("required_completion_file") or "")
    required_token = str(entry.get("required_completion_token") or "").strip()
    allowed = {required_token} if required_token else DEFAULT_READY_TOKENS
    details: dict[str, Any] = {
        "executor_id": eid,
        "branch_name": branch,
        "required_completion_file": completion_file,
        "required_completion_token": required_token,
        "records": [],
    }
    if not branch_exists(repo_root, branch):
        return False, f"{eid}: executor branch does not exist", details
    source_head = branch_head(repo_root, branch)
    base = merge_base(repo_root, branch)
    details["source_branch_head"] = source_head
    details["merge_base"] = base
    if source_head and base and source_head == base:
        return False, f"{eid}: branch contains no executor commit beyond baseline", details
    clean, clean_record = branch_clean(repo_root, entry)
    details["records"].append(clean_record)
    if not clean:
        return False, f"{eid}: executor branch is not clean", details
    text, source, rec = read_completion_from_worktree_or_branch(repo_root, entry)
    details["records"].append(rec)
    details["completion_source"] = source
    if text is None:
        return False, f"{eid}: required completion file missing in worktree/branch", details
    token = completion_token(text)
    details["completion_token"] = token
    if token in FORBIDDEN_COMPLETION_TOKENS or any(token.startswith(prefix) for prefix in FORBIDDEN_COMPLETION_TOKENS):
        return False, f"{eid}: completion token is not mergeable: {token}", details
    if token not in allowed:
        return False, f"{eid}: completion token {token} does not match required token {required_token}", details
    if completion_file and not tracked_in_branch(repo_root, branch, completion_file):
        return False, f"{eid}: required packet is not tracked in branch: {completion_file}", details
    structured_state = completion_structured_state(text).upper()
    details["completion_structured_state"] = structured_state
    if structured_state in FORBIDDEN_COMPLETION_TOKENS or any(structured_state.startswith(prefix) for prefix in FORBIDDEN_COMPLETION_TOKENS):
        return False, f"{eid}: blocking Slurm work is not terminal in completion file", details
    return True, "ready", details


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
    status = run(["git", "status", "--short"], repo_root)
    if status.returncode != 0 or status.stdout.strip():
        errors.append("controller main worktree must be clean before executor wave merge")
    entries = wave_entries(plan, args.wave)
    if not entries:
        errors.append(f"wave {args.wave}: no executors")
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    plan_hash = sha256_file(args.plan)
    receipt_path = args.receipt_path or task_wave_dir(repo_root, plan, args.wave) / "merge_receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "task_key": plan.get("task_key"),
        "plan_path": str(args.plan),
        "plan_sha256": plan_hash,
        "wave": args.wave,
        "created_at": utc_now(),
        "baseline_commit": run(["git", "rev-parse", "HEAD"], repo_root).stdout.strip(),
        "merge_state": "INITIALIZING",
        "records": [],
        "merged_executors": [],
        "dry_run": args.dry_run,
    }

    for entry in entries:
        eid = str(entry.get("id"))
        branch = str(entry.get("branch_name"))
        blocking = bool(entry.get("blocking", True))
        ready, reason, ready_details = validate_executor_ready(repo_root, entry)
        receipt["records"].extend(ready_details.get("records", []))
        if blocking and not ready:
            receipt["merge_state"] = "NEEDS_EVIDENCE"
            receipt["failure_reason"] = reason
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(receipt["failure_reason"], file=sys.stderr)
            return 1
        if not blocking and not ready:
            receipt.setdefault("merge_details", []).append(
                {
                    "executor_id": eid,
                    "merge_state": "SKIPPED_OPTIONAL_NOT_READY",
                    "failure_reason": reason,
                    "required_completion_token": entry.get("required_completion_token"),
                    "merge_order": entry.get("merge_order"),
                }
            )
            continue
        if args.dry_run:
            receipt["merged_executors"].append(eid)
            continue
        source_head = str(ready_details.get("source_branch_head", ""))
        cp = run(["git", "merge", "--no-ff", "--no-commit", branch], repo_root)
        receipt["records"].append(record(["git", "merge", "--no-ff", "--no-commit", branch], cp))
        if cp.returncode != 0:
            run(["git", "merge", "--abort"], repo_root)
            receipt["merge_state"] = "NEEDS_REVISION_PARALLEL_MERGE_CONFLICT"
            receipt["failure_reason"] = f"{eid}: merge conflict or merge failure"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(receipt["failure_reason"], file=sys.stderr)
            return 1
        merged_head_before_commit = run(["git", "rev-parse", "HEAD"], repo_root).stdout.strip()
        cp = run(["git", "commit", "-m", f"Merge executor {eid}"], repo_root)
        receipt["records"].append(record(["git", "commit", "-m", f"Merge executor {eid}"], cp))
        if cp.returncode != 0:
            receipt["merge_state"] = "NEEDS_REVISION_PARALLEL_MERGE_CONFLICT"
            receipt["failure_reason"] = f"{eid}: merge commit failed"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(cp.stderr or cp.stdout, file=sys.stderr)
            return 1
        merged_commit = run(["git", "rev-parse", "HEAD"], repo_root).stdout.strip()
        receipt.setdefault("merge_details", []).append(
            {
                "executor_id": eid,
                "merged_commit": merged_commit,
                "source_branch_head": source_head,
                "pre_merge_head": merged_head_before_commit,
                "required_completion_token": entry.get("required_completion_token"),
                "completion_token": ready_details.get("completion_token"),
                "merge_order": entry.get("merge_order"),
                "merge_state": "MERGED",
            }
        )
        receipt["merged_executors"].append(eid)
    receipt["merge_state"] = "MERGED" if not args.dry_run else "DRY_RUN_READY"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(receipt["merge_state"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
