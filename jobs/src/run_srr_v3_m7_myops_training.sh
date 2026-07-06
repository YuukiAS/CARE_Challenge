#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRv3M7MyOPS
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=07:30:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

MAX_STEPS_VALUE="${MAX_STEPS:-6000}"
VAL_EVERY_VALUE="${VAL_EVERY:-300}"
if (( MAX_STEPS_VALUE < 3000 )); then
  echo "Refusing M7 run: MAX_STEPS=${MAX_STEPS_VALUE} is below M7 minimum 3000." >&2
  exit 64
fi
if (( VAL_EVERY_VALUE > 500 )); then
  echo "Refusing M7 run: VAL_EVERY=${VAL_EVERY_VALUE} is above M7 maximum 500." >&2
  exit 64
fi

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRv3M7MyOPS_${SLURM_ARRAY_TASK_ID:-local}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

VARIANTS=(
  m7_full_srr_context_arbitration
  m7_conservative_component_arbitration
  m7_scar_precision_edema_safe
)

PROFILES=(
  balanced_4scale
  safe_4scale
  balanced_4scale
)

TASK_ID="${SLURM_ARRAY_TASK_ID:-0}"
if (( TASK_ID < 0 || TASK_ID >= ${#VARIANTS[@]} )); then
  echo "Invalid SLURM_ARRAY_TASK_ID=${TASK_ID}; expected 0..$((${#VARIANTS[@]} - 1))." >&2
  exit 65
fi

VARIANT="${VARIANTS[$TASK_ID]}"
PROFILE="${PROFILES[$TASK_ID]}"
OUT_ROOT="${CARE_ROOT}/results/20260705_srr_v3_m7_training_and_cine_utilization/runtime"
LOCK_ROOT="${OUT_ROOT}/routing_locks"
LOCK_DIR="${LOCK_ROOT}/${VARIANT}.lock"
CONFIG_DIR="${OUT_ROOT}/variants/${VARIANT}/configs"
mkdir -p "${LOCK_ROOT}" "${CONFIG_DIR}"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "M7 routing duplicate: ${VARIANT} already claimed by $(cat "${LOCK_DIR}/owner.txt" 2>/dev/null || echo unknown). Exiting without training."
  exit 0
fi
cat > "${LOCK_DIR}/owner.txt" <<EOF
variant=${VARIANT}
job_id=${SLURM_JOB_ID:-local}
array_task_id=${TASK_ID}
partition=${SLURM_JOB_PARTITION:-unknown}
claimed_at=$(date -Iseconds)
EOF
GIT_HEAD="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
GIT_STATUS_SHORT="$(git status --short 2>/dev/null | tr '\n' ';' || true)"

cat > "${CONFIG_DIR}/run_config.env" <<EOF
variant=${VARIANT}
encoder_profile=${PROFILE}
fold=0
git_head=${GIT_HEAD}
git_status_short=${GIT_STATUS_SHORT}
job_id=${SLURM_JOB_ID:-local}
array_task_id=${TASK_ID}
partition=${SLURM_JOB_PARTITION:-unknown}
max_runtime_seconds=${MAX_RUNTIME_SECONDS:-25200}
max_steps=${MAX_STEPS_VALUE}
patch_shape=${PATCH_SHAPE:-8,64,64}
batch_size=${BATCH_SIZE:-1}
base_channels=${BASE_CHANNELS:-32}
val_every=${VAL_EVERY_VALUE}
log_file=${LOG_FILE}
out_root=${OUT_ROOT}
EOF

python scripts/training/run_srr_propref_myops_fold0.py \
  --variant "${VARIANT}" \
  --run-label "${VARIANT}" \
  --fold 0 \
  --device cuda \
  --base-channels "${BASE_CHANNELS:-32}" \
  --encoder-profile "${PROFILE}" \
  --patch-shape "${PATCH_SHAPE:-8,64,64}" \
  --batch-size "${BATCH_SIZE:-1}" \
  --max-steps "${MAX_STEPS_VALUE}" \
  --max-runtime-seconds "${MAX_RUNTIME_SECONDS:-25200}" \
  --val-every "${VAL_EVERY_VALUE}" \
  --log-every "${LOG_EVERY:-100}" \
  --overfit-steps "${OVERFIT_STEPS:-40}" \
  --min-overfit-loss-decrease "${MIN_OVERFIT_LOSS_DECREASE:-0.001}" \
  --min-optimizer-steps-for-plateau "${MIN_OPTIMIZER_STEPS_FOR_PLATEAU:-3000}" \
  --min-train-loop-seconds-for-plateau "${MIN_TRAIN_LOOP_SECONDS_FOR_PLATEAU:-1800}" \
  --max-eval-cases "${MAX_EVAL_CASES:-12}" \
  --proposal-thresholds "${PROPOSAL_THRESHOLDS:-0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90}" \
  --scar-decode-threshold "${SCAR_DECODE_THRESHOLD:-0.50}" \
  --edema-decode-threshold "${EDEMA_DECODE_THRESHOLD:-0.50}" \
  --out-root "${OUT_ROOT}" \
  --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv
