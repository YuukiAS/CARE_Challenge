#!/usr/bin/env python
"""Build a lightweight W4.5 CARE-ASE implementation audit package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.training.care_ase_trainer import write_json


RESULT_DIR = REPO_ROOT / "results/20260801_care_ase_final_model"
SNAPSHOT_DIR = RESULT_DIR / "w45_implementation_snapshot"

SOURCE_PATHS = [
    "prompts/blueprints/CARE_ASE_final_model_blueprint_20260801.md",
    "prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md",
    "prompts/blueprints/CARE_ASE_exact_implementation_contract_20260801.yaml",
    "prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml",
    "prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment01_20260801.yaml",
    "prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment02_controller_only_interactive_20260801.yaml",
    "prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment03_final_audit_20260801.yaml",
    "src/care_myocardium/models/care_ase.py",
    "src/care_myocardium/training/care_ase_trainer.py",
    "src/care_myocardium/data/care_ase_splits.py",
    "src/care_myocardium/data/case_metadata.py",
    "scripts/training/care_ase/run_care_ase_train.py",
    "scripts/evaluation/care_ase/evaluate_care_ase_outer.py",
    "scripts/evaluation/care_ase/build_hard_negative_manifest.py",
    "scripts/evaluation/care_ase/aggregate_care_ase_final.py",
    "scripts/evaluation/care_ase/build_w45_implementation_snapshot.py",
    "scripts/validation/validate_care_ase_implementation.py",
    "scripts/validation/validate_care_ase_preflight.py",
    "scripts/validation/validate_care_ase_split_authority.py",
    "scripts/validation/validate_care_ase_freeze_reload.py",
    "scripts/validation/validate_care_ase_final.py",
    "tests/care_ase/test_loss_and_gradient_contract.py",
    "tests/care_ase/test_no_t2_safety.py",
]

RECEIPT_PATHS = [
    "results/20260801_care_ase_final_model/contract_coverage.json",
    "results/20260801_care_ase_final_model/stock_clone_and_parity_receipt.json",
    "results/20260801_care_ase_final_model/parameter_group_coverage_receipt.json",
    "results/20260801_care_ase_final_model/component_final_logit_wiring_receipt.json",
    "results/20260801_care_ase_final_model/runtime_helper_contract_receipt.json",
    "results/20260801_care_ase_final_model/w2_preflight_receipt.json",
    "results/20260801_care_ase_final_model/w2_preflight_casewise.csv",
    "results/20260801_care_ase_final_model/split_authority_receipt.json",
    "results/20260801_care_ase_final_model/split_authority_fold2.csv",
    "results/20260801_care_ase_final_model/split_authority_fold3.csv",
    "results/20260801_care_ase_final_model/checkpoint_freeze_receipt.json",
    "results/20260801_care_ase_final_model/full_reload_parity_receipt.json",
    "results/20260801_care_ase_final_model/outer_access_audit_receipt.json",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_text(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout


def implementation_diff_text(paths: list[str]) -> str:
    status = git_text(["status", "--porcelain", "--", *paths])
    untracked = {line[3:] for line in status.splitlines() if line.startswith("?? ")}
    tracked = [path for path in paths if path not in untracked]
    chunks = []
    if tracked:
        chunks.append(git_text(["diff", "--", *tracked]))
    for rel_path in sorted(untracked):
        path = REPO_ROOT / rel_path
        if path.is_file():
            chunks.append(git_text(["diff", "--no-index", "--", "/dev/null", rel_path]))
    return "\n".join(chunk for chunk in chunks if chunk)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_preconditions() -> dict[str, Any]:
    freeze = read_json(RESULT_DIR / "checkpoint_freeze_receipt.json")
    reload_receipt = read_json(RESULT_DIR / "full_reload_parity_receipt.json")
    outer_audit = read_json(RESULT_DIR / "outer_access_audit_receipt.json")
    terminal = {}
    for fold in (2, 3):
        terminal[fold] = read_json(RESULT_DIR / "runtime" / f"fold_{fold}" / "training_terminal_receipt.json")
    checks = {
        "fold2_step_14000": terminal[2].get("global_optimizer_step") == 14000,
        "fold3_step_14000": terminal[3].get("global_optimizer_step") == 14000,
        "checkpoint_freeze_pass": freeze.get("status") == "PASS",
        "full_reload_parity_pass": reload_receipt.get("status") == "PASS",
        "outer_access_count_before_freeze_zero": outer_audit.get("outer_access_count_before_freeze") == 0,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "freeze": freeze,
        "full_reload_parity": reload_receipt,
        "outer_access_audit": outer_audit,
    }


def copy_into_snapshot(rel_path: str, category: str) -> dict[str, Any]:
    src = REPO_ROOT / rel_path
    dst = SNAPSHOT_DIR / "package_contents" / category / rel_path
    if not src.exists() or src.is_dir():
        return {"path": rel_path, "status": "MISSING"}
    if src.suffix in {".pt", ".pth", ".nii", ".gz", ".npz", ".npy", ".b2nd"}:
        return {"path": rel_path, "status": "REJECTED_LARGE_OR_BINARY"}
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {"path": rel_path, "status": "INCLUDED", "sha256": sha256_file(src), "size_bytes": src.stat().st_size}


def write_w3_summary() -> dict[str, Any]:
    rows = []
    summary: dict[str, Any] = {}
    for fold in (2, 3):
        runtime = RESULT_DIR / "runtime" / f"fold_{fold}"
        log_path = runtime / "training_log.csv"
        stage_counts: dict[str, int] = {}
        first_step = None
        last_step = None
        if log_path.exists():
            with log_path.open("r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    stage = str(row["stage"])
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1
                    step = int(row["optimizer_step"])
                    first_step = step if first_step is None else min(first_step, step)
                    last_step = step if last_step is None else max(last_step, step)
        receipts = sorted(str(path.relative_to(REPO_ROOT)) for path in runtime.glob("checkpoint_step*_receipt.json"))
        terminal = read_json(runtime / "training_terminal_receipt.json") if (runtime / "training_terminal_receipt.json").exists() else {}
        summary[f"fold_{fold}"] = {
            "first_step": first_step,
            "last_step": last_step,
            "stage_counts": stage_counts,
            "checkpoint_receipts": receipts,
            "resume_receipts": sorted(str(path.relative_to(REPO_ROOT)) for path in runtime.glob("*resume*receipt*.json")),
            "scheduler_state": "none_static_lr_contract",
            "terminal_receipt": str((runtime / "training_terminal_receipt.json").relative_to(REPO_ROOT)),
            "terminal_global_optimizer_step": terminal.get("global_optimizer_step"),
        }
        rows.append({"fold": fold, "first_step": first_step, "last_step": last_step, "stage_counts": json.dumps(stage_counts, sort_keys=True), "checkpoint_receipt_count": len(receipts)})
    out = SNAPSHOT_DIR / "package_contents" / "receipts" / "w3_stage_scheduler_checkpoint_summary.json"
    write_json(out, summary)
    csv_out = SNAPSHOT_DIR / "package_contents" / "receipts" / "w3_stage_scheduler_checkpoint_summary.csv"
    with csv_out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return {"json": str(out.relative_to(REPO_ROOT)), "csv": str(csv_out.relative_to(REPO_ROOT)), "summary": summary}


def build_package() -> dict[str, Any]:
    if SNAPSHOT_DIR.exists():
        shutil.rmtree(SNAPSHOT_DIR)
    (SNAPSHOT_DIR / "package_contents").mkdir(parents=True)
    preconditions = require_preconditions()
    if preconditions["status"] != "PASS":
        write_json(SNAPSHOT_DIR / "w45_implementation_snapshot_receipt.json", {"status": "FAIL", "preconditions": preconditions})
        raise SystemExit(1)

    copied = []
    for rel_path in SOURCE_PATHS:
        copied.append(copy_into_snapshot(rel_path, "source_and_contract"))
    for rel_path in RECEIPT_PATHS:
        copied.append(copy_into_snapshot(rel_path, "receipts"))
    for fold in (2, 3):
        runtime = RESULT_DIR / "runtime" / f"fold_{fold}"
        for rel_path in [
            runtime / "training_start_receipt.json",
            runtime / "training_terminal_receipt.json",
            *sorted(runtime.glob("checkpoint_step*_receipt.json")),
        ]:
            copied.append(copy_into_snapshot(str(rel_path.relative_to(REPO_ROOT)), "receipts"))
    w3_summary = write_w3_summary()
    diff_path = SNAPSHOT_DIR / "package_contents" / "source_and_contract" / "implementation_diff.patch"
    diff_path.write_text(implementation_diff_text(SOURCE_PATHS), encoding="utf-8")
    status_path = SNAPSHOT_DIR / "package_contents" / "source_and_contract" / "git_status_short.txt"
    status_path.write_text(git_text(["status", "--short", "--", *SOURCE_PATHS, *RECEIPT_PATHS]), encoding="utf-8")

    manifest = {
        "status": "PASS",
        "snapshot_kind": "W4.5_IMPLEMENTATION_SNAPSHOT",
        "non_blocking": True,
        "not_a_critic_or_reviewer_gate": True,
        "preconditions": preconditions,
        "included_files": copied,
        "excluded_large_artifact_patterns": ["*.pt", "*.pth", "*.nii.gz", "*.npz", "*.npy", "*.b2nd", "training_log.csv"],
        "w3_stage_scheduler_checkpoint_summary": w3_summary,
    }
    manifest_path = SNAPSHOT_DIR / "package_contents" / "manifest.json"
    write_json(manifest_path, manifest)
    tar_path = SNAPSHOT_DIR / "care_ase_w45_implementation_snapshot.tar"
    with tarfile.open(tar_path, "w") as tar:
        for path in sorted((SNAPSHOT_DIR / "package_contents").rglob("*")):
            if path.is_file():
                info = tar.gettarinfo(str(path), arcname=str(path.relative_to(SNAPSHOT_DIR / "package_contents")))
                info.mtime = 0
                with path.open("rb") as f:
                    tar.addfile(info, f)
    package_sha = sha256_file(tar_path)
    receipt = {
        "status": "PASS",
        "audit_package_path": str(tar_path.relative_to(REPO_ROOT)),
        "audit_package_sha256": package_sha,
        "manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
        "preconditions": preconditions["checks"],
        "continue_to_w5_without_manual_gate": True,
    }
    write_json(SNAPSHOT_DIR / "w45_implementation_snapshot_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt


def record_push(args: argparse.Namespace) -> None:
    receipt_path = SNAPSHOT_DIR / "w45_implementation_snapshot_receipt.json"
    receipt = read_json(receipt_path)
    payload = {
        "status": "PASS",
        "implementation_snapshot_commit_sha": args.snapshot_commit_sha,
        "origin_main_sha_after_snapshot_push": args.origin_main_sha,
        "audit_package_path": receipt["audit_package_path"],
        "audit_package_sha256": receipt["audit_package_sha256"],
        "w5_must_continue_without_manual_gate": True,
        "invalid_implementation_run_policy": "If later GPT review finds a true contract implementation error, mark current W5 output INVALID_IMPLEMENTATION_RUN and rerun only the fixed evaluation contract from frozen step14000 checkpoints.",
    }
    out = SNAPSHOT_DIR / "w45_implementation_snapshot_push_receipt.json"
    write_json(out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-push", action="store_true")
    parser.add_argument("--snapshot-commit-sha", default="")
    parser.add_argument("--origin-main-sha", default="")
    args = parser.parse_args()
    if args.record_push:
        if not args.snapshot_commit_sha or not args.origin_main_sha:
            raise ValueError("--record-push requires --snapshot-commit-sha and --origin-main-sha")
        record_push(args)
        return 0
    build_package()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
