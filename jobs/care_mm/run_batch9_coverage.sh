#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareB9Cov
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
PYTHON="${PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
cd "${CARE_ROOT}"

export CARE_MM_TASK_KEY="${CARE_MM_TASK_KEY:-20260723_care_myops_batch9_exposed_issues_repair}"
export CARE_MM_CONFIG_PATH="${CARE_MM_CONFIG_PATH:-configs/care_mm/batch9_exposed_issues_repair.yaml}"
mkdir -p "logs/${CARE_MM_TASK_KEY}/coverage"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/${CARE_MM_TASK_KEY}/coverage/Batch9Cov_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

: "${BATCH9_SEED:?BATCH9_SEED is required}"
: "${BATCH9_TEACHER_CHECKPOINT:?BATCH9_TEACHER_CHECKPOINT is required}"

echo "care_root=${CARE_ROOT}"
echo "python_executable=${PYTHON}"
"${PYTHON}" --version
"${PYTHON}" scripts/training/run_care_mm_batch9_reliable_distill.py distillation-coverage   --seed "${BATCH9_SEED}"   --teacher-checkpoint "${BATCH9_TEACHER_CHECKPOINT}"   --device cuda
