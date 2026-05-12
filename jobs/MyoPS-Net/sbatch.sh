#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=MyoPS-Net_D501
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# MyoPS-Net (third_party/MyoPS-Net). Optional prepare when PREPARE=1.
set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${THIS_DIR}/../.." && pwd)}"
cd "${CARE_ROOT}"
export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/MyoPS-Net_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${CARE_ROOT}/env_CARE/bin/python"
PREP="${CARE_ROOT}/code/MyoPS-Net/prepare_myops_net_layout.py"
SPLITS="${SPLITS_FILE:-${CARE_ROOT}/data/benchmarks/protocol/splits_MyoPS.json}"
FOLD="${FOLD:-0}"
DATA="${MYOPS_NET_DATA:-${CARE_ROOT}/data/benchmarks/MyoPS-Net/fold_${FOLD}}"
WORKDIR="${MYOPS_NET_WORKDIR:-${CARE_ROOT}/results/checkpoints/MyoPS-Net/fold_${FOLD}}"

export MYOPS_NET_DATA="${DATA}"
export MYOPS_NET_WORKDIR="${WORKDIR}"

echo "===== MyoPS-Net train (data=${DATA}, workdir=${WORKDIR}, fold=${FOLD}) ====="

if [[ "${PREPARE:-1}" == "1" ]]; then
  "${PY}" "${PREP}" --splits-file "${SPLITS}" --fold "${FOLD}" --output "${DATA}"
fi

bash "${CARE_ROOT}/code/MyoPS-Net/run_train.sh" "$@"
echo "===== MyoPS-Net done ====="
