#!/usr/bin/env bash
# MyoPS-Net (QJYBall/MyoPS-Net): prepare data if needed, then train.
set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
DATA="${CARE_ROOT}/data/benchmarks/MyoPS-Net"
PREP="${CARE_ROOT}/scripts/myops_net/prepare_myops_net_layout.py"

if [[ ! -f "${DATA}/train.txt" ]]; then
  echo "Preparing MyoPS-Net layout under ${DATA} ..."
  "${CARE_ROOT}/env_CARE/bin/python" "${PREP}" --output "${DATA}"
fi
exec bash "${CARE_ROOT}/scripts/myops_net/run_train.sh" "$@"
