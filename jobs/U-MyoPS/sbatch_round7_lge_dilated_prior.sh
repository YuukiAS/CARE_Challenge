#!/bin/bash
# U-MyoPS round7 paper-aligned prior repair: LGE + dilated Stage1 prior, fold0 only.
# Submit from repo root:
#   sbatch jobs/U-MyoPS/sbatch_round7_lge_dilated_prior.sh
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=U-MyoPS-r7-prior
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"

if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  CARE_ROOT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
else
  THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
fi
export CARE_ROOT
cd "${CARE_ROOT}"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/U-MyoPS_r7_lge_dilated_prior_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${CARE_EVAL_PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
GT_DIR="${CARE_ROOT}/data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json"

echo "===== U-MyoPS round7 LGE + dilated prior ====="
echo "host=$(hostname) SLURM_JOB_ID=${SLURM_JOB_ID:-na}"
echo "LOG_FILE=${LOG_FILE}"

export FOLD=0
export UMYOPS_STAGE2_TASK=Task914_CARE_UmyopsLGEDilatedPrior
export UMYOPS_STAGE2_TASK_NAME=Task914_CARE_UmyopsLGEDilatedPrior_fold0
export UMYOPS_STAGE2_INPUT_VARIANT=lge_dilated_prior
export UMYOPS_STAGE2_PRIOR_DILATION_RADIUS_XY="${UMYOPS_STAGE2_PRIOR_DILATION_RADIUS_XY:-8}"
export UMYOPS_STAGE2_TRAINER=nnUNetTrainerPSNV8ScarCE2
export UMYOPS_STAGE2_EPOCHS="${UMYOPS_STAGE2_EPOCHS:-80}"
export UMYOPS_STAGE2_WHICH_SUBNET=scar
export UMYOPS_STAGE2_MAX_RUNTIME_SECONDS="${UMYOPS_STAGE2_MAX_RUNTIME_SECONDS:-27000}"
export UMYOPS_STAGE2_PATIENCE="${UMYOPS_STAGE2_PATIENCE:-20}"
export UMYOPS_STAGE2_EARLYSTOP_METRIC=scar
export UMYOPS_STAGE2_AUTO_PREP=1
export UMYOPS_STAGE2_FORCE_CLEAN="${UMYOPS_STAGE2_FORCE_CLEAN:-1}"

echo "Task=${UMYOPS_STAGE2_TASK_NAME}"
echo "Variant=${UMYOPS_STAGE2_INPUT_VARIANT}"
echo "Prior dilation radius xy=${UMYOPS_STAGE2_PRIOR_DILATION_RADIUS_XY}"
echo "Trainer=${UMYOPS_STAGE2_TRAINER} epochs=${UMYOPS_STAGE2_EPOCHS}"

bash "${CARE_ROOT}/jobs/U-MyoPS/sbatch_stage2.sh"

for chk in model_best model_final_checkpoint; do
  tag="round7_lge_dilated_prior_${chk}"
  echo ""
  echo "===== export ${chk} tag=${tag} ====="
  UMYOPS_EXPORT_TASK="${UMYOPS_STAGE2_TASK}" \
  UMYOPS_EXPORT_TRAINER="${UMYOPS_STAGE2_TRAINER}" \
  UMYOPS_EXPORT_CHECKPOINT="${chk}" \
  UMYOPS_EXPORT_TAG="${tag}" \
  UMYOPS_STAGE2_WHICH_SUBNET=scar \
  UMYOPS_EXPORT_FORCE_FALLBACK=1 \
  LOG_FILE="${LOG_FILE}" \
  CARE_ROOT="${CARE_ROOT}" \
  bash "${CARE_ROOT}/jobs/U-MyoPS/sbatch_export_eval_fold0.sh"
done

echo "===== U-MyoPS round7 LGE + dilated prior done ====="
