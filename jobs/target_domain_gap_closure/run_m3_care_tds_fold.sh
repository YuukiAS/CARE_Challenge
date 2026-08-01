#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --job-name=M3TDS
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
STEPS="${STEPS:-4000}"
PATCH_SIZE="${PATCH_SIZE:-16,64,64}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M3TDS_fold${FOLD}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
echo "[M3TDS] job=${SLURM_JOB_ID:-local} fold=${FOLD} host=$(hostname) start=$(date -Is)"
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/target_domain_gap_closure/run_m3_care_tds.py --fold "${FOLD}" --steps "${STEPS}" --patch-size "${PATCH_SIZE}"
echo "[M3TDS] job=${SLURM_JOB_ID:-local} fold=${FOLD} end=$(date -Is)"
