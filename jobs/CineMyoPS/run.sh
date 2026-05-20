#!/usr/bin/env bash
# Local: export CARE Cine → Task025 layout, then nnU-Net v1 training (bundled in third_party/CineMyoPS).
set -euo pipefail
CARE_ROOT="${CARE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export CARE_ROOT
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"
CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/envs/env_CARE_nnUNet_v1}}"
export PATH="${CARE_CineMyoPS_ENV}/bin:${PATH}"
PY="${CARE_CineMyoPS_ENV}/bin/python"

"${PY}" "${CARE_ROOT}/code/CineMyoPS/prepare_task025_from_care.py" "$@"
bash "${CARE_ROOT}/code/CineMyoPS/run_train.sh" "$@"
