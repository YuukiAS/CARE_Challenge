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
ROUTE_IDS_BY_LABEL = {label: route for route, label in ROUTE_LABELS.items()}
SLURM_RACE_READINESS = [
    "htzhulab 是默认 CARE GPU partition。",
    "a100-gpu 是 fallback/race partner。",
    "volta-gpu 只用于 exact-compatible 或 independent-compatible 工作；V100 semantic downscaling forbidden。",
    "formal wrapper must use /users/a/e/aereinh/CARE/envs/env_CARE/bin/python；no bare python。",
    "race requires isolated roots, atomic winner lock, pending-loser cancellation, loser zero credit, retry lineage, all-attempt finalizer coverage。",
]
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
    "ROUTE_A_REVIEW_NEEDS_EVIDENCE",
    "ROUTE_A_REVIEW_NEEDS_MONITOR",
    "ROUTE_A_REVIEW_PASS",
    "ROUTE_B_REVIEW_NEEDS_REVISION",
    "ROUTE_B_REVIEW_NEEDS_EVIDENCE",
    "ROUTE_B_REVIEW_NEEDS_MONITOR",
    "ROUTE_B_REVIEW_PASS",
    "ROUTE_B_SCIENTIFIC_UNDERTRAINED",
    "ROUTE_C_NEEDS_REVISION",
    "ROUTE_C_REVIEW_NEEDS_REVISION",
    "ROUTE_C_REVIEW_NEEDS_EVIDENCE",
    "ROUTE_C_REVIEW_NEEDS_MONITOR",
    "ROUTE_C_REVIEW_PASS",
    "SCIENTIFIC_UNDERTRAINED",
    "NEEDS_REVISION",
    "TERMINAL_NON_READY_PACKET",
)
ROLE_TOKEN_PATTERN = re.compile(
    r"(?<![A-Z0-9_])"
    r"(ROUTE_(?P<route>[ABC])_ROUND(?P<round>[0-9]+)_"
    r"(?P<kind>PLANNING_READY_FOR_CONTROLLER|PLANNING_NEEDS_REVISION|TERMINAL_PACKET_READY_FOR_REVIEW|"
    r"REVIEW_EVIDENCE_COMPLETE|REVIEW_ADEQUATE_NEGATIVE|REVIEW_NEEDS_REVISION|REVIEW_NEEDS_EVIDENCE|"
    r"REVIEW_NEEDS_MONITOR|REVIEW_UNDERTRAINED|REVIEW_EXTERNAL_RESOURCE_BLOCKER))"
    r"(?![A-Z0-9_])"
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
REVIEW_REVISION_KEYWORDS = (
    "ROUTE_A_REVIEW_NEEDS_REVISION",
    "ROUTE_B_REVIEW_NEEDS_REVISION",
    "ROUTE_C_REVIEW_NEEDS_REVISION",
)
REVIEW_EVIDENCE_KEYWORDS = (
    "ROUTE_A_REVIEW_NEEDS_EVIDENCE",
    "ROUTE_B_REVIEW_NEEDS_EVIDENCE",
    "ROUTE_C_REVIEW_NEEDS_EVIDENCE",
)
REVIEW_MONITOR_KEYWORDS = (
    "ROUTE_A_REVIEW_NEEDS_MONITOR",
    "ROUTE_B_REVIEW_NEEDS_MONITOR",
    "ROUTE_C_REVIEW_NEEDS_MONITOR",
)
REVIEW_PASS_KEYWORDS = (
    "ROUTE_A_REVIEW_PASS",
    "ROUTE_B_REVIEW_PASS",
    "ROUTE_C_REVIEW_PASS",
)
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
    "route_B": ("route_B", "RouteB", "route-b", "care_route_B", "Route B", "RB3"),
    "route_C": ("route_C", "RouteC", "route-c", "care_route_C", "Route C", "RCR3"),
}
PACKET_LABELS_ZH = {
    "controller_context": "Controller context",
    "finalizer_state": "Finalizer state",
    "completion_check": "完成检查",
    "review_request": "审查请求",
    "commands_run": "命令记录",
    "controller_ledger": "Controller ledger",
    "result": "结果包",
    "review": "独立审查",
    "controller_report": "Controller 报告",
    "manifest": "清单",
}
CARE_PARTITION_ORDER = ("htzhulab", "a100-gpu", "volta-gpu")
PACKET_SCAN_FILES = {
    "controller_context": "controller_context.json",
    "finalizer_state": "finalizer_state.json",
    "completion_check": "completion_check.md",
    "review_request": "review_request.md",
    "commands_run": "commands_run.md",
    "controller_ledger": "controller_ledger.csv",
    "result": "result.md",
    "review": "review.md",
    "controller_report": "controller_report.md",
    "manifest": "MANIFEST.md",
}
AUTHORITY_KEYS = (
    "controller_authorized_now",
    "validation_upload_authorized",
    "route_promotion_authorized",
    "m11_authorized",
    "cross_route_merge_authorized",
    "hosted_metric_claim_authorized",
    "final_scientific_decision_authorized",
)
V100_INCOMPATIBLE_PATTERNS = (
    "sm_70",
    "no-kernel-image",
    "no kernel image",
    "tesla_v100",
    "Tesla V100",
    "V100 incompatible",
    "compute capability 7.0",
    "unsupported on V100",
)
MUTATING_COMMANDS = {"sbatch", "srun", "scancel", "upload"}
MUTATING_GIT_SUBCOMMANDS = {"merge", "push", "pull", "reset", "checkout", "commit", "add", "rebase"}
MUTATING_TMUX_SUBCOMMANDS = {"send-keys", "new-session", "kill-session", "kill-window", "kill-pane", "rename-window"}
TMUX_SESSION_SPECS = (
    {
        "session": "care_watchboard",
        "label_zh": "Ops layer",
        "purpose_zh": "Watchboard server、cloudflared tunnel 与 controller goal email notifier",
        "expected_windows": ("Watchboard", "watchboard-tunnel", "Notify"),
        "window_aliases": {
            "Watchboard": ("python", "python3", "./envs/env_CARE/bin/python", "/users/a/e/aereinh/CARE/envs/env_CARE/bin/python"),
            "watchboard-tunnel": ("Tunnel", "cloudflared"),
        },
    },
    {
        "session": "care_route_A",
        "label_zh": "Route A 常驻工作台",
        "purpose_zh": "controller、continue、executor、reviewer 分窗隔离",
        "route": "route_A",
        "reviewer_window": "RouteA-Reviewer",
        "expected_windows": ("RouteA-Controller", "RouteA-Continue", "RouteA-Exec", "RouteA-Reviewer"),
    },
    {
        "session": "care_route_B",
        "label_zh": "Route B 常驻工作台",
        "purpose_zh": "controller、continue、executor、reviewer 分窗隔离",
        "route": "route_B",
        "reviewer_window": "RouteB-Reviewer",
        "expected_windows": ("RouteB-Controller", "RouteB-Continue", "RouteB-Exec", "RouteB-Reviewer"),
    },
    {
        "session": "care_route_C",
        "label_zh": "Route C 常驻工作台",
        "purpose_zh": "controller、continue、executor、reviewer 分窗隔离",
        "route": "route_C",
        "reviewer_window": "RouteC-Reviewer",
        "expected_windows": ("RouteC-Controller", "RouteC-Continue", "RouteC-Exec", "RouteC-Reviewer"),
    },
)
ROUTE_TMUX_PLAN = {spec["route"]: spec for spec in TMUX_SESSION_SPECS if spec.get("route")}
FORBIDDEN_ACTIONS = (
    "scancel",
    "sbatch",
    "srun",
    "git merge",
    "git push",
    "upload",
    "route promotion",
    "M11",
    "hosted metric claim",
    "final scientific decision",
)


def run_cmd(args: list[str], cwd: Path, timeout: int = 8) -> dict[str, Any]:
    if args and args[0] in MUTATING_COMMANDS:
        return {"ok": False, "stdout": "", "stderr": f"forbidden mutating command: {args[0]}", "code": 126}
    if len(args) > 1 and args[0] == "git" and args[1] in MUTATING_GIT_SUBCOMMANDS:
        return {"ok": False, "stdout": "", "stderr": f"forbidden mutating git command: git {args[1]}", "code": 126}
    if len(args) > 1 and args[0] == "tmux" and args[1] in MUTATING_TMUX_SUBCOMMANDS:
        return {"ok": False, "stdout": "", "stderr": f"forbidden mutating tmux command: tmux {args[1]}", "code": 126}
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
    for match in ROLE_TOKEN_PATTERN.finditer(text):
        token = match.group(0)
        if token not in found:
            found.append(token)
    return found


def extract_role_tokens(text: str, *, source_role: str = "", source_path: str = "", mtime: float = 0) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for match in ROLE_TOKEN_PATTERN.finditer(text):
        route = f"route_{match.group('route')}"
        kind = match.group("kind")
        if kind.startswith("PLANNING_"):
            role = "planning_critic"
        elif kind.startswith("REVIEW_"):
            role = "reviewer"
        else:
            role = "controller_terminal"
        tokens.append(
            {
                "token": match.group(1),
                "route": route,
                "round": int(match.group("round")),
                "kind": kind,
                "role": role,
                "source_role": source_role,
                "source_path": source_path,
                "mtime": mtime,
            }
        )
    return tokens


def extract_slurm_job_ids(text: str) -> list[str]:
    """Extract likely Slurm job IDs from lightweight packet text."""
    ids: set[str] = set()
    direct_patterns = [
        r"(?i)\b(?:job[_ -]?id|jobid|slurm[_ -]?job|submitted\s+job|sbatch\s+submitted)\D{0,30}(\d{5,}(?:[_\.]\d+)?)",
        r"->\s*`?(\d{5,}(?:[_\.]\d+)?)`?",
        r"\b(\d{5,}(?:_\d+)?)\|[^\n|]*(?:COMPLETED|FAILED|CANCELLED|PENDING|RUNNING|TIMEOUT)",
    ]
    for pattern in direct_patterns:
        for match in re.finditer(pattern, text):
            ids.add(match.group(1))
    return sorted(ids, key=job_sort_key)


def read_json_file(path: Path) -> tuple[Any, str]:
    if not path.exists() or not path.is_file():
        return None, ""
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace")), ""
    except json.JSONDecodeError as exc:
        return None, f"{path}: JSON parse failed: {exc}"


def extract_job_ids_from_json(value: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ("job_id", "jobid", "slurm_job", "array_job", "required_job")):
                if isinstance(item, (str, int)) and is_slurm_job_id(str(item)):
                    ids.add(str(item))
                elif isinstance(item, list):
                    ids.update(str(entry) for entry in item if isinstance(entry, (str, int)) and is_slurm_job_id(str(entry)))
            ids.update(extract_job_ids_from_json(item))
    elif isinstance(value, list):
        for item in value:
            ids.update(extract_job_ids_from_json(item))
    return ids


