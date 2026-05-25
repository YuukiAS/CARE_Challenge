#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=R16ExtMech
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

ROUND16_MANIFEST="${ROUND16_MANIFEST:-${CARE_ROOT}/results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/round16_submitted_jobs.csv}"
if [[ -n "${SLURM_JOB_ID:-}" && "${ROUND16_ALLOW_UNREGISTERED:-0}" != "1" ]]; then
  if [[ ! -f "${ROUND16_MANIFEST}" ]] || ! awk -F, -v jid="${SLURM_JOB_ID}" 'NR > 1 && $2 == jid && ($4 ~ /^active/ || $4 ~ /^submitted_active/) {found=1} END {exit found ? 0 : 1}' "${ROUND16_MANIFEST}"; then
    echo "[$(date)] Round16 job ${SLURM_JOB_ID} is not active in ${ROUND16_MANIFEST}; exiting without training."
    exit 0
  fi
fi

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
CANDIDATE_ID="${CANDIDATE_ID:?Set CANDIDATE_ID to one of the Round16 first-party candidates}"
SAFE_CANDIDATE_ID="${CANDIDATE_ID//[^A-Za-z0-9_]/_}"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/LaneA_R16_${SAFE_CANDIDATE_ID}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export nnUNet_raw="${nnUNet_raw:-${CARE_ROOT}/data/nnUNet/nnUNet_raw}"
export nnUNet_preprocessed="${nnUNet_preprocessed:-${CARE_ROOT}/data/nnUNet/nnUNet_preprocessed}"
export nnUNet_results="${nnUNet_results:-${CARE_ROOT}/data/nnUNet/nnUNet_results}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-${CARE_ROOT}/results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/mpl_cache}"

echo "[$(date)] Lane A Round16 external mechanism fold0 very-short"
echo "CARE_ROOT=${CARE_ROOT}"
echo "CANDIDATE_ID=${CANDIDATE_ID}"
echo "LOG_FILE=${LOG_FILE}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"

"${CARE_ROOT}/envs/env_CARE/bin/python" \
  scripts/training/run_laneA_round16_external_mechanism_train.py \
  --candidate-id "${CANDIDATE_ID}" \
  --epochs "${R16_EPOCHS:-6}" \
  --threshold "${R16_THRESHOLD:-0.55}" \
  --device "${R16_DEVICE:-cuda}"

echo "[$(date)] Done"
