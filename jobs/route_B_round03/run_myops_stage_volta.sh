#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=RB3MyoPSV100
#SBATCH --output=/users/a/e/aereinh/CARE_worktrees/route_B/logs/route_B_round03/slurm_RB3MyoPSV100_%j.out
#SBATCH --error=/users/a/e/aereinh/CARE_worktrees/route_B/logs/route_B_round03/slurm_RB3MyoPSV100_%j.err
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:tesla_v100-sxm2-16gb:1
#SBATCH --partition=volta-gpu
#SBATCH --qos=gpu_access

set -euo pipefail
CARE_ROOT="/users/a/e/aereinh/CARE_worktrees/route_B"
MAIN_CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
mkdir -p logs/route_B_round03
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/route_B_round03/RouteBMyopsV100_${ROUTE_B_EXECUTOR:-Bx}_${SLURM_JOB_ID:-local}_${TS}.log}"
touch "${LOG_FILE}"
echo "route_B_volta_wrapper_start job=${SLURM_JOB_ID:-local} partition=${SLURM_JOB_PARTITION:-volta-gpu} log=${LOG_FILE}"
exec >> "${LOG_FILE}" 2>&1
source "${MAIN_CARE_ROOT}/.care-codex-env.sh"
source "${MAIN_CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${MAIN_CARE_ROOT}/envs/env_CARE/bin:${PATH}"
CARE_PYTHON="${MAIN_CARE_ROOT}/envs/env_CARE/bin/python"
: "${ROUTE_B_EXECUTOR:?missing ROUTE_B_EXECUTOR}"
: "${ROUTE_B_STAGE:?missing ROUTE_B_STAGE}"
: "${ROUTE_B_STEPS:?missing ROUTE_B_STEPS}"
: "${ROUTE_B_OUT:?missing ROUTE_B_OUT}"
: "${ROUTE_B_CONFIG:=configs/route_B_round03/formal.yaml}"
"${CARE_PYTHON}" scripts/route_B_round03/preflight.py --executor "${ROUTE_B_EXECUTOR}" --partition "${SLURM_JOB_PARTITION:-volta-gpu}" --config "${ROUTE_B_CONFIG}" --out "results/route_B/round03/executors/${ROUTE_B_EXECUTOR}/preflight_${SLURM_JOB_PARTITION:-volta-gpu}.json"
RACE_DIR="${CARE_ROOT}/results/route_B/runtime/round03/${ROUTE_B_EXECUTOR}/race"
RACE_LOCK="${RACE_DIR}/winner.lock"
mkdir -p "${RACE_DIR}" "results/route_B/round03/executors/${ROUTE_B_EXECUTOR}"
if mkdir "${RACE_LOCK}" 2>/dev/null; then
  {
    echo "winner_job_id=${SLURM_JOB_ID:-local}"
    echo "winner_partition=${SLURM_JOB_PARTITION:-volta-gpu}"
    echo "winner_log=${LOG_FILE}"
    echo "winner_started_at=$(date -Is)"
    echo "winner_output_root=${ROUTE_B_OUT}"
  } > "${RACE_LOCK}/winner.txt"
else
  LOSER_RECEIPT="results/route_B/round03/executors/${ROUTE_B_EXECUTOR}/race_lost_${SLURM_JOB_PARTITION:-volta-gpu}_${SLURM_JOB_ID:-local}.json"
  "${CARE_PYTHON}" - <<PY
import json
from pathlib import Path
Path("${LOSER_RECEIPT}").write_text(json.dumps({
  "status": "RACE_LOST_ZERO_CREDIT",
  "job_id": "${SLURM_JOB_ID:-local}",
  "partition": "${SLURM_JOB_PARTITION:-volta-gpu}",
  "winner_lock": "${RACE_LOCK}",
  "training_credit": 0
}, indent=2) + "\\n", encoding="utf-8")
PY
  exit 0
fi
cmd=("${CARE_PYTHON}" scripts/training/route_B_round03/train_myops.py --stage "${ROUTE_B_STAGE}" --steps "${ROUTE_B_STEPS}" --config "${ROUTE_B_CONFIG}" --out "${ROUTE_B_OUT}")
if [[ -n "${ROUTE_B_PARENT:-}" ]]; then
  cmd+=(--parent "${ROUTE_B_PARENT}")
fi
"${cmd[@]}"
case "${ROUTE_B_EXECUTOR}" in
  B3|B4|B5)
    "${CARE_PYTHON}" scripts/validation/route_B_round03/validate_stage.py --stage "${ROUTE_B_STAGE}" --strict "results/route_B/round03/executors/${ROUTE_B_EXECUTOR}"
    ;;
  B6)
    "${CARE_PYTHON}" scripts/route_B_round03/select_myops_checkpoint.py --force --all-stages --out results/route_B/round03/executors/B6
    "${CARE_PYTHON}" scripts/validation/route_B_round03/validate_myops_evidence.py --strict results/route_B/round03/executors/B6
    ;;
esac
