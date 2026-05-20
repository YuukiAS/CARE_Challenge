#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=MyoPS-Net_D501
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# MyoPS-Net (third_party/MyoPS-Net). Optional prepare when PREPARE=1.
#
# Environment (common):
#   FOLD / SPLITS_FILE / MYOPS_NET_DATA / MYOPS_NET_WORKDIR / PREPARE (1=run prepare_myops_net_layout.py)
#   MYOPS_NET_VARIANT / MYOPS_NET_BATCH_SIZE / MYOPS_NET_DIM / MYOPS_NET_START_EPOCH / MYOPS_NET_END_EPOCH
#   MYOPS_NET_EPOCHS — alias for MYOPS_NET_END_EPOCH (passed as --end_epoch to main.py)
#   MYOPS_NET_MAX_CASES — if set and non-zero, pass --max-cases to prepare (subset of train cases for smoke)
#   MYOPS_NET_PREP_TRAIN_REQUIRE_ALL_MODALITIES / MYOPS_NET_PREP_VAL_REQUIRE_ALL_MODALITIES — filter staged cases to C0+LGE+T2 complete cases
#   MYOPS_NET_NUM_WORKERS — DataLoader workers for training (default 4 in train.py)
#   MYOPS_NET_PATHOLOGY_SAMPLER — weighted slice sampler for scar/edema positives (default on for challenge3)
#   MYOPS_NET_SAMPLE_WEIGHT_SCAR / MYOPS_NET_SAMPLE_WEIGHT_EDEMA / MYOPS_NET_SAMPLE_WEIGHT_BOTH — sampler bonuses
#   MYOPS_NET_MODALITY_DROPOUT / MYOPS_NET_DROPOUT_C0 / MYOPS_NET_DROPOUT_T2 — drop present C0/T2 only (challenge3 defaults: 0.10/0.20)
#   MYOPS_NET_MASK_GATED_LOSS — skip C0/T2 branch and invariant losses for unavailable/effectively dropped modalities
#   MYOPS_NET_INIT_CHECKPOINT — optional state_dict checkpoint to initialize from
#   MYOPS_NET_BEST_METRIC / MYOPS_NET_BEST_WEIGHT_SCAR / MYOPS_NET_BEST_WEIGHT_EDEMA — best.pth selection
#   MYOPS_NET_MAX_RUNTIME_HOURS — training loop guard, default 7.75
#   MYOPS_NET_EXPORT_EVAL / MYOPS_NET_PRED_DIR / MYOPS_NET_EVAL_OUTPUT_DIR — optional isolated fold eval
#
# DEBUG_SMOKE=1 preset (override any of these by exporting before sbatch):
#   MYOPS_NET_END_EPOCH=3, MYOPS_NET_MAX_CASES=20, MYOPS_NET_BATCH_SIZE=4, PREPARE=1
set -euo pipefail

# Slurm may copy the batch script to a spool path; prefer the submit directory when it is the repo root.
if [[ -n "${CARE_ROOT:-}" ]]; then
  :
elif [[ -n "${SLURM_SUBMIT_DIR:-}" && -f "${SLURM_SUBMIT_DIR}/env_nnunet.sh" ]]; then
  CARE_ROOT="${SLURM_SUBMIT_DIR}"
else
  _THIS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CARE_ROOT="$(cd "${_THIS}/../.." && pwd)"
  unset _THIS
fi

cd "${CARE_ROOT}"
export PATH="${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

if [[ -n "${MYOPS_NET_EPOCHS:-}" ]]; then
  export MYOPS_NET_END_EPOCH="${MYOPS_NET_EPOCHS}"
fi

if [[ "${DEBUG_SMOKE:-0}" == "1" ]]; then
  export MYOPS_NET_END_EPOCH="${MYOPS_NET_END_EPOCH:-3}"
  export MYOPS_NET_MAX_CASES="${MYOPS_NET_MAX_CASES:-20}"
  export MYOPS_NET_BATCH_SIZE="${MYOPS_NET_BATCH_SIZE:-4}"
  export PREPARE="${PREPARE:-1}"
