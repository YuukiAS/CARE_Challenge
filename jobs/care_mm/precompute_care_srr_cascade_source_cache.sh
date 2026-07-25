#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareSRRCache
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=8:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p "${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue"
RESULT_ROOT="${CARE_ROOT}/results/20260724_care_myops_srr_cascade_submission_rescue"
RACE_GROUP="${CACHE_RACE_GROUP:-care_srr_cache_full_all220_20260725_rc2_v6}"
ATTEMPT_ID="${CACHE_ATTEMPT_ID:-${SLURM_JOB_ID:-local}_${SLURM_JOB_PARTITION:-unknown}}"
LOCK_DIR="${CARE_SOURCE_CACHE_LOCK_DIR:-${RESULT_ROOT}/runtime/source_cache_v2.${RACE_GROUP}.winner.lock}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue/CareSRRCache_${ATTEMPT_ID}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "CARE_ROOT=${CARE_ROOT}"
echo "RACE_GROUP=${RACE_GROUP}"
echo "ATTEMPT_ID=${ATTEMPT_ID}"
echo "LOCK_DIR=${LOCK_DIR}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-local}"
echo "SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION:-unknown}"
echo "SLURM_JOB_ACCOUNT=${SLURM_JOB_ACCOUNT:-unknown}"
echo "SLURM_JOB_QOS=${SLURM_JOB_QOS:-unknown}"
echo "python=${CARE_ROOT}/envs/env_CARE/bin/python"
nvidia-smi || true

export CARE_SOURCE_CACHE_RACE_GROUP="${RACE_GROUP}"
export CARE_SOURCE_CACHE_ATTEMPT_ID="${ATTEMPT_ID}"
export CARE_SOURCE_CACHE_LOCK_DIR="${LOCK_DIR}"
export CARE_SOURCE_CACHE_LOG_FILE="${LOG_FILE}"

"${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PY'
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import socket
from pathlib import Path

import blosc2
import numpy as np
import torch
from torch.nn import functional as F

from nnunetv2.inference.sliding_window_prediction import compute_gaussian, compute_steps_for_sliding_window
from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.models.care_mm_reliable_distill import CAREMMReliableDistillResEnc, final_margin_logits

ROOT = Path("/users/a/e/aereinh/CARE")
RESULT = ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
PREPROCESSED = ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
PLANS = ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetResEncUNetMPlans.json"
CONFIG = ROOT / "configs/care_mm/srr_cascade_runtime_closure_repair.yaml"
ANCHOR_MANIFEST = ROOT / "results/srr_production/code_maturity/batch2a_raw_oof_anchor_manifest.json"
FINAL_CACHE_DIR = RESULT / "runtime/source_cache_v2"
ATTEMPT_ID = os.environ.get("CARE_SOURCE_CACHE_ATTEMPT_ID", os.environ.get("SLURM_JOB_ID", "local"))
RACE_GROUP = os.environ.get("CARE_SOURCE_CACHE_RACE_GROUP", "care_srr_cache_full_all220_20260724")
LOCK_DIR = Path(os.environ["CARE_SOURCE_CACHE_LOCK_DIR"])
TMP_CACHE_DIR = RESULT / "runtime" / f"source_cache_v2_attempt_{ATTEMPT_ID}"
WINNER_RECEIPT = RESULT / f"source_cache_v2_race_winner_{ATTEMPT_ID}.json"
LOST_RECEIPT = RESULT / f"source_cache_v2_race_lost_{ATTEMPT_ID}.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def claim_winner_lock() -> bool:
    try:
        LOCK_DIR.mkdir(parents=True)
    except FileExistsError:
        winner_meta = LOCK_DIR / "winner.json"
        write_json(
            LOST_RECEIPT,
            {
                "status": "RACE_LOST",
                "decision": "PASS_EXIT_ZERO_NO_OVERWRITE",
                "attempt_id": ATTEMPT_ID,
                "race_group": RACE_GROUP,
                "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
                "partition": os.environ.get("SLURM_JOB_PARTITION", "unknown"),
                "winner_lock_dir": str(LOCK_DIR.relative_to(ROOT)),
                "winner_receipt_exists": winner_meta.exists(),
                "log_file": os.environ.get("CARE_SOURCE_CACHE_LOG_FILE", ""),
                "reason": "winner lock already exists; this started loser exits before source-cache writes",
            },
        )
        return False
    write_json(
        LOCK_DIR / "winner.json",
        {
            "status": "WINNER_CLAIMED",
            "attempt_id": ATTEMPT_ID,
            "race_group": RACE_GROUP,
            "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
            "partition": os.environ.get("SLURM_JOB_PARTITION", "unknown"),
            "hostname": socket.gethostname(),
            "log_file": os.environ.get("CARE_SOURCE_CACHE_LOG_FILE", ""),
        },
    )
    write_json(
        WINNER_RECEIPT,
        {
            "status": "WINNER_RUNNING",
            "decision": "NEEDS_MONITOR",
            "attempt_id": ATTEMPT_ID,
            "race_group": RACE_GROUP,
            "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
            "partition": os.environ.get("SLURM_JOB_PARTITION", "unknown"),
            "winner_lock_dir": str(LOCK_DIR.relative_to(ROOT)),
            "attempt_cache_dir": str(TMP_CACHE_DIR.relative_to(ROOT)),
            "final_cache_dir": str(FINAL_CACHE_DIR.relative_to(ROOT)),
            "log_file": os.environ.get("CARE_SOURCE_CACHE_LOG_FILE", ""),
        },
    )
    return True


