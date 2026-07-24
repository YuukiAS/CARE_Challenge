#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=B10CkptScreen
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
mkdir -p logs/care_myops_batch10_deadline_rescue/inference
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_batch10_deadline_rescue/inference/B10CkptScreen_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
source "${CARE_ROOT}/.care-codex-env.sh" || true
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
export CARE_ROOT
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
echo "[B10CkptScreen] start $(date -Is) job=${SLURM_JOB_ID:-local} cwd=${PWD} log=${LOG_FILE}"
nvidia-smi || true
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/batch10_checkpoint_screening.py --phase all --device cuda
echo "[B10CkptScreen] done $(date -Is)"
