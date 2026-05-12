#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=U-MyoPS-Stage1-D501
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# U-MyoPS stage 1 only: data prepare (optional) + joint registration / myocardium segmentation.
# Stage 2 (pathology nnU-Net v1): submit sbatch_stage2.sh (see run_unified_benchmark_{test,all}.sh, UMYOPS_BENCHMARK_STAGES).
set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
cd "${CARE_ROOT}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
export CARE_CineMyoPS_ENV
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
export LEGACY_PYTHON="${LEGACY_PYTHON:-${CARE_CineMyoPS_ENV}/bin/python}"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/U-MyoPS_Stage1_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${UMYOPS_PYTHON:-${CARE_CineMyoPS_ENV}/bin/python}"

echo "===== U-MyoPS Stage 1: prepare + training (py=${PY}) ====="
if [[ "${PREPARE:-1}" == "1" ]]; then
  "${PY}" "${CARE_ROOT}/code/U-MyoPS/prepare_u_myops_from_care.py" "$@"
fi
bash "${CARE_ROOT}/code/U-MyoPS/run_stage1.sh"
echo "===== U-MyoPS Stage 1 done ====="
