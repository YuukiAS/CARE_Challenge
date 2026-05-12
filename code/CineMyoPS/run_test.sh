#!/usr/bin/env bash
# Inference wrapper for CineMyoPS Lascar_4_test.py (requires same LEGACY_PYTHON / paths as training).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/CineMyoPS"
CODE="${REPO}/code"
CARE_CineMyoPS_ENV="${CARE_CineMyoPS_ENV:-${CARE_CINEMYOPS_ENV:-${CARE_ROOT}/env_CARE_nnUNet_v1}}"
PY="${LEGACY_PYTHON:-${CARE_CineMyoPS_ENV}/bin/python}"
cd "${CODE}"
export PYTHONPATH="${CODE}:${PYTHONPATH:-}"
exec "${PY}" ./Lascar_4_test.py "$@"