def load_model(path: Path) -> CAREMMReliableDistillResEnc:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model = CAREMMReliableDistillResEnc()
    model.load_state_dict(checkpoint["model"])
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return model.to(DEVICE)


def load_patch_size() -> tuple[int, int, int]:
    plans = json.loads(PLANS.read_text())
    cm = PlansManager(plans).get_configuration("3d_fullres")
    return tuple(int(v) for v in cm.patch_size)


def load_direct_parity_contract() -> dict[str, object]:
    text = CONFIG.read_text()
    block_match = re.search(r"(?ms)^  direct_parity:\n(?P<block>(?:    .+\n)+)", text)
    if not block_match:
        raise RuntimeError("source_cache direct_parity block missing from runtime closure config")
    block = block_match.group("block")
    minimum_match = re.search(r"minimum_cases:\s*(\d+)", block)
    patterns_match = re.search(r"include_modality_patterns:\s*\[([^\]]+)\]", block)
    feature_match = re.search(r"feature_max_abs_delta:\s*([0-9.eE+-]+)", block)
    logit_match = re.search(r"logit_max_abs_delta:\s*([0-9.eE+-]+)", block)
    if not (minimum_match and patterns_match and feature_match and logit_match):
        raise RuntimeError("source_cache direct_parity contract is incomplete")
    return {
        "minimum_cases": int(minimum_match.group(1)),
        "include_modality_patterns": [item.strip() for item in patterns_match.group(1).split(",")],
        "feature_max_abs_delta": float(feature_match.group(1)),
        "logit_max_abs_delta": float(logit_match.group(1)),
    }


def contract_modality_pattern(meta) -> str:
    mapping = {
        "C0+LGE+T2": "trimodal",
        "C0+LGE": "LGE_C0",
        "LGE-only": "LGE_only",
    }
    if meta.modality_group not in mapping:
        return "other"
    return mapping[meta.modality_group]


