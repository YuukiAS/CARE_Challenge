#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CineMAAdapter
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
cd "${CARE_ROOT}"

mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CineMAAdapter_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "HOST=$(hostname)"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
echo "CARE_ROOT=${CARE_ROOT}"

PYTHONPATH="${CARE_ROOT}/results/cinema_adapter/python_deps:${CARE_ROOT}/results/cinema_adapter/external/CineMA:${PYTHONPATH:-}" \
  "${CARE_ROOT}/envs/env_CARE/bin/python" "${CARE_ROOT}/scripts/external_adapters/cinema_care_adapter.py" \
    --output-dir "${OUTPUT_DIR:-${CARE_ROOT}/results/cinema_adapter/${TS}__cinema_acdc_seed0_ed_mid_repr}" \
    --cinema-repo "${CARE_ROOT}/results/cinema_adapter/external/CineMA" \
    --max-train-cases "${MAX_TRAIN_CASES:-64}" \
    --max-val-cases "${MAX_VAL_CASES:-15}" \
    --frame-strategy "${FRAME_STRATEGY:-ed_middle_representative}" \
    --trained-dataset "${TRAINED_DATASET:-acdc}" \
    --seed "${SEED:-0}" \
    --device "${DEVICE:-cuda}"
