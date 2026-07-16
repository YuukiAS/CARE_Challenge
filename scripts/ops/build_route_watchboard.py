#!/usr/bin/env python3
"""Build a read-only CARE SRR route watchboard.

The watchboard is intentionally observational: it reads route metadata, git,
tmux, Slurm, and result packet files, then writes a static HTML dashboard.
It never submits, cancels, merges, uploads, or mutates runtime state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import socketserver
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any


ROUTES = ("route_A", "route_B", "route_C")
ROUTE_LABELS = {
    "route_A": "Route A",
    "route_B": "Route B",
    "route_C": "Route C",
}
ROUTE_ARCHITECTURE_HINTS = {
    "route_A": [
        "最快形成非纯 nnU-Net submission candidate 的压缩 SRR 路线。",
        "当前应先完成 route 合同、implementation gap list 和 validation gate。",
        "具体实现架构等待 Route A 合同和缺口清单落地后再收敛。",
    ],
    "route_B": [
        "完整 SRR-v3 架构实现路线。",
        "正式训练前必须暴露 model/loss/dataflow 的完整缺口清单。",
        "具体 component wiring 应在 Route B 合同写入后由这里展示。",
    ],
    "route_C": [
        "继承 M10 evidence 与 Cine fidelity 的完整证据路线。",
        "重点是 M10 资产复用、证据连续性和 Cine temporal fidelity。",
        "具体 runtime architecture 应在 Route C 发布继承清单后从 M10 packet 派生。",
    ],
}
STATUS_KEYWORDS = (
    "NEEDS_MONITOR",
    "PENDING_MONITOR",
    "JOB_SUBMITTED",
    "PENDING_PRIORITY",
    "RUNNING",
    "AWAITING_SACCT",
    "NEEDS_EVIDENCE",
    "AWAITING_REVIEW",
    "COMPLETE",
    "PASS",
    "FAIL",
    "BLOCKED",
    "NOT_REVIEWED",
    "ROUTE_A_NEEDS_MONITOR",
    "ROUTE_A_REVIEW_NEEDS_REVISION",
    "ROUTE_B_SCIENTIFIC_UNDERTRAINED",
    "ROUTE_C_NEEDS_REVISION",
    "SCIENTIFIC_UNDERTRAINED",
    "NEEDS_REVISION",
    "TERMINAL_NON_READY_PACKET",
)
INCOMPLETE_KEYWORDS = (
    "NEEDS_MONITOR",
    "PENDING_MONITOR",
    "JOB_SUBMITTED",
    "PENDING_PRIORITY",
    "RUNNING",
    "AWAITING_SACCT",
)
REVIEW_PENDING_KEYWORDS = ("AWAITING_REVIEW", "NOT_REVIEWED")
FAILURE_KEYWORDS = ("NEEDS_EVIDENCE", "FAIL", "BLOCKED")
REVISION_KEYWORDS = ("NEEDS_REVISION", "ROUTE_A_REVIEW_NEEDS_REVISION", "ROUTE_C_NEEDS_REVISION")
UNDERTRAINED_KEYWORDS = ("SCIENTIFIC_UNDERTRAINED", "ROUTE_B_SCIENTIFIC_UNDERTRAINED")
PASS_KEYWORDS = ("PASS", "COMPLETE")
ACTIVE_SLURM_STATES = {
    "CONFIGURING",
    "COMPLETING",
    "PENDING",
    "REQUEUED",
    "RESIZING",
    "RUNNING",
    "SUSPENDED",
}
SLURM_PENDING_STATES = {"PENDING", "CONFIGURING", "REQUEUED", "RESIZING"}
SLURM_RUNNING_STATES = {"RUNNING", "COMPLETING", "SUSPENDED"}
ROUTE_JOB_HINTS = {
    "route_A": ("route_A", "RouteA", "route-a", "care_route_A", "Route A"),
    "route_B": ("route_B", "RouteB", "route-b", "care_route_B", "Route B"),
    "route_C": ("route_C", "RouteC", "route-c", "care_route_C", "Route C"),
}
PACKET_LABELS_ZH = {
    "result": "结果包",
    "controller_report": "Controller 报告",
    "manifest": "清单",
    "review": "独立审查",
    "completion_check": "完成检查",
    "review_request": "审查请求",
}
CARE_PARTITION_ORDER = ("htzhulab", "a100-gpu", "volta-gpu")
TMUX_SESSION_PLAN = (
    {
        "session": "care_watchboard",
        "label_zh": "Watchboard 服务",
        "purpose_zh": "本地 shell、动态看板服务与 cloudflared tunnel",
        "expected_windows": ("bash", "watchboard-tunnel"),
    },
    {
        "session": "care_route_A",
        "label_zh": "Route A 常驻工作台",
        "purpose_zh": "controller、continue、executor、reviewer 分窗隔离",
        "route": "route_A",
        "controller_window": "RouteA-Controller",
        "reviewer_window": "RouteA-Reviewer",
        "expected_windows": ("RouteA-Controller", "RouteA-Continue", "RouteA-Exec", "RouteA-Reviewer"),
    },
    {
        "session": "care_route_B",
        "label_zh": "Route B 常驻工作台",
        "purpose_zh": "Route B controller",
        "route": "route_B",
        "controller_window": "RouteB-Controller",
        "reviewer_window": "",
        "expected_windows": ("RouteB-Controller",),
    },
    {
        "session": "care_route_C",
        "label_zh": "Route C 常驻工作台",
        "purpose_zh": "Route C controller",
        "route": "route_C",
        "controller_window": "RouteC-Controller",
        "reviewer_window": "",
        "expected_windows": ("RouteC-Controller",),
    },
)
ROUTE_TMUX_PLAN = {spec["route"]: spec for spec in TMUX_SESSION_PLAN if spec.get("route")}
FORBIDDEN_ACTIONS = (
    "scancel",
    "sbatch",
    "srun",
    "git merge",
    "git push",
    "upload",
)


def run_cmd(args: list[str], cwd: Path, timeout: int = 8) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "stderr": f"{args[0]} not found", "code": 127}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "timeout", "code": 124}
    return {
        "ok": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "code": completed.returncode,
    }


def read_text(path: Path, limit: int = 80_000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    data = path.read_text(encoding="utf-8", errors="replace")
    if len(data) > limit:
        return data[:limit] + "\n[truncated]\n"
    return data


def parse_markdown_field_table(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in {"field", "字段"}:
            continue
        value = re.sub(r"`([^`]+)`", r"\1", cells[1])
        value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
        fields[cells[0].lower()] = value
    return fields


def field_value(fields: dict[str, str], *names: str, default: str = "unknown") -> str:
    for name in names:
        if name in fields and fields[name]:
            return fields[name]
    return default


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def extract_status_keywords(text: str) -> list[str]:
    found: list[str] = []
    for keyword in STATUS_KEYWORDS:
        pattern = rf"(?<![A-Z0-9_]){re.escape(keyword)}(?![A-Z0-9_])"
        if re.search(pattern, text) and keyword not in found:
            found.append(keyword)
    return found


def extract_slurm_job_ids(text: str) -> list[str]:
    """Extract likely Slurm job IDs from lightweight packet text."""
    ids: set[str] = set()
    direct_patterns = [
        r"(?i)\b(?:job(?:\s*id)?|job_id|jobid|slurm[_ -]?job|sbatch(?:\s+submitted)?)\D{0,30}(\d+(?:[_\.]\d+)?)",
        r"\b(\d{5,}(?:_\d+)?)\|[^\n|]*(?:COMPLETED|FAILED|CANCELLED|PENDING|RUNNING|TIMEOUT)",
    ]
    for pattern in direct_patterns:
        for match in re.finditer(pattern, text):
            ids.add(match.group(1))
    return sorted(ids, key=job_sort_key)


def job_sort_key(job_id: str) -> tuple[int, str]:
    match = re.match(r"(\d+)", job_id)
    return (int(match.group(1)) if match else 0, job_id)


def normalize_job_id(job_id: str) -> str:
    return job_id.split(".", 1)[0]


def compact_job(job: dict[str, str]) -> dict[str, str]:
    keys = ("id", "partition", "name", "state", "time", "reason", "exit_code", "elapsed", "start", "end", "source")
    return {key: job.get(key, "") for key in keys if job.get(key, "")}


def route_name_matches(route: str, name: str) -> bool:
    lowered = name.lower()
    return any(hint.lower() in lowered for hint in ROUTE_JOB_HINTS[route])


def job_matches_route(job: dict[str, str], route: dict[str, Any]) -> bool:
    job_id = normalize_job_id(job.get("id", ""))
    route_ids = {normalize_job_id(value) for value in route.get("slurm_job_ids", [])}
    return bool(job_id and job_id in route_ids) or route_name_matches(route["id"], job.get("name", ""))


def evidence_summary_zh(packet_files: dict[str, Path], latest_packet: Path | None) -> str:
    existing = [PACKET_LABELS_ZH[name] for name, path in packet_files.items() if path.exists()]
    if not existing:
        return "尚未发现 route 结果包；当前只能展示 route README 和运行环境。"
    latest = latest_packet.name if latest_packet else "未知文件"
    return f"已发现 {len(existing)} 类轻量证据：{'、'.join(existing)}；最新证据为 {latest}。"


def relative_repo_path(root: Path, raw: str) -> dict[str, Any]:
    value = raw.strip().strip("`")
    if not value or value == "NO_CURRENT_CRITIC_HANDOFF":
        return {"path": value, "exists": False, "active": False, "absolute_path": ""}
    candidate = Path(value)
    absolute = candidate if candidate.is_absolute() else root / candidate
    return {
        "path": value,
        "exists": absolute.exists(),
        "active": True,
        "absolute_path": str(absolute),
    }


def first_fenced_path_after(text: str, marker: str) -> str:
    start = text.find(marker)
    if start < 0:
        return ""
    match = re.search(r"```text\s*([^`\n][^`]*)```", text[start:], re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip().splitlines()[0].strip()


def parse_current_handoff(text: str, root: Path) -> dict[str, Any]:
    round_id = re.search(r"(?m)^round_id:\s*(\S+)", text)
    round_date = re.search(r"(?m)^date:\s*(\S+)", text)
    planner_prompt = first_fenced_path_after(text, "The single portfolio GPT planner should read:")
    critics: dict[str, dict[str, Any]] = {}
    for route in ROUTES:
        match = re.search(rf"(?m)^{re.escape(route)} critic current prompt:\s*\n([^\n]+)", text)
        raw = match.group(1).strip() if match else "NO_CURRENT_CRITIC_HANDOFF"
        critics[route] = relative_repo_path(root, raw)
    return {
        "round_id": round_id.group(1) if round_id else "unknown",
        "date": round_date.group(1) if round_date else "",
        "planner_prompt": relative_repo_path(root, planner_prompt),
        "critics": critics,
    }


def collect_handoff_status(root: Path) -> dict[str, Any]:
    current_path = root / "prompts" / "routes" / "handoffs" / "CURRENT.md"
    text = read_text(current_path)
    if not text:
        return {
            "current_path": str(current_path),
            "current_exists": False,
            "round_id": "unknown",
            "date": "",
            "planner_prompt": {"path": "", "exists": False, "active": False, "absolute_path": ""},
            "critics": {route: relative_repo_path(root, "NO_CURRENT_CRITIC_HANDOFF") for route in ROUTES},
            "current_worker_zh": "等待发布当前轮次入口",
            "next_worker_zh": "规划者补齐 CURRENT.md",
        }
    parsed = parse_current_handoff(text, root)
    active_critics = [ROUTE_LABELS[route] for route, entry in parsed["critics"].items() if entry.get("active")]
    if active_critics:
        current_worker = "、".join(f"{label} Critic 正在判断" for label in active_critics)
        next_worker = "规划者汇总 Critic 结论后决定下一步"
    elif parsed["planner_prompt"].get("active"):
        current_worker = "规划者正在处理"
        next_worker = "按规划者结论交给 Critic、Controller 或 Reviewer"
    else:
        current_worker = "等待发布规划者入口"
        next_worker = "规划者补齐当前轮次提示词"
    return {
        "current_path": str(current_path),
        "current_exists": True,
        **parsed,
        "current_worker_zh": current_worker,
        "next_worker_zh": next_worker,
    }


def result_label_zh(route: dict[str, Any]) -> str:
    state = route.get("display_state_zh") or "待判定"
    if route.get("completion_blockers"):
        return "未完成"
    return state


def annotate_handoff_workers(route: dict[str, Any], handoff: dict[str, Any]) -> None:
    critic = handoff.get("critics", {}).get(route["id"], relative_repo_path(Path("/"), "NO_CURRENT_CRITIC_HANDOFF"))
    route["round_id"] = handoff.get("round_id", "unknown")
    route["critic_handoff"] = critic
    if critic.get("active") and critic.get("exists"):
        critic_state = "已发布"
    elif critic.get("active"):
        critic_state = "文件缺失"
    else:
        critic_state = "未发布"
    route["critic_handoff_state_zh"] = critic_state

    display_state = route.get("display_state_zh", "")
    result_state = result_label_zh(route)
    has_result_packet = bool(route.get("packet_files", {}).get("result") or route.get("packet_files", {}).get("controller_report"))
    has_review = bool(route.get("packet_files", {}).get("review"))

    if display_state in {"Slurm 运行中", "Slurm 排队中", "等待监控", "等待 sacct", "未完成"}:
        route["current_worker_zh"] = "Controller 正在执行"
        route["work_summary_zh"] = f"Controller 尚未形成可审查结果，当前状态：{result_state}。"
        route["next_action_zh"] = "等待 Slurm 完成并提交完成后聚合证据。"
    elif not has_result_packet:
        route["current_worker_zh"] = "等待任务启动"
        route["work_summary_zh"] = "尚未形成结果包。"
        route["next_action_zh"] = "等待规划者或 Controller 发布任务。"
    elif not has_review:
        route["current_worker_zh"] = "需要 Reviewer"
        route["work_summary_zh"] = f"Controller 已执行完毕，结果：{result_state}。"
        route["next_action_zh"] = f"需要 {route['label']} Reviewer 只读审查结果包。"
    elif critic.get("active"):
        route["current_worker_zh"] = f"{route['label']} Critic 正在判断"
        route["work_summary_zh"] = f"Reviewer 已完成，结论：{result_state}。"
        if critic.get("exists"):
            route["next_action_zh"] = "规划者汇总 Critic 结论后决定是否交回 Controller。"
        else:
            route["next_action_zh"] = "Critic 提示词文件缺失，需先修正 CURRENT.md 指向。"
    elif has_review:
        route["current_worker_zh"] = "等待规划者"
        route["work_summary_zh"] = f"Reviewer 已完成，结论：{result_state}。"
        route["next_action_zh"] = "等待规划者汇总审查结论并决定下一步。"
    else:
        route["current_worker_zh"] = "等待规划者"
        route["work_summary_zh"] = f"当前结果：{result_state}。"
        route["next_action_zh"] = "等待规划者决定下一步。"

    route["next_worker_zh"] = route["next_action_zh"]


def reviewability_from_state(display_state: str, blockers: list[str]) -> dict[str, Any]:
    if blockers:
        return {
            "can_review_complete": False,
            "label_zh": "不可作为完成包审查",
            "reason_zh": "存在未完成运行态或缺失聚合证据。",
        }
    if display_state == "待独立审查":
        return {
            "can_review_complete": True,
            "label_zh": "可进入独立审查",
            "reason_zh": "已有审查请求且未发现 pending/monitor 阻断 token。",
        }
    if display_state == "审查通过":
        return {
            "can_review_complete": True,
            "label_zh": "已审查通过",
            "reason_zh": "存在 review 证据且未发现未完成阻断 token。",
        }
    return {
        "can_review_complete": False,
        "label_zh": "尚不可审查为完成",
        "reason_zh": "route 合同、运行证据或独立审查尚未形成完成闭环。",
    }


def annotate_route_runtime(
    route: dict[str, Any],
    tmux: dict[str, bool],
    jobs: list[dict[str, str]],
    recent_jobs: list[dict[str, str]],
    controller_activity: dict[str, Any] | None = None,
) -> None:
    matched_jobs = [job for job in jobs + recent_jobs if job_matches_route(job, route)]
    seen: set[tuple[str, str]] = set()
    deduped_jobs: list[dict[str, str]] = []
    for job in matched_jobs:
        key = (job.get("id", ""), job.get("source", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped_jobs.append(job)

    route_ids = {normalize_job_id(value) for value in route.get("slurm_job_ids", [])}
    route_ids.update(normalize_job_id(job.get("id", "")) for job in deduped_jobs if job.get("id"))
    route["slurm_job_ids"] = sorted((value for value in route_ids if value), key=job_sort_key)
    route["recent_slurm_jobs"] = [compact_job(job) for job in deduped_jobs[:12]]

    blockers: list[str] = []
    for keyword in route["status_keywords"]:
        if keyword in INCOMPLETE_KEYWORDS:
            blockers.append(f"packet 包含 {keyword}，不能作为完成证据")

    current_states = {job.get("state", "").split()[0] for job in deduped_jobs if job.get("source") == "squeue"}
    recent_terminal_states = {job.get("state", "").split()[0] for job in deduped_jobs if job.get("source") == "sacct"}
    active_states = current_states & ACTIVE_SLURM_STATES
    monitor_keyword_present = any(keyword in route["status_keywords"] for keyword in INCOMPLETE_KEYWORDS)
    completed_after_monitor = bool(monitor_keyword_present and "COMPLETED" in recent_terminal_states and not active_states)
    if current_states & SLURM_PENDING_STATES:
        blockers.append("Slurm 当前仍有排队作业")
    if current_states & SLURM_RUNNING_STATES:
        blockers.append("Slurm 当前仍有运行中作业")
    if completed_after_monitor:
        blockers.append("Slurm job 已完成，但 packet 仍是 monitor 状态；需要完成后聚合/提交")

    keywords = set(route["status_keywords"])
    if blockers:
        if completed_after_monitor:
            display_state = "需补证据"
        elif "NEEDS_MONITOR" in keywords or "PENDING_MONITOR" in keywords:
            display_state = "等待监控"
        elif "AWAITING_SACCT" in keywords:
            display_state = "等待 sacct"
        elif current_states & SLURM_RUNNING_STATES or "RUNNING" in keywords:
            display_state = "Slurm 运行中"
        elif current_states & SLURM_PENDING_STATES or "JOB_SUBMITTED" in keywords or "PENDING_PRIORITY" in keywords:
            display_state = "Slurm 排队中"
        else:
            display_state = "未完成"
    elif keywords & set(UNDERTRAINED_KEYWORDS):
        display_state = "训练不足"
    elif keywords & set(REVISION_KEYWORDS):
        display_state = "需修订"
    elif keywords & set(FAILURE_KEYWORDS):
        display_state = "审查未通过" if route["packet_files"].get("review") else "需补证据"
    elif route["packet_files"].get("review") and keywords & set(PASS_KEYWORDS):
        display_state = "审查通过"
    elif route["packet_files"].get("review_request") or keywords & set(REVIEW_PENDING_KEYWORDS):
        display_state = "待独立审查"
    elif tmux.get(route["controller_tmux"]):
        if controller_activity and controller_activity.get("state") == "completed_or_idle":
            display_state = "Controller 已结束"
        else:
            display_state = "Controller 运行中"
    elif str(route.get("current_status", "")).lower() == "setup only":
        display_state = "仅环境搭建"
    elif not route.get("result_root_exists"):
        display_state = "等待合同"
    else:
        display_state = "等待合同"

    route["display_state_zh"] = display_state
    if display_state in {"训练不足", "需修订", "Controller 已结束"}:
        route["reviewability"] = {
            "can_review_complete": False,
            "label_zh": "终态非 ready",
            "reason_zh": "controller 已停止或 packet 给出非 ready 终态，需要 reviewer/GPT 决策或修订。",
        }
    else:
        route["reviewability"] = reviewability_from_state(display_state, blockers)
    route["completion_blockers"] = blockers
    route["controller_activity"] = controller_activity or {}


def latest_existing(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def route_scoped_path(root: Path, worktree: Path, value: str, default: str) -> tuple[Path, str]:
    raw = value or default
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate, "absolute"
    worktree_candidate = worktree / candidate
    root_candidate = root / candidate
    if worktree_candidate.exists() or worktree.exists():
        return worktree_candidate, "worktree"
    return root_candidate, "main"


def controller_activity_from_pane(root: Path, target: str) -> dict[str, Any]:
    pane_target = target if ":" in target else f"{target}:0.0"
    captured = run_cmd(["tmux", "capture-pane", "-pt", pane_target, "-S", "-80"], root, timeout=3)
    text = captured["stdout"] if captured["ok"] else ""
    complete_markers = (
        "Goal achieved",
        "Goal 已标记完成",
        "Goal 已标记 complete",
        "Active goal 已标记完成",
        "已完成",
    )
    prompt_markers = ("› Implement", "› Explain", "gpt-5.5", "Context")
    return {
        "ok": captured["ok"],
        "state": "completed_or_idle" if any(marker in text for marker in complete_markers) else "active_or_unknown",
        "has_prompt": any(marker in text for marker in prompt_markers),
        "tail": "\n".join(text.splitlines()[-12:]),
    }


def collect_route(root: Path, worktree_root: Path, route: str) -> dict[str, Any]:
    route_readme = root / "routes" / route / "README.md"
    readme_text = read_text(route_readme)
    fields = parse_markdown_field_table(readme_text)
    worktree = Path(fields.get("worktree") or worktree_root / route)
    result_root, result_root_source = route_scoped_path(root, worktree, fields.get("result root", ""), f"results/{route}")

    branch = fields.get("branch", route)
    git_sha = run_cmd(["git", "rev-parse", branch], root)
    ahead_behind = run_cmd(["git", "rev-list", "--left-right", "--count", f"main...{branch}"], root)
    worktree_branch = run_cmd(["git", "-C", str(worktree), "branch", "--show-current"], root) if worktree.exists() else {"stdout": "", "ok": False}
    worktree_dirty = run_cmd(["git", "-C", str(worktree), "status", "--porcelain"], root) if worktree.exists() else {"stdout": "", "ok": False}

    packet_files = {
        "result": result_root / "result.md",
        "controller_report": result_root / "controller_report.md",
        "manifest": result_root / "MANIFEST.md",
        "review": result_root / "review.md",
        "completion_check": result_root / "completion_check.md",
        "review_request": result_root / "review_request.md",
    }
    packet_texts = {name: read_text(path) for name, path in packet_files.items()}
    latest_packet = latest_existing(list(packet_files.values()))
    combined_packet_text = "\n".join(packet_texts.values())

    architecture_file = latest_existing(
        [
            root / "routes" / route / "architecture.md",
            result_root / "architecture.md",
            result_root / "execution_plan.md",
            result_root / "controller_report.md",
        ]
    )
    architecture_text = read_text(architecture_file, limit=20_000) if architecture_file else ""
    architecture_lines = []
    if architecture_text:
        for line in architecture_text.splitlines():
            clean = line.strip(" -\t")
            if clean and not clean.startswith("#") and len(clean) < 180:
                architecture_lines.append(clean)
            if len(architecture_lines) >= 4:
                break
    if not architecture_lines:
        architecture_lines = ROUTE_ARCHITECTURE_HINTS[route]

    status_keywords = extract_status_keywords(combined_packet_text)
    slurm_job_ids = extract_slurm_job_ids(combined_packet_text)

    tmux_plan = ROUTE_TMUX_PLAN[route]
    tmux_session = fields.get("tmux session", tmux_plan["session"])
    controller_window = fields.get("controller window", tmux_plan.get("controller_window", ""))
    reviewer_window = fields.get("reviewer window", tmux_plan.get("reviewer_window", ""))
    legacy_controller_tmux = fields.get("controller tmux", "")
    legacy_reviewer_tmux = fields.get("reviewer tmux", "")

    return {
        "id": route,
        "label": ROUTE_LABELS[route],
        "title": first_heading(readme_text) or ROUTE_LABELS[route],
        "purpose": field_value(fields, "route purpose", "route 目的"),
        "branch": branch,
        "sha": git_sha["stdout"] if git_sha["ok"] else "MISSING_BRANCH",
        "ahead_behind_main": ahead_behind["stdout"] if ahead_behind["ok"] else "unknown",
        "worktree": str(worktree),
        "worktree_exists": worktree.exists(),
        "worktree_branch": worktree_branch["stdout"] if worktree_branch["ok"] else "",
        "dirty_count": len([line for line in worktree_dirty["stdout"].splitlines() if line.strip()]) if worktree_dirty["ok"] else None,
        "tmux_session": tmux_session,
        "expected_tmux_windows": list(tmux_plan["expected_windows"]),
        "controller_tmux_window": controller_window,
        "reviewer_tmux_window": reviewer_window,
        "controller_tmux": tmux_session,
        "reviewer_tmux": tmux_session if reviewer_window else "",
        "legacy_controller_tmux": legacy_controller_tmux,
        "legacy_reviewer_tmux": legacy_reviewer_tmux,
        "controller_tmux_target": f"{tmux_session}:{controller_window}.0" if controller_window else tmux_session,
        "reviewer_tmux_target": f"{tmux_session}:{reviewer_window}.0" if reviewer_window else "",
        "tmux_window_status": {},
        "result_root": str(result_root),
        "result_root_source": result_root_source,
        "result_root_exists": result_root.exists(),
        "runtime_root": fields.get("runtime root", f"results/{route}/runtime/"),
        "log_root": fields.get("log root", f"logs/{route}/"),
        "lock_root": fields.get("lock root", f"results/{route}/locks/"),
        "current_status": field_value(fields, "current status", "当前状态"),
        "next_gate": field_value(fields, "next gate", "下一个 gate"),
        "packet_files": {name: path.exists() for name, path in packet_files.items()},
        "latest_packet": str(latest_packet) if latest_packet else "",
        "latest_packet_mtime": dt.datetime.fromtimestamp(latest_packet.stat().st_mtime).isoformat(timespec="seconds") if latest_packet else "",
        "status_keywords": status_keywords,
        "display_state_zh": "待判定",
        "reviewability": {},
        "completion_blockers": [],
        "slurm_job_ids": slurm_job_ids,
        "recent_slurm_jobs": [],
        "evidence_summary_zh": evidence_summary_zh(packet_files, latest_packet),
        "architecture_source": str(architecture_file) if architecture_file else "route default",
        "architecture_lines": architecture_lines,
    }


def collect_tmux(root: Path, sessions: list[str]) -> dict[str, bool]:
    status: dict[str, bool] = {}
    for session in sessions:
        if not session:
            continue
        check = run_cmd(["tmux", "has-session", "-t", session], root, timeout=3)
        status[session] = check["ok"]
    return status


def parse_tmux_windows(stdout: str) -> list[dict[str, str]]:
    windows: list[dict[str, str]] = []
    for line in stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        windows.append({"index": parts[0], "name": parts[1], "command": parts[2]})
    return windows


def parse_tmux_panes(stdout: str, session: str) -> list[dict[str, str]]:
    panes: list[dict[str, str]] = []
    for line in stdout.splitlines():
        parts = line.split("|", 4)
        if len(parts) < 5 or parts[0] != session:
            continue
        panes.append(
            {
                "window": parts[1],
                "pane": parts[2],
                "title": parts[3],
                "command": parts[4],
            }
        )
    return panes


def collect_tmux_topology(root: Path, tmux: dict[str, bool]) -> list[dict[str, Any]]:
    topology: list[dict[str, Any]] = []
    all_panes = run_cmd(
        ["tmux", "list-panes", "-a", "-F", "#{session_name}|#{window_name}|#{pane_index}|#{pane_title}|#{pane_current_command}"],
        root,
        timeout=3,
    )
    for spec in TMUX_SESSION_PLAN:
        session = spec["session"]
        present = tmux.get(session, False)
        windows_result = run_cmd(["tmux", "list-windows", "-t", session, "-F", "#{window_index}|#{window_name}|#{pane_current_command}"], root, timeout=3) if present else {"ok": False, "stdout": ""}
        windows = parse_tmux_windows(windows_result["stdout"]) if windows_result["ok"] else []
        live_names = {window["name"] for window in windows}
        expected = list(spec["expected_windows"])
        topology.append(
            {
                "session": session,
                "label_zh": spec["label_zh"],
                "purpose_zh": spec["purpose_zh"],
                "route": spec.get("route", ""),
                "present": present,
                "expected_windows": expected,
                "window_status": {name: name in live_names for name in expected},
                "live_windows": windows,
                "panes": parse_tmux_panes(all_panes["stdout"], session) if all_panes["ok"] and present else [],
            }
        )
    return topology


def annotate_route_tmux(route: dict[str, Any], topology_by_session: dict[str, dict[str, Any]]) -> None:
    session_info = topology_by_session.get(route.get("tmux_session", ""), {})
    route["tmux_window_status"] = session_info.get("window_status", {})
    route["tmux_live_windows"] = session_info.get("live_windows", [])
    route["tmux_panes"] = session_info.get("panes", [])


def parse_squeue(stdout: str) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    for line in stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 7:
            continue
        jobs.append(
            {
                "id": parts[0],
                "user": parts[1],
                "partition": parts[2],
                "name": parts[3],
                "state": parts[4],
                "time": parts[5],
                "reason": parts[6],
                "is_route_job": any(route_name_matches(route, parts[3]) for route in ROUTES),
                "is_general": parts[2] == "general",
                "source": "squeue",
            }
        )
    return jobs


def normalize_partition_name(name: str) -> str:
    return name.rstrip("*")


def parse_sinfo(stdout: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 6 or parts[0] == "PARTITION":
            continue
        rows.append(
            {
                "partition": parts[0],
                "partition_key": normalize_partition_name(parts[0]),
                "availability": parts[1],
                "time_limit": parts[2],
                "nodes": parts[3],
                "state": parts[4],
                "gres": parts[5],
            }
        )
    return rows


def dedupe_slurm_jobs(jobs: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for job in jobs:
        key = (job.get("id", ""), job.get("partition", ""), job.get("name", ""), job.get("source", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(job)
    return deduped


def dedupe_sinfo_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()
    for row in rows:
        key = (
            row.get("partition_key", ""),
            row.get("availability", ""),
            row.get("time_limit", ""),
            row.get("nodes", ""),
            row.get("state", ""),
            row.get("gres", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def care_partition_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_partition: dict[str, list[dict[str, str]]] = {name: [] for name in CARE_PARTITION_ORDER}
    for row in rows:
        key = row.get("partition_key") or normalize_partition_name(row["partition"])
        if key in by_partition:
            by_partition[key].append(row)

    summary: list[dict[str, str]] = []
    for partition in CARE_PARTITION_ORDER:
        matches = by_partition[partition]
        if not matches:
            summary.append(
                {
                    "partition": partition,
                    "partition_key": partition,
                    "availability": "不可见",
                    "time_limit": "unknown",
                    "nodes": "0",
                    "state": "NO_SINFO_ROW",
                    "gres": "未在当前 sinfo 输出中出现",
                }
            )
            continue
        for row in matches:
            summary.append(row)
    return summary


def parse_sacct(stdout: str) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    for line in stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 8:
            continue
        job_id, name, partition, state, exit_code, elapsed, start, end = parts[:8]
        normalized_state = state.split()[0] if state else ""
        jobs.append(
            {
                "id": job_id,
                "partition": partition,
                "name": name,
                "state": normalized_state,
                "exit_code": exit_code,
                "elapsed": elapsed,
                "start": start,
                "end": end,
                "is_route_job": any(route_name_matches(route, name) for route in ROUTES),
                "is_general": partition == "general",
                "source": "sacct",
            }
        )
    return jobs


def collect_status(root: Path, worktree_root: Path, user: str) -> dict[str, Any]:
    routes = [collect_route(root, worktree_root, route) for route in ROUTES]
    sessions = [spec["session"] for spec in TMUX_SESSION_PLAN]
    for route in routes:
        sessions.append(route["controller_tmux"])
        sessions.append(route["reviewer_tmux"])
    tmux = collect_tmux(root, sorted({session for session in sessions if session}))
    tmux_topology = collect_tmux_topology(root, tmux)
    topology_by_session = {item["session"]: item for item in tmux_topology}
    for route in routes:
        annotate_route_tmux(route, topology_by_session)
    controller_activities = {
        route["id"]: controller_activity_from_pane(root, route["controller_tmux_target"])
        for route in routes
        if tmux.get(route["controller_tmux"], False) and route.get("controller_tmux_target")
    }

    squeue = run_cmd(["squeue", "-h", "-u", user, "-o", "%i|%u|%P|%j|%T|%M|%R"], root)
    sinfo = run_cmd(["sinfo", "-o", "%P|%a|%l|%D|%t|%G"], root)
    partition_squeues = {
        partition: run_cmd(["squeue", "-h", "-u", user, "-p", partition, "-o", "%i|%u|%P|%j|%T|%M|%R"], root)
        for partition in CARE_PARTITION_ORDER
    }
    partition_sinfos = {
        partition: run_cmd(["sinfo", "-p", partition, "-o", "%P|%a|%l|%D|%t|%G"], root)
        for partition in CARE_PARTITION_ORDER
    }
    sacct_start = (dt.date.today() - dt.timedelta(days=14)).isoformat()
    sacct = run_cmd(
        [
            "sacct",
            "-n",
            "-P",
            "-S",
            sacct_start,
            "-u",
            user,
            "--format",
            "JobIDRaw,JobName,Partition,State,ExitCode,Elapsed,Start,End",
        ],
        root,
    )
    git_main = run_cmd(["git", "rev-parse", "main"], root)
    git_origin_main = run_cmd(["git", "rev-parse", "origin/main"], root)
    git_current = run_cmd(["git", "branch", "--show-current"], root)

    jobs = parse_squeue(squeue["stdout"]) if squeue["ok"] else []
    for result in partition_squeues.values():
        if result["ok"]:
            jobs.extend(parse_squeue(result["stdout"]))
    jobs = dedupe_slurm_jobs(jobs)
    recent_jobs = parse_sacct(sacct["stdout"]) if sacct["ok"] else []
    sinfo_rows = parse_sinfo(sinfo["stdout"]) if sinfo["ok"] else []
    for result in partition_sinfos.values():
        if result["ok"]:
            sinfo_rows.extend(parse_sinfo(result["stdout"]))
    sinfo_rows = dedupe_sinfo_rows(sinfo_rows)
    partitions = care_partition_summary(sinfo_rows)

    handoff = collect_handoff_status(root)
    for route in routes:
        annotate_route_runtime(route, tmux, jobs, recent_jobs, controller_activities.get(route["id"]))
        annotate_handoff_workers(route, handoff)

    route_jobs = [job for job in jobs if job["is_route_job"] or any(job_matches_route(job, route) for route in routes)]
    general_jobs = [job for job in jobs if job["partition"] == "general"]
    warnings = []
    if general_jobs:
        warnings.append("general partition 作业只读展示；不要从 watchboard 取消或修改它们。")
    if not sacct["ok"]:
        warnings.append("sacct 最近作业查询不可用；看板仍显示 squeue 当前态和已落盘证据。")
    if not partition_sinfos["htzhulab"]["ok"]:
        warnings.append("htzhulab 分区专项 sinfo 查询不可用；分区摘要可能缺少 lab GPU 当前态。")
    if not handoff.get("current_exists"):
        warnings.append("CURRENT.md 不存在或不可读；GPT round/worker 状态无法自动判定。")
    planner_entry = handoff.get("planner_prompt", {})
    if planner_entry.get("active") and not planner_entry.get("exists"):
        warnings.append(f"规划者提示词指向的文件不存在：{planner_entry.get('path', '')}。")
    for route_id, critic_entry in handoff.get("critics", {}).items():
        if critic_entry.get("active") and not critic_entry.get("exists"):
            warnings.append(f"{ROUTE_LABELS.get(route_id, route_id)} Critic 提示词指向的文件不存在：{critic_entry.get('path', '')}。")
    for route in routes:
        if not route["result_root_exists"]:
            warnings.append(f"{route['label']} 尚无 result root，当前仍处于合同/环境阶段。")
        if not tmux.get(route["controller_tmux"], False):
            warnings.append(f"{route['label']} tmux session {route['controller_tmux']} 未启动或不可见。")
        missing_windows = [name for name, present in route.get("tmux_window_status", {}).items() if not present]
        if missing_windows:
            warnings.append(f"{route['label']} tmux 缺少窗口：{', '.join(missing_windows)}。")
        if route["dirty_count"]:
            warnings.append(f"{route['label']} worktree 有 {route['dirty_count']} 个未提交变更。")
        for blocker in route["completion_blockers"]:
            warnings.append(f"{route['label']} 未完成阻断：{blocker}")

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "care_root": str(root),
        "worktree_root": str(worktree_root),
        "user": user,
        "git": {
            "current_branch": git_current["stdout"],
            "main_sha": git_main["stdout"] if git_main["ok"] else "",
            "origin_main_sha": git_origin_main["stdout"] if git_origin_main["ok"] else "",
        },
        "routes": routes,
        "handoff": handoff,
        "tmux": tmux,
        "tmux_topology": tmux_topology,
        "controller_activities": controller_activities,
        "jobs": jobs,
        "recent_jobs": recent_jobs,
        "route_jobs": route_jobs,
        "general_jobs": general_jobs,
        "partitions": partitions,
        "warnings": warnings,
        "guardrails": {
            "mode": "read-only",
            "forbidden_actions": FORBIDDEN_ACTIONS,
            "general_partition_policy": "display only; never cancel or mutate from this watchboard",
        },
        "command_health": {
            "squeue": {"ok": squeue["ok"], "stderr": squeue["stderr"]},
            "sinfo": {"ok": sinfo["ok"], "stderr": sinfo["stderr"]},
            "squeue_partitions": {
                partition: {"ok": result["ok"], "stderr": result["stderr"]}
                for partition, result in partition_squeues.items()
            },
            "sinfo_partitions": {
                partition: {"ok": result["ok"], "stderr": result["stderr"]}
                for partition, result in partition_sinfos.items()
            },
            "sacct": {"ok": sacct["ok"], "stderr": sacct["stderr"]},
        },
    }


def status_class(route: dict[str, Any], tmux: dict[str, bool]) -> str:
    state = route.get("display_state_zh", "")
    if state in {"Controller 运行中", "Slurm 运行中", "Slurm 排队中"}:
        return "active"
    if route.get("completion_blockers") or state in {"需补证据", "等待监控", "等待 sacct", "未完成"}:
        return "risk"
    if state in {"训练不足"}:
        return "undertrained"
    if state in {"需修订", "审查未通过"}:
        return "revision"
    if state in {"Controller 已结束"}:
        return "ended"
    if state in {"待独立审查", "审查通过"}:
        return "review"
    if tmux.get(route["controller_tmux"]):
        return "ended"
    return "idle"


def render_badge(label: str, class_name: str = "badge") -> str:
    return f'<span class="{class_name}">{html.escape(label)}</span>'


def soft_wrap_token(value: str) -> str:
    escaped = html.escape(value)
    return escaped.replace("/", "/<wbr>").replace("-", "-<wbr>").replace("_", "_<wbr>")


def window_badges(window_status: dict[str, bool]) -> str:
    if not window_status:
        return render_badge("未配置窗口", "badge muted")
    return "".join(
        render_badge(name, "badge ok" if present else "badge danger")
        for name, present in window_status.items()
    )


def tmux_presence_label(present: bool) -> str:
    return "可见" if present else "未启动/不可见"


def render_tmux_topology(data: dict[str, Any]) -> str:
    rows = []
    for item in data.get("tmux_topology", []):
        live = item.get("live_windows", [])
        live_text = ", ".join(f"{window.get('name', '')}/{window.get('command', '')}" for window in live) or "无"
        pane_text = ", ".join(
            f"{pane.get('window', '')}:{pane.get('pane', '')}/{pane.get('command', '')}"
            for pane in item.get("panes", [])
        ) or "无"
        row_class = "tmux-present" if item.get("present") else "tmux-missing"
        rows.append(
            f"""
            <tr class="{row_class}">
              <td><strong>{html.escape(item.get('session', ''))}</strong><br><span>{html.escape(item.get('label_zh', ''))}</span></td>
              <td>{html.escape(item.get('purpose_zh', ''))}</td>
              <td><div class="badge-row compact">{window_badges(item.get('window_status', {}))}</div></td>
              <td>{html.escape(tmux_presence_label(item.get('present', False)))}</td>
              <td>{html.escape(live_text)}</td>
              <td>{html.escape(pane_text)}</td>
            </tr>
            """
        )
    body = "".join(rows) if rows else '<tr><td colspan="6">没有 tmux 拓扑数据。</td></tr>'
    return f"""
    <section class="panel tmux-topology">
      <div class="panel-head"><h2>tmux 常驻拓扑</h2><span>4 个常驻 session</span></div>
      <table>
        <thead><tr><th>Session</th><th>用途</th><th>预期窗口</th><th>状态</th><th>实际窗口/命令</th><th>Pane/命令</th></tr></thead>
        <tbody>{body}</tbody>
      </table>
    </section>
    """


def render_html(data: dict[str, Any], refresh_seconds: int = 60) -> str:
    route_cards = []
    tmux = data["tmux"]
    for route in data["routes"]:
        cls = status_class(route, tmux)
        packet_badges = "".join(
            render_badge(PACKET_LABELS_ZH.get(name, name), "badge ok" if exists else "badge muted")
            for name, exists in route["packet_files"].items()
        )
        keyword_badges = "".join(render_badge(keyword, "badge warn") for keyword in route["status_keywords"]) or render_badge("暂无 packet 状态", "badge muted")
        blocker_badges = "".join(render_badge(blocker, "badge danger") for blocker in route["completion_blockers"]) or render_badge(route["reviewability"].get("label_zh", "尚不可审查为完成"), "badge muted")
        architecture_items = "".join(f"<li>{html.escape(line)}</li>" for line in route["architecture_lines"])
        recent_job_rows = "".join(
            f"<tr><td>{html.escape(job.get('id', ''))}</td><td>{html.escape(job.get('source', ''))}</td><td>{html.escape(job.get('partition', ''))}</td><td>{html.escape(job.get('name', ''))}</td><td>{html.escape(job.get('state', ''))}</td><td>{html.escape(job.get('exit_code', job.get('reason', '')))}</td></tr>"
            for job in route["recent_slurm_jobs"]
        )
        if not recent_job_rows:
            recent_job_rows = '<tr><td colspan="6">未发现该 route 的 Slurm job。</td></tr>'
        route_cards.append(
            f"""
            <article class="route-card {cls}">
              <div class="route-head">
                <div>
                  <p class="eyeline">{html.escape(route['id'])}</p>
                  <h2>{html.escape(route['label'])}</h2>
                  <p class="purpose">{html.escape(route['purpose'])}</p>
                </div>
                <span class="state-pill">{html.escape(route['display_state_zh'])}</span>
              </div>
              <div class="round-strip">
                <span>{html.escape(route.get('round_id', 'unknown')).replace('round', '第 ')} 轮</span>
                <strong>当前：{html.escape(route.get('current_worker_zh', '未判定'))}</strong>
              </div>
              <div class="status-sentence">
                <p>{html.escape(route.get('work_summary_zh', '当前状态尚未判定。'))}</p>
                <p>{html.escape(route.get('next_action_zh', '等待下一步指派。'))}</p>
              </div>
              <div class="metric-row compact-metrics">
                <div><span>下一个关口</span><strong>{html.escape(route['next_gate'])}</strong></div>
                <div><span>tmux</span><strong>{html.escape(route['tmux_session'])}: {tmux_presence_label(tmux.get(route['tmux_session'], False))}</strong></div>
                <div><span>Controller 窗口</span><strong>{html.escape(route['controller_tmux_window'] or '未配置')}: {tmux_presence_label(route.get('tmux_window_status', {}).get(route['controller_tmux_window'], False)) if route['controller_tmux_window'] else '未配置'}</strong></div>
                <div><span>工作树变更</span><strong>{route['dirty_count'] if route['dirty_count'] is not None else 'n/a'}</strong></div>
              </div>
              <div class="route-section compact-section">
                <h3>tmux 窗口</h3>
                <div class="badge-row compact">{window_badges(route.get('tmux_window_status', {}))}</div>
              </div>
              <section class="route-section">
                <h3>SRR 架构/合同状态</h3>
                <ul class="architecture-list">{architecture_items}</ul>
                <p class="source">来源：{html.escape(route['architecture_source'])}</p>
              </section>
              <section class="route-section">
                <h3>证据与可审查性</h3>
                <p class="evidence-summary">{html.escape(route['evidence_summary_zh'])}</p>
                <div class="badge-row">{packet_badges}</div>
                <div class="badge-row">{keyword_badges}</div>
                <div class="badge-row">{blocker_badges}</div>
                <p class="path">{html.escape(route['result_root'])} ({html.escape(route.get('result_root_source', ''))})</p>
              </section>
              <section class="route-section">
                <h3>Slurm 关联作业</h3>
                <p class="source">作业 ID：{html.escape(', '.join(route['slurm_job_ids']) or '未发现')}</p>
                <table class="route-jobs-table">
                  <thead><tr><th>ID</th><th>来源</th><th>分区</th><th>名称</th><th>状态</th><th>退出码/原因</th></tr></thead>
                  <tbody>{recent_job_rows}</tbody>
                </table>
              </section>
            </article>
            """
        )

    jobs_by_partition: dict[str, list[dict[str, str]]] = {}
    for job in data["jobs"]:
        jobs_by_partition.setdefault(job["partition"], []).append(job)
    job_sections = []
    for partition in sorted(jobs_by_partition):
        rows = []
        for job in jobs_by_partition[partition]:
            danger = " danger" if job["is_general"] else ""
            readonly_note = "只读展示" if job["is_general"] else ""
            rows.append(
                f"""
                <tr class="{danger}">
                  <td>{html.escape(job['id'])}</td>
                  <td>{html.escape(job['partition'])}</td>
                  <td>{html.escape(job['name'])}</td>
                  <td>{html.escape(job['state'])}</td>
                  <td>{html.escape(job['time'])}</td>
                  <td>{html.escape(job['reason'])}</td>
                  <td>{readonly_note}</td>
                </tr>
                """
            )
        job_sections.append(
            f"""
            <section class="panel">
              <div class="panel-head">
                <h2>{html.escape(partition)}</h2>
                <span>{len(rows)} 个作业</span>
              </div>
              <table>
                <thead><tr><th>ID</th><th>分区</th><th>名称</th><th>状态</th><th>时间</th><th>节点/原因</th><th>备注</th></tr></thead>
                <tbody>{''.join(rows)}</tbody>
              </table>
            </section>
            """
        )
    if not job_sections:
        job_sections.append('<section class="panel empty">当前用户没有可见 Slurm 作业。</section>')

    partition_rows = []
    for row in data["partitions"]:
        partition_rows.append(
            f"<tr><td>{html.escape(row['partition'])}</td><td>{html.escape(row['availability'])}</td><td>{html.escape(row['time_limit'])}</td><td>{html.escape(row['nodes'])}</td><td>{html.escape(row['state'])}</td><td>{html.escape(row['gres'])}</td></tr>"
        )
    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in data["warnings"]) or "<li>当前没有 watchboard 警告。</li>"

    total_routes = len(data["routes"])
    active_routes = sum(1 for route in data["routes"] if tmux.get(route["tmux_session"]))
    present_tmux_sessions = sum(1 for item in data.get("tmux_topology", []) if item.get("present"))
    route_jobs = len(data["route_jobs"])
    general_jobs = len(data["general_jobs"])
    tmux_topology_html = render_tmux_topology(data)
    handoff = data.get("handoff", {})

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="{int(refresh_seconds)}">
  <title>SRR 三路线动态看板</title>
  <style>{CSS}</style>
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyeline">CARE SRR Route A+B+C</p>
      <h1>SRR 三路线动态看板</h1>
      <p class="subhead">只读汇总 Route A/B/C 的合同状态、轻量证据、tmux、Slurm 当前态和最近作业。看板不提交、不取消、不上传、不合并，也不产生科学结论。</p>
    </div>
    <div class="top-actions">
      <span class="readonly">只读</span>
      <span class="timestamp">更新于 {html.escape(data['generated_at'])}</span>
    </div>
  </header>

  <main>
    <section class="summary-grid">
      <div class="summary-card"><span>当前轮次</span><strong>{html.escape(handoff.get('round_id', 'unknown'))}</strong><small>由 CURRENT.md 自动读取</small></div>
      <div class="summary-card"><span>路线工作台</span><strong>{active_routes}/{total_routes}</strong><small>Route A/B/C tmux 可见</small></div>
      <div class="summary-card"><span>路线 Slurm 作业</span><strong>{route_jobs}</strong><small>按 job 名称或证据包关联</small></div>
      <div class="summary-card"><span>常驻 tmux</span><strong>{present_tmux_sessions}/4</strong><small>watchboard + 3 条路线</small></div>
    </section>

    <section class="flow">
      <div class="flow-line"></div>
      <div class="flow-step done"><span>1</span><strong>环境搭建</strong><small>分支 / 工作树 / tmux</small></div>
      <div class="flow-step active"><span>2</span><strong>合同与缺口</strong><small>路线合同 / 缺口清单</small></div>
      <div class="flow-step"><span>3</span><strong>实现验收</strong><small>实现关口先于训练</small></div>
      <div class="flow-step"><span>4</span><strong>运行证据</strong><small>Slurm 完成后必须聚合</small></div>
      <div class="flow-step"><span>5</span><strong>独立审查</strong><small>Reviewer 只读审查结果包</small></div>
    </section>

    <section class="routes-grid">
      {''.join(route_cards)}
    </section>

    {tmux_topology_html}

    <section class="two-col">
      <section class="panel warnings">
        <div class="panel-head"><h2>风险与护栏</h2><span>{len(data['warnings'])}</span></div>
        <ul>{warnings}</ul>
        <p class="guardrail">此界面禁用动作：{html.escape(', '.join(data['guardrails']['forbidden_actions']))}。</p>
      </section>
      <section class="panel">
        <div class="panel-head"><h2>分区摘要</h2><span>CARE GPU 分区</span></div>
        <table>
          <thead><tr><th>分区</th><th>可用</th><th>时限</th><th>节点</th><th>状态</th><th>GRES</th></tr></thead>
          <tbody>{''.join(partition_rows) if partition_rows else '<tr><td colspan="6">没有可用分区数据。</td></tr>'}</tbody>
        </table>
      </section>
    </section>

    <section class="jobs">
      <h2>{html.escape(data['user'])} 的 Slurm 当前作业</h2>
      {''.join(job_sections)}
    </section>
  </main>
</body>
</html>
"""


