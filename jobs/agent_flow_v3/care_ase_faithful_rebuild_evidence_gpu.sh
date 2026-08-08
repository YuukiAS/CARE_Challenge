#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CAREASEEvidence
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=00:45:00
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE_agent_flow/care-ase-faithful/controller}"
CARE_RUNTIME_ROOT="${CARE_RUNTIME_ROOT:-/users/a/e/aereinh/CARE}"
CARE_PYTHON="${CARE_PYTHON:-${CARE_RUNTIME_ROOT}/envs/env_CARE/bin/python}"

mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/CAREASEEvidence_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

cd "${CARE_ROOT}"

export PYTHONDONTWRITEBYTECODE=1
export CARE_ROOT="${CARE_RUNTIME_ROOT}"
export nnUNet_raw="${CARE_RUNTIME_ROOT}/data/nnUNet/nnUNet_raw"
export nnUNet_preprocessed="${CARE_RUNTIME_ROOT}/data/nnUNet/nnUNet_preprocessed"
export nnUNet_results="${CARE_RUNTIME_ROOT}/data/nnUNet/nnUNet_results"
export MPLCONFIGDIR="${CARE_RUNTIME_ROOT}/.tmp/codex-verifier/matplotlib"

echo "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "slurm_job_id=${SLURM_JOB_ID:-local}"
echo "hostname=$(hostname)"
echo "care_root=${PWD}"
echo "care_runtime_root=${CARE_RUNTIME_ROOT}"
echo "care_python=${CARE_PYTHON}"
echo "formal_training_started=false"
echo "outer_accessed=false"
echo "docker_or_upload=false"
"${CARE_PYTHON}" - <<'INNER_PY'
import torch
print("torch_version=" + torch.__version__)
print("cuda_available=" + str(torch.cuda.is_available()))
print("cuda_device_count=" + str(torch.cuda.device_count()))
if torch.cuda.is_available():
    print("cuda_device_name=" + torch.cuda.get_device_name(0))
INNER_PY

"${CARE_PYTHON}" scripts/training/care_ase/build_care_ase_faithful_implementation_evidence.py --repo-root .
echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
