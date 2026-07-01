#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=RePropF0
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=07:30:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#SBATCH --array=0-2

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
VARIANTS=(
  repaired_uncertainty_hardneg
  repaired_posneg_scar_hardneg
  repaired_joint_calibrated_proposal
)
VARIANT="${VARIANTS[${SLURM_ARRAY_TASK_ID:-0}]}"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/RePropF0_${VARIANT}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "LOG_FILE=${LOG_FILE}"
echo "variant=${VARIANT}"
echo "partition=${SLURM_JOB_PARTITION:-local}"
date

COMMON_ARGS=(
  --variant "${VARIANT}"
  --fold 0
  --device cuda
  --base-channels 16
  --patch-shape 12,96,96
  --batch-size 2
  --max-runtime-seconds 23400
  --min-effective-seconds 21600
  --max-steps 1000000
  --log-every 500
  --val-every 5000
  --out-root results/20260629_repaired_proposal_repeat
  --hardneg-components-csv results/20260629_proposal_memory_hardneg/mined_components.csv
  --retrieval-entropy-floor 0.70
  --retrieval-entropy-weight 0.08
  --retrieval-coverage-weight 0.10
  --retrieval-max-weight-penalty 0.05
)

case "${VARIANT}" in
  repaired_uncertainty_hardneg)
    EXTRA_ARGS=(--proposal-bce-weight 0.44 --proposal-margin-weight 0.22 --proposal-uncertainty-weight 0.10 --proposal-margin 0.25 --proposal-final-mix-weight 0.45 --hardneg-sample-prob 0.35)
    ;;
  repaired_posneg_scar_hardneg)
    EXTRA_ARGS=(--proposal-bce-weight 0.46 --proposal-margin-weight 0.30 --proposal-uncertainty-weight 0.02 --proposal-margin 0.30 --proposal-final-mix-weight 0.40 --hardneg-sample-prob 0.40 --scar-weight 1.45)
    ;;
  repaired_joint_calibrated_proposal)
    EXTRA_ARGS=(--proposal-bce-weight 0.45 --proposal-margin-weight 0.24 --proposal-uncertainty-weight 0.08 --proposal-margin 0.25 --proposal-final-mix-weight 0.50 --hardneg-sample-prob 0.30)
    ;;
  *)
    echo "unknown variant ${VARIANT}" >&2
    exit 2
    ;;
esac

echo "preflight=${VARIANT}"
"${CARE_ROOT}/envs/env_CARE/bin/python" -u scripts/training/run_srr_myops_fold0.py \
  "${COMMON_ARGS[@]}" \
  "${EXTRA_ARGS[@]}" \
  --out-root results/20260629_repaired_proposal_repeat/preflight \
  --max-steps 2 \
  --max-runtime-seconds 600 \
  --min-effective-seconds 0 \
  --log-every 1 \
  --val-every 1 \
  --skip-export

echo "formal=${VARIANT}"
"${CARE_ROOT}/envs/env_CARE/bin/python" -u scripts/training/run_srr_myops_fold0.py "${COMMON_ARGS[@]}" "${EXTRA_ARGS[@]}"
