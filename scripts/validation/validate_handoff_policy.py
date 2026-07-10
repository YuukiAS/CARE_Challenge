#!/usr/bin/env python3
"""Validate CARE handoff route, publication, and scientific-status policy."""

from __future__ import annotations

import argparse
import ast
import csv
import json
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Iterable, Sequence


FORBIDDEN_PUBLICATION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(^|/)checkpoints?(/|$)",
        r"checkpoint_.*\.(pth|pt|ckpt)$",
        r"\.(pth|pt|ckpt)$",
        r"(^|/)predictions?(/|$)",
        r"\.nii(\.gz)?$",
        r"\.zip$",
        r"(^|/)upload_ready(/|$)",
        r"validation[_-]?package",
        r"hosted[_-]?validation",
        r"(^|/)logs?(/|$)",
        r"\.log$",
        r"transcript",
        r"environment[_-]?dump",
        r"\.env($|[./])",
        r"credential",
        r"secret",
        r"\.csv$",
    ]
]

REPORT_REQUIRED_FIELDS = [
    "controller_run_status",
    "operational_completion_status",
    "experiment_adequacy_decision",
    "route_promotion_decision",
    "route_negative_decision",
    "scientific_resolution_status",
    "diagnostic_publication_decision",
    "git_commit_decision",
    "git_push_decision",
    "published_files",
    "blocked_actions",
    "next_required_action",
    "reason_if_not_published",
    "reason_if_no_route_promotion",
]

DIAGNOSTIC_ONLY_PHRASE = "diagnostic publication only; no route promotion"
ROUTE_NEGATIVE_RE = re.compile(r"\bSTOP_NO_[A-Z0-9_]+\b|\b[A-Z0-9_]*NO_SIGNAL\b")
TRAINING_EVIDENCE_FIELDS = [
    "actual_steps",
    "train_loop_seconds",
    "loss_decrease",
    "prediction_sanity",
]
MONITOR_STATE_RE = re.compile(
    r"\b(NEEDS_MONITOR|PENDING_MONITOR|JOB_SUBMITTED|PENDING_PRIORITY|PENDING|RUNNING|AWAITING_SACCT|CONFIGURING|COMPLETING)\b",
    re.IGNORECASE,
)
FORBIDDEN_MAPPER_SCAN_RE = re.compile(
    r"mapper.*(raw data|NIfTI|\.nii(\.gz)?|checkpoint|\.pt|\.pth|large log|secret|credential|upload package)",
    re.IGNORECASE,
)
STALE_INSTALL_REPORT_RE = re.compile(r"docs/local_install_report\.md", re.IGNORECASE)
LONG_TASK_RE = re.compile(
    r"\b(overnight|long[ -]?slurm|multi[ -]?job|high[ -]?resume[ -]?risk|slurm_runtime_continuity_required\s*:\s*true)\b",
    re.IGNORECASE,
)
ARCHITECTURE_IMPACT_RE = re.compile(r"architecture_impact\s*:\s*[\"']?(component|system)[\"']?", re.IGNORECASE)
V2_FRONTMATTER_FIELDS = [
    "execution_mode",
    "requires_execution_controller",
    "executor_slots",
    "executor_count",
    "parallel_execution_allowed",
    "executor_plan_path",
    "mapper_slots",
    "mapper_required",
    "architecture_impact",
    "wiki_update_required",
    "diagram_update_required",
    "slurm_runtime_continuity_required",
    "continuity_backend",
    "review_mode",
    "reviewer",
]
COMPONENT_REQUIRED_COLUMNS = [
    "component_id",
    "branch",
    "role",
    "current_status",
    "evidence_status",
    "target_status",
    "source_file",
    "symbol",
    "entrypoint",
    "grep_key",
    "config_keys",
    "inputs",
    "outputs",
    "losses",
    "final_output_effect",
    "runtime_evidence",
    "code_fingerprint_member",
    "last_verified_milestone",
    "review_token",
    "notes",
]
ACTIVE_DOC_BASENAMES = {
    "AGENTS.md",
    "START_HERE_FOR_GPT.md",
    "GPT_PLANNER_CARE_PROTOCOL.md",
    "AGENT_FLOW_V2_PROTOCOL.md",
    "HANDOFF_ROLES.md",
    "HANDOFF_STATE_MACHINE.md",
    "CONTROLLER_TASK_PROTOCOL.md",
    "HANDOFF_GATE_POLICY.md",
    "GPT_HARD_GATE_PROMPT.md",
    "MILESTONE_REVIEW_PROTOCOL.md",
    "CONTROLLER_TASK_TEMPLATE.md",
}
PUSH_TRUE_RE = re.compile(r"(?m)^\s*(auto_git_push|allow_git_push|allow_diagnostic_push)\s*:\s*true\s*$", re.IGNORECASE)
TODO_RUNTIME_RE = re.compile(r"\bTODO-agents(?:-v2)?\.md\b")
HISTORY_READ_FILES = [
    "wiki/history/COMPARISON.md",
    "wiki/history/M08/README.md",
    "wiki/history/M09/README.md",
    "wiki/history/M09/COMPONENTS.csv",
]


@dataclass(frozen=True)
class Finding:
    severity: str
    path: Path
    message: str


def parse_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    block = text[4:end]
    values: dict[str, object] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not raw_value:
            values[key] = ""
            continue
        lower_value = raw_value.lower()
        if lower_value == "true":
            values[key] = True
        elif lower_value == "false":
            values[key] = False
        elif raw_value.startswith("[") and raw_value.endswith("]"):
            try:
                values[key] = ast.literal_eval(raw_value)
            except (SyntaxError, ValueError):
                values[key] = raw_value
        else:
            values[key] = raw_value.strip("\"'")
    return values


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False


def is_controller_task(frontmatter: dict[str, object], text: str) -> bool:
    return (
        frontmatter.get("task_type") == "controller"
        or as_bool(frontmatter.get("controller_mode"))
        or "controller_report_path" in frontmatter
        or "# CARE Controller Task:" in text
    )


def is_execution_task(frontmatter: dict[str, object]) -> bool:
    return frontmatter.get("task_type") in ("execution", None) and not as_bool(
        frontmatter.get("controller_mode")
    )


def has_any_git_permission(frontmatter: dict[str, object]) -> bool:
    return as_bool(frontmatter.get("allow_git_commit")) or as_bool(
        frontmatter.get("allow_git_push")
    )


def is_model_training_task(frontmatter: dict[str, object], text: str) -> bool:
    mechanism = str(frontmatter.get("mechanism_class", "")).lower()
    haystack = f"{mechanism}\n{text[:1200].lower()}"
    return any(
        token in haystack
        for token in (
            "segmentation",
            "training",
            "train",
            "proposal",
            "refinement",
            "cascade",
            "missing_modality",
            "cine_temporal",
            "external_adapter",
        )
    )


def is_truthy_field(frontmatter: dict[str, object], key: str) -> bool:
    return as_bool(frontmatter.get(key))


def is_blank_or_none(value: object) -> bool:
    if value is None:
        return True
    return str(value).strip().strip("\"'").lower() in {"", "none", "null"}


def as_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip().strip("\"'"))
    except (TypeError, ValueError):
        return default


def severity(strict: bool) -> str:
    return "error" if strict else "warning"


