#!/usr/bin/env python3
"""Validate CARE handoff route, publication, and scientific-status policy."""

from __future__ import annotations

import argparse
import ast
import csv
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
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
MILESTONE_STAGING_REQUIRED_FIELDS = [
    "task_key",
    "task_type",
    "controller_mode",
    "milestone",
    "status",
    "risk_level",
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
    "review_required",
    "allow_git_commit",
    "auto_git_commit",
    "allow_git_push",
    "auto_git_push",
    "allow_diagnostic_push",
    "route_promotion_gate",
    "experiment_adequacy_gate",
    "route_negative_gate",
    "scientific_completion_gate",
    "diagnostic_publication_gate",
    "diagnostic_publication_scope",
    "blocked_after_diagnostic_publication",
    "planning_review_required",
    "planning_reviewer",
    "planning_review_path",
    "planning_review_token",
    "planning_reviewed_commit",
]
PLANNING_REVIEW_BLOCKED_STATUSES = {
    "DRAFT_FOR_GPT_REVIEW",
    "DRAFT_FOR_PLANNING_REVIEW",
    "PLANNING_REVIEW_RUNNING",
    "NEEDS_PLANNING_REVISION",
    "BLOCKED_HANDOFF_REVIEW",
}
PLANNING_REVIEW_READY_STATUSES = {"READY", "READY_FOR_CODEX_MERGE"}
PLAN_READY_TOKENS = {
    "READY_FOR_MERGE",
    "READY_FOR_CONTROLLER_MERGE",
    "PACKET_COMMITTED_FOR_CONTROLLER",
}
BAD_PLANNING_REVIEWER_RE = re.compile(
    r"\b(controller|executor|mapper|finalizer|validator|runtime|subagent|internal)\b",
    re.IGNORECASE,
)
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


@dataclass(frozen=True)
class Finding:
    severity: str
    path: Path
    message: str


def load_yaml_file(path: Path) -> dict[str, object]:
    try:
        import yaml  # type: ignore
    except ImportError:
        # Narrow fallback for flat/list-heavy policy files used in this repo.
        data: dict[str, object] = {}
        current_key: str | None = None
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if not line.startswith(" ") and ":" in line:
                key, value = line.split(":", 1)
                current_key = key.strip()
                value = value.strip()
                data[current_key] = [] if not value else value.strip("\"'")
            elif current_key and line.strip().startswith("- "):
                value = line.strip()[2:].strip().strip("\"'")
                if not isinstance(data.get(current_key), list):
                    data[current_key] = []
                data[current_key].append(value)  # type: ignore[union-attr]
        return data
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def schema_path(repo_root: Path, name: str) -> Path:
    return repo_root / "prompts" / "schemas" / name


def load_schema(repo_root: Path, name: str) -> dict[str, object]:
    path = schema_path(repo_root, name)
    if not path.is_file():
        return {}
    return load_yaml_file(path)


def list_value(data: dict[str, object], key: str, default: Sequence[str] = ()) -> list[str]:
    value = data.get(key)
    if isinstance(value, list):
        return [str(item) for item in value]
    return list(default)


def milestone_staging_required_fields(repo_root: Path | None = None) -> list[str]:
    repo_root = repo_root or Path.cwd()
    schema = load_schema(repo_root, "milestone_staging.schema.yaml")
    return list_value(schema, "common_required_fields", MILESTONE_STAGING_REQUIRED_FIELDS)


def controller_packet_base_files(repo_root: Path | None = None) -> list[str]:
    repo_root = repo_root or Path.cwd()
    schema = load_schema(repo_root, "controller_packet.schema.yaml")
    return list_value(schema, "base_required_files", [
        "result.md",
        "controller_context.json",
        "controller_ledger.csv",
        "controller_bootstrap_snapshot.md",
        "implementation_snapshot.md",
        "finalizer_state.json",
        "validator_report.md",
        "controller_report.md",
        "completion_check.md",
        "review_request.md",
        "MANIFEST.md",
        "subagents/reviewer_prompt.md",
    ])


