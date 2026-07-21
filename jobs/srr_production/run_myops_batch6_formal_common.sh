#!/usr/bin/env bash
set -euo pipefail

STAGE="${BATCH6_STAGE:?BATCH6_STAGE required: 300 or 900}"
PARTITION_LABEL="${PARTITION_LABEL:?PARTITION_LABEL required}"
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

RESULT_ROOT="${RESULT_ROOT:-${CARE_ROOT}/results/20260721_srr_batch6_final_objective_alignment}"
LOCK_ROOT="${LOCK_ROOT:-${RESULT_ROOT}/runtime/locks}"
LOGICAL_RUN_ID="${LOGICAL_RUN_ID:-batch6_formal${STAGE}}"
ATTEMPT_LABEL="${ATTEMPT_LABEL:-${LOGICAL_RUN_ID}_${PARTITION_LABEL}_${SLURM_JOB_ID:-local}}"
ATTEMPT_ROOT="${RESULT_ROOT}/runtime/attempts/${ATTEMPT_LABEL}"
LOCK_DIR="${LOCK_ROOT}/${LOGICAL_RUN_ID}.winner.lock"
mkdir -p "${LOCK_ROOT}" "${ATTEMPT_ROOT}"

echo "CARE_ROOT=${CARE_ROOT}"
echo "BATCH6_STAGE=${STAGE}"
echo "PARTITION_LABEL=${PARTITION_LABEL}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-local}"
echo "ATTEMPT_LABEL=${ATTEMPT_LABEL}"
echo "ATTEMPT_ROOT=${ATTEMPT_ROOT}"
echo "LOCK_DIR=${LOCK_DIR}"
"${CARE_ROOT}/envs/env_CARE/bin/python" --version
"${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PYTORCH'
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
print("cuda_device_count", torch.cuda.device_count())
if not torch.cuda.is_available():
    raise SystemExit("CUDA_NOT_AVAILABLE_FOR_BATCH6_FORMAL")
print("cuda_device_name", torch.cuda.get_device_name(0))
major, minor = torch.cuda.get_device_capability(0)
current = f"sm_{major}{minor}"
print("cuda_device_capability", current)
print("torch_cuda_arch_list", ",".join(sorted(torch.cuda.get_arch_list())))
PYTORCH

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_srr_batch6_formal.py \
  --config configs/srr_production/myops_batch6.yaml \
  --stage "${STAGE}" \
  --attempt-label "${ATTEMPT_LABEL}" \
  --print-contract

if mkdir "${LOCK_DIR}" 2>/dev/null; then
  cat > "${LOCK_DIR}/owner.json" <<OWNER
{"attempt_label":"${ATTEMPT_LABEL}","partition":"${PARTITION_LABEL}","job_id":"${SLURM_JOB_ID:-local}","stage":"${STAGE}","log_file":"${LOG_FILE:-}","status":"winner_started"}
OWNER
else
  echo "winner_lock_status=lost lock=${LOCK_DIR}; loser exits before optimizer step"
  exit 0
fi

exec "${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_srr_batch6_formal.py \
  --config configs/srr_production/myops_batch6.yaml \
  --stage "${STAGE}" \
  --attempt-label "${ATTEMPT_LABEL}"
