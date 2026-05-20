#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=MyoPSR8HD
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

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

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MyoPS-Net_Round8HD_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${CARE_ROOT}/envs/env_CARE/bin/python"
FOLD="${FOLD:-0}"
SPLITS="${SPLITS_FILE:-${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json}"
DATA="${MYOPS_NET_DATA:-${CARE_ROOT}/data/benchmarks/MyoPS-Net/fold_${FOLD}_round8_t2aware_hd}"
WORKDIR="${MYOPS_NET_WORKDIR:-${CARE_ROOT}/results/checkpoints/MyoPS-Net_round8_t2aware_hd/fold_${FOLD}}"
RAW_PRED="${CARE_ROOT}/results/predictions/MyoPS-Net_round8_t2aware_hd_raw/fold_${FOLD}"
RAW_MET="${CARE_ROOT}/results/metrics/unified/MyoPS-Net_round8_t2aware_hd_raw/fold_${FOLD}"
HYB_PRED="${CARE_ROOT}/results/predictions/MyoPS-Net_round8_t2aware_hd_round4scar_hybrid/fold_${FOLD}"
HYB_MET="${CARE_ROOT}/results/metrics/unified/MyoPS-Net_round8_t2aware_hd_round4scar_hybrid/fold_${FOLD}"
ROUND4="${CARE_ROOT}/results/predictions/MyoPS-Net_round4_combined_safe/fold_${FOLD}"

echo "[round8] log=${LOG_FILE}"
echo "[round8] data=${DATA}"
echo "[round8] workdir=${WORKDIR}"

export FOLD
export SPLITS_FILE="${SPLITS}"
export MYOPS_NET_DATA="${DATA}"
export MYOPS_NET_WORKDIR="${WORKDIR}"
export PREPARE="${PREPARE:-1}"
export MYOPS_NET_PREP_TRAIN_REQUIRE_ALL_MODALITIES="${MYOPS_NET_PREP_TRAIN_REQUIRE_ALL_MODALITIES:-1}"
export MYOPS_NET_PREP_VAL_REQUIRE_ALL_MODALITIES="${MYOPS_NET_PREP_VAL_REQUIRE_ALL_MODALITIES:-0}"
export MYOPS_NET_VARIANT="${MYOPS_NET_VARIANT:-challenge3}"
export MYOPS_NET_END_EPOCH="${MYOPS_NET_END_EPOCH:-80}"
export MYOPS_NET_BATCH_SIZE="${MYOPS_NET_BATCH_SIZE:-12}"
export MYOPS_NET_MAX_RUNTIME_HOURS="${MYOPS_NET_MAX_RUNTIME_HOURS:-7.5}"
export MYOPS_NET_EARLY_STOP_PATIENCE="${MYOPS_NET_EARLY_STOP_PATIENCE:-12}"
export MYOPS_NET_MASK_GATED_LOSS="${MYOPS_NET_MASK_GATED_LOSS:-1}"
export MYOPS_NET_MODALITY_DROPOUT="${MYOPS_NET_MODALITY_DROPOUT:-0}"
export MYOPS_NET_PATHOLOGY_SAMPLER="${MYOPS_NET_PATHOLOGY_SAMPLER:-1}"
export MYOPS_NET_SAMPLE_WEIGHT_SCAR="${MYOPS_NET_SAMPLE_WEIGHT_SCAR:-3.0}"
export MYOPS_NET_SAMPLE_WEIGHT_EDEMA="${MYOPS_NET_SAMPLE_WEIGHT_EDEMA:-10.0}"
export MYOPS_NET_SAMPLE_WEIGHT_BOTH="${MYOPS_NET_SAMPLE_WEIGHT_BOTH:-4.0}"
export MYOPS_NET_LOSS_WEIGHT_SCAR="${MYOPS_NET_LOSS_WEIGHT_SCAR:-2.0}"
export MYOPS_NET_LOSS_WEIGHT_EDEMA="${MYOPS_NET_LOSS_WEIGHT_EDEMA:-3.0}"
export MYOPS_NET_FOCAL_TVERSKY_WEIGHT="${MYOPS_NET_FOCAL_TVERSKY_WEIGHT:-0.6}"
export MYOPS_NET_BOUNDARY_WEIGHT="${MYOPS_NET_BOUNDARY_WEIGHT:-0.15}"
export MYOPS_NET_ROI_WEIGHT="${MYOPS_NET_ROI_WEIGHT:-0.08}"
export MYOPS_NET_ROI_DILATION="${MYOPS_NET_ROI_DILATION:-3}"
export MYOPS_NET_BEST_METRIC="${MYOPS_NET_BEST_METRIC:-weighted_pathology}"
export MYOPS_NET_BEST_WEIGHT_SCAR="${MYOPS_NET_BEST_WEIGHT_SCAR:-1.0}"
export MYOPS_NET_BEST_WEIGHT_EDEMA="${MYOPS_NET_BEST_WEIGHT_EDEMA:-2.0}"

