#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=RouteBTrainEval
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE_worktrees/route_B}"
cd "${CARE_ROOT}"

mkdir -p logs/route_B
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/route_B/RouteBTrainEval_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

export PYTHONUNBUFFERED=1
MAIN_CARE_ROOT="${MAIN_CARE_ROOT:-/users/a/e/aereinh/CARE}"
if [[ -f "${MAIN_CARE_ROOT}/.care-codex-env.sh" ]]; then
  # Keep runtime/cache/auth paths consistent with the active /users CARE copy.
  source "${MAIN_CARE_ROOT}/.care-codex-env.sh"
fi
if [[ -f "${MAIN_CARE_ROOT}/env_nnunet.sh" ]]; then
  source "${MAIN_CARE_ROOT}/env_nnunet.sh"
fi
export PATH="/users/a/e/aereinh/codex-runtime/bin:${MAIN_CARE_ROOT}/envs/env_CARE/bin:${PATH}"
CARE_PYTHON="${CARE_PYTHON:-${MAIN_CARE_ROOT}/envs/env_CARE/bin/python}"
if [[ ! -x "${CARE_PYTHON}" ]]; then
  echo "ERROR: CARE_PYTHON is not executable: ${CARE_PYTHON}" >&2
  exit 127
fi
"${CARE_PYTHON}" - <<'PYINFO'
import sys
print(f"python_executable={sys.executable}")
try:
    import torch
    print(f"torch_version={torch.__version__}")
    print(f"cuda_available={torch.cuda.is_available()}")
except Exception as exc:
    print(f"torch_import_error={type(exc).__name__}: {exc}")
    raise
PYINFO

RACE_LOCK_ROOT="${CARE_ROOT}/results/route_B/locks"
RACE_LOCK_DIR="${RACE_LOCK_ROOT}/bounded_train_eval_winner.lock"
mkdir -p "${RACE_LOCK_ROOT}"
if mkdir "${RACE_LOCK_DIR}" 2>/dev/null; then
  echo "race_status=RACE_WINNER"
  {
    echo "winner_job_id=${SLURM_JOB_ID:-local}"
    echo "winner_partition=${SLURM_JOB_PARTITION:-unknown}"
    echo "winner_host=$(hostname)"
    echo "winner_started_at=$(date -Is)"
    echo "winner_log=${LOG_FILE}"
  } > "${RACE_LOCK_DIR}/winner.txt"
else
  echo "race_status=RACE_LOST"
  echo "winner_lock=${RACE_LOCK_DIR}"
  if [[ -f "${RACE_LOCK_DIR}/winner.txt" ]]; then
    cat "${RACE_LOCK_DIR}/winner.txt"
  fi
  exit 0
fi

"${CARE_PYTHON}" -u scripts/training/route_B/run_bounded_train_eval.py --steps "${ROUTE_B_STEPS:-500}" --myops-eval-cases 10 --cine-eval-cases 5
