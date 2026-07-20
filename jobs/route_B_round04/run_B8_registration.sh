#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=RouteB04B8
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
OUT_DIR="${ROUTE_B_B8_OUT:-results/route_B/round04/executors/B8}"
RUNTIME_DIR="${ROUTE_B_B8_RUNTIME:-results/route_B/runtime/round04/B8/${SLURM_JOB_ID:-local}}"
export ROUTE_B_B8_RUNTIME="${RUNTIME_DIR}"
mkdir -p logs "${OUT_DIR}" "${RUNTIME_DIR}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/RouteB04B8_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "stage=B8"
echo "python=${PYTHON}"
echo "out_dir=${OUT_DIR}"
echo "runtime_dir=${RUNTIME_DIR}"
"${PYTHON}" --version
"${PYTHON}" scripts/route_B_round04/preflight.py \
  --stage B8 \
  --contract results/route_B/round04/planning_snapshot/prompts/routes/route_B_round04_controller_contract.md \
  --out "${OUT_DIR}/preflight_receipt.json"
"${PYTHON}" scripts/training/route_B_round04/cine/B8/run_B8_registration.py \
  --manifest configs/route_B_round04/manifests/cine_train12.json \
  --b7 results/route_B/round04/executors/B7 \
  --out "${OUT_DIR}" \
  --steps "${ROUTE_B_B8_STEPS:-25000}" \
  --min-train-seconds "${ROUTE_B_B8_MIN_SECONDS:-7200}" \
  --validation-events "${ROUTE_B_B8_VALIDATION_EVENTS:-10}" \
  --formal
"${PYTHON}" scripts/validation/route_B_round04/validate_B8_registration.py \
  --strict \
  --input "${OUT_DIR}" \
  --report "${OUT_DIR}/validator_report.json" \
  --require-token ROUTE_B_ROUND04_B8_REGISTRATION_STAGE_COMPLETE
"${PYTHON}" scripts/validation/route_B_round04/run_known_bad_matrix.py \
  --stage B8 \
  --matrix tests/route_B_round04/fixtures/B8/known_bad_matrix.yaml \
  --validator scripts/validation/route_B_round04/validate_B8_registration.py \
  --report "${OUT_DIR}/known_bad_matrix_report.json" \
  --source-input "${OUT_DIR}"
