#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRv3M8MyOPS
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=05:45:00
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access
#SBATCH --array=0-2

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

TASK_KEY="20260707_srr_v3_m8_editor_grade_leaderboard_sprint"
OUT_DIR="${CARE_ROOT}/results/${TASK_KEY}"
RUNTIME_ROOT="${OUT_DIR}/runtime"
CONFIG_PATH="${OUT_DIR}/m8_variant_config_contract.json"

MAX_STEPS_VALUE="${MAX_STEPS:-9000}"
VAL_EVERY_VALUE="${VAL_EVERY:-300}"
MAX_RUNTIME_SECONDS_VALUE="${MAX_RUNTIME_SECONDS:-18000}"
if (( MAX_STEPS_VALUE < 6000 )); then
  echo "Refusing M8 run: MAX_STEPS=${MAX_STEPS_VALUE} is below M8 long-candidate minimum 6000." >&2
  exit 64
fi
if (( VAL_EVERY_VALUE > 500 )); then
  echo "Refusing M8 run: VAL_EVERY=${VAL_EVERY_VALUE} is above M8 maximum 500." >&2
  exit 64
fi
if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Refusing M8 run: config contract missing at ${CONFIG_PATH}." >&2
  exit 66
fi

mkdir -p logs "${RUNTIME_ROOT}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRv3M8MyOPS_${SLURM_ARRAY_TASK_ID:-local}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

VARIANTS=(
  m8_full_srr_context_arbitration_longrun
  m8_scar_precision_edema_safe_longrun
  m8_t2_centerC_edema_repair_longrun
)

PROFILES=(
  full_4scale
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
CONFIG_DIR="${RUNTIME_ROOT}/variants/${VARIANT}/configs"
mkdir -p "${CONFIG_DIR}"
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
max_runtime_seconds=${MAX_RUNTIME_SECONDS_VALUE}
max_steps=${MAX_STEPS_VALUE}
patch_shape=${PATCH_SHAPE:-8,64,64}
batch_size=${BATCH_SIZE:-1}
base_channels=${BASE_CHANNELS:-32}
val_every=${VAL_EVERY_VALUE}
log_file=${LOG_FILE}
out_root=${RUNTIME_ROOT}
variant_config_contract=${CONFIG_PATH}
EOF

python scripts/training/run_srr_propref_myops_fold0.py \
  --variant "${VARIANT}" \
  --variant-config-contract "${CONFIG_PATH}" \
  --variant-config-key "${VARIANT}" \
  --run-label "${VARIANT}" \
  --fold 0 \
  --device cuda \
  --base-channels "${BASE_CHANNELS:-32}" \
  --encoder-profile "${PROFILE}" \
  --patch-shape "${PATCH_SHAPE:-8,64,64}" \
  --batch-size "${BATCH_SIZE:-1}" \
  --max-steps "${MAX_STEPS_VALUE}" \
  --max-runtime-seconds "${MAX_RUNTIME_SECONDS_VALUE}" \
  --val-every "${VAL_EVERY_VALUE}" \
  --log-every "${LOG_EVERY:-100}" \
  --overfit-steps "${OVERFIT_STEPS:-40}" \
  --min-overfit-loss-decrease "${MIN_OVERFIT_LOSS_DECREASE:-0.001}" \
  --min-optimizer-steps-for-plateau "${MIN_OPTIMIZER_STEPS_FOR_PLATEAU:-6000}" \
  --min-train-loop-seconds-for-plateau "${MIN_TRAIN_LOOP_SECONDS_FOR_PLATEAU:-7200}" \
  --enforce-min-train-loop-seconds \
  --max-eval-cases "${MAX_EVAL_CASES:-12}" \
  --proposal-thresholds "${PROPOSAL_THRESHOLDS:-0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90}" \
  --scar-decode-threshold "${SCAR_DECODE_THRESHOLD:-0.50}" \
  --edema-decode-threshold "${EDEMA_DECODE_THRESHOLD:-0.50}" \
  --out-root "${RUNTIME_ROOT}" \
  --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv
