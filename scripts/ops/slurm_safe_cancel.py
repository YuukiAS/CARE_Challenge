#!/usr/bin/env python3
"""Invoke the installed slurm-workflows safe-cancel entry without fallback."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_safe_cancel_entry(explicit: str | Path | None = None) -> Path | None:
    candidates = [
        Path(explicit).expanduser() if explicit else None,
        Path(os.environ["SLURM_WORKFLOWS_SAFE_CANCEL_ENTRY"]).expanduser()
        if os.environ.get("SLURM_WORKFLOWS_SAFE_CANCEL_ENTRY")
        else None,
        REPO_ROOT / ".agents" / "skills" / "tools-hpc-slurm-workflows" / "scripts" / "slurm_routing.py",
        Path.home() / ".agents" / "skills" / "tools-hpc-slurm-workflows" / "scripts" / "slurm_routing.py",
        Path.home() / ".codex" / "skills" / "tools-hpc-slurm-workflows" / "scripts" / "slurm_routing.py",
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    return None


def classify_safe_cancel_result(result: dict[str, Any]) -> dict[str, Any]:
    decision = result.get("decision")
    executed = decision == "ALLOW_OWNED_UNPROTECTED" and result.get("executed") is True
    if decision == "ALLOW_OWNED_UNPROTECTED" and executed:
        action = "SAFE_CANCEL_EXECUTED"
    elif decision == "ALLOW_OWNED_UNPROTECTED":
        action = "SAFE_CANCEL_EVALUATED_ALLOW"
    elif decision == "REQUIRE_FRESH_HUMAN":
        action = "RETAIN_REQUEST_FRESH_HUMAN"
    else:
        action = "RETAIN_DENIED"
    return {
        "action": action,
        "decision": decision or "DENY_UNKNOWN_OR_FORBIDDEN",
        "executed": executed,
        "retain_target": not executed,
        "reason": result.get("reason", "unknown_safe_cancel_result"),
        "human_request": result.get("human_request"),
        "readback_states": result.get("readback_states"),
    }


def safe_cancel_pending_job(
    job_id: str,
    *,
    current_run_id: str,
    site_id: str,
    local_override: str | Path | None = None,
    dry_run: bool = False,
    entry: str | Path | None = None,
) -> dict[str, Any]:
    helper = resolve_safe_cancel_entry(entry)
    if helper is None:
        return classify_safe_cancel_result(
            {"decision": "DENY_UNKNOWN_OR_FORBIDDEN", "reason": "safe_cancel_entry_unavailable", "executed": False}
        )
    command = [
        sys.executable,
        str(helper),
        "safe-cancel",
        "--job-id",
        str(job_id),
        "--owned-job-id",
        str(job_id),
        "--current-run-id",
        current_run_id,
        "--site-id",
        site_id,
    ]
    if local_override:
        command.extend(["--local-override", str(Path(local_override).expanduser())])
    if not dry_run:
        command.append("--execute")
    try:
        proc = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        result = classify_safe_cancel_result(
            {"decision": "DENY_UNKNOWN_OR_FORBIDDEN", "reason": "safe_cancel_entry_failed", "executed": False}
        )
        result["entry"] = str(helper)
        result["job_id"] = str(job_id)
        return result
    try:
        payload = json.loads(proc.stdout)
    except (TypeError, json.JSONDecodeError):
        payload = {
            "decision": "DENY_UNKNOWN_OR_FORBIDDEN",
            "reason": "safe_cancel_invalid_response",
            "executed": False,
        }
    if proc.returncode not in {0, 2}:
        payload = {
            "decision": "DENY_UNKNOWN_OR_FORBIDDEN",
            "reason": "safe_cancel_entry_failed",
            "executed": False,
        }
    result = classify_safe_cancel_result(payload)
    result["entry"] = str(helper)
    result["job_id"] = str(job_id)
    return result
