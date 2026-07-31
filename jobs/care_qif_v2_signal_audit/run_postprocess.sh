#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --job-name=QIFv2Post
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=128G
#SBATCH --time=4:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"

mkdir -p logs/care_qif_v2_signal_audit
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_qif_v2_signal_audit/QIFv2Post_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
CARE_PYTHON="${CARE_ROOT}/envs/env_CARE/bin/python"
export PYTHONUNBUFFERED=1

"${CARE_PYTHON}" - <<'PYINFO'
import sys
print(f"python_executable={sys.executable}")
import torch
print(f"torch_version={torch.__version__}")
print(f"cuda_available={torch.cuda.is_available()}")
print(f"cuda_device={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none'}")
PYINFO

"${CARE_PYTHON}" scripts/forensics/care_qif_v2_signal_audit/run_intensity_audit.py
"${CARE_PYTHON}" scripts/forensics/care_qif_v2_signal_audit/aggregate_intensity_audit.py
"${CARE_PYTHON}" scripts/evaluation/care_qif_v2_signal_audit/evaluate_query_pilot.py
