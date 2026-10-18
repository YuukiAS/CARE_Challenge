#!/usr/bin/env python3
"""Run one exact ordinary cancellation through the project guard shim."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_DIR = REPO_ROOT / ".codex/automation-bin"
GUARD = GUARD_DIR / "scancel"
EXACT_JOB_ID = re.compile(r"^[0-9]+(?:_[0-9]+)?$")


def guarded_scancel(job_id: str, *, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    """Preserve business cancellation intent while delegating all policy to the central guard."""

    command = ["scancel", str(job_id)]
    if not EXACT_JOB_ID.fullmatch(str(job_id)):
        return subprocess.CompletedProcess(command, 64, "", "non_exact_job_id")
    expected = GUARD.resolve()
    path = str(GUARD_DIR) + os.pathsep + os.environ.get("PATH", "")
    resolved = shutil.which("scancel", path=path)
    if resolved is None or Path(resolved).resolve() != expected:
        return subprocess.CompletedProcess(command, 126, "", "project_guard_not_resolved")
    if dry_run:
        return subprocess.CompletedProcess(command, 0, "DRY_RUN_GUARDED_SCANCEL", "")
    env = dict(os.environ)
    env["PATH"] = path
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
