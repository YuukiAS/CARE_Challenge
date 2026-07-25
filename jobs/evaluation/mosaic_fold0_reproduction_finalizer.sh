#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=MoSAICF0Fin
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
if [[ -z "${MOSAIC_JOB_IDS:-}" ]]; then
  MOSAIC_JOB_IDS="$("${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PY_IDS'
import json
import os
from pathlib import Path

root = Path(os.environ.get("RESULT_ROOT", "results/20260725_care_myops_mosaic_fold0_reproduction"))
receipt = root / "slurm_submission_receipt.json"
if not receipt.is_file():
    print("")
    raise SystemExit(0)
payload = json.loads(receipt.read_text())
ids = [payload.get("coarse_job_id"), payload.get("scar_job_id"), payload.get("edema_job_id")]
print(":".join(str(x) for x in ids if x))
PY_IDS
)"
fi
mkdir -p "${CARE_ROOT}/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MoSAICF0_finalizer_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "===== MoSAIC fold0 finalizer ====="
echo "CARE_ROOT=${CARE_ROOT}"
echo "RESULT_ROOT=${RESULT_ROOT}"
echo "MOSAIC_JOB_IDS=${MOSAIC_JOB_IDS:-}"
echo "LOG_FILE=${LOG_FILE}"
"${CARE_ROOT}/envs/env_CARE/bin/python" \
  "${CARE_ROOT}/scripts/evaluation/finalize_mosaic_fold0_reproduction.py" \
  --config "${CARE_ROOT}/configs/baselines/mosaic_fold0_fair.yaml" \
  --result-root "${RESULT_ROOT}" \
  --gpu "${MOSAIC_GPU:-0}" \
  --job-ids "${MOSAIC_JOB_IDS:-}"

echo "===== MoSAIC fold0 finalizer done ====="
