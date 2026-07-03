#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRPropRefF0
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
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRPropRefF0_${SLURM_ARRAY_TASK_ID:-local}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

VARIANTS=(
  srr_propref_shared_dual_dict
  srr_propref_scar_precision
  srr_propref_no_proto_cascade
)

TASK_ID="${SLURM_ARRAY_TASK_ID:-0}"
VARIANT="${VARIANTS[$TASK_ID]}"
OUT_ROOT="${CARE_ROOT}/results/20260703_srr_propref_repair"
CONFIG_DIR="${OUT_ROOT}/variants/${VARIANT}/configs"
mkdir -p "${CONFIG_DIR}"

cat > "${CONFIG_DIR}/run_config.env" <<EOF
variant=${VARIANT}
fold=0
job_id=${SLURM_JOB_ID:-local}
array_task_id=${TASK_ID}
max_runtime_seconds=25200
max_steps=${MAX_STEPS:-1800}
min_effective_optimizer_steps=1500
min_effective_train_loop_seconds=1800
patch_shape=${PATCH_SHAPE:-12,96,96}
batch_size=${BATCH_SIZE:-2}
base_channels=${BASE_CHANNELS:-10}
val_every=${VAL_EVERY:-300}
proposal_thresholds=${PROPOSAL_THRESHOLDS:-0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90}
scar_decode_threshold=${SCAR_DECODE_THRESHOLD:-0.50}
edema_decode_threshold=${EDEMA_DECODE_THRESHOLD:-0.50}
log_file=${LOG_FILE}
EOF

python scripts/training/run_srr_propref_myops_fold0.py \
  --variant "${VARIANT}" \
  --fold 0 \
  --device cuda \
  --base-channels "${BASE_CHANNELS:-10}" \
  --patch-shape "${PATCH_SHAPE:-12,96,96}" \
  --batch-size "${BATCH_SIZE:-2}" \
  --max-steps "${MAX_STEPS:-1800}" \
  --max-runtime-seconds 25200 \
  --val-every "${VAL_EVERY:-300}" \
  --proposal-thresholds "${PROPOSAL_THRESHOLDS:-0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90}" \
  --scar-decode-threshold "${SCAR_DECODE_THRESHOLD:-0.50}" \
  --edema-decode-threshold "${EDEMA_DECODE_THRESHOLD:-0.50}" \
  --out-root "${OUT_ROOT}" \
  --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv
