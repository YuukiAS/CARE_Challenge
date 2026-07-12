#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=M10Align
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH=/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M10Align_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

TRAIN_ARGS=(--phase alignment_control)
EVAL_ARGS=(--phase alignment_control)
AGG_ARGS=(--phase alignment_control)
if [ -n "${M10_RUNTIME_ROOT:-}" ]; then
  TRAIN_ARGS+=(--out-root "${M10_RUNTIME_ROOT}" --contract-output-dir "${M10_RUNTIME_ROOT}/contracts")
  EVAL_ARGS+=(--runtime-root "${M10_RUNTIME_ROOT}")
  AGG_ARGS+=(--runtime-root "${M10_RUNTIME_ROOT}")
fi

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_srr_v3_m10_complete_repair.py "${TRAIN_ARGS[@]}"
if [ "${M10_DEFER_AGGREGATION:-0}" != "1" ]; then
  "${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/evaluate_srr_v3_m10_full_case.py "${EVAL_ARGS[@]}"
  "${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/aggregate_srr_v3_m10_myops.py "${AGG_ARGS[@]}"
fi
