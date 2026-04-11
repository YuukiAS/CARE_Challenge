#!/usr/bin/env bash
# U-MyoPS (NanYoMy/myops): stage 1 = joint registration; stage 2 = pathology (legacy nnU-Net v1).
set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
STAGE="${STAGE:-1}"
BENCH="${CARE_ROOT}/data/benchmarks/U-MyoPS/gen_ZS_unaligned/data"

if [[ ! -d "${BENCH}" ]] || [[ -z "$(ls -A "${BENCH}" 2>/dev/null)" ]]; then
  echo "Preparing U-MyoPS data under ${BENCH} ..."
  "${CARE_ROOT}/env_CARE/bin/python" "${CARE_ROOT}/scripts/u_myops/prepare_u_myops_from_care.py"
fi

if [[ "${STAGE}" == "2" ]]; then
  exec bash "${CARE_ROOT}/scripts/u_myops/run_stage2.sh" "$@"
fi
exec bash "${CARE_ROOT}/scripts/u_myops/run_stage1.sh" "$@"
