#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRv2Light
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
OUT_ROOT="${OUT_ROOT:-results/20260629_srr_v2_unet_core/light_refine_extras}"
PREFLIGHT_OUT_ROOT="${PREFLIGHT_OUT_ROOT:-${OUT_ROOT}/preflight}"

case "${SLURM_ARRAY_TASK_ID:-0}" in
  0)
    OUTPUT_VARIANT="srr_v2_light_refine_lowmix"
    SEED="2026070101"
    LR="0.0008"
    PROPOSAL_FINAL_MIX="0.25"
    HARDNEG_PROB="0.15"
    PROPOSAL_BCE="0.36"
    PROPOSAL_MARGIN_WEIGHT="0.18"
    PROPOSAL_UNCERTAINTY_WEIGHT="0.06"
    ;;
  1)
    OUTPUT_VARIANT="srr_v2_light_refine_hardneg"
    SEED="2026070102"
    LR="0.0008"
    PROPOSAL_FINAL_MIX="0.35"
    HARDNEG_PROB="0.45"
    PROPOSAL_BCE="0.42"
    PROPOSAL_MARGIN_WEIGHT="0.24"
    PROPOSAL_UNCERTAINTY_WEIGHT="0.12"
    ;;
  *)
    echo "Unsupported SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID}; expected 0 or 1" >&2
    exit 2
    ;;
esac

LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRv2Light_${OUTPUT_VARIANT}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "variant=srr_v2_light_refine"
echo "output_variant=${OUTPUT_VARIANT}"
echo "partition=${SLURM_JOB_PARTITION:-local}"
echo "OUT_ROOT=${OUT_ROOT}"
echo "PREFLIGHT_OUT_ROOT=${PREFLIGHT_OUT_ROOT}"
date

COMMON_ARGS=(
  --variant srr_v2_light_refine
  --output-variant-name "${OUTPUT_VARIANT}"
  --fold 0
  --seed "${SEED}"
  --device cuda
  --base-channels 8
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
