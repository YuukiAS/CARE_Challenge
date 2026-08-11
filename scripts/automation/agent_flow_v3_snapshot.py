#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SNAPSHOT_SCHEMA = "AGENT_FLOW_V3_SOURCE_SNAPSHOT_V1"
BUNDLE_SCHEMA = "AGENT_FLOW_V3_REVIEW_BUNDLE_V1"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return data


def git_value(repo: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def rel(repo: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo.resolve()))


def expand_paths(repo: Path, values: list[str]) -> list[str]:
    paths: list[str] = []
    for value in values:
        path = (repo / value).resolve()
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if not child.is_file():
                    continue
                if "__pycache__" in child.parts or child.name.endswith(".pyc"):
                    continue
                paths.append(rel(repo, child))
        elif path.is_file():
            paths.append(rel(repo, path))
        else:
            raise FileNotFoundError(value)
    return sorted(dict.fromkeys(paths))


def path_digest(repo: Path, paths: list[str]) -> dict[str, Any]:
    file_hashes = {path: sha_file(repo / path) for path in paths}
    digest = sha_bytes(json.dumps(file_hashes, sort_keys=True).encode("utf-8"))
    return {"digest_sha256": digest, "file_hashes": file_hashes}


def compute_review_target_id(stable_inputs: dict[str, Any]) -> str:
    allowed = {
        "request_nonce",
        "frozen_contract_sha256",
        "requirement_ledger_sha256",
        "implementation_critical_source_digest_sha256",
        "verifier_critical_source_digest_sha256",
    }
    canonical = {key: stable_inputs.get(key) for key in sorted(allowed)}
    return sha_bytes(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def build_source_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo_root.resolve()
    current = load_json(repo / args.current)
    requirement_ledger_path = repo / args.requirement_ledger
    implementation_paths = expand_paths(repo, args.implementation_path)
    verifier_paths = expand_paths(repo, args.verifier_path)
    implementation_digest = path_digest(repo, implementation_paths)
    verifier_digest = path_digest(repo, verifier_paths)
    requirement_ledger_sha = sha_file(requirement_ledger_path)
    stable_inputs = {
        "request_nonce": current.get("request_nonce"),
        "frozen_contract_sha256": current.get("frozen_contract_sha256"),
        "requirement_ledger_sha256": requirement_ledger_sha,
        "implementation_critical_source_digest_sha256": implementation_digest["digest_sha256"],
        "verifier_critical_source_digest_sha256": verifier_digest["digest_sha256"],
    }
    review_target_id = compute_review_target_id(stable_inputs)
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "task_id": current.get("task_id") or args.task_id,
        "request_nonce": current.get("request_nonce"),
        "frozen_contract_sha256": current.get("frozen_contract_sha256"),
        "requirement_ledger_path": args.requirement_ledger,
        "requirement_ledger_sha256": requirement_ledger_sha,
        "implementation_critical_source": implementation_digest,
        "verifier_critical_source": verifier_digest,
        "review_target_id": review_target_id,
        "review_target_inputs": stable_inputs,
        "git_locators": {
            "head_sha": git_value(repo, "rev-parse", "HEAD"),
            "branch": git_value(repo, "branch", "--show-current"),
            "origin_develop_sha": git_value(repo, "rev-parse", "origin/develop"),
        },
        "identity_policy": {
            "git_commits_are_locators_only": True,
            "controller_merge_current_receipt_ci_commits_do_not_change_review_target_id": True,
            "review_target_changes_only_when_contract_ledger_or_critical_source_content_changes": True,
        },
        "created_utc": now(),
    }
    write_json(repo / args.output, snapshot)
    return snapshot


def build_review_bundle(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo_root.resolve()
    snapshot_path = repo / args.snapshot
    snapshot = load_json(snapshot_path)
    evidence = {
        path: sha_file(repo / path)
        for path in args.evidence
        if (repo / path).is_file()
    }
    missing = sorted(path for path in args.evidence if not (repo / path).is_file())
    if missing:
        raise FileNotFoundError("missing review evidence: " + ",".join(missing))
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "task_id": snapshot.get("task_id"),
        "request_nonce": snapshot.get("request_nonce"),
        "frozen_contract_sha256": snapshot.get("frozen_contract_sha256"),
        "requirement_ledger_sha256": snapshot.get("requirement_ledger_sha256"),
        "review_target_id": snapshot.get("review_target_id"),
        "source_snapshot_path": args.snapshot,
        "source_snapshot_sha256": sha_file(snapshot_path),
        "evidence_sha256s": evidence,
        "ci_pass": bool(args.ci_pass),
        "heavy_verifier_status": args.heavy_verifier_status,
        "provenance_policy": {
            "evidence_bound_to_stable_source_snapshot": True,
            "receipt_only_changes_do_not_invalidate_heavy_verification": True,
            "runtime_and_ci_receipts_are_dag_children_not_identity_inputs": True,
        },
        "created_utc": now(),
    }
    write_json(repo / args.output, bundle)
    bundle["review_bundle_sha256"] = sha_file(repo / args.output)
    write_json(repo / args.output, bundle)
    return bundle


