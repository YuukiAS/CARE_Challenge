#!/usr/bin/env python3
"""Return one exact cancellation intent to the root interactive Codex."""

from __future__ import annotations

import json
import re
import subprocess


EXACT_JOB_ID = re.compile(r"^[0-9]+(?:_[0-9]+)?$")
INTENT_EXIT = 75


def guarded_scancel(job_id: str, *, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    """Preserve business intent without starting any cancellation executable."""

    command = ["scancel", str(job_id)]
    if not EXACT_JOB_ID.fullmatch(str(job_id)):
        return subprocess.CompletedProcess(command, 64, "", "non_exact_job_id")
    if dry_run:
        return subprocess.CompletedProcess(command, 0, "DRY_RUN_CANCELLATION_INTENT", "")
    payload = {
        "status": "NEEDS_ROOT_INTERACTIVE_CODEX_CANCELLATION",
        "operation": "ordinary_cancel",
        "job_id": str(job_id),
        "command": f"scancel {job_id}",
        "mutation_count": 0,
    }
    return subprocess.CompletedProcess(
        command,
        INTENT_EXIT,
        json.dumps(payload, sort_keys=True),
        "cancellation intent must be handled by root interactive Codex",
    )
