#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareSRRFormal
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=8:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"

LOGICAL_RUN_ID="${CARE_FORMAL_LOGICAL_RUN_ID:?missing CARE_FORMAL_LOGICAL_RUN_ID}"
PATHOLOGY="${CARE_FORMAL_PATHOLOGY:?missing CARE_FORMAL_PATHOLOGY}"
SEED="${CARE_FORMAL_SEED:?missing CARE_FORMAL_SEED}"
VARIANTS="${CARE_FORMAL_VARIANTS:?missing CARE_FORMAL_VARIANTS}"
STEPS="${CARE_FORMAL_STEPS:-6250}"
VALIDATION_STEPS="${CARE_FORMAL_VALIDATION_STEPS:-1250|2500|3750|5000|6250}"

mkdir -p "${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue/${LOGICAL_RUN_ID}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_care_srr_cascade_formal.py \
  --logical-run-id "${LOGICAL_RUN_ID}" \
  --pathology "${PATHOLOGY}" \
  --seed "${SEED}" \
  --variants "${VARIANTS}" \
  --optimizer-steps-each "${STEPS}" \
  --validation-steps "${VALIDATION_STEPS}"
