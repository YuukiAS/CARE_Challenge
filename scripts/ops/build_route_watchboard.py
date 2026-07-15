#!/usr/bin/env python3
"""Build a read-only CARE route watchboard.

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
        "Fastest path to a new submission candidate.",
        "Expected to stay narrow: route contract, implementation gap list, validation gate, then only a bounded candidate path.",
        "Concrete implementation architecture is pending the route contract / gap inventory.",
    ],
    "route_B": [
        "Complete architecture implementation path.",
        "Expected to expose the full model/loss/dataflow gap list before formal training.",
        "Concrete component wiring should be promoted here after the route contract is written.",
    ],
    "route_C": [
        "Continuation of M10 evidence and Cine fidelity work.",
        "Expected to reuse inherited M10 assets and focus on evidence continuity / Cine temporal fidelity.",
        "Concrete runtime architecture should be derived from M10 packets once Route C publishes its inventory.",
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
)
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
        if keyword in text and keyword not in found:
            found.append(keyword)
    return found


def latest_existing(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def collect_route(root: Path, worktree_root: Path, route: str) -> dict[str, Any]:
    route_readme = root / "routes" / route / "README.md"
    readme_text = read_text(route_readme)
    fields = parse_markdown_field_table(readme_text)
    worktree = Path(fields.get("worktree") or worktree_root / route)
    result_root = root / fields.get("result root", f"results/{route}")

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
        "controller_tmux": fields.get("controller tmux", f"care_{route}_controller"),
        "reviewer_tmux": fields.get("reviewer tmux", f"care_{route}_reviewer"),
        "result_root": str(result_root),
        "result_root_exists": result_root.exists(),
        "runtime_root": fields.get("runtime root", f"results/{route}/runtime/"),
        "log_root": fields.get("log root", f"logs/{route}/"),
        "lock_root": fields.get("lock root", f"results/{route}/locks/"),
        "current_status": field_value(fields, "current status", "当前状态"),
        "next_gate": field_value(fields, "next gate", "下一个 gate"),
        "packet_files": {name: path.exists() for name, path in packet_files.items()},
        "latest_packet": str(latest_packet) if latest_packet else "",
        "latest_packet_mtime": dt.datetime.fromtimestamp(latest_packet.stat().st_mtime).isoformat(timespec="seconds") if latest_packet else "",
        "status_keywords": extract_status_keywords(combined_packet_text),
        "architecture_source": str(architecture_file) if architecture_file else "route default",
        "architecture_lines": architecture_lines,
    }


def collect_tmux(root: Path, sessions: list[str]) -> dict[str, bool]:
    status: dict[str, bool] = {}
    for session in sessions:
        check = run_cmd(["tmux", "has-session", "-t", session], root, timeout=3)
        status[session] = check["ok"]
    return status


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
                "is_route_job": any(route in parts[3] for route in ROUTES),
                "is_general": parts[2] == "general",
            }
        )
    return jobs


def parse_sinfo(stdout: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 6:
            continue
        rows.append(
            {
                "partition": parts[0],
                "availability": parts[1],
                "time_limit": parts[2],
                "nodes": parts[3],
                "state": parts[4],
                "gres": parts[5],
            }
        )
    return rows


def collect_status(root: Path, worktree_root: Path, user: str) -> dict[str, Any]:
    routes = [collect_route(root, worktree_root, route) for route in ROUTES]
    sessions = ["care_portfolio"]
    for route in routes:
        sessions.append(route["controller_tmux"])
        sessions.append(route["reviewer_tmux"])
    tmux = collect_tmux(root, sessions)

    squeue = run_cmd(["squeue", "-h", "-u", user, "-o", "%i|%u|%P|%j|%T|%M|%R"], root)
    sinfo = run_cmd(["sinfo", "-o", "%P|%a|%l|%D|%t|%G"], root)
    git_main = run_cmd(["git", "rev-parse", "main"], root)
    git_origin_main = run_cmd(["git", "rev-parse", "origin/main"], root)
    git_current = run_cmd(["git", "branch", "--show-current"], root)

    jobs = parse_squeue(squeue["stdout"]) if squeue["ok"] else []
    partitions = parse_sinfo(sinfo["stdout"]) if sinfo["ok"] else []
    partitions = [
        row
        for row in partitions
        if any(name in row["partition"] for name in ("htzhulab", "a100-gpu", "volta-gpu", "general"))
    ]

    route_jobs = [job for job in jobs if job["is_route_job"]]
    general_jobs = [job for job in jobs if job["partition"] == "general"]
    warnings = []
    if general_jobs:
        warnings.append("general partition jobs are visible and treated as connection/runtime jobs; watchboard is read-only.")
    for route in routes:
        if not route["result_root_exists"]:
            warnings.append(f"{route['label']} result root is missing.")
        if not tmux.get(route["controller_tmux"], False):
            warnings.append(f"{route['label']} controller tmux is missing.")
        if route["dirty_count"]:
            warnings.append(f"{route['label']} worktree has {route['dirty_count']} dirty entries.")

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
        "tmux": tmux,
        "jobs": jobs,
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
        },
    }


def status_class(route: dict[str, Any], tmux: dict[str, bool]) -> str:
    if "NEEDS_EVIDENCE" in route["status_keywords"] or "FAIL" in route["status_keywords"]:
        return "risk"
    if "AWAITING_REVIEW" in route["status_keywords"] or route["packet_files"].get("review_request"):
        return "review"
    if tmux.get(route["controller_tmux"]):
        return "active"
    return "idle"


def render_badge(label: str, class_name: str = "badge") -> str:
    return f'<span class="{class_name}">{html.escape(label)}</span>'


def soft_wrap_token(value: str) -> str:
    escaped = html.escape(value)
    return escaped.replace("/", "/<wbr>").replace("-", "-<wbr>").replace("_", "_<wbr>")


def render_html(data: dict[str, Any]) -> str:
    route_cards = []
    tmux = data["tmux"]
    for route in data["routes"]:
        cls = status_class(route, tmux)
        packet_badges = "".join(
            render_badge(name.replace("_", " "), "badge ok" if exists else "badge muted")
            for name, exists in route["packet_files"].items()
        )
        keyword_badges = "".join(render_badge(keyword, "badge warn") for keyword in route["status_keywords"]) or render_badge("NO_PACKET_STATUS", "badge muted")
        architecture_items = "".join(f"<li>{html.escape(line)}</li>" for line in route["architecture_lines"])
        route_cards.append(
            f"""
            <article class="route-card {cls}">
              <div class="route-head">
                <div>
                  <p class="eyeline">{html.escape(route['id'])}</p>
                  <h2>{html.escape(route['label'])}</h2>
                  <p class="purpose">{html.escape(route['purpose'])}</p>
                </div>
                <span class="state-pill">{html.escape(cls.upper())}</span>
              </div>
              <div class="metric-row">
                <div><span>Next gate</span><strong>{html.escape(route['next_gate'])}</strong></div>
                <div><span>Controller</span><strong>{'present' if tmux.get(route['controller_tmux']) else 'missing'}</strong></div>
                <div><span>Reviewer</span><strong>{'present' if tmux.get(route['reviewer_tmux']) else 'missing'}</strong></div>
                <div><span>Dirty</span><strong>{route['dirty_count'] if route['dirty_count'] is not None else 'n/a'}</strong></div>
              </div>
              <section class="route-section">
                <h3>Implementation Architecture</h3>
                <ul class="architecture-list">{architecture_items}</ul>
                <p class="source">source: {html.escape(route['architecture_source'])}</p>
              </section>
              <section class="route-section">
                <h3>Progress Evidence</h3>
                <div class="badge-row">{packet_badges}</div>
                <div class="badge-row">{keyword_badges}</div>
                <p class="path">{html.escape(route['result_root'])}</p>
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
            rows.append(
                f"""
                <tr class="{danger}">
                  <td>{html.escape(job['id'])}</td>
                  <td>{html.escape(job['partition'])}</td>
                  <td>{html.escape(job['name'])}</td>
                  <td>{html.escape(job['state'])}</td>
                  <td>{html.escape(job['time'])}</td>
                  <td>{html.escape(job['reason'])}</td>
                </tr>
                """
            )
        job_sections.append(
            f"""
            <section class="panel">
              <div class="panel-head">
                <h2>{html.escape(partition)}</h2>
                <span>{len(rows)} job(s)</span>
              </div>
              <table>
                <thead><tr><th>ID</th><th>Partition</th><th>Name</th><th>State</th><th>Time</th><th>Node / Reason</th></tr></thead>
                <tbody>{''.join(rows)}</tbody>
              </table>
            </section>
            """
        )
    if not job_sections:
        job_sections.append('<section class="panel empty">No jobs visible for this user.</section>')

    partition_rows = []
    for row in data["partitions"]:
        partition_rows.append(
            f"<tr><td>{html.escape(row['partition'])}</td><td>{html.escape(row['availability'])}</td><td>{html.escape(row['time_limit'])}</td><td>{html.escape(row['nodes'])}</td><td>{html.escape(row['state'])}</td><td>{html.escape(row['gres'])}</td></tr>"
        )
    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in data["warnings"]) or "<li>No current watchboard warnings.</li>"

    total_routes = len(data["routes"])
    active_routes = sum(1 for route in data["routes"] if tmux.get(route["controller_tmux"]))
    route_jobs = len(data["route_jobs"])
    general_jobs = len(data["general_jobs"])

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="60">
  <title>CARE Route Watchboard</title>
  <style>{CSS}</style>
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyeline">CARE Benchmark Portfolio</p>
      <h1>Route Watchboard</h1>
      <p class="subhead">Read-only CARE route progress, architecture, Slurm, and review evidence.</p>
    </div>
    <div class="top-actions">
      <span class="readonly">READ ONLY</span>
      <span class="timestamp">Updated {html.escape(data['generated_at'])}</span>
    </div>
  </header>

  <main>
    <section class="summary-grid">
      <div class="summary-card"><span>Routes with controllers</span><strong>{active_routes}/{total_routes}</strong><small>tmux controller sessions</small></div>
      <div class="summary-card"><span>Route Slurm jobs</span><strong>{route_jobs}</strong><small>name contains route_A/B/C</small></div>
      <div class="summary-card guard"><span>General jobs</span><strong>{general_jobs}</strong><small>display only; never mutate</small></div>
      <div class="summary-card"><span>Branch</span><strong>{soft_wrap_token(data['git']['current_branch'])}</strong><small>{html.escape(data['care_root'])}</small></div>
    </section>

    <section class="flow">
      <div class="flow-line"></div>
      <div class="flow-step done"><span>1</span><strong>Route Setup</strong><small>branches, worktrees, tmux</small></div>
      <div class="flow-step active"><span>2</span><strong>Contract / Gap List</strong><small>route architecture becomes concrete</small></div>
      <div class="flow-step"><span>3</span><strong>Implementation Gate</strong><small>no formal training before pass</small></div>
      <div class="flow-step"><span>4</span><strong>Runtime Evidence</strong><small>Slurm plus aggregation packet</small></div>
      <div class="flow-step"><span>5</span><strong>Independent Review</strong><small>reviewer worktree only after packet</small></div>
    </section>

    <section class="routes-grid">
      {''.join(route_cards)}
    </section>

    <section class="two-col">
      <section class="panel warnings">
        <div class="panel-head"><h2>Risks And Guardrails</h2><span>{len(data['warnings'])}</span></div>
        <ul>{warnings}</ul>
        <p class="guardrail">Forbidden actions in this interface: {html.escape(', '.join(data['guardrails']['forbidden_actions']))}.</p>
      </section>
      <section class="panel">
        <div class="panel-head"><h2>Partition Summary</h2><span>live-ish</span></div>
        <table>
          <thead><tr><th>Partition</th><th>Avail</th><th>Limit</th><th>Nodes</th><th>State</th><th>GRES</th></tr></thead>
          <tbody>{''.join(partition_rows) if partition_rows else '<tr><td colspan="6">No partition data available.</td></tr>'}</tbody>
        </table>
      </section>
    </section>

    <section class="jobs">
      <h2>Slurm Jobs For {html.escape(data['user'])}</h2>
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
.route-card.active { border-top-color: var(--accent); }
.route-card.review { border-top-color: #8b5cf6; }
.route-card.risk { border-top-color: #f97316; background: var(--risk); }
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


def write_outputs(data: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "status.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "index.html").write_text(render_html(data), encoding="utf-8")


def serve_output(output_dir: Path, host: str, port: int) -> None:
    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(output_dir), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            sys.stderr.write("watchboard: " + format % args + "\n")

    with socketserver.TCPServer((host, port), QuietHandler) as httpd:
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
    args = parser.parse_args(argv)

    root = Path(args.care_root).resolve()
    worktree_root = Path(args.worktree_root).resolve()
    output_dir = (root / args.output_dir).resolve()
    if not root.exists():
        print(f"CARE root does not exist: {root}", file=sys.stderr)
        return 2

    data = collect_status(root, worktree_root, args.user)
    write_outputs(data, output_dir)
    print(output_dir / "index.html")
    if args.serve:
        serve_output(output_dir, args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
