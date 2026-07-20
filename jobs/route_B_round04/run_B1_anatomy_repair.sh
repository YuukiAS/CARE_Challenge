#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=RouteB04B1
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${ROUTE_B_WORKTREE:-/users/a/e/aereinh/CARE_worktrees/route_B}"
PYTHON="${PYTHON:-/users/a/e/aereinh/CARE/envs/env_CARE/bin/python}"
cd "${CARE_ROOT}"
CANONICAL_OUT="results/route_B/round04/executors/B1"
ATTEMPT_TAG="${ROUTE_B_ATTEMPT_TAG:-${SLURM_JOB_ID:-local}}"
RACE_MODE="${ROUTE_B_RACE_MODE:-0}"
if [[ "${RACE_MODE}" == "1" ]]; then
  OUT_DIR="${ROUTE_B_B1_OUT:-${CANONICAL_OUT}/attempts/${ATTEMPT_TAG}}"
else
  OUT_DIR="${ROUTE_B_B1_OUT:-${CANONICAL_OUT}}"
fi
RUNTIME_DIR="${ROUTE_B_B1_RUNTIME:-results/route_B/runtime/round04/B1/${ATTEMPT_TAG}}"
export ROUTE_B_B1_RUNTIME="${RUNTIME_DIR}"
WINNER_LOCK="results/route_B/runtime/round04/B1/B1_winner.lock"
mkdir -p logs "${RUNTIME_DIR}" "${OUT_DIR}" results/route_B/runtime/round04/B1
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/RouteB04B1_${SLURM_JOB_ID:-local}_${ATTEMPT_TAG}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "stage=B1"
echo "python=${PYTHON}"
echo "attempt_tag=${ATTEMPT_TAG}"
echo "race_mode=${RACE_MODE}"
echo "out_dir=${OUT_DIR}"
echo "runtime_dir=${RUNTIME_DIR}"
"${PYTHON}" --version
"${PYTHON}" scripts/route_B_round04/preflight.py \
  --stage B1 \
  --contract results/route_B/round04/planning_snapshot/prompts/routes/route_B_round04_controller_contract.md \
  --out "${OUT_DIR}/preflight_receipt.json"
"${PYTHON}" scripts/training/route_B_round04/run_B1_anatomy_repair.py \
  --manifest configs/route_B_round04/manifests/myops_fold0_primary_44.json \
  --out "${OUT_DIR}" \
  --steps "${ROUTE_B_B1_STEPS:-2000}" \
  --min-train-seconds "${ROUTE_B_B1_MIN_SECONDS:-600}"
"${PYTHON}" scripts/validation/route_B_round04/validate_B1_anatomy_repair.py \
  --strict \
  --input "${OUT_DIR}" \
  --report "${OUT_DIR}/validator_report.json" \
  --require-token ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_IMPLEMENTED
"${PYTHON}" scripts/validation/route_B_round04/run_known_bad_matrix.py \
  --stage B1 \
  --matrix tests/route_B_round04/fixtures/B1/known_bad_matrix.yaml \
  --validator scripts/validation/route_B_round04/validate_B1_anatomy_repair.py \
  --report "${OUT_DIR}/known_bad_matrix_report.json" \
  --source-input "${OUT_DIR}"

if [[ "${RACE_MODE}" == "1" ]]; then
  if mkdir "${WINNER_LOCK}" 2>/dev/null; then
    {
      echo "winner_attempt_tag=${ATTEMPT_TAG}"
      echo "winner_job_id=${SLURM_JOB_ID:-local}"
      echo "winner_partition=${SLURM_JOB_PARTITION:-unknown}"
      echo "winner_out_dir=${OUT_DIR}"
      echo "winner_log=${LOG_FILE}"
      echo "winner_time=${TS}"
    } > "${WINNER_LOCK}/winner.txt"
    mkdir -p "${CANONICAL_OUT}"
    cp -a "${OUT_DIR}/." "${CANONICAL_OUT}/"
  else
    echo "B1 race winner already published; leaving zero-credit loser attempt at ${OUT_DIR}"
  fi
fi
