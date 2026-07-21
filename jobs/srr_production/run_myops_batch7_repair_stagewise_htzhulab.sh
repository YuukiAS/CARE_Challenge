#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=B7RStage
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
STAGE="${STAGE:?set STAGE to proposal, scar_refiner, edema_refiner, source_arbiter, or production_gate}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
export PARTITION_LABEL=htzhulab
mkdir -p logs/srr_batch7_repair
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/srr_batch7_repair/B7RStage_${STAGE}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

ATTEMPT_LABEL="${ATTEMPT_LABEL:-batch7_repair_${STAGE}_${PARTITION_LABEL}_${SLURM_JOB_ID:-local}}"
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_srr_batch7_repair_stagewise.py --stage "${STAGE}" --attempt-label "${ATTEMPT_LABEL}"
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/aggregate_srr_batch7_repair_training.py \
  --stage "${STAGE}" \
  --attempt-label "${ATTEMPT_LABEL}" \
  --job-id "${SLURM_JOB_ID:-local}" \
  --job-state "${JOB_STATE:-UNKNOWN_IN_JOB}" \
  --exit-code "${EXIT_CODE:-UNKNOWN_IN_JOB}" \
  --elapsed "${ELAPSED:-UNKNOWN_IN_JOB}" \
  --node "${SLURM_JOB_NODELIST:-local}"