bash "${CARE_ROOT}/jobs/MyoPS-Net/sbatch.sh"

mkdir -p "${RAW_PRED}" "${RAW_MET}" "${HYB_PRED}" "${HYB_MET}"
rm -f "${RAW_PRED}"/*.nii.gz "${HYB_PRED}"/*.nii.gz

"${PY}" "${CARE_ROOT}/code/MyoPS-Net/export_val_predictions.py" \
  --data-root "${DATA}" \
  --output-dir "${RAW_PRED}" \
  --checkpoint-dir "${WORKDIR}/checkpoints" \
  --variant "${MYOPS_NET_VARIANT}" \
  --edema-softmax-dir "${CARE_ROOT}/results/predictions/MyoPS-Net_round8_t2aware_hd_edema_softmax/fold_${FOLD}"

"${PY}" "${CARE_ROOT}/scripts/evaluation/evaluate_predictions.py" \
  --pred-dir "${RAW_PRED}" \
  --gt-dir "${nnUNet_raw}/Dataset501_CAREMyoPS/labelsTr" \
  --fold-json "${SPLITS}" \
  --fold "${FOLD}" \
  --foreground-classes 4,5 \
  --skip-dice-if-gt-empty \
  --hd \
  --hd95 \
  --output-dir "${RAW_MET}"

"${PY}" "${CARE_ROOT}/code/MyoPS-Net/report_modality_groups.py" \
  --evaluation-summary "${RAW_MET}/evaluation_summary.json" \
  --fold-json "${SPLITS}" \
  --fold "${FOLD}" \
  --data-root "${DATA}" \
  --output-json "${RAW_MET}/modality_group_metrics.json" \
  --output-md "${RAW_MET}/modality_group_metrics.md"

"${PY}" "${CARE_ROOT}/code/MyoPS-Net/apply_round7_edema_calibration.py" \
  --round4-pred-dir "${ROUND4}" \
  --round5-pred-dir "${RAW_PRED}" \
  --output-dir "${HYB_PRED}" \
  --data-root "${DATA}" \
  --fold-json "${SPLITS}" \
  --fold "${FOLD}" \
  --variant keep_round4_scar_round5_edema_complete \
  --summary-json "${HYB_MET}/hybrid_summary.json" \
  --summary-md "${HYB_MET}/hybrid_summary.md"

"${PY}" "${CARE_ROOT}/scripts/evaluation/evaluate_predictions.py" \
  --pred-dir "${HYB_PRED}" \
  --gt-dir "${nnUNet_raw}/Dataset501_CAREMyoPS/labelsTr" \
  --fold-json "${SPLITS}" \
  --fold "${FOLD}" \
  --foreground-classes 4,5 \
  --skip-dice-if-gt-empty \
  --hd \
  --hd95 \
  --output-dir "${HYB_MET}"

"${PY}" "${CARE_ROOT}/code/MyoPS-Net/report_modality_groups.py" \
  --evaluation-summary "${HYB_MET}/evaluation_summary.json" \
  --fold-json "${SPLITS}" \
  --fold "${FOLD}" \
  --data-root "${DATA}" \
  --output-json "${HYB_MET}/modality_group_metrics.json" \
  --output-md "${HYB_MET}/modality_group_metrics.md"

for met in "${RAW_MET}" "${HYB_MET}"; do
  "${PY}" "${CARE_ROOT}/scripts/evaluation/aggregate_folds.py" \
    --inputs "${met}/evaluation_summary.json" \
    --output-json "$(dirname "${met}")/aggregate.json" \
    --output-md "$(dirname "${met}")/aggregate.md"
done

echo "[round8] done"