def extract_partition_from_text(text: str) -> str:
    for pattern in (r"(?im)^partition\s*[:=|]\s*([^|\n]+)", r"(?i)--partition[=\s]+([^\s]+)", r"(?i)\bpartition\s+([a-z0-9_-]+)"):
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def parse_pipe_ledger(text: str, source_packet: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = [line.strip() for line in text.splitlines() if "|" in line and line.strip()]
    if not lines:
        return rows
    header = [cell.strip().lower().replace(" ", "_") for cell in lines[0].strip("|").split("|")]
    if not any("job" in cell for cell in header):
        return rows
    for line in lines[1:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        values = dict(zip(header, cells, strict=False))
        job_id = values.get("job_id") or values.get("slurm_job_id") or values.get("jobid") or values.get("job")
        if not job_id or not is_slurm_job_id(job_id):
            continue
        rows.append(
            {
                "job_id": job_id,
                "partition": values.get("partition", ""),
                "state": values.get("state", values.get("slurm_state", "")),
                "source_packet": source_packet,
                "source_confidence": "packet_ledger",
                "credit": values.get("credit", ""),
                "compatibility_evidence": values.get("compatibility", values.get("compatibility_evidence", "")),
            }
        )
    return rows


def collect_packet_attempts(packet_texts: dict[str, str], packet_jsons: dict[str, Any]) -> list[dict[str, Any]]:
    attempts: dict[tuple[str, str], dict[str, Any]] = {}
    for source, data in packet_jsons.items():
        if data is None:
            continue
        for job_id in extract_job_ids_from_json(data):
            attempts[(normalize_job_id(job_id), source)] = {
                "job_id": job_id,
                "source_packet": source,
                "source_confidence": "structured_packet",
            }
    for source, text in packet_texts.items():
        if not text:
            continue
        for row in parse_pipe_ledger(text, source):
            attempts[(normalize_job_id(row["job_id"]), source)] = row
        partition = extract_partition_from_text(text)
        for job_id in extract_slurm_job_ids(text):
            if not is_slurm_job_id(job_id):
                continue
            attempts.setdefault(
                (normalize_job_id(job_id), source),
                {
                    "job_id": job_id,
                    "partition": partition,
                    "source_packet": source,
                    "source_confidence": "packet_text",
                },
            )
    return sorted(attempts.values(), key=lambda item: job_sort_key(str(item.get("job_id", ""))))


def detect_v100_compatibility(packet_text: str) -> dict[str, Any]:
    matches = [pattern for pattern in V100_INCOMPATIBLE_PATTERNS if pattern.lower() in packet_text.lower()]
    if matches:
        return {"volta_usable": False, "evidence": matches, "source": "packet_or_ledger"}
    if "volta-gpu" in packet_text or "tesla_v100" in packet_text.lower():
        return {"volta_usable": True, "evidence": ["packet mentions volta-gpu without incompatibility marker"], "source": "packet_or_ledger"}
    return {"volta_usable": None, "evidence": [], "source": "not_recorded"}


def split_array_job_id(job_id: str) -> tuple[str, str]:
    match = re.match(r"^(\d+)(?:[_\.](\d+))?", job_id or "")
    if not match:
        return "", ""
    return match.group(1), match.group(2) or ""


def slurm_attempt_from_job(job: dict[str, str], source_packet: str, source_confidence: str) -> dict[str, Any]:
    root, task = split_array_job_id(job.get("id", ""))
    return {
        "job_id": job.get("id", ""),
        "array_root": root,
        "array_task": task,
        "partition": job.get("partition", ""),
        "state": job.get("state", ""),
        "reason": job.get("reason", job.get("exit_code", "")),
        "elapsed": job.get("time", job.get("elapsed", "")),
        "start_estimate": job.get("start", ""),
        "dependency": job.get("dependency", ""),
        "source_packet": source_packet,
        "source_confidence": source_confidence,
        "credit": job.get("credit", ""),
        "compatibility_evidence": job.get("compatibility_evidence", ""),
    }


def job_match_confidence(job: dict[str, str], route: dict[str, Any]) -> str:
    job_id = normalize_job_id(job.get("id", ""))
    route_ids = {normalize_job_id(value) for value in route.get("slurm_job_ids", [])}
    if job_id and job_id in route_ids:
        return "packet_job_id"
    if route_name_matches(route["id"], job.get("name", "")):
        return "fuzzy_name"
    return ""


def is_slurm_job_id(value: str) -> bool:
    return bool(re.match(r"^\d{5,}(?:[_\.].+)?$", str(value or "")))


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
    return bool(job_match_confidence(job, route))


def evidence_summary_zh(packet_files: dict[str, Path], latest_packet: Path | None) -> str:
    existing = [PACKET_LABELS_ZH[name] for name, path in packet_files.items() if path.exists()]
    if not existing:
        return "尚未发现 route 结果包；当前只能展示 route README 和运行环境。"
    latest = latest_packet.name if latest_packet else "未知文件"
    return f"已发现 {len(existing)} 类轻量证据：{'、'.join(existing)}；最新证据为 {latest}。"


def relative_repo_path(root: Path, raw: str) -> dict[str, Any]:
    value = raw.strip().strip("`")
    if not value or value.startswith("NO_CURRENT_"):
        return {"path": value, "exists": False, "active": False, "absolute_path": ""}
    candidate = Path(value)
    absolute = candidate if candidate.is_absolute() else root / candidate
    return {
        "path": value,
        "exists": absolute.exists(),
        "active": True,
        "absolute_path": str(absolute),
    }


def marker_offset(text: str, marker: str) -> int:
    start = text.find(marker)
    if start >= 0:
        return start
    plain_marker = marker.strip().lstrip("#").strip().rstrip(":").lower()
    for match in re.finditer(r"(?im)^#{0,6}\s*([^\n:]+):?\s*$", text):
        heading = match.group(1).strip().rstrip(":").lower()
        if heading == plain_marker:
            return match.start()
    lowered = text.lower()
    return lowered.find(marker.lower())


def first_fenced_path_after(text: str, marker: str) -> str:
    start = marker_offset(text, marker)
    if start < 0:
        return ""
    match = re.search(r"```(?:text)?\s*([^`\n][^`]*)```", text[start:], re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip().splitlines()[0].strip()


def fenced_block_after(text: str, marker: str) -> str:
    start = marker_offset(text, marker)
    if start < 0:
        return ""
    match = re.search(r"```(?:text)?\s*(.*?)```", text[start:], re.DOTALL)
    return match.group(1).strip() if match else ""


def fenced_block_after_any(text: str, markers: tuple[str, ...]) -> str:
    for marker in markers:
        block = fenced_block_after(text, marker)
        if block:
            return block
    return ""


def path_after_label(text: str, label: str) -> str:
    match = re.search(rf"(?m)^{re.escape(label)}\s*\n([^\n]+)", text)
    return match.group(1).strip() if match else ""


def parse_bool_text(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def parse_key_values(block: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip().strip("- ")
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("`")
    return values


def parse_portfolio_state(text: str) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    block = fenced_block_after_any(text, ("## Portfolio state", "Portfolio state:"))
    values = parse_key_values(block)
    main_only_development = bool(
        re.search(r"(?m)^active_development_branch:\s*main\b", text)
        and re.search(r"(?m)^route_worktree_development_authorized:\s*false\b", text, re.IGNORECASE)
    )
    routes: dict[str, str] = {}
    active_routes: list[str] = []
    deferred_routes: list[str] = []
    active_controller_routes: list[str] = []
    portfolio_context_routes: list[str] = []
    for label, route in ROUTE_IDS_BY_LABEL.items():
        state = values.get(label, "UNKNOWN")
        upper_state = state.upper()
        routes[route] = state
        is_deferred = (
            upper_state.startswith("DEFERRED")
            or upper_state.startswith("DORMANT")
            or upper_state.startswith("INACTIVE")
            or "FALLBACK_NOT_ACTIVE" in upper_state
            or "STOP_AND_HOLD" in upper_state
            or "HISTORICAL" in upper_state
        )
        if is_deferred:
            deferred_routes.append(route)
        elif state != "UNKNOWN":
            active_routes.append(route)
            if upper_state.startswith("ACTIVE"):
                active_controller_routes.append(route)
            else:
                portfolio_context_routes.append(route)
    raw_authorizations = values.get("current_controller_authorizations")
    if raw_authorizations is None:
        match = re.search(r"(?m)^controller_authorized_now:\s*(\d+)", text)
        raw_authorizations = match.group(1) if match else "0"
    try:
        current_controller_authorizations = int(str(raw_authorizations).strip())
    except ValueError:
        current_controller_authorizations = 0
        warnings.append("CURRENT.md current_controller_authorizations/controller_authorized_now 不是整数。")
    if not block:
        warnings.append("CURRENT.md Portfolio state 缺失或不可解析。")
    if not active_routes and block and not main_only_development:
        warnings.append("CURRENT.md 未解析到 current/active route。")
    if not deferred_routes and block:
        warnings.append("CURRENT.md 未解析到 deferred_routes。")
    return (
        {
            "routes": routes,
            "main_only_development": main_only_development,
            "active_routes": active_routes,
            "current_routes": active_routes,
            "active_controller_routes": active_controller_routes,
            "portfolio_context_routes": portfolio_context_routes,
            "deferred_routes": deferred_routes,
            "active_route_labels": [ROUTE_LABELS[route] for route in active_routes],
            "current_route_labels": [ROUTE_LABELS[route] for route in active_routes],
            "active_controller_route_labels": [ROUTE_LABELS[route] for route in active_controller_routes],
            "portfolio_context_route_labels": [ROUTE_LABELS[route] for route in portfolio_context_routes],
            "deferred_route_labels": [ROUTE_LABELS[route] for route in deferred_routes],
            "current_controller_authorizations": current_controller_authorizations,
        },
        warnings,
    )


def parse_authority_boundary(text: str) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    block = fenced_block_after_any(text, ("## Authority boundary", "## Authority Boundary", "Authority Boundary"))
    values = parse_key_values(block)
    authority: dict[str, Any] = {}
    for key, value in values.items():
        parsed_bool = parse_bool_text(value)
        if parsed_bool is not None:
            authority[key] = parsed_bool
        else:
            try:
                authority[key] = int(value)
            except ValueError:
                authority[key] = value
    top_controller = re.search(r"(?m)^controller_authorized_now:\s*(\d+)", text)
    if top_controller and "controller_authorized_now" not in authority:
        authority["controller_authorized_now"] = int(top_controller.group(1))
    for key in AUTHORITY_KEYS:
        if key not in authority:
            warnings.append(f"CURRENT.md Authority Boundary 缺少 {key}。")
    return authority, warnings


def parse_exact_evidence_bindings(text: str) -> dict[str, str]:
    block = fenced_block_after_any(text, ("## Exact remote evidence bindings", "Exact remote evidence bindings"))
    return parse_key_values(block)


def parse_route_binding(text: str, route: str) -> dict[str, str]:
    label = ROUTE_LABELS[route]
    match = re.search(rf"(?ms)^### {re.escape(label)}[^\n]*\n(.*?)(?=^### |^## |\Z)", text)
    section = match.group(1) if match else ""
    block = fenced_block_after(section, "```text") if "```" in section else section
    values = parse_key_values(block)
    exact = parse_exact_evidence_bindings(text)

    def first_value(*keys: str) -> str:
        for key in keys:
            if values.get(key):
                return values[key]
            if exact.get(key):
                return exact[key]
        return ""

    evidence_key = f"{label} evidence commit"
    reviewer_key = f"{label} reviewer commit"
    reviewed_key = f"{label} reviewed controller repair"
    return {
        "required_head": first_value("route head", "required head", "required route head", evidence_key),
        "evidence_head": first_value(evidence_key, "route head", "required head", "required route head"),
        "reviewer_commit": first_value("review commit", reviewer_key),
        "reviewed_controller_commit": first_value("reviewed controller repair", reviewed_key),
        "review_token": first_value("review token"),
        "portfolio_status": first_value("portfolio status"),
        "contract_blob": first_value("contract blob"),
        "executor_plan_blob": first_value("executor-plan blob", "executor plan blob"),
        "critic_request_blob": first_value("critic-request blob", "critic request blob"),
        "planner_audit_blob": first_value("planner-audit blob", "planner audit blob"),
        "critic_handoff_blob": first_value("Critic-handoff blob", "critic-handoff blob", "critic handoff blob"),
        "critic_handoff_path": first_value("critic handoff", "critic handoff path"),
        "coordinator_receipt_path": first_value("coordinator receipt", "coordinator receipt path"),
        "critic_review_output_path": first_value("critic output", "critic review output path", "critic-review output path", "critic review path", "critic-review path"),
        "revision_source_critic_token": first_value("revision source critic token"),
        "critic_review_blob": first_value("critic review blob", "critic-review blob"),
        "evidence_mapping_blob": first_value("evidence-mapping blob"),
        "evidence_mapping_required_row_count": first_value("evidence-mapping required row count"),
    }


def parse_terminal_reviewer_targets(text: str) -> dict[str, dict[str, str]]:
    block = fenced_block_after(text, "## Controller Terminal Packet / Reviewer Targets")
    values = {key.lower(): value for key, value in parse_key_values(block).items()}
    targets: dict[str, dict[str, str]] = {}
    for route in ROUTES:
        prefix = route.lower()

        def value_for(*suffixes: str) -> str:
            for suffix in suffixes:
                for candidate in (f"{prefix} {suffix}", f"{prefix}_{suffix}"):
                    if values.get(candidate):
                        return values[candidate]
            return ""

        target = {
            "reviewer_target_head": value_for("reviewer target head", "reviewer_target_head", "target head"),
            "terminal_token": value_for("terminal token", "terminal_token"),
            "reviewer_output_path": value_for("reviewer output path", "reviewer_output_path"),
            "route_promotion_decision": value_for("route promotion decision", "route_promotion_decision"),
            "route_negative_decision": value_for("route negative decision", "route_negative_decision"),
            "scientific_resolution_status": value_for("scientific resolution status", "scientific_resolution_status"),
            "validation_upload": value_for("validation upload", "validation_upload"),
            "hosted_metric_claim": value_for("hosted metric claim", "hosted_metric_claim"),
            "m11_started": value_for("m11 started", "m11_started"),
        }
        if any(target.values()):
            targets[route] = target
    return targets


def parse_allowed_tokens(text: str, route: str) -> list[str]:
    label = ROUTE_LABELS[route]
    letter = route_letter(route)
    patterns = (
        rf"Allowed {re.escape(label)}(?: Round[0-9]+)? planning (?:tokens|decisions):",
        rf"Allowed {re.escape(route)}(?: Round[0-9]+)? planning (?:tokens|decisions):",
        rf"{re.escape(label)} allowed planning tokens:",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        block = fenced_block_after(text[match.start():], match.group(0))
        tokens = [line.strip() for line in block.splitlines() if line.strip()]
        if tokens:
            return tokens
    return [token["token"] for token in extract_role_tokens(text) if token["route"] == route and token["role"] == "planning_critic"]


def parse_round_checkpoints(text: str) -> list[dict[str, Any]]:
    match = re.search(r"(?ms)^## ((?:Round[0-9]+ )?Decision Checkpoints)\s*(.*?)(?=^## |\Z)", text)
    if not match:
        return []
    heading = match.group(1)
    checkpoints: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in match.group(2).splitlines():
        line = raw.strip()
        date_match = re.match(r"(20\d{2}-\d{2}-\d{2}):", line)
        if date_match:
            current = {"date": date_match.group(1), "items": [], "source_heading": heading}
            checkpoints.append(current)
            remainder = line.split(":", 1)[1].strip()
            if remainder:
                current["items"].append(remainder)
        elif current and line.startswith("-"):
            current["items"].append(line.lstrip("- ").strip())
    return checkpoints


def discover_critic_review_output(root: Path, route: str, round_id: str, configured: dict[str, Any]) -> dict[str, Any]:
    if configured.get("exists"):
        return configured
    round_suffix = round_id if round_id and round_id != "unknown" else "round[0-9]+"
    candidates: list[Path] = []
    if round_suffix.startswith("round") and "[" not in round_suffix:
        candidates.extend(
            [
                root / "prompts" / "routes" / f"{route}_{round_suffix}_critic_review.md",
                root / "prompts" / "routes" / f"{route}_{round_suffix}_critic_rereview.md",
            ]
        )
    candidates.extend(sorted((root / "prompts" / "routes").glob(f"{route}_round*_critic_review.md")))
    candidates.extend(sorted((root / "prompts" / "routes").glob(f"{route}_round*_critic_rereview.md")))
    existing = [path for path in candidates if path.is_file()]
    if not existing:
        return configured
    latest = max(existing, key=lambda path: path.stat().st_mtime)
    try:
        rel = str(latest.relative_to(root))
    except ValueError:
        rel = str(latest)
    return relative_repo_path(root, rel)


def detect_critic_decision(root: Path, route: str, round_id: str, review_path: dict[str, Any], allowed_tokens: list[str]) -> dict[str, Any]:
    resolved_review_path = discover_critic_review_output(root, route, round_id, review_path)
    text = read_text(Path(resolved_review_path.get("absolute_path", ""))) if resolved_review_path.get("absolute_path") else ""
    found = [token for token in allowed_tokens if re.search(rf"(?<![A-Z0-9_]){re.escape(token)}(?![A-Z0-9_])", text)]
    if not found:
        found = [token["token"] for token in extract_role_tokens(text) if token["route"] == route and token["role"] == "planning_critic"]
    ready = [token for token in found if token.endswith("READY_FOR_CONTROLLER")]
    revision = [token for token in found if token.endswith("NEEDS_REVISION")]
    return {
        "review_output": resolved_review_path,
        "found_tokens": found,
        "ready_token": ready[0] if ready else "",
        "revision_token": revision[0] if revision else "",
        "state_zh": "ready token present" if ready else "needs revision token present" if revision else "pending critic token",
    }


def build_critic_readiness(
    root: Path,
    critics: dict[str, dict[str, Any]],
    allowed_tokens: dict[str, list[str]],
    review_outputs: dict[str, dict[str, Any]] | None = None,
    round_id: str = "unknown",
) -> dict[str, Any]:
    readiness: dict[str, Any] = {}
    review_outputs = review_outputs or {}
    for route in ROUTES:
        review_path = review_outputs.get(route) or relative_repo_path(root, "NO_CURRENT_CRITIC_REVIEW")
        tokens = allowed_tokens.get(route, [])
        decision = detect_critic_decision(root, route, round_id, review_path, tokens)
        if not review_path.get("active"):
            decision["state_zh"] = "critic review output unknown"
        elif not tokens:
            decision["state_zh"] = "allowed token unknown"
        readiness[route] = {
            "critic_handoff": critics.get(route, relative_repo_path(root, "NO_CURRENT_CRITIC_HANDOFF")),
            "allowed_tokens": tokens,
            **decision,
        }
    return readiness


def current_role_entry(text: str, route: str, role: str) -> str:
    label = ROUTE_LABELS[route]
    block = fenced_block_after_any(text, ("## Current role entries", "## Critic Entries", "Critic Entries"))
    patterns = (
        rf"(?im)^{re.escape(label)}\s+{re.escape(role)}:\s*([^\n]+)",
        rf"(?im)^{re.escape(route)}\s+{re.escape(role)}\s+current\s+prompt:\s*\n([^\n]+)",
        rf"(?im)^{re.escape(route)}\s+{re.escape(role)}:\s*([^\n]+)",
    )
    haystacks = (block, text)
    for haystack in haystacks:
        for pattern in patterns:
            match = re.search(pattern, haystack)
            if match:
                return match.group(1).strip()
    return f"NO_CURRENT_{role.upper()}_HANDOFF"


def route_token_priority(token: dict[str, Any]) -> tuple[int, int, float, str]:
    source_role = token.get("source_role", "")
    if source_role == "review":
        source_rank = 4
    elif source_role == "critic_review":
        source_rank = 3
    elif source_role in {"result", "controller_report", "completion_check", "review_request"}:
        source_rank = 2
    else:
        source_rank = 1
    role = token.get("role", "")
    role_rank = {"reviewer": 4, "planning_critic": 3, "controller_terminal": 2}.get(role, 1)
    return (role_rank + source_rank, int(token.get("round", 0)), float(token.get("mtime", 0)), str(token.get("token", "")))


def latest_role_token(tokens: list[dict[str, Any]], route: str, roles: set[str] | None = None) -> dict[str, Any]:
    candidates = [token for token in tokens if token.get("route") == route and (roles is None or token.get("role") in roles)]
    if not candidates:
        return {}
    return max(candidates, key=route_token_priority)


def parse_critic_blockers(path_info: dict[str, Any]) -> list[str]:
    path = Path(path_info.get("absolute_path", "")) if path_info.get("absolute_path") else None
    text = read_text(path) if path else ""
    blockers: list[str] = []
    capture = False
    for raw in text.splitlines():
        line = raw.strip()
        lowered = line.lower()
        if lowered.startswith("hard_blockers") or lowered.startswith("blockers") or lowered.startswith("critical blockers"):
            capture = True
            continue
        if capture and line.startswith("#"):
            break
        if capture and line.startswith("-"):
            blocker = line.lstrip("- ").strip().strip("`")
            if blocker:
                blockers.append(blocker)
        if len(blockers) >= 8:
            break
    if not blockers:
        for match in re.finditer(r"(?m)^-\s*`?([A-Z0-9_]{8,})`?", text):
            value = match.group(1)
            if value not in blockers and any(part in value for part in ("CURRENT", "B10", "VALIDATOR", "EXECUTABLE", "RECEIPT")):
                blockers.append(value)
            if len(blockers) >= 8:
                break
    return blockers


def stale_warning_for_route(route: dict[str, Any]) -> str:
    required_head = route.get("required_head", "")
    origin_sha = route.get("origin_sha", "")
    reviewer_commit = route.get("reviewer_commit", "")
    if required_head and origin_sha and required_head != origin_sha and reviewer_commit and origin_sha == reviewer_commit:
        return "handoff stale for controller authorization, but reviewer result current"
    if required_head and origin_sha and required_head != origin_sha:
        return "CURRENT.md stale for current route head; controller remains blocked"
    return ""


def parse_current_handoff(text: str, root: Path) -> dict[str, Any]:
    parse_warnings: list[str] = []
    round_id = re.search(r"(?m)^round_id:\s*(\S+)", text)
    round_date = re.search(r"(?m)^date:\s*(\S+)", text)
    planner_prompt = path_after_label(text, "current Planner handoff:") or first_fenced_path_after(text, "The single portfolio GPT planner should read:")
    portfolio, portfolio_warnings = parse_portfolio_state(text)
    authority, authority_warnings = parse_authority_boundary(text)
    parse_warnings.extend(portfolio_warnings)
    parse_warnings.extend(authority_warnings)

    critics: dict[str, dict[str, Any]] = {}
    allowed_tokens: dict[str, list[str]] = {}
    route_bindings: dict[str, dict[str, str]] = {}
    critic_review_outputs: dict[str, dict[str, Any]] = {}
    terminal_reviewer_targets = parse_terminal_reviewer_targets(text)
    round_value = round_id.group(1) if round_id else "unknown"
    round_checkpoints = parse_round_checkpoints(text)
    for route in ROUTES:
        raw = current_role_entry(text, route, "critic")
        route_bindings[route] = parse_route_binding(text, route)
        if raw.startswith("NO_CURRENT_") and route_bindings[route].get("critic_handoff_path"):
            raw = route_bindings[route]["critic_handoff_path"]
        critics[route] = relative_repo_path(root, raw)
        allowed_tokens[route] = parse_allowed_tokens(text, route)
        critic_review_outputs[route] = relative_repo_path(root, route_bindings[route].get("critic_review_output_path", "NO_CURRENT_CRITIC_REVIEW"))

    if round_value == "unknown":
        parse_warnings.append("CURRENT.md 缺少 round_id；portfolio_round.round_id=unknown。")
    if not portfolio.get("active_routes") and not portfolio.get("main_only_development"):
        parse_warnings.append("CURRENT.md current route 为空；看板不能回退为三路线同权。")
    for route in portfolio.get("active_routes", []):
        binding = route_bindings.get(route, {})
        state = str(portfolio.get("routes", {}).get(route, "")).upper()
        if state.startswith("PLANNING_REVISION") or state.startswith("ACTIVE"):
            required_keys = ("required_head", "critic_review_output_path")
            for key in required_keys:
                if key == "critic_review_output_path" and terminal_reviewer_targets.get(route):
                    continue
                if not binding.get(key):
                    parse_warnings.append(f"{ROUTE_LABELS[route]} CURRENT binding 缺少 {key}；显示 unknown/blocked。")
            if state.startswith("ACTIVE") and not allowed_tokens.get(route):
                parse_warnings.append(f"{ROUTE_LABELS[route]} CURRENT 缺少 allowed planning tokens；Critic gate blocked/unknown。")
        elif state == "EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION":
            if not (binding.get("reviewer_commit") and binding.get("reviewed_controller_commit") and binding.get("review_token")):
                parse_warnings.append(f"{ROUTE_LABELS[route]} evidence-complete binding 缺少 reviewer commit/review token 字段。")
    critic_readiness = build_critic_readiness(root, critics, allowed_tokens, critic_review_outputs, round_id=round_value)
    exact_bindings = parse_exact_evidence_bindings(text)
    portfolio_round = {
        "round_id": round_value,
        "date": round_date.group(1) if round_date else "",
        "source": "prompts/routes/handoffs/CURRENT.md",
        "active_routes": portfolio.get("active_routes", []),
        "current_routes": portfolio.get("current_routes", []),
        "active_controller_routes": portfolio.get("active_controller_routes", []),
        "portfolio_context_routes": portfolio.get("portfolio_context_routes", []),
        "deferred_routes": portfolio.get("deferred_routes", []),
        "controller_authority": authority,
        "route_bindings": route_bindings,
        "exact_remote_evidence_bindings": exact_bindings,
        "round_checkpoints": round_checkpoints,
        "terminal_reviewer_targets": terminal_reviewer_targets,
    }
    return {
        "round_id": round_value,
        "date": round_date.group(1) if round_date else "",
        "planner_prompt": relative_repo_path(root, planner_prompt),
        "critics": critics,
        "portfolio": portfolio,
        "portfolio_round": portfolio_round,
        "authority": authority,
        "critic_readiness": critic_readiness,
        "route_bindings": route_bindings,
        "critic_review_outputs": critic_review_outputs,
        "round_checkpoints": round_checkpoints,
        "terminal_reviewer_targets": terminal_reviewer_targets,
        "parse_warnings": parse_warnings,
    }

def empty_portfolio_state() -> dict[str, Any]:
    return {
        "routes": {route: "UNKNOWN" for route in ROUTES},
        "main_only_development": False,
        "active_routes": [],
        "current_routes": [],
        "active_controller_routes": [],
        "portfolio_context_routes": [],
        "deferred_routes": [],
        "active_route_labels": [],
        "current_route_labels": [],
        "active_controller_route_labels": [],
        "portfolio_context_route_labels": [],
        "deferred_route_labels": [],
        "current_controller_authorizations": 0,
    }


def collect_handoff_status(root: Path) -> dict[str, Any]:
    current_path = root / "prompts" / "routes" / "handoffs" / "CURRENT.md"
    text = read_text(current_path)
    if not text:
        critics = {route: relative_repo_path(root, "NO_CURRENT_CRITIC_HANDOFF") for route in ROUTES}
        empty_authority = {"controller_authorized_now": 0}
        portfolio = empty_portfolio_state()
        portfolio_round = {
            "round_id": "unknown",
            "date": "",
            "source": "prompts/routes/handoffs/CURRENT.md",
            "active_routes": [],
            "current_routes": [],
            "active_controller_routes": [],
            "portfolio_context_routes": [],
            "deferred_routes": [],
            "controller_authority": empty_authority,
            "route_bindings": {route: {} for route in ROUTES},
            "round_checkpoints": [],
            "terminal_reviewer_targets": {},
        }
        return {
            "current_path": str(current_path),
            "current_exists": False,
            "round_id": "unknown",
            "date": "",
            "planner_prompt": {"path": "", "exists": False, "active": False, "absolute_path": ""},
            "critics": critics,
            "portfolio": portfolio,
            "portfolio_round": portfolio_round,
            "authority": empty_authority,
            "critic_readiness": build_critic_readiness(root, critics, {}, {}),
            "route_bindings": {route: {} for route in ROUTES},
            "critic_review_outputs": {route: relative_repo_path(root, "NO_CURRENT_CRITIC_REVIEW") for route in ROUTES},
            "round_checkpoints": [],
            "terminal_reviewer_targets": {},
            "parse_warnings": ["CURRENT.md 不存在或不可读；看板不能判定当前 portfolio truth。"],
            "current_worker_zh": "等待发布当前轮次入口",
            "next_worker_zh": "规划者补齐 CURRENT.md",
        }
    parsed = parse_current_handoff(text, root)
    active_critics = [ROUTE_LABELS[route] for route, entry in parsed["critics"].items() if entry.get("active")]
    controller_count = parsed.get("authority", {}).get("controller_authorized_now", parsed.get("portfolio", {}).get("current_controller_authorizations", 0))
    if active_critics:
        current_worker = "、".join(f"{label} Critic 正在判断" for label in active_critics)
        next_worker = "等待各自 route-specific ready/revision token；Controller 当前 blocked" if not controller_count else "仅 exact ready token 对应 route Controller 可启动"
    elif parsed["planner_prompt"].get("active"):
        current_worker = "规划者正在处理"
        next_worker = "按规划者结论交给 Critic；Controller 未获授权前保持 blocked"
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


def apply_terminal_reviewer_target(route: dict[str, Any], handoff: dict[str, Any]) -> None:
    target = handoff.get("terminal_reviewer_targets", {}).get(route.get("id", ""), {})
    route["terminal_reviewer_target"] = target
    if not target:
        route["terminal_reviewer_ready"] = False
        route["terminal_reviewer_warnings"] = []
        return

    token = target.get("terminal_token", "")
    target_head = target.get("reviewer_target_head", "")
    route_head = route.get("sha", "")
    origin_head = route.get("origin_sha", "")
    required_files = ("result", "completion_check", "review_request", "manifest")
    missing_files = [name for name in required_files if not route.get("packet_files", {}).get(name)]
    token_present = bool(token and token in route.get("status_keywords", []))
    head_matches_local = bool(target_head and route_head and target_head == route_head)
    head_matches_origin = bool(target_head and origin_head and target_head == origin_head)
    decisions_open = (
        target.get("route_promotion_decision") in {"", "NOT_REVIEWED"}
        and target.get("route_negative_decision") in {"", "NOT_REVIEWED"}
        and target.get("scientific_resolution_status") in {"", "AWAITING_REVIEW"}
    )
    forbidden_closed = (
        target.get("validation_upload") in {"", "false", "False"}
        and target.get("hosted_metric_claim") in {"", "false", "False"}
        and target.get("m11_started") in {"", "false", "False"}
    )
    warnings = []
    if not token_present:
        warnings.append("terminal reviewer target token not found in route packet")
    if missing_files:
        warnings.append("terminal reviewer target missing packet files: " + ", ".join(missing_files))
    if not head_matches_local:
        warnings.append("terminal reviewer target head does not match local route head")
    if not decisions_open or not forbidden_closed:
        warnings.append("terminal reviewer target authority fields are not review-boundary safe")
    route["terminal_reviewer_ready"] = bool(token_present and not missing_files and head_matches_local and decisions_open and forbidden_closed)
    route["terminal_reviewer_target_head_matches_origin"] = head_matches_origin
    route["terminal_reviewer_warnings"] = warnings


def next_checkpoint_for_route(handoff: dict[str, Any], route: str) -> dict[str, Any]:
    label = ROUTE_LABELS.get(route, route)
    for checkpoint in handoff.get("round_checkpoints", []):
        items = [item for item in checkpoint.get("items", []) if label in item]
        if items:
            return {"date": checkpoint.get("date", ""), "items": items}
    return {"date": "", "items": []}


def annotate_handoff_workers(route: dict[str, Any], handoff: dict[str, Any]) -> None:
    route_id = route["id"]
    readiness = handoff.get("critic_readiness", {}).get(route_id, {})
    critic = readiness.get("critic_handoff") or handoff.get("critics", {}).get(route_id, relative_repo_path(Path("/"), "NO_CURRENT_CRITIC_HANDOFF"))
    portfolio = handoff.get("portfolio", empty_portfolio_state())
    authority = handoff.get("authority", {})
    binding = handoff.get("route_bindings", {}).get(route_id, {})
    portfolio_state = portfolio.get("routes", {}).get(route_id, "UNKNOWN")
    active_routes = set(portfolio.get("active_routes", []))
    active_controller_routes = set(portfolio.get("active_controller_routes", []))
    deferred_routes = set(portfolio.get("deferred_routes", []))
    allowed_tokens = readiness.get("allowed_tokens", [])
    ready_token = readiness.get("ready_token", "")
    revision_token = readiness.get("revision_token", "")
    required_head = binding.get("required_head", "")
    origin_sha = route.get("origin_sha", "")
    head_matches_required = bool(required_head and origin_sha and required_head == origin_sha)
    controller_authorized_now = int(authority.get("controller_authorized_now", portfolio.get("current_controller_authorizations", 0)) or 0)
    controller_authorized = bool(route_id in active_routes and ready_token and head_matches_required and controller_authorized_now > 0)

    route["round_id"] = handoff.get("round_id", "unknown")
    route["critic_handoff"] = critic
    route["portfolio_state"] = portfolio_state
    route["is_active_round_route"] = route_id in active_routes
    route["is_active_controller_route"] = route_id in active_controller_routes
    route["is_deferred_fallback"] = route_id in deferred_routes
    route["controller_authorized"] = controller_authorized
    route["controller_authority_state_zh"] = "authorized" if controller_authorized else "blocked"
    route["allowed_tokens"] = allowed_tokens
    route["critic_review_output_path"] = readiness.get("review_output", {}).get("path", "")
    route["critic_review_output"] = readiness.get("review_output", {})
    route["critic_found_tokens"] = readiness.get("found_tokens", [])
    route["critic_ready_token"] = ready_token
    route["critic_revision_token"] = revision_token
    route["critic_gate_state_zh"] = readiness.get("state_zh", "pending critic token")
    route["latest_role_token"] = latest_role_token(route.get("role_tokens", []), route_id)
    route["required_head"] = required_head
    route["evidence_head"] = binding.get("evidence_head", "")
    route["reviewer_commit"] = binding.get("reviewer_commit", "")
    route["reviewed_controller_commit"] = binding.get("reviewed_controller_commit", "")
    route["review_token"] = binding.get("review_token", "")
    route["source_of_truth"] = "CURRENT.md + route-local packet/review + main critic review"
    route["controller_allowed"] = controller_authorized
    route["planning_blockers"] = parse_critic_blockers(route.get("critic_review_output", {})) if route_id == "route_B" else []
    stale_warning = stale_warning_for_route(route)
    route["stale_warnings"] = [stale_warning] if stale_warning else []
    route["contract_blob"] = binding.get("contract_blob", "")
    route["executor_plan_blob"] = binding.get("executor_plan_blob", "")
    route["critic_request_blob"] = binding.get("critic_request_blob", "")
    route["critic_handoff_blob"] = binding.get("critic_handoff_blob", "")
    route["evidence_mapping_blob"] = binding.get("evidence_mapping_blob", "")
    route["evidence_mapping_required_row_count"] = binding.get("evidence_mapping_required_row_count", "")
    route["head_matches_required"] = head_matches_required
    route["next_checkpoint"] = next_checkpoint_for_route(handoff, route_id)
    route["route_requirements_summary"] = [
        portfolio_state or "UNKNOWN portfolio state",
        "CURRENT.md binding and route-local packet are source-of-truth.",
        "M9/M10 hard requirements remain active from ROUTE_HARD_REQUIREMENTS_MATRIX.md.",
    ]
    if route_id in deferred_routes:
        route["route_requirements_summary"] = [
            f"{portfolio_state} / dormant or deferred route.",
            "No current controller/training/Slurm authority unless CURRENT.md authorizes it.",
            "Historical evidence remains display-only.",
        ]
    route["planning_gate"] = {
        "state": route["critic_gate_state_zh"],
        "critic_handoff": critic,
        "critic_review_output": route.get("critic_review_output", {}),
        "allowed_planning_tokens": allowed_tokens,
        "ready_token": ready_token,
        "revision_token": revision_token,
        "source": "CURRENT.md + critic review output",
    }
    route["controller_authority"] = {
        "authorized": controller_authorized,
        "state": route["controller_authority_state_zh"],
        "head_matches_required": head_matches_required,
        "controller_authorized_now": controller_authorized_now,
        "source": "CURRENT.md Authority Boundary + route head binding",
    }

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

    portfolio_upper = str(portfolio_state or "").upper()

    if route["is_deferred_fallback"]:
        route["historical_display_state_zh"] = display_state
        route["display_state_zh"] = "Dormant fallback / inactive unless explicitly reauthorized"
        route["current_worker_zh"] = "非当前 active route"
        route["work_summary_zh"] = f"{route['label']} 是 {portfolio_state}；历史证据只读保留，无当前 Critic、Controller、training 或 Slurm authority。"
        route["next_action_zh"] = "除非用户明确授权或后续 Portfolio Planner 重新激活，否则不得启动 Route A controller。"
        route["reviewability"] = {
            "can_review_complete": False,
            "label_zh": "历史归档 / 非当前 active route",
            "reason_zh": "Dormant/deferred route 不参与当前 active route readiness。",
        }
        route["runtime_state"] = {
            "state": "dormant_deferred",
            "label_zh": "Dormant fallback",
            "completion_blocked": True,
            "source": "CURRENT.md portfolio_state",
        }
        route["review_state"] = {**route["reviewability"], "source": "portfolio_state"}
        route["next_worker_zh"] = route["next_action_zh"]
        route["next_action"] = {"label_zh": route["next_action_zh"], "source": "portfolio_state"}
        return

    if portfolio_upper.startswith("PLANNING_REVISION_READY_FOR_CRITIC_REREVIEW"):
        route["historical_display_state_zh"] = display_state
        route["display_state_zh"] = f"{str(route.get('round_id', 'round')).capitalize()} planning ready for critic rereview / controller blocked"
        route["current_worker_zh"] = f"{route['label']} Critic rereview pending"
        route["work_summary_zh"] = (
            f"{route['label']} 当前是 {portfolio_state}；coordinator receipt 已就绪，"
            "正在等待 independent planning critic rereview。Controller 仍不可启动。"
        )
        route["next_action_zh"] = f"交 {route['label']} independent planning critic rereview；ready token 前不得交 Controller。"
        route["next_worker_zh"] = route["next_action_zh"]
        route["completion_blockers"] = []
        route["reviewability"] = {
            "can_review_complete": False,
            "label_zh": "planning critic rereview pending",
            "reason_zh": "Coordinator receipt 已就绪，但 planning critic rereview 尚未给出 ready token。",
        }
        route["runtime_state"] = {
            "state": "planning_ready_for_critic_rereview",
            "label_zh": route["display_state_zh"],
            "completion_blocked": False,
            "source": "CURRENT.md portfolio_state + coordinator receipt",
        }
        route["review_state"] = {**route["reviewability"], "source": "planning_critic_rereview_gate"}
        route["controller_authority"] = {
            **route["controller_authority"],
            "authorized": False,
            "state": "controller blocked",
            "source": "CURRENT.md Authority Boundary + pending planning critic rereview",
        }
        route["controller_allowed"] = False
        route["next_action"] = {"label_zh": route["next_action_zh"], "source": "planning_critic_rereview_gate"}
        return

    if portfolio_upper.startswith("PLANNING_REVISION_PENDING"):
        token = revision_token or binding.get("revision_source_critic_token", "")
        route["latest_role_token"] = {
            "token": token,
            "route": route_id,
            "round": int(re.search(r"ROUND([0-9]+)", token).group(1)) if token and re.search(r"ROUND([0-9]+)", token) else 0,
            "kind": "PLANNING_NEEDS_REVISION",
            "role": "planning_critic",
            "source_role": "critic_review",
            "source_path": route.get("critic_review_output_path", ""),
        } if token else route.get("latest_role_token", {})
        blockers = route.get("planning_blockers") or [
            "stale CURRENT/coordinator receipt must be repaired before controller authorization",
            "critic rereview ready token is not present",
        ]
        route["historical_display_state_zh"] = display_state
        round_label = (token.split("_PLANNING", 1)[0].split("_", 2)[-1].title().replace("Round", "Round") if token else str(route.get("round_id", "round")).capitalize())
        route["display_state_zh"] = f"{round_label} planning needs revision / controller blocked"
        route["current_worker_zh"] = "等待 coordinator receipt / Route B critic rereview"
        route["work_summary_zh"] = f"{route['label']} 当前是 {portfolio_state}；Planning critic 给出 needs revision，Controller 不可启动。"
        route["next_action_zh"] = "GPT Planner / coordinator 先修订 receipt 与 critic blocker；完成 ready token 前不得交 Controller。"
        route["next_worker_zh"] = route["next_action_zh"]
        route["completion_blockers"] = blockers
        route["reviewability"] = {
            "can_review_complete": False,
            "label_zh": "planning gate blocked",
            "reason_zh": "Planning critic needs-revision token 不授权 controller，也不是 reviewer 完成证据。",
        }
        route["runtime_state"] = {
            "state": "planning_needs_revision",
            "label_zh": route["display_state_zh"],
            "completion_blocked": True,
            "source": "CURRENT.md portfolio_state + main planning critic review",
        }
        route["review_state"] = {**route["reviewability"], "source": "planning_critic"}
        route["controller_authority"] = {
            **route["controller_authority"],
            "authorized": False,
            "state": "controller blocked",
            "source": "CURRENT.md Authority Boundary + planning needs-revision token",
        }
        route["controller_allowed"] = False
        route["next_action"] = {"label_zh": route["next_action_zh"], "source": "planning_critic"}
        return

    if portfolio_upper == "EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION":
        token = binding.get("review_token", "")
        if not token:
            reviewer_token = latest_role_token(route.get("role_tokens", []), route_id, {"reviewer"})
            token = reviewer_token.get("token", "")
        route["latest_role_token"] = {
            "token": token,
            "route": route_id,
            "round": int(re.search(r"ROUND([0-9]+)", token).group(1)) if token and re.search(r"ROUND([0-9]+)", token) else 0,
            "kind": "REVIEW_EVIDENCE_COMPLETE",
            "role": "reviewer",
            "source_role": "CURRENT.md" if binding.get("review_token") else "review",
            "source_path": binding.get("reviewer_commit", "") or route.get("latest_packet", ""),
        } if token else route.get("latest_role_token", {})
        route["historical_display_state_zh"] = display_state
        route["display_state_zh"] = "Reviewed evidence-complete / waiting portfolio reconciliation"
        route["current_worker_zh"] = "当前不需要 critic/reviewer/controller"
        route["work_summary_zh"] = f"{route['label']} reviewer 已确认 evidence complete；当前仅等待 portfolio reconciliation。"
        route["next_action_zh"] = "等待 GPT Planner 做 portfolio reconciliation；不得 upload、promotion、M11 或 final decision。"
        route["next_worker_zh"] = route["next_action_zh"]
        route["completion_blockers"] = []
        route["reviewability"] = {
            "can_review_complete": False,
            "label_zh": "review complete / portfolio pending",
            "reason_zh": "Reviewer 结果已完成 evidence completeness；下一步不是 controller 或 reviewer。",
        }
        route["runtime_state"] = {
            "state": "reviewed_evidence_complete",
            "label_zh": route["display_state_zh"],
            "completion_blocked": False,
            "source": "CURRENT.md Route C section + route-local review.md",
        }
        route["review_state"] = {**route["reviewability"], "source": "route-local reviewer result"}
        route["controller_authority"] = {
            **route["controller_authority"],
            "authorized": False,
            "state": "not needed / blocked",
            "source": "CURRENT.md portfolio evidence-complete state",
        }
        route["controller_allowed"] = False
        route["next_action"] = {"label_zh": route["next_action_zh"], "source": "portfolio_reconciliation"}
        return
    if route.get("terminal_reviewer_ready"):
        target = route.get("terminal_reviewer_target", {})
        route["controller_authority_state_zh"] = "terminal packet ready"
        route["controller_authority"] = {
            **route["controller_authority"],
            "state": "terminal_packet_ready_for_reviewer",
            "source": "CURRENT.md terminal reviewer target + route-local packet",
        }
        route["current_worker_zh"] = "等待 independent reviewer"
        route["work_summary_zh"] = f"{route['label']} controller terminal packet 已绑定到 reviewer target；当前不是 controller blocked。"
        output_path = target.get("reviewer_output_path") or f"results/{route_id}/review.md"
        short_head = target.get("reviewer_target_head", route.get("sha", ""))[:7]
        route["next_action_zh"] = f"交 {route['label']} independent reviewer 审 `{short_head}`，输出 `{output_path}`。"
        route["next_worker_zh"] = route["next_action_zh"]
        route["next_action"] = {"label_zh": route["next_action_zh"], "source": "terminal_reviewer_target"}
        return

    if route["is_active_round_route"] and critic.get("active"):
        route["current_worker_zh"] = f"{route['label']} Critic 正在判断"
        route["work_summary_zh"] = f"{route['label']} 是 {route.get('round_id', 'unknown')} active route；Critic gate: {route['critic_gate_state_zh']}；Controller: {route['controller_authority_state_zh']}。"
        if controller_authorized:
            route["next_action_zh"] = "仅该 exact route Controller 可作为 Codex goal / goal resume 启动；其他权限仍禁止。"
        elif revision_token:
            route["next_action_zh"] = "Critic 给出 needs-revision token；返回 Planner 修订，不启动 Controller。"
        elif ready_token and not head_matches_required:
            route["next_action_zh"] = "Ready token 与当前 origin route head 不匹配；需要重新绑定后才可授权。"
        else:
            route["next_action_zh"] = "等待 route-specific ready/revision token；Controller 当前 blocked。"
        route["next_worker_zh"] = route["next_action_zh"]
        route["next_action"] = {"label_zh": route["next_action_zh"], "source": "critic_gate"}
        return

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
    route["next_action"] = {"label_zh": route["next_action_zh"], "source": "route_packet"}

def reviewability_from_state(display_state: str, blockers: list[str]) -> dict[str, Any]:
    if blockers:
        return {
            "can_review_complete": False,
            "label_zh": "不可作为完成包审查",
            "reason_zh": "存在未完成运行态或缺失聚合证据。",
        }
    if display_state in {"待独立审查", "等待 independent reviewer"}:
        return {
            "can_review_complete": True,
            "label_zh": "可进入独立审查",
            "reason_zh": "已有 terminal packet/review_request，且未发现当前 pending/monitor 阻断。",
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
    packet_attempts = list(route.get("slurm_attempts", []))
    packet_ids = {normalize_job_id(str(item.get("job_id", ""))) for item in packet_attempts if item.get("job_id") and is_slurm_job_id(str(item.get("job_id", "")))}
    matched_jobs = []
    for job in jobs + recent_jobs:
        confidence = job_match_confidence(job, route)
        if not confidence:
            continue
        item = dict(job)
        item["source_confidence"] = confidence
        matched_jobs.append(item)
    seen: set[tuple[str, str]] = set()
    deduped_jobs: list[dict[str, str]] = []
    for job in matched_jobs:
        key = (job.get("id", ""), job.get("source", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped_jobs.append(job)

    route_ids = {normalize_job_id(value) for value in route.get("slurm_job_ids", [])}
    route_ids.update(packet_ids)
    route_ids.update(normalize_job_id(job.get("id", "")) for job in deduped_jobs if job.get("id"))
    route["slurm_job_ids"] = sorted((value for value in route_ids if value), key=job_sort_key)
    route["recent_slurm_jobs"] = [compact_job(job) | {"source_confidence": job.get("source_confidence", "")} for job in deduped_jobs[:12]]

    attempts_by_job: dict[str, dict[str, Any]] = {}
    for attempt in packet_attempts:
        job_id = str(attempt.get("job_id", ""))
        if not job_id or not is_slurm_job_id(job_id):
            continue
        root_id, task = split_array_job_id(job_id)
        normalized = normalize_job_id(job_id)
        attempts_by_job[normalized] = {
            "job_id": job_id,
            "array_root": root_id,
            "array_task": task,
            "partition": attempt.get("partition", ""),
            "state": attempt.get("state", ""),
            "reason": attempt.get("reason", ""),
            "elapsed": attempt.get("elapsed", ""),
            "start_estimate": attempt.get("start_estimate", ""),
            "dependency": attempt.get("dependency", ""),
            "source_packet": attempt.get("source_packet", "packet"),
            "source_confidence": attempt.get("source_confidence", "packet_text"),
            "credit": attempt.get("credit", ""),
            "compatibility_evidence": attempt.get("compatibility_evidence", ""),
        }
    for job in deduped_jobs:
        normalized = normalize_job_id(job.get("id", ""))
        if not normalized:
            continue
        existing = attempts_by_job.get(normalized, {})
        source_packet = existing.get("source_packet") or ("job_name_fallback" if job.get("source_confidence") == "fuzzy_name" else "slurm")
        merged = slurm_attempt_from_job(job, source_packet, job.get("source_confidence", "slurm"))
        merged.update({key: value for key, value in existing.items() if value and not merged.get(key)})
        attempts_by_job[normalized] = merged
    route["slurm_attempts"] = sorted(attempts_by_job.values(), key=lambda item: job_sort_key(str(item.get("job_id", ""))))

    current_states = {job.get("state", "").split()[0] for job in deduped_jobs if job.get("source") == "squeue"}
    recent_terminal_states = {job.get("state", "").split()[0] for job in deduped_jobs if job.get("source") == "sacct"}
    active_states = current_states & ACTIVE_SLURM_STATES
    terminal_reviewer_ready = bool(route.get("terminal_reviewer_ready"))
    suppress_stale_monitor_keywords = terminal_reviewer_ready and not active_states

    blockers: list[str] = []
    for keyword in route["status_keywords"]:
        if keyword in INCOMPLETE_KEYWORDS:
            if not suppress_stale_monitor_keywords:
                blockers.append(f"packet 包含 {keyword}，monitor, not completion")
        if keyword in UNDERTRAINED_KEYWORDS:
            blockers.append(f"packet 包含 {keyword}，undertrained 不能作为完成证据")

    monitor_keyword_present = any(keyword in route["status_keywords"] for keyword in INCOMPLETE_KEYWORDS) and not suppress_stale_monitor_keywords
    completed_after_monitor = bool(monitor_keyword_present and "COMPLETED" in recent_terminal_states and not active_states)
    if current_states & SLURM_PENDING_STATES:
        blockers.append("Slurm 当前仍有排队作业，monitor, not completion")
    if current_states & SLURM_RUNNING_STATES:
        blockers.append("Slurm 当前仍有运行中作业，monitor, not completion")
    if completed_after_monitor:
        blockers.append("Slurm job 已完成，但 packet 仍是 monitor 状态；需要完成后聚合/提交")
    blockers.extend(route.get("packet_parse_warnings", []))

    keywords = set(route["status_keywords"])
    has_review = bool(route["packet_files"].get("review")) and not terminal_reviewer_ready
    review_revision = bool(keywords & set(REVIEW_REVISION_KEYWORDS))
    review_evidence = bool(keywords & set(REVIEW_EVIDENCE_KEYWORDS))
    review_monitor = bool(keywords & set(REVIEW_MONITOR_KEYWORDS))
    review_pass = bool(keywords & set(REVIEW_PASS_KEYWORDS))

    if has_review and review_revision:
        display_state = "需修订"
    elif has_review and review_evidence:
        display_state = "审查未通过"
    elif has_review and review_monitor:
        display_state = "等待监控"
    elif has_review and review_pass:
        display_state = "审查通过"
    elif terminal_reviewer_ready:
        display_state = "等待 independent reviewer"
    elif blockers:
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
        elif keywords & set(UNDERTRAINED_KEYWORDS):
            display_state = "训练不足"
        else:
            display_state = "未完成"
    elif keywords & set(UNDERTRAINED_KEYWORDS):
        display_state = "训练不足"
    elif keywords & set(REVISION_KEYWORDS):
        display_state = "需修订"
    elif "TERMINAL_NON_READY_PACKET" in keywords:
        display_state = "终态 negative"
    elif keywords & set(FAILURE_KEYWORDS):
        display_state = "审查未通过" if route["packet_files"].get("review") else "需补证据"
    elif has_review and keywords & set(PASS_KEYWORDS):
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
    if blockers or display_state in {"训练不足", "Controller 已结束"}:
        route["reviewability"] = {
            "can_review_complete": False,
            "label_zh": "不可作为完成包审查" if blockers else "终态非 ready",
            "reason_zh": "存在 monitor/pending/running/awaiting-accounting/undertrained 或缺失聚合证据。" if blockers else "controller 已停止或 packet 给出非 ready 终态，需要 reviewer/GPT 决策或修订。",
        }
    elif display_state in {"需修订", "终态 negative"}:
        route["reviewability"] = {
            "can_review_complete": False,
            "label_zh": "终态非 ready",
            "reason_zh": "packet/review 给出 needs revision 或 terminal negative。",
        }
    else:
        route["reviewability"] = reviewability_from_state(display_state, blockers)
    route["completion_blockers"] = blockers
    route["controller_activity"] = controller_activity or {}
    runtime_state = "monitor_or_incomplete" if blockers or display_state in {"Slurm 运行中", "Slurm 排队中", "等待监控", "等待 sacct", "训练不足", "未完成"} else "terminal_packet_ready" if display_state in {"待独立审查", "等待 independent reviewer"} else "reviewer_completed" if display_state == "审查通过" else "needs_revision" if display_state == "需修订" else "terminal_negative" if display_state in {"审查未通过", "终态 negative"} else "controller_active" if display_state == "Controller 运行中" else "unknown"
    route["runtime_state"] = {
        "state": runtime_state,
        "label_zh": display_state,
        "completion_blocked": not route["reviewability"].get("can_review_complete", False) and runtime_state == "monitor_or_incomplete",
        "source": "packet/slurm/tmux cross-check",
    }
    route["packet_state"] = {
        **route.get("packet_state", {}),
        "latest_packet": route.get("latest_packet", ""),
        "status_keywords": route.get("status_keywords", []),
        "parse_warnings": route.get("packet_parse_warnings", []),
        "state": "parse_warning" if route.get("packet_parse_warnings") else display_state,
    }
    route["review_state"] = {
        **route.get("reviewability", {}),
        "source": "route-local review/review_request tokens",
    }

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
    git_origin_sha = run_cmd(["git", "rev-parse", f"origin/{route}"], root)
    ahead_behind = run_cmd(["git", "rev-list", "--left-right", "--count", f"main...{branch}"], root)
    worktree_branch = run_cmd(["git", "-C", str(worktree), "branch", "--show-current"], root) if worktree.exists() else {"stdout": "", "ok": False}
    worktree_dirty = run_cmd(["git", "-C", str(worktree), "status", "--porcelain"], root) if worktree.exists() else {"stdout": "", "ok": False}

    packet_files = {name: result_root / filename for name, filename in PACKET_SCAN_FILES.items()}
    extra_ledger_candidates = [
        result_root / "routing_ledger.csv",
        result_root / "slurm_ledger.csv",
        result_root / "runtime" / "controller_ledger.csv",
    ]
    for index, ledger in enumerate(extra_ledger_candidates, start=1):
        if ledger.exists():
            packet_files[f"route_ledger_{index}"] = ledger
    packet_texts = {name: read_text(path) for name, path in packet_files.items()}
    packet_jsons: dict[str, Any] = {}
    packet_parse_warnings: list[str] = []
    for name in ("controller_context", "finalizer_state"):
        parsed_json, warning = read_json_file(packet_files[name])
        packet_jsons[name] = parsed_json
        if warning:
            packet_parse_warnings.append(warning)
    latest_packet = latest_existing(list(packet_files.values()))
    combined_packet_text = "\n".join(packet_texts.values())
    packet_attempts = collect_packet_attempts(packet_texts, packet_jsons)

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
    role_tokens: list[dict[str, Any]] = []
    for name, path in packet_files.items():
        role_tokens.extend(
            extract_role_tokens(
                packet_texts.get(name, ""),
                source_role=name,
                source_path=str(path),
                mtime=path.stat().st_mtime if path.exists() else 0,
            )
        )
    slurm_job_ids = sorted(
        {normalize_job_id(attempt.get("job_id", "")) for attempt in packet_attempts if attempt.get("job_id") and is_slurm_job_id(str(attempt.get("job_id", "")))},
        key=job_sort_key,
    )
    slurm_job_ids = [job_id for job_id in slurm_job_ids if job_id]

    tmux_plan = ROUTE_TMUX_PLAN[route]
    tmux_session = fields.get("tmux session", tmux_plan["session"])
    controller_window = fields.get("controller window", default_controller_window(route, ""))
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
        "origin_sha": git_origin_sha["stdout"] if git_origin_sha["ok"] else "MISSING_ORIGIN_BRANCH",
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
        "packet_paths": {name: str(path) for name, path in packet_files.items()},
        "packet_parse_warnings": packet_parse_warnings,
        "packet_state": {
            "files": {name: str(path) for name, path in packet_files.items() if path.exists()},
            "latest_packet": str(latest_packet) if latest_packet else "",
            "status_keywords": status_keywords,
            "role_tokens": role_tokens,
            "parse_warnings": packet_parse_warnings,
        },
        "role_tokens": role_tokens,
        "slurm_attempts": packet_attempts,
        "routing_compatibility": detect_v100_compatibility(combined_packet_text),
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


def route_letter(route: str) -> str:
    return route.rsplit("_", 1)[-1]


def default_controller_window(route: str, round_id: str = "") -> str:
    letter = route_letter(route)
    if round_id and round_id != "unknown":
        round_label = round_id.capitalize() if round_id.startswith("round") else round_id
        return f"Route{letter}-{round_label}Controller"
    return f"Route{letter}-Controller"


def controller_window_pattern(route: str) -> re.Pattern[str]:
    letter = route_letter(route)
    return re.compile(rf"^Route{letter}-(?:Round[0-9]+)?Controller$")


def classify_tmux_window(route: str, name: str, round_id: str) -> dict[str, Any]:
    if not controller_window_pattern(route).match(name):
        return {"role": "other", "legacy": False, "active_for_round": False}
    legacy = name == default_controller_window(route, "")
    round_specific = default_controller_window(route, round_id) if round_id and round_id != "unknown" else ""
    return {
        "role": "controller",
        "legacy": legacy,
        "active_for_round": bool(round_specific and name == round_specific),
    }


def choose_controller_window(route: str, windows: list[dict[str, str]], round_id: str) -> tuple[str, list[str]]:
    names = [window.get("name", "") for window in windows]
    preferred = default_controller_window(route, round_id) if round_id and round_id != "unknown" else ""
    if preferred and preferred in names:
        return preferred, [name for name in names if controller_window_pattern(route).match(name) and name != preferred]
    generic = default_controller_window(route, "")
    if generic in names:
        return generic, [name for name in names if controller_window_pattern(route).match(name) and name != generic]
    discovered = [name for name in names if controller_window_pattern(route).match(name)]
    return (discovered[0] if discovered else generic, discovered[1:] if discovered else [])


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
        parts = line.split("|", 5)
        if len(parts) < 5 or parts[0] != session:
            continue
        panes.append(
            {
                "window": parts[1],
                "pane": parts[2],
                "title": parts[3],
                "path": parts[4] if len(parts) > 5 else "",
                "command": parts[5] if len(parts) > 5 else parts[4],
            }
        )
    return panes


def collect_tmux_topology(root: Path, tmux: dict[str, bool], round_id: str = "unknown", active_controller_routes: set[str] | None = None) -> list[dict[str, Any]]:
    topology: list[dict[str, Any]] = []
    active_controller_routes = active_controller_routes or set(ROUTES)
    all_panes = run_cmd(
        ["tmux", "list-panes", "-a", "-F", "#{session_name}|#{window_name}|#{pane_index}|#{pane_title}|#{pane_current_path}|#{pane_current_command}"],
        root,
        timeout=3,
    )
    for spec in TMUX_SESSION_SPECS:
        session = spec["session"]
        route = spec.get("route", "")
        present = tmux.get(session, False)
        windows_result = run_cmd(["tmux", "list-windows", "-t", session, "-F", "#{window_index}|#{window_name}|#{pane_current_command}"], root, timeout=3) if present else {"ok": False, "stdout": ""}
        windows = parse_tmux_windows(windows_result["stdout"]) if windows_result["ok"] else []
        window_aliases = spec.get("window_aliases", {})
        expected = list(spec["expected_windows"])
        if route and route in active_controller_routes:
            preferred_controller = default_controller_window(route, round_id)
            if preferred_controller not in expected:
                expected = [preferred_controller, *expected]

        def has_window(expected_name: str) -> bool:
            candidates = {expected_name, *window_aliases.get(expected_name, ())}
            if route and expected_name == default_controller_window(route, round_id):
                if not round_id or round_id == "unknown":
                    return any(controller_window_pattern(route).match(window["name"]) for window in windows)
                return any(classify_tmux_window(route, window["name"], round_id).get("active_for_round") for window in windows)
            if route and expected_name == default_controller_window(route, ""):
                return any(controller_window_pattern(route).match(window["name"]) for window in windows)
            return any(window["name"] in candidates or window.get("command", "") in candidates for window in windows)

        annotated_windows = []
        for window in windows:
            item = dict(window)
            if route:
                item.update(classify_tmux_window(route, window.get("name", ""), round_id))
            annotated_windows.append(item)

        topology.append(
            {
                "session": session,
                "label_zh": spec["label_zh"],
                "purpose_zh": spec["purpose_zh"],
                "route": route,
                "round_id": round_id,
                "present": present,
                "expected_windows": expected,
                "window_status": {name: has_window(name) for name in expected},
                "live_windows": annotated_windows,
                "panes": parse_tmux_panes(all_panes["stdout"], session) if all_panes["ok"] and present else [],
            }
        )
    return topology


def annotate_route_tmux(route: dict[str, Any], topology_by_session: dict[str, dict[str, Any]], round_id: str = "unknown") -> None:
    session_info = topology_by_session.get(route.get("tmux_session", ""), {})
    live_windows = session_info.get("live_windows", [])
    controller_window, legacy_windows = choose_controller_window(route["id"], live_windows, round_id)
    route["controller_tmux_window"] = controller_window
    route["controller_tmux_target"] = f"{route['tmux_session']}:{controller_window}.0" if controller_window else route.get("tmux_session", "")
    route["legacy_controller_windows"] = legacy_windows
    route["tmux_window_status"] = session_info.get("window_status", {})
    route["tmux_live_windows"] = live_windows
    route["tmux_panes"] = session_info.get("panes", [])
    route["tmux_activity"] = {
        "session": route.get("tmux_session", ""),
        "controller_window": controller_window,
        "legacy_controller_windows": legacy_windows,
        "panes": session_info.get("panes", []),
        "source": "tmux list-panes/list-windows",
    }


def parse_squeue(stdout: str) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    for line in stdout.splitlines():
        parts = line.split("|")
        if len(parts) >= 10:
            job_id, array_root, array_task, partition, name, state, reason, elapsed, start, dependency = parts[:10]
            user = ""
            time_value = elapsed
        elif len(parts) >= 7:
            job_id, user, partition, name, state, time_value, reason = parts[:7]
            array_root, array_task, start, dependency = split_array_job_id(job_id)[0], split_array_job_id(job_id)[1], "", ""
        else:
            continue
        jobs.append(
            {
                "id": job_id,
                "array_root": array_root,
                "array_task": array_task,
                "user": user,
                "partition": partition,
                "name": name,
                "state": state,
                "time": time_value,
                "reason": reason,
                "start": start,
                "dependency": dependency,
                "is_route_job": any(route_name_matches(route, name) for route in ROUTES),
                "is_general": partition == "general",
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


def slurm_job_group_key(job: dict[str, str]) -> tuple[int, int, str, str]:
    partition = job.get("partition", "")
    if partition == "general":
        group_order = 0
    elif partition in CARE_PARTITION_ORDER:
        group_order = 1
    else:
        group_order = 2
    try:
        partition_order = CARE_PARTITION_ORDER.index(partition)
    except ValueError:
        partition_order = len(CARE_PARTITION_ORDER)
    return (group_order, partition_order, partition, job.get("id", ""))


def slurm_job_display_groups(jobs: list[dict[str, str]]) -> list[dict[str, Any]]:
    general_jobs = sorted([job for job in jobs if job.get("partition") == "general"], key=slurm_job_group_key)
    care_gpu_jobs = sorted([job for job in jobs if job.get("partition") in CARE_PARTITION_ORDER], key=slurm_job_group_key)
    other_jobs_by_partition: dict[str, list[dict[str, str]]] = {}
    for job in jobs:
        partition = job.get("partition", "")
        if partition == "general" or partition in CARE_PARTITION_ORDER:
            continue
        other_jobs_by_partition.setdefault(partition, []).append(job)

    groups: list[dict[str, Any]] = []
    if general_jobs:
        groups.append({"title": "general", "subtitle": f"{len(general_jobs)} 个作业", "jobs": general_jobs})
    if care_gpu_jobs:
        groups.append({"title": "CARE GPU 分区", "subtitle": "htzhulab > a100-gpu > volta-gpu", "jobs": care_gpu_jobs})
    for partition in sorted(other_jobs_by_partition):
        grouped_jobs = sorted(other_jobs_by_partition[partition], key=slurm_job_group_key)
        groups.append({"title": partition, "subtitle": f"{len(grouped_jobs)} 个作业", "jobs": grouped_jobs})
    return groups


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


def parse_watchboard_processes(stdout: str, root: Path) -> dict[str, Any]:
    processes: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        if "scripts/ops/build_route_watchboard.py" not in line or "--serve" not in line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, etime, cmd = parts
        port_match = re.search(r"--port\s+(\d+)", cmd)
        port = int(port_match.group(1)) if port_match else 0
        executable = cmd.split()[0] if cmd.split() else ""
        canonical_python = executable in {
            "/users/a/e/aereinh/CARE/envs/env_CARE/bin/python",
            "./envs/env_CARE/bin/python",
        }
        canonical = port == 8766 and canonical_python
        risk = ""
        if port == 8765:
            risk = "legacy_port"
        if not canonical_python:
            risk = "bare_python_or_unknown_executable" if not risk else f"{risk}+bare_python_or_unknown_executable"
        processes.append(
            {
                "pid": pid,
                "ppid": ppid,
                "etime": etime,
                "cmd": cmd,
                "port": port,
                "python_executable": executable,
                "canonical": canonical,
                "risk": risk,
            }
        )
    canonical_count = sum(1 for proc in processes if proc.get("canonical"))
    return {
        "canonical_port": 8766,
        "canonical_python": "/users/a/e/aereinh/CARE/envs/env_CARE/bin/python",
        "processes": processes,
        "duplicate_or_legacy_detected": len(processes) > 1 or any(proc.get("risk") for proc in processes),
        "status_schema_freshness": "unknown_until_served_status_compared",
        "refresh_required": canonical_count != 1 or len(processes) != 1 or any(proc.get("risk") for proc in processes),
    }


def path_from_config(root: Path, config: dict[str, Any], key: str, default: str) -> Path:
    raw = Path(str(config.get(key) or default))
    return raw if raw.is_absolute() else root / raw


def parse_notifier_processes(stdout: str) -> list[dict[str, Any]]:
    processes: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        if "notify_goal_watcher.py" not in line or "--loop" not in line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, etime, cmd = parts
        processes.append(
            {
                "pid": pid,
                "ppid": ppid,
                "etime": etime,
                "cmd": cmd,
                "canonical_python": "/users/a/e/aereinh/CARE/envs/env_CARE/bin/python" in cmd,
            }
        )
    return processes


def read_notifier_config(root: Path) -> tuple[dict[str, Any], list[str]]:
    path = root / "controller_notifications" / "config.example.json"
    config, warning = read_json_file(path)
    warnings: list[str] = []
    if warning:
        warnings.append(warning)
    if not isinstance(config, dict):
        config = {}
    config.setdefault("enabled_routes", [])
    config.setdefault("state_path", "controller_notifications/state/notified_goals.json")
    config.setdefault("status_path", "controller_notifications/state/notify_goal_watcher_status.json")
    config.setdefault("log_path", "controller_notifications/logs/notify_goal_watcher.log")
    config.setdefault("tmux_session", "care_watchboard")
    config.setdefault("tmux_window", "Notify")
    return config, warnings


def secret_file_presence(root: Path) -> dict[str, Any]:
    env_path = root / "secrets" / "care_notify.env"
    return {
        "env_file_path": str(env_path),
        "env_file_exists": env_path.is_file(),
    }


def collect_ops_services(
    root: Path,
    tmux_topology: list[dict[str, Any]],
    process_stdout: str,
    live_service_state: dict[str, Any],
) -> dict[str, Any]:
    topology_by_session = {item.get("session", ""): item for item in tmux_topology}
    watchboard_topology = topology_by_session.get("care_watchboard", {})
    window_status = watchboard_topology.get("window_status", {})
    live_windows = watchboard_topology.get("live_windows", [])
    panes = watchboard_topology.get("panes", [])

    notifier_config, config_warnings = read_notifier_config(root)
    notifier_status_path = path_from_config(root, notifier_config, "status_path", "controller_notifications/state/notify_goal_watcher_status.json")
    notifier_state_path = path_from_config(root, notifier_config, "state_path", "controller_notifications/state/notified_goals.json")
    notifier_log_path = path_from_config(root, notifier_config, "log_path", "controller_notifications/logs/notify_goal_watcher.log")
    notifier_status, notifier_status_warning = read_json_file(notifier_status_path)
    if notifier_status_warning:
        config_warnings.append(notifier_status_warning)
    if not isinstance(notifier_status, dict):
        notifier_status = {}

    notifier_processes = parse_notifier_processes(process_stdout)
    notify_window = str(notifier_config.get("tmux_window") or "Notify")
    notify_window_present = bool(window_status.get(notify_window)) or any(window.get("name") == notify_window for window in live_windows)
    notifier_warnings = list(config_warnings)
    if not notify_window_present:
        notifier_warnings.append(f"care_watchboard:{notify_window} window missing")
    if notify_window_present and not notifier_processes:
        notifier_warnings.append("Notify window exists but notify_goal_watcher.py --loop process was not detected")
    if not notifier_status_path.exists():
        notifier_warnings.append("notify_goal_watcher_status.json missing until watcher completes first scan")

    smtp_from_status = notifier_status.get("smtp", {}) if isinstance(notifier_status.get("smtp"), dict) else {}
    secret_presence = secret_file_presence(root)
    smtp_secret_present = bool(smtp_from_status.get("smtp_password_present")) or bool(secret_presence.get("env_file_exists"))

    tunnel_processes = []
    for line in process_stdout.splitlines():
        if "cloudflared" not in line:
            continue
        if " rg " in f" {line} " or " grep " in f" {line} " or "ps -u" in line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, etime, cmd = parts
        if "care-watchboard" in cmd or "cloudflared_watchboard" in cmd:
            tunnel_processes.append({"pid": pid, "ppid": ppid, "etime": etime, "cmd": cmd})
    tunnel_window_present = bool(window_status.get("watchboard-tunnel")) or bool(window_status.get("Tunnel"))
    tunnel_warnings: list[str] = []
    if not tunnel_window_present:
        tunnel_warnings.append("care_watchboard tunnel window missing")
    if not tunnel_processes:
        tunnel_warnings.append("cloudflared care-watchboard process not detected")

    server_warnings: list[str] = []
    if not window_status.get("Watchboard"):
        server_warnings.append("canonical Watchboard window missing; legacy python window may still be serving")
    if live_service_state.get("duplicate_or_legacy_detected"):
        server_warnings.append("duplicate or legacy watchboard serve detected")

    notifier_enabled_routes = list(notifier_config.get("enabled_routes", []))
    stale_status_routes = list(notifier_status.get("enabled_routes") or [])
    if stale_status_routes != notifier_enabled_routes:
        notifier_warnings.append("notify_goal_watcher_status.json enabled_routes stale; config.example.json/current config wins")

    controller_notifier = {
        "enabled": bool(notifier_enabled_routes),
        "tmux_window": notify_window,
        "tmux_window_present": notify_window_present,
        "process_detected": bool(notifier_processes),
        "processes": notifier_processes,
        "loop_command": notifier_processes[0]["cmd"] if notifier_processes else "",
        "log_path": str(notifier_log_path),
        "state_path": str(notifier_state_path),
        "status_path": str(notifier_status_path),
        "enabled_routes": notifier_enabled_routes,
        "last_scan": str(notifier_status.get("last_scan_at_utc") or ""),
        "last_event": notifier_status.get("last_event"),
        "last_email_status": str(notifier_status.get("last_email_status") or "unknown"),
        "smtp_secret_present": smtp_secret_present,
        "smtp_user_present": bool(smtp_from_status.get("smtp_user_present")),
        "config_warnings": notifier_warnings,
    }
    return {
        "watchboard_server": {
            "enabled": True,
            "tmux_window": "Watchboard",
            "tmux_window_present": bool(window_status.get("Watchboard")),
            "process_detected": bool(live_service_state.get("processes")),
            "canonical_process_detected": any(proc.get("canonical") for proc in live_service_state.get("processes", [])),
            "canonical_command": "/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/build_route_watchboard.py --user aereinh --serve --host 127.0.0.1 --port 8766",
            "processes": live_service_state.get("processes", []),
            "warnings": server_warnings,
        },
        "watchboard_tunnel": {
            "enabled": True,
            "tmux_window": "watchboard-tunnel",
            "tmux_window_present": tunnel_window_present,
            "process_detected": bool(tunnel_processes),
            "processes": tunnel_processes,
            "warnings": tunnel_warnings,
        },
        "controller_notifier": controller_notifier,
        "source": "tmux list-windows/list-panes + ps + notifier health JSON",
        "panes": panes,
    }


def collect_staleness(routes: list[dict[str, Any]], handoff: dict[str, Any], live_service_state: dict[str, Any]) -> list[dict[str, str]]:
    staleness: list[dict[str, str]] = []
    for warning in handoff.get("parse_warnings", []):
        staleness.append({"scope": "CURRENT.md", "state": "parse_warning", "detail": warning})
    if live_service_state.get("duplicate_or_legacy_detected"):
        staleness.append({"scope": "live_service_state", "state": "duplicate_or_legacy", "detail": "旧 watchboard serve 可能覆盖 generated status.json。"})
    for route in routes:
        for warning in route.get("stale_warnings", []):
            staleness.append({"scope": route["id"], "state": "stale_current", "detail": warning})
        if route.get("required_head") and route.get("origin_sha") and not route.get("head_matches_required") and not route.get("stale_warnings"):
            staleness.append({"scope": route["id"], "state": "stale_head", "detail": "CURRENT required_head 与 origin route head 不一致。"})
        if route.get("dirty_count"):
            staleness.append({"scope": route["id"], "state": "dirty_worktree", "detail": f"worktree has {route['dirty_count']} uncommitted changes"})
        if route.get("packet_parse_warnings"):
            staleness.append({"scope": route["id"], "state": "packet_parse_warning", "detail": "; ".join(route.get("packet_parse_warnings", []))})
    return staleness


def collect_status(root: Path, worktree_root: Path, user: str) -> dict[str, Any]:
    handoff = collect_handoff_status(root)
    round_id = handoff.get("round_id", "unknown")
    routes = [collect_route(root, worktree_root, route) for route in ROUTES]
    sessions = [spec["session"] for spec in TMUX_SESSION_SPECS]
    for route in routes:
        sessions.append(route["controller_tmux"])
        sessions.append(route["reviewer_tmux"])
    tmux = collect_tmux(root, sorted({session for session in sessions if session}))
    tmux_topology = collect_tmux_topology(root, tmux, round_id=round_id, active_controller_routes=set(handoff.get("portfolio", {}).get("active_controller_routes", [])))
    topology_by_session = {item["session"]: item for item in tmux_topology}
    for route in routes:
        annotate_route_tmux(route, topology_by_session, round_id=round_id)
    controller_activities = {
        route["id"]: controller_activity_from_pane(root, route["controller_tmux_target"])
        for route in routes
        if tmux.get(route["controller_tmux"], False) and route.get("controller_tmux_target")
    }

    squeue = run_cmd(["squeue", "-h", "-u", user, "-o", "%i|%A|%a|%P|%j|%T|%R|%M|%S|%E"], root)
    sinfo = run_cmd(["sinfo", "-o", "%P|%a|%l|%D|%t|%G"], root)
    partition_squeues = {
        partition: run_cmd(["squeue", "-h", "-u", user, "-p", partition, "-o", "%i|%A|%a|%P|%j|%T|%R|%M|%S|%E"], root)
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

    process_table = run_cmd(["ps", "-u", user, "-o", "pid,ppid,etime,cmd"], root)
    live_service_state = parse_watchboard_processes(process_table["stdout"], root) if process_table["ok"] else {"processes": [], "refresh_required": True, "duplicate_or_legacy_detected": False}
    ops_services = collect_ops_services(root, tmux_topology, process_table["stdout"] if process_table["ok"] else "", live_service_state)
    for route in routes:
        apply_terminal_reviewer_target(route, handoff)
        annotate_route_runtime(route, tmux, jobs, recent_jobs, controller_activities.get(route["id"]))
        annotate_handoff_workers(route, handoff)

    route_jobs = [job for job in jobs if job["is_route_job"] or any(job_matches_route(job, route) for route in routes)]
    general_jobs = [job for job in jobs if job["partition"] == "general"]
    warnings = []
    exact_bindings = handoff.get("portfolio_round", {}).get("exact_remote_evidence_bindings", {})
    planner_base_main = exact_bindings.get("planner base main", "")
    if planner_base_main and git_origin_main["ok"] and planner_base_main != git_origin_main["stdout"]:
        warnings.append("CURRENT.md stale: planner base main differs from origin/main; show as warning only, not as route-local truth override.")
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
    warnings.extend(handoff.get("parse_warnings", []))
    if live_service_state.get("duplicate_or_legacy_detected"):
        warnings.append("检测到 duplicate/legacy watchboard serve；旧服务可能覆盖 results/watchboard/status.json，需只维护 care_watchboard 服务。")
    notifier_health = ops_services.get("controller_notifier", {})
    if notifier_health.get("config_warnings"):
        warnings.append("Controller notifier health warning: " + "; ".join(notifier_health.get("config_warnings", [])))
    for route in routes:
        if route.get("is_deferred_fallback"):
            if route["dirty_count"]:
                warnings.append(f"{route['label']} dormant fallback worktree 有 {route['dirty_count']} 个未提交变更。")
            continue
        if not route["result_root_exists"]:
            warnings.append(f"{route['label']} 尚无 result root，当前仍处于合同/环境阶段。")
        if route.get("is_active_controller_route") and not tmux.get(route["controller_tmux"], False):
            warnings.append(f"{route['label']} active controller route tmux session {route['controller_tmux']} 未启动或不可见。")
        missing_windows = [name for name, present in route.get("tmux_window_status", {}).items() if not present]
        if route.get("is_active_controller_route") and missing_windows:
            warnings.append(f"{route['label']} active controller route tmux 缺少窗口：{', '.join(missing_windows)}。")
        if route.get("stale_warnings"):
            warnings.extend(f"{route['label']} {warning}" for warning in route.get("stale_warnings", []))
        elif route.get("is_active_round_route") and route.get("required_head") and route.get("origin_sha") and not route.get("head_matches_required"):
            if route.get("terminal_reviewer_ready"):
                target_head = route.get("terminal_reviewer_target", {}).get("reviewer_target_head", "")
                warnings.append(
                    f"{route['label']} planner/critic binding head {route['required_head']} 已进入历史阶段；当前 terminal reviewer target 为 {target_head}。"
                )
            else:
                warnings.append(
                    f"{route['label']} CURRENT 绑定 head {route['required_head']} 与 origin head {route['origin_sha']} 不一致；Critic handoff stale，Controller 保持 blocked。"
                )
        if route["dirty_count"]:
            warnings.append(f"{route['label']} worktree 有 {route['dirty_count']} 个未提交变更。")
        if route.get("routing_compatibility", {}).get("volta_usable") is False:
            warnings.append(f"{route['label']} packet/ledger 记录 V100/volta incompatibility；不得因 volta 队列空闲提示可用。")
        for blocker in route["completion_blockers"]:
            warnings.append(f"{route['label']} 未完成阻断：{blocker}")

    staleness = collect_staleness(routes, handoff, live_service_state)

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
        "portfolio_round": handoff.get("portfolio_round", {}),
        "portfolio": handoff.get("portfolio", empty_portfolio_state()),
        "authority": handoff.get("authority", {}),
        "critic_readiness": handoff.get("critic_readiness", {}),
        "route_bindings": handoff.get("route_bindings", {}),
        "round_checkpoints": handoff.get("round_checkpoints", []),
        "tmux": tmux,
        "tmux_topology": tmux_topology,
        "controller_activities": controller_activities,
        "jobs": jobs,
        "recent_jobs": recent_jobs,
        "route_jobs": route_jobs,
        "general_jobs": general_jobs,
        "partitions": partitions,
        "warnings": warnings,
        "staleness": staleness,
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
        "live_service_state": live_service_state,
        "ops_services": ops_services,
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
    if route.get("is_deferred_fallback") or state.startswith("Dormant fallback"):
        return "archive"
    if state in {"Controller 运行中", "Slurm 运行中", "Slurm 排队中"}:
        return "active"
    if state in {"需修订", "审查未通过"} or (state.startswith("Round") and "planning needs revision" in state):
        return "revision"
    if route.get("completion_blockers") or state in {"需补证据", "等待监控", "等待 sacct", "未完成"}:
        return "risk"
    if state in {"训练不足"}:
        return "undertrained"
    if state in {"Controller 已结束"}:
        return "ended"
    if state in {"待独立审查", "审查通过", "Reviewed evidence-complete / waiting portfolio reconciliation"}:
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


def route_labels(routes: list[str]) -> str:
    return ", ".join(ROUTE_LABELS.get(route, route) for route in routes) or "无"


def render_token_list(tokens: list[str]) -> str:
    if not tokens:
        return render_badge("无 allowed token", "badge muted")
    return "".join(render_badge(token, "badge warn") for token in tokens)


def render_handoff_state(data: dict[str, Any]) -> str:
    handoff = data.get("handoff", {})
    portfolio_round = data.get("portfolio_round", handoff.get("portfolio_round", {}))
    round_id = portfolio_round.get("round_id", handoff.get("round_id", "unknown"))
    portfolio = data.get("portfolio", handoff.get("portfolio", empty_portfolio_state()))
    authority = data.get("authority", handoff.get("authority", {}))
    active = route_labels(portfolio.get("active_routes", []))
    deferred = route_labels(portfolio.get("deferred_routes", []))
    controller_count = authority.get("controller_authorized_now", portfolio.get("current_controller_authorizations", 0))
    boundary_rows = []
    for key in (
        "validation_upload_authorized",
        "route_promotion_authorized",
        "m11_authorized",
        "cross_route_merge_authorized",
        "hosted_metric_claim_authorized",
        "final_scientific_decision_authorized",
    ):
        value = authority.get(key, False)
        boundary_rows.append(f"<tr><td>{html.escape(key)}</td><td>{html.escape(str(value).lower())}</td></tr>")
    checkpoints = []
    for checkpoint in data.get("round_checkpoints", [])[:4]:
        items = "; ".join(checkpoint.get("items", []))
        source_heading = checkpoint.get("source_heading", "Decision Checkpoints")
        checkpoints.append(f"<li><strong>{html.escape(checkpoint.get('date', ''))}</strong> <span>{html.escape(source_heading)}</span>: {html.escape(items)}</li>")
    checkpoint_html = "".join(checkpoints) or "<li>未解析到当前 round checkpoint。</li>"
    return f"""
    <section class="panel handoff-state">
      <div class="panel-head"><h2>Portfolio handoff state</h2><span>{html.escape(round_id)}</span></div>
      <div class="portfolio-grid">
        <div><span>active routes</span><strong>{html.escape(active)}</strong></div>
        <div><span>deferred routes</span><strong>{html.escape(deferred)}</strong></div>
        <div><span>controller_authorized_now</span><strong>{html.escape(str(controller_count))}</strong></div>
        <div><span>boundary</span><strong>ready token scope only</strong></div>
      </div>
      <p class="authority-note">Ready token 只授权对应 exact route Controller 作为 Codex goal / goal resume 启动；不授权 validation upload、route promotion、M11、cross-route merge、hosted metric claim 或 final scientific decision。</p>
      <div class="two-col-inner">
        <table><thead><tr><th>Authority</th><th>值</th></tr></thead><tbody>{''.join(boundary_rows)}</tbody></table>
        <ul class="checkpoint-list">{checkpoint_html}</ul>
      </div>
    </section>
    """


def render_critic_readiness(data: dict[str, Any]) -> str:
    rows = []
    for route in data.get("portfolio", empty_portfolio_state()).get("active_routes", []):
        item = data.get("critic_readiness", {}).get(route, {})
        handoff = item.get("critic_handoff", {})
        review = item.get("review_output", {})
        found = item.get("found_tokens", [])
        rows.append(
            f"""
            <tr>
              <td><strong>{html.escape(ROUTE_LABELS[route])}</strong></td>
              <td>{soft_wrap_token(handoff.get('path', ''))}</td>
              <td>{soft_wrap_token(review.get('path', ''))}</td>
              <td><div class="badge-row compact">{render_token_list(item.get('allowed_tokens', []))}</div></td>
              <td>{html.escape(', '.join(found) or item.get('state_zh', 'pending critic token'))}</td>
            </tr>
            """
        )
    return f"""
    <section class="panel critic-readiness">
      <div class="panel-head"><h2>Critic readiness gate</h2><span>active routes only</span></div>
      <table>
        <thead><tr><th>Route</th><th>Critic handoff</th><th>Critic review output</th><th>Allowed tokens</th><th>当前 token</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
    """


def render_slurm_race_readiness() -> str:
    items = "".join(f"<li>{html.escape(item)}</li>" for item in SLURM_RACE_READINESS)
    return f"""
    <section class="panel slurm-readiness">
      <div class="panel-head"><h2>Slurm/Race readiness</h2><span>只读展示</span></div>
      <ul>{items}</ul>
      <p class="guardrail">submitted / pending / running / awaiting-accounting / undertrained / monitor packet 都不是完成。</p>
    </section>
    """


def render_ops_services(data: dict[str, Any]) -> str:
    services = data.get("ops_services", {})
    server = services.get("watchboard_server", {})
    tunnel = services.get("watchboard_tunnel", {})
    notifier = services.get("controller_notifier", {})

    def status_badge(ok: bool, label: str) -> str:
        return render_badge(label, "badge ok" if ok else "badge danger")

    server_status = "canonical" if server.get("canonical_process_detected") else "needs attention"
    tunnel_status = "running" if tunnel.get("tmux_window_present") and tunnel.get("process_detected") else "needs attention"
    notifier_status = str(notifier.get("last_email_status") or "unknown")
    last_event = notifier.get("last_event")
    if isinstance(last_event, dict):
        last_event_text = f"{last_event.get('route', '')} {last_event.get('status', '')} {last_event.get('detected_at_utc', '')}"
    else:
        last_event_text = str(last_event or "none")
    warning_items = []
    for scope, service in (("watchboard_server", server), ("watchboard_tunnel", tunnel)):
        for warning in service.get("warnings", []):
            warning_items.append(f"<li>{html.escape(scope)}: {html.escape(str(warning))}</li>")
    for warning in notifier.get("config_warnings", []):
        warning_items.append(f"<li>controller_notifier: {html.escape(str(warning))}</li>")
    warnings_html = "".join(warning_items) or "<li>ops services have no current warnings.</li>"

    return f"""
    <section class="panel ops-services">
      <div class="panel-head"><h2>Ops services</h2><span>care_watchboard</span></div>
      <div class="ops-grid">
        <div class="ops-card">
          <h3>Watchboard server</h3>
          <div class="badge-row compact">
            {status_badge(bool(server.get('tmux_window_present')), 'tmux window')}
            {status_badge(bool(server.get('canonical_process_detected')), 'canonical process')}
          </div>
          <p><strong>{html.escape(server_status)}</strong></p>
          <p class="path">{soft_wrap_token(str(server.get('canonical_command', '')))}</p>
        </div>
        <div class="ops-card">
          <h3>Watchboard tunnel</h3>
          <div class="badge-row compact">
            {status_badge(bool(tunnel.get('tmux_window_present')), 'tmux window')}
            {status_badge(bool(tunnel.get('process_detected')), 'cloudflared')}
          </div>
          <p><strong>{html.escape(tunnel_status)}</strong></p>
          <p class="path">window: {html.escape(str(tunnel.get('tmux_window', 'watchboard-tunnel')))}</p>
        </div>
        <div class="ops-card">
          <h3>Controller notifier</h3>
          <div class="badge-row compact">
            {status_badge(bool(notifier.get('tmux_window_present')), 'Notify window')}
            {status_badge(bool(notifier.get('process_detected')), 'watcher loop')}
            {status_badge(bool(notifier.get('smtp_secret_present')), 'SMTP secret present')}
          </div>
          <div class="binding-grid single">
            <div><span>enabled_routes</span><strong>{html.escape(', '.join(notifier.get('enabled_routes', [])) or 'none')}</strong></div>
            <div><span>last_scan</span><strong>{html.escape(str(notifier.get('last_scan') or 'never'))}</strong></div>
            <div><span>last_email_status</span><strong>{html.escape(notifier_status)}</strong></div>
            <div><span>last_event</span><strong>{html.escape(last_event_text)}</strong></div>
            <div><span>state_path</span><strong>{soft_wrap_token(str(notifier.get('state_path', '')))}</strong></div>
            <div><span>log_path</span><strong>{soft_wrap_token(str(notifier.get('log_path', '')))}</strong></div>
          </div>
        </div>
      </div>
      <ul class="ops-warnings">{warnings_html}</ul>
    </section>
    """


def render_live_service_state(data: dict[str, Any]) -> str:
    service = data.get("live_service_state", {})
    rows = []
    for proc in service.get("processes", []):
        rows.append(
            f"""
            <tr>
              <td>{html.escape(str(proc.get('pid', '')))}</td>
              <td>{html.escape(str(proc.get('port', '')))}</td>
              <td>{soft_wrap_token(str(proc.get('python_executable', '')))}</td>
              <td>{html.escape('canonical' if proc.get('canonical') else proc.get('risk', 'legacy/unknown'))}</td>
              <td>{soft_wrap_token(str(proc.get('cmd', '')))}</td>
            </tr>
            """
        )
    body = "".join(rows) if rows else '<tr><td colspan="5">未检测到 watchboard --serve 进程。</td></tr>'
    badge = "refresh required" if service.get("refresh_required") else "canonical"
    return f"""
    <section class="panel live-service">
      <div class="panel-head"><h2>Live service state</h2><span>{html.escape(badge)}</span></div>
      <table>
        <thead><tr><th>PID</th><th>Port</th><th>Python</th><th>状态</th><th>Command</th></tr></thead>
        <tbody>{body}</tbody>
      </table>
      <p class="guardrail">canonical serve: /users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/build_route_watchboard.py --serve --host 127.0.0.1 --port 8766；8765 或 bare python 是 legacy risk。</p>
    </section>
    """


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
    portfolio_round = data.get("portfolio_round", data.get("handoff", {}).get("portfolio_round", {}))
    round_id = portfolio_round.get("round_id", data.get("handoff", {}).get("round_id", "unknown"))
    for route in data["routes"]:
        cls = status_class(route, tmux)
        packet_badges = "".join(
            render_badge(PACKET_LABELS_ZH.get(name, name), "badge ok" if exists else "badge muted")
            for name, exists in route["packet_files"].items()
        )
        keyword_badges = "".join(render_badge(keyword, "badge warn") for keyword in route["status_keywords"]) or render_badge("暂无 packet 状态", "badge muted")
        blocker_badges = "".join(render_badge(blocker, "badge danger") for blocker in route["completion_blockers"]) or render_badge(route["reviewability"].get("label_zh", "尚不可审查为完成"), "badge muted")
        portfolio_badges = "".join(
            [
                render_badge(route.get("portfolio_state", "UNKNOWN"), "badge ok" if route.get("is_active_round_route") else "badge muted"),
                render_badge(f"Controller {route.get('controller_authority_state_zh', 'blocked')}", "badge ok" if route.get("controller_authorized") or route.get("controller_authority_state_zh") != "blocked" else "badge danger"),
                render_badge("head matched" if route.get("head_matches_required") else "head not matched/unknown", "badge ok" if route.get("head_matches_required") else "badge warn"),
            ]
        )
        architecture_items = "".join(f"<li>{html.escape(line)}</li>" for line in (route.get("route_requirements_summary") or route["architecture_lines"]))
        checkpoint = route.get("next_checkpoint", {})
        checkpoint_text = f"{checkpoint.get('date', '')}: {'; '.join(checkpoint.get('items', []))}" if checkpoint.get("date") else "未解析到 route checkpoint"
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
                <span class="state-pill">{html.escape(route.get('display_state_zh', '待判定'))}</span>
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
              <section class="route-section compact-section">
                <h3>Portfolio route state</h3>
                <div class="badge-row compact">{portfolio_badges}</div>
                <div class="binding-grid">
                  <div><span>latest role token</span><strong>{soft_wrap_token(route.get('latest_role_token', {}).get('token', '') or route.get('review_token', '') or route.get('critic_revision_token', '') or 'none')}</strong></div>
                  <div><span>source of truth</span><strong>{html.escape(route.get('source_of_truth', 'packet/slurm/tmux'))}</strong></div>
                  <div><span>required/evidence head</span><strong>{soft_wrap_token(route.get('required_head', '') or route.get('evidence_head', '') or 'unknown')}</strong></div>
                  <div><span>origin route head</span><strong>{soft_wrap_token(route.get('origin_sha', '') or 'unknown')}</strong></div>
                  <div><span>reviewer commit</span><strong>{soft_wrap_token(route.get('reviewer_commit', '') or 'none')}</strong></div>
                  <div><span>reviewed controller commit</span><strong>{soft_wrap_token(route.get('reviewed_controller_commit', '') or 'none')}</strong></div>
                  <div><span>critic handoff</span><strong>{soft_wrap_token(route.get('critic_handoff', {}).get('path', '') or 'none')}</strong></div>
                  <div><span>critic review output</span><strong>{soft_wrap_token(route.get('critic_review_output_path', '') or 'none')}</strong></div>
                  <div><span>expected token</span><strong>{soft_wrap_token(', '.join(route.get('allowed_tokens', [])) or 'none')}</strong></div>
                  <div><span>next checkpoint</span><strong>{html.escape(checkpoint_text)}</strong></div>
                </div>
              </section>
              <div class="route-section compact-section">
                <h3>tmux 窗口</h3>
                <div class="badge-row compact">{window_badges(route.get('tmux_window_status', {}))}</div>
              </div>
              <section class="route-section">
                <h3>Route requirements boundary</h3>
                <ul class="architecture-list">{architecture_items}</ul>
                <p class="source">来源：CURRENT.md / ROUTE_HARD_REQUIREMENTS_MATRIX.md；历史架构来源：{html.escape(route['architecture_source'])}</p>
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

    job_sections = []
    for group in slurm_job_display_groups(data["jobs"]):
        rows = []
        for job in group["jobs"]:
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
                <h2>{html.escape(group['title'])}</h2>
                <span>{html.escape(group['subtitle'])}</span>
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

    portfolio = data.get("portfolio", empty_portfolio_state())
    authority = data.get("authority", {})
    active_route_text = route_labels(portfolio.get("active_routes", []))
    deferred_route_text = route_labels(portfolio.get("deferred_routes", []))
    controller_authorized_now = authority.get("controller_authorized_now", portfolio.get("current_controller_authorizations", 0))
    critic_pending = [
        ROUTE_LABELS[route]
        for route in portfolio.get("active_routes", [])
        if not data.get("critic_readiness", {}).get(route, {}).get("found_tokens")
    ]
    if portfolio.get("main_only_development") and not portfolio.get("active_routes"):
        critic_status_text = "main-only: no active route critic"
    else:
        critic_status_text = ", ".join(critic_pending) + " pending" if critic_pending else "ready/revision token present"
    present_tmux_sessions = sum(1 for item in data.get("tmux_topology", []) if item.get("present"))
    route_jobs = len(data["route_jobs"])
    general_jobs = len(data["general_jobs"])
    tmux_topology_html = render_tmux_topology(data)
    ops_services_html = render_ops_services(data)
    live_service_html = render_live_service_state(data)
    handoff_state_html = render_handoff_state(data)
    critic_readiness_html = render_critic_readiness(data)
    slurm_race_html = render_slurm_race_readiness()
    handoff = data.get("handoff", {})

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="{int(refresh_seconds)}">
  <title>CARE Route Portfolio {html.escape(round_id)}</title>
  <style>{CSS}</style>
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyeline">CARE Route Portfolio {html.escape(round_id)}</p>
      <h1>Route Portfolio watchboard</h1>
      <p class="subhead">只读汇总当前 main-only/portfolio posture、active/deferred routes、Critic readiness、Controller authority boundary、tmux、Slurm 当前态和最近作业。看板不提交、不取消、不上传、不合并，也不产生科学结论。</p>
    </div>
    <div class="top-actions">
      <span class="readonly">只读</span>
      <span class="timestamp">更新于 {html.escape(data['generated_at'])}</span>
    </div>
  </header>

  <main>
    <section class="summary-grid">
      <div class="summary-card"><span>active routes</span><strong>{html.escape(active_route_text)}</strong><small>由 CURRENT.md Portfolio state 自动读取；main-only 时应为无</small></div>
      <div class="summary-card"><span>inactive/deferred routes</span><strong>{html.escape(deferred_route_text)}</strong><small>Route A/C 不进入 active count</small></div>
      <div class="summary-card guard"><span>controller_authorized_now</span><strong>{html.escape(str(controller_authorized_now))}</strong><small>0 时页面不得暗示 Controller 可启动</small></div>
      <div class="summary-card"><span>critic status</span><strong>{html.escape(critic_status_text)}</strong><small>仅当前 active route 进入 critic gate；inactive routes 只读保留</small></div>
    </section>

    <section class="flow">
      <div class="flow-line"></div>
      <div class="flow-step done"><span>1</span><strong>CURRENT 绑定</strong><small>{html.escape(round_id)} portfolio truth</small></div>
      <div class="flow-step active"><span>2</span><strong>Critic gate</strong><small>active route ready/revision token</small></div>
      <div class="flow-step"><span>3</span><strong>Controller boundary</strong><small>exact route only</small></div>
      <div class="flow-step"><span>4</span><strong>运行证据</strong><small>monitor 不是 completion</small></div>
      <div class="flow-step"><span>5</span><strong>独立审查</strong><small>Reviewer 后置只读</small></div>
    </section>

    {handoff_state_html}

    {critic_readiness_html}

    <section class="routes-grid">
      {''.join(route_cards)}
    </section>

    {slurm_race_html}

    {ops_services_html}

    {live_service_html}

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
  --archive: #f3f4f6;
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
.route-card.archive { border-top-color: #6b7280; background: var(--archive); }
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
.portfolio-grid, .binding-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.binding-grid.single {
  grid-template-columns: 1fr;
}
.ops-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.ops-card {
  min-width: 0;
  padding: 14px;
  background: #fbfcfd;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.ops-card h3 {
  margin-bottom: 10px;
  font-size: 15px;
}
.ops-card p {
  margin: 8px 0 0;
}
.ops-warnings {
  margin: 12px 0 0;
  padding-left: 18px;
  color: #374151;
  line-height: 1.5;
}
.portfolio-grid div, .binding-grid div {
  min-width: 0;
  padding: 12px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.portfolio-grid span, .binding-grid span {
  display: block;
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}
.portfolio-grid strong, .binding-grid strong {
  display: block;
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.authority-note {
  margin: 12px 0;
  color: #374151;
  line-height: 1.5;
}
.two-col-inner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 14px;
}
.checkpoint-list, .slurm-readiness ul {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  line-height: 1.55;
}
.handoff-state, .critic-readiness, .slurm-readiness {
  margin: 16px 0;
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
  .summary-grid, .routes-grid, .two-col, .two-col-inner, .ops-grid {
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
  .metric-row, .portfolio-grid, .binding-grid {
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
