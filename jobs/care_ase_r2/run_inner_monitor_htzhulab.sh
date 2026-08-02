#!/usr/bin/env bash
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"

source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

FOLD="${FOLD:?FOLD is required}"
CHECKPOINT_STEP="${CHECKPOINT_STEP:?CHECKPOINT_STEP is required}"
CHECKPOINT="${CHECKPOINT:?CHECKPOINT is required}"
PATCH_SIZE="${PATCH_SIZE:-20,256,256}"
OUTPUT_DIR="${OUTPUT_DIR:-${CARE_ROOT}/results/20260803_care_ase_r2_full_fidelity_execution/inner_checkpoint_monitor/fold_${FOLD}/step$(printf '%05d' "${CHECKPOINT_STEP}")}"

case "${CHECKPOINT_STEP}" in
  4000|6000|8000|10000|12000|14000) ;;
  *) echo "unsupported checkpoint monitor step: ${CHECKPOINT_STEP}" >&2; exit 2 ;;
esac

mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CareASER2InnerMonitor_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "CARE-ASE R2 inner monitor command: ${CARE_ROOT}/envs/env_CARE/bin/python ${CARE_ROOT}/scripts/evaluation/care_ase/monitor_care_ase_r2_inner_trend.py --fold ${FOLD} --checkpoint ${CHECKPOINT} --checkpoint-step ${CHECKPOINT_STEP} --patch-size ${PATCH_SIZE} --output-dir ${OUTPUT_DIR}"

"${CARE_ROOT}/envs/env_CARE/bin/python" \
  "${CARE_ROOT}/scripts/evaluation/care_ase/monitor_care_ase_r2_inner_trend.py" \
  --fold "${FOLD}" \
  --checkpoint "${CHECKPOINT}" \
  --checkpoint-step "${CHECKPOINT_STEP}" \
  --patch-size "${PATCH_SIZE}" \
  --output-dir "${OUTPUT_DIR}"
