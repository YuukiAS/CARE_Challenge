#!/usr/bin/env bash
set -euo pipefail
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=M10F3CineAdapter
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M10F3CineAdapter_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
python scripts/training/run_cinema_adapter_m10.py \
  --out-root "${OUT_ROOT:-results/20260714_srr_v3_m10_followup_cine_runtime/runtime/cinema_adapter}" \
  --device "${DEVICE:-auto}" \
  ${MAX_STEPS:+--max-steps "${MAX_STEPS}"} \
  ${MIN_TRAIN_LOOP_SECONDS:+--min-train-loop-seconds "${MIN_TRAIN_LOOP_SECONDS}"}
