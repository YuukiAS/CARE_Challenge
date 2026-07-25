#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=MoSAICFair
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=8:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
cd "${CARE_ROOT}"

# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

export PYTHONUNBUFFERED=1
export MOSAIC_ROOT="${MOSAIC_ROOT:-/users/a/e/aereinh/MoSAIC}"
export MOSAIC_SOURCE_ROOT="${MOSAIC_SOURCE_ROOT:-${CARE_ROOT}/third_party/MoSAIC/source}"
RESULT_ROOT="${RESULT_ROOT:-${CARE_ROOT}/results/20260725_care_m0_mosaic_fold0_fair_repro}"
VAL_DIR="${MOSAIC_VAL_DIR:-${RESULT_ROOT}/mosaic_runtime/fold0_val}"

mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MoSAICFair_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "===== MoSAIC fold0 fair protocol ====="
echo "CARE_ROOT=${CARE_ROOT}"
echo "MOSAIC_ROOT=${MOSAIC_ROOT}"
echo "MOSAIC_SOURCE_ROOT=${MOSAIC_SOURCE_ROOT}"
echo "RESULT_ROOT=${RESULT_ROOT}"
echo "VAL_DIR=${VAL_DIR}"
echo "LOG_FILE=${LOG_FILE}"
echo "MOSAIC_RUN_NATIVE=${MOSAIC_RUN_NATIVE:-0}"

"${CARE_ROOT}/envs/env_CARE/bin/python"   "${CARE_ROOT}/scripts/inference/prepare_mosaic_inference_runtime.py"   --source-root "${MOSAIC_SOURCE_ROOT}"   --mosaic-root "${MOSAIC_ROOT}"   --result-root "${RESULT_ROOT}"   --stage-fold0   --force

INFER_ARGS=(--dry-run)
if [[ "${MOSAIC_RUN_NATIVE:-0}" == "1" ]]; then
  INFER_ARGS=()
fi

"${CARE_ROOT}/envs/env_CARE/bin/python"   "${CARE_ROOT}/scripts/inference/run_mosaic_fold0_fair_inference.py"   --config "${CARE_ROOT}/configs/baselines/mosaic_fold0_fair.yaml"   --mosaic-root "${MOSAIC_ROOT}"   --source-root "${MOSAIC_SOURCE_ROOT}"   --val-dir "${VAL_DIR}"   --gpu "${MOSAIC_GPU:-0}"   --result-root "${RESULT_ROOT}"   "${INFER_ARGS[@]}"

"${CARE_ROOT}/envs/env_CARE/bin/python"   "${CARE_ROOT}/scripts/evaluation/evaluate_mosaic_fold0_fair_comparison.py"   --config "${CARE_ROOT}/configs/baselines/mosaic_fold0_fair.yaml"   --result-root "${RESULT_ROOT}"   --dry-run

echo "===== MoSAIC fold0 fair protocol done ====="
