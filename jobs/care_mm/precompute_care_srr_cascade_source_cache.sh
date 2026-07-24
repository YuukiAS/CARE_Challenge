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
RACE_GROUP="${CACHE_RACE_GROUP:-care_srr_cache_full_all220_20260724}"
ATTEMPT_ID="${CACHE_ATTEMPT_ID:-${SLURM_JOB_ID:-local}_${SLURM_JOB_PARTITION:-unknown}}"
LOCK_DIR="${RESULT_ROOT}/source_cache_full_runtime.winner.lock"
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
import shutil
import socket
from pathlib import Path

import blosc2
import torch
from torch.nn import functional as F

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.models.care_mm_reliable_distill import CAREMMReliableDistillResEnc, final_margin_logits

ROOT = Path("/users/a/e/aereinh/CARE")
RESULT = ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
PREPROCESSED = ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
ANCHOR_MANIFEST = ROOT / "results/srr_production/code_maturity/batch2a_raw_oof_anchor_manifest.json"
FINAL_CACHE_DIR = RESULT / "source_cache_full_runtime"
ATTEMPT_ID = os.environ.get("CARE_SOURCE_CACHE_ATTEMPT_ID", os.environ.get("SLURM_JOB_ID", "local"))
RACE_GROUP = os.environ.get("CARE_SOURCE_CACHE_RACE_GROUP", "care_srr_cache_full_all220_20260724")
LOCK_DIR = Path(os.environ["CARE_SOURCE_CACHE_LOCK_DIR"])
TMP_CACHE_DIR = RESULT / f"source_cache_full_runtime_attempt_{ATTEMPT_ID}"
WINNER_RECEIPT = RESULT / f"source_cache_race_winner_{ATTEMPT_ID}.json"
LOST_RECEIPT = RESULT / f"source_cache_race_lost_{ATTEMPT_ID}.json"


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
case_ids = sorted(manifest["unique_cases"])
if len(case_ids) != 220:
    raise RuntimeError(f"expected 220 internal cases, got {len(case_ids)}")
metadata = load_myops_case_metadata(ROOT)

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
    "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
    "race_group": RACE_GROUP,
    "attempt_id": ATTEMPT_ID,
    "winner_lock_dir": str(LOCK_DIR.relative_to(ROOT)),
    "files": {},
}

with torch.inference_mode():
    for index, case_id in enumerate(case_ids, start=1):
        image = blosc2.open(str(PREPROCESSED / f"{case_id}.b2nd"), mode="r")[...]
        x = torch.from_numpy(image).unsqueeze(0).float().to(DEVICE)
        meta = metadata[case_id]
        availability = torch.tensor([meta.availability], dtype=torch.float32, device=DEVICE)
        teacher_out = teacher(x, availability, return_features=True)
        student_out = student(x, availability, return_features=True)
        fields = {
            ("teacher_full_view", "full_resolution_feature"): F.normalize(teacher_out["features"], dim=1).detach().cpu(),
            ("teacher_full_view", "anatomy_logits"): teacher_out["anatomy_logits"].detach().cpu(),
            ("teacher_full_view", "edema_logit"): teacher_out["six_class_logits"][:, 4:5].detach().cpu(),
            ("student_reliable_distill", "scar_final_margin"): final_margin_logits(student_out["six_class_logits"])["scar"].detach().cpu(),
        }
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
                },
                cache_path,
            )
            loaded = torch.load(cache_path, map_location="cpu", weights_only=True)["tensor"].float()
            max_abs_delta = float((direct.float() - loaded).abs().max().item())
            threshold = 0.002 if field == "full_resolution_feature" else 1e-5
            decision = "PASS" if max_abs_delta <= threshold else "NEEDS_REPAIR"
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
                    "source_forward_run": True,
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
                    "feature_representation": "l2_normalized_full_resolution_feature" if field == "full_resolution_feature" else "logit_field",
                    "decision": decision,
                }
            )
            hashes["files"][str((FINAL_CACHE_DIR / rel_name).relative_to(ROOT))] = sha256_file(cache_path)
        if index % 10 == 0 or index == len(case_ids):
            print(f"cached {index}/{len(case_ids)} cases", flush=True)

if any(row["decision"] != "PASS" for row in parity_rows):
    write_csv(RESULT / "source_cache_manifest.failed.csv", manifest_rows)
    write_csv(RESULT / "source_cache_parity_checks.failed.csv", parity_rows)
    raise RuntimeError("source cache parity failure")

backup_dir = None
if FINAL_CACHE_DIR.exists():
    backup_dir = RESULT / f"source_cache_full_runtime_superseded_by_{ATTEMPT_ID}"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    FINAL_CACHE_DIR.rename(backup_dir)
TMP_CACHE_DIR.rename(FINAL_CACHE_DIR)
write_csv(RESULT / "source_cache_manifest.csv", manifest_rows)
write_csv(RESULT / "source_cache_parity_checks.csv", parity_rows)
hashes["status"] = "PASS"
hashes["decision"] = "PASS"
hashes["case_count_observed"] = len(case_ids)
hashes["manifest_row_count"] = len(manifest_rows)
hashes["parity_row_count"] = len(parity_rows)
hashes["manifest_sha256"] = sha256_file(RESULT / "source_cache_manifest.csv")
hashes["parity_checks_sha256"] = sha256_file(RESULT / "source_cache_parity_checks.csv")
hashes["superseded_previous_final_cache_dir"] = str(backup_dir.relative_to(ROOT)) if backup_dir is not None else ""
(RESULT / "source_cache_hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
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
