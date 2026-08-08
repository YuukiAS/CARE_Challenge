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
LLM_ROLES = ("planner", "critic", "controller", "verifier", "executor")
REQUIREMENT_ID_RE = re.compile(r"^REQ_[A-Z0-9]+_[0-9]{3}$")
REQUIREMENT_LEDGER_SCHEMA = "AGENT_FLOW_V3_REQUIREMENT_LEDGER"

DEFAULT_CLASSIFICATION_ROUTES = {
    "IMPLEMENTATION_BUG": "executor",
    "VERIFIER_BUG": "verifier",
    "VERIFIER_CONTRACT_DRIFT": "verifier_plus_planner_adjudication",
    "EVIDENCE_GAP": "owning_role",
    "PROVENANCE_BINDING_GAP": "controller",
    "OPERATIONAL_FAILURE": "controller_same_scope_recovery",
    "RUNTIME_ENVIRONMENT_FAILURE": "controller_runtime_repair",
    "CONTRACT_AMBIGUITY": "planner",
    "CONTRACT_CONTRADICTION": "planner_then_critic",
    "DIAGNOSTIC_ANOMALY": "planner_diagnostic_review",
    "SCIENTIFIC_CHOICE_REQUIRED": "user",
}


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


def _schema_values(schema: dict[str, Any], key: str, fallback: list[str]) -> set[str]:
    value = schema.get(key)
    if isinstance(value, list):
        return {str(item) for item in value}
    return set(fallback)


