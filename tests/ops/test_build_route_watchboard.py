from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ops" / "build_route_watchboard.py"
spec = importlib.util.spec_from_file_location("build_route_watchboard", MODULE_PATH)
watchboard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(watchboard)


def route_fixture(**overrides):
    route = {
        "id": "route_A",
        "label": "Route A",
        "status_keywords": [],
        "packet_files": {
            "result": False,
            "controller_report": False,
            "manifest": False,
            "review": False,
            "completion_check": False,
            "review_request": False,
        },
        "slurm_job_ids": [],
        "recent_slurm_jobs": [],
        "controller_tmux": "care_route_A_controller",
        "reviewer_tmux": "care_route_A_reviewer",
        "dirty_count": 0,
        "current_status": "setup only",
        "result_root_exists": False,
    }
    route.update(overrides)
    return route


def test_parse_squeue_marks_route_and_general_jobs():
    rows = watchboard.parse_squeue(
        "12345|aereinh|htzhulab|route_A_train|RUNNING|00:03|node1\n"
        "22222|aereinh|general|care-watchboard-tunnel|PENDING|0:00|Priority"
    )

    assert rows[0]["is_route_job"] is True
    assert rows[0]["source"] == "squeue"
    assert rows[1]["is_general"] is True


def test_parse_sacct_normalizes_state_and_marks_route():
    rows = watchboard.parse_sacct(
        "12345|route_B_eval|a100-gpu|COMPLETED|0:0|00:10:00|2026-07-16T01:00:00|2026-07-16T01:10:00\n"
        "12346|other|general|CANCELLED by 123|0:15|00:00:05|2026-07-16T01:00:00|2026-07-16T01:00:05"
    )

    assert rows[0]["state"] == "COMPLETED"
    assert rows[0]["is_route_job"] is True
    assert rows[0]["exit_code"] == "0:0"
    assert rows[1]["state"] == "CANCELLED"
    assert rows[1]["is_general"] is True


def test_extract_status_keywords_and_slurm_job_ids():
    text = "sbatch submitted job 57617442 and status JOB_SUBMITTED then AWAITING_SACCT"

    assert watchboard.extract_status_keywords(text) == ["JOB_SUBMITTED", "AWAITING_SACCT"]
    assert watchboard.extract_slurm_job_ids(text) == ["57617442"]


def test_parse_current_handoff_tracks_round_and_route_critic(tmp_path):
    root = tmp_path / "CARE"
    planner = root / "prompts" / "routes" / "handoffs" / "portfolio_round02_planner_handoff_20260716.md"
    critic = root / "prompts" / "routes" / "handoffs" / "route_A_round02_critic_handoff_20260716.md"
    critic.parent.mkdir(parents=True)
    planner.write_text("planner", encoding="utf-8")
    critic.write_text("critic", encoding="utf-8")
    current_text = """# Current\n\n```text\nround_id: round02\ndate: 2026-07-16\n```\n\nThe single portfolio GPT planner should read:\n\n```text\nprompts/routes/handoffs/portfolio_round02_planner_handoff_20260716.md\n```\n\nroute_A critic current prompt:\nprompts/routes/handoffs/route_A_round02_critic_handoff_20260716.md\n\nroute_B critic current prompt:\nNO_CURRENT_CRITIC_HANDOFF\n\nroute_C critic current prompt:\nNO_CURRENT_CRITIC_HANDOFF\n"""

    parsed = watchboard.parse_current_handoff(current_text, root)

    assert parsed["round_id"] == "round02"
    assert parsed["date"] == "2026-07-16"
    assert parsed["planner_prompt"]["exists"] is True
    assert parsed["critics"]["route_A"]["active"] is True
    assert parsed["critics"]["route_A"]["exists"] is True
    assert parsed["critics"]["route_B"]["active"] is False


def test_handoff_worker_annotation_prefers_published_route_critic(tmp_path):
    root = tmp_path / "CARE"
    critic = root / "prompts" / "routes" / "handoffs" / "route_A_round03_critic_handoff_20260716.md"
    critic.parent.mkdir(parents=True)
    critic.write_text("critic", encoding="utf-8")
    handoff = {
        "round_id": "round03",
        "critics": {
            "route_A": watchboard.relative_repo_path(root, "prompts/routes/handoffs/route_A_round03_critic_handoff_20260716.md"),
            "route_B": watchboard.relative_repo_path(root, "NO_CURRENT_CRITIC_HANDOFF"),
            "route_C": watchboard.relative_repo_path(root, "NO_CURRENT_CRITIC_HANDOFF"),
        },
    }
    route = route_fixture(display_state_zh="需修订")

    watchboard.annotate_handoff_workers(route, handoff)

    assert route["round_id"] == "round03"
    assert route["critic_handoff_state_zh"] == "已发布"
    assert route["current_worker_zh"] == "GPT Critic (Route A)"
    assert "GPT Planner" in route["next_worker_zh"]


