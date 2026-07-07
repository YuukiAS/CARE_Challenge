#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=M8BroadEval
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
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

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M8BroadEval_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PACKET="results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint"

echo "job_id=${SLURM_JOB_ID:-local}"
echo "partition=${SLURM_JOB_PARTITION:-local}"
echo "host=$(hostname)"
echo "log=${LOG_FILE}"
echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

python scripts/evaluation/export_srr_v3_m8_broad_eval.py \
  --packet "${PACKET}" \
  --max-cases 12 \
  --device cuda

python scripts/evaluation/aggregate_srr_v3_m8_leaderboard_sprint_packet.py \
  --packet "${PACKET}" \
  --contribution-device cpu \
  --skip-contribution-compute

python scripts/evaluation/validate_srr_v3_m8_leaderboard_sprint_packet.py \
  --packet "${PACKET}" \
  --self-test

python scripts/evaluation/validate_srr_v3_m8_leaderboard_sprint_packet.py \
  --packet "${PACKET}"

echo "end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
