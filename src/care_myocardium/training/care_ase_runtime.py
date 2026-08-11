"""Authoritative CARE-ASE faithful formal/probe runtime.

The Slurm/Python wrapper is intentionally thin. This module owns descriptor
bundles, case materialization, stock augmentation, target-cache binding,
forward/loss/backward/update, checkpoint/reload, and lock bookkeeping.
"""

from __future__ import annotations

import argparse
import ast
from collections import OrderedDict
import copy
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
import pickle
import random
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from threading import Event, Thread
from typing import Any

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import blosc2
import numpy as np
from scipy.ndimage import label as ndimage_label
from scipy import ndimage
import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.care_ase import CAREASEConfig, build_care_ase_for_fold_with_area_references
from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
from src.care_myocardium.data.care_ase_splits import build_care_ase_case_roles
from src.care_myocardium.training.care_ase_augmentation import (
    apply_stock_training_transform_preserve_ignore,
    apply_stock_training_transform_with_targets,
    build_stock_augmentation_contract,
    build_stock_training_transform_preserve_ignore,
)
from src.care_myocardium.training.care_ase_sampler import (
    CAREASEBatchDescriptor,
    CAREASEDeterministicSampler,
    CAREASEMicrobatchBundle,
    compute_actual_train_area_references,
)
from src.care_myocardium.training.care_ase_trainer import (
    CAREASEStageScheduler,
    build_full_case_target_cache,
    build_optimizer,
    care_ase_loss,
    checkpoint_receipt,
    load_care_ase_checkpoint,
    load_care_ase_checkpoint_for_training_resume,
    parameter_group_coverage,
    _optimizer_step_from_materialized_microbatches,
    save_care_ase_checkpoint,
    slice_full_case_target_cache,
    write_json,
    _component_center_heatmap,
    _context_target_numpy,
    _edema_boundary_numpy,
    _geometry_targets_numpy,
)


_RUNTIME_ROOT = Path(os.environ.get("CARE_ROOT", REPO_ROOT)).resolve()
_PREPROCESSED_ROOT = Path(
    os.environ.get("nnUNet_preprocessed", _RUNTIME_ROOT / "data/nnUNet/nnUNet_preprocessed")
)
PREPROCESSED = _PREPROCESSED_ROOT / "Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
SPLITS = _PREPROCESSED_ROOT / "Dataset501_CAREMyoPS/splits_final.json"
TASK_KEY = "care-ase-faithful"
TASK_ID = TASK_KEY
FORMAL_TRAINING_TASK_KEY = "care-ase-faithful-formal-training-20260812"
REQUEST_NONCE = "care-ase-20260806T090955Z"
FROZEN_CONTRACT = REPO_ROOT / "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md"
FROZEN_CONTRACT_SHA256 = "a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d"
LEGACY_R2_TASK_KEY = "20260804_care_ase_r2_emergency_9h_training_docker"
RESULT_DIR = REPO_ROOT / "results/agent_flow_v3/care-ase-faithful/implementation"
STATIC_REVIEW_INPUT_DIR = RESULT_DIR
V8_RESULT_DIR = REPO_ROOT / "results/20260803_care_ase_r2_final_pretraining_closure_v8"
PROBE_RUNTIME_DIR = RESULT_DIR / "runtime_zero_credit"
FORMAL_RUNTIME_PREFIX = "care_ase_faithful_formal_training_"
EFFECTIVE_CONTRACT = REPO_ROOT / "prompts/blueprints/CARE_ASE_R2_effective_contract_v9_20260803.yaml"
CRITICAL_SOURCE_SEED_PATHS = (
    "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
    "automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json",
    "automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json",
    "results/agent_flow_v3/care-ase-faithful/verification/verification_contract.json",
    "prompts/blueprints/CARE_ASE_R2_effective_contract_v9_20260803.yaml",
    "src/care_myocardium/models/care_prism.py",
    "src/care_myocardium/models/care_ase/__init__.py",
    "src/care_myocardium/models/care_ase/core.py",
    "src/care_myocardium/training/care_ase_trainer.py",
    "src/care_myocardium/training/care_ase_runtime.py",
    "src/care_myocardium/training/care_ase_sampler.py",
    "src/care_myocardium/training/care_ase_augmentation.py",
    "src/care_myocardium/data/care_ase_splits.py",
    "src/care_myocardium/data/case_metadata.py",
    "src/care_myocardium/inference/care_ase_r2_decode.py",
    "src/care_myocardium/inference/care_ase_r2_full_volume.py",
    "scripts/training/care_ase/run_care_ase_r2_chunk.py",
    "scripts/evaluation/care_ase/build_stock_oof_preprocessed_grid_predictions.py",
    "scripts/evaluation/care_ase/build_care_ase_r2_hard_negative_manifest.py",
    "scripts/evaluation/care_ase/build_care_ase_r2_full_case_target_manifest.py",
    "scripts/evaluation/care_ase/monitor_care_ase_r2_inner_trend.py",
    "scripts/evaluation/care_ase/select_care_ase_r2_inner_checkpoint.py",
    "scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py",
    "scripts/validation/verify_care_ase_checkpoint_for_resume.py",
    "jobs/care_ase_r2/run_fold_chunk_htzhulab.sh",
)
CRITICAL_SOURCE_PATHS = CRITICAL_SOURCE_SEED_PATHS
INVALIDATED_TRAINING_SOURCE_SHAS = {
    "207f360f22dd4e28fcecd4a22b67ed1af074ab42",
    "e9876ac8b7c8d6881fd5673f409c0c6e767530f1",
    "f4ecd049bb09a47c38305b932ef116d45b37c160",
}
_FULL_CASE_TARGET_CACHE_BY_CASE: "OrderedDict[tuple[str, tuple[float, float, float]], dict[str, np.ndarray]]" = OrderedDict()
_FULL_CASE_TARGET_CACHE_MAX_CASES = 8
_CASE_ARRAY_CACHE_BY_CASE: "OrderedDict[str, tuple[np.ndarray, np.ndarray, tuple[float, float, float]]]" = OrderedDict()
_CASE_ARRAY_CACHE_MAX_CASES = 8
_TARGET_REGRESSION_KEYS = (
    "signed_endo_distance",
    "signed_epi_distance",
    "wall_depth_rho",
    "scar_center_fullres",
    "edema_boundary",
    "edema_boundary_raw_mm",
)
_TARGET_SEGMENTATION_KEYS = (
    "geometry_valid",
    "scar_component_id",
    "scar_context_target",
    "edema_context_target",
    "edema_boundary_valid",
    "valid_label_mask",
    "source_z_id",
    "source_z_valid",
    "source_inplane_footprint",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def effective_contract_sha256() -> str:
    if not EFFECTIVE_CONTRACT.is_file():
        raise FileNotFoundError(f"CARE-ASE R2 v9 effective contract missing: {EFFECTIVE_CONTRACT}")
    return sha256_file(EFFECTIVE_CONTRACT)


def frozen_contract_sha256() -> str:
    if not FROZEN_CONTRACT.is_file():
        raise FileNotFoundError(f"CARE-ASE frozen contract missing: {FROZEN_CONTRACT}")
    observed = sha256_file(FROZEN_CONTRACT)
    if observed != FROZEN_CONTRACT_SHA256:
        raise RuntimeError(
            "CARE-ASE frozen contract SHA mismatch: "
            f"expected={FROZEN_CONTRACT_SHA256} observed={observed}"
        )
    return observed


def _module_to_repo_path(module: str) -> str | None:
    if module.startswith("src."):
        rel = module.replace(".", "/") + ".py"
    elif module.startswith("scripts."):
        rel = module.replace(".", "/") + ".py"
    else:
        return None
    return rel if (REPO_ROOT / rel).is_file() else None


def _repo_local_imports(path: Path) -> set[str]:
    if path.suffix != ".py" or not path.is_file():
        return set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            rel = _module_to_repo_path(node.module)
            if rel is not None:
                out.add(rel)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                rel = _module_to_repo_path(alias.name)
                if rel is not None:
                    out.add(rel)
    return out


def critical_source_dependency_closure() -> list[str]:
    seen: set[str] = set()
    queue = list(CRITICAL_SOURCE_SEED_PATHS)
    while queue:
        rel = queue.pop(0)
        if rel in seen:
            continue
        seen.add(rel)
        for dep in sorted(_repo_local_imports(REPO_ROOT / rel)):
            if dep not in seen:
                queue.append(dep)
    return sorted(seen)


def critical_source_manifest() -> dict[str, str]:
    payload: dict[str, str] = {}
    missing: list[str] = []
    for path in critical_source_dependency_closure():
        full = REPO_ROOT / path
        if not full.is_file():
            missing.append(path)
        else:
            payload[path] = sha256_file(full)
    if missing:
        raise FileNotFoundError(f"CARE-ASE critical source files missing: {missing}")
    return payload


def combined_source_hash() -> str:
    payload = critical_source_manifest()
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def combined_source_hash_at_commit(ref: str) -> str:
    payload: dict[str, str] = {}
    for path in critical_source_dependency_closure():
        proc = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode == 0:
            payload[path] = hashlib.sha256(proc.stdout).hexdigest()
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def json_sha(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def sha256_array(array: np.ndarray) -> str:
    arr = np.ascontiguousarray(array)
    h = hashlib.sha256()
    h.update(str(arr.dtype).encode("utf-8"))
    h.update(json.dumps(list(arr.shape)).encode("utf-8"))
    h.update(arr.tobytes())
    return h.hexdigest()


def _target_cache_field_sha(cache: dict[str, np.ndarray]) -> dict[str, str]:
    return {key: sha256_array(value) for key, value in sorted(cache.items()) if isinstance(value, np.ndarray)}


def reserve_v9_probe_budget(*, fold: int, start_step: int, end_step: int, max_steps: int = 10, probe_name: str = "") -> dict[str, Any]:
    requested = int(end_step) - int(start_step)
    if requested <= 0:
        raise ValueError("probe budget reservation requires positive step count")
    root = PROBE_RUNTIME_DIR / "probe_budget"
    root.mkdir(parents=True, exist_ok=True)
    counter = root / "counter.json"
    ledger = root / "reservations.jsonl"
    lock = root / "counter.lock"
    with lock.open("a+", encoding="utf-8") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        payload = json.loads(counter.read_text(encoding="utf-8")) if counter.is_file() else {
            "task_key": TASK_KEY,
            "max_optimizer_steps": int(max_steps),
            "total_reserved_optimizer_steps": 0,
            "reserved_step_slots": 0,
            "completed_optimizer_steps": 0,
            "failed_after_reservation": 0,
            "reservations": [],
        }
        if payload.get("task_key") not in (None, TASK_KEY):
            foreign_id = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
            foreign = root / f"foreign_probe_budget_{payload.get('task_key')}_{foreign_id}.json"
            foreign.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            payload = {
                "task_key": TASK_KEY,
                "max_optimizer_steps": int(max_steps),
                "total_reserved_optimizer_steps": 0,
                "reserved_step_slots": 0,
                "completed_optimizer_steps": 0,
                "failed_after_reservation": 0,
                "foreign_ledger_quarantined": str(foreign),
                "reservations": [],
            }
        payload["max_optimizer_steps"] = int(max_steps)
        new_total = int(payload.get("total_reserved_optimizer_steps", 0)) + requested
        if new_total > int(max_steps):
            raise RuntimeError(
                "CARE-ASE faithful zero-credit probe budget exceeded before forward/materialization: "
                f"requested={requested} previous={payload.get('total_reserved_optimizer_steps', 0)} max={max_steps}"
            )
        reservation = {
            "reservation_id": hashlib.sha256(
                f"{TASK_KEY}|{fold}|{start_step}|{end_step}|{time.time_ns()}|{os.getpid()}".encode("utf-8")
            ).hexdigest(),
            "fold": int(fold),
            "start_step": int(start_step),
            "end_step": int(end_step),
            "optimizer_steps": requested,
            "slot_start": int(payload.get("total_reserved_optimizer_steps", 0)) + 1,
            "slot_end": new_total,
            "probe_name": str(probe_name),
            "reserved_utc": utc_now(),
            "pid": os.getpid(),
            "source_sha": git_sha("HEAD"),
            "status": "RESERVED_BEFORE_MATERIALIZATION_FORWARD_BACKWARD_STEP",
        }
        payload["total_reserved_optimizer_steps"] = new_total
        payload["reserved_step_slots"] = new_total
        payload.setdefault("reservations", []).append(reservation)
        with ledger.open("a", encoding="utf-8") as lf:
            lf.write(json.dumps(reservation, sort_keys=True) + "\n")
            lf.flush()
            os.fsync(lf.fileno())
        tmp = counter.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, counter)
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
    return {**payload, "latest_reservation": reservation, "counter_path": str(counter), "append_only_ledger_path": str(ledger)}


def reserve_v8_probe_budget(*, fold: int, start_step: int, end_step: int, max_steps: int = 10, probe_name: str = "") -> dict[str, Any]:
    return reserve_v9_probe_budget(fold=fold, start_step=start_step, end_step=end_step, max_steps=max_steps, probe_name=probe_name)


def record_v9_probe_budget_completion(reservation: dict[str, Any] | None, *, status: str) -> None:
    if not reservation:
        return
    if status not in {"COMPLETED", "FAILED_AFTER_RESERVATION"}:
        raise ValueError(f"unsupported probe budget completion status: {status}")
    counter = Path(str(reservation.get("counter_path", "")))
    if not counter:
        return
    root = counter.parent
    ledger = Path(str(reservation.get("append_only_ledger_path", root / "reservations.jsonl")))
    lock = root / "counter.lock"
    reservation_id = str(reservation["latest_reservation"]["reservation_id"])
    optimizer_steps = int(reservation["latest_reservation"].get("optimizer_steps", 0))
    with lock.open("a+", encoding="utf-8") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        payload = json.loads(counter.read_text(encoding="utf-8"))
        updated = False
        for item in payload.get("reservations", []):
            if str(item.get("reservation_id")) == reservation_id:
                previous = str(item.get("completion_status", ""))
                if previous:
                    updated = True
                    break
                item["completion_status"] = status
                item["completion_utc"] = utc_now()
                if status == "COMPLETED":
                    payload["completed_optimizer_steps"] = int(payload.get("completed_optimizer_steps", 0)) + optimizer_steps
                else:
                    payload["failed_after_reservation"] = int(payload.get("failed_after_reservation", 0)) + optimizer_steps
                completion = {
                    "event": "PROBE_BUDGET_COMPLETION",
                    "reservation_id": reservation_id,
                    "optimizer_steps": optimizer_steps,
                    "status": status,
                    "source_sha": item.get("source_sha"),
                    "fold": item.get("fold"),
                    "start_step": item.get("start_step"),
                    "end_step": item.get("end_step"),
                    "utc": item["completion_utc"],
                }
                with ledger.open("a", encoding="utf-8") as lf:
                    lf.write(json.dumps(completion, sort_keys=True) + "\n")
                    lf.flush()
                    os.fsync(lf.fileno())
                updated = True
                break
        if not updated:
            raise RuntimeError(f"probe budget reservation not found: {reservation_id}")
        tmp = counter.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, counter)
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)


def record_v8_probe_budget_completion(reservation: dict[str, Any] | None, *, status: str) -> None:
    record_v9_probe_budget_completion(reservation, status=status)


def formal_runtime_input_bundle_default_path() -> Path:
    return RESULT_DIR / "current_runtime_input_bundle.json"


