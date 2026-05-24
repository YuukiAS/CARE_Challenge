#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=LaneA_R4_F0
#SBATCH --output=logs/LaneA_R4_F0_slurm_%j.out
#SBATCH --error=logs/LaneA_R4_F0_slurm_%j.err
#SBATCH --mem=64G
#SBATCH --time=4:00:00
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
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/LaneA_R4_F0_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export PATH="${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
source "${CARE_ROOT}/env_nnunet.sh"

export MPLCONFIGDIR="${CARE_ROOT}/results/diagnostics/phase0_phase1/laneA_myops/round4_fold0_short_train/mpl_cache"
export PYTHONPATH="${CARE_ROOT}:${PYTHONPATH:-}"
export OMP_NUM_THREADS=1
export nnUNet_n_proc_DA="${nnUNet_n_proc_DA:-4}"
export LANEA_ROUND4_EPOCHS="${LANEA_ROUND4_EPOCHS:-20}"
export LANEA_ROUND4_ITERS_PER_EPOCH="${LANEA_ROUND4_ITERS_PER_EPOCH:-25}"
export LANEA_ROUND4_VAL_ITERS_PER_EPOCH="${LANEA_ROUND4_VAL_ITERS_PER_EPOCH:-10}"
export LANEA_ROUND4_INITIAL_LR="${LANEA_ROUND4_INITIAL_LR:-0.0001}"
export LANEA_ROUND4_AUX_WEIGHT="${LANEA_ROUND4_AUX_WEIGHT:-0.25}"
export LANEA_ROUND4_NO_T2_WEIGHT="${LANEA_ROUND4_NO_T2_WEIGHT:-0.25}"

PRETRAINED="${CARE_ROOT}/data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth"

echo "LOG_FILE=${LOG_FILE}"
echo "Timestamp: $(date -Iseconds 2>/dev/null || date)"
echo "Host: $(hostname 2>/dev/null || true) JobID: ${SLURM_JOB_ID:-local}"
echo "Scope: Lane A Round4 fold0 short train only"
echo "Trainer: nnUNetTrainerLaneAEdemaFocalTverskyT2DownShort"
echo "Experiment: laneA_edema_focal_tversky_t2down_fold0_short"
echo "PRETRAINED=${PRETRAINED}"

"${CARE_ROOT}/envs/env_CARE/bin/python" "${CARE_ROOT}/scripts/training/run_laneA_round4_nnunet_short_train.py" \
  --dataset 501 \
  --configuration 3d_fullres \
  --fold 0 \
  --pretrained-weights "${PRETRAINED}" \
  --export-validation-probabilities

"${CARE_ROOT}/envs/env_CARE/bin/python" "${CARE_ROOT}/scripts/diagnostics/laneA_round4_fold0_short_train_eval.py"

echo "===== Lane A Round4 fold0 short train complete ====="
