#!/usr/bin/env python3
"""Email concise controller goal terminal notifications."""

from __future__ import annotations

import argparse
import csv
import glob
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
import hashlib
import html
import json
import os
import re
from pathlib import Path
import smtplib
import sqlite3
import subprocess
import sys
import time
from typing import Any, Callable


NOTIFY_STATUSES = {"complete", "blocked"}
IGNORED_TERMINAL_STATUSES = {"paused", "usage_limited", "budget_limited"}
ALL_GOAL_STATUSES = NOTIFY_STATUSES | IGNORED_TERMINAL_STATUSES | {"active"}
DEFAULT_REPO_ROOT = Path(os.environ.get("CARE_REPO_ROOT", Path(__file__).resolve().parents[1]))
DEFAULT_STATE_PATH = Path("controller_notifications/state/notified_goals.json")
DEFAULT_STATUS_PATH = Path("controller_notifications/state/notify_goal_watcher_status.json")
DEFAULT_LOG_PATH = Path("controller_notifications/logs/notify_goal_watcher.log")
FORBIDDEN_NOTIFICATION_BRIEF_TOKENS = (
    "PENDING",
    "RUNNING",
    "NEEDS_MONITOR",
    "JOB_SUBMITTED",
    "AWAITING_SACCT",
)
REQUIRED_NOTIFICATION_BRIEF_FIELDS = {
    "task_name",
    "final_status",
    "commit_status",
    "push_status",
    "key_conclusion",
    "blocked_or_failure_reason",
    "slurm_terminal_status",
    "evidence_paths",
    "next_step",
}


@dataclass(frozen=True)
class GoalFact:
    route: str
    source: str
    source_path: str
    thread_id: str
    objective: str
    status: str
    updated_at_ms: str
    tokens_used: int = 0
    time_used_seconds: int = 0
    tmux_target: str = ""
    pane_signature: str = ""


@dataclass(frozen=True)
class NotificationEvent:
    route: str
    status: str
    subject_status: str
    thread_id: str
    objective: str
    updated_at_ms: str
    source: str
    source_path: str
    tmux_target: str
    tokens_used: int
    time_used_seconds: int
    packet_paths: list[str]
    git_head: str
    detected_at_utc: str
    previous_status: str

    @property
    def key(self) -> str:
        parts = [self.route, self.source, self.thread_id, self.status, str(self.updated_at_ms)]
        return "|".join(parts)


@dataclass(frozen=True)
class SlurmJobSummary:
    job_id: str
    partition: str = "unknown"
    state: str = "UNKNOWN"
    exit_code: str = "unknown"
    elapsed: str = ""
    credited: bool = False
    role: str = ""
    note: str = ""


