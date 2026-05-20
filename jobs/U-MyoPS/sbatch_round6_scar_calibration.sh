#!/bin/bash
# U-MyoPS round6 export-only scar calibration/routing.
# Submit from repo root:
#   sbatch jobs/U-MyoPS/sbatch_round6_scar_calibration.sh
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=U-MyoPS-r6-cal
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=32G
#SBATCH --time=02:00:00
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

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/U-MyoPS_r6_calibration_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${CARE_EVAL_PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
GT_DIR="${CARE_ROOT}/data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
SPLIT_JSON="${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json"

echo "===== U-MyoPS round6 scar calibration ====="
echo "host=$(hostname) SLURM_JOB_ID=${SLURM_JOB_ID:-na}"
echo "LOG_FILE=${LOG_FILE}"

"${PY}" "${CARE_ROOT}/code/U-MyoPS/apply_round6_scar_calibration.py"

for tag in \
  U-MyoPS_round6_scar_component_filter_100 \
  U-MyoPS_round6_scar_component_filter_250 \
  U-MyoPS_round6_missing_volume_cap_1500 \
  U-MyoPS_round6_scar_complete_umyops_missing_nnunet \
  U-MyoPS_round6_complete_umyops_missing_nnunet
do
  pred_dir="${CARE_ROOT}/results/predictions/${tag}/fold_0"
  out_dir="${CARE_ROOT}/results/metrics/unified/${tag}/fold_0"
  agg_root="${CARE_ROOT}/results/metrics/unified/${tag}"
  mkdir -p "${out_dir}"

  echo ""
  echo "===== evaluate ${tag} ====="
  "${PY}" "${CARE_ROOT}/scripts/evaluation/evaluate_predictions.py" \
    --pred-dir "${pred_dir}" \
    --gt-dir "${GT_DIR}" \
    --fold-json "${SPLIT_JSON}" \
    --fold 0 \
    --foreground-classes 4,5 \
    --output-dir "${out_dir}"

  "${PY}" "${CARE_ROOT}/scripts/evaluation/report_umyops_round2.py" \
    --checkpoint-tag "${tag#U-MyoPS_}" \
    --pred-dir "${pred_dir}" \
    --out-dir "${out_dir}"

  "${PY}" "${CARE_ROOT}/scripts/evaluation/aggregate_folds.py" \
    --inputs "${out_dir}/evaluation_summary.json" \
    --output-json "${agg_root}/aggregate.json" \
    --output-md "${agg_root}/aggregate.md"
done

echo "===== U-MyoPS round6 scar calibration done ====="