CSS = """
:root {
  --bg: #f7f8fa;
  --surface: #ffffff;
  --panel: #f0f2f5;
  --line: #dfe4ea;
  --text: #16181d;
  --muted: #6b7280;
  --soft: #9aa3af;
  --accent: #1f8fdd;
  --accent-dark: #126cac;
  --active: #e8f4fd;
  --risk: #fff4e8;
  --danger: #fff0f0;
  --revision: #fff1f2;
  --undertrained: #fff7d6;
  --ended: #f1f5f9;
  --ok: #eaf8ef;
  --shadow: 0 18px 45px rgba(17, 24, 39, 0.08);
}
* { box-sizing: border-box; }
html {
  width: 100%;
  overflow-x: hidden;
}
body {
  margin: 0;
  width: 100%;
  overflow-x: hidden;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--text);
  background: var(--bg);
  letter-spacing: 0;
}
.topbar {
  display: flex;
  justify-content: space-between;
  gap: 28px;
  padding: 34px 48px 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
}
.eyeline {
  margin: 0 0 8px;
  color: var(--accent-dark);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
h1, h2, h3, p { margin-top: 0; }
h1 {
  margin-bottom: 8px;
  font-size: 34px;
  line-height: 1.12;
}
.subhead {
  margin: 0;
  max-width: 760px;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}
.top-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  min-width: 230px;
}
.readonly, .timestamp, .state-pill, .badge {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: var(--panel);
  color: var(--muted);
}
.readonly {
  background: #111827;
  color: #fff;
}
main {
  max-width: 1440px;
  margin: 0 auto;
  padding: 26px 48px 48px;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
.summary-card {
  min-width: 0;
  padding: 20px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow);
}
.summary-card span, .metric-row span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}
.summary-card strong {
  display: block;
  margin: 8px 0 4px;
  font-size: 28px;
  line-height: 1;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.summary-card small {
  color: var(--soft);
  overflow-wrap: anywhere;
}
.summary-card.guard {
  background: var(--danger);
}
.round-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 16px 0 10px;
  padding: 12px;
  background: var(--active);
  border: 1px solid #cfe7fb;
  border-radius: 8px;
}
.round-strip span {
  color: var(--accent-dark);
  font-size: 12px;
  font-weight: 800;
}
.round-strip strong {
  color: #0f3554;
  font-size: 15px;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.status-sentence {
  display: grid;
  gap: 8px;
  margin: 0 0 16px;
  padding: 12px;
  background: #fbfcfd;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.status-sentence p {
  margin: 0;
  color: #374151;
  font-size: 14px;
  line-height: 1.45;
}
.flow {
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin: 26px 0;
  padding: 12px 0 8px;
}
.flow-line {
  position: absolute;
  left: 7%;
  right: 7%;
  top: 31px;
  height: 3px;
  background: var(--line);
}
.flow-step {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 7px;
  text-align: center;
}
.flow-step span {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e5e7eb;
  color: var(--muted);
  font-weight: 800;
  border: 3px solid var(--bg);
}
.flow-step.done span, .flow-step.active span {
  background: var(--accent);
  color: #fff;
}
.flow-step strong {
  font-size: 14px;
}
.flow-step small {
  color: var(--muted);
  font-size: 12px;
}
.routes-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.route-card {
  min-width: 0;
  background: var(--surface);
  border: 1px solid var(--line);
  border-top: 5px solid var(--soft);
  border-radius: 8px;
  padding: 20px;
  box-shadow: var(--shadow);
}
.route-card.active { border-top-color: var(--accent); background: #fff; }
.route-card.review { border-top-color: #8b5cf6; background: #f5f3ff; }
.route-card.risk { border-top-color: #f97316; background: var(--risk); }
.route-card.undertrained { border-top-color: #ca8a04; background: var(--undertrained); }
.route-card.revision { border-top-color: #e11d48; background: var(--revision); }
.route-card.ended { border-top-color: #64748b; background: var(--ended); }
.route-card.idle { border-top-color: #94a3b8; background: var(--ended); }
.route-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}
.route-head h2 {
  margin-bottom: 8px;
  font-size: 24px;
}
.purpose {
  color: var(--muted);
  line-height: 1.5;
}
.state-pill {
  color: var(--accent-dark);
  background: var(--active);
  white-space: nowrap;
}
.metric-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 18px 0;
}
.metric-row div {
  min-height: 76px;
  padding: 12px;
  background: var(--panel);
  border-radius: 8px;
}
.metric-row strong {
  display: block;
  margin-top: 7px;
  font-size: 15px;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.route-section {
  padding-top: 16px;
  border-top: 1px solid var(--line);
  overflow-x: auto;
}
.compact-section {
  padding-top: 12px;
}
.route-section h3 {
  margin-bottom: 10px;
  font-size: 15px;
}
.architecture-list {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  line-height: 1.5;
  font-size: 14px;
}
.source, .path {
  margin: 10px 0 0;
  color: var(--soft);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 9px;
}
.badge-row.compact {
  gap: 6px;
  margin-bottom: 0;
}
.badge-row.compact .badge {
  min-height: 24px;
  padding: 4px 8px;
  font-size: 11px;
}
.badge.ok {
  background: var(--ok);
  color: #166534;
}
.badge.warn {
  background: #fff7d6;
  color: #854d0e;
}
.badge.muted {
  background: #eef0f3;
  color: var(--soft);
}
.badge.danger {
  background: #fee2e2;
  color: #991b1b;
}
.evidence-summary {
  color: #374151;
  line-height: 1.5;
  font-size: 14px;
}
.route-jobs-table {
  min-width: 520px;
  font-size: 12px;
}
.two-col {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
  gap: 16px;
  margin-top: 16px;
}
.panel {
  min-width: 0;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px;
  box-shadow: var(--shadow);
  overflow: auto;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.panel-head h2 {
  margin: 0;
  font-size: 18px;
}
.panel-head span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}
.warnings ul {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  line-height: 1.55;
}
.guardrail {
  margin: 14px 0 0;
  color: #991b1b;
  font-size: 13px;
}
table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  font-size: 13px;
}
th, td {
  padding: 10px 8px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
}
td {
  overflow-wrap: anywhere;
}
tr.danger td {
  background: var(--danger);
}
.tmux-topology {
  margin: 24px 0;
}
.tmux-topology table {
  min-width: 980px;
}
.tmux-topology td {
  vertical-align: top;
}
.tmux-topology td span {
  color: var(--muted);
  font-size: 12px;
}
tr.tmux-missing td {
  background: var(--danger);
}
tr.tmux-present td {
  background: #fbfcfd;
}
.jobs {
  margin-top: 16px;
}
.jobs > h2 {
  margin: 0 0 12px;
  font-size: 20px;
}
.empty {
  color: var(--muted);
}
@media (max-width: 1100px) {
  .summary-grid, .routes-grid, .two-col {
    grid-template-columns: 1fr;
  }
  .flow {
    grid-template-columns: 1fr;
  }
  .flow-line {
    display: none;
  }
  .flow-step {
    grid-template-columns: 42px 1fr;
    justify-items: start;
    text-align: left;
  }
  .flow-step small {
    grid-column: 2;
  }
}
@media (max-width: 760px) {
  .topbar {
    flex-direction: column;
    padding: 24px 18px 18px;
  }
  .top-actions {
    align-items: flex-start;
  }
  main {
    padding: 18px;
  }
  h1 {
    font-size: 28px;
  }
  .summary-card strong {
    font-size: 22px;
    line-height: 1.08;
  }
  .subhead {
    max-width: 320px;
  }
  .metric-row {
    grid-template-columns: 1fr;
  }
}
"""


