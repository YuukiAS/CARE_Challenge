#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=R17MedNeXt
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
CANDIDATE_ID="${CANDIDATE_ID:-R17_A_mednext_s_kernel3_standard_dicece_fold0_vs}"
SAFE_CANDIDATE_ID="${CANDIDATE_ID//[^A-Za-z0-9_]/_}"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/LaneA_R17_MedNeXt_${SAFE_CANDIDATE_ID}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export nnUNet_raw="${nnUNet_raw:-${CARE_ROOT}/data/nnUNet/nnUNet_raw}"
export nnUNet_preprocessed="${nnUNet_preprocessed:-${CARE_ROOT}/data/nnUNet/nnUNet_preprocessed}"
export nnUNet_results="${nnUNet_results:-${CARE_ROOT}/data/nnUNet/nnUNet_results}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-${CARE_ROOT}/results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone/mpl_cache}"
export CARE_MEDNEXT_REPO="${CARE_MEDNEXT_REPO:-${CARE_ROOT}/results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/external_repos/MedNeXt}"

echo "[$(date)] Lane A Round17 MedNeXt fold0 very-short"
echo "CARE_ROOT=${CARE_ROOT}"
echo "CANDIDATE_ID=${CANDIDATE_ID}"
echo "LOG_FILE=${LOG_FILE}"
echo "CARE_MEDNEXT_REPO=${CARE_MEDNEXT_REPO}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"

"${CARE_ROOT}/envs/env_CARE/bin/python" \
  scripts/training/run_laneA_round17_mednext_train.py \
  --candidate-id "${CANDIDATE_ID}" \
  --epochs "${R17_EPOCHS:-25}" \
  --steps-per-epoch "${R17_STEPS_PER_EPOCH:-40}" \
  --batch-size "${R17_BATCH_SIZE:-1}" \
  --patch-shape "${R17_PATCH_SHAPE:-32x128x128}" \
  --stride-shape "${R17_STRIDE_SHAPE:-32x96x96}" \
  --device "${R17_DEVICE:-cuda}"

echo "[$(date)] Done"