def select_parity_cases(
    case_ids: list[str],
    metadata: dict[str, object],
    contract: dict[str, object],
) -> list[str]:
    required = [str(item) for item in contract["include_modality_patterns"]]
    minimum = int(contract["minimum_cases"])
    requested = max(minimum, int(os.environ.get("CARE_SOURCE_CACHE_PARITY_CASE_COUNT", str(minimum))))
    inventory: dict[str, list[str]] = {}
    for case_id in case_ids:
        pattern = contract_modality_pattern(metadata[case_id])
        inventory.setdefault(pattern, []).append(case_id)
    missing = [pattern for pattern in required if not inventory.get(pattern)]
    if missing:
        raise RuntimeError(
            "source_cache parity modality pattern inventory missing "
            + json.dumps({"missing": missing, "inventory": {k: len(v) for k, v in sorted(inventory.items())}}, sort_keys=True)
        )
    selected: list[str] = []
    for pattern in required:
        selected.append(inventory[pattern][0])
    for case_id in case_ids:
        if len(selected) >= requested:
            break
        if case_id not in selected:
            selected.append(case_id)
    selected_patterns = {contract_modality_pattern(metadata[case_id]) for case_id in selected}
    if len(selected) < minimum or any(pattern not in selected_patterns for pattern in required):
        raise RuntimeError(
            "source_cache parity selection failed "
            + json.dumps(
                {
                    "minimum": minimum,
                    "requested": requested,
                    "selected_count": len(selected),
                    "required_patterns": required,
                    "selected_patterns": sorted(selected_patterns),
                    "inventory": {k: len(v) for k, v in sorted(inventory.items())},
                },
                sort_keys=True,
            )
        )
    return selected


def pad_to_patch(x: torch.Tensor, patch_size: tuple[int, int, int]) -> tuple[torch.Tensor, tuple[int, int, int]]:
    shape = tuple(int(v) for v in x.shape[2:])
    padded_shape = tuple(max(s, p) for s, p in zip(shape, patch_size))
    pad_pairs = []
    for size, target in reversed(list(zip(shape, padded_shape))):
        pad_pairs.extend([0, target - size])
    if any(v > 0 for v in pad_pairs):
        x = F.pad(x, pad_pairs)
    return x, shape


def crop_to_shape(tensor: torch.Tensor, shape: tuple[int, int, int]) -> torch.Tensor:
    return tensor[(slice(None), slice(None), slice(0, shape[0]), slice(0, shape[1]), slice(0, shape[2]))]


def weighted_accumulate(
    store: dict[str, torch.Tensor],
    norm: torch.Tensor | None,
    outputs: dict[str, torch.Tensor],
    *,
    keys: tuple[str, ...],
    slicer: tuple[slice, slice, slice],
    gaussian: torch.Tensor,
) -> torch.Tensor:
    if norm is None:
        norm = torch.zeros((1, 1, *store[keys[0]].shape[2:]), dtype=torch.float32, device="cpu")
    weight = gaussian.float().cpu().unsqueeze(0).unsqueeze(0)
    dest = (slice(None), slice(None), *slicer)
    norm[dest] += weight
    for key in keys:
        store[key][dest] += outputs[key].detach().float().cpu() * weight
    return norm


def model_sliding_window(
    model: CAREMMReliableDistillResEnc,
    x: torch.Tensor,
    availability: torch.Tensor,
    *,
    patch_size: tuple[int, int, int],
    role: str,
) -> tuple[dict[str, torch.Tensor], int]:
    padded, original_shape = pad_to_patch(x, patch_size)
    steps = compute_steps_for_sliding_window(tuple(int(v) for v in padded.shape[2:]), patch_size, 0.5)
    gaussian = compute_gaussian(patch_size, sigma_scale=1.0 / 8.0, value_scaling_factor=1.0, dtype=torch.float32, device=DEVICE)
    keys = ("features", "anatomy_logits", "six_class_logits")
    store: dict[str, torch.Tensor] | None = None
    norm: torch.Tensor | None = None
    tile_count = 0
    for z in steps[0]:
        for y in steps[1]:
            for xx in steps[2]:
                slicer = (slice(z, z + patch_size[0]), slice(y, y + patch_size[1]), slice(xx, xx + patch_size[2]))
                tile = padded[(slice(None), slice(None), *slicer)]
                out = model(tile, availability, return_features=True)
                if store is None:
                    store = {
                        key: torch.zeros((out[key].shape[0], out[key].shape[1], *padded.shape[2:]), dtype=torch.float32, device="cpu")
                        for key in keys
                    }
                norm = weighted_accumulate(store, norm, out, keys=keys, slicer=slicer, gaussian=gaussian)
                tile_count += 1
    if store is None or norm is None:
        raise RuntimeError(f"sliding_window_no_tiles: {role}")
    norm = norm.clamp_min(1e-8)
    merged = {key: crop_to_shape(value / norm, original_shape) for key, value in store.items()}
    return merged, tile_count


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if DEVICE.type != "cuda":
    raise RuntimeError("source-cache precompute requires a Slurm GPU allocation")

