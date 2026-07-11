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
    nodes: list[dict[str, str]] = []
    edges: list[dict[str, str]] = []
    meta: dict[str, str] = {}
    section = ""
    current: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        top = line.split(":", 1)
        if not line.startswith(" ") and len(top) == 2:
            key = top[0].strip()
            value = top[1].strip()
            if key in {"nodes", "edges"}:
                section = key
                current = None
            else:
                meta[key] = value.strip("\"'")
            continue
        item = line.strip()
        if item.startswith("- "):
            current = {}
            if section == "nodes":
                nodes.append(current)
            elif section == "edges":
                edges.append(current)
            item = item[2:]
        if current is not None and ":" in item:
            key, value = item.split(":", 1)
            current[key.strip()] = value.strip().strip("\"'")
    return nodes, edges, meta


def read_components(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    rows = csv.DictReader(path.read_text(encoding="utf-8").splitlines())
    return {row.get("component_id", ""): row for row in rows if row.get("component_id")}


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
    lines = [
        "# Generated by scripts/architecture/generate_care_architecture_wiki.py",
        "direction: right",
        f'meta: "{q(f"delta_from: {previous}\\ndelta_to: {current}\\nsource_hash: {digest}")}"',
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
    if version == "M08":
        gap_nodes = [
            ("m8_anchor_centered", "M8 anchor-centered residual\nnnU-Net 仍像主角"),
            ("m8_dictionary_weak", "dictionary 有实现\n语义检索未闭环"),
            ("m8_proposal_refiner_weak", "proposal/refiner 有路径\nlesion formation 证据弱"),
            ("m8_loss_checkpoint_gap", "loss/checkpoint\n配置与证据不一致"),
            ("m8_cine_proxy", "Cine 只是 local proxy"),
            ("m8_next_constraint", "后续约束\n不能 route promotion"),
        ]
        gap_edges = [
            ("m8_anchor_centered", "m8_dictionary_weak", "SRR 被 anchor 稀释"),
            ("m8_dictionary_weak", "m8_proposal_refiner_weak", "检索未证明病灶收益"),
            ("m8_proposal_refiner_weak", "m8_loss_checkpoint_gap", "ROI/logit 因果不足"),
            ("m8_loss_checkpoint_gap", "m8_cine_proxy", "formal evidence 不足"),
            ("m8_cine_proxy", "m8_next_constraint", "只能诊断，不能晋级"),
        ]
    elif version == "M09":
        gap_nodes = [
            ("m9_fixed", "已修/更明确\nloss wiring\nSRR-main contract"),
            ("m9_dictionary_gap", "未闭环\ndictionary 仍偏 global\nPattern-SIP 仍 alias"),
            ("m9_memory_gap", "未闭环\nprototype memory helper\nhard-negative replay 不完整"),
            ("m9_refiner_gap", "未闭环\nproposal/refiner 因果证据不足"),
            ("m9_selection_gap", "仍需加固\ncheckpoint selection\nformal decision validator"),
            ("m9_cine_gap", "Cine 仍 local proxy\n不能救 MyoPS"),
            ("m9_m10_constraint", "M10 约束\n先证明机制贡献\n不能包装 overall success"),
        ]
        gap_edges = [
            ("m9_fixed", "m9_dictionary_gap", "修了 wiring，但检索贡献未证明"),
            ("m9_dictionary_gap", "m9_memory_gap", "representer 未形成病灶记忆"),
            ("m9_memory_gap", "m9_refiner_gap", "proposal/refiner 缺因果链"),
            ("m9_refiner_gap", "m9_selection_gap", "metrics 负面，选择仍需严格"),
            ("m9_selection_gap", "m9_cine_gap", "MyoPS/Cine 决策必须分离"),
            ("m9_cine_gap", "m9_m10_constraint", "system redesign 前必须读 history"),
        ]
    else:
        prefix = version.lower()
        gap_nodes = [
            (f"{prefix}_snapshot", f"{version} history snapshot\n来自当前 wiki 状态"),
            (f"{prefix}_component_status", "组件状态\n见 COMPONENTS.csv"),
            (f"{prefix}_evidence_status", "证据状态\n见 snapshot 与 review"),
            (f"{prefix}_later_status", "后续状态\n由 post-review reconciliation 更新"),
        ]
        gap_edges = [
            (f"{prefix}_snapshot", f"{prefix}_component_status", "component table"),
            (f"{prefix}_component_status", f"{prefix}_evidence_status", "evidence mapping"),
            (f"{prefix}_evidence_status", f"{prefix}_later_status", "review reconciliation"),
        ]
    for node_id, label in gap_nodes:
        gap_lines.append(f'{node_id}: "{q(label)}" {{')
        gap_lines.append("  style.stroke-dash: 5")
        gap_lines.append("  style.fill: \"#fff7e6\"")
        gap_lines.append("}")
    for source, target, label in gap_edges:
        gap_lines.append(f'{source} -> {target}: "{q(label)}"')
    sources = {"architecture": "\n".join(architecture_lines) + "\n", "gap": "\n".join(gap_lines) + "\n"}
    if version == "M09":
        delta = [
            "# Generated by scripts/architecture/generate_care_architecture_wiki.py",
            "direction: down",
            f"meta: \"{q(meta_text)}\"",
        ]
        deltas = [
            ("m8_anchor", "M8\nanchor-centered residual"),
            ("m9_srr_main", "M9\nSRR-main final output"),
            ("loss_wiring_fixed", "loss wiring fixed"),
            ("dictionary_global", "dictionary 仍 global"),
            ("pattern_sip_alias", "Pattern-SIP 仍 alias"),
            ("prototype_not_closed", "prototype memory 未完成闭环"),
            ("refiner_evidence_gap", "refiner causal evidence 不足"),
            ("checkpoint_incomplete", "checkpoint selection 仍不完整"),
            ("cine_local_proxy", "Cine 仍为 local proxy"),
            ("m10_constraint", "M10 前置约束\n机制贡献优先"),
        ]
        for node_id, label in deltas:
            delta.append(f'{node_id}: "{q(label)}" {{')
            delta.append("  style.stroke-dash: 4")
            delta.append("  style.fill: \"#fff7e6\"")
            delta.append("}")
        delta_edges = [
            ("m8_anchor", "m9_srr_main", "final-output strategy changed"),
            ("m9_srr_main", "loss_wiring_fixed", "配置/目标更可审计"),
            ("m9_srr_main", "dictionary_global", "主干增强后仍未局部检索"),
            ("dictionary_global", "pattern_sip_alias", "pattern 仍偏诊断命名"),
            ("dictionary_global", "prototype_not_closed", "memory 未进入闭环"),
            ("m9_srr_main", "refiner_evidence_gap", "ROI 因果证据不足"),
            ("loss_wiring_fixed", "checkpoint_incomplete", "选择规则仍需 validator"),
            ("checkpoint_incomplete", "cine_local_proxy", "Cine 仍单独阻塞"),
            ("cine_local_proxy", "m10_constraint", "不能包装 overall success"),
        ]
        for source, target, label in delta_edges:
            delta.append(f'{source} -> {target}: "{q(label)}"')
        sources["delta-from-M08"] = "\n".join(delta) + "\n"
    else:
        previous = previous_history_version(repo_root, version)
        if previous is not None:
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
    parser.add_argument("--history", help="Generate/check one history version, e.g. M10.")
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
