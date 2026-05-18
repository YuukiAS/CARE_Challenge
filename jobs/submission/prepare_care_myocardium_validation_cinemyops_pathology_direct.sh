#!/bin/bash
# Prepare a CARE-Myocardium validation package with nnU-Net MyoPS and
# CineMyoPS Task026 pathology_direct fixed inference. No upload is performed.
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CAREValCinePD
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
cd "${CARE_ROOT}"

export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p logs /tmp/matplotlib-care
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CAREValCinePD_${SLURM_JOB_ID:-local}_${TS}.log}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/matplotlib-care}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "===== CARE-Myocardium validation: CineMyoPS pathology_direct ====="
echo "Timestamp: $(date -Iseconds 2>/dev/null || date)"
echo "Host: $(hostname 2>/dev/null || true) JobID: ${SLURM_JOB_ID:-local}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"
echo "CINE_COMBINE_MODE=${CINE_COMBINE_MODE:-pathology_direct}"
echo "CINE_NUM_FRAMES=${CINE_NUM_FRAMES:-4}"

cmd=(
  "${CARE_ROOT}/env_CARE/bin/python" "${CARE_ROOT}/scripts/submission/prepare_care_myocardium_validation.py"
  --team-name "${TEAM_NAME:-OrganAgent}"
  --myops-model nnUNet
  --cine-model CineMyoPS
  --run-name "${RUN_NAME:-nnUNet_MyoPS+CineMyoPS_pathology_direct}"
  --timestamp "${SUBMISSION_TS:-${TS}}"
  --folds 0
  --checkpoint "${CHECKPOINT:-checkpoint_best.pth}"
  --cine-task "${CINE_NNUNET_TASK:-Task026_Cine_4D}"
  --cine-trainer "${CINE_NNUNET_TRAINER:-CARECineMyoPSTrainerBNCalib}"
  --cine-checkpoint "${CINE_PRED_CHECKPOINT:-model_final_checkpoint}"
  --cine-num-frames "${CINE_NUM_FRAMES:-4}"
  --cine-combine-mode "${CINE_COMBINE_MODE:-pathology_direct}"
  --device "${DEVICE:-cuda}"
  --continue-prediction
)
"${cmd[@]}"

echo "===== Finished CARE-Myocardium validation: CineMyoPS pathology_direct ====="
