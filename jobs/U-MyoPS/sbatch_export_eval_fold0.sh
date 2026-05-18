#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=U-MyoPS-ExportEval
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# Stage2 pathology: nnUNet test-time inference (GPU) + remap + unified Dice vs Dataset501 labels (fold 0).
# Env (defaults shown):
#   UMYOPS_EXPORT_TRAINER=nnUNetTrainerPSNV8
#   UMYOPS_EXPORT_CHECKPOINT=model_final_checkpoint|model_best
#   UMYOPS_EXPORT_FORCE_FALLBACK=1
#   CARE_CineMyoPS_ENV, CARE_ROOT (via SLURM_SUBMIT_DIR)
set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"

if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  CARE_ROOT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
  THIS_DIR="${CARE_ROOT}/jobs/U-MyoPS"
else
  THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
fi
export CARE_ROOT
cd "${CARE_ROOT}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
export CARE_CineMyoPS_ENV
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
export LEGACY_PYTHON="${LEGACY_PYTHON:-${CARE_CineMyoPS_ENV}/bin/python}"

mkdir -p logs results/experiments
if [[ -z "${LOG_FILE:-}" ]]; then
  TS="$(date +%Y%m%d_%H%M%S)"
  LOG_FILE="${CARE_ROOT}/logs/U-MyoPS_ExportEval_${SLURM_JOB_ID:-local}_${TS}.log"
fi
exec > >(tee -a "${LOG_FILE}") 2>&1

TRAINER="${UMYOPS_EXPORT_TRAINER:-${UMYOPS_STAGE2_TRAINER:-nnUNetTrainerPSNV8}}"
CHK="${UMYOPS_EXPORT_CHECKPOINT:-model_final_checkpoint}"
BASE_TASK="${UMYOPS_EXPORT_TASK:-${UMYOPS_STAGE2_TASK:-Task901_CARE_UmyopsPathology}}"
export UMYOPS_EXPORT_FORCE_FALLBACK="${UMYOPS_EXPORT_FORCE_FALLBACK:-1}"
TRAINER_TAG="$(echo "${TRAINER}" | sed 's/[^A-Za-z0-9_-]/_/g')"
CHK_TAG="$(echo "${CHK}" | sed 's/[^A-Za-z0-9_-]/_/g')"
TAG="${UMYOPS_EXPORT_TAG:-${TRAINER_TAG}_${CHK_TAG}}"
PRED_DIR="${CARE_ROOT}/results/predictions/U-MyoPS_${TAG}/fold_0"
OUT_DIR="${CARE_ROOT}/results/metrics/unified/U-MyoPS_${TAG}/fold_0"
AGG_ROOT="${CARE_ROOT}/results/metrics/unified/U-MyoPS_${TAG}"
GT_DIR="${nnUNet_raw}/Dataset501_CAREMyoPS/labelsTr"
SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json"
PY="${CARE_EVAL_PYTHON:-${CARE_ROOT}/env_CARE/bin/python}"

echo "===== U-MyoPS export+eval fold0 task=${BASE_TASK} trainer=${TRAINER} chk=${CHK} tag=${TAG} force_fallback=${UMYOPS_EXPORT_FORCE_FALLBACK} ====="
echo "PRED_DIR=${PRED_DIR} OUT_DIR=${OUT_DIR}"
rm -rf "${PRED_DIR}"
mkdir -p "${PRED_DIR}" "${OUT_DIR}"

"${PY}" "${CARE_ROOT}/code/U-MyoPS/export_stage2_val_predictions.py" \
  --fold 0 \
  --base-task-name "${BASE_TASK}" \
  --per-fold-task \
  --trainer "${TRAINER}" \
  --checkpoint "${CHK}" \
  --output-dir "${PRED_DIR}" \
  --force-fallback

"${PY}" "${CARE_ROOT}/scripts/evaluation/evaluate_predictions.py" \
  --pred-dir "${PRED_DIR}" \
  --gt-dir "${GT_DIR}" \
  --fold-json "${SPLIT_JSON}" \
  --fold 0 \
  --foreground-classes 4,5 \
  --output-dir "${OUT_DIR}"

"${PY}" "${CARE_ROOT}/scripts/evaluation/report_umyops_round2.py" \
  --checkpoint-tag "${TAG}"

"${PY}" "${CARE_ROOT}/scripts/evaluation/aggregate_folds.py" \
  --inputs "${OUT_DIR}/evaluation_summary.json" \
  --output-json "${AGG_ROOT}/aggregate.json" \
  --output-md "${AGG_ROOT}/aggregate.md"

echo "===== done | metrics -> ${OUT_DIR}/evaluation_summary.json ====="
