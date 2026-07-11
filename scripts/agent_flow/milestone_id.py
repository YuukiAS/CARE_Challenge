#!/usr/bin/env python3
"""CARE agent-flow milestone identifier helpers."""

from __future__ import annotations

import argparse
import re
import sys


MILESTONE_ID_RE = re.compile(r"^M([0-9]+)$", re.IGNORECASE)


def canonical_milestone_id(value: int | str) -> str:
    """Return the canonical milestone ID such as M08, M10, or M103."""

    if isinstance(value, int):
        number = value
    else:
        text = str(value).strip()
        match = MILESTONE_ID_RE.match(text)
        number = int(match.group(1)) if match else int(text)
    if number <= 0:
        raise ValueError("milestone number must be positive")
    return f"M{number:02d}" if number < 100 else f"M{number}"


def milestone_number(value: int | str) -> int:
    text = str(value).strip()
    match = MILESTONE_ID_RE.match(text)
    if match:
        number = int(match.group(1))
    else:
        number = int(text)
    if number <= 0:
        raise ValueError("milestone number must be positive")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("milestone")
    args = parser.parse_args(argv)
    try:
        print(canonical_milestone_id(args.milestone))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
