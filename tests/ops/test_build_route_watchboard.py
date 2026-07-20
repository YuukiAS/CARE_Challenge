from __future__ import annotations

import importlib.util
import json
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
        "controller_tmux": "care_route_A",
        "reviewer_tmux": "care_route_A",
        "tmux_session": "care_route_A",
        "controller_tmux_window": "RouteA-Controller",
        "tmux_window_status": {"RouteA-Controller": False},
        "dirty_count": 0,
        "current_status": "setup only",
        "next_gate": "unknown",
        "purpose": "test route",
        "architecture_lines": ["test architecture"],
        "architecture_source": "test",
        "evidence_summary_zh": "测试证据。",
        "result_root": "results/route_A",
        "result_root_source": "test",
        "reviewability": {"label_zh": "尚不可审查为完成", "can_review_complete": False},
        "completion_blockers": [],
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


def handoff_fixture(root, **critic_overrides):
    critics = {
        "route_A": watchboard.relative_repo_path(root, "NO_CURRENT_CRITIC_HANDOFF"),
        "route_B": watchboard.relative_repo_path(root, "NO_CURRENT_CRITIC_HANDOFF"),
        "route_C": watchboard.relative_repo_path(root, "NO_CURRENT_CRITIC_HANDOFF"),
    }
    critics.update(critic_overrides)
    return {"round_id": "round03", "critics": critics}


def test_controller_packet_without_review_needs_reviewer(tmp_path):
    root = tmp_path / "CARE"
    route = route_fixture(
        display_state_zh="训练不足",
        packet_files={**route_fixture()["packet_files"], "result": True, "controller_report": True, "review": False},
    )

    watchboard.annotate_handoff_workers(route, handoff_fixture(root))

    assert route["round_id"] == "round03"
    assert route["current_worker_zh"] == "需要 Reviewer"
    assert route["work_summary_zh"] == "Controller 已执行完毕，结果：训练不足。"
    assert route["next_action_zh"] == "需要 Route A Reviewer 只读审查结果包。"


def test_handoff_worker_annotation_prefers_published_route_critic(tmp_path):
    root = tmp_path / "CARE"
    critic = root / "prompts" / "routes" / "handoffs" / "route_A_round03_critic_handoff_20260716.md"
    critic.parent.mkdir(parents=True)
    critic.write_text("critic", encoding="utf-8")
    route = route_fixture(
        display_state_zh="需修订",
        packet_files={**route_fixture()["packet_files"], "result": True, "controller_report": True, "review": True},
    )

    watchboard.annotate_handoff_workers(
        route,
        handoff_fixture(root, route_A=watchboard.relative_repo_path(root, "prompts/routes/handoffs/route_A_round03_critic_handoff_20260716.md")),
    )

    assert route["round_id"] == "round03"
    assert route["critic_handoff_state_zh"] == "已发布"
    assert route["current_worker_zh"] == "Route A Critic 正在判断"
    assert route["work_summary_zh"] == "Reviewer 已完成，结论：需修订。"
    assert route["next_action_zh"] == "规划者汇总 Critic 结论后决定是否交回 Controller。"


def test_missing_critic_prompt_is_warning_state_without_main_table(tmp_path):
    root = tmp_path / "CARE"
    route = route_fixture(
        display_state_zh="需修订",
        packet_files={**route_fixture()["packet_files"], "result": True, "controller_report": True, "review": True},
    )
    handoff = handoff_fixture(
        root,
        route_A=watchboard.relative_repo_path(root, "prompts/routes/handoffs/missing_route_A_critic.md"),
    )

    watchboard.annotate_handoff_workers(route, handoff)
    html = watchboard.render_html(
        {
            "generated_at": "2026-07-16T12:00:00",
            "tmux": {"care_route_A": False},
            "routes": [route],
            "jobs": [],
            "route_jobs": [],
            "general_jobs": [],
            "partitions": [],
            "warnings": [],
            "guardrails": {"forbidden_actions": []},
            "tmux_topology": [],
            "handoff": handoff,
            "user": "aereinh",
        }
    )

    assert route["critic_handoff_state_zh"] == "文件缺失"
    assert route["next_action_zh"] == "Critic 提示词文件缺失，需先修正 CURRENT.md 指向。"
    assert "当前 round 与 GPT handoff" not in html
    assert "Prompt path" not in html
    assert "missing_route_A_critic.md" not in html


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

    watchboard.annotate_route_runtime(route, {"care_route_A": False}, jobs, [])

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

    watchboard.annotate_route_runtime(route, {"care_route_A": False}, jobs, [])

    assert route["display_state_zh"] == "Slurm 运行中"
    assert route["reviewability"]["label_zh"] == "不可作为完成包审查"


def test_awaiting_sacct_has_explicit_state():
    route = route_fixture(status_keywords=["AWAITING_SACCT"])

    watchboard.annotate_route_runtime(route, {"care_route_A": False}, [], [])

    assert route["display_state_zh"] == "等待 sacct"
    assert route["reviewability"]["can_review_complete"] is False


def test_needs_evidence_and_review_states():
    needs_evidence = route_fixture(status_keywords=["NEEDS_EVIDENCE"])
    review_pending = route_fixture(status_keywords=["AWAITING_REVIEW"], packet_files={**route_fixture()["packet_files"], "review_request": True})
    review_pass = route_fixture(status_keywords=["PASS", "COMPLETE"], packet_files={**route_fixture()["packet_files"], "review": True})
    review_fail = route_fixture(status_keywords=["FAIL"], packet_files={**route_fixture()["packet_files"], "review": True})

    for route in (needs_evidence, review_pending, review_pass, review_fail):
        watchboard.annotate_route_runtime(route, {"care_route_A": False}, [], [])

    assert needs_evidence["display_state_zh"] == "需补证据"
    assert review_pending["display_state_zh"] == "待独立审查"
    assert review_pending["reviewability"]["can_review_complete"] is True
    assert review_pass["display_state_zh"] == "审查通过"
    assert review_fail["display_state_zh"] == "审查未通过"


