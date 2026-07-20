#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=RB10Final
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail
CARE_ROOT="/users/a/e/aereinh/CARE_worktrees/route_B"
MAIN_CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
mkdir -p logs/route_B_round03
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/route_B_round03/RouteBFinalizer_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
source "${MAIN_CARE_ROOT}/.care-codex-env.sh"
source "${MAIN_CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${MAIN_CARE_ROOT}/envs/env_CARE/bin:${PATH}"
CARE_PYTHON="${MAIN_CARE_ROOT}/envs/env_CARE/bin/python"
"${CARE_PYTHON}" scripts/route_B_round03/preflight.py --executor B10 --partition "${SLURM_JOB_PARTITION:-htzhulab}" --config configs/route_B_round03/formal.yaml --out results/route_B/round03/executors/B10/preflight_${SLURM_JOB_PARTITION:-htzhulab}.json
"${CARE_PYTHON}" scripts/route_B_round03/aggregate_packet.py --strict --include-all-started-attempts --allow-terminal-adequate-negative --allow-early-gate-failure --validator-command "${CARE_PYTHON} scripts/validation/route_B_round03/validate_packet.py --strict --require-all-attempt-accounting results/route_B"
"${CARE_PYTHON}" scripts/validation/route_B_round03/validate_packet.py --strict --require-all-attempt-accounting results/route_B
git diff --check
