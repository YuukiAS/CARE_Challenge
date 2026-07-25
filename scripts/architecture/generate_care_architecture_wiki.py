#!/usr/bin/env python3
"""Generate and check CARE architecture wiki diagram artifacts from YAML/CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FIGURES = ("model-current", "model-gap", "execution-flow")
HISTORY_VERSION_RE = re.compile(r"^M[0-9]{2,}$")
HISTORY_REQUIRED_FILES = ("README.md", "snapshot.yaml", "COMPONENTS.csv", "architecture.yaml", "components", "figures")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def parse_architecture(text: str) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]]:
    """Parse architecture.yaml.

    Prefer real YAML parsing because repo maintenance may use standard yaml.safe_dump,
    whose list indentation differs from the original hand-written file.
    """
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
    except Exception:
        loaded = None
    if isinstance(loaded, dict):
        raw_nodes = loaded.get("nodes", [])
        raw_edges = loaded.get("edges", [])
        nodes = [{str(k): str(v) for k, v in item.items()} for item in raw_nodes if isinstance(item, dict)] if isinstance(raw_nodes, list) else []
        edges = [{str(k): str(v) for k, v in item.items()} for item in raw_edges if isinstance(item, dict)] if isinstance(raw_edges, list) else []
        meta = {str(k): str(v) for k, v in loaded.items() if k not in {"nodes", "edges"}}
        return nodes, edges, meta

    nodes: list[dict[str, str]] = []
    edges: list[dict[str, str]] = []
    meta: dict[str, str] = {}
    section = ""
    current: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = line.strip()
        if item.startswith("- "):
            current = {}
            if section == "nodes":
                nodes.append(current)
            elif section == "edges":
                edges.append(current)
            item = item[2:]
        elif not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            if key in {"nodes", "edges"}:
                section = key
                current = None
            else:
                meta[key] = value.strip().strip("\"'")
            continue
        if current is not None and ":" in item:
            key, value = item.split(":", 1)
            current[key.strip()] = value.strip().strip("\"'")
    return nodes, edges, meta

def read_components(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    rows = csv.DictReader(path.read_text(encoding="utf-8").splitlines())
    return {row.get("component_id", ""): row for row in rows if row.get("component_id")}


def load_yaml_mapping(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def read_annotations(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        data: dict[str, object] = {}
        current_key: str | None = None
        current_item: dict[str, str] | None = None
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            if not raw.startswith(" ") and raw.rstrip().endswith(":"):
                current_key = raw.strip()[:-1]
                data[current_key] = []
                current_item = None
                continue
            if current_key and raw.startswith("  - "):
                current_item = {}
                cast_list = data.setdefault(current_key, [])
                if isinstance(cast_list, list):
                    cast_list.append(current_item)
                item_text = raw[4:]
                if ":" in item_text:
                    key, value = item_text.split(":", 1)
                    current_item[key.strip()] = value.strip().strip("\"'")
                continue
            if current_item is not None and raw.startswith("    ") and ":" in raw:
                key, value = raw.strip().split(":", 1)
                current_item[key.strip()] = value.strip().strip("\"'")
        return data
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def annotation_items(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            items.append({str(key): str(val) for key, val in item.items()})
    return items


def version_number(version: str) -> int:
    if not HISTORY_VERSION_RE.match(version):
        raise ValueError(f"invalid history version: {version}")
    return int(version[1:])


def previous_history_version(repo_root: Path, version: str) -> str | None:
    current = version_number(version)
    candidates = [item for item in discover_history_versions(repo_root) if version_number(item) < current]
    if not candidates:
        return None
    return max(candidates, key=version_number)


def q(value: str) -> str:
    normalized = value.replace("\\\\n", "\n").replace("\\n", "\n")
    return normalized.replace('"', '\\"').replace("\n", "\\n")


def status_style(status: str, evidence: str = "") -> str:
    status = status.lower()
    evidence = evidence.lower()
    if status in {"legacy", "disabled"}:
        return "style.stroke: \"#6b7280\"\n  style.fill: \"#f3f4f6\""
    if status in {"partial", "scaffold"} or evidence in {"unverified", "stale", "missing"}:
        return "style.stroke-dash: 5\n  style.fill: \"#fff7e6\""
    if status == "implemented" and evidence == "verified":
        return "style.fill: \"#e8f5e9\""
    return "style.stroke-dash: 3\n  style.fill: \"#eef1f8\""


def component_for_node(node: dict[str, str], components: dict[str, dict[str, str]]) -> dict[str, str]:
    node_id = node.get("id", "")
    if node_id in components:
        return components[node_id]
    for row in components.values():
        if node_id in row.get("component_id", "") or node_id in row.get("role", "").lower().replace(" ", "_"):
            return row
    return {}


def provenance(meta: dict[str, str], arch_text: str, comp_text: str) -> str:
    digest = hashlib.sha256((arch_text + "\n" + comp_text).encode("utf-8")).hexdigest()[:16]
    return (
        f"generated_from: architecture.yaml + COMPONENTS.csv\\n"
        f"review_token: {meta.get('review_token', 'UNKNOWN')}\\n"
        f"source_hash: {digest}"
    )


def delta_source_hash(prev_arch: str, prev_comp: str, curr_arch: str, curr_comp: str) -> str:
    return hashlib.sha256(
        (prev_arch + "\n" + prev_comp + "\n---CURRENT---\n" + curr_arch + "\n" + curr_comp).encode("utf-8")
    ).hexdigest()[:16]


def summarize_changed_components(
    previous_components: dict[str, dict[str, str]],
    current_components: dict[str, dict[str, str]],
    field: str,
) -> list[str]:
    changes: list[str] = []
    for cid in sorted(set(previous_components) & set(current_components)):
        old = previous_components[cid].get(field, "")
        new = current_components[cid].get(field, "")
        if old != new:
            changes.append(f"{cid}: {old or 'empty'} -> {new or 'empty'}")
    return changes


def compact_items(items: list[str], empty: str) -> str:
    if not items:
        return empty
    if len(items) <= 6:
        return "\n".join(items)
    return "\n".join(items[:6] + [f"... +{len(items) - 6} more"])


def render_delta_from_previous(
    repo_root: Path,
    previous: str,
    current: str,
    current_meta: dict[str, str],
    current_arch_text: str,
    current_comp_text: str,
) -> str:
    prev_base = repo_root / "wiki" / "history" / previous
    prev_arch_text = (prev_base / "architecture.yaml").read_text(encoding="utf-8")
    prev_comp_text = (prev_base / "COMPONENTS.csv").read_text(encoding="utf-8")
    prev_nodes, _prev_edges, prev_meta = parse_architecture(prev_arch_text)
    curr_nodes, _curr_edges, _curr_meta = parse_architecture(current_arch_text)
    prev_components = read_components(prev_base / "COMPONENTS.csv")
    curr_components = read_components(repo_root / "wiki" / "history" / current / "COMPONENTS.csv")
    prev_ids = set(prev_components)
    curr_ids = set(curr_components)
    prev_node_ids = {node.get("id", "") for node in prev_nodes if node.get("id")}
    curr_node_ids = {node.get("id", "") for node in curr_nodes if node.get("id")}
    source_changes: list[str] = []
    for cid in sorted(prev_ids & curr_ids):
        old = f"{prev_components[cid].get('source_file', '')}::{prev_components[cid].get('symbol', '')}"
        new = f"{curr_components[cid].get('source_file', '')}::{curr_components[cid].get('symbol', '')}"
        if old != new:
            source_changes.append(f"{cid}: {old} -> {new}")
    review_old = prev_meta.get("review_token", "UNKNOWN")
    review_new = current_meta.get("review_token", "UNKNOWN")
    digest = delta_source_hash(prev_arch_text, prev_comp_text, current_arch_text, current_comp_text)
    node_labels = {
        "source_hash": f"delta source\n{previous} + {current}\nsource_hash: {digest}",
        "added_components": "新增组件\n" + compact_items(sorted(curr_ids - prev_ids), "none"),
        "removed_components": "删除/disabled 组件\n" + compact_items(sorted(prev_ids - curr_ids), "none"),
        "status_changes": "implemented/partial/scaffold 状态变化\n" + compact_items(summarize_changed_components(prev_components, curr_components, "current_status"), "none"),
        "evidence_changes": "evidence_status 变化\n" + compact_items(summarize_changed_components(prev_components, curr_components, "evidence_status"), "none"),
        "source_symbol_changes": "source/symbol 变化\n" + compact_items(source_changes, "none"),
        "final_output_changes": "final_output_effect 变化\n" + compact_items(summarize_changed_components(prev_components, curr_components, "final_output_effect"), "none"),
        "review_token_changes": f"review token 变化\n{review_old} -> {review_new}",
        "notes_changes": "主要 notes delta\n" + compact_items(summarize_changed_components(prev_components, curr_components, "notes"), "none"),
        "architecture_node_changes": "architecture.yaml 节点变化\nadded: "
        + (", ".join(sorted(curr_node_ids - prev_node_ids)) or "none")
        + "\nremoved: "
        + (", ".join(sorted(prev_node_ids - curr_node_ids)) or "none"),
    }
    meta_label = f"delta_from: {previous}\ndelta_to: {current}\nsource_hash: {digest}"
    lines = [
        "# Generated by scripts/architecture/generate_care_architecture_wiki.py",
        "direction: right",
        f'meta: "{q(meta_label)}"',
    ]
    for node_id, label in node_labels.items():
        lines.append(f'{node_id}: "{q(label)}" {{')
        lines.append("  style.stroke-dash: 4")
        lines.append("  style.fill: \"#fff7e6\"")
        lines.append("}")
    for source, target, label in [
        ("source_hash", "added_components", "component table diff"),
        ("source_hash", "removed_components", "component table diff"),
        ("added_components", "status_changes", "status review"),
        ("removed_components", "status_changes", "disabled/deleted impact"),
        ("status_changes", "evidence_changes", "evidence maturity"),
        ("evidence_changes", "source_symbol_changes", "implementation mapping"),
        ("source_symbol_changes", "final_output_changes", "runtime effect"),
        ("final_output_changes", "review_token_changes", "review boundary"),
        ("review_token_changes", "notes_changes", "planner constraints"),
        ("source_hash", "architecture_node_changes", "architecture.yaml diff"),
    ]:
        lines.append(f'{source} -> {target}: "{q(label)}"')
    return "\n".join(lines) + "\n"


def annotated_graph_source(
    meta_text: str,
    nodes: object,
    edges: object,
    direction: str = "right",
) -> str | None:
    if not isinstance(nodes, list) or not nodes:
        return None
    lines = [
        "# Generated by scripts/architecture/generate_care_architecture_wiki.py",
        f"direction: {direction}",
        f"meta: \"{q(meta_text)}\"",
    ]
    for item in nodes:
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("id", "")).strip()
        label = str(item.get("label", node_id))
        if not node_id:
            continue
        lines.append(f'{node_id}: "{q(label)}" {{')
        lines.append("  style.stroke-dash: 5")
        lines.append("  style.fill: \"#fff7e6\"")
        lines.append("}")
    if isinstance(edges, list):
        for item in edges:
            if not isinstance(item, dict):
                continue
            source = str(item.get("from", "")).strip()
            target = str(item.get("to", "")).strip()
            label = str(item.get("label", item.get("condition", "")))
            if source and target:
                lines.append(f'{source} -> {target}: "{q(label)}"')
    return "\n".join(lines) + "\n"


def render_model_current(nodes: list[dict[str, str]], edges: list[dict[str, str]], components: dict[str, dict[str, str]], meta_text: str) -> str:
    lines = [
        "# Generated by scripts/architecture/generate_care_architecture_wiki.py",
        "direction: right",
        f"meta: \"{q(meta_text)}\"",
    ]
    for node in nodes:
        node_id = node.get("id", "node")
        comp = component_for_node(node, components)
        status = node.get("current_status") or comp.get("current_status", "unknown")
        evidence = comp.get("evidence_status", "unverified")
        label = node.get("label", node_id)
        lines.append(f'{node_id}: "{q(label)}" {{')
        lines.append("  " + status_style(status, evidence).replace("\n", "\n  "))
        lines.append("}")
    node_ids = {node.get("id") for node in nodes}
    for edge in edges:
        source = edge.get("from", "")
        target = edge.get("to", "")
        if source in node_ids and target in node_ids:
            lines.append(f'{source} -> {target}: "{q(edge.get("condition", edge.get("kind", "")))}"')
    return "\n".join(lines) + "\n"


def render_model_gap(nodes: list[dict[str, str]], components: dict[str, dict[str, str]], meta_text: str) -> str:
    lines = [
        "# Generated by scripts/architecture/generate_care_architecture_wiki.py",
        "direction: down",
        f"meta: \"{q(meta_text)}\"",
    ]
    for node in nodes:
        node_id = node.get("id", "node")
        comp = component_for_node(node, components)
        current = comp.get("current_status") or node.get("current_status", "unknown")
        target = comp.get("target_status") or node.get("target_status", "unknown")
        evidence = comp.get("evidence_status", "unverified")
        label = f"{node.get('label', node_id)}\n当前: {current}\n目标: {target}\n证据: {evidence}"
        lines.append(f'{node_id}: "{q(label)}" {{')
        lines.append("  " + status_style(current, evidence).replace("\n", "\n  "))
        lines.append("}")
    return "\n".join(lines) + "\n"


def render_execution_flow(meta_text: str) -> str:
    lines = [
        "# Generated by scripts/architecture/generate_care_architecture_wiki.py",
        "direction: right",
        f"meta: \"{q(meta_text)}\"",
        'planner: "规划者\\nGPT task contract"',
        'controller: "controller\\nphase grounding"',
        'executor: "executor wave(s)\\nimplementation/jobs"',
        'mapper_draft: "mapper draft\\n架构快照"',
        'finalizer_a: "FINALIZER_A\\nSlurm accounting + aggregation"',
        'mapper_final: "mapper final\\nwiki/evidence reconciliation"',
        'finalizer_b: "FINALIZER_B\\nvalidators + local commit"',
        'reviewer: "独立 reviewer\\nreview.md"',
        'planner -> controller',
        'controller -> executor',
        'executor -> mapper_draft: implementation snapshot',
        'mapper_draft -> finalizer_a: job ids + runtime paths',
        'finalizer_a -> mapper_final: tracked evidence',
        'mapper_final -> finalizer_b',
        'finalizer_b -> reviewer: committed final packet',
    ]
    return "\n".join(lines) + "\n"


def generated_sources(repo_root: Path) -> dict[str, str]:
    arch_path = repo_root / "wiki" / "architecture.yaml"
    comp_path = repo_root / "wiki" / "COMPONENTS.csv"
    arch_text = arch_path.read_text(encoding="utf-8")
    comp_text = comp_path.read_text(encoding="utf-8")
    nodes, edges, meta = parse_architecture(arch_text)
    components = read_components(comp_path)
    meta_text = provenance(meta, arch_text, comp_text)
    return {
        "model-current": render_model_current(nodes, edges, components, meta_text),
        "model-gap": render_model_gap(nodes, components, meta_text),
        "execution-flow": render_execution_flow(meta_text),
    }


def generated_history_sources(repo_root: Path, version: str) -> dict[str, str]:
    if not HISTORY_VERSION_RE.match(version):
        raise ValueError(f"invalid history version: {version}")
    base = repo_root / "wiki" / "history" / version
    arch_path = base / "architecture.yaml"
    comp_path = base / "COMPONENTS.csv"
    arch_text = arch_path.read_text(encoding="utf-8")
    comp_text = comp_path.read_text(encoding="utf-8")
    nodes, edges, meta = parse_architecture(arch_text)
    components = read_components(comp_path)
    meta_text = provenance(meta, arch_text, comp_text)
    architecture_lines = [
        "# Generated by scripts/architecture/generate_care_architecture_wiki.py",
        "direction: right",
        f"meta: \"{q(meta_text)}\"",
    ]
    for node in nodes:
        comp = component_for_node(node, components)
        status = comp.get("current_status") or node.get("current_status", "unknown")
        evidence = comp.get("evidence_status", "unverified")
        architecture_lines.append(f'{node["id"]}: "{q(node.get("label", node["id"]))}" {{')
        architecture_lines.append("  " + status_style(status, evidence).replace("\n", "\n  "))
        architecture_lines.append("}")
    for edge in edges:
        architecture_lines.append(f'{edge.get("from")} -> {edge.get("to")}: {q(edge.get("condition", edge.get("kind", "")))}')
    gap_lines = [
        "# Generated by scripts/architecture/generate_care_architecture_wiki.py",
        "direction: right",
        f"meta: \"{q(meta_text)}\"",
    ]
    annotations = read_annotations(base / "annotations.yaml")
    gap_node_items = annotation_items(annotations.get("gap_nodes"))
    gap_edge_items = annotation_items(annotations.get("gap_edges"))
    if not gap_node_items:
        gap_node_items = [
            {"id": node.get("id", "node"), "label": f"{node.get('label', node.get('id', 'node'))}\n当前: {component_for_node(node, components).get('current_status', 'unknown')}\n证据: {component_for_node(node, components).get('evidence_status', 'unverified')}"}
            for node in nodes
        ]
    if not gap_edge_items:
        gap_edge_items = [
            {"from": edge.get("from", ""), "to": edge.get("to", ""), "label": edge.get("condition", edge.get("kind", ""))}
            for edge in edges
        ]
    for item in gap_node_items:
        node_id = item.get("id", "node")
        label = item.get("label", node_id)
        gap_lines.append(f'{node_id}: "{q(label)}" {{')
        gap_lines.append("  style.stroke-dash: 5")
        gap_lines.append("  style.fill: \"#fff7e6\"")
        gap_lines.append("}")
    for item in gap_edge_items:
        source = item.get("from", "")
        target = item.get("to", "")
        label = item.get("label", "")
        gap_lines.append(f'{source} -> {target}: "{q(label)}"')
    sources = {"architecture": "\n".join(architecture_lines) + "\n", "gap": "\n".join(gap_lines) + "\n"}
    delta_node_items = annotation_items(annotations.get("delta_nodes"))
    delta_edge_items = annotation_items(annotations.get("delta_edges"))
    previous = previous_history_version(repo_root, version)
    if previous is not None and delta_node_items:
        delta = [
            "# Generated by scripts/architecture/generate_care_architecture_wiki.py",
            "direction: down",
            f"meta: \"{q(meta_text)}\"",
        ]
        for item in delta_node_items:
            node_id = item.get("id", "node")
            label = item.get("label", node_id)
            delta.append(f'{node_id}: "{q(label)}" {{')
            delta.append("  style.stroke-dash: 4")
            delta.append("  style.fill: \"#fff7e6\"")
            delta.append("}")
        for item in delta_edge_items:
            source = item.get("from", "")
            target = item.get("to", "")
            label = item.get("label", "")
            delta.append(f'{source} -> {target}: "{q(label)}"')
        sources[f"delta-from-{previous}"] = "\n".join(delta) + "\n"
    elif previous is not None:
        sources[f"delta-from-{previous}"] = render_delta_from_previous(
            repo_root,
            previous,
            version,
            meta,
            arch_text,
            comp_text,
        )
    return sources


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


def render_outputs(repo_root: Path, stem: str, d2_path: Path, svg_path: Path, png_path: Path) -> list[str]:
    errors: list[str] = []
    d2 = shutil.which("d2")
    if not d2:
        return ["d2 executable not found"]
    convert = shutil.which("convert")
    cp = run([d2, str(d2_path), str(svg_path)], repo_root)
    if cp.returncode != 0:
        return [f"d2 svg render failed for {stem}: {cp.stderr.strip() or cp.stdout.strip()}"]
    cp = run([d2, str(d2_path), str(png_path)], repo_root)
    if cp.returncode == 0:
        return errors
    if not convert:
        return [f"d2 png render failed for {stem} and ImageMagick convert is unavailable: {cp.stderr.strip()}"]
    cp2 = run([convert, str(svg_path), str(png_path)], repo_root)
    if cp2.returncode != 0:
        errors.append(
            f"png render failed for {stem}: d2={cp.stderr.strip() or cp.stdout.strip()}; "
            f"convert={cp2.stderr.strip() or cp2.stdout.strip()}"
        )
    return errors


def check(repo_root: Path, sources: dict[str, str], figure_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    figure_dir = figure_dir or repo_root / "wiki" / "figures"
    for stem, source in sources.items():
        d2_path = figure_dir / f"{stem}.d2"
        svg_path = figure_dir / f"{stem}.svg"
        png_path = figure_dir / f"{stem}.png"
        if not d2_path.is_file():
            errors.append(f"missing generated D2 source: {d2_path}")
            continue
        if d2_path.read_text(encoding="utf-8") != source:
            errors.append(f"stale generated D2 source: {d2_path}")
        for output in (svg_path, png_path):
            if not output.is_file():
                errors.append(f"missing rendered artifact: {output}")
            elif output.stat().st_mtime < d2_path.stat().st_mtime:
                errors.append(f"rendered artifact older than generated D2 source: {output}")
    return errors


def write_and_render(repo_root: Path, sources: dict[str, str], figure_dir: Path | None = None) -> list[str]:
    figure_dir = figure_dir or repo_root / "wiki" / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for stem, source in sources.items():
        d2_path = figure_dir / f"{stem}.d2"
        svg_path = figure_dir / f"{stem}.svg"
        png_path = figure_dir / f"{stem}.png"
        d2_path.write_text(source, encoding="utf-8")
        errors.extend(render_outputs(repo_root, stem, d2_path, svg_path, png_path))
    return errors


def process_history(repo_root: Path, version: str, check_only: bool) -> list[str]:
    figure_dir = repo_root / "wiki" / "history" / version / "figures"
    sources = generated_history_sources(repo_root, version)
    return check(repo_root, sources, figure_dir) if check_only else write_and_render(repo_root, sources, figure_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check current artifacts without writing.")
    parser.add_argument("--current", action="store_true", help="Generate/check current wiki figures.")
    parser.add_argument("--history", help="Generate/check one history version such as a canonical milestone ID.")
    parser.add_argument("--check-all", action="store_true", help="Check current and all history versions.")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    required_inputs = [repo_root / "wiki" / "architecture.yaml", repo_root / "wiki" / "COMPONENTS.csv"]
    errors = [f"missing required input: {path}" for path in required_inputs if not path.is_file()]
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    if args.check_all:
        errors = check(repo_root, generated_sources(repo_root))
        for version in discover_history_versions(repo_root):
            errors.extend(process_history(repo_root, version, True))
    elif args.history:
        if not HISTORY_VERSION_RE.match(args.history):
            errors = [f"invalid history version: {args.history}"]
        else:
            errors = process_history(repo_root, args.history, args.check)
    else:
        sources = generated_sources(repo_root)
        errors = check(repo_root, sources) if args.check else write_and_render(repo_root, sources)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("care architecture wiki diagrams ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