def test_setup_only_route_state():
    route = route_fixture(current_status="setup only")

    watchboard.annotate_route_runtime(route, {"care_route_A": False}, [], [])

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


def test_slurm_job_display_groups_puts_care_gpu_under_general_in_policy_order():
    jobs = [
        {"id": "3", "partition": "volta-gpu", "name": "v", "is_general": False},
        {"id": "1", "partition": "general", "name": "shell", "is_general": True},
        {"id": "4", "partition": "debug", "name": "d", "is_general": False},
        {"id": "2", "partition": "a100-gpu", "name": "a", "is_general": False},
        {"id": "5", "partition": "htzhulab", "name": "h", "is_general": False},
    ]

    groups = watchboard.slurm_job_display_groups(jobs)

    assert [group["title"] for group in groups] == ["general", "CARE GPU 分区", "debug"]
    assert [job["partition"] for job in groups[1]["jobs"]] == ["htzhulab", "a100-gpu", "volta-gpu"]


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


def test_watchboard_service_window_allows_python_auto_rename(monkeypatch):
    def fake_run_cmd(args, cwd, timeout=8):
        if args[:3] == ["tmux", "list-panes", "-a"]:
            return {"ok": True, "stdout": "", "stderr": "", "code": 0}
        if args[:3] == ["tmux", "list-windows", "-t"] and args[3] == "care_watchboard":
            return {
                "ok": True,
                "stdout": "0|./envs/env_CARE/bin/python|./envs/env_CARE/bin/python\n1|watchboard-tunnel|cloudflared",
                "stderr": "",
                "code": 0,
            }
        return {"ok": True, "stdout": "", "stderr": "", "code": 0}

    monkeypatch.setattr(watchboard, "run_cmd", fake_run_cmd)

    topology = watchboard.collect_tmux_topology(Path("/tmp"), {"care_watchboard": True})
    watchboard_session = next(item for item in topology if item["session"] == "care_watchboard")

    assert watchboard_session["window_status"]["Watchboard"] is True
    assert watchboard_session["window_status"]["watchboard-tunnel"] is True


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

    route_b = next(item for item in topology if item["session"] == "care_route_B")
    route_c = next(item for item in topology if item["session"] == "care_route_C")
    assert set(route_b["window_status"]) == {"RouteB-Controller", "RouteB-Continue", "RouteB-Exec", "RouteB-Reviewer"}
    assert set(route_c["window_status"]) == {"RouteC-Controller", "RouteC-Continue", "RouteC-Exec", "RouteC-Reviewer"}


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

    watchboard.annotate_route_runtime(route, {"care_route_A": False}, [], [])

    assert route["display_state_zh"] == "需修订"
    assert watchboard.status_class(route, {}) == "revision"


def test_review_decision_overrides_stale_controller_undertrained_token():
    route = route_fixture(
        id="route_B",
        label="Route B",
        status_keywords=["ROUTE_B_SCIENTIFIC_UNDERTRAINED", "ROUTE_B_REVIEW_NEEDS_REVISION"],
        packet_files={**route_fixture()["packet_files"], "review": True},
    )

    watchboard.annotate_route_runtime(route, {"care_route_B": False}, [], [])

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
    assert watchboard.status_class(route, {"care_route_A": True}) == "active"

    route = route_fixture(display_state_zh="Controller 已结束")
    assert watchboard.status_class(route, {"care_route_A": True}) == "ended"



def round03_current_text():
    return """# CARE Route Portfolio Current Round

```text
round_id: round03
date: 2026-07-18
```

current Planner handoff:
prompts/routes/handoffs/portfolio_round03_planner_handoff_20260718.md
blob: c7024ee99f1a3135f02f893b053bad8b63bf5208

Portfolio state:

```text
Route A: DEFERRED_FALLBACK_NOT_ACTIVE
Route B: ACTIVE_FULL_SRR_V3
Route C: ACTIVE_M10_FORENSIC_EVIDENCE_AND_CINE_FIDELITY
current_controller_authorizations: 0
```

### Route A — dormant fallback

```text
route head: fae8a732bbf625db367e0b68c04f1490d0c97be3
contract blob: 370c25de0e35dbd5c854bbdfb81589ee8c0a4368
executor-plan blob: c681d761cfa145d68ba906f5eb33607843af8b80
critic-request blob: 227c8f69f69e2b07b72f5df5f3323b2f03136bd1
planner-audit blob: 61d8cb48fab3728d1330975fb1bc2178446313f9
```

### Route B — full SRR-v3

```text
route head: a282007ecab44274699ab49a389ba107ac04d5b2
contract blob: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
executor-plan blob: 83494fbf40df7b79c26c3be3c00d51e23830208c
critic-request blob: 50fba61a5512e4ba7b124fd2355ca84c2a688ed8
planner-audit blob: 3a0d422ed81695f77750f59ebfdca38700c69516
Critic-handoff blob: cfe69bbd597d6cdd80f3b27bc42f577f8dce122a
```

### Route C — M10 forensic evidence and Cine fidelity

```text
route head: 2f0a9403b220c10e7b75cea465c4b54a8da899c5
contract blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
executor-plan blob: 9b5d0bd369dd95d926337ef2d8c315e7fdbfb982
evidence-mapping blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
evidence-mapping required row count: 37
critic-request blob: 0beb1ef72cc8fb1e712be76a57c11b0fdc04043e
planner-audit blob: f703decf4b8480da467f7f3387a273fe3b66d3eb
Critic-handoff blob: 641509ed7a2dbb188109ea594199a6e2a04e2893
```

## Critic Entries

```text
route_A critic current prompt:
NO_CURRENT_CRITIC_HANDOFF

route_B critic current prompt:
prompts/routes/handoffs/route_B_round03_critic_handoff_20260718.md

route_C critic current prompt:
prompts/routes/handoffs/route_C_round03_critic_handoff_20260718.md
```

Allowed Route B planning tokens:

```text
ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
```

Allowed Route C planning tokens:

```text
ROUTE_C_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION
```

## Round03 Decision Checkpoints

```text
2026-07-20:
- Route B B0-B2 implementation/manifest/validator/preflight gate terminal.
- Route C C0/C0B fingerprint/evidence-map and exact recovery decision terminal.
```

## Authority Boundary

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
```
"""