if not claim_winner_lock():
    print(json.dumps({"decision": "RACE_LOST_EXIT_ZERO", "attempt_id": ATTEMPT_ID}, indent=2), flush=True)
    raise SystemExit(0)

teacher_spec = {
    "checkpoint_role": "teacher_full_view",
    "checkpoint_path": ROOT / "results/20260723_care_myops_batch9_exposed_issues_repair/runtime/seed20260723/teacher_full_view/checkpoint_epoch50.pt",
    "checkpoint_sha256": "e92521fccec92d0066f3fa5c076fce16aea3bb02330b940c85321ab4726d1474",
}
student_spec = {
    "checkpoint_role": "student_reliable_distill",
    "checkpoint_path": ROOT / "results/20260723_care_myops_batch9_exposed_issues_repair/runtime/seed20260723/student_reliable_distill/checkpoint_epoch25.pt",
    "checkpoint_sha256": "366722497a47f292e07a0d1c1a3da57c2502b61042bc89b5cfc56b5a89e6a3a0",
}
for spec in (teacher_spec, student_spec):
    digest = sha256_file(spec["checkpoint_path"])
    if digest != spec["checkpoint_sha256"]:
        raise RuntimeError(f"checkpoint sha mismatch for {spec['checkpoint_role']}: {digest}")

manifest = json.loads(ANCHOR_MANIFEST.read_text())
case_ids = sorted({str(entry["case_id"]) for entry in manifest.get("entries", [])})
if len(case_ids) != 220:
    raise RuntimeError(f"expected 220 internal cases, got {len(case_ids)}")
metadata = load_myops_case_metadata(ROOT)
patch_size = load_patch_size()
tile_step_size = 0.5
use_gaussian = True
mirror_axes: list[int] = []

if TMP_CACHE_DIR.exists():
    shutil.rmtree(TMP_CACHE_DIR)
TMP_CACHE_DIR.mkdir(parents=True)

teacher = load_model(teacher_spec["checkpoint_path"])
student = load_model(student_spec["checkpoint_path"])