def validate_snapshot(args: argparse.Namespace) -> int:
    repo = args.repo_root.resolve()
    snapshot = load_json(repo / args.snapshot)
    stable_inputs = snapshot.get("review_target_inputs")
    if not isinstance(stable_inputs, dict):
        print("review_target_inputs_missing")
        return 2
    expected = compute_review_target_id(stable_inputs)
    if snapshot.get("review_target_id") != expected:
        print("review_target_id_mismatch")
        return 2
    return 0


def validate_bundle(args: argparse.Namespace) -> int:
    repo = args.repo_root.resolve()
    bundle = load_json(repo / args.bundle)
    snapshot = load_json(repo / str(bundle["source_snapshot_path"]))
    failures: list[str] = []
    if bundle.get("schema") != BUNDLE_SCHEMA:
        failures.append("schema")
    if bundle.get("review_target_id") != snapshot.get("review_target_id"):
        failures.append("review_target_id")
    if bundle.get("source_snapshot_sha256") != sha_file(repo / str(bundle["source_snapshot_path"])):
        failures.append("source_snapshot_sha256")
    for path, expected_sha in dict(bundle.get("evidence_sha256s", {})).items():
        evidence_path = repo / path
        if not evidence_path.is_file():
            failures.append(f"evidence_missing:{path}")
        elif sha_file(evidence_path) != expected_sha:
            failures.append(f"evidence_sha256:{path}")
    implementation_fingerprint_path = repo / "results/agent_flow_v3/care-ase-faithful/implementation/implementation_fingerprint.json"
    if implementation_fingerprint_path.is_file():
        implementation_fingerprint = load_json(implementation_fingerprint_path)
        forbidden_keys = {
            "runtime_receipt_manifest_sha256",
            "current_runtime_input_bundle_sha256",
            "current_runtime_identity_receipt_sha256",
            "executable_verifier_receipt_sha256",
            "transaction_gate_receipt_sha256",
        }
        if forbidden_keys.intersection(implementation_fingerprint):
            failures.append("implementation_fingerprint_self_referential_runtime_hash")
    if failures:
        print(json.dumps({"passed": False, "failures": failures}, indent=2, sort_keys=True))
        return 2
    print(json.dumps({"passed": True, "review_target_id": bundle.get("review_target_id")}, indent=2, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Agent-Flow v3 stable source snapshot and review bundle tools")
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("build-source-snapshot")
    q.add_argument("--repo-root", type=Path, default=Path("."))
    q.add_argument("--task-id", default="care-ase-faithful")
    q.add_argument("--current", default="automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json")
    q.add_argument("--requirement-ledger", default="automation/agent_flow_v3/tasks/care-ase-faithful/REQUIREMENT_LEDGER.json")
    q.add_argument("--implementation-path", action="append", required=True)
    q.add_argument("--verifier-path", action="append", required=True)
    q.add_argument("--output", required=True)
    q.set_defaults(func=lambda args: (build_source_snapshot(args), 0)[1])

    q = sub.add_parser("build-review-bundle")
    q.add_argument("--repo-root", type=Path, default=Path("."))
    q.add_argument("--snapshot", required=True)
    q.add_argument("--evidence", action="append", required=True)
    q.add_argument("--ci-pass", action="store_true")
    q.add_argument("--heavy-verifier-status", required=True)
    q.add_argument("--output", required=True)
    q.set_defaults(func=lambda args: (build_review_bundle(args), 0)[1])

    q = sub.add_parser("validate-source-snapshot")
    q.add_argument("--repo-root", type=Path, default=Path("."))
    q.add_argument("--snapshot", required=True)
    q.set_defaults(func=validate_snapshot)

    q = sub.add_parser("validate-review-bundle")
    q.add_argument("--repo-root", type=Path, default=Path("."))
    q.add_argument("--bundle", required=True)
    q.set_defaults(func=validate_bundle)
    return p


def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
