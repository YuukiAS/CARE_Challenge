#!/bin/bash
# Round6 CineMyoPS fixed-inference combine-mode ablations. No training.
# Submit from repo root:
#   sbatch jobs/CineMyoPS/sbatch_round6_fixed_inference_modes.sh
# This intentionally reuses the fixed Task026 inference path and writes
# unique R6 prediction/metric directories for cache isolation.
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CineMyoPS_r6_modes
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

if [[ -z "${CARE_ROOT:-}" ]]; then
  if [[ -n "${SLURM_SUBMIT_DIR:-}" && -f "${SLURM_SUBMIT_DIR}/env_nnunet.sh" ]]; then
    CARE_ROOT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
  else
    THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CARE_ROOT="$(cd "${THIS_DIR}/../.." && pwd)"
  fi
fi
export CARE_ROOT
cd "${CARE_ROOT}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/envs/env_CARE_nnUNet_v1}}"
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
export CARE_CineMyoPS_ENV
export PYTHONUNBUFFERED=1
export MPLCONFIGDIR="${TMPDIR:-/tmp}/matplotlib-${SLURM_JOB_ID:-local}"

export FOLD="${FOLD:-0}"
export CINE_NNUNET_TASK="${CINE_NNUNET_TASK:-Task026_Cine_4D}"
export CINE_NNUNET_TRAINER="${CINE_NNUNET_TRAINER:-CARECineMyoPSTrainerBNCalib}"
export CINE_NNUNET_DIM="${CINE_NNUNET_DIM:-2d}"
export CINE_PRED_CHECKPOINT="${CINE_PRED_CHECKPOINT:-model_final_checkpoint}"
export CINE_BN_RECALIBRATE="${CINE_BN_RECALIBRATE:-1}"
export CINE_BN_RECALIB_BATCHES="${CINE_BN_RECALIB_BATCHES:-32}"
export CINE_INFERENCE_TRAIN_MODE="${CINE_INFERENCE_TRAIN_MODE:-0}"
export CINE_PROTOCOL_SPLIT_JSON="${CINE_PROTOCOL_SPLIT_JSON:-${CARE_ROOT}/data/benchmarks/protocol/splits_CineMyoPS.json}"

mkdir -p "${CARE_ROOT}/logs" "${CARE_ROOT}/results/metrics/unified"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CineMyoPS_r6_modes_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "===== CineMyoPS round6 fixed-inference combine-mode ablation ====="
echo "host=$(hostname) SLURM_JOB_ID=${SLURM_JOB_ID:-na}"
echo "CARE_ROOT=$(readlink -f "${CARE_ROOT}")"
echo "LOG_FILE=$(readlink -f "${LOG_FILE}")"
echo "FOLD=${FOLD} TASK=${CINE_NNUNET_TASK} TRAINER=${CINE_NNUNET_TRAINER} CHECKPOINT=${CINE_PRED_CHECKPOINT}"
echo "CINE_INFERENCE_TRAIN_MODE=${CINE_INFERENCE_TRAIN_MODE} CINE_BN_RECALIBRATE=${CINE_BN_RECALIBRATE} CINE_BN_RECALIB_BATCHES=${CINE_BN_RECALIB_BATCHES}"

PY_EVAL="${CARE_EVAL_PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"

run_mode() {
  local mode="$1"
  local output_model="$2"
  export CINE_COMBINE_MODE="${mode}"
  export CINE_OUTPUT_MODEL="${output_model}"
  echo ""
  echo "===== mode=${CINE_COMBINE_MODE} output_model=${CINE_OUTPUT_MODEL} ====="
  bash "${CARE_ROOT}/code/CineMyoPS/export_protocol_val_predictions.sh"
  local eval_json="${CARE_ROOT}/results/metrics/unified/${CINE_OUTPUT_MODEL}/fold_${FOLD}/evaluation_summary.json"
  "${PY_EVAL}" "${CARE_ROOT}/scripts/evaluation/evaluate_predictions.py" \
    --pred-dir "${CARE_ROOT}/results/predictions/${CINE_OUTPUT_MODEL}/fold_${FOLD}" \
    --gt-dir "${nnUNet_raw}/Dataset502_CARECineMyoPS/labelsTr" \
    --fold-json "${CINE_PROTOCOL_SPLIT_JSON}" \
    --fold "${FOLD}" \
    --foreground-classes "1,2,3" \
    --output-dir "${CARE_ROOT}/results/metrics/unified/${CINE_OUTPUT_MODEL}/fold_${FOLD}"
  "${PY_EVAL}" "${CARE_ROOT}/scripts/evaluation/aggregate_folds.py" \
    --inputs "${eval_json}" \
    --output-json "${CARE_ROOT}/results/metrics/unified/${CINE_OUTPUT_MODEL}/aggregate.json" \
    --output-md "${CARE_ROOT}/results/metrics/unified/${CINE_OUTPUT_MODEL}/aggregate.md"
  echo "===== mode done: ${mode}; eval=${eval_json} ====="
}

run_mode current CineMyoPS_R6_current
run_mode cardiac_only CineMyoPS_R6_cardiac_only
run_mode myocardium_gated_scar CineMyoPS_R6_myo_gated_scar
run_mode pathology_direct CineMyoPS_R6_pathology_direct

echo "===== all round6 fixed-inference modes done ====="
