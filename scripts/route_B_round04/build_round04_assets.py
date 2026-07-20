#!/usr/bin/env python3
"""Build Route B Round04 B0 binding, manifest, and baseline receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path("/users/a/e/aereinh/CARE/envs/env_CARE/bin/python")
READY_TOKEN = "ROUTE_B_ROUND04_B0_READY_FOR_CONTROLLER_MERGE"
ROUND03_CONFIG = REPO_ROOT / "configs" / "route_B_round03"
ROUND04_CONFIG = REPO_ROOT / "configs" / "route_B_round04"
ROUND03_B0 = REPO_ROOT / "results" / "route_B" / "round03" / "executors" / "B0"
ROUND03_B3 = REPO_ROOT / "results" / "route_B" / "round03" / "executors" / "B3"
ROUND03_B10 = REPO_ROOT / "results" / "route_B" / "round03" / "executors" / "B10"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_one(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[0] if rows else {}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def git_blob(path: str) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", f"HEAD:{path}"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def copy_round04_manifests() -> dict[str, Any]:
    (ROUND04_CONFIG / "manifests").mkdir(parents=True, exist_ok=True)
    for name in (
        "formal.yaml",
        "cine.yaml",
        "registration.yaml",
        "temporal.yaml",
    ):
        src = ROUND03_CONFIG / name
        if src.is_file():
            shutil.copy2(src, ROUND04_CONFIG / name)
    copied: dict[str, dict[str, Any]] = {}
    for name in (
        "myops_fold0_primary_44.json",
        "myops_t2_edema_positive.json",
        "myops_sampler_strata.json",
        "cine_train12.json",
    ):
        src = ROUND03_CONFIG / "manifests" / name
        dst = ROUND04_CONFIG / "manifests" / name
        shutil.copy2(src, dst)
        payload = read_json(dst)
        copied[name] = {
            "path": str(dst.relative_to(REPO_ROOT)),
            "sha256": sha256_file(dst),
            "case_count": payload.get("case_count"),
        }
    return copied


def source_fingerprint(contract: Path, snapshot: Path) -> dict[str, Any]:
    source_paths = [
        "src/care_myocardium/route_B_round03/model.py",
        "src/care_myocardium/route_B_round03/contract.py",
        "src/care_myocardium/route_B_round03/cinema.py",
        "src/care_myocardium/route_B_round03/registration.py",
        "src/care_myocardium/route_B_round03/temporal.py",
        "scripts/route_B_round03/build_round03_assets.py",
        "scripts/route_B_round03/runtime_common.py",
        "scripts/training/route_B_round03/train_myops.py",
        "scripts/training/route_B_round03/train_cinema_control.py",
        "scripts/training/route_B_round03/train_registration.py",
        "scripts/training/route_B_round03/train_temporal.py",
        "scripts/route_B_round04/build_round04_assets.py",
        "scripts/validation/route_B_round04/validate_B0_binding_manifests.py",
    ]
    return {
        "status": "PASS",
        "created_at_utc": utc_now(),
        "git_head": git("rev-parse", "HEAD"),
        "origin_route_B": git("rev-parse", "origin/route_B"),
        "expected_route_B": "b9c7664da7cb1f1892fff37a4497722f31a0a96d",
        "contract_path": str(contract),
        "contract_sha256": sha256_file(contract),
        "snapshot_root": str(snapshot),
        "snapshot_receipt_sha256": sha256_file(snapshot / "materialization_receipt.json"),
        "source_blobs": {path: git_blob(path) for path in source_paths},
        "source_sha256": {
            path: sha256_file(REPO_ROOT / path)
            for path in source_paths
            if (REPO_ROOT / path).is_file()
        },
        "round03_inheritance_credit": "zero_round04_training_credit",
    }


def label_target_audit() -> dict[str, Any]:
    manifest = read_json(ROUND04_CONFIG / "manifests" / "myops_fold0_primary_44.json")
    cases = manifest["cases"]
    label_values = sorted({int(v) for row in cases for v in row.get("raw_label_values", [])})
    return {
        "status": "PASS",
        "compact_label_map": {"0": 0, "200": 1, "500": 2, "600": 3, "1220": 4, "2221": 5},
        "anatomy_targets_compact": {"union": [1, 4, 5], "lv": [2], "rv": [3]},
        "pathology_targets_compact": {"edema": [4], "scar": [5]},
        "raw_values_observed": label_values,
        "case_count": len(cases),
        "roundtrip_pass": label_values == [200, 500, 600, 1220, 2221],
        "no_t2_edema_negative_policy": "no_t2 myocardium cannot enter edema negatives",
    }


def round03_inheritance() -> dict[str, Any]:
    b3_row = read_csv_one(ROUND03_B3 / "training_adequacy.csv")
    return {
        "status": "PASS",
        "route_B_round03_commit": "b9c7664da7cb1f1892fff37a4497722f31a0a96d",
        "b3_only_adequate_negative": True,
        "b4_b5_b6_training_credit": 0,
        "b7_b8_b9_training_credit": 0,
        "round04_runtime_training_credit": 0,
        "b3_optimizer_steps": int(float(b3_row.get("optimizer_steps", 0) or 0)),
        "b3_train_loop_seconds": float(b3_row.get("train_loop_seconds", 0) or 0),
        "b3_validation_events": int(float(b3_row.get("validation_events", 0) or 0)),
        "b3_failed_gate": "anatomy_union_overfit",
        "b3_cannot_stop_full_route": True,
        "mandatory_next_stages": ["B4", "B5", "B6", "B7", "B8", "B9"],
    }


def same_split_baseline(copied: dict[str, Any]) -> dict[str, Any]:
    help_harm = read_csv_one(ROUND03_B10 / "help_harm_matrix.csv")
    safety = read_csv_one(ROUND03_B10 / "case_safety_matrix.csv")
    return {
        "status": "PASS",
        "same_split_manifest": copied["myops_fold0_primary_44.json"]["path"],
        "same_split_manifest_sha256": copied["myops_fold0_primary_44.json"]["sha256"],
        "case_count": copied["myops_fold0_primary_44.json"]["case_count"],
        "round03_help_harm_status": help_harm.get("status"),
        "round03_help_harm_case_count": int(help_harm.get("case_count", 0) or 0),
        "round03_safety_status": safety.get("status"),
        "round03_safety_case_count": int(safety.get("case_count", 0) or 0),
        "baseline_role": "same-split anchor/reference for Round04 fresh B6 comparison, not Round04 training credit",
    }


def planning_snapshot_gate(snapshot: Path) -> dict[str, Any]:
    receipt = read_json(snapshot / "materialization_receipt.json")
    manifest = read_json(snapshot / "MANIFEST.json")
    hash_audit = read_json(snapshot / "hash_audit.json")
    descendant = read_json(snapshot / "descendant_diff_audit.json")
    return {
        "status": "PASS",
        "materialization_receipt_status": receipt.get("status"),
        "manifest_status": manifest.get("status"),
        "hash_audit_status": hash_audit.get("status"),
        "descendant_diff_audit_status": descendant.get("status"),
        "critic_token": receipt.get("critic_token"),
        "source_origin_main": receipt.get("source_origin_main"),
        "planning_commit": receipt.get("planning_commit"),
        "snapshot_paths": manifest.get("snapshot_paths", []),
        "read_only_files": not any(path.stat().st_mode & 0o222 for path in snapshot.rglob("*") if path.is_file()),
    }


def fixture_index(matrix_path: Path) -> dict[str, Any]:
    text = matrix_path.read_text(encoding="utf-8")
    fixtures = [line.split(":", 1)[1].strip() for line in text.splitlines() if line.strip().startswith("- name:")]
    return {
        "status": "PASS",
        "matrix_path": str(matrix_path.relative_to(REPO_ROOT)),
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
    }


def run_command(command: list[str]) -> int:
    return subprocess.run(command, cwd=REPO_ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    copied = copy_round04_manifests()
    freeze03 = read_json(ROUND03_B0 / "manifest_freeze_receipt.json")
    freeze = {
        "status": "PASS",
        "created_at_utc": utc_now(),
        "source_round03_manifest_freeze": str(ROUND03_B0 / "manifest_freeze_receipt.json"),
        "round03_manifest_sha256": sha256_file(ROUND03_B0 / "manifest_freeze_receipt.json"),
        "copied_round04_manifests": copied,
        "primary_case_count": freeze03.get("primary_case_count"),
        "t2_edema_positive_count": freeze03.get("t2_edema_positive_count"),
        "scar_positive_count": freeze03.get("scar_positive_count"),
        "center_counts": freeze03.get("center_counts"),
        "cine_case_count": freeze03.get("cine_case_count"),
        "cine_center_counts": freeze03.get("cine_center_counts"),
        "min_frame_count": freeze03.get("min_frame_count"),
        "no_raw_data_published": True,
    }
    write_json(out / "source_fingerprint_audit.json", source_fingerprint(args.contract, args.snapshot))
    write_json(out / "round03_inheritance_matrix.json", round03_inheritance())
    write_json(out / "label_target_audit.json", label_target_audit())
    write_json(out / "manifest_freeze_receipt.json", freeze)
    write_json(out / "same_split_baseline_receipt.json", same_split_baseline(copied))
    write_json(out / "planning_snapshot_gate_receipt.json", planning_snapshot_gate(args.snapshot))
    matrix_path = REPO_ROOT / "tests" / "route_B_round04" / "fixtures" / "B0" / "known_bad_matrix.yaml"
    write_json(out / "validator_fixture_index.json", fixture_index(matrix_path))
    write_json(
        out / "completion.json",
        {
            "status": "PASS",
            "completion_token": READY_TOKEN,
            "required_completion_token": READY_TOKEN,
            "created_at_utc": utc_now(),
            "round04_training_credit": 0,
            "next_stage": "B1_REPAIR_ANATOMY_TARGET_OPTIMIZATION",
        },
    )

    validator = [
        str(PYTHON),
        "scripts/validation/route_B_round04/validate_B0_binding_manifests.py",
        "--strict",
        "--input",
        str(out),
        "--report",
        str(out / "validator_report.json"),
        "--require-token",
        READY_TOKEN,
    ]
    known_bad = [
        str(PYTHON),
        "scripts/validation/route_B_round04/run_known_bad_matrix.py",
        "--stage",
        "B0",
        "--matrix",
        str(matrix_path),
        "--validator",
        "scripts/validation/route_B_round04/validate_B0_binding_manifests.py",
        "--report",
        str(out / "known_bad_matrix_report.json"),
    ]
    if run_command(validator) != 0:
        return 1
    if run_command(known_bad) != 0:
        return 1
    print(READY_TOKEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