manifest_rows: list[dict[str, object]] = []
parity_rows: list[dict[str, object]] = []
hashes: dict[str, object] = {
    "status": "RUNNING",
    "scope": "full_all_220_internal_source_cache",
    "case_count_expected": 220,
    "feature_representation": "l2_normalized_full_resolution_feature",
    "feature_dtype": "float16",
    "logit_dtype": "float32",
    "device": str(DEVICE),
    "inference_mode": "tiled_sliding_window",
    "patch_size": list(patch_size),
    "patch_size_source": "nnUNetResEncUNetMPlans:3d_fullres ConfigurationManager",
    "tile_step_size": tile_step_size,
    "gaussian": use_gaussian,
    "mirror_axes": mirror_axes,
    "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
    "race_group": RACE_GROUP,
    "attempt_id": ATTEMPT_ID,
    "winner_lock_dir": str(LOCK_DIR.relative_to(ROOT)),
    "checkpoint_sha256": {
        "teacher_full_view": teacher_spec["checkpoint_sha256"],
        "student_reliable_distill": student_spec["checkpoint_sha256"],
    },
    "failed_attempts_carried_forward": [
        {
            "attempt_id": "cache_htzhulab_rc2_repair",
            "job_id": "60539519",
            "state": "FAILED",
            "exit_code": "1:0",
            "reason": "legacy whole_volume_forward parity on unpadded non-divisible volume hit ResEnc residual shape mismatch",
            "failed_lock_archived": str(
                (
                    RESULT
                    / "runtime/source_cache_v2.care_srr_cache_full_all220_20260725_rc2_v3.failed_60539519.winner.lock"
                ).relative_to(ROOT)
            ),
        },
        {
            "attempt_id": "cache_a100_rc2_repair",
            "job_id": "60539522",
            "state": "CANCELLED",
            "exit_code": "0:0",
            "reason": "cancelled after paired v3 race winner failed before publish; v4 retry uses new lock",
        },
        {
            "attempt_id": "cache_htzhulab_rc2_v4",
            "job_id": "60546764",
            "state": "FAILED",
            "exit_code": "1:0",
            "reason": "parity compared non-contract direct single-tile forward against tiled sliding-window cache; v5 uses equivalent tiled recompute",
            "failed_lock_archived": str(
                (
                    RESULT
                    / "runtime/source_cache_v2.care_srr_cache_full_all220_20260725_rc2_v4.failed_60546764.winner.lock"
                ).relative_to(ROOT)
            ),
        },
        {
            "attempt_id": "cache_a100_rc2_v4",
            "job_id": "60546773",
            "state": "CANCELLED",
            "exit_code": "0:0",
            "reason": "Controller-cancelled v4 mirror after htzhulab v4 failed; v5 retry uses new lock",
        },
        {
            "attempt_id": "cache_htzhulab_rc2_v5",
            "job_id": "60552238",
            "state": "CANCELLED",
            "exit_code": "0:0",
            "reason": "Controller-cancelled before start because submitted parity case count 4 violated config minimum_cases 8 and required modality pattern selector",
        },
        {
            "attempt_id": "cache_a100_rc2_v5",
            "job_id": "60552252",
            "state": "CANCELLED",
            "exit_code": "0:0",
            "reason": "Controller-cancelled before start because submitted parity case count 4 violated config minimum_cases 8 and required modality pattern selector",
        },
    ],
    "files": {},
}
direct_parity_contract = load_direct_parity_contract()
parity_case_ids_ordered = select_parity_cases(case_ids, metadata, direct_parity_contract)
parity_case_ids = set(parity_case_ids_ordered)
parity_case_count = len(parity_case_ids_ordered)
parity_case_patterns = {
    case_id: contract_modality_pattern(metadata[case_id])
    for case_id in parity_case_ids_ordered
}
hashes["direct_parity_contract"] = direct_parity_contract
hashes["parity_case_count"] = parity_case_count
hashes["parity_recompute_case_ids"] = parity_case_ids_ordered
hashes["parity_recompute_case_patterns"] = parity_case_patterns