def test_pending_packet_blocks_completion_review():
    route = route_fixture(status_keywords=["JOB_SUBMITTED"], slurm_job_ids=["12345"])
    jobs = [
        {
            "id": "12345",
            "partition": "htzhulab",
            "name": "route_A_train",
            "state": "PENDING",
            "time": "0:00",
            "reason": "Priority",
            "source": "squeue",
        }
    ]

    watchboard.annotate_route_runtime(route, {"care_route_A_controller": False}, jobs, [])

    assert route["display_state_zh"] == "Slurm 排队中"
    assert route["reviewability"]["can_review_complete"] is False
    assert any("JOB_SUBMITTED" in blocker for blocker in route["completion_blockers"])


def test_running_packet_blocks_completion_review():
    route = route_fixture(status_keywords=["RUNNING"], slurm_job_ids=["12345"])
    jobs = [
        {
            "id": "12345",
            "partition": "htzhulab",
            "name": "route_A_train",
            "state": "RUNNING",
            "time": "00:03",
            "reason": "node1",
            "source": "squeue",
        }
    ]

    watchboard.annotate_route_runtime(route, {"care_route_A_controller": False}, jobs, [])

    assert route["display_state_zh"] == "Slurm 运行中"
    assert route["reviewability"]["label_zh"] == "不可作为完成包审查"


def test_awaiting_sacct_has_explicit_state():
    route = route_fixture(status_keywords=["AWAITING_SACCT"])

    watchboard.annotate_route_runtime(route, {"care_route_A_controller": False}, [], [])

    assert route["display_state_zh"] == "等待 sacct"
    assert route["reviewability"]["can_review_complete"] is False


def test_needs_evidence_and_review_states():
    needs_evidence = route_fixture(status_keywords=["NEEDS_EVIDENCE"])
    review_pending = route_fixture(status_keywords=["AWAITING_REVIEW"], packet_files={**route_fixture()["packet_files"], "review_request": True})
    review_pass = route_fixture(status_keywords=["PASS", "COMPLETE"], packet_files={**route_fixture()["packet_files"], "review": True})
    review_fail = route_fixture(status_keywords=["FAIL"], packet_files={**route_fixture()["packet_files"], "review": True})

    for route in (needs_evidence, review_pending, review_pass, review_fail):
        watchboard.annotate_route_runtime(route, {"care_route_A_controller": False}, [], [])

    assert needs_evidence["display_state_zh"] == "需补证据"
    assert review_pending["display_state_zh"] == "待独立审查"
    assert review_pending["reviewability"]["can_review_complete"] is True
    assert review_pass["display_state_zh"] == "审查通过"
    assert review_fail["display_state_zh"] == "审查未通过"


def test_setup_only_route_state():
    route = route_fixture(current_status="setup only")

    watchboard.annotate_route_runtime(route, {"care_route_A_controller": False}, [], [])

    assert route["display_state_zh"] == "仅环境搭建"
    assert route["reviewability"]["can_review_complete"] is False


def test_care_partition_summary_excludes_general_and_keeps_htzhulab():
    rows = watchboard.parse_sinfo(
        "PARTITION|AVAIL|TIMELIMIT|NODES|STATE|GRES\n"
        "general*|up|11-00:00:00|2|idle|(null)\n"
        "general_big|up|11-00:00:00|1|mix|(null)\n"
        "htzhulab|up|11-00:00:00|1|mix-|gpu:nvidia_a100-sxm4-80gb:8\n"
        "a100-gpu|up|6-00:00:00|8|mix|gpu:nvidia_a100-pcie-40gb:3\n"
    )

    summary = watchboard.care_partition_summary(rows)

    assert [row["partition_key"] for row in summary] == ["htzhulab", "a100-gpu", "volta-gpu"]
    assert summary[0]["partition"] == "htzhulab"
    assert summary[0]["gres"] == "gpu:nvidia_a100-sxm4-80gb:8"
    assert summary[2]["state"] == "NO_SINFO_ROW"
    assert all("general" not in row["partition"] for row in summary)


