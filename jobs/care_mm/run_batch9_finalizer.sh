#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareB9Final
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
PYTHON="${PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
cd "${CARE_ROOT}"

export CARE_MM_TASK_KEY="${CARE_MM_TASK_KEY:-20260723_care_myops_batch9_exposed_issues_repair}"
export CARE_MM_CONFIG_PATH="${CARE_MM_CONFIG_PATH:-configs/care_mm/batch9_exposed_issues_repair.yaml}"
TASK_ROOT="results/${CARE_MM_TASK_KEY}"
mkdir -p "logs/${CARE_MM_TASK_KEY}"/finalizer
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/${CARE_MM_TASK_KEY}/finalizer/Batch9Final_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "care_root=${CARE_ROOT}"
echo "python_executable=${PYTHON}"
"${PYTHON}" --version

echo "finalizer_mode=${BATCH9_FINALIZER_DIRECT_ONLY:-0}"
echo "task_root=${TASK_ROOT}"
# Formal selected-checkpoint evaluation is executed by nnUNetTrainerCAREMMReliableDistill
# every 25 epochs. The finalizer aggregates those runtime-derived CSVs only.

"${PYTHON}" scripts/evaluation/aggregate_care_mm_batch9.py
"${PYTHON}" scripts/evaluation/finalize_care_mm_batch9.py
