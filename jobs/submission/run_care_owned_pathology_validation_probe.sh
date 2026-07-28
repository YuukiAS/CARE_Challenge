#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareOwnProbe
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"

if [ -f "${CARE_ROOT}/.care-codex-env.sh" ]; then
  # shellcheck disable=SC1091
  source "${CARE_ROOT}/.care-codex-env.sh"
fi
if [ -f "${CARE_ROOT}/env_nnunet.sh" ]; then
  # shellcheck disable=SC1091
  source "${CARE_ROOT}/env_nnunet.sh"
fi

export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
export nnUNet_raw="${nnUNet_raw:-${CARE_ROOT}/data/nnUNet/nnUNet_raw}"
export nnUNet_preprocessed="${nnUNet_preprocessed:-${CARE_ROOT}/data/nnUNet/nnUNet_preprocessed}"
export nnUNet_results="${nnUNet_results:-${CARE_ROOT}/data/nnUNet/nnUNet_results}"
export nnUNet_raw_data_base="${nnUNet_raw_data_base:-${CARE_ROOT}/data/nnUNet}"
export RESULTS_FOLDER="${RESULTS_FOLDER:-${nnUNet_results}}"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CareOwnProbe_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "CARE_ROOT=${CARE_ROOT}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-local}"
echo "LOG_FILE=${LOG_FILE}"
nvidia-smi || true

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/inference/run_care_owned_pathology_validation_probe.py \
  --device cuda \
  --skip-existing-anchor
