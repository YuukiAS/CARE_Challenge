#!/usr/bin/env python3
"""Validate CARE architecture wiki, component table, and generated diagrams."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
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
HISTORY_VERSION_RE = re.compile(r"^M[0-9]{2,}$")
HISTORY_REQUIRED_FILES = ("README.md", "snapshot.yaml", "COMPONENTS.csv", "architecture.yaml", "components", "figures")
HISTORY_COMPONENTS = (
    "availability-no-t2",
    "retrieval-dictionary",
    "prototype-memory",
    "anatomy-prior",
    "proposal",
    "refiner",
    "arbitration",
    "losses",
    "checkpoint-selection",
    "training-evidence",
    "cine-temporal",
)
REQUIRED_CURRENT_COMPONENTS = {
    "inputs_availability",
    "modality_stems_encoders",
    "retrieval_dictionary",
    "router_pattern_sip",
    "prototype_memory",
    "anatomy_prior",
    "scar_proposal",
    "edema_proposal",
    "scar_refiner",
    "edema_refiner",
    "no_t2_safety",
    "arbitration_final_output",
    "losses",
    "checkpoint_selection",
    "cine_temporal",
    "controller_continuity",
    "mapper_wiki_observability",
}

FORBIDDEN_HISTORY_DIAGRAM_TOKENS = (
    "历史组件关系",
    "component_delta",
    "component delta",
    "COMPONENT_DELTA",
)


def discover_history_versions(repo_root: Path) -> list[str]:
    history_root = repo_root / "wiki" / "history"
    if not history_root.is_dir():
        return []
    versions: list[str] = []
    for path in sorted(history_root.iterdir()):
        if not path.is_dir() or not HISTORY_VERSION_RE.match(path.name):
            continue
        if all((path / rel).exists() for rel in HISTORY_REQUIRED_FILES):
            versions.append(path.name)
    return versions


def parse_yaml_ids(text: str, key: str) -> set[str]:
    inside = False
    ids: set[str] = set()
    for line in text.splitlines():
        if re.match(rf"^{re.escape(key)}\s*:", line):
            inside = True
            continue
        if inside and re.match(r"^[A-Za-z_][A-Za-z0-9_-]*\s*:", line):
            break
        match = re.match(r"\s*-\s+id\s*:\s*[\"']?([A-Za-z0-9_.-]+)[\"']?", line)
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
        if cid in {"controller_supervision", "controller_continuity", "mapper_wiki_observability"}:
            if current != "partial" or evidence != "unverified":
                errors.append(f"{cid}: must remain current_status=partial and evidence_status=unverified until real controller runtime evidence exists")
    ids = {row.get("component_id", "") for row in rows}
    missing = REQUIRED_CURRENT_COMPONENTS - ids
    if missing:
        errors.append("COMPONENTS.csv missing required current components: " + ", ".join(sorted(missing)))
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
    if f"review_token: {EXPECTED_M9_REVIEW_TOKEN}" not in text and f'review_token: "{EXPECTED_M9_REVIEW_TOKEN}"' not in text:
        errors.append("architecture.yaml review_token does not match current M9 follow-up review token")
    comp_path = repo_root / "wiki" / "COMPONENTS.csv"
    if comp_path.is_file():
        comp_ids = {row.get("component_id", "") for row in csv.DictReader(comp_path.read_text(encoding="utf-8").splitlines())}
        if node_ids != comp_ids:
            errors.append(
                "architecture.yaml node IDs must match COMPONENTS.csv component IDs exactly; "
                f"missing_in_arch={sorted(comp_ids - node_ids)} missing_in_components={sorted(node_ids - comp_ids)}"
            )
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
        if stem in {"model-current", "model-gap"}:
            arch_ids = parse_yaml_ids((repo_root / "wiki" / "architecture.yaml").read_text(encoding="utf-8"), "nodes")
            for cid in arch_ids:
                if f"{cid}:" not in d2_text:
                    errors.append(f"{stem}.d2 missing component node id: {cid}")
        for output in (svg_path, png_path):
            if not output.is_file():
                errors.append(f"missing rendered artifact: {output.relative_to(repo_root)}")
            elif output.stat().st_mtime < d2_path.stat().st_mtime:
                errors.append(f"rendered artifact older than D2 source: {output.relative_to(repo_root)}")
    return errors


def validate_writing_receipt(repo_root: Path) -> list[str]:
    path = repo_root / "wiki" / "writing_skill_receipt.json"
    if not path.is_file():
        return ["missing wiki/writing_skill_receipt.json"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"writing_skill_receipt.json invalid JSON: {exc}"]
    skills = data.get("skills", [])
    names = {item.get("skill_name") for item in skills if isinstance(item, dict)}
    errors: list[str] = []
    if "chinese-prose" not in names:
        errors.append("writing_skill_receipt missing global chinese-prose skill")
    if "scientific-prose" not in names:
        errors.append("writing_skill_receipt missing global scientific-prose skill")
    for item in skills:
        source = Path(str(item.get("source_path_or_runtime_identifier", "")))
        if not source.is_file():
            errors.append(f"writing skill source missing: {source}")
    return errors


def validate_history(repo_root: Path) -> list[str]:
    errors: list[str] = []
    hist = repo_root / "wiki" / "history"
    for rel in ("README.md", "COMPARISON.md", "MIGRATION_MANIFEST.csv"):
        if not (hist / rel).is_file():
            errors.append(f"missing history file: wiki/history/{rel}")
    source_headings: set[tuple[str, str]] = set()
    archived_sources = {
        "TODO.md": hist / "M08" / "ORIGINAL_ANALYSIS.md",
        "todo-m10.md": hist / "M09" / "ORIGINAL_ANALYSIS.md",
    }
    for source_name, source_path in archived_sources.items():
        if not source_path.is_file():
            errors.append(f"missing archived original analysis: {source_path.relative_to(repo_root)}")
            continue
        for line in source_path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^#{1,3} ", line):
                source_headings.add((source_name, line.strip()))
    manifest_path = hist / "MIGRATION_MANIFEST.csv"
    covered: set[tuple[str, str]] = set()
    if manifest_path.is_file():
        for row in csv.DictReader(manifest_path.read_text(encoding="utf-8").splitlines()):
            covered.add((row.get("source_file", ""), row.get("source_heading", "")))
            dest = repo_root / str(row.get("destination_file", ""))
            if row.get("migration_status") != "migrated":
                errors.append(f"manifest row not migrated: {row.get('source_heading')}")
            if not dest.is_file():
                errors.append(f"manifest destination missing: {dest}")
    missing_headings = source_headings - covered
    for source, heading in sorted(missing_headings):
        errors.append(f"manifest missing heading from {source}: {heading}")
    if (repo_root / "TODO.md").exists() or (repo_root / "todo-m10.md").exists() or (repo_root / "TODO-M10.md").exists():
        errors.append("root TODO analysis files must be removed after wiki/history migration")
    generator = load_generator(repo_root)
    for version in discover_history_versions(repo_root):
        base = hist / version
        for rel in ("README.md", "snapshot.yaml", "COMPONENTS.csv", "architecture.yaml", "figures/architecture.d2", "figures/architecture.svg", "figures/architecture.png", "figures/gap.d2", "figures/gap.svg", "figures/gap.png"):
            if not (base / rel).is_file():
                errors.append(f"missing history file: wiki/history/{version}/{rel}")
        if version == "M09":
            for rel in ("figures/delta-from-M08.d2", "figures/delta-from-M08.svg", "figures/delta-from-M08.png"):
                if not (base / rel).is_file():
                    errors.append(f"missing history delta file: wiki/history/{version}/{rel}")
        if version in {"M08", "M09"}:
            for comp in HISTORY_COMPONENTS:
                comp_path = base / "components" / f"{comp}.md"
                if not comp_path.is_file():
                    errors.append(f"missing history component: wiki/history/{version}/components/{comp}.md")
        snapshot = base / "snapshot.yaml"
        if version in {"M08", "M09"} and snapshot.is_file() and "original_analysis_sha256" not in snapshot.read_text(encoding="utf-8"):
            errors.append(f"{snapshot.relative_to(repo_root)} missing original_analysis_sha256")
        try:
            sources = generator.generated_history_sources(repo_root, version)
        except Exception as exc:
            errors.append(f"failed to generate history sources for {version}: {exc}")
            continue
        for stem, source in sources.items():
            d2 = base / "figures" / f"{stem}.d2"
            if d2.is_file():
                d2_text = d2.read_text(encoding="utf-8")
                if d2_text != source:
                    errors.append(f"stale history D2: {d2.relative_to(repo_root)}")
                for token in FORBIDDEN_HISTORY_DIAGRAM_TOKENS:
                    if token in d2_text:
                        errors.append(f"history D2 contains placeholder token {token!r}: {d2.relative_to(repo_root)}")
    comparison = hist / "COMPARISON.md"
    if comparison.is_file():
        text = comparison.read_text(encoding="utf-8")
        if text.count("证据要求更严格") > 3:
            errors.append("history comparison still looks like generic placeholder")
        for token in ("M8 -> M9 实际代码变化", "对 M10 的约束", "loss wiring fixed", "dictionary", "Cine"):
            if token not in text:
                errors.append(f"history comparison missing required token: {token}")
    return errors


def validate(repo_root: Path, strict: bool, history: bool) -> list[str]:
    wiki_root = repo_root / "wiki"
    errors: list[str] = []
    for rel in REQUIRED_WIKI_FILES:
        if not (wiki_root / rel).is_file():
            errors.append(f"missing wiki file: wiki/{rel}")
    errors.extend(validate_components(repo_root, strict))
    errors.extend(validate_architecture(repo_root))
    errors.extend(validate_review_token(repo_root))
    errors.extend(validate_generated_diagrams(repo_root))
    errors.extend(validate_writing_receipt(repo_root))
    if history:
        errors.extend(validate_history(repo_root))
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
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args(argv)
    errors = validate(Path.cwd(), strict=args.strict, history=args.history)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("care architecture wiki validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
