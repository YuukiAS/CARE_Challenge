from __future__ import annotations

from email.message import EmailMessage
import importlib.util
from pathlib import Path
import sqlite3
import sys


MODULE_PATH = Path(__file__).resolve().parents[2] / "controller_notifications" / "notify_goal_watcher.py"
spec = importlib.util.spec_from_file_location("notify_goal_watcher", MODULE_PATH)
notify = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = notify
spec.loader.exec_module(notify)


def make_config(tmp_path: Path) -> dict:
    runtime = tmp_path / "runtime"
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    return {
        "enabled_routes": ["route_B", "route_C"],
        "repo_root": str(repo),
        "codex_runtime_root": str(runtime),
        "state_path": str(tmp_path / "state" / "notified_goals.json"),
        "email": {
            "from": "humc2013@gmail.com",
            "to": ["1155246312@link.cuhk.edu.hk"],
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "starttls": True,
            "subject_prefix": "[CARE]",
        },
        "routes": {
            "route_B": {
                "tmux_target": "care_route_B:RouteB-Controller",
                "runtime_home_candidates": [
                    "route_B_tmux_care_route_B__care_route_B",
                    "route_B_tmux_care_route_B_controller__care_route_B_controller",
                ],
                "packet_paths": ["results/route_B/controller_report.md"],
            },
            "route_C": {
                "tmux_target": "care_route_C:RouteC-Controller",
                "runtime_home_candidates": [
                    "route_C_tmux_care_route_C__care_route_C",
                    "route_C_tmux_care_route_C_controller__care_route_C_controller",
                ],
                "packet_paths": ["results/route_C/controller_report.md"],
            },
        },
    }


def write_goal_db(db_path: Path, status: str, updated_at_ms: int = 1) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        drop table if exists thread_goals;
        create table thread_goals (
            thread_id text primary key not null,
            goal_id text not null,
            objective text not null,
            status text not null,
            token_budget integer,
            tokens_used integer not null default 0,
            time_used_seconds integer not null default 0,
            created_at_ms integer not null,
            updated_at_ms integer not null
        );
        """
    )
    conn.execute(
        """
        insert into thread_goals
        (thread_id, goal_id, objective, status, token_budget, tokens_used, time_used_seconds, created_at_ms, updated_at_ms)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("thread-route-b", "goal-1", "RouteB controller objective", status, None, 123, 45, 1, updated_at_ms),
    )
    conn.commit()
    conn.close()


class Sender:
    def __init__(self) -> None:
        self.events = []

    def __call__(self, config, env, event) -> None:
        self.events.append(event)


def test_active_to_complete_sends_once(tmp_path):
    config = make_config(tmp_path)
    db = tmp_path / "runtime" / "route_B_tmux_care_route_B__care_route_B" / "goals_1.sqlite"
    state_path = Path(config["state_path"])
    sender = Sender()

    write_goal_db(db, "active", updated_at_ms=1)
    assert notify.run_once(config, state_path=state_path, env={}, sender=sender) == []

    write_goal_db(db, "complete", updated_at_ms=2)
    events = notify.run_once(config, state_path=state_path, env={}, sender=sender)
    assert len(events) == 1
    assert events[0].route == "route_B"
    assert events[0].status == "complete"
    assert events[0].subject_status == "GOAL_COMPLETE"
    assert len(sender.events) == 1

    assert notify.run_once(config, state_path=state_path, env={}, sender=sender) == []
    assert len(sender.events) == 1


def test_active_to_blocked_sends_once(tmp_path):
    config = make_config(tmp_path)
    db = tmp_path / "runtime" / "route_C_tmux_care_route_C__care_route_C" / "goals_1.sqlite"
    state_path = Path(config["state_path"])
    sender = Sender()

    write_goal_db(db, "active", updated_at_ms=1)
    notify.run_once(config, state_path=state_path, env={}, sender=sender)
    write_goal_db(db, "blocked", updated_at_ms=2)

    events = notify.run_once(config, state_path=state_path, env={}, sender=sender)
    assert len(events) == 1
    assert events[0].route == "route_C"
    assert events[0].subject_status == "GOAL_BLOCKED"


