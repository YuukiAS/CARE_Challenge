#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=MoSAICF0
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=8:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
cd "${CARE_ROOT}"

source "${CARE_ROOT}/.care-codex-env.sh" 2>/dev/null || true
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
export PYTHONUNBUFFERED=1

RESULT_ROOT="${RESULT_ROOT:-${CARE_ROOT}/results/20260725_care_myops_mosaic_fold0_reproduction}"
if [[ -z "${MOSAIC_STAGE:-}" ]]; then
  MOSAIC_STAGE="$("${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PY_STAGE'
import json
import os
from pathlib import Path

root = Path(os.environ.get("RESULT_ROOT", "results/20260725_care_myops_mosaic_fold0_reproduction"))
receipt = root / "slurm_submission_receipt.json"
job_id = os.environ.get("SLURM_JOB_ID", "")
if not receipt.is_file() or not job_id:
    raise SystemExit(1)
payload = json.loads(receipt.read_text())
mapping = {
    str(payload.get("coarse_job_id")): "coarse",
    str(payload.get("scar_job_id")): "scar",
    str(payload.get("edema_job_id")): "edema",
}
stage = mapping.get(job_id)
if not stage:
    raise SystemExit(1)
print(stage)
PY_STAGE
)"
fi
MOSAIC_STAGE="${MOSAIC_STAGE:?set MOSAIC_STAGE to coarse, scar, or edema}"
mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MoSAICF0_${MOSAIC_STAGE}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "===== MoSAIC fold0 stage ${MOSAIC_STAGE} ====="
echo "CARE_ROOT=${CARE_ROOT}"
echo "RESULT_ROOT=${RESULT_ROOT}"
echo "LOG_FILE=${LOG_FILE}"
echo "python=$(command -v python)"
"${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PYSMOKE'
import torch, sys
print('python_executable=' + sys.executable)
print('torch_version=' + torch.__version__)
print('cuda_available=' + str(torch.cuda.is_available()))
if not torch.cuda.is_available():
    raise SystemExit('CUDA unavailable for formal MoSAIC stage')
PYSMOKE

"${CARE_ROOT}/envs/env_CARE/bin/python" \
  "${CARE_ROOT}/scripts/training/run_mosaic_fold0_reproduction.py" \
  --config "${CARE_ROOT}/configs/baselines/mosaic_fold0_fair.yaml" \
  --result-root "${RESULT_ROOT}" \
  --stage "${MOSAIC_STAGE}" \
  --gpu "${MOSAIC_GPU:-0}"

echo "===== MoSAIC fold0 stage ${MOSAIC_STAGE} done ====="
