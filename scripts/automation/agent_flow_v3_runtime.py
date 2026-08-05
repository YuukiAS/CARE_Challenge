#!/usr/bin/env python3
"""Runtime helpers for CARE Agent-Flow v3 infrastructure.

These helpers are deliberately deterministic. They validate visual source
access, role-session receipts, and watcher routing logic without claiming that
GitHub Actions, scheduled GPT, GPU, Slurm, or scientific implementation review
has passed.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

SCHEMA = "CARE_AGENT_FLOW_V3"
ROLE_RECEIPT_SCHEMA = "CARE_AGENT_FLOW_V3_ROLE_SESSION_RECEIPT"
WATCHER_RECEIPT_SCHEMA = "CARE_AGENT_FLOW_V3_WATCHER_RECEIPT"
VISUAL_RECEIPT_SCHEMA = "CARE_AGENT_FLOW_V3_VISUAL_SOURCE_ACCESS_RECEIPT"
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CODEX_ROLES = ("controller", "verifier", "executor")
REVISION_STATES = {
    "PLANNER_REVISE_EXECUTOR": ("executor",),
    "PLANNER_REVISE_VERIFIER": ("verifier",),
    "PLANNER_REVISE_BOTH": ("verifier", "executor"),
}


class RuntimeErrorV3(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeErrorV3(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeErrorV3(f"JSON root is not an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def safe_rel_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeErrorV3(f"unsafe repository path: {value}")
    return path


def fetch_bytes(url: str, timeout: int) -> tuple[int | None, bytes, str | None]:
    req = Request(url, headers={"User-Agent": "CARE-Agent-Flow-v3-visual-audit"})
    try:
        with urlopen(req, timeout=timeout) as response:
            status = getattr(response, "status", None)
            return status, response.read(), None
    except Exception as exc:  # noqa: BLE001 - receipt must preserve failure text.
        fallback = subprocess.run(
            ["curl", "-fsSL", "--max-time", str(timeout), url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if fallback.returncode == 0 and fallback.stdout:
            return 200, fallback.stdout, f"python_urlopen_failed_then_curl_passed:{exc}"
        return None, b"", f"{exc}; curl_exit={fallback.returncode}; curl_stderr={fallback.stderr.decode('utf-8', 'replace')[:200]}"


def cmd_audit_visual_sources(args: argparse.Namespace) -> int:
    repo = args.repo_root.resolve()
    manifest_path = repo / args.visual_sources
    manifest = load_json(manifest_path)
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        raise RuntimeErrorV3("VISUAL_SOURCES.json must contain a sources list")

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for source in sources:
        if not isinstance(source, dict):
            failures.append("source_not_object")
            continue
        name = str(source.get("name", ""))
        rel = safe_rel_path(str(source.get("repository_reference", "")))
        local_path = repo / rel
        expected_sha = source.get("sha256")
        row: dict[str, Any] = {
            "name": name,
            "repository_reference": str(rel),
            "local_exists": local_path.is_file(),
            "expected_sha256": expected_sha,
            "local_sha256": None,
            "local_sha_match": False,
            "raw_url": source.get("public_visual_url"),
            "raw_http_status": None,
            "raw_sha256": None,
            "raw_sha_match": False,
            "anonymous_access": False,
            "error": None,
        }
        if not local_path.is_file():
            failures.append(f"{name}:missing_local")
        else:
            actual = sha_file(local_path)
            row["local_sha256"] = actual
            row["local_sha_match"] = actual == expected_sha
            if not row["local_sha_match"]:
                failures.append(f"{name}:local_sha_mismatch")
        url = source.get("public_visual_url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            status, payload, error = fetch_bytes(url, args.timeout_seconds)
            row["raw_http_status"] = status
            row["error"] = error
            if status == 200 and payload:
                digest = sha_bytes(payload)
                row["raw_sha256"] = digest
                row["raw_sha_match"] = digest == expected_sha
                row["anonymous_access"] = bool(row["raw_sha_match"])
                if not row["raw_sha_match"]:
                    failures.append(f"{name}:raw_sha_mismatch")
            else:
                failures.append(f"{name}:raw_access_failed")
        else:
            failures.append(f"{name}:missing_raw_url")
        rows.append(row)

    receipt = {
        "schema": VISUAL_RECEIPT_SCHEMA,
        "task_id": manifest.get("task_id"),
        "source_manifest": args.visual_sources,
        "source_manifest_sha256": sha_file(manifest_path),
        "required_source_count": sum(1 for s in sources if isinstance(s, dict) and s.get("required")),
        "checked_source_count": len(rows),
        "all_local_sha_match": all(row["local_sha_match"] for row in rows),
        "all_raw_urls_anonymous_and_sha_match": all(row["anonymous_access"] for row in rows),
        "scheduled_planner_critic_visual_smoke": "not_performed_by_this_command",
        "failures": failures,
        "sources": rows,
        "updated_utc": now(),
    }
    if args.output:
        write_json(args.output, receipt)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


def load_role_receipts(paths: list[Path]) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for path in paths:
        data = load_json(path)
        role = data.get("role")
        if role not in CODEX_ROLES:
            raise RuntimeErrorV3(f"invalid role in {path}: {role}")
        data["_path"] = str(path)
        receipts[str(role)] = data
    return receipts


def validate_role_receipts(receipts: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for role in CODEX_ROLES:
        if role not in receipts:
            failures.append(f"missing_role_receipt:{role}")
    if failures:
        return failures
    required = (
        "schema",
        "role",
        "thread_id",
        "codex_home",
        "worktree",
        "local_branch",
        "pid_or_process_status",
        "log_path",
        "state_path",
        "write_scope",
        "forbidden_scope",
        "last_commit_sha",
        "started_utc",
        "updated_utc",
    )
    for role, receipt in receipts.items():
        for key in required:
            if key not in receipt:
                failures.append(f"{role}:missing:{key}")
        if receipt.get("schema") != ROLE_RECEIPT_SCHEMA:
            failures.append(f"{role}:schema")
        if receipt.get("role") != role:
            failures.append(f"{role}:role_binding")
        sha = receipt.get("last_commit_sha")
        if sha is not None and not SHA40_RE.fullmatch(str(sha)):
            failures.append(f"{role}:last_commit_sha")
        for key in ("write_scope", "forbidden_scope"):
            value = receipt.get(key)
            if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
                failures.append(f"{role}:{key}")
    for field in ("thread_id", "codex_home", "worktree", "local_branch"):
        values = [str(receipts[role].get(field, "")) for role in CODEX_ROLES]
        if len(set(values)) != len(values):
            failures.append(f"duplicate:{field}")
    return failures


def cmd_validate_role_receipts(args: argparse.Namespace) -> int:
    receipts = load_role_receipts([path.resolve() for path in args.receipt])
    failures = validate_role_receipts(receipts)
    result = {
        "schema": "CARE_AGENT_FLOW_V3_ROLE_RECEIPT_VALIDATION",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "updated_utc": now(),
    }
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


def build_resume_command(codex_bin: str, worktree: Path, thread_id: str) -> list[str]:
    if not thread_id:
        raise RuntimeErrorV3("missing exact thread id")
    return [codex_bin, "exec", "-C", str(worktree), "resume", thread_id, "-"]


def cmd_watcher_once(args: argparse.Namespace) -> int:
    repo = args.repo_root.resolve()
    state_root = args.state_root.resolve()
    task_id = args.task_id
    lock_path = state_root / task_id / "watcher.lock"
    state_path = state_root / task_id / "watcher_state.json"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock_fh:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeErrorV3("watcher flock is already held") from exc

        if args.fetch:
            git(repo, "fetch", "origin", args.branch, "--prune")
        request = load_json(repo / args.request_path)
        current = load_json(repo / args.current_path)
        local_state = load_json(state_path) if state_path.is_file() else {
            "schema": WATCHER_RECEIPT_SCHEMA,
            "task_id": task_id,
            "processed_events": [],
        }
        receipt = evaluate_watcher_event(args, request, current, local_state)
        write_json(state_path, receipt)
        if args.output:
            write_json(args.output, receipt)
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0 if receipt["decision"] in {"IGNORE", "DRY_RUN_RESUME", "STOP_AT_HUMAN_GATE"} else 1


def evaluate_watcher_event(
    args: argparse.Namespace,
    request: dict[str, Any],
    current: dict[str, Any],
    local_state: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    if request.get("schema") != SCHEMA or current.get("schema") != SCHEMA:
        failures.append("schema")
    if request.get("task_id") != args.task_id or current.get("task_id") != args.task_id:
        failures.append("task_id")
    if request.get("integration_branch") != args.branch:
        failures.append("integration_branch")
    if current.get("request_nonce") != request.get("request_nonce"):
        failures.append("nonce_binding")
    if current.get("frozen_contract_sha256") != request.get("frozen_contract_sha256"):
        failures.append("frozen_contract_binding")
    integration_sha = current.get("integration_commit_sha")
    expected_integration_sha = request.get("expected_integration_commit_sha")
    if expected_integration_sha is not None and integration_sha != expected_integration_sha:
        failures.append("integration_commit_binding")
    if integration_sha is not None and not SHA40_RE.fullmatch(str(integration_sha)):
        failures.append("integration_commit_sha")
    state = current.get("state")
    event_key = f"{args.task_id}:{current.get('request_nonce')}:{current.get('review_round')}:{state}:{integration_sha}"
    processed = set(local_state.get("processed_events", []))
    target_roles = REVISION_STATES.get(str(state), ())
    decision = "IGNORE"
    commands: list[dict[str, str]] = []

    if failures:
        decision = "INVALID_EVENT"
    elif state in {"PLANNER_PASS", "AWAIT_HUMAN_DECISION"}:
        decision = "STOP_AT_HUMAN_GATE"
    elif event_key in processed:
        decision = "IGNORE"
    elif target_roles:
        role_plan = load_json(Path(args.role_plan).resolve())
        roles = role_plan.get("roles", {})
        if not request.get("enabled"):
            failures.append("request_disabled")
            decision = "INVALID_EVENT"
        else:
            decision = "DRY_RUN_RESUME" if args.dry_run else "LIVE_RESUME"
            for role in target_roles:
                role_data = roles.get(role, {})
                thread_file = Path(str(role_data.get("thread_id_file", "")))
                thread_id = args.thread_id_override or (thread_file.read_text(encoding="utf-8").strip() if thread_file.is_file() else "")
                receipt_path = Path(args.session_receipt_root) / f"{role}_session_receipt.json"
                if receipt_path.is_file():
                    role_receipt = load_json(receipt_path)
                    if role_receipt.get("thread_id") != thread_id:
                        failures.append(f"{role}:thread_id_receipt_mismatch")
                        continue
                command = build_resume_command(
                    args.codex_bin,
                    Path(str(role_data.get("worktree", ""))),
                    thread_id,
                )
                commands.append(
                    {
                        "role": role,
                        "thread_id": thread_id,
                        "codex_home": str(role_data.get("codex_home", "")),
                        "worktree": str(role_data.get("worktree", "")),
                        "command": shlex.join(command),
                    }
                )
            if failures:
                commands = []
                decision = "INVALID_EVENT"
            if not args.dry_run:
                failures.append("live_resume_not_enabled_in_watcher_once")
                decision = "INVALID_EVENT"
    if decision in {"DRY_RUN_RESUME", "STOP_AT_HUMAN_GATE"}:
        processed.add(event_key)

    return {
        "schema": WATCHER_RECEIPT_SCHEMA,
        "task_id": args.task_id,
        "branch": args.branch,
        "state": state,
        "review_round": current.get("review_round"),
        "request_nonce": current.get("request_nonce"),
        "integration_commit_sha": integration_sha,
        "event_key": event_key,
        "decision": decision,
        "target_roles": list(target_roles),
        "resume_commands": commands,
        "failures": failures,
        "processed_events": sorted(processed),
        "lock_path": str((args.state_root.resolve() / args.task_id / "watcher.lock")),
        "updated_utc": now(),
    }


def cmd_write_role_receipt(args: argparse.Namespace) -> int:
    receipt = {
        "schema": ROLE_RECEIPT_SCHEMA,
        "role": args.role,
        "thread_id": args.thread_id,
        "codex_home": args.codex_home,
        "worktree": args.worktree,
        "local_branch": args.local_branch,
        "pid_or_process_status": args.pid_or_process_status,
        "log_path": args.log_path,
        "state_path": args.state_path,
        "write_scope": args.write_scope,
        "forbidden_scope": args.forbidden_scope,
        "last_commit_sha": args.last_commit_sha,
        "started_utc": args.started_utc or now(),
        "updated_utc": now(),
    }
    write_json(args.output, receipt)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("audit-visual-sources")
    q.add_argument("--repo-root", type=Path, default=Path.cwd())
    q.add_argument("--visual-sources", default="automation/agent_flow_v3/tasks/care-ase-faithful/VISUAL_SOURCES.json")
    q.add_argument("--output", type=Path)
    q.add_argument("--timeout-seconds", type=int, default=20)
    q.set_defaults(func=cmd_audit_visual_sources)

    q = sub.add_parser("write-role-receipt")
    q.add_argument("--role", choices=CODEX_ROLES, required=True)
    q.add_argument("--thread-id", required=True)
    q.add_argument("--codex-home", required=True)
    q.add_argument("--worktree", required=True)
    q.add_argument("--local-branch", required=True)
    q.add_argument("--pid-or-process-status", required=True)
    q.add_argument("--log-path", required=True)
    q.add_argument("--state-path", required=True)
    q.add_argument("--write-scope", action="append", required=True)
    q.add_argument("--forbidden-scope", action="append", required=True)
    q.add_argument("--last-commit-sha")
    q.add_argument("--started-utc")
    q.add_argument("--output", type=Path, required=True)
    q.set_defaults(func=cmd_write_role_receipt)

    q = sub.add_parser("validate-role-receipts")
    q.add_argument("--receipt", type=Path, action="append", required=True)
    q.add_argument("--output", type=Path)
    q.set_defaults(func=cmd_validate_role_receipts)

    q = sub.add_parser("watcher-once")
    q.add_argument("--repo-root", type=Path, required=True)
    q.add_argument("--task-id", required=True)
    q.add_argument("--branch", default="develop")
    q.add_argument("--request-path", default="automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json")
    q.add_argument("--current-path", default="automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json")
    q.add_argument("--role-plan", default="prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json")
    q.add_argument("--session-receipt-root", default="results/agent_flow_v3/care-ase-faithful")
    q.add_argument("--codex-bin", default="/users/a/e/aereinh/codex-runtime/bin/codex")
    q.add_argument("--state-root", type=Path, default=Path("/users/a/e/aereinh/.agent-flow-v3"))
    q.add_argument("--thread-id-override", default="")
    q.add_argument("--fetch", action="store_true")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--output", type=Path)
    q.set_defaults(func=cmd_watcher_once)

    return p


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except RuntimeErrorV3 as exc:
        print(f"Agent-Flow v3 runtime error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
