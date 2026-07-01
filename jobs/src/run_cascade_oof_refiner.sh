#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CascadeOOFRefine
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=07:30:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

export CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
export CODEX_HOME="${CODEX_HOME:-/users/a/e/aereinh/.codex-home-care}"
export CODEX_HOME_BASE="${CODEX_HOME_BASE:-/users/a/e/aereinh/.codex-homes}"
export CODEX_REPO_ROOT="${CODEX_REPO_ROOT:-${CARE_ROOT}}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/users/a/e/aereinh/.cache/codex-care}"
export TMPDIR="${TMPDIR:-/users/a/e/aereinh/.tmp/codex-care}"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

cd "${CARE_ROOT}"
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CascadeOOFRefine_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

if [[ -n "${SLURM_ARRAY_TASK_ID:-}" && -z "${VARIANT:-}" ]]; then
  case "${SLURM_ARRAY_TASK_ID}" in
    0) VARIANT="nnunet_anatomy_prior_refiner" ;;
    1) VARIANT="nnunet_pathology_teacher_srr_refiner" ;;
    2) VARIANT="coarse_to_fine_srr_roi" ;;
    *) echo "Unsupported SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID}; expected 0, 1, or 2" >&2; exit 2 ;;
  esac
fi

VARIANT="${VARIANT:-nnunet_anatomy_prior_refiner}"
RUN_NAME="${RUN_NAME:-${VARIANT}_oof_refiner}"
OUT_ROOT="${OUT_ROOT:-${CARE_ROOT}/results/20260629_cascade_teacher_route/variants/${VARIANT}}"
EPOCHS="${EPOCHS:-30}"
STEPS_PER_EPOCH="${STEPS_PER_EPOCH:-200}"
PATCH_SHAPE="${PATCH_SHAPE:-8,128,128}"
HIDDEN_CHANNELS="${HIDDEN_CHANNELS:-}"
DELTA_MAX="${DELTA_MAX:-}"
THRESHOLD="${THRESHOLD:-}"
SCAR_THRESHOLD="${SCAR_THRESHOLD:-}"
LR="${LR:-0.001}"
SEED="${SEED:-42}"

case "${VARIANT}" in
  nnunet_anatomy_prior_refiner)
    HIDDEN_CHANNELS="${HIDDEN_CHANNELS:-24}"
    DELTA_MAX="${DELTA_MAX:-1.0}"
    THRESHOLD="${THRESHOLD:-0.50}"
    SCAR_THRESHOLD="${SCAR_THRESHOLD:-0.80}"
    ;;
  nnunet_pathology_teacher_srr_refiner)
    HIDDEN_CHANNELS="${HIDDEN_CHANNELS:-32}"
    DELTA_MAX="${DELTA_MAX:-0.75}"
    THRESHOLD="${THRESHOLD:-0.55}"
    SCAR_THRESHOLD="${SCAR_THRESHOLD:-0.70}"
    ;;
  coarse_to_fine_srr_roi)
    HIDDEN_CHANNELS="${HIDDEN_CHANNELS:-24}"
    DELTA_MAX="${DELTA_MAX:-1.25}"
    THRESHOLD="${THRESHOLD:-0.45}"
    SCAR_THRESHOLD="${SCAR_THRESHOLD:-0.65}"
    ;;
  *)
    echo "Unsupported VARIANT=${VARIANT}" >&2
    exit 2
    ;;
esac

echo "CARE_ROOT=${CARE_ROOT}"
echo "LOG_FILE=${LOG_FILE}"
echo "VARIANT=${VARIANT}"
echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID:-none}"
echo "RUN_NAME=${RUN_NAME}"
echo "OUT_ROOT=${OUT_ROOT}"
echo "EPOCHS=${EPOCHS} STEPS_PER_EPOCH=${STEPS_PER_EPOCH}"
echo "HIDDEN_CHANNELS=${HIDDEN_CHANNELS} DELTA_MAX=${DELTA_MAX} THRESHOLD=${THRESHOLD} SCAR_THRESHOLD=${SCAR_THRESHOLD}"

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/preflight_cascade_teacher_cache.py \
  --out-dir "${CARE_ROOT}/results/20260629_cascade_teacher_route/teacher_cache" \
  --fold 0 \
  --teacher-mode oof5

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_laneA_round10_refiner_train.py \
  --run-name "${RUN_NAME}" \
  --out-root "${OUT_ROOT}" \
  --cascade-variant "${VARIANT}" \
  --epochs "${EPOCHS}" \
  --steps-per-epoch "${STEPS_PER_EPOCH}" \
  --lr "${LR}" \
  --hidden-channels "${HIDDEN_CHANNELS}" \
  --delta-max "${DELTA_MAX}" \
  --threshold "${THRESHOLD}" \
  --scar-threshold "${SCAR_THRESHOLD}" \
  --seed "${SEED}" \
  --patch-shape "${PATCH_SHAPE}"

echo "Cascade OOF refiner complete: ${OUT_ROOT}"
