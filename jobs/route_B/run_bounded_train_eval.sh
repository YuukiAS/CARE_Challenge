#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=RouteBTrainEval
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE_worktrees/route_B}"
cd "${CARE_ROOT}"

mkdir -p logs/route_B
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/route_B/RouteBTrainEval_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export PYTHONUNBUFFERED=1
python scripts/training/route_B/run_bounded_train_eval.py --steps "${ROUTE_B_STEPS:-500}" --myops-eval-cases 10 --cine-eval-cases 5
