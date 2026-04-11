#!/usr/bin/env bash
# Stage 1: joint registration + myocardium segmentation (jrs/joint_registration_myocardium_segmentation.py).
# Run from repo root after prepare_u_myops_from_care.py. Requires GPU for training.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/U-MyoPS_myops"
DATA_LINK="${REPO}/data/gen_ZS_unaligned/data"
BENCH_DATA="${CARE_ROOT}/data/benchmarks/U-MyoPS/gen_ZS_unaligned/data"
export PYTHONPATH="${REPO}/jrs:${REPO}:${PYTHONPATH:-}"

if [[ ! -d "${BENCH_DATA}" ]] || [[ -z "$(ls -A "${BENCH_DATA}" 2>/dev/null)" ]]; then
  echo "Missing prepared data under ${BENCH_DATA}. Run:" >&2
  echo "  python ${SCRIPT_DIR}/prepare_u_myops_from_care.py" >&2
  exit 1
fi

mkdir -p "${REPO}/data/gen_ZS_unaligned"
ln -sfn "${BENCH_DATA}" "${DATA_LINK}"

cd "${REPO}/jrs"
# shellcheck disable=SC2086
exec python joint_registration_myocardium_segmentation.py --phase train "$@"