def validate_task_file(path: Path, text: str, strict: bool) -> list[Finding]:
    frontmatter = parse_frontmatter(text)
    findings: list[Finding] = []
    if not frontmatter:
        return findings

    execution_mode = str(frontmatter.get("execution_mode", "")).strip("\"'")
    continuity_backend = str(frontmatter.get("continuity_backend", "")).strip("\"'")

    if is_controller_task(frontmatter, text):
        missing_v2 = [field for field in V2_FRONTMATTER_FIELDS if field not in frontmatter]
        if missing_v2:
            findings.append(
                Finding(
                    severity(strict),
                    path,
                    "controller task is missing agent-flow v2 fields: "
                    + ", ".join(missing_v2)
                    + ".",
                )
            )
        if as_bool(frontmatter.get("auto_git_push")) or as_bool(frontmatter.get("allow_git_push")) or as_bool(frontmatter.get("allow_diagnostic_push")):
            findings.append(
                Finding(
                    severity(strict),
                    path,
                    "new controller tasks must not enable auto_git_push, allow_git_push, or allow_diagnostic_push; user pushes manually.",
                )
            )
        if "reviewer_review" in text:
            findings.append(
                Finding(
                    severity(strict),
                    path,
                    "controller task must not require reviewer_review before controller local packet commit.",
                )
            )
        executor_slots = as_int(frontmatter.get("executor_slots"), 0)
        executor_count = as_int(frontmatter.get("executor_count"), 0)
        if executor_slots < 1:
            findings.append(Finding(severity(strict), path, "executor_slots must be a positive integer."))
        if executor_count < 1:
            findings.append(Finding(severity(strict), path, "executor_count must be a positive integer."))
        parallel_allowed = as_bool(frontmatter.get("parallel_execution_allowed"))
        if (executor_slots > 1 or executor_count > 1 or parallel_allowed) and is_blank_or_none(frontmatter.get("executor_plan_path")):
            findings.append(
                Finding(
                    severity(strict),
                    path,
                    "parallel/multi-executor controller task must declare executor_plan_path.",
                )
            )

    if LONG_TASK_RE.search(text) and execution_mode == "direct_executor":
        findings.append(
            Finding(
                severity(strict),
                path,
                "overnight/long-Slurm/multi-job/high-resume-risk task cannot use execution_mode: direct_executor.",
            )
        )

    if is_truthy_field(frontmatter, "slurm_runtime_continuity_required") and (
        is_blank_or_none(continuity_backend) or continuity_backend == "none"
    ):
        findings.append(
            Finding(
                severity(strict),
                path,
                "slurm_runtime_continuity_required task must set continuity_backend to slurm_dependency or tmux_watcher.",
            )
        )

    if is_truthy_field(frontmatter, "slurm_runtime_continuity_required") and "finalizer_state.json" not in text:
        findings.append(
            Finding(
                severity(strict),
                path,
                "long Slurm/controller task declares continuity but lacks finalizer_state.json durable finalizer evidence contract.",
            )
        )

    if LONG_TASK_RE.search(text) and "## Controller Prompt" not in text and path.name.startswith("M"):
        findings.append(
            Finding(
                severity(strict),
                path,
                "long/overnight staging prompt must include ## Controller Prompt.",
            )
        )
    if LONG_TASK_RE.search(text) and "durable finalizer" not in text.lower() and path.name.startswith("M"):
        findings.append(
            Finding(
                severity(strict),
                path,
                "long/overnight staging prompt must include a durable finalizer contract.",
            )
        )

    if "auditor_subtasks" in frontmatter or re.search(r"(?m)^\s*auditor_subtasks\s*:", text):
        findings.append(
            Finding(
                severity(strict),
                path,
                "new controller tasks must not use auditor_subtasks; use mapper_subtasks and reviewer_prompt_path.",
            )
        )

    if ARCHITECTURE_IMPACT_RE.search(text):
        if not is_truthy_field(frontmatter, "mapper_required"):
            findings.append(
                Finding(
                    severity(strict),
                    path,
                    "architecture_impact component/system requires mapper_required: true.",
                )
            )
        if "system" in text.lower() or path.name.lower().startswith("m10") or "m10" in path.name.lower():
            missing_history = [item for item in HISTORY_READ_FILES if item not in text]
            if "wiki/history/M09/components/" not in text and "wiki/history/M09/components/*.md" not in text:
                missing_history.append("wiki/history/M09/components/*.md")
            if missing_history:
                findings.append(
                    Finding(
                        severity(strict),
                        path,
                        "M10/system-level milestone must list history_files_read including: "
                        + ", ".join(missing_history),
                    )
                )
        if not is_truthy_field(frontmatter, "wiki_update_required"):
            findings.append(
                Finding(
                    severity(strict),
                    path,
                    "architecture_impact component/system requires wiki_update_required: true or an explicit no-change fingerprint receipt.",
                )
            )

    if is_controller_task(frontmatter, text) and has_any_git_permission(frontmatter):
        missing = [
            field
            for field in (
                "route_promotion_gate",
                "experiment_adequacy_gate",
                "route_negative_gate",
                "scientific_completion_gate",
                "diagnostic_publication_gate",
                "diagnostic_publication_scope",
                "blocked_after_diagnostic_publication",
            )
            if not frontmatter.get(field)
        ]
        if missing:
            legacy_note = ""
            if frontmatter.get("promotion_gate") and "route_promotion_gate" in missing:
                legacy_note = " Legacy promotion_gate is compatible but should be split."
            findings.append(
                Finding(
                    severity(strict),
                    path,
                    "controller task with git permission is missing explicit "
                    + ", ".join(missing)
                    + "."
                    + legacy_note,
                )
            )

    risk_level = str(frontmatter.get("risk_level", "")).lower()
    if (
        risk_level in {"medium", "high"}
        and is_model_training_task(frontmatter, text)
        and (
            frontmatter.get("task_type") in {"execution", "controller"}
            or as_bool(frontmatter.get("controller_mode"))
        )
    ):
        missing_model_fields = [
            field
            for field in (
                "experiment_adequacy_gate",
                "route_negative_gate",
                "scientific_completion_gate",
            )
            if not frontmatter.get(field)
        ]
        if "minimum_effective_training" not in text:
            missing_model_fields.append("minimum_effective_training")
        if missing_model_fields:
            findings.append(
                Finding(
                    severity(strict),
                    path,
                    "medium/high-risk model task is missing explicit "
                    + ", ".join(missing_model_fields)
                    + ". Legacy tasks default to not supporting route-negative stops.",
                )
            )

    if (
        is_execution_task(frontmatter)
        and risk_level in {"medium", "high"}
        and has_any_git_permission(frontmatter)
    ):
        if not as_bool(frontmatter.get("review_required")):
            findings.append(
                Finding(
                    severity(strict),
                    path,
                    "medium/high-risk executor task allows git without review_required: true.",
                )
            )
        if "audit" not in text.lower() and "review" not in text.lower():
            findings.append(
                Finding(
                    severity(strict),
                    path,
                    "medium/high-risk executor task allows git without explicit audit/review text.",
                )
            )

    return findings


