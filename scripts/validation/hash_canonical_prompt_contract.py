#!/usr/bin/env python3
"""Compute a stable hash for merged shared prompt sections."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def extract_section(path: Path, heading: str) -> str:
    text = path.read_text(encoding="utf-8")
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        raise ValueError(f"missing heading in {path}: {marker}")
    rest = text[start:]
    next_match = re.search(r"\n## M[0-9]+[^\n]*\n", rest[len(marker) :])
    if next_match:
        rest = rest[: len(marker) + next_match.start()]
    return normalize(rest)


def normalize(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def contract_hash(executor_file: Path, executor_heading: str, reviewer_file: Path, reviewer_heading: str) -> str:
    payload = {
        "executor": {
            "path": str(executor_file),
            "heading": executor_heading,
            "section": extract_section(executor_file, executor_heading),
        },
        "reviewer": {
            "path": str(reviewer_file),
            "heading": reviewer_heading,
            "section": extract_section(reviewer_file, reviewer_heading),
        },
    }
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executor-file", type=Path, required=True)
    parser.add_argument("--executor-heading", required=True)
    parser.add_argument("--reviewer-file", type=Path, required=True)
    parser.add_argument("--reviewer-heading", required=True)
    args = parser.parse_args(argv)
    try:
        print(
            contract_hash(
                args.executor_file,
                args.executor_heading,
                args.reviewer_file,
                args.reviewer_heading,
            )
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
