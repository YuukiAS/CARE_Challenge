#!/usr/bin/env python3
"""Audit SRR production formal-entrypoint authority.

This script is intentionally static. It does not train, submit Slurm jobs,
package validation outputs, or run inference. Its job is to prevent old
synthetic/proxy scripts from regaining formal authority.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs/srr_production/entrypoints.yaml"

FORBIDDEN_FORMAL_PATHS = {
    "scripts/training/route_B_round04/myops/B3/run_B3_representation.py",
    "scripts/training/route_B_round04/myops/B4/run_B4_proposal.py",
    "scripts/training/route_B_round04/myops/B5/run_B5_refiner.py",
    "scripts/training/route_B_round04/myops/B6/run_B6_joint.py",
    "scripts/training/route_B_round04/cine/B7/run_B7_cinema_control.py",
    "scripts/training/route_B_round04/cine/B8/run_B8_registration.py",
    "jobs/route_B_round04/run_B3_representation.sh",
    "jobs/route_B_round04/run_B4_proposal.sh",
    "jobs/route_B_round04/run_B5_refiner.sh",
    "jobs/route_B_round04/run_B6_joint.sh",
    "jobs/route_B_round04/run_B7_cinema_control.sh",
    "jobs/route_B_round04/run_B8_registration.sh",
}

RANDOM_SCIENCE_PATTERNS = (
    re.compile(r"\btorch\.(randn|rand|randint|randn_like|rand_like)\b"),
    re.compile(r"\bnp\.random\b"),
    re.compile(r"\bnumpy\.random\b"),
)

HARDCODED_METRIC_PATTERN = re.compile(
    r"(?i)(dice|auc|hd95|hd|metric|score|proxy)[A-Za-z0-9_\"' :,-]{0,80}[:=]\s*[-+]?(?:0?\.\d+|\d+\.\d+)"
)

PROTOTYPE_BOOTSTRAP_PATTERNS = (
    re.compile(r"\bdeterministic_axis_prototypes\b"),
    re.compile(r"(?i)\brandom[_ -]?prototype"),
    re.compile(r"(?i)\bbootstrap[_ -]?pending"),
)


def repo_rel(path: str | Path) -> str:
    value = Path(path)
    if not value.is_absolute():
        value = REPO_ROOT / value
    try:
        return value.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return value.as_posix()


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return data


def _entry_is_formal(entry: dict[str, Any], *, default_formal: bool) -> bool:
    if "formal_authority" in entry:
        return bool(entry.get("formal_authority"))
    status = str(entry.get("status", entry.get("audit_status", ""))).lower()
    return default_formal or status in {"formal", "production", "ready", "formal_training"}


def formal_entries(config: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for entry in config.get("formal_entrypoints", []) or []:
        if isinstance(entry, dict) and entry.get("path") and _entry_is_formal(entry, default_formal=True):
            entries.append(entry)
    for entry in config.get("candidate_entrypoints", []) or []:
        if isinstance(entry, dict) and entry.get("path") and _entry_is_formal(entry, default_formal=False):
            entries.append(entry)
    return entries


def configured_forbidden(config: dict[str, Any]) -> set[str]:
    out = set(FORBIDDEN_FORMAL_PATHS)
    for entry in config.get("forbidden_formal_entrypoints", []) or []:
        if isinstance(entry, dict) and entry.get("path"):
            out.add(repo_rel(str(entry["path"])))
    return out


def source_matches(path: Path, patterns: tuple[re.Pattern[str], ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for pattern in patterns:
            if pattern.search(line):
                rows.append({"line": lineno, "pattern": pattern.pattern, "text": line.strip()[:220]})
    return rows


def source_metric_matches(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if HARDCODED_METRIC_PATTERN.search(line):
            rows.append({"line": lineno, "pattern": HARDCODED_METRIC_PATTERN.pattern, "text": line.strip()[:220]})
    return rows


def source_calls_forbidden(path: Path, forbidden: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        normalized = line.strip()
        for forbidden_path in sorted(forbidden):
            if forbidden_path in normalized or Path(forbidden_path).name in normalized:
                rows.append({"line": lineno, "forbidden_path": forbidden_path, "text": normalized[:220]})
    return rows


def audit_config(config: dict[str, Any], *, strict: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    forbidden = configured_forbidden(config)
    entries = formal_entries(config)
    formal_training_status = str(config.get("formal_training_status", ""))

    allowed_empty_formal_statuses = {
        "BLOCKED_PENDING_BATCH1_REPAIR",
        "BLOCKED_PENDING_BATCH2_INFERENCE_AND_FAIR_EVALUATION",
        "BLOCKED_PENDING_BATCH2B_INFERENCE_AND_FAIR_EVALUATION",
        "BLOCKED_PENDING_AUTHORIZED_FOLD0_TRAINING",
    }
    if strict and not entries and formal_training_status not in allowed_empty_formal_statuses:
        failures.append(
            {
                "check": "formal_authority_empty_without_blocked_status",
                "message": "No formal entrypoint is declared, but formal_training_status is not an allowed blocked status.",
            }
        )

    for entry in entries:
        rel = repo_rel(str(entry["path"]))
        abs_path = REPO_ROOT / rel
        if rel in forbidden or re.search(r"scripts/training/route_B_round04/.*/B[3-8]/", rel):
            failures.append({"check": "forbidden_formal_entrypoint", "path": rel})
            continue
        if not abs_path.is_file():
            failures.append({"check": "formal_entrypoint_missing", "path": rel})
            continue

        forbidden_calls = source_calls_forbidden(abs_path, forbidden)
        if forbidden_calls:
            failures.append({"check": "formal_entrypoint_calls_forbidden_legacy_path", "path": rel, "hits": forbidden_calls[:12]})

        random_hits = source_matches(abs_path, RANDOM_SCIENCE_PATTERNS)
        if random_hits:
            failures.append({"check": "formal_random_or_synthetic_science_data", "path": rel, "hits": random_hits[:12]})

        metric_hits = source_metric_matches(abs_path)
        if metric_hits:
            failures.append({"check": "formal_hardcoded_or_fixed_metric", "path": rel, "hits": metric_hits[:12]})

        prototype_hits = source_matches(abs_path, PROTOTYPE_BOOTSTRAP_PATTERNS)
        if prototype_hits:
            failures.append({"check": "formal_deterministic_or_random_prototype_bootstrap", "path": rel, "hits": prototype_hits[:12]})

    for entry in config.get("candidate_entrypoints", []) or []:
        if isinstance(entry, dict) and entry.get("path"):
            rel = repo_rel(str(entry["path"]))
            if rel in forbidden and bool(entry.get("formal_authority")):
                failures.append({"check": "candidate_marked_formal_but_forbidden", "path": rel})
            elif rel in forbidden:
                warnings.append({"check": "forbidden_candidate_recorded_nonformal", "path": rel})

    return failures, warnings


def apply_known_bad(config: dict[str, Any], fixture: str) -> None:
    mapping = {
        "legacy_b6": "scripts/training/route_B_round04/myops/B6/run_B6_joint.py",
        "legacy_b8": "scripts/training/route_B_round04/cine/B8/run_B8_registration.py",
    }
    if fixture not in mapping:
        return
    config["formal_training_status"] = "READY"
    config["formal_entrypoints"] = [
        {
            "id": fixture,
            "role": "known_bad_fixture",
            "path": mapping[fixture],
            "formal_authority": True,
        }
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--known-bad", choices=["legacy_b6", "legacy_b8"], default="")
    args = parser.parse_args(argv)

    config_path = args.config if args.config.is_absolute() else REPO_ROOT / args.config
    config = load_config(config_path)
    if args.known_bad:
        apply_known_bad(config, args.known_bad)
    failures, warnings = audit_config(config, strict=bool(args.strict))
    report = {
        "config": display_path(config_path),
        "strict": bool(args.strict),
        "known_bad": args.known_bad or None,
        "formal_training_status": config.get("formal_training_status"),
        "formal_entrypoint_count": len(formal_entries(config)),
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
