#!/bin/bash
# Slurm smoke: small Task026 export + few-epoch nnU-Net v1 training (no protocol export).
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CineMyoPS_smoke
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

# Slurm may execute the batch file from a spool copy; prefer submit directory for CARE_ROOT.
if [[ -z "${CARE_ROOT:-}" ]]; then
  if [[ -n "${SLURM_SUBMIT_DIR:-}" && -f "${SLURM_SUBMIT_DIR}/env_nnunet.sh" ]]; then
    CARE_ROOT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
  else
    THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CARE_ROOT="$(cd "${THIS_DIR}/../.." && pwd)"
  fi
fi
export CARE_ROOT
cd "${CARE_ROOT}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
_SHORT="${SLURM_JOB_NAME:-CineMyoPS_smoke}"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/${_SHORT}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export PYTHONUNBUFFERED=1
export CINE_SMOKE_SKIP_EXPORT="${CINE_SMOKE_SKIP_EXPORT:-1}"
export CINE_SMOKE_EPOCHS="${CINE_SMOKE_EPOCHS:-5}"

echo "===== CineMyoPS smoke (Slurm) ====="
echo "log: $(readlink -f "${LOG_FILE}")"
echo "CINE_SMOKE_EPOCHS=${CINE_SMOKE_EPOCHS} CINE_SMOKE_SKIP_EXPORT=${CINE_SMOKE_SKIP_EXPORT}"

bash "${CARE_ROOT}/code/CineMyoPS/smoke_test.sh"
echo "===== CineMyoPS smoke done ====="
