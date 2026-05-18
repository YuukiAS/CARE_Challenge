#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=U-MyoPS-Smoke
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# Short GPU sanity run for U-MyoPS (see AGENTS.md logging). Does not package validation zips.
#
# UMYOPS_SMOKE_TARGET:
#   stage2 (default) — pathology nnU-Net v1; skips full preprocess rebuild when UMYOPS_STAGE2_AUTO_PREP=0.
#   stage1         — prepare (subset) + joint registration / myocardium for a few epochs.
#
# Common overrides:
#   UMYOPS_STAGE2_EPOCHS=5 UMYOPS_STAGE2_AUTO_PREP=0 FOLD=0
#   UMYOPS_STAGE1_EPOCHS=3 UMYOPS_PREPARE_MAX_CASES=12 PREPARE=1
set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"

# Slurm copies the batch script to a spool path; dirname(BASH_SOURCE) is not the repo. Prefer submit dir.
if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  CARE_ROOT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
  THIS_DIR="${CARE_ROOT}/jobs/U-MyoPS"
else
  THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
fi
export CARE_ROOT
cd "${CARE_ROOT}"

TS="$(date +%Y%m%d_%H%M%S)"
export LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/U-MyoPS_Smoke_${SLURM_JOB_ID:-local}_${TS}.log}"

TARGET="${UMYOPS_SMOKE_TARGET:-stage2}"
case "${TARGET}" in
  stage2)
    export FOLD="${FOLD:-0}"
    export UMYOPS_STAGE2_AUTO_PREP="${UMYOPS_STAGE2_AUTO_PREP:-0}"
    export UMYOPS_STAGE2_EPOCHS="${UMYOPS_STAGE2_EPOCHS:-5}"
    export UMYOPS_STAGE2_WHICH_SUBNET="${UMYOPS_STAGE2_WHICH_SUBNET:-scar}"
    exec /bin/bash "${THIS_DIR}/sbatch_stage2.sh"
    ;;
  stage1)
    export FOLD="${FOLD:-0}"
    export UMYOPS_STAGE1_EPOCHS="${UMYOPS_STAGE1_EPOCHS:-3}"
    export UMYOPS_PREPARE_MAX_CASES="${UMYOPS_PREPARE_MAX_CASES:-16}"
    export PREPARE="${PREPARE:-1}"
    exec /bin/bash "${THIS_DIR}/sbatch_stage1.sh"
    ;;
  *)
    echo "error: UMYOPS_SMOKE_TARGET must be stage1 or stage2, got: ${TARGET}" >&2
    exit 1
    ;;
esac