def test_parse_current_handoff_round03_portfolio_authority_and_bindings(tmp_path):
    root = tmp_path / "CARE"
    (root / "prompts" / "routes" / "handoffs").mkdir(parents=True)
    (root / "prompts" / "routes" / "handoffs" / "portfolio_round03_planner_handoff_20260718.md").write_text("planner", encoding="utf-8")
    (root / "prompts" / "routes" / "handoffs" / "route_B_round03_critic_handoff_20260718.md").write_text("critic b", encoding="utf-8")
    (root / "prompts" / "routes" / "handoffs" / "route_C_round03_critic_handoff_20260718.md").write_text("critic c", encoding="utf-8")

    parsed = watchboard.parse_current_handoff(round03_current_text(), root)

    assert parsed["round_id"] == "round03"
    assert parsed["portfolio"]["active_routes"] == ["route_B", "route_C"]
    assert parsed["portfolio"]["deferred_routes"] == ["route_A"]
    assert parsed["authority"]["controller_authorized_now"] == 0
    assert parsed["authority"]["validation_upload_authorized"] is False
    assert parsed["route_bindings"]["route_B"]["required_head"] == "a282007ecab44274699ab49a389ba107ac04d5b2"
    assert parsed["route_bindings"]["route_C"]["evidence_mapping_required_row_count"] == "37"
    assert parsed["critic_readiness"]["route_B"]["allowed_tokens"] == [
        "ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER",
        "ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION",
    ]


def test_round03_route_a_is_dormant_not_active_controller_waiting(tmp_path):
    root = tmp_path / "CARE"
    handoff = watchboard.parse_current_handoff(round03_current_text(), root)
    route = route_fixture(
        id="route_A",
        label="Route A",
        display_state_zh="需修订",
        origin_sha="fae8a732bbf625db367e0b68c04f1490d0c97be3",
        packet_files={**route_fixture()["packet_files"], "result": True, "review": True},
    )

    watchboard.annotate_handoff_workers(route, handoff)

    assert route["is_deferred_fallback"] is True
    assert route["is_active_round_route"] is False
    assert route["display_state_zh"].startswith("Dormant fallback")
    assert route["controller_authorized"] is False
    assert "不得启动 Route A controller" in route["next_action_zh"]
    assert "等待任务启动" not in route["current_worker_zh"]


def test_round03_active_route_b_controller_blocked_until_authority_and_ready_token(tmp_path):
    root = tmp_path / "CARE"
    handoff = watchboard.parse_current_handoff(round03_current_text(), root)
    route = route_fixture(
        id="route_B",
        label="Route B",
        tmux_session="care_route_B",
        controller_tmux="care_route_B",
        controller_tmux_window="RouteB-Controller",
        origin_sha="a282007ecab44274699ab49a389ba107ac04d5b2",
    )

    watchboard.annotate_handoff_workers(route, handoff)

    assert route["is_active_round_route"] is True
    assert route["controller_authorized"] is False
    assert route["controller_authority_state_zh"] == "blocked"
    assert route["required_head"] == route["origin_sha"]
    assert "Controller 当前 blocked" in route["next_action_zh"]


def test_render_html_uses_round03_portfolio_title_and_slurm_race_guardrail(tmp_path):
    handoff = watchboard.parse_current_handoff(round03_current_text(), tmp_path / "CARE")
    route_a = route_fixture(id="route_A", label="Route A", origin_sha="fae8a732bbf625db367e0b68c04f1490d0c97be3")
    route_b = route_fixture(id="route_B", label="Route B", tmux_session="care_route_B", controller_tmux="care_route_B", controller_tmux_window="RouteB-Controller", origin_sha="a282007ecab44274699ab49a389ba107ac04d5b2")
    route_c = route_fixture(id="route_C", label="Route C", tmux_session="care_route_C", controller_tmux="care_route_C", controller_tmux_window="RouteC-Controller", origin_sha="2f0a9403b220c10e7b75cea465c4b54a8da899c5")
    for route in (route_a, route_b, route_c):
        watchboard.annotate_route_runtime(route, {}, [], [])
        watchboard.annotate_handoff_workers(route, handoff)

    html = watchboard.render_html(
        {
            "generated_at": "2026-07-18T12:00:00",
            "tmux": {},
            "routes": [route_a, route_b, route_c],
            "jobs": [],
            "route_jobs": [],
            "general_jobs": [],
            "partitions": [],
            "warnings": [],
            "guardrails": {"forbidden_actions": ["scancel", "sbatch", "srun", "git merge", "git push", "upload"]},
            "tmux_topology": [],
            "handoff": handoff,
            "portfolio": handoff["portfolio"],
            "authority": handoff["authority"],
            "critic_readiness": handoff["critic_readiness"],
            "round_checkpoints": handoff["round_checkpoints"],
            "user": "aereinh",
        }
    )

    assert "CARE Route Portfolio round03" in html
    assert "CARE SRR Route A+B+C" not in html
    assert "Route A/C 不进入 active count" in html
    assert "controller_authorized_now" in html
    assert "formal wrapper must use /users/a/e/aereinh/CARE/envs/env_CARE/bin/python" in html
    assert "pending-loser cancellation" in html



