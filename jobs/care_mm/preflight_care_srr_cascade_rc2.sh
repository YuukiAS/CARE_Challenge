#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --job-name=CareSRRPre2
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=24G
#SBATCH --time=0:20:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"

RESULT_ROOT="${CARE_ROOT}/results/20260724_care_myops_srr_cascade_submission_rescue"
RC1_ROOT="${RESULT_ROOT}/runtime_closure_repair_rc1"
PARTITION_NAME="${CARE_PREFLIGHT_PARTITION:-${SLURM_JOB_PARTITION:-unknown}}"
ATTEMPT_ID="${CARE_PREFLIGHT_ATTEMPT_ID:-${SLURM_JOB_ID:-local}_${PARTITION_NAME}}"
mkdir -p "${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue/preflight_v2" "${RC1_ROOT}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue/preflight_v2/CareSRRPre2_${ATTEMPT_ID}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

"${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PY'
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import torch

ROOT = Path("/users/a/e/aereinh/CARE")
RESULT = ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
RC1 = RESULT / "runtime_closure_repair_rc1"
ATTEMPT_ID = os.environ.get("CARE_PREFLIGHT_ATTEMPT_ID", os.environ.get("SLURM_JOB_ID", "local"))
PARTITION = os.environ.get("CARE_PREFLIGHT_PARTITION", os.environ.get("SLURM_JOB_PARTITION", "unknown"))
JOB_ID = os.environ.get("SLURM_JOB_ID", "local")
LOG_FILE = os.environ.get("LOG_FILE", "")

from src.care_myocardium.models.care_srr_cascade_rescue import CARESRRCascadeRescue
from src.care_myocardium.training.care_srr_cascade_trainer import CARESRRCascadeFormalTrainer, FormalRuntimeConfig

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
decision = "PASS" if device.type == "cuda" else "NEEDS_REPAIR_NO_CUDA"
error = ""
try:
    model = CARESRRCascadeRescue(source_feature_channels=32).to(device)
    trainer = CARESRRCascadeFormalTrainer(
        model=model,
        config=FormalRuntimeConfig("rc2_gpu_preflight", "scar", "scar_srr_cascade", 20260725, optimizer_steps=1),
        device=device,
        use_amp=device.type == "cuda",
    )
    if not trainer.optimizer.param_groups:
        raise RuntimeError("optimizer has no parameter groups")
except Exception as exc:
    decision = "NEEDS_REPAIR"
    error = repr(exc)

receipt = {
    "attempt_id": ATTEMPT_ID,
    "partition": PARTITION,
    "slurm_job_id": JOB_ID,
    "python": sys.executable,
    "torch_version": torch.__version__,
    "cuda_available": torch.cuda.is_available(),
    "cuda_device_count": torch.cuda.device_count(),
    "device": str(device),
    "log_file": LOG_FILE,
    "exit_code": 0 if decision == "PASS" else 2,
    "decision": decision,
    "error": error,
}
path = RC1 / f"gpu_preflight_attempt_{ATTEMPT_ID}.json"
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

matrix = RC1 / "gpu_preflight_attempts_v2.csv"
rows = []
if matrix.exists():
    with matrix.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("partition") != PARTITION]
rows.append(receipt)
fieldnames = ["attempt_id", "partition", "slurm_job_id", "python", "torch_version", "cuda_available", "cuda_device_count", "device", "log_file", "exit_code", "decision", "error"]
with matrix.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(json.dumps(receipt, indent=2, sort_keys=True))
raise SystemExit(0 if decision == "PASS" else 2)
PY