def test_non_notified_statuses_do_not_send(tmp_path):
    for status in ("paused", "usage_limited", "budget_limited"):
        config = make_config(tmp_path / status)
        db = Path(config["codex_runtime_root"]) / "route_B_tmux_care_route_B__care_route_B" / "goals_1.sqlite"
        sender = Sender()
        write_goal_db(db, "active", updated_at_ms=1)
        notify.run_once(config, state_path=Path(config["state_path"]), env={}, sender=sender)
        write_goal_db(db, status, updated_at_ms=2)
        events = notify.run_once(config, state_path=Path(config["state_path"]), env={}, sender=sender)
        assert events == []
        assert sender.events == []


def test_discovers_old_and_new_runtime_home_paths(tmp_path):
    config = make_config(tmp_path)
    runtime = Path(config["codex_runtime_root"])
    new_db = runtime / "route_B_tmux_care_route_B__care_route_B" / "goals_1.sqlite"
    old_db = runtime / "route_B_tmux_care_route_B_controller__care_route_B_controller" / "goals_1.sqlite"
    write_goal_db(new_db, "active", updated_at_ms=1)
    write_goal_db(old_db, "active", updated_at_ms=1)

    discovered = notify.route_runtime_goal_dbs(config, "route_B")
    assert new_db in discovered
    assert old_db in discovered


def test_parse_pane_goal_status_markers():
    assert notify.parse_pane_goal_status("Goal achieved (22m)") == "complete"
    assert notify.parse_pane_goal_status("status: blocked\nneeds user input") == "blocked"
    assert notify.parse_pane_goal_status("controller still running") == "active"


def test_pane_fallback_transition_and_dedupe(tmp_path):
    config = make_config(tmp_path)
    config["enabled_routes"] = ["route_B"]
    state_path = Path(config["state_path"])
    sender = Sender()

    def active_capture(target, root):
        return "controller running"

    def complete_capture(target, root):
        return "final response\nGoal achieved (22m)"

    notify.run_once(config, state_path=state_path, env={}, sender=sender, capture_func=active_capture)
    events = notify.run_once(config, state_path=state_path, env={}, sender=sender, capture_func=complete_capture)
    assert len(events) == 1
    assert events[0].source == "tmux_pane"
    assert len(sender.events) == 1

    assert notify.run_once(config, state_path=state_path, env={}, sender=sender, capture_func=complete_capture) == []
    assert len(sender.events) == 1


def test_dry_run_returns_event_without_sending_or_writing_state(tmp_path):
    config = make_config(tmp_path)
    db = tmp_path / "runtime" / "route_B_tmux_care_route_B__care_route_B" / "goals_1.sqlite"
    state_path = Path(config["state_path"])
    sender = Sender()
    write_goal_db(db, "active", updated_at_ms=1)
    notify.run_once(config, state_path=state_path, env={}, sender=sender)

    before = state_path.read_text(encoding="utf-8")
    write_goal_db(db, "complete", updated_at_ms=2)
    events = notify.run_once(config, state_path=state_path, env={}, sender=sender, dry_run=True)

    assert len(events) == 1
    assert sender.events == []
    assert state_path.read_text(encoding="utf-8") == before


def test_send_email_uses_starttls_login_and_recipient(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    event = notify.build_test_event(config)
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            calls.append(("starttls",))

        def login(self, user, password):
            calls.append(("login", user, password))

        def send_message(self, message: EmailMessage):
            calls.append(("send_message", message["From"], message["To"], message["Subject"], message.get_content()))

    monkeypatch.setattr(notify.smtplib, "SMTP", FakeSMTP)
    notify.send_email(
        config,
        {"CARE_NOTIFY_SMTP_USER": "humc2013@gmail.com", "CARE_NOTIFY_SMTP_PASSWORD": "app-password"},
        event,
    )

    assert ("connect", "smtp.gmail.com", 587, 30) in calls
    assert ("starttls",) in calls
    assert ("login", "humc2013@gmail.com", "app-password") in calls
    sent = [call for call in calls if call[0] == "send_message"][0]
    assert sent[1] == "humc2013@gmail.com"
    assert "1155246312@link.cuhk.edu.hk" in sent[2]
    assert "[CARE][route_B][GOAL_COMPLETE]" in sent[3]
    assert "route: route_B" in sent[4]