def write_outputs(data: dict[str, Any], output_dir: Path, refresh_seconds: int = 60) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "status.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "index.html").write_text(render_html(data, refresh_seconds=refresh_seconds), encoding="utf-8")


def serve_output(
    root: Path,
    worktree_root: Path,
    user: str,
    output_dir: Path,
    host: str,
    port: int,
    refresh_seconds: int = 60,
) -> None:
    class DynamicWatchboardHandler(SimpleHTTPRequestHandler):
        last_refresh = 0.0

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(output_dir), **kwargs)

        def maybe_refresh(self) -> None:
            now = dt.datetime.now().timestamp()
            if now - self.__class__.last_refresh < max(1, refresh_seconds):
                return
            try:
                data = collect_status(root, worktree_root, user)
                write_outputs(data, output_dir, refresh_seconds=refresh_seconds)
                self.__class__.last_refresh = now
            except Exception as exc:  # pragma: no cover - defensive server logging
                sys.stderr.write(f"watchboard: dynamic refresh failed: {exc}\n")

        def do_GET(self) -> None:  # noqa: N802
            requested = self.path.split("?", 1)[0]
            if requested in {"/", "/index.html", "/status.json"}:
                self.maybe_refresh()
            super().do_GET()

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            sys.stderr.write("watchboard: " + format % args + "\n")

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableTCPServer((host, port), DynamicWatchboardHandler) as httpd:
        print(f"http://{host}:{port}/index.html")
        httpd.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--care-root", default=os.environ.get("CARE_ROOT", "/users/a/e/aereinh/CARE"))
    parser.add_argument("--worktree-root", default=os.environ.get("WORKTREE_ROOT", "/users/a/e/aereinh/CARE_worktrees"))
    parser.add_argument("--user", default=os.environ.get("USER") or os.environ.get("LOGNAME") or "aereinh")
    parser.add_argument("--output-dir", default="results/watchboard")
    parser.add_argument("--serve", action="store_true", help="serve the generated watchboard after writing it")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--refresh-seconds", type=int, default=60, help="HTML meta refresh interval in seconds")
    args = parser.parse_args(argv)

    root = Path(args.care_root).resolve()
    worktree_root = Path(args.worktree_root).resolve()
    output_dir = (root / args.output_dir).resolve()
    if not root.exists():
        print(f"CARE root does not exist: {root}", file=sys.stderr)
        return 2

    data = collect_status(root, worktree_root, args.user)
    write_outputs(data, output_dir, refresh_seconds=args.refresh_seconds)
    print(output_dir / "index.html")
    if args.serve:
        serve_output(root, worktree_root, args.user, output_dir, args.host, args.port, refresh_seconds=args.refresh_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