def canonical_milestone_id(value: object) -> str:
    text = normalized_scalar(value)
    match = re.match(r"^M([0-9]+)$", text, re.IGNORECASE)
    try:
        number = int(match.group(1) if match else text)
    except (TypeError, ValueError):
        return text.upper()
    return f"M{number:02d}" if number < 100 else f"M{number}"


def critic_required(frontmatter: dict[str, object]) -> bool:
    task_kind = normalized_scalar(frontmatter.get("task_kind")).lower()
    risk_level = normalized_scalar(frontmatter.get("risk_level")).lower()
    architecture_impact = normalized_scalar(frontmatter.get("architecture_impact")).lower()
    scientific_scope = normalized_scalar(frontmatter.get("scientific_decision_scope")).lower()
    return (
        task_kind == "scientific_milestone"
        or risk_level == "high"
        or architecture_impact == "system"
        or as_bool(frontmatter.get("slurm_runtime_continuity_required"))
        or as_int(frontmatter.get("executor_count"), 1) > 1
        or as_bool(frontmatter.get("route_change"))
        or (scientific_scope not in {"", "none", "null"})
    )


def load_contract_hasher(repo_root: Path):
    path = repo_root / "scripts" / "validation" / "hash_milestone_contract.py"
    spec = importlib.util.spec_from_file_location("hash_milestone_contract_for_handoff", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load contract hasher: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_contains_path_at_commit(repo_root: Path, commit: str, path: str) -> bool:
    if is_blank_or_none(commit) or is_blank_or_none(path):
        return False
    cp = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path}"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return cp.returncode == 0


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


def is_milestone_staging_file(path: Path) -> bool:
    if path.suffix == ".md" and "fixtures" in path.parts:
        return True
    return path.suffix == ".md" and path.name.startswith("M") and bool(
        re.match(r"^M[0-9]+_.*\.md$", path.name)
    ) and "shared" in path.parts


def parse_body_execution_contract(text: str) -> dict[str, object]:
    match = re.search(
        r"(?ms)^## Execution Contract\s*^```ya?ml\s*(.*?)^```",
        text,
    )
    if not match:
        return {}
    values: dict[str, object] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line or line.startswith("- "):
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        if not raw_value:
            values[key] = ""
            continue
        lower_value = raw_value.lower()
        if lower_value == "true":
            values[key] = True
        elif lower_value == "false":
            values[key] = False
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


def normalized_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().strip("\"'")


