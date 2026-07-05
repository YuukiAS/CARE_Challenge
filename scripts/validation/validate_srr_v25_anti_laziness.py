#!/usr/bin/env python3
"""Anti-laziness validator for SRR-v2/v2.5 implementation claims.

The validator is intentionally conservative: it reports issues when a claim is
defined only as a utility, when runtime evidence is absent, or when exact
controller-required filenames are missing. It does not train models.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


CONTROLLER_TASK_PATTERN = re.compile(r"prompts/tasks/([0-9]{8}_[a-zA-Z0-9_]+)\.md")
OUTPUT_FILE_PATTERN = re.compile(r"`([^`]+?\.(?:md|csv|json|yaml|yml|txt))`")
FAILURE_SOURCE_PATTERNS = (
    "deterministic_axis",
    "random",
    "trainable_parameter_only",
    "no_proto_variant",
    "pending_train_or_oof_fit",
)


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str
    evidence: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iter_task_keys(controller_text: str) -> list[str]:
    seen: list[str] = []
    for match in CONTROLLER_TASK_PATTERN.finditer(controller_text):
        key = match.group(1)
        if key not in seen:
            seen.append(key)
    return seen


def required_outputs_from_task(task_text: str) -> list[str]:
    marker = "## Required Outputs"
    if marker not in task_text:
        return []
    section = task_text.split(marker, 1)[1]
    next_header = re.search(r"\n## ", section)
    if next_header:
        section = section[: next_header.start()]
    outputs: list[str] = []
    for match in OUTPUT_FILE_PATTERN.finditer(section):
        name = Path(match.group(1)).name
        if name not in outputs:
            outputs.append(name)
    return outputs


def check_required_file_names(repo: Path, controller: Path, results_root: Path) -> list[Issue]:
    issues: list[Issue] = []
    controller_text = read_text(controller)
    for key in iter_task_keys(controller_text):
        task_path = repo / "prompts" / "tasks" / f"{key}.md"
        if not task_path.exists():
            issues.append(Issue("TASK_FILE_MISSING", "error", f"controller references missing task {key}", str(task_path)))
            continue
        required = required_outputs_from_task(read_text(task_path))
        result_dir = results_root / key
        if not result_dir.exists():
            continue
        existing = {p.name for p in result_dir.iterdir() if p.is_file()}
        for name in required:
            if name not in existing:
                similar = sorted(candidate for candidate in existing if candidate.lower().replace("_", "") == name.lower().replace("_", ""))
                hint = f"; similar={similar}" if similar else ""
                issues.append(Issue("REQUIRED_FILE_MISSING", "error", f"{key} missing exact required file {name}{hint}", str(result_dir / name)))
    return issues


def ast_defined_and_called(paths: Iterable[Path]) -> tuple[set[str], set[str]]:
    defined: set[str] = set()
    called: set[str] = set()
    for path in paths:
        if not path.exists() or path.suffix != ".py":
            continue
        try:
            tree = ast.parse(read_text(path), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    called.add(func.id)
                elif isinstance(func, ast.Attribute):
                    called.add(func.attr)
    return defined, called


def check_runtime_call_trace(repo: Path) -> list[Issue]:
    issues: list[Issue] = []
    formal_paths = [
        repo / "src/care_myocardium/models/srr_propref.py",
        repo / "src/care_myocardium/models/srr_v2_unet.py",
        repo / "src/care_myocardium/models/srr_blocks.py",
        repo / "src/care_myocardium/models/proposal_prototypes.py",
        repo / "src/care_myocardium/losses/srr_losses.py",
        repo / "scripts/training/run_srr_propref_myops_fold0.py",
    ]
    defined, called = ast_defined_and_called(formal_paths)
    required_runtime_calls = {
        "build_prototype_bank_from_labeled_features": "real prototype banks are defined but must be loaded by formal model/runner",
        "load_prototype_bank": "prototype loader exists but must be called by formal model/runner",
    }
    for name, message in required_runtime_calls.items():
        if name in defined and name not in called:
            issues.append(Issue("UTILITY_ONLY_NOT_CALLED", "error", message, name))
    return issues


def check_prototype_sources(repo: Path, results_root: Path) -> list[Issue]:
    issues: list[Issue] = []
    model_path = repo / "src/care_myocardium/models/srr_propref.py"
    runner_path = repo / "scripts/training/run_srr_propref_myops_fold0.py"
    runner_text = read_text(runner_path) if runner_path.exists() else ""
    formal_loads_real_bank = (
        "build_prototype_bank_from_labeled_features" in runner_text
        and "load_prototype_bank" in runner_text
        and "prototype_bank_summary.json" in runner_text
    )
    if model_path.exists():
        text = read_text(model_path)
        if "deterministic_axis_bootstrap_pending_train_or_oof_fit" in text and not formal_loads_real_bank:
            issues.append(
                Issue(
                    "PROTOTYPE_SOURCE_NOT_FINAL",
                    "error",
                    "default proposal dictionary source is deterministic bootstrap, not a real train/OOF bank",
                    f"{model_path}:37",
                )
            )
    for summary in results_root.glob("202607*/**/summary.json"):
        try:
            payload = json.loads(read_text(summary))
        except json.JSONDecodeError:
            continue
        encoded = json.dumps(payload, sort_keys=True)
        if any(pattern in encoded for pattern in FAILURE_SOURCE_PATTERNS):
            issues.append(Issue("PROTOTYPE_SUMMARY_UNSAFE_SOURCE", "warning", "summary records non-final prototype source", str(summary)))
    return issues


def check_residual_gate_contract(repo: Path) -> list[Issue]:
    model_files = [
        repo / "src/care_myocardium/models/srr_propref.py",
        repo / "src/care_myocardium/models/srr_v2_unet.py",
    ]
    combined = "\n".join(read_text(path) for path in model_files if path.exists())
    has_anchor_formula = any(token in combined for token in ("nnunet_logits", "nnunet_prob", "baseline_logits", "anchor_logits", "BaselinePreservingResidualGate"))
    has_gate_delta = any(token in combined for token in ("bounded_delta", "bounded_delta_srr", "baseline_residual_gate", "residual_gate", "gate_open", "closed_gate"))
    if not (has_anchor_formula and has_gate_delta):
        return [
            Issue(
                "BASELINE_PRESERVING_GATE_MISSING",
                "error",
                "no callable baseline-preserving nnU-Net residual/gated correction formula was found",
                "expected final_logits = nnunet_logits + gate * bounded_delta or equivalent",
            )
        ]
    return []


def identity_fallback_matches_anchor(anchor_logits, gate, delta):
    return anchor_logits + gate * delta


def check_no_t2_toy_decode(repo: Path) -> list[Issue]:
    try:
        import torch

        from src.care_myocardium.anchors.myops_decode import EDEMA_CLASS, decode_myops_logits_for_export_policy
    except Exception as exc:  # pragma: no cover - import failure is reportable.
        return [Issue("NO_T2_TOY_IMPORT_FAILED", "error", f"could not import no-T2 guardrail APIs: {exc}", "src.care_myocardium.anchors.myops_decode")]

    logits = torch.zeros(2, 6, 2, 2, 2)
    logits[:, EDEMA_CLASS] = 9.0
    availability = torch.tensor([[1.0, 0.0, 1.0], [1.0, 1.0, 1.0]])
    compact, _raw, summary = decode_myops_logits_for_export_policy(logits, availability, policy="block_edema")
    if bool(torch.any(compact[0] == EDEMA_CLASS)) or summary.get("no_t2_edema_voxels_after") != 0:
        return [Issue("NO_T2_TOY_DECODE_FAILED", "error", "toy no-T2 decode/export policy did not block edema", json.dumps(summary, sort_keys=True))]
    return []


def unsupported_claim_issues(text: str, evidence_path: str) -> list[Issue]:
    issues: list[Issue] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if not line.strip().startswith("claim."):
            continue
        lowered = line.lower()
        has_concrete_evidence = (
            bool(re.search(r"\b[\w./-]+\.(?:py|md|csv|json|yaml|yml)(?::\d+)?\b", line))
            or bool(re.search(r"\bline\s+\d+\b", lowered))
            or bool(re.search(r"\b[a-zA-Z0-9_./-]+:\d+\b", line))
        )
        if "supported" in lowered and not has_concrete_evidence:
            issues.append(Issue("CLAIM_WITHOUT_RUNTIME_EVIDENCE", "error", "claim line lacks concrete file/line/runtime evidence", f"{evidence_path}:{idx}"))
    return issues


def check_claim_runtime_evidence(results_root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for path in results_root.glob("202607*/**/*.md"):
        if path.name not in {"result.md", "review.md", "controller_report.md"}:
            continue
        issues.extend(unsupported_claim_issues(read_text(path), str(path)))
    return issues


def run_checks(repo: Path, controller: Path, results_root: Path) -> list[Issue]:
    issues: list[Issue] = []
    issues.extend(check_required_file_names(repo, controller, results_root))
    issues.extend(check_runtime_call_trace(repo))
    issues.extend(check_prototype_sources(repo, results_root))
    issues.extend(check_residual_gate_contract(repo))
    issues.extend(check_no_t2_toy_decode(repo))
    issues.extend(check_claim_runtime_evidence(results_root))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--controller", type=Path, default=Path("prompts/tasks/20260704_srr_v25_full_completion_goal.md"))
    parser.add_argument("--results-root", type=Path, default=Path("results"))
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--strict", action="store_true", help="return nonzero when error-severity issues are found")
    args = parser.parse_args(argv)

    repo = args.repo_root.resolve()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    controller = args.controller if args.controller.is_absolute() else repo / args.controller
    results_root = args.results_root if args.results_root.is_absolute() else repo / args.results_root
    issues = run_checks(repo, controller, results_root)
    payload = {
        "issue_count": len(issues),
        "error_count": sum(1 for issue in issues if issue.severity == "error"),
        "warning_count": sum(1 for issue in issues if issue.severity == "warning"),
        "issues": [asdict(issue) for issue in issues],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"issue_count={payload['issue_count']} error_count={payload['error_count']} warning_count={payload['warning_count']}")
        for issue in issues:
            print(f"{issue.severity.upper()} {issue.code}: {issue.message} [{issue.evidence}]")
    return 1 if args.strict and payload["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
