#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --job-name=M0RGap
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
FOLD="${FOLD:?set FOLD to 2 or 3}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
export nnUNet_compile="${nnUNet_compile:-false}"
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M0RGap_fold${FOLD}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
echo "[M0RGap] job=${SLURM_JOB_ID:-local} fold=${FOLD} host=$(hostname) start=$(date -Is)"
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/target_domain_gap_closure/run_m0r_faithful_nnunet.py --fold "${FOLD}"
echo "[M0RGap] job=${SLURM_JOB_ID:-local} fold=${FOLD} end=$(date -Is)"
