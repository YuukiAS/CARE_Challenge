#!/usr/bin/env bash
# Stage 2: pathology nnUNet (legacy nnU-Net v1 API). Set LEGACY_PYTHON to a Python that has nnunet v1 installed.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/U-MyoPS_myops"
PY="${LEGACY_PYTHON:-}"

if [[ -z "${PY}" ]] || [[ ! -x "${PY}" ]]; then
  echo "LEGACY_PYTHON must point to a Python interpreter with nnU-Net v1 (pip install nnunet). Example:" >&2
  echo "  export LEGACY_PYTHON=/path/to/env/bin/python" >&2
  exit 1
fi

export PYTHONPATH="${REPO}/jrs:${REPO}:${PYTHONPATH:-}"
cd "${REPO}/jrs"
exec "${PY}" pathology_segmentation_train.py "$@"