def extract_published_files(text: str) -> list[str]:
    files: list[str] = []
    in_block = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if re.match(r"^published_files\s*:", stripped):
            in_block = True
            after = stripped.split(":", 1)[1].strip()
            if after and after not in {"[]", "none"}:
                files.append(after.strip("- `"))
            continue
        if in_block:
            if not stripped:
                continue
            if re.match(r"^[A-Za-z_][A-Za-z0-9_ -]*\s*:", stripped):
                break
            if stripped.startswith("-"):
                files.append(stripped[1:].strip().strip("`"))
            elif raw_line.startswith((" ", "\t")):
                files.append(stripped.strip("`"))
            else:
                break
    return [item for item in files if item and item.lower() != "none"]


def field_value(text: str, field: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(field)}[ \t]*:[ \t]*(.*)$", text)
    if not match:
        return None
    return match.group(1).strip()


def field_nonempty(text: str, field: str) -> bool:
    value = field_value(text, field)
    return value is not None and value.strip().lower() not in {"", "none", "..."}


def has_route_negative_conclusion(text: str) -> bool:
    return bool(ROUTE_NEGATIVE_RE.search(text)) or bool(
        re.search(r"(?m)^route_negative_decision\s*:\s*STOP_SUPPORTED\s*$", text)
    ) or bool(
        re.search(
            r"(?m)^scientific_resolution_status\s*:\s*SCIENTIFIC_STOP_SUPPORTED\s*$",
            text,
        )
    )


