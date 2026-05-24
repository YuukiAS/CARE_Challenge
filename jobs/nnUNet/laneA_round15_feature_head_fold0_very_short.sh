#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=R15FeatHead
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
cd "${CARE_ROOT}"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
CANDIDATE_ID="${CANDIDATE_ID:?Set CANDIDATE_ID to one of the Round15 feature-head candidates}"
SAFE_CANDIDATE_ID="${CANDIDATE_ID//[^A-Za-z0-9_]/_}"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/LaneA_R15_${SAFE_CANDIDATE_ID}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export nnUNet_raw="${nnUNet_raw:-${CARE_ROOT}/data/nnUNet/nnUNet_raw}"
export nnUNet_preprocessed="${nnUNet_preprocessed:-${CARE_ROOT}/data/nnUNet/nnUNet_preprocessed}"
export nnUNet_results="${nnUNet_results:-${CARE_ROOT}/data/nnUNet/nnUNet_results}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-${CARE_ROOT}/results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/mpl_cache}"

echo "[$(date)] Lane A Round15 feature-head fold0 very-short"
echo "CARE_ROOT=${CARE_ROOT}"
echo "CANDIDATE_ID=${CANDIDATE_ID}"
echo "LOG_FILE=${LOG_FILE}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"

"${CARE_ROOT}/envs/env_CARE/bin/python" \
  scripts/training/run_laneA_round15_feature_head_train.py \
  --candidate-id "${CANDIDATE_ID}" \
  --epochs "${R15_EPOCHS:-6}" \
  --threshold "${R15_THRESHOLD:-0.55}" \
  --device "${R15_DEVICE:-cuda}"

echo "[$(date)] Done"
