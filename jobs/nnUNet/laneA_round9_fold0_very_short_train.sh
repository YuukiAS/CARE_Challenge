#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=LaneA_R9_F0VS
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
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/LaneA_R9_F0VS_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export PATH="${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
source "${CARE_ROOT}/env_nnunet.sh"

export MPLCONFIGDIR="${CARE_ROOT}/results/diagnostics/care_myocardium/laneA_myops/round09_baseline_initialized_adaptation/mpl_cache"
export PYTHONPATH="${CARE_ROOT}:${PYTHONPATH:-}"
export OMP_NUM_THREADS=1
export nnUNet_n_proc_DA="${nnUNet_n_proc_DA:-2}"
export LANEA_ROUND9_INIT_CHECKPOINT="${LANEA_ROUND9_INIT_CHECKPOINT:-${CARE_ROOT}/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth}"
export LANEA_ROUND9_EXPERIMENT_NAME="${LANEA_ROUND9_EXPERIMENT_NAME:-laneA_r9_ckptinit_6ch_edema_adapt_fold0_very_short_v2}"
export LANEA_ROUND9_EPOCHS="${LANEA_ROUND9_EPOCHS:-3}"
export LANEA_ROUND9_ITERS_PER_EPOCH="${LANEA_ROUND9_ITERS_PER_EPOCH:-5}"
export LANEA_ROUND9_VAL_ITERS_PER_EPOCH="${LANEA_ROUND9_VAL_ITERS_PER_EPOCH:-2}"
export LANEA_ROUND9_INITIAL_LR="${LANEA_ROUND9_INITIAL_LR:-0.00001}"
export LANEA_ROUND9_FULL_CE_WEIGHT="${LANEA_ROUND9_FULL_CE_WEIGHT:-1.0}"
export LANEA_ROUND9_DICE_WEIGHT="${LANEA_ROUND9_DICE_WEIGHT:-1.0}"
export LANEA_ROUND9_EDEMA_EXPERT_WEIGHT="${LANEA_ROUND9_EDEMA_EXPERT_WEIGHT:-1.0}"
export LANEA_ROUND9_EDEMA_POSITIVE_WEIGHT_CAP="${LANEA_ROUND9_EDEMA_POSITIVE_WEIGHT_CAP:-50.0}"
export LANEA_ROUND9_NO_T2_CONFIDENCE_WEIGHT="${LANEA_ROUND9_NO_T2_CONFIDENCE_WEIGHT:-0.0}"
export LANEA_ROUND9_NO_T2_CONFIDENCE_THRESHOLD="${LANEA_ROUND9_NO_T2_CONFIDENCE_THRESHOLD:-0.5}"
export LANEA_ROUND9_T2_ABSENT_LOGIT_BIAS="${LANEA_ROUND9_T2_ABSENT_LOGIT_BIAS:-0.0}"

echo "LOG_FILE=${LOG_FILE}"
echo "Timestamp: $(date -Iseconds 2>/dev/null || date)"
echo "Host: $(hostname 2>/dev/null || true) JobID: ${SLURM_JOB_ID:-local}"
echo "Scope: Lane A Round9 fold0 very-short train only"
echo "Trainer: nnUNetTrainerLaneABaselineInitializedEdemaAdapt"
echo "Experiment: ${LANEA_ROUND9_EXPERIMENT_NAME}"
echo "InitCheckpoint=${LANEA_ROUND9_INIT_CHECKPOINT}"
echo "Epochs=${LANEA_ROUND9_EPOCHS} TrainIters=${LANEA_ROUND9_ITERS_PER_EPOCH} ValIters=${LANEA_ROUND9_VAL_ITERS_PER_EPOCH}"
echo "InitialLR=${LANEA_ROUND9_INITIAL_LR} EdemaExpertWeight=${LANEA_ROUND9_EDEMA_EXPERT_WEIGHT}"

"${CARE_ROOT}/envs/env_CARE/bin/python" "${CARE_ROOT}/scripts/training/run_laneA_round9_nnunet_train.py" \
  --dataset 501 \
  --configuration 3d_fullres \
  --fold 0 \
  --run-validation-export \
  --init-checkpoint "${LANEA_ROUND9_INIT_CHECKPOINT}"

"${CARE_ROOT}/envs/env_CARE/bin/python" "${CARE_ROOT}/scripts/diagnostics/laneA_round9_fold0_eval.py"

echo "===== Lane A Round9 fold0 very-short train complete ====="
