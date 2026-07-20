#!/usr/bin/env python3
"""Email on Route B/C Codex controller goal terminal transitions."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
import hashlib
import html
import json
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
DEFAULT_REPO_ROOT = Path("/users/a/e/aereinh/CARE")
DEFAULT_STATE_PATH = Path("controller_notifications/state/notified_goals.json")
DEFAULT_STATUS_PATH = Path("controller_notifications/state/notify_goal_watcher_status.json")
DEFAULT_LOG_PATH = Path("controller_notifications/logs/notify_goal_watcher.log")


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


def load_config(path: Path) -> dict[str, Any]:
    config = load_json(path)
    config.setdefault("enabled_routes", ["route_B"])
    config.setdefault("repo_root", str(DEFAULT_REPO_ROOT))
    config.setdefault("codex_runtime_root", "/users/a/e/aereinh/.codex-runtime-homes")
    config.setdefault("state_path", str(DEFAULT_STATE_PATH))
    config.setdefault("status_path", str(DEFAULT_STATUS_PATH))
    config.setdefault("log_path", str(DEFAULT_LOG_PATH))
    config.setdefault("tmux_session", "care_watchboard")
    config.setdefault("tmux_window", "Notify")
    config.setdefault(
        "watchboard_urls",
        {
            "public": "https://watchboard.httpwwwcardiacnexus-ukb.com/index.html",
            "local": "http://127.0.0.1:8766/index.html",
        },
    )
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
    runtime_root = Path(config.get("codex_runtime_root") or "/users/a/e/aereinh/.codex-runtime-homes")
    candidates: list[Path] = []
    seen: set[Path] = set()

    for raw in route_config(config, route).get("runtime_home_candidates", []):
        home = Path(raw)
        if not home.is_absolute():
            home = runtime_root / home
        db = home / "goals_1.sqlite"
        if db.is_file() and db not in seen:
            candidates.append(db)
            seen.add(db)

    if runtime_root.is_dir():
        for home in sorted(runtime_root.iterdir()):
            if route in home.name:
                db = home / "goals_1.sqlite"
                if db.is_file() and db not in seen:
                    candidates.append(db)
                    seen.add(db)
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
    for route in config.get("enabled_routes", ["route_B"]):
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
            continue
        pane_fact = read_goal_fact_from_pane(config, route, capture_func=capture_func)
        if pane_fact is not None:
            facts.append(pane_fact)
    return facts


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
    enabled_routes = list(config.get("enabled_routes", ["route_B"]))
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
        "tmux_session": str(config.get("tmux_session", "care_watchboard")),
        "tmux_window": str(config.get("tmux_window", "Notify")),
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


def collect_watchboard_status(config: dict[str, Any]) -> dict[str, Any]:
    repo_root = repo_root_from_config(config)
    module_path = repo_root / "scripts" / "ops" / "build_route_watchboard.py"
    if not module_path.is_file():
        return {}
    try:
        spec = importlib.util.spec_from_file_location("care_watchboard_status_for_notifier", module_path)
        if spec is None or spec.loader is None:
            return {}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        worktree_root = repo_root.parent / "CARE_worktrees"
        user = str(config.get("user") or os.environ.get("USER") or "aereinh")
        return module.collect_status(repo_root, worktree_root, user)
    except Exception:
        return {}


def route_summary_from_watchboard(route: dict[str, Any]) -> dict[str, str]:
    dirty_count = route.get("dirty_count")
    dirty = "clean" if dirty_count in {0, None} else f"dirty {dirty_count}"
    state = str(route.get("display_state_zh") or route.get("runtime_state", {}).get("label_zh") or "待判定")
    controller = str(route.get("current_worker_zh") or route.get("controller_authority", {}).get("state") or "未判定")
    next_action = str(route.get("next_action_zh") or route.get("next_action", {}).get("label_zh") or "等待下一步")
    return {
        "route": str(route.get("label") or route.get("id", "route")),
        "branch_head": str(route.get("sha") or "unknown"),
        "origin_head": str(route.get("origin_sha") or "unknown"),
        "dirty_ahead": f"{dirty}; main delta {str(route.get('ahead_behind_main') or 'unknown').replace(chr(9), ' ')}",
        "controller_state": controller,
        "reviewer_state": state,
        "next_action": next_action,
        "source": "watchboard",
    }


def fallback_route_summary(config: dict[str, Any], route: str) -> dict[str, str]:
    worktree = route_worktree(config, route)
    branch = route_branch(route)
    if worktree.exists():
        head = run_git_text(["rev-parse", "--short=12", "HEAD"], worktree)
        origin = run_git_text(["rev-parse", "--short=12", f"origin/{branch}"], worktree)
        status = run_git_text(["status", "--porcelain"], worktree)
        ahead = run_git_text(["rev-list", "--left-right", "--count", f"origin/{branch}...HEAD"], worktree)
        dirty = "clean" if status == "unknown" or not status else f"dirty {len(status.splitlines())}"
        sync = ahead if ahead != "unknown" else "unknown"
    else:
        head = origin = sync = "missing"
        dirty = "missing"
    return {
        "route": route_label(config, route),
        "branch_head": head,
        "origin_head": origin,
        "dirty_ahead": f"{dirty}; ahead/behind {sync}",
        "controller_state": "watchboard summary unavailable",
        "reviewer_state": "只读 git fallback",
        "next_action": "查看 watchboard / route packet 后判断",
        "source": "fallback",
    }


def route_summary(config: dict[str, Any], route: str, trigger_route: str = "", watchboard_status: dict[str, Any] | None = None) -> dict[str, str]:
    status = watchboard_status if watchboard_status is not None else collect_watchboard_status(config)
    for item in status.get("routes", []) if isinstance(status, dict) else []:
        if item.get("id") == route:
            return route_summary_from_watchboard(item)
    return fallback_route_summary(config, route)


def route_summary_rows(config: dict[str, Any], trigger_route: str, watchboard_status: dict[str, Any] | None = None) -> list[dict[str, str]]:
    status = watchboard_status if watchboard_status is not None else collect_watchboard_status(config)
    routes = [route for route in config.get("enabled_routes", ["route_B"]) if route in {"route_A", "route_B", "route_C"}]
    if trigger_route in {"route_A", "route_B", "route_C"} and trigger_route not in routes:
        routes.append(trigger_route)
    return [route_summary(config, route, trigger_route, status) for route in routes]


def render_route_summary_text(rows: list[dict[str, str]]) -> str:
    rendered = []
    for summary in rows:
        state = f"{summary['controller_state']} / {summary['reviewer_state']}"
        dirty_ahead = summary["dirty_ahead"].replace("\t", " ")
        rendered.append(
            f"{summary['route']}：branch {short_hash(summary['branch_head'])} / origin {short_hash(summary['origin_head'])}；"
            f"{dirty_ahead}；{state}；下一步：{summary['next_action']}"
        )
    return "\n".join(rendered)


def route_summary_table(config: dict[str, Any], trigger_route: str, watchboard_status: dict[str, Any] | None = None) -> str:
    return render_route_summary_text(route_summary_rows(config, trigger_route, watchboard_status))


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
        intent = "需要 controller 修复"
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
    watchboard_status = collect_watchboard_status(config)
    trigger_summary = route_summary(config, event.route, event.route, watchboard_status)
    route_head = short_hash(trigger_summary["branch_head"])
    watchboard_urls = config.get("watchboard_urls", {})
    public_url = str(watchboard_urls.get("public") or "https://watchboard.httpwwwcardiacnexus-ukb.com/index.html")
    local_url = str(watchboard_urls.get("local") or "http://127.0.0.1:8766/index.html")
    if event.status == "complete":
        conclusion = f"{label} controller goal 已完成；终端包已准备给 independent reviewer，不需要 main/controller 介入。"
        action = f"交 {label} independent reviewer 审 {route_head}。"
    else:
        conclusion = f"{label} controller goal 已 blocked；当前需要 controller/main 介入修复，暂不交 reviewer。"
        action = f"{label} controller 修复后继续 goal。"
    return {
        "label": label,
        "route_head": route_head,
        "conclusion": conclusion,
        "action": action,
        "route_rows": route_summary_rows(config, event.route, watchboard_status),
        "route_summary_source": "watchboard" if watchboard_status.get("routes") else "fallback",
        "packet_lines": [brief_file_status(path, config=config, route=event.route) for path in packet_target_paths(config, event)],
        "slurm": summarize_slurm(config, event),
        "public_url": public_url,
        "local_url": local_url,
    }


def render_plain_email(config: dict[str, Any], event: NotificationEvent) -> str:
    ctx = build_email_context(config, event)
    slurm: SlurmRunSummary = ctx["slurm"]
    lines = [
        f"结论：{ctx['conclusion']}",
        f"下一步：{ctx['action']}",
        "",
        "Controller 状态",
        f"状态：{event.status}",
        f"上一状态：{event.previous_status}",
        f"thread：{event.thread_id}",
        f"目标摘要：{event.objective[:500]}",
        f"用量：{event.tokens_used} tokens / {event.time_used_seconds} 秒",
        f"检测时间：{event.detected_at_utc}",
        f"来源：{event.source} ({event.source_path})",
        f"tmux：{event.tmux_target or '未记录'}",
        "",
        "Slurm 作业概览",
        f"总 job：{slurm.total_jobs if slurm.total_jobs else '未记录'}",
        f"结果：{summarize_counts(slurm.state_counts)}",
        f"可得总运行时长：{slurm.total_elapsed}",
        f"计入结果：{slurm.credited_jobs if slurm.total_jobs else '未记录'}",
    ]
    if slurm.important_jobs:
        lines.append("关键 job：")
        lines.extend(f"- {format_job_line(job)}" for job in slurm.important_jobs)
    if slurm.warnings:
        lines.append("备注：")
        lines.extend(f"- {warning}" for warning in slurm.warnings)
    if ctx.get("route_summary_source") != "watchboard":
        lines.extend(["", "Route 总览", "watchboard 动态状态暂不可用，以下为只读 fallback 摘要。", render_route_summary_text(ctx["route_rows"]), "", "关键证据"])
    else:
        lines.extend(["", "Route 总览", render_route_summary_text(ctx["route_rows"]), "", "关键证据"])
    lines.extend(f"- {line}" for line in ctx["packet_lines"])
    lines.extend(["", "Watchboard", f"public：{ctx['public_url']}", f"local：{ctx['local_url']}", ""])
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
    job_items = "".join(f"<li>{html.escape(format_job_line(job))}</li>" for job in slurm.important_jobs)
    warning_items = "".join(f"<li>{html.escape(warning)}</li>" for warning in slurm.warnings)
    packet_items = "".join(f"<li>{html.escape(line)}</li>" for line in ctx["packet_lines"])
    return f"""<!doctype html>
