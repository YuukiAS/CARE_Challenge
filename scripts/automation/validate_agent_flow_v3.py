#!/usr/bin/env python3
"""Validate tracked CARE Agent-Flow v3 requests and state.

This validator intentionally uses only the Python standard library so it can run
on GitHub-hosted runners. It validates orchestration contracts and bindings; it
does not claim to validate GPU, private-data, Slurm or scientific behavior.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_NAME = "CARE_AGENT_FLOW_V3"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
TASK_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")
CODEX_ROLES = ("controller", "verifier", "executor")


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be an object: {path}")
    return value


def _missing(data: dict[str, Any], required: list[str]) -> list[str]:
    return [f"missing:{name}" for name in required if name not in data]


def validate_request(request: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors = _missing(request, list(schema["request_required"]))
    if errors:
        return errors

    if request.get("schema") != SCHEMA_NAME:
        errors.append("schema")
    if not TASK_RE.fullmatch(str(request.get("task_id", ""))):
        errors.append("task_id")
    if request.get("integration_branch") != "develop":
        errors.append("integration_branch_must_be_develop")

    required_true = (
        "planner_reentry_required",
        "critic_freeze_required",
        "controller_executor_separation_required",
        "verifier_executor_separation_required",
        "human_gate_after_planner_pass",
    )
    for key in required_true:
        if request.get(key) is not True:
            errors.append(f"{key}_must_be_true")

    forbidden_authorizations = (
        "training_authorized",
        "outer_access_authorized",
        "deployment_authorized",
    )
    for key in forbidden_authorizations:
        if request.get(key) is not False:
            errors.append(f"{key}_must_be_false")

    if not isinstance(request.get("max_repair_rounds"), int) or request["max_repair_rounds"] < 1:
        errors.append("max_repair_rounds")

    contract_sha = request.get("frozen_contract_sha256")
    if contract_sha is not None and not SHA256_RE.fullmatch(str(contract_sha)):
        errors.append("frozen_contract_sha256")

    roles = request.get("role_sessions")
    if not isinstance(roles, dict):
        return errors + ["role_sessions"]
    for role in CODEX_ROLES:
        if role not in roles or not isinstance(roles[role], dict):
            errors.append(f"missing_role:{role}")
    if any(role not in roles for role in CODEX_ROLES):
        return errors

    unique_fields = ("thread_id_file", "codex_home", "worktree", "local_branch")
    for field in unique_fields:
        values = [roles[role].get(field) for role in CODEX_ROLES]
        if any(not isinstance(value, str) or not value for value in values):
            errors.append(f"role_field_missing:{field}")
        elif len(set(values)) != len(values):
            errors.append(f"role_field_not_unique:{field}")

    expected_permissions = {
        "controller": (False, False),
        "verifier": (False, True),
        "executor": (True, False),
    }
    for role, (implementation, verification) in expected_permissions.items():
        role_data = roles[role]
        if role_data.get("may_edit_implementation") is not implementation:
            errors.append(f"{role}:may_edit_implementation")
        if role_data.get("may_edit_verification") is not verification:
            errors.append(f"{role}:may_edit_verification")

    critical_paths = request.get("critical_paths")
    if not isinstance(critical_paths, list) or not critical_paths:
        errors.append("critical_paths")
    elif not all(isinstance(path, str) and path and ".." not in Path(path).parts for path in critical_paths):
        errors.append("critical_paths_unsafe")

    return errors


def validate_current(
    current: dict[str, Any], request: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    errors = _missing(current, list(schema["current_required"]))
    if errors:
        return errors

    allowed_states = set(schema["normal_states"]) | set(schema["exception_states"])
    if current.get("schema") != SCHEMA_NAME:
        errors.append("schema")
    if current.get("task_id") != request.get("task_id"):
        errors.append("binding:task_id")
    if current.get("frozen_contract_sha256") != request.get("frozen_contract_sha256"):
        errors.append("binding:frozen_contract_sha256")
    if current.get("state") not in allowed_states:
        errors.append("state")
    if not isinstance(current.get("review_round"), int) or current["review_round"] < 0:
        errors.append("review_round")
    if not isinstance(current.get("request_nonce"), str) or not current["request_nonce"]:
        errors.append("request_nonce")

    for key in (
        "integration_commit_sha",
        "implementation_fingerprint_sha256",
        "verifier_fingerprint_sha256",
    ):
        value = current.get(key)
        if value is None:
            continue
        if key == "integration_commit_sha":
            if not SHA40_RE.fullmatch(str(value)):
                errors.append(key)
        elif not SHA256_RE.fullmatch(str(value)):
            errors.append(key)

    if current.get("state") in {"PLANNER_PASS", "AWAIT_HUMAN_DECISION"}:
        if current.get("next_action") != "AWAIT_HUMAN_DECISION":
            errors.append("planner_pass_must_stop_at_human_gate")
        if any(current.get(key) is None for key in (
            "integration_commit_sha",
            "implementation_fingerprint_sha256",
            "verifier_fingerprint_sha256",
        )):
            errors.append("planner_pass_missing_exact_bindings")

    if current.get("state") == "WAITING_FOR_EXTERNAL_GPT":
        for key in (
            "external_wait_started_utc",
            "external_wait_deadline_utc",
            "expected_state_or_artifact",
            "last_observed_remote_sha",
            "last_poll_utc",
        ):
            if not isinstance(current.get(key), str) or not str(current.get(key)).strip():
                errors.append(f"external_wait_missing:{key}")
        remote_sha = current.get("last_observed_remote_sha")
        if isinstance(remote_sha, str) and not SHA40_RE.fullmatch(remote_sha):
            errors.append("last_observed_remote_sha")

    return errors


def validate_repo(repo_root: Path) -> list[str]:
    root = repo_root / "automation" / "agent_flow_v3"
    schema_path = root / "schema.json"
    template_path = root / "task_template.json"
    schema = load_json(schema_path)
    template = load_json(template_path)

    failures = [f"{template_path}:{error}" for error in validate_request(template, schema)]
    tasks_root = root / "tasks"
    if tasks_root.is_dir():
        for task_dir in sorted(path for path in tasks_root.iterdir() if path.is_dir()):
            request_path = task_dir / "REQUEST.json"
            current_path = task_dir / "CURRENT.json"
            if not request_path.exists() and not current_path.exists():
                continue
            if not request_path.exists() or not current_path.exists():
                failures.append(f"{task_dir}:REQUEST/CURRENT pair missing")
                continue
            request = load_json(request_path)
            current = load_json(current_path)
            failures.extend(f"{request_path}:{error}" for error in validate_request(request, schema))
            failures.extend(
                f"{current_path}:{error}"
                for error in validate_current(current, request, schema)
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()

    try:
        failures = validate_repo(args.repo_root.resolve())
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("CARE Agent-Flow v3 contract validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
