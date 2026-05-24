#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=LaneA_R10_Refiner
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
cd "${CARE_ROOT}"
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/LaneA_R10_Refiner_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export CARE_ROOT
export nnUNet_raw="${CARE_ROOT}/data/nnUNet/nnUNet_raw"
export nnUNet_preprocessed="${CARE_ROOT}/data/nnUNet/nnUNet_preprocessed"
export nnUNet_results="${CARE_ROOT}/data/nnUNet/nnUNet_results"
export MPLCONFIGDIR="${CARE_ROOT}/results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/mpl_cache"

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_laneA_round10_refiner_train.py \
  --run-name laneA_r10_edema_residual_refiner_fold0_very_short \
  --epochs 3 \
  --steps-per-epoch 40 \
  --lr 0.001 \
  --hidden-channels 16 \
  --delta-max 1.0 \
  --threshold 0.5 \
  --seed 42 \
  --patch-shape 8,128,128
