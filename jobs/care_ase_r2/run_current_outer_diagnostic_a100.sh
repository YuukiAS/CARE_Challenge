#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=ASEOUTER
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE/.worktrees/care-ase-faithful-formal-training-20260812}"
CARE_ENV_ROOT="${CARE_ENV_ROOT:-/users/a/e/aereinh/CARE}"
PYTHON_BIN="${PYTHON_BIN:-${CARE_ENV_ROOT}/envs/env_CARE/bin/python}"
cd "${CARE_ROOT}"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/ASEOUTER_A100_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "started_at=$(date -Is)"
echo "job_id=${SLURM_JOB_ID:-local}"
echo "host=$(hostname)"
echo "care_root=${CARE_ROOT}"
echo "log_file=${LOG_FILE}"

RESULT_ROOT="${CARE_ROOT}/results/agent_flow_v3/care-ase-faithful-formal-training-20260812"
OUTER_DIR="${RESULT_ROOT}/outer_diagnostic_user_authorized"
SUMMARY_PATH="${OUTER_DIR}/outer_diagnostic_latest_combined_summary.json"
LOCK_DIR="${OUTER_DIR}/outer_diagnostic_latest_eval.lock"
mkdir -p "${OUTER_DIR}"
if [[ -f "${SUMMARY_PATH}" ]]; then
  echo "outer diagnostic summary already exists: ${SUMMARY_PATH}"
  exit 0
fi
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "outer diagnostic lock already exists, treating this as duplicate mirror exit: ${LOCK_DIR}"
  exit 0
fi
trap 'rmdir "${LOCK_DIR}" 2>/dev/null || true' EXIT

source "${CARE_ENV_ROOT}/.care-codex-env.sh" || true
source "${CARE_ENV_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ENV_ROOT}/envs/env_CARE/bin:${PATH}"
export nnUNet_raw="${CARE_ROOT}/data/nnUNet/nnUNet_raw"
export nnUNet_preprocessed="${CARE_ROOT}/data/nnUNet/nnUNet_preprocessed"
export nnUNet_results="${CARE_ROOT}/data/nnUNet/nnUNet_results"
export MPLCONFIGDIR="${CARE_ROOT}/.tmp/matplotlib"
mkdir -p "${MPLCONFIGDIR}"

"${PYTHON_BIN}" - <<'PY'
import json
import os
import platform
import torch
payload = {
    "python": platform.python_version(),
    "torch": torch.__version__,
    "cuda_available": torch.cuda.is_available(),
    "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
}
print(json.dumps(payload, indent=2, sort_keys=True))
PY

"${PYTHON_BIN}" \
  scripts/evaluation/care_ase/run_current_user_authorized_outer_diagnostic.py \
  --latest \
  --force

echo "finished_at=$(date -Is)"
