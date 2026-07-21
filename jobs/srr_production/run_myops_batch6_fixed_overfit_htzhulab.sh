#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=B6FixOvf
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=01:30:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

mkdir -p logs/srr_batch6
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/srr_batch6/B6FixedOverfit_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

RESULT_ROOT="${RESULT_ROOT:-${CARE_ROOT}/results/20260721_srr_batch6_final_objective_alignment}"
LOCK_ROOT="${LOCK_ROOT:-${RESULT_ROOT}/runtime/locks}"
ATTEMPT_LABEL="${ATTEMPT_LABEL:-fixed_overfit_htzhulab_${SLURM_JOB_ID:-local}}"
LOCK_DIR="${LOCK_ROOT}/fixed_overfit_winner.lock"
mkdir -p "${LOCK_ROOT}" "${RESULT_ROOT}/runtime/attempts/${ATTEMPT_LABEL}"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "winner_lock_status=lost lock=${LOCK_DIR}"
  exit 0
fi
printf '%s\n' "${ATTEMPT_LABEL}" > "${LOCK_DIR}/winner_attempt.txt"

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_srr_batch6_fixed_overfit.py \
  --config configs/srr_production/myops_batch6.yaml \
  --result-root results/20260721_srr_batch6_final_objective_alignment \
  --device cuda