def portfolio_current_text(round_id="round04", include_missing=False, active=("Route B",), deferred=("Route A", "Route C")):
    route_a_state = "DEFERRED_FALLBACK_NOT_ACTIVE" if "Route A" in deferred else "ACTIVE_ROUTE_A"
    route_b_state = "ACTIVE_FULL_SRR_V3" if "Route B" in active else "DEFERRED"
    route_c_state = "ACTIVE_M10_FORENSIC_EVIDENCE_AND_CINE_FIDELITY" if "Route C" in active else "DEFERRED"
    route_b_review = "" if include_missing else f"critic review output path: prompts/routes/route_B_{round_id}_critic_review.md\n"
    route_c_review = "" if include_missing else f"critic review output path: prompts/routes/route_C_{round_id}_critic_review.md\n"
    b_tokens = "" if include_missing else f"""Allowed Route B planning tokens:

```text
ROUTE_B_{round_id.upper()}_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_{round_id.upper()}_PLANNING_NEEDS_REVISION
```
"""
    return f"""# CARE Route Portfolio Current Round

```text
round_id: {round_id}
date: 2026-07-18
```

current Planner handoff:
prompts/routes/handoffs/portfolio_{round_id}_planner.md

Portfolio state:

```text
Route A: {route_a_state}
Route B: {route_b_state}
Route C: {route_c_state}
current_controller_authorizations: 0
```

### Route A - dormant fallback

```text
route head: aaa111
contract blob: contract-a
executor-plan blob: exec-a
critic-request blob: request-a
planner-audit blob: audit-a
```

### Route B - full SRR

```text
route head: bbb222
contract blob: contract-b
executor-plan blob: exec-b
critic-request blob: request-b
planner-audit blob: audit-b
Critic-handoff blob: handoff-b
{route_b_review}```

### Route C - evidence route

```text
route head: ccc333
contract blob: contract-c
executor-plan blob: exec-c
critic-request blob: request-c
planner-audit blob: audit-c
Critic-handoff blob: handoff-c
{route_c_review}```

## Critic Entries

```text
route_A critic current prompt:
NO_CURRENT_CRITIC_HANDOFF

route_B critic current prompt:
prompts/routes/handoffs/route_B_{round_id}_critic_handoff.md

route_C critic current prompt:
prompts/routes/handoffs/route_C_{round_id}_critic_handoff.md
```

{b_tokens}Allowed Route C planning tokens:

```text
ROUTE_C_{round_id.upper()}_PLANNING_READY_FOR_CONTROLLER
ROUTE_C_{round_id.upper()}_PLANNING_NEEDS_REVISION
```

## Decision Checkpoints

```text
2026-07-20:
- Route B implementation gate.
- Route C evidence gate.
```

## Authority Boundary

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
```
"""


def test_parse_current_handoff_round04_without_round03_hardcode(tmp_path):
    parsed = watchboard.parse_current_handoff(portfolio_current_text("round04"), tmp_path / "CARE")
    assert parsed["portfolio_round"]["round_id"] == "round04"
    assert parsed["portfolio_round"]["active_routes"] == ["route_B"]
    html = watchboard.render_html(
        {
            "generated_at": "2026-07-18T12:00:00",
            "tmux": {},
            "routes": [route_fixture(id="route_B", label="Route B", origin_sha="bbb222")],
            "jobs": [],
            "route_jobs": [],
            "general_jobs": [],
            "partitions": [],
            "warnings": [],
            "guardrails": {"forbidden_actions": []},
            "tmux_topology": [],
            "handoff": parsed,
            "portfolio_round": parsed["portfolio_round"],
            "portfolio": parsed["portfolio"],
            "authority": parsed["authority"],
            "critic_readiness": parsed["critic_readiness"],
            "round_checkpoints": parsed["round_checkpoints"],
            "live_service_state": {"processes": []},
            "user": "aereinh",
        }
    )
    assert "round04" in html
    assert "Round03" not in html


def test_parse_current_handoff_round05_missing_fields_blocks_unknown(tmp_path):
    parsed = watchboard.parse_current_handoff(portfolio_current_text("round05", include_missing=True), tmp_path / "CARE")
    assert parsed["portfolio_round"]["round_id"] == "round05"
    assert parsed["critic_readiness"]["route_B"]["allowed_tokens"] == []
    assert parsed["critic_readiness"]["route_B"]["state_zh"] in {"critic review output unknown", "allowed token unknown"}
    assert any("critic_review_output_path" in warning for warning in parsed["parse_warnings"])
    assert any("allowed planning tokens" in warning for warning in parsed["parse_warnings"])


def test_active_and_deferred_routes_drive_portfolio_state(tmp_path):
    parsed = watchboard.parse_current_handoff(portfolio_current_text("round04", active=("Route C",), deferred=("Route A", "Route B")), tmp_path / "CARE")
    assert parsed["portfolio"]["active_routes"] == ["route_C"]
    assert parsed["portfolio"]["deferred_routes"] == ["route_A", "route_B"]


def test_stop_and_hold_portfolio_state_is_inactive_not_active(tmp_path):
    current = portfolio_current_text("round04").replace("Route C: DEFERRED", "Route C: ROUTE_C_PORTFOLIO_STOP_AND_HOLD")
    parsed = watchboard.parse_current_handoff(current, tmp_path / "CARE")
    assert parsed["portfolio"]["active_routes"] == ["route_B"]
    assert parsed["portfolio"]["deferred_routes"] == ["route_A", "route_C"]


def test_route_b_only_active_mode_keeps_route_a_c_inactive_from_blocking_route_b(tmp_path):
    parsed = watchboard.parse_current_handoff(portfolio_current_text("round04"), tmp_path / "CARE")
    assert parsed["portfolio"]["active_routes"] == ["route_B"]
    assert parsed["portfolio"]["active_controller_routes"] == ["route_B"]
    assert parsed["portfolio"]["deferred_routes"] == ["route_A", "route_C"]

    route_a = route_fixture(id="route_A", label="Route A", origin_sha="aaa111")
    route_b = route_fixture(id="route_B", label="Route B", origin_sha="bbb222")
    route_c = route_fixture(id="route_C", label="Route C", origin_sha="ccc333")
    for route in (route_a, route_b, route_c):
        watchboard.annotate_route_runtime(route, {}, [], [])
        watchboard.annotate_handoff_workers(route, parsed)

    assert route_b["is_active_round_route"] is True
    assert route_b["display_state_zh"] != "Dormant fallback / inactive unless explicitly reauthorized"
    assert route_a["is_deferred_fallback"] is True
    assert route_c["is_deferred_fallback"] is True
    assert route_c["runtime_state"]["state"] == "dormant_deferred"
    assert route_b["runtime_state"]["state"] != "dormant_deferred"


