#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareB9Stage
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
mkdir -p "logs/${CARE_MM_TASK_KEY}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/${CARE_MM_TASK_KEY}/Batch9Stage_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "care_root=${CARE_ROOT}"
echo "python_executable=${PYTHON}"
"${PYTHON}" --version
"${PYTHON}" - <<'PY'
import torch
from dynamic_network_architectures.architectures.unet import ResidualEncoderUNet
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
print("cuda_device_count", torch.cuda.device_count())
print("ResidualEncoderUNet", ResidualEncoderUNet)
PY

: "${BATCH9_VARIANT:?BATCH9_VARIANT is required}"
: "${BATCH9_SEED:?BATCH9_SEED is required}"
: "${BATCH9_EPOCHS:?BATCH9_EPOCHS is required}"
: "${BATCH9_TOTAL_STEPS:?BATCH9_TOTAL_STEPS is required}"
: "${BATCH9_RUNTIME_ROOT:?BATCH9_RUNTIME_ROOT is required}"

ARGS=(
  scripts/training/run_care_mm_batch9_reliable_distill.py
  train-stage
  --variant "${BATCH9_VARIANT}"
  --seed "${BATCH9_SEED}"
  --epochs "${BATCH9_EPOCHS}"
  --total-steps "${BATCH9_TOTAL_STEPS}"
  --steps-per-epoch "${BATCH9_STEPS_PER_EPOCH:-250}"
  --batch-size "${BATCH9_BATCH_SIZE:-1}"
  --lr "${BATCH9_LR:-0.01}"
  --device cuda
  --validation-interval-epochs "${BATCH9_VALIDATION_INTERVAL_EPOCHS:-25}"
  --runtime-root "${BATCH9_RUNTIME_ROOT}"
)

if [[ -n "${BATCH9_WARM_START:-}" ]]; then
  ARGS+=(--warm-start "${BATCH9_WARM_START}")
fi
if [[ -n "${BATCH9_TEACHER_CHECKPOINT:-}" ]]; then
  ARGS+=(--teacher-checkpoint "${BATCH9_TEACHER_CHECKPOINT}")
fi
if [[ -n "${BATCH9_MAX_RUNTIME_SECONDS:-}" ]]; then
  ARGS+=(--max-runtime-seconds "${BATCH9_MAX_RUNTIME_SECONDS}")
fi

"${PYTHON}" "${ARGS[@]}"
