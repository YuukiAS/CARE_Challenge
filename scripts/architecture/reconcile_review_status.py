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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-md", required=True, type=Path)
    parser.add_argument("--history-version", default="M09")
    parser.add_argument("--no-generate", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    if not HISTORY_VERSION_RE.match(args.history_version):
        print(f"error: invalid history version: {args.history_version}", file=sys.stderr)
        return 1
    snapshot_path = repo_root / "wiki" / "history" / args.history_version / "snapshot.yaml"
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
    if not args.no_generate:
        for cmd in (
            ["python", "scripts/architecture/generate_care_architecture_wiki.py"],
            ["python", "scripts/architecture/generate_care_architecture_wiki.py", "--history", args.history_version],
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