fi

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MyoPS-Net_${SLURM_JOB_ID:-local}_${TS}.log}"
mkdir -p "$(dirname "${LOG_FILE}")"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${CARE_ROOT}/envs/env_CARE/bin/python"
PREP="${CARE_ROOT}/code/MyoPS-Net/prepare_myops_net_layout.py"
SPLITS="${SPLITS_FILE:-${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json}"
FOLD="${FOLD:-0}"
DATA="${MYOPS_NET_DATA:-${CARE_ROOT}/data/benchmarks/MyoPS-Net/fold_${FOLD}}"
WORKDIR="${MYOPS_NET_WORKDIR:-${CARE_ROOT}/results/checkpoints/MyoPS-Net/fold_${FOLD}}"

export MYOPS_NET_DATA="${DATA}"
export MYOPS_NET_WORKDIR="${WORKDIR}"

echo "===== MyoPS-Net train (data=${DATA}, workdir=${WORKDIR}, fold=${FOLD}) ====="
echo "DEBUG_SMOKE=${DEBUG_SMOKE:-0} PREPARE=${PREPARE:-1} MYOPS_NET_END_EPOCH=${MYOPS_NET_END_EPOCH:-} MYOPS_NET_MAX_CASES=${MYOPS_NET_MAX_CASES:-unset} MYOPS_NET_BATCH_SIZE=${MYOPS_NET_BATCH_SIZE:-16}"
echo "MYOPS_NET_VARIANT=${MYOPS_NET_VARIANT:-challenge3} MYOPS_NET_PATHOLOGY_SAMPLER=${MYOPS_NET_PATHOLOGY_SAMPLER:-auto} MYOPS_NET_SAMPLE_WEIGHT_SCAR=${MYOPS_NET_SAMPLE_WEIGHT_SCAR:-2.0} MYOPS_NET_SAMPLE_WEIGHT_EDEMA=${MYOPS_NET_SAMPLE_WEIGHT_EDEMA:-6.0} MYOPS_NET_SAMPLE_WEIGHT_BOTH=${MYOPS_NET_SAMPLE_WEIGHT_BOTH:-2.0}"
echo "MYOPS_NET_MODALITY_DROPOUT=${MYOPS_NET_MODALITY_DROPOUT:-auto} MYOPS_NET_DROPOUT_C0=${MYOPS_NET_DROPOUT_C0:-0.10} MYOPS_NET_DROPOUT_T2=${MYOPS_NET_DROPOUT_T2:-0.20} MYOPS_NET_MASK_GATED_LOSS=${MYOPS_NET_MASK_GATED_LOSS:-0} MYOPS_NET_MAX_RUNTIME_HOURS=${MYOPS_NET_MAX_RUNTIME_HOURS:-7.75} MYOPS_NET_EARLY_STOP_PATIENCE=${MYOPS_NET_EARLY_STOP_PATIENCE:-20}"
echo "MYOPS_NET_INIT_CHECKPOINT=${MYOPS_NET_INIT_CHECKPOINT:-none} MYOPS_NET_BEST_METRIC=${MYOPS_NET_BEST_METRIC:-avg_pathology} MYOPS_NET_BEST_WEIGHT_SCAR=${MYOPS_NET_BEST_WEIGHT_SCAR:-1.0} MYOPS_NET_BEST_WEIGHT_EDEMA=${MYOPS_NET_BEST_WEIGHT_EDEMA:-1.0} MYOPS_NET_PREP_TRAIN_REQUIRE_ALL_MODALITIES=${MYOPS_NET_PREP_TRAIN_REQUIRE_ALL_MODALITIES:-0} MYOPS_NET_PREP_VAL_REQUIRE_ALL_MODALITIES=${MYOPS_NET_PREP_VAL_REQUIRE_ALL_MODALITIES:-0}"