def test_critic_ready_needs_revision_missing_review_and_stale_head(tmp_path):
    root = tmp_path / "CARE"
    (root / "prompts" / "routes").mkdir(parents=True)
    review = root / "prompts" / "routes" / "route_B_round04_critic_review.md"
    review.write_text("ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER", encoding="utf-8")
    parsed = watchboard.parse_current_handoff(portfolio_current_text("round04"), root)
    route = route_fixture(id="route_B", label="Route B", origin_sha="stale")
    watchboard.annotate_handoff_workers(route, parsed)
    assert route["planning_gate"]["ready_token"] == "ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER"
    assert route["controller_authority"]["authorized"] is False
    assert route["head_matches_required"] is False
    assert parsed["critic_readiness"]["route_C"]["state_zh"] == "pending critic token"


def test_controller_running_goal_achieved_queued_message_and_stale_pane():
    running = route_fixture(id="route_B", label="Route B", controller_tmux="care_route_B")
    watchboard.annotate_route_runtime(running, {"care_route_B": True}, [], [], {"state": "active_or_unknown", "tail": "queued"})
    assert running["runtime_state"]["state"] == "controller_active"
    ended = route_fixture(id="route_B", label="Route B", controller_tmux="care_route_B")
    watchboard.annotate_route_runtime(ended, {"care_route_B": True}, [], [], {"state": "completed_or_idle", "tail": "Goal achieved"})
    assert ended["display_state_zh"] == "Controller 已结束"


def test_slurm_pending_running_completed_awaiting_aggregation():
    route = route_fixture(status_keywords=["NEEDS_MONITOR"], slurm_job_ids=["12345"])
    current = [{"id": "12345", "partition": "a100-gpu", "name": "RCR3", "state": "PENDING", "time": "0:00", "reason": "Priority", "source": "squeue"}]
    watchboard.annotate_route_runtime(route, {"care_route_A": False}, current, [])
    assert route["runtime_state"]["state"] == "monitor_or_incomplete"
    assert route["review_state"]["can_review_complete"] is False
    completed = route_fixture(status_keywords=["NEEDS_MONITOR"], slurm_job_ids=["12345"])
    recent = [{"id": "12345", "partition": "a100-gpu", "name": "RCR3", "state": "COMPLETED", "elapsed": "00:10", "exit_code": "0:0", "source": "sacct"}]
    watchboard.annotate_route_runtime(completed, {"care_route_A": False}, [], recent)
    assert any("聚合" in blocker for blocker in completed["completion_blockers"])


def test_terminal_negative_packet_ready_for_reviewer():
    route = route_fixture(status_keywords=["TERMINAL_NON_READY_PACKET"], packet_files={**route_fixture()["packet_files"], "review_request": True})
    watchboard.annotate_route_runtime(route, {}, [], [])
    assert route["runtime_state"]["state"] == "terminal_negative"
    assert route["review_state"]["can_review_complete"] is False


def test_v100_incompatible_ledger_overrides_idle_volta_partition():
    compat = watchboard.detect_v100_compatibility("volta-gpu failed with sm_70 no-kernel-image")
    assert compat["volta_usable"] is False


def test_tmux_discovers_round_specific_controller_windows(monkeypatch):
    def fake_run_cmd(args, cwd, timeout=8):
        if args[:3] == ["tmux", "list-panes", "-a"]:
            return {"ok": True, "stdout": "care_route_B|RouteB-Round04Controller|0|title|/users/a/e/aereinh/CARE_worktrees/route_B|codex", "stderr": "", "code": 0}
        if args[:3] == ["tmux", "list-windows", "-t"]:
            return {"ok": True, "stdout": "0|RouteB-Round04Controller|codex", "stderr": "", "code": 0} if args[3] == "care_route_B" else {"ok": True, "stdout": "", "stderr": "", "code": 0}
        return {"ok": True, "stdout": "", "stderr": "", "code": 0}
    monkeypatch.setattr(watchboard, "run_cmd", fake_run_cmd)
    topology = watchboard.collect_tmux_topology(Path("/tmp"), {"care_route_B": True}, round_id="round04")
    route = route_fixture(id="route_B", label="Route B", tmux_session="care_route_B")
    watchboard.annotate_route_tmux(route, {item["session"]: item for item in topology}, "round04")
    assert route["controller_tmux_window"] == "RouteB-Round04Controller"
    assert route["tmux_activity"]["controller_window"] == "RouteB-Round04Controller"


def test_tmux_marks_old_controller_windows_legacy_inactive(monkeypatch):
    def fake_run_cmd(args, cwd, timeout=8):
        if args[:3] == ["tmux", "list-panes", "-a"]:
            return {"ok": True, "stdout": "", "stderr": "", "code": 0}
        if args[:3] == ["tmux", "list-windows", "-t"]:
            return {"ok": True, "stdout": "0|RouteC-Controller|codex\n1|RouteC-Round04Controller|codex", "stderr": "", "code": 0} if args[3] == "care_route_C" else {"ok": True, "stdout": "", "stderr": "", "code": 0}
        return {"ok": True, "stdout": "", "stderr": "", "code": 0}
    monkeypatch.setattr(watchboard, "run_cmd", fake_run_cmd)
    topology = watchboard.collect_tmux_topology(Path("/tmp"), {"care_route_C": True}, round_id="round04")
    route = route_fixture(id="route_C", label="Route C", tmux_session="care_route_C")
    watchboard.annotate_route_tmux(route, {item["session"]: item for item in topology}, "round04")
    assert route["controller_tmux_window"] == "RouteC-Round04Controller"
    assert "RouteC-Controller" in route["legacy_controller_windows"]


