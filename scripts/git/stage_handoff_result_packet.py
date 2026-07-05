#!/usr/bin/env python3
"""Stage a safe, lightweight handoff result packet from an ignored results dir.

This helper intentionally stages only first-level Markdown files from
results/<task_key>/, with guardrails for known sensitive/heavy transcript names.
It does not stage predictions, checkpoints, NIfTI outputs, zips, logs, nested
artifacts, CSV/JSON metric dumps, or environment transcripts.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_MAX_BYTES = 512 * 1024
FORBIDDEN_NAME_TOKENS = (
    "command_transcript",
    "transcript",
    "env_dump",
    "environment_dump",
    "secret",
    "credential",
)


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return Path(proc.stdout.strip()).resolve()


def is_task_result_dir(root: Path, path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root)
    except ValueError:
        return False
    parts = rel.parts
    if len(parts) != 2 or parts[0] != "results":
        return False
    task_key = parts[1]
    return len(task_key) > 9 and task_key[:8].isdigit() and task_key[8] == "_"


def safe_markdown_files(result_dir: Path, max_bytes: int) -> tuple[list[Path], list[str]]:
    staged: list[Path] = []
    skipped: list[str] = []
    for path in sorted(result_dir.iterdir()):
        if not path.is_file() or path.suffix != ".md":
            continue
        lowered = path.name.lower()
        if any(token in lowered for token in FORBIDDEN_NAME_TOKENS):
            skipped.append(f"{path}: forbidden name token")
            continue
        size = path.stat().st_size
        if size > max_bytes:
            skipped.append(f"{path}: {size} bytes exceeds max {max_bytes}")
            continue
        staged.append(path)
    return staged, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_dir", type=Path, help="results/<task_key> directory")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    result_dir = args.result_dir if args.result_dir.is_absolute() else root / args.result_dir
    result_dir = result_dir.resolve()
    if not result_dir.is_dir():
        print(f"ERROR: result directory not found: {result_dir}", file=sys.stderr)
        return 2
    if not is_task_result_dir(root, result_dir):
        print(f"ERROR: expected first-level results/<task_key> directory: {result_dir}", file=sys.stderr)
        return 2

    paths, skipped = safe_markdown_files(result_dir, args.max_bytes)
    for item in skipped:
        print(f"SKIP {item}")
    if not paths:
        print("No safe Markdown files to stage.")
        return 0

    rel_paths = [str(path.relative_to(root)) for path in paths]
    if args.dry_run:
        for rel in rel_paths:
            print(f"WOULD_STAGE {rel}")
        return 0

    subprocess.run(["git", "add", "-f", *rel_paths], cwd=root, check=True)
    for rel in rel_paths:
        print(f"STAGED {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
