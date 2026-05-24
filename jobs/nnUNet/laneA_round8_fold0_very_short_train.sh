#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=LaneA_R8_F0VS
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=2:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#SBATCH --chdir=/overflow/htzhu/CARE
set -euo pipefail

CARE_ROOT="/overflow/htzhu/CARE"
export CARE_ROOT
cd "${CARE_ROOT}"
mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/LaneA_R8_F0VS_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export PATH="${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
source "${CARE_ROOT}/env_nnunet.sh"

export MPLCONFIGDIR="${CARE_ROOT}/results/diagnostics/care_myocardium/laneA_myops/round08_t2_edema_expert/mpl_cache"
export PYTHONPATH="${CARE_ROOT}:${PYTHONPATH:-}"
export OMP_NUM_THREADS=1
export nnUNet_n_proc_DA="${nnUNet_n_proc_DA:-2}"
export LANEA_ROUND8_EPOCHS="${LANEA_ROUND8_EPOCHS:-3}"
export LANEA_ROUND8_ITERS_PER_EPOCH="${LANEA_ROUND8_ITERS_PER_EPOCH:-5}"
export LANEA_ROUND8_VAL_ITERS_PER_EPOCH="${LANEA_ROUND8_VAL_ITERS_PER_EPOCH:-2}"
export LANEA_ROUND8_INITIAL_LR="${LANEA_ROUND8_INITIAL_LR:-0.0001}"
export LANEA_ROUND8_FULL_CE_WEIGHT="${LANEA_ROUND8_FULL_CE_WEIGHT:-1.0}"
export LANEA_ROUND8_DICE_WEIGHT="${LANEA_ROUND8_DICE_WEIGHT:-1.0}"
export LANEA_ROUND8_EDEMA_EXPERT_WEIGHT="${LANEA_ROUND8_EDEMA_EXPERT_WEIGHT:-3.0}"
export LANEA_ROUND8_EDEMA_POSITIVE_WEIGHT_CAP="${LANEA_ROUND8_EDEMA_POSITIVE_WEIGHT_CAP:-50.0}"
export LANEA_ROUND8_NO_T2_CONFIDENCE_WEIGHT="${LANEA_ROUND8_NO_T2_CONFIDENCE_WEIGHT:-0.0}"
export LANEA_ROUND8_NO_T2_CONFIDENCE_THRESHOLD="${LANEA_ROUND8_NO_T2_CONFIDENCE_THRESHOLD:-0.5}"
export LANEA_ROUND8_T2_ABSENT_LOGIT_BIAS="${LANEA_ROUND8_T2_ABSENT_LOGIT_BIAS:-6.0}"

echo "LOG_FILE=${LOG_FILE}"
echo "Timestamp: $(date -Iseconds 2>/dev/null || date)"
echo "Host: $(hostname 2>/dev/null || true) JobID: ${SLURM_JOB_ID:-local}"
echo "Scope: Lane A Round8 fold0 very-short train only"
echo "Trainer: nnUNetTrainerLaneAT2EdemaExpertShort"
echo "Experiment: laneA_t2_edema_expert_sephead_fold0_short"
echo "Epochs=${LANEA_ROUND8_EPOCHS} TrainIters=${LANEA_ROUND8_ITERS_PER_EPOCH} ValIters=${LANEA_ROUND8_VAL_ITERS_PER_EPOCH}"
echo "EdemaExpertWeight=${LANEA_ROUND8_EDEMA_EXPERT_WEIGHT} NoT2Bias=${LANEA_ROUND8_T2_ABSENT_LOGIT_BIAS}"

"${CARE_ROOT}/envs/env_CARE/bin/python" "${CARE_ROOT}/scripts/training/run_laneA_round8_nnunet_train.py" \
  --dataset 501 \
  --configuration 3d_fullres \
  --fold 0 \
  --run-validation-export

"${CARE_ROOT}/envs/env_CARE/bin/python" "${CARE_ROOT}/scripts/diagnostics/laneA_round8_fold0_eval.py"

echo "===== Lane A Round8 fold0 very-short train complete ====="
