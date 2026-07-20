#!/usr/bin/env bash
set -euo pipefail

PARTITION_LABEL="${1:?partition label required}"
shift || true

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
PYTHON="${PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
TASK_KEY="20260721_srr_batch4_forced_fold0_training"
RESULT_ROOT="${CARE_ROOT}/results/${TASK_KEY}"
RUNTIME_ROOT="${RESULT_ROOT}/runtime"
LOGICAL_RUN_ID="${LOGICAL_RUN_ID:-srr_batch4_m10d3_full4scale_fold0_seed20260721}"
ATTEMPT_ID="${LOGICAL_RUN_ID}_${PARTITION_LABEL}_${SLURM_JOB_ID:-local}"
ATTEMPT_ROOT="${RUNTIME_ROOT}/attempts/${ATTEMPT_ID}"
WINNER_LOCK="${RUNTIME_ROOT}/locks/${LOGICAL_RUN_ID}.winner"

mkdir -p "${ATTEMPT_ROOT}" "${RUNTIME_ROOT}/locks"

if mkdir "${WINNER_LOCK}" 2>/dev/null; then
  cat > "${WINNER_LOCK}/owner.json" <<EOF
{"attempt_id":"${ATTEMPT_ID}","partition":"${PARTITION_LABEL}","job_id":"${SLURM_JOB_ID:-local}","log_file":"${LOG_FILE:-}","status":"winner_started"}
EOF
else
  echo "Winner lock already exists at ${WINNER_LOCK}; started loser exits before optimizer step."
  exit 0
fi

echo "CARE_ROOT=${CARE_ROOT}"
echo "PYTHON=${PYTHON}"
echo "PARTITION_LABEL=${PARTITION_LABEL}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-local}"
echo "LOGICAL_RUN_ID=${LOGICAL_RUN_ID}"
echo "ATTEMPT_ROOT=${ATTEMPT_ROOT}"
echo "WINNER_LOCK=${WINNER_LOCK}"
"${PYTHON}" --version
"${PYTHON}" - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
print("cuda_device_count", torch.cuda.device_count())
if torch.cuda.is_available():
    print("cuda_device_name", torch.cuda.get_device_name(0))
PY

exec "${PYTHON}" scripts/training/run_srr_propref_myops_fold0.py \
  --variant m10_d3_hierarchical_memory_propref \
  --run-label "${ATTEMPT_ID}" \
  --fold 0 \
  --seed 20260721 \
  --device cuda \
  --base-channels 32 \
  --encoder-profile full_4scale \
  --final-output-mode anchor_bounded_srr_correction \
  --patch-shape 12,96,96 \
  --batch-size 1 \
  --max-steps 1800 \
  --max-runtime-seconds 21600 \
  --lr 0.0002 \
  --weight-decay 0.0001 \
  --grad-clip 12.0 \
  --val-every 300 \
  --early-stop-patience 0 \
  --min-train-loop-seconds-for-plateau 1800 \
  --enforce-min-train-loop-seconds \
  --overfit-steps 60 \
  --min-overfit-loss-decrease 0.05 \
  --prototype-bank-cases 176 \
  --prototype-memory-asset "${ATTEMPT_ROOT}/frozen_prototype_memory.pt" \
  --prototype-memory-manifest "${ATTEMPT_ROOT}/frozen_prototype_memory_manifest.json" \
  --full-volume-eval-steps 600,1200,1800 \
  --out-root "${ATTEMPT_ROOT}" \
  --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv \
  --batch4-production-contract \
  "$@"
