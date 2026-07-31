
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
cd "${CARE_ROOT}"
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MyoPathA0A3_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
"${PYTHON_BIN}" - <<'INNERPY'
import sys, torch
print('python_executable', sys.executable)
print('torch_version', torch.__version__)
print('cuda_available', torch.cuda.is_available())
INNERPY
"${PYTHON_BIN}" scripts/training/care_myopath_pilot/run_pilot.py --mode preflight
