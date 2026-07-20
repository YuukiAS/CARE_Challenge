from __future__ import annotations

from email.message import EmailMessage
import json
import os
import subprocess
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
        "enabled_routes": ["route_B"],
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


def write_route_packet_fixture(config: dict, tmp_path: Path, route: str = "route_B") -> Path:
    worktree = tmp_path / "CARE_worktrees" / route
    root = worktree / "results" / route
    root.mkdir(parents=True, exist_ok=True)
    config["routes"][route]["worktree"] = str(worktree)
    config["routes"][route]["packet_paths"] = [
        str(root / "controller_report.md"),
        str(root / "completion_check.md"),
    ]
    (root / "result.md").write_text(
        "status: ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW\n"
        "scientific_resolution_status: AWAITING_REVIEW\n"
        "route_promotion_decision: NOT_REVIEWED\n"
        "Slurm job: 111\n",
        encoding="utf-8",
    )
    (root / "completion_check.md").write_text(
        "ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW\nstatus: PASS\n",
        encoding="utf-8",
    )
    (root / "review_request.md").write_text("ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW\n", encoding="utf-8")
    (root / "MANIFEST.md").write_text("manifest\n", encoding="utf-8")
    (root / "controller_report.md").write_text("ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW\nPASS\n", encoding="utf-8")
    (root / "routing_ledger.csv").write_text(
        "timestamp_utc,event,executor,stage,partition,job_id,state,exit_code,output_root,credit,lineage_note\n"
        "2026-07-19T00:00:00Z,submitted,B3,train,htzhulab,111,SUBMITTED,,out,pending,submitted\n"
        "2026-07-19T00:03:00Z,terminal,B3,train,htzhulab,111,COMPLETED,0:0,out,true,sacct elapsed 00:03:00\n"
        "2026-07-19T00:04:00Z,terminal,B3,train,a100-gpu,222,FAILED,2:0,out,zero,sacct elapsed 00:01:30\n"
        "2026-07-19T00:05:00Z,cancel,B3,train,volta-gpu,333,CANCELLED by 123,0:0,out,zero,cancelled while pending\n",
        encoding="utf-8",
    )
    (root / "finalizer_state.json").write_text(
        json.dumps(
            {
                "job_states": {"444": "COMPLETED"},
                "exit_codes": {"444": "0:0"},
                "elapsed": {"444": "00:00:10"},
                "required_job_ids": ["444"],
            }
        ),
        encoding="utf-8",
    )
    return root


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
    config["enabled_routes"] = ["route_B", "route_C"]
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
    root = write_route_packet_fixture(config, tmp_path)
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
            calls.append(("send_message", message))

    monkeypatch.setattr(notify.smtplib, "SMTP", FakeSMTP)
    notify.send_email(
        config,
        {"CARE_NOTIFY_SMTP_USER": "humc2013@gmail.com", "CARE_NOTIFY_SMTP_PASSWORD": "app-password"},
        event,
    )

    assert ("connect", "smtp.gmail.com", 587, 30) in calls
    assert ("starttls",) in calls
    assert ("login", "humc2013@gmail.com", "app-password") in calls
    message = [call[1] for call in calls if call[0] == "send_message"][0]
    assert message["From"] == "humc2013@gmail.com"
    assert "1155246312@link.cuhk.edu.hk" in message["To"]
    assert "[CARE][Route B][GOAL_COMPLETE][等待 reviewer]" in message["Subject"]
    assert message.is_multipart()
    parts = {part.get_content_type(): part.get_content() for part in message.iter_parts()}
    plain = parts["text/plain"]
    html_body = parts["text/html"]

    assert "结论：Route B controller goal 已完成" in plain
    assert "下一步：交 Route B independent reviewer 审" in plain
    assert "Slurm 作业概览" in plain
    assert "结果：COMPLETED 2；FAILED 1；CANCELLED 1" in plain
    assert "计入结果：2" in plain
    assert "可得总运行时长：4分40秒" in plain
    assert "Route 总览" in plain
    assert "Watchboard" in plain
    assert "https://watchboard.httpwwwcardiacnexus-ukb.com/index.html" in plain
    assert "http://127.0.0.1:8766/index.html" in plain
    assert "| --- |" not in plain
    assert "##" not in plain
    assert "event signature" not in plain
    assert "app-password" not in plain
    assert "tunnel secret" not in plain.lower()
    assert str(root) not in plain
    assert "results/route_B/result.md" in plain
    assert "<table" in html_body
    assert "结论" in html_body
    assert "app-password" not in html_body