def terminal_reviewer_current_text(round_id="round04"):
    base = portfolio_current_text(round_id)
    section = f"""
## Controller Terminal Packet / Reviewer Targets

```text
route_B reviewer_target_head: bbb222
route_B terminal_token: ROUTE_B_{round_id.upper()}_TERMINAL_PACKET_READY_FOR_REVIEW
route_B reviewer_output_path: results/route_B/review.md
route_B route_promotion_decision: NOT_REVIEWED
route_B route_negative_decision: NOT_REVIEWED
route_B scientific_resolution_status: AWAITING_REVIEW
route_B validation_upload: false
route_B hosted_metric_claim: false
route_B m11_started: false
route_C reviewer_target_head: ccc333
route_C terminal_token: ROUTE_C_{round_id.upper()}_TERMINAL_PACKET_READY_FOR_REVIEW
route_C reviewer_output_path: results/route_C/review.md
route_C route_promotion_decision: NOT_REVIEWED
route_C route_negative_decision: NOT_REVIEWED
route_C scientific_resolution_status: AWAITING_REVIEW
route_C validation_upload: false
route_C hosted_metric_claim: false
route_C m11_started: false
```
"""
    return base.replace("## Decision Checkpoints", section + "\n## Decision Checkpoints")


def test_terminal_reviewer_target_parsed_from_current_round_agnostic(tmp_path):
    parsed = watchboard.parse_current_handoff(terminal_reviewer_current_text("round05"), tmp_path / "CARE")

    target = parsed["terminal_reviewer_targets"]["route_B"]
    assert target["reviewer_target_head"] == "bbb222"
    assert target["terminal_token"] == "ROUTE_B_ROUND05_TERMINAL_PACKET_READY_FOR_REVIEW"
    assert target["reviewer_output_path"] == "results/route_B/review.md"
    assert target["scientific_resolution_status"] == "AWAITING_REVIEW"


def test_terminal_reviewer_ready_overrides_stale_monitor_and_review_keyword(tmp_path):
    handoff = watchboard.parse_current_handoff(terminal_reviewer_current_text("round04"), tmp_path / "CARE")
    route = route_fixture(
        id="route_B",
        label="Route B",
        sha="bbb222",
        origin_sha="old-origin",
        status_keywords=[
            "NEEDS_MONITOR",
            "ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW",
            "AWAITING_REVIEW",
            "ROUTE_B_REVIEW_NEEDS_EVIDENCE",
        ],
        packet_files={
            **route_fixture()["packet_files"],
            "result": True,
            "completion_check": True,
            "review_request": True,
            "manifest": True,
            "review": True,
        },
    )

    watchboard.apply_terminal_reviewer_target(route, handoff)
    watchboard.annotate_route_runtime(route, {}, [], [])
    watchboard.annotate_handoff_workers(route, handoff)

    assert route["terminal_reviewer_ready"] is True
    assert route["display_state_zh"] == "等待 independent reviewer"
    assert route["runtime_state"]["state"] == "terminal_packet_ready"
    assert route["review_state"]["can_review_complete"] is True
    assert route["current_worker_zh"] == "等待 independent reviewer"
    assert "Controller 当前 blocked" not in route["next_action_zh"]



def test_duplicate_watchboard_serve_process_state_requires_refresh():
    stdout = """192375 1 04:35:22 ./envs/env_CARE/bin/python scripts/ops/build_route_watchboard.py --user aereinh --serve --host 127.0.0.1 --port 8766
1783551 1 1-00:00:00 python scripts/ops/build_route_watchboard.py --user aereinh --serve --host 127.0.0.1 --port 8765
"""
    state = watchboard.parse_watchboard_processes(stdout, Path("/users/a/e/aereinh/CARE"))
    assert state["duplicate_or_legacy_detected"] is True
    assert state["refresh_required"] is True
    assert any(proc["risk"] for proc in state["processes"] if proc["port"] == 8765)


def test_no_side_effect_guard_forbidden_commands_not_invoked():
    assert watchboard.run_cmd(["sbatch", "x.sh"], Path("/tmp"))["code"] == 126
    assert watchboard.run_cmd(["srun", "hostname"], Path("/tmp"))["code"] == 126
    assert watchboard.run_cmd(["scancel", "123"], Path("/tmp"))["code"] == 126
    assert watchboard.run_cmd(["git", "merge", "route_A"], Path("/tmp"))["code"] == 126
    assert watchboard.run_cmd(["git", "push", "origin", "main"], Path("/tmp"))["code"] == 126
    assert watchboard.run_cmd(["tmux", "send-keys", "x"], Path("/tmp"))["code"] == 126



def test_ops_services_controller_notifier_schema_and_html(tmp_path):
    root = tmp_path / "CARE"
    (root / "controller_notifications" / "state").mkdir(parents=True)
    (root / "controller_notifications" / "logs").mkdir(parents=True)
    (root / "controller_notifications" / "config.example.json").write_text(
        json.dumps(
            {
                "enabled_routes": ["route_B", "route_C"],
                "state_path": "controller_notifications/state/notified_goals.json",
                "status_path": "controller_notifications/state/notify_goal_watcher_status.json",
                "log_path": "controller_notifications/logs/notify_goal_watcher.log",
                "tmux_session": "care_watchboard",
                "tmux_window": "Notify",
                "routes": {"main": {}, "route_A": {}, "route_B": {}, "route_C": {}},
            }
        ),
        encoding="utf-8",
    )
    status_path = root / "controller_notifications" / "state" / "notify_goal_watcher_status.json"
    status_path.write_text(
        json.dumps(
            {
                "last_scan_at_utc": "2026-07-19T12:00:00+00:00",
                "enabled_routes": ["route_B", "route_C"],
                "last_event": {"route": "route_B", "status": "complete", "detected_at_utc": "2026-07-19T12:01:00+00:00"},
                "last_email_status": "sent",
                "smtp": {"smtp_user_present": True, "smtp_password_present": True},
                "config_warnings": [],
            }
        ),
        encoding="utf-8",
    )
    topology = [
        {
            "session": "care_watchboard",
            "window_status": {"Watchboard": True, "watchboard-tunnel": True, "Notify": True},
            "live_windows": [],
            "panes": [],
        }
    ]
    process_stdout = "\n".join(
        [
            "111 1 00:01 /users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/build_route_watchboard.py --user aereinh --serve --host 127.0.0.1 --port 8766",
            f"222 1 00:01 /users/a/e/aereinh/CARE/envs/env_CARE/bin/python {root}/controller_notifications/notify_goal_watcher.py --loop --poll-seconds 60",
            "333 1 00:01 /usr/bin/cloudflared tunnel --config /tmp/cloudflared_watchboard/config.yml run care-watchboard",
        ]
    )
    services = watchboard.collect_ops_services(
        root,
        topology,
        process_stdout,
        watchboard.parse_watchboard_processes(process_stdout, root),
    )

    notifier = services["controller_notifier"]
    assert notifier["enabled"] is True
    assert notifier["tmux_window"] == "Notify"
    assert notifier["process_detected"] is True
    assert "notify_goal_watcher.py" in notifier["loop_command"]
    assert notifier["enabled_routes"] == ["route_B", "route_C"]
    assert notifier["last_scan"] == "2026-07-19T12:00:00+00:00"
    assert notifier["last_email_status"] == "sent"
    assert notifier["smtp_secret_present"] is True
    assert "password" not in json.dumps(notifier).lower()
    html = watchboard.render_ops_services({"ops_services": services})
    assert "Controller notifier" in html
    assert "notify_<wbr>goal_<wbr>watcher.log" in html
    assert "route_B, route_C" in html


