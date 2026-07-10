#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --job-name=CareFinalizer
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=8G
#SBATCH --time=02:00:00

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

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CareFinalizer_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PYTHON="${PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
if [ ! -x "${PYTHON}" ]; then
  PYTHON="python"
fi

echo "CARE_ROOT=${CARE_ROOT}"
echo "LOG_FILE=${LOG_FILE}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-local}"
exec "${PYTHON}" scripts/ops/care_milestone_finalizer.py "$@"
