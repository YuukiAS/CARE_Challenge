#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=U-MyoPS-Stage1-D501
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# U-MyoPS stage 1 only: data prepare (optional) + joint registration / myocardium segmentation.
# Stage 2 (pathology nnU-Net v1): submit sbatch_stage2.sh (see run_unified_benchmark_{test,all}.sh, UMYOPS_BENCHMARK_STAGES).
set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"

if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  CARE_ROOT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
  THIS_DIR="${CARE_ROOT}/jobs/U-MyoPS"
else
  THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
fi
export CARE_ROOT
cd "${CARE_ROOT}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
export CARE_CineMyoPS_ENV
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
export LEGACY_PYTHON="${LEGACY_PYTHON:-${CARE_CineMyoPS_ENV}/bin/python}"

mkdir -p logs
if [[ -z "${LOG_FILE:-}" ]]; then
  TS="$(date +%Y%m%d_%H%M%S)"
  LOG_FILE="${CARE_ROOT}/logs/U-MyoPS_Stage1_${SLURM_JOB_ID:-local}_${TS}.log"
fi
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${UMYOPS_PYTHON:-${CARE_CineMyoPS_ENV}/bin/python}"

echo "===== U-MyoPS Stage 1: prepare + training (py=${PY}) ====="
if [[ "${PREPARE:-1}" == "1" ]]; then
  _prep_args=( "$@" )
  if [[ -n "${UMYOPS_PREPARE_MAX_CASES:-}" ]]; then
    _prep_args+=( --max-cases "${UMYOPS_PREPARE_MAX_CASES}" )
  fi
  "${PY}" "${CARE_ROOT}/code/U-MyoPS/prepare_u_myops_from_care.py" "${_prep_args[@]}"
fi
bash "${CARE_ROOT}/code/U-MyoPS/run_stage1.sh"
echo "===== U-MyoPS Stage 1 done ====="
