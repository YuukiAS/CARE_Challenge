#!/usr/bin/env bash
# Eval remaining SRR-v2.5 bounded checkpoints on full MyoPS fold0.
# This is eval-only: no training, no validation packaging, no upload.
# Submit from repo root:
#   sbatch jobs/evaluation/export_srr_v25_full_fold0_remaining.sh
# Optional:
#   VARIANTS=srr_v25_no_anchor,srr_v25_no_anatomy_roi sbatch ...
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRv25F0Eval
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
export PYTHONUNBUFFERED=1

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRv25F0Eval_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

OUTPUT_ROOT="${OUTPUT_ROOT:-results/20260704_srr_v25_training_ablation_matrix/full_fold0_eval}"
VARIANTS="${VARIANTS:-srr_propref_no_proto_cascade,srr_propref_scar_precision,srr_v25_no_local_refine,srr_v25_no_anatomy_roi,srr_v25_no_anchor}"

echo "===== SRR-v2.5 full fold0 eval-only remaining rows ====="
echo "host=$(hostname) SLURM_JOB_ID=${SLURM_JOB_ID:-na}"
echo "CARE_ROOT=${CARE_ROOT}"
echo "LOG_FILE=${LOG_FILE}"
echo "OUTPUT_ROOT=${OUTPUT_ROOT}"
echo "VARIANTS=${VARIANTS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"

python scripts/evaluation/export_srr_v25_full_fold0_metrics.py \
  --device cuda \
  --variants "${VARIANTS}" \
  --output-root "${OUTPUT_ROOT}"

IFS=',' read -r -a VARIANT_ARRAY <<< "${VARIANTS}"
for VARIANT in "${VARIANT_ARRAY[@]}"; do
  VARIANT="$(echo "${VARIANT}" | xargs)"
  [[ -n "${VARIANT}" ]] || continue
  METRICS="${OUTPUT_ROOT}/variants/${VARIANT}/component_hd_by_case_checkpoint_final_full_fold0.csv"
  if [[ ! -s "${METRICS}" ]]; then
    echo "Skipping help/harm for ${VARIANT}: missing ${METRICS}"
    continue
  fi
  python scripts/evaluation/srr_help_harm_vs_nnunet.py \
    --srr-metrics "${METRICS}" \
    --output-dir "${OUTPUT_ROOT}/help_harm/${VARIANT}" \
    --fold 0
done

echo "===== SRR-v2.5 full fold0 eval-only remaining rows done ====="
