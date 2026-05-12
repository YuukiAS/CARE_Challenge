#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=UnifiedEval
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=1-00:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# Slurm entry: unified offline eval (GPU). Invoked by jobs/run_unified_benchmark_*.sh (post/eval).
# Implementation: scripts/evaluation/run_unified_eval_all.sh
# Env from submitter: MODELS, FOLDS, optional CARE_ROOT.
set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
cd "${CARE_ROOT}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

export PYTHONUNBUFFERED=1

mkdir -p "${CARE_ROOT}/logs"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/UnifiedEval_${SLURM_JOB_ID:-local}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "===== Unified eval (GPU): MODELS=${MODELS:-} FOLDS=${FOLDS:-} ====="
echo "LOG_FILE=${LOG_FILE}"
echo "CARE_EVAL_PYTHON=${CARE_EVAL_PYTHON:-}"

bash "${CARE_ROOT}/scripts/evaluation/run_unified_eval_all.sh"
echo "===== Unified eval done ====="
