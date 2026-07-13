#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --job-name=M10CinePre
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH=/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}
mkdir -p logs results/20260711_srr_v3_m10_complete_mechanism_repair/logs results/20260711_srr_v3_m10_complete_mechanism_repair/locks
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M10CinePre_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

python scripts/ops/run_care_training_preflight.py \
  --python ./envs/env_CARE/bin/python \
  --entrypoint scripts/training/run_cine_temporal_model_m10.py \
  --config configs/srr_v3_m10_complete_repair.yaml \
  --result-dir results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_cine_temporal_executor \
  --log-dir results/20260711_srr_v3_m10_complete_mechanism_repair/logs \
  --lock-path results/20260711_srr_v3_m10_complete_mechanism_repair/locks/m10_cine_temporal_executor.lock \
  --import torch \
  --import sympy \
  --import mpmath \
  --optimizer-smoke-command adamw \
  --contract-command "scripts/training/run_cine_temporal_model_m10.py --print-contract" \
  --receipt-path results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_cine_temporal_executor/preflight_receipt.json
