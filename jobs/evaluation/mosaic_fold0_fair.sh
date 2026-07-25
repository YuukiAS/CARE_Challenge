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

mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MoSAICFair_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "===== MoSAIC fold0 fair protocol ====="
echo "CARE_ROOT=${CARE_ROOT}"
echo "MOSAIC_ROOT=${MOSAIC_ROOT}"
echo "LOG_FILE=${LOG_FILE}"

DRY_RUN_ARGS=()
if [[ -n "${MOSAIC_DRY_RUN:-}" ]]; then
  DRY_RUN_ARGS+=(--dry-run)
fi

"${CARE_ROOT}/envs/env_CARE/bin/python"   "${CARE_ROOT}/scripts/inference/run_mosaic_fold0_fair_inference.py"   --config "${CARE_ROOT}/configs/baselines/mosaic_fold0_fair.yaml"   --mosaic-root "${MOSAIC_ROOT}"   --result-root "${CARE_ROOT}/results/20260725_care_m0_mosaic_fold0_fair_repro"   "${DRY_RUN_ARGS[@]}"

"${CARE_ROOT}/envs/env_CARE/bin/python"   "${CARE_ROOT}/scripts/evaluation/evaluate_mosaic_fold0_fair_comparison.py"   --config "${CARE_ROOT}/configs/baselines/mosaic_fold0_fair.yaml"   --result-root "${CARE_ROOT}/results/20260725_care_m0_mosaic_fold0_fair_repro"   "${DRY_RUN_ARGS[@]}"

echo "===== MoSAIC fold0 fair protocol done ====="