def test_send_test_dry_run_uses_summary_email_format(tmp_path):
    config_path = tmp_path / "config.json"
    config = make_config(tmp_path)
    write_route_packet_fixture(config, tmp_path)
    config["watchboard_urls"] = {
        "public": "https://watchboard.httpwwwcardiacnexus-ukb.com/index.html",
        "local": "http://127.0.0.1:8766/index.html",
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--config", str(config_path), "--send-test", "--dry-run"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert "[CARE][Route B][GOAL_COMPLETE][等待 reviewer]" in payload["subject"]
    assert "结论：Route B controller goal 已完成" in payload["plain_body"]
    assert "Slurm 作业概览" in payload["plain_body"]
    assert "结果：COMPLETED 2；FAILED 1；CANCELLED 1" in payload["plain_body"]
    assert "Route 总览" in payload["plain_body"]
    assert "Route B：" in payload["plain_body"]
    assert "Route C：" not in payload["plain_body"]
    assert "Watchboard" in payload["plain_body"]
    assert "| --- |" not in payload["plain_body"]
    assert "##" not in payload["plain_body"]
    assert "event signature" not in payload["plain_body"]
    assert "<table" in payload["html_body"]
    assert "https://watchboard.httpwwwcardiacnexus-ukb.com/index.html" in payload["plain_body"]
    assert "CARE_NOTIFY_SMTP_PASSWORD" not in payload["plain_body"]
    assert "app-password" not in payload["plain_body"]


def test_slurm_summary_handles_missing_packet_evidence(tmp_path):
    config = make_config(tmp_path)
    empty_worktree = tmp_path / "CARE_worktrees" / "route_B_empty"
    empty_worktree.mkdir(parents=True)
    config["routes"]["route_B"]["worktree"] = str(empty_worktree)
    config["routes"]["route_B"]["packet_paths"] = [
        str(empty_worktree / "results" / "route_B" / "controller_report.md")
    ]
    event = notify.build_test_event(config)
    summary = notify.summarize_slurm(config, event)

    assert summary.total_jobs == 0
    assert summary.total_elapsed == "未记录"
    assert "packet 未记录 Slurm ledger/finalizer_state" in summary.warnings


def test_important_jobs_keep_credited_completed_elapsed_when_truncated(tmp_path):
    config = make_config(tmp_path)
    config["email"]["max_important_slurm_jobs"] = 4
    worktree = tmp_path / "CARE_worktrees" / "route_B"
    root = worktree / "results" / "route_B"
    root.mkdir(parents=True)
    config["routes"]["route_B"]["worktree"] = str(worktree)
    config["routes"]["route_B"]["packet_paths"] = [str(root / "controller_report.md")]
    (root / "controller_report.md").write_text("ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW\n", encoding="utf-8")
    ledger_lines = ["timestamp_utc,event,executor,stage,partition,job_id,state,exit_code,output_root,credit,lineage_note"]
    for idx in range(10):
        ledger_lines.append(
            f"2026-07-19T00:{idx:02d}:00Z,terminal,B{idx},train,a100-gpu,{7000 + idx},FAILED,2:0,out,zero,sacct elapsed 00:00:0{idx % 10}"
        )
    ledger_lines.append(
        "2026-07-19T01:00:00Z,terminal,B10,train,htzhulab,9999,COMPLETED,0:0,out,true,sacct elapsed 02:03:04"
    )
    (root / "routing_ledger.csv").write_text("\n".join(ledger_lines) + "\n", encoding="utf-8")

    event = notify.build_test_event(config)
    summary = notify.summarize_slurm(config, event)
    important_ids = [job.job_id for job in summary.important_jobs]
    assert "9999" in important_ids
    completed = next(job for job in summary.important_jobs if job.job_id == "9999")
    assert completed.state == "COMPLETED"
    assert completed.credited is True
    assert completed.elapsed == "02:03:04"
    assert len(summary.important_jobs) == 4
    assert any("未省略 credited COMPLETED job" in warning for warning in summary.warnings)

    plain = notify.render_plain_email(config, event)
    html_body = notify.render_html_email(config, event)
    assert "job 9999" in plain
    assert "耗时 02:03:04" in plain
    assert "计入结果" in plain
    assert "job 9999" in html_body
    assert "02:03:04" in html_body


def test_slurm_elapsed_parser_handles_route_ledger_notes():
    assert notify.extract_elapsed_from_note("allocated then failed after 00:00:05 before receipt") == "00:00:05"
    assert notify.extract_elapsed_from_note("6000 steps completed but train_loop_seconds 300.9 < 1800") == "00:05:01"
    assert notify.extract_elapsed_from_note("62346 steps and 1801.4 seconds completed") == "00:30:01"


def test_load_config_defaults_to_route_b_only(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"routes": {"route_B": {}}}), encoding="utf-8")
    loaded = notify.load_config(config_path)
    assert loaded["enabled_routes"] == ["route_B"]


