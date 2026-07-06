#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=M7ContCPU
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=128G
#SBATCH --time=1:00:00
#SBATCH --partition=general

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"

source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH=/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}
export MPLCONFIGDIR="${CARE_ROOT}/.tmp/matplotlib"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-2}"

mkdir -p logs "${MPLCONFIGDIR}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M7ContCPU_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

LOCK_DIR="${CARE_ROOT}/results/20260705_srr_v3_m7_training_and_cine_utilization/runtime"
LOCK_FILE="${LOCK_DIR}/m7_continued_repair.lock"
DONE_FILE="${LOCK_DIR}/.m7_continued_repair_done"
mkdir -p "${LOCK_DIR}"
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "[M7ContCPU] another repair job holds ${LOCK_FILE}; exiting without duplicate write"
  exit 0
fi
if [[ -f "${DONE_FILE}" ]]; then
  echo "[M7ContCPU] done stamp exists at ${DONE_FILE}; exiting without duplicate write"
  exit 0
fi

echo "[M7ContCPU] host=$(hostname) job=${SLURM_JOB_ID:-local} partition=${SLURM_JOB_PARTITION:-local}"
echo "[M7ContCPU] start=$(date -Is)"
MAX_FORMAL_VAL_CASES="${MAX_FORMAL_VAL_CASES:-8}"
python scripts/evaluation/run_srr_v3_m7_continued_repair.py --device cpu --max-formal-val-cases "${MAX_FORMAL_VAL_CASES}"
touch "${DONE_FILE}"
echo "[M7ContCPU] end=$(date -Is)"
