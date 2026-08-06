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
WATCHER_STATE_SCHEMA = "CARE_AGENT_FLOW_V3_WATCHER_STATE"
RESUME_RECEIPT_SCHEMA = "CARE_AGENT_FLOW_V3_EXACT_RESUME_RECEIPT"
VISUAL_RECEIPT_SCHEMA = "CARE_AGENT_FLOW_V3_VISUAL_SOURCE_ACCESS_RECEIPT"
VISUAL_SMOKE_FINAL_SCHEMA = "CARE_AGENT_FLOW_V3_VISUAL_SMOKE_FINAL"
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


def git_show_json(repo: Path, ref: str, rel_path: str) -> dict[str, Any]:
    payload = subprocess.check_output(
        ["git", "show", f"{ref}:{rel_path}"],
        cwd=repo,
        text=True,
    )
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise RuntimeErrorV3(f"remote JSON root is not an object: {ref}:{rel_path}")
    return data


def git_show_text_or_none(repo: Path, ref: str, rel_path: str) -> str | None:
    cp = subprocess.run(
        ["git", "show", f"{ref}:{rel_path}"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return cp.stdout if cp.returncode == 0 else None


def parse_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


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


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def active_process_path(state_root: Path, task_id: str, role: str) -> Path:
    return state_root / task_id / f"{role}_active_process.json"


def role_active_process(state_root: Path, task_id: str, role: str) -> dict[str, Any] | None:
    path = active_process_path(state_root, task_id, role)
    if not path.is_file():
        return None
    try:
        data = load_json(path)
    except RuntimeErrorV3:
        return None
    pid = data.get("pid")
    if isinstance(pid, int) and is_pid_running(pid) and data.get("exit_code") is None:
        return data
    return None


def prompt_candidate_paths(repo: Path, task_id: str, role: str, current: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []
    role_prompts = current.get("repair_prompts")
    if isinstance(role_prompts, dict) and isinstance(role_prompts.get(role), str):
        candidates.append(repo / safe_rel_path(role_prompts[role]))
    if isinstance(current.get("repair_prompt_path"), str):
        candidates.append(repo / safe_rel_path(str(current["repair_prompt_path"])))
    if isinstance(current.get("planner_review_artifact"), str):
        candidates.append(repo / safe_rel_path(str(current["planner_review_artifact"])))
    review_round = current.get("review_round")
    if isinstance(review_round, int):
        candidates.append(repo / "results" / "agent_flow_v3" / task_id / "planner_reviews" / f"round_{review_round:03d}.json")
        candidates.append(repo / "results" / "agent_flow_v3" / task_id / "planner_reviews" / f"round_{review_round:03d}.md")
    return candidates


def load_exact_repair_prompt(repo: Path, task_id: str, role: str, current: dict[str, Any]) -> tuple[bytes, Path, str]:
    for path in prompt_candidate_paths(repo, task_id, role, current):
        if path.is_file():
            payload = path.read_bytes()
            return payload, path, sha_bytes(payload)
    raise RuntimeErrorV3(f"{role}:repair_prompt_missing")


def execute_live_resume(
    *,
    command: list[str],
    codex_home: str,
    role: str,
    task_id: str,
    state_root: Path,
    log_root: Path,
    prompt_payload: bytes,
    prompt_path: Path,
    popen_factory: Any = subprocess.Popen,
) -> dict[str, Any]:
    active = role_active_process(state_root, task_id, role)
    if active:
        raise RuntimeErrorV3(f"{role}:active_process")

    started = now()
    prompt_sha = sha_bytes(prompt_payload)
    log_dir = log_root / task_id / role
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = started.replace(":", "").replace("-", "")
    stdout_path = log_dir / f"resume_{stamp}.stdout.log"
    stderr_path = log_dir / f"resume_{stamp}.stderr.log"
    active_path = active_process_path(state_root, task_id, role)
    active_path.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["CODEX_HOME"] = codex_home
    proc = popen_factory(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    active_record = {
        "schema": RESUME_RECEIPT_SCHEMA,
        "task_id": task_id,
        "role": role,
        "pid": int(proc.pid),
        "thread_id": command[-2],
        "command": shlex.join(command),
        "codex_home": codex_home,
        "prompt_path": str(prompt_path),
        "prompt_sha256": prompt_sha,
        "started_utc": started,
        "exit_code": None,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
    }
    write_json(active_path, active_record)
    stdout, stderr = proc.communicate(input=prompt_payload)
    stdout_path.write_bytes(stdout or b"")
    stderr_path.write_bytes(stderr or b"")
    finished = now()
    receipt = {
        **active_record,
        "exit_code": int(proc.returncode),
        "finished_utc": finished,
    }
    write_json(active_path, receipt)
    return receipt


def validate_role_plan_push_authority(role_plan: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if role_plan.get("integration_branch") != "develop":
        failures.append("integration_branch")
    if role_plan.get("controller_pushes_integration_branch") is not True:
        failures.append("controller_pushes_integration_branch")
    if role_plan.get("remote_role_branches_authorized") is not False:
        failures.append("remote_role_branches_authorized")
    roles = role_plan.get("roles", {})
    if not isinstance(roles, dict):
        return failures + ["roles"]
    for role in ("verifier", "executor"):
        role_data = roles.get(role, {})
        if isinstance(role_data, dict) and role_data.get("pushes_integration_branch"):
            failures.append(f"{role}:pushes_integration_branch")
    return failures


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
        if args.from_origin:
            ref = f"origin/{args.branch}"
            request = git_show_json(repo, ref, args.request_path)
            current = git_show_json(repo, ref, args.current_path)
        else:
            request = load_json(repo / args.request_path)
            current = load_json(repo / args.current_path)
        local_state = load_json(state_path) if state_path.is_file() else {
            "schema": WATCHER_STATE_SCHEMA,
            "task_id": task_id,
            "processed_events": [],
            "resume_history": [],
            "invalid_events": [],
        }
        receipt = evaluate_watcher_event(args, request, current, local_state)
        if receipt["decision"] == "LIVE_RESUME":
            receipt = perform_live_resumes(args, repo, request, current, receipt, local_state)
        new_state = update_watcher_state(local_state, receipt)
        write_json(state_path, new_state)
        if args.output:
            write_json(args.output, receipt)
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0 if receipt["decision"] in {"IGNORE", "IGNORE_DISABLED", "DRY_RUN_RESUME", "LIVE_RESUME", "STOP_AT_HUMAN_GATE"} else 1


def update_watcher_state(local_state: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    state = {
        "schema": WATCHER_STATE_SCHEMA,
        "task_id": receipt["task_id"],
        "processed_events": list(local_state.get("processed_events", [])),
        "resume_history": list(local_state.get("resume_history", [])),
        "invalid_events": list(local_state.get("invalid_events", [])),
        "last_receipt": receipt,
        "updated_utc": now(),
    }
    if receipt["decision"] in {"DRY_RUN_RESUME", "LIVE_RESUME", "STOP_AT_HUMAN_GATE"}:
        if receipt["event_key"] not in state["processed_events"]:
            state["processed_events"].append(receipt["event_key"])
    if receipt["decision"] == "LIVE_RESUME":
        state["resume_history"].extend(receipt.get("resume_results", []))
    if receipt["decision"] == "INVALID_EVENT":
        state["invalid_events"].append(
            {
                "event_key": receipt["event_key"],
                "failures": receipt.get("failures", []),
                "updated_utc": receipt["updated_utc"],
            }
        )
    state["processed_events"] = sorted(set(state["processed_events"]))
    return state


def perform_live_resumes(
    args: argparse.Namespace,
    repo: Path,
    request: dict[str, Any],
    current: dict[str, Any],
    receipt: dict[str, Any],
    local_state: dict[str, Any],
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    failures = list(receipt.get("failures", []))
    for item in receipt.get("resume_commands", []):
        role = item["role"]
        prompt_payload, prompt_path, prompt_sha = load_exact_repair_prompt(repo, args.task_id, role, current)
        item["prompt_path"] = str(prompt_path)
        item["prompt_sha256"] = prompt_sha
        try:
            result = execute_live_resume(
                command=item["command_argv"],
                codex_home=item["codex_home"],
                role=role,
                task_id=args.task_id,
                state_root=args.state_root.resolve(),
                log_root=args.log_root.resolve(),
                prompt_payload=prompt_payload,
                prompt_path=prompt_path,
            )
            results.append(result)
            if result["exit_code"] != 0:
                failures.append(f"{role}:resume_exit:{result['exit_code']}")
        except RuntimeErrorV3 as exc:
            failures.append(str(exc))
    receipt["resume_results"] = results
    receipt["failures"] = failures
    if failures:
        receipt["decision"] = "INVALID_EVENT"
    return receipt


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
    expected_review_round = request.get("expected_review_round")
    if expected_review_round is not None and current.get("review_round") != expected_review_round:
        failures.append("review_round_binding")
    if not isinstance(current.get("review_round"), int) or current.get("review_round") < 0:
        failures.append("review_round")
    state = current.get("state")
    event_key = f"{args.task_id}:{current.get('request_nonce')}:{current.get('review_round')}:{state}:{integration_sha}"
    processed = set(local_state.get("processed_events", []))
    target_roles = REVISION_STATES.get(str(state), ())
    decision = "IGNORE"
    commands: list[dict[str, str]] = []

    if request.get("enabled") is not True:
        decision = "IGNORE_DISABLED"
        failures.append("request_disabled")
    elif failures:
        decision = "INVALID_EVENT"
    elif state in {"PLANNER_PASS", "AWAIT_HUMAN_DECISION"}:
        decision = "STOP_AT_HUMAN_GATE"
    elif event_key in processed:
        decision = "IGNORE"
    elif target_roles:
        role_plan = load_json(Path(args.role_plan).resolve())
        roles = role_plan.get("roles", {})
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
            if role_active_process(args.state_root.resolve(), args.task_id, role):
                failures.append(f"{role}:active_process")
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
                    "command_argv": command,
                }
            )
        if failures:
            commands = []
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


def cmd_watch(args: argparse.Namespace) -> int:
    repo = args.repo_root.resolve()
    state_root = args.state_root.resolve()
    task_id = args.task_id
    lock_path = state_root / task_id / "watcher.lock"
    stop_path = state_root / task_id / "stop_watcher"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    cycles = 0
    with lock_path.open("a+") as lock_fh:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeErrorV3("watcher flock is already held") from exc
        while True:
            cycles += 1
            if stop_path.exists():
                return 0
            try:
                cycle_args = argparse.Namespace(**vars(args))
                cycle_args.fetch = True
                cycle_args.from_origin = True
                cycle_args.dry_run = False
                cycle_args.output = args.output
                cycle_args.max_cycles = None
                run_watch_cycle_without_lock(cycle_args)
            except Exception as exc:  # noqa: BLE001 - long watcher must fail closed and keep polling.
                failure_path = state_root / task_id / "watcher_last_error.json"
                write_json(
                    failure_path,
                    {
                        "schema": WATCHER_STATE_SCHEMA,
                        "task_id": task_id,
                        "error": f"{type(exc).__name__}: {exc}",
                        "updated_utc": now(),
                    },
                )
            if args.max_cycles and cycles >= args.max_cycles:
                return 0
            time.sleep(args.poll_seconds)


def run_watch_cycle_without_lock(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo_root.resolve()
    git(repo, "fetch", "origin", args.branch, "--prune")
    request = git_show_json(repo, f"origin/{args.branch}", args.request_path)
    current = git_show_json(repo, f"origin/{args.branch}", args.current_path)
    state_path = args.state_root.resolve() / args.task_id / "watcher_state.json"
    local_state = load_json(state_path) if state_path.is_file() else {
        "schema": WATCHER_STATE_SCHEMA,
        "task_id": args.task_id,
        "processed_events": [],
        "resume_history": [],
        "invalid_events": [],
    }
    receipt = evaluate_watcher_event(args, request, current, local_state)
    if receipt["decision"] == "LIVE_RESUME":
        receipt = perform_live_resumes(args, repo, request, current, receipt, local_state)
    state = update_watcher_state(local_state, receipt)
    write_json(state_path, state)
    if args.output:
        write_json(args.output, receipt)
    return receipt


def tmux_target(session: str, window: str) -> str:
    return f"{session}:{window}"


def cmd_start_watcher(args: argparse.Namespace) -> int:
    stop_path = args.state_root.resolve() / args.task_id / "stop_watcher"
    if stop_path.exists():
        stop_path.unlink()
    script = Path(__file__).resolve()
    command = [
        sys.executable,
        str(script),
        "watch",
        "--repo-root",
        str(args.repo_root),
        "--task-id",
        args.task_id,
        "--branch",
        args.branch,
        "--request-path",
        args.request_path,
        "--current-path",
        args.current_path,
        "--role-plan",
        args.role_plan,
        "--session-receipt-root",
        args.session_receipt_root,
        "--codex-bin",
        args.codex_bin,
        "--state-root",
        str(args.state_root),
        "--log-root",
        str(args.log_root),
        "--poll-seconds",
        str(args.poll_seconds),
    ]
    shell_command = shlex.join(command)
    target = tmux_target(args.tmux_session, args.tmux_window)
    has_session = subprocess.run(
        ["tmux", "has-session", "-t", args.tmux_session],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if has_session.returncode != 0:
        tmux_cmd = ["tmux", "new-session", "-d", "-s", args.tmux_session, "-n", args.tmux_window, shell_command]
    else:
        existing = subprocess.run(["tmux", "list-windows", "-t", args.tmux_session, "-F", "#{window_name}"], text=True, stdout=subprocess.PIPE, check=False)
        if args.tmux_window in existing.stdout.splitlines():
            print(json.dumps({"status": "already_running_or_window_exists", "target": target}, indent=2))
            return 0
        tmux_cmd = ["tmux", "new-window", "-d", "-t", args.tmux_session, "-n", args.tmux_window, shell_command]
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN", "target": target, "command": shell_command}, indent=2))
        return 0
    subprocess.check_call(tmux_cmd)
    print(json.dumps({"status": "STARTED", "target": target, "command": shell_command}, indent=2))
    return 0


def cmd_stop_watcher(args: argparse.Namespace) -> int:
    stop_path = args.state_root.resolve() / args.task_id / "stop_watcher"
    stop_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.write_text(now() + "\n", encoding="utf-8")
    target = tmux_target(args.tmux_session, args.tmux_window)
    subprocess.run(["tmux", "kill-window", "-t", target], check=False)
    print(json.dumps({"status": "STOP_REQUESTED", "target": target, "stop_path": str(stop_path)}, indent=2))
    return 0


def cmd_status_watcher(args: argparse.Namespace) -> int:
    target = tmux_target(args.tmux_session, args.tmux_window)
    tmux = subprocess.run(["tmux", "display-message", "-p", "-t", target, "#{pane_pid}|#{pane_current_command}"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    state_path = args.state_root.resolve() / args.task_id / "watcher_state.json"
    status = {
        "schema": WATCHER_STATE_SCHEMA,
        "task_id": args.task_id,
        "target": target,
        "tmux_window_found": tmux.returncode == 0,
        "tmux_detail": tmux.stdout.strip() if tmux.returncode == 0 else tmux.stderr.strip(),
        "state_path": str(state_path),
        "state_exists": state_path.is_file(),
        "updated_utc": now(),
    }
    if state_path.is_file():
        status["state"] = load_json(state_path)
    if getattr(args, "output", None):
        write_json(args.output, status)
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0


def validate_visual_smoke_receipt(
    receipt: dict[str, Any],
    *,
    expected_role: str,
    request_nonce: str,
    expected_shas: dict[str, str],
) -> list[str]:
    failures: list[str] = []
    if receipt.get("role") != expected_role:
        failures.append("role")
    if receipt.get("request_nonce") != request_nonce:
        failures.append("request_nonce")
    image_sha256 = receipt.get("image_sha256")
    if not isinstance(image_sha256, dict):
        failures.append("image_sha256")
    else:
        for name, digest in expected_shas.items():
            if image_sha256.get(name) != digest:
                failures.append(f"image_sha256:{name}")
    answers = receipt.get("answers")
    required_answers = (
        "main_modules",
        "key_data_flow",
        "missing_modality_no_t2_safety",
        "explicitly_absent_components",
        "structural_differences",
    )
    if not isinstance(answers, dict):
        failures.append("answers")
    else:
        for key in required_answers:
            value = answers.get(key)
            if not isinstance(value, str) or len(value.strip()) < 20:
                failures.append(f"answers:{key}")
    provenance = receipt.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("producer") != "scheduled_gpt":
        failures.append("provenance:scheduled_gpt")
    return failures


def cmd_observe_visual_smoke(args: argparse.Namespace) -> int:
    repo = args.repo_root.resolve()
    if args.fetch:
        git(repo, "fetch", "origin", args.branch, "--prune")
    ref = f"origin/{args.branch}" if args.from_origin else "HEAD"
    request = git_show_json(repo, ref, args.request_path)
    current = git_show_json(repo, ref, args.current_path)
    visual = git_show_json(repo, ref, args.visual_sources_path)
    expected_shas = {
        str(source["name"]): str(source["sha256"])
        for source in visual.get("sources", [])
        if isinstance(source, dict) and source.get("name") in {"CARE-ASE", "SRR-v3", "MoSAIC"}
    }
    request_nonce = str(request.get("request_nonce") or current.get("request_nonce") or "")
    start_utc = str(request.get("created_utc") or current.get("updated_utc"))
    elapsed_seconds = max(0, int((datetime.now(timezone.utc) - parse_utc(start_utc)).total_seconds()))
    completed_windows = elapsed_seconds // args.window_seconds

    receipt_status: dict[str, Any] = {}
    all_failures: list[str] = []
    for role in ("planner", "critic"):
        rel = f"results/agent_flow_v3/{args.task_id}/{role}_visual_receipt.json"
        raw = git_show_text_or_none(repo, ref, rel)
        status: dict[str, Any] = {"path": rel, "exists": raw is not None, "valid": False, "failures": []}
        if raw is not None:
            try:
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError("not object")
                failures = validate_visual_smoke_receipt(
                    data,
                    expected_role=f"{role}_visual_smoke",
                    request_nonce=request_nonce,
                    expected_shas=expected_shas,
                )
                status["valid"] = not failures
                status["failures"] = failures
                status["commit_sha"] = git(repo, "log", "-1", "--format=%H", ref, "--", rel)
            except Exception as exc:  # noqa: BLE001 - receipt preserves validation problem.
                status["failures"] = [f"unreadable:{type(exc).__name__}:{exc}"]
        if not status["valid"]:
            all_failures.extend(f"{role}:{failure}" for failure in status["failures"] or ["missing"])
        receipt_status[role] = status

    passed = not all_failures and completed_windows >= args.min_windows
    result = {
        "schema": VISUAL_SMOKE_FINAL_SCHEMA,
        "task_id": args.task_id,
        "branch": args.branch,
        "request_nonce": request_nonce,
        "request_enabled": request.get("enabled"),
        "current_state": current.get("state"),
        "expected_image_sha256": expected_shas,
        "window_seconds": args.window_seconds,
        "minimum_wait_windows_required": args.min_windows,
        "minimum_wait_windows_completed": completed_windows,
        "elapsed_seconds": elapsed_seconds,
        "scheduled_planner_receipt": receipt_status["planner"],
        "scheduled_critic_receipt": receipt_status["critic"],
        "status": "PASS" if passed else "AWAITING_REAL_SCHEDULED_GPT_RECEIPTS",
        "failures": all_failures,
        "updated_utc": now(),
    }
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


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

    def add_watcher_args(q: argparse.ArgumentParser) -> None:
        q.add_argument("--repo-root", type=Path, required=True)
        q.add_argument("--task-id", required=True)
        q.add_argument("--branch", default="develop")
        q.add_argument("--request-path", default="automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json")
        q.add_argument("--current-path", default="automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json")
        q.add_argument("--role-plan", default="prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json")
        q.add_argument("--session-receipt-root", default="results/agent_flow_v3/care-ase-faithful")
        q.add_argument("--codex-bin", default="/users/a/e/aereinh/codex-runtime/bin/codex")
        q.add_argument("--state-root", type=Path, default=Path("/users/a/e/aereinh/.agent-flow-v3"))
        q.add_argument("--log-root", type=Path, default=Path("/users/a/e/aereinh/.agent-flow-v3/logs"))
        q.add_argument("--thread-id-override", default="")

    q = sub.add_parser("watcher-once")
    add_watcher_args(q)
    q.add_argument("--fetch", action="store_true")
    q.add_argument("--from-origin", action="store_true")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--output", type=Path)
    q.set_defaults(func=cmd_watcher_once)

    q = sub.add_parser("watch")
    add_watcher_args(q)
    q.add_argument("--poll-seconds", type=int, default=60)
    q.add_argument("--max-cycles", type=int)
    q.add_argument("--output", type=Path)
    q.set_defaults(func=cmd_watch)

    q = sub.add_parser("start-watcher")
    add_watcher_args(q)
    q.add_argument("--poll-seconds", type=int, default=60)
    q.add_argument("--tmux-session", default="care_agent_flow_v3")
    q.add_argument("--tmux-window", default="Watcher")
    q.add_argument("--dry-run", action="store_true")
    q.set_defaults(func=cmd_start_watcher)

    q = sub.add_parser("stop-watcher")
    q.add_argument("--task-id", required=True)
    q.add_argument("--state-root", type=Path, default=Path("/users/a/e/aereinh/.agent-flow-v3"))
    q.add_argument("--tmux-session", default="care_agent_flow_v3")
    q.add_argument("--tmux-window", default="Watcher")
    q.set_defaults(func=cmd_stop_watcher)

    q = sub.add_parser("status-watcher")
    q.add_argument("--task-id", required=True)
    q.add_argument("--state-root", type=Path, default=Path("/users/a/e/aereinh/.agent-flow-v3"))
    q.add_argument("--tmux-session", default="care_agent_flow_v3")
    q.add_argument("--tmux-window", default="Watcher")
    q.add_argument("--output", type=Path)
    q.set_defaults(func=cmd_status_watcher)

    q = sub.add_parser("observe-visual-smoke")
    q.add_argument("--repo-root", type=Path, required=True)
    q.add_argument("--task-id", default="care-visual-smoke")
    q.add_argument("--branch", default="develop")
    q.add_argument("--request-path", default="automation/agent_flow_v3/tasks/care-visual-smoke/REQUEST.json")
    q.add_argument("--current-path", default="automation/agent_flow_v3/tasks/care-visual-smoke/CURRENT.json")
    q.add_argument("--visual-sources-path", default="automation/agent_flow_v3/tasks/care-visual-smoke/VISUAL_SOURCES.json")
    q.add_argument("--from-origin", action="store_true")
    q.add_argument("--fetch", action="store_true")
    q.add_argument("--window-seconds", type=int, default=3600)
    q.add_argument("--min-windows", type=int, default=2)
    q.add_argument("--output", type=Path)
    q.set_defaults(func=cmd_observe_visual_smoke)

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
