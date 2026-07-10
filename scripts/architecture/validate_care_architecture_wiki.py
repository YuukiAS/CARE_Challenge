#!/usr/bin/env python3
"""Validate CARE architecture wiki, component table, and diagram consistency."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
import sys


REQUIRED_WIKI_FILES = [
    "README.md",
    "MODEL.md",
    "EXECUTION.md",
    "COMPONENTS.csv",
    "LINEAGE.md",
    "architecture.yaml",
    "figures/model-current.d2",
    "figures/model-current.svg",
    "figures/model-current.png",
    "figures/model-gap.d2",
    "figures/model-gap.svg",
    "figures/model-gap.png",
    "figures/execution-flow.d2",
    "figures/execution-flow.svg",
    "figures/execution-flow.png",
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

VALID_CURRENT_STATUS = {"implemented", "partial", "scaffold", "legacy", "disabled", "unknown"}
VALID_EVIDENCE_STATUS = {"verified", "unverified", "stale", "missing"}


def parse_yaml_ids(text: str, key: str) -> set[str]:
    inside = False
    ids: set[str] = set()
    for line in text.splitlines():
        if re.match(rf"^{re.escape(key)}\s*:", line):
            inside = True
            continue
        if inside and re.match(r"^[A-Za-z_][A-Za-z0-9_-]*\s*:", line):
            break
        match = re.match(r"\s*-\s+id\s*:\s*([A-Za-z0-9_.-]+)", line)
        if inside and match:
            ids.add(match.group(1))
    return ids


def validate(repo_root: Path, strict: bool) -> list[str]:
    wiki_root = repo_root / "wiki"
    errors: list[str] = []
    for rel in REQUIRED_WIKI_FILES:
        path = wiki_root / rel
        if not path.is_file():
            errors.append(f"missing wiki file: wiki/{rel}")

    components_path = wiki_root / "COMPONENTS.csv"
    if components_path.is_file():
        rows = list(csv.DictReader(components_path.read_text(encoding="utf-8").splitlines()))
        columns = rows[0].keys() if rows else []
        for column in COMPONENT_REQUIRED_COLUMNS:
            if column not in columns:
                errors.append(f"COMPONENTS.csv missing column: {column}")
        for idx, row in enumerate(rows, start=2):
            cid = row.get("component_id", f"row-{idx}")
            if row.get("current_status") not in VALID_CURRENT_STATUS:
                errors.append(f"{cid}: invalid current_status {row.get('current_status')!r}")
            if row.get("evidence_status") not in VALID_EVIDENCE_STATUS:
                errors.append(f"{cid}: invalid evidence_status {row.get('evidence_status')!r}")
            if row.get("evidence_status") == "verified" and not row.get("runtime_evidence", "").strip():
                errors.append(f"{cid}: verified without runtime_evidence")
            if row.get("evidence_status") == "verified" and not row.get("final_output_effect", "").strip():
                errors.append(f"{cid}: verified without final_output_effect")
            if row.get("current_status") == "implemented" and not row.get("source_file", "").strip():
                errors.append(f"{cid}: implemented without source_file")
            source = row.get("source_file", "").strip()
            if strict and source and not (repo_root / source).exists() and not source.startswith("wiki/"):
                errors.append(f"{cid}: source_file does not exist: {source}")

    arch_path = wiki_root / "architecture.yaml"
    if arch_path.is_file():
        arch = arch_path.read_text(encoding="utf-8")
        for token in ("architecture_version:", "review_token:", "code_fingerprint:", "nodes:", "edges:"):
            if token not in arch:
                errors.append(f"architecture.yaml missing {token}")
        node_ids = parse_yaml_ids(arch, "nodes")
        if not node_ids:
            errors.append("architecture.yaml has no node ids")
        for fig in ("model-current", "model-gap", "execution-flow"):
            d2_path = wiki_root / "figures" / f"{fig}.d2"
            if d2_path.is_file() and d2_path.stat().st_size == 0:
                errors.append(f"{fig}.d2 is empty")

    readme = wiki_root / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        for rel in ("figures/model-current.png", "figures/model-gap.png", "figures/execution-flow.png"):
            if rel not in text:
                errors.append(f"wiki README does not reference {rel}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    errors = validate(Path.cwd(), strict=args.strict)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("care architecture wiki validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