def test_missing_notifier_window_warns_without_breaking_dashboard(tmp_path):
    root = tmp_path / "CARE"
    (root / "controller_notifications").mkdir(parents=True)
    (root / "controller_notifications" / "config.example.json").write_text(
        json.dumps({"enabled_routes": ["route_B", "route_C"], "tmux_window": "Notify"}),
        encoding="utf-8",
    )
    services = watchboard.collect_ops_services(
        root,
        [{"session": "care_watchboard", "window_status": {"Watchboard": True, "watchboard-tunnel": True, "Notify": False}, "live_windows": [], "panes": []}],
        "111 1 00:01 /usr/bin/cloudflared tunnel --config /tmp/cloudflared_watchboard/config.yml run care-watchboard",
        {"processes": [], "duplicate_or_legacy_detected": False},
    )
    html = watchboard.render_ops_services({"ops_services": services})
    assert services["controller_notifier"]["tmux_window_present"] is False
    assert any("window missing" in warning for warning in services["controller_notifier"]["config_warnings"])
    assert "Ops services" in html
    assert "care_watchboard:Notify window missing" in html


def test_stale_generated_watchboard_status_is_not_route_truth(tmp_path):
    root = tmp_path / "CARE"
    generated = root / "results" / "watchboard"
    generated.mkdir(parents=True)
    (generated / "status.json").write_text(
        json.dumps({"portfolio_round": {"round_id": "round03", "active_routes": ["route_A"]}}),
        encoding="utf-8",
    )
    handoff = watchboard.parse_current_handoff(portfolio_current_text("round04", active=("Route C",), deferred=("Route A", "Route B")), root)
    route_a = route_fixture(id="route_A", label="Route A", origin_sha="aaa111")
    watchboard.annotate_route_runtime(route_a, {}, [], [])
    watchboard.annotate_handoff_workers(route_a, handoff)

    assert handoff["portfolio_round"]["round_id"] == "round04"
    assert handoff["portfolio"]["active_routes"] == ["route_C"]
    assert route_a["is_deferred_fallback"] is True
    assert route_a["display_state_zh"].startswith("Dormant fallback")


def test_forbidden_actions_include_scientific_boundaries():
    assert "route promotion" in watchboard.FORBIDDEN_ACTIONS
    assert "M11" in watchboard.FORBIDDEN_ACTIONS
    assert "hosted metric claim" in watchboard.FORBIDDEN_ACTIONS
    assert "final scientific decision" in watchboard.FORBIDDEN_ACTIONS



def round04_current_style_text() -> str:
    return """# CARE Route Portfolio Current Round

## Active round

```text
round_id: round04
date: 2026-07-19
controller_authorized_now: 0
```

## Exact remote evidence bindings

```text
planner base main: 30098813522cecd98e60bcb99e2676b28c1a5461
Route B evidence: b9c7664da7cb1f1892fff37a4497722f31a0a96d
Route C reviewer commit: 17062b00edc3443aacefe8583568797a9f2655ba
Route C reviewed controller repair: 1e663cfa64f00413f005bef26310290fd43ec8ab
```

## Portfolio state

```text
Route A: DEFERRED_FALLBACK_NOT_ACTIVE
Route B: PLANNING_REVISION_PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW
Route C: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
```

### Route C

```text
review path: results/route_C/review.md
review commit: 17062b00edc3443aacefe8583568797a9f2655ba
reviewed controller repair: 1e663cfa64f00413f005bef26310290fd43ec8ab
review token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
portfolio status: EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION
reviewer required now: false
```

### Route B Round04 planning binding

```text
Route B evidence commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
revision source critic token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
critic handoff: prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
coordinator receipt: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
critic output: prompts/routes/route_B_round04_critic_rereview.md
controller start authorized: false
```

## Current role entries

```text
Route A critic: NO_CURRENT_CRITIC_HANDOFF
Route B critic: prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
Route C critic: NO_CURRENT_CRITIC_HANDOFF
Route C reviewer: NO_CURRENT_REVIEWER_HANDOFF
```

Allowed Route B Round04 planning decisions:

```text
ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
```

## Authority boundary

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
```
"""


