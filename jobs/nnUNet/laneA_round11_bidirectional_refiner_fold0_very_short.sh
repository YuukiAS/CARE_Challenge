#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=LaneA_R11_BiRef
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
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/LaneA_R11_BiRef_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export CARE_ROOT
export nnUNet_raw="${CARE_ROOT}/data/nnUNet/nnUNet_raw"
export nnUNet_preprocessed="${CARE_ROOT}/data/nnUNet/nnUNet_preprocessed"
export nnUNet_results="${CARE_ROOT}/data/nnUNet/nnUNet_results"
export MPLCONFIGDIR="${CARE_ROOT}/results/diagnostics/care_myocardium/laneA_myops/round11_component_safe_refiner/mpl_cache"

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_laneA_round11_bidirectional_refiner_train.py \
  --mode train \
  --run-name laneA_r11_bidirectional_edema_refiner_fold0_very_short \
  --epochs 3 \
  --steps-per-epoch 40 \
  --lr 0.001 \
  --hidden-channels 16 \
  --delta-max 1.0 \
  --threshold 0.5 \
  --add-threshold 0.5 \
  --remove-threshold 0.45 \
  --seed 42 \
  --patch-shape 8,128,128