if [[ "${PREPARE:-1}" == "1" ]]; then
  prep_cmd=( "${PY}" "${PREP}" --splits-file "${SPLITS}" --fold "${FOLD}" --output "${DATA}" )
  if [[ -n "${MYOPS_NET_MAX_CASES:-}" ]] && [[ "${MYOPS_NET_MAX_CASES}" != "0" ]]; then
    prep_cmd+=( --max-cases "${MYOPS_NET_MAX_CASES}" )
  fi
  if [[ "${MYOPS_NET_PREP_TRAIN_REQUIRE_ALL_MODALITIES:-0}" =~ ^(1|true|TRUE|yes|YES|on|ON)$ ]]; then
    prep_cmd+=( --train-require-all-modalities )
  fi
  if [[ "${MYOPS_NET_PREP_VAL_REQUIRE_ALL_MODALITIES:-0}" =~ ^(1|true|TRUE|yes|YES|on|ON)$ ]]; then
    prep_cmd+=( --val-require-all-modalities )
  fi
  "${prep_cmd[@]}"
fi

bash "${CARE_ROOT}/code/MyoPS-Net/run_train.sh" "$@"
echo "===== MyoPS-Net training loop finished ====="

if [[ "${MYOPS_NET_EXPORT_EVAL:-0}" == "1" ]]; then
  echo "===== MyoPS-Net export val predictions + unified eval (fold ${FOLD}) ====="
  PRED_DIR="${MYOPS_NET_PRED_DIR:-${CARE_ROOT}/results/predictions/MyoPS-Net/fold_${FOLD}}"
  MET_DIR="${MYOPS_NET_EVAL_OUTPUT_DIR:-${CARE_ROOT}/results/metrics/unified/MyoPS-Net/fold_${FOLD}}"
  mkdir -p "${PRED_DIR}" "${MET_DIR}"
  rm -f "${PRED_DIR}"/*.nii.gz
  "${PY}" "${CARE_ROOT}/code/MyoPS-Net/export_val_predictions.py" \
    --data-root "${DATA}" \
    --output-dir "${PRED_DIR}" \
    --checkpoint-dir "${WORKDIR}/checkpoints" \
    --variant "${MYOPS_NET_VARIANT:-challenge3}"
  eval_cmd=(
    "${PY}" "${CARE_ROOT}/scripts/evaluation/evaluate_predictions.py"
    --pred-dir "${PRED_DIR}"
    --gt-dir "${nnUNet_raw}/Dataset501_CAREMyoPS/labelsTr"
    --fold-json "${SPLITS}"
    --fold "${FOLD}"
    --foreground-classes 4,5
    --skip-dice-if-gt-empty
    --output-dir "${MET_DIR}"
  )
  if [[ "${MYOPS_NET_EVAL_HD:-0}" == "1" ]]; then
    eval_cmd+=( --hd )
  fi
  "${eval_cmd[@]}"
  "${PY}" "${CARE_ROOT}/code/MyoPS-Net/report_modality_groups.py" \
    --evaluation-summary "${MET_DIR}/evaluation_summary.json" \
    --fold-json "${SPLITS}" \
    --fold "${FOLD}" \
    --data-root "${DATA}" \
    --output-json "${MET_DIR}/modality_group_metrics.json" \
    --output-md "${MET_DIR}/modality_group_metrics.md"
  "${PY}" "${CARE_ROOT}/scripts/evaluation/aggregate_folds.py" \
    --inputs "${MET_DIR}/evaluation_summary.json" \
    --output-json "$(dirname "${MET_DIR}")/aggregate.json" \
    --output-md "$(dirname "${MET_DIR}")/aggregate.md"
  echo "===== MyoPS-Net export/eval finished (metrics under ${MET_DIR}) ====="
fi

echo "===== MyoPS-Net done ====="
