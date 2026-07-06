#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=M7FU2Probe
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=4:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"

source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH=/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}
export MPLCONFIGDIR="${CARE_ROOT}/.tmp/matplotlib"

mkdir -p logs "${MPLCONFIGDIR}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M7FU2Probe_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

LOCK_DIR="${CARE_ROOT}/results/20260705_srr_v3_m7_training_and_cine_utilization/runtime"
LOCK_FILE="${LOCK_DIR}/m7_followup2_primary_probe.lock"
DONE_FILE="${LOCK_DIR}/.m7_followup2_primary_probe_done"
mkdir -p "${LOCK_DIR}"
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "[M7FU2Probe] another follow-up2 probe holds ${LOCK_FILE}; exiting without duplicate write"
  exit 0
fi
if [[ -f "${DONE_FILE}" ]]; then
  echo "[M7FU2Probe] done stamp exists at ${DONE_FILE}; exiting without duplicate write"
  exit 0
fi

echo "[M7FU2Probe] host=$(hostname) job=${SLURM_JOB_ID:-local} partition=${SLURM_JOB_PARTITION:-local}"
echo "[M7FU2Probe] start=$(date -Is)"
python scripts/training/run_srr_propref_myops_fold0.py \
  --variant m7_full_srr_context_arbitration \
  --run-label m7_followup2_primary_repair \
  --device cuda \
  --base-channels 32 \
  --encoder-profile balanced_4scale \
  --patch-shape 12,96,96 \
  --batch-size 2 \
  --max-steps 1200 \
  --max-runtime-seconds 14400 \
  --min-train-loop-seconds-for-plateau 900 \
  --enforce-min-train-loop-seconds \
  --log-every 50 \
  --val-every 300 \
  --limit-train-cases 24 \
  --limit-val-cases 8 \
  --max-eval-cases 8 \
  --out-root results/20260705_srr_v3_m7_training_and_cine_utilization/runtime
touch "${DONE_FILE}"
echo "[M7FU2Probe] end=$(date -Is)"