def test_explicit_route_c_enabled_remains_backward_compatible(tmp_path):
    config = make_config(tmp_path)
    config["enabled_routes"] = ["route_B", "route_C"]
    db = tmp_path / "runtime" / "route_C_tmux_care_route_C__care_route_C" / "goals_1.sqlite"
    write_goal_db(db, "active", updated_at_ms=1)
    facts = notify.collect_goal_facts(config, capture_func=lambda target, root: "")
    assert any(fact.route == "route_C" for fact in facts)

def test_health_status_written_on_scan(tmp_path):
    config = make_config(tmp_path)
    db = tmp_path / "runtime" / "route_B_tmux_care_route_B__care_route_B" / "goals_1.sqlite"
    state_path = Path(config["state_path"])
    status_path = tmp_path / "state" / "notify_goal_watcher_status.json"

    write_goal_db(db, "active", updated_at_ms=1)
    notify.run_once(config, state_path=state_path, status_path=status_path, env={}, sender=Sender(), capture_func=lambda target, root: "")

    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["service"] == "controller_goal_notifier"
    assert status["last_scan_at_utc"]
    assert status["enabled_routes"] == ["route_B"]
    assert status["facts_count"] == 1
    assert status["state_path"] == str(state_path)
    assert status["status_path"] == str(status_path)
    assert status["smtp"]["smtp_password_present"] is False
    assert "CARE_NOTIFY_SMTP_PASSWORD is missing" in status["config_warnings"]


def test_email_failure_records_status_and_retries_next_scan(tmp_path):
    config = make_config(tmp_path)
    db = tmp_path / "runtime" / "route_B_tmux_care_route_B__care_route_B" / "goals_1.sqlite"
    state_path = Path(config["state_path"])
    status_path = tmp_path / "state" / "notify_goal_watcher_status.json"
    sender = Sender()

    write_goal_db(db, "active", updated_at_ms=1)
    notify.run_once(config, state_path=state_path, status_path=status_path, env={}, sender=sender)
    write_goal_db(db, "complete", updated_at_ms=2)

    def failing_sender(config, env, event):
        raise OSError("smtp temporary down")

    events = notify.run_once(
        config,
        state_path=state_path,
        status_path=status_path,
        env={"CARE_NOTIFY_SMTP_USER": "user", "CARE_NOTIFY_SMTP_PASSWORD": "password"},
        sender=failing_sender,
    )
    assert len(events) == 1
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["last_email_status"] == "failed"
    assert status["failed_email_count"] == 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["notified"] == {}
    assert state["observed"]["route_B|sqlite|thread-route-b"]["status"] == "active"

    events = notify.run_once(
        config,
        state_path=state_path,
        status_path=status_path,
        env={"CARE_NOTIFY_SMTP_USER": "user", "CARE_NOTIFY_SMTP_PASSWORD": "password"},
        sender=sender,
    )
    assert len(events) == 1
    assert len(sender.events) == 1
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["last_email_status"] == "sent"
    assert status["sent_email_count"] == 1


def test_missing_smtp_config_records_blocked_config_without_crashing(tmp_path):
    config = make_config(tmp_path)
    config["enabled_routes"] = ["route_B", "route_C"]
    db = tmp_path / "runtime" / "route_C_tmux_care_route_C__care_route_C" / "goals_1.sqlite"
    state_path = Path(config["state_path"])
    status_path = tmp_path / "state" / "notify_goal_watcher_status.json"

    write_goal_db(db, "active", updated_at_ms=1)
    notify.run_once(config, state_path=state_path, status_path=status_path, env={})
    write_goal_db(db, "blocked", updated_at_ms=2)
    events = notify.run_once(config, state_path=state_path, status_path=status_path, env={})

    assert len(events) == 1
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["last_email_status"] == "blocked_config"
    assert status["last_event"]["status"] == "blocked"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["notified"] == {}


def test_existing_terminal_goal_baselines_without_backfill(tmp_path):
    config = make_config(tmp_path)
    db = tmp_path / "runtime" / "route_B_tmux_care_route_B__care_route_B" / "goals_1.sqlite"
    state_path = Path(config["state_path"])
    status_path = tmp_path / "state" / "notify_goal_watcher_status.json"
    sender = Sender()

    write_goal_db(db, "complete", updated_at_ms=1)
    events = notify.run_once(config, state_path=state_path, status_path=status_path, env={}, sender=sender)

    assert events == []
    assert sender.events == []
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["observed"]["route_B|sqlite|thread-route-b"]["status"] == "complete"
    assert state["notified"] == {}