def test_collect_status_uses_partition_specific_squeue_when_global_empty(monkeypatch):
    def fake_collect_route(root, worktree_root, route):
        return route_fixture(id=route, label=watchboard.ROUTE_LABELS[route], controller_tmux=f"care_{route}_controller")

    def fake_collect_tmux(root, sessions):
        return {session: False for session in sessions}

    def fake_run_cmd(args, cwd, timeout=8):
        command = args[0]
        if command == "squeue" and "-p" in args:
            partition = args[args.index("-p") + 1]
            if partition == "htzhulab":
                return {"ok": True, "stdout": "98765|aereinh|htzhulab|route_A_train|RUNNING|00:10|node-a", "stderr": "", "code": 0}
            return {"ok": True, "stdout": "", "stderr": "", "code": 0}
        if command == "squeue":
            return {"ok": True, "stdout": "", "stderr": "", "code": 0}
        if command == "sinfo" and "-p" in args:
            partition = args[args.index("-p") + 1]
            if partition == "htzhulab":
                return {"ok": True, "stdout": "PARTITION|AVAIL|TIMELIMIT|NODES|STATE|GRES\nhtzhulab|up|11-00:00:00|1|mix-|gpu:nvidia_a100-sxm4-80gb:8", "stderr": "", "code": 0}
            return {"ok": True, "stdout": "PARTITION|AVAIL|TIMELIMIT|NODES|STATE|GRES", "stderr": "", "code": 0}
        if command == "sinfo":
            return {"ok": True, "stdout": "PARTITION|AVAIL|TIMELIMIT|NODES|STATE|GRES\ngeneral*|up|11-00:00:00|1|idle|(null)", "stderr": "", "code": 0}
        if command == "sacct":
            return {"ok": True, "stdout": "", "stderr": "", "code": 0}
        if args[:2] == ["git", "branch"]:
            return {"ok": True, "stdout": "main", "stderr": "", "code": 0}
        return {"ok": True, "stdout": "sha", "stderr": "", "code": 0}

    monkeypatch.setattr(watchboard, "collect_route", fake_collect_route)
    monkeypatch.setattr(watchboard, "collect_tmux", fake_collect_tmux)
    monkeypatch.setattr(watchboard, "run_cmd", fake_run_cmd)

    status = watchboard.collect_status(Path("/tmp"), Path("/tmp/worktrees"), "aereinh")

    assert len(status["jobs"]) == 1
    assert status["jobs"][0]["partition"] == "htzhulab"
    assert status["route_jobs"][0]["id"] == "98765"
    assert status["routes"][0]["display_state_zh"] == "Slurm 运行中"
    assert [row["partition_key"] for row in status["partitions"]] == ["htzhulab", "a100-gpu", "volta-gpu"]


def test_collect_route_uses_new_route_session_over_legacy_tmux_fields(tmp_path, monkeypatch):
    root = tmp_path / "CARE"
    worktree_root = tmp_path / "worktrees"
    route_dir = root / "routes" / "route_A"
    route_dir.mkdir(parents=True)
    worktree = worktree_root / "route_A"
    worktree.mkdir(parents=True)
    (route_dir / "README.md").write_text(
        "# Route A\n\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        "| worktree | {worktree} |\n"
        "| controller tmux | care_route_A_controller |\n"
        "| reviewer tmux | care_route_A_reviewer |\n"
        "| current status | setup only |\n"
        .format(worktree=worktree),
        encoding="utf-8",
    )

    def fake_run_cmd(args, cwd, timeout=8):
        if args[:2] == ["git", "rev-parse"]:
            return {"ok": True, "stdout": "sha", "stderr": "", "code": 0}
        if args[:2] == ["git", "rev-list"]:
            return {"ok": True, "stdout": "0\t0", "stderr": "", "code": 0}
        if args[:3] == ["git", "-C", str(worktree)]:
            return {"ok": True, "stdout": "", "stderr": "", "code": 0}
        return {"ok": True, "stdout": "", "stderr": "", "code": 0}

    monkeypatch.setattr(watchboard, "run_cmd", fake_run_cmd)

    route = watchboard.collect_route(root, worktree_root, "route_A")

    assert route["controller_tmux"] == "care_route_A"
    assert route["reviewer_tmux"] == "care_route_A"
    assert route["legacy_controller_tmux"] == "care_route_A_controller"
    assert route["controller_tmux_target"] == "care_route_A:RouteA-Controller.0"


