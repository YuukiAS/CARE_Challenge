#!/usr/bin/env python3
"""Route B zero-credit preflight.

This preflight is intentionally not formal training evidence. It records the
local command contract, import availability, and route_B namespace writability
before any implementation gate or Slurm runtime is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results" / "route_B"
LOG_ROOT = REPO_ROOT / "logs" / "route_B"
LOCK_ROOT = RESULT_ROOT / "locks"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def check_imports() -> dict[str, object]:
    imports: dict[str, object] = {}
    for module in (
        "torch",
        "src.care_myocardium.models.srr_propref",
        "src.care_myocardium.models.srr_blocks",
        "src.care_myocardium.cine.temporal_model",
        "src.care_myocardium.cine.registration_model",
    ):
        try:
            __import__(module)
        except Exception as exc:  # pragma: no cover - diagnostic path
            imports[module] = {"status": "FAIL", "error": repr(exc)}
        else:
            imports[module] = {"status": "PASS"}
    return imports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()

    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    LOCK_ROOT.mkdir(parents=True, exist_ok=True)

    writable = {}
    for path in (RESULT_ROOT, LOG_ROOT, LOCK_ROOT):
        probe = path / ".route_b_preflight_write_probe"
        try:
            probe.write_text("ok\n", encoding="utf-8")
            probe.unlink()
        except Exception as exc:  # pragma: no cover - diagnostic path
            writable[str(path.relative_to(REPO_ROOT))] = {"status": "FAIL", "error": repr(exc)}
        else:
            writable[str(path.relative_to(REPO_ROOT))] = {"status": "PASS"}

    payload = {
        "task": "RouteB-Controller",
        "status": "ZERO_CREDIT_PREFLIGHT_RECORDED",
        "formal_training_credit": 0,
        "formal_training_submitted": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "platform": platform.platform(),
        },
        "git": {
            "head": git(["rev-parse", "HEAD"]),
            "branch": git(["branch", "--show-current"]),
        },
        "contract": {
            "route": "route_B",
            "implementation_gate_required": True,
            "formal_training_allowed_before_gate": False,
            "validation_upload_allowed": False,
            "m11_allowed": False,
            "review_md_allowed": False,
        },
        "hashes": {
            "AGENTS.md": sha256(REPO_ROOT / "AGENTS.md"),
            "prompts/routes/route_B.md": sha256(REPO_ROOT / "prompts/routes/route_B.md"),
            "prompts/routes/route_B_executor_plan.yaml": sha256(REPO_ROOT / "prompts/routes/route_B_executor_plan.yaml"),
            ".agents/skills/slurm-routing-partition/SKILL.md": sha256(REPO_ROOT / ".agents/skills/slurm-routing-partition/SKILL.md"),
        },
        "imports": check_imports(),
        "writable_roots": writable,
        "cuda_visible": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        "strict": bool(args.strict),
    }
    failures = [
        key
        for section in ("imports", "writable_roots")
        for key, value in payload[section].items()
        if isinstance(value, dict) and value.get("status") != "PASS"
    ]
    payload["preflight_failures"] = failures
    receipt = RESULT_ROOT / "preflight_receipt.json"
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.print_contract:
        print(json.dumps(payload["contract"], indent=2, sort_keys=True))
    if args.strict and failures:
        print(json.dumps({"status": "FAIL", "failures": failures}, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