def load_executor_plan_validator(repo_root: Path):
    path = repo_root / "scripts" / "ops" / "validate_executor_plan.py"
    spec = importlib.util.spec_from_file_location("validate_executor_plan_for_handoff", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load executor plan validator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def severity(strict: bool) -> str:
    return "error" if strict else "warning"


def validate_task_file(path: Path, text: str, strict: bool) -> list[Finding]:
    frontmatter = parse_frontmatter(text)
    findings: list[Finding] = []
    milestone_staging = is_milestone_staging_file(path)
    if milestone_staging and not text.startswith("---\n"):
        return [
            Finding(
                "error",
                path,
                "milestone staging prompt must start with real YAML frontmatter; ## Execution Contract is only a human-readable mirror.",
            )
        ]
    if milestone_staging and not frontmatter:
        return [Finding("error", path, "milestone staging prompt has malformed or missing YAML frontmatter.")]
    if not frontmatter:
        return findings

    execution_mode = str(frontmatter.get("execution_mode", "")).strip("\"'")
    continuity_backend = str(frontmatter.get("continuity_backend", "")).strip("\"'")
    if milestone_staging:
        required_fields = milestone_staging_required_fields(Path.cwd())
        missing_staging = [field for field in required_fields if field not in frontmatter]
        if missing_staging:
            findings.append(
                Finding(
                    "error",
                    path,
                    "milestone staging frontmatter missing required fields: " + ", ".join(missing_staging) + ".",
                )
            )
        milestone_number_value = frontmatter.get("milestone_number")
        milestone_id_value = frontmatter.get("milestone_id") or frontmatter.get("milestone")
        if milestone_number_value is not None and milestone_id_value is not None:
            if canonical_milestone_id(milestone_number_value) != canonical_milestone_id(milestone_id_value):
                findings.append(Finding("error", path, "milestone_number and milestone_id do not resolve to the same canonical ID."))
        status = normalized_scalar(frontmatter.get("status")).upper()
        needs_critic = critic_required(frontmatter)
        if execution_mode == "direct_executor":
            if frontmatter.get("task_type") not in {"milestone", "execution"}:
                findings.append(Finding("error", path, "direct_executor staging must use task_type: milestone or execution."))
            if as_bool(frontmatter.get("controller_mode")) or as_bool(frontmatter.get("requires_execution_controller")):
                findings.append(Finding("error", path, "direct_executor staging must set controller_mode and requires_execution_controller false."))
            if as_int(frontmatter.get("executor_count"), 0) != 1 or as_int(frontmatter.get("executor_slots"), 0) != 1:
                findings.append(Finding("error", path, "direct_executor staging must use exactly one executor."))
        elif execution_mode == "controller_supervised":
            if frontmatter.get("task_type") != "controller":
                findings.append(Finding("error", path, "controller_supervised staging must declare task_type: controller."))
            if not as_bool(frontmatter.get("controller_mode")) or not as_bool(frontmatter.get("requires_execution_controller")):
                findings.append(Finding("error", path, "controller_supervised staging must enable controller_mode and requires_execution_controller."))
        else:
            findings.append(Finding("error", path, "milestone staging execution_mode must be direct_executor or controller_supervised."))
        if as_bool(frontmatter.get("planning_review_required")):
            if normalized_scalar(frontmatter.get("planning_reviewer")) != "separate_gpt_thread":
                findings.append(
                    Finding(
                        "error",
                        path,
                        "planning_reviewer must be separate_gpt_thread; it is not a controller runtime subagent.",
                    )
                )
            if BAD_PLANNING_REVIEWER_RE.search(normalized_scalar(frontmatter.get("planning_reviewer"))):
                findings.append(Finding("error", path, "planning reviewer cannot be a controller/executor/runtime subagent."))
        elif needs_critic:
            findings.append(Finding("error", path, "this task requires planning_review_required: true under agent_flow_policy critic_required_when."))
        if status in PLANNING_REVIEW_READY_STATUSES:
            if needs_critic and is_blank_or_none(frontmatter.get("planning_review_token")):
                findings.append(Finding("error", path, "READY milestone staging requires non-empty planning_review_token."))
            if needs_critic and is_blank_or_none(frontmatter.get("planning_reviewed_commit")):
                findings.append(Finding("error", path, "READY milestone staging requires planning_reviewed_commit."))
        elif needs_critic and as_bool(frontmatter.get("planning_review_required")) and status not in PLANNING_REVIEW_BLOCKED_STATUSES:
            findings.append(
                Finding(
                    "error",
                    path,
                    "candidate without completed planning review must use a planning draft/revision/blocked state.",
                )
            )
        body_contract = parse_body_execution_contract(text)
        for field in V2_FRONTMATTER_FIELDS:
            if field in frontmatter and field in body_contract and normalized_scalar(frontmatter[field]) != normalized_scalar(body_contract[field]):
                findings.append(
                    Finding(
                        "error",
                        path,
                        f"frontmatter/body Execution Contract mismatch for {field}: {frontmatter[field]!r} != {body_contract[field]!r}.",
                    )
                )

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
        if normalized_scalar(frontmatter.get("architecture_impact")).lower() == "system":
            if "wiki/history/COMPARISON.md" not in text:
                findings.append(Finding(severity(strict), path, "system-level planning must list wiki/history/COMPARISON.md in history_files_read."))
            if "wiki/current_state.yaml" not in text and "history_baseline" not in text:
                findings.append(
                    Finding(
                        severity(strict),
                        path,
                        "system-level planning must resolve history baseline dynamically from wiki/current_state.yaml or an explicit history_baseline override.",
                    )
                )
            if "components/*.md" not in text and "component files" not in text.lower():
                findings.append(Finding(severity(strict), path, "system-level planning must read predecessor component analysis files dynamically."))
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
        if re.search(r"(?i)controller\s+(launches|starts|creates|uses)\s+(an\s+)?internal auditor|auditor_subtasks|controller-internal auditor", text) and not re.search(r"(?is)must not.*internal auditor|must not.*controller-internal auditor|must not use `?auditor_subtasks`?|do not create.*internal auditor|do not create.*controller-internal auditor", text):
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
    schema = load_schema(Path.cwd(), "controller_packet.schema.yaml")
    required = list_value(schema, "precommit_finalizer_fields", [
        "task_key",
        "final_state",
        "git_commit_decision",
        "precommit_head",
        "tracked_paths",
        "manifest_sha256",
    ])
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


def validate_executor_plan_file(repo_root: Path, path: Path) -> list[Finding]:
    if not path.name.endswith("executor_plan.yaml"):
        return []
    findings: list[Finding] = []
    try:
        plan_validator = load_executor_plan_validator(repo_root)
        data = plan_validator.load_yaml(path)
        errors = plan_validator.validate_plan(data)
    except Exception as exc:
        return [Finding("error", path, f"executor plan validation failed to run: {exc}")]
    for error in errors:
        findings.append(Finding("error", path, f"executor plan invalid: {error}"))
    return findings


def validate_planning_review_for_candidate(
    repo_root: Path,
    candidate_path: Path,
    frontmatter: dict[str, object],
) -> list[Finding]:
    findings: list[Finding] = []
    if not as_bool(frontmatter.get("planning_review_required")):
        return findings
    status = normalized_scalar(frontmatter.get("status")).upper()
    if status not in PLANNING_REVIEW_READY_STATUSES:
        return findings
    review_value = normalized_scalar(frontmatter.get("planning_review_path"))
    if is_blank_or_none(review_value):
        return [Finding("error", candidate_path, "READY candidate requires planning_review_path.")]
    review_path = repo_root / review_value
    if not review_path.is_file():
        return [Finding("error", candidate_path, f"planning review file missing: {review_value}")]
    review_text = review_path.read_text(encoding="utf-8")
    review_frontmatter = parse_frontmatter(review_text)
    if not review_frontmatter:
        return [Finding("error", review_path, "planning review must start with real YAML frontmatter.")]
    schema = load_schema(repo_root, "planning_review.schema.yaml")
    missing = [field for field in list_value(schema, "required_fields") if field not in review_frontmatter]
    if missing:
        findings.append(Finding("error", review_path, "planning review frontmatter missing fields: " + ", ".join(missing) + "."))
    if normalized_scalar(review_frontmatter.get("role")) != "critic":
        findings.append(Finding("error", review_path, "planning review role must be critic."))
    if normalized_scalar(review_frontmatter.get("task_key")) != normalized_scalar(frontmatter.get("task_key")):
        findings.append(Finding("error", review_path, "planning review task_key does not match candidate."))
    if canonical_milestone_id(review_frontmatter.get("milestone_id")) != canonical_milestone_id(frontmatter.get("milestone_id") or frontmatter.get("milestone_number")):
        findings.append(Finding("error", review_path, "planning review milestone_id does not match candidate."))
    reviewed_prompt_path = normalized_scalar(review_frontmatter.get("reviewed_prompt_path"))
    if reviewed_prompt_path != str(candidate_path):
        findings.append(Finding("error", review_path, "planning review reviewed_prompt_path does not match candidate path."))
    try:
        hasher = load_contract_hasher(repo_root)
        actual_hash = hasher.contract_sha256(repo_root / candidate_path)
    except Exception as exc:
        findings.append(Finding("error", candidate_path, f"could not hash milestone contract: {exc}"))
        actual_hash = ""
    if normalized_scalar(review_frontmatter.get("reviewed_contract_sha256")) != actual_hash:
        findings.append(Finding("error", review_path, "planning review hash mismatch; prompt changed after critic review or review targets another contract."))
    decision = normalized_scalar(review_frontmatter.get("critic_decision"))
    token = normalized_scalar(review_frontmatter.get("critic_token"))
    expected_tokens = schema.get("valid_tokens", {})
    if isinstance(expected_tokens, dict) and expected_tokens.get(decision) and token != expected_tokens.get(decision):
        findings.append(Finding("error", review_path, "critic_token does not match critic_decision."))
    if decision != "READY_FOR_CODEX_MERGE":
        findings.append(Finding("error", review_path, "candidate READY requires critic_decision: READY_FOR_CODEX_MERGE."))
    if normalized_scalar(frontmatter.get("planning_review_token")) != token:
        findings.append(Finding("error", candidate_path, "candidate planning_review_token does not match critic_token."))
    reviewed_commit = normalized_scalar(frontmatter.get("planning_reviewed_commit"))
    if not git_contains_path_at_commit(repo_root, reviewed_commit, str(candidate_path)):
        findings.append(Finding("error", candidate_path, "planning_reviewed_commit does not contain the reviewed prompt path."))
    return findings


def validate_milestone_staging_plan(repo_root: Path, path: Path, text: str) -> list[Finding]:
    if not is_milestone_staging_file(path):
        return []
    frontmatter = parse_frontmatter(text)
    if not frontmatter:
        return []
    findings: list[Finding] = []
    plan_value = normalized_scalar(frontmatter.get("executor_plan_path"))
    if is_blank_or_none(plan_value):
        return [Finding("error", path, "milestone staging must declare executor_plan_path in frontmatter.")]
    plan_path = (repo_root / plan_value).resolve()
    if not plan_path.is_file():
        return [Finding("error", path, f"executor_plan_path does not exist: {plan_value}")]
    try:
        plan_validator = load_executor_plan_validator(repo_root)
        plan_data = plan_validator.load_yaml(plan_path)
        plan_errors = plan_validator.validate_plan(plan_data)
    except Exception as exc:
        return [Finding("error", path, f"executor_plan_path validation failed: {exc}")]
    for error in plan_errors:
        findings.append(Finding("error", path, f"executor_plan_path invalid: {error}"))
    plan_task_key = normalized_scalar(plan_data.get("task_key"))
    if not is_blank_or_none(plan_task_key) and plan_task_key != normalized_scalar(frontmatter.get("task_key")):
        findings.append(Finding("error", path, "task_key differs between milestone staging frontmatter and executor plan."))
    executors = plan_data.get("executors", [])
    plan_count = len(executors) if isinstance(executors, list) else 0
    if as_int(frontmatter.get("executor_count"), 0) != plan_count:
        findings.append(
            Finding(
                "error",
                path,
                f"executor_count differs from executor plan: frontmatter={frontmatter.get('executor_count')} plan={plan_count}.",
            )
        )
    max_parallel = as_int(plan_data.get("max_parallel"), 1)
    if as_int(frontmatter.get("executor_slots"), 0) != max_parallel:
        findings.append(
            Finding(
                "error",
                path,
                f"executor_slots differs from executor plan max_parallel: frontmatter={frontmatter.get('executor_slots')} plan={max_parallel}.",
            )
        )
    if as_bool(frontmatter.get("parallel_execution_allowed")) != as_bool(plan_data.get("parallel_execution_allowed")):
        findings.append(Finding("error", path, "parallel_execution_allowed differs between milestone staging and executor plan."))
    findings.extend(validate_planning_review_for_candidate(repo_root, path, frontmatter))
    return findings


def validate_controller_packet_dir(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    completion = path / "completion_check.md"
    if not completion.is_file():
        return findings
    text = completion.read_text(encoding="utf-8")
    if "PACKET_COMMITTED_FOR_REVIEW" not in text:
        return findings
    missing = [rel for rel in controller_packet_base_files(Path.cwd()) if not (path / rel).is_file()]
    if missing:
        findings.append(
            Finding(
                "error",
                path,
                "controller packet committed for review is missing required files: " + ", ".join(missing),
            )
        )
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
    repo_root = Path.cwd()
    for path in paths:
        if path.is_dir():
            findings.extend(validate_controller_packet_dir(path))
            for completion in path.rglob("completion_check.md"):
                findings.extend(validate_controller_packet_dir(completion.parent))
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
        if path.name.endswith("executor_plan.yaml"):
            findings.extend(validate_executor_plan_file(repo_root, path))
        if is_milestone_staging_file(path):
            findings.extend(validate_milestone_staging_plan(repo_root, path, text))
    return findings


def default_paths(repo_root: Path) -> list[Path]:
    registry = repo_root / "prompts" / "ACTIVE_POLICY_FILES.yaml"
    if not registry.is_file():
        return [repo_root / "AGENTS.md", repo_root / "prompts"]
    data = load_yaml_file(registry)
    paths = [repo_root / str(item) for item in list_value(data, "active_rule_sources")]
    paths.extend(repo_root / str(item) for item in list_value(data, "schemas"))
    paths.append(registry)
    return paths


def candidate_paths(repo_root: Path) -> list[Path]:
    registry = repo_root / "prompts" / "ACTIVE_POLICY_FILES.yaml"
    data = load_yaml_file(registry) if registry.is_file() else {}
    paths: list[Path] = []
    for pattern in list_value(data, "candidate_globs", ["prompts/shared/M[0-9]*_*.md"]):
        paths.extend(sorted(repo_root.glob(pattern)))
    return paths


def validate_candidate(repo_root: Path, candidate: Path) -> list[Finding]:
    path = candidate if candidate.is_absolute() else repo_root / candidate
    if not path.is_file():
        return [Finding("error", candidate, "candidate file does not exist.")]
    rel = path.relative_to(repo_root) if path.is_relative_to(repo_root) else candidate
    text = path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    validation_path = rel
    if not is_milestone_staging_file(rel) and frontmatter.get("milestone_id"):
        validation_path = Path("prompts/shared") / f"{canonical_milestone_id(frontmatter.get('milestone_id'))}_candidate.md"
    findings = validate_task_file(validation_path, text, strict=True)
    findings.extend(validate_milestone_staging_plan(repo_root, validation_path, text))
    return findings


def validate_packet(repo_root: Path, packet: Path) -> list[Finding]:
    path = packet if packet.is_absolute() else repo_root / packet
    if not path.is_dir():
        return [Finding("error", packet, "packet directory does not exist.")]
    return validate_paths([path], strict_tasks=True)


def validate_repository_readiness(repo_root: Path) -> list[Finding]:
    findings = validate_paths(default_paths(repo_root), strict_tasks=True)
    for candidate in candidate_paths(repo_root):
        text = candidate.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        if normalized_scalar(frontmatter.get("status")).upper() in PLANNING_REVIEW_READY_STATUSES:
            findings.extend(validate_candidate(repo_root, candidate))
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Markdown files or directories to validate.")
    parser.add_argument("--policy", action="store_true", help="Validate active policy/schema/template/skill consistency only.")
    parser.add_argument("--candidate", type=Path, help="Validate one milestone staging candidate for execution readiness.")
    parser.add_argument("--packet", type=Path, help="Validate one controller/executor result packet.")
    parser.add_argument("--repository-readiness", action="store_true", help="Validate active policy plus active READY candidates and packets.")
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
    selected_modes = sum(bool(value) for value in (args.policy, args.candidate, args.packet, args.repository_readiness))
    if selected_modes > 1:
        print("error: choose only one validation mode", file=sys.stderr)
        return 2
    if args.policy:
        findings = validate_paths(default_paths(repo_root), strict_tasks=True)
    elif args.candidate:
        findings = validate_candidate(repo_root, args.candidate)
    elif args.packet:
        findings = validate_packet(repo_root, args.packet)
    elif args.repository_readiness:
        findings = validate_repository_readiness(repo_root)
    else:
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
