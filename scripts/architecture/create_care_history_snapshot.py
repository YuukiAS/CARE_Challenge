#!/usr/bin/env python3
"""Create an immutable CARE wiki/history milestone snapshot from current wiki."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys


HISTORY_VERSION_RE = re.compile(r"^M[0-9]{2,}$")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version_number(version: str) -> int:
    return int(version[1:])


def discover_history_versions(repo_root: Path) -> list[str]:
    history_root = repo_root / "wiki" / "history"
    if not history_root.is_dir():
        return []
    versions: list[str] = []
    for path in sorted(history_root.iterdir()):
        if path.is_dir() and HISTORY_VERSION_RE.match(path.name):
            versions.append(path.name)
    return versions


def previous_history_version(repo_root: Path, version: str) -> str | None:
    current = version_number(version)
    candidates = [item for item in discover_history_versions(repo_root) if version_number(item) < current]
    return max(candidates, key=version_number) if candidates else None


def write(path: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_file(src: Path, dst: Path, dry_run: bool) -> None:
    if dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def update_later_status_only(base: Path, args: argparse.Namespace) -> int:
    snapshot = base / "snapshot.yaml"
    if not snapshot.is_file():
        print(f"error: missing snapshot for later-status update: {snapshot}", file=sys.stderr)
        return 1
    line = f"later_status_update: \"{args.later_status_update or 'pending post-review reconciliation'}\""
    text = snapshot.read_text(encoding="utf-8")
    if re.search(r"(?m)^later_status_update:", text):
        text = re.sub(r"(?m)^later_status_update:.*$", line, text)
    else:
        text += ("\n" if not text.endswith("\n") else "") + line + "\n"
    if not args.dry_run:
        snapshot.write_text(text, encoding="utf-8")
    print(f"history snapshot later_status_update {'would be updated' if args.dry_run else 'updated'}: {snapshot}")
    return 0


def append_comparison_stub(repo_root: Path, previous: str | None, milestone: str) -> None:
    if previous is None:
        return
    path = repo_root / "wiki" / "history" / "COMPARISON.md"
    if not path.is_file():
        return
    marker = f"## {previous} -> {milestone} 自动比较入口"
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    section = f"""

{marker}

| 比较项 | 结论入口 |
| --- | --- |
| component-level delta | `wiki/history/{milestone}/figures/delta-from-{previous}.png` |
| 机器来源 | `wiki/history/{previous}/COMPONENTS.csv` + `wiki/history/{previous}/architecture.yaml` 对比 `wiki/history/{milestone}/COMPONENTS.csv` + `wiki/history/{milestone}/architecture.yaml` |
| 需人工补充 | mapper/reviewer 可在独立审阅后补充具体科学解释；本节只记录确定性生成入口，不替代 review。 |
"""
    path.write_text(text.rstrip() + section + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--milestone", required=True)
    parser.add_argument("--review-token", default="NOT_REVIEWED")
    parser.add_argument("--source-commit", default="")
    parser.add_argument("--later-status-update", default="")
    parser.add_argument("--update-later-status-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    milestone = args.milestone
    if not HISTORY_VERSION_RE.match(milestone):
        print(f"error: invalid milestone history version: {milestone}", file=sys.stderr)
        return 1
    base = repo_root / "wiki" / "history" / milestone
    if args.update_later_status_only:
        return update_later_status_only(base, args)
    if base.exists():
        print(f"error: history snapshot already exists: {base}", file=sys.stderr)
        return 1

    required = [repo_root / "wiki" / "COMPONENTS.csv", repo_root / "wiki" / "architecture.yaml", repo_root / "wiki" / "MODEL.md"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print("error: missing required current wiki inputs: " + ", ".join(missing), file=sys.stderr)
        return 1

    current_commit = args.source_commit or run(["git", "rev-parse", "HEAD"], repo_root).stdout.strip()
    previous = previous_history_version(repo_root, milestone)
    if args.dry_run:
        print(f"would create {base}")
        print("would copy COMPONENTS.csv, architecture.yaml, and generate component pages/figures")
        if previous:
            print(f"would generate wiki/history/{milestone}/figures/delta-from-{previous}.d2/svg/png")
        return 0

    (base / "components").mkdir(parents=True, exist_ok=False)
    (base / "figures").mkdir(parents=True, exist_ok=True)
    copy_file(repo_root / "wiki" / "COMPONENTS.csv", base / "COMPONENTS.csv", args.dry_run)
    copy_file(repo_root / "wiki" / "architecture.yaml", base / "architecture.yaml", args.dry_run)

    rows = list(csv.DictReader((repo_root / "wiki" / "COMPONENTS.csv").read_text(encoding="utf-8").splitlines()))
    for row in rows:
        cid = row.get("component_id", "").strip()
        if not cid:
            continue
        body = [
            f"# {row.get('role') or cid}",
            "",
            f"> 历史快照：{milestone}。本页由当前 root wiki component table 生成；当前状态以 root wiki 和最新 review 为准。",
            "",
            f"- component_id: `{cid}`",
            f"- branch: `{row.get('branch', '')}`",
            f"- current_status: `{row.get('current_status', '')}`",
            f"- evidence_status: `{row.get('evidence_status', '')}`",
            f"- target_status: `{row.get('target_status', '')}`",
            f"- source_file: `{row.get('source_file', '')}`",
            f"- symbol: `{row.get('symbol', '')}`",
            f"- runtime_evidence: `{row.get('runtime_evidence', '')}`",
            f"- review_token: `{row.get('review_token', '')}`",
            "",
            "## Notes",
            "",
            row.get("notes", ""),
            "",
        ]
        write(base / "components" / f"{cid}.md", "\n".join(body), args.dry_run)

    readme = [
        f"# {milestone} 历史分析快照",
        "",
        "本目录由 `scripts/architecture/create_care_history_snapshot.py` 从当前 root wiki 生成。",
        "",
        f"- source commit: `{current_commit}`",
        f"- review token: `{args.review_token}`",
        f"- created at: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "组件页只归档快照时的 component table 状态，不作为未来 runtime 证据。",
        "",
    ]
    write(base / "README.md", "\n".join(readme), args.dry_run)
    snapshot = [
        f'version: "{milestone}"',
        'analysis_source: "current wiki snapshot"',
        f'source_commit: "{current_commit}"',
        f'component_table_path: "wiki/history/{milestone}/COMPONENTS.csv"',
        f'architecture_path: "wiki/history/{milestone}/architecture.yaml"',
        f'component_table_sha256: "{sha256(base / "COMPONENTS.csv")}"',
        f'architecture_sha256: "{sha256(base / "architecture.yaml")}"',
        f'review_token: "{args.review_token}"',
        'later_status_update: "none"',
        "nodes:",
        "edges:",
        "",
    ]
    write(base / "snapshot.yaml", "\n".join(snapshot), args.dry_run)

    cp = run(["python", "scripts/architecture/generate_care_architecture_wiki.py", "--history", milestone], repo_root)
    if cp.returncode != 0:
        print(cp.stderr or cp.stdout, file=sys.stderr)
        return cp.returncode
    append_comparison_stub(repo_root, previous, milestone)
    print(f"created history snapshot: {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
