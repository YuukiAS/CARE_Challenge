#!/usr/bin/env python3
"""Validate CARE controller executor-plan isolation and parallel wave safety."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

VALID_LANES = {"myops", "cine", "shared", "tooling"}
PATH_FIELDS = ("branch_name", "worktree_path", "result_dir", "runtime_output_root", "slurm_job_namespace", "lock_path", "log_path")


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in ("", "null", "None"):
        return None
    if value == "[]":
        return []
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def load_executor_plan_without_pyyaml(text: str) -> dict[str, Any]:
    """Parse the narrow YAML subset used by CARE executor plans.

    This fallback is intentionally small: it supports top-level scalars and the
    `executors:` list of mappings with scalar or list values. Full YAML remains
    delegated to PyYAML when available.
    """

    data: dict[str, Any] = {}
    lines = text.splitlines()
    idx = 0
    while idx < len(lines):
        raw = lines[idx]
        idx += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith(" ") or ":" not in raw:
            raise ValueError(f"unsupported top-level YAML line: {raw!r}")
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key != "executors":
            data[key] = parse_scalar(value)
            continue
        executors: list[dict[str, Any]] = []
        while idx < len(lines):
            raw = lines[idx]
            if not raw.strip() or raw.lstrip().startswith("#"):
                idx += 1
                continue
            if not raw.startswith("  "):
                break
            if not raw.startswith("  - "):
                raise ValueError(f"unsupported executor list line: {raw!r}")
            entry: dict[str, Any] = {}
            item_text = raw[4:]
            idx += 1
            if item_text:
                if ":" not in item_text:
                    raise ValueError(f"unsupported executor item: {raw!r}")
                item_key, item_value = item_text.split(":", 1)
                entry[item_key.strip()] = parse_scalar(item_value)
            while idx < len(lines):
                raw = lines[idx]
                if not raw.strip() or raw.lstrip().startswith("#"):
                    idx += 1
                    continue
                if raw.startswith("  - ") or not raw.startswith("    "):
                    break
                field_text = raw[4:]
                if ":" not in field_text:
                    raise ValueError(f"unsupported executor field: {raw!r}")
                field, field_value = field_text.split(":", 1)
                field = field.strip()
                field_value = field_value.strip()
                idx += 1
                if field_value:
                    entry[field] = parse_scalar(field_value)
                    continue
                values: list[str] = []
                while idx < len(lines):
                    list_line = lines[idx]
                    if not list_line.strip() or list_line.lstrip().startswith("#"):
                        idx += 1
                        continue
                    if not list_line.startswith("      - "):
                        break
                    values.append(str(parse_scalar(list_line[8:])))
                    idx += 1
                entry[field] = values
            executors.append(entry)
        data[key] = executors
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:  # pragma: no cover - depends on local environment
        data = load_executor_plan_without_pyyaml(path.read_text(encoding="utf-8"))
    else:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("executor plan must be a mapping")
    return data


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def normalized_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return str(Path(text).expanduser())


def path_overlap(left: str, right: str) -> bool:
    if not left or not right:
        return False
    lp = Path(normalized_path(left))
    rp = Path(normalized_path(right))
    return lp == rp or lp in rp.parents or rp in lp.parents


def scopes_overlap(left: list[str], right: list[str]) -> bool:
    for lpath in left:
        for rpath in right:
            if path_overlap(lpath, rpath):
                return True
    return False


def build_dependency_graph(executors: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {str(item.get("id")): as_list(item.get("depends_on")) for item in executors}


def find_cycle(graph: dict[str, list[str]]) -> list[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> list[str]:
        if node in visiting:
            return stack[stack.index(node) :] + [node] if node in stack else [node]
        if node in visited:
            return []
        visiting.add(node)
        stack.append(node)
        for dep in graph.get(node, []):
            cycle = visit(dep)
            if cycle:
                return cycle
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return []

    for node in graph:
        cycle = visit(node)
        if cycle:
            return cycle
    return []


def validate_plan(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    executors = data.get("executors")
    if not isinstance(executors, list) or not executors:
        return ["executor plan must define non-empty executors list"]
    max_parallel = int(data.get("max_parallel", 1))
    if max_parallel < 1:
        errors.append("max_parallel must be >= 1")
    ids: set[str] = set()
    by_wave: dict[int, list[dict[str, Any]]] = {}
    seen_values: dict[str, dict[str, str]] = {field: {} for field in PATH_FIELDS}
    merge_orders: dict[int, str] = {}
    for item in executors:
        if not isinstance(item, dict):
            errors.append("each executor entry must be a mapping")
            continue
        eid = str(item.get("id", "")).strip()
        if not eid:
            errors.append("executor missing id")
            continue
        if eid in ids:
            errors.append(f"duplicate executor id: {eid}")
        ids.add(eid)
        lane = str(item.get("lane", "")).strip().lower()
        if lane not in VALID_LANES:
            errors.append(f"{eid}: lane must be one of {sorted(VALID_LANES)}")
        wave = int(item.get("wave", 1))
        by_wave.setdefault(wave, []).append(item)
        for field in (
            "prompt_path",
            "result_dir",
            "runtime_output_root",
            "slurm_job_namespace",
            "merge_order",
            "required_completion_file",
            "required_completion_token",
        ):
            if not str(item.get(field, "")).strip():
                errors.append(f"{eid}: missing {field}")
        if lane in {"myops", "cine", "shared"} and not as_list(item.get("write_scope")):
            errors.append(f"{eid}: code-writing executor must define non-empty write_scope")
        try:
            merge_order = int(item.get("merge_order"))
            if merge_order in merge_orders:
                errors.append(f"duplicate merge_order {merge_order}: {merge_orders[merge_order]} and {eid}")
            merge_orders[merge_order] = eid
        except (TypeError, ValueError):
            errors.append(f"{eid}: merge_order must be an integer")
        for field in PATH_FIELDS:
            value = normalized_path(item.get(field))
            if not value:
                continue
            for other_id, other_value in seen_values[field].items():
                if field == "branch_name":
                    conflict = value == other_value
                else:
                    conflict = path_overlap(value, other_value)
                if conflict:
                    errors.append(f"{eid}: {field} conflicts with {other_id}")
            seen_values[field][eid] = value
        if str(item.get("isolation_mode", "")) == "separate_worktree":
            if not str(item.get("branch_name", "")).strip() or not str(item.get("worktree_path", "")).strip():
                errors.append(f"{eid}: separate_worktree requires branch_name and worktree_path")
    cycle = find_cycle(build_dependency_graph([item for item in executors if isinstance(item, dict)]))
    if cycle:
        errors.append("dependency cycle: " + " -> ".join(cycle))
    for wave, entries in by_wave.items():
        parallel_entries = [entry for entry in entries if bool(entry.get("can_run_parallel", False))]
        if len(entries) > max_parallel:
            errors.append(f"wave {wave}: executor count exceeds max_parallel")
        for entry in entries:
            eid = str(entry.get("id"))
            for dep in as_list(entry.get("depends_on")):
                if dep not in ids:
                    errors.append(f"{eid}: depends_on unknown executor {dep}")
                dep_wave = next((int(other.get("wave", 1)) for other in executors if other.get("id") == dep), None)
                if dep_wave is not None and dep_wave >= int(entry.get("wave", 1)):
                    errors.append(f"{eid}: dependency {dep} is not in an earlier wave")
        for idx, left in enumerate(parallel_entries):
            for right in parallel_entries[idx + 1 :]:
                lid = str(left.get("id"))
                rid = str(right.get("id"))
                if scopes_overlap(as_list(left.get("write_scope")), as_list(right.get("write_scope"))):
                    errors.append(f"wave {wave}: write_scope overlap between {lid} and {rid}")
                left_lane = str(left.get("lane", "")).lower()
                right_lane = str(right.get("lane", "")).lower()
                if {left_lane, right_lane} == {"myops", "cine"}:
                    if not left.get("isolation_proof") or not right.get("isolation_proof"):
                        errors.append(f"wave {wave}: MyoPS/Cine parallel execution requires explicit isolation_proof")
                    if not (bool(left.get("can_run_parallel")) and bool(right.get("can_run_parallel"))):
                        errors.append(f"wave {wave}: MyoPS/Cine same-wave execution requires both entries to opt into parallel execution")
        for entry in parallel_entries:
            forbidden = set(as_list(entry.get("shared_files_forbidden")))
            writes = set(as_list(entry.get("write_scope")))
            if any(path_overlap(forbid, write) for forbid in forbidden for write in writes):
                errors.append(f"{entry.get('id')}: write_scope includes forbidden shared files")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args(argv)
    try:
        errors = validate_plan(load_yaml(args.plan))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("executor plan validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