def has_forbidden_publication_path(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/")
    return any(pattern.search(normalized) for pattern in FORBIDDEN_PUBLICATION_PATTERNS)


def validate_controller_report(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    lower_text = text.lower()
    if path.name != "controller_report.md":
        return findings

    if "review.md" in text and re.search(r"(?i)controller.*wrote|wrote.*review\.md|AUDITED_GO", text):
        findings.append(
            Finding(
                "error",
                path,
                "controller report appears to write review.md or audited-go; final review must be separate.",
            )
        )

    if field_value(text, "controller_run_status") == "COMPLETE" and MONITOR_STATE_RE.search(text):
        findings.append(
            Finding(
                "error",
                path,
                "COMPLETE controller report contains unresolved monitor/pending state.",
            )
        )

    if field_value(text, "controller_run_status") == "BLOCKED" and MONITOR_STATE_RE.search(text):
        findings.append(
            Finding(
                "error",
                path,
                "controller report maps pending/running monitor state to BLOCKED.",
            )
        )

    if (
        re.search(r"(?i)scheduler[ -]?block|scheduler saturation|controller_run_status\s*:\s*BLOCKED", text)
        and MONITOR_STATE_RE.search(text)
        and not re.search(r"12 consecutive 2-hour|24-hour|24 hours|12\s+consecutive", text, re.IGNORECASE)
    ):
        findings.append(
            Finding(
                "error",
                path,
                "scheduler block from pending/running states requires the Slurm skill 12 consecutive 2-hour / 24-hour threshold evidence.",
            )
        )

    if re.search(r"(?i)outputs? missing|runtime output.*missing|NEEDS_EVIDENCE", text) and re.search(
        r"(?i)\bRUNNING\b|job.*still.*running", text
    ):
        findings.append(
            Finding(
                "error",
                path,
                "running jobs cannot be closed as output-missing completion; use NEEDS_MONITOR.",
            )
        )

    if "controller_supervised" in text and "controller_context.json" not in text:
        findings.append(
            Finding(
                "error",
                path,
                "controller_supervised report must reference fresh controller_context.json receipts.",
            )
        )

    if re.search(r"(?i)executor_slots(_allowed)?\s*:\s*1", text) and re.search(
        r"(?i)(launched_executor_count|executor_sessions|actual_executor_slots)\s*:\s*[2-9]", text
    ):
        findings.append(Finding("error", path, "controller exceeded GPT-authored executor_slots."))

    if re.search(r"(?i)mapper_slots(_allowed)?\s*:\s*1", text) and re.search(
        r"(?i)(launched_mapper_count|mapper_sessions|actual_mapper_slots)\s*:\s*[2-9]", text
    ):
        findings.append(Finding("error", path, "controller exceeded GPT-authored mapper_slots."))

    if re.search(r"(?i)reviewer.*(internal|subagent|resume|monitor|controller child)", text):
        findings.append(Finding("error", path, "controller treats reviewer as an internal recovery/subagent role."))

    if FORBIDDEN_MAPPER_SCAN_RE.search(text):
        findings.append(Finding("error", path, "mapper scanned forbidden raw/heavy/secret/upload artifacts."))

    if STALE_INSTALL_REPORT_RE.search(text):
        findings.append(Finding("error", path, "controller/mapper must not rely on stale Toolkit docs/local_install_report.md."))

    if re.search(r"(?i)chat/user statement.*finished|from chat.*follow-up.*complete|claimed.*from chat", text) and not re.search(
        r"(?i)committed.*review|committed.*evidence|review\.md", text
    ):
        findings.append(Finding("error", path, "planner/mapper cannot claim follow-up completion from chat without committed evidence/review."))

    for field in REPORT_REQUIRED_FIELDS:
        if not re.search(rf"(?m)^{re.escape(field)}\s*:", text):
            findings.append(Finding("error", path, f"controller report missing {field}."))

    git_push = field_value(text, "git_push_decision")
    if git_push and git_push != "SKIP_PUSH":
        findings.append(Finding("error", path, "controller report must not push; user pushes manually."))

    if (
        field_value(text, "route_promotion_decision") not in {None, "NOT_REVIEWED"}
        and re.search(r"(?i)awaiting independent review|before reviewer|pre[- ]review", text)
    ):
        findings.append(Finding("error", path, "pre-review controller report must use route_promotion_decision: NOT_REVIEWED."))

    if has_route_negative_conclusion(text):
        if field_value(text, "experiment_adequacy_decision") != "PASS":
            findings.append(
                Finding(
                    "error",
                    path,
                    "route-negative conclusion requires experiment_adequacy_decision: PASS.",
                )
            )
        if field_value(text, "route_negative_decision") != "STOP_SUPPORTED":
            findings.append(
                Finding(
                    "error",
                    path,
                    "STOP_NO_* or scientific stop requires route_negative_decision: STOP_SUPPORTED.",
                )
            )

    if (
        field_value(text, "controller_run_status") == "COMPLETE"
        and field_value(text, "scientific_resolution_status") == "SCIENTIFIC_UNRESOLVED"
        and not field_nonempty(text, "next_required_action")
    ):
        findings.append(
            Finding(
                "error",
                path,
                "COMPLETE controller with SCIENTIFIC_UNRESOLVED must state next_required_action.",
            )
        )

    no_promotion = re.search(r"route_promotion_decision\s*:\s*NO_PROMOTION", text)
    diagnostic_commit = re.search(
        r"git_commit_decision\s*:\s*(COMMIT_DIAGNOSTIC_ONLY|COMMIT_[A-Z_]*DIAGNOSTIC[A-Z_]*)",
        text,
    )
    diagnostic_push = re.search(
        r"git_push_decision\s*:\s*(PUSH_DIAGNOSTIC_ONLY|PUSH_[A-Z_]*DIAGNOSTIC[A-Z_]*)",
        text,
    )
    any_commit_or_push = diagnostic_commit or diagnostic_push or re.search(
        r"(commit_executed|push_executed)\s*:\s*true", lower_text
    )

    if no_promotion and any_commit_or_push:
        if not re.search(
            r"diagnostic_publication_decision\s*:\s*PUBLISH_REVIEWED_DIAGNOSTIC_PACKET",
            text,
        ):
            findings.append(
                Finding(
                    "error",
                    path,
                    "no-promotion report with commit/push must publish through diagnostic_publication_decision.",
                )
            )
        if DIAGNOSTIC_ONLY_PHRASE not in lower_text:
            findings.append(
                Finding(
                    "error",
                    path,
                    f"diagnostic-only commit/push must state `{DIAGNOSTIC_ONLY_PHRASE}`.",
                )
            )
        if not extract_published_files(text):
            findings.append(
                Finding(
                    "error",
                    path,
                    "no-promotion report with commit/push must list published_files.",
                )
            )

    for published in extract_published_files(text):
        if has_forbidden_publication_path(published):
            findings.append(
                Finding(
                    "error",
                    path,
                    f"published_files contains forbidden diagnostic artifact path: {published}",
                )
            )

    return findings


def validate_review_file(path: Path, text: str) -> list[Finding]:
    if path.name != "review.md":
        return []
    findings: list[Finding] = []
    if "AUDITED_GO" in text and MONITOR_STATE_RE.search(text):
        findings.append(
            Finding(
                "error",
                path,
                "review cannot grant audited-go while monitor/pending states remain.",
            )
        )
    if "AUDITED_GO" in text and re.search(r"(?i)missing.*wiki|missing.*COMPONENTS|missing.*PNG|missing.*architecture_delta", text):
        findings.append(Finding("error", path, "review cannot grant audited-go when architecture wiki/diagram evidence is missing."))
    if "AUDITED_GO" in text and re.search(r"(?i)long[ -]?slurm|overnight|multi[ -]?job", text) and "direct_executor" in text:
        findings.append(
            Finding(
                "error",
                path,
                "review cannot grant audited-go to long/overnight Slurm packet executed as direct_executor.",
            )
        )
    route_negative_supported = (
        field_value(text, "route_negative_decision") == "STOP_SUPPORTED"
        or field_value(text, "scientific_resolution_status") == "SCIENTIFIC_STOP_SUPPORTED"
        or ("AUDITED_GO" in text and has_route_negative_conclusion(text))
    )
    if not route_negative_supported:
        return findings
    if field_value(text, "experiment_adequacy_decision") != "PASS":
        findings.append(
            Finding(
                "error",
                path,
                "review cannot support route-negative stop without experiment_adequacy_decision: PASS.",
            )
        )
    missing = [field for field in TRAINING_EVIDENCE_FIELDS if field not in text]
    if missing:
        findings.append(
            Finding(
                "error",
                path,
                "review supports route-negative stop but lacks training adequacy fields: "
                + ", ".join(missing)
                + ".",
            )
        )
    return findings


def validate_active_policy_doc(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    if path.name in ACTIVE_DOC_BASENAMES:
        if TODO_RUNTIME_RE.search(text) and not re.search(r"(?i)retired|legacy|must not be used", text):
            findings.append(
                Finding(
                    "error",
                    path,
                    "active runtime policy references retired TODO-agents/TODO-agents-v2.md; use prompts/AGENT_FLOW_V2_PROTOCOL.md.",
                )
            )
        if re.search(r"(?i)controller\s+(launches|starts|creates|uses)\s+(an\s+)?internal auditor|auditor_subtasks", text) and not re.search(r"(?i)must not.*internal auditor|do not create.*internal auditor", text):
            findings.append(Finding("error", path, "active policy still describes controller-internal auditor behavior."))
        if re.search(r"(?i)controller.*(decide|decides|decision).*route promotion", text) and "NOT_REVIEWED" not in text:
            findings.append(Finding("error", path, "active policy lets controller decide route promotion before reviewer."))
        if "reviewer_review" in text and not re.search(r"(?i)must not require `?reviewer_review`?|without reviewer_review|requires `?reviewer_review`?.*failure", text):
            findings.append(Finding("error", path, "active policy requires reviewer_review before controller commit."))
        if PUSH_TRUE_RE.search(text):
            findings.append(Finding("error", path, "active policy enables controller/reviewer push; user pushes manually."))
    if path.name in {"EXECUTOR_PROMPTS.md", "REVIEWER_PROMPTS.md"}:
        head = "\n".join(text.splitlines()[:220])
        if TODO_RUNTIME_RE.search(head):
            findings.append(Finding("error", path, "shared global rule section references retired TODO-agents files."))
        if PUSH_TRUE_RE.search(head):
            findings.append(Finding("error", path, "shared global rule section enables push."))
    return findings


def validate_finalizer_state(path: Path, text: str) -> list[Finding]:
    if path.name != "finalizer_state.json":
        return []
    findings: list[Finding] = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [Finding("error", path, f"finalizer_state.json is not valid JSON: {exc}")]
    required = [
        "task_key",
        "required_job_ids",
        "job_states",
        "exit_codes",
        "elapsed",
        "log_paths",
        "runtime_output_paths",
        "aggregation_command",
        "aggregation_exit_code",
        "validator_commands",
        "validator_exit_codes",
        "mapper_final_status",
        "lock_path",
        "git_head_before",
        "git_commit_after",
        "final_state",
    ]
    missing = [field for field in required if field not in data]
    if missing:
        findings.append(Finding("error", path, "finalizer_state.json missing fields: " + ", ".join(missing)))
    states = {str(value).upper() for value in dict(data.get("job_states", {})).values()}
    final_state = str(data.get("final_state", "")).upper()
    if states & {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING", "AWAITING_SACCT"} and final_state not in {"NEEDS_MONITOR"}:
        findings.append(Finding("error", path, "nonterminal Slurm states must map to NEEDS_MONITOR."))
    if final_state in {"PACKET_COMMITTED_FOR_REVIEW", "READY_FOR_LOCAL_PACKET_COMMIT"} and states & {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING", "AWAITING_SACCT"}:
        findings.append(Finding("error", path, "completion finalizer_state contains nonterminal Slurm state."))
    return findings


def validate_components_csv(path: Path, text: str) -> list[Finding]:
    if path.name != "COMPONENTS.csv":
        return []
    findings: list[Finding] = []
    rows = list(csv.DictReader(text.splitlines()))
    columns = rows[0].keys() if rows else []
    missing = [column for column in COMPONENT_REQUIRED_COLUMNS if column not in columns]
    if missing:
        findings.append(Finding("error", path, "COMPONENTS.csv missing columns: " + ", ".join(missing) + "."))
        return findings
    for index, row in enumerate(rows, start=2):
        if row.get("evidence_status") == "verified" and not row.get("runtime_evidence", "").strip():
            findings.append(Finding("error", path, f"row {index} is verified without runtime_evidence."))
        if row.get("current_status") == "implemented" and not row.get("source_file", "").strip():
            findings.append(Finding("error", path, f"row {index} is implemented without source_file."))
        if row.get("evidence_status") == "verified" and not row.get("final_output_effect", "").strip():
            findings.append(Finding("error", path, f"row {index} is verified without final_output_effect."))
        if row.get("current_status") == "implemented":
            row_text = " ".join(str(value) for value in row.values()).lower()
            if "scaffold" in row_text:
                findings.append(Finding("error", path, f"row {index} marks scaffold as implemented."))
    return findings


def validate_architecture_yaml(path: Path, text: str) -> list[Finding]:
    if path.name != "architecture.yaml":
        return []
    findings: list[Finding] = []
    for token in ("architecture_version:", "review_token:", "code_fingerprint:", "nodes:", "edges:"):
        if token not in text:
            findings.append(Finding("error", path, f"architecture.yaml missing {token}"))
    if re.search(r"(?i)fingerprint_?(status)?:\s*(mismatch|different|changed)", text) and "stale" not in text.lower():
        findings.append(Finding("error", path, "architecture fingerprint mismatch must mark wiki stale."))
    return findings


def iter_policy_files(paths: Sequence[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_dir():
            for suffix in ("*.md", "*.csv", "*.yaml", "*.yml", "*.json"):
                yield from sorted(path.rglob(suffix))
        elif path.suffix in {".md", ".csv", ".yaml", ".yml", ".json"}:
            yield path


def validate_paths(paths: Sequence[Path], strict_tasks: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_policy_files(paths):
        text = path.read_text(encoding="utf-8")
        findings.extend(validate_active_policy_doc(path, text))
        findings.extend(validate_finalizer_state(path, text))
        if path.suffix == ".md":
            findings.extend(validate_task_file(path, text, strict=strict_tasks))
            findings.extend(validate_controller_report(path, text))
            findings.extend(validate_review_file(path, text))
        elif path.name == "COMPONENTS.csv":
            findings.extend(validate_components_csv(path, text))
        elif path.name == "architecture.yaml":
            findings.extend(validate_architecture_yaml(path, text))
    return findings


def default_paths(repo_root: Path) -> list[Path]:
    return [
        repo_root / "AGENTS.md",
        repo_root / "START_HERE_FOR_GPT.md",
        repo_root / "GPT_PLANNER_CARE_PROTOCOL.md",
        repo_root / "prompts" / "AGENT_FLOW_V2_PROTOCOL.md",
        repo_root / "prompts" / "HANDOFF_ROLES.md",
        repo_root / "prompts" / "HANDOFF_STATE_MACHINE.md",
        repo_root / "prompts" / "CONTROLLER_TASK_PROTOCOL.md",
        repo_root / "prompts" / "HANDOFF_GATE_POLICY.md",
        repo_root / "prompts" / "GPT_HARD_GATE_PROMPT.md",
        repo_root / "prompts" / "MILESTONE_REVIEW_PROTOCOL.md",
        repo_root / "prompts" / "templates",
        repo_root / "prompts" / "shared" / "EXECUTOR_PROMPTS.md",
        repo_root / "prompts" / "shared" / "REVIEWER_PROMPTS.md",
        repo_root / "wiki",
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Markdown files or directories to validate.")
    parser.add_argument(
        "--strict-tasks",
        action="store_true",
        help="Treat legacy task frontmatter omissions as errors instead of warnings.",
    )
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Return non-zero when warnings are present.",
    )
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    paths = args.paths or default_paths(repo_root)
    findings = validate_paths(paths, strict_tasks=args.strict_tasks)

    for item in findings:
        print(f"{item.severity}: {item.path}: {item.message}")

    has_errors = any(item.severity == "error" for item in findings)
    has_warnings = any(item.severity == "warning" for item in findings)
    if has_errors or (args.warnings_as_errors and has_warnings):
        return 1
    print("handoff policy validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
