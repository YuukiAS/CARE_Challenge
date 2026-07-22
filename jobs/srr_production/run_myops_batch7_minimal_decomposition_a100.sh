#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=B7MinDec
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access

set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
PATHOLOGY="${PATHOLOGY:?set PATHOLOGY to scar or edema}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
export PARTITION_LABEL=a100-gpu
mkdir -p logs/srr_batch7_minimal_decomposition
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/srr_batch7_minimal_decomposition/B7MinDec_${PATHOLOGY}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

ATTEMPT_LABEL="${ATTEMPT_LABEL:-batch7_minimal_decomposition_${PATHOLOGY}_${PARTITION_LABEL}_${SLURM_JOB_ID:-local}}"
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_srr_batch7_minimal_decomposition.py   --pathology "${PATHOLOGY}"   --attempt-label "${ATTEMPT_LABEL}"
