#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=MyoPathA0A3
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE_worktrees/task_myopath_a0_a3_20260731}"
PYTHON_BIN="${PYTHON_BIN:-/users/a/e/aereinh/CARE/envs/env_CARE/bin/python}"
TASK_OUT_DIR="${TASK_OUT_DIR:-${CARE_ROOT}/results/20260731_care_myopath_pr_a0_a3_feasibility}"
MODE="${MODE:-formal-train}"
VARIANT="${VARIANT:-A1}"
STEPS="${STEPS:-}"
PATCH_SHAPE="${PATCH_SHAPE:-16x64x64}"
LOG_EVERY="${LOG_EVERY:-50}"
CHECKPOINT_EVERY="${CHECKPOINT_EVERY:-500}"
SEED="${SEED:-20260731}"
cd "${CARE_ROOT}"
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MyoPathA0A3_${MODE}_${VARIANT}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
printf 'log_file %s\n' "${LOG_FILE}"
printf 'care_root %s\n' "${CARE_ROOT}"
printf 'python_bin %s\n' "${PYTHON_BIN}"
printf 'mode %s\n' "${MODE}"
printf 'variant %s\n' "${VARIANT}"
"${PYTHON_BIN}" - <<'INNERPY'
import sys, torch
print('python_executable', sys.executable)
print('torch_version', torch.__version__)
print('cuda_available', torch.cuda.is_available())
if torch.cuda.is_available():
    print('cuda_device_count', torch.cuda.device_count())
    print('cuda_device_name', torch.cuda.get_device_name(0))
INNERPY
case "${MODE}" in
  preflight)
    "${PYTHON_BIN}" scripts/training/care_myopath_pilot/run_pilot.py --mode preflight --out-dir "${TASK_OUT_DIR}"
    ;;
  a0-identity)
    "${PYTHON_BIN}" scripts/training/care_myopath_pilot/run_pilot.py --mode a0-identity --out-dir "${TASK_OUT_DIR}"
    ;;
  formal-train)
    EXTRA_ARGS=()
    if [[ -n "${STEPS}" ]]; then EXTRA_ARGS+=(--steps "${STEPS}"); fi
    "${PYTHON_BIN}" scripts/training/care_myopath_pilot/run_pilot.py --mode formal-train --variant "${VARIANT}" --patch-shape "${PATCH_SHAPE}" --log-every "${LOG_EVERY}" --checkpoint-every "${CHECKPOINT_EVERY}" --seed "${SEED}" --out-dir "${TASK_OUT_DIR}" "${EXTRA_ARGS[@]}"
    ;;
  *)
    echo "unsupported MODE=${MODE}" >&2
    exit 2
    ;;
esac
