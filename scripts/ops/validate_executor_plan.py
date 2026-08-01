#!/usr/bin/env python3
"""Validate CARE controller executor-plan isolation and parallel wave safety."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

PATH_FIELDS = ("branch_name", "worktree_path", "result_dir", "runtime_output_root", "slurm_job_namespace", "lock_path", "log_path")


def load_schema() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "prompts" / "schemas" / "executor_plan.schema.yaml"
    if not path.is_file():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def schema_list(key: str, default: list[str]) -> list[str]:
    value = load_schema().get(key)
    if isinstance(value, list):
        return [str(item) for item in value]
    return default


def valid_lanes() -> set[str]:
    return set(schema_list("valid_lanes", ["myops", "cine", "shared", "tooling"]))


def required_executor_fields() -> list[str]:
    return schema_list(
        "required_executor_fields",
        [
            "id",
            "lane",
            "wave",
            "prompt_path",
            "result_dir",
            "runtime_output_root",
            "slurm_job_namespace",
            "lock_path",
            "log_path",
            "merge_order",
            "required_completion_file",
            "required_completion_token",
        ],
    )


def slurm_executor_required_fields() -> list[str]:
    return schema_list("slurm_executor_required_fields", ["retry_policy", "slurm_dependency_policy", "preflight", "retry_ledger_path"])


def retry_policy_required_fields() -> list[str]:
    return schema_list(
        "retry_policy_required_fields",
        [
            "operational_retry_allowed",
            "same_executor_attempt",
            "max_startup_retries",
            "max_preemption_retries",
            "max_unknown_retries",
            "require_same_code_hash",
            "require_same_config_hash",
            "require_same_split_hash",
            "failed_attempt_training_credit",
        ],
    )


def preflight_required_fields() -> list[str]:
    return schema_list("preflight_required_fields", ["required", "command", "receipt_path"])


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
                mapping: dict[str, Any] = {}
                while idx < len(lines):
                    nested_line = lines[idx]
                    if not nested_line.strip() or nested_line.lstrip().startswith("#"):
                        idx += 1
                        continue
                    if nested_line.startswith("      - "):
                        values.append(str(parse_scalar(nested_line[8:])))
                        idx += 1
                        continue
                    if nested_line.startswith("      ") and ":" in nested_line:
                        nested_key, nested_value = nested_line[6:].split(":", 1)
                        mapping[nested_key.strip()] = parse_scalar(nested_value)
                        idx += 1
                        continue
                    break
                entry[field] = mapping if mapping else values
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


def as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def path_overlap(left: str, right: str) -> bool:
    if not left or not right:
        return False
    lp = Path(normalized_path(left))
    rp = Path(normalized_path(right))
    return lp == rp or lp in rp.parents or rp in lp.parents


def is_slurm_executor(item: dict[str, Any]) -> bool:
    return bool(item.get("slurm_dependency_chain")) or bool(item.get("finalizer_dependency_policy")) or bool(item.get("slurm_required"))


def validate_slurm_retry_contract(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    eid = str(item.get("id"))
    if not is_slurm_executor(item):
        return errors

    for field in slurm_executor_required_fields():
        if field not in item or item.get(field) in (None, "", []):
            errors.append(f"{eid}: Slurm executor missing {field}")

    retry = as_mapping(item.get("retry_policy"))
    for field in retry_policy_required_fields():
        if field not in retry:
            errors.append(f"{eid}: retry_policy missing {field}")
    for field in ("operational_retry_allowed", "same_executor_attempt", "require_same_code_hash", "require_same_config_hash", "require_same_split_hash"):
        if retry.get(field) is not True:
            errors.append(f"{eid}: retry_policy.{field} must be true")
    for field in ("max_startup_retries", "max_preemption_retries", "max_unknown_retries"):
        try:
            value = int(retry.get(field, -1))
        except (TypeError, ValueError):
            errors.append(f"{eid}: retry_policy.{field} must be an integer")
            continue
        if value < 0:
            errors.append(f"{eid}: retry_policy.{field} must be non-negative")
        if value > 5:
            errors.append(f"{eid}: retry_policy.{field} must be bounded <= 5")
    if str(retry.get("failed_attempt_training_credit", "")).lower() != "zero":
        errors.append(f"{eid}: retry_policy.failed_attempt_training_credit must be zero")

    dependency = as_mapping(item.get("slurm_dependency_policy"))
    if dependency.get("training_dependency") != "afterok":
        if dependency.get("training_dependency") == "afterany" and item.get("independent_of_upstream_success") is True and item.get("independent_dependency_reason"):
            pass
        else:
            errors.append(f"{eid}: slurm_dependency_policy.training_dependency must be afterok unless explicitly independent")
    if dependency.get("finalizer_dependency") != "afterany":
        errors.append(f"{eid}: slurm_dependency_policy.finalizer_dependency must be afterany")

    preflight = as_mapping(item.get("preflight"))
    for field in preflight_required_fields():
        if field not in preflight or preflight.get(field) in (None, ""):
            errors.append(f"{eid}: preflight missing {field}")
    if preflight.get("required") is not True:
        errors.append(f"{eid}: preflight.required must be true")

    result_dir = normalized_path(item.get("result_dir"))
    receipt_path = normalized_path(preflight.get("receipt_path"))
    retry_ledger_path = normalized_path(item.get("retry_ledger_path"))
    if result_dir and receipt_path and not path_overlap(result_dir, receipt_path):
        errors.append(f"{eid}: preflight receipt_path must be inside result_dir")
    if result_dir and retry_ledger_path and not path_overlap(result_dir, retry_ledger_path):
        errors.append(f"{eid}: retry_ledger_path must be inside result_dir")
    return errors


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
        waves = data.get("waves")
        if isinstance(waves, list) and waves:
            if int(data.get("executor_count", 1)) > 1 or int(data.get("executor_slots", 1)) > 1 or bool(data.get("parallel_execution_allowed", False)):
                return validate_controller_supervised_wave_plan(data, waves)
            return validate_single_executor_wave_plan(data, waves)
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
        if lane not in valid_lanes():
            errors.append(f"{eid}: lane must be one of {sorted(valid_lanes())}")
        wave = int(item.get("wave", 1))
        by_wave.setdefault(wave, []).append(item)
        for field in required_executor_fields():
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
        errors.extend(validate_slurm_retry_contract(item))
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


def validate_controller_supervised_wave_plan(data: dict[str, Any], waves: list[Any]) -> list[str]:
    """Validate controller-supervised wave plans with nested lane executors.

    This plan shape is used when a controller owns the lifecycle while multiple
    lane executors work in isolated local worktrees. It is distinct from the
    older top-level `executors:` schema and from the single-executor `waves:`
    schema below.
    """

    errors: list[str] = []
    if int(data.get("executor_count", 0)) < 2:
        errors.append("parallel waves plan requires executor_count >= 2")
    if int(data.get("executor_slots", 0)) < 2:
        errors.append("parallel waves plan requires executor_slots >= 2")
    if data.get("parallel_execution_allowed") is not True:
        errors.append("parallel waves plan requires parallel_execution_allowed=true")
    for field in ("task_key", "result_root", "runtime_root"):
        if not str(data.get(field, "")).strip():
            errors.append(f"parallel waves plan missing {field}")
    if not str(data.get("lock_root") or data.get("shared_lock_root") or "").strip():
        errors.append("parallel waves plan missing lock_root/shared_lock_root")

    worktrees = as_mapping(data.get("local_worktrees") or data.get("worktrees"))
    if not worktrees:
        errors.append("parallel waves plan missing local_worktrees/worktrees")
    seen_worktree_paths: dict[str, str] = {}
    for name, item in worktrees.items():
        tree = as_mapping(item)
        branch = str(tree.get("branch", "")).strip()
        path = normalized_path(tree.get("path"))
        if not branch:
            errors.append(f"worktree {name}: missing branch")
        if not path:
            errors.append(f"worktree {name}: missing path")
        if str(tree.get("remote_push", tree.get("remote_publication", "forbidden"))) != "forbidden":
            errors.append(f"worktree {name}: remote publication must be forbidden")
        for other_name, other_path in seen_worktree_paths.items():
            if path_overlap(path, other_path):
                errors.append(f"worktree {name}: path conflicts with {other_name}")
        seen_worktree_paths[str(name)] = path

    seen_waves: set[str] = set()
    nested_executors: list[dict[str, Any]] = []
    for idx, wave in enumerate(waves):
        if not isinstance(wave, dict):
            errors.append(f"wave[{idx}] must be a mapping")
            continue
        wave_id = str(wave.get("wave_id", "")).strip()
        if not wave_id:
            errors.append(f"wave[{idx}] missing wave_id")
            continue
        if wave_id in seen_waves:
            errors.append(f"duplicate wave_id: {wave_id}")
        for dep in as_list(wave.get("dependencies")):
            if dep and dep not in seen_waves:
                errors.append(f"{wave_id}: dependency {dep} is not an earlier wave")
        seen_waves.add(wave_id)
        if wave.get("mode") in (None, ""):
            errors.append(f"{wave_id}: missing mode")
        if wave.get("completion_condition") in (None, ""):
            errors.append(f"{wave_id}: missing completion_condition")
        if "failure_token" in wave and not str(wave.get("failure_token", "")).strip():
            errors.append(f"{wave_id}: empty failure_token")

        executors_in_wave = wave.get("executors")
        if executors_in_wave is not None:
            if not isinstance(executors_in_wave, list) or not executors_in_wave:
                errors.append(f"{wave_id}: executors must be a non-empty list")
            else:
                for executor in executors_in_wave:
                    if not isinstance(executor, dict):
                        errors.append(f"{wave_id}: executor entry must be a mapping")
                        continue
                    nested = dict(executor)
                    nested["_wave_id"] = wave_id
                    nested_executors.append(nested)

        if "claim_protocol" in wave or "interactive_takeover_loop" in wave:
            claim = as_mapping(wave.get("claim_protocol"))
            if not str(claim.get("atomic_claim_root", "")).strip():
                errors.append(f"{wave_id}: claim_protocol missing atomic_claim_root")
            if claim.get("queue_and_interactive_same_lane_duplicate_forbidden") is not True:
                errors.append(f"{wave_id}: duplicate queue/interactive lane must be forbidden")
            if str(wave.get("queue_partition", "")).strip() and str(wave.get("queue_partition")).strip() != "htzhulab":
                errors.append(f"{wave_id}: queue_partition must be htzhulab")
            resources = as_mapping(wave.get("queue_resources"))
            for field in ("gpu", "cpu", "memory_gb", "walltime_hours"):
                if field not in resources:
                    errors.append(f"{wave_id}: queue_resources missing {field}")
            if not as_list(wave.get("interactive_takeover_loop")):
                errors.append(f"{wave_id}: missing interactive_takeover_loop")

    if not nested_executors:
        errors.append("parallel waves plan must define nested executors in at least one wave")

    seen_executor_ids: set[str] = set()
    seen_scopes: dict[str, list[str]] = {}
    for executor in nested_executors:
        wave_id = str(executor.get("_wave_id", "wave"))
        eid = str(executor.get("executor_id", "")).strip()
        if not eid:
            errors.append(f"{wave_id}: nested executor missing executor_id")
            continue
        if eid in seen_executor_ids:
            errors.append(f"duplicate executor_id: {eid}")
        seen_executor_ids.add(eid)
        worktree_name = str(executor.get("worktree", "")).strip()
        if worktree_name not in worktrees:
            errors.append(f"{eid}: unknown worktree {worktree_name}")
        write_scope = as_list(executor.get("write_scope"))
        if not write_scope:
            errors.append(f"{eid}: missing write_scope")
        for other_id, other_scope in seen_scopes.items():
            if scopes_overlap(write_scope, other_scope):
                errors.append(f"{eid}: write_scope overlaps with {other_id}")
        seen_scopes[eid] = write_scope
        if not as_list(executor.get("implementation_gate") or executor.get("required_preflight")):
            errors.append(f"{eid}: missing implementation_gate/required_preflight")

    return errors


def validate_single_executor_wave_plan(data: dict[str, Any], waves: list[Any]) -> list[str]:
    """Validate the sequential `waves:` plan shape used by controller tasks.

    Parallel executor plans still use the stricter `executors:` isolation
    schema above. This branch exists for single-executor controller plans whose
    task graph is wave-ordered but not split across separate worktrees.
    """

    errors: list[str] = []
    if int(data.get("executor_count", 1)) != 1:
        errors.append("waves plan is allowed only for executor_count=1")
    if int(data.get("executor_slots", 1)) != 1:
        errors.append("waves plan is allowed only for executor_slots=1")
    if bool(data.get("parallel_execution_allowed", False)):
        errors.append("waves plan is allowed only when parallel_execution_allowed=false")
    if not str(data.get("result_root", "")).strip():
        errors.append("waves plan missing result_root")

    seen: set[str] = set()
    for idx, wave in enumerate(waves):
        if not isinstance(wave, dict):
            errors.append(f"wave[{idx}] must be a mapping")
            continue
        wave_id = str(wave.get("wave_id", "")).strip()
        if not wave_id:
            errors.append(f"wave[{idx}] missing wave_id")
            continue
        if wave_id in seen:
            errors.append(f"duplicate wave_id: {wave_id}")
        seen.add(wave_id)
        for field in ("executor_id", "write_scope", "required_outputs", "completion_conditions", "failure_action"):
            value = wave.get(field)
            if value in (None, "", []):
                errors.append(f"{wave_id}: missing {field}")
        if not isinstance(wave.get("write_scope"), list):
            errors.append(f"{wave_id}: write_scope must be a list")
        if not isinstance(wave.get("required_outputs"), list):
            errors.append(f"{wave_id}: required_outputs must be a list")
        if not isinstance(wave.get("completion_conditions"), list):
            errors.append(f"{wave_id}: completion_conditions must be a list")
        for dep in as_list(wave.get("dependencies")):
            if dep and dep not in seen:
                errors.append(f"{wave_id}: dependency {dep} is not an earlier wave")
        if "routing" in wave:
            routing = as_mapping(wave.get("routing"))
            for field in ("primary_partition", "partitions", "require_atomic_winner_lock", "require_isolated_attempt_directories"):
                if routing.get(field) in (None, "", []):
                    errors.append(f"{wave_id}: routing missing {field}")
            if routing.get("require_atomic_winner_lock") is not True:
                errors.append(f"{wave_id}: routing.require_atomic_winner_lock must be true")
            if routing.get("require_isolated_attempt_directories") is not True:
                errors.append(f"{wave_id}: routing.require_isolated_attempt_directories must be true")
        if "retry_policy" in wave:
            retry = as_mapping(wave.get("retry_policy"))
            for field in ("max_startup_retries", "max_preemption_retries", "max_unknown_retries"):
                if field not in retry:
                    errors.append(f"{wave_id}: retry_policy missing {field}")

    finalizer = as_mapping(data.get("finalizer"))
    if finalizer:
        if finalizer.get("dependency") != "afterany":
            errors.append("finalizer.dependency must be afterany")
        if not str(finalizer.get("required_state_file", "")).strip():
            errors.append("finalizer missing required_state_file")
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