@dataclass(frozen=True)
class SlurmRunSummary:
    total_jobs: int
    state_counts: dict[str, int]
    credited_jobs: int
    total_elapsed: str
    important_jobs: list[SlurmJobSummary]
    warnings: list[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root_from_config(config: dict[str, Any]) -> Path:
    return Path(config.get("repo_root") or DEFAULT_REPO_ROOT)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def default_config_path() -> Path:
    env_path = os.environ.get("CARE_NOTIFY_CONFIG")
    if env_path:
        return Path(env_path)
    local_path = DEFAULT_REPO_ROOT / "config" / "local" / "controller_notifications.json"
    if local_path.is_file():
        return local_path
    return Path(__file__).with_name("config.example.json")


def default_env_path() -> Path:
    env_path = os.environ.get("CARE_NOTIFY_ENV_FILE")
    if env_path:
        return Path(env_path)
    return DEFAULT_REPO_ROOT / "secrets" / "care_notify.env"


def config_env_defaults() -> dict[str, str]:
    repo_root = str(DEFAULT_REPO_ROOT)
    return {
        "CARE_REPO_ROOT": repo_root,
        "CARE_CODEX_RUNTIME_ROOT": str(Path(repo_root).parent / ".codex-runtime-homes"),
        "CARE_CODEX_HOME_ROOT": str(Path(repo_root).parent / ".codex-homes" / "CARE"),
        "CARE_ROUTE_WORKTREE_ROOT": str(Path(repo_root).parent / "CARE_worktrees"),
        "CARE_NOTIFY_TMUX_SESSION": "care_notifier",
        "CARE_NOTIFY_TMUX_WINDOW": "Notifier",
        "CARE_NOTIFY_FROM": os.environ.get("CARE_NOTIFY_SMTP_USER", ""),
        "CARE_NOTIFY_TO": os.environ.get("CARE_NOTIFY_TO", ""),
        "CARE_ROUTE_A_TMUX_TARGET": "",
        "CARE_ROUTE_B_TMUX_TARGET": "",
        "CARE_ROUTE_C_TMUX_TARGET": "",
    }


def expand_config_placeholders(value: Any, env: dict[str, str]) -> Any:
    if isinstance(value, str):
        expanded = value
        for key, replacement in env.items():
            expanded = expanded.replace("${" + key + "}", replacement)
        return os.path.expanduser(expanded)
    if isinstance(value, list):
        return [expand_config_placeholders(item, env) for item in value]
    if isinstance(value, dict):
        return {key: expand_config_placeholders(item, env) for key, item in value.items()}
    return value


def load_config(path: Path) -> dict[str, Any]:
    config = load_json(path)
    config = expand_config_placeholders(config, config_env_defaults())
    config.setdefault("enabled_routes", [])
    config.setdefault("repo_root", str(DEFAULT_REPO_ROOT))
    config.setdefault("codex_runtime_root", config_env_defaults()["CARE_CODEX_RUNTIME_ROOT"])
    config.setdefault("codex_home_root", config_env_defaults()["CARE_CODEX_HOME_ROOT"])
    config.setdefault("state_path", str(DEFAULT_STATE_PATH))
    config.setdefault("status_path", str(DEFAULT_STATUS_PATH))
    config.setdefault("log_path", str(DEFAULT_LOG_PATH))
    config.setdefault("tmux_session", "care_notifier")
    config.setdefault("tmux_window", "Notifier")
    config.setdefault("routes", {})
    return config


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"observed": {}, "notified": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"observed": {}, "notified": {}}
    state.setdefault("observed", {})
    state.setdefault("notified", {})
    return state


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_status(path: Path, status: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def state_path_from_config(config: dict[str, Any], override: Path | None = None) -> Path:
    if override is not None:
        return override
    path = Path(config.get("state_path", str(DEFAULT_STATE_PATH)))
    if path.is_absolute():
        return path
    return repo_root_from_config(config) / path


def status_path_from_config(config: dict[str, Any], override: Path | None = None) -> Path:
    if override is not None:
        return override
    path = Path(config.get("status_path", str(DEFAULT_STATUS_PATH)))
    if path.is_absolute():
        return path
    return repo_root_from_config(config) / path


def log_path_from_config(config: dict[str, Any]) -> Path:
    path = Path(config.get("log_path", str(DEFAULT_LOG_PATH)))
    if path.is_absolute():
        return path
    return repo_root_from_config(config) / path


def route_config(config: dict[str, Any], route: str) -> dict[str, Any]:
    return dict(config.get("routes", {}).get(route, {}))


def route_runtime_goal_dbs(config: dict[str, Any], route: str) -> list[Path]:
    env_defaults = config_env_defaults()
    runtime_root = Path(config.get("codex_runtime_root") or env_defaults["CARE_CODEX_RUNTIME_ROOT"])
    codex_home_root = Path(config.get("codex_home_root") or env_defaults["CARE_CODEX_HOME_ROOT"])
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add_db(path: Path) -> None:
        db = path if path.name == "goals_1.sqlite" else path / "goals_1.sqlite"
        if db.is_file() and db not in seen:
            candidates.append(db)
            seen.add(db)

    if route == "main":
        add_db(codex_home_root)

    for raw in route_config(config, route).get("runtime_home_candidates", []):
        home = Path(raw)
        if not home.is_absolute():
            home = runtime_root / home
        add_db(home)

    if runtime_root.is_dir():
        for home in sorted(runtime_root.iterdir()):
            if route in home.name or (route == "main" and home.name.startswith("CARE__codex-")):
                add_db(home)
    return candidates


def read_goal_facts_from_db(route: str, db_path: Path) -> list[GoalFact]:
    uri = f"file:{db_path}?mode=ro"
    facts: list[GoalFact] = []
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return facts
    try:
        rows = conn.execute(
            """
            select thread_id, objective, status, tokens_used, time_used_seconds, updated_at_ms
            from thread_goals
            where status in (?, ?, ?, ?, ?, ?)
            order by updated_at_ms desc
            """,
            tuple(sorted(ALL_GOAL_STATUSES)),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    for thread_id, objective, status, tokens_used, time_used_seconds, updated_at_ms in rows:
        facts.append(
            GoalFact(
                route=route,
                source="sqlite",
                source_path=str(db_path),
                thread_id=str(thread_id),
                objective=str(objective or ""),
                status=str(status or "").lower(),
                updated_at_ms=str(updated_at_ms),
                tokens_used=int(tokens_used or 0),
                time_used_seconds=int(time_used_seconds or 0),
            )
        )
    return facts


def parse_pane_goal_status(text: str) -> str | None:
    lowered = text.lower()
    complete_markers = (
        "goal achieved",
        "goal 已标记完成",
        "goal 已标记 complete",
        "active goal 已标记完成",
        "goal complete",
    )
    blocked_markers = (
        "goal blocked",
        "active goal 已标记 blocked",
        "goal 已标记 blocked",
        "status: blocked",
    )
    if any(marker in lowered for marker in complete_markers):
        return "complete"
    if any(marker in lowered for marker in blocked_markers):
        return "blocked"
    return "active" if text.strip() else None


def capture_tmux_pane(target: str, repo_root: Path) -> str:
    if not target:
        return ""
    pane_target = target if "." in target else f"{target}.0"
    cp = subprocess.run(
        ["tmux", "capture-pane", "-pt", pane_target, "-S", "-120"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
        check=False,
    )
    return cp.stdout if cp.returncode == 0 else ""


def read_goal_fact_from_pane(
    config: dict[str, Any],
    route: str,
    capture_func: Callable[[str, Path], str] = capture_tmux_pane,
) -> GoalFact | None:
    rcfg = route_config(config, route)
    target = str(rcfg.get("tmux_target") or "")
    if not target:
        return None
    text = capture_func(target, repo_root_from_config(config))
    status = parse_pane_goal_status(text)
    if not status:
        return None
    tail = "\n".join(text.splitlines()[-40:])
    signature = hashlib.sha256(tail.encode("utf-8", errors="replace")).hexdigest()[:16]
    objective = ""
    for line in reversed(text.splitlines()):
        if "/goal" in line:
            objective = line.strip()
            break
    return GoalFact(
        route=route,
        source="tmux_pane",
        source_path=target,
        thread_id=target,
        objective=objective or f"pane fallback for {target}",
        status=status,
        updated_at_ms=signature,
        tmux_target=target,
        pane_signature=signature,
    )


def collect_goal_facts(
    config: dict[str, Any],
    capture_func: Callable[[str, Path], str] = capture_tmux_pane,
) -> list[GoalFact]:
    facts: list[GoalFact] = []
    for route in config.get("enabled_routes", []):
        route_db_facts: list[GoalFact] = []
        for db in route_runtime_goal_dbs(config, route):
            route_db_facts.extend(read_goal_facts_from_db(route, db))
        if route_db_facts:
            rcfg = route_config(config, route)
            tmux_target = str(rcfg.get("tmux_target") or "")
            for fact in route_db_facts:
                facts.append(
                    GoalFact(
                        **{
                            **asdict(fact),
                            "tmux_target": tmux_target,
                        }
                    )
                )
            facts.extend(collect_manual_completion_facts(config, route))
            continue
        facts.extend(collect_manual_completion_facts(config, route))
        pane_fact = read_goal_fact_from_pane(config, route, capture_func=capture_func)
        if pane_fact is not None:
            facts.append(pane_fact)
    return facts


def collect_manual_completion_facts(config: dict[str, Any], route: str) -> list[GoalFact]:
    repo_root = repo_root_from_config(config)
    candidates: list[Path] = []
    for raw in route_config(config, route).get("notification_brief_paths", []):
        pattern = Path(str(raw))
        pattern_text = str(pattern if pattern.is_absolute() else repo_root / pattern)
        matches = [Path(match) for match in glob.glob(pattern_text)] if any(ch in pattern_text for ch in "*?[") else [Path(pattern_text)]
        candidates.extend(path for path in matches if path.is_file())
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for path in candidates[:1]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or notification_brief_error(payload):
            continue
        status = str(payload.get("final_status", "")).lower()
        if status not in NOTIFY_STATUSES:
            continue
        return [
            GoalFact(
                route=route,
                source="manual_controller_completion",
                source_path=str(path.relative_to(repo_root) if path.is_relative_to(repo_root) else path),
                thread_id=str(payload.get("task_name") or path.parent.name),
                objective=str(payload.get("key_conclusion") or payload.get("task_name") or path.parent.name),
                status=status,
                updated_at_ms=str(int(path.stat().st_mtime * 1000)),
            )
        ]
    return []


def observed_key(fact: GoalFact) -> str:
    return "|".join([fact.route, fact.source, fact.thread_id])


def git_head(repo_root: Path) -> str:
    cp = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return cp.stdout.strip() if cp.returncode == 0 else "UNKNOWN"


def event_for_transition(
    config: dict[str, Any],
    fact: GoalFact,
    previous_status: str,
) -> NotificationEvent:
    rcfg = route_config(config, fact.route)
    status_label = "GOAL_COMPLETE" if fact.status == "complete" else "GOAL_BLOCKED"
    return NotificationEvent(
        route=fact.route,
        status=fact.status,
        subject_status=status_label,
        thread_id=fact.thread_id,
        objective=fact.objective,
        updated_at_ms=fact.updated_at_ms,
        source=fact.source,
        source_path=fact.source_path,
        tmux_target=fact.tmux_target or str(rcfg.get("tmux_target") or ""),
        tokens_used=fact.tokens_used,
        time_used_seconds=fact.time_used_seconds,
        packet_paths=list(rcfg.get("packet_paths", [])),
        git_head=git_head(repo_root_from_config(config)),
        detected_at_utc=utc_now(),
        previous_status=previous_status,
    )


def pending_events_from_facts(config: dict[str, Any], state: dict[str, Any], facts: list[GoalFact]) -> list[NotificationEvent]:
    events: list[NotificationEvent] = []
    for fact in facts:
        key = observed_key(fact)
        previous = state["observed"].get(key, {})
        previous_status = str(previous.get("status", ""))
        if not previous_status and fact.source == "manual_controller_completion":
            previous_status = "manual_pending"
        if fact.status in NOTIFY_STATUSES and previous_status and previous_status not in NOTIFY_STATUSES:
            event = event_for_transition(config, fact, previous_status)
            if event.key not in state["notified"]:
                events.append(event)
    return events


def discovered_goal_sources(facts: list[GoalFact]) -> dict[str, list[dict[str, Any]]]:
    sources: dict[str, list[dict[str, Any]]] = {}
    for fact in facts:
        sources.setdefault(fact.route, []).append(
            {
                "source": fact.source,
                "source_path": fact.source_path,
                "thread_id": fact.thread_id,
                "status": fact.status,
                "updated_at_ms": fact.updated_at_ms,
                "tmux_target": fact.tmux_target,
            }
        )
    return sources


def smtp_secret_status(env: dict[str, str]) -> dict[str, bool]:
    return {
        "smtp_user_present": bool(env.get("CARE_NOTIFY_SMTP_USER")),
        "smtp_password_present": bool(env.get("CARE_NOTIFY_SMTP_PASSWORD")),
    }


def build_config_warnings(config: dict[str, Any], env: dict[str, str]) -> list[str]:
    warnings: list[str] = []
    if not config.get("enabled_routes"):
        warnings.append("enabled_routes is empty")
    if not config.get("email", {}).get("to"):
        warnings.append("email.to is empty")
    secrets = smtp_secret_status(env)
    if not secrets["smtp_user_present"]:
        warnings.append("CARE_NOTIFY_SMTP_USER is missing")
    if not secrets["smtp_password_present"]:
        warnings.append("CARE_NOTIFY_SMTP_PASSWORD is missing")
    return warnings


def event_summary(event: NotificationEvent) -> dict[str, Any]:
    return {
        "route": event.route,
        "status": event.status,
        "subject_status": event.subject_status,
        "thread_id": event.thread_id,
        "source": event.source,
        "source_path": event.source_path,
        "updated_at_ms": event.updated_at_ms,
        "detected_at_utc": event.detected_at_utc,
        "previous_status": event.previous_status,
        "key": event.key,
    }


def base_health_status(
    config: dict[str, Any],
    *,
    state_path: Path,
    status_path: Path,
    env: dict[str, str],
    dry_run: bool,
    facts: list[GoalFact],
    events: list[NotificationEvent],
) -> dict[str, Any]:
    enabled_routes = list(config.get("enabled_routes", []))
    return {
        "service": "controller_goal_notifier",
        "enabled": bool(enabled_routes),
        "last_scan_at_utc": utc_now(),
        "enabled_routes": enabled_routes,
        "discovered_goal_sources": discovered_goal_sources(facts),
        "facts_count": len(facts),
        "pending_events": [event_summary(event) for event in events],
        "pending_event_count": len(events),
        "state_path": str(state_path),
        "status_path": str(status_path),
        "log_path": str(log_path_from_config(config)),
        "tmux_session": str(config.get("tmux_session", "care_notifier")),
        "tmux_window": str(config.get("tmux_window", "Notifier")),
        "dry_run": dry_run,
        "smtp": smtp_secret_status(env),
        "config_warnings": build_config_warnings(config, env),
        "last_event": None,
        "last_email_status": "dry_run" if dry_run else "idle",
        "sent_email_count": 0,
        "failed_email_count": 0,
        "failures": [],
    }


def update_observed_state(state: dict[str, Any], facts: list[GoalFact], skip_keys: set[str] | None = None) -> None:
    skip_keys = skip_keys or set()
    for fact in facts:
        key = observed_key(fact)
        if key in skip_keys:
            continue
        state["observed"][key] = {
            "route": fact.route,
            "source": fact.source,
            "source_path": fact.source_path,
            "thread_id": fact.thread_id,
            "status": fact.status,
            "updated_at_ms": fact.updated_at_ms,
            "seen_at_utc": utc_now(),
        }


def route_label(config: dict[str, Any], route: str) -> str:
    return str(route_config(config, route).get("label") or route.replace("_", " ").title())


def route_branch(route: str) -> str:
    return "main" if route == "main" else route


def route_worktree(config: dict[str, Any], route: str) -> Path:
    rcfg = route_config(config, route)
    configured = rcfg.get("worktree")
    if configured:
        return Path(str(configured))
    repo_root = repo_root_from_config(config)
    if route == "main":
        return repo_root
    return repo_root.parent / "CARE_worktrees" / route


def run_git_text(args: list[str], cwd: Path) -> str:
    try:
        cp = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return cp.stdout.strip() if cp.returncode == 0 and cp.stdout.strip() else "unknown"



def read_limited_text(path: Path, limit: int) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def packet_target_paths(config: dict[str, Any], event: NotificationEvent) -> list[Path]:
    explicit_paths = [Path(path) for path in event.packet_paths]
    roots: list[Path] = []
    for packet_path in explicit_paths:
        if packet_path.name in {"controller_report.md", "completion_check.md", "result.md", "review_request.md", "MANIFEST.md"}:
            roots.append(packet_path.parent)
    if not roots:
        roots.append(route_worktree(config, event.route) / "results" / event.route)
    result_root = roots[0]
    candidates = [
        result_root / "result.md",
        result_root / "completion_check.md",
        result_root / "review_request.md",
        result_root / "MANIFEST.md",
    ]
    for packet_path in explicit_paths:
        if packet_path not in candidates:
            candidates.append(packet_path)
    return candidates


def short_hash(value: str, length: int = 7) -> str:
    value = str(value or "")
    if re.fullmatch(r"[0-9a-fA-F]{12,}", value):
        return value[:length]
    return value or "unknown"


def display_path(config: dict[str, Any], route: str, path: Path) -> str:
    roots = [route_worktree(config, route), repo_root_from_config(config)]
    for root in roots:
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


def brief_file_status(path: Path, *, config: dict[str, Any] | None = None, route: str = "") -> str:
    label = display_path(config, route, path) if config is not None and route else str(path)
    if not path.exists():
        return f"{label}: missing"
    text = read_limited_text(path, 3000)
    tokens = []
    for pattern in (
        r"ROUTE_[A-Z]_[A-Z0-9_]*TERMINAL_PACKET_READY_FOR_REVIEW",
        r"status:\s*`?([A-Z0-9_]+)`?",
        r"route_promotion_decision:\s*`?([A-Z0-9_]+)`?",
        r"route_negative_decision:\s*`?([A-Z0-9_]+)`?",
        r"scientific_resolution_status:\s*`?([A-Z0-9_]+)`?",
        r"job[_ -]?id:\s*`?([0-9]+)`?",
        r"Slurm job:\s*`?([0-9]+)`?",
    ):
        for match in re.finditer(pattern, text):
            value = match.group(1) if match.groups() else match.group(0)
            if value not in tokens:
                tokens.append(value)
    summary = ", ".join(tokens[:5]) if tokens else "present"
    return f"{label}: {summary}"


def notification_brief_required(config: dict[str, Any], event: NotificationEvent) -> bool:
    return bool(route_config(config, event.route).get("require_notification_brief", False))


def configured_brief_patterns(config: dict[str, Any], event: NotificationEvent) -> list[str]:
    patterns: list[str] = []
    if event.source == "manual_controller_completion" and event.source_path:
        patterns.append(event.source_path)
    for packet_path in event.packet_paths:
        path = Path(packet_path)
        if path.name == "notification_brief.json":
            patterns.append(str(path))
        elif path.name in {"controller_report.md", "completion_check.md", "result.md", "MANIFEST.md"}:
            patterns.append(str(path.parent / "notification_brief.json"))
    return patterns


def notification_brief_candidates(config: dict[str, Any], event: NotificationEvent) -> list[Path]:
    repo_root = repo_root_from_config(config)
    candidates: list[Path] = []
    seen: set[Path] = set()
    for raw in configured_brief_patterns(config, event):
        pattern = Path(str(raw))
        pattern_text = str(pattern if pattern.is_absolute() else repo_root / pattern)
        matches = [Path(match) for match in glob.glob(pattern_text)] if any(ch in pattern_text for ch in "*?[") else [Path(pattern_text)]
        for candidate in matches:
            if candidate.is_file() and candidate not in seen:
                candidates.append(candidate)
                seen.add(candidate)
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates


def iter_json_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_json_strings(item)


def notification_brief_error(payload: dict[str, Any]) -> str:
    missing = sorted(REQUIRED_NOTIFICATION_BRIEF_FIELDS - set(payload))
    if missing:
        return "notification_brief missing fields: " + ",".join(missing)
    for value in iter_json_strings(payload):
        upper = value.upper()
        for token in FORBIDDEN_NOTIFICATION_BRIEF_TOKENS:
            if token in upper:
                return f"notification_brief contains forbidden token: {token}"
    evidence_paths = payload.get("evidence_paths")
    if not isinstance(evidence_paths, list) or not evidence_paths:
        return "notification_brief evidence_paths must be a non-empty list"
    return ""


def load_notification_brief(config: dict[str, Any], event: NotificationEvent) -> tuple[dict[str, Any] | None, Path | None, str]:
    candidates = notification_brief_candidates(config, event)
    if not candidates:
        if notification_brief_required(config, event):
            return None, None, "notification_brief.json missing"
        return None, None, ""
    path = candidates[0]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, path, f"notification_brief unreadable: {type(exc).__name__}: {exc}"
    if not isinstance(payload, dict):
        return None, path, "notification_brief must be a JSON object"
    error = notification_brief_error(payload)
    if error:
        return None, path, error
    return payload, path, ""


def event_observed_key(event: NotificationEvent) -> str:
    return "|".join([event.route, event.source, event.thread_id])


def notification_ready_events(config: dict[str, Any], events: list[NotificationEvent]) -> tuple[list[NotificationEvent], list[dict[str, Any]]]:
    ready: list[NotificationEvent] = []
    suppressed: list[dict[str, Any]] = []
    for event in events:
        _, path, error = load_notification_brief(config, event)
        if error:
            suppressed.append({
                "event": event_summary(event),
                "reason": error,
                "brief_path": str(path) if path else "",
                "observed_key": event_observed_key(event),
            })
        else:
            ready.append(event)
    return ready, suppressed


def brief_text(brief: dict[str, Any] | None, key: str, default: str = "未记录") -> str:
    if not brief:
        return default
    value = brief.get(key, default)
    if isinstance(value, str):
        return value.strip() or default
    return str(value)


def evidence_lines_from_brief(brief: dict[str, Any] | None) -> list[str]:
    if not brief:
        return []
    values = brief.get("evidence_paths")
    if not isinstance(values, list):
        return []
    lines = []
    for item in values[:8]:
        text = str(item).strip()
        if text:
            lines.append(text)
    return lines


def terminal_intent(config: dict[str, Any], event: NotificationEvent) -> str:
    if event.status == "blocked":
        return "needs controller repair"
    if event.source == "manual_test" or "terminal packet ready for reviewer" in event.objective.lower():
        return "terminal packet ready for reviewer"
    for packet_path in packet_target_paths(config, event):
        text = read_limited_text(packet_path, 4000)
        if "TERMINAL_PACKET_READY_FOR_REVIEW" in text or "AWAITING_REVIEW" in text:
            return "terminal packet ready for reviewer"
    return "terminal goal complete"


def subject_for_event(config: dict[str, Any], event: NotificationEvent) -> str:
    prefix = config.get("email", {}).get("subject_prefix", "[CARE]")
    route = route_label(config, event.route)
    if event.status == "blocked":
        intent = "需要处理"
    elif event.route == "main":
        intent = "Batch 完成"
    else:
        intent = "等待 reviewer"
    return f"{prefix}[{route}][{event.subject_status}][{intent}]"


def normalize_slurm_state(raw: str) -> str:
    state = str(raw or "").strip().upper()
    if not state:
        return "UNKNOWN"
    if state.startswith("COMPLETED"):
        return "COMPLETED"
    if state.startswith("FAILED"):
        return "FAILED"
    if state.startswith("CANCELLED"):
        return "CANCELLED"
    if state.startswith("RUNNING"):
        return "RUNNING"
    if state.startswith("PENDING") or state == "SUBMITTED":
        return "PENDING"
    return state.split()[0]


def elapsed_to_seconds(value: str) -> int | None:
    value = str(value or "").strip()
    if not value or value.lower() in {"unknown", "n/a"}:
        return None
    parts = value.split("-")
    days = 0
    clock = parts[-1]
    if len(parts) == 2:
        try:
            days = int(parts[0])
        except ValueError:
            return None
    fields = clock.split(":")
    try:
        if len(fields) == 3:
            hours, minutes, seconds = [int(part) for part in fields]
        elif len(fields) == 2:
            hours = 0
            minutes, seconds = [int(part) for part in fields]
        else:
            return None
    except ValueError:
        return None
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def format_elapsed(seconds: int | None) -> str:
    if seconds is None:
        return "未记录"
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}小时{minutes}分{secs}秒"
    if minutes:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"


def credited_value(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    if not lowered:
        return False
    if lowered in {"true", "yes", "credited", "credit"}:
        return True
    if lowered.startswith("zero") or lowered in {"false", "no", "pending", "none"}:
        return False
    return "credit" in lowered and "zero" not in lowered


def update_job_summary(jobs: dict[str, SlurmJobSummary], candidate: SlurmJobSummary) -> None:
    current = jobs.get(candidate.job_id)
    if current is None:
        jobs[candidate.job_id] = candidate
        return
    terminal_order = {"UNKNOWN": 0, "PENDING": 1, "RUNNING": 2, "CANCELLED": 3, "FAILED": 4, "COMPLETED": 5}
    if terminal_order.get(candidate.state, 0) >= terminal_order.get(current.state, 0):
        jobs[candidate.job_id] = SlurmJobSummary(
            job_id=candidate.job_id,
            partition=candidate.partition if candidate.partition != "unknown" else current.partition,
            state=candidate.state,
            exit_code=candidate.exit_code if candidate.exit_code != "unknown" else current.exit_code,
            elapsed=candidate.elapsed or current.elapsed,
            credited=candidate.credited or current.credited,
            role=candidate.role or current.role,
            note=candidate.note or current.note,
        )


def seconds_to_clock(seconds: float) -> str:
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def extract_elapsed_from_note(note: str) -> str:
    for pattern in (
        r"elapsed\s+([0-9]+-[0-9:]+|[0-9]{1,2}:[0-9]{2}:[0-9]{2}|[0-9]{1,2}:[0-9]{2})",
        r"after\s+([0-9]+-[0-9:]+|[0-9]{1,2}:[0-9]{2}:[0-9]{2}|[0-9]{1,2}:[0-9]{2})",
    ):
        match = re.search(pattern, note, re.I)
        if match:
            return match.group(1)
    for pattern in (
        r"train_loop_seconds\s+([0-9]+(?:\.[0-9]+)?)",
        r"([0-9]+(?:\.[0-9]+)?)\s+seconds completed",
    ):
        match = re.search(pattern, note, re.I)
        if match:
            return seconds_to_clock(float(match.group(1)))
    return ""


def route_packet_root(config: dict[str, Any], event: NotificationEvent) -> Path:
    paths = packet_target_paths(config, event)
    for path in paths:
        if path.name in {"controller_report.md", "completion_check.md", "result.md", "review_request.md", "MANIFEST.md"}:
            return path.parent
    return route_worktree(config, event.route) / "results" / event.route


def evidence_file_candidates(root: Path) -> list[Path]:
    if not root.exists():
        return []
    candidates: list[Path] = []
    for name in ("finalizer_state.json", "routing_and_finalizer_ledger.csv", "routing_ledger.csv", "controller_ledger.csv"):
        path = root / name
        if path.is_file():
            candidates.append(path)
    for path in sorted(root.rglob("*ledger*.csv")):
        if "runtime" not in path.parts and path not in candidates:
            candidates.append(path)
    for path in sorted(root.rglob("finalizer_state.json")):
        if "runtime" not in path.parts and path not in candidates:
            candidates.append(path)
    return candidates[:40]


def parse_slurm_csv(path: Path, jobs: dict[str, SlurmJobSummary], warnings: list[str]) -> None:
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            for row in csv.DictReader(handle):
                job_id = str(row.get("job_id") or "").strip()
                if not job_id:
                    continue
                state = normalize_slurm_state(row.get("state") or row.get("scheduler_state") or "")
                note = str(row.get("lineage_note") or row.get("winner_lock_result") or row.get("cancel_command") or "").strip()
                role = str(row.get("stage") or row.get("logical_run_id") or row.get("executor") or row.get("attempt_id") or "").strip()
                elapsed = str(row.get("elapsed") or "").strip() or extract_elapsed_from_note(note)
                update_job_summary(
                    jobs,
                    SlurmJobSummary(
                        job_id=job_id,
                        partition=str(row.get("partition") or "unknown").strip() or "unknown",
                        state=state,
                        exit_code=str(row.get("exit_code") or "unknown").strip() or "unknown",
                        elapsed=elapsed,
                        credited=credited_value(str(row.get("credited") or row.get("credit") or "")),
                        role=role,
                        note=note,
                    ),
                )
    except (OSError, csv.Error) as exc:
        warnings.append(f"无法读取 Slurm ledger {path.name}: {type(exc).__name__}")


def parse_finalizer_json(path: Path, jobs: dict[str, SlurmJobSummary], warnings: list[str]) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"无法读取 finalizer state {path.name}: {type(exc).__name__}")
        return
    for item in data.get("slurm_jobs", []) if isinstance(data.get("slurm_jobs"), list) else []:
        job_id = str(item.get("job_id") or "").strip()
        if not job_id:
            continue
        update_job_summary(
            jobs,
            SlurmJobSummary(
                job_id=job_id,
                partition=str(item.get("partition") or "unknown"),
                state=normalize_slurm_state(item.get("state") or ""),
                exit_code=str(item.get("exit_code") or "unknown"),
                elapsed=str(item.get("elapsed") or ""),
                credited=item.get("state") == "COMPLETED" and str(item.get("exit_code") or "") == "0:0",
                role="finalizer slurm_jobs",
                note=str(item.get("log_path") or ""),
            ),
        )
    job_states = data.get("job_states") if isinstance(data.get("job_states"), dict) else {}
    elapsed = data.get("elapsed") if isinstance(data.get("elapsed"), dict) else {}
    exit_codes = data.get("exit_codes") if isinstance(data.get("exit_codes"), dict) else {}
    required = {str(job_id) for job_id in data.get("required_job_ids", [])} if isinstance(data.get("required_job_ids"), list) else set()
    for job_id, state in job_states.items():
        job_id = str(job_id)
        update_job_summary(
            jobs,
            SlurmJobSummary(
                job_id=job_id,
                state=normalize_slurm_state(str(state)),
                exit_code=str(exit_codes.get(job_id) or "unknown"),
                elapsed=str(elapsed.get(job_id) or ""),
                credited=job_id in required,
                role="required runtime" if job_id in required else "finalizer state",
            ),
        )
    repair = data.get("reviewer_revision_repair")
    if isinstance(repair, dict):
        repair_job_id = str(repair.get("repair_job_id") or "").strip()
        if repair_job_id:
            update_job_summary(
                jobs,
                SlurmJobSummary(
                    job_id=repair_job_id,
                    partition="htzhulab",
                    state=normalize_slurm_state(repair.get("repair_job_state") or ""),
                    exit_code=str(repair.get("repair_exit_code") or "unknown"),
                    elapsed=str(repair.get("repair_elapsed") or ""),
                    credited=True,
                    role="reviewer revision repair",
                    note=str(repair.get("repair_log_path") or ""),
                ),
            )
        failed_job_id = str(repair.get("superseded_failed_repair_job_id") or "").strip()
        if failed_job_id:
            update_job_summary(
                jobs,
                SlurmJobSummary(
                    job_id=failed_job_id,
                    partition="htzhulab",
                    state=normalize_slurm_state(repair.get("superseded_failed_repair_state") or ""),
                    exit_code=str(repair.get("superseded_failed_repair_exit_code") or "unknown"),
                    elapsed=str(repair.get("superseded_failed_repair_elapsed") or ""),
                    credited=False,
                    role="superseded repair",
                ),
            )


def summarize_slurm(config: dict[str, Any], event: NotificationEvent) -> SlurmRunSummary:
    root = route_packet_root(config, event)
    jobs: dict[str, SlurmJobSummary] = {}
    warnings: list[str] = []
    candidates = evidence_file_candidates(root)
    if not candidates:
        warnings.append("packet 未记录 Slurm ledger/finalizer_state")
    for path in candidates:
        if path.suffix == ".csv":
            parse_slurm_csv(path, jobs, warnings)
        elif path.name == "finalizer_state.json":
            parse_finalizer_json(path, jobs, warnings)
    state_counts: dict[str, int] = {}
    elapsed_seconds = 0
    elapsed_seen = False
    for job in jobs.values():
        state_counts[job.state] = state_counts.get(job.state, 0) + 1
        seconds = elapsed_to_seconds(job.elapsed)
        if seconds is not None:
            elapsed_seconds += seconds
            elapsed_seen = True
    max_jobs = int(config.get("email", {}).get("max_important_slurm_jobs", 6) or 6)
    credited_completed = sorted(
        (job for job in jobs.values() if job.state == "COMPLETED" and job.credited and job.elapsed),
        key=lambda job: job.job_id,
    )
    other_ordered = sorted(
        (job for job in jobs.values() if job not in credited_completed),
        key=lambda job: (
            {"FAILED": 0, "CANCELLED": 1, "RUNNING": 2, "PENDING": 3, "COMPLETED": 4}.get(job.state, 5),
            not job.credited,
            job.job_id,
        ),
    )
    important = list(credited_completed)
    remaining_slots = max(0, max_jobs - len(important))
    important.extend(other_ordered[:remaining_slots])
    important_ids = {job.job_id for job in important}
    omitted = [job for job in jobs.values() if job.job_id not in important_ids]
    if omitted:
        omitted_credited_completed = [job for job in omitted if job.state == "COMPLETED" and job.credited]
        suffix = ""
        if omitted_credited_completed:
            suffix = f"；其中 {len(omitted_credited_completed)} 个为 credited COMPLETED job"
        else:
            suffix = "；未省略 credited COMPLETED job"
        warnings.append(f"另有 {len(omitted)} 个 job 未在邮件正文展开{suffix}")
    return SlurmRunSummary(
        total_jobs=len(jobs),
        state_counts=state_counts,
        credited_jobs=sum(1 for job in jobs.values() if job.credited),
        total_elapsed=format_elapsed(elapsed_seconds if elapsed_seen else None),
        important_jobs=important,
        warnings=warnings,
    )


def summarize_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "未记录"
    order = ["COMPLETED", "FAILED", "CANCELLED", "RUNNING", "PENDING", "UNKNOWN"]
    parts = [f"{state} {counts[state]}" for state in order if counts.get(state)]
    parts.extend(f"{state} {count}" for state, count in sorted(counts.items()) if state not in order)
    return "；".join(parts)


def format_job_line(job: SlurmJobSummary) -> str:
    elapsed = job.elapsed or "未记录"
    credited = "计入结果" if job.credited else "未计入结果"
    role = f"，{job.role}" if job.role else ""
    note = f"，{job.note[:120]}" if job.note else ""
    return f"job {job.job_id}，{job.partition}，{job.state}，exit {job.exit_code}，耗时 {elapsed}，{credited}{role}{note}"


def build_email_context(config: dict[str, Any], event: NotificationEvent) -> dict[str, Any]:
    label = route_label(config, event.route)
    route_head = short_hash(event.git_head)
    brief, brief_path, _ = load_notification_brief(config, event)
    if brief:
        conclusion = brief_text(brief, "key_conclusion")
        action = brief_text(brief, "next_step")
        packet_lines = evidence_lines_from_brief(brief)
    elif event.status == "complete":
        conclusion = f"{label} controller goal 已完成；终端包已准备给 independent reviewer。"
        action = f"交 {label} independent reviewer 审 {route_head}。"
        packet_lines = [brief_file_status(path, config=config, route=event.route) for path in packet_target_paths(config, event)]
    else:
        conclusion = f"{label} controller goal 已 blocked；当前需要 controller/main 介入修复。"
        action = f"{label} controller 修复后继续 goal。"
        packet_lines = [brief_file_status(path, config=config, route=event.route) for path in packet_target_paths(config, event)]
    return {
        "label": label,
        "route_head": route_head,
        "conclusion": conclusion,
        "action": action,
        "brief": brief,
        "brief_path": str(brief_path) if brief_path else "",
        "packet_lines": packet_lines,
        "slurm": summarize_slurm(config, event),
    }


def render_plain_email(config: dict[str, Any], event: NotificationEvent) -> str:
    ctx = build_email_context(config, event)
    slurm: SlurmRunSummary = ctx["slurm"]
    brief = ctx.get("brief")
    lines = [
        f"结论：{ctx['conclusion']}",
        f"下一步：{ctx['action']}",
        "",
        "状态",
        f"controller goal：{event.status}（上一状态：{event.previous_status}）",
        f"batch：{brief_text(brief, 'final_status', event.status)}",
        f"commit：{brief_text(brief, 'commit_status')}；push：{brief_text(brief, 'push_status')}",
        f"检测时间：{event.detected_at_utc}",
        "",
        "Slurm 作业概览",
        f"终态：{brief_text(brief, 'slurm_terminal_status')}",
        f"结果：{summarize_counts(slurm.state_counts)}；计入结果：{slurm.credited_jobs if slurm.total_jobs else '未记录'}；运行时长：{slurm.total_elapsed}",
    ]
    if slurm.important_jobs:
        lines.append("关键 job：")
        lines.extend(f"- {format_job_line(job)}" for job in slurm.important_jobs[:3])
    if slurm.warnings:
        lines.append("备注：")
        lines.extend(f"- {warning}" for warning in slurm.warnings[:3])
    lines.extend(["", "关键证据"])
    lines.extend(f"- {line}" for line in ctx["packet_lines"][:8])
    if ctx.get("brief_path"):
        lines.append(f"- notification brief：{ctx['brief_path']}")
    lines.append("")
    return "\n".join(lines)


def render_route_rows_html(rows: list[dict[str, str]]) -> str:
    body = []
    for row in rows:
        state = f"{row['controller_state']} / {row['reviewer_state']}"
        body.append(
            "<tr>"
            f"<td>{html.escape(row['route'])}</td>"
            f"<td>{html.escape(short_hash(row['branch_head']))}</td>"
            f"<td>{html.escape(short_hash(row['origin_head']))}</td>"
            f"<td>{html.escape(row['dirty_ahead'])}</td>"
            f"<td>{html.escape(state)}</td>"
            f"<td>{html.escape(row['next_action'])}</td>"
            "</tr>"
        )
    return "".join(body)


def render_html_email(config: dict[str, Any], event: NotificationEvent) -> str:
    ctx = build_email_context(config, event)
    slurm: SlurmRunSummary = ctx["slurm"]
    brief = ctx.get("brief")
    job_items = "".join(f"<li>{html.escape(format_job_line(job))}</li>" for job in slurm.important_jobs[:3])
    warning_items = "".join(f"<li>{html.escape(warning)}</li>" for warning in slurm.warnings[:3])
    evidence = list(ctx["packet_lines"][:8])
    if ctx.get("brief_path"):
        evidence.append(f"notification brief：{ctx['brief_path']}")
    packet_items = "".join(f"<li>{html.escape(line)}</li>" for line in evidence)
    return f"""<!doctype html>
<html>
  <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #111827; line-height: 1.45;">
    <h2>结论</h2>
    <p>{html.escape(ctx['conclusion'])}</p>
    <p><strong>下一步：</strong>{html.escape(ctx['action'])}</p>

    <h2>状态</h2>
    <ul>
      <li>controller goal：{html.escape(event.status)}（上一状态：{html.escape(event.previous_status)}）</li>
      <li>batch：{html.escape(brief_text(brief, 'final_status', event.status))}</li>
      <li>commit：{html.escape(brief_text(brief, 'commit_status'))}；push：{html.escape(brief_text(brief, 'push_status'))}</li>
      <li>检测时间：{html.escape(event.detected_at_utc)}</li>
    </ul>

    <h2>Slurm 作业概览</h2>
    <ul>
      <li>终态：{html.escape(brief_text(brief, 'slurm_terminal_status'))}</li>
      <li>结果：{html.escape(summarize_counts(slurm.state_counts))}</li>
      <li>计入结果：{html.escape(str(slurm.credited_jobs if slurm.total_jobs else '未记录'))}</li>
      <li>运行时长：{html.escape(slurm.total_elapsed)}</li>
    </ul>
    {('<p><strong>关键 job：</strong></p><ul>' + job_items + '</ul>') if job_items else ''}
    {('<p><strong>备注：</strong></p><ul>' + warning_items + '</ul>') if warning_items else ''}

    <h2>关键证据</h2>
    <ul>{packet_items}</ul>

  </body>
</html>
"""


def body_for_event(config: dict[str, Any], event: NotificationEvent) -> str:
    return render_plain_email(config, event)


def send_email(config: dict[str, Any], env: dict[str, str], event: NotificationEvent) -> None:
    email_cfg = config.get("email", {})
    smtp_user = env.get("CARE_NOTIFY_SMTP_USER", "")
    smtp_password = env.get("CARE_NOTIFY_SMTP_PASSWORD", "")
    if not smtp_user or not smtp_password:
        raise RuntimeError("CARE_NOTIFY_SMTP_USER and CARE_NOTIFY_SMTP_PASSWORD are required")
    sender = str(email_cfg.get("from") or smtp_user)
    recipients = email_cfg.get("to") or []
    if isinstance(recipients, str):
        recipients = [recipients]
    if not recipients:
        raise RuntimeError("email.to must contain at least one recipient")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject_for_event(config, event)
    message.set_content(render_plain_email(config, event))
    message.add_alternative(render_html_email(config, event), subtype="html")

    host = str(email_cfg.get("smtp_host") or "smtp.gmail.com")
    port = int(email_cfg.get("smtp_port") or 587)
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if bool(email_cfg.get("starttls", True)):
            smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

def run_once(
    config: dict[str, Any],
    *,
    state_path: Path,
    status_path: Path | None = None,
    env: dict[str, str] | None = None,
    dry_run: bool = False,
    sender: Callable[[dict[str, Any], dict[str, str], NotificationEvent], None] = send_email,
    capture_func: Callable[[str, Path], str] = capture_tmux_pane,
) -> list[NotificationEvent]:
    env = env or {}
    status_path = status_path or status_path_from_config(config)
    state = load_state(state_path)
    facts = collect_goal_facts(config, capture_func=capture_func)
    raw_events = pending_events_from_facts(config, state, facts)
    events, suppressed_notifications = notification_ready_events(config, raw_events)
    health = base_health_status(
        config,
        state_path=state_path,
        status_path=status_path,
        env=env,
        dry_run=dry_run,
        facts=facts,
        events=events,
    )
    health["suppressed_notification_count"] = len(suppressed_notifications)
    health["suppressed_notifications"] = suppressed_notifications
    if suppressed_notifications and health["last_email_status"] == "idle":
        health["last_email_status"] = "blocked_notification_brief"
    if dry_run:
        write_status(status_path, health)
        return events

    failed_observed_keys: set[str] = {item["observed_key"] for item in suppressed_notifications}
    for event in events:
        try:
            sender(config, env, event)
        except Exception as exc:  # keep the watcher alive and retry on next scan
            message = str(exc)
            if "CARE_NOTIFY_SMTP_USER" in message or "CARE_NOTIFY_SMTP_PASSWORD" in message:
                health["last_email_status"] = "blocked_config"
            else:
                health["last_email_status"] = "failed"
            health["failed_email_count"] += 1
            health["last_event"] = event_summary(event)
            health["failures"].append(
                {
                    "event": event_summary(event),
                    "error_type": type(exc).__name__,
                    "error": message,
                    "failed_at_utc": utc_now(),
                }
            )
            failed_observed_keys.add("|".join([event.route, event.source, event.thread_id]))
            continue

        sent_at = utc_now()
        state["notified"][event.key] = {
            "route": event.route,
            "status": event.status,
            "thread_id": event.thread_id,
            "sent_at_utc": sent_at,
            "source": event.source,
            "source_path": event.source_path,
        }
        health["last_email_status"] = "sent"
        health["sent_email_count"] += 1
        health["last_event"] = {**event_summary(event), "sent_at_utc": sent_at}

    update_observed_state(state, facts, skip_keys=failed_observed_keys)
    write_state(state_path, state)
    if health["last_email_status"] == "idle" and health["config_warnings"]:
        health["last_email_status"] = "blocked_config"
    write_status(status_path, health)
    return events


def build_test_event(config: dict[str, Any]) -> NotificationEvent:
    enabled_routes = list(config.get("enabled_routes") or [])
    route = enabled_routes[0] if enabled_routes else ("main" if "main" in config.get("routes", {}) else "route_B")
    rcfg = route_config(config, route)
    return NotificationEvent(
        route=route,
        status="complete",
        subject_status="GOAL_COMPLETE",
        thread_id="test-email",
        objective="CARE controller notification test",
        updated_at_ms=str(int(time.time() * 1000)),
        source="manual_test",
        source_path="--send-test",
        tmux_target=rcfg.get("tmux_target", ""),
        tokens_used=0,
        time_used_seconds=0,
        packet_paths=rcfg.get("packet_paths", []),
        git_head=git_head(repo_root_from_config(config)),
        detected_at_utc=utc_now(),
        previous_status="manual_test",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--env-file", type=Path, default=default_env_path())
    parser.add_argument("--state-path", type=Path)
    parser.add_argument("--poll-seconds", type=int, default=0)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--send-test", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    state_path = state_path_from_config(config, args.state_path)
    status_path = status_path_from_config(config)
    env = load_env_file(args.env_file)

    if args.send_test:
        event = build_test_event(config)
        if args.dry_run:
            print(
                json.dumps(
                    {
                        "send_test": asdict(event),
                        "subject": subject_for_event(config, event),
                        "body": render_plain_email(config, event),
                        "plain_body": render_plain_email(config, event),
                        "html_body": render_html_email(config, event),
                    },
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                )
            )
            return 0
        send_email(config, env, event)
        print("sent test email")
        return 0

    poll_seconds = args.poll_seconds or int(config.get("poll_seconds", 60))
    loop = args.loop and not args.once
    while True:
        events = run_once(config, state_path=state_path, status_path=status_path, env=env, dry_run=args.dry_run)
        print(
            json.dumps(
                {
                    "checked_at_utc": utc_now(),
                    "dry_run": args.dry_run,
                    "events": [asdict(event) for event in events],
                    "state_path": str(state_path),
                    "status_path": str(status_path),
                },
                indent=2,
                sort_keys=True,
            )
        )
        sys.stdout.flush()
        if not loop:
            return 0
        time.sleep(max(5, poll_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
