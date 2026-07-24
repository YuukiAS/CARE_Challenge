#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --job-name=SRRW3Final
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=8G
#SBATCH --time=1:00:00
#SBATCH --partition=general

set -euo pipefail

CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p "${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue/SRRW3Final_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/orchestrate_care_srr_cascade_w3.py --once
