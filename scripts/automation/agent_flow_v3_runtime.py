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
from fnmatch import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
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
ORCHESTRATOR_STATE_SCHEMA = "CARE_AGENT_FLOW_V3_STAGE_ORCHESTRATOR_STATE"
ORCHESTRATOR_RECEIPT_SCHEMA = "CARE_AGENT_FLOW_V3_STAGE_ORCHESTRATOR_RECEIPT"
CONTROLLER_START_RECEIPT_SCHEMA = "CARE_AGENT_FLOW_V3_CONTROLLER_START_RECEIPT"
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


def git_status_short(repo: Path) -> str:
    return subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip()


def git_commit_subject(repo: Path, commit_sha: str) -> str:
    return git(repo, "show", "-s", "--format=%s", commit_sha)


def ensure_clean_ff_to_remote(repo: Path, branch: str) -> str:
    status = git_status_short(repo)
    if status:
        raise RuntimeErrorV3("worktree_not_clean_before_stage_update")
    git(repo, "merge", "--ff-only", f"origin/{branch}")
    return git(repo, "rev-parse", "HEAD")


def commit_and_push(repo: Path, branch: str, paths: list[str], message: str) -> dict[str, Any]:
    subprocess.check_call(["git", "add", *paths], cwd=repo)
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo,
        check=False,
    )
    if diff.returncode == 0:
        return {
            "status": "NO_CHANGES",
            "branch": branch,
            "commit_sha": git(repo, "rev-parse", "HEAD"),
            "pushed": False,
        }
    subprocess.check_call(["git", "commit", "-m", message], cwd=repo)
    commit_sha = git(repo, "rev-parse", "HEAD")
    subprocess.check_call(["git", "push", "origin", f"HEAD:{branch}"], cwd=repo)
    return {
        "status": "COMMITTED_AND_PUSHED",
        "branch": branch,
        "commit_sha": commit_sha,
        "pushed": True,
    }


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