with torch.inference_mode():
    for index, case_id in enumerate(case_ids, start=1):
        image = blosc2.open(str(PREPROCESSED / f"{case_id}.b2nd"), mode="r")[...]
        x = torch.from_numpy(image).unsqueeze(0).float().to(DEVICE)
        meta = metadata[case_id]
        availability = torch.tensor([meta.availability], dtype=torch.float32, device=DEVICE)
        teacher_out, teacher_tile_count = model_sliding_window(teacher, x, availability, patch_size=patch_size, role="teacher_full_view")
        student_out, student_tile_count = model_sliding_window(student, x, availability, patch_size=patch_size, role="student_reliable_distill")
        fields = {
            ("teacher_full_view", "full_resolution_feature"): F.normalize(teacher_out["features"], dim=1).detach().cpu(),
            ("teacher_full_view", "anatomy_logits"): teacher_out["anatomy_logits"].detach().cpu(),
            ("teacher_full_view", "edema_logit"): teacher_out["six_class_logits"][:, 4:5].detach().cpu(),
            ("student_reliable_distill", "scar_final_margin"): final_margin_logits(student_out["six_class_logits"])["scar"].detach().cpu(),
        }
        recompute_fields = None
        recompute_mode = "cache_reload_integrity_only"
        if case_id in parity_case_ids:
            teacher_recompute, _ = model_sliding_window(teacher, x, availability, patch_size=patch_size, role="teacher_full_view_recompute")
            student_recompute, _ = model_sliding_window(student, x, availability, patch_size=patch_size, role="student_reliable_distill_recompute")
            recompute_fields = {
                ("teacher_full_view", "full_resolution_feature"): F.normalize(teacher_recompute["features"], dim=1).detach().cpu(),
                ("teacher_full_view", "anatomy_logits"): teacher_recompute["anatomy_logits"].detach().cpu(),
                ("teacher_full_view", "edema_logit"): teacher_recompute["six_class_logits"][:, 4:5].detach().cpu(),
                ("student_reliable_distill", "scar_final_margin"): final_margin_logits(student_recompute["six_class_logits"])["scar"].detach().cpu(),
            }
            recompute_mode = "tiled_sliding_window_recompute_vs_cache"
        for (role, field), direct in fields.items():
            dtype_name = "float16" if field == "full_resolution_feature" else "float32"
            stored = direct.half() if dtype_name == "float16" else direct.float()
            rel_name = f"{case_id}__{role}__{field}.pt"
            cache_path = TMP_CACHE_DIR / rel_name
            torch.save(
                {
                    "case_id": case_id,
                    "field": field,
                    "checkpoint_role": role,
                    "tensor": stored,
                    "dtype": dtype_name,
                    "availability_lge_t2_c0": list(meta.availability),
                    "source_forward_run": True,
                    "inference_mode": "tiled_sliding_window",
                    "patch_size": patch_size,
                    "tile_step_size": tile_step_size,
                    "gaussian": use_gaussian,
                    "mirror_axes": mirror_axes,
                },
                cache_path,
            )
            loaded_payload = torch.load(cache_path, map_location="cpu", weights_only=True)
            loaded_raw = loaded_payload["tensor"]
            loaded = loaded_raw.float()
            reference = recompute_fields[(role, field)] if recompute_fields is not None else direct.float()
            max_abs_delta = float((reference.float() - loaded).abs().max().item())
            threshold = (
                float(direct_parity_contract["feature_max_abs_delta"])
                if field == "full_resolution_feature"
                else float(direct_parity_contract["logit_max_abs_delta"])
            )
            shape_ok = tuple(int(v) for v in loaded_raw.shape) == tuple(int(v) for v in stored.shape)
            dtype_ok = str(loaded_raw.dtype).replace("torch.", "") == dtype_name
            finite_ok = bool(torch.isfinite(loaded).all().item())
            if field == "full_resolution_feature":
                norms = loaded.norm(dim=1)
                l2_norm_max_abs_error = float((norms - 1.0).abs().max().item())
                l2_normalized = l2_norm_max_abs_error <= 0.0025
            else:
                l2_norm_max_abs_error = 0.0
                l2_normalized = True
            decision = (
                "PASS"
                if max_abs_delta <= threshold and shape_ok and dtype_ok and finite_ok and l2_normalized
                else "NEEDS_REPAIR"
            )
            manifest_rows.append(
                {
                    "case_id": case_id,
                    "case_index": index,
                    "case_count_expected": 220,
                    "checkpoint_role": role,
                    "field": field,
                    "cache_path": str((FINAL_CACHE_DIR / rel_name).relative_to(ROOT)),
                    "cache_dtype": dtype_name,
                    "tensor_shape": "x".join(map(str, stored.shape)),
                    "availability_lge_t2_c0": "".join(str(int(v)) for v in meta.availability),
                    "modality_pattern": contract_modality_pattern(meta),
                    "parity_recompute_case": case_id in parity_case_ids,
                    "source_forward_run": True,
                    "inference_mode": "tiled_sliding_window",
                    "patch_size": "x".join(map(str, patch_size)),
                    "tile_step_size": tile_step_size,
                    "gaussian": use_gaussian,
                    "mirror_axes": "",
                    "tile_count": teacher_tile_count if role == "teacher_full_view" else student_tile_count,
                    "shape_check": "PASS" if shape_ok else "NEEDS_REPAIR",
                    "dtype_check": "PASS" if dtype_ok else "NEEDS_REPAIR",
                    "finite_check": "PASS" if finite_ok else "NEEDS_REPAIR",
                    "l2_normalized_check": "PASS" if l2_normalized else "NEEDS_REPAIR",
                    "l2_norm_max_abs_error": l2_norm_max_abs_error,
                    "formal_training_credit": 0,
                    "decision": decision,
                }
            )
            parity_rows.append(
                {
                    "case_id": case_id,
                    "checkpoint_role": role,
                    "field": field,
                    "direct_dtype": str(direct.dtype).replace("torch.", ""),
                    "cache_dtype": dtype_name,
                    "max_abs_delta": max_abs_delta,
                    "threshold": threshold,
                    "parity_mode": recompute_mode,
                    "modality_pattern": contract_modality_pattern(meta),
                    "parity_recompute_case": case_id in parity_case_ids,
                    "inference_mode": "tiled_sliding_window",
                    "patch_size": "x".join(map(str, patch_size)),
                    "tile_step_size": tile_step_size,
                    "gaussian": use_gaussian,
                    "mirror_axes": "",
                    "shape_check": "PASS" if shape_ok else "NEEDS_REPAIR",
                    "dtype_check": "PASS" if dtype_ok else "NEEDS_REPAIR",
                    "finite_check": "PASS" if finite_ok else "NEEDS_REPAIR",
                    "l2_normalized_check": "PASS" if l2_normalized else "NEEDS_REPAIR",
                    "l2_norm_max_abs_error": l2_norm_max_abs_error,
                    "feature_representation": "l2_normalized_full_resolution_feature" if field == "full_resolution_feature" else "logit_field",
                    "decision": decision,
                }
            )
            hashes["files"][str((FINAL_CACHE_DIR / rel_name).relative_to(ROOT))] = sha256_file(cache_path)
        if index % 10 == 0 or index == len(case_ids):
            print(f"cached {index}/{len(case_ids)} cases", flush=True)

