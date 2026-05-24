#!/bin/bash
# CineMyoPS round5 fixed inference-semantics diagnostic. No training.
# Submit from repo root:
#   sbatch jobs/CineMyoPS/sbatch_round5_debug_fixed.sh
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CineMyoPS_r5_debug
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

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

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/envs/env_CARE_nnUNet_v1}}"
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
export CARE_CineMyoPS_ENV
export PYTHONUNBUFFERED=1
export MPLCONFIGDIR="${TMPDIR:-/tmp}/matplotlib-${SLURM_JOB_ID:-local}"

mkdir -p "${CARE_ROOT}/logs" "${CARE_ROOT}/results/diagnostics/baseline_paper_models/CineMyoPS/round05_fixed_inference"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CineMyoPS_r5_debug_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "===== CineMyoPS round5 fixed debug inference semantics ====="
echo "host=$(hostname) SLURM_JOB_ID=${SLURM_JOB_ID:-na}"
echo "LOG_FILE=${LOG_FILE}"
echo "CINE_BN_RECALIBRATE=${CINE_BN_RECALIBRATE:-1} CINE_BN_RECALIB_BATCHES=${CINE_BN_RECALIB_BATCHES:-32}"

export CINE_BN_RECALIBRATE="${CINE_BN_RECALIBRATE:-1}"
export CINE_BN_RECALIB_BATCHES="${CINE_BN_RECALIB_BATCHES:-32}"

"${CARE_CineMyoPS_ENV}/bin/python" "${CARE_ROOT}/scripts/evaluation/debug_cinemyops_inference_semantics.py" \
  --output-json "${CARE_ROOT}/results/diagnostics/baseline_paper_models/CineMyoPS/round05_fixed_inference/inference_semantics_fixed.json" \
  "$@"

echo "===== CineMyoPS round5 fixed debug done ====="
