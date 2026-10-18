#!/usr/bin/env python3
"""Return one exact cancellation intent to the root interactive Codex."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


EXACT_JOB_ID = re.compile(r"^[0-9]+(?:_[0-9]+)?$")
INTENT_EXIT = 75


@dataclass(frozen=True)
class CancellationIntent:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


def request_slurm_cancellation(job_id: str, *, dry_run: bool = False) -> CancellationIntent:
    """Return a cancellation intent without starting any command or API call."""

    command = ["scancel", str(job_id)]
    if not EXACT_JOB_ID.fullmatch(str(job_id)):
        return CancellationIntent(command, 64, "", "non_exact_job_id")
    if dry_run:
        return CancellationIntent(command, 0, "DRY_RUN_CANCELLATION_INTENT", "")
    payload = {
        "status": "NEEDS_ROOT_INTERACTIVE_CODEX_CANCELLATION",
        "operation": "ordinary_cancel",
        "job_id": str(job_id),
        "command": f"scancel {job_id}",
        "mutation_count": 0,
    }
    return CancellationIntent(
        command,
        INTENT_EXIT,
        json.dumps(payload, sort_keys=True),
        "cancellation intent must be handled by root interactive Codex",
    )
