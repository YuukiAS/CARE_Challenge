#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=U-MyoPS-Stage2-D501
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# U-MyoPS stage 2 only: pathology nnU-Net v1 (requires Task raw + plan_and_preprocess under U-MyoPS_myops/outputs/nnunet).
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

resolve_stage2_task_name() {
  local base="${UMYOPS_STAGE2_TASK:-Task901_CARE_UmyopsPathology}"
  if [[ "${UMYOPS_STAGE2_PER_FOLD_TASK:-1}" == "1" ]]; then
    printf '%s_fold%s\n' "${base}" "${FOLD:-0}"
  else
    printf '%s\n' "${base}"
  fi
}

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/U-MyoPS_Stage2_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

UMYO_REPO="$(cd "${CARE_ROOT}/third_party/U-MyoPS_myops" && pwd)"
UMYOPS_STAGE2_TASK_NAME="${UMYOPS_STAGE2_TASK_NAME:-$(resolve_stage2_task_name)}"
export UMYOPS_STAGE2_TASK_NAME

_PREPRO="${UMYO_REPO}/outputs/nnunet/prepro/${UMYOPS_STAGE2_TASK_NAME}"
if [[ "${UMYOPS_STAGE2_DIM:-2d}" == "2d" ]]; then
  _PLANS="${_PREPRO}/nnUNetPlansv2.1_plans_2D.pkl"
else
  _PLANS="${_PREPRO}/nnUNetPlansv2.1_plans_3D.pkl"
fi
if [[ "${UMYOPS_STAGE2_AUTO_PREP:-1}" == "1" ]] || [[ ! -f "${_PLANS}" ]]; then
  if [[ ! -f "${_PLANS}" ]]; then
    echo "Stage2 plans missing; running prepare_stage2_task.sh to build raw task + preprocess."
  else
    echo "UMYOPS_STAGE2_AUTO_PREP=1; refreshing Stage2 raw task + preprocess."
  fi
  bash "${CARE_ROOT}/code/U-MyoPS/prepare_stage2_task.sh"
fi
if [[ ! -f "${_PLANS}" ]]; then
  echo "error: U-MyoPS stage 2 requires nnU-Net v1 preprocessing (missing plans pickle)." >&2
  echo "  Expected file: ${_PLANS}" >&2
  echo "  Raw task root:   ${UMYO_REPO}/outputs/nnunet/raw/nnUNet_raw_data/${UMYOPS_STAGE2_TASK_NAME}/" >&2
  echo "  See jobs/U-MyoPS/README.md — Stage 2 prerequisites (create Task + plan_and_preprocess)." >&2
  exit 1
fi

echo "===== U-MyoPS Stage 2: pathology nnU-Net (task=${UMYOPS_STAGE2_TASK_NAME}, fold=${FOLD:-0}) ====="
bash "${CARE_ROOT}/code/U-MyoPS/run_stage2.sh" \
  "${UMYOPS_STAGE2_DIM:-2d}" \
  "${UMYOPS_STAGE2_TRAINER:-nnUNetTrainerPSNV8}" \
  "${UMYOPS_STAGE2_TASK_NAME}" \
  "${FOLD:-0}" \
  --epochs "${UMYOPS_STAGE2_EPOCHS:-100}"
echo "===== U-MyoPS Stage 2 done ====="