if any(row["decision"] != "PASS" for row in parity_rows):
    write_csv(RESULT / "source_cache_manifest_v2.failed.csv", manifest_rows)
    write_csv(RESULT / "source_cache_parity_v2.failed.csv", parity_rows)
    raise RuntimeError("source cache parity failure")

backup_dir = None
if FINAL_CACHE_DIR.exists():
    backup_dir = RESULT / "runtime" / f"source_cache_v2_superseded_by_{ATTEMPT_ID}"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    FINAL_CACHE_DIR.rename(backup_dir)
TMP_CACHE_DIR.rename(FINAL_CACHE_DIR)
write_csv(RESULT / "source_cache_manifest_v2.csv", manifest_rows)
write_csv(RESULT / "source_cache_parity_v2.csv", parity_rows)
hashes["status"] = "PASS"
hashes["decision"] = "PASS"
hashes["case_count_observed"] = len(case_ids)
hashes["manifest_row_count"] = len(manifest_rows)
hashes["parity_row_count"] = len(parity_rows)
hashes["manifest_sha256"] = sha256_file(RESULT / "source_cache_manifest_v2.csv")
hashes["parity_checks_sha256"] = sha256_file(RESULT / "source_cache_parity_v2.csv")
hashes["superseded_previous_final_cache_dir"] = str(backup_dir.relative_to(ROOT)) if backup_dir is not None else ""
(RESULT / "source_cache_hashes_v2.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
write_json(
    WINNER_RECEIPT,
    {
        "status": "WINNER_COMPLETED",
        "decision": "PASS",
        "attempt_id": ATTEMPT_ID,
        "race_group": RACE_GROUP,
        "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "partition": os.environ.get("SLURM_JOB_PARTITION", "unknown"),
        "winner_lock_dir": str(LOCK_DIR.relative_to(ROOT)),
        "final_cache_dir": str(FINAL_CACHE_DIR.relative_to(ROOT)),
        "manifest_sha256": hashes["manifest_sha256"],
        "parity_checks_sha256": hashes["parity_checks_sha256"],
        "log_file": os.environ.get("CARE_SOURCE_CACHE_LOG_FILE", ""),
    },
)
print(json.dumps({"decision": "PASS", "case_count": len(case_ids), "manifest_rows": len(manifest_rows)}, indent=2))
PY
