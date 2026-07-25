#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --job-name=SRRW3Watch
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=8G
#SBATCH --time=24:00:00
#SBATCH --partition=general

set -euo pipefail

CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p "${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue/SRRW3Watch_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
export CARE_W3_WATCHER_ACTIVE=1

PAIRS="${CARE_FORMAL_RACE_PAIRS:?missing CARE_FORMAL_RACE_PAIRS}"
STATE_FILE="${CARE_FORMAL_RACE_WATCH_STATE_FILE:-${CARE_ROOT}/results/20260724_care_myops_srr_cascade_submission_rescue/runtime_closure_repair_rc1/formal_race_watcher_state_v2.json}"

"${CARE_ROOT}/envs/env_CARE/bin/python" \
  scripts/evaluation/watch_care_srr_cascade_formal_race.py \
  --pairs "${PAIRS}" \
  --interval-seconds "${WATCH_INTERVAL_SECONDS:-300}" \
  --max-iterations "${WATCH_MAX_ITERATIONS:-288}" \
  --state-file "${STATE_FILE}"