def git_show_bytes_or_none(repo: Path, ref: str, rel_path: str) -> bytes | None:
    cp = subprocess.run(
        ["git", "show", f"{ref}:{rel_path}"],
        cwd=repo,
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


def role_rollout_paths(codex_home: Path, thread_id: str) -> list[Path]:
    if not thread_id or not codex_home.is_dir():
        return []
    sessions = codex_home / "sessions"
    if not sessions.is_dir():
        return []
    return sorted(sessions.glob(f"**/*{thread_id}*.jsonl"))


def role_rollout_exists(codex_home: str, thread_id: str) -> bool:
    return bool(role_rollout_paths(Path(codex_home), thread_id))


def role_rollout_goal_complete(codex_home: str, thread_id: str) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for rollout in role_rollout_paths(Path(codex_home), thread_id):
        try:
            lines = rollout.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            if payload.get("type") != "function_call_output":
                continue
            output = payload.get("output")
            if not isinstance(output, str) or '"goal"' not in output or '"status"' not in output:
                continue
            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                continue
            goal = parsed.get("goal")
            if isinstance(goal, dict) and goal.get("status") == "complete":
                latest = {
                    "rollout_path": str(rollout),
                    "thread_id": goal.get("threadId") or thread_id,
                    "status": goal.get("status"),
                    "tokens_used": goal.get("tokensUsed"),
                    "time_used_seconds": goal.get("timeUsedSeconds"),
                    "updated_at": goal.get("updatedAt"),
                }
    return latest


def validate_role_receipts(receipts: dict[str, dict[str, Any]], *, require_production: bool = False) -> list[str]:
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
        if require_production:
            if receipt.get("production_eligible") is not True:
                failures.append(f"{role}:production_eligible")
            if receipt.get("resume_verified") is not True:
                failures.append(f"{role}:resume_verified")
            for key in (
                "launch_command",
                "launch_prompt_sha256",
                "launch_exit_code",
                "launch_started_utc",
                "launch_finished_utc",
                "resume_command",
                "resume_prompt_sha256",
                "resume_exit_code",
                "resume_started_utc",
                "resume_finished_utc",
            ):
                if key not in receipt:
                    failures.append(f"{role}:missing:{key}")
            if receipt.get("launch_exit_code") != 0:
                failures.append(f"{role}:launch_exit_code")
            if receipt.get("resume_exit_code") != 0:
                failures.append(f"{role}:resume_exit_code")
            thread_id = str(receipt.get("thread_id", ""))
            codex_home = str(receipt.get("codex_home", ""))
            rollout_path = receipt.get("rollout_session_path") or receipt.get("rollout_path")
            if isinstance(rollout_path, str) and rollout_path:
                path = Path(rollout_path)
                if not path.is_file():
                    failures.append(f"{role}:rollout_missing")
                else:
                    try:
                        path.relative_to(Path(codex_home))
                    except ValueError:
                        failures.append(f"{role}:rollout_wrong_codex_home")
            elif not role_rollout_exists(codex_home, thread_id):
                failures.append(f"{role}:rollout_missing")
    for field in ("thread_id", "codex_home", "worktree", "local_branch"):
        values = [str(receipts[role].get(field, "")) for role in CODEX_ROLES]
        if len(set(values)) != len(values):
            failures.append(f"duplicate:{field}")
    return failures


def cmd_validate_role_receipts(args: argparse.Namespace) -> int:
    receipts = load_role_receipts([path.resolve() for path in args.receipt])
    failures = validate_role_receipts(receipts, require_production=args.require_production)
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
    return [codex_bin, "exec", "-C", str(worktree), "resume", "--all", thread_id, "-"]


def build_controller_start_command(codex_bin: str, worktree: Path, thread_id: str) -> list[str]:
    if not thread_id:
        raise RuntimeErrorV3("missing exact controller thread id")
    return [codex_bin, "exec", "-C", str(worktree), "resume", thread_id, "-"]


def role_codex_env(codex_home: str, worktree: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["CODEX_HOME"] = codex_home
    env["CODEX_PERSISTENT_HOME"] = codex_home
    env["CODEX_HOME_OVERRIDE"] = codex_home
    env["CODEX_RESPECT_CODEX_HOME"] = "1"
    env["CODEX_USE_RUNTIME_HOME"] = "0"
    if worktree is not None:
        env["CODEX_REPO_ROOT"] = str(worktree)
        env["CODEX_RESPECT_REPO_ROOT"] = "1"
    return env


def resume_command_worktree(command: list[str]) -> Path | None:
    for flag in ("-C", "--cd"):
        if flag in command:
            index = command.index(flag)
            if index + 1 < len(command):
                return Path(command[index + 1])
    return None


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


def pid_command(pid: int) -> str:
    cp = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return cp.stdout.strip() if cp.returncode == 0 else ""


def pid_looks_like_codex(pid: int) -> bool:
    command = pid_command(pid)
    return "codex" in command and (" exec" in command or "codex.js" in command)


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
    if data.get("completion_detected_via_rollout") is True and data.get("exit_code") == 0:
        return None
    pid = data.get("pid")
    if isinstance(pid, int) and is_pid_running(pid) and data.get("exit_code") is None:
        if pid_looks_like_codex(pid) or process_has_child(pid):
            return data
    return None


def prompt_candidate_rel_paths(task_id: str, role: str, current: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []
    role_prompts = current.get("repair_prompts")
    if isinstance(role_prompts, dict) and isinstance(role_prompts.get(role), str):
        candidates.append(safe_rel_path(role_prompts[role]))
    if isinstance(current.get("repair_prompt_path"), str):
        candidates.append(safe_rel_path(str(current["repair_prompt_path"])))
    if isinstance(current.get("planner_review_artifact"), str):
        candidates.append(safe_rel_path(str(current["planner_review_artifact"])))
    review_round = current.get("review_round")
    if isinstance(review_round, int):
        candidates.append(Path("results") / "agent_flow_v3" / task_id / "planner_reviews" / f"round_{review_round:03d}.json")
        candidates.append(Path("results") / "agent_flow_v3" / task_id / "planner_reviews" / f"round_{review_round:03d}.md")
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.as_posix()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def prompt_candidate_paths(repo: Path, task_id: str, role: str, current: dict[str, Any]) -> list[Path]:
    return [repo / rel_path for rel_path in prompt_candidate_rel_paths(task_id, role, current)]


def load_exact_repair_prompt(
    repo: Path,
    task_id: str,
    role: str,
    current: dict[str, Any],
    *,
    ref: str | None = None,
) -> tuple[bytes, Path, str]:
    for rel_path in prompt_candidate_rel_paths(task_id, role, current):
        path = repo / rel_path
        if path.is_file():
            payload = path.read_bytes()
            return payload, path, sha_bytes(payload)
        if ref:
            payload = git_show_bytes_or_none(repo, ref, rel_path.as_posix())
            if payload is not None:
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

    worktree = resume_command_worktree(command)
    env = role_codex_env(codex_home, worktree)
    proc = popen_factory(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(worktree) if worktree else None,
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
        prompt_payload, prompt_path, prompt_sha = load_exact_repair_prompt(
            repo,
            args.task_id,
            role,
            current,
            ref=f"origin/{args.branch}",
        )
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
    args = resolve_watcher_paths(args)
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
    args = resolve_watcher_paths(args)
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


def tmux_window_exists(session: str, window: str) -> bool:
    existing = subprocess.run(
        ["tmux", "list-windows", "-t", session, "-F", "#{window_name}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return existing.returncode == 0 and window in existing.stdout.splitlines()


def tmux_pane_pid(session: str, window: str) -> int | None:
    cp = subprocess.run(
        ["tmux", "display-message", "-p", "-t", tmux_target(session, window), "#{pane_pid}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if cp.returncode != 0:
        return None
    try:
        return int(cp.stdout.strip())
    except ValueError:
        return None


def process_has_child(pid: int | None) -> bool:
    if not pid:
        return False
    cp = subprocess.run(
        ["pgrep", "-P", str(pid)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return cp.returncode == 0 and bool(cp.stdout.strip())


def care_ase_controller_start_receipt_path(stage_state_root: Path) -> Path:
    return stage_state_root.resolve().parent / "care-ase-faithful" / "controller_start_receipt.json"


def care_ase_verifier_launch_receipt_path(stage_state_root: Path) -> Path:
    return stage_state_root.resolve().parent / "care-ase-faithful" / "verifier_launch_receipt.json"


def care_ase_role_launch_receipt_path(stage_state_root: Path, role: str) -> Path:
    return stage_state_root.resolve().parent / "care-ase-faithful" / f"{role}_launch_receipt.json"


def care_ase_role_launch_satisfied(stage_state_root: Path, current: dict[str, Any], role: str) -> bool:
    receipt_path = care_ase_role_launch_receipt_path(stage_state_root, role)
    if not receipt_path.is_file():
        return False
    try:
        receipt = load_json(receipt_path)
    except RuntimeErrorV3:
        return False
    if receipt.get("task_id") != "care-ase-faithful":
        return False
    if receipt.get("role") != role:
        return False
    if receipt.get("request_nonce") != current.get("request_nonce"):
        return False
    if receipt.get("frozen_contract_sha256") != current.get("frozen_contract_sha256"):
        return False
    status = receipt.get("status")
    if status == "VERIFIER_FREEZE_COMPLETE":
        return True
    if status in {"STARTED", "ALREADY_RUNNING", "STARTED_RUNNING"}:
        pid = receipt.get("pid") or receipt.get("pane_pid")
        return isinstance(pid, int) and is_pid_running(pid)
    return False


def path_matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def validate_role_commit_scope(paths: list[str], role_data: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    write_scope = [str(item) for item in role_data.get("write_scope", []) if isinstance(item, str)]
    forbidden_scope = [str(item) for item in role_data.get("forbidden_scope", []) if isinstance(item, str)]
    for path in paths:
        if path_matches_any(path, forbidden_scope):
            failures.append(f"forbidden_path:{path}")
        elif write_scope and not path_matches_any(path, write_scope):
            failures.append(f"outside_write_scope:{path}")
    return failures


def care_ase_controller_start_satisfied(stage_state_root: Path, current: dict[str, Any]) -> bool:
    return care_ase_role_launch_satisfied(stage_state_root, current, "verifier")


def resolve_watcher_paths(args: argparse.Namespace) -> argparse.Namespace:
    task_dir = f"automation/agent_flow_v3/tasks/{args.task_id}"
    if not args.request_path:
        args.request_path = f"{task_dir}/REQUEST.json"
    if not args.current_path:
        args.current_path = f"{task_dir}/CURRENT.json"
    if not args.role_plan:
        task_role_plan = f"{task_dir}/ROLE_PLAN.json"
        legacy_ase_role_plan = "prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json"
        if args.task_id == "care-ase-faithful" and (args.repo_root / legacy_ase_role_plan).is_file():
            args.role_plan = legacy_ase_role_plan
        else:
            args.role_plan = task_role_plan
    if not args.session_receipt_root:
        args.session_receipt_root = f"results/agent_flow_v3/{args.task_id}"
    return args


def cmd_start_watcher(args: argparse.Namespace) -> int:
    args = resolve_watcher_paths(args)
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


def remote_head(repo: Path, branch: str) -> str:
    return git(repo, "rev-parse", f"origin/{branch}")


def remote_task_request_paths(repo: Path, ref: str) -> list[str]:
    listing = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", ref, "automation/agent_flow_v3/tasks"],
        cwd=repo,
        text=True,
    )
    return sorted(path for path in listing.splitlines() if path.endswith("/REQUEST.json"))


def load_orchestrator_state(path: Path) -> dict[str, Any]:
    if path.is_file():
        return load_json(path)
    return {
        "schema": ORCHESTRATOR_STATE_SCHEMA,
        "processed_events": [],
        "waits": {},
        "last_receipt": None,
        "updated_utc": now(),
    }


def wait_deadline(start_utc: str, hours: int) -> str:
    return (parse_utc(start_utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def update_wait_fields(current: dict[str, Any], *, remote_sha: str, expected: str, default_hours: int) -> dict[str, Any]:
    updated = dict(current)
    started = str(updated.get("external_wait_started_utc") or now())
    deadline = str(updated.get("external_wait_deadline_utc") or wait_deadline(started, default_hours))
    updated.update(
        {
            "state": "WAITING_FOR_EXTERNAL_GPT",
            "external_wait_started_utc": started,
            "external_wait_deadline_utc": deadline,
            "expected_state_or_artifact": str(updated.get("expected_state_or_artifact") or expected),
            "last_observed_remote_sha": remote_sha,
            "last_poll_utc": now(),
            "next_action": "KEEP_FETCHING_ORIGIN_DEVELOP_UNTIL_EXPECTED_GPT_STATE_OR_ARTIFACT",
            "updated_utc": now(),
        }
    )
    return updated


def stage_event_key(task_id: str, current: dict[str, Any], remote_sha: str) -> str:
    del remote_sha
    return ":".join(
        [
            task_id,
            str(current.get("request_nonce")),
            str(current.get("review_round")),
            str(current.get("state")),
        ]
    )


def stage_event_was_processed(event_key: str, processed: set[str]) -> bool:
    return event_key in processed or any(old_key.startswith(f"{event_key}:") for old_key in processed)


def merge_existing_wait_metadata(current: dict[str, Any], previous_wait: dict[str, Any] | None) -> dict[str, Any]:
    if not previous_wait:
        return current
    if previous_wait.get("event_key") != stage_event_key(
        str(current.get("task_id") or previous_wait.get("task_id")),
        current,
        str(previous_wait.get("remote_sha") or ""),
    ):
        return current
    merged = dict(current)
    for key in (
        "external_wait_started_utc",
        "external_wait_deadline_utc",
        "expected_state_or_artifact",
    ):
        if merged.get(key) is None and previous_wait.get(key) is not None:
            merged[key] = previous_wait[key]
    return merged


def evaluate_stage_event(
    *,
    task_id: str,
    request: dict[str, Any],
    current: dict[str, Any],
    visual_final: dict[str, Any] | None,
    remote_sha: str,
    processed: set[str],
    default_wait_hours: int,
    care_ase_executor_complete: bool = False,
) -> dict[str, Any]:
    state = str(current.get("state"))
    event_key = stage_event_key(task_id, current, remote_sha)
    decision = "IGNORE"
    action = "none"
    failures: list[str] = []
    wait_current = current
    if request.get("enabled") is not True:
        decision = "IGNORE_DISABLED"
    elif stage_event_was_processed(event_key, processed):
        decision = "IGNORE_PROCESSED"
    elif state == "PLAN_REQUESTED":
        decision = "WAITING_FOR_EXTERNAL_GPT"
        action = "scheduled Planner initial planning"
        wait_current = update_wait_fields(
            current,
            remote_sha=remote_sha,
            expected="Scheduled Planner updates CURRENT to PLAN_READY_FOR_CRITIC or BLOCKED_VISUAL_SOURCES with a bound planning artifact.",
            default_hours=default_wait_hours,
        )
    elif state == "PLAN_READY_FOR_CRITIC":
        decision = "WAITING_FOR_EXTERNAL_GPT"
        action = "scheduled Critic direct repair and freeze"
        wait_current = update_wait_fields(
            current,
            remote_sha=remote_sha,
            expected="Scheduled Critic updates CURRENT to PLAN_FROZEN, NEEDS_USER_SCIENTIFIC_CHOICE, or BLOCKED_VISUAL_SOURCES with a bound freeze artifact.",
            default_hours=default_wait_hours,
        )
    elif state == "WAITING_FOR_EXTERNAL_GPT":
        deadline_raw = current.get("external_wait_deadline_utc")
        if not isinstance(deadline_raw, str):
            failures.append("external_wait_deadline_utc")
            decision = "INVALID_EVENT"
        elif datetime.now(timezone.utc) >= parse_utc(deadline_raw):
            decision = "STOPPED_DEADLINE"
            action = "deadline_elapsed_without_expected_external_gpt_state"
        else:
            decision = "WAITING_FOR_EXTERNAL_GPT"
            action = str(current.get("expected_state_or_artifact") or "external GPT artifact")
    elif state in REVISION_STATES:
        decision = "HANDOFF_TO_WATCHER"
        action = "existing watcher resumes exact role sessions"
    elif state == "READY_FOR_PLANNER_REVIEW":
        decision = "WAITING_FOR_EXTERNAL_GPT"
        action = "scheduled Planner review"
        wait_current = update_wait_fields(
            current,
            remote_sha=remote_sha,
            expected="Scheduled Planner returns PLANNER_PASS or a bound PLANNER_REVISE_* artifact for the current integration SHA.",
            default_hours=default_wait_hours,
        )
    elif task_id == "gpt-loop-smoke-b" and state == "PLANNER_PASS":
        decision = "CONTROLLER_UPDATE_REQUIRED"
        action = "validate Smoke B Planner PASS artifact, write gpt_loop_smoke_final PASS, then arm care-ase-faithful"
    elif state in {"PLANNER_PASS", "AWAIT_HUMAN_DECISION"}:
        decision = "STOP_AT_HUMAN_GATE"
        action = "no automatic main merge, training, outer, Docker, upload or organizer email"
    elif task_id == "care-visual-smoke" and state == "PLAN_FROZEN":
        if visual_final and visual_final.get("status") == "PASS" and visual_final.get("supersedes_prior_blocked_status") is True:
            decision = "STAGE_READY"
            action = "visual smoke passed; prepare Smoke B"
        else:
            decision = "CONTROLLER_UPDATE_REQUIRED"
            action = "write visual_smoke_final PASS from validated Planner/Critic/freeze receipts"
    elif task_id == "care-ase-faithful" and state == "PLAN_FROZEN":
        decision = "STAGE_READY"
        action = "start persistent CARE-ASE Controller only; do not implement in orchestrator"
    elif task_id == "care-ase-faithful" and state == "VERIFIER_RUNNING":
        decision = "CONTROLLER_UPDATE_REQUIRED"
        action = "validate and integrate Verifier freeze commit, then mark VERIFIER_FROZEN"
    elif task_id == "care-ase-faithful" and state == "VERIFIER_FROZEN":
        if care_ase_executor_complete:
            decision = "CONTROLLER_UPDATE_REQUIRED"
            action = "validate and integrate Executor implementation commit, then enter WAITING_FOR_EXTERNAL_GPT"
        else:
            decision = "STAGE_READY"
            action = "start persistent CARE-ASE Executor exact session after Verifier freeze"
    else:
        decision = "MONITOR_ONLY"
        action = f"observed state {state}"
    return {
        "task_id": task_id,
        "state": state,
        "event_key": event_key,
        "decision": decision,
        "action": action,
        "failures": failures,
        "request_nonce": current.get("request_nonce"),
        "review_round": current.get("review_round"),
        "remote_sha": remote_sha,
        "external_wait_started_utc": wait_current.get("external_wait_started_utc"),
        "external_wait_deadline_utc": wait_current.get("external_wait_deadline_utc"),
        "expected_state_or_artifact": wait_current.get("expected_state_or_artifact"),
        "last_observed_remote_sha": remote_sha,
        "last_poll_utc": wait_current.get("last_poll_utc") or now(),
        "updated_utc": wait_current.get("updated_utc") or now(),
        "default_external_wait_hours": default_wait_hours,
    }


def apply_smoke_b_pass_controller_update(repo: Path, branch: str) -> dict[str, Any]:
    head_before = ensure_clean_ff_to_remote(repo, branch)
    activation = activate_care_ase_after_smoke_b(
        repo=repo,
        branch=branch,
        ref="HEAD",
        activation_nonce="care-ase-" + now().replace(":", "").replace("-", ""),
        dry_run=False,
    )
    commit_result = commit_and_push(
        repo,
        branch,
        activation["updated_paths"],
        "automation: arm care ase after smoke b pass",
    )
    return {
        "status": "APPLIED",
        "head_before_update": head_before,
        "activation": activation,
        "commit": commit_result,
        "updated_utc": now(),
    }


def visual_source_sha_map(visual_sources: dict[str, Any]) -> dict[str, str]:
    return {
        str(source["name"]): str(source["sha256"])
        for source in visual_sources.get("sources", [])
        if isinstance(source, dict) and isinstance(source.get("name"), str) and isinstance(source.get("sha256"), str)
    }


def validate_care_ase_plan_frozen_for_controller_start(
    repo: Path,
    ref: str,
    request: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if request.get("enabled") is not True:
        failures.append("request_enabled")
    if request.get("task_id") != "care-ase-faithful" or current.get("task_id") != "care-ase-faithful":
        failures.append("task_id")
    if current.get("state") != "PLAN_FROZEN":
        failures.append("current_state")
    if current.get("request_nonce") != request.get("request_nonce"):
        failures.append("request_nonce")
    if current.get("critic_decision") != "PLAN_FROZEN":
        failures.append("critic_decision")
    frozen_contract_path = str(current.get("frozen_contract_path") or request.get("frozen_contract_path") or "")
    frozen_contract_sha = str(current.get("frozen_contract_sha256") or "")
    if not frozen_contract_path:
        failures.append("frozen_contract_path")
    if frozen_contract_sha != request.get("frozen_contract_sha256"):
        failures.append("frozen_contract_request_binding")
    contract_payload = git_show_bytes_or_none(repo, ref, frozen_contract_path) if frozen_contract_path else None
    if contract_payload is None:
        failures.append("frozen_contract_missing")
    elif sha_bytes(contract_payload) != frozen_contract_sha:
        failures.append("frozen_contract_sha256")

    visual_sources_path = str(request.get("visual_sources_path") or "automation/agent_flow_v3/tasks/care-ase-faithful/VISUAL_SOURCES.json")
    try:
        visual_sources = git_show_json(repo, ref, visual_sources_path)
        expected_shas = visual_source_sha_map(visual_sources)
    except Exception as exc:  # noqa: BLE001 - preserve exact validation failure for receipt.
        expected_shas = {}
        failures.append(f"visual_sources:{type(exc).__name__}")

    freeze_path = str(current.get("critic_freeze_receipt_path") or "")
    freeze_raw = git_show_text_or_none(repo, ref, freeze_path) if freeze_path else None
    if not freeze_path:
        failures.append("critic_freeze_receipt_path")
    if freeze_raw is None:
        failures.append("critic_freeze_receipt_missing")
    else:
        freeze_sha = sha_bytes(freeze_raw.encode("utf-8"))
        if freeze_sha != current.get("critic_freeze_receipt_sha256"):
            failures.append("critic_freeze_receipt_sha256")
        try:
            freeze = json.loads(freeze_raw)
            if not isinstance(freeze, dict):
                raise ValueError("not object")
            failures.extend(
                "critic_freeze:" + failure
                for failure in validate_critic_freeze_receipt(
                    freeze,
                    expected_task_id="care-ase-faithful",
                    request_nonce=str(current.get("request_nonce") or ""),
                    expected_contract_sha=frozen_contract_sha,
                    expected_visual_receipt_commit_sha=str(current.get("critic_visual_receipt_commit_sha") or ""),
                    expected_shas=expected_shas,
                )
            )
        except Exception as exc:  # noqa: BLE001 - preserve exact validation failure for receipt.
            failures.append(f"critic_freeze_unreadable:{type(exc).__name__}:{exc}")
    return failures


def build_care_ase_controller_start_prompt(
    *,
    repo: Path,
    ref: str,
    request: dict[str, Any],
    current: dict[str, Any],
) -> bytes:
    contract_path = str(current.get("frozen_contract_path") or request.get("frozen_contract_path"))
    contract_text = git_show_text_or_none(repo, ref, contract_path) or ""
    prompt = f"""/goal You are the CARE Agent-Flow v3 Controller for care-ase-faithful.

Read and obey the current repository rules and protocol before acting:
- AGENTS.md
- START_HERE_FOR_GPT.md
- GPT_PLANNER_CARE_PROTOCOL.md
- prompts/AGENT_FLOW_V3_PROTOCOL.md
- prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json
- automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json
- automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json
- automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md

Current verified state:
- task_id: care-ase-faithful
- request_nonce: {current.get("request_nonce")}
- integration_branch: develop
- CURRENT.state: {current.get("state")}
- frozen_contract_sha256: {current.get("frozen_contract_sha256")}
- critic_decision: {current.get("critic_decision")}

Your role is Controller only. This is an execution turn, not a planning turn. You may coordinate, verify, integrate, commit, and push develop when the protocol authorizes it. You must not directly edit Executor implementation files or Verifier test files.

Required immediate action in this turn:
1. Verify the same PLAN_FROZEN bindings above from origin/develop.
2. Start or resume the independent Verifier exact thread from prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json.
3. Send the Verifier a precise prompt requiring fail-closed tests and a frozen verifier contract before any Executor implementation starts.
4. Record a durable Verifier launch receipt at /users/a/e/aereinh/.agent-flow-v3/care-ase-faithful/verifier_launch_receipt.json and a lightweight repository receipt under results/agent_flow_v3/care-ase-faithful/.
5. If the Verifier cannot be started, write a fail-closed receipt with the concrete cause before ending.

After Verifier freezes real tests, start the independent Executor. Preserve exact role separation, use the configured role worktrees and CODEX_HOME values, and record thread IDs, prompts, commits, CI, and state transitions under results/agent_flow_v3/care-ase-faithful/.

Do not end this turn with only "I will" or a plan. Either the Verifier exact thread is started and recorded, or a concrete fail-closed launch receipt exists.

Forbidden for this goal: training, outer access, Docker build/upload, validation/challenge upload, organizer email, develop-to-main merge, hand-written Planner/Critic decisions, fake receipts, --last resume, and TUI key injection.

Frozen contract follows. Treat it as binding source text, not as optional guidance.

```markdown
{contract_text}
```
"""
    return prompt.encode("utf-8")


def ensure_role_worktree_current(worktree: Path, branch: str) -> str:
    if not worktree.is_dir():
        raise RuntimeErrorV3(f"controller_worktree_missing:{worktree}")
    if git_status_short(worktree):
        raise RuntimeErrorV3(f"controller_worktree_dirty:{worktree}")
    git(worktree, "fetch", "origin", branch, "--prune")
    git(worktree, "merge", "--ff-only", f"origin/{branch}")
    return git(worktree, "rev-parse", "HEAD")


def start_care_ase_controller_from_frozen_contract(
    *,
    args: argparse.Namespace,
    repo: Path,
    ref: str,
    request: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    failures = validate_care_ase_plan_frozen_for_controller_start(repo, ref, request, current)
    state_root = args.state_root.resolve().parent
    receipt_path = care_ase_controller_start_receipt_path(args.state_root)
    task_state_dir = state_root / "care-ase-faithful"
    task_state_dir.mkdir(parents=True, exist_ok=True)
    target = tmux_target(args.controller_tmux_session, args.controller_tmux_window)
    if failures:
        receipt = {
            "schema": CONTROLLER_START_RECEIPT_SCHEMA,
            "status": "INVALID_PLAN_FROZEN",
            "task_id": "care-ase-faithful",
            "request_nonce": current.get("request_nonce"),
            "frozen_contract_sha256": current.get("frozen_contract_sha256"),
            "failures": failures,
            "target": target,
            "updated_utc": now(),
        }
        write_json(receipt_path, receipt)
        raise RuntimeErrorV3("care_ase_controller_start_invalid:" + ",".join(failures))

    role_plan = load_json((repo / args.controller_role_plan).resolve())
    controller = dict(role_plan.get("roles", {}).get("controller", {}))
    worktree = Path(str(controller.get("worktree", "")))
    codex_home = str(controller.get("codex_home", ""))
    thread_file = Path(str(controller.get("thread_id_file", "")))
    thread_id = thread_file.read_text(encoding="utf-8").strip() if thread_file.is_file() else ""
    command = build_controller_start_command(args.codex_bin, worktree, thread_id)
    prompt_payload = build_care_ase_controller_start_prompt(repo=repo, ref=ref, request=request, current=current)
    prompt_sha = sha_bytes(prompt_payload)
    stamp = now().replace(":", "").replace("-", "")
    prompt_path = task_state_dir / f"controller_start_prompt_{stamp}.md"
    stdout_path = task_state_dir / f"controller_start_{stamp}.stdout.log"
    stderr_path = task_state_dir / f"controller_start_{stamp}.stderr.log"
    prompt_path.write_bytes(prompt_payload)

    head_after_ff = ensure_role_worktree_current(worktree, args.branch)
    shell_command = (
        f"CODEX_HOME={shlex.quote(codex_home)} "
        f"CODEX_PERSISTENT_HOME={shlex.quote(codex_home)} "
        f"CODEX_HOME_OVERRIDE={shlex.quote(codex_home)} "
        "CODEX_RESPECT_CODEX_HOME=1 "
        "CODEX_USE_RUNTIME_HOME=0 "
        "CODEX_RESPECT_REPO_ROOT=1 "
        f"CODEX_REPO_ROOT={shlex.quote(str(worktree))} "
        f"{shlex.join(command)} "
        f"< {shlex.quote(str(prompt_path))} "
        f"> {shlex.quote(str(stdout_path))} "
        f"2> {shlex.quote(str(stderr_path))}"
    )

    if tmux_window_exists(args.controller_tmux_session, args.controller_tmux_window) and process_has_child(tmux_pane_pid(args.controller_tmux_session, args.controller_tmux_window)):
        pane_pid = tmux_pane_pid(args.controller_tmux_session, args.controller_tmux_window)
        status = "ALREADY_RUNNING"
    else:
        if tmux_window_exists(args.controller_tmux_session, args.controller_tmux_window):
            subprocess.run(["tmux", "kill-window", "-t", target], check=False)
        if subprocess.run(["tmux", "has-session", "-t", args.controller_tmux_session], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode != 0:
            tmux_cmd = ["tmux", "new-session", "-d", "-s", args.controller_tmux_session, "-n", args.controller_tmux_window, shell_command]
        else:
            tmux_cmd = ["tmux", "new-window", "-d", "-t", args.controller_tmux_session, "-n", args.controller_tmux_window, shell_command]
        subprocess.check_call(tmux_cmd)
        time.sleep(1)
        pane_pid = tmux_pane_pid(args.controller_tmux_session, args.controller_tmux_window)
        status = "STARTED"

    receipt = {
        "schema": CONTROLLER_START_RECEIPT_SCHEMA,
        "status": status,
        "task_id": "care-ase-faithful",
        "request_nonce": current.get("request_nonce"),
        "frozen_contract_sha256": current.get("frozen_contract_sha256"),
        "target": target,
        "pane_pid": pane_pid,
        "thread_id": thread_id,
        "codex_home": codex_home,
        "worktree": str(worktree),
        "worktree_head_after_ff": head_after_ff,
        "command": shell_command,
        "prompt_path": str(prompt_path),
        "prompt_sha256": prompt_sha,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "failures": [],
        "forbidden_actions_confirmed": [
            "no Planner/Critic decision generated",
            "no Verifier/Executor source modified by orchestrator",
            "no --last resume",
            "no TUI key injection",
            "no training, outer, Docker, upload, organizer email or develop-to-main merge",
        ],
        "updated_utc": now(),
    }
    write_json(receipt_path, receipt)
    write_json(active_process_path(state_root, "care-ase-faithful", "controller"), {**receipt, "pid": pane_pid, "exit_code": None})
    return receipt


def build_care_ase_verifier_start_prompt(current: dict[str, Any]) -> bytes:
    prompt = f"""/goal You are the independent Verifier for CARE Agent-Flow v3 task care-ase-faithful.

This is an execution turn. Do not stop with a plan.

Read and obey:
- AGENTS.md
- prompts/AGENT_FLOW_V3_PROTOCOL.md
- prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json
- automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json
- automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json
- automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md

Current binding:
- request_nonce: {current.get("request_nonce")}
- frozen_contract_sha256: {current.get("frozen_contract_sha256")}
- CURRENT.state: {current.get("state")}

Your required output is a real fail-closed Verifier freeze before any Executor implementation starts. You may edit only tests, validators, automation/agent_flow_v3, and results/agent_flow_v3/care-ase-faithful/verification as allowed by the role plan. You must not edit src, scripts/training, scripts/inference, jobs, configs, blueprints, or the frozen contract.

Write and run deterministic tests/validators that fail on protected known-bad cases from section 15 of FROZEN_CONTRACT.md. Produce verification_contract.json, public_test_manifest.json, protected_known_bad_manifest.json, verifier_fingerprint.json, and verifier_session_receipt.json under results/agent_flow_v3/care-ase-faithful/verification or the task receipt root as appropriate. Commit your verifier-only changes on the verifier local branch. Do not push develop; Controller owns integration/push.

Forbidden: no CARE-ASE implementation edits, no training, no outer access, no Docker, no upload, no organizer email, no Planner/Critic decision fabrication, no --last, no TUI key injection.

If you cannot complete the Verifier freeze, write a fail-closed receipt with the concrete cause before ending.
"""
    return prompt.encode("utf-8")


def previous_role_launch_failed_no_rollout(stage_state_root: Path, role: str) -> bool:
    receipt_path = care_ase_role_launch_receipt_path(stage_state_root, role)
    if not receipt_path.is_file():
        return False
    try:
        receipt = load_json(receipt_path)
    except RuntimeErrorV3:
        return False
    text = " ".join(str(receipt.get(key, "")) for key in ("status", "failure_reason", "stderr_excerpt"))
    previous = receipt.get("previous_attempt")
    if isinstance(previous, dict):
        text += " " + str(previous.get("stderr_summary", ""))
    stderr_log = receipt.get("stderr_log")
    if isinstance(stderr_log, str) and stderr_log:
        stderr_path = Path(stderr_log)
        if stderr_path.is_file():
            text += " " + stderr_path.read_text(encoding="utf-8", errors="replace")[-1000:]
    return "no rollout found" in text


def create_initial_role_thread(
    *,
    codex_bin: str,
    worktree: Path,
    codex_home: str,
    role: str,
    thread_file: Path,
) -> dict[str, Any]:
    prompt = (
        f"Initialize the CARE Agent-Flow v3 {role} session for care-ase-faithful. "
        "Do not run tools and do not edit files. Reply exactly SESSION_READY."
    )
    command = [codex_bin, "exec", "--json", "-C", str(worktree), "-"]
    env = role_codex_env(codex_home, worktree)
    started = now()
    cp = subprocess.run(
        command,
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(worktree),
        check=False,
        timeout=120,
    )
    thread_id = ""
    for line in cp.stdout.decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            thread_id = event["thread_id"]
            break
    if cp.returncode != 0 or not thread_id:
        raise RuntimeErrorV3(
            f"{role}:initial_thread_create_failed:{cp.returncode}:"
            f"{cp.stderr.decode('utf-8', 'replace')[:200]}"
        )
    rollout_paths = role_rollout_paths(Path(codex_home), thread_id)
    if not rollout_paths:
        raise RuntimeErrorV3(f"{role}:initial_thread_missing_rollout")
    thread_file.parent.mkdir(parents=True, exist_ok=True)
    thread_file.write_text(thread_id + "\n", encoding="utf-8")
    return {
        "status": "CREATED",
        "role": role,
        "thread_id": thread_id,
        "command": shlex.join(command),
        "codex_home": codex_home,
        "worktree": str(worktree),
        "rollout_session_path": str(rollout_paths[0]),
        "prompt_sha256": sha_bytes(prompt.encode("utf-8")),
        "started_utc": started,
        "finished_utc": now(),
    }


def start_care_ase_verifier_from_frozen_contract(
    *,
    args: argparse.Namespace,
    repo: Path,
    ref: str,
    request: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    failures = validate_care_ase_plan_frozen_for_controller_start(repo, ref, request, current)
    state_root = args.state_root.resolve().parent
    receipt_path = care_ase_role_launch_receipt_path(args.state_root, "verifier")
    task_state_dir = state_root / "care-ase-faithful"
    task_state_dir.mkdir(parents=True, exist_ok=True)
    target = tmux_target(args.verifier_tmux_session, args.verifier_tmux_window)
    if failures:
        receipt = {
            "schema": CONTROLLER_START_RECEIPT_SCHEMA,
            "status": "INVALID_PLAN_FROZEN",
            "task_id": "care-ase-faithful",
            "role": "verifier",
            "request_nonce": current.get("request_nonce"),
            "frozen_contract_sha256": current.get("frozen_contract_sha256"),
            "failures": failures,
            "target": target,
            "updated_utc": now(),
        }
        write_json(receipt_path, receipt)
        raise RuntimeErrorV3("care_ase_verifier_start_invalid:" + ",".join(failures))

    role_plan = load_json((repo / args.controller_role_plan).resolve())
    verifier = dict(role_plan.get("roles", {}).get("verifier", {}))
    worktree = Path(str(verifier.get("worktree", "")))
    codex_home = str(verifier.get("codex_home", ""))
    thread_file = Path(str(verifier.get("thread_id_file", "")))
    thread_id = thread_file.read_text(encoding="utf-8").strip() if thread_file.is_file() else ""
    thread_initialization = None
    if not thread_id or previous_role_launch_failed_no_rollout(args.state_root, "verifier"):
        thread_initialization = create_initial_role_thread(
            codex_bin=args.codex_bin,
            worktree=worktree,
            codex_home=codex_home,
            role="verifier",
            thread_file=thread_file,
        )
        thread_id = str(thread_initialization["thread_id"])
    command = build_controller_start_command(args.codex_bin, worktree, thread_id)
    prompt_payload = build_care_ase_verifier_start_prompt(current)
    prompt_sha = sha_bytes(prompt_payload)
    stamp = now().replace(":", "").replace("-", "")
    prompt_path = task_state_dir / f"verifier_start_prompt_{stamp}.md"
    stdout_path = task_state_dir / f"verifier_start_{stamp}.stdout.log"
    stderr_path = task_state_dir / f"verifier_start_{stamp}.stderr.log"
    prompt_path.write_bytes(prompt_payload)

    head_after_ff = ensure_role_worktree_current(worktree, args.branch)
    shell_command = (
        f"CODEX_HOME={shlex.quote(codex_home)} "
        f"CODEX_PERSISTENT_HOME={shlex.quote(codex_home)} "
        f"CODEX_HOME_OVERRIDE={shlex.quote(codex_home)} "
        "CODEX_RESPECT_CODEX_HOME=1 "
        "CODEX_USE_RUNTIME_HOME=0 "
        "CODEX_RESPECT_REPO_ROOT=1 "
        f"CODEX_REPO_ROOT={shlex.quote(str(worktree))} "
        f"{shlex.join(command)} "
        f"< {shlex.quote(str(prompt_path))} "
        f"> {shlex.quote(str(stdout_path))} "
        f"2> {shlex.quote(str(stderr_path))}"
    )

    if tmux_window_exists(args.verifier_tmux_session, args.verifier_tmux_window) and process_has_child(tmux_pane_pid(args.verifier_tmux_session, args.verifier_tmux_window)):
        pane_pid = tmux_pane_pid(args.verifier_tmux_session, args.verifier_tmux_window)
        status = "ALREADY_RUNNING"
    else:
        if tmux_window_exists(args.verifier_tmux_session, args.verifier_tmux_window):
            subprocess.run(["tmux", "kill-window", "-t", target], check=False)
        if subprocess.run(["tmux", "has-session", "-t", args.verifier_tmux_session], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode != 0:
            tmux_cmd = ["tmux", "new-session", "-d", "-s", args.verifier_tmux_session, "-n", args.verifier_tmux_window, shell_command]
        else:
            tmux_cmd = ["tmux", "new-window", "-d", "-t", args.verifier_tmux_session, "-n", args.verifier_tmux_window, shell_command]
        subprocess.check_call(tmux_cmd)
        time.sleep(1)
        pane_pid = tmux_pane_pid(args.verifier_tmux_session, args.verifier_tmux_window)
        status = "STARTED"

    receipt = {
        "schema": CONTROLLER_START_RECEIPT_SCHEMA,
        "status": status,
        "task_id": "care-ase-faithful",
        "role": "verifier",
        "request_nonce": current.get("request_nonce"),
        "frozen_contract_sha256": current.get("frozen_contract_sha256"),
        "target": target,
        "pane_pid": pane_pid,
        "thread_id": thread_id,
        "thread_initialization": thread_initialization,
        "codex_home": codex_home,
        "worktree": str(worktree),
        "worktree_head_after_ff": head_after_ff,
        "command": shell_command,
        "prompt_path": str(prompt_path),
        "prompt_sha256": prompt_sha,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "failures": [],
        "forbidden_actions_confirmed": [
            "no Planner/Critic decision generated",
            "no implementation source modified by orchestrator",
            "no --last resume",
            "no TUI key injection",
            "no training, outer, Docker, upload, organizer email or develop-to-main merge",
        ],
        "updated_utc": now(),
    }
    write_json(receipt_path, receipt)
    write_json(active_process_path(state_root, "care-ase-faithful", "verifier"), {**receipt, "pid": pane_pid, "exit_code": None})
    return receipt


def care_ase_verifier_freeze_relpath() -> str:
    return "results/agent_flow_v3/care-ase-faithful/verification/verifier_freeze_receipt.json"


def validate_care_ase_verifier_freeze(
    *,
    verifier_worktree: Path,
    verifier_head: str,
    request: dict[str, Any],
    current: dict[str, Any],
    role_data: dict[str, Any],
    branch: str,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    if git_status_short(verifier_worktree):
        failures.append(f"verifier_worktree_dirty:{verifier_worktree}")
    if not SHA40_RE.fullmatch(verifier_head):
        failures.append("verifier_head_sha")
    merge_base = git(verifier_worktree, "merge-base", f"origin/{branch}", verifier_head)
    changed_paths = [
        line
        for line in git(verifier_worktree, "diff", "--name-only", f"{merge_base}..{verifier_head}").splitlines()
        if line
    ]
    failures.extend(validate_role_commit_scope(changed_paths, role_data))
    freeze_rel = care_ase_verifier_freeze_relpath()
    freeze_raw = git_show_text_or_none(verifier_worktree, verifier_head, freeze_rel)
    if freeze_raw is None:
        failures.append("verifier_freeze_receipt_missing")
        freeze: dict[str, Any] = {}
    else:
        try:
            freeze = json.loads(freeze_raw)
            if not isinstance(freeze, dict):
                raise ValueError("not object")
        except Exception as exc:  # noqa: BLE001 - receipt must preserve validation problem.
            freeze = {}
            failures.append(f"verifier_freeze_receipt_unreadable:{type(exc).__name__}:{exc}")
    if freeze:
        if freeze.get("schema") != "CARE_ASE_FAITHFUL_VERIFIER_FREEZE_RECEIPT_V1":
            failures.append("verifier_freeze_schema")
        if freeze.get("task_id") != "care-ase-faithful":
            failures.append("verifier_freeze_task_id")
        if freeze.get("request_nonce") != request.get("request_nonce") or freeze.get("request_nonce") != current.get("request_nonce"):
            failures.append("verifier_freeze_nonce")
        if freeze.get("frozen_contract_sha256") != request.get("frozen_contract_sha256"):
            failures.append("verifier_freeze_contract_sha")
        if freeze.get("state_for_controller") != "VERIFIER_FROZEN":
            failures.append("verifier_freeze_state_for_controller")
        if freeze.get("executor_may_start_after_controller_freezes_this_commit") is not True:
            failures.append("verifier_freeze_executor_gate")
        if freeze.get("protected_known_bad_count") != 24:
            failures.append("verifier_freeze_known_bad_count")
        if freeze.get("protected_known_bad_all_nonzero") is not True:
            failures.append("verifier_freeze_known_bad_nonzero")
        fingerprint_rel = "results/agent_flow_v3/care-ase-faithful/verification/verifier_fingerprint.json"
        fingerprint_raw = git_show_text_or_none(verifier_worktree, verifier_head, fingerprint_rel)
        if fingerprint_raw is None:
            failures.append("verifier_fingerprint_missing")
        else:
            try:
                fingerprint = json.loads(fingerprint_raw)
                if not isinstance(fingerprint, dict):
                    raise ValueError("not object")
                if fingerprint.get("fingerprint_sha256") != freeze.get("verifier_fingerprint_sha256"):
                    failures.append("verifier_fingerprint_binding")
                if fingerprint.get("request_nonce") != request.get("request_nonce"):
                    failures.append("verifier_fingerprint_nonce")
                if fingerprint.get("frozen_contract_sha256") != request.get("frozen_contract_sha256"):
                    failures.append("verifier_fingerprint_contract_sha")
            except Exception as exc:  # noqa: BLE001
                failures.append(f"verifier_fingerprint_unreadable:{type(exc).__name__}:{exc}")
    return failures, {
        "verifier_head": verifier_head,
        "merge_base": merge_base,
        "changed_paths": changed_paths,
        "freeze": freeze,
        "freeze_relpath": freeze_rel,
    }


def apply_care_ase_verifier_freeze_controller_update(
    *,
    args: argparse.Namespace,
    repo: Path,
    request: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    role_plan = load_json((repo / args.controller_role_plan).resolve())
    verifier = dict(role_plan.get("roles", {}).get("verifier", {}))
    verifier_worktree = Path(str(verifier.get("worktree", "")))
    git(verifier_worktree, "fetch", "origin", args.branch, "--prune")
    verifier_head = git(verifier_worktree, "rev-parse", "HEAD")
    failures, freeze_status = validate_care_ase_verifier_freeze(
        verifier_worktree=verifier_worktree,
        verifier_head=verifier_head,
        request=request,
        current=current,
        role_data=verifier,
        branch=args.branch,
    )
    if failures:
        raise RuntimeErrorV3("care_ase_verifier_freeze_invalid:" + ",".join(failures))

    head_before = ensure_clean_ff_to_remote(repo, args.branch)
    subprocess.check_call(
        ["git", "merge", "--no-ff", "-m", "verification: integrate care ase verifier freeze", verifier_head],
        cwd=repo,
    )
    integration_merge_sha = git(repo, "rev-parse", "HEAD")
    freeze_rel = str(freeze_status["freeze_relpath"])
    freeze = dict(freeze_status["freeze"])
    current_path = repo / "automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json"
    updated_current = load_json(current_path)
    updated_current.update(
        {
            "state": "VERIFIER_FROZEN",
            "verifier_fingerprint_sha256": freeze.get("verifier_fingerprint_sha256"),
            "verifier_freeze_receipt_path": freeze_rel,
            "verifier_freeze_receipt_sha256": sha_file(repo / freeze_rel),
            "verifier_freeze_receipt_commit_sha": git(repo, "log", "-1", "--format=%H", "HEAD", "--", freeze_rel),
            "verifier_branch_head_sha": verifier_head,
            "verifier_integration_merge_sha": integration_merge_sha,
            "next_action": "START_EXECUTOR_AFTER_VERIFIER_FREEZE",
            "updated_utc": now(),
        }
    )
    write_json(current_path, updated_current)
    integration_receipt_path = repo / "results/agent_flow_v3/care-ase-faithful/verifier_integration_receipt.json"
    integration_receipt = {
        "schema": "CARE_AGENT_FLOW_V3_VERIFIER_INTEGRATION_RECEIPT",
        "task_id": "care-ase-faithful",
        "request_nonce": current.get("request_nonce"),
        "frozen_contract_sha256": current.get("frozen_contract_sha256"),
        "head_before_update": head_before,
        "verifier_branch_head_sha": verifier_head,
        "verifier_merge_base": freeze_status.get("merge_base"),
        "integration_merge_sha": integration_merge_sha,
        "verifier_fingerprint_sha256": freeze.get("verifier_fingerprint_sha256"),
        "changed_paths": freeze_status.get("changed_paths"),
        "state_after_integration": "VERIFIER_FROZEN",
        "forbidden_actions_confirmed": [
            "no Planner/Critic decision generated",
            "no implementation source modified by controller integration",
            "no training, outer, Docker, upload, organizer email or develop-to-main merge",
        ],
        "updated_utc": now(),
    }
    write_json(integration_receipt_path, integration_receipt)
    commit_result = commit_and_push(
        repo,
        args.branch,
        [
            "automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json",
            "results/agent_flow_v3/care-ase-faithful/verifier_integration_receipt.json",
        ],
        "automation: mark care ase verifier frozen",
    )
    return {
        "status": "APPLIED",
        "verifier_validation": freeze_status,
        "integration_receipt_path": str(integration_receipt_path),
        "commit": commit_result,
        "updated_utc": now(),
    }


def validate_care_ase_verifier_frozen_for_executor_start(
    repo: Path,
    ref: str,
    request: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if request.get("enabled") is not True:
        failures.append("request_enabled")
    if current.get("state") != "VERIFIER_FROZEN":
        failures.append("current_state")
    if current.get("request_nonce") != request.get("request_nonce"):
        failures.append("request_nonce")
    if current.get("frozen_contract_sha256") != request.get("frozen_contract_sha256"):
        failures.append("frozen_contract_sha256")
    freeze_path = str(current.get("verifier_freeze_receipt_path") or care_ase_verifier_freeze_relpath())
    freeze_raw = git_show_text_or_none(repo, ref, freeze_path)
    if freeze_raw is None:
        failures.append("verifier_freeze_receipt_missing")
        return failures
    freeze_sha = sha_bytes(freeze_raw.encode("utf-8"))
    if current.get("verifier_freeze_receipt_sha256") and freeze_sha != current.get("verifier_freeze_receipt_sha256"):
        failures.append("verifier_freeze_receipt_sha256")
    try:
        freeze = json.loads(freeze_raw)
        if not isinstance(freeze, dict):
            raise ValueError("not object")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"verifier_freeze_receipt_unreadable:{type(exc).__name__}:{exc}")
        return failures
    if freeze.get("state_for_controller") != "VERIFIER_FROZEN":
        failures.append("verifier_freeze_state")
    if freeze.get("executor_may_start_after_controller_freezes_this_commit") is not True:
        failures.append("verifier_freeze_executor_gate")
    if freeze.get("verifier_fingerprint_sha256") != current.get("verifier_fingerprint_sha256"):
        failures.append("verifier_fingerprint_sha256")
    return failures


def build_care_ase_executor_start_prompt(current: dict[str, Any]) -> bytes:
    prompt = f"""/goal You are the independent Executor for CARE Agent-Flow v3 task care-ase-faithful.

This is an implementation turn in the isolated Executor worktree. Read and obey:
- AGENTS.md
- START_HERE_FOR_GPT.md
- GPT_PLANNER_CARE_PROTOCOL.md
- prompts/AGENT_FLOW_V3_PROTOCOL.md
- prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json
- automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json
- automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json
- automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md
- results/agent_flow_v3/care-ase-faithful/verification/verifier_freeze_receipt.json
- results/agent_flow_v3/care-ase-faithful/verification/verification_contract.json

Current verified binding:
- request_nonce: {current.get("request_nonce")}
- frozen_contract_sha256: {current.get("frozen_contract_sha256")}
- verifier_fingerprint_sha256: {current.get("verifier_fingerprint_sha256")}
- CURRENT.state: {current.get("state")}

Implement CARE-ASE faithfully against the frozen contract and the Verifier package. You may edit only the Executor role write scope: src, scripts/training, scripts/inference, jobs, configs, and results/agent_flow_v3/care-ase-faithful/implementation. You must not edit tests, validators, automation schema, blueprints, Planner/Critic artifacts, or the frozen contract.

Do not train, access outer data, build or upload Docker, upload validation/challenge results, send organizer email, hand-write Planner/Critic decisions, use --last, or use TUI key injection. Commit implementation-only changes on the local Executor branch. Do not push develop; Controller owns integration and push.

If implementation cannot proceed under the contract, write a fail-closed implementation receipt with the concrete cause before ending.
"""
    return prompt.encode("utf-8")


def start_care_ase_executor_from_verifier_freeze(
    *,
    args: argparse.Namespace,
    repo: Path,
    ref: str,
    request: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    failures = validate_care_ase_verifier_frozen_for_executor_start(repo, ref, request, current)
    state_root = args.state_root.resolve().parent
    receipt_path = care_ase_role_launch_receipt_path(args.state_root, "executor")
    task_state_dir = state_root / "care-ase-faithful"
    task_state_dir.mkdir(parents=True, exist_ok=True)
    target = tmux_target(args.executor_tmux_session, args.executor_tmux_window)
    if failures:
        receipt = {
            "schema": CONTROLLER_START_RECEIPT_SCHEMA,
            "status": "INVALID_VERIFIER_FROZEN",
            "task_id": "care-ase-faithful",
            "role": "executor",
            "request_nonce": current.get("request_nonce"),
            "frozen_contract_sha256": current.get("frozen_contract_sha256"),
            "failures": failures,
            "target": target,
            "updated_utc": now(),
        }
        write_json(receipt_path, receipt)
        raise RuntimeErrorV3("care_ase_executor_start_invalid:" + ",".join(failures))

    role_plan = load_json((repo / args.controller_role_plan).resolve())
    executor = dict(role_plan.get("roles", {}).get("executor", {}))
    worktree = Path(str(executor.get("worktree", "")))
    codex_home = str(executor.get("codex_home", ""))
    thread_file = Path(str(executor.get("thread_id_file", "")))
    thread_id = thread_file.read_text(encoding="utf-8").strip() if thread_file.is_file() else ""
    thread_initialization = None
    if not thread_id or previous_role_launch_failed_no_rollout(args.state_root, "executor"):
        thread_initialization = create_initial_role_thread(
            codex_bin=args.codex_bin,
            worktree=worktree,
            codex_home=codex_home,
            role="executor",
            thread_file=thread_file,
        )
        thread_id = str(thread_initialization["thread_id"])
    command = build_controller_start_command(args.codex_bin, worktree, thread_id)
    prompt_payload = build_care_ase_executor_start_prompt(current)
    prompt_sha = sha_bytes(prompt_payload)
    stamp = now().replace(":", "").replace("-", "")
    prompt_path = task_state_dir / f"executor_start_prompt_{stamp}.md"
    stdout_path = task_state_dir / f"executor_start_{stamp}.stdout.log"
    stderr_path = task_state_dir / f"executor_start_{stamp}.stderr.log"
    prompt_path.write_bytes(prompt_payload)

    head_after_ff = ensure_role_worktree_current(worktree, args.branch)
    shell_command = (
        f"CODEX_HOME={shlex.quote(codex_home)} "
        f"CODEX_PERSISTENT_HOME={shlex.quote(codex_home)} "
        f"CODEX_HOME_OVERRIDE={shlex.quote(codex_home)} "
        "CODEX_RESPECT_CODEX_HOME=1 "
        "CODEX_USE_RUNTIME_HOME=0 "
        "CODEX_RESPECT_REPO_ROOT=1 "
        f"CODEX_REPO_ROOT={shlex.quote(str(worktree))} "
        f"{shlex.join(command)} "
        f"< {shlex.quote(str(prompt_path))} "
        f"> {shlex.quote(str(stdout_path))} "
        f"2> {shlex.quote(str(stderr_path))}"
    )

    if tmux_window_exists(args.executor_tmux_session, args.executor_tmux_window) and process_has_child(tmux_pane_pid(args.executor_tmux_session, args.executor_tmux_window)):
        pane_pid = tmux_pane_pid(args.executor_tmux_session, args.executor_tmux_window)
        status = "ALREADY_RUNNING"
    else:
        if tmux_window_exists(args.executor_tmux_session, args.executor_tmux_window):
            subprocess.run(["tmux", "kill-window", "-t", target], check=False)
        if subprocess.run(["tmux", "has-session", "-t", args.executor_tmux_session], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode != 0:
            tmux_cmd = ["tmux", "new-session", "-d", "-s", args.executor_tmux_session, "-n", args.executor_tmux_window, shell_command]
        else:
            tmux_cmd = ["tmux", "new-window", "-d", "-t", args.executor_tmux_session, "-n", args.executor_tmux_window, shell_command]
        subprocess.check_call(tmux_cmd)
        time.sleep(1)
        pane_pid = tmux_pane_pid(args.executor_tmux_session, args.executor_tmux_window)
        status = "STARTED"

    receipt = {
        "schema": CONTROLLER_START_RECEIPT_SCHEMA,
        "status": status,
        "task_id": "care-ase-faithful",
        "role": "executor",
        "request_nonce": current.get("request_nonce"),
        "frozen_contract_sha256": current.get("frozen_contract_sha256"),
        "verifier_fingerprint_sha256": current.get("verifier_fingerprint_sha256"),
        "target": target,
        "pane_pid": pane_pid,
        "thread_id": thread_id,
        "thread_initialization": thread_initialization,
        "codex_home": codex_home,
        "worktree": str(worktree),
        "worktree_head_after_ff": head_after_ff,
        "command": shell_command,
        "prompt_path": str(prompt_path),
        "prompt_sha256": prompt_sha,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "failures": [],
        "forbidden_actions_confirmed": [
            "no Planner/Critic decision generated",
            "no verifier source modified by orchestrator",
            "no --last resume",
            "no TUI key injection",
            "no training, outer, Docker, upload, organizer email or develop-to-main merge",
        ],
        "updated_utc": now(),
    }
    write_json(receipt_path, receipt)
    write_json(active_process_path(state_root, "care-ase-faithful", "executor"), {**receipt, "pid": pane_pid, "exit_code": None})
    return receipt


def run_controller_gate(name: str, command: list[str], *, repo: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "name": name,
        "command": shlex.join(command),
        "exit_code": int(completed.returncode),
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def load_care_ase_executor_binding(args: argparse.Namespace, current: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], Path, str, str]:
    role_plan = load_json((args.repo_root.resolve() / args.controller_role_plan).resolve())
    executor = dict(role_plan.get("roles", {}).get("executor", {}))
    worktree = Path(str(executor.get("worktree", "")))
    codex_home = str(executor.get("codex_home", ""))
    thread_file = Path(str(executor.get("thread_id_file", "")))
    thread_id = thread_file.read_text(encoding="utf-8").strip() if thread_file.is_file() else ""
    current_thread = str(current.get("executor_production_thread_id") or current.get("executor_thread_id") or "")
    if current_thread and thread_id and current_thread != thread_id:
        raise RuntimeErrorV3("executor_thread_id_current_mismatch")
    return role_plan, executor, worktree, codex_home, thread_id


def care_ase_executor_completion_available(args: argparse.Namespace, current: dict[str, Any]) -> bool:
    try:
        _, _, worktree, codex_home, thread_id = load_care_ase_executor_binding(args, current)
    except RuntimeErrorV3:
        return False
    if not worktree.is_dir() or not thread_id:
        return False
    if role_rollout_goal_complete(codex_home, thread_id) is None:
        return False
    if git_status_short(worktree):
        return False
    executor_head = git(worktree, "rev-parse", "HEAD")
    origin_ref = f"origin/{args.branch}"
    subprocess.run(["git", "fetch", "origin", args.branch, "--prune"], cwd=worktree, check=False)
    merge_base = git(worktree, "merge-base", origin_ref, executor_head)
    if merge_base == executor_head:
        return False
    validation_path = worktree / "results/agent_flow_v3/care-ase-faithful/implementation/implementation_evidence_validation_result.json"
    if not validation_path.is_file():
        return False
    try:
        validation = load_json(validation_path)
    except RuntimeErrorV3:
        return False
    return validation.get("passed") is True and validation.get("failure_count") == 0


def validate_care_ase_executor_completion(
    *,
    args: argparse.Namespace,
    request: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    role_plan, executor, worktree, codex_home, thread_id = load_care_ase_executor_binding(args, current)
    failures = validate_role_plan_push_authority(role_plan)
    if request.get("enabled") is not True:
        failures.append("request_enabled")
    if current.get("state") != "VERIFIER_FROZEN":
        failures.append("current_state")
    if current.get("request_nonce") != request.get("request_nonce"):
        failures.append("request_nonce")
    if current.get("frozen_contract_sha256") != request.get("frozen_contract_sha256"):
        failures.append("frozen_contract_sha256")
    if not worktree.is_dir():
        failures.append("executor_worktree_missing")
    if not thread_id:
        failures.append("executor_thread_id")
    if failures:
        raise RuntimeErrorV3("care_ase_executor_completion_invalid:" + ",".join(failures))

    git(worktree, "fetch", "origin", args.branch, "--prune")
    executor_head = git(worktree, "rev-parse", "HEAD")
    origin_ref = f"origin/{args.branch}"
    merge_base = git(worktree, "merge-base", origin_ref, executor_head)
    changed_paths = git(worktree, "diff", "--name-only", f"{merge_base}..{executor_head}").splitlines()
    scope_failures = validate_role_commit_scope(changed_paths, executor)
    status = git_status_short(worktree)
    if status:
        scope_failures.append("executor_worktree_dirty")
    if merge_base == executor_head:
        scope_failures.append("executor_no_local_commit")

    goal_complete = role_rollout_goal_complete(codex_home, thread_id)
    if goal_complete is None:
        scope_failures.append("executor_goal_not_complete")

    implementation_dir = worktree / "results/agent_flow_v3/care-ase-faithful/implementation"
    validation = load_json(implementation_dir / "implementation_evidence_validation_result.json")
    fingerprint = load_json(implementation_dir / "implementation_fingerprint.json")
    evidence = load_json(implementation_dir / "implementation_evidence.json")
    source_manifest = load_json(implementation_dir / "implementation_source_manifest.json")
    if validation.get("passed") is not True or validation.get("failure_count") != 0:
        scope_failures.append("implementation_validation_failed")
    if fingerprint.get("frozen_contract_sha256") != current.get("frozen_contract_sha256"):
        scope_failures.append("fingerprint_frozen_contract_sha256")
    if fingerprint.get("request_nonce") != current.get("request_nonce"):
        scope_failures.append("fingerprint_request_nonce")
    if fingerprint.get("verifier_fingerprint_sha256") != current.get("verifier_fingerprint_sha256"):
        scope_failures.append("fingerprint_verifier_fingerprint_sha256")
    if evidence.get("source_manifest_sha256") != fingerprint.get("source_manifest_sha256"):
        scope_failures.append("evidence_source_manifest_sha256")
    if source_manifest.get("frozen_contract_sha256") != current.get("frozen_contract_sha256"):
        scope_failures.append("source_manifest_frozen_contract_sha256")
    if source_manifest.get("request_nonce") != current.get("request_nonce"):
        scope_failures.append("source_manifest_request_nonce")

    if scope_failures:
        raise RuntimeErrorV3("care_ase_executor_completion_invalid:" + ",".join(scope_failures))
    return {
        "executor_head": executor_head,
        "executor_commit_subject": git_commit_subject(worktree, executor_head),
        "merge_base": merge_base,
        "changed_paths": changed_paths,
        "thread_id": thread_id,
        "codex_home": codex_home,
        "worktree": str(worktree),
        "goal_complete": goal_complete,
        "implementation_fingerprint_sha256": fingerprint.get("implementation_fingerprint_sha256"),
        "implementation_evidence_sha256": evidence.get("implementation_evidence_sha256"),
        "source_manifest_sha256": fingerprint.get("source_manifest_sha256"),
        "implementation_fingerprint_file_sha256": sha_file(implementation_dir / "implementation_fingerprint.json"),
        "implementation_evidence_file_sha256": sha_file(implementation_dir / "implementation_evidence.json"),
        "implementation_source_manifest_file_sha256": sha_file(implementation_dir / "implementation_source_manifest.json"),
        "runtime_asset_manifest_file_sha256": sha_file(implementation_dir / "runtime_asset_manifest.json"),
        "validation_result_file_sha256": sha_file(implementation_dir / "implementation_evidence_validation_result.json"),
    }


def apply_care_ase_executor_completion_controller_update(
    *,
    args: argparse.Namespace,
    repo: Path,
    request: dict[str, Any],
    current: dict[str, Any],
    remote_sha: str,
) -> dict[str, Any]:
    completion = validate_care_ase_executor_completion(args=args, request=request, current=current)
    origin_ref = f"origin/{args.branch}"
    repo_head = git(repo, "rev-parse", "HEAD")
    executor_already_merged = subprocess.run(
        ["git", "merge-base", "--is-ancestor", str(completion["executor_head"]), repo_head],
        cwd=repo,
        check=False,
    ).returncode == 0
    origin_already_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", origin_ref, repo_head],
        cwd=repo,
        check=False,
    ).returncode == 0
    if executor_already_merged and origin_already_ancestor and repo_head != git(repo, "rev-parse", origin_ref):
        if git_status_short(repo):
            raise RuntimeErrorV3("worktree_not_clean_after_existing_executor_merge")
        head_before = remote_sha
        merge_candidates = git(repo, "rev-list", "--merges", "--reverse", f"{origin_ref}..{repo_head}").splitlines()
        integration_merge_sha = merge_candidates[-1] if merge_candidates else repo_head
    else:
        head_before = ensure_clean_ff_to_remote(repo, args.branch)
        subprocess.check_call(
            ["git", "merge", "--no-ff", "-m", "implementation: integrate care ase faithful round 0 repair", completion["executor_head"]],
            cwd=repo,
        )
        integration_merge_sha = git(repo, "rev-parse", "HEAD")

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["CARE_ROOT"] = str(repo)
    care_python = "/users/a/e/aereinh/CARE/envs/env_CARE/bin/python"
    local_gates = [
        run_controller_gate(
            "agent_flow_v3_contract_validation",
            [sys.executable, "scripts/automation/validate_agent_flow_v3.py", "--repo-root", "."],
            repo=repo,
            env=env,
        ),
        run_controller_gate(
            "frozen_verifier_validate_implementation_evidence",
            [
                care_python,
                "validators/care_ase_faithful/validate_contract_evidence.py",
                "--verification-contract",
                "results/agent_flow_v3/care-ase-faithful/verification/verification_contract.json",
                "--evidence",
                "results/agent_flow_v3/care-ase-faithful/implementation/implementation_evidence.json",
                "--report-json",
                "results/agent_flow_v3/care-ase-faithful/implementation/frozen_verifier_validation_result.json",
            ],
            repo=repo,
            env=env,
        ),
        run_controller_gate(
            "py_compile_integrated_sources",
            [
                care_python,
                "-m",
                "py_compile",
                "scripts/training/care_ase/build_care_ase_faithful_implementation_evidence.py",
                "src/care_myocardium/models/care_ase/__init__.py",
                "src/care_myocardium/models/care_ase/core.py",
                "src/care_myocardium/training/care_ase_runtime.py",
                "src/care_myocardium/training/care_ase_trainer.py",
            ],
            repo=repo,
            env=env,
        ),
        run_controller_gate(
            "public_verifier_pytest",
            [care_python, "-m", "pytest", "tests/care_ase_faithful/test_verifier_package.py", "-q"],
            repo=repo,
            env=env,
        ),
    ]
    gate_failures = [gate["name"] for gate in local_gates if gate["exit_code"] != 0]
    if gate_failures:
        raise RuntimeErrorV3("care_ase_executor_local_gates_failed:" + ",".join(gate_failures))

    integration_receipt_path = repo / "results/agent_flow_v3/care-ase-faithful/controller_integration_receipt.json"
    ci_receipt_path = repo / "results/agent_flow_v3/care-ase-faithful/controller_ci_receipt.json"
    planner_packet_path = repo / "results/agent_flow_v3/care-ase-faithful/planner_review_packet.json"
    integration_receipt = {
        "schema": "CARE_ASE_FAITHFUL_CONTROLLER_INTEGRATION_RECEIPT_V2",
        "task_id": "care-ase-faithful",
        "request_nonce": current.get("request_nonce"),
        "created_utc": now(),
        "state_transition": {
            "from": "VERIFIER_FROZEN",
            "through": ["INTEGRATION_RUNNING", "CI_RUNNING", "READY_FOR_PLANNER_REVIEW"],
            "to": "WAITING_FOR_EXTERNAL_GPT",
        },
        "frozen_contract_sha256": current.get("frozen_contract_sha256"),
        "origin_develop_before_integration_sha": head_before,
        "last_observed_remote_sha_before_integration": remote_sha,
        "executor_thread_id": completion.get("thread_id"),
        "executor_local_commit_sha": completion.get("executor_head"),
        "executor_local_commit_subject": completion.get("executor_commit_subject"),
        "executor_merge_base": completion.get("merge_base"),
        "executor_goal_complete": completion.get("goal_complete"),
        "integration_merge_sha": integration_merge_sha,
        "verifier_fingerprint_sha256": current.get("verifier_fingerprint_sha256"),
        "verifier_freeze_receipt_commit_sha": current.get("verifier_freeze_receipt_commit_sha"),
        "implementation_fingerprint_sha256": completion.get("implementation_fingerprint_sha256"),
        "implementation_evidence_payload_sha256": completion.get("implementation_evidence_sha256"),
        "source_manifest_sha256": completion.get("source_manifest_sha256"),
        "implementation_fingerprint_file_sha256": completion.get("implementation_fingerprint_file_sha256"),
        "implementation_evidence_file_sha256": completion.get("implementation_evidence_file_sha256"),
        "implementation_source_manifest_file_sha256": completion.get("implementation_source_manifest_file_sha256"),
        "runtime_asset_manifest_file_sha256": completion.get("runtime_asset_manifest_file_sha256"),
        "implementation_validation_result_file_sha256": completion.get("validation_result_file_sha256"),
        "local_controller_gates": local_gates,
        "role_separation_review": {
            "controller_direct_implementation_edits": False,
            "controller_direct_verifier_test_edits": False,
            "executor_changed_tests_or_validators": False,
            "executor_commit_paths_reviewed": True,
            "changed_paths": completion.get("changed_paths"),
        },
        "supersedes_prior_executor_status": current.get("executor_status"),
        "supersedes_prior_executor_commits": [
            current.get("executor_original_commit_sha"),
            current.get("executor_retry_commit_sha"),
            current.get("executor_integrated_retry_commit_sha"),
        ],
        "forbidden_actions": {
            "formal_training_started": False,
            "outer_accessed": False,
            "docker_built_or_uploaded": False,
            "validation_or_challenge_uploaded": False,
            "organizer_email_sent": False,
            "develop_to_main_merge": False,
            "planner_or_critic_decision_generated": False,
        },
        "updated_utc": now(),
    }
    write_json(integration_receipt_path, integration_receipt)
    wait_started = now()
    wait_deadline_value = wait_deadline(wait_started, max(4, int(args.default_wait_hours)))
    ci_receipt = {
        "schema": "CARE_ASE_FAITHFUL_CONTROLLER_CI_RECEIPT_V2",
        "task_id": "care-ase-faithful",
        "request_nonce": current.get("request_nonce"),
        "created_utc": now(),
        "checked_commit_sha": integration_merge_sha,
        "local_gates_status": "PASS",
        "local_gates": local_gates,
        "github_actions_status": "PENDING_AFTER_PUSH",
        "workflow_path": ".github/workflows/agent-flow-v3-ci.yml",
    }
    write_json(ci_receipt_path, ci_receipt)
    planner_packet = {
        "schema": "CARE_ASE_FAITHFUL_PLANNER_REVIEW_PACKET_V2",
        "task_id": "care-ase-faithful",
        "request_nonce": current.get("request_nonce"),
        "created_utc": now(),
        "decision_requested": "PLANNER_REVIEW",
        "current_state_after_commit": "WAITING_FOR_EXTERNAL_GPT",
        "ready_state_reached_before_wait": "READY_FOR_PLANNER_REVIEW",
        "frozen_contract_sha256": current.get("frozen_contract_sha256"),
        "verifier_fingerprint_sha256": current.get("verifier_fingerprint_sha256"),
        "executor_thread_id": completion.get("thread_id"),
        "executor_local_commit_sha": completion.get("executor_head"),
        "controller_integration_merge_sha": integration_merge_sha,
        "implementation_fingerprint_sha256": completion.get("implementation_fingerprint_sha256"),
        "controller_integration_receipt": str(integration_receipt_path.relative_to(repo)),
        "controller_ci_receipt": str(ci_receipt_path.relative_to(repo)),
        "local_gates": "PASS",
        "ci_for_integration_state": "PENDING_AFTER_PUSH",
        "planner_allowed_decisions": sorted({"PLANNER_REVISE_EXECUTOR", "PLANNER_REVISE_VERIFIER", "PLANNER_REVISE_BOTH", "PLANNER_PASS"}),
    }
    write_json(planner_packet_path, planner_packet)
    current_path = repo / "automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json"
    updated_current = load_json(current_path)
    updated_current.update(
        {
            "state": "WAITING_FOR_EXTERNAL_GPT",
            "ready_state_reached_before_wait": "READY_FOR_PLANNER_REVIEW",
            "review_round": int(current.get("review_round", 0)) + 1,
            "planner_decision": None,
            "planner_review_artifact": None,
            "planner_review_artifact_commit_sha": None,
            "repair_prompt_path": None,
            "repair_prompts": {},
            "integration_commit_sha": integration_merge_sha,
            "executor_thread_id": completion.get("thread_id"),
            "executor_production_thread_id": completion.get("thread_id"),
            "executor_local_commit_sha": completion.get("executor_head"),
            "executor_integration_merge_sha": integration_merge_sha,
            "implementation_fingerprint_sha256": completion.get("implementation_fingerprint_sha256"),
            "controller_integration_receipt_path": str(integration_receipt_path.relative_to(repo)),
            "controller_integration_receipt_sha256": sha_file(integration_receipt_path),
            "controller_ci_receipt_path": str(ci_receipt_path.relative_to(repo)),
            "controller_ci_receipt_sha256": sha_file(ci_receipt_path),
            "planner_review_packet_path": str(planner_packet_path.relative_to(repo)),
            "planner_review_packet_sha256": sha_file(planner_packet_path),
            "controller_local_gates_status": "PASS",
            "ci_status": "PENDING_AFTER_PUSH",
            "external_wait_started_utc": wait_started,
            "external_wait_deadline_utc": wait_deadline_value,
            "expected_state_or_artifact": "Scheduled Planner returns PLANNER_PASS or bound PLANNER_REVISE_* artifact for the current integration SHA and review_round 1.",
            "last_observed_remote_sha": remote_sha,
            "last_poll_utc": now(),
            "next_action": "KEEP_FETCHING_ORIGIN_DEVELOP_UNTIL_SCHEDULED_PLANNER_REVIEW_ARRIVES",
            "updated_utc": now(),
        }
    )
    write_json(current_path, updated_current)
    commit_result = commit_and_push(
        repo,
        args.branch,
        [
            "automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json",
            "results/agent_flow_v3/care-ase-faithful/controller_integration_receipt.json",
            "results/agent_flow_v3/care-ase-faithful/controller_ci_receipt.json",
            "results/agent_flow_v3/care-ase-faithful/planner_review_packet.json",
            "results/agent_flow_v3/care-ase-faithful/implementation/frozen_verifier_validation_result.json",
        ],
        "automation: integrate care ase executor repair",
    )
    task_state_root = args.state_root.resolve().parent
    executor_active = active_process_path(task_state_root, "care-ase-faithful", "executor")
    if executor_active.is_file():
        try:
            active_data = load_json(executor_active)
            active_data.update(
                {
                    "exit_code": 0,
                    "finished_utc": now(),
                    "completion_detected_via_rollout": True,
                    "os_process_still_present_at_completion_receipt_update": True,
                    "goal_complete_rollout_path": completion.get("goal_complete", {}).get("rollout_path"),
                    "completed_executor_commit_sha": completion.get("executor_head"),
                    "controller_integration_commit_sha": commit_result.get("commit_sha"),
                }
            )
            write_json(executor_active, active_data)
        except RuntimeErrorV3:
            pass
    return {
        "status": "APPLIED",
        "completion": completion,
        "integration_receipt_path": str(integration_receipt_path),
        "ci_receipt_path": str(ci_receipt_path),
        "planner_review_packet_path": str(planner_packet_path),
        "commit": commit_result,
        "external_wait_started_utc": wait_started,
        "external_wait_deadline_utc": wait_deadline_value,
        "updated_utc": now(),
    }


def stage_event_should_mark_processed(event: dict[str, Any]) -> bool:
    if event.get("decision") == "STOP_AT_HUMAN_GATE":
        return True
    if event.get("decision") != "STAGE_READY":
        return False
    return not (
        event.get("task_id") == "care-ase-faithful"
        and event.get("state") in {"PLAN_FROZEN", "VERIFIER_FROZEN"}
    )


def run_orchestrator_cycle_without_lock(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo_root.resolve()
    git(repo, "fetch", "origin", args.branch, "--prune")
    ref = f"origin/{args.branch}"
    remote_sha = remote_head(repo, args.branch)
    state_path = args.state_root.resolve() / "stage_orchestrator_state.json"
    local_state = load_orchestrator_state(state_path)
    processed = set(local_state.get("processed_events", []))
    task_events: list[dict[str, Any]] = []
    for request_path in remote_task_request_paths(repo, ref):
        task_dir = str(Path(request_path).parent)
        current_path = f"{task_dir}/CURRENT.json"
        request = git_show_json(repo, ref, request_path)
        current = git_show_json(repo, ref, current_path)
        task_id = str(request.get("task_id") or current.get("task_id") or Path(task_dir).name)
        current.setdefault("task_id", task_id)
        current = merge_existing_wait_metadata(
            current,
            dict(local_state.get("waits", {})).get(task_id),
        )
        event_key = stage_event_key(task_id, current, remote_sha)
        care_ase_executor_complete = False
        if task_id == "care-ase-faithful" and current.get("state") == "VERIFIER_FROZEN":
            care_ase_executor_complete = care_ase_executor_completion_available(args, current)
        if (
            task_id == "care-ase-faithful"
            and current.get("state") == "PLAN_FROZEN"
            and stage_event_was_processed(event_key, processed)
            and not care_ase_controller_start_satisfied(args.state_root, current)
        ):
            processed = {key for key in processed if not key.startswith(event_key)}
        if (
            task_id == "care-ase-faithful"
            and current.get("state") == "VERIFIER_FROZEN"
            and stage_event_was_processed(event_key, processed)
            and not care_ase_role_launch_satisfied(args.state_root, current, "executor")
        ):
            processed = {key for key in processed if not key.startswith(event_key)}
        if (
            task_id == "care-ase-faithful"
            and current.get("state") == "VERIFIER_FROZEN"
            and stage_event_was_processed(event_key, processed)
            and care_ase_executor_complete
        ):
            processed = {key for key in processed if not key.startswith(event_key)}
        visual_final = None
        visual_final_path = f"results/agent_flow_v3/{task_id}/visual_smoke_final.json"
        raw_visual_final = git_show_text_or_none(repo, ref, visual_final_path)
        if raw_visual_final:
            try:
                parsed = json.loads(raw_visual_final)
                if isinstance(parsed, dict):
                    visual_final = parsed
            except json.JSONDecodeError:
                visual_final = None
        event = evaluate_stage_event(
            task_id=task_id,
            request=request,
            current=current,
            visual_final=visual_final,
            remote_sha=remote_sha,
            processed=processed,
            default_wait_hours=max(4, int(args.default_wait_hours)),
            care_ase_executor_complete=care_ase_executor_complete,
        )
        if stage_event_should_mark_processed(event):
            processed.add(event["event_key"])
        elif (
            event["decision"] == "STAGE_READY"
            and task_id == "care-ase-faithful"
            and event["state"] == "PLAN_FROZEN"
        ):
            action_failures: list[str] = []
            try:
                event["action_result"] = start_care_ase_controller_from_frozen_contract(
                    args=args,
                    repo=repo,
                    ref=ref,
                    request=request,
                    current=current,
                )
            except Exception as exc:  # noqa: BLE001 - controller dirtiness must not block Verifier launch.
                action_failures.append("controller_start_failed")
                event["action_result"] = {
                    "status": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                    "updated_utc": now(),
                }
            if not care_ase_role_launch_satisfied(args.state_root, current, "verifier"):
                try:
                    event["verifier_action_result"] = start_care_ase_verifier_from_frozen_contract(
                        args=args,
                        repo=repo,
                        ref=ref,
                        request=request,
                        current=current,
                    )
                except Exception as exc:  # noqa: BLE001 - keep polling; do not mark failed start processed.
                    action_failures.append("verifier_start_failed")
                    event["verifier_action_result"] = {
                        "status": "FAILED",
                        "error": f"{type(exc).__name__}: {exc}",
                        "updated_utc": now(),
                    }
            if care_ase_role_launch_satisfied(args.state_root, current, "verifier"):
                event["decision"] = "CONTROLLER_START_APPLIED"
                event["action"] = "PLAN_FROZEN validated; Verifier exact session active or frozen"
                processed.add(event["event_key"])
            else:
                event["failures"] = list(event.get("failures", [])) + action_failures
        elif (
            event["decision"] == "CONTROLLER_UPDATE_REQUIRED"
            and task_id == "gpt-loop-smoke-b"
            and event["state"] == "PLANNER_PASS"
        ):
            try:
                event["action_result"] = apply_smoke_b_pass_controller_update(repo, args.branch)
                event["decision"] = "CONTROLLER_UPDATE_APPLIED"
                event["action"] = "Smoke B PASS validated and care-ase-faithful armed by Controller automation"
                processed.add(event["event_key"])
                event["remote_sha_after_controller_update"] = remote_head(repo, args.branch)
            except Exception as exc:  # noqa: BLE001 - keep polling; do not mark failed update processed.
                event["action_result"] = {
                    "status": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                    "updated_utc": now(),
                }
                event["failures"] = list(event.get("failures", [])) + ["controller_update_failed"]
        elif (
            event["decision"] == "CONTROLLER_UPDATE_REQUIRED"
            and task_id == "care-ase-faithful"
            and event["state"] == "VERIFIER_RUNNING"
        ):
            try:
                event["action_result"] = apply_care_ase_verifier_freeze_controller_update(
                    args=args,
                    repo=repo,
                    request=request,
                    current=current,
                )
                event["decision"] = "CONTROLLER_UPDATE_APPLIED"
                event["action"] = "Verifier freeze validated, integrated, pushed, and CURRENT moved to VERIFIER_FROZEN"
                processed.add(event["event_key"])
                event["remote_sha_after_controller_update"] = remote_head(repo, args.branch)
            except Exception as exc:  # noqa: BLE001 - keep polling; do not fake verifier freeze.
                event["action_result"] = {
                    "status": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                    "updated_utc": now(),
                }
                event["failures"] = list(event.get("failures", [])) + ["verifier_freeze_integration_failed"]
        elif (
            event["decision"] == "CONTROLLER_UPDATE_REQUIRED"
            and task_id == "care-ase-faithful"
            and event["state"] == "VERIFIER_FROZEN"
        ):
            try:
                event["action_result"] = apply_care_ase_executor_completion_controller_update(
                    args=args,
                    repo=repo,
                    request=request,
                    current=current,
                    remote_sha=remote_sha,
                )
                event["decision"] = "CONTROLLER_UPDATE_APPLIED"
                event["action"] = "Executor commit validated, integrated, pushed, and CURRENT moved to WAITING_FOR_EXTERNAL_GPT"
                processed.add(event["event_key"])
                event["remote_sha_after_controller_update"] = remote_head(repo, args.branch)
            except Exception as exc:  # noqa: BLE001 - keep polling; do not fake Executor completion.
                event["action_result"] = {
                    "status": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                    "updated_utc": now(),
                }
                event["failures"] = list(event.get("failures", [])) + ["executor_integration_failed"]
        elif (
            event["decision"] == "STAGE_READY"
            and task_id == "care-ase-faithful"
            and event["state"] == "VERIFIER_FROZEN"
        ):
            try:
                event["action_result"] = start_care_ase_executor_from_verifier_freeze(
                    args=args,
                    repo=repo,
                    ref=ref,
                    request=request,
                    current=current,
                )
            except Exception as exc:  # noqa: BLE001 - keep polling; do not mark failed executor start processed.
                event["action_result"] = {
                    "status": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                    "updated_utc": now(),
                }
                event["failures"] = list(event.get("failures", [])) + ["executor_start_failed"]
            if care_ase_role_launch_satisfied(args.state_root, current, "executor"):
                event["decision"] = "EXECUTOR_START_APPLIED"
                event["action"] = "VERIFIER_FROZEN validated; Executor exact session active"
                processed.add(event["event_key"])
        task_events.append(event)
    receipt = {
        "schema": ORCHESTRATOR_RECEIPT_SCHEMA,
        "branch": args.branch,
        "remote_sha": remote_sha,
        "poll_seconds": args.poll_seconds,
        "task_events": task_events,
        "forbidden_actions_confirmed": [
            "no Planner/Critic decision generated",
            "no Verifier/Executor source modified",
            "no --last resume",
            "no TUI key injection",
            "no training, outer, Docker, upload, organizer email or develop-to-main merge",
        ],
        "updated_utc": now(),
    }
    new_state = {
        "schema": ORCHESTRATOR_STATE_SCHEMA,
        "processed_events": sorted(processed),
        "waits": dict(local_state.get("waits", {})),
        "last_receipt": receipt,
        "updated_utc": now(),
    }
    for event in task_events:
        if event["decision"] == "WAITING_FOR_EXTERNAL_GPT":
            new_state["waits"][event["task_id"]] = event
    write_json(state_path, new_state)
    if args.output:
        write_json(args.output, receipt)
    return receipt


def cmd_stage_orchestrator_once(args: argparse.Namespace) -> int:
    lock_path = args.state_root.resolve() / "stage_orchestrator.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock_fh:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeErrorV3("stage orchestrator flock is already held") from exc
        receipt = run_orchestrator_cycle_without_lock(args)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


def cmd_stage_orchestrator_watch(args: argparse.Namespace) -> int:
    lock_path = args.state_root.resolve() / "stage_orchestrator.lock"
    stop_path = args.state_root.resolve() / "stop_stage_orchestrator"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    cycles = 0
    with lock_path.open("a+") as lock_fh:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeErrorV3("stage orchestrator flock is already held") from exc
        while True:
            cycles += 1
            if stop_path.exists():
                return 0
            try:
                run_orchestrator_cycle_without_lock(args)
            except Exception as exc:  # noqa: BLE001 - long orchestrator must fail closed and keep polling.
                write_json(
                    args.state_root.resolve() / "stage_orchestrator_last_error.json",
                    {
                        "schema": ORCHESTRATOR_STATE_SCHEMA,
                        "error": f"{type(exc).__name__}: {exc}",
                        "updated_utc": now(),
                    },
                )
            if args.max_cycles and cycles >= args.max_cycles:
                return 0
            time.sleep(args.poll_seconds)


def cmd_start_stage_orchestrator(args: argparse.Namespace) -> int:
    stop_path = args.state_root.resolve() / "stop_stage_orchestrator"
    if stop_path.exists():
        stop_path.unlink()
    script = Path(__file__).resolve()
    command = [
        sys.executable,
        str(script),
        "stage-orchestrator-watch",
        "--repo-root",
        str(args.repo_root),
        "--branch",
        args.branch,
        "--state-root",
        str(args.state_root),
        "--poll-seconds",
        str(args.poll_seconds),
        "--default-wait-hours",
        str(args.default_wait_hours),
        "--output",
        str(args.output),
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


def cmd_stop_stage_orchestrator(args: argparse.Namespace) -> int:
    stop_path = args.state_root.resolve() / "stop_stage_orchestrator"
    stop_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.write_text(now() + "\n", encoding="utf-8")
    target = tmux_target(args.tmux_session, args.tmux_window)
    subprocess.run(["tmux", "kill-window", "-t", target], check=False)
    print(json.dumps({"status": "STOP_REQUESTED", "target": target, "stop_path": str(stop_path)}, indent=2))
    return 0


def cmd_status_stage_orchestrator(args: argparse.Namespace) -> int:
    target = tmux_target(args.tmux_session, args.tmux_window)
    tmux = subprocess.run(["tmux", "display-message", "-p", "-t", target, "#{pane_pid}|#{pane_current_command}"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    state_path = args.state_root.resolve() / "stage_orchestrator_state.json"
    status = {
        "schema": ORCHESTRATOR_STATE_SCHEMA,
        "target": target,
        "tmux_window_found": tmux.returncode == 0,
        "tmux_detail": tmux.stdout.strip() if tmux.returncode == 0 else tmux.stderr.strip(),
        "state_path": str(state_path),
        "state_exists": state_path.is_file(),
        "updated_utc": now(),
    }
    if state_path.is_file():
        status["state"] = load_json(state_path)
    if args.output:
        write_json(args.output, status)
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0


def validate_visual_smoke_receipt(
    receipt: dict[str, Any],
    *,
    expected_task_id: str,
    expected_role: str,
    request_nonce: str,
    expected_shas: dict[str, str],
    expected_source_manifest_path: str,
) -> list[str]:
    failures: list[str] = []
    if receipt.get("task_id") != expected_task_id:
        failures.append("task_id")
    expected_base_role = expected_role.split("_", 1)[0]
    if receipt.get("role") not in {expected_role, expected_base_role}:
        failures.append("role")
    if receipt.get("request_nonce") != request_nonce:
        failures.append("request_nonce")
    if receipt.get("source_manifest_path") != expected_source_manifest_path:
        failures.append("source_manifest_path")

    image_sha256 = receipt.get("image_sha256")
    if isinstance(image_sha256, dict):
        observed_shas = image_sha256
    else:
        observed_shas = {}
        images = receipt.get("images")
        if isinstance(images, list):
            for image in images:
                if isinstance(image, dict) and isinstance(image.get("name"), str):
                    observed_shas[image["name"]] = image.get("sha256")
    if not observed_shas:
        failures.append("image_sha256")
    else:
        for name, digest in expected_shas.items():
            if observed_shas.get(name) != digest:
                failures.append(f"image_sha256:{name}")

    answers = receipt.get("answers")
    required_answers = (
        "main_modules",
        "key_data_flow",
        "missing_modality_no_t2_safety",
        "explicitly_absent_components",
        "structural_differences",
    )
    if isinstance(answers, dict):
        answer_values = answers
    else:
        answer_values = {}
        images = receipt.get("images")
        if isinstance(images, list):
            answer_values["main_modules"] = " ".join(
                " ".join(str(item) for item in image.get("main_modules_visible", []))
                for image in images
                if isinstance(image, dict) and isinstance(image.get("main_modules_visible"), list)
            )
            answer_values["key_data_flow"] = " ".join(
                str(image.get("key_dataflow", ""))
                for image in images
                if isinstance(image, dict)
            )
            answer_values["missing_modality_no_t2_safety"] = " ".join(
                " ".join(str(item) for item in image.get("missing_modality_and_no_t2_rules", []))
                for image in images
                if isinstance(image, dict) and isinstance(image.get("missing_modality_and_no_t2_rules"), list)
            )
            answer_values["explicitly_absent_components"] = " ".join(
                " ".join(
                    str(item)
                    for item in (
                        image.get("explicitly_absent_components")
                        if isinstance(image.get("explicitly_absent_components"), list)
                        else image.get("explicitly_absent_from_figure", [])
                    )
                )
                for image in images
                if isinstance(image, dict)
                and (
                    isinstance(image.get("explicitly_absent_components"), list)
                    or isinstance(image.get("explicitly_absent_from_figure"), list)
                )
            )
        structural = receipt.get("structural_differences")
        if not isinstance(structural, list):
            structural = receipt.get("cross_architecture_judgment")
        if isinstance(structural, list):
            answer_values["structural_differences"] = " ".join(str(item) for item in structural)
    if not isinstance(answers, dict) and not answer_values:
        failures.append("answers")
    else:
        for key in required_answers:
            value = answer_values.get(key)
            if not isinstance(value, str) or len(value.strip()) < 20:
                failures.append(f"answers:{key}")

    provenance = receipt.get("provenance")
    access_context = str(receipt.get("access_context", "")).lower()
    scheduled_context = "scheduled" in access_context and ("gpt" in access_context or "chatgpt" in access_context)
    if not (
        isinstance(provenance, dict) and provenance.get("producer") == "scheduled_gpt"
    ) and not (
        receipt.get("actual_visual_access") is True and scheduled_context
    ):
        failures.append("provenance:scheduled_gpt")
    return failures


def validate_critic_freeze_receipt(
    receipt: dict[str, Any],
    *,
    expected_task_id: str,
    request_nonce: str,
    expected_contract_sha: str,
    expected_visual_receipt_commit_sha: str | None,
    expected_shas: dict[str, str],
) -> list[str]:
    failures: list[str] = []
    if receipt.get("task_id") != expected_task_id:
        failures.append("task_id")
    if receipt.get("request_nonce") != request_nonce:
        failures.append("request_nonce")
    if receipt.get("critic_decision") != "PLAN_FROZEN":
        failures.append("critic_decision")
    if receipt.get("frozen_contract_sha256") != expected_contract_sha:
        failures.append("frozen_contract_sha256")
    if expected_visual_receipt_commit_sha and receipt.get("critic_visual_receipt_commit_sha") != expected_visual_receipt_commit_sha:
        failures.append("critic_visual_receipt_commit_sha")
    reviewed = receipt.get("visual_sources_reviewed")
    if not isinstance(reviewed, list):
        failures.append("visual_sources_reviewed")
        return failures
    observed = {
        str(item.get("name")): item
        for item in reviewed
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    for name, digest in expected_shas.items():
        item = observed.get(name)
        if not item:
            failures.append(f"visual_sources_reviewed:{name}:missing")
            continue
        if item.get("sha256") != digest:
            failures.append(f"visual_sources_reviewed:{name}:sha256")
        if item.get("actual_visual_access") is not True:
            failures.append(f"visual_sources_reviewed:{name}:actual_visual_access")
    return failures


def validate_smoke_b_planner_pass(
    review: dict[str, Any],
    *,
    request: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if review.get("schema") != "CARE_AGENT_FLOW_V3_PLANNER_REVIEW":
        failures.append("schema")
    if review.get("task_id") != "gpt-loop-smoke-b":
        failures.append("task_id")
    if review.get("decision") != "PLANNER_PASS":
        failures.append("decision")
    if review.get("request_nonce") != current.get("request_nonce") or review.get("request_nonce") != request.get("request_nonce"):
        failures.append("request_nonce")
    if review.get("review_round") != current.get("review_round"):
        failures.append("review_round")
    for key in (
        "frozen_contract_sha256",
        "integration_commit_sha",
        "implementation_fingerprint_sha256",
        "verifier_fingerprint_sha256",
    ):
        if review.get(key) != current.get(key):
            failures.append(key)
    if current.get("state") != "PLANNER_PASS":
        failures.append("current_state")
    if current.get("planner_decision") not in {None, "PLANNER_PASS"}:
        failures.append("planner_decision")
    blocking = review.get("blocking_findings")
    if blocking not in (None, []):
        failures.append("blocking_findings")
    return failures


def build_smoke_b_final_receipt(
    *,
    request: dict[str, Any],
    current: dict[str, Any],
    review: dict[str, Any],
    review_path: str,
    review_commit_sha: str,
) -> dict[str, Any]:
    failures = validate_smoke_b_planner_pass(review, request=request, current=current)
    return {
        "schema": "CARE_AGENT_FLOW_V3_GPT_LOOP_SMOKE_FINAL",
        "task_id": "gpt-loop-smoke-b",
        "status": "PASS" if not failures else "FAIL",
        "request_nonce": current.get("request_nonce"),
        "review_round": current.get("review_round"),
        "planner_review_artifact": review_path,
        "planner_review_artifact_commit_sha": review_commit_sha,
        "planner_decision": review.get("decision"),
        "integration_commit_sha": current.get("integration_commit_sha"),
        "implementation_fingerprint_sha256": current.get("implementation_fingerprint_sha256"),
        "verifier_fingerprint_sha256": current.get("verifier_fingerprint_sha256"),
        "external_wait_started_utc": current.get("external_wait_started_utc"),
        "external_wait_deadline_utc": current.get("external_wait_deadline_utc"),
        "validated_bindings": not failures,
        "failures": failures,
        "forbidden_actions_confirmed": [
            "no Planner decision generated by Codex",
            "no CARE-ASE implementation started",
            "no training, outer, Docker, upload, organizer email or develop-to-main merge",
        ],
        "updated_utc": now(),
    }


def smoke_b_planner_review_candidates(current: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    review_round = current.get("review_round")
    if isinstance(review_round, int):
        candidates.append(f"results/agent_flow_v3/gpt-loop-smoke-b/planner_reviews/round_{review_round:03d}.json")
    artifact = current.get("planner_review_artifact")
    if isinstance(artifact, str):
        candidates.append(artifact)
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def prepare_care_ase_activation_after_smoke_b(
    *,
    request: dict[str, Any],
    current: dict[str, Any],
    visual_sources: dict[str, Any],
    visual_smoke_final: dict[str, Any],
    smoke_b_final: dict[str, Any],
    activation_nonce: str,
    frozen_contract_sha256: str | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    failures: list[str] = []
    if visual_smoke_final.get("status") != "PASS":
        failures.append("visual_smoke_final")
    if smoke_b_final.get("status") != "PASS":
        failures.append("smoke_b_final")
    if request.get("task_id") != "care-ase-faithful" or current.get("task_id") != "care-ase-faithful":
        failures.append("task_id")
    if not activation_nonce:
        failures.append("activation_nonce")
    if frozen_contract_sha256 is not None and not SHA256_RE.fullmatch(frozen_contract_sha256):
        failures.append("frozen_contract_sha256")

    armed_request = dict(request)
    armed_request.update(
        {
            "enabled": not failures,
            "request_nonce": activation_nonce,
            "frozen_contract_sha256": frozen_contract_sha256,
        }
    )
    armed_visual_sources = dict(visual_sources)
    armed_visual_sources["ready_for_scheduled_visual_review"] = not failures
    armed_visual_sources["activation_binding"] = {
        "visual_smoke_final_status": visual_smoke_final.get("status"),
        "visual_smoke_request_nonce": visual_smoke_final.get("request_nonce"),
        "gpt_loop_smoke_final_status": smoke_b_final.get("status"),
        "gpt_loop_smoke_request_nonce": smoke_b_final.get("request_nonce"),
        "activated_request_nonce": activation_nonce,
        "updated_utc": now(),
    }
    armed_current = {
        **current,
        "state": "PLAN_REQUESTED",
        "review_round": 0,
        "request_nonce": activation_nonce,
        "frozen_contract_sha256": frozen_contract_sha256,
        "integration_commit_sha": None,
        "implementation_fingerprint_sha256": None,
        "verifier_fingerprint_sha256": None,
        "next_action": "WAIT_FOR_TRUE_SCHEDULED_PLANNER_AND_CRITIC",
        "updated_utc": now(),
    }
    activation_state = {
        "schema": "CARE_AGENT_FLOW_V3_CARE_ASE_ACTIVATION_STATE",
        "task_id": "care-ase-faithful",
        "status": "ARMED" if not failures else "NOT_ARMED",
        "request_nonce": activation_nonce,
        "frozen_contract_sha256": frozen_contract_sha256,
        "visual_smoke_final_status": visual_smoke_final.get("status"),
        "gpt_loop_smoke_final_status": smoke_b_final.get("status"),
        "failures": failures,
        "forbidden_actions_confirmed": [
            "no CARE-ASE implementation started by activation",
            "no training, outer, Docker, upload, organizer email or develop-to-main merge",
        ],
        "updated_utc": now(),
    }
    return armed_request, armed_current, armed_visual_sources, activation_state, failures


def activate_care_ase_after_smoke_b(
    *,
    repo: Path,
    branch: str,
    ref: str,
    activation_nonce: str,
    dry_run: bool,
) -> dict[str, Any]:
    smoke_request_path = "automation/agent_flow_v3/tasks/gpt-loop-smoke-b/REQUEST.json"
    smoke_current_path = "automation/agent_flow_v3/tasks/gpt-loop-smoke-b/CURRENT.json"
    care_request_path = "automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json"
    care_current_path = "automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json"
    care_visual_sources_path = "automation/agent_flow_v3/tasks/care-ase-faithful/VISUAL_SOURCES.json"
    visual_final_path = "results/agent_flow_v3/care-visual-smoke/visual_smoke_final.json"
    smoke_final_path = "results/agent_flow_v3/gpt-loop-smoke-b/gpt_loop_smoke_final.json"
    activation_state_path = "results/agent_flow_v3/care-ase-faithful/care_ase_activation_state.json"

    smoke_request = git_show_json(repo, ref, smoke_request_path)
    smoke_current = git_show_json(repo, ref, smoke_current_path)
    care_request = git_show_json(repo, ref, care_request_path)
    care_current = git_show_json(repo, ref, care_current_path)
    visual_sources = git_show_json(repo, ref, care_visual_sources_path)
    visual_final = git_show_json(repo, ref, visual_final_path)

    review_path = ""
    review: dict[str, Any] | None = None
    for candidate in smoke_b_planner_review_candidates(smoke_current):
        raw = git_show_text_or_none(repo, ref, candidate)
        if raw is None:
            continue
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            review_path = candidate
            review = parsed
            break
    if review is None:
        raise RuntimeErrorV3("smoke_b_planner_pass_artifact_missing")
    review_commit_sha = git(repo, "log", "-1", "--format=%H", ref, "--", review_path)
    smoke_final = build_smoke_b_final_receipt(
        request=smoke_request,
        current=smoke_current,
        review=review,
        review_path=review_path,
        review_commit_sha=review_commit_sha,
    )
    if smoke_final["status"] != "PASS":
        raise RuntimeErrorV3("smoke_b_planner_pass_invalid:" + ",".join(smoke_final.get("failures", [])))

    activation_nonce = activation_nonce or "care-ase-" + now().replace(":", "").replace("-", "")
    frozen_contract_sha256 = care_request.get("frozen_contract_sha256")
    if frozen_contract_sha256 is not None:
        frozen_contract_sha256 = str(frozen_contract_sha256)
    armed_request, armed_current, armed_visual_sources, activation_state, failures = prepare_care_ase_activation_after_smoke_b(
        request=care_request,
        current=care_current,
        visual_sources=visual_sources,
        visual_smoke_final=visual_final,
        smoke_b_final=smoke_final,
        activation_nonce=activation_nonce,
        frozen_contract_sha256=frozen_contract_sha256,
    )
    if failures:
        raise RuntimeErrorV3("care_ase_activation_invalid:" + ",".join(failures))
    result = {
        "schema": "CARE_AGENT_FLOW_V3_CARE_ASE_ACTIVATION_COMMAND",
        "status": "DRY_RUN" if dry_run else "WROTE_FILES",
        "branch": branch,
        "source_ref": ref,
        "smoke_final_path": smoke_final_path,
        "activation_state_path": activation_state_path,
        "updated_paths": [
            smoke_final_path,
            care_visual_sources_path,
            care_request_path,
            care_current_path,
            activation_state_path,
        ],
        "request_nonce": activation_nonce,
        "updated_utc": now(),
    }
    if not dry_run:
        write_json(repo / smoke_final_path, smoke_final)
        write_json(repo / care_visual_sources_path, armed_visual_sources)
        write_json(repo / care_request_path, armed_request)
        write_json(repo / care_current_path, armed_current)
        write_json(repo / activation_state_path, activation_state)
    return result


def cmd_activate_care_ase_after_smoke_b(args: argparse.Namespace) -> int:
    repo = args.repo_root.resolve()
    if args.fetch:
        git(repo, "fetch", "origin", args.branch, "--prune")
    ref = f"origin/{args.branch}" if args.from_origin else "HEAD"
    result = activate_care_ase_after_smoke_b(
        repo=repo,
        branch=args.branch,
        ref=ref,
        activation_nonce=args.activation_nonce,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


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
                    expected_task_id=args.task_id,
                    expected_role=f"{role}_visual_smoke",
                    request_nonce=request_nonce,
                    expected_shas=expected_shas,
                    expected_source_manifest_path=args.visual_sources_path,
                )
                status["valid"] = not failures
                status["failures"] = failures
                status["commit_sha"] = git(repo, "log", "-1", "--format=%H", ref, "--", rel)
            except Exception as exc:  # noqa: BLE001 - receipt preserves validation problem.
                status["failures"] = [f"unreadable:{type(exc).__name__}:{exc}"]
        if not status["valid"]:
            all_failures.extend(f"{role}:{failure}" for failure in status["failures"] or ["missing"])
        receipt_status[role] = status

    freeze_rel = current.get("critic_freeze_receipt_path") or f"results/agent_flow_v3/{args.task_id}/critic_freeze_receipt.json"
    freeze_raw = git_show_text_or_none(repo, ref, str(freeze_rel))
    freeze_status: dict[str, Any] = {
        "path": str(freeze_rel),
        "exists": freeze_raw is not None,
        "valid": False,
        "failures": [],
    }
    if freeze_raw is not None:
        try:
            freeze = json.loads(freeze_raw)
            if not isinstance(freeze, dict):
                raise ValueError("not object")
            freeze_failures = validate_critic_freeze_receipt(
                freeze,
                expected_task_id=args.task_id,
                request_nonce=request_nonce,
                expected_contract_sha=str(request.get("frozen_contract_sha256") or ""),
                expected_visual_receipt_commit_sha=receipt_status["critic"].get("commit_sha"),
                expected_shas=expected_shas,
            )
            freeze_status["valid"] = not freeze_failures
            freeze_status["failures"] = freeze_failures
            freeze_status["commit_sha"] = git(repo, "log", "-1", "--format=%H", ref, "--", str(freeze_rel))
            freeze_status["critic_decision"] = freeze.get("critic_decision")
        except Exception as exc:  # noqa: BLE001 - receipt preserves validation problem.
            freeze_status["failures"] = [f"unreadable:{type(exc).__name__}:{exc}"]
    if not freeze_status["valid"]:
        all_failures.extend(f"critic_freeze:{failure}" for failure in freeze_status["failures"] or ["missing"])

    passed = not all_failures and completed_windows >= args.min_windows and current.get("state") == "PLAN_FROZEN"
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
        "scheduled_critic_freeze_receipt": freeze_status,
        "critic_decision": current.get("critic_decision"),
        "supersedes_prior_blocked_status": passed,
        "superseded_reason": "real Scheduled Critic visual and freeze receipts appeared on origin/develop after the earlier waiting snapshot" if passed else "",
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
    q.add_argument("--require-production", action="store_true")
    q.add_argument("--output", type=Path)
    q.set_defaults(func=cmd_validate_role_receipts)

    def add_watcher_args(q: argparse.ArgumentParser) -> None:
        q.add_argument("--repo-root", type=Path, required=True)
        q.add_argument("--task-id", required=True)
        q.add_argument("--branch", default="develop")
        q.add_argument("--request-path")
        q.add_argument("--current-path")
        q.add_argument("--role-plan")
        q.add_argument("--session-receipt-root")
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

    def add_orchestrator_args(q: argparse.ArgumentParser) -> None:
        q.add_argument("--repo-root", type=Path, required=True)
        q.add_argument("--branch", default="develop")
        q.add_argument("--state-root", type=Path, default=Path("/users/a/e/aereinh/.agent-flow-v3/stage_orchestrator"))
        q.add_argument("--poll-seconds", type=int, default=60)
        q.add_argument("--default-wait-hours", type=int, default=4)
        q.add_argument("--output", type=Path, default=Path("/users/a/e/aereinh/.agent-flow-v3/stage_orchestrator/stage_orchestrator_receipt.json"))
        q.add_argument("--codex-bin", default="/users/a/e/aereinh/codex-runtime/bin/codex")
        q.add_argument(
            "--controller-role-plan",
            default="prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json",
        )
        q.add_argument("--controller-tmux-session", default="care_agent_flow_v3")
        q.add_argument("--controller-tmux-window", default="Controller-care-ase-faithful")
        q.add_argument("--verifier-tmux-session", default="care_agent_flow_v3")
        q.add_argument("--verifier-tmux-window", default="Verifier-care-ase-faithful")
        q.add_argument("--executor-tmux-session", default="care_agent_flow_v3")
        q.add_argument("--executor-tmux-window", default="Executor-care-ase-faithful")

    q = sub.add_parser("stage-orchestrator-once")
    add_orchestrator_args(q)
    q.set_defaults(func=cmd_stage_orchestrator_once)

    q = sub.add_parser("stage-orchestrator-watch")
    add_orchestrator_args(q)
    q.add_argument("--max-cycles", type=int)
    q.set_defaults(func=cmd_stage_orchestrator_watch)

    q = sub.add_parser("start-stage-orchestrator")
    add_orchestrator_args(q)
    q.add_argument("--tmux-session", default="care_agent_flow_v3")
    q.add_argument("--tmux-window", default="Orchestrator")
    q.add_argument("--dry-run", action="store_true")
    q.set_defaults(func=cmd_start_stage_orchestrator)

    q = sub.add_parser("stop-stage-orchestrator")
    q.add_argument("--state-root", type=Path, default=Path("/users/a/e/aereinh/.agent-flow-v3/stage_orchestrator"))
    q.add_argument("--tmux-session", default="care_agent_flow_v3")
    q.add_argument("--tmux-window", default="Orchestrator")
    q.set_defaults(func=cmd_stop_stage_orchestrator)

    q = sub.add_parser("status-stage-orchestrator")
    q.add_argument("--state-root", type=Path, default=Path("/users/a/e/aereinh/.agent-flow-v3/stage_orchestrator"))
    q.add_argument("--tmux-session", default="care_agent_flow_v3")
    q.add_argument("--tmux-window", default="Orchestrator")
    q.add_argument("--output", type=Path)
    q.set_defaults(func=cmd_status_stage_orchestrator)

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

    q = sub.add_parser("activate-care-ase-after-smoke-b")
    q.add_argument("--repo-root", type=Path, required=True)
    q.add_argument("--branch", default="develop")
    q.add_argument("--from-origin", action="store_true")
    q.add_argument("--fetch", action="store_true")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--activation-nonce", default="")
    q.set_defaults(func=cmd_activate_care_ase_after_smoke_b)

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
