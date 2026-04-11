#!/usr/bin/env bash
# Train MyoPS-Net after prepare_myops_net_layout.py (see data/benchmarks/MyoPS-Net/README.md).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/MyoPS-Net"
DATA="${CARE_ROOT}/data/benchmarks/MyoPS-Net"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"

if [[ ! -f "${DATA}/train.txt" ]]; then
  echo "Missing ${DATA}/train.txt. Run:" >&2
  echo "  python ${SCRIPT_DIR}/prepare_myops_net_layout.py --output ${DATA}" >&2
  exit 1
fi
cd "${REPO}"
exec python main.py --path "${DATA}" --batch_size 16 --dim 192 --lr 1e-4 --threshold 0.50 --end_epoch 200 "$@"
