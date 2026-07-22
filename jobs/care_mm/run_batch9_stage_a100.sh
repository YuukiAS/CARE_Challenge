#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareB9A100
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
PYTHON="${PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
cd "${CARE_ROOT}"

mkdir -p logs/care_myops_batch9_reliable_label_distillation
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_batch9_reliable_label_distillation/Batch9A100_${SLURM_JOB_ID:-local}_${TS}.log}"
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
  --patch-size ${BATCH9_PATCH_SIZE:-20 128 128}
  --lr "${BATCH9_LR:-0.01}"
  --device cuda
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
