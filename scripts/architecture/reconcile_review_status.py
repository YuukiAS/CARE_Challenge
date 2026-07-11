#!/usr/bin/env python3
"""Copy controlled review status fields into CARE wiki lineage after review."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys


CONTROLLED_FIELDS = ("review token", "review decision", "reviewed commit", "route status", "review timestamp")
HISTORY_VERSION_RE = re.compile(r"^M[0-9]{2,}$")


def canonical_milestone_id(value: str) -> str:
    match = re.match(r"^M([0-9]+)$", value.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(f"invalid milestone id: {value}")
    number = int(match.group(1))
    return f"M{number:02d}" if number < 100 else f"M{number}"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def extract_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw in text.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        norm = key.strip().lower().replace("_", " ")
        if norm in CONTROLLED_FIELDS:
            fields[norm] = value.strip()
    token_match = re.search(r"\b(M[0-9][A-Z0-9_]*AUDITED[A-Z0-9_]*)\b", text)
    if token_match and "review token" not in fields:
        fields["review token"] = token_match.group(1)
    return fields


def upsert_block(path: Path, title: str, lines: list[str]) -> None:
    marker_start = f"<!-- {title}:start -->"
    marker_end = f"<!-- {title}:end -->"
    block = marker_start + "\n" + "\n".join(lines) + "\n" + marker_end
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    pattern = re.compile(re.escape(marker_start) + r".*?" + re.escape(marker_end), re.DOTALL)
    if pattern.search(text):
        text = pattern.sub(block, text)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n" + block + "\n"
    path.write_text(text, encoding="utf-8")


def update_snapshot(path: Path, fields: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    line = (
        "later_status_update: "
        f"review_token={fields.get('review token', 'UNKNOWN')}; "
        f"review_decision={fields.get('review decision', 'UNKNOWN')}; "
        f"route_status={fields.get('route status', 'UNKNOWN')}; "
        f"reviewed_commit={fields.get('reviewed commit', 'UNKNOWN')}"
    )
    if re.search(r"(?m)^later_status_update:", text):
        text = re.sub(r"(?m)^later_status_update:.*$", line, text)
    else:
        text += ("\n" if text and not text.endswith("\n") else "") + line + "\n"
    path.write_text(text, encoding="utf-8")


def upsert_yaml_field(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    line = f'{key}: "{value}"'
    if re.search(rf"(?m)^{re.escape(key)}\s*:", text):
        text = re.sub(rf"(?m)^{re.escape(key)}\s*:.*$", line, text)
    else:
        text += ("\n" if text and not text.endswith("\n") else "") + line + "\n"
    path.write_text(text, encoding="utf-8")


def write_current_state(repo_root: Path, milestone_id: str, review_path: Path, fields: dict[str, str]) -> None:
    rel_review = str(review_path.relative_to(repo_root)) if review_path.is_absolute() and review_path.is_relative_to(repo_root) else str(review_path)
    previous = ""
    history_root = repo_root / "wiki" / "history"
    if history_root.is_dir():
        versions = []
        current_num = int(milestone_id[1:])
        for path in history_root.iterdir():
            if path.is_dir() and HISTORY_VERSION_RE.match(path.name) and int(path.name[1:]) < current_num:
                versions.append(path.name)
        previous = max(versions, key=lambda item: int(item[1:])) if versions else ""
    lines = [
        f"current_milestone_id: {milestone_id}",
        f"current_task_key: {review_path.parent.name}",
        f"current_review_path: {rel_review}",
        f"current_review_token: {fields.get('review token', 'UNKNOWN')}",
        f"reviewed_commit: {fields.get('reviewed commit', 'UNKNOWN')}",
        "architecture_path: wiki/architecture.yaml",
        "component_table_path: wiki/COMPONENTS.csv",
        f"wiki_fingerprint: post_review_{milestone_id}",
        f"previous_milestone_id: {previous or 'UNKNOWN'}",
        f"updated_at: \"{fields.get('review timestamp', datetime.now(timezone.utc).isoformat())}\"",
    ]
    (repo_root / "wiki" / "current_state.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-md", required=True, type=Path)
    parser.add_argument("--milestone-id", required=True)
    parser.add_argument("--history-version")
    parser.add_argument("--no-generate", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    try:
        milestone_id = canonical_milestone_id(args.milestone_id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    history_version = args.history_version or milestone_id
    if canonical_milestone_id(history_version) != milestone_id:
        print("error: --history-version must match --milestone-id when provided", file=sys.stderr)
        return 1
    snapshot_path = repo_root / "wiki" / "history" / milestone_id / "snapshot.yaml"
    if not snapshot_path.is_file():
        print(f"error: missing history snapshot: {snapshot_path}", file=sys.stderr)
        return 1
    review_path = args.review_md
    if not review_path.is_file():
        print(f"error: missing review.md: {review_path}", file=sys.stderr)
        return 1
    fields = extract_fields(review_path.read_text(encoding="utf-8"))
    if not fields.get("review token"):
        print("error: review.md does not contain a controlled review token", file=sys.stderr)
        return 1
    fields.setdefault("review timestamp", datetime.now(timezone.utc).isoformat())
    review_path = review_path if review_path.is_absolute() else repo_root / review_path
    lines = [
        "## Post-Review Status",
        "",
        f"- review token: `{fields.get('review token', 'UNKNOWN')}`",
        f"- review decision: `{fields.get('review decision', 'UNKNOWN')}`",
        f"- reviewed commit: `{fields.get('reviewed commit', 'UNKNOWN')}`",
        f"- route status: `{fields.get('route status', 'UNKNOWN')}`",
        f"- review timestamp: `{fields.get('review timestamp', 'UNKNOWN')}`",
        "",
        "This block was copied deterministically from `review.md`; it is not a new scientific judgment.",
    ]
    upsert_block(repo_root / "wiki" / "README.md", "post-review-status", lines)
    upsert_block(repo_root / "wiki" / "LINEAGE.md", "post-review-status", lines)
    update_snapshot(snapshot_path, fields)
    write_current_state(repo_root, milestone_id, review_path, fields)
    upsert_yaml_field(repo_root / "wiki" / "architecture.yaml", "review_token", fields.get("review token", "UNKNOWN"))
    if not args.no_generate:
        for cmd in (
            ["python", "scripts/architecture/generate_care_architecture_wiki.py"],
            ["python", "scripts/architecture/generate_care_architecture_wiki.py", "--history", milestone_id],
            ["python", "scripts/architecture/validate_care_architecture_wiki.py", "--strict", "--history"],
        ):
            cp = run(cmd, repo_root)
            if cp.returncode != 0:
                print(cp.stderr or cp.stdout, file=sys.stderr)
                return cp.returncode
    print("review status reconciliation complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
