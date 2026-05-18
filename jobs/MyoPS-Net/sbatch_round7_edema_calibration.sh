#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=MyoPSR7Cal
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
cd "${CARE_ROOT}"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MyoPS-Net_Round7Cal_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${CARE_ROOT}/env_CARE/bin/python"
DATA_ROOT="${CARE_ROOT}/data/benchmarks/MyoPS-Net/fold_0_maskgated_round3"
FOLD_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json"
GT_DIR="${CARE_ROOT}/data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
ROUND4="${CARE_ROOT}/results/predictions/MyoPS-Net_round4_combined_safe/fold_0"
ROUND5="${CARE_ROOT}/results/predictions/MyoPS-Net_round6_fullmod_on_allval/fold_0"

echo "[round7] log=${LOG_FILE}"
echo "[round7] fold=0 data_root=${DATA_ROOT}"

variants=(
  keep_round4_scar_round5_edema_complete
  edema_component_filter
  round5_edema_component_filter
  edema_support_limited
)

for variant in "${variants[@]}"; do
  pred_dir="${CARE_ROOT}/results/predictions/MyoPS-Net_round7_${variant}/fold_0"
  metric_dir="${CARE_ROOT}/results/metrics/unified/MyoPS-Net_round7_${variant}/fold_0"

  "${PY}" code/MyoPS-Net/apply_round7_edema_calibration.py \
    --round4-pred-dir "${ROUND4}" \
    --round5-pred-dir "${ROUND5}" \
    --output-dir "${pred_dir}" \
    --data-root "${DATA_ROOT}" \
    --fold-json "${FOLD_JSON}" \
    --fold 0 \
    --variant "${variant}" \
    --min-component-voxels 20 \
    --summary-json "${metric_dir}/calibration_summary.json" \
    --summary-md "${metric_dir}/calibration_summary.md"

  "${PY}" scripts/evaluation/evaluate_predictions.py \
    --pred-dir "${pred_dir}" \
    --gt-dir "${GT_DIR}" \
    --fold-json "${FOLD_JSON}" \
    --fold 0 \
    --foreground-classes 4,5 \
    --skip-dice-if-gt-empty \
    --output-dir "${metric_dir}"

  "${PY}" code/MyoPS-Net/report_modality_groups.py \
    --evaluation-summary "${metric_dir}/evaluation_summary.json" \
    --fold-json "${FOLD_JSON}" \
    --fold 0 \
    --data-root "${DATA_ROOT}" \
    --output-json "${metric_dir}/modality_group_metrics.json" \
    --output-md "${metric_dir}/modality_group_metrics.md"

  "${PY}" scripts/evaluation/aggregate_folds.py \
    --inputs "${metric_dir}/evaluation_summary.json" \
    --output-json "${CARE_ROOT}/results/metrics/unified/MyoPS-Net_round7_${variant}/aggregate.json" \
    --output-md "${CARE_ROOT}/results/metrics/unified/MyoPS-Net_round7_${variant}/aggregate.md"
done

echo "[round7] done"
