#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareASER2
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
cd "${CARE_ROOT}"
CURRENT_SOURCE_SHA="$(git rev-parse HEAD)"
if [[ -z "${EXPECTED_TRAINING_SOURCE_SHA:-}" && "${ALLOW_UNREVIEWED_LOCAL_SMOKE:-0}" != "1" ]]; then
  echo "EXPECTED_TRAINING_SOURCE_SHA is required for formal CARE-ASE R2 execution" >&2
  exit 64
fi
if [[ -n "${EXPECTED_TRAINING_SOURCE_SHA:-}" && "${CURRENT_SOURCE_SHA}" != "${EXPECTED_TRAINING_SOURCE_SHA}" ]]; then
  echo "source SHA mismatch: current=${CURRENT_SOURCE_SHA} expected=${EXPECTED_TRAINING_SOURCE_SHA}" >&2
  exit 65
fi
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CareASER2_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

FOLD="${FOLD:?FOLD is required and must be 1 or 4}"
START_STEP="${START_STEP:?START_STEP is required}"
END_STEP="${END_STEP:?END_STEP is required}"
OUTPUT_DIR="${OUTPUT_DIR:-${CARE_ROOT}/results/20260803_care_ase_r2_full_fidelity_execution/runtime/fold_${FOLD}}"
PATCH_SIZE="${PATCH_SIZE:-20,256,256}"
SEED="${SEED:-20260803}"

cmd=(
  "${CARE_ROOT}/envs/env_CARE/bin/python"
  "${CARE_ROOT}/scripts/training/care_ase/run_care_ase_r2_chunk.py"
  --fold "${FOLD}"
  --start-step "${START_STEP}"
  --end-step "${END_STEP}"
  --patch-size "${PATCH_SIZE}"
  --output-dir "${OUTPUT_DIR}"
  --seed "${SEED}"
)

if [[ -n "${RESUME_CHECKPOINT:-}" ]]; then
  cmd+=(--resume-checkpoint "${RESUME_CHECKPOINT}")
fi

printf 'CARE-ASE R2 formal command:'
printf ' %q' "${cmd[@]}"
printf '\n'
"${cmd[@]}"
