#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRB5Diag
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

mkdir -p logs/srr_batch5
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/srr_batch5/SRRB5DiagA100_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${CARE_ROOT}/envs/env_CARE/bin/python"
RESULT_ROOT="${CARE_ROOT}/results/20260721_srr_batch5_post_batch4_diagnostic_repair"
CHECKPOINT="${CARE_ROOT}/results/20260721_srr_batch4_forced_fold0_training/runtime/attempts/srr_batch4_m10d3_full4scale_fold0_seed20260721_htzhulab_59682067/variants/srr_batch4_m10d3_full4scale_fold0_seed20260721_htzhulab_59682067/checkpoints/fold_0/propref_config/checkpoint_validation_step_1800.pt"
TRAINING_SUMMARY="${CARE_ROOT}/results/20260721_srr_batch4_forced_fold0_training/runtime/attempts/srr_batch4_m10d3_full4scale_fold0_seed20260721_htzhulab_59682067/variants/srr_batch4_m10d3_full4scale_fold0_seed20260721_htzhulab_59682067/summary.json"
LOCK_DIR="${RESULT_ROOT}/runtime/locks"
LOCK_PATH="${LOCK_DIR}/batch5_diagnostic.winner"
OWNER_PATH="${LOCK_PATH}/owner.json"

mkdir -p "${LOCK_DIR}" "${RESULT_ROOT}/runtime/inference"
if mkdir "${LOCK_PATH}" 2>/dev/null; then
  printf '{"job_id":"%s","partition":"%s","log_file":"%s","optimizer_steps":0}\n' \
    "${SLURM_JOB_ID:-local}" "${SLURM_JOB_PARTITION:-a100-gpu}" "${LOG_FILE}" > "${OWNER_PATH}"
else
  echo "Winner lock already exists at ${LOCK_PATH}; exiting with zero training credit."
  exit 0
fi

MODES=(
  anchor_identity_control
  anchor_bounded_full
  srr_no_anchor_control
  anchor_bounded_proposal_only
  anchor_bounded_refiner_only
  production_gate_closed
  production_gate_open_bounded_control
)

for mode in "${MODES[@]}"; do
  echo "Running Batch5 inference mode: ${mode}"
  "${PY}" scripts/srr_production/infer_myops.py \
    --config configs/srr_production/myops_batch5.yaml \
    --mode "${mode}" \
    --fold 0 \
    --checkpoint "${CHECKPOINT}" \
    --training-summary "${TRAINING_SUMMARY}" \
    --output-root "${RESULT_ROOT}/runtime/inference" \
    --device cuda
done

"${PY}" scripts/evaluation/audit_srr_batch4_selection_semantics.py \
  --config configs/srr_production/myops_batch5.yaml \
  --result-root "results/20260721_srr_batch5_post_batch4_diagnostic_repair"

cat > "${RESULT_ROOT}/slurm_attempts.csv" <<EOF
job_id,partition,state,exit_code,elapsed,log_path,runtime_output_path,optimizer_steps,parameter_updates,training_credit
${SLURM_JOB_ID:-local},${SLURM_JOB_PARTITION:-a100-gpu},COMPLETED,0:0,UNKNOWN,${LOG_FILE},${RESULT_ROOT}/runtime/inference,0,0,0_DIAGNOSTIC_INFERENCE_ONLY
EOF

echo "Batch5 diagnostic inference complete."
