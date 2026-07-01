#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRv2Tgt
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
export CODEX_HOME="${CODEX_HOME:-/users/a/e/aereinh/.codex-home-care}"
export CODEX_REPO_ROOT="${CARE_ROOT}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/users/a/e/aereinh/.cache/codex-care}"
export TMPDIR="${TMPDIR:-/users/a/e/aereinh/.tmp/codex-care}"
mkdir -p logs "${TMPDIR}"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_ROOT="${OUT_ROOT:-results/20260629_srr_v2_unet_core/targeted_extras}"
PREFLIGHT_OUT_ROOT="${PREFLIGHT_OUT_ROOT:-${OUT_ROOT}/preflight}"

case "${SLURM_ARRAY_TASK_ID:-0}" in
  0)
    BASE_VARIANT="srr_v2_multiscale_private_proposal"
    OUTPUT_VARIANT="srr_v2_edema_t2_focus"
    SEED="2026070105"
    BASE_CHANNELS="8"
    LR="0.0008"
    COMPLETE_OVERSAMPLE="0.90"
    OVERSAMPLE_FOREGROUND="0.95"
    SCAR_WEIGHT="1.0"
    EDEMA_WEIGHT="2.3"
    PROPOSAL_FINAL_MIX="0.30"
    HARDNEG_PROB="0.05"
    PROPOSAL_BCE="0.58"
    PROPOSAL_MARGIN_WEIGHT="0.18"
    PROPOSAL_UNCERTAINTY_WEIGHT="0.04"
    EXTRA_FLAGS=()
    ;;
  1)
    BASE_VARIANT="srr_v2_proposal_uncertainty_hardneg"
    OUTPUT_VARIANT="srr_v2_scar_precision_nointeract"
    SEED="2026070106"
    BASE_CHANNELS="8"
    LR="0.00075"
    COMPLETE_OVERSAMPLE="0.70"
    OVERSAMPLE_FOREGROUND="0.90"
    SCAR_WEIGHT="1.8"
    EDEMA_WEIGHT="1.0"
    PROPOSAL_FINAL_MIX="0.18"
    HARDNEG_PROB="0.70"
    PROPOSAL_BCE="0.38"
    PROPOSAL_MARGIN_WEIGHT="0.34"
    PROPOSAL_UNCERTAINTY_WEIGHT="0.18"
    EXTRA_FLAGS=(--disable-srr-v2-interactions)
    ;;
  *)
    echo "Unsupported SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID}; expected 0 or 1" >&2
    exit 2
    ;;
esac

LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRv2Tgt_${OUTPUT_VARIANT}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "variant=${BASE_VARIANT}"
echo "output_variant=${OUTPUT_VARIANT}"
echo "partition=${SLURM_JOB_PARTITION:-local}"
echo "OUT_ROOT=${OUT_ROOT}"
echo "PREFLIGHT_OUT_ROOT=${PREFLIGHT_OUT_ROOT}"
date

COMMON_ARGS=(
  --variant "${BASE_VARIANT}"
  --output-variant-name "${OUTPUT_VARIANT}"
  --fold 0
  --seed "${SEED}"
  --device cuda
  --base-channels "${BASE_CHANNELS}"
  --patch-shape 8,80,80
  --batch-size 1
  --max-runtime-seconds 23400
  --min-effective-seconds 21600
  --max-steps 1000000
  --log-every 250
  --val-every 2500
  --lr "${LR}"
  --out-root "${OUT_ROOT}"
  --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv
  --complete-oversample "${COMPLETE_OVERSAMPLE}"
  --oversample-foreground "${OVERSAMPLE_FOREGROUND}"
  --scar-weight "${SCAR_WEIGHT}"
  --edema-weight "${EDEMA_WEIGHT}"
  --retrieval-entropy-floor 0.55
  --retrieval-entropy-weight 0.05
  --retrieval-coverage-weight 0.06
  --retrieval-max-weight-penalty 0.04
  --proposal-bce-weight "${PROPOSAL_BCE}"
  --proposal-margin-weight "${PROPOSAL_MARGIN_WEIGHT}"
  --proposal-uncertainty-weight "${PROPOSAL_UNCERTAINTY_WEIGHT}"
  --proposal-margin 0.25
  --proposal-final-mix-weight "${PROPOSAL_FINAL_MIX}"
  --hardneg-sample-prob "${HARDNEG_PROB}"
  "${EXTRA_FLAGS[@]}"
)

echo "preflight=${OUTPUT_VARIANT}"
"${CARE_ROOT}/envs/env_CARE/bin/python" -u scripts/training/run_srr_myops_fold0.py \
  "${COMMON_ARGS[@]}" \
  --out-root "${PREFLIGHT_OUT_ROOT}" \
  --max-steps 2 \
  --max-runtime-seconds 600 \
  --min-effective-seconds 0 \
  --log-every 1 \
  --val-every 1 \
  --skip-export

echo "formal=${OUTPUT_VARIANT}"
"${CARE_ROOT}/envs/env_CARE/bin/python" -u scripts/training/run_srr_myops_fold0.py "${COMMON_ARGS[@]}"
