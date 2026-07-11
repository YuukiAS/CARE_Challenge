#!/usr/bin/env python3
"""Compute a stable hash for a CARE milestone staging contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


REVIEW_METADATA_FIELDS = {
    "planning_review_token",
    "planning_reviewed_commit",
    "planning_review_path",
    "reviewed_at",
    "critic_token",
    "critic_decision",
}


def parse_frontmatter_block(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    block = text[4:end]
    body = text[end + 4 :]
    values: dict[str, str] = {}
    for raw_line in block.splitlines():
        if ":" not in raw_line or raw_line.lstrip().startswith("#"):
            continue
        key, value = raw_line.split(":", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values, body


def normalize_body(body: str) -> str:
    lines: list[str] = []
    for raw in body.splitlines():
        stripped = raw.rstrip()
        if re.match(r"(?i)^\s*(planning_review_token|planning_reviewed_commit|reviewed_at|critic_token)\s*:", stripped):
            continue
        lines.append(stripped)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def normalized_contract_text(text: str) -> str:
    frontmatter, body = parse_frontmatter_block(text)
    normalized_frontmatter = {
        key: value
        for key, value in sorted(frontmatter.items())
        if key not in REVIEW_METADATA_FIELDS
    }
    payload = {
        "frontmatter": normalized_frontmatter,
        "body": normalize_body(body),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def contract_sha256(path: Path) -> str:
    return hashlib.sha256(normalized_contract_text(path.read_text(encoding="utf-8")).encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    if not args.path.is_file():
        print(f"error: missing file: {args.path}", file=sys.stderr)
        return 1
    print(contract_sha256(args.path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
