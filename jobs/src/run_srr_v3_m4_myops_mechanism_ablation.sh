#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=SRRv3M4Abl
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"

source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/SRRv3M4Ablation_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "[SRRv3M4Ablation] start $(date -Is)"
echo "[SRRv3M4Ablation] CARE_ROOT=${CARE_ROOT}"
echo "[SRRv3M4Ablation] LOG_FILE=${LOG_FILE}"

python scripts/evaluation/run_srr_v3_m4_mechanism_ablation.py \
  --output-dir results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness \
  --m3-dir results/20260705_srr_v3_m3_myops_min_effective_pilot_training \
  --m3-variant srr_v3_m3_shared_dual_dict_pilot \
  --device cuda

echo "[SRRv3M4Ablation] end $(date -Is)"
