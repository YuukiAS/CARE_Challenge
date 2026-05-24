#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=LaneA_R7_F0VS
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
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/LaneA_R7_F0VS_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export PATH="${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
source "${CARE_ROOT}/env_nnunet.sh"

export MPLCONFIGDIR="${CARE_ROOT}/results/diagnostics/care_myocardium/laneA_myops/round07_modality_uncertainty/mpl_cache"
export PYTHONPATH="${CARE_ROOT}:${PYTHONPATH:-}"
export OMP_NUM_THREADS=1
export nnUNet_n_proc_DA="${nnUNet_n_proc_DA:-2}"
export LANEA_ROUND7_EPOCHS="${LANEA_ROUND7_EPOCHS:-3}"
export LANEA_ROUND7_ITERS_PER_EPOCH="${LANEA_ROUND7_ITERS_PER_EPOCH:-5}"
export LANEA_ROUND7_VAL_ITERS_PER_EPOCH="${LANEA_ROUND7_VAL_ITERS_PER_EPOCH:-2}"
export LANEA_ROUND7_INITIAL_LR="${LANEA_ROUND7_INITIAL_LR:-0.0001}"
export LANEA_ROUND7_AUX_WEIGHT="${LANEA_ROUND7_AUX_WEIGHT:-1.0}"
export LANEA_ROUND7_NO_T2_NEGATIVE_WEIGHT="${LANEA_ROUND7_NO_T2_NEGATIVE_WEIGHT:-0.25}"
export LANEA_ROUND7_T2_PRESENT_WEIGHT="${LANEA_ROUND7_T2_PRESENT_WEIGHT:-1.0}"

echo "LOG_FILE=${LOG_FILE}"
echo "Timestamp: $(date -Iseconds 2>/dev/null || date)"
echo "Host: $(hostname 2>/dev/null || true) JobID: ${SLURM_JOB_ID:-local}"
echo "Scope: Lane A Round7 fold0 very-short train only"
echo "Trainer: nnUNetTrainerLaneAModPresenceUncertaintyShort"
echo "Experiment: laneA_modpresence_uncertainty_fold0_short"
echo "Epochs=${LANEA_ROUND7_EPOCHS} TrainIters=${LANEA_ROUND7_ITERS_PER_EPOCH} ValIters=${LANEA_ROUND7_VAL_ITERS_PER_EPOCH}"
echo "AuxWeight=${LANEA_ROUND7_AUX_WEIGHT} NoT2Weight=${LANEA_ROUND7_NO_T2_NEGATIVE_WEIGHT}"

"${CARE_ROOT}/envs/env_CARE/bin/python" "${CARE_ROOT}/scripts/training/run_laneA_round7_nnunet_train.py" \
  --dataset 501 \
  --configuration 3d_fullres \
  --fold 0 \
  --run-validation-export

"${CARE_ROOT}/envs/env_CARE/bin/python" "${CARE_ROOT}/scripts/diagnostics/laneA_round7_fold0_eval.py"

echo "===== Lane A Round7 fold0 very-short train complete ====="