def _ledger_requirements(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    requirements = ledger.get("requirements")
    if not isinstance(requirements, list):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        requirement_id = requirement.get("requirement_id")
        if isinstance(requirement_id, str):
            rows[requirement_id] = requirement
    return rows


def validate_requirement_ledger(ledger: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors = _missing(
        ledger,
        [
            "schema",
            "task_id",
            "request_nonce",
            "frozen_contract_sha256",
            "requirements",
            "open_scientific_choices",
        ],
    )
    if ledger.get("schema") != REQUIREMENT_LEDGER_SCHEMA:
        errors.append("ledger:schema")
    if not TASK_RE.fullmatch(str(ledger.get("task_id", ""))):
        errors.append("ledger:task_id")
    if not isinstance(ledger.get("request_nonce"), str) or not ledger.get("request_nonce"):
        errors.append("ledger:request_nonce")
    if not SHA256_RE.fullmatch(str(ledger.get("frozen_contract_sha256", ""))):
        errors.append("ledger:frozen_contract_sha256")

    requirement_types = _schema_values(schema, "requirement_types", [])
    requirements = ledger.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        return errors + ["ledger:requirements"]

    seen: set[str] = set()
    for idx, requirement in enumerate(requirements):
        prefix = f"requirement[{idx}]"
        if not isinstance(requirement, dict):
            errors.append(f"{prefix}:not_object")
            continue
        errors.extend(
            f"{prefix}:{error}"
            for error in _missing(
                requirement,
                [
                    "requirement_id",
                    "source_path",
                    "source_clause_or_field",
                    "requirement_text",
                    "requirement_type",
                    "blocking",
                    "owner_role",
                    "verification_allowed",
                    "numeric_threshold",
                    "threshold_source",
                    "scientific_rationale",
                    "derived_invariants",
                    "change_requires_contract_revision",
                ],
            )
        )
        requirement_id = str(requirement.get("requirement_id", ""))
        if not REQUIREMENT_ID_RE.fullmatch(requirement_id):
            errors.append(f"{prefix}:requirement_id")
        elif requirement_id in seen:
            errors.append(f"{prefix}:duplicate_requirement_id")
        seen.add(requirement_id)

        if requirement.get("requirement_type") not in requirement_types:
            errors.append(f"{prefix}:requirement_type")
        if requirement.get("owner_role") not in LLM_ROLES:
            errors.append(f"{prefix}:owner_role")
        if not isinstance(requirement.get("blocking"), bool):
            errors.append(f"{prefix}:blocking")
        if not isinstance(requirement.get("verification_allowed"), bool):
            errors.append(f"{prefix}:verification_allowed")
        if not isinstance(requirement.get("change_requires_contract_revision"), bool):
            errors.append(f"{prefix}:change_requires_contract_revision")
        if requirement.get("blocking") is True:
            if not str(requirement.get("source_path", "")).strip():
                errors.append(f"{prefix}:blocking_missing_source_path")
            if not str(requirement.get("source_clause_or_field", "")).strip():
                errors.append(f"{prefix}:blocking_missing_source_clause")
        if requirement.get("numeric_threshold") is not None and requirement.get("blocking") is True:
            if not str(requirement.get("threshold_source", "")).strip():
                errors.append(f"{prefix}:blocking_numeric_threshold_missing_source")

        derived = requirement.get("derived_invariants")
        if not isinstance(derived, list):
            errors.append(f"{prefix}:derived_invariants")
            continue
        for didx, invariant in enumerate(derived):
            iprefix = f"{prefix}:derived[{didx}]"
            if not isinstance(invariant, dict):
                errors.append(f"{iprefix}:not_object")
                continue
            for key in (
                "parent_requirement_ids",
                "logical_derivation",
                "why_necessary",
                "whether_it_changes_scientific_semantics",
            ):
                if key not in invariant:
                    errors.append(f"{iprefix}:missing:{key}")
            parents = invariant.get("parent_requirement_ids")
            if not isinstance(parents, list) or not parents:
                errors.append(f"{iprefix}:parent_requirement_ids")
            elif any(parent not in seen and parent != requirement_id for parent in parents):
                errors.append(f"{iprefix}:unknown_parent_requirement_id")
            if invariant.get("blocking") is True and invariant.get("whether_it_changes_scientific_semantics") is True:
                errors.append(f"{iprefix}:blocking_invariant_changes_science")

    return errors


def validate_verifier_finding(
    finding: dict[str, Any], ledger: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    errors = _missing(finding, ["classification", "blocking", "observed_violation", "verification_method"])
    classifications = _schema_values(schema, "finding_classifications", list(DEFAULT_CLASSIFICATION_ROUTES))
    classification = finding.get("classification")
    if classification not in classifications:
        errors.append("finding:classification")
    if not isinstance(finding.get("blocking"), bool):
        errors.append("finding:blocking")

    requirements = _ledger_requirements(ledger)
    requirement_id = finding.get("requirement_id")
    if finding.get("blocking") is True:
        for key in (
            "requirement_id",
            "contract_source_path",
            "contract_clause_or_field",
            "why_this_test_is_logically_implied_by_requirement",
        ):
            if not str(finding.get(key, "")).strip():
                errors.append(f"verifier_blocking_finding_missing:{key}")
        if requirement_id not in requirements:
            errors.append("verifier_blocking_finding_unknown_requirement_id")
        elif requirements[str(requirement_id)].get("blocking") is not True:
            errors.append("verifier_blocking_finding_nonblocking_requirement")
        if classification == "DIAGNOSTIC_ANOMALY":
            errors.append("verifier_diagnostic_must_not_block")
        if finding.get("numeric_threshold") is not None:
            threshold_source = finding.get("threshold_source") or (
                requirements.get(str(requirement_id), {}).get("threshold_source")
            )
            if not str(threshold_source or "").strip():
                errors.append("verifier_blocking_numeric_threshold_missing_source")
    elif requirement_id and requirement_id not in requirements:
        errors.append("verifier_finding_unknown_requirement_id")

    return errors


def validate_controller_routing_decision(
    decision: dict[str, Any], ledger: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    errors = _missing(decision, ["classification", "route", "target_role_or_state"])
    routes = schema.get("classification_routes")
    if not isinstance(routes, dict):
        routes = DEFAULT_CLASSIFICATION_ROUTES
    classification = decision.get("classification")
    expected_route = routes.get(str(classification))
    if expected_route is None:
        errors.append("routing:classification")
    elif decision.get("route") != expected_route:
        errors.append("routing:route")

    target = decision.get("target_role_or_state")
    if target == "NEEDS_USER_SCIENTIFIC_CHOICE":
        planner = decision.get("planner_adjudication")
        if classification != "SCIENTIFIC_CHOICE_REQUIRED":
            errors.append("human_gate_requires_scientific_choice_classification")
        if not isinstance(planner, dict) or planner.get("classification") != "SCIENTIFIC_CHOICE_REQUIRED":
            errors.append("human_gate_requires_planner_scientific_choice")
        if not decision.get("scientific_contract_fields_requiring_change"):
            errors.append("human_gate_missing_contract_fields_requiring_change")
        alternatives = decision.get("scientific_alternatives")
        if not isinstance(alternatives, list) or len(alternatives) < 2:
            errors.append("human_gate_missing_mutually_exclusive_alternatives")
        citations = decision.get("requirement_ids")
        requirements = _ledger_requirements(ledger)
        if not isinstance(citations, list) or not citations or any(item not in requirements for item in citations):
            errors.append("human_gate_missing_requirement_ids")
        repairs = decision.get("same_scope_repairs_exhausted")
        if not isinstance(repairs, dict) or not all(repairs.get(key) is True for key in (
            "executor_repair",
            "verifier_repair",
            "runtime_repair",
            "transaction_rebind",
        )):
            errors.append("human_gate_same_scope_repairs_not_exhausted")
        if decision.get("caused_by_verifier_added_requirement") is True:
            errors.append("human_gate_cannot_use_verifier_added_requirement")
        if classification in {
            "VERIFIER_CONTRACT_DRIFT",
            "RUNTIME_ENVIRONMENT_FAILURE",
            "OPERATIONAL_FAILURE",
            "PROVENANCE_BINDING_GAP",
            "IMPLEMENTATION_BUG",
            "VERIFIER_BUG",
        }:
            errors.append("human_gate_wrong_failure_class")

    return errors


def validate_executor_result(result: dict[str, Any]) -> list[str]:
    errors = _missing(result, ["status", "test_aware_behavior_detected", "normal_public_path_exercised"])
    if result.get("status") == "PASS" and result.get("test_aware_behavior_detected") is True:
        errors.append("executor_test_aware_pass_forbidden")
    indicators = result.get("test_awareness_indicators", [])
    if result.get("status") == "PASS" and isinstance(indicators, list) and indicators:
        errors.append("executor_test_awareness_indicators_forbid_pass")
    if result.get("status") == "PASS" and result.get("normal_public_path_exercised") is not True:
        errors.append("executor_pass_requires_normal_public_path")
    return errors


def validate_contract_interpretation_review(review: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors = _missing(review, ["schema", "decision", "classification", "requirement_ids", "planner_read_set"])
    allowed = _schema_values(schema, "contract_interpretation_decisions", [])
    if review.get("schema") != "AGENT_FLOW_V3_CONTRACT_INTERPRETATION_REVIEW":
        errors.append("contract_review:schema")
    if review.get("decision") not in allowed:
        errors.append("contract_review:decision")
    if not isinstance(review.get("planner_read_set"), list) or not review.get("planner_read_set"):
        errors.append("contract_review:planner_read_set")
    return errors


def validate_critic_freeze(freeze: dict[str, Any], ledger: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors = _missing(freeze, ["critic_decision", "requirement_ledger_sha256", "contradictions", "numeric_threshold_audit"])
    if freeze.get("critic_decision") == "PLAN_FROZEN":
        contradictions = freeze.get("contradictions")
        if isinstance(contradictions, list) and contradictions:
            errors.append("critic_freeze_has_contradictory_requirements")
        if validate_requirement_ledger(ledger, schema):
            errors.append("critic_freeze_invalid_requirement_ledger")
        audit = freeze.get("numeric_threshold_audit")
        if not isinstance(audit, list):
            errors.append("critic_freeze:numeric_threshold_audit")
        else:
            for idx, row in enumerate(audit):
                if not isinstance(row, dict):
                    errors.append(f"critic_freeze:numeric_threshold_audit[{idx}]")
                    continue
                if row.get("blocking") is True and not str(row.get("threshold_source", "")).strip():
                    errors.append(f"critic_freeze:numeric_threshold_audit[{idx}]:missing_source")
    return errors


def validate_transaction_binding(transaction: dict[str, Any]) -> list[str]:
    errors = _missing(
        transaction,
        [
            "request_nonce",
            "frozen_contract_sha",
            "requirement_ledger_sha",
            "integration_sha",
            "implementation_fingerprint",
            "verifier_source_fingerprint",
            "verifier_runtime_fingerprint",
            "runtime_receipt_manifest_sha",
            "ci_exact_head_sha",
            "review_round",
            "classification_on_failure",
            "route_on_failure",
        ],
    )
    if transaction.get("ci_exact_head_sha") != transaction.get("integration_sha"):
        if transaction.get("classification_on_failure") != "PROVENANCE_BINDING_GAP":
            errors.append("transaction_stale_ci_must_be_provenance_gap")
        if transaction.get("route_on_failure") != "controller":
            errors.append("transaction_stale_ci_must_route_controller")
    sha_fields = [
        ("frozen_contract_sha", SHA256_RE),
        ("requirement_ledger_sha", SHA256_RE),
        ("integration_sha", SHA40_RE),
        ("implementation_fingerprint", SHA256_RE),
        ("verifier_source_fingerprint", SHA256_RE),
        ("verifier_runtime_fingerprint", SHA256_RE),
        ("runtime_receipt_manifest_sha", SHA256_RE),
        ("ci_exact_head_sha", SHA40_RE),
    ]
    for field, pattern in sha_fields:
        value = transaction.get(field)
        if value is not None and not pattern.fullmatch(str(value)):
            errors.append(f"transaction:{field}")
    return errors


def validate_role_authority_event(event: dict[str, Any]) -> list[str]:
    errors = _missing(event, ["role", "attempted_authority"])
    role = event.get("role")
    authority = event.get("attempted_authority")
    forbidden = {
        "controller": {"scientific_interpretation", "implementation_edit", "verifier_oracle_edit"},
        "verifier": {"scientific_requirement_creation", "implementation_edit"},
        "executor": {"verifier_edit", "contract_edit"},
        "planner": {"implementation_edit", "runtime_implementation"},
        "critic": {"implementation_edit", "runtime_implementation"},
    }
    if role not in LLM_ROLES:
        errors.append("authority:role")
    elif authority in forbidden.get(str(role), set()):
        errors.append(f"authority_violation:{role}:{authority}")
    return errors


def validate_fail_closed_routing(receipt: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if receipt.get("status") == "BLOCKED" and "classification" not in receipt:
        errors.append("generic_blocked_missing_classification")
    if receipt.get("status") == "FAIL_CLOSED" and not receipt.get("repair_route"):
        errors.append("fail_closed_missing_repair_route")
    if "classification" in receipt:
        classifications = _schema_values(schema, "finding_classifications", list(DEFAULT_CLASSIFICATION_ROUTES))
        if receipt.get("classification") not in classifications:
            errors.append("receipt:classification")
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
            ledger_path = task_dir / "REQUIREMENT_LEDGER.json"
            if ledger_path.exists():
                ledger = load_json(ledger_path)
                failures.extend(
                    f"{ledger_path}:{error}"
                    for error in validate_requirement_ledger(ledger, schema)
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
