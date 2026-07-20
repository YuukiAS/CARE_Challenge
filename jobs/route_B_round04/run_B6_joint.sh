#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=RouteB04B6
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
OUT_DIR="${ROUTE_B_B6_OUT:-results/route_B/round04/executors/B6}"
RUNTIME_DIR="${ROUTE_B_B6_RUNTIME:-results/route_B/runtime/round04/B6/${SLURM_JOB_ID:-local}}"
export ROUTE_B_B6_RUNTIME="${RUNTIME_DIR}"
mkdir -p logs "${OUT_DIR}" "${RUNTIME_DIR}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/RouteB04B6_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "stage=B6"
echo "python=${PYTHON}"
echo "out_dir=${OUT_DIR}"
echo "runtime_dir=${RUNTIME_DIR}"
"${PYTHON}" --version
"${PYTHON}" scripts/route_B_round04/preflight.py \
  --stage B6 \
  --contract results/route_B/round04/planning_snapshot/prompts/routes/route_B_round04_controller_contract.md \
  --out "${OUT_DIR}/preflight_receipt.json"
"${PYTHON}" scripts/training/route_B_round04/myops/B6/run_B6_joint.py \
  --manifest configs/route_B_round04/manifests/myops_fold0_primary_44.json \
  --b5 results/route_B/round04/executors/B5 \
  --b0 results/route_B/round04/executors/B0 \
  --out "${OUT_DIR}" \
  --steps "${ROUTE_B_B6_STEPS:-8000}" \
  --min-train-seconds "${ROUTE_B_B6_MIN_SECONDS:-2400}" \
  --validation-events "${ROUTE_B_B6_VALIDATION_EVENTS:-4}" \
  --formal
"${PYTHON}" scripts/validation/route_B_round04/validate_B6_myops_terminal.py \
  --strict \
  --input "${OUT_DIR}" \
  --report "${OUT_DIR}/validator_report.json" \
  --require-token ROUTE_B_ROUND04_B6_MYOPS_TERMINAL_EVIDENCE_READY
"${PYTHON}" scripts/validation/route_B_round04/run_known_bad_matrix.py \
  --stage B6 \
  --matrix tests/route_B_round04/fixtures/B6/known_bad_matrix.yaml \
  --validator scripts/validation/route_B_round04/validate_B6_myops_terminal.py \
  --report "${OUT_DIR}/known_bad_matrix_report.json" \
  --source-input "${OUT_DIR}"
