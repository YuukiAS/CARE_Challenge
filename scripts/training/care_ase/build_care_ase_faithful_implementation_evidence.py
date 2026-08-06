#!/usr/bin/env python3
"""Build CARE-ASE faithful implementation evidence for Agent-Flow v3.

This script is Executor-owned. It does not modify verifier assets and it does
not train. When the runtime cannot execute the zero-credit probes required by
the frozen contract, it writes a fail-closed receipt instead of synthesizing a
passing evidence packet.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "care-ase-faithful"
REQUEST_NONCE = "care-ase-20260806T090955Z"
FROZEN_CONTRACT_SHA256 = "a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d"
VERIFIER_FINGERPRINT_SHA256 = "b3f1a0f630b346494cbeb7f1ae92764ab993047e373a0a1e23d77c194f8cecdf"

ROOT = Path(__file__).resolve().parents[3]
IMPLEMENTATION_DIR = ROOT / "results" / "agent_flow_v3" / TASK_ID / "implementation"
VERIFICATION_CONTRACT = ROOT / "results" / "agent_flow_v3" / TASK_ID / "verification" / "verification_contract.json"

SOURCE_PATHS = [
    "src/care_myocardium/models/care_ase.py",
    "src/care_myocardium/training/care_ase_trainer.py",
    "src/care_myocardium/training/care_ase_runtime.py",
    "src/care_myocardium/training/care_ase_sampler.py",
    "src/care_myocardium/training/care_ase_augmentation.py",
    "src/care_myocardium/inference/care_ase_r2_decode.py",
    "src/care_myocardium/inference/care_ase_r2_full_volume.py",
    "scripts/training/care_ase/run_care_ase_r2_chunk.py",
    "scripts/training/care_ase/run_care_ase_train.py",
    "scripts/training/care_ase/build_care_ase_faithful_implementation_evidence.py",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_sha(payload: Any) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_value(*args: str) -> str | None:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def source_manifest() -> dict[str, Any]:
    file_hashes: dict[str, str] = {}
    missing: list[str] = []
    for rel in SOURCE_PATHS:
        path = ROOT / rel
        if path.is_file():
            file_hashes[rel] = sha256_file(path)
        else:
            missing.append(rel)
    payload = {
        "schema": "CARE_ASE_FAITHFUL_IMPLEMENTATION_SOURCE_MANIFEST_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "verifier_fingerprint_sha256": VERIFIER_FINGERPRINT_SHA256,
        "git_head": git_value("rev-parse", "HEAD"),
        "git_branch": git_value("branch", "--show-current"),
        "file_hashes": file_hashes,
        "missing_files": missing,
    }
    payload["source_manifest_sha256"] = json_sha(payload)
    return payload


def static_architecture_checks() -> dict[str, Any]:
    model_path = ROOT / "src" / "care_myocardium" / "models" / "care_ase.py"
    inference_path = ROOT / "src" / "care_myocardium" / "inference" / "care_ase_r2_full_volume.py"
    trainer_path = ROOT / "src" / "care_myocardium" / "training" / "care_ase_trainer.py"
    model = model_path.read_text(encoding="utf-8") if model_path.is_file() else ""
    inference = inference_path.read_text(encoding="utf-8") if inference_path.is_file() else ""
    trainer = trainer_path.read_text(encoding="utf-8") if trainer_path.is_file() else ""
    tokens = {
        "carease_class": "class CAREASE(nn.Module)" in model,
        "stock_checkpoint_load": "stock.load_state_dict" in model and "stock_parameter_byte_coverage" in model,
        "highest_two_pathology_branch": "class CAREASEPathologyBranch" in model and "stock_decoder.stages[4]" in model and "stock_decoder.stages[5]" in model,
        "named_zero_projections": "class NamedEvidenceProjectionSet" in model and "nn.init.zeros_(proj.weight)" in model,
        "active_modality_adapter": "class ModalityAdapter" in model and "nn.init.kaiming_normal_" in model,
        "edema_t2_subset_execution": "t2_present_mask" in model and "selected_skips = [skip[idx] for skip in skips]" in model,
        "class4_no_t2_decode_support": "decode_care_ase_r2_logits" in (ROOT / "src/care_myocardium/inference/care_ase_r2_decode.py").read_text(encoding="utf-8"),
        "shared_extent_statistics": "compute_slice_extent_statistics" in model and "compute_slice_extent_statistics" in inference,
        "tile_bias_after_aggregation": "global_extent_bias" in inference and "disable_extent_wall=True" in inference,
        "schema_v4_checkpoint": "CHECKPOINT_SCHEMA_VERSION = 4" in trainer,
    }
    return {
        "schema": "CARE_ASE_FAITHFUL_STATIC_ARCHITECTURE_CHECKS_V1",
        "tokens": tokens,
        "all_static_tokens_present": all(tokens.values()),
        "canonical_truth_status": "legacy_monolith_present",
        "canonical_truth_note": "Current executable truth is src/care_myocardium/models/care_ase.py; frozen contract prefers src/care_myocardium/models/care_ase/ package.",
    }


def environment_gate() -> tuple[bool, list[str], dict[str, Any]]:
    failures: list[str] = []
    details: dict[str, Any] = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "torch_available": importlib.util.find_spec("torch") is not None,
        "nnunet_available": importlib.util.find_spec("nnunetv2") is not None,
        "default_plans_exists": (ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json").is_file(),
        "default_dataset_json_exists": (ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/dataset.json").is_file(),
        "default_stock_root_exists": (ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres").is_dir(),
    }
    for key in ("torch_available", "nnunet_available", "default_plans_exists", "default_dataset_json_exists", "default_stock_root_exists"):
        if not details[key]:
            failures.append(key)
    return not failures, failures, details


def fail_closed_payload(reason: str, failures: list[str], details: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "CARE_ASE_FAITHFUL_IMPLEMENTATION_FAIL_CLOSED_RECEIPT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "verifier_fingerprint_sha256": VERIFIER_FINGERPRINT_SHA256,
        "status": "FAIL_CLOSED",
        "implementation_complete": False,
        "reason": reason,
        "failures": failures,
        "environment": details,
        "source_manifest_path": f"results/agent_flow_v3/{TASK_ID}/implementation/implementation_source_manifest.json",
        "source_manifest_sha256": manifest["source_manifest_sha256"],
        "verification_contract_path": str(VERIFICATION_CONTRACT.relative_to(ROOT)),
        "no_training_started": True,
        "outer_accessed": False,
        "docker_built_or_uploaded": False,
        "validation_or_challenge_uploaded": False,
        "created_utc": utc_now(),
    }


def build_static_only_receipts() -> int:
    manifest = source_manifest()
    static_checks = static_architecture_checks()
    env_ok, env_failures, env_details = environment_gate()
    write_json(IMPLEMENTATION_DIR / "implementation_source_manifest.json", manifest)
    write_json(IMPLEMENTATION_DIR / "static_architecture_checks.json", static_checks)

    if not static_checks["all_static_tokens_present"]:
        payload = fail_closed_payload(
            "static architecture evidence is incomplete",
            [name for name, ok in static_checks["tokens"].items() if not ok],
            {"static_checks": static_checks, **env_details},
            manifest,
        )
        write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
        return 2

    if not env_ok:
        payload = fail_closed_payload(
            "required runtime environment/assets are unavailable for zero-credit forward/backward and inference probes",
            env_failures,
            env_details,
            manifest,
        )
        write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
        return 2

    payload = fail_closed_payload(
        "runtime environment is present, but this Executor-safe builder intentionally stops before formal training; Controller should run the dedicated probe extension in the GPU/data environment",
        ["probe_extension_not_executed"],
        env_details,
        manifest,
    )
    write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
    return 2


def write_summary(exit_code: int) -> None:
    receipt = IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json"
    lines = [
        "# CARE-ASE faithful implementation receipt",
        "",
        "本 Executor 没有完成可验收的忠实实现证据：当前隔离 worktree 缺少 Torch/nnU-Net 运行环境和 Dataset501 stock 资产，无法真实执行冻结合同要求的零信用 forward/backward 与 full-volume inference 探针。因此本包按合同 fail closed，不伪造 `implementation_evidence.json`。",
        "",
        f"- task_id: `{TASK_ID}`",
        f"- request_nonce: `{REQUEST_NONCE}`",
        f"- frozen_contract_sha256: `{FROZEN_CONTRACT_SHA256}`",
        f"- verifier_fingerprint_sha256: `{VERIFIER_FINGERPRINT_SHA256}`",
        f"- exit_code: `{exit_code}`",
        f"- fail_closed_receipt: `{receipt.relative_to(ROOT)}`",
        "- formal_training_started: `false`",
        "- outer_accessed: `false`",
        "- docker_or_upload: `false`",
        "",
    ]
    (IMPLEMENTATION_DIR / "result.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build CARE-ASE faithful implementation evidence or fail closed.")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    if args.repo_root.resolve() != ROOT:
        parser.error(f"--repo-root must resolve to {ROOT}")
    exit_code = build_static_only_receipts()
    write_summary(exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
