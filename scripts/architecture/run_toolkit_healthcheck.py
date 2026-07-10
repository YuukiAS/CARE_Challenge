#!/usr/bin/env python3
"""Run AI Research Toolkit health checks without writing to the read-only source tree."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


COMMANDS = [
    ["bin/ai-research-toolkit", "validate"],
    ["bin/ai-research-toolkit", "doctor", "--json"],
    ["bin/ai-research-toolkit", "status"],
    ["bin/ai-research-toolkit", "smoke"],
]


def copy_shadow(src: Path, dst: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".git", ".local", "__pycache__"}}

    shutil.copytree(src, dst, ignore=ignore)


def run_command(source_root: Path, shadow_root: Path, rel_cmd: list[str]) -> dict[str, object]:
    cmd = [str(source_root / rel_cmd[0]), *rel_cmd[1:]]
    env = os.environ.copy()
    env["TOOLKIT_ROOT"] = str(shadow_root)
    cp = subprocess.run(cmd, cwd=shadow_root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "command": " ".join(rel_cmd),
        "exit_code": cp.returncode,
        "stdout": cp.stdout[-4000:],
        "stderr": cp.stderr[-4000:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolkit-root", default=os.environ.get("AI_RESEARCH_TOOLKIT_ROOT", "/overflow/htzhu/mingcheng_new/AI_Research_Toolkit"))
    parser.add_argument("--output", default="wiki/toolkit_healthcheck.json")
    parser.add_argument("--check", action="store_true", help="Return nonzero if any toolkit command fails.")
    args = parser.parse_args(argv)

    source_root = Path(args.toolkit_root).resolve()
    required = ["README.md", "RESOURCE_INDEX.md", "inventory/resources.yaml", "bin/ai-research-toolkit"]
    missing = [rel for rel in required if not (source_root / rel).exists()]
    if missing:
        print("missing toolkit files: " + ", ".join(missing), file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="care_toolkit_shadow_") as tmp:
        shadow = Path(tmp) / "AI_Research_Toolkit"
        copy_shadow(source_root, shadow)
        results = [run_command(source_root, shadow, cmd) for cmd in COMMANDS]

    payload = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root),
        "shadow_mode": True,
        "commands": results,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failed = [item for item in results if item["exit_code"] != 0]
    if failed:
        for item in failed:
            print(f"error: toolkit command failed: {item['command']} exit={item['exit_code']}", file=sys.stderr)
        return 1 if args.check else 0
    print(f"toolkit healthcheck passed: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
