#!/usr/bin/env bash
# Train CineMyoPS upstream entry (legacy nnU-Net v1 inside third_party/CineMyoPS/code).
# Prepare data first: python scripts/cinemyops/prepare_task025_from_care.py
# Then this script links the task into the repo-relative paths expected by nnunet/paths.py and runs Lascar_3_train.py.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/CineMyoPS"
CODE="${REPO}/code"
TASK_SRC="${CINEMYOPS_TASK_SRC:-${CARE_ROOT}/data/benchmarks/CineMyoPS/Task025_Cine_Seg}"
PY="${LEGACY_PYTHON:-${CARE_ROOT}/env_CARE/bin/python}"

if [[ ! -f "${TASK_SRC}/dataset.json" ]]; then
  echo "Missing ${TASK_SRC}/dataset.json. Run:" >&2
  echo "  python ${SCRIPT_DIR}/prepare_task025_from_care.py --output ${TASK_SRC}" >&2
  exit 1
fi

RAW_BASE="${CODE}/../outputs/nnunet/raw"
mkdir -p "${RAW_BASE}/nnUNet_raw_data"
ln -sfn "${TASK_SRC}" "${RAW_BASE}/nnUNet_raw_data/Task025_Cine_Seg"

mkdir -p "${CODE}/../outputs/nnunet/prepro" "${CODE}/../outputs/nnunet/output"
cd "${CODE}"
export PYTHONPATH="${CODE}:${PYTHONPATH:-}"
exec "${PY}" ./Lascar_3_train.py 3d_fullres TrainerV6WithoutIMG Task025_Cine_Seg all "$@"
