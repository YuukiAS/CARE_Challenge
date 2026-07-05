#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRv3M3Pilot
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

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRv3M3Pilot_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

OUT_ROOT="${CARE_ROOT}/results/20260705_srr_v3_m3_myops_min_effective_pilot_training"
RUN_LABEL="${RUN_LABEL:-srr_v3_m3_shared_dual_dict_pilot}"
TRAIN_CASE_IDS="${TRAIN_CASE_IDS:-Case1004,Case1028,Case2001,Case2004,Case3001,Case3008,Case3032,Case5001,Case6002,Case7006,Case8001,Case8028}"
EVAL_CASE_IDS="${EVAL_CASE_IDS:-Case1029,Case1045,Case2002,Case2008,Case2031,Case3004,Case3012,Case3023,Case3038,Case5005,Case7005,Case8011}"
MAX_STEPS_VALUE="${MAX_STEPS:-6000}"
VAL_EVERY_VALUE="${VAL_EVERY:-300}"

if (( MAX_STEPS_VALUE < 1200 )); then
  echo "Refusing M3 pilot: MAX_STEPS=${MAX_STEPS_VALUE} is below task minimum 1200." >&2
  exit 64
fi
if (( VAL_EVERY_VALUE > 300 )); then
  echo "Refusing M3 pilot: VAL_EVERY=${VAL_EVERY_VALUE} is above reviewable validation interval 300." >&2
  exit 64
fi

CONFIG_DIR="${OUT_ROOT}/variants/${RUN_LABEL}/configs"
mkdir -p "${CONFIG_DIR}"
cat > "${CONFIG_DIR}/run_config.env" <<EOF
task_key=20260705_srr_v3_m3_myops_min_effective_pilot_training
variant=srr_propref_shared_dual_dict
run_label=${RUN_LABEL}
fold=0
job_id=${SLURM_JOB_ID:-local}
max_steps=${MAX_STEPS_VALUE}
min_effective_optimizer_steps=1200
min_effective_train_loop_seconds=1800
min_effective_eval_cases=12
patch_shape=${PATCH_SHAPE:-12,96,96}
batch_size=${BATCH_SIZE:-2}
base_channels=${BASE_CHANNELS:-8}
encoder_profile=strong_4scale
val_every=${VAL_EVERY_VALUE}
train_case_ids=${TRAIN_CASE_IDS}
eval_case_ids=${EVAL_CASE_IDS}
max_eval_cases=12
log_file=${LOG_FILE}
EOF

TRAINING_COMMAND=(
  python scripts/training/run_srr_propref_myops_fold0.py
  --variant srr_propref_shared_dual_dict
  --run-label "${RUN_LABEL}"
  --fold 0
  --device cuda
  --base-channels "${BASE_CHANNELS:-8}"
  --encoder-profile strong_4scale
  --patch-shape "${PATCH_SHAPE:-12,96,96}"
  --batch-size "${BATCH_SIZE:-2}"
  --max-steps "${MAX_STEPS_VALUE}"
  --max-runtime-seconds "${MAX_RUNTIME_SECONDS:-25200}"
  --val-every "${VAL_EVERY_VALUE}"
  --overfit-steps "${OVERFIT_STEPS:-60}"
  --prototype-bank-cases "${PROTOTYPE_BANK_CASES:-8}"
  --max-eval-cases 12
  --train-case-ids "${TRAIN_CASE_IDS}"
  --eval-case-ids "${EVAL_CASE_IDS}"
  --proposal-thresholds "${PROPOSAL_THRESHOLDS:-0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90}"
  --scar-decode-threshold "${SCAR_DECODE_THRESHOLD:-0.50}"
  --edema-decode-threshold "${EDEMA_DECODE_THRESHOLD:-0.50}"
  --out-root "${OUT_ROOT}"
  --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv
)

printf 'Training command:'
printf ' %q' "${TRAINING_COMMAND[@]}"
printf '\n'
"${TRAINING_COMMAND[@]}"

AGG_COMMAND=(
  python scripts/evaluation/aggregate_srr_v3_m3_pilot.py
  --out-root "${OUT_ROOT}"
  --variant "${RUN_LABEL}"
  --training-command "$(printf '%q ' "${TRAINING_COMMAND[@]}")"
)
printf 'Aggregate command:'
printf ' %q' "${AGG_COMMAND[@]}"
printf '\n'
"${AGG_COMMAND[@]}"
