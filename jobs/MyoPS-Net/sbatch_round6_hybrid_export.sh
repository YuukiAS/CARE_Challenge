#!/bin/bash
# MyoPS-Net round6 export-only all-val + hybrid routing. No training.
# Submit from repo root:
#   sbatch jobs/MyoPS-Net/sbatch_round6_hybrid_export.sh
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=MyoPSNet_r6_hybrid
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
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
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MyoPSNet_r6_hybrid_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${CARE_ROOT}/env_CARE/bin/python"
FOLD="${FOLD:-0}"
ALLVAL_DATA="${MYOPS_NET_ALLVAL_DATA:-${CARE_ROOT}/data/benchmarks/MyoPS-Net/fold_0_maskgated_round3}"
ROUND5_CKPT="${MYOPS_NET_ROUND5_CKPT:-${CARE_ROOT}/results/checkpoints/MyoPS-Net/fold_0_fullmod_round5/checkpoints/best.pth}"
FULLMOD_ALLVAL_PRED="${CARE_ROOT}/results/predictions/MyoPS-Net_round6_fullmod_on_allval/fold_${FOLD}"
FULLMOD_ALLVAL_MET="${CARE_ROOT}/results/metrics/unified/MyoPS-Net_round6_fullmod_on_allval/fold_${FOLD}"
FALLBACK_PRED="${MYOPS_NET_ROUND6_FALLBACK_PRED:-${CARE_ROOT}/results/predictions/MyoPS-Net_round4_combined_safe/fold_${FOLD}}"
HYBRID_PRED="${CARE_ROOT}/results/predictions/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_${FOLD}"
HYBRID_MET="${CARE_ROOT}/results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_${FOLD}"
SPLITS="${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json"
GT_DIR="${nnUNet_raw}/Dataset501_CAREMyoPS/labelsTr"

echo "===== MyoPS-Net round6 hybrid export ====="
echo "host=$(hostname) SLURM_JOB_ID=${SLURM_JOB_ID:-na}"
echo "LOG_FILE=${LOG_FILE}"
echo "ALLVAL_DATA=${ALLVAL_DATA}"
echo "ROUND5_CKPT=${ROUND5_CKPT}"
echo "FALLBACK_PRED=${FALLBACK_PRED}"

rm -rf "${FULLMOD_ALLVAL_PRED}" "${FULLMOD_ALLVAL_MET}" "${HYBRID_PRED}" "${HYBRID_MET}"
mkdir -p "${FULLMOD_ALLVAL_PRED}" "${FULLMOD_ALLVAL_MET}" "${HYBRID_PRED}" "${HYBRID_MET}"

"${PY}" "${CARE_ROOT}/code/MyoPS-Net/export_val_predictions.py" \
  --data-root "${ALLVAL_DATA}" \
  --output-dir "${FULLMOD_ALLVAL_PRED}" \
  --checkpoint "${ROUND5_CKPT}" \
  --variant challenge3

"${PY}" "${CARE_ROOT}/scripts/evaluation/evaluate_predictions.py" \
  --pred-dir "${FULLMOD_ALLVAL_PRED}" \
  --gt-dir "${GT_DIR}" \
  --fold-json "${SPLITS}" \
  --fold "${FOLD}" \
  --foreground-classes 4,5 \
  --skip-dice-if-gt-empty \
  --output-dir "${FULLMOD_ALLVAL_MET}"

"${PY}" "${CARE_ROOT}/code/MyoPS-Net/build_round6_hybrid.py" \
  --data-root "${ALLVAL_DATA}" \
  --fold-json "${SPLITS}" \
  --fold "${FOLD}" \
  --fullmod-pred-dir "${FULLMOD_ALLVAL_PRED}" \
  --fallback-pred-dir "${FALLBACK_PRED}" \
  --output-dir "${HYBRID_PRED}" \
  --summary-json "${HYBRID_MET}/routing_summary.json"

"${PY}" "${CARE_ROOT}/scripts/evaluation/evaluate_predictions.py" \
  --pred-dir "${HYBRID_PRED}" \
  --gt-dir "${GT_DIR}" \
  --fold-json "${SPLITS}" \
  --fold "${FOLD}" \
  --foreground-classes 4,5 \
  --skip-dice-if-gt-empty \
  --output-dir "${HYBRID_MET}"

for met in "${FULLMOD_ALLVAL_MET}" "${HYBRID_MET}"; do
  "${PY}" "${CARE_ROOT}/code/MyoPS-Net/report_modality_groups.py" \
    --evaluation-summary "${met}/evaluation_summary.json" \
    --fold-json "${SPLITS}" \
    --fold "${FOLD}" \
    --data-root "${ALLVAL_DATA}" \
    --output-json "${met}/modality_group_metrics.json" \
    --output-md "${met}/modality_group_metrics.md"
done

echo "===== MyoPS-Net round6 done ====="
echo "fullmod all-val: ${FULLMOD_ALLVAL_MET}/evaluation_summary.json"
echo "hybrid: ${HYBRID_MET}/evaluation_summary.json"