def test_round04_current_style_parses_portfolio_roles_and_authority(tmp_path):
    root = tmp_path / "CARE"
    critic = root / "prompts" / "routes" / "route_B_round04_critic_review.md"
    critic.parent.mkdir(parents=True)
    critic.write_text(
        "decision_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION\n"
        "hard_blockers:\n"
        "- CURRENT_NOT_ADVANCED_TO_ROUND04\n"
        "- B10_TERMINAL_FINALIZER_UNREACHABLE_ON_EARLY_TERMINAL_BRANCHES\n",
        encoding="utf-8",
    )
    parsed = watchboard.parse_current_handoff(round04_current_style_text(), root)

    assert parsed["round_id"] == "round04"
    assert parsed["portfolio"]["active_routes"] == ["route_B"]
    assert parsed["portfolio"]["portfolio_context_routes"] == ["route_B"]
    assert parsed["portfolio"]["deferred_routes"] == ["route_A", "route_C"]
    assert parsed["authority"]["controller_authorized_now"] == 0
    assert not any("Authority Boundary 缺少" in warning for warning in parsed["parse_warnings"])
    assert not any("active route 为空" in warning for warning in parsed["parse_warnings"])
    assert parsed["critics"]["route_B"]["path"].endswith("route_B_round04_critic_handoff_20260719.md")
    assert parsed["route_bindings"]["route_B"]["required_head"] == "b9c7664da7cb1f1892fff37a4497722f31a0a96d"
    assert parsed["route_bindings"]["route_C"]["reviewer_commit"] == "17062b00edc3443aacefe8583568797a9f2655ba"
    assert parsed["critic_readiness"]["route_B"]["revision_token"] == "ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION"


def test_round04_status_priorities_override_stale_packet_keywords(tmp_path):
    root = tmp_path / "CARE"
    critic = root / "prompts" / "routes" / "route_B_round04_critic_review.md"
    critic.parent.mkdir(parents=True)
    critic.write_text(
        "ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION\n"
        "hard_blockers:\n"
        "- CURRENT_NOT_ADVANCED_TO_ROUND04\n"
        "- B10_TERMINAL_FINALIZER_UNREACHABLE_ON_EARLY_TERMINAL_BRANCHES\n"
        "- PER_EXECUTOR_VALIDATOR_COMMANDS_NOT_MACHINE_BOUND\n"
        "- REQUIRED_USERS_EXECUTABLE_CHECKS_NOT_EXIT_ZERO\n",
        encoding="utf-8",
    )
    handoff = watchboard.parse_current_handoff(round04_current_style_text(), root)
    route_a = route_fixture(id="route_A", label="Route A", status_keywords=["ROUTE_A_REVIEW_NEEDS_REVISION"], display_state_zh="需修订")
    route_b = route_fixture(
        id="route_B",
        label="Route B",
        origin_sha="b9c7664da7cb1f1892fff37a4497722f31a0a96d",
        status_keywords=["ROUTE_B_SCIENTIFIC_UNDERTRAINED", "ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW"],
        display_state_zh="训练不足",
    )
    route_c = route_fixture(
        id="route_C",
        label="Route C",
        origin_sha="17062b00edc3443aacefe8583568797a9f2655ba",
        status_keywords=["NEEDS_MONITOR", "ROUTE_C_REVIEW_NEEDS_REVISION", "ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE"],
        display_state_zh="需补证据",
        role_tokens=[
            {
                "token": "ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE",
                "route": "route_C",
                "round": 3,
                "kind": "REVIEW_EVIDENCE_COMPLETE",
                "role": "reviewer",
                "source_role": "review",
                "source_path": "results/route_C/review.md",
                "mtime": 2,
            }
        ],
    )

    for route in (route_a, route_b, route_c):
        watchboard.annotate_route_runtime(route, {}, [], [])
        watchboard.annotate_handoff_workers(route, handoff)

    assert route_a["display_state_zh"].startswith("Dormant fallback")
    assert route_a["controller_allowed"] is False
    assert route_b["display_state_zh"] == "Round04 planning needs revision / controller blocked"
    assert route_b["latest_role_token"]["token"] == "ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION"
    assert route_b["controller_allowed"] is False
    assert any("B10_TERMINAL_FINALIZER" in blocker for blocker in route_b["completion_blockers"])
    assert route_c["display_state_zh"].startswith("Dormant fallback")
    assert route_c["runtime_state"]["state"] == "dormant_deferred"
    assert route_c["reviewer_commit"] == "17062b00edc3443aacefe8583568797a9f2655ba"
    assert route_c["reviewed_controller_commit"] == "1e663cfa64f00413f005bef26310290fd43ec8ab"
    assert route_c["controller_allowed"] is False


def test_round04_ready_for_critic_rereview_overrides_stale_packet_keywords(tmp_path):
    root = tmp_path / "CARE"
    handoff = watchboard.parse_current_handoff(
        round04_current_style_text().replace(
            "PLANNING_REVISION_PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW",
            "PLANNING_REVISION_READY_FOR_CRITIC_REREVIEW",
        ),
        root,
    )
    route_b = route_fixture(
        id="route_B",
        label="Route B",
        origin_sha="b9c7664da7cb1f1892fff37a4497722f31a0a96d",
        status_keywords=["ROUTE_B_SCIENTIFIC_UNDERTRAINED", "ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION"],
        display_state_zh="训练不足",
    )

    watchboard.annotate_route_runtime(route_b, {}, [], [])
    watchboard.annotate_handoff_workers(route_b, handoff)

    assert route_b["display_state_zh"] == "Round04 planning ready for critic rereview / controller blocked"
    assert route_b["runtime_state"]["state"] == "planning_ready_for_critic_rereview"
    assert route_b["completion_blockers"] == []
    assert route_b["controller_allowed"] is False
    assert "Critic rereview" in route_b["current_worker_zh"]
    assert "ready token 前不得交 Controller" in route_b["next_action_zh"]


def test_future_round05_tokens_parse_without_controller_authority():
    text = "ROUTE_B_ROUND05_PLANNING_NEEDS_REVISION\nROUTE_C_ROUND05_REVIEW_EVIDENCE_COMPLETE"
    tokens = watchboard.extract_role_tokens(text)
    assert {token["round"] for token in tokens} == {5}
    assert {token["role"] for token in tokens} == {"planning_critic", "reviewer"}
    route = route_fixture(id="route_B", label="Route B", role_tokens=tokens)
    handoff = watchboard.parse_current_handoff(round04_current_style_text().replace("ROUND04", "ROUND05").replace("round04", "round05"), Path("/tmp/CARE"))
    watchboard.annotate_handoff_workers(route, handoff)
    assert route["controller_allowed"] is False
