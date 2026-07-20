#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRB4Ctrl
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

PYTHON="${PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
TASK_KEY="20260721_srr_batch4_forced_fold0_training"
CONFIG="${CONFIG:-configs/srr_production/myops_batch4.yaml}"
CHECKPOINT="${CHECKPOINT:?CHECKPOINT is required}"
OUTPUT_ROOT="${OUTPUT_ROOT:-results/${TASK_KEY}/selected_checkpoint_controls}"
EVAL_ROOT="${EVAL_ROOT:-results/${TASK_KEY}/selected_checkpoint_evaluation}"

mkdir -p logs/srr_batch4 "${OUTPUT_ROOT}" "${EVAL_ROOT}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/srr_batch4/SRRB4Ctrl_htzhulab_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "CARE_ROOT=${CARE_ROOT}"
echo "PYTHON=${PYTHON}"
echo "CONFIG=${CONFIG}"
echo "CHECKPOINT=${CHECKPOINT}"
echo "OUTPUT_ROOT=${OUTPUT_ROOT}"
echo "EVAL_ROOT=${EVAL_ROOT}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-local}"
"${PYTHON}" --version
"${PYTHON}" - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
print("cuda_device_count", torch.cuda.device_count())
if torch.cuda.is_available():
    print("cuda_device_name", torch.cuda.get_device_name(0))
    major, minor = torch.cuda.get_device_capability(0)
    print("cuda_device_capability", f"sm_{major}{minor}")
    print("torch_cuda_arch_list", ",".join(sorted(torch.cuda.get_arch_list())))
PY

for MODE in anchor_identity_control anchor_bounded_srr_correction srr_no_anchor_control; do
  "${PYTHON}" scripts/srr_production/infer_myops.py \
    --config "${CONFIG}" \
    --mode "${MODE}" \
    --fold 0 \
    --checkpoint "${CHECKPOINT}" \
    --output-root "${OUTPUT_ROOT}" \
    --device cuda
done

"${PYTHON}" scripts/srr_production/evaluate_myops_fair.py \
  --config "${CONFIG}" \
  --fold 0 \
  --identity-pred-dir "${OUTPUT_ROOT}/anchor_identity_control/predictions" \
  --srr-pred-dir "${OUTPUT_ROOT}/anchor_bounded_srr_correction/predictions" \
  --srr-contract "${OUTPUT_ROOT}/batch3a_anchor_bounded_srr_correction_inference_contract.json" \
  --output-dir "${EVAL_ROOT}"
