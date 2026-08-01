#!/usr/bin/env python3
"""Validate the CARE test Docker cross-machine server bundle packet."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
TASK_KEY = "20260801_care_test_docker_server_bundle"
RESULT_DIR = REPO / "results" / TASK_KEY
RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine")
TRANSFER = RUNTIME / "transfer"

FORBIDDEN_GIT_SUFFIXES = {
    ".pt",
    ".pth",
    ".nii",
    ".gz",
    ".tar",
    ".zip",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def require_file(errors: list[str], path: Path) -> bool:
    if not path.is_file():
        add_error(errors, f"missing file: {path}")
        return False
    return True


def validate_nnunet_replay(errors: list[str]) -> str | None:
    receipt_path = RESULT_DIR / "fresh_nnunet_provenance_receipt.json"
    casewise_path = RESULT_DIR / "fresh_nnunet_vs_historical_casewise.csv"
    manifest_path = RESULT_DIR / "fresh_nnunet_15case_manifest.json"
    for path in (receipt_path, casewise_path, manifest_path):
        require_file(errors, path)
    if not receipt_path.is_file() or not casewise_path.is_file():
        return None
    receipt = read_json(receipt_path)
    token = receipt.get("token")
    if receipt.get("fresh_output_count") != 15:
        add_error(errors, "fresh nnU-Net replay must produce 15 outputs")
    rows = list(csv.DictReader(casewise_path.open(encoding="utf-8")))
    if len(rows) != 15:
        add_error(errors, "fresh nnU-Net casewise CSV must contain 15 cases")
    array_pass = sum(r.get("array_equal") == "True" for r in rows)
    geometry_pass = sum(r.get("geometry_equal") == "True" for r in rows)
    if geometry_pass != 15:
        add_error(errors, "fresh nnU-Net geometry comparison is not 15/15")
    if token == "NNUNET_EDEMA_PROVENANCE_REPRODUCED" and array_pass != 15:
        add_error(errors, "reproduced token is invalid unless array equality is 15/15")
    if token == "NNUNET_PROVENANCE_REPLAY_MISMATCH" and array_pass == 15 and geometry_pass == 15:
        add_error(errors, "mismatch token is invalid when array+geometry equality is 15/15")
    return token


def validate_mosaic_receipts(errors: list[str], terminal_state: str) -> None:
    myops = RESULT_DIR / "fresh_mosaic_myops_manifest.json"
    cine = RESULT_DIR / "fresh_mosaic_cine_manifest.json"
    receipt = RESULT_DIR / "fresh_mosaic_replay_receipt.json"
    if terminal_state == "SERVER_BUNDLE_READY":
        for path in (myops, cine, receipt):
            require_file(errors, path)
    if receipt.is_file():
        data = read_json(receipt)
        if data.get("mosaic_commit") != "d334bd1fb2a99dbbc230510590cd8e3ee08cc377":
            add_error(errors, "MoSAIC replay receipt has unexpected commit")


def validate_runtime_markers(errors: list[str], terminal_state: str) -> None:
    ready = TRANSFER / "SERVER_BUNDLE_READY.json"
    blocked = TRANSFER / "SERVER_BUNDLE_BLOCKED.json"
    if ready.exists() and blocked.exists():
        add_error(errors, "ready and blocked runtime markers must not both exist")
    if terminal_state == "SERVER_BUNDLE_READY":
        if not require_file(errors, ready):
            return
        marker = read_json(ready)
        if marker.get("status") != "READY":
            add_error(errors, "SERVER_BUNDLE_READY status must be READY")
        archive = Path(marker.get("archive_path", ""))
        sha_path = Path(marker.get("archive_sha256_path", ""))
        if require_file(errors, archive) and marker.get("archive_sha256") != sha256_path(archive):
            add_error(errors, "archive SHA256 does not match ready marker")
        require_file(errors, sha_path)
    elif terminal_state == "SERVER_BUNDLE_BLOCKED":
        if ready.exists():
            add_error(errors, "SERVER_BUNDLE_READY must not exist for blocked terminal state")
        if not require_file(errors, blocked):
            return
        marker = read_json(blocked)
        if marker.get("status") != "BLOCKED":
            add_error(errors, "SERVER_BUNDLE_BLOCKED status must be BLOCKED")


def validate_git_scope(errors: list[str]) -> None:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    staged = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    for name in staged:
        p = Path(name)
        suffixes = "".join(p.suffixes)
        if suffixes.endswith(".nii.gz") or suffixes.endswith(".tar.gz") or p.suffix in FORBIDDEN_GIT_SUFFIXES:
            add_error(errors, f"forbidden large/binary artifact staged: {name}")
        if name.startswith("results/") and not name.startswith(f"results/{TASK_KEY}/"):
            continue
    # Also fail if transfer artifacts were accidentally copied into this task's
    # tracked source/result scope.
    for base in (REPO / "docker/CARE2026_Myocardium", RESULT_DIR):
        if not base.exists():
            continue
        for pattern in ("*.nii.gz", "*.pth", "*.pt", "*.tar", "*.tar.gz", "*.zip"):
            for bad in base.rglob(pattern):
                rel = bad.relative_to(REPO)
                add_error(errors, f"forbidden model or NIfTI/archive file inside tracked-scope directory: {rel}")


def validate() -> int:
    errors: list[str] = []
    finalizer_path = RESULT_DIR / "finalizer_state.json"
    require_file(errors, finalizer_path)
    finalizer = read_json(finalizer_path) if finalizer_path.is_file() else {}
    terminal_state = finalizer.get("terminal_state")
    if terminal_state not in {"SERVER_BUNDLE_READY", "SERVER_BUNDLE_BLOCKED"}:
        add_error(errors, f"invalid terminal_state: {terminal_state!r}")

    token = validate_nnunet_replay(errors)
    if terminal_state == "SERVER_BUNDLE_READY" and token != "NNUNET_EDEMA_PROVENANCE_REPRODUCED":
        add_error(errors, "SERVER_BUNDLE_READY requires NNUNET_EDEMA_PROVENANCE_REPRODUCED")
    if terminal_state == "SERVER_BUNDLE_BLOCKED" and token == "NNUNET_EDEMA_PROVENANCE_REPRODUCED":
        add_error(errors, "SERVER_BUNDLE_BLOCKED needs a blocker other than reproduced nnU-Net")

    validate_mosaic_receipts(errors, terminal_state or "")
    validate_runtime_markers(errors, terminal_state or "")
    validate_git_scope(errors)

    for name in (
        "controller_context.json",
        "controller_ledger.csv",
        "implementation_snapshot.md",
        "production_asset_manifest.json",
        "mapper_report_final.md",
        "controller_report.md",
        "completion_check.md",
        "MANIFEST.md",
        "notification_brief.json",
    ):
        require_file(errors, RESULT_DIR / name)

    brief_path = RESULT_DIR / "notification_brief.json"
    if brief_path.is_file():
        brief = read_json(brief_path)
        if brief.get("final_status") not in {"complete", "blocked"}:
            add_error(errors, "notification_brief final_status must be complete or blocked")
        text = brief_path.read_text(encoding="utf-8", errors="replace")
        for forbidden in ("PENDING", "RUNNING", "NEEDS_MONITOR", "JOB_SUBMITTED", "AWAITING_SACCT"):
            if forbidden in text:
                add_error(errors, f"notification_brief contains forbidden token: {forbidden}")

    report = {
        "status": "FAIL" if errors else "PASS",
        "task_key": TASK_KEY,
        "terminal_state": terminal_state,
        "nnunet_token": token,
        "errors": errors,
    }
    out_path = RESULT_DIR / "strict_validator_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(validate())