def test_start_in_tmux_dry_run_no_duplicate_and_dead_restart(tmp_path):
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    care_root = tmp_path / "CARE"
    python_path = care_root / "envs" / "env_CARE" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    python_path.chmod(0o755)

    tmux = fakebin / "tmux"
    tmux.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"has-session\" ]]; then exit 0; fi\n"
        "if [[ \"$1\" == \"list-windows\" ]]; then echo Notify; exit 0; fi\n"
        "echo unexpected tmux $* >&2; exit 1\n",
        encoding="utf-8",
    )
    tmux.chmod(0o755)
    ps = fakebin / "ps"
    ps.write_text(
        f"#!/usr/bin/env bash\n"
        f"if [[ \"${{CARE_FAKE_WATCHER_RUNNING:-0}}\" == \"1\" ]]; then echo '{python_path} {care_root}/controller_notifications/notify_goal_watcher.py --loop --poll-seconds 60'; fi\n",
        encoding="utf-8",
    )
    ps.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{fakebin}:{os.environ['PATH']}",
        "CARE_ROOT": str(care_root),
        "CARE_FAKE_WATCHER_RUNNING": "1",
        "USER": "aereinh",
    }
    script = Path(__file__).resolve().parents[2] / "controller_notifications" / "start_in_tmux.sh"

    running = subprocess.run(["bash", str(script), "--dry-run"], env=env, text=True, capture_output=True, check=False)
    assert running.returncode == 0
    assert "watcher already running" in running.stdout
    assert "new-window" not in running.stdout

    env["CARE_FAKE_WATCHER_RUNNING"] = "0"
    dead = subprocess.run(["bash", str(script), "--dry-run"], env=env, text=True, capture_output=True, check=False)
    assert dead.returncode == 0
    assert "tmux respawn-window -k -t care_watchboard:Notify" in dead.stdout



def test_route_summary_defaults_to_enabled_route_b_only(tmp_path):
    config = make_config(tmp_path)
    rows = notify.route_summary_rows(config, "route_B", {"routes": []})
    assert [row["route"] for row in rows] == ["Route B"]

    config["enabled_routes"] = ["route_B", "route_C"]
    rows = notify.route_summary_rows(config, "route_C", {"routes": []})
    assert [row["route"] for row in rows] == ["Route B", "Route C"]


def test_route_summary_uses_watchboard_dynamic_status(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    config["enabled_routes"] = ["route_A", "route_B", "route_C"]
    status = {
        "routes": [
            {
                "id": "route_A",
                "label": "Route A",
                "sha": "fae8a732bbf625db367e0b68c04f1490d0c97be3",
                "origin_sha": "fae8a732bbf625db367e0b68c04f1490d0c97be3",
                "dirty_count": 0,
                "ahead_behind_main": "0\t0",
                "current_worker_zh": "非当前 active route",
                "display_state_zh": "Dormant fallback / inactive unless explicitly reauthorized",
                "next_action_zh": "保持只读观察",
            },
            {
                "id": "route_B",
                "label": "Route B",
                "sha": "b9c7664da7cb1f1892fff37a4497722f31a0a96d",
                "origin_sha": "b9c7664da7cb1f1892fff37a4497722f31a0a96d",
                "dirty_count": 0,
                "ahead_behind_main": "56\t58",
                "current_worker_zh": "等待 coordinator receipt / Route B critic rereview",
                "display_state_zh": "Round04 planning needs revision / controller blocked",
                "next_action_zh": "GPT Planner / planner revision",
            },
            {
                "id": "route_C",
                "label": "Route C",
                "sha": "17062b00edc3443aacefe8583568797a9f2655ba",
                "origin_sha": "17062b00edc3443aacefe8583568797a9f2655ba",
                "dirty_count": 0,
                "ahead_behind_main": "56\t60",
                "current_worker_zh": "当前不需要 critic/reviewer/controller",
                "display_state_zh": "Reviewed evidence-complete / waiting portfolio reconciliation",
                "next_action_zh": "等待 GPT Planner 做 portfolio reconciliation",
            },
        ]
    }
    monkeypatch.setattr(notify, "collect_watchboard_status", lambda cfg: status)
    event = notify.build_test_event(config)
    plain = notify.render_plain_email(config, event)

    assert "Route A：branch fae8a73 / origin fae8a73" in plain
    assert "Dormant fallback / inactive unless explicitly reauthorized" in plain
    assert "Round04 planning needs revision / controller blocked" in plain
    assert "Reviewed evidence-complete / waiting portfolio reconciliation" in plain
    assert "terminal event observed / 等待 independent reviewer" not in plain
    assert "not triggered / 按 route packet 判定" not in plain
