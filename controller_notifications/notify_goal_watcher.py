#!/usr/bin/env python3
"""Email on Route B/C Codex controller goal terminal transitions."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
import hashlib
import json
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root_from_config(config: dict[str, Any]) -> Path:
    return Path(config.get("repo_root") or DEFAULT_REPO_ROOT)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(path: Path) -> dict[str, Any]:
    config = load_json(path)
    config.setdefault("enabled_routes", ["route_B", "route_C"])
    config.setdefault("repo_root", str(DEFAULT_REPO_ROOT))
    config.setdefault("codex_runtime_root", "/users/a/e/aereinh/.codex-runtime-homes")
    config.setdefault("state_path", "controller_notifications/state/notified_goals.json")
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


def state_path_from_config(config: dict[str, Any], override: Path | None = None) -> Path:
    if override is not None:
        return override
    path = Path(config.get("state_path", "controller_notifications/state/notified_goals.json"))
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
    for route in config.get("enabled_routes", ["route_B", "route_C"]):
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


def update_observed_state(state: dict[str, Any], facts: list[GoalFact]) -> None:
    for fact in facts:
        state["observed"][observed_key(fact)] = {
            "route": fact.route,
            "source": fact.source,
            "source_path": fact.source_path,
            "thread_id": fact.thread_id,
            "status": fact.status,
            "updated_at_ms": fact.updated_at_ms,
            "seen_at_utc": utc_now(),
        }


def subject_for_event(config: dict[str, Any], event: NotificationEvent) -> str:
    prefix = config.get("email", {}).get("subject_prefix", "[CARE]")
    return f"{prefix}[{event.route}][{event.subject_status}] controller goal {event.status}"


def body_for_event(event: NotificationEvent) -> str:
    packet_lines = "\n".join(f"- {path}" for path in event.packet_paths) or "- none configured"
    return "\n".join(
        [
            f"route: {event.route}",
            f"goal_status: {event.status}",
            f"previous_status: {event.previous_status}",
            f"thread_id: {event.thread_id}",
            f"objective: {event.objective[:500]}",
            f"updated_at_ms_or_signature: {event.updated_at_ms}",
            f"detected_at_utc: {event.detected_at_utc}",
            f"source: {event.source}",
            f"source_path: {event.source_path}",
            f"tmux_target: {event.tmux_target}",
            f"tokens_used: {event.tokens_used}",
            f"time_used_seconds: {event.time_used_seconds}",
            f"git_head: {event.git_head}",
            "packet_paths:",
            packet_lines,
            "",
        ]
    )


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
    message.set_content(body_for_event(event))

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
    env: dict[str, str] | None = None,
    dry_run: bool = False,
    sender: Callable[[dict[str, Any], dict[str, str], NotificationEvent], None] = send_email,
    capture_func: Callable[[str, Path], str] = capture_tmux_pane,
) -> list[NotificationEvent]:
    state = load_state(state_path)
    facts = collect_goal_facts(config, capture_func=capture_func)
    events = pending_events_from_facts(config, state, facts)
    if dry_run:
        return events
    env = env or {}
    for event in events:
        sender(config, env, event)
        state["notified"][event.key] = {
            "route": event.route,
            "status": event.status,
            "thread_id": event.thread_id,
            "sent_at_utc": utc_now(),
            "source": event.source,
            "source_path": event.source_path,
        }
    update_observed_state(state, facts)
    write_state(state_path, state)
    return events


def build_test_event(config: dict[str, Any]) -> NotificationEvent:
    return NotificationEvent(
        route="route_B",
        status="complete",
        subject_status="GOAL_COMPLETE",
        thread_id="test-email",
        objective="CARE controller notification test",
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
    env = load_env_file(args.env_file)

    if args.send_test:
        event = build_test_event(config)
        if args.dry_run:
            print(json.dumps({"send_test": asdict(event)}, indent=2, sort_keys=True))
            return 0
        send_email(config, env, event)
        print("sent test email")
        return 0

    poll_seconds = args.poll_seconds or int(config.get("poll_seconds", 60))
    loop = args.loop and not args.once
    while True:
        events = run_once(config, state_path=state_path, env=env, dry_run=args.dry_run)
        print(
            json.dumps(
                {
                    "checked_at_utc": utc_now(),
                    "dry_run": args.dry_run,
                    "events": [asdict(event) for event in events],
                    "state_path": str(state_path),
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
