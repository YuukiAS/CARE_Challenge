#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRv3M8CineReg
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=05:45:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
export SRR_CINE_TASK_KEY="20260707_srr_v3_m8_editor_grade_leaderboard_sprint"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRv3M8CineReg_htzhulab_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

python scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py \
  --max-cases "${MAX_CINE_CASES:-12}" \
  --pairs-per-case "${CINE_PAIRS_PER_CASE:-3}" \
  --demons-iterations "${DEMONS_ITERATIONS:-40}" \
  --antspy-iterations "${ANTSPY_ITERATIONS:-25}"

OUT_DIR="${CARE_ROOT}/results/${SRR_CINE_TASK_KEY}"
[[ -f "${OUT_DIR}/registration_same_subset_matrix.csv" ]] && cp "${OUT_DIR}/registration_same_subset_matrix.csv" "${OUT_DIR}/m8_registration_same_subset_matrix.csv"
[[ -f "${OUT_DIR}/cine_metrics_summary.csv" ]] && cp "${OUT_DIR}/cine_metrics_summary.csv" "${OUT_DIR}/m8_cine_metrics_summary.csv"
[[ -f "${OUT_DIR}/cine_registration_repair_report.md" ]] && cp "${OUT_DIR}/cine_registration_repair_report.md" "${OUT_DIR}/m8_registration_method_selection.md"