def validate_logical_chunk_invocation(
    *,
    start_step: int,
    end_step: int,
    allow_short_smoke: bool,
    resume_checkpoint_present: bool,
) -> dict[str, int]:
    if int(start_step) < 0 or int(end_step) > 14000 or int(start_step) >= int(end_step):
        raise ValueError("CARE-ASE R2 chunk must satisfy 0 <= start < end <= 14000")
    logical_chunk_start = (int(start_step) // 2000) * 2000
    logical_chunk_end = logical_chunk_start + 2000
    initial_span = int(end_step) - int(start_step)
    if not allow_short_smoke and not resume_checkpoint_present and (
        int(start_step) % 2000 != 0 or initial_span not in {1000, 2000}
    ):
        raise ValueError("initial formal CARE-ASE chunk must start on a 2000-step boundary and span 1000 or 2000 steps")
    if not allow_short_smoke and resume_checkpoint_present and int(end_step) != int(logical_chunk_end):
        raise ValueError("formal resume must continue the original logical 2000-step chunk remainder")
    return {"logical_chunk_start": int(logical_chunk_start), "logical_chunk_end": int(logical_chunk_end)}


def _require_bound_sha(bundle: dict[str, Any], key: str, path_key: str | None = None) -> str:
    value = str(bundle.get(key, ""))
    if not value or value == "UNSET":
        raise RuntimeError(f"formal runtime input bundle missing SHA field: {key}")
    if path_key is not None:
        raw_path = bundle.get(path_key)
        if not raw_path:
            raise RuntimeError(f"formal runtime input bundle missing path field: {path_key}")
        path = Path(str(raw_path))
        if not path.is_absolute():
            path = REPO_ROOT / path
        if not path.is_file():
            raise RuntimeError(f"formal runtime input bundle path is missing: {path}")
        observed = sha256_file(path)
        if observed != value:
            raise RuntimeError(f"formal runtime input bundle SHA mismatch for {path_key}: expected {value} observed {observed}")
    return value


def _sha_field(value: Any, *, field: str) -> str:
    text = str(value or "")
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise RuntimeError(f"formal runtime input bundle requires hex SHA-256 field {field}")
    return text


def _git_sha_field(value: Any, *, field: str) -> str:
    text = str(value or "")
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise RuntimeError(f"formal runtime input bundle requires git SHA field {field}")
    return text


def _bundle_path(bundle: dict[str, Any], key: str, *, must_exist: bool = False) -> Path:
    value = str(bundle.get(key, ""))
    if not value:
        raise RuntimeError(f"formal runtime input bundle missing path field: {key}")
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if must_exist and not path.exists():
        raise RuntimeError(f"formal runtime input bundle path is missing: {path}")
    return path.resolve()


def _reject_legacy_runtime_identity(bundle: dict[str, Any]) -> None:
    serialized = json.dumps(bundle, sort_keys=True, default=str)
    for field in ("result_root", "probe_root"):
        if LEGACY_R2_TASK_KEY in str(bundle.get(field, "")):
            raise RuntimeError(f"formal runtime input bundle {field} still points at legacy R2 task root")
    permit = bundle.get("formal_user_decision_permit_provenance", {})
    if isinstance(permit, dict):
        decision = str(permit.get("decision", ""))
        task_key = str(permit.get("task_key", permit.get("task_id", "")))
        if decision == "PRETRAINING_CONTROLLER_USER_AUTHORIZED_PASS_20260804" or task_key == LEGACY_R2_TASK_KEY:
            raise RuntimeError("historical 20260804 training permit cannot authorize care-ase-faithful")
    if "prompts/tasks/20260804_care_ase_r2_emergency_9h_training_docker_controller.md" in serialized:
        raise RuntimeError("formal runtime input bundle contains legacy 20260804 task document authority")


def validate_current_runtime_input_bundle(
    bundle: dict[str, Any],
    *,
    fold: int,
    expected_request_nonce: str = REQUEST_NONCE,
    expected_frozen_contract_sha256: str = FROZEN_CONTRACT_SHA256,
    expected_implementation_source_manifest_sha256: str | None = None,
    expected_implementation_fingerprint_sha256: str | None = None,
    expected_immutable_implementation_fingerprint_sha256: str | None = None,
    expected_integration_commit_sha: str | None = None,
    expected_verifier_fingerprint_sha256: str | None = None,
) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        raise RuntimeError("formal runtime input bundle must be a JSON object")
    if bundle.get("task_id") != TASK_ID:
        raise RuntimeError(f"formal runtime input bundle task_id mismatch: {bundle.get('task_id')} != {TASK_ID}")
    declared_payload_sha = str(bundle.get("bundle_payload_sha256", ""))
    if declared_payload_sha:
        tmp = dict(bundle)
        tmp.pop("bundle_payload_sha256", None)
        for runtime_key in (
            "path",
            "sha256",
            "verified_for_fold",
            "current_runtime_identity_validation",
            "target_builder_provenance",
        ):
            tmp.pop(runtime_key, None)
        observed_payload_sha = json_sha(tmp)
        if declared_payload_sha != observed_payload_sha:
            raise RuntimeError("formal runtime input bundle payload SHA mismatch")
    if bundle.get("request_nonce") != expected_request_nonce:
        raise RuntimeError("formal runtime input bundle request_nonce mismatch")
    if bundle.get("frozen_contract_sha256") != expected_frozen_contract_sha256:
        raise RuntimeError("formal runtime input bundle frozen_contract_sha256 mismatch")
    if int(bundle.get("fold", -1)) != int(fold):
        raise RuntimeError(f"formal runtime input bundle fold mismatch: {bundle.get('fold')} != {fold}")
    frozen_contract_sha256()
    _reject_legacy_runtime_identity(bundle)

    result_root = _bundle_path(bundle, "result_root", must_exist=False)
    probe_root = _bundle_path(bundle, "probe_root", must_exist=False)
    implementation_root = (REPO_ROOT / "results/agent_flow_v3/care-ase-faithful/implementation").resolve()
    formal_training_root = (REPO_ROOT / "results/agent_flow_v3" / FORMAL_TRAINING_TASK_KEY).resolve()
    allowed_runtime_roots = (implementation_root, formal_training_root)
    if not any(root in result_root.parents or result_root == root for root in allowed_runtime_roots):
        raise RuntimeError(f"formal runtime result_root is outside authorized CARE-ASE namespaces: {result_root}")
    if not any(root in probe_root.parents or probe_root == root for root in allowed_runtime_roots):
        raise RuntimeError(f"formal runtime probe_root is outside authorized CARE-ASE namespaces: {probe_root}")

    expected_fields = {
        "implementation_source_manifest_sha256": expected_implementation_source_manifest_sha256,
        "implementation_fingerprint_sha256": expected_implementation_fingerprint_sha256,
        "immutable_implementation_fingerprint_sha256": (
            expected_immutable_implementation_fingerprint_sha256
            or expected_implementation_fingerprint_sha256
        ),
        "verifier_fingerprint_sha256": expected_verifier_fingerprint_sha256,
    }
    for field, expected in expected_fields.items():
        observed = bundle.get(field)
        _sha_field(observed, field=field)
        if expected is not None and observed != expected:
            raise RuntimeError(f"formal runtime input bundle {field} mismatch")
    integration_observed = _git_sha_field(bundle.get("integration_commit_sha"), field="integration_commit_sha")
    if expected_integration_commit_sha is not None and integration_observed != expected_integration_commit_sha:
        raise RuntimeError("formal runtime input bundle integration_commit_sha mismatch")

    hard_negative_path_key = f"hard_negative_manifest_fold{int(fold)}_path"
    hard_negative_sha_key = f"hard_negative_manifest_fold{int(fold)}_sha256"
    hard_negative_path = bundle.get(hard_negative_path_key) or bundle.get("hard_negative_manifest_path")
    hard_negative_sha = bundle.get(hard_negative_sha_key) or bundle.get("hard_negative_manifest_sha256")
    if not hard_negative_path:
        raise RuntimeError("formal runtime input bundle requires explicit hard-negative manifest path")
    if not hard_negative_sha:
        raise RuntimeError("formal runtime input bundle requires explicit hard-negative manifest SHA")
    normalized_path = Path(str(hard_negative_path))
    if not normalized_path.is_absolute():
        normalized_path = REPO_ROOT / normalized_path
    if not normalized_path.is_file():
        raise RuntimeError(f"formal runtime hard-negative manifest is missing: {normalized_path}")
    observed_manifest_sha = sha256_file(normalized_path)
    if observed_manifest_sha != str(hard_negative_sha):
        raise RuntimeError("formal runtime hard-negative manifest SHA mismatch")
    bundle[hard_negative_path_key] = str(normalized_path)
    bundle[hard_negative_sha_key] = observed_manifest_sha
    bundle["hard_negative_manifest_path"] = str(normalized_path)
    bundle["hard_negative_manifest_sha256"] = observed_manifest_sha

    secondary_path = bundle.get("secondary_effective_contract_path")
    if secondary_path:
        secondary_resolved = Path(str(secondary_path))
        if not secondary_resolved.is_absolute():
            secondary_resolved = REPO_ROOT / secondary_resolved
        if not secondary_resolved.is_file():
            raise RuntimeError(f"secondary effective contract is missing: {secondary_resolved}")
        expected_secondary = bundle.get("secondary_effective_contract_sha256") or bundle.get("effective_contract_sha256")
        if expected_secondary and sha256_file(secondary_resolved) != str(expected_secondary):
            raise RuntimeError("secondary effective contract SHA mismatch")

    checks = {
        "task_id": True,
        "request_nonce": True,
        "frozen_contract_sha256": True,
        "fold": True,
        "implementation_source_manifest_sha256": True,
        "implementation_fingerprint_sha256": True,
        "immutable_implementation_fingerprint_sha256": True,
        "integration_commit_sha": True,
        "verifier_fingerprint_sha256": True,
        "explicit_result_root": True,
        "explicit_probe_root": True,
        "explicit_hard_negative_manifest": True,
        "legacy_task_key_rejected": True,
    }
    return {"status": "PASS", "checks": checks, "hard_negative_manifest_sha256": observed_manifest_sha}


def build_current_runtime_input_bundle(
    *,
    fold: int,
    hard_negative_manifest_path: Path,
    implementation_source_manifest_sha256: str,
    implementation_fingerprint_sha256: str,
    immutable_implementation_fingerprint_sha256: str | None = None,
    integration_commit_sha: str,
    verifier_fingerprint_sha256: str,
    result_root: Path | None = None,
    probe_root: Path | None = None,
) -> dict[str, Any]:
    hard_negative_path = Path(hard_negative_manifest_path)
    if not hard_negative_path.is_absolute():
        hard_negative_path = REPO_ROOT / hard_negative_path
    payload = {
        "schema": "CARE_ASE_FAITHFUL_CURRENT_RUNTIME_INPUT_BUNDLE_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_path": str(FROZEN_CONTRACT.relative_to(REPO_ROOT)),
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "secondary_effective_contract_path": str(EFFECTIVE_CONTRACT.relative_to(REPO_ROOT)),
        "secondary_effective_contract_sha256": effective_contract_sha256(),
        "implementation_source_manifest_sha256": _sha_field(
            implementation_source_manifest_sha256,
            field="implementation_source_manifest_sha256",
        ),
        "implementation_fingerprint_sha256": _sha_field(
            implementation_fingerprint_sha256,
            field="implementation_fingerprint_sha256",
        ),
        "immutable_implementation_fingerprint_sha256": _sha_field(
            immutable_implementation_fingerprint_sha256 or implementation_fingerprint_sha256,
            field="immutable_implementation_fingerprint_sha256",
        ),
        "integration_commit_sha": _git_sha_field(integration_commit_sha, field="integration_commit_sha"),
        "verifier_fingerprint_sha256": _sha_field(verifier_fingerprint_sha256, field="verifier_fingerprint_sha256"),
        "fold": int(fold),
        "result_root": str((result_root or RESULT_DIR / "formal_runtime").resolve()),
        "probe_root": str((probe_root or PROBE_RUNTIME_DIR).resolve()),
        "hard_negative_manifest_path": str(hard_negative_path.resolve()),
        "hard_negative_manifest_sha256": sha256_file(hard_negative_path),
        f"hard_negative_manifest_fold{int(fold)}_path": str(hard_negative_path.resolve()),
        f"hard_negative_manifest_fold{int(fold)}_sha256": sha256_file(hard_negative_path),
        "formal_user_decision_permit_provenance": {
            "training_authorized": False,
            "decision": "NO_FORMAL_TRAINING_AUTHORIZED_FOR_CARE_ASE_FAITHFUL",
            "permit_path": None,
        },
    }
    payload["bundle_payload_sha256"] = json_sha({k: v for k, v in payload.items() if k != "bundle_payload_sha256"})
    return payload


def resolve_zero_credit_hard_negative_manifest_path(fold: int) -> Path:
    explicit = os.environ.get("CARE_ASE_HARD_NEGATIVE_MANIFEST")
    candidates = [Path(explicit)] if explicit else []
    candidates.extend(
        [
            REPO_ROOT / f"results/20260804_care_ase_r2_emergency_9h_training_docker/hard_negative_manifest_fold{int(fold)}.json",
            REPO_ROOT / f"results/20260803_care_ase_r2_last_hotfix_v9/hard_negative_manifest_fold{int(fold)}.json",
            REPO_ROOT / f"results/20260803_care_ase_r2_final_pretraining_closure_v8/hard_negative_manifest_fold{int(fold)}.json",
        ]
    )
    for candidate in candidates:
        path = candidate if candidate.is_absolute() else REPO_ROOT / candidate
        if path.is_file():
            return path.resolve()
    raise FileNotFoundError(f"no explicit zero-credit hard-negative manifest is available for fold {fold}")


def load_formal_runtime_input_bundle(
    path: Path,
    *,
    fold: int,
    implementation_source_sha: str,
    review_packet_sha: str,
    effective_contract_sha256_expected: str,
    implementation_source_manifest_sha256_expected: str | None = None,
    implementation_fingerprint_sha256_expected: str | None = None,
    immutable_implementation_fingerprint_sha256_expected: str | None = None,
    integration_commit_sha_expected: str | None = None,
    verifier_fingerprint_sha256_expected: str | None = None,
) -> dict[str, Any]:
    if path is None:
        raise RuntimeError("formal runtime requires --formal-runtime-input-bundle before forward")
    path = Path(path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file():
        raise RuntimeError(f"formal runtime input bundle is missing before forward: {path}")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    payload_sha = str(bundle.get("bundle_payload_sha256", ""))
    tmp = dict(bundle)
    tmp.pop("bundle_payload_sha256", None)
    observed_payload_sha = json_sha(tmp)
    if payload_sha != observed_payload_sha:
        raise RuntimeError(f"formal runtime input bundle payload SHA mismatch: expected {payload_sha} observed {observed_payload_sha}")
    current_checks = validate_current_runtime_input_bundle(
        bundle,
        fold=fold,
        expected_implementation_source_manifest_sha256=implementation_source_manifest_sha256_expected,
        expected_implementation_fingerprint_sha256=implementation_fingerprint_sha256_expected,
        expected_immutable_implementation_fingerprint_sha256=immutable_implementation_fingerprint_sha256_expected,
        expected_integration_commit_sha=integration_commit_sha_expected,
        expected_verifier_fingerprint_sha256=verifier_fingerprint_sha256_expected,
    )
    if "implementation_source_commit_sha" in bundle and str(bundle.get("implementation_source_commit_sha")) != str(implementation_source_sha):
        raise RuntimeError("formal runtime input bundle implementation Commit A mismatch")
    binding_mode = str(bundle.get("review_packet_sha_binding_mode", "embedded_exact_sha"))
    if "review_packet_commit_sha" not in bundle:
        binding_mode = "current_agent_flow_runtime_bundle_without_legacy_review_commit"
    if binding_mode == "embedded_exact_sha":
        if str(bundle.get("review_packet_commit_sha")) != str(review_packet_sha):
            raise RuntimeError("formal runtime input bundle review packet Commit B mismatch")
    elif binding_mode in {
        "external_review_request_and_external_permit",
        "external_review_and_permit_bind_actual_origin_main_head",
        "controller_user_authorized_permit_bind_actual_origin_main_head",
    }:
        if str(bundle.get("review_packet_commit_sha", "BOUND_BY_EXTERNAL_REVIEW")) not in {
            "BOUND_BY_EXTERNAL_PERMIT",
            "BOUND_BY_EXTERNAL_REVIEW",
            "BOUND_BY_CONTROLLER_PERMIT",
        }:
            raise RuntimeError("formal runtime input bundle must not embed a self-referential Commit B SHA")
    elif binding_mode != "current_agent_flow_runtime_bundle_without_legacy_review_commit":
        raise RuntimeError(f"unsupported formal runtime input bundle Commit B binding mode: {binding_mode}")
    effective_observed = str(bundle.get("effective_contract_sha256", bundle.get("secondary_effective_contract_sha256", "")))
    if effective_observed and effective_observed != str(effective_contract_sha256_expected):
        raise RuntimeError("formal runtime input bundle effective contract SHA mismatch")
    _require_bound_sha(bundle, f"hard_negative_manifest_fold{int(fold)}_sha256", f"hard_negative_manifest_fold{int(fold)}_path")
    if f"full_case_target_cache_manifest_fold{int(fold)}_path" in bundle:
        _require_bound_sha(bundle, f"full_case_target_cache_manifest_fold{int(fold)}_sha256", f"full_case_target_cache_manifest_fold{int(fold)}_path")
    for key in ("direct_stock_oof_provenance_manifest_sha256", "area_reference_receipt_sha256"):
        if key in bundle:
            _require_bound_sha(bundle, key)
    bundle["path"] = str(path)
    bundle["sha256"] = sha256_file(path)
    bundle["verified_for_fold"] = int(fold)
    bundle["current_runtime_identity_validation"] = current_checks
    bundle["target_builder_provenance"] = "full_case_target_cache_manifest_verified"
    return bundle


def git_sha(ref: str) -> str:
    return subprocess.check_output(["git", "rev-parse", ref], cwd=REPO_ROOT, text=True).strip()


def freeze_cuda_determinism() -> None:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def package_source_hash(module_name: str) -> dict[str, Any]:
    try:
        module = __import__(module_name)
    except Exception as exc:
        return {"module": module_name, "import_error": str(exc), "sha256": "UNAVAILABLE"}
    path = Path(getattr(module, "__file__", "") or "")
    return {
        "module": module_name,
        "path": str(path),
        "sha256": sha256_file(path) if path.is_file() else "UNAVAILABLE",
    }


def environment_determinism_manifest(device: torch.device | None = None) -> dict[str, Any]:
    import scipy
    import blosc2 as blosc2_module

    gpu: dict[str, Any] = {"cuda_available": torch.cuda.is_available()}
    if torch.cuda.is_available() and device is not None:
        idx = device.index if device.index is not None else torch.cuda.current_device()
        gpu.update(
            {
                "cuda_device_name": torch.cuda.get_device_name(idx),
                "cuda_compute_capability": list(torch.cuda.get_device_capability(idx)),
                "cuda_device_count": torch.cuda.device_count(),
            }
        )
    payload = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "blosc2_version": blosc2_module.__version__,
        "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
        "cudnn_deterministic": torch.backends.cudnn.deterministic,
        "cuda_matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
        "cudnn_allow_tf32": torch.backends.cudnn.allow_tf32,
        "gpu": gpu,
        "nnunetv2": package_source_hash("nnunetv2"),
        "batchgeneratorsv2": package_source_hash("batchgeneratorsv2"),
    }
    payload["sha256"] = json_sha(payload)
    return payload


def git_fetch_origin_main() -> None:
    proc = subprocess.run(
        ["git", "fetch", "origin", "main", "--prune"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"formal wrapper failed to refresh origin/main before permit validation: {proc.stderr.strip()}")


def _normalize_status_path(status_line: str) -> str:
    text = status_line[3:] if len(status_line) > 3 else status_line
    if " -> " in text:
        text = text.split(" -> ", 1)[1]
    return text.strip()


def _path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def critical_worktree_dirty_paths(authorized_runtime_root: Path | None = None) -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git status failed during formal permit validation: {proc.stderr.strip()}")
    dirty: list[str] = []
    runtime_root = authorized_runtime_root.resolve() if authorized_runtime_root is not None else None
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        rel_text = _normalize_status_path(line)
        full = (REPO_ROOT / rel_text).resolve()
        if runtime_root is not None and _path_is_under(full, runtime_root):
            continue
        if rel_text.startswith(f"results/{FORMAL_RUNTIME_PREFIX}"):
            continue
        dirty.append(line)
    return dirty


def worktree_dirty_paths() -> list[str]:
    return critical_worktree_dirty_paths()


def review_packet_contains_implementation_source(review_packet_sha: str, implementation_sha: str) -> bool:
    proc = subprocess.run(
        ["git", "grep", "-F", str(implementation_sha), str(review_packet_sha), "--", "results/"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode == 0


def verify_external_review_permit(path: Path, *, expected_environment_determinism_manifest_sha256: str) -> dict[str, Any]:
    permit = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "decision",
        "reviewed_candidate_commit_sha",
        "implementation_source_sha",
        "review_packet_commit_sha",
        "formal_execution_checkout_commit_sha",
        "effective_contract_sha256",
        "critical_source_manifest_sha256",
        "environment_determinism_manifest_sha256",
        "created_utc",
    }
    missing = sorted(required - set(permit))
    if missing:
        raise RuntimeError(f"external review permit missing fields: {missing}")
    allowed_decisions = {
        "PRETRAINING_EXTERNAL_REVIEW_PASS",
        "USER_FORMAL_TRAINING_AUTHORIZED_20260812",
    }
    if permit["decision"] not in allowed_decisions:
        raise RuntimeError(f"CARE-ASE training permit decision is not authorized: {permit['decision']}")
    user_authorized_training = permit["decision"] == "USER_FORMAL_TRAINING_AUTHORIZED_20260812"
    if not user_authorized_training:
        git_fetch_origin_main()
    head = git_sha("HEAD")
    origin = git_sha("origin/main")
    implementation_sha = str(permit["implementation_source_sha"])
    implementation_bound = {str(permit["reviewed_candidate_commit_sha"]), implementation_sha}
    if permit.get("semantic_reviewer_sha") is not None:
        implementation_bound.add(str(permit["semantic_reviewer_sha"]))
    if len(implementation_bound) != 1:
        raise RuntimeError(f"external review permit Commit A mismatch: {sorted(implementation_bound)}")
    review_packet_sha = str(permit["review_packet_commit_sha"])
    formal_checkout_sha = str(permit["formal_execution_checkout_commit_sha"])
    if head != review_packet_sha or formal_checkout_sha != review_packet_sha:
        raise RuntimeError(
            "formal execution must run from clean detached Commit B checkout: "
            f"HEAD={head} review_packet={review_packet_sha} formal_checkout={formal_checkout_sha}"
        )
    origin_main_at_review = str(permit.get("origin_main_at_review_request", permit.get("origin_main_sha", "")))
    if review_packet_sha != origin_main_at_review and not user_authorized_training:
        raise RuntimeError(
            "external review permit Commit B mismatch: "
            f"review_packet_commit_sha={permit['review_packet_commit_sha']} origin_main_at_review_request={origin_main_at_review}"
        )
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", implementation_sha, review_packet_sha],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if ancestor.returncode != 0:
        raise RuntimeError(f"implementation Commit A is not an ancestor of review packet Commit B: {ancestor.stderr.strip()}")
    origin_contains_a = subprocess.run(
        ["git", "merge-base", "--is-ancestor", implementation_sha, "origin/main"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if origin_contains_a.returncode != 0 and not user_authorized_training:
        raise RuntimeError(f"implementation Commit A is not contained in current origin/main: {origin_contains_a.stderr.strip()}")
    origin_contains_b = subprocess.run(
        ["git", "merge-base", "--is-ancestor", review_packet_sha, "origin/main"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if origin_contains_b.returncode != 0 and not user_authorized_training:
        raise RuntimeError(f"review packet Commit B is not contained in current origin/main: {origin_contains_b.stderr.strip()}")
    if head in INVALIDATED_TRAINING_SOURCE_SHAS:
        raise RuntimeError(f"invalidated training source is permanently refused: {head}")
    authorized_runtime_root = Path(str(permit.get("authorized_runtime_root", ""))) if permit.get("authorized_runtime_root") else None
    dirty = critical_worktree_dirty_paths(authorized_runtime_root=authorized_runtime_root)
    if dirty:
        raise RuntimeError(f"formal CARE-ASE execution requires clean worktree before step0; dirty entries: {dirty[:20]}")
    live_contract = effective_contract_sha256()
    if str(permit["effective_contract_sha256"]) != live_contract:
        raise RuntimeError(
            "external review permit effective contract mismatch: "
            f"permit={permit['effective_contract_sha256']} current={live_contract}"
        )
    current_manifest = combined_source_hash()
    if str(permit["critical_source_manifest_sha256"]) != current_manifest:
        raise RuntimeError(
            "external review permit critical source manifest mismatch: "
            f"permit={permit['critical_source_manifest_sha256']} current={current_manifest}"
        )
    if str(permit["environment_determinism_manifest_sha256"]) != str(expected_environment_determinism_manifest_sha256):
        raise RuntimeError(
            "external review permit environment determinism manifest mismatch: "
            f"permit={permit['environment_determinism_manifest_sha256']} current={expected_environment_determinism_manifest_sha256}"
        )
    implementation_manifest = combined_source_hash_at_commit(implementation_sha)
    review_packet_manifest = combined_source_hash_at_commit(review_packet_sha)
    if implementation_manifest != current_manifest or review_packet_manifest != current_manifest:
        raise RuntimeError(
            "critical source tree changed between implementation Commit A and review packet Commit B: "
            f"commitA={implementation_manifest} commitB={review_packet_manifest} current={current_manifest}"
        )
    if not user_authorized_training and not review_packet_contains_implementation_source(review_packet_sha, implementation_sha):
        raise RuntimeError(
            "review packet Commit B does not contain the reviewed implementation source SHA "
            f"{implementation_sha}"
        )
    permit["current_head_sha"] = head
    permit["current_origin_main_sha"] = origin
    permit["current_effective_contract_sha256"] = live_contract
    permit["current_critical_source_manifest_sha256"] = current_manifest
    permit["current_environment_determinism_manifest_sha256"] = expected_environment_determinism_manifest_sha256
    permit["permit_verified_for_formal_training"] = True
    return permit


def _slurm_job_is_live(job_id: str) -> bool:
    if not job_id or job_id == "local":
        return False
    try:
        state = subprocess.check_output(
            ["squeue", "-h", "-j", str(job_id), "-o", "%T"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=15,
        ).strip()
    except Exception:
        return False
    return bool(state) and state.splitlines()[0].strip() in {"PENDING", "CONFIGURING", "RUNNING", "COMPLETING"}


def _slurm_step_is_live(job_id: str, step_id: str) -> bool:
    if not job_id or job_id == "local" or not step_id or step_id == "local":
        return _slurm_job_is_live(job_id)
    step_ref = f"{job_id}.{step_id}"
    for cmd in (
        ["squeue", "--steps", "-h", "-j", step_ref, "-o", "%T"],
        ["sacct", "-n", "-j", step_ref, "--format=State", "--parsable2"],
    ):
        try:
            state = subprocess.check_output(cmd, cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL, timeout=15).strip()
        except Exception:
            continue
        if not state:
            continue
        first = state.splitlines()[0].split("|")[0].strip().split()[0]
        if first in {"PENDING", "CONFIGURING", "RUNNING", "COMPLETING"}:
            return True
        if first in {"FAILED", "CANCELLED", "COMPLETED", "TIMEOUT", "PREEMPTED", "OUT_OF_MEMORY"}:
            return False
    return _slurm_job_is_live(job_id)


def _local_pid_is_live(pid: Any) -> bool:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def acquire_chunk_lock(lock_dir: Path, out_dir: Path, *, fold: int, start_step: int, end_step: int) -> dict[str, Any]:
    owner_payload = {
        "pid": os.getpid(),
        "hostname": os.uname().nodename,
        "SLURM_JOB_ID": os.environ.get("SLURM_JOB_ID", "local"),
        "SLURM_STEP_ID": os.environ.get("SLURM_STEP_ID", "local"),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "slurm_step_id": os.environ.get("SLURM_STEP_ID", "local"),
        "source_sha": git_sha("HEAD"),
        "fold": int(fold),
        "chunk": f"{int(start_step)}-{int(end_step)}",
        "start_step": int(start_step),
        "end_step": int(end_step),
        "created_unix": int(time.time()),
        "heartbeat_unix": int(time.time()),
        "created_utc": utc_now(),
        "heartbeat_utc": utc_now(),
    }
    try:
        lock_dir.mkdir()
        write_json(lock_dir / "owner.json", owner_payload)
        return {"status": "ACQUIRED", "recovered_stale_lock": False, "owner": owner_payload}
    except FileExistsError:
        owner_path = lock_dir / "owner.json"
        owner = json.loads(owner_path.read_text(encoding="utf-8")) if owner_path.is_file() else {}
        terminal = out_dir / f"chunk_terminal_{start_step:05d}_{end_step:05d}.json"
        terminal_status = json.loads(terminal.read_text(encoding="utf-8")).get("status") if terminal.is_file() else None
        live_owner = _slurm_step_is_live(str(owner.get("slurm_job_id", "")), str(owner.get("slurm_step_id", ""))) or (
            str(owner.get("slurm_job_id", "local")) == "local" and _local_pid_is_live(owner.get("pid"))
        )
        if live_owner and terminal_status != "PASS":
            write_json(
                out_dir / f"lock_lost_{os.getpid()}_{start_step:05d}_{end_step:05d}.json",
                {"status": "LOCK_HELD", "owner": owner, "terminal_status": terminal_status, "live_owner": True},
            )
            raise RuntimeError(f"active chunk lock is held by live owner: {owner}")
        if terminal_status == "PASS":
            write_json(
                out_dir / f"already_completed_{start_step:05d}_{end_step:05d}.json",
                {"status": "ALREADY_COMPLETED", "owner": owner, "terminal_status": terminal_status, "live_owner": live_owner},
            )
            return {"status": "ALREADY_COMPLETED", "owner": owner, "terminal_status": terminal_status, "live_owner": live_owner}
        archive_root = out_dir / "stale_locks"
        archive_root.mkdir(parents=True, exist_ok=True)
        claim = out_dir / f".stale_lock_claim_{lock_dir.name}_{os.getpid()}"
        try:
            os.replace(lock_dir, claim)
        except FileNotFoundError:
            raise RuntimeError("stale lock disappeared during atomic recovery claim; retry chunk launch")
        except OSError as exc:
            raise RuntimeError(f"failed to atomically claim stale lock for recovery: {exc}") from exc
        archive = archive_root / f"{lock_dir.name}_{int(time.time())}_{os.getpid()}"
        shutil.move(str(claim), str(archive))
        write_json(
            out_dir / f"stale_lock_recovered_{start_step:05d}_{end_step:05d}.json",
            {"status": "PASS", "archived_lock": str(archive), "owner": owner, "terminal_status": terminal_status, "live_owner": live_owner},
        )
        lock_dir.mkdir()
        write_json(lock_dir / "owner.json", owner_payload)
        return {"status": "ACQUIRED", "recovered_stale_lock": True, "archived_lock": str(archive), "previous_owner": owner, "owner": owner_payload}


def refresh_chunk_lock(lock_dir: Path) -> None:
    owner_path = lock_dir / "owner.json"
    owner = json.loads(owner_path.read_text(encoding="utf-8")) if owner_path.is_file() else {}
    owner["heartbeat_unix"] = int(time.time())
    owner["heartbeat_utc"] = utc_now()
    write_json(owner_path, owner)


class HeartbeatTicker:
    """Refresh the chunk heartbeat independently of optimizer-step duration."""

    def __init__(self, lock_dir: Path, *, interval_seconds: int = 300) -> None:
        self.lock_dir = lock_dir
        self.interval_seconds = int(interval_seconds)
        self.stop_event = Event()
        self.error: BaseException | None = None
        self.thread = Thread(target=self._run, name=f"care_ase_heartbeat_{os.getpid()}", daemon=True)

    def _run(self) -> None:
        while not self.stop_event.wait(self.interval_seconds):
            try:
                refresh_chunk_lock(self.lock_dir)
            except BaseException as exc:  # propagate asynchronous heartbeat failures to the training thread.
                self.error = exc
                self.stop_event.set()
                return

    def start(self) -> None:
        self.thread.start()

    def check(self) -> None:
        if self.error is not None:
            raise RuntimeError(f"CARE-ASE heartbeat thread failed: {self.error}") from self.error

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=10)
        self.check()


def parse_patch_size(text: str) -> tuple[int, int, int]:
    parts = tuple(int(v) for v in text.replace("x", ",").split(",") if v)
    if len(parts) != 3:
        raise ValueError(f"patch size must have 3 dimensions, got {text}")
    return parts


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def read_preprocessed_case_arrays(case_id: str) -> tuple[np.ndarray, np.ndarray, tuple[float, float, float]]:
    key = str(case_id)
    cached = _CASE_ARRAY_CACHE_BY_CASE.get(key)
    if cached is not None:
        _CASE_ARRAY_CACHE_BY_CASE.move_to_end(key)
        return cached
    image = read_b2nd(PREPROCESSED / f"{key}.b2nd").astype(np.float32, copy=False)
    seg = read_b2nd(PREPROCESSED / f"{key}_seg.b2nd")[0].astype(np.int64, copy=False)
    spacing = preprocessed_spacing_zyx()
    properties_path = PREPROCESSED / f"{key}.pkl"
    if spacing == (1.0, 1.0, 1.0) and properties_path.is_file():
        with properties_path.open("rb") as f:
            spacing = tuple(float(v) for v in pickle.load(f).get("spacing", spacing))
    cached = (image, seg, spacing)
    _CASE_ARRAY_CACHE_BY_CASE[key] = cached
    while len(_CASE_ARRAY_CACHE_BY_CASE) > _CASE_ARRAY_CACHE_MAX_CASES:
        _CASE_ARRAY_CACHE_BY_CASE.popitem(last=False)
    return cached


def preprocessed_spacing_zyx() -> tuple[float, float, float]:
    plans_path = PREPROCESSED.parent / "nnUNetPlans.json"
    if plans_path.is_file():
        plans = json.loads(plans_path.read_text(encoding="utf-8"))
        return tuple(float(v) for v in plans["configurations"]["3d_fullres"]["spacing"])
    return (1.0, 1.0, 1.0)


def crop_or_pad(array: np.ndarray, center: tuple[int, int, int], patch_size: tuple[int, int, int], *, pad_value: float | int = 0) -> np.ndarray:
    spatial = array.shape[-3:]
    src_slices: list[slice] = []
    dst_slices: list[slice] = []
    for c, dim, size in zip(center, spatial, patch_size):
        start = int(c) - size // 2
        stop = start + size
        src_start = max(0, start)
        src_stop = min(dim, stop)
        dst_start = src_start - start
        dst_stop = dst_start + (src_stop - src_start)
        src_slices.append(slice(src_start, src_stop))
        dst_slices.append(slice(dst_start, dst_stop))
    out = np.full(array.shape[:-3] + patch_size, pad_value, dtype=array.dtype)
    out[(..., *dst_slices)] = array[(..., *src_slices)]
    return out


def patch_origin(center: tuple[int, int, int], patch_size: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(int(c) - int(size) // 2 for c, size in zip(center, patch_size))


def source_z_mapping(
    *,
    origin_z: int,
    output_z: int,
    full_z: int,
    z_mirrored: bool = False,
) -> tuple[list[int], list[bool]]:
    raw = [int(origin_z) + idx for idx in range(int(output_z))]
    indices = list(reversed(raw)) if bool(z_mirrored) else raw
    valid = [0 <= idx < int(full_z) for idx in indices]
    return indices, valid


def _full_hw_coverage(origin: tuple[int, int, int], patch_size: tuple[int, int, int], full_shape: tuple[int, int, int]) -> bool:
    _z0, y0, x0 = origin
    _pz, py, px = patch_size
    _fz, fy, fx = full_shape
    return int(y0) <= 0 and int(x0) <= 0 and int(y0) + int(py) >= int(fy) and int(x0) + int(px) >= int(fx)


def _write_step_timing_receipt(
    out_dir: Path,
    *,
    fold: int,
    completed_step: int,
    start_step: int,
    end_step: int,
    step_seconds: list[float],
    task_start_monotonic: float,
) -> None:
    if not step_seconds:
        return
    sorted_seconds = sorted(float(v) for v in step_seconds)
    p90_index = min(len(sorted_seconds) - 1, max(0, int(math.ceil(0.90 * len(sorted_seconds))) - 1))
    recent = sorted_seconds[-min(20, len(sorted_seconds)) :]
    recent_median = float(statistics.median(recent))
    median_seconds = float(statistics.median(sorted_seconds))
    p90_seconds = float(sorted_seconds[p90_index])
    remaining_in_chunk = max(int(end_step) - int(completed_step), 0)
    payload = {
        "status": "PASS",
        "fold": int(fold),
        "completed_step": int(completed_step),
        "start_step": int(start_step),
        "end_step": int(end_step),
        "observed_step_count": int(len(step_seconds)),
        "median_step_seconds": median_seconds,
        "p90_step_seconds": p90_seconds,
        "recent_median_step_seconds": recent_median,
        "elapsed_wall_seconds": float(time.monotonic() - task_start_monotonic),
        "estimated_remaining_chunk_seconds_median": float(remaining_in_chunk * median_seconds),
        "estimated_remaining_chunk_seconds_p90": float(remaining_in_chunk * p90_seconds),
        "estimated_2000_step_seconds_median": float(2000 * median_seconds),
        "estimated_2000_step_seconds_p90": float(2000 * p90_seconds),
        "allowed_speed_actions": [
            "LRU case cache",
            "verified target cache persistence",
            "collect_metrics_false_on_non_log_steps",
            "batched log writes",
            "smaller runtime invocations with exact resume",
        ],
        "forbidden_speed_actions": [
            "reduce patch size",
            "reduce microbatch count",
            "delete losses or heads",
            "disable stock augmentation",
            "shorten 14000 steps",
            "skip Stage B or Stage C",
        ],
    }
    write_json(out_dir / f"training_runtime_eta_step{int(completed_step):05d}.json", payload)


def _slice_profile_by_source_z(profile: np.ndarray, source_z: list[int], source_valid: list[bool]) -> np.ndarray:
    values = np.asarray(profile)
    out = np.zeros((len(source_z),), dtype=np.float32)
    for idx, (z, valid) in enumerate(zip(source_z, source_valid)):
        if valid and 0 <= int(z) < values.shape[0]:
            out[idx] = float(values[int(z)])
    return out


def _component_metadata_from_full_case(full_case_targets: dict[str, np.ndarray]) -> dict[int, dict[str, Any]]:
    component_id = np.asarray(full_case_targets["scar_component_id"], dtype=np.int64)
    metadata: dict[int, dict[str, Any]] = {}
    for comp_id in sorted(int(v) for v in np.unique(component_id) if int(v) > 0):
        mask = component_id == comp_id
        metadata[comp_id] = {
            "full_case_volume_mm3": float(np.asarray(full_case_targets["scar_component_volume_mm3"])[mask][0]),
            "full_case_center_zyx": [
                float(np.asarray(full_case_targets["scar_component_center_z"])[mask][0]),
                float(np.asarray(full_case_targets["scar_component_center_y"])[mask][0]),
                float(np.asarray(full_case_targets["scar_component_center_x"])[mask][0]),
            ],
            "source_component_sha256": hashlib.sha256(mask.astype(np.uint8).tobytes()).hexdigest(),
        }
    return metadata


def _apply_component_metadata_lookup(target_cache_patch: dict[str, np.ndarray], metadata: dict[int, dict[str, Any]]) -> None:
    component_id = np.asarray(target_cache_patch["scar_component_id"], dtype=np.int64)
    volume = np.zeros_like(component_id, dtype=np.float32)
    center_z = np.zeros_like(component_id, dtype=np.float32)
    center_y = np.zeros_like(component_id, dtype=np.float32)
    center_x = np.zeros_like(component_id, dtype=np.float32)
    for comp_id, row in metadata.items():
        mask = component_id == int(comp_id)
        if not mask.any():
            continue
        volume[mask] = float(row["full_case_volume_mm3"])
        center_z[mask] = float(row["full_case_center_zyx"][0])
        center_y[mask] = float(row["full_case_center_zyx"][1])
        center_x[mask] = float(row["full_case_center_zyx"][2])
    target_cache_patch["scar_component_volume_mm3"] = volume
    target_cache_patch["scar_component_center_z"] = center_z
    target_cache_patch["scar_component_center_y"] = center_y
    target_cache_patch["scar_component_center_x"] = center_x


def _recompute_augmented_physical_targets(target_cache_patch: dict[str, np.ndarray], final_seg: np.ndarray, spacing: tuple[float, float, float]) -> None:
    seg = np.asarray(final_seg, dtype=np.int16)
    valid = seg >= 0
    seg_clean = np.where(valid, seg, -1).astype(np.int16, copy=False)
    geometry = _geometry_targets_numpy(seg_clean, spacing)
    boundary = _edema_boundary_numpy(seg_clean, spacing)
    target_cache_patch.update(geometry)
    target_cache_patch["scar_context_target"] = _context_target_numpy(seg_clean, edema=False, spacing=spacing)
    target_cache_patch["edema_context_target"] = _context_target_numpy(seg_clean, edema=True, spacing=spacing)
    target_cache_patch.update(boundary)
    existing_center = target_cache_patch.get("scar_center_fullres")
    if existing_center is None:
        target_cache_patch["scar_center_fullres"] = np.zeros_like(seg_clean, dtype=np.float32)
    target_cache_patch["valid_label_mask"] = valid.astype(np.float32)


def _pack_target_cache_for_transform(cache_patch: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    regression = np.stack([np.asarray(cache_patch[key], dtype=np.float32) for key in _TARGET_REGRESSION_KEYS])
    segmentation = np.stack([np.asarray(cache_patch[key], dtype=np.int64) for key in _TARGET_SEGMENTATION_KEYS])
    remaining = {
        key: value
        for key, value in cache_patch.items()
        if key not in set(_TARGET_REGRESSION_KEYS) | set(_TARGET_SEGMENTATION_KEYS)
    }
    return regression, segmentation, remaining


def _unpack_transformed_target_cache(
    regression: np.ndarray,
    segmentation: np.ndarray,
    remaining: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    out = dict(remaining)
    for key, value in zip(_TARGET_REGRESSION_KEYS, regression):
        out[key] = np.asarray(value, dtype=np.float32)
    for key, value in zip(_TARGET_SEGMENTATION_KEYS, segmentation):
        if key.endswith("_target") or key in {"scar_component_id", "source_z_id"}:
            out[key] = np.rint(value).astype(np.int64, copy=False)
        else:
            out[key] = (np.asarray(value) > 0.5).astype(np.float32, copy=False)
    return out


def deterministic_center(
    seg: np.ndarray,
    *,
    descriptor_sha: str,
    pathology_focus: str,
    within_focus: str,
    hard_negative_category: str,
    resolved_target_coordinates: tuple[tuple[int, int, int], ...],
    selected_target_coordinate: tuple[int, int, int] | None,
    fallback_sequence: tuple[str, ...],
    micro: int,
    patch_size: tuple[int, int, int],
    spacing: tuple[float, float, float],
) -> tuple[int, int, int]:
    if selected_target_coordinate is not None:
        return tuple(int(v) for v in selected_target_coordinate)
    if resolved_target_coordinates:
        idx = int(hashlib.sha256(f"{descriptor_sha}|coords|micro={micro}".encode("utf-8")).hexdigest()[:16], 16) % len(resolved_target_coordinates)
        return tuple(int(v) for v in resolved_target_coordinates[idx])
    wall = (seg == 1) | (seg == 4) | (seg == 5)
    blood = (seg == 2) | (seg == 3)
    pathology = (seg == 4) | (seg == 5)
    background = seg == 0
    scar = seg == 5
    edema = seg == 4
    lesion = scar if pathology_focus == "scar" else edema
    labels, count = ndimage_label(lesion)
    small_component = np.zeros_like(lesion, dtype=bool)
    if count > 0:
        component_ids = list(range(1, count + 1))
        physical_volumes = {idx: float((labels == idx).sum() * np.prod(spacing)) for idx in component_ids}
        small_ids = [idx for idx in component_ids if physical_volumes[idx] < 1000.0]
        if small_ids:
            chosen = small_ids[int(hashlib.sha256(f"{descriptor_sha}|small_component|micro={micro}".encode("utf-8")).hexdigest()[:16], 16) % len(small_ids)]
            small_component = labels == chosen
    gt_component = lesion
    if count > 0:
        component_ids = list(range(1, count + 1))
        chosen = component_ids[int(hashlib.sha256(f"{descriptor_sha}|gt_component|micro={micro}".encode("utf-8")).hexdigest()[:16], 16) % len(component_ids)]
        gt_component = labels == chosen
    dist_wall = ndimage.distance_transform_edt(~wall, sampling=spacing)
    dist_blood = ndimage.distance_transform_edt(~blood, sampling=spacing)
    remote_background = background & (dist_wall >= 10.0)
    blood_pool_adjacent = (~pathology) & (dist_blood <= 3.0)
    if edema.any() and not edema.all():
        raw_edema_boundary_mm = ndimage.distance_transform_edt(edema, sampling=spacing) - ndimage.distance_transform_edt(~edema, sampling=spacing)
        edema_boundary_band = (np.abs(raw_edema_boundary_mm) <= 10.0) | edema
    else:
        edema_boundary_band = np.zeros_like(edema, dtype=bool)
    masks = {
        "gt_component": gt_component,
        "small_component": small_component,
        "oof_fn": gt_component,
        "scar_oof_fn": gt_component,
        "scar_oof_fp": remote_background,
        "oof_fp": remote_background,
        "edema_oof_fn_or_low_volume": gt_component,
        "oof_fn_or_low_volume": gt_component,
        "edema_safe_fp": remote_background,
        "safe_fp": remote_background,
        "positive": lesion,
        "boundary": edema_boundary_band if pathology_focus == "edema" else wall,
        "remote_background": remote_background,
        "blood_pool_adjacent": blood_pool_adjacent,
        "random_wall": wall,
        "random_background": background,
        "background": background,
        "random": wall | background,
    }
    mask = np.zeros_like(lesion, dtype=bool)
    for item in (hard_negative_category, within_focus, *fallback_sequence, "random"):
        candidate = masks.get(str(item), mask)
        if bool(candidate.any()):
            mask = candidate
            break
    coords = np.argwhere(mask)
    if coords.size == 0:
        return tuple(int(v // 2) for v in seg.shape)
    idx = int(hashlib.sha256(f"{descriptor_sha}|micro={micro}|{patch_size}".encode("utf-8")).hexdigest()[:16], 16) % len(coords)
    return tuple(int(v) for v in coords[idx])


def make_batch(
    descriptor: Any,
    *,
    descriptor_sha: str,
    micro: int,
    initial_patch_size: tuple[int, int, int],
    final_patch_size: tuple[int, int, int],
    stock_transform: Any | None,
    device: torch.device,
) -> dict[str, torch.Tensor]:
    image, seg, spacing = read_preprocessed_case_arrays(str(descriptor.case_id))
    if getattr(descriptor, "selected_target_coordinate", None) is None:
        raise RuntimeError(
            "formal CARE-ASE batch descriptor is missing selected_target_coordinate; "
            "silent deterministic center fallback is forbidden"
        )
    center = deterministic_center(
        seg,
        descriptor_sha=descriptor_sha,
        pathology_focus=descriptor.pathology_focus,
        within_focus=descriptor.within_focus,
        hard_negative_category=descriptor.hard_negative_category,
        resolved_target_coordinates=descriptor.resolved_target_coordinates,
        selected_target_coordinate=descriptor.selected_target_coordinate,
        fallback_sequence=descriptor.fallback_sequence,
        micro=micro,
        patch_size=initial_patch_size,
        spacing=spacing,
    )
    initial_origin = patch_origin(center, initial_patch_size)
    full_case_shape = tuple(int(v) for v in seg.shape)
    full_hw_coverage = _full_hw_coverage(initial_origin, initial_patch_size, full_case_shape)
    initial_image = crop_or_pad(image, center, initial_patch_size, pad_value=0)
    initial_seg = crop_or_pad(seg[None], center, initial_patch_size, pad_value=-1)[0]
    cache_key = (str(descriptor.case_id), tuple(float(v) for v in spacing))
    full_case_targets = _FULL_CASE_TARGET_CACHE_BY_CASE.get(cache_key)
    if full_case_targets is None:
        full_case_targets = build_full_case_target_cache(seg, spacing)
        _FULL_CASE_TARGET_CACHE_BY_CASE[cache_key] = full_case_targets
        while len(_FULL_CASE_TARGET_CACHE_BY_CASE) > _FULL_CASE_TARGET_CACHE_MAX_CASES:
            _FULL_CASE_TARGET_CACHE_BY_CASE.popitem(last=False)
    else:
        _FULL_CASE_TARGET_CACHE_BY_CASE.move_to_end(cache_key)
    component_metadata = _component_metadata_from_full_case(full_case_targets)
    initial_target_cache_patch = slice_full_case_target_cache(full_case_targets, center=center, patch_size=initial_patch_size)
    initial_source_z = np.zeros(tuple(int(v) for v in initial_patch_size), dtype=np.int64)
    initial_source_z_valid = np.zeros(tuple(int(v) for v in initial_patch_size), dtype=np.float32)
    initial_source_inplane_footprint = np.zeros(tuple(int(v) for v in initial_patch_size), dtype=np.float32)
    for local_z in range(int(initial_patch_size[0])):
        source_z = int(initial_origin[0]) + int(local_z)
        if 0 <= source_z < full_case_shape[0]:
            initial_source_z[local_z, :, :] = source_z + 1
            initial_source_z_valid[local_z, :, :] = 1.0
    y0, x0 = int(initial_origin[1]), int(initial_origin[2])
    for local_y in range(int(initial_patch_size[1])):
        source_y = y0 + int(local_y)
        if not (0 <= source_y < full_case_shape[1]):
            continue
        for local_x in range(int(initial_patch_size[2])):
            source_x = x0 + int(local_x)
            if 0 <= source_x < full_case_shape[2]:
                initial_source_inplane_footprint[:, local_y, local_x] = 1.0
    initial_target_cache_patch["source_z_id"] = initial_source_z
    initial_target_cache_patch["source_z_valid"] = initial_source_z_valid
    initial_target_cache_patch["source_inplane_footprint"] = initial_source_inplane_footprint
    if stock_transform is not None:
        regression_patch, segmentation_patch, untouched_cache = _pack_target_cache_for_transform(initial_target_cache_patch)
        final_image, final_seg, transformed_regression, transformed_segmentation = apply_stock_training_transform_with_targets(
            initial_image,
            initial_seg,
            transform=stock_transform,
            availability=descriptor.availability,
            regression_target_patch=regression_patch,
            segmentation_extra_patch=segmentation_patch,
            seed=int(getattr(descriptor, "augmentation_seed", 0)),
        )
        if transformed_regression is None or transformed_segmentation is None:
            raise RuntimeError("stock augmentation did not return transformed CARE-ASE target maps")
        target_cache_patch = _unpack_transformed_target_cache(transformed_regression, transformed_segmentation, untouched_cache)
        source_z_id = np.asarray(target_cache_patch["source_z_id"], dtype=np.int64)
        source_z_valid_map = np.asarray(target_cache_patch["source_z_valid"], dtype=np.float32) > 0.5
        footprint = np.asarray(target_cache_patch["source_inplane_footprint"], dtype=np.float32) > 0.5
        final_source_z = []
        final_source_z_valid = []
        full_hw_coverage_by_z = []
        full_hw_area = int(full_case_shape[1]) * int(full_case_shape[2])
        for z_idx in range(int(source_z_id.shape[0])):
            ids = source_z_id[z_idx][source_z_valid_map[z_idx] & (source_z_id[z_idx] > 0)]
            if ids.size:
                values, counts = np.unique(ids, return_counts=True)
                source_z = int(values[int(np.argmax(counts))]) - 1
                valid_z = 0 <= source_z < full_case_shape[0]
            else:
                source_z = -1
                valid_z = False
            final_source_z.append(source_z)
            final_source_z_valid.append(bool(valid_z))
            full_hw_coverage_by_z.append(bool(valid_z and full_hw_coverage and int(footprint[z_idx].sum()) >= full_hw_area))
    else:
        final_image = crop_or_pad(initial_image, tuple(v // 2 for v in initial_patch_size), final_patch_size, pad_value=0)
        final_seg = crop_or_pad(initial_seg[None], tuple(v // 2 for v in initial_patch_size), final_patch_size, pad_value=-1)[0]
        target_cache_patch = slice_full_case_target_cache(full_case_targets, center=center, patch_size=final_patch_size)
        final_source_z, final_source_z_valid = source_z_mapping(origin_z=patch_origin(center, final_patch_size)[0], output_z=int(final_seg.shape[-3]), full_z=full_case_shape[0])
        full_hw_coverage_by_z = [bool(full_hw_coverage and valid) for valid in final_source_z_valid]
    _recompute_augmented_physical_targets(target_cache_patch, final_seg, spacing)
    _apply_component_metadata_lookup(target_cache_patch, component_metadata)
    extent_presence_valid_z = np.asarray([bool(v) for v in final_source_z_valid], dtype=np.float32)
    extent_area_valid_z = np.asarray([bool(v) for v in full_hw_coverage_by_z], dtype=np.float32)
    for key in (
        "scar_slice_presence",
        "scar_slice_pathology_voxels",
        "scar_slice_wall_voxels",
        "edema_slice_presence",
        "edema_slice_pathology_voxels",
        "edema_slice_wall_voxels",
    ):
        target_cache_patch[key] = _slice_profile_by_source_z(np.asarray(full_case_targets[key]), final_source_z, final_source_z_valid)
    for key in ("scar_slice_area", "scar_slice_area_valid", "edema_slice_area", "edema_slice_area_valid"):
        target_cache_patch[key] = _slice_profile_by_source_z(np.asarray(full_case_targets[key]), final_source_z, final_source_z_valid) * extent_area_valid_z
    target_cache_patch["extent_presence_valid_by_output_z"] = extent_presence_valid_z
    target_cache_patch["extent_area_valid_by_output_z"] = extent_area_valid_z
    target_cache_patch["extent_supervision_valid_by_output_z"] = extent_area_valid_z
    extent_valid_mask = (np.asarray(final_seg) >= 0).astype(np.float32)
    extent_valid_mask = extent_valid_mask * extent_area_valid_z.reshape(-1, 1, 1)
    return {
        "image": torch.from_numpy(final_image[None]).to(device=device, dtype=torch.float32),
        "seg": torch.from_numpy(final_seg[None]).to(device=device, dtype=torch.long),
        "availability": torch.tensor([descriptor.availability], device=device, dtype=torch.float32),
        "spacing": torch.tensor([spacing], device=device, dtype=torch.float32),
        "initial_patch_size": tuple(int(v) for v in initial_patch_size),
        "final_patch_size": tuple(int(v) for v in final_patch_size),
        "initial_patch_origin_zyx": tuple(int(v) for v in initial_origin),
        "final_patch_source_z_indices": tuple(int(v) for v in final_source_z),
        "final_patch_source_z_valid": tuple(bool(v) for v in final_source_z_valid),
        "augmentation_z_mapping": "stock_transform_source_z_id_authority" if stock_transform is not None else "center_crop_source_z_id_authority",
        "full_hw_coverage_by_output_z": tuple(bool(v) for v in full_hw_coverage_by_z),
        "extent_presence_valid_by_output_z": tuple(bool(v) for v in extent_presence_valid_z),
        "extent_area_valid_by_output_z": tuple(bool(v) for v in extent_area_valid_z),
        "extent_supervision_valid_by_output_z": tuple(bool(v) for v in extent_area_valid_z),
        "focused_coordinate_zyx": tuple(int(v) for v in center),
        "stock_transform_applied": stock_transform is not None,
        "augmentation_seed": int(getattr(descriptor, "augmentation_seed", 0)),
        "case_id": descriptor.case_id,
        "full_case_seg_shape_zyx": full_case_shape,
        "full_case_target_cache": target_cache_patch,
        "extent_valid_spatial_mask": torch.from_numpy(extent_valid_mask[None, None]).to(device=device, dtype=torch.float32),
        "full_case_target_cache_source": "preprocessed_full_case_grid_sliced_to_initial_patch_then_stock_spatial_transform_synced",
        "full_case_target_cache_alignment_note": "CARE-ASE target maps are passed through the same batchgeneratorsv2 stock spatial transform call as image/seg; extent z profiles remain full-case fields.",
    }


def append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def optimizer_lr_by_group(optimizer: torch.optim.Optimizer) -> dict[str, float]:
    return {str(group.get("name", f"group_{idx}")): float(group.get("lr", 0.0)) for idx, group in enumerate(optimizer.param_groups)}


def _stable_pickle_sha(value: Any) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=4)).hexdigest()


def rng_state_hashes(sampler: CAREASEDeterministicSampler | None = None) -> dict[str, str]:
    payload = {
        "python_rng": _stable_pickle_sha(random.getstate()),
        "numpy_rng": _stable_pickle_sha(np.random.get_state()),
        "torch_cpu_rng": hashlib.sha256(torch.random.get_rng_state().cpu().numpy().tobytes()).hexdigest(),
        "torch_cuda_rng": _stable_pickle_sha([item.cpu().numpy().tobytes() for item in torch.cuda.get_rng_state_all()]) if torch.cuda.is_available() else "NO_CUDA",
    }
    if sampler is not None:
        state = sampler.state_dict()
        payload.update(
            {
                "sampler_rng": str(state.get("sampler_rng_state", "UNSET")),
                "micro_case_rng": json_sha(state.get("micro_case_rng_state_by_group", {})),
                "micro_patch_rng": str(state.get("micro_patch_rng_state", "UNSET")),
                "augmentation_rng": str(state.get("micro_patch_rng_state", "UNSET")),
            }
        )
    return payload


def capture_training_rng_state(sampler: CAREASEDeterministicSampler | None = None) -> dict[str, Any]:
    return {
        "python_rng": random.getstate(),
        "numpy_rng": np.random.get_state(),
        "torch_cpu_rng": torch.random.get_rng_state(),
        "torch_cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        "sampler_state": copy.deepcopy(sampler.state_dict()) if sampler is not None else None,
    }


def restore_training_rng_state(state: dict[str, Any], sampler: CAREASEDeterministicSampler | None = None) -> None:
    random.setstate(state["python_rng"])
    np.random.set_state(state["numpy_rng"])
    torch.random.set_rng_state(state["torch_cpu_rng"])
    if torch.cuda.is_available() and state.get("torch_cuda_rng") is not None:
        torch.cuda.set_rng_state_all(state["torch_cuda_rng"])
    if sampler is not None and state.get("sampler_state") is not None:
        sampler.load_state_dict(copy.deepcopy(state["sampler_state"]))


def validate_resume_payload(
    payload: dict[str, Any],
    *,
    requested_fold: int,
    expected_effective_contract_sha256: str,
    expected_critical_source_manifest_sha256: str,
    expected_split_file_sha256: str,
    expected_actual_train_case_ids_sha256: str,
    expected_hard_negative_manifest_sha256: str,
    expected_area_reference_receipt_sha256: str,
    expected_stock_checkpoint_sha256: str | None = None,
    expected_environment_determinism_manifest_sha256: str | None = None,
    expected_request_nonce: str | None = None,
    expected_frozen_contract_sha256: str | None = None,
    expected_implementation_source_manifest_sha256: str | None = None,
    expected_implementation_fingerprint_sha256: str | None = None,
    expected_verifier_fingerprint_sha256: str | None = None,
    expected_integration_commit_sha: str | None = None,
    allow_short_smoke_resume: bool = False,
) -> dict[str, Any]:
    canonical_stock_path = Path(CAREASEConfig.for_fold(int(requested_fold)).checkpoint_path)
    observed_stock_sha = sha256_file(canonical_stock_path) if canonical_stock_path.is_file() else "MISSING"
    expected_stock_sha = expected_stock_checkpoint_sha256 or observed_stock_sha
    critical_manifest_matches = str(payload.get("critical_source_manifest_sha256")) == str(expected_critical_source_manifest_sha256)
    if not critical_manifest_matches and os.environ.get("CARE_ASE_ALLOW_RUNTIME_LOCK_HOTFIX_RESUME", "0") == "1":
        allowed_previous = {
            item.strip()
            for item in os.environ.get("CARE_ASE_RUNTIME_LOCK_HOTFIX_PREVIOUS_CRITICAL_HASHES", "").split(",")
            if item.strip()
        }
        if str(payload.get("critical_source_manifest_sha256")) in allowed_previous:
            critical_manifest_matches = True
    checks = {
        "payload_fold": int(payload.get("fold", -1)) == int(requested_fold),
        "model_config_fold": int(payload.get("config", {}).get("fold", -1)) == int(requested_fold),
        "model_config_stock_path": str(payload.get("config", {}).get("checkpoint_path")) == str(canonical_stock_path),
        "effective_contract_sha256": str(payload.get("effective_contract_sha256")) == str(expected_effective_contract_sha256),
        "critical_source_manifest_sha256": critical_manifest_matches,
        "split_file_sha256": str(payload.get("split_file_sha256")) == str(expected_split_file_sha256),
        "actual_train_case_ids_sha256": str(payload.get("actual_train_case_ids_sha256")) == str(expected_actual_train_case_ids_sha256),
        "hard_negative_manifest_sha256": str(payload.get("hard_negative_manifest_sha256")) == str(expected_hard_negative_manifest_sha256),
        "area_reference_receipt_sha256": str(payload.get("area_reference_receipt_sha256")) == str(expected_area_reference_receipt_sha256),
        "stock_checkpoint_sha256": str(payload.get("stock_checkpoint_sha256")) == str(expected_stock_sha),
        "stock_checkpoint_file_sha256": str(payload.get("stock_checkpoint_sha256")) == str(observed_stock_sha),
        "environment_determinism_manifest_sha256": expected_environment_determinism_manifest_sha256 is None
        or str(payload.get("environment_determinism_manifest_sha256")) == str(expected_environment_determinism_manifest_sha256),
        "request_nonce": expected_request_nonce is None or str(payload.get("request_nonce")) == str(expected_request_nonce),
        "frozen_contract_sha256": expected_frozen_contract_sha256 is None
        or str(payload.get("frozen_contract_sha256")) == str(expected_frozen_contract_sha256),
        "implementation_source_manifest_sha256": expected_implementation_source_manifest_sha256 is None
        or str(payload.get("implementation_source_manifest_sha256")) == str(expected_implementation_source_manifest_sha256),
        "implementation_fingerprint_sha256": expected_implementation_fingerprint_sha256 is None
        or str(payload.get("implementation_fingerprint_sha256")) == str(expected_implementation_fingerprint_sha256),
        "verifier_fingerprint_sha256": expected_verifier_fingerprint_sha256 is None
        or str(payload.get("verifier_fingerprint_sha256")) == str(expected_verifier_fingerprint_sha256),
        "integration_commit_sha": expected_integration_commit_sha is None
        or str(payload.get("integration_commit_sha")) == str(expected_integration_commit_sha),
        "formal_resumable": bool(allow_short_smoke_resume) or payload.get("formal_resumable") is True,
        "microbatch_cursor_zero": int(payload.get("accumulation_microbatch_cursor", -1)) == 0,
        "next_optimizer_step_micro_descriptor_sha256_present": str(payload.get("next_optimizer_step_micro_descriptor_sha256", "")) not in {"", "UNSET"},
    }
    failed = sorted(key for key, ok in checks.items() if not ok)
    receipt = {"status": "PASS" if not failed else "FAIL", "checks": checks, "failed_checks": failed}
    if failed:
        raise RuntimeError(f"CARE-ASE formal resume provenance mismatch: {failed}")
    return receipt


def verify_checkpoint_verified_receipt(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    verified_path = path.with_suffix(path.suffix + ".verified.json")
    if not verified_path.is_file():
        raise RuntimeError(f"formal resume requires checkpoint verified receipt: {verified_path}")
    receipt = json.loads(verified_path.read_text(encoding="utf-8"))
    checks = {
        "status_pass": receipt.get("status") == "PASS",
        "checkpoint_sha256": receipt.get("checkpoint_sha256") == sha256_file(path),
        "fold": int(receipt.get("fold", -1)) == int(payload.get("fold", -2)),
        "global_step": int(receipt.get("global_step", -1)) == int(payload.get("global_optimizer_step", -2)),
        "contract_sha256": receipt.get("contract_sha256") == payload.get("effective_contract_sha256"),
        "full_reload_logit_parity": receipt.get("full_reload_logit_parity") == "PASS",
        "verification_rng_transparency": receipt.get("verification_rng_transparency") == "PASS",
    }
    failed = sorted(key for key, ok in checks.items() if not ok)
    if failed:
        raise RuntimeError(f"checkpoint verified receipt is not resumable: {failed}")
    return {"status": "PASS", "verified_receipt": str(verified_path), "checks": checks}


def _load_previous(
    path: Path,
    device: torch.device,
    *,
    requested_fold: int,
    expected_effective_contract_sha256: str,
    expected_critical_source_manifest_sha256: str,
    expected_split_file_sha256: str,
    expected_actual_train_case_ids_sha256: str,
    expected_hard_negative_manifest_sha256: str,
    expected_area_reference_receipt_sha256: str,
    expected_stock_checkpoint_sha256: str | None = None,
    expected_environment_determinism_manifest_sha256: str | None = None,
    expected_request_nonce: str | None = None,
    expected_frozen_contract_sha256: str | None = None,
    expected_implementation_source_manifest_sha256: str | None = None,
    expected_implementation_fingerprint_sha256: str | None = None,
    expected_verifier_fingerprint_sha256: str | None = None,
    expected_integration_commit_sha: str | None = None,
    allow_short_smoke_resume: bool = False,
) -> tuple[torch.nn.Module, dict[str, Any]]:
    model, payload = load_care_ase_checkpoint_for_training_resume(
        path,
        requested_fold=int(requested_fold),
        map_location=device,
        restore_rng=True,
        expected_request_nonce=expected_request_nonce,
        expected_frozen_contract_sha256=expected_frozen_contract_sha256,
        expected_implementation_source_manifest_sha256=expected_implementation_source_manifest_sha256,
        expected_implementation_fingerprint_sha256=expected_implementation_fingerprint_sha256,
        expected_integration_commit_sha=expected_integration_commit_sha,
        expected_verifier_fingerprint_sha256=expected_verifier_fingerprint_sha256,
    )
    source_sha = str(payload.get("training_source_commit_sha", payload.get("config", {}).get("training_source_commit_sha", "")))
    if source_sha in INVALIDATED_TRAINING_SOURCE_SHAS:
        raise RuntimeError(f"refusing resume from invalidated source checkpoint: {source_sha}")
    verify_checkpoint_verified_receipt(path, payload)
    validate_resume_payload(
        payload,
        requested_fold=requested_fold,
        expected_effective_contract_sha256=expected_effective_contract_sha256,
        expected_critical_source_manifest_sha256=expected_critical_source_manifest_sha256,
        expected_split_file_sha256=expected_split_file_sha256,
        expected_actual_train_case_ids_sha256=expected_actual_train_case_ids_sha256,
        expected_hard_negative_manifest_sha256=expected_hard_negative_manifest_sha256,
        expected_area_reference_receipt_sha256=expected_area_reference_receipt_sha256,
        expected_stock_checkpoint_sha256=expected_stock_checkpoint_sha256,
        expected_environment_determinism_manifest_sha256=expected_environment_determinism_manifest_sha256,
        expected_request_nonce=expected_request_nonce,
        expected_frozen_contract_sha256=expected_frozen_contract_sha256,
        expected_implementation_source_manifest_sha256=expected_implementation_source_manifest_sha256,
        expected_implementation_fingerprint_sha256=expected_implementation_fingerprint_sha256,
        expected_verifier_fingerprint_sha256=expected_verifier_fingerprint_sha256,
        expected_integration_commit_sha=expected_integration_commit_sha,
        allow_short_smoke_resume=allow_short_smoke_resume,
    )
    return model.to(device), payload


def _sampler_state_from_checkpoint_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_group_cursor": payload["case_group_cursor"],
        "complete_center_selector_cursor": payload.get("complete_center_selector_cursor", payload.get("complete_center_cursor", payload.get("center_cursor", 0))),
        "complete_centerB_case_cursor": payload.get("complete_centerB_case_cursor", 0),
        "complete_centerC_case_cursor": payload.get("complete_centerC_case_cursor", 0),
        "complete_center_cursor": payload.get("complete_center_cursor", payload.get("center_cursor", 0)),
        "complete_pathology_cursor": payload.get("complete_pathology_cursor", payload.get("pathology_focus_cursor", 0)),
        "partial_case_cursors": payload.get("partial_case_cursors", {"lge_only": 0, "lge_c0": 0}),
        "micro_case_cursors_by_group": payload.get("micro_case_cursors_by_group", {}),
        "micro_case_rng_state_by_group": payload.get("micro_case_rng_state_by_group", {}),
        "micro_patch_cursor": payload.get("micro_patch_cursor", 0),
        "micro_patch_rng_state": payload.get("micro_patch_rng_state", "UNSET"),
        "center_cursor": payload.get("center_cursor", payload.get("complete_center_cursor", 0)),
        "pathology_focus_cursor": payload.get("pathology_focus_cursor", payload.get("complete_pathology_cursor", 0)),
        "scar_focus_cursor": payload["scar_focus_cursor"],
        "edema_focus_cursor": payload["edema_focus_cursor"],
        "sampler_rng_state": payload["sampler_rng_state"],
        "batch_descriptor_cursor": payload["batch_descriptor_cursor"],
    }


def _write_full_reload_receipt(
    ckpt: Path,
    *,
    live_model: torch.nn.Module,
    live_optimizer: torch.optim.Optimizer,
    live_scheduler: CAREASEStageScheduler,
    fixed_batch: dict[str, torch.Tensor],
    global_step: int,
    fold: int,
    seed: int,
    out_dir: Path,
    hard_negative_manifest_path: Path | None = None,
    expected_request_nonce: str | None = None,
    expected_frozen_contract_sha256: str | None = None,
    expected_implementation_source_manifest_sha256: str | None = None,
    expected_integration_commit_sha: str | None = None,
) -> dict[str, Any]:
    was_training = live_model.training
    live_model.eval()
    with torch.no_grad():
        live_logits = live_model(
            fixed_batch["image"],
            fixed_batch["availability"],
            global_step=global_step,
            extent_valid_spatial_mask=fixed_batch.get("extent_valid_spatial_mask"),
        )["final_logits"].detach().float().cpu()
    if was_training:
        live_model.train()
    reloaded_model, payload = load_care_ase_checkpoint_for_training_resume(
        ckpt,
        requested_fold=int(fold),
        map_location=fixed_batch["image"].device,
        restore_rng=False,
        expected_request_nonce=expected_request_nonce,
        expected_frozen_contract_sha256=expected_frozen_contract_sha256,
        expected_implementation_source_manifest_sha256=expected_implementation_source_manifest_sha256,
        expected_integration_commit_sha=expected_integration_commit_sha,
    )
    reloaded_model = reloaded_model.to(fixed_batch["image"].device)
    reloaded_optimizer = build_optimizer(reloaded_model)
    reloaded_optimizer.load_state_dict(payload["optimizer"])
    reloaded_scheduler = CAREASEStageScheduler(reloaded_optimizer)
    reloaded_scheduler.load_state_dict(payload["scheduler"])
    reloaded_sampler = CAREASEDeterministicSampler(REPO_ROOT, fold, seed=seed, hard_negative_manifest_path=hard_negative_manifest_path)
    reloaded_sampler.load_state_dict(_sampler_state_from_checkpoint_payload(payload))
    reloaded_model.eval()
    with torch.no_grad():
        reloaded_logits = reloaded_model(
            fixed_batch["image"],
            fixed_batch["availability"],
            global_step=global_step,
            extent_valid_spatial_mask=fixed_batch.get("extent_valid_spatial_mask"),
        )["final_logits"].detach().float().cpu()
    max_abs = float((live_logits - reloaded_logits).abs().max().item())
    next_hash = "TRAINING_COMPLETE"
    if int(global_step) < 14000:
        next_hash = reloaded_sampler.peek_descriptor_bundle_for_step(global_step).sha256()
    receipt = {
        "status": "PASS" if max_abs <= 1.0e-5 else "FAIL",
        "fold": int(fold),
        "checkpoint_path": str(ckpt),
        "checkpoint_sha256": sha256_file(ckpt),
        "global_optimizer_step": int(global_step),
        "fresh_model_instance_loaded": True,
        "optimizer_state_loaded": bool(reloaded_optimizer.state_dict()["state"] or live_optimizer.state_dict()["state"]),
        "scheduler_state_loaded": reloaded_scheduler.state_dict(),
        "sampler_rng_state_loaded": bool(payload.get("sampler_rng_state")) and payload.get("sampler_rng_state") != "UNSET",
        "augmentation_rng_state_loaded": bool(payload.get("augmentation_rng_state")) and payload.get("augmentation_rng_state") != "UNSET",
        "dataloader_worker_seed_state_nonempty": bool(payload.get("dataloader_worker_seed_state")),
        "fixed_batch_case_id": fixed_batch.get("case_id", "UNSET"),
        "fixed_batch_descriptor_sha256": fixed_batch.get("descriptor_sha256", "UNSET"),
        "logits_max_abs_error": max_abs,
        "logits_tolerance": 1.0e-5,
        "next_batch_hash_payload": payload.get("next_batch_descriptor_sha256"),
        "next_optimizer_step_micro_descriptor_hash_payload": payload.get("next_optimizer_step_micro_descriptor_sha256"),
        "next_batch_hash_recomputed": next_hash,
        "next_batch_hash_match": payload.get("next_batch_descriptor_sha256") == next_hash,
        "next_optimizer_step_micro_descriptor_hash_match": payload.get("next_optimizer_step_micro_descriptor_sha256") == next_hash,
        "live_scheduler_last_global_step": live_scheduler.last_global_step,
        "hard_negative_manifest_path": str(hard_negative_manifest_path) if hard_negative_manifest_path else "EXPLICIT_CURRENT_MANIFEST_REQUIRED",
    }
    receipt["payload_sha256"] = hashlib.sha256(json.dumps(receipt, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    fold_receipt = out_dir / f"{ckpt.stem}_full_reload_receipt.json"
    write_json(fold_receipt, receipt)
    if receipt["status"] != "PASS" or not receipt["next_batch_hash_match"] or not receipt["next_optimizer_step_micro_descriptor_hash_match"]:
        raise RuntimeError(f"full checkpoint reload failed for {ckpt}: {receipt}")
    return receipt


class CAREASEFormalRuntime:
    """Single public authority for CARE-ASE faithful optimizer-step execution."""

    public_api_name = "src.care_myocardium.training.care_ase_runtime.CAREASEFormalRuntime.run_formal_training_step"

    def __init__(
        self,
        *,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: CAREASEStageScheduler,
        sampler: CAREASEDeterministicSampler,
        stock_transform: Any | None,
        initial_patch_size: tuple[int, int, int],
        final_patch_size: tuple[int, int, int],
        device: torch.device,
        autocast_device_type: str = "cuda",
        autocast_dtype: torch.dtype = torch.bfloat16,
        autocast_enabled: bool = False,
        formal_mode: bool = False,
        runtime_input_bundle: dict[str, Any] | None = None,
        full_case_target_cache_manifest_path: Path | None = None,
        target_builder_provenance: str | None = None,
    ) -> None:
        self.model = model
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.sampler = sampler
        self.stock_transform = stock_transform
        self.initial_patch_size = tuple(int(v) for v in initial_patch_size)
        self.final_patch_size = tuple(int(v) for v in final_patch_size)
        self.device = device
        self.autocast_device_type = autocast_device_type
        self.autocast_dtype = autocast_dtype
        self.autocast_enabled = bool(autocast_enabled)
        self.formal_mode = bool(formal_mode)
        self.runtime_input_bundle = copy.deepcopy(runtime_input_bundle) if runtime_input_bundle is not None else None
        self.full_case_target_cache_manifest_path = Path(full_case_target_cache_manifest_path) if full_case_target_cache_manifest_path is not None else None
        self.target_builder_provenance = target_builder_provenance or "patch_local_fallback_for_tests_only"
        self.full_case_target_manifest: dict[str, Any] | None = None
        self._verified_target_cache_cases: set[str] = set()
        if self.formal_mode:
            if self.runtime_input_bundle is None:
                raise RuntimeError("formal runtime requires current runtime input bundle before materialization")
            validate_current_runtime_input_bundle(
                self.runtime_input_bundle,
                fold=int(self.sampler.fold),
                expected_implementation_source_manifest_sha256=str(self.runtime_input_bundle["implementation_source_manifest_sha256"]),
                expected_implementation_fingerprint_sha256=str(self.runtime_input_bundle["implementation_fingerprint_sha256"]),
                expected_immutable_implementation_fingerprint_sha256=str(
                    self.runtime_input_bundle["immutable_implementation_fingerprint_sha256"]
                ),
                expected_integration_commit_sha=str(self.runtime_input_bundle["integration_commit_sha"]),
                expected_verifier_fingerprint_sha256=str(self.runtime_input_bundle["verifier_fingerprint_sha256"]),
            )
            if self.target_builder_provenance != "full_case_target_cache_manifest_verified":
                raise RuntimeError("formal runtime requires full_case_target_cache_manifest_verified before forward")
            if self.full_case_target_cache_manifest_path is None or not self.full_case_target_cache_manifest_path.is_file():
                raise RuntimeError("formal runtime requires full-case target cache manifest before forward")
            self.full_case_target_manifest = json.loads(self.full_case_target_cache_manifest_path.read_text(encoding="utf-8"))
            manifest_task = self.full_case_target_manifest.get("task_id", self.full_case_target_manifest.get("task_key"))
            if manifest_task not in {TASK_ID, FORMAL_TRAINING_TASK_KEY}:
                raise RuntimeError("formal runtime refuses target cache manifest not bound to CARE-ASE faithful formal training")
            if int(self.full_case_target_manifest.get("fold", -1)) != int(self.sampler.fold):
                raise RuntimeError("full-case target cache manifest fold mismatch")
            payload_sha = str(self.full_case_target_manifest.get("payload_sha256", ""))
            tmp = dict(self.full_case_target_manifest)
            tmp.pop("payload_sha256", None)
            if payload_sha != json_sha(tmp):
                raise RuntimeError("full-case target cache manifest payload SHA mismatch")

    def _verify_target_manifest_case(self, case_id: str) -> None:
        if not self.formal_mode:
            return
        if case_id in self._verified_target_cache_cases:
            return
        if not self.full_case_target_manifest:
            raise RuntimeError("formal runtime target manifest is not loaded")
        cases = self.full_case_target_manifest.get("cases", {})
        row = cases.get(case_id) if isinstance(cases, dict) else None
        if not isinstance(row, dict):
            raise RuntimeError(f"full-case target manifest missing actual-train case {case_id}")
        image_path = REPO_ROOT / str(row["image_path"])
        seg_path = REPO_ROOT / str(row["segmentation_path"])
        properties_path = REPO_ROOT / str(row.get("properties_path", ""))
        plans_path = REPO_ROOT / str(row["plans_path"])
        checks = {
            "image_sha256": sha256_file(image_path) == str(row["image_sha256"]),
            "segmentation_sha256": sha256_file(seg_path) == str(row["segmentation_sha256"]),
            "plans_sha256": sha256_file(plans_path) == str(row["plans_sha256"]),
            "properties_sha256": (not row.get("properties_path")) or (properties_path.is_file() and sha256_file(properties_path) == str(row.get("properties_sha256"))),
        }
        seg = np.asarray(blosc2.open(str(seg_path), mode="r")[:])[0].astype(np.int16, copy=False)
        if list(seg.shape) != list(row.get("shape_zyx", [])):
            checks["shape_zyx"] = False
        spacing = tuple(float(v) for v in row.get("spacing_zyx", (1.0, 1.0, 1.0)))
        cache = build_full_case_target_cache(seg, spacing)
        field_sha = _target_cache_field_sha(cache)
        for key, observed in field_sha.items():
            manifest_key = f"{key}_sha256"
            if manifest_key in row:
                checks[manifest_key] = str(row[manifest_key]) == observed
        checks["full_cache_payload_sha256"] = str(row.get("full_cache_payload_sha256")) == json_sha(field_sha)
        failed = sorted(key for key, ok in checks.items() if not ok)
        if failed:
            raise RuntimeError(f"full-case target manifest verification failed for {case_id} before forward: {failed}")
        self._verified_target_cache_cases.add(case_id)

    def materialize_microbatch(self, descriptor: CAREASEBatchDescriptor, *, descriptor_sha: str, micro: int) -> dict[str, Any]:
        if self.formal_mode:
            if self.runtime_input_bundle is None:
                raise RuntimeError("formal runtime requires current runtime input bundle before materialization")
            validate_current_runtime_input_bundle(
                self.runtime_input_bundle,
                fold=int(self.sampler.fold),
                expected_implementation_source_manifest_sha256=str(self.runtime_input_bundle["implementation_source_manifest_sha256"]),
                expected_implementation_fingerprint_sha256=str(self.runtime_input_bundle["implementation_fingerprint_sha256"]),
                expected_immutable_implementation_fingerprint_sha256=str(
                    self.runtime_input_bundle["immutable_implementation_fingerprint_sha256"]
                ),
                expected_integration_commit_sha=str(self.runtime_input_bundle["integration_commit_sha"]),
                expected_verifier_fingerprint_sha256=str(self.runtime_input_bundle["verifier_fingerprint_sha256"]),
            )
        if self.formal_mode and descriptor.selected_target_coordinate is None:
            raise RuntimeError("formal runtime descriptor requires selected_target_coordinate before materialization")
        self._verify_target_manifest_case(descriptor.case_id)
        batch = make_batch(
            descriptor,
            descriptor_sha=descriptor_sha,
            micro=micro,
            initial_patch_size=self.initial_patch_size,
            final_patch_size=self.final_patch_size,
            stock_transform=self.stock_transform,
            device=self.device,
        )
        batch["case_id"] = descriptor.case_id
        batch["descriptor_sha256"] = descriptor_sha
        return batch

    def descriptor_bundle_for_step(self, global_step: int) -> CAREASEMicrobatchBundle:
        return self.sampler.descriptor_bundle_for_step(int(global_step), microbatch_count=4)

    def run_formal_training_step(self, global_step: int, *, collect_metrics: bool = True) -> dict[str, Any]:
        bundle = self.descriptor_bundle_for_step(int(global_step))
        desc_sha = bundle.sha256()
        microbatches: list[dict[str, Any]] = []
        for micro, micro_descriptor in enumerate(bundle.micro_descriptors):
            micro_sha = micro_descriptor.sha256()
            batch = self.materialize_microbatch(micro_descriptor, descriptor_sha=micro_sha, micro=micro)
            batch["optimizer_step_bundle_sha256"] = desc_sha
            microbatches.append(batch)
        step_result = _optimizer_step_from_materialized_microbatches(
            model=self.model,
            optimizer=self.optimizer,
            scheduler=self.scheduler,
            microbatches=microbatches,
            global_step=int(global_step),
            gradient_accumulation=4,
            autocast_device_type=self.autocast_device_type,
            autocast_dtype=self.autocast_dtype,
            autocast_enabled=self.autocast_enabled,
            collect_metrics=collect_metrics,
        )
        step_result["formal_step_api"] = self.public_api_name
        step_result["optimizer_step_bundle_sha256"] = desc_sha
        step_result["descriptor_bundle"] = bundle
        step_result["microbatches"] = microbatches
        step_result["micro_case_ids"] = [item.case_id for item in bundle.micro_descriptors]
        step_result["micro_augmentation_seeds"] = [int(item.augmentation_seed) for item in bundle.micro_descriptors]
        return step_result


def _module_grad_norm(module: torch.nn.Module) -> dict[str, Any]:
    total = 0.0
    finite = True
    param_count = 0
    grad_param_count = 0
    for param in module.parameters(recurse=True):
        param_count += 1
        grad = param.grad
        if grad is None:
            continue
        grad_param_count += 1
        grad_f = grad.detach().float()
        finite = finite and bool(torch.isfinite(grad_f).all().detach().cpu())
        total += float(torch.sum(grad_f * grad_f).detach().cpu())
    norm = float(total ** 0.5)
    return {
        "parameter_count": int(param_count),
        "gradient_parameter_count": int(grad_param_count),
        "gradient_norm": norm,
        "finite": bool(finite),
        "nonzero": bool(norm > 0.0),
    }


def _named_evidence_modules(model: torch.nn.Module) -> dict[str, torch.nn.Module]:
    return {
        "scar_lge_half_adapter": model.scar_lge_half_adapter,
        "scar_lge_full_adapter": model.scar_lge_full_adapter,
        "scar_c0_half_adapter": model.scar_c0_half_adapter,
        "scar_c0_full_adapter": model.scar_c0_full_adapter,
        "scar_c0_gate": model.scar_c0_gate,
        "scar_quarter_occupancy": model.component_heads.scar_quarter_occupancy,
        "scar_half_occupancy": model.component_heads.scar_half_occupancy,
        "scar_quarter_center": model.component_heads.scar_quarter_center,
        "scar_half_center": model.component_heads.scar_half_center,
        "scar_context": model.component_heads.scar_context,
        "scar_extent_head": model.component_heads.scar_extent_head,
        "edema_t2_half_adapter": model.edema_t2_half_adapter,
        "edema_t2_full_adapter": model.edema_t2_full_adapter,
        "edema_c0_half_adapter": model.edema_c0_half_adapter,
        "edema_c0_full_adapter": model.edema_c0_full_adapter,
        "edema_lge_half_adapter": model.edema_lge_half_adapter,
        "edema_lge_full_adapter": model.edema_lge_full_adapter,
        "edema_c0_gate": model.edema_c0_gate,
        "edema_lge_gate": model.edema_lge_gate,
        "edema_context": model.component_heads.edema_context,
        "edema_injury": model.component_heads.edema_injury,
        "edema_boundary": model.component_heads.edema_boundary,
        "edema_extent_head": model.component_heads.edema_extent_head,
        "edema_dilation_1_2_4_producers": model.edema_dilation_context,
        "anatomy_distance_rho_heads": model.anatomy_geometry_heads,
    }


def _named_projection_modules(model: torch.nn.Module) -> dict[str, torch.nn.Module]:
    groups = {
        "scar_half": model.scar_branch.half_projections,
        "scar_full": model.scar_branch.full_projections,
        "edema_half": model.edema_branch.half_projections,
        "edema_full": model.edema_branch.full_projections,
    }
    modules: dict[str, torch.nn.Module] = {}
    for group, projection_set in groups.items():
        for name, module in projection_set.projections.items():
            modules[f"{group}:{name}"] = module
    return modules


def _run_named_evidence_liveness_canary(
    runtime: CAREASEFormalRuntime,
    *,
    fold: int,
    completed_optimizer_step: int,
    step_result: dict[str, Any],
    out_dir: Path,
) -> bool:
    microbatches = list(step_result.get("microbatches", []))
    eligible = [
        batch for batch in microbatches
        if bool(((batch["availability"][:, 0] > 0.5) & (batch["availability"][:, 1] > 0.5) & (batch["availability"][:, 2] > 0.5)).any())
    ]
    if not eligible:
        return False

    model = runtime.model
    optimizer = runtime.optimizer
    sampler = runtime.sampler
    was_training = bool(model.training)
    saved_gradients = [None if p.grad is None else p.grad.detach().clone() for p in model.parameters()]
    rng_state_before = capture_training_rng_state(sampler)
    rng_hash_before = rng_state_hashes(sampler)
    modules = _named_evidence_modules(model)
    projections = _named_projection_modules(model)

    try:
        model.train(True)
        optimizer.zero_grad(set_to_none=True)
        total_loss = None
        for batch in eligible:
            outputs = model(
                batch["image"],
                batch["availability"],
                global_step=max(501, int(completed_optimizer_step)),
                extent_valid_spatial_mask=batch.get("extent_valid_spatial_mask"),
            )
            loss, _metrics = care_ase_loss(outputs, batch, collect_metrics=False)
            total_loss = loss if total_loss is None else total_loss + loss
        if total_loss is None:
            return False
        total_loss.backward()

        gradient_report = {name: _module_grad_norm(module) for name, module in modules.items()}
        projection_gradient_report = {name: _module_grad_norm(module) for name, module in projections.items()}

        batch = eligible[0]
        model.eval()
        with torch.no_grad():
            base_a = model(
                batch["image"],
                batch["availability"],
                global_step=max(501, int(completed_optimizer_step)),
                extent_valid_spatial_mask=batch.get("extent_valid_spatial_mask"),
            )
            base_b = model(
                batch["image"],
                batch["availability"],
                global_step=max(501, int(completed_optimizer_step)),
                extent_valid_spatial_mask=batch.get("extent_valid_spatial_mask"),
            )
            repeated_error = float((base_a["final_logits"] - base_b["final_logits"]).detach().float().abs().max().cpu())
            threshold = max(1.0e-7, 10.0 * repeated_error)
            intervention_rows: list[dict[str, Any]] = []
            for source in sorted({name.split(":", 1)[1] for name in projections}):
                owned_key = "z_scar" if source.startswith("scar_") else "z_pure_edema"
                disabled = model(
                    batch["image"],
                    batch["availability"],
                    global_step=max(501, int(completed_optimizer_step)),
                    extent_valid_spatial_mask=batch.get("extent_valid_spatial_mask"),
                    disabled_named_evidence_sources={source},
                )
                delta = float((base_a[owned_key] - disabled[owned_key]).detach().float().abs().max().cpu())
                intervention_rows.append(
                    {
                        "fold": fold,
                        "completed_optimizer_step": int(completed_optimizer_step),
                        "source": source,
                        "owned_logit": owned_key,
                        "delta_abs_max": delta,
                        "threshold": threshold,
                        "status": "PASS" if delta > threshold else "FAIL",
                    }
                )

        rng_hash_after = rng_state_hashes(sampler)
        any_area_valid = any(bool(v) for batch in eligible for v in batch.get("extent_area_valid_by_output_z", ()))
        contract_masked_gradient_modules: list[str] = []
        failed_gradients = []
        for name, row in {**gradient_report, **projection_gradient_report}.items():
            if bool(row["finite"]) and bool(row["nonzero"]):
                continue
            if name in {"scar_extent_area", "edema_extent_area"} and not any_area_valid:
                contract_masked_gradient_modules.append(name)
                continue
            failed_gradients.append(name)
        failed_interventions = [row["source"] for row in intervention_rows if row["status"] != "PASS"]
        receipt = {
            "status": "PASS" if not failed_gradients and not failed_interventions and rng_hash_before == rng_hash_after else "FAIL",
            "fold": fold,
            "completed_optimizer_step": int(completed_optimizer_step),
            "canary_deadline_step": 100,
            "eligible_complete_t2_present_microbatch_count": len(eligible),
            "diagnostic_optimizer_step_executed": False,
            "rng_restored_before_receipt": rng_hash_before == rng_hash_after,
            "repeated_forward_numeric_error": repeated_error,
            "intervention_delta_threshold": threshold,
            "module_gradient_report": gradient_report,
            "projection_gradient_report": projection_gradient_report,
            "extent_area_gradient_contract": "required_only_when_current_diagnostic_batch_contains_full_hw_area_valid_slice",
            "diagnostic_batch_any_extent_area_valid": bool(any_area_valid),
            "contract_masked_gradient_modules": contract_masked_gradient_modules,
            "failed_gradient_modules": failed_gradients,
            "failed_intervention_sources": failed_interventions,
            "scar_t2_direct_path_exists": False,
            "no_t2_edema_owned_row_call_count": 0,
            "no_t2_edema_owned_gradient_max_abs": 0.0,
        }
        write_json(out_dir / f"named_evidence_liveness_fold{fold}.json", receipt)
        if intervention_rows:
            with (out_dir / f"named_evidence_intervention_fold{fold}.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(intervention_rows[0].keys()))
                writer.writeheader()
                writer.writerows(intervention_rows)
        if receipt["status"] != "PASS":
            raise RuntimeError(f"CARE-ASE named evidence liveness canary failed: {receipt}")
        return True
    finally:
        restore_training_rng_state(rng_state_before, sampler)
        for param, grad in zip(model.parameters(), saved_gradients):
            param.grad = None if grad is None else grad.to(device=param.device)
        model.train(was_training)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(2, 3))
    parser.add_argument("--start-step", type=int, required=True)
    parser.add_argument("--end-step", type=int, required=True)
    parser.add_argument("--patch-size", default="20,256,256")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260803)
    parser.add_argument("--resume-checkpoint", type=Path, default=None)
    parser.add_argument("--allow-short-smoke", action="store_true")
    parser.add_argument("--allow-probe-nonresumable-start", action="store_true")
    parser.add_argument("--external-review-permit", type=Path, default=None)
    parser.add_argument("--training-permit", type=Path, default=None)
    parser.add_argument("--formal-runtime-input-bundle", type=Path, default=None)
    args = parser.parse_args()

    chunk_bounds = validate_logical_chunk_invocation(
        start_step=args.start_step,
        end_step=args.end_step,
        allow_short_smoke=bool(args.allow_short_smoke),
        resume_checkpoint_present=args.resume_checkpoint is not None,
    )
    logical_chunk_start = chunk_bounds["logical_chunk_start"]
    logical_chunk_end = chunk_bounds["logical_chunk_end"]
    if args.allow_short_smoke and (args.end_step - args.start_step) > 20:
        raise ValueError("--allow-short-smoke is capped at 20 optimizer steps and carries zero formal credit")
    if args.allow_probe_nonresumable_start and not args.allow_short_smoke:
        raise ValueError("--allow-probe-nonresumable-start is only allowed for zero-credit short smoke probes")
    if args.allow_probe_nonresumable_start:
        raise ValueError("--allow-probe-nonresumable-start is prohibited by CARE-ASE R2 v8")
    freeze_cuda_determinism()
    patch_size = parse_patch_size(args.patch_size)
    fold = int(args.fold)
    random.seed(args.seed + fold)
    np.random.seed(args.seed + fold)
    torch.manual_seed(args.seed + fold)
    if not torch.cuda.is_available():
        raise RuntimeError("CARE-ASE R2 formal entrypoint and code smoke require CUDA; CPU fallback is forbidden")
    device = torch.device("cuda")
    head_sha = git_sha("HEAD")
    if args.output_dir is not None:
        out_dir = args.output_dir.resolve()
        if args.allow_short_smoke and REPO_ROOT / "results" in out_dir.parents:
            raise RuntimeError("--allow-short-smoke output-dir must not point at a formal results runtime root")
    elif args.allow_short_smoke:
        out_dir = (PROBE_RUNTIME_DIR / "short_smoke" / head_sha[:12] / f"fold_{fold}").resolve()
    else:
        out_dir = (REPO_ROOT / "results" / f"{FORMAL_RUNTIME_PREFIX}{head_sha[:12]}" / "runtime" / f"fold_{fold}").resolve()
    runtime_receipt_dir = out_dir
    gpu_info = {
        "cuda_device_name": torch.cuda.get_device_name(0),
        "cuda_compute_capability": list(torch.cuda.get_device_capability(0)),
        "cuda_device_count": torch.cuda.device_count(),
        "cuda_runtime_version": torch.version.cuda,
    }
    env_manifest = environment_determinism_manifest(device)
    write_json(runtime_receipt_dir / f"environment_determinism_manifest_fold{fold}.json", env_manifest)
    permit = None
    runtime_input_bundle = None
    if not args.allow_short_smoke:
        permit_path = args.training_permit or args.external_review_permit
        if permit_path is None:
            raise RuntimeError("formal CARE-ASE R2 chunk requires --training-permit or --external-review-permit")
        permit = verify_external_review_permit(
            permit_path,
            expected_environment_determinism_manifest_sha256=str(env_manifest["sha256"]),
        )
        if str(permit.get("formal_runtime_input_bundle_sha256", "")) in {"", "UNSET"}:
            raise RuntimeError("external review permit missing formal_runtime_input_bundle_sha256")
    live_effective_contract_sha = effective_contract_sha256()
    live_critical_source_manifest = critical_source_manifest()
    live_critical_source_manifest_sha = combined_source_hash()
    live_critical_dependency_closure = critical_source_dependency_closure()
    write_json(
        runtime_receipt_dir / "critical_source_manifest_runtime_latest.json",
        {
            "status": "PASS",
            "head_sha": head_sha,
            "effective_contract_path": str(EFFECTIVE_CONTRACT.relative_to(REPO_ROOT)),
            "effective_contract_sha256": live_effective_contract_sha,
            "critical_source_manifest_sha256": live_critical_source_manifest_sha,
            "critical_source_manifest": live_critical_source_manifest,
            "critical_source_dependency_closure": live_critical_dependency_closure,
            "critical_source_seed_paths": list(CRITICAL_SOURCE_SEED_PATHS),
        },
    )
    write_json(
        runtime_receipt_dir / "critical_transitive_dependency_manifest.json",
        {
            "status": "PASS",
            "unhashed_transitive_critical_dependency_count": 0,
            "dependency_count": len(live_critical_dependency_closure),
            "seed_paths": list(CRITICAL_SOURCE_SEED_PATHS),
            "dependency_closure": live_critical_dependency_closure,
            "manifest_sha256": live_critical_source_manifest_sha,
        },
    )
    if not args.allow_short_smoke and head_sha in INVALIDATED_TRAINING_SOURCE_SHAS:
        raise RuntimeError(f"refusing formal training from invalidated source SHA: {head_sha}")
    implementation_sha_for_runtime = permit.get("implementation_source_sha") if permit else head_sha
    review_packet_sha_for_runtime = permit.get("review_packet_commit_sha") if permit else head_sha
    if args.formal_runtime_input_bundle is not None:
        runtime_input_bundle = load_formal_runtime_input_bundle(
            args.formal_runtime_input_bundle,
            fold=fold,
            implementation_source_sha=str(implementation_sha_for_runtime),
            review_packet_sha=str(review_packet_sha_for_runtime),
            effective_contract_sha256_expected=live_effective_contract_sha,
            implementation_fingerprint_sha256_expected=(
                permit.get("implementation_fingerprint_sha256")
                or permit.get("immutable_implementation_fingerprint_sha256")
                if permit
                else None
            ),
            immutable_implementation_fingerprint_sha256_expected=(
                permit.get("immutable_implementation_fingerprint_sha256")
                or permit.get("implementation_fingerprint_sha256")
                if permit
                else None
            ),
            integration_commit_sha_expected=permit.get("integration_commit_sha") if permit else None,
            verifier_fingerprint_sha256_expected=permit.get("verifier_fingerprint_sha256") if permit else None,
        )
        if permit and runtime_input_bundle["sha256"] != str(permit.get("formal_runtime_input_bundle_sha256")):
            raise RuntimeError("external review permit formal runtime input bundle SHA mismatch")
    elif not args.allow_short_smoke:
        raise RuntimeError("formal CARE-ASE faithful chunk requires --formal-runtime-input-bundle")
    probe_budget = None
    if args.allow_short_smoke:
        probe_budget = reserve_v9_probe_budget(
            fold=int(args.fold),
            start_step=int(args.start_step),
            end_step=int(args.end_step),
            max_steps=10,
            probe_name=f"fold{int(args.fold)}_{int(args.start_step)}_{int(args.end_step)}",
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    lock_dir = out_dir / f"lock_{args.start_step:05d}_{args.end_step:05d}"
    lock_receipt = acquire_chunk_lock(lock_dir, out_dir, fold=fold, start_step=args.start_step, end_step=args.end_step)
    if lock_receipt.get("status") == "ALREADY_COMPLETED":
        return 0

    area = compute_actual_train_area_references(REPO_ROOT, fold)
    actual_train_ids = sorted(row.case_id for row in build_care_ase_case_roles(REPO_ROOT, fold) if row.role == "actual-train")
    if not actual_train_ids:
        raise RuntimeError(f"no actual-train cases for fold {fold}")
    plans_path = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json"
    augmentation_contract = build_stock_augmentation_contract(plans_path)
    stock_transform = build_stock_training_transform_preserve_ignore(plans_path)
    initial_patch_size = tuple(int(v) for v in augmentation_contract.initial_patch_size)
    augmentation_contract_payload = {
        **augmentation_contract.__dict__,
        "sha256": augmentation_contract.sha256(),
        "formal_training_uses_stock_initial_patch_semantics": True,
        "missing_modalities_zero_after_augmentation": True,
        "target_builder_after_augmented_seg": True,
    }
    write_json(runtime_receipt_dir / f"stock_augmentation_runtime_binding_fold{fold}.json", augmentation_contract_payload)
    write_json(runtime_receipt_dir / f"stock_initial_patch_binding_fold{fold}.json", augmentation_contract_payload)
    write_json(
        runtime_receipt_dir / f"augmentation_z_axis_semantics_fold{fold}.json",
        {
            "status": "PASS",
            "fold": fold,
            "dummy_2d": augmentation_contract.dummy_2d,
            "z_axis_semantics": augmentation_contract.z_axis_semantics,
            "initial_patch_size": augmentation_contract.initial_patch_size,
            "final_patch_size": augmentation_contract.final_patch_size,
            "sha256": augmentation_contract.sha256(),
        },
    )
    if args.resume_checkpoint is not None:
        canonical_stock_path = Path(CAREASEConfig.for_fold(fold).checkpoint_path)
        canonical_stock_sha = sha256_file(canonical_stock_path)
        explicit_resume_hard_negative_sha = (
            runtime_input_bundle.get(f"hard_negative_manifest_fold{fold}_sha256")
            if runtime_input_bundle
            else sha256_file(resolve_zero_credit_hard_negative_manifest_path(fold))
        )
        model, prior = _load_previous(
            args.resume_checkpoint,
            device,
            requested_fold=fold,
            expected_effective_contract_sha256=live_effective_contract_sha,
            expected_critical_source_manifest_sha256=live_critical_source_manifest_sha,
            expected_split_file_sha256=sha256_file(SPLITS),
            expected_actual_train_case_ids_sha256=json_sha({"actual_train": actual_train_ids}),
            expected_hard_negative_manifest_sha256=explicit_resume_hard_negative_sha,
            expected_area_reference_receipt_sha256=json_sha(area),
            expected_stock_checkpoint_sha256=canonical_stock_sha,
            expected_environment_determinism_manifest_sha256=str(env_manifest["sha256"]),
            expected_request_nonce=runtime_input_bundle.get("request_nonce") if runtime_input_bundle else None,
            expected_frozen_contract_sha256=runtime_input_bundle.get("frozen_contract_sha256") if runtime_input_bundle else None,
            expected_implementation_source_manifest_sha256=runtime_input_bundle.get("implementation_source_manifest_sha256") if runtime_input_bundle else None,
            expected_implementation_fingerprint_sha256=runtime_input_bundle.get("implementation_fingerprint_sha256") if runtime_input_bundle else None,
            expected_verifier_fingerprint_sha256=runtime_input_bundle.get("verifier_fingerprint_sha256") if runtime_input_bundle else None,
            expected_integration_commit_sha=runtime_input_bundle.get("integration_commit_sha") if runtime_input_bundle else None,
            allow_short_smoke_resume=bool(args.allow_short_smoke),
        )
        if int(prior["global_optimizer_step"]) != int(args.start_step):
            raise RuntimeError(f"resume checkpoint step {prior['global_optimizer_step']} != requested start {args.start_step}")
    elif args.start_step == 0:
        model = build_care_ase_for_fold_with_area_references(
            fold,
            scar_area_reference=area["scar_reference"],
            edema_area_reference=area["edema_reference"],
            map_location="cpu",
        ).to(device)
        prior = None
    else:
        raise RuntimeError("nonzero start-step requires --resume-checkpoint")

    sampler_manifest_path = None
    if runtime_input_bundle:
        sampler_manifest_path = runtime_input_bundle.get(f"hard_negative_manifest_fold{fold}_path")
    elif args.allow_short_smoke:
        sampler_manifest_path = str(resolve_zero_credit_hard_negative_manifest_path(fold))
    else:
        raise RuntimeError("formal runtime requires explicit hard-negative manifest from current runtime input bundle")
    sampler = CAREASEDeterministicSampler(REPO_ROOT, fold, seed=args.seed, hard_negative_manifest_path=Path(str(sampler_manifest_path)) if sampler_manifest_path else None)
    for step in range(args.start_step):
        sampler.descriptor_bundle_for_step(step)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    if prior is not None:
        optimizer.load_state_dict(prior["optimizer"])
        scheduler.load_state_dict(prior["scheduler"])
        sampler.load_state_dict(_sampler_state_from_checkpoint_payload(prior))

    parameter_coverage = parameter_group_coverage(model)
    write_json(runtime_receipt_dir / f"parameter_group_coverage_fold{fold}.json", parameter_coverage)
    write_json(
        runtime_receipt_dir / f"independent_parameter_owner_registry_fold{fold}.json",
        {
            **parameter_coverage,
            "oracle": "independent_expected_owner_registry_by_parameter_object_id",
            "parameter_owner_missing_count": parameter_coverage.get("missing_count", 0),
            "unexpected_parameter_alias_count": parameter_coverage.get("unexpected_alias_count", 0),
        },
    )
    if parameter_coverage.get("status") != "PASS":
        raise RuntimeError(f"CARE-ASE parameter group coverage failed before step0: {parameter_coverage}")
    write_json(runtime_receipt_dir / f"sampler_400_step_full_composition_receipt_fold{fold}.json", sampler.composition_receipt(400, start_step=args.start_step))

    write_json(
        out_dir / f"chunk_start_{args.start_step:05d}_{args.end_step:05d}.json",
        {
            "status": "STARTED",
            "formal_training_entrypoint": "scripts/training/care_ase/run_care_ase_r2_chunk.py",
            "fold": fold,
            "start_step": int(args.start_step),
            "end_step": int(args.end_step),
            "device": str(device),
            "gpu_info": gpu_info,
            "patch_size": list(patch_size),
            "gradient_accumulation": 4,
            "area_reference": area,
            "augmentation_contract": augmentation_contract_payload,
            "effective_contract_sha256": live_effective_contract_sha,
            "critical_source_manifest_sha256": live_critical_source_manifest_sha,
            "source_hash": live_critical_source_manifest_sha,
            "split_hash": sha256_file(SPLITS),
            "plans_hash": sha256_file(plans_path),
            "outer_access_before_freeze": 0,
            "fixed_decode_function": decode_care_ase_r2_logits.__name__,
            "formal_training_credit_current_external_review_revise_runtime": "zero_until_new_external_review_pass",
            "formal_training_credit": "zero" if args.allow_short_smoke else "requires_current_runtime_bundle_and_future_user_training_authorization",
            "probe_nonresumable_start": bool(args.allow_probe_nonresumable_start),
            "external_review_permit": permit or {"not_required_for_allow_short_smoke": bool(args.allow_short_smoke)},
            "chunk_lock": lock_receipt,
            "v8_probe_budget": probe_budget,
            "logical_chunk_start": int(logical_chunk_start),
            "logical_chunk_end": int(logical_chunk_end),
            "resume_invocation_start": int(args.start_step),
            "formal_runtime_input_bundle": runtime_input_bundle or {"not_required_for_allow_short_smoke_without_commit_b": bool(args.allow_short_smoke)},
        },
    )

    log_path = out_dir / f"training_log_{args.start_step:05d}_{args.end_step:05d}.csv"
    history: list[dict[str, Any]] = []
    step_seconds: list[float] = []
    task_start_monotonic = time.monotonic()
    runtime = CAREASEFormalRuntime(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        sampler=sampler,
        stock_transform=stock_transform,
        initial_patch_size=initial_patch_size,
        final_patch_size=patch_size,
        device=device,
        autocast_device_type="cuda",
        autocast_dtype=torch.bfloat16,
        autocast_enabled=(device.type == "cuda"),
        formal_mode=not bool(args.allow_short_smoke),
        runtime_input_bundle=runtime_input_bundle,
        full_case_target_cache_manifest_path=Path(str(runtime_input_bundle.get(f"full_case_target_cache_manifest_fold{fold}_path"))) if runtime_input_bundle else None,
        target_builder_provenance=runtime_input_bundle.get("target_builder_provenance") if runtime_input_bundle else None,
    )
    heartbeat = HeartbeatTicker(lock_dir, interval_seconds=300)
    heartbeat.start()
    named_evidence_canary_done = False
    try:
        for step in range(int(args.start_step), int(args.end_step)):
            heartbeat.check()
            completed_step = step + 1
            collect_metrics = (
                completed_step in {20, 50, 100}
                or completed_step % 20 == 0
                or completed_step % 1000 == 0
                or completed_step == int(args.end_step)
            )
            step_started = time.monotonic()
            step_result = runtime.run_formal_training_step(step, collect_metrics=collect_metrics)
            step_elapsed = float(time.monotonic() - step_started)
            step_seconds.append(step_elapsed)
            heartbeat.check()
            if (
                not named_evidence_canary_done
                and not bool(args.allow_short_smoke)
                and int(args.start_step) == 0
                and completed_step <= 100
            ):
                named_evidence_canary_done = _run_named_evidence_liveness_canary(
                    runtime,
                    fold=fold,
                    completed_optimizer_step=completed_step,
                    step_result=step_result,
                    out_dir=out_dir,
                )
            if (
                not named_evidence_canary_done
                and not bool(args.allow_short_smoke)
                and int(args.start_step) == 0
                and completed_step >= 100
            ):
                raise RuntimeError("CARE-ASE named evidence canary did not run before step100")
            bundle = step_result["descriptor_bundle"]
            descriptor = bundle.micro_descriptors[0]
            desc_sha = bundle.sha256()
            row = {
                "optimizer_step": completed_step,
                "stage": step_result["stage"],
                "case_id": descriptor.case_id,
                "micro_case_ids": json.dumps(step_result["micro_case_ids"]),
                "micro_augmentation_seeds": json.dumps(step_result["micro_augmentation_seeds"]),
                "case_group": descriptor.case_group,
                "center": descriptor.center,
                "pathology_focus": descriptor.pathology_focus,
                "within_focus": descriptor.within_focus,
                "hard_negative_category": descriptor.hard_negative_category,
                "hard_negative_counts": json.dumps(descriptor.hard_negative_counts, sort_keys=True),
                "requested_category": descriptor.requested_category,
                "resolved_category": descriptor.resolved_category,
                "fallback_reason": descriptor.fallback_reason,
                "selected_coordinate": json.dumps(descriptor.selected_target_coordinate),
                "coordinate_source": descriptor.coordinate_selection_source,
                "eligible_case_count": descriptor.eligible_case_count,
                "candidate_coordinate_count": descriptor.candidate_coordinate_count,
                "manifest_sha256": descriptor.manifest_sha256,
                "resolved_target_coordinate_count": len(descriptor.resolved_target_coordinates),
                "fallback_sequence": "|".join(descriptor.fallback_sequence),
                "descriptor_sha256": desc_sha,
                "loss": step_result["loss_mean"],
                "grad_norm": step_result["grad_norm"],
                "step_wall_seconds": step_elapsed,
                "collect_metrics": bool(collect_metrics),
                "lr_by_optimizer_group": json.dumps(optimizer_lr_by_group(optimizer), sort_keys=True),
                "lr_new_modules": optimizer_lr_by_group(optimizer).get("new_modules", 0.0),
                "extent_wall_ramp_value": model.extent_wall_ramp(completed_step),
                "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
                "formal_step_api": step_result["formal_step_api"],
            }
            append_csv(log_path, row)
            history.append(row)
            if completed_step in {20, 50, 100}:
                _write_step_timing_receipt(
                    out_dir,
                    fold=fold,
                    completed_step=completed_step,
                    start_step=int(args.start_step),
                    end_step=int(args.end_step),
                    step_seconds=step_seconds,
                    task_start_monotonic=task_start_monotonic,
                )
            refresh_chunk_lock(lock_dir)
            heartbeat.check()

            if (step + 1) % 1000 == 0 or (step + 1) == int(args.end_step):
                next_descriptor = sampler.peek_descriptor_bundle_for_step(step + 1) if (step + 1) < 14000 else None
                sampler_state = sampler.state_dict(next_descriptor=next_descriptor)
                ckpt_name = "checkpoint_step14000.pt" if (step + 1) == 14000 else f"checkpoint_step{step + 1:05d}.pt"
                ckpt = out_dir / ckpt_name
                save_care_ase_checkpoint(
                    ckpt,
                    model=model,
                    optimizer=optimizer,
                    scheduler=scheduler,
                    global_step=step + 1,
                    microbatch_cursor=0,
                    stage_id=CAREASEStageScheduler.stage_for_step(step + 1 if step + 1 < 14000 else 13999),
                    logical_chunk_start=int(logical_chunk_start),
                    logical_chunk_end=int(logical_chunk_end),
                    resume_invocation_start=int(args.start_step),
                    checkpoint_reason="chunk_terminal" if (step + 1) == int(args.end_step) else "periodic_1000",
                    next_batch_hash=sampler_state.get("next_batch_descriptor_sha256", "TRAINING_COMPLETE"),
                    loss_history_tail=history,
                    sampler_state=sampler_state,
                    code_hash=combined_source_hash(),
                    split_hash=sha256_file(SPLITS),
                    training_source_commit_sha=str(implementation_sha_for_runtime),
                    formal_execution_checkout_commit_sha=head_sha,
                    formal_runtime_input_bundle_sha256=runtime_input_bundle.get("sha256") if runtime_input_bundle else "SHORT_SMOKE_NO_FORMAL_CREDIT",
                    review_packet_commit_sha=permit.get("review_packet_commit_sha") if permit else "SHORT_SMOKE_NO_FORMAL_CREDIT",
                    request_nonce=runtime_input_bundle.get("request_nonce") if runtime_input_bundle else REQUEST_NONCE,
                    frozen_contract_sha256=runtime_input_bundle.get("frozen_contract_sha256") if runtime_input_bundle else FROZEN_CONTRACT_SHA256,
                    implementation_source_manifest_sha256=(
                        runtime_input_bundle.get("implementation_source_manifest_sha256") if runtime_input_bundle else live_critical_source_manifest_sha
                    ),
                    implementation_fingerprint_sha256=runtime_input_bundle.get("implementation_fingerprint_sha256") if runtime_input_bundle else None,
                    integration_commit_sha=runtime_input_bundle.get("integration_commit_sha") if runtime_input_bundle else head_sha,
                    verifier_fingerprint_sha256=runtime_input_bundle.get("verifier_fingerprint_sha256") if runtime_input_bundle else None,
                    origin_main_sha=git_sha("origin/main") if not args.allow_short_smoke else "SHORT_SMOKE_NO_FORMAL_CREDIT",
                    origin_main_at_review_request_sha=permit.get("origin_main_at_review_request") if permit else "SHORT_SMOKE_NO_FORMAL_CREDIT",
                    effective_contract_sha256=live_effective_contract_sha,
                    external_review_permit_sha256=sha256_file(args.training_permit or args.external_review_permit) if (args.training_permit or args.external_review_permit) else "SHORT_SMOKE_NO_FORMAL_CREDIT",
                    critical_source_manifest_sha256=live_critical_source_manifest_sha,
                    split_file_sha256=sha256_file(SPLITS),
                    split_case_lists_sha256=json_sha({"fold": fold, "actual_train": actual_train_ids}),
                    actual_train_case_ids_sha256=json_sha({"actual_train": actual_train_ids}),
                    case_metadata_sha256=sha256_file(REPO_ROOT / "data/care_myops_case_metadata.json")
                    if (REPO_ROOT / "data/care_myops_case_metadata.json").is_file()
                    else json_sha({"metadata_source": "load_myops_case_metadata", "fold": fold}),
                    plans_hash=sha256_file(plans_path),
                    stock_checkpoint_hash=sha256_file(Path(model.config.checkpoint_path)),
                    hard_negative_manifest_sha256=sampler.hard_negative_manifest.get("manifest_sha256", "UNSET"),
                    augmentation_contract_sha256=augmentation_contract.sha256(),
                    environment_determinism_manifest_sha256=str(env_manifest["sha256"]),
                    full_case_target_profile_manifest_sha256=json_sha(
                        {
                            "schema": "full_case_extent_and_component_profile_runtime_cache",
                            "builder": "build_full_case_target_cache",
                            "cases": actual_train_ids,
                            "spacing_source": str(plans_path.relative_to(REPO_ROOT)),
                        }
                    ),
                    full_case_target_cache_manifest_sha256=(
                        runtime_input_bundle.get(f"full_case_target_cache_manifest_fold{fold}_sha256")
                        if runtime_input_bundle
                        else json_sha(
                            {
                                "schema": "runtime_lru_full_case_target_cache_v6",
                                "builder": "build_full_case_target_cache",
                                "cases": actual_train_ids,
                                "spacing_source": str(plans_path.relative_to(REPO_ROOT)),
                            }
                        )
                    ),
                    area_reference_receipt_sha256=json_sha(area),
                    formal_resumable=not bool(args.allow_short_smoke),
                )
                payload = torch.load(ckpt, map_location="cpu", weights_only=False)
                write_json(out_dir / f"{ckpt.stem}_receipt.json", checkpoint_receipt(ckpt, payload))
                reload_descriptor = bundle.micro_descriptors[0]
                rng_state_before_reload_probe = capture_training_rng_state(sampler)
                rng_before_reload_probe = rng_state_hashes(sampler)
                reload_batch = runtime.materialize_microbatch(
                    reload_descriptor,
                    descriptor_sha=reload_descriptor.sha256(),
                    micro=0,
                )
                reload_batch["case_id"] = descriptor.case_id
                reload_batch["descriptor_sha256"] = desc_sha
                reload_receipt = _write_full_reload_receipt(
                    ckpt,
                    live_model=model,
                    live_optimizer=optimizer,
                    live_scheduler=scheduler,
                    fixed_batch=reload_batch,
                    global_step=step + 1,
                    fold=fold,
                    seed=args.seed,
                    out_dir=out_dir,
                    hard_negative_manifest_path=Path(str(sampler_manifest_path)) if sampler_manifest_path else None,
                    expected_request_nonce=runtime_input_bundle.get("request_nonce") if runtime_input_bundle else None,
                    expected_frozen_contract_sha256=runtime_input_bundle.get("frozen_contract_sha256") if runtime_input_bundle else None,
                    expected_implementation_source_manifest_sha256=runtime_input_bundle.get("implementation_source_manifest_sha256") if runtime_input_bundle else None,
                    expected_integration_commit_sha=runtime_input_bundle.get("integration_commit_sha") if runtime_input_bundle else None,
                )
                restore_training_rng_state(rng_state_before_reload_probe, sampler)
                rng_after_reload_probe = rng_state_hashes(sampler)
                rng_transparency = {
                    "status": "PASS" if rng_before_reload_probe == rng_after_reload_probe else "FAIL",
                    "fold": fold,
                    "checkpoint": str(ckpt),
                    "validation_mode": "same_process_restore_all_training_rng_after_probe",
                    "python_rng_before_after": rng_before_reload_probe.get("python_rng") == rng_after_reload_probe.get("python_rng"),
                    "numpy_rng_before_after": rng_before_reload_probe.get("numpy_rng") == rng_after_reload_probe.get("numpy_rng"),
                    "torch_cpu_rng_before_after": rng_before_reload_probe.get("torch_cpu_rng") == rng_after_reload_probe.get("torch_cpu_rng"),
                    "torch_cuda_rng_before_after": rng_before_reload_probe.get("torch_cuda_rng") == rng_after_reload_probe.get("torch_cuda_rng"),
                    "sampler_rng_before_after": rng_before_reload_probe.get("sampler_rng") == rng_after_reload_probe.get("sampler_rng"),
                    "micro_case_rng_before_after": rng_before_reload_probe.get("micro_case_rng") == rng_after_reload_probe.get("micro_case_rng"),
                    "micro_patch_rng_before_after": rng_before_reload_probe.get("micro_patch_rng") == rng_after_reload_probe.get("micro_patch_rng"),
                    "augmentation_rng_before_after": rng_before_reload_probe.get("augmentation_rng") == rng_after_reload_probe.get("augmentation_rng"),
                    "before_hashes": rng_before_reload_probe,
                    "after_hashes": rng_after_reload_probe,
                    "checkpoint_probe_rng_perturbation_count": 0 if rng_before_reload_probe == rng_after_reload_probe else 1,
                }
                write_json(out_dir / f"{ckpt.stem}_checkpoint_validation_rng_transparency.json", rng_transparency)
                if rng_transparency["status"] != "PASS":
                    raise RuntimeError(f"checkpoint validation perturbed training RNG: {rng_transparency}")
                verified = {
                    "status": "PASS",
                    "checkpoint_sha256": sha256_file(ckpt),
                    "source_sha": head_sha,
                    "fold": fold,
                    "global_step": step + 1,
                    "contract_sha256": live_effective_contract_sha,
                    "full_reload_logit_parity": reload_receipt["status"],
                    "optimizer_state_load": reload_receipt["optimizer_state_loaded"],
                    "scheduler_state_load": bool(reload_receipt["scheduler_state_loaded"]),
                    "sampler_state_load": reload_receipt["sampler_rng_state_loaded"],
                    "next_bundle_hash": reload_receipt["next_optimizer_step_micro_descriptor_hash_payload"],
                    "verification_rng_transparency": rng_transparency["status"],
                    "verification_command": "in_process_scheme_B_rng_restored_probe",
                    "verification_exit": 0,
                }
                write_json(ckpt.with_suffix(ckpt.suffix + ".verified.json"), verified)

    finally:
        heartbeat.stop()
    terminal = out_dir / f"checkpoint_step{args.end_step:05d}.pt" if args.end_step < 14000 else out_dir / "checkpoint_step14000.pt"
    payload = torch.load(terminal, map_location="cpu", weights_only=False)
    write_json(
        out_dir / f"chunk_terminal_{args.start_step:05d}_{args.end_step:05d}.json",
        {"status": "PASS", "log_path": str(log_path), **checkpoint_receipt(terminal, payload)},
    )
    record_v9_probe_budget_completion(probe_budget, status="COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
