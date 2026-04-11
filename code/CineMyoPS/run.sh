#!/usr/bin/env bash
# CineMyoPS paper repo (NanYoMy/CineMyoPS): Task025 + Lascar trainer; legacy nnU-Net v1 under third_party.
# Not the same as CARE nnU-Net v2 dataset-502 job (see code/nnUNet/run_CineMyoPS.sh).
set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
TASK="${CARE_ROOT}/data/benchmarks/CineMyoPS/Task025_Cine_Seg"

if [[ ! -f "${TASK}/dataset.json" ]]; then
  echo "Preparing Task025 under ${TASK} ..."
  "${CARE_ROOT}/env_CARE/bin/python" "${CARE_ROOT}/scripts/cinemyops/prepare_task025_from_care.py" --output "${TASK}"
fi
exec bash "${CARE_ROOT}/scripts/cinemyops/run_train.sh" "$@"
