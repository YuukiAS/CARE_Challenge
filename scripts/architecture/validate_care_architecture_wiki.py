#!/usr/bin/env python3
"""Validate CARE architecture wiki, component table, and generated diagrams."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
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
EXPECTED_M9_REVIEW_TOKEN = "M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY"


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


def load_generator(repo_root: Path):
    path = repo_root / "scripts" / "architecture" / "generate_care_architecture_wiki.py"
    spec = importlib.util.spec_from_file_location("generate_care_architecture_wiki", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def contains_token(path: Path, token: str) -> bool:
    if not token.strip():
        return False
    try:
        return token in path.read_text(encoding="utf-8", errors="ignore")
    except UnicodeDecodeError:
        return False


def validate_components(repo_root: Path, strict: bool) -> list[str]:
    path = repo_root / "wiki" / "COMPONENTS.csv"
    if not path.is_file():
        return ["missing wiki file: wiki/COMPONENTS.csv"]
    errors: list[str] = []
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    columns = rows[0].keys() if rows else []
    for column in COMPONENT_REQUIRED_COLUMNS:
        if column not in columns:
            errors.append(f"COMPONENTS.csv missing column: {column}")
    if errors:
        return errors
    for idx, row in enumerate(rows, start=2):
        cid = row.get("component_id", f"row-{idx}")
        current = row.get("current_status", "")
        evidence = row.get("evidence_status", "")
        source = row.get("source_file", "").strip()
        runtime = row.get("runtime_evidence", "").strip()
        symbol = row.get("symbol", "").strip()
        grep_key = row.get("grep_key", "").strip()
        if current not in VALID_CURRENT_STATUS:
            errors.append(f"{cid}: invalid current_status {current!r}")
        if evidence not in VALID_EVIDENCE_STATUS:
            errors.append(f"{cid}: invalid evidence_status {evidence!r}")
        if evidence == "verified":
            if not runtime:
                errors.append(f"{cid}: verified without runtime_evidence")
            elif not (repo_root / runtime).exists():
                errors.append(f"{cid}: verified runtime_evidence does not exist: {runtime}")
            if not row.get("final_output_effect", "").strip():
                errors.append(f"{cid}: verified without final_output_effect")
        if current == "implemented" and not source:
            errors.append(f"{cid}: implemented without source_file")
        if source:
            source_path = repo_root / source
            if not source_path.exists():
                errors.append(f"{cid}: source_file does not exist: {source}")
            elif strict and source_path.is_file():
                token_ok = contains_token(source_path, grep_key) or contains_token(source_path, symbol)
                if (grep_key or symbol) and not token_ok:
                    errors.append(f"{cid}: neither grep_key nor symbol found in source_file: {source}")
        if cid in {"controller_supervision", "mapper_wiki_observability"}:
            if current != "partial" or evidence != "unverified":
                errors.append(f"{cid}: must remain current_status=partial and evidence_status=unverified until real controller runtime evidence exists")
    return errors


def validate_architecture(repo_root: Path) -> list[str]:
    path = repo_root / "wiki" / "architecture.yaml"
    if not path.is_file():
        return ["missing wiki file: wiki/architecture.yaml"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for token in ("architecture_version:", "review_token:", "code_fingerprint:", "nodes:", "edges:"):
        if token not in text:
            errors.append(f"architecture.yaml missing {token}")
    node_ids = parse_yaml_ids(text, "nodes")
    edge_ids = parse_yaml_ids(text, "edges")
    if not node_ids:
        errors.append("architecture.yaml has no node ids")
    if "review_token: " + EXPECTED_M9_REVIEW_TOKEN not in text:
        errors.append("architecture.yaml review_token does not match current M9 follow-up review token")
    return errors


def validate_review_token(repo_root: Path) -> list[str]:
    review = repo_root / "results" / "20260708_srr_v3_m9_dictionary_fidelity_repair_training" / "review.md"
    if not review.is_file():
        return [f"missing committed review token source: {review}"]
    text = review.read_text(encoding="utf-8")
    if EXPECTED_M9_REVIEW_TOKEN not in text:
        return ["current M9 follow-up review.md does not contain expected review token"]
    return []


def validate_generated_diagrams(repo_root: Path) -> list[str]:
    errors: list[str] = []
    try:
        generator = load_generator(repo_root)
        sources = generator.generated_sources(repo_root)
    except Exception as exc:  # pragma: no cover - defensive CLI error
        return [f"failed to load generated diagram sources: {exc}"]
    figure_dir = repo_root / "wiki" / "figures"
    for stem, source in sources.items():
        d2_path = figure_dir / f"{stem}.d2"
        svg_path = figure_dir / f"{stem}.svg"
        png_path = figure_dir / f"{stem}.png"
        if not d2_path.is_file():
            errors.append(f"missing generated D2 source: wiki/figures/{stem}.d2")
            continue
        d2_text = d2_path.read_text(encoding="utf-8")
        if d2_text != source:
            errors.append(f"stale generated D2 source: wiki/figures/{stem}.d2")
        if "Generated by scripts/architecture/generate_care_architecture_wiki.py" not in d2_text:
            errors.append(f"{stem}.d2 missing generator provenance marker")
        for output in (svg_path, png_path):
            if not output.is_file():
                errors.append(f"missing rendered artifact: {output.relative_to(repo_root)}")
            elif output.stat().st_mtime < d2_path.stat().st_mtime:
                errors.append(f"rendered artifact older than D2 source: {output.relative_to(repo_root)}")
    return errors


def validate(repo_root: Path, strict: bool) -> list[str]:
    wiki_root = repo_root / "wiki"
    errors: list[str] = []
    for rel in REQUIRED_WIKI_FILES:
        if not (wiki_root / rel).is_file():
            errors.append(f"missing wiki file: wiki/{rel}")
    errors.extend(validate_components(repo_root, strict))
    errors.extend(validate_architecture(repo_root))
    errors.extend(validate_review_token(repo_root))
    errors.extend(validate_generated_diagrams(repo_root))
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
