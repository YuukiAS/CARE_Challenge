#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareB9Final
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
PYTHON="${PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
TASK_ROOT="results/20260722_care_myops_batch9_reliable_label_distillation"
cd "${CARE_ROOT}"

mkdir -p logs/care_myops_batch9_reliable_label_distillation/finalizer
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_batch9_reliable_label_distillation/finalizer/Batch9Final_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "care_root=${CARE_ROOT}"
echo "python_executable=${PYTHON}"
"${PYTHON}" --version

for seed in 20260723 20260724; do
  for variant in student_direct_reliable teacher_full_view student_moddrop_control student_reliable_distill; do
    case "${variant}" in
      student_direct_reliable) epoch=500 ;;
      *) epoch=100 ;;
    esac
    ckpt="${TASK_ROOT}/runtime/seed${seed}/${variant}/checkpoint_epoch${epoch}.pt"
    pred="${TASK_ROOT}/runtime/seed${seed}/${variant}/predictions"
    prefix="seed${seed}_${variant}"
    "${PYTHON}" scripts/evaluation/evaluate_care_mm_batch9.py \
      --variant "${variant}" \
      --seed "${seed}" \
      --checkpoint "${ckpt}" \
      --prediction-dir "${pred}" \
      --output-dir "${TASK_ROOT}" \
      --prefix "${prefix}" \
      --device cuda
  done
done

"${PYTHON}" scripts/evaluation/aggregate_care_mm_batch9.py
"${PYTHON}" scripts/evaluation/finalize_care_mm_batch9.py
