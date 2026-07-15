#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=M10FU2W2Replay
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
export PYTHONPATH="${CARE_ROOT}:${PYTHONPATH:-}"

mkdir -p logs results/20260715_srr_v3_m10_followup2_wave2_evidence_repair/worker_logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M10FU2W2Replay_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PHASE_ARGS=()
if [[ -n "${M10_FOLLOWUP2_PHASE:-}" ]]; then
  PHASE_ARGS+=(--phase "${M10_FOLLOWUP2_PHASE}")
fi
if [[ -n "${M10_FOLLOWUP2_CHECKPOINT:-}" ]]; then
  PHASE_ARGS+=(--checkpoint "${M10_FOLLOWUP2_CHECKPOINT}")
fi

if [[ "${M10_FOLLOWUP2_PREFLIGHT:-0}" == "1" ]]; then
  "${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/evaluate_srr_v3_m10_followup2_all_checkpoints.py --print-contract
  exit 0
fi

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/evaluate_srr_v3_m10_followup2_all_checkpoints.py \
  --evaluate --force --device cuda "${PHASE_ARGS[@]}"