def test_tmux_topology_tracks_expected_route_windows(monkeypatch):
    def fake_run_cmd(args, cwd, timeout=8):
        if args[:3] == ["tmux", "list-panes", "-a"]:
            return {
                "ok": True,
                "stdout": (
                    "care_route_A|RouteA-Controller|0|route_A|node\n"
                    "care_route_A|RouteA-Continue|0|route_A|node\n"
                    "care_route_A|RouteA-Exec|0|c151417|bash\n"
                ),
                "stderr": "",
                "code": 0,
            }
        if args[:3] == ["tmux", "list-windows", "-t"]:
            session = args[3]
            if session == "care_route_A":
                return {
                    "ok": True,
                    "stdout": "0|RouteA-Controller|node\n1|RouteA-Continue|node\n2|RouteA-Exec|bash",
                    "stderr": "",
                    "code": 0,
                }
            return {"ok": True, "stdout": "", "stderr": "", "code": 0}
        return {"ok": False, "stdout": "", "stderr": "unexpected", "code": 1}

    monkeypatch.setattr(watchboard, "run_cmd", fake_run_cmd)

    topology = watchboard.collect_tmux_topology(Path("/tmp"), {"care_route_A": True})
    route_a = next(item for item in topology if item["session"] == "care_route_A")

    assert route_a["present"] is True
    assert route_a["window_status"]["RouteA-Controller"] is True
    assert route_a["window_status"]["RouteA-Continue"] is True
    assert route_a["window_status"]["RouteA-Exec"] is True
    assert route_a["window_status"]["RouteA-Reviewer"] is False
    assert route_a["panes"][0]["command"] == "node"


def test_collect_status_degrades_when_slurm_commands_fail(monkeypatch):
    def fake_collect_route(root, worktree_root, route):
        return route_fixture(id=route, label=watchboard.ROUTE_LABELS[route], controller_tmux=f"care_{route}_controller")

    def fake_collect_tmux(root, sessions):
        return {session: False for session in sessions}

    def fake_run_cmd(args, cwd, timeout=8):
        command = args[0]
        if command in {"squeue", "sinfo", "sacct"}:
            return {"ok": False, "stdout": "", "stderr": f"{command} unavailable", "code": 127}
        if args[:2] == ["git", "branch"]:
            return {"ok": True, "stdout": "main", "stderr": "", "code": 0}
        return {"ok": True, "stdout": "sha", "stderr": "", "code": 0}

    monkeypatch.setattr(watchboard, "collect_route", fake_collect_route)
    monkeypatch.setattr(watchboard, "collect_tmux", fake_collect_tmux)
    monkeypatch.setattr(watchboard, "run_cmd", fake_run_cmd)

    status = watchboard.collect_status(Path("/tmp"), Path("/tmp/worktrees"), "aereinh")

    assert status["command_health"]["sacct"]["ok"] is False
    assert any("sacct 最近作业查询不可用" in warning for warning in status["warnings"])


def test_route_a_review_needs_revision_token_sets_revision_state():
    route = route_fixture(status_keywords=["ROUTE_A_REVIEW_NEEDS_REVISION"], packet_files={**route_fixture()["packet_files"], "review": True})

    watchboard.annotate_route_runtime(route, {"care_route_A_controller": False}, [], [])

    assert route["display_state_zh"] == "需修订"
    assert watchboard.status_class(route, {}) == "revision"


def test_status_class_colors_non_ready_states():
    route = route_fixture(display_state_zh="训练不足")
    assert watchboard.status_class(route, {}) == "undertrained"

    route = route_fixture(display_state_zh="需修订")
    assert watchboard.status_class(route, {}) == "revision"

    route = route_fixture(display_state_zh="需补证据", completion_blockers=["missing aggregation"])
    assert watchboard.status_class(route, {}) == "risk"


def test_status_class_keeps_white_background_for_active_only():
    route = route_fixture(display_state_zh="Controller 运行中")
    assert watchboard.status_class(route, {"care_route_A_controller": True}) == "active"

    route = route_fixture(display_state_zh="Controller 已结束")
    assert watchboard.status_class(route, {"care_route_A_controller": True}) == "ended"
