#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareB9Pre
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

mkdir -p logs/care_myops_batch9_reliable_label_distillation/preflight
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_batch9_reliable_label_distillation/preflight/Batch9Pre_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "care_root=${CARE_ROOT}"
echo "python_executable=${PYTHON}"
"${PYTHON}" --version
"${PYTHON}" scripts/training/run_care_mm_batch9_reliable_distill.py print-contract \
  --variant student_direct_reliable \
  --seed 20260723 \
  --epochs 500 \
  --total-steps 125000
"${PYTHON}" scripts/training/run_care_mm_batch9_reliable_distill.py fixed-overfit --device cuda
