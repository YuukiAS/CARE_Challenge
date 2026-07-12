#!/usr/bin/env python3
"""Submit a CARE training chain with afterok dependencies and retry ledger."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyYAML is required for training chain manifests") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("training chain manifest must be a mapping")
    return data


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def parse_job_id(stdout: str) -> str:
    return stdout.strip().split(";", 1)[0].split()[0]


def validate_manifest(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stages = data.get("stages")
    if not isinstance(stages, list) or not stages:
        return ["manifest must define non-empty stages"]
    ids: set[str] = set()
    for stage in stages:
        if not isinstance(stage, dict):
            errors.append("each stage must be a mapping")
            continue
        sid = str(stage.get("id", "")).strip()
        if not sid:
            errors.append("stage missing id")
        if sid in ids:
            errors.append(f"duplicate stage id: {sid}")
        ids.add(sid)
        if not str(stage.get("script", "")).strip():
            errors.append(f"{sid}: missing script")
        if str(stage.get("dependency_type", "afterok")) == "afterany" and not (
            stage.get("independent_of_upstream_success") is True and stage.get("independent_dependency_reason")
        ):
            errors.append(f"{sid}: training dependency afterany requires independent_of_upstream_success and reason")
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        sid = str(stage.get("id", ""))
        for dep in stage.get("requires_success_of", []) or []:
            if dep not in ids:
                errors.append(f"{sid}: requires unknown upstream stage {dep}")
    return errors


def append_retry_ledger(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.is_file()
    fields = ["timestamp_utc", "stage_id", "attempt_number", "old_job_id", "new_job_id", "retry_reason", "training_credit", "fingerprint_status"]
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--receipt-path", required=True, type=Path)
    parser.add_argument("--retry-ledger-path", type=Path)
    parser.add_argument("--replacement-for", type=Path)
    parser.add_argument("--retry-reason", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    data = load_yaml(args.manifest)
    errors = validate_manifest(data)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    old_receipt = json.loads(args.replacement_for.read_text(encoding="utf-8")) if args.replacement_for else {}
    stage_to_job: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, str]] = []
    for stage in data["stages"]:
        sid = str(stage["id"])
        script = str(stage["script"])
        deps = [stage_to_job[dep] for dep in stage.get("requires_success_of", []) or []]
        command = ["sbatch", "--parsable"]
        if deps:
            command.append("--dependency=afterok:" + ":".join(deps))
        command.append(script)
        record = {
            "stage_id": sid,
            "script": script,
            "dependency_type": "afterok" if deps else "none",
            "dependency_job_ids": deps,
            "command": " ".join(shlex.quote(part) for part in command),
            "script_hash": sha256_path(repo_root / script),
            "submit_exit_code": None,
            "job_id": None,
        }
        if args.dry_run:
            record["job_id"] = f"DRYRUN_{sid}"
        else:
            cp = run(command, repo_root)
            record["submit_exit_code"] = cp.returncode
            record["stdout"] = cp.stdout
            record["stderr"] = cp.stderr
            if cp.returncode != 0:
                records.append(record)
                break
            record["job_id"] = parse_job_id(cp.stdout)
        stage_to_job[sid] = str(record["job_id"])
        records.append(record)
        if old_receipt:
            old_job = str(old_receipt.get("stage_to_job", {}).get(sid, ""))
            ledger_rows.append(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "stage_id": sid,
                    "attempt_number": "replacement",
                    "old_job_id": old_job,
                    "new_job_id": str(record["job_id"]),
                    "retry_reason": args.retry_reason,
                    "training_credit": "zero_for_failed_startup_old_attempt",
                    "fingerprint_status": "must_match_manifest_hashes",
                }
            )
    receipt = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest),
        "manifest_hash": sha256_path(args.manifest),
        "replacement_for": str(args.replacement_for or ""),
        "retry_reason": args.retry_reason,
        "stage_to_job": stage_to_job,
        "all_training_job_ids": list(stage_to_job.values()),
        "records": records,
        "dry_run": args.dry_run,
    }
    args.receipt_path.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.retry_ledger_path and ledger_rows:
        append_retry_ledger(args.retry_ledger_path, ledger_rows)
    print(args.receipt_path)
    return 0 if len(stage_to_job) == len(data["stages"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
