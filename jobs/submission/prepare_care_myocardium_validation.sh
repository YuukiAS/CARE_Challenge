#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CAREMyocardVal
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# Run CARE-Myocardium validation inference and package an official upload zip.
# The zip filename has no timestamp; the parent upload_ready folder does.
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
cd "${CARE_ROOT}"

export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p logs /tmp/matplotlib-care
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CAREMyocardVal_${SLURM_JOB_ID:-local}_${TS}.log}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/matplotlib-care}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "===== CARE-Myocardium validation submission ====="
echo "Timestamp: $(date -Iseconds 2>/dev/null || date)"
echo "Host: $(hostname 2>/dev/null || true) JobID: ${SLURM_JOB_ID:-local}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"

cmd=(
  "${CARE_ROOT}/env_CARE/bin/python" "${CARE_ROOT}/scripts/submission/prepare_care_myocardium_validation.py"
  --team-name "${TEAM_NAME:-OrganAgent}"
  --submission-model "${SUBMISSION_MODEL:-nnUNet}"
  --timestamp "${SUBMISSION_TS:-${TS}}"
  --folds ${FOLDS:-0 1 2 3 4}
  --checkpoint "${CHECKPOINT:-checkpoint_best.pth}"
  --device "${DEVICE:-cuda}"
  --continue-prediction
)
if [[ -n "${RUN_NAME:-}" ]]; then
  cmd+=( --run-name "${RUN_NAME}" )
fi
"${cmd[@]}"

echo "===== Finished CARE-Myocardium validation submission ====="
