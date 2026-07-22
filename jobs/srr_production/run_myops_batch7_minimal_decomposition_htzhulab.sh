#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=B7MinDec
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
PATHOLOGY="${PATHOLOGY:?set PATHOLOGY to scar or edema}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
export PARTITION_LABEL=htzhulab
mkdir -p logs/srr_batch7_minimal_decomposition
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/srr_batch7_minimal_decomposition/B7MinDec_${PATHOLOGY}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

"${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PYCHECK'
import torch
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS
model = SRRProposeRefineMyoPS(
    base_channels=4,
    variant="m10_d3_hierarchical_memory_propref",
    encoder_profile="tiny_3scale",
    final_output_mode="anchor_bounded_srr_correction",
    enable_batch7_decomposition_br2=True,
)
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
print({"cuda_available": torch.cuda.is_available(), "cuda_device_count": torch.cuda.device_count(), "optimizer_param_groups": len(optimizer.param_groups)})
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not visible inside Batch7 minimal decomposition Slurm job")
PYCHECK

EXTRA_ARGS=()
if [[ "${PRINT_CONTRACT:-0}" == "1" ]]; then
  EXTRA_ARGS+=(--print-contract)
fi
ATTEMPT_LABEL="${ATTEMPT_LABEL:-batch7_minimal_decomposition_${PATHOLOGY}_${PARTITION_LABEL}_${SLURM_JOB_ID:-local}}"
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_srr_batch7_minimal_decomposition.py   --pathology "${PATHOLOGY}"   --attempt-label "${ATTEMPT_LABEL}"   "${EXTRA_ARGS[@]}"