<html>
  <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #111827; line-height: 1.45;">
    <h2>结论</h2>
    <p>{html.escape(ctx['conclusion'])}</p>
    <p><strong>下一步：</strong>{html.escape(ctx['action'])}</p>

    <h2>Controller 状态</h2>
    <ul>
      <li>状态：{html.escape(event.status)}</li>
      <li>上一状态：{html.escape(event.previous_status)}</li>
      <li>thread：{html.escape(event.thread_id)}</li>
      <li>目标摘要：{html.escape(event.objective[:500])}</li>
      <li>用量：{event.tokens_used} tokens / {event.time_used_seconds} 秒</li>
      <li>检测时间：{html.escape(event.detected_at_utc)}</li>
      <li>来源：{html.escape(event.source)} ({html.escape(event.source_path)})</li>
      <li>tmux：{html.escape(event.tmux_target or '未记录')}</li>
    </ul>

    <h2>Slurm 作业概览</h2>
    <ul>
      <li>总 job：{html.escape(str(slurm.total_jobs if slurm.total_jobs else '未记录'))}</li>
      <li>结果：{html.escape(summarize_counts(slurm.state_counts))}</li>
      <li>可得总运行时长：{html.escape(slurm.total_elapsed)}</li>
      <li>计入结果：{html.escape(str(slurm.credited_jobs if slurm.total_jobs else '未记录'))}</li>
    </ul>
    {('<p><strong>关键 job：</strong></p><ul>' + job_items + '</ul>') if job_items else ''}
    {('<p><strong>备注：</strong></p><ul>' + warning_items + '</ul>') if warning_items else ''}

    <h2>Route 总览</h2>
    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse: collapse;">
      <thead><tr><th>route</th><th>branch</th><th>origin</th><th>dirty/ahead</th><th>状态</th><th>next action</th></tr></thead>
      <tbody>{render_route_rows_html(ctx['route_rows'])}</tbody>
    </table>

    <h2>关键证据</h2>
    <ul>{packet_items}</ul>

    <h2>Watchboard</h2>
    <p>public：<a href="{html.escape(ctx['public_url'])}">{html.escape(ctx['public_url'])}</a><br>
       local：<a href="{html.escape(ctx['local_url'])}">{html.escape(ctx['local_url'])}</a></p>
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
    events = pending_events_from_facts(config, state, facts)
    health = base_health_status(
        config,
        state_path=state_path,
        status_path=status_path,
        env=env,
        dry_run=dry_run,
        facts=facts,
        events=events,
    )
    if dry_run:
        write_status(status_path, health)
        return events

    failed_observed_keys: set[str] = set()
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
    return NotificationEvent(
        route="route_B",
        status="complete",
        subject_status="GOAL_COMPLETE",
        thread_id="test-email",
        objective="CARE controller notification test: terminal packet ready for reviewer",
        updated_at_ms=str(int(time.time() * 1000)),
        source="manual_test",
        source_path="--send-test",
        tmux_target=route_config(config, "route_B").get("tmux_target", ""),
        tokens_used=0,
        time_used_seconds=0,
        packet_paths=route_config(config, "route_B").get("packet_paths", []),
        git_head=git_head(repo_root_from_config(config)),
        detected_at_utc=utc_now(),
        previous_status="manual_test",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.example.json"))
    parser.add_argument("--env-file", type=Path, default=DEFAULT_REPO_ROOT / "secrets" / "care_notify.env")
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
